# 程序作用：实现 Phase C Step 8 的 ingest / documents 服务逻辑。
# 整体结构：
# 1) ingest_upload：校验上传文件 -> 保存到 corpus -> 全量 rebuild index -> 返回统计。
# 2) list_documents：扫描 data/corpus/phase_a/internal 与 external，返回最小文档信息。
# 3) delete_document：按 doc_id 删除 corpus 文件 -> 全量 rebuild index。
# 4) rebuild 回滚：rebuild 失败时恢复 vector store / manifest 旧文件，避免污染索引状态。
# 说明：本阶段不做增量索引、不做数据库、不支持 PDF；local_npy_jsonl 写入仍由 ingest_pipeline.index_corpus 接管。

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.parse import unquote

from fastapi import UploadFile

from agentic_rag.ingest.ingest_pipeline import index_corpus


ALLOWED_SUFFIXES = {".md", ".txt"}
ALLOWED_SOURCE_CATEGORIES = {"internal", "external"}


class UnsupportedFileTypeError(ValueError):
    """上传文件类型不受支持。"""


class EmptyDocumentError(ValueError):
    """上传文档为空。"""


class UploadTooLargeError(ValueError):
    """上传文档超过管理面配置上限。"""


class InvalidDocumentIdError(ValueError):
    """doc_id 非法或存在路径穿越风险。"""


class DocumentNotFoundError(FileNotFoundError):
    """待删除文档不存在。"""


class VectorStoreRebuildError(RuntimeError):
    """索引重建失败。"""


