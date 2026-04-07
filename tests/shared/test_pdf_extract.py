from __future__ import annotations

import logging
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from shared.pdf_extract import _extract_with_pypdf, extract_pdf_text


class PdfExtractTests(unittest.TestCase):
    def test_missing_pdf_reports_missing_file(self) -> None:
        result = extract_pdf_text(Path("/does/not/exist.pdf"))
        self.assertEqual(result.status, "missing_file")
        self.assertFalse(result.ok)

    def test_no_backend_reports_backend_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n%EOF\n")
            result = extract_pdf_text(path)
            self.assertEqual(result.status, "backend_unavailable")
            self.assertEqual(result.text, "")

    def test_pypdf_extraction_restores_logger_level(self) -> None:
        class FakePage:
            def extract_text(self) -> str:
                return "hello"

        class FakeReader:
            def __init__(self, _: str) -> None:
                self.pages = [FakePage()]

        fake_module = types.SimpleNamespace(PdfReader=FakeReader)
        logger = logging.getLogger("pypdf")
        original_level = logger.level
        logger.setLevel(logging.WARNING)

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir) / "sample.pdf"
                path.write_bytes(b"%PDF-1.4\n%EOF\n")
                with patch.dict(sys.modules, {"pypdf": fake_module}):
                    result = _extract_with_pypdf(path)
            self.assertIsNotNone(result)
            self.assertEqual(result.backend, "pypdf")
            self.assertEqual(result.text, "hello")
            self.assertEqual(logger.level, logging.WARNING)
        finally:
            logger.setLevel(original_level)


if __name__ == "__main__":
    unittest.main()
