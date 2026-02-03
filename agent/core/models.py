"""
AgentFlow Python Agent Service
数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Step:
    """执行步骤"""
    step_id: int
    description: str
    tool: str
    parameters: Dict[str, Any]
    expected_output: str
    dependencies: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tool": self.tool,
            "parameters": self.parameters,
            "expected_output": self.expected_output,
            "dependencies": self.dependencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        return cls(
            step_id=data["step_id"],
            description=data["description"],
            tool=data["tool"],
            parameters=data["parameters"],
            expected_output=data["expected_output"],
            dependencies=data.get("dependencies", [])
        )


@dataclass
class Plan:
    """执行计划"""
    task_id: str
    steps: List[Step]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "steps": [step.to_dict() for step in self.steps]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        return cls(
            task_id=data["task_id"],
            steps=[Step.from_dict(s) for s in data["steps"]]
        )


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: int
    status: str  # success / failed / skipped
    output: Any
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata
        }


@dataclass
class ExecutionContext:
    """执行上下文"""
    task_id: str
    user_input: str
    plan: Plan
    step_results: Dict[int, StepResult] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_step_result(self, result: StepResult):
        """添加步骤结果"""
        self.step_results[result.step_id] = result
        self.updated_at = datetime.now()
    
    def get_step_output(self, step_id: int) -> Any:
        """获取指定步骤的输出"""
        if step_id not in self.step_results:
            raise ValueError(f"Step {step_id} not executed yet")
        return self.step_results[step_id].output
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_input": self.user_input,
            "plan": self.plan.to_dict(),
            "step_results": {
                str(k): v.to_dict() for k, v in self.step_results.items()
            },
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
