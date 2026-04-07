from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

from shared.pdf_extract import extract_text_from_pdf


YEARS = (2022, 2023, 2024, 2025)
SAMPLE_PER_YEAR = 15
SAMPLE_SEED = 20260407
KEYWORDS = (
    "github",
    "gitlab",
    "zenodo",
    "figshare",
    "dryad",
    "supplementary material",
    "supplementary materials",
    "supplementary",
    "available on request",
    "available upon request",
    "publicly available",
    "code and data available",
    "dataset",
    "data available",
    "repository",
    "our code",
    "our data",
)
SOURCE_CONFIG = {
    "phm": {
        "processed_group": "phm_society_conf",
        "raw_group": "phm_conf_society",
        "prefix": "phm",
    },
    "ijphm": {
        "processed_group": "ijphm",
        "raw_group": "ijphm",
        "prefix": "ijphm",
    },
}


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def _keyword_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for sentence in _sentences(text):
        lower = sentence.lower()
        if any(keyword in lower for keyword in KEYWORDS):
            snippets.append(sentence)
    return snippets[:12]


def _source_config(source: str) -> dict[str, str]:
    try:
        return SOURCE_CONFIG[source]
    except KeyError as exc:
        raise ValueError(f"Unsupported source '{source}'. Expected one of: {', '.join(sorted(SOURCE_CONFIG))}.") from exc


def _html_to_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _load_paper_text(paper_root: Path) -> str:
    pdf_candidates = sorted(paper_root.glob("*.pdf"))
    if pdf_candidates:
        return extract_text_from_pdf(pdf_candidates[0]).text
    html_path = paper_root / "article.html"
    if html_path.exists():
        return _html_to_text(html_path)
    return ""


def sample_rows(root: Path, *, source: str) -> list[dict[str, str]]:
    config = _source_config(source)
    rng = random.Random(SAMPLE_SEED)
    sampled: list[dict[str, str]] = []
    for year in YEARS:
        path = root / "data" / "processed" / config["processed_group"] / str(year) / "audit" / "audit_results.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        sampled.extend(rng.sample(rows, min(SAMPLE_PER_YEAR, len(rows))))
    return sampled


def build_manual_validation_bundle(root: Path, output_dir: Path, *, source: str) -> tuple[Path, Path]:
    config = _source_config(source)
    sampled = sample_rows(root, source=source)

    rows: list[dict[str, str]] = []
    snippets_rows: list[dict[str, str]] = []
    for row in sampled:
        paper_root = root / "data" / "raw" / config["raw_group"] / row["year"] / row["paper_id"]
        text = _load_paper_text(paper_root)
        snippets = _keyword_snippets(text)
        rows.append(
            {
                "paper_id": row["paper_id"],
                "source": source,
                "year": row["year"],
                "title": row["title"],
                "article_url": row["article_url"],
                "pred_code_label": row["code_label"],
                "pred_data_label": row["data_label"],
                "pred_code_note": row.get("code_note", ""),
                "pred_data_note": row.get("data_note", ""),
                "manual_code_label": "",
                "manual_data_label": "",
                "manual_code_note": "",
                "manual_data_note": "",
                "manual_comments": "",
            }
        )
        snippets_rows.append(
            {
                "paper_id": row["paper_id"],
                "source": source,
                "year": row["year"],
                "title": row["title"],
                "snippet_count": str(len(snippets)),
                "snippets": " || ".join(snippets),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    sample_path = output_dir / f"{config['prefix']}_manual_validation_sample.csv"
    snippets_path = output_dir / f"{config['prefix']}_manual_validation_snippets.csv"
    with sample_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with snippets_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(snippets_rows[0].keys()))
        writer.writeheader()
        writer.writerows(snippets_rows)
    return sample_path, snippets_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reproducible PHM/IJPHM manual-validation sample.")
    parser.add_argument(
        "--source",
        choices=sorted(SOURCE_CONFIG),
        required=True,
        help="Audit source to sample from.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/validation",
        help="Destination directory for the sample and snippet CSVs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_path, snippets_path = build_manual_validation_bundle(
        Path("."),
        Path(args.output_dir),
        source=args.source,
    )
    print(sample_path)
    print(snippets_path)


if __name__ == "__main__":
    main()
