"""Inspector XML and failed-output regression tests; no Office or network.

Run: python -X utf8 -B tests/test_inspector_edges.py
INSPECTOR_TEST_ROOT optionally selects an existing isolated scratch parent.
"""
from contextlib import redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile

sys.dont_write_bytecode = True
TESTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('inspector_edge_fixtures', TESTS / 'test_runtime_helpers.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
inspector = fixtures.inspector


class XmlDeclarationEdges(unittest.TestCase):
    def parse(self, payload):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('part.xml', payload)
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as archive:
            package = inspector.Package(archive)
            root = package.xml('part.xml')
        return root, package

    def encodings(self, body):
        for encoding in ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be'):
            declaration = 'UTF-8' if encoding == 'utf-8' else 'UTF-16'
            yield encoding, ('<?xml version="1.0" encoding="' + declaration + '"?>' + body).encode(encoding)

    def test_declaration_literals_in_cdata_comments_and_pi_are_text(self):
        cases = [
            ('<root><![CDATA[<!DOCTYPE html> <!ENTITY example "x">]]></root>',
             '<!DOCTYPE html> <!ENTITY example "x">'),
            ('<!-- <!DOCTYPE html> <!ENTITY example "x"> --><root>正文</root>', '正文'),
            ('<?example <!DOCTYPE html> <!ENTITY example "x">?><root>正文</root>', '正文'),
            ('<root>&lt;!DOCTYPE html&gt; &amp; &quot;x&quot;</root>', '<!DOCTYPE html> & "x"'),
        ]
        for body, expected in cases:
            for encoding, payload in self.encodings(body):
                with self.subTest(body=body, encoding=encoding):
                    root, package = self.parse(payload)
                    self.assertEqual(package.errors, [])
                    self.assertEqual(root.text, expected)

    def test_real_dtd_and_entity_declarations_are_rejected_in_all_encodings(self):
        cases = [
            '<!DOCTYPE root><root/>',
            '<!DOCTYPE root SYSTEM "file:///never-open"><root/>',
            '<!DOCTYPE root [<!ENTITY value "expanded">]><root>&value;</root>',
            '<!DOCTYPE root [<!ENTITY value SYSTEM "file:///never-open">]><root>&value;</root>',
            '<!DOCTYPE root [<!ENTITY % parameter "ignored">%parameter;]><root/>',
            # A declaration without a DTD is malformed XML and must also fail.
            '<!ENTITY value "expanded"><root/>',
        ]
        for body in cases:
            for encoding, payload in self.encodings(body):
                with self.subTest(body=body, encoding=encoding):
                    root, package = self.parse(payload)
                    self.assertIsNone(root)
                    self.assertEqual([e['code'] for e in package.errors], ['unreadable_xml'])
                    if body.startswith('<!DOCTYPE'):
                        self.assertIn('DOCTYPE and ENTITY declarations are rejected', package.errors[0]['detail'])

    def test_malformed_xml_and_undeclared_entities_keep_structural_errors(self):
        for payload in (b'<root>', b'<root>&missing;</root>', b'<root>\x00</root>'):
            with self.subTest(payload=payload):
                root, package = self.parse(payload)
                self.assertIsNone(root)
                self.assertEqual(package.errors[0]['code'], 'unreadable_xml')

    def test_existing_xml_byte_limits_are_still_enforced(self):
        for name in ('MAX_XML_BYTES', 'MAX_TOTAL_XML_BYTES'):
            with self.subTest(limit=name), patch.object(inspector, name, 5):
                root, package = self.parse(b'<root/>')
                self.assertIsNone(root)
                self.assertEqual(package.errors[0]['code'], 'unreadable_xml')
                self.assertIn('size limit', package.errors[0]['detail'])


class OutputFailureEdges(unittest.TestCase):
    def setUp(self):
        self.parent = Path(os.environ.get('INSPECTOR_TEST_ROOT', tempfile.gettempdir())).resolve()
        self.root = self.parent / ('inspector-edges-' + uuid.uuid4().hex)
        # Ordinary inherited permissions avoid Windows tempfile's restricted ACL.
        self.root.mkdir()
        fixture = fixtures.PptxInventoryBehavior()
        fixture.root = self.root
        self.pptx = fixture.presentation()
        self.output = self.root / 'inventory.json'

    def tearDown(self):
        resolved = self.root.resolve()
        if resolved.parent != self.parent or not resolved.name.startswith('inspector-edges-'):
            raise RuntimeError('Refusing cleanup outside the isolated test directory')
        shutil.rmtree(resolved)

    def invoke(self):
        stderr = io.StringIO()
        with patch.object(sys, 'argv', ['inspect_pptx.py', '--pptx', str(self.pptx),
                                      '--out', str(self.output)]), redirect_stderr(stderr):
            code = inspector.main()
        return code, stderr.getvalue()

    def intercept(self, phase, replace_output=False, fail_close=False):
        actual_open = Path.open
        owner = self
        opened = []

        class Stream:
            def __init__(self, stream):
                self.stream = stream
                self.triggered = False

            def __getattr__(self, key):
                return getattr(self.stream, key)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

            def write(self, text):
                if phase == 'write':
                    self.stream.write(text[:25])
                    self.stream.flush()
                    if replace_output:
                        self.stream.close()
                        replacement = owner.root / 'replacement.json'
                        replacement.write_bytes(b'other writer data')
                        os.replace(replacement, owner.output)
                    raise OSError('original write failure')
                return self.stream.write(text)

            def flush(self):
                self.stream.flush()
                if phase == 'flush' and not self.triggered:
                    self.triggered = True
                    raise OSError('original flush failure')

            def close(self):
                if not self.stream.closed:
                    try:
                        self.flush()
                    finally:
                        self.stream.close()
                if phase == 'close':
                    raise OSError('original close failure')
                if fail_close:
                    raise OSError('secondary close failure')

        def opening(target, *args, **kwargs):
            stream = actual_open(target, *args, **kwargs)
            mode = args[0] if args else kwargs.get('mode', 'r')
            if mode == 'x' and target == self.output:
                opened.append(target)
                return Stream(stream)
            return stream

        return patch.object(Path, 'open', opening), opened

    def failed_output(self, phase):
        interceptor, opened = self.intercept(phase)
        with interceptor:
            code, error = self.invoke()
        self.assertTrue(opened, 'The intended output write was not exercised')
        self.assertEqual(code, 2)
        self.assertIn('original ' + phase + ' failure', error)
        self.assertEqual(set(self.root.iterdir()), {self.pptx})
        self.assertEqual(self.invoke(), (0, ''))
        self.assertEqual(json.loads(self.output.read_bytes())['status'], 'inventory_generated')

    def test_write_failure_leaves_no_new_output_and_allows_retry(self):
        self.failed_output('write')

    def test_flush_failure_leaves_no_new_output_and_allows_retry(self):
        self.failed_output('flush')

    def test_close_failure_leaves_no_new_output_and_allows_retry(self):
        self.failed_output('close')

    def test_write_error_survives_a_secondary_close_error(self):
        interceptor, opened = self.intercept('write', fail_close=True)
        with interceptor:
            code, error = self.invoke()
        self.assertTrue(opened)
        self.assertEqual(code, 2)
        self.assertIn('original write failure', error)
        self.assertNotIn('secondary close failure', error)
        self.assertEqual(set(self.root.iterdir()), {self.pptx})

    def test_replacement_output_survives_failed_write_cleanup(self):
        interceptor, opened = self.intercept('write', replace_output=True)
        with interceptor:
            code, error = self.invoke()
        self.assertTrue(opened)
        self.assertEqual(code, 2)
        self.assertIn('original write failure', error)
        self.assertEqual(self.output.read_bytes(), b'other writer data')
        self.assertEqual(set(self.root.iterdir()), {self.pptx, self.output})

    def test_output_does_not_require_hard_links(self):
        with patch.object(os, 'link', side_effect=OSError('hard links unsupported')) as link:
            code, error = self.invoke()
        self.assertEqual((code, error), (0, ''))
        link.assert_not_called()
        self.assertEqual(json.loads(self.output.read_bytes())['status'], 'inventory_generated')
        self.assertEqual(set(self.root.iterdir()), {self.pptx, self.output})

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'original data')
        code, error = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn('already exists', error)
        self.assertEqual(self.output.read_bytes(), b'original data')

    def test_output_created_during_inspection_is_not_overwritten_or_deleted(self):
        original = inspector.inspect

        def create_output(*args, **kwargs):
            report = original(*args, **kwargs)
            self.output.write_bytes(b'other writer data')
            return report

        with patch.object(inspector, 'inspect', side_effect=create_output):
            code, error = self.invoke()
        self.assertEqual(code, 2)
        self.assertTrue(error)
        self.assertEqual(self.output.read_bytes(), b'other writer data')
        self.assertEqual(set(self.root.iterdir()), {self.pptx, self.output})


if __name__ == '__main__':
    unittest.main(verbosity=2)
