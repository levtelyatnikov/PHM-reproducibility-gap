from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AttachmentRecord:
    label: str
    url: str
    role: str = "paper"
    mime_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaperRecord:
    paper_id: str
    source: str
    year: int
    track: str
    title: str
    authors: list[str]
    article_url: str
    doi: str | None = None
    article_id: str | None = None
    issue_url: str | None = None
    pdf_url: str | None = None
    abstract: str | None = None
    published_at: str | None = None
    attachments: list[AttachmentRecord] = field(default_factory=list)
    retrieval_status: str = "discovered"
    phm_relevant: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        return payload


@dataclass(slots=True)
class ArticlePageDetails:
    doi: str | None = None
    published_at: str | None = None
    attachments: list[AttachmentRecord] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceWindow:
    url: str | None
    context: str
    domain: str | None
    start: int
    end: int


@dataclass(slots=True)
class RuleAssessment:
    channel: str
    label: str
    confidence: float
    reasons: list[str]
    rule_hits: dict[str, bool]
    evidence_snippets: list[str] = field(default_factory=list)
    supporting_urls: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass(slots=True)
class JudgeVote:
    model: str
    channel: str
    label: str
    confidence: float
    rationale: str


@dataclass(slots=True)
class JudgeVoteRecord:
    model_name: str
    channel: str
    label: str
    confidence: float
    rationale: str
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConsensusDecision:
    channel: str
    label: str
    confidence: float
    reasons: list[str]
    votes: list[JudgeVote]
    note: str | None = None
    supporting_urls: list[str] = field(default_factory=list)
    review_required: bool = False

    def vote_summary(self) -> str:
        return "; ".join(
            f"{vote.model}:{vote.label}@{vote.confidence:.2f}" for vote in self.votes
        )


@dataclass(slots=True)
class FetchArtifact:
    url: str
    status_code: int
    content_type: str | None
    body: bytes
    headers: dict[str, str]


@dataclass(slots=True)
class ClassificationRecord:
    paper_id: str
    code_label: str
    data_label: str
    code_evidence: list[str] = field(default_factory=list)
    data_evidence: list[str] = field(default_factory=list)
    review_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditTraceRecord:
    paper_id: str
    source: str
    year: int
    track: str
    title: str
    code_label: str
    data_label: str
    code_a1: bool
    code_a2: bool
    code_a3: bool
    code_a4: bool
    code_a5: bool
    data_a1: bool
    data_a2: bool
    data_a3: bool
    data_a4: bool
    data_a5: bool
    judge_votes: list[JudgeVoteRecord] = field(default_factory=list)
    main_urls: list[str] = field(default_factory=list)
    retrieval_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["judge_votes"] = [vote.to_dict() for vote in self.judge_votes]
        return payload


@dataclass(slots=True)
class PdfExtractionResult:
    text: str
    backend: str
    warnings: list[str] = field(default_factory=list)
