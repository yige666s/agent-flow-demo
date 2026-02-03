"""
LLM 提供商抽象基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json


class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化提供商
        
        Args:
            config: 提供商配置字典
        """
        self.config = config
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        对话接口
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            system: 系统提示词
            **kwargs: 其他参数
        
        Returns:
            LLM 生成的文本
        """
        pass
    
    def chat_with_json(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用 LLM 并期望返回 JSON 格式
        
        Args:
            messages: 消息列表
            system: 系统提示词
        
        Returns:
            解析后的 JSON 对象
        """
        # 在系统提示词中要求返回 JSON
        json_system = (system or "") + "\n\nIMPORTANT: You must respond with valid JSON only, no additional text."
        
        response_text = self.chat(messages, system=json_system)
        
        # 尝试提取 JSON（可能包含在 ```json 代码块中）
        response_text = response_text.strip()
        
        # 去掉可能的代码块标记
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # 尝试提取第一个完整的 JSON 对象（处理后面有额外文本的情况）
            try:
                # 找到第一个 { 和与之匹配的 }
                start_idx = response_text.find('{')
                if start_idx == -1:
                    raise ValueError("No JSON object found in response")
                
                # 简单的括号匹配来找到完整的 JSON 对象
                bracket_count = 0
                end_idx = -1
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        bracket_count += 1
                    elif response_text[i] == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx == -1:
                    raise ValueError("No complete JSON object found")
                
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            except Exception as parse_error:
                raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response_text[:500]}...")
    
    def __str__(self) -> str:
        return f"{self.provider_name}(model={self.model})"
