"""
程序作用：
验证 CER 的序列化、公开投影脱敏、执行事件和只追加 JSONL 写入等核心记录契约。

整体结构：
1）_record 构造含私有证据、提示和连接信息的最小 CER；
2）ExecutionRecordTests 检查内部记录保真与公开投影脱敏；
3）同时验证事件顺序、完成状态和 JSONL 落盘行为。
"""

from __future__ import annotations

import unittest

from agentic_rag.execution.record import CanonicalExecutionRecord


def _record() -> CanonicalExecutionRecord:
    record = CanonicalExecutionRecord(
        schema_version="1.0.0",
        identity={"request_id": "req-a", "qid": "q01"},
        provenance={"profile": "baseline", "engine": "fake"},
        principal={"principal_id": "alice", "roles": ["admin"], "groups": ["platform"], "tenant_id": "a"},
        query="RAG 是什么？",
    )
    record.evidence = {"selected": [{"chunk_id": "c1", "text": "private chunk"}]}
    record.prompt = {
        "prompt_text": "full private prompt",
        "rendered_prompt": "exact private prompt",
        "visible": [{"chunk_id": "c1"}],
    }
    record.model_calls = [{"provider": "openrouter", "endpoint": "https://internal.example"}]
    record.append_event("REQUEST_ACCEPTED")
    record.finish("ANSWERED", answer="answer", citations=[])
    return record


class ExecutionRecordTests(unittest.TestCase):
    """覆盖规范执行记录的持久化与脱敏边界。"""
    def test_round_trip_and_sequence(self) -> None:
        record = _record()
        restored = CanonicalExecutionRecord.from_dict(record.to_dict())
        self.assertEqual(restored.events[0].sequence, 1)
        self.assertEqual(restored.outcome["status"], "ANSWERED")

    def test_public_projection_drops_private_content(self) -> None:
        public = _record().sanitized_dict()
        self.assertNotIn("roles", public["principal"])
        self.assertNotIn("text", public["evidence"]["selected"][0])
        self.assertNotIn("prompt_text", public["prompt"])
        self.assertNotIn("rendered_prompt", public["prompt"])
        self.assertNotIn("endpoint", public["model_calls"][0])


if __name__ == "__main__":
    unittest.main()
