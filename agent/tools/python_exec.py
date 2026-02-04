"""
Python 代码执行工具 - 增强版（受限沙箱）
更多内置函数、更好的错误信息、输出限制
"""

from __future__ import annotations

from typing import Any, Dict
import json
import re
import datetime
import math
from collections import Counter, defaultdict

from .base import BaseTool, ToolSchema, ToolParameter


class PythonExecTool(BaseTool):
    """Python 代码执行工具（增强版沙箱）"""
    
    # 输出最大长度限制
    MAX_OUTPUT_LENGTH = 100000
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="python_exec",
            description=(
                "在受限沙箱中执行 Python 代码片段。\n"
                "已预置模块：json, re, datetime, math, Counter, defaultdict\n"
                "无需 import，直接使用即可。"
            ),
            parameters={
                "code": ToolParameter(
                    name="code",
                    type="string",
                    description=(
            "python_exec 的规则：\n"
            "- 只编写有效的 Python 代码\n"
            "- 不要使用 import 语句（模块已预先导入）\n"
            "- input_data 可作为变量使用\n"
            "- 将最终结果赋值给名为 output 的变量\n"
            "- 除非调试需要，否则不要打印输出\n"
            "- 可用模块: json、re、datetime、math、Counter、defaultdict"
                    ),
                    required=True
                ),
                "input_data": ToolParameter(
                    name="input_data",
                    type="any",
                    description="传入代码的输入数据（将作为变量 input_data 提供给代码）",
                    required=False
                )
            },
            timeout=30
        )
    
    def _truncate_output(self, output: Any) -> Any:
        """截断过大的输出"""
        if isinstance(output, str) and len(output) > self.MAX_OUTPUT_LENGTH:
            return output[:self.MAX_OUTPUT_LENGTH] + f"... [截断，原始长度: {len(output)}]"
        if isinstance(output, (list, dict)):
            try:
                json_str = json.dumps(output, ensure_ascii=False)
                if len(json_str) > self.MAX_OUTPUT_LENGTH:
                    return {"_truncated": True, "_message": f"输出过大（{len(json_str)} 字符），已截断", "_preview": str(output)[:1000]}
            except (TypeError, ValueError):
                pass
        return output
    
    def _format_error(self, e: Exception, code: str) -> Dict[str, Any]:
        """格式化错误信息，提供更有帮助的提示"""
        error_msg = str(e)
        error_type = type(e).__name__
        
        hints = []
        
        # 常见错误提示
        if "import" in error_msg.lower() or "__import__" in error_msg:
            hints.append("不要使用 import 语句，直接使用预置模块：json, re, datetime, math, Counter, defaultdict")
        
        if "NameError" in error_type:
            if "input_data" in error_msg:
                hints.append("确保 input_data 参数已传入")
            else:
                hints.append("变量未定义，请检查变量名拼写")
        
        if "SyntaxError" in error_type:
            hints.append("Python 语法错误，请检查代码格式（括号匹配、缩进等）")
        
        if "TypeError" in error_type:
            hints.append("类型错误，请检查操作是否适用于该数据类型")
        
        if "KeyError" in error_type:
            hints.append("字典键不存在，请使用 .get() 方法安全访问")
        
        if "IndexError" in error_type:
            hints.append("列表索引越界，请先检查列表长度")
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": error_type,
            "hints": hints if hints else None
        }
    
    def execute(self, code: str, input_data: Any = None) -> Dict[str, Any]:
        """执行 Python 代码"""
        # 参数规范化
        if not code or not isinstance(code, str):
            return {"success": False, "error": "code 参数必须是非空字符串"}
        
        code = code.strip()
        
        # 检查危险操作
        dangerous_patterns = [
            r'\bopen\s*\(',
            r'\bexec\s*\(',
            r'\beval\s*\(',
            r'\b__import__\s*\(',
            r'\bos\.',
            r'\bsys\.',
            r'\bsubprocess\.',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return {
                    "success": False,
                    "error": f"代码包含禁止的操作: {pattern}",
                    "hints": ["沙箱环境禁止文件操作、系统调用等危险操作"]
                }
        
        try:
            # 创建受限的执行环境
            allowed_globals = {
                "__builtins__": {
                    # 基础类型
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "frozenset": frozenset,
                    "bytes": bytes,
                    "bytearray": bytearray,
                    
                    # 迭代器
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "reversed": reversed,
                    "iter": iter,
                    "next": next,
                    
                    # 排序和比较
                    "sorted": sorted,
                    "max": max,
                    "min": min,
                    "sum": sum,
                    "abs": abs,
                    "round": round,
                    "pow": pow,
                    "divmod": divmod,
                    
                    # 类型检查
                    "isinstance": isinstance,
                    "issubclass": issubclass,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    "setattr": setattr,
                    "type": type,
                    "callable": callable,
                    
                    # 逻辑
                    "any": any,
                    "all": all,
                    
                    # 字符串
                    "chr": chr,
                    "ord": ord,
                    "repr": repr,
                    "ascii": ascii,
                    "format": format,
                    
                    # 其他
                    "slice": slice,
                    "id": id,
                    "hash": hash,
                    "bin": bin,
                    "hex": hex,
                    "oct": oct,
                    "print": print,  # 调试用
                    
                    # 异常（只读）
                    "Exception": Exception,
                    "ValueError": ValueError,
                    "TypeError": TypeError,
                    "KeyError": KeyError,
                    "IndexError": IndexError,
                },
                
                # 预置模块
                "json": json,
                "re": re,
                "datetime": datetime,
                "math": math,
                "Counter": Counter,
                "defaultdict": defaultdict,
            }
            
            local_vars = {
                "input_data": input_data,
                "output": None,
            }
            
            # 执行代码
            exec(code, allowed_globals, local_vars)
            
            # 获取并截断输出
            output = local_vars.get("output")
            output = self._truncate_output(output)
            
            return {
                "success": True,
                "output": output,
            }
            
        except Exception as e:
            return self._format_error(e, code)
