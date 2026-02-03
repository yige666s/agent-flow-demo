"""
Executor - 任务执行器
负责按照 Plan 逐步执行任务
"""

import re
from datetime import datetime
from typing import Any, Dict
from models import Plan, ExecutionContext, StepResult
from tools.base import ToolRegistry
import json


class Executor:
    """任务执行器"""
    
    def __init__(self):
        pass
    
    def execute_plan(self, plan: Plan, user_input: str, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行计划
        
        Args:
            plan: 执行计划
            user_input: 用户输入
            initial_context: 初始上下文
        
        Returns:
            执行结果
        """
        # 创建执行上下文
        context = ExecutionContext(
            task_id=plan.task_id,
            user_input=user_input,
            plan=plan,
            variables=initial_context or {}
        )
        
        # 逐步执行
        for step in plan.steps:
            print(f"Executing step {step.step_id}: {step.description}")
            
            # 执行步骤
            result = self._execute_step(step, context)
            
            # 添加到上下文
            context.add_step_result(result)
            
            # 如果步骤失败，停止执行
            if result.status == "failed":
                return {
                    "status": "failed",
                    "task_id": plan.task_id,
                    "error": f"Step {step.step_id} failed: {result.error}",
                    "context": context.to_dict()
                }
        
        # 生成最终结果
        final_output = self._generate_final_output(context)
        
        return {
            "status": "completed",
            "task_id": plan.task_id,
            "result": final_output,
            "context": context.to_dict()
        }
    
    def _execute_step(self, step, context: ExecutionContext) -> StepResult:
        """执行单个步骤"""
        start_time = datetime.now()
        
        try:
            # 解析参数（替换变量引用）
            resolved_params = self._resolve_parameters(step.parameters, context)
            
            # 调用工具
            output = ToolRegistry.execute_tool(step.tool, resolved_params)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return StepResult(
                step_id=step.step_id,
                status="success",
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
        
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return StepResult(
                step_id=step.step_id,
                status="failed",
                output=None,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
    
    def _resolve_parameters(self, parameters: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        解析参数中的变量引用
        
        支持格式：
        - {{step_1.output}}
        - {{step_2.output.data.title}}
        - {{variables.user_name}}
        """
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # 查找所有 {{...}} 引用
                resolved[key] = self._resolve_value(value, context)
            elif isinstance(value, dict):
                # 递归处理字典
                resolved[key] = self._resolve_parameters(value, context)
            elif isinstance(value, list):
                # 处理列表
                resolved[key] = [
                    self._resolve_value(item, context) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_value(self, value: str, context: ExecutionContext) -> Any:
        """解析单个值中的变量引用"""
        # 匹配 {{...}} 模式
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, value)
        
        if not matches:
            return value
        
        # 如果整个值就是一个引用，直接返回引用的值
        if value.strip() == f"{{{{{matches[0]}}}}}":
            return self._get_reference_value(matches[0].strip(), context)
        
        # 否则进行字符串替换
        result = value
        for match in matches:
            ref_value = self._get_reference_value(match.strip(), context)
            # 转换为字符串进行替换
            if isinstance(ref_value, (dict, list)):
                ref_str = json.dumps(ref_value, ensure_ascii=False)
            else:
                ref_str = str(ref_value)
            result = result.replace(f"{{{{{match}}}}}", ref_str)
        
        return result
    
    def _get_reference_value(self, ref: str, context: ExecutionContext) -> Any:
        """获取引用的值"""
        parts = ref.split('.')
        
        if parts[0].startswith('step_'):
            # 解析 step_X.output.path
            step_id = int(parts[0].replace('step_', ''))
            value = context.get_step_output(step_id)
            
            # 处理嵌套路径
            for part in parts[1:]:
                if part == 'output':
                    continue
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    raise ValueError(f"Cannot access '{part}' on non-dict value")
            
            return value
        
        elif parts[0] == 'variables':
            # 解析 variables.name
            var_name = '.'.join(parts[1:])
            return context.variables.get(var_name)
        
        else:
            raise ValueError(f"Invalid reference format: {ref}")
    
    def _generate_final_output(self, context: ExecutionContext) -> Dict[str, Any]:
        """生成最终输出"""
        # 获取最后一个步骤的输出作为最终结果
        if not context.step_results:
            return {}
        
        last_step_id = max(context.step_results.keys())
        last_output = context.step_results[last_step_id].output
        
        return {
            "final_output": last_output,
            "steps_executed": len(context.step_results),
            "execution_time": (context.updated_at - context.created_at).total_seconds()
        }
