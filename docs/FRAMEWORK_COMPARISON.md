# Agent 框架对比：Legacy vs LangGraph vs AutoGen vs CrewAI

## 📊 框架概览

| 特性 | Legacy（自研） | LangGraph | AutoGen | CrewAI |
|------|---------------|-----------|---------|--------|
| **开发者** | 自己实现 | LangChain 团队 | 微软 | CrewAI Inc |
| **核心理念** | Plan + Execute | 状态图 (StateGraph) | 多 Agent 对话 | 角色扮演团队 |
| **架构模式** | 两阶段执行 | 图结构循环 | Agent 协作对话 | Crew 协作 |
| **工具调用** | 自定义 Registry | LangChain Tool | Function Calling | BaseTool |
| **适用场景** | 学习原理、定制化 | 复杂工作流 | 多 Agent 协作 | 团队角色协作 |
| **隐喻** | 计划+执行器 | 状态流转图 | 对话群聊 | 船员团队 |

---

## 🔄 执行流程对比

### 1. Legacy（自研）

```
用户任务
    ↓
┌─────────────┐
│   Planner   │  ← LLM 一次性生成完整计划
└──────┬──────┘
       ↓
   [Plan JSON]
       ↓
┌─────────────┐
│  Executor   │  ← 按计划顺序执行
└──────┬──────┘
       ↓
   逐步执行工具
       ↓
   返回结果
```

**特点**：
- 计划一次性生成，不可动态调整
- 执行器按部就班执行
- 需要处理步骤间数据传递 `{{step_X.output}}`

### 2. LangGraph

```
用户任务
    ↓
┌─────────────┐
│    Agent    │  ← LLM 决定下一步
└──────┬──────┘
       ↓
  有工具调用？
   ↙      ↘
  是        否
  ↓         ↓
┌─────┐   ┌─────┐
│Tools│   │ END │
└──┬──┘   └─────┘
   │
   └──→ Agent（循环）
```

**特点**：
- 动态决策，可根据结果调整
- 支持循环，直到任务完成
- 内置状态管理和 Checkpoint

### 3. AutoGen

```
用户任务
    ↓
┌─────────────────────────────────────┐
│           对话循环                   │
│  ┌──────────┐    ┌──────────┐      │
│  │UserProxy │←──→│Assistant │      │
│  │(执行工具) │    │(LLM决策) │      │
│  └──────────┘    └──────────┘      │
│        ↑              │             │
│        └──── 工具结果 ←┘             │
└─────────────────────────────────────┘
    ↓
收到 "TERMINATE" 结束
```

**特点**：
- 基于对话的协作模式
- 支持多 Agent 群聊
- 天然支持人机交互

### 4. CrewAI

```
用户任务
    ↓
┌─────────────────────────────────────────┐
│              Crew（船员团队）             │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │Researcher│→ │ Analyst  │→ │ Writer │ │
│  │ 研究员   │  │ 分析师    │  │ 撰写员 │ │
│  └──────────┘  └──────────┘  └────────┘ │
│       ↓             ↓            ↓      │
│   Task 1 ────→ Task 2 ────→ Task 3     │
│  (数据收集)    (数据分析)   (报告生成)   │
└─────────────────────────────────────────┘
    ↓
kickoff() 执行完成
```

**特点**：
- 强调角色扮演，每个 Agent 有明确定位
- 任务可设置依赖关系 (context)
- 支持顺序执行和层级执行模式

---

## 💻 代码对比

### 工具定义

```python
# ========== Legacy ==========
class HTTPRequestTool(BaseTool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="http_request",
            description="发起 HTTP 请求",
            parameters={...}
        )
    
    def execute(self, url, method, **kwargs):
        return requests.get(url).json()

ToolRegistry.register(HTTPRequestTool())


# ========== LangGraph ==========
from langchain_core.tools import tool

@tool
def http_request(url: str, method: str = "GET") -> dict:
    """发起 HTTP 请求获取数据"""
    return requests.get(url).json()

# 自动从函数签名和 docstring 生成 schema


# ========== AutoGen ==========
from typing import Annotated

def http_request(
    url: Annotated[str, "请求的 URL 地址"],
    method: Annotated[str, "HTTP 方法"] = "GET"
) -> dict:
    """发起 HTTP 请求获取数据"""
    return requests.get(url).json()

register_function(
    http_request,
    caller=assistant,
    executor=user_proxy,
    name="http_request",
    description="发起 HTTP 请求"
)


# ========== CrewAI ==========
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class HttpRequestInput(BaseModel):
    url: str = Field(description="请求的 URL")
    method: str = Field(default="GET", description="HTTP 方法")

class HttpRequestTool(BaseTool):
    name: str = "http_request"
    description: str = "发起 HTTP 请求获取数据"
    args_schema: type[BaseModel] = HttpRequestInput

    def _run(self, url: str, method: str = "GET") -> str:
        return str(requests.get(url).json())
```

