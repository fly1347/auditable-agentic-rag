"""
Phase C / Phase E Streamlit demo UI.

作用：
- 为已服务化的 Agentic RAG FastAPI 提供最小可演示 UI。
- 通过 HTTP 调用现有 API：documents / ingest / chat / debug / health / metrics。
- Phase E 补全段增加 demo user selector，用于直观展示 source-level ACL 差异。
- 不改动 RAG pipeline、router、rerank、sufficiency、prompt 等核心行为。

整体结构：
1. 全局配置、demo user context 与 HTTP helper
2. 通用渲染函数
3. Documents / Chat / Metrics / Debug 四个页面
4. Debug 页 ACL demo summary
5. main() 入口
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


DEFAULT_API_BASE_URL = os.getenv("AGENTIC_RAG_API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("AGENTIC_RAG_UI_TIMEOUT_SECONDS", "300"))


DEMO_IDENTITY_PRESETS: Dict[str, Dict[str, Optional[str]]] = {
    "public": {
        "label": "Public · public-only",
        "token": "demo-public-token",
    },
    "alice": {
        "label": "Alice · engineer / platform",
        "token": "demo-platform-token",
    },
    "bob": {
        "label": "Bob · analyst / product",
        "token": "demo-product-token",
    },
    "admin": {
        "label": "Admin · admin override",
        "token": "demo-admin-token",
    },
    "custom": {
        "label": "Custom token",
        "token": None,
    },
}

DEMO_USER_CONTEXTS: Dict[str, Dict[str, str]] = {
    "anonymous": {
        "label": "anonymous · public-only",
        "roles": "-",
        "groups": "-",
        "description": "只能看到 public evidence。",
    },
    "alice": {
        "label": "alice · engineer / platform",
        "roles": "engineer",
        "groups": "platform",
        "description": "可看到 platform internal_demo evidence。",
    },
    "bob": {
        "label": "bob · analyst / product",
        "roles": "analyst",
        "groups": "product",
        "description": "可看到 product internal_demo evidence；当前演示问题里通常接近 public-only。",
    },
    "admin": {
        "label": "admin · admin override",
        "roles": "admin",
        "groups": "*",
        "description": "管理员演示身份，可看全部 ACL 范围。",
    },
}


# ---------------------------------------------------------------------------
# HTTP 请求辅助函数
# ---------------------------------------------------------------------------


def _normalize_api_base_url(raw_url: str) -> str:
    """规范化 API base URL，避免末尾斜杠导致拼接异常。"""
    return raw_url.strip().rstrip("/")


def _api_url(path: str) -> str:
    """拼接完整 API URL。"""
    base_url = _normalize_api_base_url(st.session_state.get("api_base_url", DEFAULT_API_BASE_URL))
    return f"{base_url}{path}"


def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> Tuple[Optional[Any], Optional[str], Optional[requests.Response], float]:
    """统一 HTTP 请求封装，返回 data / error / response / elapsed_ms。"""
    started_at = time.perf_counter()
    try:
        api_token = str(st.session_state.get("api_token", "") or "").strip()
        headers = {"X-API-Key": api_token} if api_token else {}
        response = requests.request(
            method=method.upper(),
            url=_api_url(path),
            headers=headers,
            json=json_body,
            files=files,
            data=data,
            timeout=timeout,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload: Any = response.json()
        else:
            payload = response.text

        if response.status_code >= 400:
            return payload, f"HTTP {response.status_code}", response, elapsed_ms

        return payload, None, response, elapsed_ms

    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return None, f"请求超时：超过 {timeout:.0f}s 未返回", None, elapsed_ms
    except requests.exceptions.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return None, f"请求失败：{exc}", None, elapsed_ms


def get_json(path: str, *, timeout: float = 30) -> Tuple[Optional[Any], Optional[str], Optional[requests.Response], float]:
    """请求 GET 接口，并兼容返回 JSON 或纯文本。"""
    return _request("GET", path, timeout=timeout)


def post_json(path: str, payload: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str], Optional[requests.Response], float]:
    """向 POST 接口提交 JSON，并解析响应内容。"""
    return _request("POST", path, json_body=payload)


def _selected_demo_user_id() -> str:
    """返回当前 UI 选择的 Phase E demo user_id。"""
    user_id = str(st.session_state.get("demo_user_id", "anonymous"))
    return user_id if user_id in DEMO_USER_CONTEXTS else "anonymous"


def _build_chat_payload(query: str) -> Dict[str, Any]:
    """构造不含身份声明的 chat/debug 请求体。"""
    return {
        "query": query,
        "profile": str(st.session_state.get("execution_profile", "orchestrated")),
    }


def render_demo_user_context_selector() -> None:
    """选择本地 demo token；真实 principal 由 API 解析。"""
    st.header("Execution")

    preset_id = st.selectbox(
        "Demo identity",
        options=list(DEMO_IDENTITY_PRESETS),
        index=0,
        format_func=lambda item: str(
            DEMO_IDENTITY_PRESETS[item]["label"]
        ),
        key="demo_identity_preset",
        help="本地演示身份；选择项会切换对应的 API token。",
    )

    preset_token = str(
        DEMO_IDENTITY_PRESETS[preset_id].get("token") or ""
    )

    if preset_token:
        st.session_state["api_token"] = preset_token
    else:
        st.text_input(
            "API token",
            type="password",
            key="api_token",
            help="输入自定义 opaque token。",
        )

    st.selectbox(
        "Profile",
        options=["baseline", "orchestrated"],
        index=1,
        key="execution_profile",
        help="orchestrated 是终版主链；baseline 用于迁移对照。",
    )

    st.caption(
        "本地 demo 选择器会切换 API token；"
        "实际身份以 Debug 页的 Authenticated context 为准。"
    )


# ---------------------------------------------------------------------------
# 通用页面渲染辅助函数
# ---------------------------------------------------------------------------


def render_api_status() -> None:
    """侧边栏展示当前 API 地址与基础连通性。"""
    with st.sidebar:
        st.header("API")
        st.session_state["api_base_url"] = st.text_input(
            "FastAPI base URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
            help="默认读取 AGENTIC_RAG_API_BASE_URL；未设置时使用 http://localhost:8000",
        )

        if st.button("检查连接", width="stretch"):
            data, error, response, elapsed_ms = get_json("/health", timeout=10)
            if error:
                st.error(f"{error} · {elapsed_ms:.1f} ms")
                if data:
                    st.code(_to_pretty_json(data), language="json")
            else:
                status = _safe_get(data, "status", default="unknown")
                st.success(f"/health: {status} · {elapsed_ms:.1f} ms")
                request_id = response.headers.get("X-Request-ID") if response else None
                if request_id:
                    st.caption(f"X-Request-ID: {request_id}")

        st.divider()
        render_demo_user_context_selector()


def _to_pretty_json(value: Any) -> str:
    """将对象转换为便于阅读的 JSON 字符串。"""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _safe_get(data: Any, key: str, default: Any = None) -> Any:
    """从 dict 中安全取值。"""
    if isinstance(data, dict):
        return data.get(key, default)
    return default


def _first_present(data: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    """按候选字段顺序返回第一个存在值。"""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def render_response_meta(response: Optional[requests.Response], elapsed_ms: float, payload: Optional[Any] = None) -> None:
    """展示 request_id 与 UI 侧观测耗时。"""
    cols = st.columns(3)
    request_id = None
    if response is not None:
        request_id = response.headers.get("X-Request-ID")
    if not request_id and isinstance(payload, dict):
        request_id = payload.get("request_id")

    cols[0].metric("UI observed latency", f"{elapsed_ms:.1f} ms")
    cols[1].metric("HTTP status", str(response.status_code if response else "N/A"))
    cols[2].metric("request_id", request_id or "N/A")


def render_error(error: Optional[str], payload: Optional[Any] = None) -> None:
    """统一错误展示。"""
    if not error:
        return
    st.error(error)
    if payload is not None:
        st.code(_to_pretty_json(payload), language="json")


def render_citations(citations: Any, retrieved_chunks: Any = None) -> None:
    """展示 citations，并尽量关联 chunk preview。"""
    st.subheader("Citations")

    if not citations:
        st.info("本次响应没有返回 citations。")
        return

    if isinstance(citations, str):
        st.write(citations)
        return

    if not isinstance(citations, list):
        st.code(_to_pretty_json(citations), language="json")
        return

    chunk_by_id = _build_chunk_lookup(retrieved_chunks)

    for index, citation in enumerate(citations, start=1):
        label = f"Citation {index}"
        if isinstance(citation, dict):
            source_id = _first_present(citation, ["source_id", "doc_id", "document_id", "id"], "")
            title = _first_present(citation, ["title", "filename", "source", "path"], "")
            label = " · ".join([part for part in [str(source_id), str(title)] if part]) or label

        with st.expander(label, expanded=False):
            st.code(_to_pretty_json(citation), language="json")
            preview = _find_chunk_preview(citation, chunk_by_id)
            if preview:
                st.markdown("**Chunk preview**")
                st.write(preview)


def _build_chunk_lookup(retrieved_chunks: Any) -> Dict[str, Any]:
    """基于 retrieved_chunks 构建 id/source_id 到 chunk 的简单索引。"""
    lookup: Dict[str, Any] = {}
    if not isinstance(retrieved_chunks, list):
        return lookup

    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue
        for key in ("chunk_id", "id", "source_id", "doc_id", "document_id"):
            value = chunk.get(key)
            if value is not None:
                lookup[str(value)] = chunk
    return lookup


def _find_chunk_preview(citation: Any, chunk_by_id: Dict[str, Any]) -> Optional[str]:
    """尽量根据 citation 找到对应 chunk preview。"""
    if not isinstance(citation, dict):
        return None

    for key in ("chunk_id", "id", "source_id", "doc_id", "document_id"):
        value = citation.get(key)
        if value is not None and str(value) in chunk_by_id:
            chunk = chunk_by_id[str(value)]
            if isinstance(chunk, dict):
                return _first_present(chunk, ["preview", "text", "content", "chunk_text"], None)
            if isinstance(chunk, str):
                return chunk

    return _first_present(citation, ["preview", "text", "content", "chunk_text"], None)


def render_retrieved_chunks(retrieved_chunks: Any) -> None:
    """展示检索 chunk 简要信息。"""
    st.subheader("Retrieved chunks")

    if not retrieved_chunks:
        st.info("本次响应没有返回 retrieved_chunks。")
        return

    if not isinstance(retrieved_chunks, list):
        st.code(_to_pretty_json(retrieved_chunks), language="json")
        return

    for index, chunk in enumerate(retrieved_chunks, start=1):
        if isinstance(chunk, dict):
            title = _first_present(
                chunk,
                ["source_id", "doc_id", "document_id", "filename", "source", "path", "title"],
                f"chunk_{index}",
            )
            score = _first_present(chunk, ["score", "rerank_score", "similarity"], None)
            label = f"{index}. {title}"
            if score is not None:
                label += f" · score={score}"
            with st.expander(label, expanded=False):
                st.code(_to_pretty_json(chunk), language="json")
        else:
            with st.expander(f"chunk_{index}", expanded=False):
                st.write(chunk)


def render_timings(timings: Any, fallback_elapsed_ms: Optional[float] = None) -> None:
    """展示 timings。"""
    st.subheader("Timings")

    if isinstance(timings, dict) and timings:
        metric_items = []
        preferred_keys = [
            "total_ms",
            "engine_init_ms",
            "first_sufficiency_ms",
            "generation_ms",
        ]
        for key in preferred_keys:
            if key in timings:
                metric_items.append((key, timings[key]))

        if metric_items:
            columns = st.columns(min(4, len(metric_items)))
            for idx, (key, value) in enumerate(metric_items):
                columns[idx % len(columns)].metric(key, _format_ms(value))

        with st.expander("完整 timings", expanded=False):
            st.code(_to_pretty_json(timings), language="json")
    else:
        st.info("响应中没有 timings 字段。")
        if fallback_elapsed_ms is not None:
            st.metric("UI observed latency", f"{fallback_elapsed_ms:.1f} ms")


def _format_ms(value: Any) -> str:
    """格式化毫秒值。"""
    try:
        return f"{float(value):.1f} ms"
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# 文档管理页面
# ---------------------------------------------------------------------------


def documents_page() -> None:
    """Documents 页面：展示、上传、删除文档。"""
    st.header("Documents")

    with st.form("upload_document_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("上传 .md / .txt", type=["md", "txt"])
        source_category = st.selectbox("source_category", options=["external", "internal"], index=0)
        submitted = st.form_submit_button("上传并更新索引")

    if submitted:
        if uploaded_file is None:
            st.warning("请选择一个 .md 或 .txt 文件。")
        else:
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "text/plain",
                )
            }
            data = {"source_category": source_category}
            with st.spinner("正在上传文档并更新索引，本地 embedding / index 可能需要一些时间……"):
                payload, error, response, elapsed_ms = _request(
                    "POST",
                    "/api/ingest",
                    files=files,
                    data=data,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            render_response_meta(response, elapsed_ms, payload)
            if error:
                render_error(error, payload)
            else:
                st.success(f"上传完成 · {elapsed_ms:.1f} ms")
                st.code(_to_pretty_json(payload), language="json")

    st.divider()
    col_left, col_right = st.columns([1, 3])
    with col_left:
        refresh = st.button("刷新文档列表", width="stretch")
    with col_right:
        st.caption("文档列表来自 GET /api/documents。")

    if refresh or "documents_payload" not in st.session_state:
        with st.spinner("正在刷新文档列表……"):
            payload, error, response, elapsed_ms = get_json("/api/documents", timeout=30)
        st.session_state["documents_payload"] = payload
        st.session_state["documents_error"] = error
        st.session_state["documents_response_status"] = response.status_code if response else None
        st.session_state["documents_elapsed_ms"] = elapsed_ms

        if refresh and not error:
            documents = _extract_documents(payload)
            st.success(f"文档列表已刷新 · {len(documents)} 个文档 · {elapsed_ms:.1f} ms")

    payload = st.session_state.get("documents_payload")
    error = st.session_state.get("documents_error")
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if error and isinstance(detail, dict) and detail.get("error") == "admin_disabled":
        st.info("文档管理面按当前配置关闭；Chat、Metrics 与 Debug 不受影响。")
        with st.expander("管理面状态", expanded=False):
            st.code(_to_pretty_json(payload), language="json")
    else:
        render_error(error, payload)

    if not error:
        documents = _extract_documents(payload)
        if documents:
            st.write(f"共 {len(documents)} 个文档。")
            for doc in documents:
                render_document_card(doc)
        else:
            st.info("没有解析到 documents 列表，下面展示原始响应。")
            st.code(_to_pretty_json(payload), language="json")


def _extract_documents(payload: Any) -> List[Dict[str, Any]]:
    """兼容不同 documents 响应结构。"""
    if isinstance(payload, dict):
        docs = payload.get("documents") or payload.get("items") or payload.get("data")
        if isinstance(docs, list):
            return [doc for doc in docs if isinstance(doc, dict)]
    if isinstance(payload, list):
        return [doc for doc in payload if isinstance(doc, dict)]
    return []


def render_document_card(doc: Dict[str, Any]) -> None:
    """渲染单个文档卡片，并提供谨慎删除。"""
    doc_id = _first_present(doc, ["doc_id", "document_id", "id", "source_id"], "")
    filename = _first_present(doc, ["filename", "name", "title", "path"], str(doc_id) or "unknown")
    source_category = _first_present(doc, ["source_category", "category"], "unknown")
    chunk_count = _first_present(doc, ["chunk_count", "chunks"], "N/A")
    mtime = _first_present(doc, ["mtime", "updated_at", "modified_at"], "N/A")
    size = _first_present(doc, ["size", "size_bytes"], "N/A")

    with st.container(border=True):
        st.markdown(f"**{filename}**")
        cols = st.columns(5)
        cols[0].caption(f"doc_id: {doc_id or 'N/A'}")
        cols[1].caption(f"category: {source_category}")
        cols[2].caption(f"chunks: {chunk_count}")
        cols[3].caption(f"size: {size}")
        cols[4].caption(f"mtime: {mtime}")

        with st.expander("原始 metadata", expanded=False):
            st.code(_to_pretty_json(doc), language="json")

        if doc_id:
            confirm_key = f"delete_confirm_{doc_id}"
            st.checkbox("确认删除该文档", key=confirm_key)
            if st.button("删除", key=f"delete_{doc_id}", type="secondary"):
                if not st.session_state.get(confirm_key):
                    st.warning("删除前需要先勾选确认。")
                else:
                    payload, error, response, elapsed_ms = _request(
                        "DELETE",
                        f"/api/documents/{doc_id}",
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                    render_response_meta(response, elapsed_ms, payload)
                    if error:
                        render_error(error, payload)
                    else:
                        st.success("删除完成。请刷新文档列表。")
                        st.code(_to_pretty_json(payload), language="json")


# ---------------------------------------------------------------------------
# 聊天页面
# ---------------------------------------------------------------------------


def chat_page() -> None:
    """Chat 页面：普通问答，不默认展示 agentic_steps。"""
    st.header("Chat")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    query = st.text_area(
        "Query",
        height=120,
        placeholder="例如：HNSW 和 IVF 有什么区别？",
        key="chat_query",
    )

    cols = st.columns([1, 1, 4])
    ask = cols[0].button("发送", type="primary", width="stretch")
    clear = cols[1].button("清空历史", width="stretch")

    if clear:
        st.session_state["chat_history"] = []


    if ask:
        if not query.strip():
            st.warning("请输入 query。")
        else:
            request_payload = _build_chat_payload(query.strip())
            with st.spinner("正在调用 /api/chat，请等后端完成返回……"):
                payload, error, response, elapsed_ms = post_json("/api/chat", request_payload)
            render_response_meta(response, elapsed_ms, payload)

            if error:
                render_error(error, payload)
                if "超时" in error:
                    st.warning("UI 已停止等待，但 FastAPI / provider 侧请求可能仍在继续执行；可以观察 API 终端是否随后打印 200 或异常。")
            elif isinstance(payload, dict):
                st.session_state["chat_history"].append({"query": query.strip(), "response": payload})
                render_chat_response(payload, elapsed_ms)
            else:
                st.code(_to_pretty_json(payload), language="json")

    if st.session_state["chat_history"]:
        st.divider()
        st.subheader("本次 UI 会话历史")
        for item in reversed(st.session_state["chat_history"][-5:]):
            with st.expander(item["query"], expanded=False):
                render_chat_response(item["response"], None)


def render_chat_response(payload: Dict[str, Any], fallback_elapsed_ms: Optional[float]) -> None:
    """渲染普通 chat 响应。"""
    refused = bool(payload.get("refused", False))
    refused_reason = payload.get("refused_reason")

    cols = st.columns(4)
    cols[0].metric("path", str(payload.get("path", "N/A")))
    cols[1].metric("refused", str(refused))
    cols[2].metric("degraded", str(payload.get("degraded", False)))
    cols[3].metric("session_id", str(payload.get("session_id", "N/A")))

    if refused:
        st.warning(f"业务拒答：{refused_reason or '未返回 refused_reason'}")

    answer = payload.get("answer") or payload.get("answer_text") or ""
    st.subheader("Answer")
    if answer:
        st.markdown(str(answer))
    else:
        st.info("响应中没有 answer 字段。")

    render_citations(payload.get("citations"), payload.get("retrieved_chunks"))
    render_timings(payload.get("timings"), fallback_elapsed_ms=fallback_elapsed_ms)

    with st.expander("Retrieved chunks", expanded=False):
        render_retrieved_chunks(payload.get("retrieved_chunks"))

    with st.expander("Raw response", expanded=False):
        st.code(_to_pretty_json(payload), language="json")


# ---------------------------------------------------------------------------
# 指标页面
# ---------------------------------------------------------------------------


def metrics_page() -> None:
    """Metrics 页面：展示 health、version、Prometheus 原始指标与可解析摘要。"""
    st.header("Metrics")

    with st.spinner("正在读取 /health、/api/version、/metrics……"):
        health_payload, health_error, health_response, health_elapsed_ms = get_json("/health", timeout=15)
        version_payload, version_error, version_response, version_elapsed_ms = get_json("/api/version", timeout=15)
        metrics_payload, metrics_error, metrics_response, metrics_elapsed_ms = get_json("/metrics", timeout=15)

    st.subheader("Health")
    render_response_meta(health_response, health_elapsed_ms, health_payload)
    if health_error:
        render_error(health_error, health_payload)
    else:
        render_health_summary(health_payload)

    st.subheader("Version")
    render_response_meta(version_response, version_elapsed_ms, version_payload)
    if version_error:
        render_error(version_error, version_payload)
    else:
        render_version_summary(version_payload)

    st.subheader("Prometheus metrics")
    render_response_meta(metrics_response, metrics_elapsed_ms, metrics_payload)
    if metrics_error:
        render_error(metrics_error, metrics_payload)
    else:
        metrics_text = metrics_payload if isinstance(metrics_payload, str) else _to_pretty_json(metrics_payload)
        render_metrics_summary(metrics_text)
        with st.expander("原始 /metrics 文本", expanded=True):
            st.code(metrics_text, language="text")


def render_health_summary(payload: Any) -> None:
    """渲染 health 摘要。"""
    if not isinstance(payload, dict):
        st.code(_to_pretty_json(payload), language="json")
        return

    status = payload.get("status", "unknown")
    st.metric("status", status)

    components = payload.get("components") or payload.get("checks") or {}
    if isinstance(components, dict):
        cols = st.columns(min(4, max(1, len(components))))
        for idx, (name, value) in enumerate(components.items()):
            component_status = value.get("status", value.get("up", value)) if isinstance(value, dict) else value
            cols[idx % len(cols)].metric(str(name), str(component_status))

    with st.expander("完整 health 响应", expanded=False):
        st.code(_to_pretty_json(payload), language="json")


def render_version_summary(payload: Any) -> None:
    """渲染 version 摘要。"""
    if not isinstance(payload, dict):
        st.code(_to_pretty_json(payload), language="json")
        return

    fields = [
        "service_version",
        "pipeline_baseline",
        "pipeline_config_hash",
        "generator_model",
        "sufficiency_model",
        "embedding_model",
        "embedding_dim",
        "vector_store_backend",
        "vector_store_dir",
    ]

    rows = [{"field": str(field), "value": str(payload.get(field, "N/A"))} for field in fields]
    st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)

    with st.expander("完整 version 响应", expanded=False):
        st.code(_to_pretty_json(payload), language="json")


def render_metrics_summary(metrics_text: str) -> None:
    """对 Prometheus text format 做轻量解析，提取关键指标。"""
    parsed = _parse_prometheus_metrics(metrics_text)
    if not parsed:
        st.info("暂未解析到可汇总的 Prometheus 指标。")
        return

    interesting_prefixes = [
        "rag_request_total",
        "rag_agentic_path_total",
        "rag_refusal_total",
        "rag_error_total",
        "rag_vector_store_chunk_count",
        "rag_vector_store_doc_count",
    ]

    rows = []
    for item in parsed:
        metric_name = item["name"]
        if any(metric_name.startswith(prefix) for prefix in interesting_prefixes):
            rows.append(item)

    if rows:
        st.markdown("**关键计数指标**")
        st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)


def _parse_prometheus_metrics(metrics_text: str) -> List[Dict[str, Any]]:
    """解析最基本的 Prometheus text format 行。"""
    rows: List[Dict[str, Any]] = []
    for line in metrics_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue

        name_with_labels, value = parts
        if "{" in name_with_labels and name_with_labels.endswith("}"):
            name, labels_raw = name_with_labels.split("{", 1)
            labels = labels_raw[:-1]
        else:
            name, labels = name_with_labels, ""

        rows.append({"name": str(name), "labels": str(labels), "value": str(value)})
    return rows



# ---------------------------------------------------------------------------
# D-full 调试信息渲染辅助函数
# ---------------------------------------------------------------------------


def _as_dict(value: Any) -> Dict[str, Any]:
    """将 dict-like 对象安全转成 dict。"""
    if isinstance(value, dict):
        return value
    return {}


def _nested_get(data: Any, path: str, default: Any = None) -> Any:
    """按 a.b.c 路径安全读取嵌套字段。"""
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _first_debug_value(payload: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    """从 debug payload 的多个可能位置读取第一个可用值。"""
    for key in keys:
        if "." in key:
            value = _nested_get(payload, key, None)
        else:
            value = payload.get(key)
        if value is not None:
            return value
    return default


def _extract_dfull_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 D-full debug 顶层概览字段。"""
    classifier = _as_dict(payload.get("classifier"))
    route_policy = _first_debug_value(
        payload,
        ["route_policy", "classifier.route_policy", "evaluation_context.route_policy"],
        None,
    )
    route_candidate = _first_debug_value(
        payload,
        ["route_candidate", "classifier.route_candidate", "evaluation_context.route_candidate"],
        None,
    )

    return {
        "question_type": _first_debug_value(
            payload,
            [
                "question_type",
                "workflow_trace.question_type",
                "classifier.question_type",
                "evaluation_context.question_type",
            ],
            classifier.get("question_type"),
        ),
        "answerability": _first_debug_value(
            payload,
            [
                "answerability",
                "workflow_trace.answerability",
                "classifier.answerability",
                "evaluation_context.answerability",
            ],
            classifier.get("answerability"),
        ),
        "route_candidate": route_candidate,
        "route_policy": route_policy,
        "route": _first_debug_value(
            payload,
            [
                "workflow_trace.route.actual_route",
                "execution_record.route.actual_route",
                "path",
                "evaluation_context.route",
            ],
            None,
        ),
        "path": payload.get("path"),
        "profile": payload.get("profile"),
        "final_status": _first_debug_value(
            payload,
            [
                "workflow_trace.outcome.status",
                "execution_record.outcome.status",
                "final_status",
                "workflow_trace.final_status",
                "workflow_final_status",
            ],
            None,
        ),
        "refused": payload.get("refused", False),
        "refused_reason": payload.get("refused_reason"),
    }


