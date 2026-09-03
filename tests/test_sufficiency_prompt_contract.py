"""
程序作用：
验证 structured sufficiency Prompt 只包含 Judge 所需的证据内容，不泄露检索分数与审计统计。

整体结构：
1）构造同时包含证据正文、检索分数和 score_summary 的 EvidencePacket；
2）调用 _format_evidence_packet_for_prompt 生成 Judge Prompt；
3）断言证据正文保留，同时 vector / RRF / rerank 分数及汇总统计均未进入 Prompt。
"""

from __future__ import annotations

import unittest

from agentic_rag.control.sufficiency import _format_evidence_packet_for_prompt
from agentic_rag.workflow.workflow_state import EvidenceItem, EvidencePacket


class SufficiencyPromptContractTests(unittest.TestCase):
    """覆盖 structured sufficiency Prompt 的证据暴露边界。"""

    def test_retrieval_scores_are_audit_only_and_not_sent_to_judge(self) -> None:
        """验证检索分数仅用于排序与审计，不发送给 sufficiency judge。"""
        packet = EvidencePacket(
            items=[
                EvidenceItem(
                    chunk_id="chunk-1",
                    source_id="source-1",
                    section_path="section",
                    text_preview="answer-bearing evidence",
                    vector_score=0.77,
                    rrf_score=0.0327868852,
                    rerank_score=0.91,
                    retrieval_query="query",
                    in_prompt=True,
                )
            ],
            score_summary={
                "vector_score_count": 1,
                "vector_score_min": 0.77,
                "rrf_score_count": 1,
                "rrf_score_min": 0.0327868852,
            },
        )

        prompt = _format_evidence_packet_for_prompt(packet)

        self.assertIn("chunk-1", prompt)
        self.assertIn("answer-bearing evidence", prompt)
        self.assertNotIn("vector_score", prompt)
        self.assertNotIn("rrf_score", prompt)
        self.assertNotIn("rerank_score", prompt)
        self.assertNotIn("score_summary", prompt)
        self.assertNotIn("0.77", prompt)
        self.assertNotIn("0.0327868852", prompt)
        self.assertNotIn("0.91", prompt)


if __name__ == "__main__":
    unittest.main()
