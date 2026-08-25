# 公开示例数据

本目录提供公开版最小演示语料，内容均为本项目编写的模拟材料，不摘录私有语料或外部文章。

## 语料

- `public_rag.md`：公开知识，所有身份可见。
- `public_rag_workflow.md`：公开 RAG 流程补充证据，所有身份可见。
- `internal_platform.md`：平台工程资料，仅 engineer 与 admin 可见。
- `analyst_note.md`：评测分析资料，仅 analyst 与 admin 可见。

权限由 `policy/source_acl.yaml` 按 `source_id` 注入，不从 Markdown 正文解析。

## 安全样例

`security_cases/malicious_prompt_injection_demo.md.disabled` 默认禁用，不进入语料索引，仅作为安全边界说明与后续测试材料。

## 许可

示例内容随本仓库许可证发布；最终许可口径以仓库根目录 `LICENSE` 为准。
