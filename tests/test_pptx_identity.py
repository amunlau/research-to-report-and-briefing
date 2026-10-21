"""PPTX identity checks with local OOXML fixtures; no Office or rendering."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
TESTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pptx_fixture_helpers', TESTS / 'test_runtime_helpers.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
inspector = fixtures.inspector


class PptxIdentityBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pptx-identity-')
        self.fixture = fixtures.PptxInventoryBehavior()
        self.fixture.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def replacement(self, path):
        before = path.read_bytes()
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(before)) as original, zipfile.ZipFile(output, 'w') as changed:
            for info in original.infolist():
                data = original.read(info)
                if info.filename == 'ppt/slides/slide1.xml':
                    data = data.replace('第一行'.encode('utf-8'), '修改行'.encode('utf-8'))
                changed.writestr(info, data)
        result = output.getvalue()
        self.assertNotEqual(result, before)
        self.assertEqual(len(result), len(before))
        return result

    def test_unchanged_input_hash_matches_extracted_file(self):
        path = self.fixture.presentation()
        before = path.read_bytes()
        report, code = inspector.inspect(path, include_text=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['input']['sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(report['slides'][0]['native_text']['text'], '第一行\n第二行')
        self.assertEqual(path.read_bytes(), before)

    def test_equal_size_and_mtime_replacement_is_detected(self):
        path = self.fixture.presentation()
        before = path.stat()
        replacement = self.replacement(path)
        zip_class = zipfile.ZipFile
        replaced = False

        def open_after_replace(*args, **kwargs):
            nonlocal replaced
            if not replaced:
                path.write_bytes(replacement)
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                replaced = True
            return zip_class(*args, **kwargs)

        with patch.object(inspector.zipfile, 'ZipFile', side_effect=open_after_replace):
            report, code = inspector.inspect(path, include_text=True)
        self.assertTrue(replaced)
        self.assertEqual(path.stat().st_size, before.st_size)
        self.assertEqual(path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(code, 1)
        self.assertIn('input_changed', {item['code'] for item in report['errors']})


if __name__ == '__main__':
    unittest.main(verbosity=2)
