from __future__ import annotations

import unittest

from engine.rows import build_audit_result_row, build_audit_trace_row
from engine.types import ChannelClassification, PaperRecord, PaperAuditResult


class TraceRowTests(unittest.TestCase):
    def test_trace_row_contains_one_hot_flags(self) -> None:
        paper = PaperRecord(
            paper_id="p4",
            source="phm",
            year=2022,
            track="technical",
            title="Test Paper",
            authors=("A. Author",),
            doi=None,
            article_url="https://example.com/paper",
            pdf_url=None,
            retrieval_status="full_text",
            phm_relevant=True,
        )
        code = ChannelClassification(label="A1", confidence=0.95, reasons=("ownership",), evidence_urls=("u1",))
        data = ChannelClassification(label="A4", confidence=0.2, reasons=("missing",), evidence_urls=())
        result = PaperAuditResult(
            paper=paper,
            code=code,
            data=data,
            repro_score=5,
            review_required=True,
            consensus_reason="split_vote",
            judge_votes={"code": ["A1", "A2", "A1"], "data": ["A4", "A4", "A5"]},
        )
        row = build_audit_trace_row(result)
        self.assertEqual(row["code_a1"], 1)
        self.assertEqual(row["code_a4"], 0)
        self.assertEqual(row["data_a4"], 1)
        self.assertEqual(row["review_required"], True)

    def test_result_row_contains_core_summary_fields(self) -> None:
        paper = PaperRecord(
            paper_id="p5",
            source="phm",
            year=2022,
            track="technical",
            title="Test Paper",
            authors=("A. Author",),
            doi=None,
            article_url="https://example.com/paper",
            pdf_url=None,
            retrieval_status="full_text",
            phm_relevant=True,
        )
        code = ChannelClassification(label="A2", confidence=0.8, reasons=("claim",), evidence_urls=())
        data = ChannelClassification(label="A5", confidence=0.1, reasons=("none",), evidence_urls=())
        result = PaperAuditResult(
            paper=paper,
            code=code,
            data=data,
            repro_score=3,
            review_required=False,
            consensus_reason="majority",
            judge_votes={"code": ["A2", "A2", "A3"], "data": ["A5", "A5", "A5"]},
        )
        row = build_audit_result_row(result)
        self.assertEqual(row["paper_id"], "p5")
        self.assertEqual(row["code_label"], "A2")
        self.assertEqual(row["data_label"], "A5")
        self.assertEqual(row["repro_score"], 3)


if __name__ == "__main__":
    unittest.main()

