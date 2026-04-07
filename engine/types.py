from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PaperRecord:
    paper_id: str
    source: str
    year: int
    track: str
    title: str
    authors: tuple[str, ...]
    doi: str | None
    article_url: str
    pdf_url: str | None
    retrieval_status: str
    phm_relevant: bool | None


@dataclass(slots=True)
class ChannelClassification:
    label: str
    confidence: float
    reasons: tuple[str, ...] = ()
    evidence_urls: tuple[str, ...] = ()


@dataclass(slots=True)
class PaperAuditResult:
    paper: PaperRecord
    code: ChannelClassification
    data: ChannelClassification
    repro_score: int
    review_required: bool
    consensus_reason: str
    judge_votes: dict[str, list[str]] = field(default_factory=dict)

