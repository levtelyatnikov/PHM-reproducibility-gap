from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


_SOURCE_GROUPS = {
    "phm_society_conf": [2022, 2023, 2024, 2025],
    "ijphm": [2022, 2023, 2024, 2025],
}
_TARGET_PER_STRATUM = 10
_SEED = 20260406
_CUE_PATTERNS = (
    "github",
    "gitlab",
    "zenodo",
    "figshare",
    "supplementary material",
    "dataset is available",
    "data available",
    "code and data available",
    "repository",
    "available online",
)


def _load_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source_group, years in _SOURCE_GROUPS.items():
        for year in years:
            path = root / "data" / "processed" / source_group / str(year) / "audit" / "audit_trace.csv"
            with path.open(newline="", encoding="utf-8") as handle:
                rows.extend(csv.DictReader(handle))
    return rows


def _row_priority(row: dict[str, str]) -> tuple[int, int]:
    score = 0
    reasons = 0
    labels = {row["code_label"], row["data_label"]}
    if "A1" in labels:
        score += 100
        reasons += 1
    if labels & {"A2", "A3", "A4"}:
        score += 60
        reasons += 1
    haystack = " ".join(
        [
            row.get("title", ""),
            row.get("code_note", ""),
            row.get("data_note", ""),
            row.get("note", ""),
            row.get("code_reasons", ""),
            row.get("data_reasons", ""),
            row.get("code_supporting_urls", ""),
            row.get("data_supporting_urls", ""),
        ]
    ).lower()
    hits = sum(pattern in haystack for pattern in _CUE_PATTERNS)
    score += hits * 10
    if hits:
        reasons += 1
    if row.get("data_named_public_benchmark", "").lower() in {"1", "true", "yes"}:
        score += 5
    return score, reasons


def _sample_stratum(rows: list[dict[str, str]], rng: random.Random) -> list[dict[str, str]]:
    ranked = sorted(rows, key=_row_priority, reverse=True)
    selected: list[dict[str, str]] = []
    used_ids: set[str] = set()

    for row in ranked:
        if len(selected) >= _TARGET_PER_STRATUM:
            break
        labels = {row["code_label"], row["data_label"]}
        score, reasons = _row_priority(row)
        if "A1" in labels or labels & {"A2", "A3"} or reasons > 1:
            selected.append(row)
            used_ids.add(row["paper_id"])

    remaining = [row for row in rows if row["paper_id"] not in used_ids]
    rng.shuffle(remaining)
    for row in remaining:
        if len(selected) >= _TARGET_PER_STRATUM:
            break
        selected.append(row)

    return selected[:_TARGET_PER_STRATUM]


def build_gold_template(root: Path) -> list[dict[str, str]]:
    all_rows = _load_rows(root)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in all_rows:
        grouped.setdefault((row["source"], row["year"]), []).append(row)

    rng = random.Random(_SEED)
    selected: list[dict[str, str]] = []
    for key in sorted(grouped):
        selected.extend(_sample_stratum(grouped[key], rng))

    output_rows: list[dict[str, str]] = []
    for row in selected:
        output_rows.append(
            {
                "paper_id": row["paper_id"],
                "source": row["source"],
                "year": row["year"],
                "track": row.get("track", ""),
                "title": row["title"],
                "article_url": row.get("article_url", ""),
                "doi": row.get("doi", ""),
                "code_label_pred": row["code_label"],
                "data_label_pred": row["data_label"],
                "code_note_pred": row.get("code_note", ""),
                "data_note_pred": row.get("data_note", ""),
                "code_label_gold": "",
                "data_label_gold": "",
                "code_note_gold": "",
                "data_note_gold": "",
                "annotator_id": "",
                "adjudicated": "",
                "adjudication_note": "",
            }
        )
    return output_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a stratified PHM/IJPHM gold-set template.")
    parser.add_argument(
        "--output",
        default="data/validation/gold_set_template.csv",
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    rows = build_gold_template(Path("."))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote={output_path}")
    print(f"papers={len(rows)}")


if __name__ == "__main__":
    main()
