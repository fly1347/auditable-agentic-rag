# 安全基线

## 1. 安全目标

公开版提供可验证的工程安全基线：

- 身份只能来自可信接入层；
- 未登记 source 默认拒绝；
- 不可见证据不能进入 TopK、Prompt 或引用；
- 外发前检查身份权限、数据类别与 provider；
- 查询、日志和发布材料经过安全规则与脱敏检查；
- 安全决策进入 CER，便于审计和回放。

这些能力用于本地参考实现和合同验证，不替代企业 IAM、DLP、SIEM 或合规审计。

## 2. 可信身份

API 使用静态 token adapter 将 token 映射为 `Principal`。roles、groups、tenant 和 `public_egress` 能力来自服务端配置，不能由请求 JSON 自行声明。

公开样例包含四类身份语义：

| 身份 | 典型权限 |
| :-- | :-- |
| public | 读取公开 source，可按配置获得公共云外发能力 |
| engineer | 读取 public 与 platform 工程资料 |
| analyst | 读取 public 与分析资料 |
| admin | 管理和诊断权限；外发能力仍按显式策略检查 |

静态 token 适合 localhost 演示。对外暴露服务前必须更换示例 token，并使用反向代理、TLS 和正式身份系统。

## 3. Source ACL

`policy/source_acl.yaml` 是 source-level 权限登记册，采用 `default_behavior: deny`。

公开 sample sources：

| source_id | visibility | 允许角色/组 |
| :-- | :-- | :-- |
| `public_rag.md` | public | 所有身份 |
| `internal_platform.md` | internal_demo | engineer/admin，platform/admin |
| `analyst_note.md` | internal_demo | analyst/admin，product/admin |

Loader 使用相对路径生成稳定 `source_id`，索引前从 Registry 注入 ACL。新文档未登记、source_id 不匹配或 ACL 字段非法时，索引构建失败。

Retriever 在 TopK 前过滤 ACL 与 tenant。这样不可见 chunk 不会参与最终排序、证据选择、Prompt 或引用。

## 4. 数据出境控制

每次 provider attempt 都独立执行 egress 检查，主要依据：

- Principal 是否具有相应外发能力；
- evidence visibility 与数据类别；
- provider 是否属于配置允许范围；
- public / restricted cloud policy；
- 运行预算与调用次数限制。

公开配置允许 public evidence 发往配置的公共云 provider，restricted evidence 默认不允许外发。`fallback_chain: []`，不会在失败时静默切换到另一条模型路径。

## 5. Query Safety 与 Prompt Injection

查询安全检查在检索和模型调用前执行，可直接拒绝明显危险输入。Prompt 模板要求把检索正文视为不可信证据，不执行文档中的指令。

`sample_data/security_cases/malicious_prompt_injection_demo.md.disabled` 默认禁用，不进入语料索引，用于说明文档级间接注入边界。

当前 Query Safety、Prompt Injection 和 redaction 主要依赖规则与固定负控，不能覆盖全部语言变体、编码绕过、间接注入和工具攻击。

## 6. CER、日志与脱敏

CER 记录 Principal 投影、policy decisions、egress decisions、retrieval/evidence/prompt lineage、模型调用、时延、usage、outcome 和 errors。

公开发布不包含：

- raw CER 与完整 prompt-visible evidence；
- provider secret、真实 `.env` 与备份；
- raw query/audit/service logs；
- 完整私有语料、向量与模型缓存；
- experiments、过程稿和历史 Git 工作现场。

发布扫描负责检查密钥形态、私有路径、备份文件、raw logs 和超范围 artifacts。规则扫描后仍需人工抽查新增字段、答案、错误信息和文档链接。

## 7. 安全验证

离线安全入口：

```bash
PYTHONPATH=src:. python eval/run_security_smoke.py \
  --output-dir artifacts/security-smoke
```

公开仓库另外保留 4 个核心治理与审计 contract test 文件（当前 11 条测试），验证 source registry、provider egress、audit projection 与 CER 不变量。完整发布门禁包括：

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -q
python scripts/release_scan.py .
```

当前 offline security smoke 为 16 条断言，直接覆盖 identity、authentication、admin、query safety、prompt injection、tenant ACL、egress、redaction 与公开 CER sanitization。

这些命令不会自动授权 provider 调用。在线评测必须同时显式允许模型调用和相应数据出境确认。

## 8. 当前边界

- 静态 token 不是 OIDC/OAuth2 或企业 IdP；
- tenant isolation 主要由合成负控验证；
- JSONL 审计适合单进程本地运行；
- 未接密钥轮换、撤销后台、集中式审计、DLP 与 SIEM；
- 安全能力属于工程基线，不构成生产合规声明。