def render_dfull_overview(payload: Dict[str, Any]) -> None:
    """展示 D-full 顶层诊断概览。"""
    overview = _extract_dfull_overview(payload)

    cols = st.columns(4)
    cols[0].metric("path", str(overview.get("path") or "N/A"))
    cols[1].metric("final_status", str(overview.get("final_status") or "N/A"))
    cols[2].metric("refused", str(overview.get("refused", False)))
    cols[3].metric("profile", str(overview.get("profile") or "N/A"))

    st.markdown("**Classifier（offline replay）**")
    classifier_cols = st.columns(4)
    classifier_fields = (
        "question_type",
        "answerability",
        "route_candidate",
        "route_policy",
    )
    for column, key in zip(classifier_cols, classifier_fields):
        value = overview.get(key)
        column.metric(key, "not_evaluated" if value is None else str(value))

    st.caption(
        "当前在线请求不运行 classifier；完整分类结果由 "
        "eval/classifier_rule_replay 离线生成。"
    )

    if overview.get("refused_reason"):
        st.warning(f"refused_reason: {overview['refused_reason']}")

    with st.expander("D-full overview raw", expanded=False):
        st.code(_to_pretty_json(overview), language="json")


def _extract_workflow_steps(payload: Dict[str, Any]) -> Any:
    """抽取 workflow steps，兼容 workflow_trace / workflow_steps / agentic_steps。"""
    workflow_trace = payload.get("workflow_trace")
    if isinstance(workflow_trace, dict) and isinstance(workflow_trace.get("steps"), list):
        return workflow_trace.get("steps")

    return _first_debug_value(
        payload,
        [
            "workflow_steps",
            "steps",
            "agentic_steps",
            "debug.workflow_trace.steps",
            "evaluation_context.workflow_trace.steps",
            "workflow_trace",
        ],
        [],
    )


