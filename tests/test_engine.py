"""CollaborationEngine 测试"""

import pytest

from agent_matrix.engine import CollaborationEngine
from agent_matrix.pool import AgentPool
from agent_matrix.agents.base import Task, TaskStatus
from agent_matrix.agents.coder import CoderAgent


class TestCollaborationEngine:
    """协作引擎测试"""

    @pytest.fixture
    def pool(self):
        """创建测试用的 Agent 池"""
        pool = AgentPool()
        pool.register(CoderAgent())
        return pool

    @pytest.fixture
    def engine(self, pool):
        """创建协作引擎"""
        return CollaborationEngine(pool)

    @pytest.mark.asyncio
    async def test_execute_single_task(self, engine):
        """测试执行单个任务"""
        task = Task(id="t1", description="编写代码实现功能")
        tasks = await engine.execute([task])

        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_dependent_tasks(self, engine):
        """测试有依赖关系的任务"""
        task1 = Task(id="t1", description="分析需求", dependencies=[])
        task2 = Task(id="t2", description="编写代码", dependencies=["t1"])
        task3 = Task(id="t3", description="测试", dependencies=["t2"])

        tasks = await engine.execute([task1, task2, task3])

        assert all(t.status == TaskStatus.COMPLETED for t in tasks)

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self, engine):
        """测试可并行执行的任务"""
        task1 = Task(id="t1", description="任务A", dependencies=[])
        task2 = Task(id="t2", description="任务B", dependencies=[])

        tasks = await engine.execute([task1, task2])

        assert len(tasks) == 2
        assert all(t.status == TaskStatus.COMPLETED for t in tasks)

    @pytest.mark.asyncio
    async def test_topological_sort(self, engine):
        """测试拓扑排序"""
        task1 = Task(id="t1", description="A", dependencies=[])
        task2 = Task(id="t2", description="B", dependencies=["t1"])
        task3 = Task(id="t3", description="C", dependencies=["t1"])
        task4 = Task(id="t4", description="D", dependencies=["t2", "t3"])

        tasks = [task4, task2, task3, task1]  # 乱序输入
        in_degree = {"t1": 0, "t2": 1, "t3": 1, "t4": 2}

        batches = engine._topological_sort(tasks, in_degree)

        assert len(batches) == 3
        assert "t1" in batches[0]
        assert "t2" in batches[1] and "t3" in batches[1]
        assert "t4" in batches[2]
