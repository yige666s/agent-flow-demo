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
1. intent: 用户意图 (如"生成海报"、"制作名片"、"设计PPT"等)
2. features: 关键特征字典 (风格、场景、色调、用途、行业等)
3. keywords: 关键词列表 (从查询中提取的核心词汇)
4. tags: 标签列表 (用于精准过滤，应该是具体的、可匹配的标签)
5. search_strategy: 检索策略
   - "vector": 语义相似搜索，适合模糊、创意类查询
   - "tag": 精确标签匹配，适合有明确属性要求的查询
   - "hybrid": 混合检索，适合大多数场景

**标签提取规则**:
- 风格类: 简约、科技、温馨、商务、现代、复古、极简等
- 场景类: 发布会、促销、节日、招聘、教育、社交媒体等
- 色调类: 蓝色、红色、暖色、冷色、黑白、渐变等
- 行业类: 电商、企业、SaaS、教育、医疗等
- 用途类: 宣传、展示、汇报、推广等

**策略选择建议**:
- 用户描述抽象、强调"感觉"或"风格" → vector
- 用户明确指定类型、颜色、场景 → tag 或 hybrid
- 用户查询包含多个维度 → hybrid

返回JSON格式,不要包含其他文字。

示例1 - 抽象查询:
输入: "给我一个有科技感的设计"
输出:
{{
  "intent": "寻找科技风格模版",
  "features": {{"style": "科技", "tone": "现代"}},
  "keywords": ["科技", "现代", "设计"],
  "tags": ["科技", "现代"],
  "search_strategy": "vector"
}}

示例2 - 具体查询:
输入: "简约商务名片设计"
输出:
{{
  "intent": "制作名片",
  "features": {{"style": "简约", "tone": "商务", "use_case": "职场个人名片"}},
  "keywords": ["简约", "商务", "名片", "职场", "专业"],
  "tags": ["简约", "商务", "名片", "职场"],
  "search_strategy": "hybrid"
}}

示例3 - 场景化查询:
输入: "双十一电商促销海报"
输出:
{{
  "intent": "生成促销海报",
  "features": {{"scenario": "电商促销", "event": "双十一", "use_case": "营销转化"}},
  "keywords": ["双十一", "电商", "促销", "海报", "营销"],
  "tags": ["电商", "促销", "节日", "海报"],
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
