# AgentFlow 项目 - 简历与面试指南

## 📝 一、简历项目描述（STAR 法则）

### 版本一：简洁版（适合简历）

**AgentFlow - AI Agent 智能任务编排系统**

- **S（情境）**：在 AI Agent 快速发展的背景下，市场缺乏工程级的、可扩展的任务编排系统
- **T（任务）**：设计并实现一个支持多 LLM、多工具的分布式 AI Agent 系统
- **A（行动）**：
  - 采用 **Go + Python 微服务架构**，Go 负责高并发调度，Python 负责 AI 推理
  - 实现 **ReAct（Reasoning + Acting）** 架构，支持 LLM 任务拆解与多步骤执行
  - 设计 **工厂模式 + 策略模式** 实现多 LLM 提供商（Claude/OpenAI/智谱/千问）热切换
  - 开发 **可扩展工具系统**，内置 HTTP、文件操作、网页爬虫等 5+ 工具
- **R（结果）**：
  - 支持 **100+ 并发任务**执行，平均任务完成时间 < 10s
  - 代码量 **3000+ 行**，完整的工程化实践（配置管理、日志分离、错误处理）
  - 系统可扩展性强，新增 LLM 或工具只需 **50 行代码**

---

### 版本二：详细版（适合项目详情页）

**项目名称**：AgentFlow - Production-Ready AI Agent Orchestration System

**项目周期**：2024.10 - 至今

**技术栈**：Go 1.21 / Python 3.10 / Flask / Gin / Claude API / OpenAI API / 智谱 AI / Redis

**项目描述**：

AgentFlow 是一个工程级的 AI Agent 任务编排与执行系统，采用 **Go + Python 混合架构**，实现了完整的 ReAct（Reasoning + Acting）模式。系统能够接收自然语言任务，由 LLM 自动拆解为结构化执行计划，并按步骤调用工具完成任务。

**核心职责与成果**：

1. **架构设计**
   - 设计微服务架构，Go Backend 负责 API 网关、任务调度、并发控制；Python Agent 负责 LLM 推理与工具执行
   - 采用 Goroutine Pool 实现高并发任务处理，支持 100+ 任务并发
   - 实现任务状态机（pending → planning → executing → completed/failed）与完整的生命周期管理

2. **多 LLM 支持**
   - 设计工厂模式 + 策略模式，支持 Claude/OpenAI/智谱/千问 4 种 LLM 提供商
   - 实现配置化切换，无需修改代码即可更换模型
   - 优化 JSON 响应解析，处理不同 LLM 的输出格式差异

3. **工具系统**
   - 设计可扩展的工具注册机制，支持动态注册与参数校验
   - 实现 HTTP 请求、文件操作、网页爬取、Python 代码执行等核心工具
   - 工具之间支持数据流转，使用 `{{step_X.output}}` 语法引用上一步结果

4. **工程化实践**
   - 实现日志与用户数据分离存储（data/log + data/user）
   - 完善错误处理与异常恢复机制
   - 支持环境变量与配置文件双重配置方式

---

## 🎯 二、面试可讲的技术点

### 1. 系统架构设计

| 技术点 | 详细内容 | 亮点 |
|--------|----------|------|
| **微服务架构** | Go 后端 + Python Agent 分离，各司其职 | 充分发挥语言优势：Go 高并发，Python AI 生态 |
| **ReAct 架构** | LLM 先 Reason（拆解计划），再 Act（执行工具） | 业界标准的 Agent 设计模式 |
| **任务状态机** | pending → planning → executing → completed/failed | 完整的生命周期管理 |
| **并发模型** | Go 的 Goroutine Pool + Channel 通信 | 支持 100+ 并发任务 |

### 2. 设计模式应用

| 模式 | 应用场景 | 代码位置 |
|------|----------|----------|
| **工厂模式** | LLM 提供商创建 | `llm_providers/factory.py` |
| **策略模式** | 不同 LLM 的调用策略 | `llm_providers/*.py` |
| **注册表模式** | 工具动态注册与发现 | `tools/base.py - ToolRegistry` |
| **模板方法** | 工具基类定义执行流程 | `tools/base.py - BaseTool` |
| **观察者模式** | 任务状态变更通知 | `orchestrator/orchestrator.go` |

