"""
程序作用：
提供从 CanonicalExecutionRecord 生成确定性评估报告的统一公开入口。

整体结构：
1）从 evaluation 导入 build_evaluation_reports；
2）通过 __all__ 固定报告子包的公开接口。
"""

from agentic_rag.reporting.evaluation import build_evaluation_reports

__all__ = ["build_evaluation_reports"]
