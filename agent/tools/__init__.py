"""
工具模块初始化
注册所有内置工具
"""

from .base import ToolRegistry
from .http_request import HTTPRequestTool
from .file_ops import FileOpsTool
from .web_scraper import WebScraperTool
from .python_exec import PythonExecTool


def register_all_tools():
    """注册所有内置工具"""
    ToolRegistry.register(HTTPRequestTool())
    ToolRegistry.register(FileOpsTool())
    ToolRegistry.register(WebScraperTool())
    ToolRegistry.register(PythonExecTool())
    print(f"Registered {len(ToolRegistry.list_tools())} tools")


__all__ = [
    'ToolRegistry',
    'HTTPRequestTool',
    'FileOpsTool',
    'WebScraperTool',
    'PythonExecTool',
    'register_all_tools'
]
