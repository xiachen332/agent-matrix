"""Reviewer Agent 实现"""

from typing import Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm.minimax import MiniMaxAdapter


SYSTEM_PROMPT = """你是一个专业的代码审查专家，负责审查代码并提供改进建议。

审查要点：
1. 代码正确性：逻辑是否正确、边界条件处理
2. 代码质量：命名规范、代码结构、可读性
3. 安全性：潜在的安全漏洞、输入验证
4. 性能：是否有性能问题
5. 最佳实践：是否符合语言/框架的最佳实践

请输出：
- 发现的问题列表
- 具体的改进建议
- 代码评分（1-10）"""


class ReviewerAgent(Agent):
    """Reviewer Agent - 负责代码审查"""

    def __init__(
        self,
        llm_adapter: Optional[MiniMaxAdapter] = None,
        api_key: Optional[str] = None,
    ):
        """初始化 Reviewer Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
        """
        self._llm = llm_adapter
        if not self._llm and (api_key or True):
            self._llm = MiniMaxAdapter(api_key=api_key)

    @property
    def role(self) -> str:
        return "reviewer"

    @property
    def description(self) -> str:
        return "代码审查、review、检查代码质量"

    async def execute(self, task: Task) -> AgentResult:
        """执行审查任务"""
        if self._llm is None or not self._llm.is_configured:
            return AgentResult(
                success=True,
                output=f"[Reviewer] 已审查(模拟): {task.description}",
                metadata={"agent": "reviewer", "mode": "mock"}
            )

        try:
            prompt = f"{SYSTEM_PROMPT}\n\n待审查代码/任务：{task.description}"
            output = await self._llm.complete(prompt, temperature=0.5)
            return AgentResult(
                success=True,
                output=output,
                metadata={"agent": "reviewer", "mode": "llm"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "reviewer", "mode": "llm"}
            )
