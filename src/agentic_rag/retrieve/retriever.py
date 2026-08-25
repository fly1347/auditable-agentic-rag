# src/agentic_rag/retrieve/retriever.py
# 程序作用：
# - 第3批“检索闭环”：输入 query 文本 -> embedding -> vector store 检索 -> 返回 RetrievalResult
# - 只负责检索与打包结构化结果，不负责生成答案（第4批做）
#
# 整体结构：
# 1) 数据结构：RetrievalHit / RetrievalResult
# 2) RetrieverConfig：topk、最小分数等检索参数
# 3) Retriever：run(query) -> RetrievalResult（核心入口）

from __future__ import annotations  # 启用前向引用类型标注（兼容性更好）  # noqa: E402

from dataclasses import dataclass  # 引入 dataclass 用于结构化返回  # noqa: E402
from typing import Any, Dict, List, Optional  # 引入类型标注  # noqa: E402

from agentic_rag.embed.embeddings import EmbeddingConfig  # 引入 embedding 配置  # noqa: E402
from agentic_rag.embed.embeddings import EmbeddingModel  # 引入 embedding 模型封装  # noqa: E402
from agentic_rag.store.vector_store import LocalVectorStore  # 引入本地向量库  # noqa: E402
from agentic_rag.store.vector_store import VectorStoreConfig  # 引入向量库配置  # noqa: E402
from agentic_rag.policy.access import UserContext, anonymous_user_context, can_read_source, parse_source_acl


@dataclass  # RetrievalHit：单条命中证据  # noqa: E402
class RetrievalHit:  # noqa: E402
    chunk_id: str  # chunk 稳定 ID（source_id:seq）  # noqa: E402
    source_id: str  # 来源文档稳定 ID（相对路径）  # noqa: E402
    score: float  # 相似度分数（向量归一化时等价 cosine）  # noqa: E402
    text: str  # 命中文本片段  # noqa: E402
    offset_start: int  # 字符偏移起点  # noqa: E402
    offset_end: int  # 字符偏移终点  # noqa: E402
    metadata: Dict[str, object]  # 命中元数据（section_path 等）  # noqa: E402


@dataclass  # RetrievalResult：一次检索的结构化结果  # noqa: E402
class RetrievalResult:  # noqa: E402
    query: str  # 原始 query 文本  # noqa: E402
    topk: int  # 实际 topk  # noqa: E402
    hits: List[RetrievalHit]  # 命中列表  # noqa: E402
    access_policy: Dict[str, Any]  # TopK 前 ACL 过滤诊断  # noqa: E402


@dataclass  # RetrieverConfig：检索参数  # noqa: E402
class RetrieverConfig:  # noqa: E402
    topk: int = 5  # 默认返回 topk 条  # noqa: E402
    min_score: Optional[float] = None  # 可选最小分数过滤（None 表示不过滤）  # noqa: E402


