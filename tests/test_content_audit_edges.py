"""Content-contract edge cases using fictional local fixtures only.

Run: python -B tests/test_content_audit_edges.py
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


class ContentAuditEdges(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='content-audit-edges-')
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def ledger(self):
        return {
            'schema_version': 'research-briefing-content/1', 'topic': '虚构边界测试',
            'sources': [{'id': 'S1', 'title': '测试输入', 'kind': 'user-note',
                         'origin': 'user', 'uri': 'inputs.txt', 'read_scope': 'full'}],
            'facts': [{'id': 'F1', 'statement': '测试计数为2', 'type': 'observation',
                       'state': 'supported', 'input_fact_ids': [], 'source_refs': [
                           {'source_id': 'S1', 'locator': '第一行', 'support': '测试计数',
                            'relation': 'supports'}]}],
            'assets': [],
            'sections': [{'id': 'C1', 'deliverable': 'report', 'heading': '测试记录',
                          'body': '计数为2。', 'fact_ids': ['F1'], 'asset_ids': [],
                          'depends_on': [], 'evidence_exceptions': []}],
        }

    def asset(self, identity='A1'):
        path = self.root / (identity + '.svg')
        path.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><text>2</text></svg>')
        return {'id': identity, 'kind': 'data-chart', 'local_path': path.name,
                'caption': '虚构测试图', 'source_refs': [], 'fact_ids': ['F1'],
                'truth_role': 'evidence', 'review_status': 'reviewed',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def deck(self):
        return {'schema_version': 'research-briefing-deck/1', 'source_ledger': 'content.json',
                'mode': 'hybrid', 'canvas': {'width_pt': 960, 'height_pt': 540},
                'pages': [{'id': 'P1', 'role': 'core', 'archetype': 'text', 'title': '测试',
                           'takeaway': '理解测试输入', 'fact_ids': ['F1'], 'asset_ids': [],
                           'blocks': [{'id': 'B1', 'kind': 'text', 'content': '计数为2。',
                                       'fact_ids': ['F1'], 'asset_ids': [],
                                       'target_editability': 'native-text'}],
                           'reading_path': ['B1'], 'speaker_notes': '这里的测试计数为2。',
                           'author_explainer_refs': [], 'density': {}, 'evidence_exceptions': []}],
                'engine_map': []}

    def audit(self, ledger, deck=None, stage='final', check_files=True):
        args = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/audit_content.py'),
                '--root', str(self.root), '--ledger', 'content.json', '--stage', stage]
        (self.root / 'content.json').write_text(json.dumps(ledger, ensure_ascii=False), encoding='utf-8')
        if deck is not None:
            (self.root / 'deck.json').write_text(json.dumps(deck, ensure_ascii=False), encoding='utf-8')
            args.extend(['--deck', 'deck.json'])
        if check_files:
            args.append('--check-files')
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        process = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertNotIn('Traceback', process.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        return process.returncode, json.loads(process.stdout)

    def codes(self, result, bucket='errors'):
        return {finding['code'] for finding in result[bucket]}

    def test_matching_optional_asset_fingerprint_passes(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        ledger['sections'][0]['asset_ids'] = ['A1']
        self.assertEqual(self.audit(ledger)[0], 0)

    def test_changed_used_asset_blocks_final_but_only_warns_in_draft(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        ledger['sections'][0]['asset_ids'] = ['A1']
        path = self.root / 'A1.svg'
        path.write_bytes(path.read_bytes().replace(b'>2<', b'>9<'))
        for stage, expected, bucket in (('draft', 0, 'warnings'), ('final', 1, 'errors')):
            with self.subTest(stage=stage):
                code, result = self.audit(ledger, stage=stage)
                self.assertEqual(code, expected)
                self.assertIn('asset_hash_mismatch', self.codes(result, bucket))

    def test_unused_changed_asset_is_a_warning(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        (self.root / 'A1.svg').write_bytes(b'changed fixture')
        code, result = self.audit(ledger)
        self.assertEqual(code, 0)
        self.assertIn('asset_hash_mismatch', self.codes(result, 'warnings'))

    def test_asset_hash_is_optional_and_file_checks_are_opt_in(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        ledger['sections'][0]['asset_ids'] = ['A1']
        (self.root / 'A1.svg').write_bytes(b'changed fixture')
        code, result = self.audit(ledger, check_files=False)
        self.assertEqual(code, 0)
        self.assertNotIn('asset_hash_mismatch', self.codes(result, 'warnings'))
        ledger['assets'][0].pop('sha256')
        self.assertEqual(self.audit(ledger)[0], 0)

    def test_missing_file_does_not_become_an_input_crash_during_hashing(self):
        ledger = self.ledger()
        ledger['assets'] = [self.asset()]
        ledger['sections'][0]['asset_ids'] = ['A1']
        (self.root / 'A1.svg').unlink()
        code, result = self.audit(ledger)
        self.assertEqual(code, 1)
        self.assertIn('missing_file', self.codes(result))
        self.assertNotIn('asset_hash_mismatch', self.codes(result))

    def test_indirect_changed_original_is_a_warning_for_reviewed_child(self):
        ledger = self.ledger()
        original, child = self.asset('A1'), self.asset('A2')
        child.update(derived_from=['A1'], fact_ids=[])
        ledger['assets'] = [original, child]
        ledger['sections'][0]['asset_ids'] = ['A2']
        (self.root / 'A1.svg').write_bytes(b'changed upstream fixture')
        code, result = self.audit(ledger)
        self.assertEqual(code, 0)
        self.assertIn('asset_hash_mismatch', self.codes(result, 'warnings'))

    def test_transitive_asset_facts_keep_unverified_conditions_visible(self):
        ledger = self.ledger()
        ledger['facts'][0].update(state='unverified', source_refs=[])
        original, child = self.asset('A1'), self.asset('A2')
        child.update(derived_from=['A1'], fact_ids=[])
        ledger['assets'] = [original, child]
        section = ledger['sections'][0]
        section.update(fact_ids=[], asset_ids=['A2'])
        code, result = self.audit(ledger)
        self.assertEqual(code, 1)
        self.assertIn('missing_or_wrong_treatment', self.codes(result))
        section['body'] += '测试计数待核。'
        section['evidence_exceptions'] = [
            {'fact_id': 'F1', 'treatment': 'qualified', 'visible_note': '测试计数待核。'}]
        self.assertEqual(self.audit(ledger)[0], 0)

    def test_notes_only_qualification_does_not_count_as_visible_page_text(self):
        ledger, deck = self.ledger(), self.deck()
        ledger['sections'] = []
        ledger['facts'][0].update(state='qualified', qualification='仅用于测试')
        page = deck['pages'][0]
        page['speaker_notes'] += '仅用于测试。'
        page['evidence_exceptions'] = [
            {'fact_id': 'F1', 'treatment': 'qualified', 'visible_note': '仅用于测试。'}]
        self.assertIn('invisible_exception', self.codes(self.audit(ledger, deck)[1]))
        page['blocks'][0]['content'] += '仅用于测试。'
        self.assertEqual(self.audit(ledger, deck)[0], 0)

    def test_duplicate_ids_are_scoped_but_each_scope_remains_unique(self):
        ledger, deck = self.ledger(), self.deck()
        second_page = deepcopy(deck['pages'][0])
        second_page['id'] = 'P2'
        deck['pages'].append(second_page)
        self.assertEqual(self.audit(ledger, deck)[0], 0)
        second_page['blocks'].append(deepcopy(second_page['blocks'][0]))
        self.assertIn('duplicate_id', self.codes(self.audit(ledger, deck)[1]))
        deck = self.deck()
        ledger['facts'].append(deepcopy(ledger['facts'][0]))
        self.assertIn('duplicate_id', self.codes(self.audit(ledger, deck)[1]))

    def test_block_fact_refs_need_page_coverage_but_notes_can_use_page_only_refs(self):
        ledger, deck = self.ledger(), self.deck()
        deck['pages'][0]['blocks'][0]['fact_ids'] = []
        self.assertEqual(self.audit(ledger, deck)[0], 0)
        deck['pages'][0]['blocks'][0]['fact_ids'] = ['F1']
        deck['pages'][0]['fact_ids'] = []
        self.assertIn('page_coverage', self.codes(self.audit(ledger, deck)[1]))

    def test_reference_cycles_are_reported_without_hanging(self):
        for family in ('sources', 'facts', 'assets', 'sections'):
            with self.subTest(family=family):
                ledger = self.ledger()
                if family == 'sources':
                    ledger['sources'][0]['parent_source_id'] = 'S1'
                elif family == 'facts':
                    ledger['facts'][0]['input_fact_ids'] = ['F1']
                elif family == 'assets':
                    ledger['assets'] = [self.asset()]
                    ledger['assets'][0]['derived_from'] = ['A1']
                else:
                    ledger['sections'][0]['depends_on'] = ['C1']
                code, result = self.audit(ledger, stage='draft')
                self.assertEqual(code, 1)
                self.assertIn('dependency_cycle', self.codes(result))

    def qualified_page(self, content):
        ledger, deck = self.ledger(), self.deck()
        ledger['sections'] = []
        ledger['facts'][0].update(state='qualified', qualification='仅用于测试')
        page = deck['pages'][0]
        page['blocks'][0]['content'] = content
        page['evidence_exceptions'] = [
            {'fact_id': 'F1', 'treatment': 'qualified', 'visible_note': '本数据仅用于测试。'}]
        return ledger, deck

    def mapping(self, page='P1', slide=1, output='deck.pptx'):
        return {'page_id': page, 'backend': 'test-fixture', 'backend_version': None,
                'output_path': output, 'slide_number': slide,
                'object_ids': {'B1': ['shape-1']}}

    def test_partial_object_mapping_identifies_unmapped_blocks(self):
        ledger, deck = self.ledger(), self.deck()
        page = deck['pages'][0]
        block = deepcopy(page['blocks'][0])
        block['id'] = 'B2'
        page['blocks'].append(block)
        page['reading_path'].append('B2')
        row = self.mapping()
        deck['engine_map'] = [row]
        for mapping in ({'B1': ['shape-1']}, {'B1': ['shape-1'], 'B2': []}):
            with self.subTest(mapping=mapping):
                row['object_ids'] = mapping
                code, result = self.audit(ledger, deck, check_files=False)
                self.assertEqual(code, 0)
                findings = [x for x in result['warnings'] if x['code'] == 'unmapped_block']
                self.assertEqual(len(findings), 1)
                self.assertIn('B2', findings[0]['message'])
        # One output object may deliberately combine several content blocks.
        row['object_ids'] = {'B1': ['shape-1'], 'B2': ['shape-1']}
        self.assertNotIn('unmapped_block', self.codes(
            self.audit(ledger, deck, check_files=False)[1], 'warnings'))

    def test_incomplete_draft_mapping_remains_allowed(self):
        ledger, deck = self.ledger(), self.deck()
        second = deepcopy(deck['pages'][0]['blocks'][0])
        second['id'] = 'B2'
        deck['pages'][0]['blocks'].append(second)
        deck['engine_map'] = [self.mapping()]
        code, result = self.audit(ledger, deck, stage='draft', check_files=False)
        self.assertEqual(code, 0)
        self.assertNotIn('unmapped_block', self.codes(result, 'warnings'))

    def test_output_order_is_compared_to_plan_not_mapping_row_order(self):
        ledger, deck = self.ledger(), self.deck()
        second = deepcopy(deck['pages'][0])
        second['id'] = 'P2'
        deck['pages'].append(second)
        deck['engine_map'] = [self.mapping('P2', 1), self.mapping('P1', 2)]
        code, result = self.audit(ledger, deck, check_files=False)
        self.assertEqual(code, 0)
        self.assertIn('page_order_mismatch', self.codes(result, 'warnings'))
        # The mapping rows themselves need not be sorted.
        deck['engine_map'] = [self.mapping('P2', 2), self.mapping('P1', 1)]
        self.assertNotIn('page_order_mismatch', self.codes(
            self.audit(ledger, deck, check_files=False)[1], 'warnings'))

    def test_order_check_keeps_separate_outputs_and_subset_exports_independent(self):
        ledger, deck = self.ledger(), self.deck()
        for pid in ('P2', 'P3'):
            page = deepcopy(deck['pages'][0])
            page['id'] = pid
            deck['pages'].append(page)
        deck['engine_map'] = [self.mapping('P3', 9, 'main.pptx'),
                              self.mapping('P2', 1, 'other.pptx'),
                              self.mapping('P1', 7, 'main.pptx')]
        code, result = self.audit(ledger, deck, check_files=False)
        self.assertEqual(code, 0)
        self.assertNotIn('page_order_mismatch', self.codes(result, 'warnings'))
        self.assertNotIn('repeated_page_mapping', self.codes(result, 'warnings'))

    def test_same_page_mapped_twice_in_one_output_is_explicitly_flagged(self):
        ledger, deck = self.ledger(), self.deck()
        deck['engine_map'] = [self.mapping('P1', 1), self.mapping('P1', 2)]
        code, result = self.audit(ledger, deck, check_files=False)
        self.assertEqual(code, 0)
        self.assertIn('repeated_page_mapping', self.codes(result, 'warnings'))
        deck['engine_map'][1]['output_path'] = 'other.pptx'
        self.assertNotIn('repeated_page_mapping', self.codes(
            self.audit(ledger, deck, check_files=False)[1], 'warnings'))

    def test_visible_qualifier_can_span_adjacent_styled_text_runs(self):
        ledger, deck = self.qualified_page({'runs': [
            {'text': '本数据', 'bold': True},
            {'text': '仅用于测试。', 'style': {'color': '#2463A2'}}]})
        self.assertEqual(self.audit(ledger, deck)[0], 0)

    def test_rich_text_does_not_join_separate_paragraphs_cells_nodes_or_blocks(self):
        parts = [{'runs': [{'text': '本数据'}]}, {'runs': [{'text': '仅用于测试。'}]}]
        for name in ('paragraphs', 'cells', 'nodes', 'blocks'):
            with self.subTest(boundary=name):
                ledger, deck = self.qualified_page({name: deepcopy(parts)})
                if name == 'blocks':
                    first = deck['pages'][0]['blocks'][0]
                    first['content'] = parts[0]
                    second = deepcopy(first)
                    second.update(id='B2', content=parts[1])
                    deck['pages'][0]['blocks'].append(second)
                    deck['pages'][0]['reading_path'].append('B2')
                code, result = self.audit(ledger, deck)
                self.assertEqual(code, 1)
                self.assertIn('invisible_exception', self.codes(result))

    def test_rich_text_styles_and_notes_are_not_visible_qualification(self):
        note = '本数据仅用于测试。'
        for field in ('style', 'styles', 'format', 'formatting', 'metadata', 'notes', 'speaker_notes'):
            for location in ('run', 'paragraph', 'nontext-run'):
                with self.subTest(field=field, location=location):
                    content = {'runs': [{'text': '计数为2。'}]}
                    if location == 'run':
                        content['runs'][0][field] = {'label': note}
                    elif location == 'paragraph':
                        content[field] = {'label': note}
                    else:
                        content['runs'].append({field: {'label': note}})
                    ledger, deck = self.qualified_page(content)
                    deck['pages'][0]['speaker_notes'] = note
                    code, result = self.audit(ledger, deck)
                    self.assertEqual(code, 1)
                    self.assertIn('invisible_exception', self.codes(result))

    def test_nontext_run_and_explicit_break_keep_text_boundaries(self):
        for separator in ({'break': True}, {'type': 'line-break'}, {'caption': '独立说明'}):
            with self.subTest(separator=separator):
                ledger, deck = self.qualified_page({'runs': [
                    {'text': '本数据'}, separator, {'text': '仅用于测试。'}]})
                code, result = self.audit(ledger, deck)
                self.assertEqual(code, 1)
                self.assertIn('invisible_exception', self.codes(result))

    def test_explicit_newline_in_a_text_run_is_preserved(self):
        for newline in ('\n', '\r\n', '\v'):
            with self.subTest(newline=newline):
                ledger, deck = self.qualified_page({'runs': [
                    {'text': '本数据' + newline}, {'text': '仅用于测试。'}]})
                code, result = self.audit(ledger, deck)
                self.assertEqual(code, 1)
                self.assertIn('invisible_exception', self.codes(result))
                deck['pages'][0]['evidence_exceptions'][0]['visible_note'] = '本数据' + newline + '仅用于测试。'
                self.assertEqual(self.audit(ledger, deck)[0], 0)

    def test_rich_text_keeps_sibling_and_unknown_body_fragments(self):
        note = '本数据仅用于测试。'
        cases = [
            {'runs': [{'text': '计数为2。'}], 'caption': note},
            {'runs': [{'text': '计数为2。'}], 'paragraphs': [{'text': note}]},
            {'runs': [{'text': '计数为2。'}, {'caption': note}]},
            {'paragraphs': [{'text': note}]},
        ]
        for content in cases:
            with self.subTest(content=content):
                ledger, deck = self.qualified_page(content)
                self.assertEqual(self.audit(ledger, deck)[0], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
