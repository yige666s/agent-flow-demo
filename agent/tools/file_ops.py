"""
文件操作工具 - 增强版
支持更多格式、更好的错误处理和自动类型转换
"""

import os
import json
from typing import Any, Dict, Union
from .base import BaseTool, ToolSchema, ToolParameter


class FileOpsTool(BaseTool):
    """文件读写工具（增强版）"""
    
    def __init__(self):
        """初始化文件操作工具，设置用户文件基础目录"""
        # 获取项目根目录（agent 的上级目录）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        # 使用 backend/data/user 目录
        self.user_data_dir = os.path.join(project_root, "backend", "data", "user")
        os.makedirs(self.user_data_dir, exist_ok=True)
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="file_ops",
            description=(
                "文件读写操作工具。支持读取、写入、追加文本/JSON文件。\n"
                "写入操作会自动保存到 data/user 目录。\n"
                "支持自动格式转换：字典/列表会自动转为美观的 JSON 格式。"
            ),
            parameters={
                "operation": ToolParameter(
                    name="operation",
                    type="string",
                    description="操作类型：read(读取)、write(写入/覆盖)、append(追加)",
                    required=True,
                    enum=["read", "write", "append"]
                ),
                "path": ToolParameter(
                    name="path",
                    type="string",
                    description="文件名（不需要完整路径，会自动保存到 data/user 目录）",
                    required=True
                ),
                "content": ToolParameter(
                    name="content",
                    type="any",
                    description="要写入的内容（write/append 操作必需）。支持字符串、字典、列表，会自动转换为适当格式",
                    required=False
                ),
                "encoding": ToolParameter(
                    name="encoding",
                    type="string",
                    description="文件编码，默认 utf-8",
                    required=False,
                    default="utf-8"
                )
            },
            timeout=10
        )
    
    def _get_full_path(self, filename: str, operation: str = "write") -> str:
        """获取完整的文件路径"""
        # 清理文件名，移除路径遍历攻击字符
        filename = os.path.basename(filename.replace("../", "").replace("..\\", ""))
        
        if operation in ["write", "append"]:
            return os.path.join(self.user_data_dir, filename)
        
        # 读取操作：优先用户目录，然后相对路径
        user_path = os.path.join(self.user_data_dir, filename)
        if os.path.exists(user_path):
            return user_path
        return filename
    
    def _convert_content(self, content: Any) -> str:
        """智能转换内容为字符串"""
        if content is None:
            return ""
        if isinstance(content, str):
            # 尝试检测是否是 JSON 字符串，如果是则美化
            try:
                parsed = json.loads(content)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                # 尝试解析 Python 字典字符串表示（如 "{'key': 'value'}"）
                try:
                    import ast
                    parsed = ast.literal_eval(content)
                    if isinstance(parsed, (dict, list)):
                        return json.dumps(parsed, ensure_ascii=False, indent=2)
                except (ValueError, SyntaxError):
                    pass
                return content
        if isinstance(content, (dict, list)):
            return json.dumps(content, ensure_ascii=False, indent=2)
        return str(content)
    
    def _safe_read_json(self, content: str) -> Union[dict, list, None]:
        """安全解析 JSON，支持容错"""
        if not content.strip():
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            try:
                # 移除 BOM
                cleaned = content.lstrip('\ufeff')
                # 移除尾部逗号
                cleaned = cleaned.replace(",]", "]").replace(",}", "}")
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None
    
    def execute(
        self,
        operation: str,
        path: str,
        content: Any = None,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """执行文件操作"""
        # 参数规范化
        operation = str(operation).lower().strip()
        path = str(path).strip()
        encoding = encoding or "utf-8"
        
        if not path:
            return {"success": False, "error": "文件路径不能为空"}
        
        try:
            if operation == "read":
                full_path = self._get_full_path(path, "read")
                
                if not os.path.exists(full_path):
                    return {
                        "success": False,
                        "error": f"文件不存在: {path}",
                        "searched_path": full_path
                    }
                
                with open(full_path, 'r', encoding=encoding, errors='replace') as f:
                    file_content = f.read()
                
                result = {
                    "success": True,
                    "content": file_content,
                    "size": len(file_content),
                    "path": full_path
                }
                
                # 尝试解析 JSON
                json_data = self._safe_read_json(file_content)
                if json_data is not None:
                    result["json"] = json_data
                    result["is_json"] = True
                
                return result
            
            elif operation in ["write", "append"]:
                if content is None:
                    return {"success": False, "error": f"{operation} 操作需要提供 content 参数"}
                
                full_path = self._get_full_path(path, operation)
                content_str = self._convert_content(content)
                
                # 确保目录存在
                dir_path = os.path.dirname(full_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                mode = 'w' if operation == "write" else 'a'
                with open(full_path, mode, encoding=encoding) as f:
                    f.write(content_str)
                
                return {
                    "success": True,
                    "operation": operation,
                    "path": full_path,
                    "size": len(content_str),
                    "message": f"文件{'写入' if operation == 'write' else '追加'}成功"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"未知操作类型: {operation}",
                    "valid_operations": ["read", "write", "append"]
                }
        
        except PermissionError:
            return {"success": False, "error": f"没有权限访问文件: {path}"}
        except UnicodeDecodeError as e:
            return {"success": False, "error": f"编码错误: {e}，尝试使用其他编码如 'gbk' 或 'latin-1'"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
