import csv
import json
from pathlib import Path

from scripts.build_validation_summary import build_validation_summary


def _write_eval(root: Path, name: str, *, total: int, code: float, data: float, joint: float, disagreements: int) -> None:
    eval_dir = root / "data" / "validation" / f"{name}_manual_validation_eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "evaluation_summary.json").write_text(
        json.dumps(
            {
                "total": total,
                "code_accuracy": code,
                "data_accuracy": data,
                "joint_accuracy": joint,
                "code_a1_precision": 1.0,
                "data_a1_precision": 0.5,
            }
        ),
        encoding="utf-8",
    )
    with (eval_dir / "evaluation_disagreements.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["paper_id"])
        writer.writeheader()
        for index in range(disagreements):
            writer.writerow({"paper_id": f"{name}-{index}"})


def test_build_validation_summary_writes_json_and_csv(tmp_path: Path) -> None:
    _write_eval(tmp_path, "phm", total=60, code=0.98, data=0.80, joint=0.80, disagreements=12)
    _write_eval(tmp_path, "ijphm", total=60, code=1.0, data=1.0, joint=1.0, disagreements=0)

    summary_path, table_path = build_validation_summary(tmp_path, tmp_path / "data" / "validation")

    assert summary_path.exists()
    assert table_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["combined"]["total_sample_size"] == 120
    assert summary["sources"]["phm"]["disagreement_count"] == 12
    assert summary["sources"]["ijphm"]["code_accuracy"] == 1.0

    with table_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["source"] for row in rows} == {"phm", "ijphm"}
