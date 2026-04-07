from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from scripts.build_validation_summary import build_validation_summary


_YEARS = (2022, 2023, 2024, 2025)
_SOURCE_META = {
    "phm_society_conf": {"label": "PHM Society Conference", "result_source": "phm"},
    "ijphm": {"label": "IJPHM", "result_source": "ijphm"},
}


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _pct(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}\\%"


def _latex_escape(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _table_tex(column_spec: str, headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        r"\begin{tabular}{" + column_spec + "}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(lines) + "\n"


def _load_source_year_summary(root: Path, source_group: str, year: int) -> dict[str, object]:
    return _read_json(root / "data" / "processed" / source_group / str(year) / "audit" / "summary.json")


def _load_source_year_results(root: Path, source_group: str, year: int) -> list[dict[str, str]]:
    return _read_csv(root / "data" / "processed" / source_group / str(year) / "audit" / "audit_results.csv")


def _pooled_categories(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {
        "Neither publicly available": 0,
        "Only data publicly available": 0,
        "Only code publicly available": 0,
        "Both code and data publicly available": 0,
    }
    for row in rows:
        code_public = row.get("code_label") == "A1"
        data_public = row.get("data_label") == "A1"
        if code_public and data_public:
            counts["Both code and data publicly available"] += 1
        elif code_public:
            counts["Only code publicly available"] += 1
        elif data_public:
            counts["Only data publicly available"] += 1
        else:
            counts["Neither publicly available"] += 1
    return counts


def _build_main_results(root: Path) -> dict[str, object]:
    combined_summary = _read_json(root / "data" / "processed" / "summary.json")
    pooled_records = _read_csv(root / "plots" / "output" / "pooled_overview_data.csv")
    pooled_counts = {row["category"]: int(row["count"]) for row in pooled_records}
    pooled_props = {row["category"]: float(row["proportion"]) for row in pooled_records}

    by_source: dict[str, dict[str, object]] = {}
    corpus_rows: list[dict[str, object]] = []
    strict_rows: list[dict[str, object]] = []
    label_distribution_rows: list[dict[str, object]] = []

    all_rows: list[dict[str, str]] = []
    for source_group, meta in _SOURCE_META.items():
        source_rows: list[dict[str, str]] = []
        source_paper_count = 0
        source_eligible = 0
        source_full_text = 0
        for year in _YEARS:
            summary = _load_source_year_summary(root, source_group, year)
            results = _load_source_year_results(root, source_group, year)
            source_rows.extend(results)
            source_paper_count += int(summary["paper_count"])
            source_eligible += int(summary["repro_audit_eligible_count"])
            analysis_sources = summary.get("analysis_text_source_counts", {})
            source_full_text += int(analysis_sources.get("full_text", 0))
            corpus_rows.append(
                {
                    "source": meta["label"],
                    "year": year,
                    "papers": int(summary["paper_count"]),
                    "eligible": int(summary["repro_audit_eligible_count"]),
                    "full_text_share": _pct(
                        int(analysis_sources.get("full_text", 0)),
                        int(summary["paper_count"]),
                    ),
                }
            )
        all_rows.extend(source_rows)
        pooled = _pooled_categories(source_rows)
        by_source[source_group] = {
            "label": meta["label"],
            "paper_count": source_paper_count,
            "repro_audit_eligible_count": source_eligible,
            "full_text_count": source_full_text,
            "full_text_share": _pct(source_full_text, source_paper_count),
            "code_label_counts": dict(Counter(row["code_label"] for row in source_rows)),
            "data_label_counts": dict(Counter(row["data_label"] for row in source_rows)),
            "strict_a1_counts": {
                "code": sum(row["code_label"] == "A1" for row in source_rows),
                "data": sum(row["data_label"] == "A1" for row in source_rows),
            },
            "pooled_strict": pooled,
        }
        label_distribution_rows.extend(
            [
                {
                    "scope": meta["label"],
                    "channel": "Code",
                    "A1": by_source[source_group]["code_label_counts"].get("A1", 0),
                    "A2": by_source[source_group]["code_label_counts"].get("A2", 0),
                    "A3": by_source[source_group]["code_label_counts"].get("A3", 0),
                    "A4": by_source[source_group]["code_label_counts"].get("A4", 0),
                    "A5": by_source[source_group]["code_label_counts"].get("A5", 0),
                },
                {
                    "scope": meta["label"],
                    "channel": "Data",
                    "A1": by_source[source_group]["data_label_counts"].get("A1", 0),
                    "A2": by_source[source_group]["data_label_counts"].get("A2", 0),
                    "A3": by_source[source_group]["data_label_counts"].get("A3", 0),
                    "A4": by_source[source_group]["data_label_counts"].get("A4", 0),
                    "A5": by_source[source_group]["data_label_counts"].get("A5", 0),
                },
            ]
        )
        strict_rows.append(
            {
                "source": meta["label"],
                "paper_count": source_paper_count,
                "both": pooled["Both code and data publicly available"],
                "only_code": pooled["Only code publicly available"],
                "only_data": pooled["Only data publicly available"],
                "neither": pooled["Neither publicly available"],
            }
        )

    strict_rows.insert(
        0,
        {
            "source": "Pooled",
            "paper_count": int(combined_summary["paper_count"]),
            "both": pooled_counts["Both code and data publicly available"],
            "only_code": pooled_counts["Only code publicly available"],
            "only_data": pooled_counts["Only data publicly available"],
            "neither": pooled_counts["Neither publicly available"],
        },
    )
    label_distribution_rows.insert(
        0,
        {
            "scope": "Pooled",
            "channel": "Code",
            "A1": int(combined_summary["code_label_counts"].get("A1", 0)),
            "A2": int(combined_summary["code_label_counts"].get("A2", 0)),
            "A3": int(combined_summary["code_label_counts"].get("A3", 0)),
            "A4": int(combined_summary["code_label_counts"].get("A4", 0)),
            "A5": int(combined_summary["code_label_counts"].get("A5", 0)),
        },
    )
    label_distribution_rows.insert(
        1,
        {
            "scope": "Pooled",
            "channel": "Data",
            "A1": int(combined_summary["data_label_counts"].get("A1", 0)),
            "A2": int(combined_summary["data_label_counts"].get("A2", 0)),
            "A3": int(combined_summary["data_label_counts"].get("A3", 0)),
            "A4": int(combined_summary["data_label_counts"].get("A4", 0)),
            "A5": int(combined_summary["data_label_counts"].get("A5", 0)),
        },
    )

    return {
        "combined_summary": combined_summary,
        "pooled_strict": {
            "total": int(combined_summary["paper_count"]),
            "counts": pooled_counts,
            "proportions": pooled_props,
        },
        "by_source": by_source,
        "corpus_rows": corpus_rows,
        "strict_rows": strict_rows,
        "label_distribution_rows": label_distribution_rows,
        "all_rows_count": len(all_rows),
    }


def _build_validation_results(root: Path) -> dict[str, object]:
    summary_path = root / "data" / "validation" / "combined_validation_summary.json"
    table_path = root / "data" / "validation" / "combined_validation_table.csv"
    if not summary_path.exists() or not table_path.exists():
        build_validation_summary(root, root / "data" / "validation")
    return {
        "summary": _read_json(summary_path),
        "table": _read_csv(table_path),
    }


def _build_sensitivity_results(root: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    all_results: list[dict[str, str]] = []
    for year in _YEARS:
        results = _load_source_year_results(root, "phm_society_conf", year)
        all_results.extend(results)
        strict_explicit = sum(row["data_label"] != "A5" for row in results)
        sensitivity_additions = sum(
            (row.get("data_public_external_dataset", "").lower() in {"1", "true", "yes"}) and row["data_label"] == "A5"
            for row in results
        )
        broader_total = strict_explicit + sensitivity_additions
        rows.append(
            {
                "year": str(year),
                "paper_count": len(results),
                "strict_explicit_data_access_count": strict_explicit,
                "strict_explicit_data_access_share": _pct(strict_explicit, len(results)),
                "external_public_dataset_additions": sensitivity_additions,
                "broader_public_data_access_count": broader_total,
                "broader_public_data_access_share": _pct(broader_total, len(results)),
            }
        )
    strict_explicit = sum(row["data_label"] != "A5" for row in all_results)
    sensitivity_additions = sum(
        (row.get("data_public_external_dataset", "").lower() in {"1", "true", "yes"}) and row["data_label"] == "A5"
        for row in all_results
    )
    broader_total = strict_explicit + sensitivity_additions
    rows.insert(
        0,
        {
            "year": "All",
            "paper_count": len(all_results),
            "strict_explicit_data_access_count": strict_explicit,
            "strict_explicit_data_access_share": _pct(strict_explicit, len(all_results)),
            "external_public_dataset_additions": sensitivity_additions,
            "broader_public_data_access_count": broader_total,
            "broader_public_data_access_share": _pct(broader_total, len(all_results)),
        },
    )
    return {
        "policy_note": (
            "Sensitivity view only: PHM rows with external-public-dataset signals and strict data=A5 "
            "are reinterpreted as broader public-data-access cases."
        ),
        "rows": rows,
    }

def _build_metrics_tex(main_results: dict[str, object], validation_results: dict[str, object], sensitivity_results: dict[str, object]) -> str:
    by_source = main_results["by_source"]
    validation_summary = validation_results["summary"]
    all_sensitivity = sensitivity_results["rows"][0]
    pooled = main_results["pooled_strict"]
    combined = main_results["combined_summary"]

    phm_external_count = 0
    ijphm_external_count = 0
    # Recompute from by-source summaries already present in JSON
    for key, bucket in by_source.items():
        if key == "phm_society_conf":
            phm_external_count = int(bucket.get("external_public_data_count", 0))
        if key == "ijphm":
            ijphm_external_count = int(bucket.get("external_public_data_count", 0))

    metrics = {
        "CorpusTotalPapers": str(combined["paper_count"]),
        "CorpusEligiblePapers": str(combined["repro_audit_eligible_count"]),
        "CorpusEligibleShare": _fmt_pct(_pct(int(combined["repro_audit_eligible_count"]), int(combined["paper_count"]))),
        "PooledNeitherCount": str(pooled["counts"]["Neither publicly available"]),
        "PooledNeitherShare": _fmt_pct(pooled["proportions"]["Neither publicly available"]),
        "PooledOnlyCodeCount": str(pooled["counts"]["Only code publicly available"]),
        "PooledOnlyCodeShare": _fmt_pct(pooled["proportions"]["Only code publicly available"]),
        "PooledOnlyDataCount": str(pooled["counts"]["Only data publicly available"]),
        "PooledOnlyDataShare": _fmt_pct(pooled["proportions"]["Only data publicly available"]),
        "PooledBothCount": str(pooled["counts"]["Both code and data publicly available"]),
        "PooledBothShare": _fmt_pct(pooled["proportions"]["Both code and data publicly available"]),
        "CombinedCodeAOneCount": str(int(combined["code_label_counts"].get("A1", 0))),
        "CombinedCodeATwoCount": str(int(combined["code_label_counts"].get("A2", 0))),
        "CombinedCodeAThreeCount": str(int(combined["code_label_counts"].get("A3", 0))),
        "CombinedCodeAFourCount": str(int(combined["code_label_counts"].get("A4", 0))),
        "CombinedCodeAFiveCount": str(int(combined["code_label_counts"].get("A5", 0))),
        "CombinedDataAOneCount": str(int(combined["data_label_counts"].get("A1", 0))),
        "CombinedDataATwoCount": str(int(combined["data_label_counts"].get("A2", 0))),
        "CombinedDataAThreeCount": str(int(combined["data_label_counts"].get("A3", 0))),
        "CombinedDataAFourCount": str(int(combined["data_label_counts"].get("A4", 0))),
        "CombinedDataAFiveCount": str(int(combined["data_label_counts"].get("A5", 0))),
        "PHMPaperCount": str(by_source["phm_society_conf"]["paper_count"]),
        "IJPHMPaperCount": str(by_source["ijphm"]["paper_count"]),
        "PHMFullTextCount": str(by_source["phm_society_conf"]["full_text_count"]),
        "PHMFullTextShare": _fmt_pct(float(by_source["phm_society_conf"]["full_text_share"])),
        "IJPHMFullTextCount": str(by_source["ijphm"]["full_text_count"]),
        "IJPHMFullTextShare": _fmt_pct(float(by_source["ijphm"]["full_text_share"])),
        "PHMStrictBothCount": str(by_source["phm_society_conf"]["pooled_strict"]["Both code and data publicly available"]),
        "PHMStrictOnlyCodeCount": str(by_source["phm_society_conf"]["pooled_strict"]["Only code publicly available"]),
        "PHMStrictOnlyDataCount": str(by_source["phm_society_conf"]["pooled_strict"]["Only data publicly available"]),
        "PHMStrictNeitherCount": str(by_source["phm_society_conf"]["pooled_strict"]["Neither publicly available"]),
        "IJPHMStrictBothCount": str(by_source["ijphm"]["pooled_strict"]["Both code and data publicly available"]),
        "IJPHMStrictOnlyCodeCount": str(by_source["ijphm"]["pooled_strict"]["Only code publicly available"]),
        "IJPHMStrictOnlyDataCount": str(by_source["ijphm"]["pooled_strict"]["Only data publicly available"]),
        "IJPHMStrictNeitherCount": str(by_source["ijphm"]["pooled_strict"]["Neither publicly available"]),
        "PHMExternalPublicDataCount": str(phm_external_count),
        "PHMExternalPublicDataShare": _fmt_pct(_pct(phm_external_count, int(by_source["phm_society_conf"]["paper_count"]))),
        "PooledBenchmarkCount": str(int(combined["data_named_public_benchmark_count"])),
        "PooledBenchmarkShare": _fmt_pct(_pct(int(combined["data_named_public_benchmark_count"]), int(combined["paper_count"]))),
        "PooledExternalPublicDataCount": str(int(combined["data_public_external_dataset_count"])),
        "PooledExternalPublicDataShare": _fmt_pct(_pct(int(combined["data_public_external_dataset_count"]), int(combined["paper_count"]))),
        "IJPHMExternalPublicDataCount": str(ijphm_external_count),
        "IJPHMExternalPublicDataShare": _fmt_pct(_pct(ijphm_external_count, int(by_source["ijphm"]["paper_count"]))),
        "CombinedValidationSampleSize": str(validation_summary["combined"]["total_sample_size"]),
        "PHMValidationCodeAccuracy": _fmt_pct(float(validation_summary["sources"]["phm"]["code_accuracy"])),
        "PHMValidationDataAccuracy": _fmt_pct(float(validation_summary["sources"]["phm"]["data_accuracy"])),
        "PHMValidationJointAccuracy": _fmt_pct(float(validation_summary["sources"]["phm"]["joint_accuracy"])),
        "IJPHMValidationCodeAccuracy": _fmt_pct(float(validation_summary["sources"]["ijphm"]["code_accuracy"])),
        "IJPHMValidationDataAccuracy": _fmt_pct(float(validation_summary["sources"]["ijphm"]["data_accuracy"])),
        "IJPHMValidationJointAccuracy": _fmt_pct(float(validation_summary["sources"]["ijphm"]["joint_accuracy"])),
        "PHMSensitivityBroaderCount": str(all_sensitivity["broader_public_data_access_count"]),
        "PHMSensitivityBroaderShare": _fmt_pct(float(all_sensitivity["broader_public_data_access_share"])),
    }
    return "\n".join(r"\providecommand{\%s}{%s}" % (name, value) for name, value in metrics.items()) + "\n"


def build_paper_exports(root: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = output_dir / "appendix_tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    main_results = _build_main_results(root)
    # add external-public-data totals to by_source
    for source_group in _SOURCE_META:
        external_total = 0
        for year in _YEARS:
            summary = _load_source_year_summary(root, source_group, year)
            external_total += int(summary.get("data_public_external_dataset_count", 0))
        main_results["by_source"][source_group]["external_public_data_count"] = external_total

    validation_results = _build_validation_results(root)
    sensitivity_results = _build_sensitivity_results(root)

    appendix_root = root / "data" / "processed" / "appendix"
    benchmark_by_source = _read_csv(appendix_root / "benchmark_summary_by_source.csv")
    benchmark_by_year = _read_csv(appendix_root / "benchmark_summary_by_year.csv")
    external_by_source = _read_csv(appendix_root / "external_public_data_summary_by_source.csv")
    external_by_year = _read_csv(appendix_root / "external_public_data_summary_by_year.csv")

    outputs = {
        "main_results": _write_text(output_dir / "main_results.json", json.dumps(main_results, indent=2)),
        "validation_results": _write_text(output_dir / "validation_results.json", json.dumps(validation_results, indent=2)),
        "sensitivity_results": _write_text(output_dir / "sensitivity_results.json", json.dumps(sensitivity_results, indent=2)),
        "metrics_tex": _write_text(output_dir / "paper_metrics.tex", _build_metrics_tex(main_results, validation_results, sensitivity_results)),
    }

    corpus_rows = [
        [
            _latex_escape(str(row["source"])),
            str(row["year"]),
            str(row["papers"]),
            str(row["eligible"]),
            _fmt_pct(float(row["full_text_share"])),
        ]
        for row in main_results["corpus_rows"]
    ]
    outputs["main_corpus_table_tex"] = _write_text(
        tables_dir / "main_corpus_table.tex",
        _table_tex("llrrr", ["Source", "Year", "Papers", "Eligible", "Full-text share"], corpus_rows),
    )

    strict_rows = [
        [
            _latex_escape(str(row["source"])),
            str(row["paper_count"]),
            str(row["both"]),
            str(row["only_code"]),
            str(row["only_data"]),
            str(row["neither"]),
        ]
        for row in main_results["strict_rows"]
    ]
    outputs["main_strict_results_table_tex"] = _write_text(
        tables_dir / "main_strict_results_table.tex",
        _table_tex("lrrrrr", ["Source", "Papers", "Both", "Only code", "Only data", "Neither"], strict_rows),
    )

    label_distribution_rows = [
        [
            _latex_escape(str(row["scope"])),
            _latex_escape(str(row["channel"])),
            str(row["A1"]),
            str(row["A2"]),
            str(row["A3"]),
            str(row["A4"]),
            str(row["A5"]),
        ]
        for row in main_results["label_distribution_rows"]
    ]
    outputs["appendix_label_distribution_table_tex"] = _write_text(
        tables_dir / "appendix_label_distribution_table.tex",
        _table_tex("llrrrrr", ["Scope", "Channel", "A1", "A2", "A3", "A4", "A5"], label_distribution_rows),
    )

    validation_rows = [
        [
            _latex_escape(row["source"].upper() if row["source"] == "phm" else "IJPHM"),
            str(row["sample_size"]),
            _fmt_pct(float(row["code_accuracy"])),
            _fmt_pct(float(row["data_accuracy"])),
            _fmt_pct(float(row["joint_accuracy"])),
            str(row["disagreement_count"]),
        ]
        for row in validation_results["table"]
    ]
    outputs["appendix_validation_table_tex"] = _write_text(
        tables_dir / "appendix_validation_table.tex",
        _table_tex("lrrrrr", ["Source", "Sample", "Code acc.", "Data acc.", "Joint acc.", "Disagreements"], validation_rows),
    )

    benchmark_rows = [
        [
            _latex_escape(_SOURCE_META.get(row["source_group"], {}).get("label", row["source_group"])),
            str(row.get("year", "All")),
            str(row["paper_count"]),
            str(row["benchmark_count"]),
            _fmt_pct(float(row["benchmark_share"])),
        ]
        for row in benchmark_by_source + benchmark_by_year
    ]
    outputs["appendix_benchmark_table_tex"] = _write_text(
        tables_dir / "appendix_benchmark_table.tex",
        _table_tex("llrrr", ["Scope", "Year", "Papers", "Benchmark rows", "Share"], benchmark_rows),
    )

    external_rows = [
        [
            _latex_escape(_SOURCE_META.get(row["source_group"], {}).get("label", row["source_group"])),
            str(row.get("year", "All")),
            str(row["paper_count"]),
            str(row["external_public_data_count"]),
            _fmt_pct(float(row["external_public_data_share"])),
        ]
        for row in external_by_source + external_by_year
    ]
    outputs["appendix_external_public_data_table_tex"] = _write_text(
        tables_dir / "appendix_external_public_data_table.tex",
        _table_tex("llrrr", ["Scope", "Year", "Papers", "External-public-data rows", "Share"], external_rows),
    )

    sensitivity_rows = [
        [
            _latex_escape(str(row["year"])),
            str(row["paper_count"]),
            str(row["strict_explicit_data_access_count"]),
            _fmt_pct(float(row["strict_explicit_data_access_share"])),
            str(row["external_public_dataset_additions"]),
            str(row["broader_public_data_access_count"]),
            _fmt_pct(float(row["broader_public_data_access_share"])),
        ]
        for row in sensitivity_results["rows"]
    ]
    outputs["appendix_phm_sensitivity_table_tex"] = _write_text(
        tables_dir / "appendix_phm_sensitivity_table.tex",
        _table_tex(
            "lrrrrrr",
            [
                "Year",
                "Papers",
                "Strict explicit",
                "Strict share",
                "Sensitivity add.",
                "Broader access",
                "Broader share",
            ],
            sensitivity_rows,
        ),
    )

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build JSON and LaTeX exports for the standalone audit report.")
    parser.add_argument(
        "--output-dir",
        default="data/paper_exports",
        help="Directory for generated JSON and LaTeX export artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = build_paper_exports(Path("."), Path(args.output_dir))
    for path in outputs.values():
        print(path)


if __name__ == "__main__":
    main()
