"""
LLM 客户端封装
支持多种大模型提供商
"""

import os
import yaml
from typing import Optional
from .llm_provider import BaseLLMProvider, LLMFactory


# 全局 LLM 提供商实例
_llm_provider: Optional[BaseLLMProvider] = None


def get_llm_client() -> BaseLLMProvider:
    """获取全局 LLM 提供商实例"""
    global _llm_provider
    if _llm_provider is None:
        # 如果未初始化，尝试从环境变量或默认配置创建
        _llm_provider = _create_default_provider()
    return _llm_provider


def init_llm_client(config: dict = None, provider_type: str = None, api_key: str = None):
    """
    初始化全局 LLM 客户端
    
    Args:
        config: 完整的LLM配置字典（优先级最高）
        provider_type: 提供商类型（claude/openai/zhipu/qwen）
        api_key: API Key（简化配置方式）
    """
    global _llm_provider
    
    if config:
        # 使用完整配置
        _llm_provider = LLMFactory.create_provider(config)
    elif provider_type and api_key:
        # 简化配置方式
        config = {
            "provider": provider_type,
            provider_type: {
                "api_key": api_key
            }
        }
        _llm_provider = LLMFactory.create_provider(config)
    else:
        raise ValueError("Either config or (provider_type + api_key) must be provided")


def load_config_from_file(config_path: str = "config.yaml") -> dict:
    """从配置文件加载 LLM 配置"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 递归替换环境变量占位符
    def replace_env_vars(obj):
        """递归处理字典和字符串中的环境变量占位符"""
        if isinstance(obj, dict):
            return {k: replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # 处理 ${VAR_NAME} 格式的占位符
            import re
            def replace_match(match):
                env_var = match.group(1)
                return os.getenv(env_var, match.group(0))
            return re.sub(r'\$\{([^}]+)\}', replace_match, obj)
        else:
            return obj
    
    llm_config = config.get('llm', {})
    return replace_env_vars(llm_config)


def _create_default_provider() -> BaseLLMProvider:
    """创建默认提供商（Claude）"""
    # 尝试从环境变量创建 Claude 提供商
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        config = {
            "provider": "claude",
            "claude": {
                "api_key": api_key,
                "model": "claude-sonnet-4-20250514"
            }
        }
        return LLMFactory.create_provider(config)
    
    raise ValueError(
        "No LLM provider configured. Please call init_llm_client() or set ANTHROPIC_API_KEY"
    )


# 向后兼容的别名
LLMClient = BaseLLMProvider
