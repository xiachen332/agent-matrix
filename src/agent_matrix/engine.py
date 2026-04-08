"""协作引擎 - 解析任务依赖拓扑并调度执行"""

import asyncio
from typing import List, Optional

from .agents.base import Agent, AgentResult, Task, TaskStatus
from .pool import AgentPool


class CollaborationEngine:
    """协作引擎

    负责：
    1. 解析任务依赖关系，构建拓扑排序
    2. 按执行顺序调度 Agent
    3. 管理任务状态转换
    """

    def __init__(self, pool: AgentPool):
        """初始化协作引擎

        Args:
            pool: Agent 池实例
        """
        self._pool = pool

    async def execute(self, tasks: List[Task]) -> List[Task]:
        """执行任务列表

        使用 Kahn 算法进行拓扑排序，保证依赖任务先执行。
        独立任务可以并行执行。

        Args:
            tasks: 任务列表

        Returns:
            带执行结果的完整任务列表
        """
        if not tasks:
            return []

        # 构建依赖图和入度表
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: len(t.dependencies) for t in tasks}

        # 拓扑排序 - Kahn 算法
        execution_order = self._topological_sort(tasks, in_degree)

        # 按批次执行（同一批次内可并行）
        completed_tasks: dict[str, Task] = {}

        for batch in execution_order:
            batch_tasks = [task_map[task_id] for task_id in batch]

            # 为每个任务分配 Agent
            for task in batch_tasks:
                if task.assigned_agent is None:
                    agent = self._pool.get_by_description(task.description)
                    if agent:
                        task.assigned_agent = agent.role

            # 并行执行当前批次
            results = await asyncio.gather(
                *[self._execute_task(task, task_map) for task in batch_tasks],
                return_exceptions=True
            )

            # 更新任务结果
            for task, result in zip(batch_tasks, results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.result = AgentResult(
                        success=False,
                        output="",
                        error=str(result)
                    )
                completed_tasks[task.id] = task

        return list(task_map.values())

    async def _execute_task(self, task: Task, task_map: dict[str, Task]) -> AgentResult:
        """执行单个任务"""
        # 确保依赖任务已完成
        for dep_id in task.dependencies:
            dep_task = task_map.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                # 等待依赖完成
                while dep_task.status == TaskStatus.RUNNING:
                    await asyncio.sleep(0.1)

                if dep_task.status != TaskStatus.COMPLETED:
                    return AgentResult(
                        success=False,
                        output="",
                        error=f"依赖任务 {dep_id} 未成功完成"
                    )

        task.status = TaskStatus.RUNNING

        # 获取 Agent 并执行
        agent = self._pool.get(task.assigned_agent) if task.assigned_agent else None

        if agent is None:
            task.status = TaskStatus.FAILED
            return AgentResult(
                success=False,
                output="",
                error=f"未找到合适的 Agent 执行任务: {task.description}"
            )

        try:
            result = await agent.execute(task)
            task.result = result
            task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            return result
        except Exception as e:
            task.status = TaskStatus.FAILED
            return AgentResult(
                success=False,
                output="",
                error=str(e)
            )

    def _topological_sort(
        self,
        tasks: List[Task],
        in_degree: dict[str, int]
    ) -> List[List[str]]:
        """拓扑排序，返回分批执行顺序

        Returns:
            二维列表，每个内层列表代表一批可并行执行的任务
        """
        task_map = {t.id: t for t in tasks}
        current_in_degree = in_degree.copy()
        batches: List[List[str]] = []

        while True:
            # 找出所有入度为 0 的任务
            batch = [
                task_id for task_id, degree in current_in_degree.items()
                if degree == 0
            ]

            if not batch:
                break

            batches.append(batch)

            # 更新入度
            for task_id in batch:
                current_in_degree[task_id] = -1  # 标记为已处理
                task = task_map[task_id]
                for dependent_id in self._get_dependents(task_id, tasks):
                    current_in_degree[dependent_id] -= 1

        return batches

    def _get_dependents(self, task_id: str, tasks: List[Task]) -> List[str]:
        """获取直接依赖指定任务的所有任务 ID"""
        return [
            t.id for t in tasks
            if task_id in t.dependencies
        ]
