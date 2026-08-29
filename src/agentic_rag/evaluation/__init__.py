"""
程序作用：
提供评估子包的最小公开入口，方便调用方统一获取 CER 断言函数。

整体结构：
1）从 assertions 导入 evaluate_record；
2）通过 __all__ 限定子包对外接口。
"""

from agentic_rag.evaluation.assertions import evaluate_record

__all__ = ["evaluate_record"]
