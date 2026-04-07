from __future__ import annotations

import csv
from pathlib import Path

from plots.build_audit_figures import (
    build_all_figures,
    collect_plot_records,
    collect_public_data_context_records,
    collect_pooled_availability_records,
)


def _write_audit_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "code_label",
                "data_label",
                "data_named_public_benchmark",
                "data_public_external_dataset",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_collect_plot_records_aggregates_venue_counts_for_appendix_figures(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    _write_audit_results(
        processed_root / "phm_society_conf" / "2022" / "audit" / "audit_results.csv",
        [
            {"paper_id": "phm-1", "code_label": "A1", "data_label": "A5"},
            {"paper_id": "phm-2", "code_label": "A5", "data_label": "A3"},
        ],
    )
    _write_audit_results(
        processed_root / "ijphm" / "2022" / "audit" / "audit_results.csv",
        [
            {"paper_id": "ijphm-1", "code_label": "A2", "data_label": "A5"},
            {"paper_id": "ijphm-2", "code_label": "A5", "data_label": "A5"},
        ],
    )

    records = collect_plot_records(processed_root=processed_root, years=[2022])

    phm_code = [record for record in records if record.figure_key == "phm_society_conf" and record.channel == "Code"]
    assert {record.category: record.count for record in phm_code}["A1"] == 1
    assert {record.category: record.count for record in phm_code}["A5"] == 1

    ijphm_data = [record for record in records if record.figure_key == "ijphm" and record.channel == "Data"]
    assert {record.category: record.count for record in ijphm_data}["A5"] == 2


def test_collect_pooled_availability_records_uses_strict_a1_categories(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    _write_audit_results(
        processed_root / "phm_society_conf" / "2022" / "audit" / "audit_results.csv",
        [
            {"paper_id": "phm-1", "code_label": "A1", "data_label": "A1"},
            {"paper_id": "phm-2", "code_label": "A1", "data_label": "A5"},
        ],
    )
    _write_audit_results(
        processed_root / "ijphm" / "2022" / "audit" / "audit_results.csv",
        [
            {"paper_id": "ijphm-1", "code_label": "A5", "data_label": "A1"},
            {"paper_id": "ijphm-2", "code_label": "A5", "data_label": "A5"},
        ],
    )

    records = collect_pooled_availability_records(processed_root=processed_root, years=[2022])

    assert {record.category: record.count for record in records} == {
        "Both code and data publicly available": 1,
        "Only code publicly available": 1,
        "Only data publicly available": 1,
        "Neither publicly available": 1,
    }


def test_collect_public_data_context_records_tracks_strict_and_external_signals(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    _write_audit_results(
        processed_root / "phm_society_conf" / "2022" / "audit" / "audit_results.csv",
        [
            {
                "paper_id": "phm-1",
                "code_label": "A5",
                "data_label": "A1",
                "data_named_public_benchmark": "true",
                "data_public_external_dataset": "true",
            },
            {
                "paper_id": "phm-2",
                "code_label": "A5",
                "data_label": "A5",
                "data_named_public_benchmark": "false",
                "data_public_external_dataset": "true",
            },
        ],
    )
    _write_audit_results(
        processed_root / "ijphm" / "2022" / "audit" / "audit_results.csv",
        [
            {
                "paper_id": "ijphm-1",
                "code_label": "A5",
                "data_label": "A5",
                "data_named_public_benchmark": "true",
                "data_public_external_dataset": "true",
            }
        ],
    )

    records = collect_public_data_context_records(processed_root=processed_root, years=[2022])
    pooled = {(record.scope, record.category): record.count for record in records}

    assert pooled[("Pooled", "Strict data A1")] == 1
    assert pooled[("Pooled", "Named benchmark")] == 2
    assert pooled[("Pooled", "External public data")] == 3


def test_build_all_figures_writes_expected_outputs(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    output_dir = tmp_path / "plots" / "output"
    for venue in ("phm_society_conf", "ijphm"):
        _write_audit_results(
            processed_root / venue / "2022" / "audit" / "audit_results.csv",
            [
                {
                    "paper_id": f"{venue}-1",
                    "code_label": "A1",
                    "data_label": "A5",
                    "data_named_public_benchmark": "true",
                    "data_public_external_dataset": "true",
                },
                {
                    "paper_id": f"{venue}-2",
                    "code_label": "A5",
                    "data_label": "A4",
                    "data_named_public_benchmark": "false",
                    "data_public_external_dataset": "false",
                },
            ],
        )

    generated = build_all_figures(processed_root=processed_root, output_dir=output_dir, years=[2022])

    expected_names = {
        "pooled_reproducibility_2022_2025.pdf",
        "pooled_reproducibility_2022_2025.png",
        "phm_society_conf_reproducibility_2022_2025.pdf",
        "phm_society_conf_reproducibility_2022_2025.png",
        "ijphm_reproducibility_2022_2025.pdf",
        "ijphm_reproducibility_2022_2025.png",
        "strict_label_distribution_2022_2025.pdf",
        "strict_label_distribution_2022_2025.png",
        "public_data_context_2022_2025.pdf",
        "public_data_context_2022_2025.png",
        "plot_data.csv",
        "pooled_overview_data.csv",
        "public_data_context_data.csv",
    }
    assert expected_names <= {path.name for path in generated}
    for name in expected_names:
        assert (output_dir / name).exists()