### Agent 创建

```python
# ========== Legacy ==========
planner = Planner()
executor = Executor()

plan = planner.create_plan(task_id, user_input)
result = executor.execute_plan(plan)


# ========== LangGraph ==========
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_conditional_edges("agent", should_continue, {...})

app = workflow.compile()
result = app.invoke(initial_state)


# ========== AutoGen ==========
from autogen import AssistantAgent, UserProxyAgent

assistant = AssistantAgent(
    name="Assistant",
    system_message="你是一个任务执行助手...",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="Executor",
    human_input_mode="NEVER",
)

# 发起对话
user_proxy.initiate_chat(assistant, message=task)


# ========== CrewAI ==========
from crewai import Agent, Task, Crew, Process

# 定义角色化 Agent
researcher = Agent(
    role="数据研究员",
    goal="收集和分析数据",
    backstory="你是一名资深研究员...",
    tools=[http_tool],
    verbose=True,
)

# 定义任务
task = Task(
    description="获取 API 数据并分析",
    expected_output="分析报告",
    agent=researcher,
)

# 组建团队并执行
crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
```

---

## 🎯 多 Agent 协作

### LangGraph 方式

```python
# 定义多个节点
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("reviewer", reviewer_node)

# 定义边（流转规则）
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "reviewer")
workflow.add_conditional_edges("reviewer", check_approval, {...})
```

### AutoGen 方式

```python
# 定义多个 Agent
planner = AssistantAgent(name="Planner", ...)
executor = AssistantAgent(name="Executor", ...)
critic = AssistantAgent(name="Critic", ...)

# 创建群聊
groupchat = GroupChat(
    agents=[user_proxy, planner, executor, critic],
    max_round=12,
)

# 群聊管理器自动协调对话
manager = GroupChatManager(groupchat=groupchat, llm_config=config)
user_proxy.initiate_chat(manager, message=task)
```

### CrewAI 方式

```python
# 定义多个角色化 Agent
researcher = Agent(role="研究员", goal="收集数据", ...)
analyst = Agent(role="分析师", goal="分析数据", ...)
writer = Agent(role="撰写员", goal="生成报告", ...)

# 定义任务链（带依赖）
research_task = Task(description="收集数据", agent=researcher)
analysis_task = Task(description="分析数据", agent=analyst, context=[research_task])
report_task = Task(description="生成报告", agent=writer, context=[analysis_task])

# 组建 Crew 执行
crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[research_task, analysis_task, report_task],
    process=Process.sequential,  # 或 Process.hierarchical
)
result = crew.kickoff()
```

---

## ✅ 框架选择建议

| 场景 | 推荐框架 | 原因 |
|------|----------|------|
| **学习 Agent 原理** | Legacy | 从零实现，理解底层 |
| **复杂工作流** | LangGraph | 图结构清晰，状态管理好 |
| **多 Agent 对话** | AutoGen | 对话模式天然适合 |
| **团队角色协作** | CrewAI | 角色定义清晰，任务依赖明确 |
| **快速原型** | LangGraph/CrewAI | 框架成熟，开箱即用 |
| **生产部署** | LangGraph | LangSmith 监控，企业支持 |
| **人机交互** | AutoGen | human_input_mode 支持好 |
| **代码生成执行** | AutoGen | 内置代码执行器 |
| **业务流程自动化** | CrewAI | 任务编排直观，角色分明 |

---

## 📦 依赖安装

```bash
# Legacy（自研）
pip install flask requests beautifulsoup4

# LangGraph
pip install langgraph langchain langchain-openai langchain-anthropic

# AutoGen
pip install pyautogen

# CrewAI
pip install crewai
```

---

## 🔗 参考资源

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **AutoGen**: https://microsoft.github.io/autogen/
- **CrewAI**: https://docs.crewai.com/
- **LangChain**: https://python.langchain.com/
