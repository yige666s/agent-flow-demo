"""
LLM 提供商工厂
"""

import os
from typing import Dict, Any
from .base import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .zhipu_provider import ZhipuProvider
from .qwen_provider import QwenProvider


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
        if api_key_var.startswith("${") and api_key_var.endswith("}"):
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
