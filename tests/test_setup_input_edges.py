"""Setup input regressions using synthetic packages; no host installation."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/setup_skill.py'
SPEC = importlib.util.spec_from_file_location('setup_input_edges', SCRIPT)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


def nested_json(depth, kind='array', leaf='0'):
    for level in range(depth):
        leaf = ('{"x":' + leaf + '}' if kind == 'object' or
                (kind == 'mixed' and level % 2) else '[' + leaf + ']')
    return leaf


class SetupInputEdges(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='setup-input-edges-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / setup.NAME
        self.source.mkdir()
        self.front = '---\nname: ' + setup.NAME + '\ndescription: Fixture\n---\n'
        self.entry = self.source / 'SKILL.md'
        self.entry.write_text(self.front, encoding='utf-8')
        for relative in setup.REQUIRED_RESOURCES:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}' if path.suffix == '.json' else '# fixture\n', encoding='utf-8')
        self.target = self.root / 'absent-skills'
        source_patch = patch.object(setup, 'SOURCE', self.source)
        source_patch.start()
        self.addCleanup(source_patch.stop)

    def put_json(self, raw):
        (self.source / 'edge.json').write_text(raw, encoding='utf-8')

    def check_cli(self):
        # A real UTF-8 stream catches surrogates that StringIO would silently accept.
        buffer = io.BytesIO()
        output = io.TextIOWrapper(buffer, encoding='utf-8', errors='strict')
        errors = io.StringIO()
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = setup.main(['check', '--skills-dir', str(self.target)])
            output.flush()
            text = buffer.getvalue().decode('utf-8')
        finally:
            output.close()
        self.assertEqual(errors.getvalue(), '')
        self.assertNotIn('Traceback', text)
        self.assertFalse(self.target.exists(), 'check must remain read-only')
        return code, json.loads(text)

    def assert_json_problem(self, raw, message):
        self.put_json(raw)
        before = setup.inventory(self.source)
        manifest, problems = setup.package_check()
        self.assertEqual(manifest, before)
        self.assertTrue(problems, 'invalid JSON was accepted')
        self.assertIn('edge.json', problems[0])
        self.assertIn(message.lower(), problems[0].lower())
        code, result = self.check_cli()
        self.assertEqual((code, result['status']), (1, 'problem'))
        self.assertEqual(result['package_problems'], problems)
        self.assertEqual(setup.inventory(self.source), before)

    def test_accepts_container_depth_128_including_empty_leaf(self):
        for kind in ('array', 'object', 'mixed'):
            for leaf, wrappers in (('0', 128), ('[]', 127), ('{}', 127)):
                with self.subTest(kind=kind, leaf=leaf):
                    self.put_json(nested_json(wrappers, kind, leaf))
                    self.assertEqual(setup.package_check()[1], [])
        self.assertEqual(self.check_cli()[0], 0)

    def test_rejects_container_depth_129_including_empty_leaf(self):
        for kind in ('array', 'object', 'mixed'):
            for leaf, wrappers in (('0', 129), ('[]', 128), ('{}', 128)):
                with self.subTest(kind=kind, leaf=leaf):
                    self.assert_json_problem(nested_json(wrappers, kind, leaf), '128')

    def test_extreme_json_is_a_package_problem(self):
        self.assert_json_problem(nested_json(20000), 'JSON')

    def test_decoder_recursion_error_is_a_package_problem(self):
        self.put_json('{}')
        with patch.object(setup.json, 'loads', side_effect=RecursionError('decoder limit')):
            manifest, problems = setup.package_check()
        self.assertIsNotNone(manifest)
        self.assertTrue(problems)
        self.assertIn('Invalid JSON in ', problems[0])
        self.assertIn('decoder limit', problems[0])

    def test_rejects_lone_surrogates_in_values_and_keys(self):
        for code in ('d800', 'dbff', 'dc00', 'dfff'):
            for raw in ('"\\u' + code + '"', '{"\\u' + code + '": 0}',
                        '{"nested": ["prefix\\u' + code + 'suffix"]}'):
                with self.subTest(raw=raw):
                    self.assert_json_problem(raw, 'surrogate')

    def test_duplicate_surrogate_key_cannot_break_output_encoding(self):
        self.put_json(r'{"\ud800": 1, "\ud800": 2}')
        code, result = self.check_cli()
        self.assertEqual((code, result['status']), (1, 'problem'))

    def test_unicode_pairs_bom_and_syntax_characters_in_strings_remain_valid(self):
        for raw in ('\ufeff{"中文😀": "café é 日本語"}',
                    r'{"\ud83d\ude00": "\ud840\udc00"}',
                    json.dumps({'text': '[{"' * 200 + '\\ud800'})):
            with self.subTest(raw=raw[:60]):
                self.put_json(raw)
                self.assertEqual(self.check_cli()[0], 0)

    def test_existing_strict_json_rejections_remain_package_problems(self):
        for raw in ('{"x":1,"x":2}', '[NaN]', '[Infinity]', '[-Infinity]', '[1e9999]', '{'):
            with self.subTest(raw=raw):
                self.assert_json_problem(raw, 'JSON')

    def test_main_catches_recursion_from_command_dispatch(self):
        with patch.object(setup, 'check', side_effect=RecursionError('dispatch recursion')):
            code, result = self.check_cli()
        self.assertEqual((code, result['status']), (2, 'error'))
        self.assertIn('dispatch recursion', result['message'])

    def test_main_catches_serialization_recursion(self):
        cyclic = []
        cyclic.append(cyclic)
        with patch.object(setup, 'check', return_value=({'data': cyclic}, 0)):
            code, result = self.check_cli()
        self.assertEqual((code, result['status']), (2, 'error'))

    def test_main_can_report_surrogate_bearing_error_message(self):
        with patch.object(setup, 'check', side_effect=ValueError('bad \ud800 input')):
            code, result = self.check_cli()
        self.assertEqual((code, result['status']), (2, 'error'))
        self.assertIn('bad', result['message'])

    def test_main_preserves_normal_unicode_output(self):
        with patch.object(setup, 'check', return_value=({'status': 'ok', 'text': '中文😀'}, 0)):
            code, result = self.check_cli()
        self.assertEqual((code, result['text']), (0, '中文😀'))

    def test_inline_balanced_parentheses_and_titles(self):
        for tail in ('', ' "a title (with parentheses)"', " 'a title'", ' (a title)'):
            with self.subTest(tail=tail):
                text = '[ref](references/a(b(c)).md' + tail + ')'
                self.assertEqual(list(setup.markdown_destinations(text)), ['references/a(b(c)).md'])

    def test_inline_escaped_parentheses_and_escape_parity(self):
        examples = (
            (r'[x](references/a\(b\).md)', 'references/a(b).md'),
            (r'[x](references/a\).md)', 'references/a).md'),
            (r'[x](references/a\(.md)', 'references/a(.md'),
            (r'![x](references/a(b\)c).svg)', 'references/a(b)c).svg'),
            (r'[x](references/a\\(b).md)', 'references/a\\(b).md'),
        )
        for text, expected in examples:
            with self.subTest(text=text):
                self.assertEqual(list(setup.markdown_destinations(text)), [expected])

    def test_angle_destinations_and_reference_definitions(self):
        text = ('[angle](<references/a (b).md> "title")\n'
                '[ref][id]\n[id]: references/a(b(c)).md "title"\n'
                r'[escaped]: references/a\(b\).md' + '\n'
                '[space]: <references/a (b).md>\n')
        self.assertEqual(list(setup.markdown_destinations(text)), [
            'references/a (b).md', 'references/a(b(c)).md',
            'references/a(b).md', 'references/a (b).md'])

    def test_code_examples_remain_excluded(self):
        text = ('`[inline](missing(a).md)`\n'
                '``[wide](missing(b).md)``\n'
                '```markdown\n[fenced](missing(c).md)\n[id]: missing(d).md\n```\n'
                '~~~\n[fenced](missing(e).md)\n~~~\n'
                '    [indent](missing(f).md)\n\t[tab](missing(g).md)\n'
                '[real](references/a(b).md)\n')
        self.assertEqual(list(setup.markdown_destinations(text)), ['references/a(b).md'])

    def test_package_resolves_parentheses_relative_paths_and_encoded_destinations(self):
        reference = self.source / 'references/a(b).md'
        reference.parent.mkdir()
        reference.write_text('[back](../SKILL.md)\n', encoding='utf-8')
        self.entry.write_text(self.front + '\n'.join((
            '[bare](references/a(b).md)', r'[escaped](references/a\(b\).md)',
            '[angle](<references/a(b).md>)', '[encoded](references/a%28b%29.md#anchor)',
            '[ref][id]', r'[id]: references/a\(b\).md "title"',
            '[url](https://example.invalid/a(b))', '[anchor](#local)',
            '`[example](missing(a).md)`')), encoding='utf-8')
        self.assertEqual(setup.package_check()[1], [])
        self.assertEqual(self.check_cli()[0], 0)

    def test_missing_parenthesized_target_is_reported_in_full(self):
        self.entry.write_text(self.front + '[x](references/missing(a(b)).md)', encoding='utf-8')
        problems = setup.package_check()[1]
        self.assertEqual(problems, [
            'Missing/outside package link in SKILL.md: references/missing(a(b)).md'])

    def test_unbalanced_or_unclosed_inline_links_are_not_truncated_destinations(self):
        for text in ('[x](references/a(b.md)', '[x](references/a(b).md',
                     '[x](<references/a(b).md)', '[x](references/a(b).md "unclosed)'):
            with self.subTest(text=text):
                self.assertEqual(list(setup.markdown_destinations(text)), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
