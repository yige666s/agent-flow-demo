"""
LangGraph Agent 实现
使用 LangGraph 的状态图来编排工作流
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from datetime import datetime
import operator
import json

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from core.llm_client import get_llm_client
from tools.base import ToolRegistry
from core.models import Plan, Step, StepResult


# 定义状态
class AgentState(TypedDict):
    """Agent 状态"""
    task_id: str
    user_input: str
    messages: Annotated[List[Any], operator.add]
    plan: Optional[Plan]
    current_step: int
    step_results: Annotated[List[StepResult], operator.add]
    final_output: Optional[Dict[str, Any]]
    error: Optional[str]
    completed: bool


class LangGraphAgent:
    """基于 LangGraph 的 Agent 实现"""
    
    def __init__(self):
        """初始化 LangGraph Agent"""
        self.llm_client = get_llm_client()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("check_completion", self._check_completion_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # 设置入口
        workflow.set_entry_point("plan")
        
        # 添加边
        workflow.add_edge("plan", "execute_step")
        workflow.add_conditional_edges(
            "execute_step",
            self._should_continue,
            {
                "check": "check_completion",
                "error": "finalize"
            }
        )
        workflow.add_conditional_edges(
            "check_completion",
            self._check_if_done,
            {
                "continue": "execute_step",
                "finish": "finalize"
            }
        )
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _plan_node(self, state: AgentState) -> Dict[str, Any]:
        """规划节点：生成执行计划"""
        print(f"[Plan Node] Creating plan for task: {state['user_input']}")
        
        try:
            # 获取所有工具的 schema
            tools_schema = ToolRegistry.get_all_schemas_for_llm()
            
            # 构建规划提示词
            system_prompt = f"""You are a task planning AI. Break down the user's task into executable steps.

Available tools:
{tools_schema}

IMPORTANT: Generate a valid JSON with strict type requirements:
- step_id: integer (e.g., 1, 2, 3)
- dependencies: array of integers (e.g., [], [1], [1, 2])
- parameters: object with string keys
- All URLs must be on a single line (no line breaks in strings)
- Use double quotes for all strings
- Escape special characters properly

