# src/agentic_rag/ingest/loaders.py
# 程序作用：从多个输入目录（seed/cleaned 等）加载 md/txt 文档，生成 Document；同 source_id 时按优先级覆盖；计算 doc_hash 用于增量判断；Phase A 明确拒绝 PDF。
# 整体结构：
# 1) LoaderConfig：描述输入目录与优先级
# 2) load_documents：扫描目录、过滤格式、生成 Document 列表
# 3) 辅助函数：hash 计算、相对路径 source_id、基础元数据

from __future__ import annotations  # 允许前置类型注解（兼容 Python 3.10）  # noqa: E402

import hashlib  # 用于 sha256 计算  # noqa: E402
import os  # 用于路径与文件系统操作  # noqa: E402
from dataclasses import dataclass  # 用于轻量配置结构  # noqa: E402
from pathlib import Path  # 用于更稳的路径处理  # noqa: E402
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple  # 类型注解  # noqa: E402

if TYPE_CHECKING:
    from agentic_rag.policy.source_registry import SourceACLRegistry

try:  # 尝试复用项目内统一类型（第1批已定义）  # noqa: E402
    from agentic_rag.types import Document  # 统一 Document 类型  # noqa: E402
except Exception:  # 如果项目还没提供 Document，则在此提供最小兼容结构  # noqa: E402
    from dataclasses import dataclass as _dataclass  # 备用 dataclass  # noqa: E402
    from typing import Any as _Any  # 备用 Any  # noqa: E402

    @_dataclass  # 备用 Document（字段与融合版对齐）  # noqa: E402
    class Document:  # noqa: E402
        source_id: str  # 相对路径作为稳定 ID  # noqa: E402
        path: str  # 绝对路径或可打开路径  # noqa: E402
        mtime: float  # 文件修改时间（秒）  # noqa: E402
        doc_hash: str  # sha256 内容哈希  # noqa: E402
        title: Optional[str] = None  # 可选标题  # noqa: E402
        lang: Optional[str] = None  # 可选语言  # noqa: E402
        metadata: Dict[str, _Any] = None  # 扩展元数据  # noqa: E402


_ALLOWED_SUFFIXES: Tuple[str, ...] = (".md", ".txt")  # Phase A 只允许 md/txt  # noqa: E402


@dataclass  # LoaderConfig：描述一个输入根目录  # noqa: E402
class LoaderConfig:  # noqa: E402
    root_dir: Path  # 语料根目录（用于生成 source_id）  # noqa: E402
    enabled: bool = True  # 是否启用该目录  # noqa: E402
    priority: int = 0  # 优先级（越大越优先；同 source_id 时覆盖）  # noqa: E402
    tags: Optional[List[str]] = None  # 可选标签（写入 metadata）  # noqa: E402


def _read_text(path: Path) -> str:  # 读取文本文件内容  # noqa: E402
    return path.read_text(encoding="utf-8", errors="ignore")  # utf-8 优先，容错忽略坏字节  # noqa: E402


def _sha256_text(text: str) -> str:  # 对文本做 sha256  # noqa: E402
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()  # 生成十六进制哈希  # noqa: E402


def _to_posix_relpath(file_path: Path, root_dir: Path) -> str:  # 生成稳定 source_id（相对 root 的 posix 路径）  # noqa: E402
    rel = file_path.relative_to(root_dir)  # 计算相对路径  # noqa: E402
    return rel.as_posix()  # 统一为 posix 风格，跨平台稳定  # noqa: E402


def _guess_lang_from_text(text: str) -> str:  # 极简语言猜测（仅用于 metadata，不做路由）  # noqa: E402
    for ch in text[:2000]:  # 仅看前 2000 字符以降低成本  # noqa: E402
        if "\u4e00" <= ch <= "\u9fff":  # 命中常见中文范围  # noqa: E402
            return "zh"  # 返回中文  # noqa: E402
    return "unknown"  # 兜底未知  # noqa: E402


