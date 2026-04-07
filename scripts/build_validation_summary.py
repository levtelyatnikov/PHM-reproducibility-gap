from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


_SOURCE_CONFIG = {
    "phm": {
        "eval_dir": "phm_manual_validation_eval",
        "headline_note": (
            "Disagreements are concentrated in broader public-data-access sensitivity cases; "
            "strict A1 calls remain high precision."
        ),
    },
    "ijphm": {
        "eval_dir": "ijphm_manual_validation_eval",
        "headline_note": (
            "The strict IJPHM sample matched after targeted fixes for repository links, "
            "reference-only URLs, and generic system-language false positives."
        ),
    },
}


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def build_validation_summary(root: Path, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    combined_sample_size = 0
    weighted_code_correct = 0.0
    weighted_data_correct = 0.0
    weighted_joint_correct = 0.0
    summary_sources: dict[str, dict[str, object]] = {}

    for source, config in _SOURCE_CONFIG.items():
        eval_dir = root / "data" / "validation" / config["eval_dir"]
        summary = _read_json(eval_dir / "evaluation_summary.json")
        disagreements = _count_rows(eval_dir / "evaluation_disagreements.csv")
        sample_size = int(summary["total"])
        code_accuracy = float(summary["code_accuracy"])
        data_accuracy = float(summary["data_accuracy"])
        joint_accuracy = float(summary["joint_accuracy"])
        code_a1_precision = float(summary["code_a1_precision"])
        data_a1_precision = float(summary["data_a1_precision"])

        row = {
            "source": source,
            "sample_size": sample_size,
            "code_accuracy": code_accuracy,
            "data_accuracy": data_accuracy,
            "joint_accuracy": joint_accuracy,
            "code_a1_precision": code_a1_precision,
            "data_a1_precision": data_a1_precision,
            "disagreement_count": disagreements,
            "headline_note": config["headline_note"],
        }
        rows.append(row)
        summary_sources[source] = row

        combined_sample_size += sample_size
        weighted_code_correct += code_accuracy * sample_size
        weighted_data_correct += data_accuracy * sample_size
        weighted_joint_correct += joint_accuracy * sample_size

    combined = {
        "total_sample_size": combined_sample_size,
        "weighted_code_accuracy": weighted_code_correct / combined_sample_size if combined_sample_size else 0.0,
        "weighted_data_accuracy": weighted_data_correct / combined_sample_size if combined_sample_size else 0.0,
        "weighted_joint_accuracy": weighted_joint_correct / combined_sample_size if combined_sample_size else 0.0,
        "strict_policy_note": (
            "Strict A1-A5 results remain official. Benchmark and externally public dataset access "
            "are tracked as a separate appendix-facing dimension."
        ),
        "intentional_conservatism_note": (
            "The analyzer is conservative by design and may undercall broader public-data access "
            "when no author-controlled artifact release is stated."
        ),
    }

    summary_payload = {
        "sources": summary_sources,
        "combined": combined,
    }

    summary_path = output_dir / "combined_validation_summary.json"
    table_path = output_dir / "combined_validation_table.csv"
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    with table_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return summary_path, table_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a combined PHM/IJPHM validation summary.")
    parser.add_argument(
        "--output-dir",
        default="data/validation",
        help="Directory for combined_validation_summary.json and combined_validation_table.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_path, table_path = build_validation_summary(Path("."), Path(args.output_dir))
    print(summary_path)
    print(table_path)


if __name__ == "__main__":
    main()
