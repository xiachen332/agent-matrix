"""Agent 基类定义"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional

if TYPE_CHECKING:
    from ..knowledge import ProjectContext


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
    file_path: Optional[str] = None  # 目标文件路径（用于 Coder/Tester 等）
    image_urls: List[str] = field(default_factory=list)  # 图片URL列表（支持 Markdown 和纯URL）

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

    def __init__(self):
        self._project_context = None

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

    async def execute_stream(self, task: Task):
        """流式执行任务，逐字产出

        Yields:
            str: 增量输出文本
        """
        # 默认实现：调用普通 execute，结果逐字 yield
        result = await self.execute(task)
        for char in result.output:
            yield char

    def set_project_context(self, context: "ProjectContext") -> None:
        """设置项目上下文

        Args:
            context: 项目上下文对象
        """
        self._project_context = context

    def get_project_context(self) -> "ProjectContext":
        """获取项目上下文"""
        return self._project_context

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.role}>"
