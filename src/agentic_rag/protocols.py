"""
作用：
- 定义 Phase A 各模块的接口协议（Protocol）
- 让实现与调用解耦，后续替换组件时不改调用方

结构：
- Loader: 文档加载器接口
- Splitter: 文本切分器接口
- Embedder: 向量化接口
- VectorStore: 向量库接口（最小接口集）
- Retriever: 检索器接口
- LLMClient: 模型调用接口
- Generator: 生成器接口
"""

from __future__ import annotations  # 启用前向引用类型标注（兼容性更好）

from typing import List, Protocol, Sequence  # 引入协议与序列类型

from .types import Answer, Chunk, Document, RetrievalResult  # 引入项目内类型


class Loader(Protocol):  # 定义 Loader 协议
    def load(self) -> List[Document]:  # 定义 load 方法：输出 Document 列表
        ...  # Protocol 方法体使用省略号占位


class Splitter(Protocol):  # 定义 Splitter 协议
    def split(self, doc: Document) -> List[Chunk]:  # 定义 split 方法：Document -> Chunk 列表
        ...  # Protocol 方法体使用省略号占位


class Embedder(Protocol):  # 定义 Embedder 协议
    def embed(self, texts: Sequence[str]) -> List[List[float]]:  # 定义 embed 方法：文本序列 -> 向量列表
        ...  # Protocol 方法体使用省略号占位


class VectorStore(Protocol):  # 定义 VectorStore 协议
    def upsert(self, chunks: List[Chunk], vectors: List[List[float]]) -> None:  # 定义 upsert：写入 chunk 与向量
        ...  # Protocol 方法体使用省略号占位

    def query(self, query_vector: List[float], topk: int) -> RetrievalResult:  # 定义 query：向量检索 topk
        ...  # Protocol 方法体使用省略号占位


class Retriever(Protocol):  # 定义 Retriever 协议
    def retrieve(self, query: str) -> RetrievalResult:  # 定义 retrieve：文本查询 -> 检索结果
        ...  # Protocol 方法体使用省略号占位


class LLMClient(Protocol):  # 定义 LLMClient 协议
    def generate(self, prompt: str) -> str:  # 定义 generate：输入 prompt -> 输出文本
        ...  # Protocol 方法体使用省略号占位


class Generator(Protocol):  # 定义 Generator 协议
    def run(self, query: str, retrieval: RetrievalResult) -> Answer:  # 定义 run：query + retrieval -> Answer
        ...  # Protocol 方法体使用省略号占位