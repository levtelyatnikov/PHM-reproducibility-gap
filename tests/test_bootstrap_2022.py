import csv
from pathlib import Path

from scripts.bootstrap_2022 import (
    _audit_summary,
    _build_rows,
    _select_analysis_text,
    bootstrap_fixture_run,
)
from shared.schemas import PaperRecord


def test_bootstrap_fixture_run_emits_all_audit_csv_outputs(tmp_path: Path) -> None:
    output_paths = bootstrap_fixture_run(tmp_path)

    assert output_paths["audit_results"].exists()
    assert output_paths["audit_trace"].exists()
    assert output_paths["manual_review"].exists()

    with output_paths["audit_trace"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert {"code_a1", "code_a5", "data_a1", "data_a5", "judge_vote_summary"} <= set(rows[0])

    phm_year_audit_dir = tmp_path / "data" / "processed" / "phm_society_conf" / "2022" / "audit"
    assert (phm_year_audit_dir / "audit_results.csv").exists()
    assert (phm_year_audit_dir / "audit_trace.csv").exists()
    assert (phm_year_audit_dir / "manual_review_queue.csv").exists()
    assert (phm_year_audit_dir / "paper_manifest.csv").exists()
    assert (phm_year_audit_dir / "summary.json").exists()


def test_audit_summary_includes_public_benchmark_counts() -> None:
    papers = [
        PaperRecord(
            paper_id="phm-2022-demo",
            source="phm",
            year=2022,
            track="Technical Research Papers",
            title="Demo",
            authors=[],
            article_url="https://example.com/demo",
        )
    ]
    results = [
        {
            "paper_id": "phm-2022-demo",
            "code_label": "A5",
            "data_label": "A5",
            "review_required": False,
            "repro_audit_eligible": True,
            "analysis_text_source": "full_text",
            "data_named_public_benchmark": True,
            "data_public_benchmark_name": "C-MAPSS",
            "data_public_external_dataset": True,
            "data_public_external_dataset_type": "named_benchmark",
        }
    ]

    summary = _audit_summary(papers, results, source_group="phm_society_conf", year=2022)

    assert summary["data_named_public_benchmark_count"] == 1
    assert summary["eligible_data_named_public_benchmark_count"] == 1
    assert summary["data_public_benchmark_name_counts"] == {"C-MAPSS": 1}
    assert summary["data_public_external_dataset_count"] == 1
    assert summary["eligible_data_public_external_dataset_count"] == 1
    assert summary["data_public_external_dataset_type_counts"] == {"named_benchmark": 1}
    assert summary["analysis_text_source_counts"] == {"full_text": 1}


def test_select_analysis_text_prefers_extracted_text_over_abstract() -> None:
    paper = PaperRecord(
        paper_id="phm-2022-demo",
        source="phm",
        year=2022,
        track="Technical Research Papers",
        title="Demo",
        authors=[],
        article_url="https://example.com",
        retrieval_status="full_text",
        abstract="Abstract mention only.",
        metadata={"extracted_text": "Full text with our code at https://github.com/acme/repo"},
    )

    assert _select_analysis_text(paper) == "Full text with our code at https://github.com/acme/repo"
    assert paper.metadata["analysis_text_source"] == "full_text"
    assert paper.metadata["analysis_text_policy_passed"] is True


def test_select_analysis_text_does_not_silently_fallback_to_abstract_for_final_labels() -> None:
    paper = PaperRecord(
        paper_id="ijphm-2025-demo",
        source="ijphm",
        year=2025,
        track="Technical Papers",
        title="Demo",
        authors=[],
        article_url="https://example.com",
        retrieval_status="metadata_only",
        abstract="Our code is available at https://github.com/acme/demo.",
    )

    assert _select_analysis_text(paper) == ""
    assert paper.metadata["analysis_text_source"] == "missing_full_text"
    assert paper.metadata["analysis_text_policy_passed"] is False
    assert paper.metadata["repro_audit_eligible"] is False


def test_build_rows_uses_body_text_when_abstract_lacks_availability_statement() -> None:
    paper = PaperRecord(
        paper_id="phm-2024-demo",
        source="phm",
        year=2024,
        track="Technical Research Papers",
        title="Demo",
        authors=[],
        article_url="https://example.com",
        retrieval_status="full_text",
        abstract="We evaluate several methods for PHM.",
        metadata={
            "extracted_text": (
                "Introduction. Our framework is available at https://github.com/acme/body-only-release ."
            ),
            "repro_audit_eligible": True,
            "text_provider": "fitz",
        },
    )

    results, traces, reviews = _build_rows([paper], ["model-a", "model-b", "model-c"])

    assert results[0]["code_label"] == "A1"
    assert "framework is available at" in results[0]["code_note"]
    assert traces[0]["analysis_text_source"] == "full_text"
    assert not reviews


def test_build_rows_marks_missing_full_text_cases_for_review() -> None:
    paper = PaperRecord(
        paper_id="ijphm-2023-missing",
        source="ijphm",
        year=2023,
        track="Technical Papers",
        title="Missing text",
        authors=[],
        article_url="https://example.com",
        retrieval_status="metadata_only",
        abstract="The data are publicly available online.",
    )

    results, traces, reviews = _build_rows([paper], ["model-a", "model-b", "model-c"])

    assert results[0]["repro_audit_eligible"] is False
    assert results[0]["analysis_text_policy_passed"] is False
    assert traces[0]["analysis_text_source"] == "missing_full_text"
    assert reviews
