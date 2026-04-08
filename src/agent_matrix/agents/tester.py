"""Tester Agent 实现"""

from typing import Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm.minimax import MiniMaxAdapter


SYSTEM_PROMPT = """你是一个测试专家，负责为代码编写测试用例。

要求：
1. 分析代码功能，设计全面的测试用例
2. 覆盖正常路径和边界情况
3. 测试用例要可执行
4. 包含单元测试和集成测试（根据需要）

请输出：
- 测试策略说明
- 具体测试用例代码
- 运行测试的说明"""


class TesterAgent(Agent):
    """Tester Agent - 负责测试验证"""

    def __init__(
        self,
        llm_adapter: Optional[MiniMaxAdapter] = None,
        api_key: Optional[str] = None,
    ):
        """初始化 Tester Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
        """
        self._llm = llm_adapter
        if not self._llm and (api_key or True):
            self._llm = MiniMaxAdapter(api_key=api_key)

    @property
    def role(self) -> str:
        return "tester"

    @property
    def description(self) -> str:
        return "测试、test、验证功能"

    async def execute(self, task: Task) -> AgentResult:
        """执行测试任务"""
        if self._llm is None or not self._llm.is_configured:
            return AgentResult(
                success=True,
                output=f"[Tester] 已测试(模拟): {task.description}",
                metadata={"agent": "tester", "mode": "mock"}
            )

        try:
            prompt = f"{SYSTEM_PROMPT}\n\n待测试的代码/功能：{task.description}"
            output = await self._llm.complete(prompt, temperature=0.5)
            return AgentResult(
                success=True,
                output=output,
                metadata={"agent": "tester", "mode": "llm"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "tester", "mode": "llm"}
            )
