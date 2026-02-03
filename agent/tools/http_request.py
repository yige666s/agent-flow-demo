"""
HTTP 请求工具
"""

import requests
from typing import Any, Dict, Optional
from .base import BaseTool, ToolSchema, ToolParameter


class HTTPRequestTool(BaseTool):
    """HTTP 请求工具"""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="http_request",
            description="发起 HTTP 请求，支持 GET、POST、PUT、DELETE 等方法。返回包含 status_code、headers、body（文本）和 json（如果响应是 JSON 格式）的结果",
            parameters={
                "url": ToolParameter(
                    name="url",
                    type="string",
                    description="请求 URL",
                    required=True
                ),
                "method": ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP 方法",
                    required=True,
                    enum=["GET", "POST", "PUT", "DELETE", "PATCH"]
                ),
                "headers": ToolParameter(
                    name="headers",
                    type="object",
                    description="请求头",
                    required=False
                ),
                "body": ToolParameter(
                    name="body",
                    type="string",
                    description="请求体（JSON 字符串）",
                    required=False
                ),
                "timeout": ToolParameter(
                    name="timeout",
                    type="number",
                    description="超时时间（秒）",
                    required=False,
                    default=10
                )
            },
            timeout=30
        )
    
    def execute(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                data=body,
                timeout=timeout
            )
            
            # 尝试解析 JSON 响应
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "success": 200 <= response.status_code < 300
            }
            
            # 如果是 JSON 响应，添加解析后的数据
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type or response.text.strip().startswith(('{', '[')):
                try:
                    json_data = response.json()
                    result["json"] = json_data
                    
                    # 智能展开：如果是字典，将其字段合并到顶层（不覆盖现有字段）
                    # 这样可以让 Planner 生成的代码更容易访问数据，例如 input_data['items'] 而不是 input_data['json']['items']
                    if isinstance(json_data, dict):
                        for k, v in json_data.items():
                            if k not in result:
                                result[k] = v
                except ValueError:
                    pass  # 如果解析失败，只保留 body 文本
            
            return result
        
        except requests.RequestException as e:
            return {
                "status_code": 0,
                "error": str(e),
                "success": False
            }
