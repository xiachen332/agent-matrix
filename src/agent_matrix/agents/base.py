"""Agent 基类定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """任务数据类"""
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    result: Optional["AgentResult"] = None
    status: TaskStatus = TaskStatus.PENDING

    def __hash__(self):
        return hash(self.id)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Agent 抽象基类"""

    @property
    @abstractmethod
    def role(self) -> str:
        """Agent 角色标识"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent 功能描述（用于任务匹配）"""
        ...

    @abstractmethod
    async def execute(self, task: Task) -> AgentResult:
        """执行任务"""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.role}>"
