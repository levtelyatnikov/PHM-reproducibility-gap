import csv
from pathlib import Path

from scripts.prepare_gold_set import build_gold_template


def _write_trace(path: Path, source: str, year: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "source",
                "year",
                "track",
                "title",
                "article_url",
                "doi",
                "code_label",
                "data_label",
                "code_note",
                "data_note",
                "note",
                "code_reasons",
                "data_reasons",
                "code_supporting_urls",
                "data_supporting_urls",
                "data_named_public_benchmark",
            ],
        )
        writer.writeheader()
        for index in range(10):
            writer.writerow(
                {
                    "paper_id": f"{source}-{year}-{index}",
                    "source": source.replace("_society_conf", "") if source.startswith("phm") else source,
                    "year": year,
                    "track": "Technical Research Papers",
                    "title": f"{source} {year} paper {index}",
                    "article_url": f"https://example.com/{source}/{year}/{index}",
                    "doi": "",
                    "code_label": "A1" if index == 0 else "A5",
                    "data_label": "A3" if index == 1 else "A5",
                    "code_note": "our code is available at https://github.com/acme/repo" if index == 0 else "",
                    "data_note": "data available upon request" if index == 1 else "",
                    "note": "",
                    "code_reasons": "[]",
                    "data_reasons": "[]",
                    "code_supporting_urls": "[]",
                    "data_supporting_urls": "[]",
                    "data_named_public_benchmark": "false",
                }
            )


def test_build_gold_template_creates_expected_sample_size(tmp_path: Path) -> None:
    for source_group in ("phm_society_conf", "ijphm"):
        for year in (2022, 2023, 2024, 2025):
            _write_trace(
                tmp_path / "data" / "processed" / source_group / str(year) / "audit" / "audit_trace.csv",
                source_group,
                year,
            )

    rows = build_gold_template(tmp_path)

    assert len(rows) == 80
    assert any(row["code_label_pred"] == "A1" for row in rows)
    assert any(row["data_label_pred"] == "A3" for row in rows)
