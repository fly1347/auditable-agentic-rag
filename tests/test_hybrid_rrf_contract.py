"""作用：锁定公开默认 Hybrid RRF 的参数、分数语义与审计轨迹。"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agentic_rag.config import AppConfig
from agentic_rag.policy.access import anonymous_user_context
from agentic_rag.query_pipeline import _retrieve_once
from agentic_rag.retrieve.hybrid_rrf import HybridRRFRetriever
from agentic_rag.retrieve.retriever import RetrievalHit, RetrievalResult as DenseRetrievalResult
from agentic_rag.service.container import RuntimeContainer
from agentic_rag.types import Chunk, RetrievalResult


class _FakeStore:
    def __init__(self) -> None:
        self.rows = [
            {"chunk_id": "c1", "source_id": "s1", "doc_hash": "h1", "text": "alpha", "offset_start": 0, "offset_end": 5, "metadata": {}},
            {"chunk_id": "c2", "source_id": "s2", "doc_hash": "h2", "text": "beta", "offset_start": 0, "offset_end": 4, "metadata": {}},
            {"chunk_id": "c3", "source_id": "s3", "doc_hash": "h3", "text": "gamma", "offset_start": 0, "offset_end": 5, "metadata": {}},
        ]

    def count(self) -> int:
        return len(self.rows)

    def sample(self, n: int):
        return list(self.rows[:n])


class _FakeDense:
    def __init__(self) -> None:
        self.store = _FakeStore()
        self.cfg = SimpleNamespace(topk=5)

    def run(self, query: str, topk: int, user_context=None) -> DenseRetrievalResult:
        hits = [
            RetrievalHit("c1", "s1", 0.9, "alpha", 0, 5, {}),
            RetrievalHit("c2", "s2", 0.8, "beta", 0, 4, {}),
            RetrievalHit("c3", "s3", 0.7, "gamma", 0, 5, {}),
        ][:topk]
        return DenseRetrievalResult(
            query=query,
            topk=topk,
            hits=hits,
            access_policy={
                "enforced_before_topk": True,
                "allowed_source_ids": ["s1", "s2", "s3"],
            },
        )


class _FakeBM25:
    def __init__(self, corpus) -> None:
        self.corpus = corpus

    def get_scores(self, tokens):
        return [0.1, 2.0, 0.5]


class HybridRRFContractTests(unittest.TestCase):
    def test_hybrid_rrf_returns_rrf_score_and_two_channel_trace(self) -> None:
        fake_jieba = types.ModuleType("jieba")
        fake_jieba.lcut = lambda text: [text]
        fake_rank_bm25 = types.ModuleType("rank_bm25")
        fake_rank_bm25.BM25Okapi = _FakeBM25

        with patch.dict(sys.modules, {"jieba": fake_jieba, "rank_bm25": fake_rank_bm25}):
            retriever = HybridRRFRetriever(
                _FakeDense(),
                dense_candidate_topk=10,
                bm25_candidate_topk=10,
                rrf_k=60,
            )
            result = retriever.run("beta", topk=2, user_context=anonymous_user_context())

        self.assertEqual(result.score_type, "rrf")
        self.assertEqual(len(result.chunks), 2)
        self.assertEqual(len(result.retrieval_events), 2)
        self.assertEqual([e["query_role"] for e in result.retrieval_events], ["dense_channel", "bm25_channel"])
        self.assertEqual(result.merge_trace["strategy"], "hybrid_dense_bm25_rrf")
        self.assertEqual(result.merge_trace["dense_candidate_topk"], 10)
        self.assertEqual(result.merge_trace["bm25_candidate_topk"], 10)
        self.assertEqual(result.merge_trace["rrf_k"], 60)

    def test_query_pipeline_keeps_hybrid_internal_trace(self) -> None:
        chunk = Chunk("c1", "s1", "h", "evidence", 0, 8, {})
        hybrid_result = RetrievalResult(
            query="q",
            chunks=[chunk],
            scores=[0.03],
            topk=1,
            timing_ms=1.0,
            retrieval_events=[{"query_role": "dense_channel"}, {"query_role": "bm25_channel"}],
            merge_trace={"strategy": "hybrid_dense_bm25_rrf"},
            score_type="rrf",
        )

        class _FakeHybrid:
            def run(self, query: str, topk: int, user_context=None):
                return hybrid_result

        result, _ = _retrieve_once(
            _FakeHybrid(),
            "q",
            1,
            user_context=anonymous_user_context(),
            round_id=1,
            query_role="original",
        )
        self.assertEqual(result.merge_trace["strategy"], "hybrid_dense_bm25_rrf")
        self.assertEqual(len(result.retrieval_events), 3)
        self.assertEqual(result.retrieval_events[0]["query_role"], "dense_channel")
        self.assertEqual(result.retrieval_events[1]["query_role"], "bm25_channel")

    def test_runtime_container_default_wraps_dense_with_fixed_hybrid_rrf(self) -> None:
        dense = object()
        hybrid = object()
        with (
            patch("agentic_rag.service.container.resolve_vector_store_dir", return_value=Path("artifacts/vector_store")),
            patch("agentic_rag.retrieve.retriever.Retriever", return_value=dense) as dense_cls,
            patch("agentic_rag.retrieve.hybrid_rrf.HybridRRFRetriever", return_value=hybrid) as hybrid_cls,
        ):
            container = RuntimeContainer(AppConfig())
            actual = container.get_retriever()

        self.assertIs(actual, hybrid)
        self.assertEqual(dense_cls.call_count, 1)
        hybrid_cls.assert_called_once_with(
            dense,
            dense_candidate_topk=10,
            bm25_candidate_topk=10,
            rrf_k=60,
        )


if __name__ == "__main__":
    unittest.main()