def render_workflow_steps_debug(payload: Dict[str, Any]) -> None:
    """展示 workflow steps。"""
    steps = _extract_workflow_steps(payload)
    if not steps:
        st.info("响应中没有 workflow_trace / workflow_steps / agentic_steps。")
        return

    if not isinstance(steps, list):
        st.code(_to_pretty_json(steps), language="json")
        return

    rows = []
    for index, step in enumerate(steps, start=1):
        if isinstance(step, dict):
            rows.append(
                {
                    "idx": index,
                    "step_type": _first_present(step, ["step_type", "type", "step", "stage"], ""),
                    "name": _first_present(step, ["name"], ""),
                    "decision": _first_present(step, ["decision", "output", "status"], ""),
                    "duration_ms": _first_present(step, ["duration_ms", "elapsed_ms"], ""),
                    "error": _first_present(step, ["error", "error_type"], ""),
                }
            )
        else:
            rows.append({"idx": index, "step_type": str(step), "name": "", "decision": "", "duration_ms": "", "error": ""})

    st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)

    with st.expander("workflow steps raw", expanded=False):
        st.code(_to_pretty_json(steps), language="json")


def _extract_evidence_packet(payload: Dict[str, Any]) -> Any:
    """抽取 EvidencePacket。"""
    return _first_debug_value(
        payload,
        [
            "evidence_packet",
            "workflow_trace.evidence_packet",
            "debug.evidence_packet",
            "evaluation_context.evidence_packet",
            "workflow_state.evidence_packet",
        ],
        {},
    )


