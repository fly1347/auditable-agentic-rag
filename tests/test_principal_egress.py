"""
程序作用：
验证可信身份解析和数据出站策略，确保角色、用户组、租户与公开出站能力不能由请求方伪造。

整体结构：
1）构造静态 token 身份配置与不同敏感级别数据；
2）检查匿名、本地 CLI、评估和 API token 身份边界；
3）断言允许、拒绝与请求级出站上下文均按策略执行。
"""

from __future__ import annotations

import json
import unittest

from agentic_rag.config import AuthConfig, EgressConfig
from agentic_rag.policy.egress import (
    EgressDenied,
    assess_provider_egress,
    authorize_provider_attempt,
    egress_scope,
)
from agentic_rag.policy.principal import (
    AuthenticationRequired,
    StaticTokenAuthAdapter,
    eval_principal,
    local_cli_principal,
)


class PrincipalAndEgressTests(unittest.TestCase):
    """覆盖身份可信边界与模型服务出站权限。"""
    def test_static_token_resolves_trusted_principal(self) -> None:
        raw = json.dumps(
            {
                "long-demo-token": {
                    "principal_id": "alice",
                    "roles": ["engineer"],
                    "groups": ["platform"],
                    "tenant_id": "tenant-a",
                }
            }
        )
        adapter = StaticTokenAuthAdapter(AuthConfig(), raw_json=raw)
        principal = adapter.resolve("long-demo-token")
        self.assertEqual(principal.principal_id, "alice")
        self.assertIn("engineer", principal.roles)
        with self.assertRaises(AuthenticationRequired):
            adapter.resolve("wrong-demo-token")

    def test_egress_rechecks_provider_and_sensitivity(self) -> None:
        config = EgressConfig()
        self.assertTrue(assess_provider_egress("openrouter", ["public"], config).allowed)
        self.assertFalse(
            assess_provider_egress("openrouter", ["internal_demo"], config).allowed
        )
        self.assertTrue(
            assess_provider_egress("ollama", ["internal_demo"], config).allowed
        )
        self.assertFalse(assess_provider_egress("unknown-cloud", ["public"], config).allowed)

    def test_request_scope_records_each_allowed_and_denied_attempt(self) -> None:
        events = []
        with egress_scope(
            EgressConfig(),
            default_visibilities=("public",),
            recorder=events.append,
        ):
            authorize_provider_attempt("openrouter", stage="rewrite", attempt=1)
            with self.assertRaises(EgressDenied):
                authorize_provider_attempt(
                    "openrouter",
                    stage="generator",
                    attempt=1,
                    visibilities=("internal_demo",),
                )
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]["allowed"])
        self.assertFalse(events[1]["allowed"])
        self.assertEqual(events[1]["sensitivity"], "restricted")

    def test_trusted_cli_and_eval_grant_explicit_public_egress(self) -> None:
        self.assertIn("public_egress", local_cli_principal().roles)
        self.assertIn("public_egress", eval_principal().roles)
        self.assertNotEqual({"admin"}, local_cli_principal().roles)


if __name__ == "__main__":
    unittest.main()
