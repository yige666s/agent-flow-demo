"""
LLM 提供商实现，整合了所有提供商和工厂类
"""

import os
import json
import unicodedata
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# 可选依赖
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None

try:
    import dashscope
except ImportError:
    dashscope = None


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
        # 在系统提示词中要求返回 JSON，明确禁止换行
        json_system = (system or "") + "\n\nIMPORTANT: You must respond with valid JSON only, no additional text. DO NOT use line breaks inside string values. Ensure all strings in JSON are properly escaped and on a single line."
        
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
        
        # 尝试修复常见的 JSON 问题
        def fix_json_string(text):
            """修复 JSON 中的字符串值，确保控制字符和无效转义被正确处理"""
            result = []
            in_string = False
            i = 0
            
            # JSON 中合法的转义字符
            valid_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}
            
            while i < len(text):
                char = text[i]
                
                if char == '"' and (i == 0 or text[i-1] != '\\' or (i >= 2 and text[i-2:i] == '\\\\')):
                    # 检查这个引号是否真的是字符串边界（处理 \" 和 \\" 的情况）
                    # 计算前面连续的反斜杠数量
                    num_backslashes = 0
                    j = i - 1
                    while j >= 0 and text[j] == '\\':
                        num_backslashes += 1
                        j -= 1
                    
                    # 如果前面有偶数个反斜杠，这个引号是字符串边界
                    if num_backslashes % 2 == 0:
                        result.append(char)
                        in_string = not in_string
                        i += 1
                        continue
                
                if in_string and char == '\\' and i + 1 < len(text):
                    next_char = text[i + 1]
                    
                    # 处理 \uXXXX
                    if next_char == 'u' and i + 5 < len(text):
                        hex_chars = text[i+2:i+6]
                        if all(c in '0123456789abcdefABCDEF' for c in hex_chars):
                            result.append(text[i:i+6])
                            i += 6
                            continue
                    
                    # 合法的转义序列
                    if next_char in valid_escapes:
                        result.append(char)
                        result.append(next_char)
                        i += 2
                        continue
                    
                    # 无效的转义序列（如 \s, \d 等）- 添加额外的反斜杠使其变成 \\s, \\d
                    result.append('\\\\')
                    result.append(next_char)
                    i += 2
                    continue
                
                # 如果在字符串内部，处理控制字符
                if in_string:
                    if char == '\n':
                        result.append('\\n')
                    elif char == '\r':
                        result.append('\\r')
                    elif char == '\t':
                        result.append('\\t')
                    elif ord(char) < 32:  # 其他控制字符
                        result.append(f'\\u{ord(char):04x}')
                    else:
                        result.append(char)
                else:
                    result.append(char)
                
                i += 1
            
            return ''.join(result)
        
        cleaned_text = fix_json_string(response_text)
        
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            # 尝试提取第一个完整的 JSON 对象（处理后面有额外文本的情况）
            try:
                # 找到第一个 { 和与之匹配的 }
                start_idx = cleaned_text.find('{')
                if start_idx == -1:
                    raise ValueError("No JSON object found in response")
                
                # 简单的括号匹配来找到完整的 JSON 对象
                bracket_count = 0
                end_idx = -1
                in_string = False
                escape_next = False
                
                for i in range(start_idx, len(cleaned_text)):
                    char = cleaned_text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            bracket_count += 1
                        elif char == '}':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_idx = i + 1
                                break
                
                if end_idx == -1:
                    raise ValueError("No complete JSON object found")
                
                json_str = cleaned_text[start_idx:end_idx]
                return json.loads(json_str)
            except Exception as parse_error:
                raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {cleaned_text[:500]}...")
    
    def __str__(self) -> str:
        return f"{self.provider_name}(model={self.model})"


class ClaudeProvider(BaseLLMProvider):
    """Claude (Anthropic) 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if Anthropic is None:
            raise ImportError("anthropic package is not installed")
            
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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if OpenAI is None:
            raise ImportError("openai package is not installed")
            
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


class ZhipuProvider(BaseLLMProvider):
    """智谱 AI 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if ZhipuAI is None:
            raise ImportError("zhipuai package is not installed")
            
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Zhipu API key is required")
        
        self.client = ZhipuAI(api_key=api_key)
        self.model = config.get("model", "glm-4")
    
    @property
    def provider_name(self) -> str:
        return "ZhipuAI"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用智谱 AI API"""
        try:
            # 智谱 AI 的 system 消息需要添加到 messages 列表中
            api_messages = []
            
            if system:
                api_messages.append({
                    "role": "system",
                    "content": system
                })
            
            api_messages.extend(messages)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            
            if response.choices:
                return response.choices[0].message.content or ""
            
            return ""
        
        except Exception as e:
            raise Exception(f"Zhipu AI API call failed: {str(e)}")


class QwenProvider(BaseLLMProvider):
    """通义千问提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if dashscope is None:
            raise ImportError("dashscope package is not installed")
            
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


class LLMFactory:
    """LLM 提供商工厂类"""
    
    # 注册的提供商
    _providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "zhipu": ZhipuProvider,
        "qwen": QwenProvider
    }
    
    @classmethod
    def create_provider(cls, config: Dict[str, Any]) -> BaseLLMProvider:
        """
        根据配置创建 LLM 提供商实例
        
        Args:
            config: 完整的 LLM 配置字典，包含 provider 字段和各提供商配置
        
        Returns:
            LLM 提供商实例
        
        Raises:
            ValueError: provider 不存在或配置缺失
        """
        provider_type = config.get("provider", "claude").lower()
        
        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown LLM provider: '{provider_type}'. "
                f"Available providers: {available}"
            )
        
        # 获取提供商特定配置
        provider_config = config.get(provider_type, {})
        
        # 支持从环境变量读取 API Key
        api_key_var = provider_config.get("api_key", "")
        if isinstance(api_key_var, str) and api_key_var.startswith("${") and api_key_var.endswith("}"):
            env_var_name = api_key_var[2:-1]
            api_key = os.getenv(env_var_name)
            if api_key:
                provider_config["api_key"] = api_key
        
        # 创建提供商实例
        provider_class = cls._providers[provider_type]
        return provider_class(provider_config)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        注册自定义提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类（必须继承自 BaseLLMProvider）
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError("Provider class must inherit from BaseLLMProvider")
        
        cls._providers[name.lower()] = provider_class
        print(f"Registered LLM provider: {name}")
    
    @classmethod
    def list_providers(cls) -> list:
        """列出所有可用的提供商"""
        return list(cls._providers.keys())
