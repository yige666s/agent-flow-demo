"""
Claude (Anthropic) 提供商实现
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from .base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """Claude (Anthropic) 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Claude API key is required")
        
        self.client = Anthropic(api_key=api_key)
        self.model = config.get("model", "claude-sonnet-4-20250514")
    
    @property
    def provider_name(self) -> str:
        return "Claude"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 Claude API"""
        try:
            request_params = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "messages": messages
            }
            
            if system:
                request_params["system"] = system
            
            if "tools" in kwargs:
                request_params["tools"] = kwargs["tools"]
            
            response = self.client.messages.create(**request_params)
            
            # 提取文本内容
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        return block.text
            
            return ""
        
        except Exception as e:
            raise Exception(f"Claude API call failed: {str(e)}")
