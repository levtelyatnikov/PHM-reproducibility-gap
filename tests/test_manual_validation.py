import csv
from pathlib import Path

from scripts.manual_validation import build_manual_validation_bundle


def _write_results(path: Path, *, source: str, year: int, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "source",
                "year",
                "title",
                "article_url",
                "code_label",
                "data_label",
                "code_note",
                "data_note",
            ],
        )
        writer.writeheader()
        for index in range(count):
            writer.writerow(
                {
                    "paper_id": f"{source}-{year}-{index}",
                    "source": source,
                    "year": year,
                    "title": f"{source} {year} paper {index}",
                    "article_url": f"https://example.com/{source}/{year}/{index}",
                    "code_label": "A5",
                    "data_label": "A5",
                    "code_note": "",
                    "data_note": "",
                }
            )


def test_build_manual_validation_bundle_supports_phm_and_ijphm(tmp_path: Path) -> None:
    for year in (2022, 2023, 2024, 2025):
        _write_results(
            tmp_path / "data" / "processed" / "phm_society_conf" / str(year) / "audit" / "audit_results.csv",
            source="phm",
            year=year,
            count=15,
        )
        _write_results(
            tmp_path / "data" / "processed" / "ijphm" / str(year) / "audit" / "audit_results.csv",
            source="ijphm",
            year=year,
            count=15,
        )

    phm_sample, phm_snippets = build_manual_validation_bundle(
        tmp_path,
        tmp_path / "out",
        source="phm",
    )
    ijphm_sample, ijphm_snippets = build_manual_validation_bundle(
        tmp_path,
        tmp_path / "out",
        source="ijphm",
    )

    assert phm_sample.name == "phm_manual_validation_sample.csv"
    assert phm_snippets.name == "phm_manual_validation_snippets.csv"
    assert ijphm_sample.name == "ijphm_manual_validation_sample.csv"
    assert ijphm_snippets.name == "ijphm_manual_validation_snippets.csv"

    with phm_sample.open(newline="", encoding="utf-8") as handle:
        phm_rows = list(csv.DictReader(handle))
    with ijphm_sample.open(newline="", encoding="utf-8") as handle:
        ijphm_rows = list(csv.DictReader(handle))

    assert len(phm_rows) == 60
    assert len(ijphm_rows) == 60
    assert {row["year"] for row in phm_rows} == {"2022", "2023", "2024", "2025"}
    assert {row["year"] for row in ijphm_rows} == {"2022", "2023", "2024", "2025"}
