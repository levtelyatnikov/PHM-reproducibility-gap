import csv
import json
from pathlib import Path

from shared.manifest import write_csv, write_jsonl
from shared.storage import StorageLayout


def test_storage_prepares_expected_directories(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path / "data")
    layout.prepare()

    assert layout.raw_dir.exists()
    assert layout.interim_dir.exists()
    assert layout.processed_dir.exists()


def test_storage_maps_raw_source_directories_consistently(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path / "data")

    assert layout.raw_year_dir("phm", 2024) == tmp_path / "data" / "raw" / "phm_conf_society" / "2024"
    assert layout.raw_year_dir("phm_conf_society", 2025) == tmp_path / "data" / "raw" / "phm_conf_society" / "2025"
    assert layout.raw_year_dir("ijphm", 2025) == tmp_path / "data" / "raw" / "ijphm" / "2025"


def test_storage_maps_processed_year_audit_directories_consistently(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path / "data")

    assert (
        layout.processed_year_audit_dir("phm_society_conf", 2024)
        == tmp_path / "data" / "processed" / "phm_society_conf" / "2024" / "audit"
    )
    assert (
        layout.processed_year_audit_dir("ijphm", 2025)
        == tmp_path / "data" / "processed" / "ijphm" / "2025" / "audit"
    )


def test_manifest_writers_emit_csv_and_jsonl(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "rows.csv", [{"paper_id": "p1", "code_label": "A1"}])
    jsonl_path = write_jsonl(tmp_path / "rows.jsonl", [{"paper_id": "p1", "code_label": "A1"}])

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with jsonl_path.open(encoding="utf-8") as handle:
        payload = [json.loads(line) for line in handle]

    assert rows[0]["paper_id"] == "p1"
    assert payload[0]["code_label"] == "A1"
