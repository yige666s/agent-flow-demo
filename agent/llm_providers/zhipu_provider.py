"""
智谱 AI (GLM) 提供商实现
"""

from typing import List, Dict, Any, Optional
from zhipuai import ZhipuAI
from .base import BaseLLMProvider


class ZhipuProvider(BaseLLMProvider):
    """智谱 AI 提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("Zhipu API key is required")
        
        self.client = ZhipuAI(api_key=api_key)
        self.model = config.get("model", "glm-4")
    
    @property		agent/
		├── app.py              # 统一入口（支持 Legacy + LangGraph）
		├── config.yaml         # 配置文件
		├── executor.py         # Legacy 执行器
		├── langgraph_agent.py  # LangGraph Agent
		├── llm_client.py       # LLM 客户端
		├── llm_providers/      # LLM 提供商
		├── models.py           # 数据模型
		├── planner.py          # Legacy 规划器
		├── requirements.txt    # 依赖
		└── tools/              # 工具模块
		
		data/
		├── log/                # 任务日志（干净）
		└── user/               # 用户文件（干净）
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
