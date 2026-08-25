# 平台运行说明

平台版 RAG 服务包含 FastAPI 后端与 Streamlit UI。API 提供健康检查、版本、指标、问答及调试入口；Docker Compose 将 API 与 UI 作为独立服务运行。

平台团队通过健康检查、指标、结构化日志和 smoke test 判断部署状态。公开版以 Docker Compose 作为主要可复现运行方式，云平台部署保留为架构说明。

本文档代表平台工程资料，仅 engineer 与 admin 可见。
