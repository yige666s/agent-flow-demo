"""
工具基类与注册中心
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import json


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string, number, boolean, object, array
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolSchema:
    """工具元数据"""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]
    timeout: int = 30  # 超时时间（秒）
    
    def to_llm_schema(self) -> Dict[str, Any]:
        """转换为 LLM Function Calling Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param_name: {
                        "type": param.type,
                        "description": param.description,
                        **({"enum": param.enum} if param.enum else {}),
                    }
                    for param_name, param in self.parameters.items()
                },
                "required": [
                    param_name 
                    for param_name, param in self.parameters.items() 
                    if param.required
                ]
            }
        }


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """返回工具 Schema"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """参数验证"""
        for param_name, param_def in self.schema.parameters.items():
            if param_def.required and param_name not in parameters:
                raise ValueError(f"Missing required parameter: {param_name}")
        return True


class ToolRegistry:
    """工具注册中心"""
    
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        """注册工具"""
        cls._tools[tool.schema.name] = tool
        print(f"Tool registered: {tool.schema.name}")
    
    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        """获取工具"""
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not found")
        return cls._tools[name]
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """列出所有工具名称"""
        return list(cls._tools.keys())
    
    @classmethod
    def get_all_schemas_for_llm(cls) -> str:
        """返回所有工具的 Schema（用于 LLM Prompt）"""
        schemas = []
        for tool in cls._tools.values():
            schemas.append(tool.schema.to_llm_schema())
        return json.dumps(schemas, indent=2, ensure_ascii=False)
    
    @classmethod
    def execute_tool(cls, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具"""
        tool = cls.get_tool(tool_name)
        tool.validate_parameters(parameters)
        return tool.execute(**parameters)