### 3. 关键技术实现

#### 3.1 LLM 任务拆解（Planner）
```python
# 核心流程
1. 构造 System Prompt（包含可用工具列表）
2. 发送用户任务到 LLM
3. LLM 返回 JSON 格式的执行计划
4. 解析计划，生成 Step 列表
```

**技术难点**：
- LLM 返回的 JSON 可能不规范（包含额外文本、格式错误）
- 解决方案：实现智能 JSON 提取算法，使用括号匹配找到完整的 JSON 对象

#### 3.2 多步骤执行（Executor）
```python
# 核心流程
1. 按 step_id 顺序执行
2. 解析参数中的变量引用 {{step_X.output}}
3. 调用对应工具执行
4. 保存步骤结果到 Context
5. 传递数据到下一步
```

**技术难点**：
- 步骤之间的数据类型不匹配（如 dict 需要序列化为 JSON 字符串）
- 解决方案：在工具层面自动处理类型转换

#### 3.3 工具注册机制
```python
class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.schema.name] = tool
    
    @classmethod
    def execute_tool(cls, name: str, params: dict):
        return cls._tools[name].execute(**params)
```

**设计优点**：
- 解耦：工具与执行器分离
- 可扩展：新增工具只需继承 BaseTool 并注册
- 统一接口：所有工具通过 schema 描述参数

### 4. 工程化实践

| 实践 | 具体做法 |
|------|----------|
| **配置管理** | YAML 配置 + 环境变量，使用 python-dotenv 加载 .env |
| **日志分离** | 任务日志 → data/log，用户文件 → data/user |
| **错误处理** | 分层捕获异常，返回结构化错误信息 |
| **代码组织** | 按功能分模块：llm_providers、tools、models |

---

## ❓ 三、面试官可能追问的问题

### A. 架构相关

**Q1: 为什么选择 Go + Python 混合架构，而不是单一语言？**

> **答**：这是基于两个核心考量：
> 1. **Go 的优势**：高并发处理（Goroutine）、编译型语言性能高、适合做 API 网关和任务调度
> 2. **Python 的优势**：AI/LLM 生态完善（Anthropic、OpenAI SDK 都是 Python 优先）、动态类型适合处理 LLM 的非结构化输出
> 
> 这种架构在业界也有先例，如 LangChain（Python）+ LangServe（可配合 Go/Rust 网关）

**Q2: 如果 Python Agent 服务挂掉，Go 后端如何处理？**

> **答**：
> 1. **超时机制**：HTTP 调用设置 30s 超时，超时后标记任务失败
> 2. **重试策略**：可配置重试次数（当前为 0，可扩展）
> 3. **熔断降级**：可引入熔断器（如 hystrix-go），当失败率过高时快速失败
> 4. **健康检查**：可添加 /health 端点，Go 定期检查 Agent 状态

**Q3: 如何保证任务不丢失？**

> **答**：
> 1. **持久化存储**：任务创建后立即写入 JSON 文件（可扩展为 Redis/MySQL）
> 2. **状态机**：明确的状态转换，每次状态变更都持久化
> 3. **幂等性**：任务 ID 唯一，重复提交不会创建新任务
> 4. **可扩展**：可引入消息队列（Kafka/RabbitMQ）实现任务队列持久化

---

### B. LLM 相关

**Q4: 如何处理 LLM 返回格式不一致的问题？**

> **答**：
> ```python
> # 1. 首先尝试直接解析
> try:
>     return json.loads(response_text)
> except JSONDecodeError:
>     # 2. 智能提取：找到第一个 { 和匹配的 }
>     start = response_text.find('{')
>     bracket_count = 0
>     for i in range(start, len(response_text)):
>         if response_text[i] == '{': bracket_count += 1
>         elif response_text[i] == '}': bracket_count -= 1
>         if bracket_count == 0:
>             return json.loads(response_text[start:i+1])
> ```
> 
> 这样可以处理 LLM 在 JSON 前后添加解释文字的情况。

