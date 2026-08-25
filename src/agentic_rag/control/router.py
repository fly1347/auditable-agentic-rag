"""
文件作用：
1）提供 D-lite 的最小问题路由能力。
2）输入用户 query，输出 DIRECT / DECOMPOSE 两类路径判定。
3）当前只用纯规则关键词，不引入 LLM 分类器。
4）为 query_pipeline 提供稳定、可观测的路由结果结构。

整体结构：
1）定义 RouteDecision 数据结构。
2）定义显式对比关键词列表 DECOMPOSE_KEYWORDS。
3）实现 route_query(query) 作为统一入口。
4）返回 path + matched_keyword，便于后续写入 flags / agentic_steps。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    """保存一次路由判定结果。"""

    path: str
    matched_keyword: str = ""


DECOMPOSE_KEYWORDS: list[str] = [
    "vs",
    "versus",
    "区别",
    "对比",
    "比较",
    "不同",
    "分别",
    "各自",
    "相比"
]


def route_query(query: str) -> RouteDecision:
    """
    对输入问题做最小路由判定。

    返回：
        RouteDecision(path="DIRECT" | "DECOMPOSE", matched_keyword=str)
    """

    text: str = str(query or "").strip()
    text_lower: str = text.lower()

    for keyword in DECOMPOSE_KEYWORDS:
        keyword_lower: str = str(keyword).lower()
        if keyword_lower in text_lower:
            return RouteDecision(path="DECOMPOSE", matched_keyword=keyword)

    return RouteDecision(path="DIRECT", matched_keyword="")
