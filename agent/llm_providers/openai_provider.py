"""
OpenAI 提供商实现
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        base_url = config.get("base_url", "https://api.openai.com/v1")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = config.get("model", "gpt-4")
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 OpenAI API"""
        try:
            # OpenAI 的 system 消息需要添加到 messages 列表中
            api_messages = []
            
            if system:
                api_messages.append({
                    "role": "system",
                    "content": system
                })
            
            api_messages.extend(messages)
            
            request_params = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature)
            }
            
            if "tools" in kwargs:
                request_params["tools"] = kwargs["tools"]
            
            response = self.client.chat.completions.create(**request_params)
            
            if response.choices:
                return response.choices[0].message.content or ""
            
            return ""
        
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")
