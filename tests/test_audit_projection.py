"""
程序作用：
验证调试响应投影到审计记录时，查询哈希严格来自 CER 中的规范查询文本。

整体结构：
1）构造包含最小执行事实的调试响应替身；
2）调用 build_audit_record_from_debug_response；
3）断言生成的 query_hash 与 CER 查询文本哈希一致。
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from agentic_rag.audit.record import build_audit_record_from_debug_response, hash_text


class AuditProjectionTests(unittest.TestCase):
    """覆盖调试响应到审计记录的关键投影契约。"""
    def test_query_hash_comes_from_canonical_execution_record(self) -> None:
        response = SimpleNamespace(
            request_id="r",
            execution_record={"query": "exact query"},
            workflow_trace={"route": {}},
            policy_trace={},
            generation_context={},
            usage={},
            timing={},
            citations=[],
            refused=False,
            refused_reason=None,
        )
        record = build_audit_record_from_debug_response(response)
        self.assertEqual(record.query_hash, hash_text("exact query"))


if __name__ == "__main__":
    unittest.main()
