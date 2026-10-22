"""Regression coverage for file identity, no-op updates, and installation rollback."""
import argparse
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name + '_edges', SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


memory = module('project_memory')
installer = module('setup_skill')


class MemoryInstallEdges(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-memory-edges-')
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_memory(self, *arguments):
        output = StringIO()
        with redirect_stdout(output):
            code = memory.main([arguments[0], '--root', str(self.root), *arguments[1:]])
        return code, json.loads(output.getvalue())

    def init(self):
        self.assertEqual(self.run_memory('init', '--topic', 'Fixture', '--deliverable', 'report')[0], 0)
        return self.root / '.research-briefing/project.json'

    def test_fingerprint_rejects_same_size_and_timestamp_file_replacement(self):
        path = self.root / 'report.md'
        path.write_bytes(b'old report')
        original = path.stat()
        replacement = self.root / 'replacement.md'
        replacement.write_bytes(b'new report')
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        actual_open = Path.open

        class ReplaceOnExit:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self.stream

            def __exit__(self, *args):
                self.stream.close()
                os.replace(replacement, path)

        def replacing_open(target, *args, **kwargs):
            stream = actual_open(target, *args, **kwargs)
            return ReplaceOnExit(stream) if target == path and args == ('rb',) else stream

        with patch.object(Path, 'open', replacing_open):
            with self.assertRaisesRegex(memory.MemoryError, 'changed while being read'):
                memory.fingerprint(path)
        self.assertEqual(path.read_bytes(), b'new report')
        self.assertEqual(path.stat().st_size, original.st_size)
        self.assertEqual(path.stat().st_mtime_ns, original.st_mtime_ns)

    def test_bound_snapshot_rejects_incomplete_binding_fields(self):
        cfg = self.init()
        report = self.root / 'report.md'
        report.write_text('Fixture report', encoding='utf-8')
        config = json.loads(cfg.read_text(encoding='utf-8'))
        config['delivery']['expected_artifacts'] = [
            {'kind': 'report', 'path': report.name, 'version': '1', 'required': True}]
        cfg.write_text(json.dumps(config), encoding='utf-8')
        self.assertEqual(self.run_memory('snapshot', '--label', 'bound', '--expected')[0], 0)
        manifest = self.root / '.research-briefing/snapshots/bound.json'
        original = json.loads(manifest.read_text(encoding='utf-8'))
        for omitted in ('expected_artifacts', 'config_identity'):
            with self.subTest(omitted=omitted):
                changed = dict(original)
                changed.pop(omitted)
                manifest.write_text(json.dumps(changed), encoding='utf-8')
                code, result = self.run_memory('verify', '--manifest', str(manifest))
                self.assertEqual(code, 2)
                self.assertIn('together', result['message'])
        manifest.write_text(json.dumps(original), encoding='utf-8')
        self.assertEqual(self.run_memory('verify', '--manifest', str(manifest))[0], 0)

    def test_legacy_file_only_and_current_working_snapshots_remain_valid(self):
        report = self.root / 'report.md'
        report.write_text('Fixture report', encoding='utf-8')
        self.assertEqual(self.run_memory('snapshot', '--label', 'working', '--file', report.name)[0], 0)
        manifest = self.root / '.research-briefing/snapshots/working.json'
        self.assertEqual(self.run_memory('verify', '--manifest', str(manifest))[0], 0)
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['schema_version'] = memory.LEGACY
        manifest.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(self.run_memory('verify', '--manifest', str(manifest))[0], 0)

    def test_noop_update_preserves_exact_configuration_bytes(self):
        cfg = self.init()
        config = json.loads(cfg.read_text(encoding='utf-8'))
        original = b'\xef\xbb\xbf' + json.dumps(config, ensure_ascii=False, indent=4).replace('\n', '\r\n').encode('utf-8')
        cfg.write_bytes(original)
        for arguments in ((), ('--stage', 'initialized'), ('--add-deliverable', 'report'),
                          ('--memory-profile', 'compact')):
            with self.subTest(arguments=arguments):
                code, result = self.run_memory('update', *arguments)
                self.assertEqual(code, 0)
                self.assertEqual(cfg.read_bytes(), original)
                self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(self.run_memory('update', '--stage', 'researching')[0], 0)
        self.assertNotEqual(cfg.read_bytes(), original)
        updated = json.loads(cfg.read_text(encoding='utf-8'))
        self.assertEqual(updated['delivery']['current_stage'], 'researching')
        self.assertEqual(updated['skill_version'], config['skill_version'])

    def test_promotion_history_links_resolve_special_character_filenames(self):
        cfg = self.init()
        config = json.loads(cfg.read_text(encoding='utf-8'))
        history = self.root / '已有记录'
        history.mkdir()
        renamed = {}
        for index, relative in enumerate(dict.fromkeys(config['memory_documents'].values()), 1):
            target = history / ('旧 记录(%s)#片段[注].md' % index)
            (self.root / relative).rename(target)
            renamed[relative] = target.relative_to(self.root).as_posix()
        config['memory_documents'] = {key: renamed[value] for key, value in config['memory_documents'].items()}
        cfg.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
        originals = {path: path.read_bytes() for path in history.iterdir()}

        code, result = self.run_memory('update', '--memory-profile', 'full')
        self.assertEqual(code, 0, result)
        updated = json.loads(cfg.read_text(encoding='utf-8'))
        resolved_sources = set()
        for relative in set(updated['memory_documents'].values()):
            path = self.root / relative
            # A link destination cannot end at a filename's space or closing
            # parenthesis, and '#' in the filename must not become an anchor.
            first_line = path.read_text(encoding='utf-8').splitlines()[0]
            destinations = re.findall(r'\]\(([^)\s]+)\)', first_line)
            self.assertEqual(len(destinations), 1, first_line)
            uri = urlsplit(destinations[0])
            self.assertFalse(uri.fragment or uri.query or uri.scheme, destinations[0])
            target = (path.parent / unquote(uri.path)).resolve()
            self.assertIn(target, originals)
            self.assertEqual(target.read_bytes(), originals[target])
            resolved_sources.add(target)
        self.assertEqual(resolved_sources, set(originals))

    def test_noop_update_does_not_accept_numeric_boolean_substitutes(self):
        cfg = self.init()
        expected_path = self.root / 'expected.json'
        for valid_required, numeric_required in ((True, 1), (False, 0)):
            with self.subTest(required=numeric_required):
                expected = [{'kind': 'report', 'path': 'report.md', 'version': '1',
                             'required': valid_required}]
                expected_path.write_text(json.dumps(expected), encoding='utf-8')
                self.assertEqual(self.run_memory('update', '--expected-artifacts', expected_path.name)[0], 0)
                before = cfg.read_bytes()
                expected[0]['required'] = numeric_required
                expected_path.write_text(json.dumps(expected), encoding='utf-8')
                code, result = self.run_memory('update', '--expected-artifacts', expected_path.name)
                self.assertEqual(code, 2)
                self.assertIn('required must be boolean', result['message'])
                self.assertEqual(cfg.read_bytes(), before)

    def test_interrupted_installation_cleans_only_its_staging_copy(self):
        source = self.root / installer.NAME
        source.mkdir()
        (source / 'first.txt').write_text('fixture A', encoding='utf-8')
        (source / 'second.txt').write_text('fixture B', encoding='utf-8')
        before = installer.inventory(source)
        parent = self.root / 'skills'
        parent.mkdir()
        unrelated = parent / 'keep.txt'
        unrelated.write_text('user data', encoding='utf-8')
        args = argparse.Namespace(command='install', skills_dir=str(parent), host=None, scope=None, project=None)
        actual_copy = installer.shutil.copy2

        def fail_after_copy(src, dest):
            actual_copy(src, dest)
            raise OSError('simulated interrupted copy')

        with patch.object(installer, 'SOURCE', source), patch.object(
                installer, 'package_check', return_value=(before, [])), patch.object(
                installer.shutil, 'copy2', side_effect=fail_after_copy):
            with self.assertRaisesRegex(OSError, 'interrupted copy'):
                installer.install(args)
        self.assertEqual(installer.inventory(source), before)
        self.assertEqual(unrelated.read_text(encoding='utf-8'), 'user data')
        self.assertEqual([path.name for path in parent.iterdir()], ['keep.txt'])

    def test_planned_output_rejects_control_characters_without_changing_config(self):
        cfg = self.init()
        expected_path = self.root / 'expected.json'
        original = cfg.read_bytes()
        schema = json.loads((SCRIPTS.parent / 'assets/project.schema.json').read_text(encoding='utf-8'))
        path_pattern = schema['$defs']['path']['pattern']
        for bad_path in ('report.md\n', 'report.md\r\n'):
            self.assertIsNone(re.search(path_pattern, bad_path))
        for control in ('\x00', '\n', '\r', '\t', '\x7f'):
            with self.subTest(control=repr(control)):
                expected = [{'kind': 'report', 'path': 'planned/bad' + control + 'name.md',
                             'version': '1', 'required': True}]
                self.assertIsNone(re.search(path_pattern, expected[0]['path']))
                expected_path.write_text(json.dumps(expected), encoding='utf-8')
                code, result = self.run_memory('update', '--expected-artifacts', expected_path.name)
                self.assertEqual(code, 2)
                self.assertIn('control character', result['message'])
                self.assertEqual(cfg.read_bytes(), original)
        expected[0]['path'] = '计划成果/技术 报告.md'
        self.assertIsNotNone(re.search(path_pattern, expected[0]['path']))
        expected_path.write_text(json.dumps(expected), encoding='utf-8')
        self.assertEqual(self.run_memory('update', '--expected-artifacts', expected_path.name)[0], 0)

    def test_installation_reports_both_copy_and_cleanup_failures(self):
        source = self.root / installer.NAME
        source.mkdir()
        (source / 'file.txt').write_text('fixture', encoding='utf-8')
        before = installer.inventory(source)
        parent = self.root / 'skills'
        parent.mkdir()
        unrelated = parent / 'keep.txt'
        unrelated.write_text('user data', encoding='utf-8')
        output = StringIO()
        with patch.object(installer, 'SOURCE', source), patch.object(
                installer, 'package_check', return_value=(before, [])), patch.object(
                installer.shutil, 'copy2', side_effect=OSError('simulated copy failure')), patch.object(
                installer.shutil, 'rmtree', side_effect=PermissionError('simulated cleanup failure')):
            with redirect_stdout(output):
                code = installer.main(['install', '--skills-dir', str(parent)])
        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertIn('simulated copy failure', result['message'])
        self.assertIn('simulated cleanup failure', result['message'])
        self.assertIn('.rb-install-', result['message'])
        self.assertFalse((parent / installer.NAME).exists())
        self.assertEqual(installer.inventory(source), before)
        self.assertEqual(unrelated.read_text(encoding='utf-8'), 'user data')

    def test_installation_detects_source_changes_before_publishing(self):
        source = self.root / installer.NAME
        source.mkdir()
        content = source / 'file.txt'
        content.write_text('fixture A', encoding='utf-8')
        before = installer.inventory(source)
        parent = self.root / 'skills'
        args = argparse.Namespace(command='install', skills_dir=str(parent), host=None, scope=None, project=None)
        actual_copy = installer.shutil.copy2

        def change_after_copy(src, dest):
            result = actual_copy(src, dest)
            content.write_text('fixture B', encoding='utf-8')
            return result

        with patch.object(installer, 'SOURCE', source), patch.object(
                installer, 'package_check', return_value=(before, [])), patch.object(
                installer.shutil, 'copy2', side_effect=change_after_copy):
            with self.assertRaisesRegex(ValueError, 'changed during installation'):
                installer.install(args)
        self.assertEqual(content.read_text(encoding='utf-8'), 'fixture B')
        self.assertFalse(list(parent.iterdir()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
