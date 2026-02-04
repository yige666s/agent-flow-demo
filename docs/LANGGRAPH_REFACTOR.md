# LangGraph Agent 重构说明

## 概述

使用 LangGraph 重构了 agent 模块，提供了更灵活的图式工作流编排能力。

## 架构对比

### 原有架构 (Legacy Mode)
```
User Input → Planner (生成完整Plan) → Executor (按顺序执行所有步骤) → Result
```

### LangGraph 架构
```
User Input → StateGraph:
  ├─ Plan Node (规划)
  ├─ Execute Step Node (执行单步)
  ├─ Check Completion Node (检查完成)
  └─ Finalize Node (生成结果)
```

## 主要改进

### 1. **状态管理**
- 使用 `AgentState` TypedDict 管理所有状态
- 状态在节点间自动传递和更新
- 支持状态追加（如 messages、step_results）

### 2. **灵活的流程控制**
- 条件分支：`_should_continue`、`_check_if_done`
- 动态路由：根据状态决定下一个节点
- 错误处理：自动捕获并路由到 finalize 节点

### 3. **可扩展性**
- 容易添加新节点（如 reflection、retry、human-in-the-loop）
- 支持并行执行（LangGraph 内置）
- 支持流式输出

### 4. **可视化**
- LangGraph 自带图可视化工具
- 可以导出 Mermaid 图表

## 使用方法

### 1. 启动 LangGraph 模式

设置环境变量：
```bash
export AGENT_MODE=langgraph
```

或修改 `.env` 文件：
```env
AGENT_MODE=langgraph
```

### 2. 启动服务

```bash
cd agent
python3 app.py
```

或使用 Makefile：
```bash
make run-agent
```

### 3. API 调用

**统一执行端点（推荐）**：
```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-001",
    "user_input": "获取 https://httpbin.org/json 的内容并提取 slideshow 字段"
  }'
```

**响应格式**：
```json
{
  "status": "completed",
  "task_id": "task-001",
  "mode": "langgraph",
  "plan": {
    "task_id": "task-001",
    "steps": [...]
  },
  "result": {
    "status": "completed",
    "result": {...},
    "steps_executed": 2,
    "execution_time": 1.23
  },
  "step_results": [...]
}
```

### 4. 测试脚本

```bash
cd agent
python3 test_langgraph.py
```

## 节点说明

### Plan Node (规划节点)
- **输入**: `user_input`, `task_id`
- **输出**: `plan` (Plan 对象)
- **功能**: 调用 LLM 生成执行计划

### Execute Step Node (执行节点)
- **输入**: `plan`, `current_step`, `step_results`
- **输出**: 更新 `step_results`, `current_step`
- **功能**: 执行单个步骤，解析参数依赖

### Check Completion Node (检查节点)
- **输入**: `plan`, `current_step`
- **输出**: `completed` (bool)
- **功能**: 检查是否所有步骤已完成

### Finalize Node (最终化节点)
- **输入**: `step_results`, `error`
- **输出**: `final_output`
- **功能**: 生成最终结果

## 高级特性

### 1. 添加新节点

```python
def custom_node(state: AgentState) -> Dict[str, Any]:
    """自定义节点"""
    # 处理逻辑
    return {
        "custom_field": "value"
    }

# 在 _build_graph 中添加
workflow.add_node("custom", custom_node)
workflow.add_edge("plan", "custom")
```

### 2. 并行执行

```python
# LangGraph 支持并行节点
workflow.add_node("parallel_1", node1)
workflow.add_node("parallel_2", node2)

# 从 plan 分支到两个并行节点
workflow.add_edge("plan", "parallel_1")
workflow.add_edge("plan", "parallel_2")

# 在 join 节点汇合
workflow.add_edge("parallel_1", "join")
workflow.add_edge("parallel_2", "join")
```

### 3. 人工干预节点

```python
def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """等待人工审批"""
    # 暂停执行，等待外部输入
    return {"waiting_for_approval": True}

workflow.add_node("human_approval", human_approval_node)
```

### 4. 流式输出

```python
# 使用 astream 进行流式执行
async for state in agent.graph.astream(initial_state):
    print(f"Current state: {state}")
```

## 与其他模式对比

| 特性 | Legacy | ReAct | LangGraph |
|------|--------|-------|-----------|
| 规划方式 | 一次性完整规划 | 动态推理 | 一次性规划 + 图式流程 |
| 执行方式 | 顺序执行 | 循环迭代 | 图式路由 |
| 灵活性 | ★☆☆ | ★★☆ | ★★★ |
| 可扩展性 | ★☆☆ | ★★☆ | ★★★ |
| 可视化 | ✗ | ✗ | ✓ |
| 并行支持 | ✗ | ✗ | ✓ |
| 适用场景 | 简单线性任务 | 需要推理的任务 | 复杂工作流 |

## 下一步计划

- [ ] 添加流式输出支持
- [ ] 实现并行步骤执行
- [ ] 添加人工审批节点
- [ ] 添加 Reflection 节点（自我检查）
- [ ] 添加 Retry 机制
- [ ] 集成 LangSmith 追踪
- [ ] 导出工作流可视化图表

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [State Machine Pattern](https://en.wikipedia.org/wiki/State_machine)
