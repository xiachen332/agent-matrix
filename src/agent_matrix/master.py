"""Master Agent - 主控 Agent"""

from typing import List, Optional

from .agents.base import AgentResult, Task
from .decomposer import TaskDecomposer
from .engine import CollaborationEngine
from .aggregator import ResultAggregator, ExecutionReport
from .pool import AgentPool


class MasterAgent:
    """Master Agent 主控

    协调任务分解、调度执行、结果汇总的完整流程。
    """

    def __init__(
        self,
        pool: Optional[AgentPool] = None,
        decomposer: Optional[TaskDecomposer] = None,
    ):
        """初始化 Master Agent

        Args:
            pool: Agent 池实例
            decomposer: 任务分解器实例
        """
        self._pool = pool or AgentPool()
        self._decomposer = decomposer or TaskDecomposer()
        self._engine = CollaborationEngine(self._pool)
        self._aggregator = ResultAggregator()

    @property
    def pool(self) -> AgentPool:
        """获取 Agent 池"""
        return self._pool

    async def execute_task(
        self,
        task_description: str,
        session_config=None,
        documents=None,
    ) -> ExecutionReport:
        """执行单个任务

        完整流程：分解 -> 调度 -> 汇总

        Args:
            task_description: 任务描述
            session_config: 会话配置（用于触发 Webhook）
            documents: 文档列表，用于 LLM 分析

        Returns:
            执行报告
        """
        # 1. 任务分解
        subtasks = await self._decomposer.decompose(task_description, documents=documents)

        # 2. 执行任务
        completed_tasks = await self._engine.execute(subtasks)

        # 3. 汇总结果
        report = self._aggregator.aggregate(completed_tasks)

        # 4. 触发 Webhook
        if session_config and session_config.webhooks:
            webhook_payload = {
                "task": task_description,
                "report": {
                    "total_tasks": report.total_tasks,
                    "successful_tasks": report.successful_tasks,
                    "failed_tasks": report.failed_tasks,
                }
            }
            await session_config.trigger_webhooks(webhook_payload)

        return report

    async def execute_tasks(self, task_descriptions: List[str]) -> List[ExecutionReport]:
        """批量执行多个任务

        Args:
            task_descriptions: 任务描述列表

        Returns:
            每个任务的执行报告列表
        """
        reports = []
        for desc in task_descriptions:
            report = await self.execute_task(desc)
            reports.append(report)
        return reports
