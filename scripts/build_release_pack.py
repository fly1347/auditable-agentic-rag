#!/usr/bin/env python3
"""
程序作用：
把最终回归 CER 与安全断言整理成固定结构的 Phase F-Review 发布证据包。

整体结构：
1）解析记录、安全汇总与证据等级参数；
2）调用 reporting.release 生成质量、安全和文件哈希清单；
3）输出生成文件路径，便于发布流程继续校验。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.reporting.release import build_release_pack


# 读取发布证据并生成固定格式的发布包。
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--security-summary", type=Path, required=True)
    parser.add_argument("--security-assertions", type=Path, required=True)
    parser.add_argument("--evidence-class", choices=["historical_bridge", "final_regression"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    records = [
        CanonicalExecutionRecord.from_dict(json.loads(line))
        for line in args.records.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    paths = build_release_pack(
        records,
        args.output_dir,
        security_summary=args.security_summary,
        security_assertions=args.security_assertions,
        evidence_class=args.evidence_class,
    )
    print(f"PASS release evidence pack: class={args.evidence_class} files={len(paths)} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