def iter_candidate_files(root_dir: Path) -> Iterable[Path]:  # 遍历 root_dir 下所有候选文件  # noqa: E402
    for p in root_dir.rglob("*"):  # 递归遍历  # noqa: E402
        if not p.is_file():  # 跳过目录等  # noqa: E402
            continue  # 继续  # noqa: E402
        if p.suffix.lower() in _ALLOWED_SUFFIXES:  # 仅允许 md/txt  # noqa: E402
            yield p  # 产出候选文件  # noqa: E402
        elif p.suffix.lower() == ".pdf":  # Phase A 明确拒绝 PDF  # noqa: E402
            continue  # 直接忽略  # noqa: E402
        else:  # 其他后缀  # noqa: E402
            continue  # 忽略  # noqa: E402


def load_documents(
    configs: List[LoaderConfig],
    *,
    acl_registry: Optional["SourceACLRegistry"] = None,
    excluded_source_ids: Optional[Iterable[str]] = None,
) -> List[Document]:  # 从多个目录加载文档并做覆盖合并  # noqa: E402
    enabled = [c for c in configs if c.enabled]  # 过滤启用项  # noqa: E402
    enabled.sort(key=lambda c: c.priority, reverse=True)  # 高优先级先处理，后写入不会覆盖先写入  # noqa: E402
    by_source_id: Dict[str, Document] = {}  # 用 source_id 去重与覆盖  # noqa: E402
    excluded = {str(item) for item in (excluded_source_ids or [])}
    for cfg in enabled:  # 遍历每个输入根目录  # noqa: E402
        root = cfg.root_dir.expanduser().resolve()  # 规范化根目录  # noqa: E402
        if not root.exists():  # 目录不存在  # noqa: E402
            continue  # 跳过  # noqa: E402
        for fp in iter_candidate_files(root):  # 遍历候选文件  # noqa: E402
            try:  # 捕获单文件异常，保证整体可继续  # noqa: E402
                text = _read_text(fp)  # 读取文本  # noqa: E402
            except Exception:  # 读取失败  # noqa: E402
                continue  # 跳过该文件  # noqa: E402
            source_id = _to_posix_relpath(fp, root)  # 生成稳定 source_id  # noqa: E402
            if source_id in excluded:
                continue
            mtime = fp.stat().st_mtime  # 获取 mtime  # noqa: E402
            doc_hash = _sha256_text(text)  # 计算内容哈希  # noqa: E402
            lang = _guess_lang_from_text(text)  # 粗略猜测语言  # noqa: E402
            meta: Dict[str, object] = {}  # 初始化 metadata  # noqa: E402
            meta["loader_root"] = root.as_posix()  # 写入根目录  # noqa: E402
            meta["suffix"] = fp.suffix.lower()  # 写入后缀  # noqa: E402
            meta["priority"] = cfg.priority  # 写入优先级  # noqa: E402
            if cfg.tags:  # 如果有 tags  # noqa: E402
                meta["tags"] = list(cfg.tags)  # 写入 tags  # noqa: E402
            doc = Document(  # 构造 Document  # noqa: E402
                source_id=source_id,  # 稳定 ID（相对路径）  # noqa: E402
                path=str(fp),  # 真实路径  # noqa: E402
                mtime=float(mtime),  # mtime  # noqa: E402
                doc_hash=doc_hash,  # 内容哈希  # noqa: E402
                title=fp.stem,  # 默认标题用文件名（不含后缀）  # noqa: E402
                lang=lang,  # 语言  # noqa: E402
                metadata=meta,  # 元数据  # noqa: E402
            )  # Document 完成  # noqa: E402
            if acl_registry is not None:
                doc = acl_registry.attach(doc)
            if source_id not in by_source_id:  # 首次出现  # noqa: E402
                by_source_id[source_id] = doc  # 直接写入  # noqa: E402
            else:  # 已存在则按“优先级覆盖”  # noqa: E402
                existing = by_source_id[source_id]  # 取已有文档  # noqa: E402
                existing_p = int(getattr(existing, "metadata", {}).get("priority", -10**9))  # 提取已有优先级  # noqa: E402
                if cfg.priority >= existing_p:  # 新文档优先级更高或相等  # noqa: E402
                    by_source_id[source_id] = doc  # 覆盖  # noqa: E402
    docs = list(by_source_id.values())  # 转为列表  # noqa: E402
    docs.sort(key=lambda d: d.source_id)  # 结果排序稳定  # noqa: E402
    return docs  # 返回文档列表  # noqa: E402
