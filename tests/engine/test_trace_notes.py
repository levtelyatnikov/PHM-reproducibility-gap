from engine.consensus import build_consensus
from engine.scoring import build_output_rows
from shared.schemas import JudgeVote, PaperRecord


def test_trace_rows_include_explicit_code_and_data_notes() -> None:
    paper = PaperRecord(
        paper_id="phm-2022-3304",
        source="phm",
        year=2022,
        track="Technical Research Papers",
        title="Developing Deep Learning Models for System Remaining Useful Life Predictions",
        authors=["Timothy Darrah"],
        article_url="https://papers.phmsociety.org/index.php/phmconf/article/view/3304",
        doi="10.36001/phmconf.2022.v14i1.3304",
        metadata={
            "data_named_public_benchmark": True,
            "data_public_benchmark_name": "C-MAPSS",
            "data_public_benchmark_note": "We evaluate the approach on the C-MAPSS dataset.",
            "data_public_external_dataset": True,
            "data_public_external_dataset_type": "named_benchmark",
            "data_public_external_dataset_note": "We evaluate the approach on the C-MAPSS dataset.",
        },
    )
    code = build_consensus(
        channel="code",
        deterministic_label="A1",
        deterministic_confidence=0.95,
        deterministic_reasons=["ownership_link"],
        deterministic_note="A pre-release version of the framework is available at https://github.com/darrahts/data",
        deterministic_urls=["https://github.com/darrahts/data"],
        votes=[
            JudgeVote(model="m1", channel="code", label="A1", confidence=0.9, rationale="owned repo"),
            JudgeVote(model="m2", channel="code", label="A1", confidence=0.8, rationale="owned repo"),
            JudgeVote(model="m3", channel="code", label="A1", confidence=0.85, rationale="owned repo"),
        ],
    )
    data = build_consensus(
        channel="data",
        deterministic_label="A5",
        deterministic_confidence=0.8,
        deterministic_reasons=["not_mentioned"],
        deterministic_note=None,
        deterministic_urls=[],
        votes=[
            JudgeVote(model="m1", channel="data", label="A5", confidence=0.8, rationale="none"),
            JudgeVote(model="m2", channel="data", label="A5", confidence=0.75, rationale="none"),
            JudgeVote(model="m3", channel="data", label="A5", confidence=0.7, rationale="none"),
        ],
    )

    _, trace_row, _ = build_output_rows(paper, code, data)

    assert trace_row["note"].startswith("A pre-release version of the framework is available at")
    assert trace_row["code_note"].startswith("A pre-release version of the framework is available at")
    assert trace_row["data_note"] == ""
    assert trace_row["data_named_public_benchmark"] is True
    assert trace_row["data_public_benchmark_name"] == "C-MAPSS"
    assert trace_row["data_public_external_dataset"] is True
    assert trace_row["data_public_external_dataset_type"] == "named_benchmark"
