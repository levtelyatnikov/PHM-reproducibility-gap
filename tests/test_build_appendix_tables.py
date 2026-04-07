import csv
from pathlib import Path

from scripts.build_appendix_tables import build_tables


def _write_results(path: Path, *, benchmark: bool, external_public: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "code_label",
                "data_label",
                "data_named_public_benchmark",
                "data_public_benchmark_name",
                "data_public_external_dataset",
                "data_public_external_dataset_type",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "paper_id": "p1",
                "code_label": "A1",
                "data_label": "A5",
                "data_named_public_benchmark": str(benchmark).lower(),
                "data_public_benchmark_name": "C-MAPSS" if benchmark else "",
                "data_public_external_dataset": str(external_public).lower(),
                "data_public_external_dataset_type": "named_benchmark" if external_public else "",
            }
        )
        writer.writerow(
            {
                "paper_id": "p2",
                "code_label": "A5",
                "data_label": "A5",
                "data_named_public_benchmark": "false",
                "data_public_benchmark_name": "",
                "data_public_external_dataset": "false",
                "data_public_external_dataset_type": "",
            }
        )


def test_build_tables_writes_benchmark_csvs(tmp_path: Path) -> None:
    for source_group in ("phm_society_conf", "ijphm"):
        for year in (2022, 2023, 2024, 2025):
            _write_results(
                tmp_path / "data" / "processed" / source_group / str(year) / "audit" / "audit_results.csv",
                benchmark=(year == 2022),
                external_public=(year in (2022, 2023)),
            )

    output_dir = tmp_path / "data" / "processed" / "appendix"
    build_tables(tmp_path, output_dir)

    assert (output_dir / "benchmark_summary_by_source.csv").exists()
    assert (output_dir / "benchmark_summary_by_year.csv").exists()
    assert (output_dir / "benchmark_name_frequency.csv").exists()
    assert (output_dir / "external_public_data_summary_by_source.csv").exists()
    assert (output_dir / "external_public_data_summary_by_year.csv").exists()
