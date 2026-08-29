"""
程序作用：
集中导出版本化索引构建目录与 current 指针解析接口。

整体结构：
1）从 current 导出 CurrentIndex、load_current_index 和 resolve_vector_store_dir；
2）通过 __all__ 固定索引子包的公开接口。
"""

from agentic_rag.indexing.current import CurrentIndex, load_current_index, resolve_vector_store_dir

__all__ = ["CurrentIndex", "load_current_index", "resolve_vector_store_dir"]
