import json
from typing import Dict, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from config import config


class AgentState(TypedDict):
    """State for the agent graph"""
    query: str
    user_id: str
    intent: str
    features: Dict[str, str]
    keywords: List[str]
    tags: List[str]
    search_strategy: str
    error: str


class TemplateAgent:
    """Template recommendation agent using LangGraph"""
    
    def __init__(self):
        # Configure LLM based on provider
        if config.llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=config.llm_model,
                temperature=0.3,
                api_key=config.anthropic_api_key or config.llm_api_key
            )
        elif config.llm_provider == "zhipu":
            # Us Zhipu's OpenAI-compatible endpoint
            self.llm = ChatOpenAI(
                model=config.llm_model,
                temperature=0.3,
                api_key=config.zhipu_api_key or config.llm_api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/"
            )
        elif config.llm_provider == "qwen":
            # Use Qwen's (DashScope) OpenAI-compatible endpoint
            self.llm = ChatOpenAI(
                model=config.llm_model,
                temperature=0.3,
                api_key=config.dashscope_api_key or config.llm_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        else:
            # Default to OpenAI (works for OpenAI and OpenAI-compatible APIs)
            self.llm = ChatOpenAI(
                model=config.llm_model,
                temperature=0.3,
                api_key=config.llm_api_key,
                base_url=config.llm_api_base if config.llm_api_base else None
            )
        
        self.intent_prompt = self._create_intent_prompt()
        self.explanation_prompt = self._create_explanation_prompt()
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    def _create_intent_prompt(self) -> ChatPromptTemplate:
        """Create prompt for intent understanding"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的设计模版意图理解助手。
分析用户的查询并提取以下信息:
1. intent: 用户意图 (如"生成海报"、"制作名片"等)
2. features: 关键特征字典 (风格、场景、色调、用途等)
3. keywords: 关键词列表
4. tags: 标签列表 (用于精准过滤)
5. search_strategy: 检索策略 ("vector"/"tag"/"hybrid")

返回JSON格式,不要包含其他文字。

示例输出:
{{
  "intent": "生成海报",
  "features": {{"style": "简约", "color": "蓝色", "scenario": "产品发布"}},
  "keywords": ["简约", "产品", "发布会", "蓝色"],
  "tags": ["简约", "商务", "蓝色"],
  "search_strategy": "hybrid"
}}"""),
            ("user", "{query}")
        ])
    
    def _create_explanation_prompt(self) -> ChatPromptTemplate:
        """Create prompt for explanation generation"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的设计模版推荐助手。
基于用户查询和推荐的模版,生成简洁的推荐说明。

格式要求:
- 开头一句话总结
- 列出每个模版的推荐理由(20字以内)
- 语气友好专业"""),
            ("user", """
用户查询: {query}

推荐模版:
{templates}

请生成推荐说明:""")
        ])
    
    def _build_graph(self):
        """Build the LangGraph agent workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("understand_intent", self._understand_intent_node)
        workflow.add_node("extract_features", self._extract_features_node)
        
        # Define edges
        workflow.set_entry_point("understand_intent")
        workflow.add_edge("understand_intent", "extract_features")
        workflow.add_edge("extract_features", END)
        
        return workflow.compile()
    
    def _understand_intent_node(self, state: AgentState) -> AgentState:
        """Node to understand user intent"""
        try:
            query = state["query"]
            
            # Call LLM to understand intent
            messages = self.intent_prompt.format_messages(query=query)
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            result = json.loads(response.content)
            
            # Update state
            state["intent"] = result.get("intent", "模版推荐")
            state["features"] = result.get("features", {})
            state["keywords"] = result.get("keywords", [])
            state["tags"] = result.get("tags", [])
            state["search_strategy"] = result.get("search_strategy", "hybrid")
            
        except Exception as e:
            # Fallback on error
            state["error"] = str(e)
            state["intent"] = "模版推荐"
            state["features"] = {}
            state["keywords"] = state["query"].split()
            state["tags"] = []
            state["search_strategy"] = "vector"
        
        return state
    
    def _extract_features_node(self, state: AgentState) -> AgentState:
        """Node to extract additional features if needed"""
        # Additional feature extraction logic can be added here
        return state
    
    def understand_intent(self, query: str, user_id: str = None, context: List[str] = None) -> Dict:
        """Main entry point for intent understanding"""
        initial_state = AgentState(
            query=query,
            user_id=user_id or "",
            intent="",
            features={},
            keywords=[],
            tags=[],
            search_strategy="",
            error=""
        )
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return {
            "intent": final_state["intent"],
            "features": final_state["features"],
            "keywords": final_state["keywords"],
            "tags": final_state["tags"],
            "search_strategy": final_state["search_strategy"]
        }
    
    def generate_explanation(self, query: str, templates: List[Dict]) -> str:
        """Generate recommendation explanation"""
        try:
            # Format templates
            templates_text = "\n".join([
                f"{i+1}. {t['name']} - {t.get('description', 'N/A')}"
                for i, t in enumerate(templates[:5])
            ])
            
            messages = self.explanation_prompt.format_messages(
                query=query,
                templates=templates_text
            )
            response = self.llm.invoke(messages)
            
            return response.content
        except Exception as e:
            # Fallback
            return f"为您推荐以下{len(templates)}个模版"
