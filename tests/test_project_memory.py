"""Portable helper regression tests. Run: python -B tests/test_project_memory.py"""
import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'project_memory.py'
spec = importlib.util.spec_from_file_location('project_memory_under_test', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class MemoryBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-skill-')
        self.root = Path(self.temp.name) / '中文项目'
        self.root.mkdir()
        self.cfg = self.root / '.research-briefing/project.json'

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, root=None):
        process = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SCRIPT), args[0],
                                  '--root', str(root or self.root), *args[1:]],
                                 capture_output=True, text=True, encoding='utf-8')
        self.assertNotIn('Traceback', process.stderr)
        return process.returncode, json.loads(process.stdout)

    def init(self, profile='compact'):
        return self.run_cli('init', '--topic', '研究方法测试', '--deliverable', 'report',
                            '--memory-profile', profile)

    def read_config(self):
        return json.loads(self.cfg.read_text(encoding='utf-8'))

    def save_config(self, config):
        self.cfg.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')

    def all_files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def expect(self, *items):
        path = self.root / 'expected.json'
        path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
        return self.run_cli('update', '--expected-artifacts', path.name)

    def artifact(self, path='报告.md', required=True):
        return {'kind': 'report', 'path': path, 'version': '1.0', 'required': required}

    def test_compact_configuration_has_separate_audiences_and_validates(self):
        self.assertEqual(self.init()[0], 0)
        config = self.read_config()
        self.assertEqual(config['schema_version'], helper.SCHEMA)
        self.assertEqual(set(config['brief']['audiences']), {'report', 'slides', 'author_explainer'})
        self.assertEqual(len(list((self.root / '研究辅助文档').glob('*.md'))), 3)
        self.assertEqual(self.run_cli('validate-config')[0], 0)

    def test_reinitialization_preserves_authored_records(self):
        self.assertEqual(self.init('full')[0], 0)
        docs = list((self.root / '研究辅助文档').glob('*.md'))
        self.assertEqual(len(docs), 6)
        docs[0].write_text('人工补充的重要决定', encoding='utf-8')
        before = self.all_files()
        self.assertEqual(self.init('full')[0], 2)
        self.assertEqual(before, self.all_files())

    def test_delivery_is_planned_until_explicit_completeness_check(self):
        self.init()
        self.assertEqual(self.expect(self.artifact())[0], 0)
        self.assertEqual(self.run_cli('validate-config')[0], 0)
        rc, result = self.run_cli('validate-config', '--check-delivery')
        self.assertEqual(rc, 1)
        self.assertEqual(result['findings'][0]['status'], 'missing-required')
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--expected')[0], 2)
        self.assertFalse((self.root / '.research-briefing/snapshots/v1.json').exists())

    def test_expected_snapshot_requires_all_required_selected_files(self):
        self.init()
        for name in ('报告.md', '附录.md'):
            (self.root / name).write_text('内容', encoding='utf-8')
        self.expect(self.artifact(), self.artifact('附录.md'))
        self.assertEqual(self.run_cli('snapshot', '--label', 'bad', '--expected', '--file', '报告.md')[0], 2)
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--expected')[0], 0)
        manifest = '.research-briefing/snapshots/v1.json'
        self.assertEqual(self.run_cli('verify', '--manifest', manifest)[0], 0)
        raw = json.loads((self.root / manifest).read_text(encoding='utf-8'))
        self.assertEqual(raw['expected_artifacts'][0]['version'], '1.0')
        self.assertEqual(len(raw['config_identity']['sha256']), 64)

    def test_expected_snapshot_binds_the_exact_configuration_bytes(self):
        self.init()
        (self.root / '报告.md').write_text('内容', encoding='utf-8')
        self.expect(self.artifact())
        raw_config = b'\xef\xbb\xbf' + json.dumps(self.read_config(), ensure_ascii=False,
                                                indent=2).replace('\n', '\r\n').encode('utf-8')
        self.cfg.write_bytes(raw_config)
        before = self.all_files()
        self.assertEqual(self.run_cli('snapshot', '--label', 'exact', '--expected')[0], 0)
        manifest = '.research-briefing/snapshots/exact.json'
        data = json.loads((self.root / manifest).read_text(encoding='utf-8'))
        self.assertEqual(data['config_identity'], {'path': '.research-briefing/project.json',
                         'bytes': len(raw_config), 'sha256': hashlib.sha256(raw_config).hexdigest()})
        rc, result = self.run_cli('verify', '--manifest', manifest)
        self.assertEqual(rc, 0)
        self.assertEqual(result['config_status'], 'match')
        self.assertEqual({p: (self.root / p).read_bytes() for p in before}, before)

    def test_expected_snapshot_rejects_a_configuration_update_during_read(self):
        self.init()
        for name in ('报告.md', '新版报告.md'):
            (self.root / name).write_text(name, encoding='utf-8')
        self.expect(self.artifact())
        before = self.all_files()
        updated = self.read_config()
        updated['delivery']['expected_artifacts'][0].update(path='新版报告.md', version='2.0')
        updated_bytes = json.dumps(updated, ensure_ascii=False).encode('utf-8')
        actual_read = Path.read_bytes
        changed = []

        def read_then_update(path):
            content = actual_read(path)
            if path == self.cfg and not changed:
                self.cfg.write_bytes(updated_bytes)
                changed.append(True)
            return content

        output = StringIO()
        with patch.object(Path, 'read_bytes', read_then_update), redirect_stdout(output):
            rc = helper.main(['snapshot', '--root', str(self.root), '--label', 'reading', '--expected'])
        self.assertTrue(changed)
        self.assertEqual(rc, 2)
        self.assertIn('Configuration changed', json.loads(output.getvalue())['message'])
        before['.research-briefing/project.json'] = updated_bytes
        self.assertEqual(self.all_files(), before)

    def test_expected_snapshot_rejects_a_configuration_update_while_fingerprinting(self):
        self.init()
        report = self.root / '报告.md'
        report.write_text('报告内容', encoding='utf-8')
        self.expect(self.artifact())
        before = self.all_files()
        updated = self.read_config()
        updated['delivery']['expected_artifacts'][0]['version'] = '2.0'
        updated_bytes = json.dumps(updated, ensure_ascii=False).encode('utf-8')
        actual_fingerprint = helper.fingerprint
        changed = []

        def fingerprint_then_update(path):
            identity = actual_fingerprint(path)
            if path == report and not changed:
                self.cfg.write_bytes(updated_bytes)
                changed.append(True)
            return identity

        output = StringIO()
        with patch.object(helper, 'fingerprint', side_effect=fingerprint_then_update), redirect_stdout(output):
            rc = helper.main(['snapshot', '--root', str(self.root), '--label', 'collecting', '--expected'])
        self.assertTrue(changed)
        self.assertEqual(rc, 2)
        self.assertIn('Configuration changed', json.loads(output.getvalue())['message'])
        before['.research-briefing/project.json'] = updated_bytes
        self.assertEqual(self.all_files(), before)

    def test_optional_missing_output_does_not_block_delivery(self):
        self.init()
        (self.root / '报告.md').write_text('内容', encoding='utf-8')
        self.expect(self.artifact(), self.artifact('附录.md', False))
        self.assertEqual(self.run_cli('validate-config', '--check-delivery')[0], 0)
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--expected')[0], 0)

    def test_unregistered_requested_kind_is_detected_before_acceptance(self):
        self.init()
        (self.root / '报告.md').write_text('内容', encoding='utf-8')
        self.expect(self.artifact())
        self.run_cli('update', '--add-deliverable', 'slides')
        rc, result = self.run_cli('validate-config', '--check-delivery')
        self.assertEqual(rc, 1)
        self.assertEqual(result['findings'], [{'kind': 'slides', 'status': 'unconfigured-deliverable'}])
        self.assertEqual(self.run_cli('snapshot', '--label', 'bad', '--expected')[0], 2)
        config = self.read_config()
        config['delivery']['expected_artifacts'].append({'kind': 'slides', 'path': '可选汇报.pptx', 'version': '1.0', 'required': False})
        self.save_config(config)
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--expected')[0], 0)

    def test_verify_detects_required_entry_removed_from_manifest(self):
        self.init()
        for name in ('报告.md', '附录.md'):
            (self.root / name).write_text('内容', encoding='utf-8')
        self.expect(self.artifact(), self.artifact('附录.md'))
        self.run_cli('snapshot', '--label', 'v1', '--expected')
        path = self.root / '.research-briefing/snapshots/v1.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['files'].pop()
        path.write_text(json.dumps(data), encoding='utf-8')
        rc, result = self.run_cli('verify', '--manifest', str(path))
        self.assertEqual(rc, 1)
        self.assertEqual(result['findings'][0]['status'], 'missing-from-manifest')

    def test_snapshot_detects_same_length_change_and_preserves_manifest(self):
        path = self.root / '报告.md'
        path.write_text('first', encoding='utf-8')
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--file', path.name)[0], 0)
        manifest = '.research-briefing/snapshots/v1.json'
        before = (self.root / manifest).read_bytes()
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--file', path.name)[0], 2)
        self.assertEqual((self.root / manifest).read_bytes(), before)
        path.write_text('other', encoding='utf-8')
        rc, result = self.run_cli('verify', '--manifest', manifest)
        self.assertEqual(rc, 1)
        self.assertEqual(result['findings'][0]['status'], 'changed')
        path.unlink()
        self.assertEqual(self.run_cli('verify', '--manifest', manifest)[1]['findings'][0]['status'], 'missing')

    def test_compact_promotion_keeps_authored_sources_and_creates_six_active_records(self):
        self.init()
        original = self.read_config()['memory_documents']
        source = self.root / original['standards']
        source.write_text('完全改写过的原始决定\n', encoding='utf-8')
        old = {p: (self.root / p).read_bytes() for p in set(original.values())}
        self.assertEqual(self.run_cli('update', '--add-deliverable', 'slides', '--memory-profile', 'full')[0], 0)
        config = self.read_config()
        self.assertEqual(config['deliverables'], ['report', 'slides'])
        self.assertEqual(config['memory_history'][0]['documents'], original)
        self.assertEqual(len(set(config['memory_documents'].values())), 6)
        for path, content in old.items():
            self.assertEqual((self.root / path).read_bytes(), content)
        self.assertIn('历史来源', (self.root / config['memory_documents']['standards']).read_text(encoding='utf-8'))
        self.assertEqual(self.run_cli('validate-config')[0], 0)

    def test_promotion_collision_and_invalid_update_leave_every_file_unchanged(self):
        self.init()
        collision = self.root / '研究辅助文档/01_写作与制作规范.md'
        collision.write_text('已有内容', encoding='utf-8')
        before = self.all_files()
        self.assertEqual(self.run_cli('update', '--memory-profile', 'full')[0], 2)
        self.assertEqual(self.all_files(), before)

    def test_failed_post_creation_validation_rolls_back_promotion_records(self):
        self.init()
        (self.root / 'expected.json').write_text('[{"bad":true}]', encoding='utf-8')
        before = self.all_files()
        self.assertEqual(self.run_cli('update', '--memory-profile', 'full', '--expected-artifacts', 'expected.json')[0], 2)
        self.assertEqual(self.all_files(), before)
        (self.root / 'expected.json').write_text('[{"bad":true}]', encoding='utf-8')
        before = self.all_files()
        self.assertEqual(self.run_cli('update', '--expected-artifacts', 'expected.json')[0], 2)
        self.assertEqual(self.all_files(), before)

    def test_legacy_migration_is_explicit_and_retains_original_configuration(self):
        self.init()
        config = self.read_config()
        config['schema_version'] = helper.LEGACY
        config.pop('skill_version')
        config.pop('memory_history')
        config['brief']['audience'] = '跨领域专家'
        config['brief'].pop('audiences')
        config['presentation'].pop('timing_plan')
        config['presentation'].pop('preference_profile')
        config['delivery'].pop('expected_artifacts')
        self.save_config(config)
        original = self.cfg.read_bytes()
        self.assertTrue(self.run_cli('validate-config')[1]['migration_required'])
        self.assertEqual(self.run_cli('update', '--add-deliverable', 'slides')[0], 2)
        self.assertEqual(original, self.cfg.read_bytes())
        self.assertEqual(self.run_cli('update', '--migrate', '--add-deliverable', 'slides')[0], 0)
        backups = list((self.root / '.research-briefing/migrations').glob('*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding='utf-8')), config)
        self.assertEqual(self.read_config()['brief']['audiences']['report'], '跨领域专家')

    def test_types_states_paths_and_extensions_are_checked(self):
        self.init()
        valid = self.read_config()
        for field, value in [('duration_minutes', True), ('duration_minutes', {'min': 90, 'max': 45}), ('focus', '错误类型')]:
            config = json.loads(json.dumps(valid))
            config['brief'][field] = value
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 2)
        config = json.loads(json.dumps(valid))
        config['delivery']['current_stage'] = 'invented'
        self.save_config(config)
        self.assertEqual(self.run_cli('validate-config')[0], 2)
        for path in ('../outside.md', str(self.root / 'absolute.md'), 'bad.pptx'):
            config = json.loads(json.dumps(valid))
            config['delivery']['expected_artifacts'] = [self.artifact(path)]
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 2)

    def test_duration_requires_finite_positive_numbers(self):
        self.init()
        config = self.read_config()
        for value in (float('inf'), float('-inf'), float('nan'),
                      {'min': 45, 'max': float('inf')},
                      {'min': float('nan'), 'max': 90}):
            with self.subTest(value=value):
                config['brief']['duration_minutes'] = value
                with self.assertRaises(helper.MemoryError):
                    helper.validate_config(self.root, config)
        for value in (45, 75.5, {'min': 45, 'max': 90.5}, None):
            config['brief']['duration_minutes'] = value
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 0)

    def test_json_rejects_non_standard_constants_and_overflow_without_writes(self):
        self.init()
        original = self.cfg.read_text(encoding='utf-8')
        for token in ('NaN', 'Infinity', '-Infinity', '1e309', '-1e309'):
            for field in ('duration', 'extension'):
                with self.subTest(token=token, field=field):
                    if field == 'duration':
                        payload = original.replace('"duration_minutes": null', '"duration_minutes": ' + token)
                    else:
                        payload = original.replace('"extensions": {}', '"extensions": {"metric": ' + token + '}')
                    self.cfg.write_text(payload, encoding='utf-8')
                    before = self.all_files()
                    self.assertEqual(self.run_cli('validate-config')[0], 2)
                    self.assertEqual(self.run_cli('update', '--stage', 'authoring')[0], 2)
                    self.assertEqual(self.all_files(), before)

    def test_skill_origin_version_does_not_determine_schema_compatibility(self):
        self.init()
        config = self.read_config()
        for version in ('1.0.0', '1.1.1', '2.0.0-research.1+build.7'):
            config['skill_version'] = version
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 0)
        self.assertEqual(self.run_cli('update', '--stage', 'authoring')[0], 0)
        self.assertEqual(self.read_config()['skill_version'], '2.0.0-research.1+build.7')
        for version in ('v1.1.0', '01.1.0', '1.1', '1.1.0-01'):
            config['skill_version'] = version
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 2)

    def test_cutoff_date_requires_calendar_yyyy_mm_dd_across_python_versions(self):
        self.init()
        config = self.read_config()
        for value in ('2026-10-16', '2024-02-29', None):
            config['research']['cutoff_date'] = value
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 0)
        for value in ('20261016', '2026-W42-5', '2026-2-01', '2026-02-29', '２０２６-１０-１６', 20261016):
            config['research']['cutoff_date'] = value
            self.save_config(config)
            self.assertEqual(self.run_cli('validate-config')[0], 2)

    def test_controlled_domain_extensions_remain_optional_and_object_shaped(self):
        self.init()
        config = self.read_config()
        self.assertEqual(config['extensions'], {})
        config.pop('extensions')
        self.save_config(config)
        self.assertEqual(self.run_cli('validate-config')[0], 0)
        config['extensions'] = {'domain': {'software': ['compiler', 'runtime']}, 'benchmark_setting': 4}
        self.save_config(config)
        self.assertEqual(self.run_cli('validate-config')[0], 0)
        self.run_cli('update', '--add-deliverable', 'slides')
        self.assertEqual(self.read_config()['extensions'], config['extensions'])
        config['extensions'] = ['wrong-shape']
        self.save_config(config)
        self.assertEqual(self.run_cli('validate-config')[0], 2)
        config.pop('extensions')
        config['unrecognized_core_field'] = True
        self.save_config(config)
        self.assertEqual(self.run_cli('validate-config')[0], 2)

    def test_planned_visual_reference_is_reported_but_active_missing_record_fails(self):
        self.init()
        config = self.read_config()
        config['presentation']['timing_plan'] = '研究辅助文档/讲述时间.json'
        config['brief']['duration_minutes'] = {'min': 45, 'max': 90}
        self.save_config(config)
        rc, result = self.run_cli('validate-config')
        self.assertEqual(rc, 0)
        self.assertEqual(result['planned_references'], ['研究辅助文档/讲述时间.json'])
        (self.root / config['memory_documents']['quality']).unlink()
        self.assertEqual(self.run_cli('validate-config')[0], 2)

    def test_frozen_acceptance_identity_survives_later_scope_change_and_project_copy(self):
        self.init()
        (self.root / '报告.md').write_text('内容', encoding='utf-8')
        self.expect(self.artifact())
        self.run_cli('snapshot', '--label', 'v1', '--expected')
        self.run_cli('update', '--add-deliverable', 'slides')
        other = self.root.parent / '复制项目'
        shutil.copytree(self.root, other)
        rc, result = self.run_cli('verify', '--manifest', '.research-briefing/snapshots/v1.json', root=other)
        self.assertEqual(rc, 0)
        self.assertEqual(result['config_status'], 'changed')

    def test_legacy_manifest_and_normalized_duplicate_inputs_remain_supported(self):
        path = self.root / '报告.md'
        path.write_text('内容', encoding='utf-8')
        self.run_cli('snapshot', '--label', 'v1', '--file', path.name, '--file', str(path))
        manifest = self.root / '.research-briefing/snapshots/v1.json'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['schema_version'] = helper.LEGACY
        manifest.write_text(json.dumps(data), encoding='utf-8')
        rc, result = self.run_cli('verify', '--manifest', str(manifest))
        self.assertEqual(rc, 0)
        self.assertEqual(result['checked'], 1)

    def test_outside_and_invalid_manifest_paths_do_not_write_files(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('原始资料', encoding='utf-8')
        self.assertEqual(self.run_cli('snapshot', '--label', 'v1', '--file', '../outside.md')[0], 2)
        manifest = self.root / 'bad.json'
        manifest.write_text(json.dumps({'schema_version': helper.SCHEMA, 'files':
                            [{'path': '../outside.md', 'bytes': 0, 'sha256': '0' * 64}]}), encoding='utf-8')
        self.assertEqual(self.run_cli('verify', '--manifest', str(manifest))[0], 2)
        self.assertFalse((self.root / '.research-briefing/snapshots/v1.json').exists())
        self.assertEqual(outside.read_text(encoding='utf-8'), '原始资料')

    def test_failed_initialization_rolls_back_new_files(self):
        actual = helper.write_new
        calls = []

        def interrupted(path, content):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('simulated full disk')
            return actual(path, content)

        args = argparse.Namespace(root=str(self.root), topic='测试', deliverable=['report'],
                                  memory_profile='compact', language='zh-CN')
        with patch.object(helper, 'write_new', side_effect=interrupted):
            with self.assertRaises(OSError):
                helper.initialize(args)
        self.assertFalse(self.all_files())

    def test_partial_file_write_is_cleaned_up(self):
        path = self.root / 'partial.md'
        actual_open = Path.open

        class FailingStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, text):
                self.stream.write(text[:3])
                raise OSError('simulated interrupted write')

        def failing_open(target, *args, **kwargs):
            return FailingStream(actual_open(target, *args, **kwargs))

        with patch.object(Path, 'open', failing_open):
            with self.assertRaises(OSError):
                helper.write_new(path, 'important content')
        self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