**Q5: 不同 LLM 的调用方式差异如何统一？**

> **答**：使用 **策略模式 + 工厂模式**：
> ```python
> # 抽象基类定义统一接口
> class BaseLLMProvider(ABC):
>     @abstractmethod
>     def chat(self, messages, system=None) -> str: pass
>     
>     def chat_with_json(self, messages, system=None) -> dict:
>         # 模板方法：统一的 JSON 解析逻辑
>         response = self.chat(messages, system)
>         return self._parse_json(response)
> 
> # 工厂创建具体实例
> class LLMFactory:
>     @staticmethod
>     def create(provider_type: str, config: dict) -> BaseLLMProvider:
>         providers = {
>             "claude": ClaudeProvider,
>             "openai": OpenAIProvider,
>             "zhipu": ZhipuProvider,
>         }
>         return providers[provider_type](config)
> ```

**Q6: 如何优化 LLM 调用成本？**

> **答**：
> 1. **Prompt 优化**：精简 System Prompt，只包含必要信息
> 2. **缓存机制**：相同任务可缓存计划，避免重复规划
> 3. **模型分级**：简单任务用小模型（如 GPT-3.5），复杂任务用大模型
> 4. **Token 控制**：设置 max_tokens 限制输出长度
> 5. **批量处理**：多个相似任务合并为一次 LLM 调用

---

### C. 工具系统相关

**Q7: 如何保证工具执行的安全性？**

> **答**：
> 1. **沙箱执行**：python_exec 工具使用受限的 globals，只暴露安全函数
> ```python
> allowed_globals = {
>     '__builtins__': {
>         'len': len, 'str': str, 'int': int,
>         # 只允许安全的内置函数
>     }
> }
> exec(code, allowed_globals, local_vars)
> ```
> 2. **参数校验**：工具定义 schema，执行前验证参数类型
> 3. **超时控制**：每个工具设置执行超时
> 4. **目录限制**：file_ops 只能操作指定目录（data/user）

**Q8: 工具之间如何传递数据？**

> **答**：使用 **变量引用 + Context 机制**：
> ```python
> # 1. Planner 生成的计划中使用 {{step_X.output}} 语法
> {
>     "step_id": 2,
>     "parameters": {
>         "input_data": "{{step_1.output}}"
>     }
> }
> 
> # 2. Executor 解析时替换为实际值
> def _resolve_value(self, value, context):
>     if value == "{{step_1.output}}":
>         return context.get_step_output(1)
>     return value
> 
> # 3. Context 保存每一步的输出
> class ExecutionContext:
>     step_results: Dict[int, StepResult]
> ```

---

### D. 性能与扩展相关

**Q9: 系统能支持多少并发？瓶颈在哪里？**

> **答**：
> - **当前能力**：100+ 并发任务（Go Goroutine 理论上支持百万级）
> - **实际瓶颈**：
>   1. LLM API 限流（如 Claude 60 RPM）
>   2. Python 单进程 GIL（可用 Gunicorn 多 Worker 解决）
>   3. 文件 IO（可引入 Redis 替代 JSON 文件）
> - **扩展方案**：
>   1. Python Agent 水平扩展（多实例 + 负载均衡）
>   2. 任务队列（Kafka/RabbitMQ）削峰
>   3. LLM 请求队列化，遵守 Rate Limit

**Q10: 如何快速添加一个新工具？**

> **答**：只需 3 步，约 50 行代码：
> ```python
> # 1. 创建工具类
> class MyNewTool(BaseTool):
>     @property
>     def schema(self) -> ToolSchema:
>         return ToolSchema(
>             name="my_tool",
>             description="工具描述",
>             parameters={...}
>         )
>     
>     def execute(self, **params):
>         # 实现逻辑
>         return {"success": True, "data": ...}
> 
> # 2. 在 __init__.py 注册
> ToolRegistry.register(MyNewTool())
> 
> # 3. 重启服务，Planner 自动发现新工具
> ```

---

### E. 开放性问题

**Q11: 如果让你重新设计，有哪些改进点？**

