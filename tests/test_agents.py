"""Agent 相关测试"""

import pytest

from agent_matrix.pool import AgentPool
from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.agents.coder import CoderAgent
from agent_matrix.agents.reviewer import ReviewerAgent
from agent_matrix.agents.tester import TesterAgent


class TestAgentPool:
    """Agent 池测试"""

    @pytest.fixture
    def pool(self):
        return AgentPool()

    def test_register_and_get(self, pool):
        """测试 Agent 注册和获取"""
        coder = CoderAgent()
        pool.register(coder)

        retrieved = pool.get("coder")
        assert retrieved is coder

    def test_get_nonexistent(self, pool):
        """测试获取不存在的 Agent"""
        assert pool.get("nonexistent") is None

    def test_list_agents(self, pool):
        """测试列出所有 Agent"""
        pool.register(CoderAgent())
        pool.register(ReviewerAgent())

        agents = pool.list_agents()
        assert "coder" in agents
        assert "reviewer" in agents

    def test_get_by_description_coder(self, pool):
        """测试通过描述匹配 Coder Agent"""
        pool.register(CoderAgent())
        pool.register(ReviewerAgent())

        agent = pool.get_by_description("编写登录功能代码")
        assert agent is not None
        assert agent.role == "coder"

    def test_get_by_description_reviewer(self, pool):
        """测试通过描述匹配 Reviewer Agent"""
        pool.register(CoderAgent())
        pool.register(ReviewerAgent())

        agent = pool.get_by_description("审查订单模块代码")
        assert agent is not None
        assert agent.role == "reviewer"


class TestAgents:
    """具体 Agent 测试"""

    @pytest.mark.asyncio
    async def test_coder_agent_execute(self):
        """测试 Coder Agent 执行"""
        coder = CoderAgent()
        task = Task(id="t1", description="实现用户模块")

        result = await coder.execute(task)

        assert result.success
        assert "Coder" in result.output

    @pytest.mark.asyncio
    async def test_reviewer_agent_execute(self):
        """测试 Reviewer Agent 执行"""
        reviewer = ReviewerAgent()
        task = Task(id="t1", description="审查代码")

        result = await reviewer.execute(task)

        assert result.success
        assert "Reviewer" in result.output

    @pytest.mark.asyncio
    async def test_tester_agent_execute(self):
        """测试 Tester Agent 执行"""
        tester = TesterAgent()
        task = Task(id="t1", description="测试登录功能")

        result = await tester.execute(task)

        assert result.success
        assert "Tester" in result.output
