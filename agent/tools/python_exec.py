"""
Python 代码执行工具
"""

from typing import Any, Dict
import json
import re
from .base import BaseTool, ToolSchema, ToolParameter


class PythonExecTool(BaseTool):
    """Python 代码执行工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="python_exec",
            description="执行 Python 代码片段进行数据处理和转换",
            parameters={
                "code": ToolParameter(
                    name="code",
                    type="string",
                    description="要执行的 Python 代码，可以访问 'input_data' 变量，需要将结果赋值给 'output' 变量",
                    required=True
                ),
                "input_data": ToolParameter(
                    name="input_data",
                    type="any",
                    description="传入代码的输入数据",
                    required=False
                )
            },
            timeout=30
        )
    
    def execute(self, code: str, input_data: Any = None) -> Dict[str, Any]:
        """执行 Python 代码"""
        try:
            # 创建受限的执行环境
            allowed_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sorted': sorted,
                    'max': max,
                    'min': min,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'print': print,
                },
                'json': json,
                're': re,
            }
            
            # 准备局部变量
            local_vars = {
                'input_data': input_data,
                'output': None
            }
            
            # 执行代码
            exec(code, allowed_globals, local_vars)
            
            # 获取输出
            output = local_vars.get('output')
            
            return {
                "success": True,
                "output": output
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
