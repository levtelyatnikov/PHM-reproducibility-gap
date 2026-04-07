from engine.consensus import build_consensus
from engine.scoring import build_output_rows, category_score
from shared.schemas import JudgeVote, PaperRecord


def make_vote(label: str, confidence: float = 0.9) -> JudgeVote:
    return JudgeVote(
        model="test-model",
        channel="code",
        label=label,
        confidence=confidence,
        rationale=f"assigned {label}",
    )


def make_paper() -> PaperRecord:
    return PaperRecord(
        paper_id="phm-2022-3144",
        source="phm",
        year=2022,
        track="Technical Research Papers",
        title="A Dataset for Fault Classification in Rock Drills",
        authors=["Jane Doe", "John Roe"],
        article_url="https://papers.phmsociety.org/index.php/phmconf/article/view/3144",
        doi="10.36001/phmconf.2022.v14i1.3144",
        article_id="3144",
    )


def test_consensus_accepts_majority_vote() -> None:
    decision = build_consensus(
        channel="code",
        deterministic_label="A1",
        deterministic_confidence=0.85,
        deterministic_reasons=["ownership_link"],
        votes=[make_vote("A1"), make_vote("A1"), make_vote("A2")],
    )

    assert decision.label == "A1"
    assert not decision.review_required


def test_consensus_routes_borderline_a1_for_review() -> None:
    decision = build_consensus(
        channel="data",
        deterministic_label="A2",
        deterministic_confidence=0.45,
        deterministic_reasons=["ambiguous_public_claim"],
        votes=[
            JudgeVote(model="m1", channel="data", label="A1", confidence=0.55, rationale="weak"),
            JudgeVote(model="m2", channel="data", label="A2", confidence=0.70, rationale="claim only"),
            JudgeVote(model="m3", channel="data", label="A1", confidence=0.52, rationale="weak"),
        ],
    )

    assert decision.label == "A2"
    assert decision.review_required


def test_output_rows_include_one_hot_trace_flags() -> None:
    paper = make_paper()
    paper.retrieval_status = "full_text"
    code_decision = build_consensus(
        channel="code",
        deterministic_label="A1",
        deterministic_confidence=0.85,
        deterministic_reasons=["ownership_link"],
        votes=[make_vote("A1"), make_vote("A1"), make_vote("A1")],
    )
    data_decision = build_consensus(
        channel="data",
        deterministic_label="A3",
        deterministic_confidence=0.90,
        deterministic_reasons=["available_on_request"],
        votes=[
            JudgeVote(model="m1", channel="data", label="A3", confidence=0.9, rationale="request"),
            JudgeVote(model="m2", channel="data", label="A3", confidence=0.8, rationale="request"),
            JudgeVote(model="m3", channel="data", label="A3", confidence=0.85, rationale="request"),
        ],
    )

    result_row, trace_row, review_row = build_output_rows(paper, code_decision, data_decision)

    assert result_row["code_label"] == "A1"
    assert result_row["data_label"] == "A3"
    assert result_row["repro_score"] == category_score("A1") + category_score("A3")
    assert trace_row["code_a1"] == 1
    assert trace_row["code_a5"] == 0
    assert trace_row["data_a3"] == 1
    assert review_row is None


def test_output_rows_include_reproducibility_eligibility_fields() -> None:
    paper = make_paper()
    paper.retrieval_status = "metadata_only"
    paper.metadata["repro_audit_eligible"] = False
    paper.metadata["text_provider"] = "missing"
    paper.metadata["analysis_text_source"] = "missing_full_text"
    paper.metadata["analysis_text_policy_passed"] = False
    paper.metadata["analysis_text_policy_note"] = "No usable extracted full paper text was available."
    code_decision = build_consensus(
        channel="code",
        deterministic_label="A5",
        deterministic_confidence=0.90,
        deterministic_reasons=["not_mentioned"],
        votes=[make_vote("A5"), make_vote("A5"), make_vote("A5")],
    )
    data_decision = build_consensus(
        channel="data",
        deterministic_label="A5",
        deterministic_confidence=0.90,
        deterministic_reasons=["not_mentioned"],
        votes=[
            JudgeVote(model="m1", channel="data", label="A5", confidence=0.9, rationale="none"),
            JudgeVote(model="m2", channel="data", label="A5", confidence=0.8, rationale="none"),
            JudgeVote(model="m3", channel="data", label="A5", confidence=0.85, rationale="none"),
        ],
    )

    result_row, trace_row, _ = build_output_rows(paper, code_decision, data_decision)

    assert result_row["repro_audit_eligible"] is False
    assert result_row["text_provider"] == "missing"
    assert result_row["analysis_text_policy_passed"] is False
    assert trace_row["repro_audit_eligible"] is False
    assert trace_row["text_provider"] == "missing"
    assert trace_row["analysis_text_source"] == "missing_full_text"


def test_output_rows_include_public_benchmark_fields() -> None:
    paper = make_paper()
    paper.metadata["data_named_public_benchmark"] = True
    paper.metadata["data_public_benchmark_name"] = "C-MAPSS"
    paper.metadata["data_public_benchmark_note"] = "We evaluate the approach on the C-MAPSS dataset."
    code_decision = build_consensus(
        channel="code",
        deterministic_label="A5",
        deterministic_confidence=0.90,
        deterministic_reasons=["not_mentioned"],
        votes=[make_vote("A5"), make_vote("A5"), make_vote("A5")],
    )
    data_decision = build_consensus(
        channel="data",
        deterministic_label="A5",
        deterministic_confidence=0.90,
        deterministic_reasons=["not_mentioned"],
        votes=[
            JudgeVote(model="m1", channel="data", label="A5", confidence=0.9, rationale="none"),
            JudgeVote(model="m2", channel="data", label="A5", confidence=0.8, rationale="none"),
            JudgeVote(model="m3", channel="data", label="A5", confidence=0.85, rationale="none"),
        ],
    )

    result_row, trace_row, _ = build_output_rows(paper, code_decision, data_decision)

    assert result_row["data_named_public_benchmark"] is True
    assert result_row["data_public_benchmark_name"] == "C-MAPSS"
    assert trace_row["data_public_benchmark_note"].startswith("We evaluate the approach")
