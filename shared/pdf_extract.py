from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from shared.schemas import PdfExtractionResult


def _extract_with_pymupdf(path: Path) -> PdfExtractionResult | None:
    try:
        import fitz  # type: ignore
    except ImportError:
        return None
    try:
        document = fitz.open(path)
        try:
            text = "\n".join(page.get_text() for page in document)
        finally:
            document.close()
        return PdfExtractionResult(text=text.strip(), backend="pymupdf")
    except Exception:  # noqa: BLE001
        return None


def _extract_with_pdfplumber(path: Path) -> PdfExtractionResult | None:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return None
    try:
        with pdfplumber.open(path) as document:
            text = "\n".join((page.extract_text() or "") for page in document.pages)
        return PdfExtractionResult(text=text.strip(), backend="pdfplumber")
    except Exception:  # noqa: BLE001
        return None


def _extract_with_pypdf(path: Path) -> PdfExtractionResult | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        with _suppress_pypdf_warnings():
            reader = PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return PdfExtractionResult(text=text.strip(), backend="pypdf")
    except Exception:  # noqa: BLE001
        return None


def _extract_with_ocr(path: Path) -> PdfExtractionResult | None:
    gs_path = shutil.which("gs")
    tesseract_path = shutil.which("tesseract")
    if not gs_path or not tesseract_path:
        return None

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            image_pattern = tmp_root / "page-%03d.png"
            subprocess.run(
                [
                    gs_path,
                    "-q",
                    "-dNOPAUSE",
                    "-dBATCH",
                    "-sDEVICE=png16m",
                    "-r200",
                    f"-sOutputFile={image_pattern}",
                    str(path),
                ],
                check=True,
                capture_output=True,
            )
            page_images = sorted(tmp_root.glob("page-*.png"))
            if not page_images:
                return None

            texts: list[str] = []
            for image_path in page_images:
                completed = subprocess.run(
                    [tesseract_path, str(image_path), "stdout", "--psm", "6"],
                    check=True,
                    capture_output=True,
                )
                text = completed.stdout.decode("utf-8", errors="ignore").strip()
                if text:
                    texts.append(text)

            combined_text = "\n".join(texts).strip()
            if not combined_text:
                return None
            return PdfExtractionResult(text=combined_text, backend="ocr_tesseract")
    except Exception:  # noqa: BLE001
        return None


@contextmanager
def _suppress_pypdf_warnings():
    logger = logging.getLogger("pypdf")
    previous_level = logger.level
    logger.setLevel(max(previous_level, logging.ERROR))
    try:
        yield
    finally:
        logger.setLevel(previous_level)


def extract_text_from_pdf(path: Path) -> PdfExtractionResult:
    last_result: PdfExtractionResult | None = None
    for extractor in (_extract_with_pymupdf, _extract_with_pdfplumber, _extract_with_pypdf):
        result = extractor(path)
        if result is None:
            continue
        last_result = result
        if result.text.strip():
            return result
    ocr_result = _extract_with_ocr(path)
    if ocr_result is not None:
        return ocr_result
    if last_result is not None:
        return last_result
    return PdfExtractionResult(
        text="",
        backend="unavailable",
        warnings=["No PDF backend installed; returning empty extraction."],
    )


class PdfTextExtraction:
    def __init__(self, *, ok: bool, status: str, text: str, backend: str | None = None) -> None:
        self.ok = ok
        self.status = status
        self.text = text
        self.backend = backend


def extract_pdf_text(path: Path) -> PdfTextExtraction:
    if not path.exists():
        return PdfTextExtraction(ok=False, status="missing_file", text="", backend=None)
    result = extract_text_from_pdf(path)
    if result.backend == "unavailable" or not result.text:
        return PdfTextExtraction(
            ok=False,
            status="backend_unavailable",
            text=result.text,
            backend=result.backend,
        )
    return PdfTextExtraction(ok=True, status="ok", text=result.text, backend=result.backend)
