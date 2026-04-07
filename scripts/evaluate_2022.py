from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


_LABELS = ("A1", "A2", "A3", "A4", "A5")


@dataclass(slots=True)
class Metrics:
    total: int
    code_accuracy: float
    data_accuracy: float
    joint_accuracy: float
    code_macro_f1: float
    data_macro_f1: float
    code_a1_precision: float
    code_a1_recall: float
    data_a1_precision: float
    data_a1_recall: float
    code_per_class: dict[str, dict[str, float]]
    data_per_class: dict[str, dict[str, float]]
    code_confusion: dict[str, dict[str, int]]
    data_confusion: dict[str, dict[str, int]]
    disagreements: list[dict[str, str]]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "code_accuracy": self.code_accuracy,
            "data_accuracy": self.data_accuracy,
            "joint_accuracy": self.joint_accuracy,
            "code_macro_f1": self.code_macro_f1,
            "data_macro_f1": self.data_macro_f1,
            "code_a1_precision": self.code_a1_precision,
            "code_a1_recall": self.code_a1_recall,
            "data_a1_precision": self.data_a1_precision,
            "data_a1_recall": self.data_a1_recall,
            "code_per_class": self.code_per_class,
            "data_per_class": self.data_per_class,
            "code_confusion": self.code_confusion,
            "data_confusion": self.data_confusion,
        }


def _label_key(row: dict[str, str], *, prefix: str) -> str:
    gold_key = f"{prefix}_label_gold"
    if gold_key in row and row[gold_key]:
        return row[gold_key]
    return row[f"{prefix}_label"]


def _note_key(row: dict[str, str], *, prefix: str) -> str:
    gold_key = f"{prefix}_note_gold"
    if gold_key in row and row[gold_key]:
        return row[gold_key]
    return row.get(f"{prefix}_note", "")


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _per_class_metrics(
    gold_labels: list[str],
    pred_labels: list[str],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, int]], float]:
    confusion = {
        gold: {pred: 0 for pred in _LABELS}
        for gold in _LABELS
    }
    for gold, pred in zip(gold_labels, pred_labels, strict=True):
        confusion[gold][pred] += 1

    per_class: dict[str, dict[str, float]] = {}
    f1_values: list[float] = []
    for label in _LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in _LABELS if other != label)
        fn = sum(confusion[label][other] for other in _LABELS if other != label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(confusion[label].values()),
        }
        f1_values.append(f1)

    return per_class, confusion, sum(f1_values) / len(f1_values)


def evaluate_predictions(gold_path: Path, predictions_path: Path) -> Metrics:
    with gold_path.open(newline="", encoding="utf-8") as handle:
        gold_rows = {row["paper_id"]: row for row in csv.DictReader(handle)}
    with predictions_path.open(newline="", encoding="utf-8") as handle:
        pred_rows = {row["paper_id"]: row for row in csv.DictReader(handle)}

    overlap = sorted(set(gold_rows) & set(pred_rows))
    if not overlap:
        raise RuntimeError("No overlapping paper_id values between gold and predictions.")

    code_correct = 0
    data_correct = 0
    joint_correct = 0
    code_gold: list[str] = []
    code_pred: list[str] = []
    data_gold: list[str] = []
    data_pred: list[str] = []
    disagreements: list[dict[str, str]] = []

    for paper_id in overlap:
        gold_row = gold_rows[paper_id]
        pred_row = pred_rows[paper_id]
        gold_code = _label_key(gold_row, prefix="code")
        gold_data = _label_key(gold_row, prefix="data")
        pred_code = pred_row["code_label"]
        pred_data = pred_row["data_label"]
        code_match = gold_code == pred_code
        data_match = gold_data == pred_data
        code_correct += int(code_match)
        data_correct += int(data_match)
        joint_correct += int(code_match and data_match)
        code_gold.append(gold_code)
        code_pred.append(pred_code)
        data_gold.append(gold_data)
        data_pred.append(pred_data)

        if not (code_match and data_match):
            disagreements.append(
                {
                    "paper_id": paper_id,
                    "source": pred_row.get("source", gold_row.get("source", "")),
                    "year": pred_row.get("year", gold_row.get("year", "")),
                    "title": pred_row.get("title", gold_row.get("title", "")),
                    "code_label_pred": pred_code,
                    "code_label_gold": gold_code,
                    "data_label_pred": pred_data,
                    "data_label_gold": gold_data,
                    "code_note_pred": pred_row.get("code_note", ""),
                    "data_note_pred": pred_row.get("data_note", ""),
                    "code_note_gold": _note_key(gold_row, prefix="code"),
                    "data_note_gold": _note_key(gold_row, prefix="data"),
                    "disagreement_type": (
                        "code_and_data" if (not code_match and not data_match)
                        else "code_only" if not code_match
                        else "data_only"
                    ),
                }
            )

    code_per_class, code_confusion, code_macro_f1 = _per_class_metrics(code_gold, code_pred)
    data_per_class, data_confusion, data_macro_f1 = _per_class_metrics(data_gold, data_pred)

    total = len(overlap)
    return Metrics(
        total=total,
        code_accuracy=code_correct / total,
        data_accuracy=data_correct / total,
        joint_accuracy=joint_correct / total,
        code_macro_f1=code_macro_f1,
        data_macro_f1=data_macro_f1,
        code_a1_precision=code_per_class["A1"]["precision"],
        code_a1_recall=code_per_class["A1"]["recall"],
        data_a1_precision=data_per_class["A1"]["precision"],
        data_a1_recall=data_per_class["A1"]["recall"],
        code_per_class=code_per_class,
        data_per_class=data_per_class,
        code_confusion=code_confusion,
        data_confusion=data_confusion,
        disagreements=disagreements,
    )


def _write_evaluation_outputs(metrics: Metrics, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation_summary.json").write_text(
        json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (output_dir / "evaluation_disagreements.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "source",
                "year",
                "title",
                "code_label_pred",
                "code_label_gold",
                "data_label_pred",
                "data_label_gold",
                "code_note_pred",
                "data_note_pred",
                "code_note_gold",
                "data_note_gold",
                "disagreement_type",
            ],
        )
        writer.writeheader()
        writer.writerows(metrics.disagreements)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate audit predictions against a gold set.")
    parser.add_argument("--gold", required=True, help="Path to the gold CSV.")
    parser.add_argument(
        "--predictions",
        default="data/processed/audit_results.csv",
        help="Path to the predicted audit results CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/validation",
        help="Directory for evaluation_summary.json and evaluation_disagreements.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = evaluate_predictions(Path(args.gold), Path(args.predictions))
    _write_evaluation_outputs(metrics, Path(args.output_dir))
    print(f"papers={metrics.total}")
    print(f"code_accuracy={metrics.code_accuracy:.3f}")
    print(f"data_accuracy={metrics.data_accuracy:.3f}")
    print(f"joint_accuracy={metrics.joint_accuracy:.3f}")
    print(f"code_macro_f1={metrics.code_macro_f1:.3f}")
    print(f"data_macro_f1={metrics.data_macro_f1:.3f}")
    print(f"code_a1_precision={metrics.code_a1_precision:.3f}")
    print(f"data_a1_precision={metrics.data_a1_precision:.3f}")


if __name__ == "__main__":
    main()
