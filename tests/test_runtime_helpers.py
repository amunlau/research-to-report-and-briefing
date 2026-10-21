"""Isolated helper behavior checks; no network, rendering or Office execution.

Run: python -B tests/test_runtime_helpers.py
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


audit_helper = module('audit_content')
inspector = module('inspect_pptx')
installer = module('setup_skill')


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-runtime-')
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, data):
        target = self.root / name
        target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return target

    def cli(self, script, *args):
        return subprocess.run([sys.executable, '-B', '-X', 'utf8',
                               str(ROOT / 'scripts' / script), *map(str, args)],
                              capture_output=True, text=True, encoding='utf-8')


class ContentAuditBehavior(Workspace):
    def ledger(self):
        return {
            'schema_version': 'research-briefing-content/1', 'topic': '夹具：测试材料',
            'sources': [{'id': 'S1', 'title': '本地测试记录', 'kind': 'user-note',
                         'origin': 'user', 'uri': 'inputs/test.txt', 'read_scope': 'full'}],
            'facts': [{'id': 'F1', 'statement': '夹具计数为2', 'type': 'observation',
                       'state': 'supported', 'input_fact_ids': [], 'source_refs': [
                           {'source_id': 'S1', 'locator': '第一行', 'support': '记录计数',
                            'relation': 'supports'}]}],
            'assets': [],
            'sections': [{'id': 'C1', 'deliverable': 'report', 'heading': '计数记录',
                          'body': '测试记录中的计数为2。', 'fact_ids': ['F1'],
                          'asset_ids': [], 'depends_on': [], 'evidence_exceptions': []}],
        }

    def asset(self, identity='A1', role='evidence'):
        name = identity + '.svg'
        (self.root / name).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
        return {'id': identity, 'kind': 'original-figure', 'local_path': name,
                'caption': '隔离测试图', 'source_refs': [], 'fact_ids': [],
                'truth_role': role, 'review_status': 'reviewed'}

    def deck(self):
        return {'schema_version': 'research-briefing-deck/1', 'source_ledger': 'content.json',
                'mode': 'hybrid', 'canvas': {'width_pt': 960, 'height_pt': 540},
                'pages': [{'id': 'P1', 'role': 'core', 'archetype': 'text', 'title': '计数',
                           'takeaway': '了解测试计数', 'fact_ids': ['F1'], 'asset_ids': [],
                           'blocks': [{'id': 'B1', 'kind': 'text', 'content': '计数为2。',
                                       'fact_ids': ['F1'], 'asset_ids': [],
                                       'target_editability': 'native-text'}],
                           'reading_path': ['B1'], 'speaker_notes': '记录中的计数为2。',
                           'author_explainer_refs': [], 'density': {}, 'evidence_exceptions': []}],
                'engine_map': []}

    def audit(self, ledger, deck=None, stage='final'):
        self.write_json('content.json', ledger)
        args = ['--root', self.root, '--ledger', 'content.json', '--stage', stage, '--check-files']
        if deck is not None:
            self.write_json('deck.json', deck)
            args.extend(['--deck', 'deck.json'])
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        process = self.cli('audit_content.py', *args)
        self.assertNotIn('Traceback', process.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        return process.returncode, json.loads(process.stdout)

    def test_report_only_needs_no_deck_and_returns_exact_ledger_hash(self):
        rc, result = self.audit(self.ledger())
        self.assertEqual(rc, 0)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['sourcehash'], {'ledger': hashlib.sha256(
            (self.root / 'content.json').read_bytes()).hexdigest()})

    def test_used_evidence_asset_requires_traceable_basis_at_final_stage(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        ledger['sections'][0]['asset_ids'] = ['A1']
        for stage, code, bucket in (('draft', 0, 'warnings'), ('final', 1, 'errors')):
            with self.subTest(stage=stage):
                rc, result = self.audit(ledger, stage=stage)
                self.assertEqual(rc, code)
                self.assertIn('untraceable_evidence_asset', {f['code'] for f in result[bucket]})

    def test_derived_evidence_can_inherit_supported_provenance(self):
        ledger = self.ledger()
        original, crop = self.asset('A1'), self.asset('A2')
        original['source_refs'] = deepcopy(ledger['facts'][0]['source_refs'])
        crop['derived_from'] = ['A1']
        ledger['assets'] = [original, crop]
        ledger['sections'][0]['asset_ids'] = ['A2']
        self.assertEqual(self.audit(ledger)[0], 0)
        original['source_refs'] = []
        original['fact_ids'] = ['F1']
        self.assertEqual(self.audit(ledger)[0], 0)

    def test_unused_evidence_gap_and_explanatory_or_decorative_assets_do_not_block(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        rc, result = self.audit(ledger)
        self.assertEqual(rc, 0)
        self.assertIn('untraceable_evidence_asset', {f['code'] for f in result['warnings']})
        ledger['sections'][0]['asset_ids'] = ['A1']
        for role in ('explanation', 'decorative'):
            ledger['assets'][0]['truth_role'] = role
            self.assertEqual(self.audit(ledger)[0], 0)

    def test_missing_used_asset_file_is_reported(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset(role='explanation')]
        ledger['sections'][0]['asset_ids'] = ['A1']
        (self.root / 'A1.svg').unlink()
        rc, result = self.audit(ledger)
        self.assertEqual(rc, 1)
        self.assertIn('missing_file', {f['code'] for f in result['errors']})

    def test_unread_support_and_broken_references_block_used_final_content(self):
        ledger = self.ledger()
        ledger['sources'][0]['read_scope'] = 'unread'
        rc, result = self.audit(ledger)
        self.assertEqual(rc, 1)
        self.assertIn('unread_support', {f['code'] for f in result['errors']})
        ledger['sources'] = []
        self.assertIn('broken_reference', {f['code'] for f in self.audit(ledger)[1]['errors']})

    def test_transitive_assumptions_need_visible_qualified_treatment(self):
        ledger = self.ledger()
        assumption = deepcopy(ledger['facts'][0])
        assumption.update(id='F2', type='assumption', source_refs=[], state='unverified')
        ledger['facts'].append(assumption)
        ledger['facts'][0].update(type='interpretation', reasoning='在假设条件下解释', input_fact_ids=['F2'])
        rc, result = self.audit(ledger)
        self.assertEqual(rc, 1)
        self.assertIn('missing_or_wrong_treatment', {f['code'] for f in result['errors']})
        ledger['sections'][0]['body'] += '本节为假设情景。'
        ledger['sections'][0]['evidence_exceptions'] = [
            {'fact_id': 'F2', 'treatment': 'hypothetical', 'visible_note': '本节为假设情景。'}]
        self.assertEqual(self.audit(ledger)[0], 0)

    def test_deck_notes_default_on_but_user_can_disable_them(self):
        deck = self.deck()
        deck['pages'][0]['speaker_notes'] = ''
        self.assertEqual(self.audit(self.ledger(), deck, 'draft')[0], 0)
        rc, result = self.audit(self.ledger(), deck)
        self.assertEqual(rc, 1)
        self.assertIn('missing_speaker_notes', {f['code'] for f in result['errors']})
        deck['notes_enabled'] = False
        self.assertEqual(self.audit(self.ledger(), deck)[0], 0)

    def test_unknown_fields_and_cell_fact_coverage_are_checked(self):
        ledger, deck = self.ledger(), self.deck()
        deck['pages'][0]['unexpected'] = True
        self.assertIn('structure', {f['code'] for f in self.audit(ledger, deck)[1]['errors']})
        deck['pages'][0].pop('unexpected')
        block = deck['pages'][0]['blocks'][0]
        block.update(content={'value': 2, 'fact_id': 'F1'}, fact_ids=[])
        self.assertIn('cell_fact_coverage', {f['code'] for f in self.audit(ledger, deck)[1]['errors']})


class PptxInventoryBehavior(Workspace):
    def presentation(self, missing_slide=False, doctype=False):
        ns = 'http://schemas.openxmlformats.org'
        presentation_ns = ns + '/presentationml/2006/main'
        drawing_ns = ns + '/drawingml/2006/main'
        office = ns + '/officeDocument/2006/relationships'
        package = ns + '/package/2006/relationships'
        members = {
            '_rels/.rels': f'<Relationships xmlns="{package}"><Relationship Id="r1" Type="{office}/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
            'ppt/presentation.xml': f'<p:presentation xmlns:p="{presentation_ns}" xmlns:r="{office}"><p:sldIdLst><p:sldId id="256" r:id="s1"/></p:sldIdLst><p:sldSz cx="9144000" cy="5143500"/></p:presentation>',
            'ppt/_rels/presentation.xml.rels': f'<Relationships xmlns="{package}"><Relationship Id="s1" Type="{office}/slide" Target="slides/slide1.xml"/></Relationships>',
            'ppt/slides/slide1.xml': f'<p:sld xmlns:p="{presentation_ns}" xmlns:a="{drawing_ns}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000000" cy="1000000"/></a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>第一行</a:t></a:r><a:br/><a:r><a:t>第二行</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>',
            'ppt/slides/_rels/slide1.xml.rels': f'<Relationships xmlns="{package}"><Relationship Id="n1" Type="{office}/notesSlide" Target="../notesSlides/notesSlide1.xml"/><Relationship Id="h1" Type="{office}/hyperlink" Target="https://example.invalid/never-open" TargetMode="External"/></Relationships>',
            'ppt/notesSlides/notesSlide1.xml': f'<p:notes xmlns:p="{presentation_ns}" xmlns:a="{drawing_ns}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>可照读的测试备注。</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>999</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>',
        }
        if missing_slide:
            members.pop('ppt/slides/slide1.xml')
        if doctype:
            members['ppt/slides/slide1.xml'] = '<!DOCTYPE sld []>' + members['ppt/slides/slide1.xml']
        target = self.root / 'fixture.pptx'
        with zipfile.ZipFile(target, 'w') as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        return target

    def test_text_notes_explicit_breaks_and_identity_without_rendering(self):
        path = self.presentation()
        before = path.read_bytes()
        report, code = inspector.inspect(path, include_text=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['slide_count'], 1)
        self.assertEqual(report['input']['sha256'], hashlib.sha256(before).hexdigest())
        slide = report['slides'][0]
        self.assertEqual(slide['native_text']['text'], '第一行\n第二行')
        self.assertEqual(slide['native_text']['characters'], 6)
        self.assertEqual(slide['notes']['text'], '可照读的测试备注。')
        self.assertEqual(slide['external_relationships_not_followed'], 1)
        self.assertEqual(before, path.read_bytes())

    def test_missing_slide_and_xml_doctype_are_structural_errors(self):
        for options, expected in (({'missing_slide': True}, 'missing_relationship_target'),
                                  ({'doctype': True}, 'unreadable_xml')):
            with self.subTest(options=options):
                report, code = inspector.inspect(self.presentation(**options))
                self.assertEqual(code, 1)
                self.assertIn(expected, {f['code'] for f in report['errors']})

    def test_inventory_refuses_to_overwrite_existing_output(self):
        path = self.presentation()
        output = self.root / 'inventory.json'
        output.write_bytes(b'preserved')
        process = self.cli('inspect_pptx.py', '--pptx', path, '--out', output)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(output.read_bytes(), b'preserved')


class InstallationBehavior(Workspace):
    def test_package_checks_and_install_preserve_existing_different_content(self):
        manifest, problems = installer.package_check()
        self.assertEqual(problems, [])
        args = argparse.Namespace(command='install', skills_dir=str(self.root / 'skills'),
                                  host=None, scope=None, project=None)
        result, code = installer.install(args)
        self.assertEqual((result['status'], code), ('installed', 0))
        target = Path(result['path'])
        self.assertEqual(installer.inventory(target), manifest)
        self.assertEqual(installer.install(args)[0]['status'], 'unchanged')
        existing = target / 'SKILL.md'
        existing.write_text('local change', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.install(args)
        self.assertEqual(existing.read_text(encoding='utf-8'), 'local change')

    def test_required_resources_and_relative_links_cannot_silently_disappear(self):
        entry = self.root / 'SKILL.md'
        entry.write_text('[missing](references/missing.md)', encoding='utf-8')
        with patch.object(installer, 'SOURCE', self.root), patch.object(
                installer, 'REQUIRED_RESOURCES', ('assets/required.json',)):
            problems = installer.resource_problems(installer.inventory(self.root))
        self.assertEqual(len(problems), 2)
        self.assertTrue(any('required.json' in p for p in problems))
        self.assertTrue(any('missing.md' in p for p in problems))


if __name__ == '__main__':
    unittest.main(verbosity=2)