Example:
{{
  "steps": [
    {{
      "step_id": 1,
      "description": "Fetch data from API",
      "tool": "http_request",
      "parameters": {{"url": "https://example.com", "method": "GET"}},
      "expected_output": "API response data",
      "dependencies": []
    }},
    {{
      "step_id": 2,
      "description": "Process the data",
      "tool": "python_exec",
      "parameters": {{"code": "output = input_data", "input_data": "{{{{step_1.output}}}}"}},
      "expected_output": "Processed data",
      "dependencies": [1]
    }}
  ]
}}"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state['user_input']}
            ]
            
            # 调用 LLM 生成计划
            plan_json = self.llm_client.chat_with_json(messages)
            
            # 构建 Plan 对象，确保类型正确
            steps = []
            for step_data in plan_json.get("steps", []):
                # 确保 dependencies 是整数数组
                deps = step_data.get("dependencies", [])
                if isinstance(deps, list):
                    # 转换所有元素为整数
                    step_data["dependencies"] = [int(d) if isinstance(d, (int, float, str)) and str(d).isdigit() else 0 for d in deps]
                else:
                    step_data["dependencies"] = []
                
                # 确保 step_id 是整数
                if "step_id" in step_data:
                    step_data["step_id"] = int(step_data["step_id"])
                
                steps.append(Step.from_dict(step_data))
            
            plan = Plan(
                task_id=state['task_id'],
                steps=steps
            )
            
            print(f"[Plan Node] Created plan with {len(steps)} steps")
            
            return {
                "plan": plan,
                "messages": [AIMessage(content=f"Plan created with {len(steps)} steps")],
                "current_step": 0
            }
            
        except Exception as e:
            print(f"[Plan Node] Error: {e}")
            return {
                "error": f"Planning failed: {str(e)}",
                "completed": True
            }
    
    def _execute_step_node(self, state: AgentState) -> Dict[str, Any]:
        """执行步骤节点"""
        plan = state['plan']
        current_idx = state['current_step']
        
        if not plan or current_idx >= len(plan.steps):
            return {"completed": True}
        
        step = plan.steps[current_idx]
        print(f"[Execute Node] Executing step {step.step_id}: {step.description}")
        
        try:
            start_time = datetime.now()
            
            # 解析参数中的依赖引用
            resolved_params = self._resolve_parameters(
                step.parameters, 
                state['step_results']
            )
            
            # 执行工具
            output = ToolRegistry.execute_tool(step.tool, resolved_params)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 创建步骤结果
            step_result = StepResult(
                step_id=step.step_id,
                status="success",
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
            
            print(f"[Execute Node] Step {step.step_id} completed in {duration:.2f}s")
            
            return {
                "step_results": [step_result],
                "current_step": current_idx + 1,
                "messages": [AIMessage(content=f"Step {step.step_id} completed")]
            }
            
        except Exception as e:
            print(f"[Execute Node] Error in step {step.step_id}: {e}")
            
            step_result = StepResult(
                step_id=step.step_id,
                status="failed",
                output=None,
                error=str(e),
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0
            )
            
            return {
                "step_results": [step_result],
                "error": f"Step {step.step_id} failed: {str(e)}",
                "completed": True
            }
    
    def _check_completion_node(self, state: AgentState) -> Dict[str, Any]:
        """检查完成节点"""
        plan = state['plan']
        current_idx = state['current_step']
        
        if not plan:
            return {"completed": True}
        
        # 检查是否所有步骤都已执行
        if current_idx >= len(plan.steps):
            print("[Check Node] All steps completed")
            return {"completed": True}
        
        print(f"[Check Node] Progress: {current_idx}/{len(plan.steps)} steps")
        return {}
    
    def _finalize_node(self, state: AgentState) -> Dict[str, Any]:
        """最终化节点：生成最终输出"""
        print("[Finalize Node] Generating final output")
        
        if state.get('error'):
            return {
                "final_output": {
                    "status": "failed",
                    "error": state['error']
                },
                "completed": True
            }
        
        # 获取最后一个步骤的输出作为最终结果
        step_results = state.get('step_results', [])
        if step_results:
            last_result = step_results[-1]
            final_output = {
                "status": "completed",
                "result": last_result.output,
                "steps_executed": len(step_results),
                "execution_time": sum(r.duration for r in step_results)
            }
        else:
            final_output = {
                "status": "completed",
                "result": None,
                "steps_executed": 0
            }
        
        return {
            "final_output": final_output,
            "completed": True
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """决定是否继续执行"""
        if state.get('error'):
            return "error"
        return "check"
    
    def _check_if_done(self, state: AgentState) -> str:
        """检查是否完成"""
        if state.get('completed'):
            return "finish"
        return "continue"

    def _resolve_parameters(
        self, 
        parameters: Dict[str, Any], 
        step_results: List[StepResult]
    ) -> Dict[str, Any]:
        """解析参数中的步骤引用"""
        import re
        
        def resolve_value(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            
            # 匹配 {{step_N.output}} 模式
            pattern = r'\{\{step_(\d+)\.output\}\}'
            matches = re.findall(pattern, value)
            
            if not matches:
                return value
            
            # 如果整个值就是一个引用，直接返回引用的值
            if value.strip() == f"{{{{step_{matches[0]}.output}}}}":
                step_id = int(matches[0])
                for result in step_results:
                    if result.step_id == step_id:
                        return result.output
                return None
            
            # 否则进行字符串替换
            result = value
            for step_id_str in matches:
                step_id = int(step_id_str)
                for step_result in step_results:
                    if step_result.step_id == step_id:
                        placeholder = f"{{{{step_{step_id}.output}}}}"
                        result = result.replace(placeholder, str(step_result.output))
            
            return result
        
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, dict):
                resolved[key] = self._resolve_parameters(value, step_results)
            elif isinstance(value, list):
                resolved[key] = [resolve_value(item) for item in value]
            else:
                resolved[key] = resolve_value(value)
        
        return resolved
    
    def run(self, task_id: str, user_input: str) -> Dict[str, Any]:
        """运行 Agent"""
        print(f"\n[LangGraph Agent] Starting task: {task_id}")
        print(f"[LangGraph Agent] User input: {user_input}")
        
        # 初始化状态
        initial_state = AgentState(
            task_id=task_id,
            user_input=user_input,
            messages=[],
            plan=None,
            current_step=0,
            step_results=[],
            final_output=None,
            error=None,
            completed=False
        )
        
        # 执行图
        try:
            final_state = self.graph.invoke(initial_state)
            
            print(f"[LangGraph Agent] Task completed")
            
            return {
                "status": "completed" if not final_state.get('error') else "failed",
                "task_id": task_id,
                "plan": final_state.get('plan').to_dict() if final_state.get('plan') else None,
                "result": final_state.get('final_output'),
                "step_results": [r.to_dict() for r in final_state.get('step_results', [])],
                "error": final_state.get('error')  # 添加错误字段
            }
            
        except Exception as e:
            print(f"[LangGraph Agent] Error: {e}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e)
            }
