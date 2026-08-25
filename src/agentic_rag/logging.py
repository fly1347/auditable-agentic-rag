"""
作用：
- 提供 Phase A 最小可用的结构化日志（JSONL）
- 用于 index/query 的可观测性与后续 eval

结构：
- log_jsonl: 写一行 JSON 到指定文件（自动创建母目录）
"""

from __future__ import annotations  # 启用前向引用类型标注（兼容性更好）

import json  # 引入 json 序列化
from datetime import datetime, timezone  # 引入时间工具
from pathlib import Path  # 引入路径处理
from typing import Any, Dict  # 引入类型标注


def _utc_now_iso() -> str:  # 定义获取 UTC 时间的函数
    return datetime.now(timezone.utc).isoformat()  # 返回 ISO 格式的 UTC 时间字符串


def log_jsonl(path: str, record: Dict[str, Any]) -> None:
    """
    作用：
    - 将 record 作为一行 JSON 追加写入 path（JSONL）
    - 自动写入 timestamp 字段（UTC）
    """
    p = Path(path)  # 将字符串路径转换为 Path
    p.parent.mkdir(parents=True, exist_ok=True)  # 创建母目录（若不存在）
    record_with_ts = dict(record)  # 复制 record，避免修改调用方对象
    record_with_ts["ts_utc"] = _utc_now_iso()  # 添加 UTC 时间戳字段
    line = json.dumps(record_with_ts, ensure_ascii=False)  # 序列化为 JSON 字符串（保留中文）
    with p.open("a", encoding="utf-8") as f:  # 以追加方式打开文件
        f.write(line + "\n")  # 写入一行并换行