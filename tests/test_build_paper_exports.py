import csv
import json
from pathlib import Path

from scripts.build_paper_exports import build_paper_exports


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_paper_exports_writes_json_and_tex_artifacts(tmp_path: Path) -> None:
    _write_summary(
        tmp_path / "data" / "processed" / "summary.json",
        {
            "paper_count": 10,
            "repro_audit_eligible_count": 9,
            "track_counts": {"Technical Research Papers": 4, "Technical Papers": 6},
            "retrieval_status_counts": {"full_text": 9, "metadata_only": 1},
            "analysis_text_source_counts": {"full_text": 9, "missing_full_text": 1},
            "code_label_counts": {"A1": 2, "A5": 8},
            "data_label_counts": {"A1": 1, "A5": 9},
            "data_named_public_benchmark_count": 3,
            "data_public_external_dataset_count": 4,
        },
    )
    for source_group, source_name, counts in (
        ("phm_society_conf", "phm", [3, 2, 0, 0]),
        ("ijphm", "ijphm", [1, 1, 2, 2]),
    ):
        for year, paper_count in zip((2022, 2023, 2024, 2025), counts, strict=False):
            _write_summary(
                tmp_path / "data" / "processed" / source_group / str(year) / "audit" / "summary.json",
                {
                    "source_group": source_group,
                    "year": year,
                    "paper_count": paper_count,
                    "repro_audit_eligible_count": paper_count,
                    "retrieval_status_counts": {"full_text": paper_count},
                    "code_label_counts": {"A1": 1 if year == 2022 else 0, "A5": max(paper_count - 1, 0)},
                    "data_label_counts": {"A1": 1 if source_name == "ijphm" and year == 2022 else 0, "A5": max(paper_count - (1 if source_name == "ijphm" and year == 2022 else 0), 0)},
                    "data_named_public_benchmark_count": 1 if year == 2022 else 0,
                    "data_public_external_dataset_count": 1 if year in (2022, 2023) else 0,
                },
            )
            _write_csv(
                tmp_path / "data" / "processed" / source_group / str(year) / "audit" / "audit_results.csv",
                ["paper_id", "source", "year", "code_label", "data_label", "data_public_external_dataset"],
                [
                    {
                        "paper_id": f"{source_name}-{year}-{index}",
                        "source": source_name,
                        "year": year,
                        "code_label": "A1" if index == 0 and paper_count else "A5",
                        "data_label": "A1" if source_name == "ijphm" and year == 2022 and index == 0 and paper_count else "A5",
                        "data_public_external_dataset": "true" if index == 0 and year in (2022, 2023) and paper_count else "false",
                    }
                    for index in range(paper_count)
                ],
            )

    _write_csv(
        tmp_path / "plots" / "output" / "pooled_overview_data.csv",
        ["category", "count", "total", "proportion"],
        [
            {"category": "Neither publicly available", "count": 7, "total": 10, "proportion": 0.7},
            {"category": "Only data publicly available", "count": 1, "total": 10, "proportion": 0.1},
            {"category": "Only code publicly available", "count": 1, "total": 10, "proportion": 0.1},
            {"category": "Both code and data publicly available", "count": 1, "total": 10, "proportion": 0.1},
        ],
    )
    appendix_root = tmp_path / "data" / "processed" / "appendix"
    _write_csv(
        appendix_root / "benchmark_summary_by_source.csv",
        ["source_group", "paper_count", "benchmark_count", "benchmark_share", "strict_code_a1_count", "strict_data_a1_count"],
        [{"source_group": "phm_society_conf", "paper_count": 5, "benchmark_count": 2, "benchmark_share": 0.4, "strict_code_a1_count": 1, "strict_data_a1_count": 0}],
    )
    _write_csv(
        appendix_root / "benchmark_summary_by_year.csv",
        ["source_group", "year", "paper_count", "benchmark_count", "benchmark_share", "strict_code_a1_count", "strict_data_a1_count"],
        [{"source_group": "phm_society_conf", "year": 2022, "paper_count": 3, "benchmark_count": 1, "benchmark_share": 0.333, "strict_code_a1_count": 1, "strict_data_a1_count": 0}],
    )
    _write_csv(
        appendix_root / "external_public_data_summary_by_source.csv",
        ["source_group", "paper_count", "external_public_data_count", "external_public_data_share", "external_public_data_type_counts"],
        [{"source_group": "phm_society_conf", "paper_count": 5, "external_public_data_count": 2, "external_public_data_share": 0.4, "external_public_data_type_counts": "{'named_benchmark': 2}"}],
    )
    _write_csv(
        appendix_root / "external_public_data_summary_by_year.csv",
        ["source_group", "year", "paper_count", "external_public_data_count", "external_public_data_share"],
        [{"source_group": "phm_society_conf", "year": 2022, "paper_count": 3, "external_public_data_count": 1, "external_public_data_share": 0.333}],
    )

    validation_root = tmp_path / "data" / "validation"
    _write_summary(
        validation_root / "combined_validation_summary.json",
        {
            "combined": {"total_sample_size": 120},
            "sources": {
                "phm": {"sample_size": 60, "code_accuracy": 0.98, "data_accuracy": 0.8, "joint_accuracy": 0.8},
                "ijphm": {"sample_size": 60, "code_accuracy": 1.0, "data_accuracy": 1.0, "joint_accuracy": 1.0},
            },
        },
    )
    _write_csv(
        validation_root / "combined_validation_table.csv",
        ["source", "sample_size", "code_accuracy", "data_accuracy", "joint_accuracy", "code_a1_precision", "data_a1_precision", "disagreement_count", "headline_note"],
        [{"source": "phm", "sample_size": 60, "code_accuracy": 0.98, "data_accuracy": 0.8, "joint_accuracy": 0.8, "code_a1_precision": 1.0, "data_a1_precision": 1.0, "disagreement_count": 12, "headline_note": "test"}],
    )

    outputs = build_paper_exports(tmp_path, tmp_path / "data" / "paper_exports")

    assert outputs["main_results"].exists()
    assert outputs["validation_results"].exists()
    assert outputs["sensitivity_results"].exists()
    assert outputs["metrics_tex"].exists()
    assert outputs["main_corpus_table_tex"].exists()
    assert outputs["appendix_validation_table_tex"].exists()

    main_results = json.loads(outputs["main_results"].read_text(encoding="utf-8"))
    assert main_results["pooled_strict"]["total"] == 10
    assert main_results["pooled_strict"]["counts"]["Both code and data publicly available"] == 1
