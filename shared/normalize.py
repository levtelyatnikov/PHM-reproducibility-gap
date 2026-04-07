from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower().strip()
    return _NON_ALNUM.sub("-", lowered).strip("-") or "untitled"


def guess_attachment_role(label: str) -> str:
    lowered = label.lower()
    if "slide" in lowered:
        return "slides"
    if "presentation" in lowered:
        return "presentation"
    if "extended abstract" in lowered:
        return "extended_abstract"
    return "paper"


def first_author_slug(authors: list[str]) -> str:
    if not authors:
        return "unknown"
    last_token = authors[0].split()[-1]
    return slugify(last_token)


def build_paper_id(
    source: str,
    year: int,
    title: str,
    article_id: str | None = None,
    doi: str | None = None,
) -> str:
    if article_id:
        return f"{source}-{year}-{article_id}"
    if doi:
        suffix = slugify(doi.split("/")[-1])[:32]
        return f"{source}-{year}-{suffix}"
    return f"{source}-{year}-{slugify(title)[:48]}"


def normalized_pdf_name(year: int, authors: list[str], title: str) -> str:
    return f"{year}_{first_author_slug(authors)}_{slugify(title)}.pdf"


def domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host[4:] if host.startswith("www.") else host

