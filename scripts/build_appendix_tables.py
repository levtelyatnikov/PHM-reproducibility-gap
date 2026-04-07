from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


_SOURCE_GROUPS = {
    "phm_society_conf": [2022, 2023, 2024, 2025],
    "ijphm": [2022, 2023, 2024, 2025],
}


def _load_rows(root: Path, source_group: str, year: int) -> list[dict[str, str]]:
    path = root / "data" / "processed" / source_group / str(year) / "audit" / "audit_results.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def build_tables(root: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    venue_rows: list[dict[str, object]] = []
    year_rows: list[dict[str, object]] = []
    name_rows: list[dict[str, object]] = []
    external_venue_rows: list[dict[str, object]] = []
    external_year_rows: list[dict[str, object]] = []
    benchmark_name_counters: dict[str, Counter[str]] = {}
    external_type_counters: dict[str, Counter[str]] = {}

    for source_group, years in _SOURCE_GROUPS.items():
        all_rows: list[dict[str, str]] = []
        benchmark_name_counters[source_group] = Counter()
        external_type_counters[source_group] = Counter()
        for year in years:
            rows = _load_rows(root, source_group, year)
            all_rows.extend(rows)
            benchmark_rows = [row for row in rows if _as_bool(row.get("data_named_public_benchmark", ""))]
            external_rows = [row for row in rows if _as_bool(row.get("data_public_external_dataset", ""))]
            for row in benchmark_rows:
                name = row.get("data_public_benchmark_name", "")
                if name:
                    benchmark_name_counters[source_group][name] += 1
            for row in external_rows:
                kind = row.get("data_public_external_dataset_type", "")
                if kind:
                    external_type_counters[source_group][kind] += 1
            year_rows.append(
                {
                    "source_group": source_group,
                    "year": year,
                    "paper_count": len(rows),
                    "benchmark_count": len(benchmark_rows),
                    "benchmark_share": len(benchmark_rows) / len(rows) if rows else 0.0,
                    "strict_code_a1_count": sum(row["code_label"] == "A1" for row in rows),
                    "strict_data_a1_count": sum(row["data_label"] == "A1" for row in rows),
                }
            )
            external_year_rows.append(
                {
                    "source_group": source_group,
                    "year": year,
                    "paper_count": len(rows),
                    "external_public_data_count": len(external_rows),
                    "external_public_data_share": len(external_rows) / len(rows) if rows else 0.0,
                }
            )

        all_benchmark_rows = [row for row in all_rows if _as_bool(row.get("data_named_public_benchmark", ""))]
        all_external_rows = [row for row in all_rows if _as_bool(row.get("data_public_external_dataset", ""))]
        venue_rows.append(
            {
                "source_group": source_group,
                "paper_count": len(all_rows),
                "benchmark_count": len(all_benchmark_rows),
                "benchmark_share": len(all_benchmark_rows) / len(all_rows) if all_rows else 0.0,
                "strict_code_a1_count": sum(row["code_label"] == "A1" for row in all_rows),
                "strict_data_a1_count": sum(row["data_label"] == "A1" for row in all_rows),
            }
        )
        external_venue_rows.append(
            {
                "source_group": source_group,
                "paper_count": len(all_rows),
                "external_public_data_count": len(all_external_rows),
                "external_public_data_share": len(all_external_rows) / len(all_rows) if all_rows else 0.0,
                "external_public_data_type_counts": dict(external_type_counters[source_group]),
            }
        )

    pooled_counter = Counter()
    for counter in benchmark_name_counters.values():
        pooled_counter.update(counter)

    for source_group, counter in benchmark_name_counters.items():
        for name, count in counter.most_common():
            name_rows.append(
                {
                    "source_group": source_group,
                    "benchmark_name": name,
                    "count": count,
                }
            )
    for name, count in pooled_counter.most_common():
        name_rows.append(
            {
                "source_group": "pooled",
                "benchmark_name": name,
                "count": count,
            }
        )

    for filename, rows in {
        "benchmark_summary_by_source.csv": venue_rows,
        "benchmark_summary_by_year.csv": year_rows,
        "benchmark_name_frequency.csv": name_rows,
        "external_public_data_summary_by_source.csv": external_venue_rows,
        "external_public_data_summary_by_year.csv": external_year_rows,
    }.items():
        path = output_dir / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build appendix-ready benchmark summary tables.")
    parser.add_argument(
        "--output-dir",
        default="data/processed/appendix",
        help="Output directory for appendix summary CSVs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_tables(Path("."), Path(args.output_dir))
    print(f"wrote={Path(args.output_dir)}")


if __name__ == "__main__":
    main()
