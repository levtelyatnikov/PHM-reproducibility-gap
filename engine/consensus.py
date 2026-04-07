from __future__ import annotations

from collections import Counter, defaultdict

from shared.schemas import ConsensusDecision, JudgeVote


_CONSERVATIVE_ORDER = {"A1": 0, "A2": 1, "A3": 2, "A4": 3, "A5": 4}


def build_consensus(
    *,
    channel: str,
    deterministic_label: str,
    deterministic_confidence: float,
    deterministic_reasons: list[str],
    deterministic_note: str | None = None,
    deterministic_urls: list[str] | None = None,
    votes: list[JudgeVote],
) -> ConsensusDecision:
    counts = Counter(vote.label for vote in votes)
    grouped_confidence: dict[str, list[float]] = defaultdict(list)
    for vote in votes:
        grouped_confidence[vote.label].append(vote.confidence)
    majority_label, majority_count = counts.most_common(1)[0]
    majority_confidence = sum(grouped_confidence[majority_label]) / len(grouped_confidence[majority_label])

    review_required = False
    reasons = list(deterministic_reasons)
    final_label = deterministic_label
    final_confidence = deterministic_confidence

    a1_votes = counts.get("A1", 0)
    if deterministic_label != "A1" and a1_votes:
        review_required = True
        reasons.append("a1_disagreement")
    elif majority_count >= 2 and majority_label == deterministic_label:
        final_label = majority_label
        final_confidence = max(deterministic_confidence, majority_confidence)
    elif majority_count >= 2 and majority_label != "A1" and deterministic_label != "A1":
        final_label = majority_label if majority_confidence >= deterministic_confidence else deterministic_label
        final_confidence = max(deterministic_confidence, majority_confidence)
        review_required = majority_label != deterministic_label
    else:
        review_required = True
        final_label = max([deterministic_label, *counts.keys()], key=_CONSERVATIVE_ORDER.get)

    if final_label == "A1" and majority_confidence < 0.7:
        review_required = True
        reasons.append("low_confidence_a1")

    return ConsensusDecision(
        channel=channel,
        label=final_label,
        confidence=round(final_confidence, 3),
        reasons=reasons,
        votes=votes,
        note=deterministic_note if final_label != "A5" else deterministic_note,
        supporting_urls=list(deterministic_urls or []),
        review_required=review_required,
    )
