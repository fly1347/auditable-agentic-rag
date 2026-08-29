"""
程序作用：
集中导出 baseline 与 orchestrated 两套执行引擎及其共享结果类型。

整体结构：
1）导入 BaselineEngineAdapter、OrchestratedEngine 和 EngineResult；
2）通过 __all__ 固定对外可用的引擎接口。
"""

from agentic_rag.engine.baseline import BaselineEngineAdapter, EngineResult
from agentic_rag.engine.orchestrated import OrchestratedEngine

__all__ = ["BaselineEngineAdapter", "EngineResult", "OrchestratedEngine"]
