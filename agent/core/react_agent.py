"""
ReAct Agent - Reason + Act 循环模式
每一轮：Thought（思考）→ Action（行动）→ Observation（观察）
直到任务完成或达到最大轮数
"""

import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from llm_client import get_llm_client
from tools.base import ToolRegistry


@dataclass
class ReActStep:
    """ReAct 单轮记录"""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_num": self.step_num,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ReActResult:
    """ReAct 执行结果"""
    task_id: str
    user_input: str
    status: str  # "completed" | "failed" | "max_iterations"
    final_answer: Optional[str] = None
    steps: List[ReActStep] = field(default_factory=list)
    total_iterations: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_input": self.user_input,
            "status": self.status,
            "final_answer": self.final_answer,
            "steps": [s.to_dict() for s in self.steps],
            "total_iterations": self.total_iterations,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error": self.error
        }


class ReActAgent:
    """
    ReAct Agent 实现
    
    核心循环：
    1. Thought: LLM 分析当前状态，思考下一步该做什么
    2. Action: 选择工具并执行
    3. Observation: 获取工具执行结果
    4. 重复直到 LLM 输出 Final Answer 或达到最大轮数
    """
    
    def __init__(self, max_iterations: int = 10):
        """
        初始化 ReAct Agent
        
        Args:
            max_iterations: 最大迭代次数，防止无限循环
        """
        self.llm = get_llm_client()
        self.max_iterations = max_iterations
    
    def run(self, task_id: str, user_input: str, initial_context: Dict[str, Any] = None) -> ReActResult:
        """
        执行 ReAct 循环
        
        Args:
            task_id: 任务 ID
            user_input: 用户输入的任务描述
            initial_context: 初始上下文变量
        
        Returns:
            ReActResult 执行结果
        """
        result = ReActResult(
            task_id=task_id,
            user_input=user_input,
            status="running"
        )
        
        # 构建初始消息
        system_prompt = self._build_system_prompt()
        messages = self._build_initial_messages(user_input, initial_context)
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'='*50}")
            print(f"ReAct 迭代 #{iteration}")
            print(f"{'='*50}")
            
            try:
                # 调用 LLM 获取 Thought 和 Action
                llm_response = self.llm.chat(
                    messages=messages,
                    system=system_prompt
                )
                
                print(f"\nLLM 响应:\n{llm_response}")
                
                # 解析 LLM 输出
                parsed = self._parse_llm_output(llm_response)
                
                # 创建步骤记录
                step = ReActStep(
                    step_num=iteration,
                    thought=parsed.get("thought", "")
                )
                
                # 检查是否完成（Final Answer）
                if parsed.get("final_answer"):
                    step.observation = f"任务完成: {parsed['final_answer']}"
                    result.steps.append(step)
                    result.final_answer = parsed["final_answer"]
                    result.status = "completed"
                    result.total_iterations = iteration
                    result.end_time = datetime.now()
                    print(f"\n✅ 任务完成！最终答案: {parsed['final_answer']}")
                    return result
                
                # 获取 Action
                action = parsed.get("action")
                action_input = parsed.get("action_input", {})
                
                if not action:
                    # 没有有效的 action，添加提示让 LLM 继续
                    messages.append({"role": "assistant", "content": llm_response})
                    messages.append({
                        "role": "user", 
                        "content": "请按照格式要求，输出 Thought、Action、Action Input，或者如果任务已完成，输出 Final Answer。"
                    })
                    continue
                
                step.action = action
                step.action_input = action_input
                
                print(f"\n🔧 执行工具: {action}")
                print(f"   参数: {json.dumps(action_input, ensure_ascii=False, indent=2)}")
                
                # 执行工具
                try:
                    observation = ToolRegistry.execute_tool(action, action_input)
                    
                    # 格式化观察结果
                    if isinstance(observation, dict):
                        obs_str = json.dumps(observation, ensure_ascii=False, indent=2)
                    else:
                        obs_str = str(observation)
                    
                    # 限制观察结果长度
                    if len(obs_str) > 3000:
                        obs_str = obs_str[:3000] + "\n... (结果已截断)"
                    
                    step.observation = obs_str
                    print(f"\n📋 观察结果:\n{obs_str[:500]}{'...' if len(obs_str) > 500 else ''}")
                    
                except Exception as e:
                    error_msg = f"工具执行失败: {str(e)}"
                    step.observation = error_msg
                    step.error = str(e)
                    print(f"\n❌ {error_msg}")
                
                result.steps.append(step)
                
                # 将本轮结果添加到消息历史
                messages.append({"role": "assistant", "content": llm_response})
                messages.append({
                    "role": "user",
                    "content": f"Observation: {step.observation}\n\n请根据上述观察结果，继续思考下一步行动，或者如果任务已完成，给出最终答案。"
                })
                
            except Exception as e:
                print(f"\n❌ 迭代 #{iteration} 发生错误: {str(e)}")
                result.steps.append(ReActStep(
                    step_num=iteration,
                    thought="",
                    error=str(e)
                ))
                result.status = "failed"
                result.error = str(e)
                result.end_time = datetime.now()
                return result
        
        # 达到最大迭代次数
        result.status = "max_iterations"
        result.total_iterations = iteration
        result.end_time = datetime.now()
        result.error = f"达到最大迭代次数 ({self.max_iterations})，任务未完成"
        print(f"\n⚠️ {result.error}")
        
        return result
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_schema = ToolRegistry.get_all_schemas_for_llm()
        
        return f"""你是一个智能助手，使用 ReAct（Reason + Act）模式来解决用户的问题。

## 可用工具
{tools_schema}

## 工作流程
你需要通过多轮 "思考-行动-观察" 循环来完成任务：

1. **Thought（思考）**: 分析当前状态，思考下一步该做什么
2. **Action（行动）**: 选择一个工具来执行
3. **Action Input（行动输入）**: 提供工具所需的参数（JSON 格式）
4. **Observation（观察）**: 系统会返回工具执行的结果

当你认为任务已经完成时，输出：
- **Final Answer（最终答案）**: 给出最终的回答

## 输出格式要求（严格遵守）

每次回复必须按以下格式：

```
Thought: <你的思考过程，分析当前状态和下一步计划>

Action: <工具名称，必须是可用工具之一>

Action Input: <JSON 格式的参数>
```

或者当任务完成时：

```
Thought: <总结思考>

Final Answer: <最终答案，回答用户的问题>
```

## 重要规则
1. 每次只能执行一个 Action
2. 必须等待 Observation 后再决定下一步
3. Action 必须是可用工具列表中的工具名称
4. Action Input 必须是合法的 JSON 格式
5. 如果工具执行失败，分析原因并尝试其他方法
6. 不要编造工具执行结果，必须等待真实的 Observation
"""
    
    def _build_initial_messages(self, user_input: str, initial_context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """构建初始消息"""
        context_str = ""
        if initial_context:
            context_str = f"\n\n初始上下文:\n{json.dumps(initial_context, ensure_ascii=False, indent=2)}"
        
        return [{
            "role": "user",
            "content": f"""请帮我完成以下任务：

{user_input}{context_str}

请开始你的思考和行动。"""
        }]
    
    def _parse_llm_output(self, output: str) -> Dict[str, Any]:
        """
        解析 LLM 输出
        
        提取：
        - Thought
        - Action
        - Action Input
        - Final Answer
        """
        result = {
            "thought": "",
            "action": None,
            "action_input": {},
            "final_answer": None
        }
        
        # 提取 Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final Answer)|\Z)', output, re.DOTALL | re.IGNORECASE)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()
        
        # 检查是否有 Final Answer
        final_match = re.search(r'Final Answer:\s*(.+?)$', output, re.DOTALL | re.IGNORECASE)
        if final_match:
            result["final_answer"] = final_match.group(1).strip()
            return result
        
        # 提取 Action
        action_match = re.search(r'Action:\s*(\w+)', output, re.IGNORECASE)
        if action_match:
            result["action"] = action_match.group(1).strip()
        
        # 提取 Action Input
        action_input_match = re.search(r'Action Input:\s*(\{.+?\})', output, re.DOTALL | re.IGNORECASE)
        if action_input_match:
            try:
                # 尝试解析 JSON
                json_str = action_input_match.group(1)
                result["action_input"] = json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试更宽松的 JSON 提取
                try:
                    # 查找从 { 开始到最后一个 } 的内容
                    json_start = output.find('{', output.lower().find('action input'))
                    if json_start != -1:
                        # 计算匹配的 }
                        brace_count = 0
                        json_end = json_start
                        for i, char in enumerate(output[json_start:]):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = json_start + i + 1
                                    break
                        json_str = output[json_start:json_end]
                        result["action_input"] = json.loads(json_str)
                except:
                    print(f"⚠️ 无法解析 Action Input JSON")
        
        return result


# 便捷函数
def create_react_agent(max_iterations: int = 10) -> ReActAgent:
    """创建 ReAct Agent 实例"""
    return ReActAgent(max_iterations=max_iterations)
