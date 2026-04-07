from __future__ import annotations

import unittest

from shared.schemas import (
    AuditTraceRecord,
    ClassificationRecord,
    JudgeVoteRecord,
    PaperRecord,
)


class SchemaTests(unittest.TestCase):
    def test_paper_record_to_dict_is_json_safe(self) -> None:
        record = PaperRecord(
            paper_id="p1",
            source="phm",
            year=2022,
            track="technical",
            title="A Study",
            authors=["Ada Lovelace"],
            doi=None,
            article_url="https://example.com",
            pdf_url=None,
            retrieval_status="ok",
            phm_relevant=True,
        )
        payload = record.to_dict()
        self.assertEqual(payload["authors"], ["Ada Lovelace"])
        self.assertTrue(payload["phm_relevant"])

    def test_audit_trace_contains_one_hot_flags(self) -> None:
        vote = JudgeVoteRecord(
            model_name="gpt-4o-mini",
            channel="code",
            label="A1",
            confidence=0.9,
            rationale="direct repository link",
            evidence_ids=["e1"],
        )
        trace = AuditTraceRecord(
            paper_id="p1",
            source="phm",
            year=2022,
            track="technical",
            title="A Study",
            code_label="A1",
            data_label="A5",
            code_a1=True,
            code_a2=False,
            code_a3=False,
            code_a4=False,
            code_a5=False,
            data_a1=False,
            data_a2=False,
            data_a3=False,
            data_a4=False,
            data_a5=True,
            judge_votes=[vote],
            main_urls=["https://example.com/repo"],
            retrieval_status="full_text",
        )
        payload = trace.to_dict()
        self.assertTrue(payload["code_a1"])
        self.assertTrue(payload["data_a5"])
        self.assertEqual(payload["judge_votes"][0]["model_name"], "gpt-4o-mini")

    def test_classification_record_defaults_are_safe(self) -> None:
        record = ClassificationRecord(
            paper_id="p1",
            code_label="A2",
            data_label="A5",
        )
        self.assertEqual(record.code_evidence, [])
        self.assertFalse(record.review_required)


if __name__ == "__main__":
    unittest.main()

