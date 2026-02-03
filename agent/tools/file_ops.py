"""
文件操作工具
"""

import os
import json
from typing import Any, Dict
from .base import BaseTool, ToolSchema, ToolParameter


class FileOpsTool(BaseTool):
    """文件读写工具"""
    
    def __init__(self):
        """初始化文件操作工具，设置用户文件基础目录"""
        self.user_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "user")
        os.makedirs(self.user_data_dir, exist_ok=True)
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="file_ops",
            description="文件读写操作，支持读取和写入文本、JSON 文件。写入操作会自动保存到 data/user 目录",
            parameters={
                "operation": ToolParameter(
                    name="operation",
                    type="string",
                    description="操作类型",
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
                    description="要写入的内容（write/append 操作必需），支持字符串、字典或列表，字典和列表会自动转换为 JSON 格式",
                    required=False
                ),
                "encoding": ToolParameter(
                    name="encoding",
                    type="string",
                    description="文件编码",
                    required=False,
                    default="utf-8"
                )
            },
            timeout=10
        )
    
    def _get_full_path(self, filename: str, operation: str = "write") -> str:
        """获取完整的文件路径"""
        # 对于写入操作，使用 data/user 目录
        if operation in ["write", "append"]:
            # 如果路径中包含目录分隔符，移除它
            filename = os.path.basename(filename)
            return os.path.join(self.user_data_dir, filename)
        
        # 对于读取操作，先尝试用户目录，再尝试相对路径
        user_path = os.path.join(self.user_data_dir, os.path.basename(filename))
        if os.path.exists(user_path):
            return user_path
        return filename
    
    def execute(
        self,
        operation: str,
        path: str,
        content: Any = None,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """执行文件操作"""
        try:
            if operation == "read":
                full_path = self._get_full_path(path, "read")
                with open(full_path, 'r', encoding=encoding) as f:
                    file_content = f.read()
                
                # 尝试解析为 JSON
                try:
                    json_content = json.loads(file_content)
                    return {
                        "success": True,
                        "content": file_content,
                        "json": json_content,
                        "size": len(file_content)
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "content": file_content,
                        "size": len(file_content)
                    }
            
            elif operation == "write":
                if content is None:
                    raise ValueError("Content is required for write operation")
                
                full_path = self._get_full_path(path, "write")
                
                # 如果 content 是字典或列表，转换为 JSON 字符串
                if isinstance(content, (dict, list)):
                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                elif not isinstance(content, str):
                    content_str = str(content)
                else:
                    content_str = content
                
                # 确保目录存在
                os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else ".", exist_ok=True)
                
                with open(full_path, 'w', encoding=encoding) as f:
                    f.write(content_str)
                
                return {
                    "success": True,
                    "path": full_path,
                    "size": len(content_str)
                }
            
            elif operation == "append":
                if content is None:
                    raise ValueError("Content is required for append operation")
                
                full_path = self._get_full_path(path, "append")
                
                # 如果 content 是字典或列表，转换为 JSON 字符串
                if isinstance(content, (dict, list)):
                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                elif not isinstance(content, str):
                    content_str = str(content)
                else:
                    content_str = content
                
                with open(full_path, 'a', encoding=encoding) as f:
                    f.write(content_str)
                
                return {
                    "success": True,
                    "path": full_path,
                    "appended_size": len(content_str)
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
