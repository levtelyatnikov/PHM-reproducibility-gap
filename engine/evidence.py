from __future__ import annotations

import re
from dataclasses import dataclass

from shared.normalize import domain_from_url
from shared.schemas import EvidenceWindow


_URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s)>\]]+")


def extract_evidence_windows(text: str, *, window_size: int = 160) -> list[EvidenceWindow]:
    windows: list[EvidenceWindow] = []
    for match in _URL_PATTERN.finditer(text):
        start = max(0, match.start() - window_size)
        end = min(len(text), match.end() + window_size)
        context = text[start:end].strip()
        url = match.group(0).rstrip(".,;")
        if url.startswith("www."):
            url = f"https://{url}"
        windows.append(
            EvidenceWindow(
                url=url,
                context=context,
                domain=domain_from_url(url),
                start=start,
                end=end,
            )
        )
    if not windows and text.strip():
        windows.append(EvidenceWindow(url=None, context=text.strip(), domain=None, start=0, end=len(text)))
    return windows


@dataclass(slots=True)
class EvidenceHit:
    url: str | None
    snippet: str
    ownership_cue: bool
    restricted_cue: bool
    is_public_artifact: bool


def extract_evidence_hits(text: str, *, kind: str) -> list[EvidenceHit]:
    hits: list[EvidenceHit] = []
    for window in extract_evidence_windows(text):
        context = window.context.lower()
        ownership = any(phrase in context for phrase in ("our code", "our repository", "we release", "our dataset"))
        restricted = any(phrase in context for phrase in ("available on request", "upon request", "nda"))
        relevant = kind == "code" and any(
            phrase in context for phrase in ("code", "repository", "repo", "github", "gitlab")
        )
        relevant = relevant or (kind == "data" and any(phrase in context for phrase in ("data", "dataset", "corpus")))
        if window.url is None and not restricted:
            continue
        hits.append(
            EvidenceHit(
                url=window.url,
                snippet=window.context,
                ownership_cue=ownership,
                restricted_cue=restricted,
                is_public_artifact=bool(window.url and relevant and not restricted),
            )
        )
    return hits