> **答**：
> 1. **引入消息队列**：任务通过 Kafka 异步处理，提高可靠性
> 2. **Agent 多实例**：Python Agent 支持水平扩展，配合服务发现（Consul/Etcd）
> 3. **流式输出**：支持 SSE，实时展示执行进度
> 4. **插件市场**：工具以插件形式发布，支持在线安装
> 5. **多 Agent 协作**：支持多个 Agent 协同完成复杂任务
> 6. **向量记忆**：引入向量数据库，让 Agent 有长期记忆

**Q12: 这个项目和 LangChain 有什么区别？**

> **答**：
> | 对比项 | AgentFlow | LangChain |
> |--------|-----------|-----------|
> | **定位** | 工程级任务编排系统 | AI 应用开发框架 |
> | **架构** | Go + Python 微服务 | 纯 Python |
> | **并发** | Go Goroutine，高并发 | Python 异步，受 GIL 限制 |
> | **学习曲线** | 较低，代码量少 | 较高，概念多 |
> | **适用场景** | 需要高并发的任务系统 | 快速原型、复杂 Chain |
> 
> AgentFlow 更像是一个 **简化版、工程化的 Agent 运行时**，适合学习 Agent 原理和生产部署。

---

## 📊 四、项目数据参考

| 指标 | 数值 |
|------|------|
| 代码行数 | 4000+ 行 |
| Go 代码 | ~1000 行 |
| Python 代码 | ~3000 行 |
| 支持 LLM | 4 种（Claude/OpenAI/智谱/千问） |
| 内置工具 | 4 个（HTTP/文件/爬虫/Python执行） |
| 并发能力 | 100+ 任务 |
| 平均响应时间 | < 10s（取决于 LLM） |
| Agent 模式 | 2 种（Legacy / LangGraph） |

---

## 🎓 五、知识储备建议

面试前建议复习：
1. **Go 并发**：Goroutine、Channel、sync 包
2. **设计模式**：工厂、策略、注册表、模板方法
3. **LLM 基础**：Prompt Engineering、Token、Temperature
4. **Agent 概念**：ReAct、Chain of Thought、Tool Use
5. **微服务**：服务拆分、API 设计、错误处理
6. **LangGraph**：StateGraph、节点、边、条件路由、Checkpoint

---

## 🔷 六、LangGraph 架构升级

### 6.1 为什么引入 LangGraph？

| 对比项 | Legacy 模式（自研） | LangGraph 模式 |
|--------|---------------------|----------------|
| **规划方式** | LLM 一次性生成完整计划 | LLM 动态决策每一步 |
| **灵活性** | 计划固定，难以中途调整 | 可根据执行结果动态调整 |
| **状态管理** | 手动维护 Context | 内置 StateGraph + Checkpoint |
| **工具调用** | 自定义 ToolRegistry | LangChain Tool 生态 |
| **可观测性** | 需手动实现 | 内置 LangSmith 集成 |
| **流式输出** | 需手动实现 | 原生支持 stream |

### 6.2 LangGraph 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent 架构                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐    ┌─────────────┐    ┌─────────┐             │
│   │  START  │───▶│    Agent    │───▶│  Tools  │             │
│   └─────────┘    │  (LLM决策)   │    │ (工具执行) │            │
│                  └──────┬──────┘    └────┬────┘             │
│                         │                 │                  │
│                         │    ┌───────────┘                  │
│                         ▼    ▼                              │
│                  ┌─────────────┐                            │
│                  │ should_cont │  条件路由                   │
│                  │   inue?     │  - 有工具调用 → tools       │
│                  └──────┬──────┘  - 无工具调用 → end         │
│                         │                                    │
│                         ▼                                    │
│                  ┌─────────────┐                            │
│                  │   Extract   │───▶ END                    │
│                  │   Result    │                            │
│                  └─────────────┘                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 核心代码结构

