"""
文件作用：
提供 Phase C Step 12 的 Locust 压测脚本，只压测 POST /api/chat。
该脚本以黑盒 HTTP 请求方式验证服务稳定性、排队行为、429 保护和响应 timings，
不调用 /api/chat/debug，也不修改 RAG pipeline 内部逻辑。

整体结构：
1）内置 10 条固定压测问题，覆盖普通事实题、流程题、对比题、DECOMPOSE、拒答题和边界题；
2）通过环境变量控制目标请求数、请求超时和是否把 429 视为预期保护行为；
3）达到目标请求数后自动停止 Locust，便于分别生成 N=1 / N=2 / N=4 报告。

常用环境变量：
- LOAD_TEST_TARGET_REQUESTS：本轮总请求数，默认 10；
- LOAD_TEST_REQUEST_TIMEOUT_SECONDS：单请求超时，默认 300；
- LOAD_TEST_ACCEPT_429：是否把 429 视为压测成功结果，默认 true。
"""

from __future__ import annotations

import os
import random
import threading
from typing import Any, Dict, List

import gevent
from locust import HttpUser, between, events, task


LOAD_TEST_CASES: List[Dict[str, str]] = [
    {
        "id": "q01",
        "scenario": "workflow",
        "query": "RAG 的完整流程包括哪些主要步骤？",
    },
    {
        "id": "q05",
        "scenario": "ordinary_fact",
        "query": "为什么 embedding 相似度常用余弦相似度？",
    },
    {
        "id": "q08",
        "scenario": "explicit_compare_decompose",
        "query": "HNSW 和 IVF 向量索引有什么主要区别？",
    },
    {
        "id": "q10",
        "scenario": "model_serving",
        "query": "KV cache 在大模型推理中有什么作用？",
    },
    {
        "id": "q14",
        "scenario": "rag_failure_mode",
        "query": "什么叫 evidence insufficient（证据不充分）？",
    },
    {
        "id": "q20",
        "scenario": "boundary_answer",
        "query": "连续批处理（Continuous Batching）和传统静态批处理有什么区别？",
    },
    {
        "id": "q23",
        "scenario": "explicit_compare_semantic_chunking",
        "query": "语义分块相比固定分块的主要优势是什么？",
    },
    {
        "id": "q26",
        "scenario": "explicit_compare_ivf_hnsw",
        "query": "IVF 索引相比 HNSW 的主要特点是什么？",
    },
    {
        "id": "q29",
        "scenario": "multi_az",
        "query": "在 Multi-AZ 架构中，为什么需要跨 AZ 部署副本？",
    },
    {
        "id": "dl02",
        "scenario": "ood_reject",
        "query": "Claude 4 Sonnet 的训练数据配比是什么？",
    },
]


def _read_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


TARGET_REQUESTS = _read_positive_int("LOAD_TEST_TARGET_REQUESTS", 10)
REQUEST_TIMEOUT_SECONDS = _read_positive_int("LOAD_TEST_REQUEST_TIMEOUT_SECONDS", 300)
ACCEPT_429 = _read_bool("LOAD_TEST_ACCEPT_429", True)

_counter_lock = threading.Lock()
_started_requests = 0
_finished_requests = 0
_stop_requested = False


def _next_case() -> Dict[str, str]:
    """随机选择一条压测问题，避免所有用户完全同步打同一题。"""

    return random.choice(LOAD_TEST_CASES)


def _should_start_request() -> bool:
    """控制整轮压测总请求数。"""

    global _started_requests
    with _counter_lock:
        if _started_requests >= TARGET_REQUESTS:
            return False
        _started_requests += 1
        return True


def _stop_runner_later(environment: Any) -> None:
    """延迟停止 Locust runner。

    说明：
    - 保留 Locust 原生 CLI 参数能力，包括 --run-time；
    - 本脚本不依赖 --run-time，仍按 LOAD_TEST_TARGET_REQUESTS 自动退出；
    - 退出动作放到独立 greenlet，避免在并发 user task 内直接 quit 导致 N=2/N=4 偶发卡住。
    """

    runner = getattr(environment, "runner", None)
    if runner is None:
        return
    gevent.spawn_later(0.2, runner.quit)


def _request_finished(environment: Any) -> None:
    """记录已完成请求数；达到目标请求数后只触发一次退出。"""

    global _finished_requests, _stop_requested
    should_stop = False

    with _counter_lock:
        _finished_requests += 1
        if _finished_requests >= TARGET_REQUESTS and not _stop_requested:
            _stop_requested = True
            should_stop = True

    if should_stop:
        print(
            "[phase-c-load-test] "
            f"target reached: finished_requests={_finished_requests}, "
            f"target_requests={TARGET_REQUESTS}; stopping locust"
        )
        _stop_runner_later(environment)


@events.test_start.add_listener
def on_test_start(environment: Any, **_: Any) -> None:
    """启动时重置计数器，并输出本轮压测配置。"""

    global _started_requests, _finished_requests, _stop_requested
    with _counter_lock:
        _started_requests = 0
        _finished_requests = 0
        _stop_requested = False

    print(
        "[phase-c-load-test] "
        f"target_requests={TARGET_REQUESTS}, "
        f"timeout_seconds={REQUEST_TIMEOUT_SECONDS}, "
        f"accept_429={ACCEPT_429}, "
        f"cases={len(LOAD_TEST_CASES)}"
    )


class PhaseCChatUser(HttpUser):
    """Phase C /api/chat 压测用户。"""

    wait_time = between(0.1, 0.5)

    @task
    def chat(self) -> None:
        """发送一次 /api/chat 请求。"""

        if not _should_start_request():
            # 目标请求数已分配完，等待最后一批请求完成后由 _request_finished 统一退出。
            gevent.sleep(0.2)
            return

        case = _next_case()
        payload = {
            "query": case["query"],
            "session_id": f"loadtest-{case['id']}",
        }

        try:
            with self.client.post(
                "/api/chat",
                json=payload,
                name=f"/api/chat [{case['scenario']}]",
                timeout=REQUEST_TIMEOUT_SECONDS,
                catch_response=True,
            ) as response:
                if response.status_code == 429 and ACCEPT_429:
                    response.success()
                    return

                if response.status_code != 200:
                    response.failure(
                        f"unexpected_status={response.status_code}, body={response.text[:300]}"
                    )
                    return

                try:
                    data = response.json()
                except ValueError:
                    response.failure("response is not valid JSON")
                    return

                if "request_id" not in data:
                    response.failure("missing request_id")
                    return
                if "timings" not in data or not isinstance(data["timings"], dict):
                    response.failure("missing timings")
                    return
                if "answer" not in data:
                    response.failure("missing answer")
                    return

                response.success()
        finally:
            _request_finished(self.environment)