class Retriever:  # Retriever：检索器封装  # noqa: E402
    def __init__(  # 初始化 retriever  # noqa: E402
        self,  # self  # noqa: E402
        retriever_cfg: Optional[RetrieverConfig] = None,  # 检索参数  # noqa: E402
        embed_cfg: Optional[EmbeddingConfig] = None,  # embedding 参数  # noqa: E402
        store_cfg: Optional[VectorStoreConfig] = None,  # store 参数  # noqa: E402
    ):  # init 结束  # noqa: E402
        self.cfg = retriever_cfg or RetrieverConfig()  # 应用默认检索配置  # noqa: E402
        self.embed_cfg = embed_cfg or EmbeddingConfig()  # 应用默认 embedding 配置  # noqa: E402
        self.store_cfg = store_cfg or VectorStoreConfig()  # 应用默认 store 配置  # noqa: E402
        self.embedder = EmbeddingModel(self.embed_cfg)  # 初始化 embedding 模型  # noqa: E402
        self.store = LocalVectorStore(self.store_cfg)  # 初始化向量库对象  # noqa: E402

    def run(
        self,
        query: str,
        topk: Optional[int] = None,
        user_context: Optional[UserContext] = None,
    ) -> RetrievalResult:  # run：输入 query 返回 RetrievalResult  # noqa: E402
        q = str(query)  # 规范化 query  # noqa: E402
        k = int(topk) if topk is not None else int(self.cfg.topk)  # 计算本次 topk  # noqa: E402
        qvec = self.embedder.embed([q])[0]  # 对 query 做 embedding（取第一条向量）  # noqa: E402
        user = user_context or anonymous_user_context()
        decision_counts: Dict[str, int] = {}
        visibility_counts: Dict[str, int] = {}
        denied_source_ids: set[str] = set()
        allowed_source_ids: set[str] = set()

        def access_predicate(obj: Dict[str, object]) -> bool:
            metadata = obj.get("metadata", {}) if isinstance(obj, dict) else {}
            metadata_dict = dict(metadata) if isinstance(metadata, dict) else {}
            metadata_dict.setdefault("source_id", str(obj.get("source_id", "")))
            metadata_dict.setdefault("chunk_id", str(obj.get("chunk_id", "")))
            acl = parse_source_acl(metadata_dict)
            decision = can_read_source(user, acl)
            reason = str(decision.reason)
            decision_counts[reason] = decision_counts.get(reason, 0) + 1
            visibility = str(acl.visibility) if acl is not None else "missing"
            visibility_counts[visibility] = visibility_counts.get(visibility, 0) + 1
            source_id = str(obj.get("source_id", ""))
            if decision.allowed:
                allowed_source_ids.add(source_id)
            else:
                denied_source_ids.add(source_id)
            return bool(decision.allowed)

        raw_hits = self.store.query(
            query_vector=qvec,
            topk=int(k),
            predicate=access_predicate,
        )
        hits: List[RetrievalHit] = []  # 初始化结构化命中列表  # noqa: E402
        for obj, score in raw_hits:  # 遍历原始命中  # noqa: E402
            s = float(score)  # 分数转 float  # noqa: E402
            if self.cfg.min_score is not None and s < float(self.cfg.min_score):  # 若启用最小分数过滤  # noqa: E402
                continue  # 跳过低分命中  # noqa: E402
            meta = obj.get("metadata", {}) if isinstance(obj, dict) else {}  # 提取 metadata（容错）  # noqa: E402
            hits.append(  # 追加结构化命中  # noqa: E402
                RetrievalHit(  # 构造 RetrievalHit  # noqa: E402
                    chunk_id=str(obj.get("chunk_id", "")),  # 读取 chunk_id  # noqa: E402
                    source_id=str(obj.get("source_id", "")),  # 读取 source_id  # noqa: E402
                    score=s,  # 写入 score  # noqa: E402
                    text=str(obj.get("text", "")),  # 读取 text  # noqa: E402
                    offset_start=int(obj.get("offset_start", 0)),  # 读取 offset_start  # noqa: E402
                    offset_end=int(obj.get("offset_end", 0)),  # 读取 offset_end  # noqa: E402
                    metadata=dict(meta) if isinstance(meta, dict) else {},  # 写入 metadata  # noqa: E402
                )  # hit 构造结束  # noqa: E402
            )  # append 结束  # noqa: E402
        access_policy: Dict[str, Any] = {
            "enforced_before_topk": True,
            "fail_close": True,
            "user_id": user.user_id,
            "roles": sorted(user.roles),
            "groups": sorted(user.groups),
            "tenant_id": user.tenant_id,
            "index_chunk_count": int(sum(decision_counts.values())),
            "eligible_chunk_count": int(sum(value for key, value in decision_counts.items() if key in {"public", "admin_override", "explicit_role_or_group_grant"})),
            "returned_chunk_count": len(hits),
            "decision_counts": dict(sorted(decision_counts.items())),
            "visibility_counts": dict(sorted(visibility_counts.items())),
            "allowed_source_ids": sorted(allowed_source_ids),
            "denied_source_ids": sorted(denied_source_ids),
        }
        return RetrievalResult(query=q, topk=int(k), hits=hits, access_policy=access_policy)
