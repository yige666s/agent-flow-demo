"""
Planner - 任务规划器
负责将用户任务拆解为结构化的执行计划
"""

from typing import Dict, Any
from models import Plan, Step
from llm_client import get_llm_client
from tools.base import ToolRegistry
import json


class Planner:
    """任务规划器"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    def create_plan(self, task_id: str, user_input: str) -> Plan:
        """
        创建执行计划
        
        Args:
            task_id: 任务 ID
            user_input: 用户输入
        
        Returns:
            Plan 对象
        """
        # 构造系统提示词
        system_prompt = self._build_system_prompt()
        
        # 构造用户消息
        user_message = f"""请分析以下用户任务，并将其拆解为具体的执行步骤：

用户任务：{user_input}

请返回 JSON 格式的执行计划，包含以下字段：
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "tool": "工具名称",
            "parameters": {{"参数名": "参数值"}},
            "expected_output": "预期输出描述",
            "dependencies": [前置步骤ID列表]
        }}
    ]
}}

重要注意事项：
1. URL 必须完整，包含所有查询参数（如 ?q=xxx&sort=xxx）
2. 使用 python_exec 工具时，必须提供 input_data 参数来传入前一步的数据，格式：{{"input_data": "{{{{step_X.output}}}}"}}
3. 工具名称必须从可用工具列表中选择
4. 如果需要使用前面步骤的输出，使用 {{{{step_X.output}}}} 格式引用
5. dependencies 字段表示该步骤依赖哪些前置步骤
"""
        
        messages = [{"role": "user", "content": user_message}]
        
        try:
            # 调用 LLM
            response_json = self.llm.chat_with_json(
                messages=messages,
                system=system_prompt
            )
            
            # 解析步骤
            steps = []
            for step_data in response_json.get("steps", []):
                step = Step(
                    step_id=step_data["step_id"],
                    description=step_data["description"],
                    tool=step_data["tool"],
                    parameters=step_data["parameters"],
                    expected_output=step_data["expected_output"],
                    dependencies=step_data.get("dependencies", [])
                )
                steps.append(step)
            
            return Plan(task_id=task_id, steps=steps)
        
        except Exception as e:
            raise Exception(f"Failed to create plan: {str(e)}")
    
    def _build_system_prompt(self) -> str:
        """构造系统提示词"""
        tools_schema = ToolRegistry.get_all_schemas_for_llm()
        
        return f"""你是一个任务规划专家，擅长将复杂的用户需求拆解为可执行的步骤序列。

可用工具列表：
{tools_schema}

你的任务是：
1. 理解用户的意图和目标
2. 将任务拆解为多个具体步骤
3. 为每个步骤选择合适的工具
4. 设计步骤之间的数据流（通过变量引用）
5. 确保步骤的执行顺序是合理的

重要规则（必须遵守）：
1. http_request 的 url 参数必须包含完整的 URL，包括所有查询参数（如 ?key=value&key2=value2）
2. python_exec 工具必须同时提供 code 和 input_data 两个参数，input_data 用于传入前一步骤的输出
3. 参数值中引用前一步骤输出时使用 {{{{step_X.output}}}} 格式

拆解原则：
- 步骤要原子化：每个步骤只完成一个明确的子任务
- 工具选择要准确：根据步骤需求选择最合适的工具
- 参数要完整：确保工具执行所需的所有参数都提供了
- 数据流要清晰：步骤之间的数据传递要通过 {{{{step_X.output}}}} 明确表示

输出格式要求：
- 必须是合法的 JSON，不要添加任何额外说明文字
- 步骤 ID 从 1 开始递增
- dependencies 数组包含该步骤依赖的前置步骤的 ID
"""
