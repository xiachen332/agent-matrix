"""Coder Agent 实现"""

from typing import Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm.minimax import MiniMaxAdapter


SYSTEM_PROMPT = """你是一个专业开发者，负责根据任务描述编写高质量代码。

要求：
1. 直接输出代码实现，不要解释
2. 代码要完整、可运行
3. 包含必要的注释说明关键逻辑
4. 遵循良好的编码规范"""


class CoderAgent(Agent):
    """Coder Agent - 负责代码编写"""

    def __init__(
        self,
        llm_adapter: Optional[MiniMaxAdapter] = None,
        api_key: Optional[str] = None,
    ):
        """初始化 Coder Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
        """
        self._llm = llm_adapter
        if not self._llm and (api_key or True):
            self._llm = MiniMaxAdapter(api_key=api_key)

    @property
    def role(self) -> str:
        return "coder"

    @property
    def description(self) -> str:
        return "代码编写、实现功能、开发"

    async def execute(self, task: Task) -> AgentResult:
        """执行编码任务"""
        if self._llm is None or not self._llm.is_configured:
            return AgentResult(
                success=True,
                output=f"[Coder] 已完成(模拟): {task.description}",
                metadata={"agent": "coder", "mode": "mock"}
            )

        try:
            prompt = f"{SYSTEM_PROMPT}\n\n任务：{task.description}"
            output = await self._llm.complete(prompt, temperature=0.7)
            return AgentResult(
                success=True,
                output=output,
                metadata={"agent": "coder", "mode": "llm"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "coder", "mode": "llm"}
            )
