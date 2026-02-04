"""
HTTP 请求工具 - 增强版
支持更好的错误处理、自动重试、请求体类型转换
"""

import requests
import json
from typing import Any, Dict, Optional, Tuple
from .base import BaseTool, ToolSchema, ToolParameter


class HTTPRequestTool(BaseTool):
    """HTTP 请求工具（增强版）"""
    
    # 常用 User-Agent
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="http_request",
            description=(
                "发起 HTTP 请求工具。支持 GET/POST/PUT/DELETE/PATCH 方法。\n"
                "自动处理 JSON 响应，支持自动重试和超时控制。\n"
                "返回包含 status_code、headers、body、json（如果是JSON响应）的结果。"
            ),
            parameters={
                "url": ToolParameter(
                    name="url",
                    type="string",
                    description="请求 URL（必须以 http:// 或 https:// 开头）",
                    required=True
                ),
                "method": ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP 方法",
                    required=False,
                    default="GET",
                    enum=["GET", "POST", "PUT", "DELETE", "PATCH"]
                ),
                "headers": ToolParameter(
                    name="headers",
                    type="object",
                    description="请求头（可选），会自动添加 User-Agent",
                    required=False
                ),
                "body": ToolParameter(
                    name="body",
                    type="any",
                    description="请求体（可选）。字符串直接发送，字典/列表自动转为 JSON",
                    required=False
                ),
                "timeout": ToolParameter(
                    name="timeout",
                    type="number",
                    description="超时时间（秒），默认 15",
                    required=False,
                    default=15
                ),
                "max_retries": ToolParameter(
                    name="max_retries",
                    type="number",
                    description="失败重试次数，默认 2",
                    required=False,
                    default=2
                ),
                "simple_response": ToolParameter(
                    name="simple_response",
                    type="boolean",
                    description="简化响应（默认 true）。true 时只返回核心数据（body/json），false 时返回完整的 HTTP 响应信息",
                    required=False,
                    default=True
                )
            },
            timeout=60
        )
    
    def _normalize_url(self, url: str) -> str:
        """规范化 URL"""
        url = str(url).strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _prepare_body(self, body: Any) -> Tuple[Optional[str], Optional[Dict]]:
        """准备请求体，返回 (data, json_body)"""
        if body is None:
            return None, None
        if isinstance(body, str):
            # 尝试解析为 JSON
            try:
                json.loads(body)
                return body, None
            except (json.JSONDecodeError, TypeError):
                return body, None
        if isinstance(body, (dict, list)):
            return None, body
        return str(body), None
    
    def _truncate_body(self, body: str, max_length: int = 50000) -> str:
        """截断过长的响应体"""
        if len(body) > max_length:
            return body[:max_length] + f"\n... [截断，原始长度: {len(body)} 字符]"
        return body
    
    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        timeout: int = 15,
        max_retries: int = 2,
        simple_response: bool = True
    ) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        # 参数规范化
        url = self._normalize_url(url)
        method = str(method).upper().strip() if method else "GET"
        timeout = max(1, min(int(timeout or 15), 120))  # 限制 1-120 秒
        max_retries = max(0, min(int(max_retries or 2), 5))  # 限制 0-5 次
        
        # 准备请求头
        request_headers = {"User-Agent": self.DEFAULT_USER_AGENT}
        if headers:
            if isinstance(headers, dict):
                request_headers.update(headers)
            elif isinstance(headers, str):
                try:
                    request_headers.update(json.loads(headers))
                except json.JSONDecodeError:
                    pass
        
        # 准备请求体
        data_body, json_body = self._prepare_body(body)
        if json_body and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        
        # 执行请求（带重试）
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data_body,
                    json=json_body,
                    timeout=timeout,
                    allow_redirects=True
                )
                content_type = response.headers.get('Content-Type', '')
                is_json_response = 'application/json' in content_type or response.text.strip().startswith(('{', '['))
                json_data = None
                
                if is_json_response:
                    try:
                        json_data = response.json()
                    except (ValueError, json.JSONDecodeError):
                        pass
                
                # 构建结果 - 根据 simple_response 参数决定返回格式
                if simple_response:
                    # 简化模式：只返回核心数据
                    if json_data is not None:
                        # JSON 响应：直接返回解析后的数据
                        result = {
                            "success": 200 <= response.status_code < 400,
                            "data": json_data,
                            "url": response.url
                        }
                    else:
                        # 非 JSON 响应：返回文本内容
                        response_body = self._truncate_body(response.text)
                        result = {
                            "success": 200 <= response.status_code < 400,
                            "data": response_body,
                            "url": response.url
                        }
                else:
                    # 详细模式：返回完整的 HTTP 响应信息
                    response_body = self._truncate_body(response.text)
                    result = {
                        "success": 200 <= response.status_code < 400,
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response_body,
                        "url": response.url,
                        "encoding": response.encoding
                    }
                    
                    if json_data is not None:
                        result["json"] = json_data
                        result["is_json"] = True
                    else:
                        result["is_json"] = False
                
                return result
                
            except requests.exceptions.Timeout:
                last_error = f"请求超时（{timeout}秒）"
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接失败: {str(e)}"
            except requests.exceptions.TooManyRedirects:
                last_error = "重定向次数过多"
            except requests.exceptions.RequestException as e:
                last_error = str(e)
            
            # 如果还有重试机会，继续
            if attempt < max_retries:
                continue
        
        # 所有重试都失败
        return {
            "success": False,
            "status_code": 0,
            "error": last_error,
            "url": url,
            "attempts": max_retries + 1
        }
