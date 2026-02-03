"""
阿里通义千问 (Qwen) 提供商实现
"""

from typing import List, Dict, Any, Optional
import dashscope
from .base import BaseLLMProvider


class QwenProvider(BaseLLMProvider):
    """通义千问提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Qwen API key is required")
        
        dashscope.api_key = api_key
        self.model = config.get("model", "qwen-max")
    
    @property
    def provider_name(self) -> str:
        return "Qwen"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用通义千问 API"""
        try:
            # 通义千问的 system 消息需要添加到 messages 列表中
            api_messages = []
            
            if system:
                api_messages.append({
                    "role": "system",
                    "content": system
                })
            
            api_messages.extend(messages)
            
            response = dashscope.Generation.call(
                model=self.model,
                messages=api_messages,
                result_format='message',
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content or ""
            else:
                raise Exception(f"API returned error: {response.message}")
        
        except Exception as e:
            raise Exception(f"Qwen API call failed: {str(e)}")
