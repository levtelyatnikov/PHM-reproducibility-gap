from __future__ import annotations

from pathlib import Path

from engine.evidence import extract_evidence_windows
from engine.rules import classify_channel
from shared.pdf_extract import extract_text_from_pdf


FIXTURE_ROOT = Path("tests/fixtures/real_pdfs")

REAL_CASES = [
    {
        "pdf": "phm_2022_3304.pdf",
        "code_label": "A1",
        "data_label": "A5",
        "code_note_contains": "framework is available at",
    },
    {
        "pdf": "phm_2022_3144.pdf",
        "code_label": "A5",
        "data_label": "A2",
        "data_note_contains": "only currently available public data set",
    },
    {
        "pdf": "phm_2022_3154.pdf",
        "code_label": "A5",
        "data_label": "A3",
        "data_note_contains": "made available for others for research purposes upon requests from the authors",
    },
    {
        "pdf": "phm_2022_3150.pdf",
        "code_label": "A5",
        "data_label": "A4",
        "data_note_contains": "yet not publicly available",
    },
    {
        "pdf": "phm_2022_3148.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3214.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3238.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3188.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3227.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3173.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
    {
        "pdf": "phm_2022_3230.pdf",
        "code_label": "A5",
        "data_label": "A5",
    },
]


def test_real_pdf_fixture_suite_spans_all_a_categories() -> None:
    observed = {case["code_label"] for case in REAL_CASES} | {case["data_label"] for case in REAL_CASES}

    assert observed == {"A1", "A2", "A3", "A4", "A5"}


def test_real_pdf_gold_cases_classify_correctly() -> None:
    for case in REAL_CASES:
        extraction = extract_text_from_pdf(FIXTURE_ROOT / case["pdf"])
        windows = extract_evidence_windows(extraction.text)
        code = classify_channel("code", extraction.text, windows)
        data = classify_channel("data", extraction.text, windows)

        assert code.label == case["code_label"], case["pdf"]
        assert data.label == case["data_label"], case["pdf"]

        if "code_note_contains" in case:
            assert case["code_note_contains"] in (code.note or ""), case["pdf"]
        if "data_note_contains" in case:
            assert case["data_note_contains"] in (data.note or ""), case["pdf"]


def test_reference_only_github_citations_do_not_trigger_code_claim() -> None:
    extraction = extract_text_from_pdf(FIXTURE_ROOT / "phm_2022_3214.pdf")
    code = classify_channel("code", extraction.text, extract_evidence_windows(extraction.text))

    assert code.label == "A5"
    assert code.note is None