```python
# 1. 定义状态
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]
    task_id: str
    user_input: str
    final_result: Optional[Any]

# 2. 定义工具（使用 @tool 装饰器）
@tool
def http_request(url: str, method: str = "GET") -> Dict[str, Any]:
    """发起 HTTP 请求"""
    response = requests.get(url)
    return {"status_code": response.status_code, "body": response.text}

# 3. 创建图
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)      # LLM 决策节点
workflow.add_node("tools", ToolNode(TOOLS)) # 工具执行节点

# 4. 添加条件边
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "end": "extract"}
)
workflow.add_edge("tools", "agent")  # 工具执行后回到 agent

# 5. 编译并运行
app = workflow.compile(checkpointer=MemorySaver())
result = app.invoke(initial_state)
```

### 6.4 面试可能的追问

**Q1: LangGraph 和 LangChain 有什么区别？**

> **答**：
> - **LangChain**：专注于 Chain（链式调用）和 Retrieval（检索），适合 RAG 场景
> - **LangGraph**：专注于 Graph（图结构），适合复杂的多步骤 Agent 场景
> - LangGraph 是 LangChain 团队的新项目，用于构建**有状态、可循环**的 AI 应用
> - 核心差异：LangChain 是 DAG（有向无环图），LangGraph 支持**循环**

**Q2: 为什么选择 LangGraph 而不是 AutoGPT/MetaGPT？**

> **答**：
> | 对比项 | LangGraph | AutoGPT | MetaGPT |
> |--------|-----------|---------|---------|
> | **定位** | 框架/库 | 完整应用 | 多 Agent 框架 |
> | **灵活性** | 高，可自定义图结构 | 低，固定流程 | 中等 |
> | **生产就绪** | 是，有企业支持 | 否，实验性 | 部分 |
> | **学习曲线** | 中等 | 低 | 高 |
> | **适用场景** | 可控的任务流 | 自主任务 | 软件开发模拟 |

**Q3: LangGraph 的 Checkpoint 机制是什么？**

> **答**：
> - Checkpoint 是 LangGraph 的**状态持久化机制**
> - 每次节点执行后，状态会被保存到 Checkpointer（如 MemorySaver、SQLite、Redis）
> - 支持**断点续传**：任务中断后可以从上次状态恢复
> - 支持**时间旅行**：可以回溯到任意历史状态
> ```python
> # 使用 Checkpoint
> memory = MemorySaver()
> app = workflow.compile(checkpointer=memory)
> 
> # 获取历史状态
> history = app.get_state_history(config)
> ```

**Q4: 如何在 LangGraph 中实现工具调用？**

> **答**：
> 1. **定义工具**：使用 `@tool` 装饰器
> 2. **绑定到 LLM**：`llm.bind_tools(tools)`
> 3. **创建 ToolNode**：`ToolNode(tools)`
> 4. **条件路由**：检查 `tool_calls` 决定下一步
> ```python
> def should_continue(state):
>     last_message = state["messages"][-1]
>     if last_message.tool_calls:
>         return "tools"
>     return "end"
> ```

**Q5: 两种模式如何切换？**

> **答**：
> 通过环境变量 `AGENT_MODE` 控制：
> ```bash
> # Legacy 模式（默认）
> AGENT_MODE=legacy python app_v2.py
> 
> # LangGraph 模式
> AGENT_MODE=langgraph python app_v2.py
> ```
> 
> API 兼容性：
> - Legacy：使用 `/agent/plan` + `/agent/execute`
> - LangGraph：使用 `/agent/run`（规划+执行一体化）
> - 两种模式都支持 `/agent/run` 端点

---

## 🆚 七、Legacy vs LangGraph 对比总结

| 维度 | Legacy 模式 | LangGraph 模式 |
|------|-------------|----------------|
| **实现复杂度** | 需自己实现 Planner/Executor | 使用框架，代码量少 |
| **学习价值** | 深入理解 Agent 原理 | 掌握主流框架用法 |
| **生产能力** | 需要更多工程化工作 | 开箱即用，有监控支持 |
| **面试亮点** | 展示底层实现能力 | 展示框架应用能力 |
| **适用场景** | 学习、定制化需求 | 快速开发、企业项目 |

**面试建议**：两种模式都要能讲清楚，展示你既能"造轮子"理解原理，也能"用轮子"高效开发。

