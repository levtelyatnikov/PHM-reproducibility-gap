from __future__ import annotations

import unittest

from engine.evidence import extract_evidence_hits


class EvidenceTests(unittest.TestCase):
    def test_extracts_url_and_ownership_cue_from_text(self) -> None:
        text = "We release our code at our repository: https://github.com/example/repo."
        hits = extract_evidence_hits(text, kind="code")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].url, "https://github.com/example/repo")
        self.assertTrue(hits[0].ownership_cue)
        self.assertTrue(hits[0].is_public_artifact)

    def test_extracts_restricted_cue_without_url(self) -> None:
        text = "The dataset is available on request due to NDA restrictions."
        hits = extract_evidence_hits(text, kind="data")
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0].restricted_cue)
        self.assertFalse(hits[0].is_public_artifact)


if __name__ == "__main__":
    unittest.main()

