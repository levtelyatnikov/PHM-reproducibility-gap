from pathlib import Path

from scripts.evaluate_2022 import evaluate_predictions


def test_evaluate_predictions_computes_joint_accuracy(tmp_path: Path) -> None:
    gold = tmp_path / "gold.csv"
    pred = tmp_path / "pred.csv"
    gold.write_text(
        "paper_id,code_label,data_label\n"
        "p1,A1,A3\n"
        "p2,A5,A5\n",
        encoding="utf-8",
    )
    pred.write_text(
        "paper_id,code_label,data_label\n"
        "p1,A1,A3\n"
        "p2,A2,A5\n",
        encoding="utf-8",
    )

    metrics = evaluate_predictions(gold, pred)

    assert metrics.total == 2
    assert metrics.code_accuracy == 0.5
    assert metrics.data_accuracy == 1.0
    assert metrics.joint_accuracy == 0.5
    assert metrics.code_per_class["A1"]["precision"] == 1.0
    assert metrics.code_per_class["A2"]["precision"] == 0.0
    assert len(metrics.disagreements) == 1
