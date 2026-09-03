"""作用：锁定 structured sufficiency 非法 JSON 的显式失败与单次格式重试行为。"""

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
    def test_extract_json_object_rejects_malformed_json(self) -> None:
        with self.assertRaises(SufficiencyJudgeOutputParseError):
            _extract_json_object('{"verdict" "SUFFICIENT"}')

    def test_retry_once_when_first_output_is_malformed(self) -> None:
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
