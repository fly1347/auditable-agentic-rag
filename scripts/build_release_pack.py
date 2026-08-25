#!/usr/bin/env python3
"""Build the fixed Phase F-Review release evidence pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.reporting.release import build_release_pack


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
