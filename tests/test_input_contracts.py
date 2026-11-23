"""Regressions for JSON input boundaries and frozen delivery contracts."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name + '_input_contracts', SCRIPTS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


memory = module('project_memory')
audit = module('audit_content')


class InputContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-input-contracts-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_memory(self, *arguments):
        output = StringIO()
        with redirect_stdout(output):
            code = memory.main([arguments[0], '--root', str(self.root), *arguments[1:]])
        return code, json.loads(output.getvalue())

    def init(self):
        self.assertEqual(self.run_memory('init', '--topic', '输入回归', '--deliverable', 'report')[0], 0)
        return self.root / '.research-briefing/project.json'

    def test_bound_snapshot_cannot_shrink_frozen_contract_while_config_matches(self):
        cfg = self.init()
        config = json.loads(cfg.read_text(encoding='utf-8'))
        for name in ('report.md', 'appendix.md'):
            (self.root / name).write_text(name, encoding='utf-8')
        config['delivery']['expected_artifacts'] = [
            {'kind': 'report', 'path': name, 'version': '1', 'required': True}
            for name in ('report.md', 'appendix.md')]
        cfg.write_text(json.dumps(config), encoding='utf-8')
        self.assertEqual(self.run_memory('snapshot', '--label', 'bound', '--expected')[0], 0)
        manifest = self.root / '.research-briefing/snapshots/bound.json'
        original = manifest.read_bytes()
        reduced = json.loads(original)
        reduced['files'] = reduced['files'][:1]
        reduced['expected_artifacts'] = reduced['expected_artifacts'][:1]
        manifest.write_text(json.dumps(reduced), encoding='utf-8')
        (self.root / 'appendix.md').write_text('changed', encoding='utf-8')
        code, result = self.run_memory('verify', '--manifest', str(manifest))
        self.assertEqual(code, 2)
        self.assertIn('bound configuration', result['message'])
        manifest.write_bytes(original)
        code, result = self.run_memory('verify', '--manifest', str(manifest))
        self.assertEqual(code, 1)
        self.assertEqual(result['config_status'], 'match')
        self.assertEqual(result['findings'][0]['path'], 'appendix.md')

    def test_changed_config_is_a_difference_not_an_invalid_frozen_contract(self):
        cfg = self.init()
        report = self.root / 'report.md'
        report.write_text('report', encoding='utf-8')
        config = json.loads(cfg.read_text(encoding='utf-8'))
        config['delivery']['expected_artifacts'] = [
            {'kind': 'report', 'path': 'report.md', 'version': '1', 'required': True}]
        cfg.write_text(json.dumps(config), encoding='utf-8')
        self.assertEqual(self.run_memory('snapshot', '--label', 'bound', '--expected')[0], 0)
        config['delivery']['expected_artifacts'] = []
        cfg.write_text(json.dumps(config), encoding='utf-8')
        code, result = self.run_memory('verify', '--manifest', '.research-briefing/snapshots/bound.json')
        self.assertEqual(code, 1)
        self.assertEqual(result['config_status'], 'changed')

    def test_json_readers_reject_lone_surrogates_in_keys_and_values(self):
        path = self.root / 'input.json'
        for payload in ('{"text":"\\ud800"}', '{"\\udfff":"text"}'):
            for reader, error in ((memory.load_json, memory.MemoryError), (audit.read_json, audit.InputError)):
                with self.subTest(payload=payload, reader=reader.__module__):
                    path.write_text(payload, encoding='utf-8')
                    with self.assertRaises(error):
                        reader(path)

    def test_json_readers_accept_paired_surrogates_and_normal_unicode(self):
        path = self.root / 'input.json'
        path.write_text('{"中文":"\\ud83d\\ude80"}', encoding='utf-8')
        self.assertEqual(memory.load_json(path), {'中文': '🚀'})
        self.assertEqual(audit.read_json(path)[0], {'中文': '🚀'})

    def test_json_readers_enforce_container_depth_boundary(self):
        path = self.root / 'input.json'
        for depth in (128, 129, 20000):
            path.write_text('[' * depth + '0' + ']' * depth, encoding='utf-8')
            for reader, error in ((memory.load_json, memory.MemoryError), (audit.read_json, audit.InputError)):
                with self.subTest(depth=depth, reader=reader.__module__):
                    if depth == 128:
                        reader(path)
                    else:
                        with self.assertRaises(error):
                            reader(path)

    def test_deep_extensions_fail_before_update_and_preserve_config(self):
        cfg = self.init()
        config = json.loads(cfg.read_text(encoding='utf-8'))
        nested = 0
        for _ in range(600):
            nested = [nested]
        config['extensions'] = {'nested': nested}
        cfg.write_text(json.dumps(config), encoding='utf-8')
        original = cfg.read_bytes()
        for arguments in (('validate-config',), ('update', '--stage', 'planning')):
            code, result = self.run_memory(*arguments)
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'error')
            self.assertEqual(cfg.read_bytes(), original)

    def test_invalid_unicode_cli_returns_json_without_traceback(self):
        path = self.root / 'input.json'
        # Duplicate-key errors occur while decoding, before the tree validation.
        for payload in ('{"text":"\\ud800"}', '{"\\ud800":1,"\\ud800":2}'):
            path.write_text(payload, encoding='utf-8')
            for script, args in (
                    ('audit_content.py', ['--ledger', path.name]),
                    ('project_memory.py', ['verify', '--manifest', path.name])):
                with self.subTest(payload=payload, script=script):
                    result = subprocess.run(
                        [sys.executable, '-X', 'utf8', '-B', str(SCRIPTS / script),
                         *args, '--root', str(self.root)], capture_output=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertIn('status', json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
