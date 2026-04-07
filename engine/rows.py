from __future__ import annotations

from engine.types import PaperAuditResult


def build_audit_result_row(result: PaperAuditResult) -> dict[str, object]:
    return {
        "paper_id": result.paper.paper_id,
        "source": result.paper.source,
        "year": result.paper.year,
        "track": result.paper.track,
        "title": result.paper.title,
        "retrieval_status": result.paper.retrieval_status,
        "phm_relevant": result.paper.phm_relevant,
        "code_label": result.code.label,
        "data_label": result.data.label,
        "repro_score": result.repro_score,
        "review_required": result.review_required,
    }


def build_audit_trace_row(result: PaperAuditResult) -> dict[str, object]:
    row = build_audit_result_row(result)
    for prefix, label in (("code", result.code.label), ("data", result.data.label)):
        for candidate in ("A1", "A2", "A3", "A4", "A5"):
            row[f"{prefix}_{candidate.lower()}"] = int(label == candidate)
    row["judge_votes"] = result.judge_votes
    row["consensus_reason"] = result.consensus_reason
    return row
