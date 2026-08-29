"""
程序作用：
提供可信的本地命令行入口；完整查询统一进入 RagApplicationService，离线建索引和检索诊断则保持为明确的运维命令。

整体结构：
1）_parse_args 解析 index、retrieve、query 三种模式及运行参数；
2）main 按模式装配配置和依赖并执行对应操作；
3）_required_query 校验需要查询文本的命令参数。
"""

from __future__ import annotations

import argparse
from typing import Optional

from agentic_rag.config import load_config
from agentic_rag.execution.command import QueryCommand
from agentic_rag.ingest.ingest_pipeline import index_corpus
from agentic_rag.policy.principal import local_cli_principal
from agentic_rag.policy.access import UserContext
from agentic_rag.service.application_service import RagApplicationService
from agentic_rag.service.container import RuntimeContainer


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="agentic_rag")
    parser.add_argument("--mode", choices=["index", "retrieve", "query"], default="query")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--profile", choices=["baseline", "orchestrated"], default=None)
    parser.add_argument("--topk", type=int, default=None)
    parser.add_argument("--corpus-dir", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--qid", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--debug-record", action="store_true")
    return parser.parse_args(argv)


# 根据命令模式执行建索引、检索诊断或完整查询。
def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    config = load_config(args.config)

    if args.mode == "index":
        stats = index_corpus(
            corpus_dir=str(args.corpus_dir or config.corpus_root),
            rebuild=bool(args.rebuild),
            artifacts_dir=config.artifacts_dir,
            acl_registry_path=config.index.acl_registry_path,
        )
        print(stats)
        return 0

    if args.mode == "retrieve":
        query = _required_query(args.query, "retrieve")
        retriever = RuntimeContainer(config).get_retriever()
        if args.min_score is not None:
            retriever.cfg.min_score = float(args.min_score)
        topk = int(args.topk or config.topk)
        principal = local_cli_principal()
        result = retriever.run(
            query=query,
            topk=topk,
            user_context=UserContext(
                user_id=principal.principal_id,
                roles=principal.roles,
                groups=principal.groups,
                tenant_id=principal.tenant_id,
            ),
        )
        print(f"query={result.query}")
        print(f"topk={result.topk} hits={len(result.hits)}")
        for index, hit in enumerate(result.hits, start=1):
            section = str(hit.metadata.get("section_path", ""))
            print(f"[{index}] score={hit.score:.4f} chunk_id={hit.chunk_id} source_id={hit.source_id}")
            print(f"    offset={hit.offset_start}-{hit.offset_end} section={section}")
        return 0

    query = _required_query(args.query, "query")
    profile = args.profile or config.execution.default_profile
    result = RagApplicationService(config).execute(
        QueryCommand(
            query=query,
            profile=profile,
            qid=args.qid,
            run_id=args.run_id,
            topk=args.topk,
            debug=bool(args.debug_record),
        ),
        local_cli_principal(),
    )
    print(f"profile={profile} status={result.record.outcome.get('status')}")
    print(result.answer.answer_text)
    print("CITATIONS:")
    for citation in result.answer.citations:
        print(
            f"- source_id={citation.source_id} chunk_id={citation.chunk_id} "
            f"offset_start={citation.offset_start} score={citation.score}"
        )
    if args.debug_record:
        print(f"record_fingerprint={result.record.parity_fingerprint()}")
    return 0


def _required_query(value: Optional[str], mode: str) -> str:
    query = str(value or "").strip()
    if not query:
        raise SystemExit(f"ERROR: --mode {mode} requires --query")
    return query


if __name__ == "__main__":
    raise SystemExit(main())
