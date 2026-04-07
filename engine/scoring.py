from __future__ import annotations

import json

from shared.schemas import ConsensusDecision, PaperRecord


_CATEGORY_SCORE = {"A1": 4, "A2": 3, "A3": 2, "A4": 1, "A5": 0}


def category_score(label: str) -> int:
    return _CATEGORY_SCORE[label]


def _one_hot(prefix: str, label: str) -> dict[str, int]:
    return {
        f"{prefix}_a1": int(label == "A1"),
        f"{prefix}_a2": int(label == "A2"),
        f"{prefix}_a3": int(label == "A3"),
        f"{prefix}_a4": int(label == "A4"),
        f"{prefix}_a5": int(label == "A5"),
    }


def _combined_note(code_note: str, data_note: str) -> str:
    notes = [note for note in (code_note, data_note) if note]
    if not notes:
        return ""
    if len(notes) == 1:
        return notes[0]
    return f"code: {code_note} | data: {data_note}"


def build_output_rows(
    paper: PaperRecord,
    code_decision: ConsensusDecision,
    data_decision: ConsensusDecision,
) -> tuple[dict[str, object], dict[str, object], dict[str, object] | None]:
    review_required = code_decision.review_required or data_decision.review_required
    score = category_score(code_decision.label) + category_score(data_decision.label)
    code_note = code_decision.note or ""
    data_note = data_decision.note or ""
    combined_note = _combined_note(code_note, data_note)
    relevance_label = paper.metadata.get("relevance_label", "")
    relevance_confidence = paper.metadata.get("relevance_confidence", "")
    relevance_note = paper.metadata.get("relevance_note", "")
    relevance_review_required = paper.metadata.get("relevance_review_required", False)
    repro_audit_eligible = paper.metadata.get("repro_audit_eligible", paper.retrieval_status == "full_text")
    text_provider = paper.metadata.get("text_provider", "")
    analysis_text_source = paper.metadata.get(
        "analysis_text_source",
        "full_text" if paper.retrieval_status == "full_text" else "",
    )
    analysis_text_policy_passed = paper.metadata.get(
        "analysis_text_policy_passed",
        paper.retrieval_status == "full_text",
    )
    analysis_text_policy_note = paper.metadata.get(
        "analysis_text_policy_note",
        "Final labels were computed from extracted full paper text."
        if paper.retrieval_status == "full_text"
        else "",
    )
    data_named_public_benchmark = paper.metadata.get("data_named_public_benchmark", False)
    data_public_benchmark_name = paper.metadata.get("data_public_benchmark_name", "")
    data_public_benchmark_note = paper.metadata.get("data_public_benchmark_note", "")
    data_public_external_dataset = paper.metadata.get("data_public_external_dataset", False)
    data_public_external_dataset_type = paper.metadata.get("data_public_external_dataset_type", "")
    data_public_external_dataset_note = paper.metadata.get("data_public_external_dataset_note", "")
    review_required = (
        code_decision.review_required
        or data_decision.review_required
        or not analysis_text_policy_passed
    )
    result_row = {
        "paper_id": paper.paper_id,
        "source": paper.source,
        "year": paper.year,
        "track": paper.track,
        "title": paper.title,
        "article_url": paper.article_url,
        "doi": paper.doi or "",
        "retrieval_status": paper.retrieval_status,
        "phm_relevant": paper.phm_relevant,
        "relevance_label": relevance_label,
        "relevance_confidence": relevance_confidence,
        "relevance_note": relevance_note,
        "relevance_review_required": relevance_review_required,
        "repro_audit_eligible": repro_audit_eligible,
        "text_provider": text_provider,
        "analysis_text_source": analysis_text_source,
        "analysis_text_policy_passed": analysis_text_policy_passed,
        "analysis_text_policy_note": analysis_text_policy_note,
        "data_named_public_benchmark": data_named_public_benchmark,
        "data_public_benchmark_name": data_public_benchmark_name,
        "data_public_benchmark_note": data_public_benchmark_note,
        "data_public_external_dataset": data_public_external_dataset,
        "data_public_external_dataset_type": data_public_external_dataset_type,
        "data_public_external_dataset_note": data_public_external_dataset_note,
        "code_label": code_decision.label,
        "data_label": data_decision.label,
        "code_note": code_note,
        "data_note": data_note,
        "note": combined_note,
        "repro_score": score,
        "review_required": review_required,
    }
    trace_row = {
        **result_row,
        **_one_hot("code", code_decision.label),
        **_one_hot("data", data_decision.label),
        "code_confidence": code_decision.confidence,
        "data_confidence": data_decision.confidence,
        "code_reasons": json.dumps(code_decision.reasons),
        "data_reasons": json.dumps(data_decision.reasons),
        "code_vote_summary": code_decision.vote_summary(),
        "data_vote_summary": data_decision.vote_summary(),
        "code_note": code_note,
        "data_note": data_note,
        "note": combined_note,
        "code_supporting_urls": json.dumps(code_decision.supporting_urls),
        "data_supporting_urls": json.dumps(data_decision.supporting_urls),
        "relevance_label": relevance_label,
        "relevance_confidence": relevance_confidence,
        "relevance_note": relevance_note,
        "relevance_review_required": relevance_review_required,
        "repro_audit_eligible": repro_audit_eligible,
        "text_provider": text_provider,
        "analysis_text_source": analysis_text_source,
        "analysis_text_policy_passed": analysis_text_policy_passed,
        "analysis_text_policy_note": analysis_text_policy_note,
        "data_named_public_benchmark": data_named_public_benchmark,
        "data_public_benchmark_name": data_public_benchmark_name,
        "data_public_benchmark_note": data_public_benchmark_note,
        "data_public_external_dataset": data_public_external_dataset,
        "data_public_external_dataset_type": data_public_external_dataset_type,
        "data_public_external_dataset_note": data_public_external_dataset_note,
        "relevance_reasons": json.dumps(paper.metadata.get("relevance_reasons", [])),
        "relevance_intro_excerpt": paper.metadata.get("relevance_intro_excerpt", ""),
        "judge_vote_summary": " | ".join(
            filter(None, [code_decision.vote_summary(), data_decision.vote_summary()])
        ),
        "evidence_pointer": paper.metadata.get("evidence_pointer", ""),
        "main_urls": json.dumps([attachment.url for attachment in paper.attachments[:5]]),
    }
    review_row = None
    if review_required:
        review_row = {
            "paper_id": paper.paper_id,
            "source": paper.source,
            "year": paper.year,
            "title": paper.title,
            "code_label": code_decision.label,
            "data_label": data_decision.label,
            "reasons": json.dumps(
                {
                    "code": code_decision.reasons,
                    "data": data_decision.reasons,
                }
            ),
        }
    return result_row, trace_row, review_row
