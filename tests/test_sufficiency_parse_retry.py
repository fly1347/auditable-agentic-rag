"""
程序作用：
验证 structured sufficiency 遇到非法 JSON 时只做一次真实格式重试，并在持续失败时显式 fail-close。

整体结构：
1）构造最小 ModelCallRecord 与 EvidencePacket；
2）验证 malformed JSON 会抛出 SufficiencyJudgeOutputParseError；
3）验证首次解析失败、第二次成功时只重试一次并保留重试调用事实；
4）验证连续两次解析失败时携带两次 provider call 并抛出类型化错误。
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agentic_rag.control.sufficiency import (
    SufficiencyJudgeOutputParseError,
    _extract_json_object,
    judge_sufficiency_with_evidence_packet,
)
from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import ModelCallRecord
from agentic_rag.workflow.workflow_state import EvidenceItem, EvidencePacket


def _call() -> ModelCallRecord:
    """构造 structured sufficiency 测试共用的最小模型调用记录。"""
    return ModelCallRecord(
        role="sufficiency_judge",
        identity=ModelIdentity(provider="deepseek", configured_model="deepseek-v4-flash"),
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        latency_ms=12.0,
        http_status=200,
    )


def _packet() -> EvidencePacket:
    """构造包含一条 Prompt-visible 证据的最小 EvidencePacket。"""
    return EvidencePacket(
        items=[
            EvidenceItem(
                chunk_id="c1",
                source_id="s1",
                text_preview="证据正文",
                visibility="public",
                in_prompt=True,
            )
        ]
    )


class StructuredSufficiencyParseRetryTests(unittest.TestCase):
    """覆盖 structured sufficiency JSON 解析、单次重试与显式失败契约。"""

    def test_extract_json_object_rejects_malformed_json(self) -> None:
        """验证 malformed JSON 会被解析层明确拒绝。"""
        with self.assertRaises(SufficiencyJudgeOutputParseError):
            _extract_json_object('{"verdict" "SUFFICIENT"}')

    def test_retry_once_when_first_output_is_malformed(self) -> None:
        """验证首次格式错误后仅重试一次，并记录恢复事实。"""
        first = _call()
        second = _call()
        responses = [
            ('{"verdict" "SUFFICIENT"}', first.identity, first),
            (
                '{"verdict":"SUFFICIENT","confidence":"high","missing_evidence":[],"supporting_evidence_ids":["c1"],"conflict_evidence_ids":[],"reason":"ok"}',
                second.identity,
                second,
            ),
        ]
        with patch("agentic_rag.control.sufficiency._call_structured_judge", side_effect=responses) as mocked:
            result, _, final_call = judge_sufficiency_with_evidence_packet(
                query="测试问题",
                evidence_packet=_packet(),
                route="DIRECT",
            )

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(result.verdict, "SUFFICIENT")
        retry_calls = list(getattr(final_call, "retry_model_calls", []) or [])
        self.assertEqual(len(retry_calls), 1)
        self.assertEqual(retry_calls[0].error_type, "structured_output_parse_error")
        self.assertTrue(getattr(final_call, "structured_output_retry_recovered", False))

    def test_second_malformed_output_raises_typed_error_with_both_calls(self) -> None:
        """验证第二次仍失败时抛出类型化错误并保留两次模型调用。"""
        first = _call()
        second = _call()
        responses = [
            ('{"verdict" "SUFFICIENT"}', first.identity, first),
            ('{"confidence" "high"}', second.identity, second),
        ]
        with patch("agentic_rag.control.sufficiency._call_structured_judge", side_effect=responses):
            with self.assertRaises(SufficiencyJudgeOutputParseError) as ctx:
                judge_sufficiency_with_evidence_packet(
                    query="测试问题",
                    evidence_packet=_packet(),
                    route="DIRECT",
                )

        self.assertEqual(len(ctx.exception.model_calls), 2)
        self.assertTrue(all(call.error_type == "structured_output_parse_error" for call in ctx.exception.model_calls))


if __name__ == "__main__":
    unittest.main()
