"""
程序作用：
定义 CLI、API、UI 与评估入口共用的查询命令结构，防止各入口自行拼装不同参数。

整体结构：
1）QueryCommand 保存查询、profile、请求身份、topk 和调试开关；
2）normalized_query 清理查询文本并拒绝空查询；
3）__all__ 固定模块公开接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QueryCommand:
    """封装一次应用层查询所需的统一参数。"""
    query: str
    profile: Optional[str] = None
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    qid: Optional[str] = None
    session_id: Optional[str] = None
    topk: Optional[int] = None
    debug: bool = False

    def normalized_query(self) -> str:
        value = str(self.query).strip()
        if not value:
            raise ValueError("query must not be empty")
        return value


__all__ = ["QueryCommand"]
