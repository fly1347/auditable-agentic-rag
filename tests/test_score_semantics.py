from __future__ import annotations

import unittest

from agentic_rag.evidence.packet import build_evidence_packet
from agentic_rag.execution.snapshots import build_evidence_snapshot
from agentic_rag.types import Chunk, RetrievalResult


def _chunk() -> Chunk:
    return Chunk(
        chunk_id="c1", source_id="s1", doc_hash="h", text="evidence",
        offset_start=0, offset_end=8, metadata={}
    )


class ScoreSemanticsTests(unittest.TestCase):
    def test_dense_score_stays_vector_score(self) -> None:
        rr = RetrievalResult(query="q", chunks=[_chunk()], scores=[0.77], topk=1, timing_ms=1.0, score_type="vector_similarity")
        packet = build_evidence_packet(rr)
        self.assertEqual(packet.items[0].vector_score, 0.77)
        self.assertIsNone(packet.items[0].rrf_score)
        self.assertEqual(packet.score_summary["vector_score_count"], 1)
        self.assertEqual(packet.score_summary["rrf_score_count"], 0)

    def test_rrf_score_is_not_mislabeled_as_vector_score(self) -> None:
        rr = RetrievalResult(query="q", chunks=[_chunk()], scores=[0.0327868852], topk=1, timing_ms=1.0, score_type="rrf")
        packet = build_evidence_packet(rr)
        self.assertIsNone(packet.items[0].vector_score)
        self.assertEqual(packet.items[0].rrf_score, 0.0327868852)
        self.assertEqual(packet.score_summary["vector_score_count"], 0)
        self.assertEqual(packet.score_summary["rrf_score_count"], 1)
        snap = build_evidence_snapshot(rr)
        self.assertEqual(snap["score_type"], "rrf")
        self.assertEqual(snap["evidence_selected"][0]["score_type"], "rrf")


if __name__ == "__main__":
    unittest.main()