class IngestService:
    """封装文档上传、文档列表、文档删除与全量索引重建。"""

    def __init__(
        self,
        corpus_dir: str = "data/corpus/phase_a",
        vector_store_dir: str = "artifacts/vector_store",
        manifest_path: str = "artifacts/index/manifest.json",
        artifacts_dir: str = "artifacts",
        acl_registry_path: str = "policy/source_acl.yaml",
        max_upload_bytes: int = 2_000_000,
        on_index_published: Optional[Callable[[], None]] = None,
    ) -> None:
        self.corpus_dir = Path(corpus_dir).expanduser().resolve()
        self.vector_store_dir = Path(vector_store_dir).expanduser().resolve()
        self.manifest_path = Path(manifest_path).expanduser().resolve()
        self.artifacts_dir = Path(artifacts_dir).expanduser().resolve()
        self.acl_registry_path = Path(acl_registry_path).expanduser().resolve()
        self.max_upload_bytes = int(max_upload_bytes)
        self.on_index_published = on_index_published

    async def ingest_upload(self, file: UploadFile, source_category: str = "external") -> Dict[str, object]:
        """保存上传文档并触发全量 rebuild。"""
        category = self._validate_source_category(source_category)
        original_filename = self._validate_filename(file.filename or "")
        suffix = Path(original_filename).suffix.lower()

        if suffix not in ALLOWED_SUFFIXES:
            raise UnsupportedFileTypeError("仅支持 .md / .txt 文档上传。")

        raw = await file.read()
        if len(raw) > self.max_upload_bytes:
            raise UploadTooLargeError(
                f"上传文档超过 {self.max_upload_bytes} bytes 上限。"
            )
        if not raw or not raw.strip():
            raise EmptyDocumentError("上传文档为空，未写入 corpus。")

        text = raw.decode("utf-8", errors="ignore")
        if not text.strip():
            raise EmptyDocumentError("上传文档解码后为空，未写入 corpus。")

        target_dir = self.corpus_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._next_available_path(target_dir / original_filename)

        target_path.write_text(text, encoding="utf-8")

        try:
            stats = self._rebuild_index_with_rollback()
        except Exception as exc:
            # 上传后 rebuild 失败，需要删除新文件并恢复旧索引。
            if target_path.exists():
                target_path.unlink()
            raise exc

        doc_id = self._to_doc_id(target_path)
        return {
            "status": "success",
            "doc_id": doc_id,
            "source_category": category,
            "saved_path": target_path.as_posix(),
            "size_bytes": int(target_path.stat().st_size),
            "mtime": float(target_path.stat().st_mtime),
            "doc_count": int(stats.doc_count),
            "chunk_count": int(stats.chunk_count),
            "vector_count": int(stats.chunk_count),
            "embedding_model": str(stats.embed_model),
            "embedding_dim": int(stats.dim),
            "index_time_ms": int(stats.index_time_ms),
        }

    def list_documents(self, source_category: Optional[str] = None) -> List[Dict[str, object]]:
        """扫描 corpus 目录，返回 md/txt 文档最小信息。"""
        categories = [self._validate_source_category(source_category)] if source_category else ["internal", "external"]

        documents: List[Dict[str, object]] = []
        for category in categories:
            root = self.corpus_dir / category
            if not root.exists():
                continue
            for path in self._iter_document_files(root):
                stat = path.stat()
                documents.append(
                    {
                        "doc_id": self._to_doc_id(path),
                        "source_category": category,
                        "path": path.as_posix(),
                        "filename": path.name,
                        "suffix": path.suffix.lower(),
                        "size_bytes": int(stat.st_size),
                        "mtime": float(stat.st_mtime),
                    }
                )

        documents.sort(key=lambda item: str(item["doc_id"]))
        return documents

    def delete_document(self, doc_id: str) -> Dict[str, object]:
        """删除指定文档并触发全量 rebuild。"""
        target_path = self._resolve_doc_id(doc_id)
        if not target_path.exists() or not target_path.is_file():
            raise DocumentNotFoundError(f"文档不存在：{doc_id}")

        if target_path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise InvalidDocumentIdError("只允许删除 corpus 下的 .md / .txt 文档。")

        backup_path = self._make_deleted_file_backup(target_path)
        target_path.unlink()

        try:
            stats = self._rebuild_index_with_rollback()
        except Exception as exc:
            # 删除后 rebuild 失败，需要恢复被删文件。
            if backup_path.exists() and not target_path.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup_path), str(target_path))
            raise exc
        finally:
            if backup_path.exists():
                backup_path.unlink()

        return {
            "status": "success",
            "deleted_doc_id": self._to_doc_id(target_path),
            "deleted_path": target_path.as_posix(),
            "doc_count": int(stats.doc_count),
            "chunk_count": int(stats.chunk_count),
            "vector_count": int(stats.chunk_count),
            "embedding_model": str(stats.embed_model),
            "embedding_dim": int(stats.dim),
            "index_time_ms": int(stats.index_time_ms),
        }

    def _rebuild_index_with_rollback(self):
        """Build immutably; failure leaves the previous current.json untouched."""
        try:
            stats = index_corpus(
                corpus_dir=self.corpus_dir.as_posix(),
                rebuild=True,
                artifacts_dir=self.artifacts_dir.as_posix(),
                acl_registry_path=self.acl_registry_path.as_posix(),
            )
            if self.on_index_published is not None:
                self.on_index_published()
            return stats
        except Exception as exc:
            raise VectorStoreRebuildError(
                f"索引重建失败；旧 current.json 未切换：{exc}"
            ) from exc

    def _validate_source_category(self, source_category: Optional[str]) -> str:
        """校验 source_category。"""
        category = (source_category or "external").strip().lower()
        if category not in ALLOWED_SOURCE_CATEGORIES:
            raise ValueError("source_category 只能是 internal 或 external。")
        return category

    def _validate_filename(self, filename: str) -> str:
        """清理并校验上传文件名。"""
        name = Path(filename).name.strip()
        if not name:
            raise ValueError("文件名不能为空。")
        if name in {".", ".."}:
            raise ValueError("文件名非法。")
        if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
            raise UnsupportedFileTypeError("仅支持 .md / .txt 文档上传。")

        # 保留中文、英文、数字、常见分隔符；其他字符压成下划线，避免路径异常。
        stem = Path(name).stem
        suffix = Path(name).suffix.lower()
        safe_stem = re.sub(r"[^\w\u4e00-\u9fff.\-]+", "_", stem).strip("._-")
        if not safe_stem:
            safe_stem = f"uploaded_{int(time.time())}"
        return f"{safe_stem}{suffix}"

    def _next_available_path(self, path: Path) -> Path:
        """若同名文件已存在，自动追加序号，避免覆盖现有 corpus。"""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        idx = 1
        while True:
            candidate = parent / f"{stem}_{idx}{suffix}"
            if not candidate.exists():
                return candidate
            idx += 1

    def _iter_document_files(self, root: Path) -> Iterable[Path]:
        """遍历指定目录下的 md/txt 文件。"""
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES:
                yield path

    def _to_doc_id(self, path: Path) -> str:
        """把 corpus 内文件路径转成稳定 doc_id。"""
        rel = path.resolve().relative_to(self.corpus_dir)
        return rel.as_posix()

    def _resolve_doc_id(self, doc_id: str) -> Path:
        """把 doc_id 解析为 corpus 内安全路径，禁止路径穿越。"""
        raw_doc_id = unquote(str(doc_id or "")).strip()
        if not raw_doc_id:
            raise InvalidDocumentIdError("doc_id 不能为空。")

        candidate = (self.corpus_dir / raw_doc_id).expanduser().resolve()
        try:
            candidate.relative_to(self.corpus_dir)
        except ValueError as exc:
            raise InvalidDocumentIdError("doc_id 超出 corpus 目录范围。") from exc

        parts = candidate.relative_to(self.corpus_dir).parts
        if not parts or parts[0] not in ALLOWED_SOURCE_CATEGORIES:
            raise InvalidDocumentIdError("doc_id 必须位于 internal 或 external 目录下。")

        return candidate

    def _make_deleted_file_backup(self, path: Path) -> Path:
        """为待删除文件创建临时备份，便于 rebuild 失败时回滚。"""
        backup_dir = Path(tempfile.mkdtemp(prefix="agentic_rag_deleted_doc_"))
        backup_path = backup_dir / path.name
        shutil.copy2(path, backup_path)
        return backup_path
