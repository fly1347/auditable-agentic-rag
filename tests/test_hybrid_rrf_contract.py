"""
程序作用：
锁定公开默认 Hybrid RRF 的固定参数、RRF 分数语义及 Dense / BM25 双通道审计轨迹。

整体结构：
1）用轻量替身构造 Dense、BM25 与本地 store；
2）验证 HybridRRFRetriever 的融合结果、内部 retrieval events 与 merge trace；
3）验证 query pipeline 保留 Hybrid 内部轨迹；
4）验证 RuntimeContainer 默认按固定参数封装 Dense 为 Hybrid RRF。
"""

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
    """提供 Hybrid RRF 合同测试所需的最小语料存储替身。"""

    def __init__(self) -> None:
        """初始化固定的三条测试语料。"""
        self.rows = [
            {"chunk_id": "c1", "source_id": "s1", "doc_hash": "h1", "text": "alpha", "offset_start": 0, "offset_end": 5, "metadata": {}},
            {"chunk_id": "c2", "source_id": "s2", "doc_hash": "h2", "text": "beta", "offset_start": 0, "offset_end": 4, "metadata": {}},
            {"chunk_id": "c3", "source_id": "s3", "doc_hash": "h3", "text": "gamma", "offset_start": 0, "offset_end": 5, "metadata": {}},
        ]

    def count(self) -> int:
        """返回测试语料条数。"""
        return len(self.rows)

    def sample(self, n: int):
        """按请求数量返回固定语料样本。"""
        return list(self.rows[:n])


class _FakeDense:
    """提供固定 Dense 排序结果，隔离真实向量检索依赖。"""

    def __init__(self) -> None:
        """初始化测试 store 与默认 TopK 配置。"""
        self.store = _FakeStore()
        self.cfg = SimpleNamespace(topk=5)

    def run(self, query: str, topk: int, user_context=None) -> DenseRetrievalResult:
        """返回固定 Dense hits 与 TopK 前权限已生效的访问策略。"""
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
    """提供固定 BM25 分数，验证双通道融合排序。"""

    def __init__(self, corpus) -> None:
        """保存 Hybrid retriever 传入的测试语料。"""
        self.corpus = corpus

    def get_scores(self, tokens):
        """返回固定 BM25 分数序列。"""
        return [0.1, 2.0, 0.5]


class HybridRRFContractTests(unittest.TestCase):
    """覆盖公开默认 Hybrid RRF 的参数、轨迹与容器装配契约。"""

    def test_hybrid_rrf_returns_rrf_score_and_two_channel_trace(self) -> None:
        """验证 Hybrid 返回 RRF 分数并保留 Dense / BM25 双通道轨迹。"""
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
        """验证 query pipeline 不丢失 Hybrid 内部 retrieval events 与 merge trace。"""
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
            """向 query pipeline 返回固定 Hybrid 结果。"""

            def run(self, query: str, topk: int, user_context=None):
                """返回预置的 Hybrid retrieval result。"""
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
        """验证 RuntimeContainer 使用固定公开参数装配默认 Hybrid RRF。"""
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