def render_evidence_packet_debug(payload: Dict[str, Any]) -> None:
    """展示 EvidencePacket 摘要与原始结构。"""
    packet = _extract_evidence_packet(payload)
    packet_dict = _as_dict(packet)

    if not packet_dict:
        st.info("响应中没有 evidence_packet。")
        return

    items = packet_dict.get("items") or []
    source_coverage = packet_dict.get("source_coverage") or {}
    known_gaps = packet_dict.get("known_gaps") or []

    cols = st.columns(4)
    cols[0].metric("items", str(len(items) if isinstance(items, list) else "N/A"))
    cols[1].metric("distinct_sources", str(source_coverage.get("distinct_source_count", "N/A")))
    cols[2].metric("known_gaps", str(len(known_gaps) if isinstance(known_gaps, list) else "N/A"))
    cols[3].metric("compression", str(packet_dict.get("compression_policy", "N/A"))[:40])

    if known_gaps:
        st.warning("known_gaps: " + ", ".join(str(x) for x in known_gaps))

    if isinstance(items, list) and items:
        rows = []
        for index, item in enumerate(items, start=1):
            if isinstance(item, dict):
                rows.append(
                    {
                        "idx": index,
                        "chunk_id": item.get("chunk_id", ""),
                        "source_id": item.get("source_id", ""),
                        "source_path": item.get("source_path", ""),
                        "section_path": item.get("section_path", ""),
                        "in_prompt": item.get("in_prompt", ""),
                        "is_answer_bearing": item.get("is_answer_bearing", ""),
                        "rank_after_rerank": item.get("rank_after_rerank", ""),
                        "vector_score": item.get("vector_score", ""),
                        "rerank_score": item.get("rerank_score", ""),
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)

    with st.expander("EvidencePacket raw", expanded=False):
        st.code(_to_pretty_json(packet), language="json")


def _extract_citation_support_debug(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 citation_support。"""
    value = _first_debug_value(
        payload,
        [
            "citation_support",
            "debug.citation_support",
            "evaluation_context.citation_support",
            "response_uncertainty.citation_support",
        ],
        {},
    )
    return _as_dict(value)


def render_citation_support_debug(payload: Dict[str, Any]) -> None:
    """展示 citation_support 摘要。"""
    report = _extract_citation_support_debug(payload)
    if not report:
        st.info("响应中没有 citation_support。")
        return

    cols = st.columns(4)
    cols[0].metric("label", str(report.get("citation_support_label", "N/A")))
    cols[1].metric("unsupported_claim_count", str(report.get("unsupported_claim_count", "N/A")))
    cols[2].metric("claim_count", str(report.get("claim_count", "N/A")))
    cols[3].metric("evidence_count", str(report.get("evidence_count", "N/A")))

    borderline = report.get("borderline_dimension")
    if borderline:
        st.warning("borderline_dimension: " + ", ".join(str(x) for x in borderline))

    claims = report.get("claims")
    if isinstance(claims, list) and claims:
        rows = []
        for idx, claim in enumerate(claims, start=1):
            if isinstance(claim, dict):
                rows.append(
                    {
                        "idx": idx,
                        "label": claim.get("label", ""),
                        "best_score": claim.get("best_score", ""),
                        "best_evidence_id": claim.get("best_evidence_id", ""),
                        "claim": claim.get("claim", ""),
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)

    with st.expander("citation_support raw", expanded=False):
        st.code(_to_pretty_json(report), language="json")


def _extract_conflict_debug(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 conflict_detection。"""
    value = _first_debug_value(
        payload,
        [
            "conflict_detection",
            "debug.conflict_detection",
            "evaluation_context.conflict_detection",
        ],
        {},
    )
    if value:
        return _as_dict(value)

    conflicts = payload.get("conflicts")
    if conflicts is not None:
        return {"conflicts": conflicts, "conflict_count": len(conflicts) if isinstance(conflicts, list) else "N/A"}

    return {}


def render_conflict_debug(payload: Dict[str, Any]) -> None:
    """展示 conflict detection。"""
    report = _extract_conflict_debug(payload)
    if not report:
        st.info("响应中没有 conflict_detection / conflicts。")
        return

    conflicts = report.get("conflicts") or []
    cols = st.columns(4)
    cols[0].metric("triggered", str(report.get("triggered", "N/A")))
    cols[1].metric("conflict_count", str(report.get("conflict_count", len(conflicts) if isinstance(conflicts, list) else "N/A")))
    cols[2].metric("distinct_sources", str(report.get("distinct_sources_in_packet", "N/A")))
    cols[3].metric("skipped_reason", str(report.get("skipped_reason", "N/A")))

    if report.get("trigger_reason"):
        st.caption(f"trigger_reason: {report.get('trigger_reason')}")

    if isinstance(conflicts, list) and conflicts:
        rows = []
        for idx, item in enumerate(conflicts, start=1):
            if isinstance(item, dict):
                rows.append(
                    {
                        "idx": idx,
                        "type": item.get("conflict_type", ""),
                        "uncertainty_level": item.get("uncertainty_level", ""),
                        "evidence_a": item.get("evidence_a", ""),
                        "evidence_b": item.get("evidence_b", ""),
                        "resolution": item.get("resolution", ""),
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)

    with st.expander("conflict_detection raw", expanded=False):
        st.code(_to_pretty_json(report), language="json")


def _extract_uncertainty_debug(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 uncertainty。"""
    value = _first_debug_value(
        payload,
        [
            "uncertainty",
            "response_uncertainty",
            "debug.uncertainty",
            "evaluation_context.uncertainty",
        ],
        {},
    )
    if isinstance(value, dict):
        return value

    level = _first_debug_value(payload, ["uncertainty_level", "evaluation_context.uncertainty_level"], None)
    if level:
        return {
            "level": level,
            "reasons": payload.get("uncertainty_reasons", []),
            "missing_info": payload.get("missing_info", []),
            "safe_answer_boundary": payload.get("safe_answer_boundary"),
            "next_steps": payload.get("next_steps", []),
        }

    return {}


def render_uncertainty_debug(payload: Dict[str, Any]) -> None:
    """展示 uncertainty report。"""
    report = _extract_uncertainty_debug(payload)
    if not report:
        st.info("响应中没有 uncertainty。")
        return

    level = str(report.get("level", "N/A"))
    if level == "high":
        st.error(f"uncertainty: {level}")
    elif level == "medium":
        st.warning(f"uncertainty: {level}")
    else:
        st.success(f"uncertainty: {level}")

    cols = st.columns(3)
    cols[0].metric("reasons", str(len(report.get("reasons") or [])))
    cols[1].metric("missing_info", str(len(report.get("missing_info") or [])))
    cols[2].metric("next_steps", str(len(report.get("next_steps") or [])))

    if report.get("reasons"):
        st.markdown("**Reasons**")
        st.write(report.get("reasons"))

    if report.get("missing_info"):
        st.markdown("**Missing info**")
        st.write(report.get("missing_info"))

    if report.get("safe_answer_boundary"):
        st.markdown("**Safe answer boundary**")
        st.write(report.get("safe_answer_boundary"))

    if report.get("next_steps"):
        st.markdown("**Next steps**")
        st.write(report.get("next_steps"))

    with st.expander("uncertainty raw", expanded=False):
        st.code(_to_pretty_json(report), language="json")


def _extract_observability_debug(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 observability / model identity / token cost latency。"""
    obs = _first_debug_value(payload, ["observability", "debug.observability"], {})
    obs_dict = _as_dict(obs)

    model_calls = (
        obs_dict.get("model_calls")
        or payload.get("model_calls")
        or _nested_get(payload, "observability_record.model_calls", [])
        or []
    )

    token_usage = (
        obs_dict.get("token_usage")
        or payload.get("token_usage")
        or payload.get("usage")
        or {}
    )

    cost = (
        obs_dict.get("estimated_cost_usd")
        or payload.get("estimated_cost_usd")
        or _nested_get(payload, "cost.estimated_cost_usd")
    )

    return {
        "observability": obs_dict,
        "model_calls": model_calls,
        "token_usage": token_usage,
        "estimated_cost_usd": cost,
        "timings": payload.get("timings", {}),
    }


def render_observability_debug(payload: Dict[str, Any]) -> None:
    """展示 token / cost / latency / model identity。"""
    data = _extract_observability_debug(payload)

    timings = data.get("timings") or {}
    token_usage = data.get("token_usage") or {}
    model_calls = data.get("model_calls") or []

    cols = st.columns(4)
    cols[0].metric("total_ms", _format_ms(timings.get("total_ms")) if isinstance(timings, dict) and timings.get("total_ms") is not None else "N/A")
    cols[1].metric("prompt_tokens", str(token_usage.get("prompt_tokens", "N/A")) if isinstance(token_usage, dict) else "N/A")
    cols[2].metric("completion_tokens", str(token_usage.get("completion_tokens", "N/A")) if isinstance(token_usage, dict) else "N/A")
    cols[3].metric("estimated_cost_usd", str(data.get("estimated_cost_usd", "N/A")))

    if isinstance(model_calls, list) and model_calls:
        rows = []
        for idx, call in enumerate(model_calls, start=1):
            if isinstance(call, dict):
                identity = call.get("identity") if isinstance(call.get("identity"), dict) else {}
                rows.append(
                    {
                        "idx": idx,
                        "role": call.get("role", ""),
                        "configured_model": identity.get("configured_model", ""),
                        "provider_response_model": identity.get("provider_response_model", ""),
                        "resolved_model": identity.get("resolved_model", ""),
                        "upstream_provider": identity.get("upstream_provider", ""),
                        "latency_ms": call.get("latency_ms", ""),
                        "timeout": call.get("timeout", ""),
                        "api_error": call.get("api_error", ""),
                        "error_type": call.get("error_type", ""),
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows).astype(str), width="stretch", hide_index=True)
    else:
        st.info("响应中没有 model_calls。")

    with st.expander("observability raw", expanded=False):
        st.code(_to_pretty_json(data), language="json")

# ---------------------------------------------------------------------------
# 调试页面
# ---------------------------------------------------------------------------


def debug_page() -> None:
    """Debug 页面：调用 /api/chat/debug，展示内部诊断字段。"""
    st.header("Debug")

    query = st.text_area(
        "Debug query",
        height=120,
        placeholder="例如：HNSW 和 IVF 有什么区别？",
        key="debug_query",
    )

    st.caption("Debug 会返回更多诊断字段，耗时通常与普通 Chat 接近。")

    if st.button("调用 /api/chat/debug", type="primary"):
        if not query.strip():
            st.warning("请输入 query。")
        else:
            request_payload = _build_chat_payload(query.strip())
            with st.spinner("正在调用 /api/chat/debug，请等后端完成返回……"):
                payload, error, response, elapsed_ms = post_json("/api/chat/debug", request_payload)
            render_response_meta(response, elapsed_ms, payload)

            if error:
                render_error(error, payload)
                if "超时" in error:
                    st.warning("UI 已停止等待，但 FastAPI / provider 侧请求可能仍在继续执行；可以观察 API 终端是否随后打印 200 或异常。")
            elif isinstance(payload, dict):
                render_debug_response(payload, elapsed_ms)
            else:
                st.code(_to_pretty_json(payload), language="json")


def _extract_acl_demo_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """抽取 Phase E ACL demo 展示字段。"""
    policy_trace = _as_dict(payload.get("policy_trace"))
    access_policy = _as_dict(policy_trace.get("access_policy"))
    pre_topk_policy = _as_dict(access_policy.get("pre_topk"))
    generation_context = _as_dict(payload.get("generation_context"))
    retrieval_diagnostics = _as_dict(payload.get("retrieval_diagnostics"))

    selected_user = access_policy.get("user_id")
    selected_context = {
        "label": str(selected_user or "unknown"),
        "roles": list(access_policy.get("roles") or []),
        "groups": list(access_policy.get("groups") or []),
    }

    denied_source_ids = list(
        pre_topk_policy.get("denied_source_ids")
        or access_policy.get("denied_source_ids")
        or []
    )
    prompt_sources = list(generation_context.get("prompt_sources") or [])
    prompt_chunk_ids = list(generation_context.get("prompt_chunk_ids") or [])

    index_chunk_count = pre_topk_policy.get("index_chunk_count")
    eligible_chunk_count = pre_topk_policy.get("eligible_chunk_count")
    excluded_chunk_count = None
    if isinstance(index_chunk_count, (int, float)) and isinstance(
        eligible_chunk_count, (int, float)
    ):
        excluded_chunk_count = max(
            0, int(index_chunk_count) - int(eligible_chunk_count)
        )

    post_topk_denied_chunk_count = access_policy.get("denied_chunk_count")
    if post_topk_denied_chunk_count is None:
        post_topk_denied_chunk_count = retrieval_diagnostics.get(
            "acl_denied_chunk_count"
        )

    retrieval_acl_checked = bool(access_policy.get("enabled")) and bool(
        access_policy.get("enforced_before_topk")
    )
    if not retrieval_acl_checked:
        retrieval_acl_checked = bool(retrieval_diagnostics.get("acl_checked"))

    return {
        "selected_user": selected_user,
        "selected_user_label": selected_context["label"],
        "selected_roles": selected_context["roles"],
        "selected_groups": selected_context["groups"],
        "response_user_id": access_policy.get("user_id"),
        "pre_topk_index_chunk_count": index_chunk_count,
        "pre_topk_eligible_chunk_count": eligible_chunk_count,
        "pre_topk_excluded_chunk_count": excluded_chunk_count,
        "post_topk_input_chunk_count": access_policy.get("input_chunk_count"),
        "post_topk_allowed_chunk_count": access_policy.get("allowed_chunk_count"),
        "post_topk_denied_chunk_count": post_topk_denied_chunk_count,
        "denied_source_ids": denied_source_ids,
        "prompt_sources": prompt_sources,
        "prompt_chunk_ids": prompt_chunk_ids,
        "acl_checked": generation_context.get("acl_checked"),
        "prompt_chunks_allowed_only": generation_context.get("prompt_chunks_allowed_only"),
        "citations_allowed_only": generation_context.get("citations_allowed_only"),
        "retrieval_acl_checked": retrieval_acl_checked,
    }


def render_acl_demo_summary(payload: Dict[str, Any]) -> None:
    """渲染 Phase E ACL demo 摘要，避免展示过多原始 JSON。"""
    summary = _extract_acl_demo_summary(payload)

    st.subheader("Phase E ACL demo summary")
    st.caption("身份来自 API 侧 token 映射；下列角色与 ACL 结果取自 debug 响应。")

    cols = st.columns(4)
    cols[0].metric("principal", str(summary.get("selected_user") or "N/A"))
    cols[1].metric("index_chunks", str(summary.get("pre_topk_index_chunk_count") or "N/A"))
    cols[2].metric("eligible_chunks", str(summary.get("pre_topk_eligible_chunk_count") or "N/A"))
    cols[3].metric("excluded_chunks", str(summary.get("pre_topk_excluded_chunk_count") or 0))

    cols = st.columns(4)
    cols[0].metric("pre_topk_acl", str(summary.get("retrieval_acl_checked", False)))
    cols[1].metric("post_topk_denied", str(summary.get("post_topk_denied_chunk_count") or 0))
    cols[2].metric("prompt_allowed_only", str(summary.get("prompt_chunks_allowed_only", "N/A")))
    cols[3].metric("citations_allowed_only", str(summary.get("citations_allowed_only", "N/A")))

    st.markdown(
        f"**Authenticated context**: `{summary['selected_user_label']}` · "
        f"roles=`{summary['selected_roles']}` · groups=`{summary['selected_groups']}`"
    )

    st.markdown("**Prompt sources used by this query**")
    prompt_sources = summary.get("prompt_sources") or []
    if prompt_sources:
        st.dataframe(
            pd.DataFrame({"prompt_sources": [str(item) for item in prompt_sources]}),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("本次响应没有返回 generation_context.prompt_sources。")

    denied_source_ids = summary.get("denied_source_ids") or []
    excluded_chunk_count = summary.get("pre_topk_excluded_chunk_count") or 0
    audit_label = (
        f"ACL audit details · {excluded_chunk_count} inaccessible chunks "
        f"across {len(denied_source_ids)} sources"
    )
    with st.expander(audit_label, expanded=False):
        st.caption(
            "这是当前身份的权限级排除清单，不是本问题的未过滤 TopK。"
        )
        if denied_source_ids:
            st.dataframe(
                pd.DataFrame(
                    {
                        "inaccessible_source_ids": [
                            str(item) for item in denied_source_ids
                        ]
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("前置 ACL 已执行；当前身份没有不可访问的 source。")

    with st.expander("ACL demo summary raw", expanded=False):
        st.code(_to_pretty_json(summary), language="json")


def render_debug_response(payload: Dict[str, Any], fallback_elapsed_ms: Optional[float]) -> None:
    """渲染 D-full debug 响应。"""
    cols = st.columns(4)
    cols[0].metric("path", str(payload.get("path", "N/A")))
    cols[1].metric("refused", str(payload.get("refused", False)))
    cols[2].metric("request_id", str(payload.get("request_id", "N/A")))
    cols[3].metric("session_id", str(payload.get("session_id", "N/A")))

    answer = payload.get("answer") or payload.get("answer_text") or ""
    st.subheader("Answer")
    st.markdown(str(answer) if answer else "N/A")

    render_dfull_overview(payload)
    render_acl_demo_summary(payload)
    render_timings(payload.get("timings"), fallback_elapsed_ms=fallback_elapsed_ms)

    (
        tab_steps,
        tab_evidence,
        tab_suff,
        tab_citation,
        tab_conflict,
        tab_uncertainty,
        tab_observability,
        tab_legacy,
        tab_raw,
    ) = st.tabs(
        [
            "Workflow",
            "EvidencePacket",
            "Sufficiency",
            "Citation support",
            "Conflicts",
            "Uncertainty",
            "Token / Cost / Latency",
            "Legacy debug",
            "Raw",
        ]
    )

    with tab_steps:
        render_workflow_steps_debug(payload)

    with tab_evidence:
        render_evidence_packet_debug(payload)

    with tab_suff:
        sufficiency = _extract_sufficiency(payload)
        st.code(_to_pretty_json(sufficiency), language="json")

    with tab_citation:
        render_citation_support_debug(payload)

    with tab_conflict:
        render_conflict_debug(payload)

    with tab_uncertainty:
        render_uncertainty_debug(payload)

    with tab_observability:
        render_observability_debug(payload)

    with tab_legacy:
        st.markdown("**Selective rerank**")
        st.code(_to_pretty_json(_extract_rerank_info(payload)), language="json")
        st.markdown("**Evaluation context**")
        st.code(_to_pretty_json(payload.get("evaluation_context", {})), language="json")
        st.markdown("**Vector store context**")
        st.code(_to_pretty_json(payload.get("vector_store_context", {})), language="json")

    with tab_raw:
        st.code(_to_pretty_json(payload), language="json")


def render_agentic_steps(agentic_steps: Any) -> None:
    """展示 agentic_steps。"""
    if not isinstance(agentic_steps, list):
        st.code(_to_pretty_json(agentic_steps), language="json")
        return

    for index, step in enumerate(agentic_steps, start=1):
        if isinstance(step, dict):
            step_name = _first_present(step, ["step", "name", "stage", "type"], f"step_{index}")
            duration_ms = _first_present(step, ["duration_ms", "elapsed_ms"], None)
            label = f"{index}. {step_name}"
            if duration_ms is not None:
                label += f" · {_format_ms(duration_ms)}"
            with st.expander(label, expanded=index == 1):
                st.code(_to_pretty_json(step), language="json")
        else:
            with st.expander(f"step_{index}", expanded=False):
                st.write(step)


def _extract_sufficiency(payload: Dict[str, Any]) -> Dict[str, Any]:
    """从 debug 响应中抽取 sufficiency 相关字段。"""
    result: Dict[str, Any] = {}

    for key in ("sufficiency_detail", "sufficiency", "sufficiency_verdict", "refused_reason"):
        if key in payload:
            result[key] = payload[key]

    sufficiency_diagnostics = payload.get("sufficiency_diagnostics")
    if isinstance(sufficiency_diagnostics, dict):
        result["sufficiency_diagnostics"] = sufficiency_diagnostics

    evaluation_context = payload.get("evaluation_context")
    if isinstance(evaluation_context, dict):
        for key, value in evaluation_context.items():
            if "suff" in key.lower() or "judge" in key.lower() or "verdict" in key.lower():
                result[f"evaluation_context.{key}"] = value

    agentic_steps = payload.get("agentic_steps")
    if isinstance(agentic_steps, list):
        suff_steps = []
        for step in agentic_steps:
            text = _to_pretty_json(step).lower()
            if "suff" in text or "judge" in text or "verdict" in text:
                suff_steps.append(step)
        if suff_steps:
            result["agentic_steps_related"] = suff_steps

    return result or {"message": "未从响应中抽取到 sufficiency 相关字段。"}


def _extract_rerank_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    """从 debug 响应中抽取 selective rerank 相关字段。"""
    result: Dict[str, Any] = {}

    for key in ("rerank_detail", "rerank", "rerank_enabled", "rerank_triggered"):
        if key in payload:
            result[key] = payload[key]

    evaluation_context = payload.get("evaluation_context")
    if isinstance(evaluation_context, dict):
        for key, value in evaluation_context.items():
            if "rerank" in key.lower():
                result[f"evaluation_context.{key}"] = value

    agentic_steps = payload.get("agentic_steps")
    if isinstance(agentic_steps, list):
        rerank_steps = []
        for step in agentic_steps:
            text = _to_pretty_json(step).lower()
            if "rerank" in text:
                rerank_steps.append(step)
        if rerank_steps:
            result["agentic_steps_related"] = rerank_steps

    return result or {"message": "未从响应中抽取到 rerank 相关字段。"}


# ---------------------------------------------------------------------------
# 页面入口
# ---------------------------------------------------------------------------


def main() -> None:
    """Streamlit 入口。"""
    st.set_page_config(
        page_title="Agentic RAG · D-full",
        page_icon="🔎",
        layout="wide",
    )

    st.title("Agentic RAG · D-full Debug UI")
    st.caption("Streamlit UI only. Calls FastAPI service. D-full debug view surfaces workflow / evidence / uncertainty diagnostics.")

    render_api_status()

    documents_tab, chat_tab, metrics_tab, debug_tab = st.tabs(
        ["Documents", "Chat", "Metrics", "Debug"]
    )

    with documents_tab:
        documents_page()

    with chat_tab:
        chat_page()

    with metrics_tab:
        metrics_page()

    with debug_tab:
        debug_page()


if __name__ == "__main__":
    main()
