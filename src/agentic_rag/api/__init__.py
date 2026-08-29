"""
程序作用：
标记 API 目录为 Python 子包，容纳 FastAPI 应用、路由、DTO、中间件与错误映射。

整体结构：
当前不在包级自动导入对象；各接口按需从 app、routes_*、schemas 等模块引用。
"""
