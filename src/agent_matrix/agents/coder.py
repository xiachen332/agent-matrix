"""Coder Agent 实现"""

import os
import re
from pathlib import Path
from typing import AsyncIterator, Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm import create_adapter


SYSTEM_PROMPT = """你是一个专业开发者，负责根据任务描述编写高质量代码。

要求：
1. 直接输出代码实现，不要解释
2. 代码要完整、可运行
3. 包含必要的注释说明关键逻辑
4. 遵循良好的编码规范
5. 必须用 markdown 代码块包裹代码，格式：```python\\n...\\n```"""


class CoderAgent(Agent):
    """Coder Agent - 负责代码编写"""

    def __init__(
        self,
        llm_adapter=None,
        api_key: Optional[str] = None,
        output_dir: Optional[str] = None,
        provider: Optional[str] = None,
        project_context=None,
    ):
        """初始化 Coder Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
            output_dir: 代码输出目录（默认为当前目录）
            provider: 提供商名称
            project_context: 项目上下文（可选，用于注入项目知识）
        """
        self._llm = llm_adapter
        if not self._llm:
            self._llm = create_adapter(provider=provider, api_key=api_key)
        self._output_dir = output_dir or "."
        self._project_context = project_context

    @property
    def role(self) -> str:
        return "coder"

    @property
    def description(self) -> str:
        return "代码编写、实现功能、开发"

    async def execute_stream(self, task: Task) -> AsyncIterator[str]:
        """流式执行编码任务"""
        if self._llm is None or not self._llm.is_configured:
            output = f"[Coder] 已完成(模拟): {task.description}"
            for char in output:
                yield char
            return

        context_info = self._build_context_info(task)
        prompt = f"{SYSTEM_PROMPT}\n\n任务：{task.description}\n\n{context_info}"
        image_urls = task.image_urls if hasattr(task, 'image_urls') else None

        async for token in self._llm.complete_stream(prompt, temperature=0.7, image_urls=image_urls):
            yield token

    async def execute(self, task: Task) -> AgentResult:
        """执行编码任务"""
        file_path = task.file_path

        if self._llm is None or not self._llm.is_configured:
            return AgentResult(
                success=True,
                output=f"[Coder] 已完成(模拟): {task.description}",
                metadata={"agent": "coder", "mode": "mock"}
            )

        try:
            # 构建上下文增强的提示词
            context_info = self._build_context_info(task)
            prompt = f"{SYSTEM_PROMPT}\n\n任务：{task.description}\n\n{context_info}"

            # 传递图片URL（用于多模态模型）
            image_urls = task.image_urls if hasattr(task, 'image_urls') else None

            output, _ = await self._llm.complete(prompt, temperature=0.7, image_urls=image_urls)

            # 提取代码块
            code = self._extract_code(output)

            # 写入文件
            if file_path and code:
                dest = Path(self._output_dir) / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(code, encoding="utf-8")
                written_file = str(dest)
            else:
                written_file = None

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "agent": "coder",
                    "mode": "llm",
                    "file_written": written_file,
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "coder", "mode": "llm"}
            )

    def _build_context_info(self, task: Task) -> str:
        """构建项目上下文信息"""
        parts = []

        # 添加项目上下文
        if self._project_context:
            parts.append(f"项目根目录: {self._project_context.root}")
            if self._project_context.key_modules:
                parts.append(f"关键模块: {', '.join(self._project_context.key_modules)}")

        # 添加任务相关的文件路径提示
        if task.file_path:
            parts.append(f"目标文件: {task.file_path}")

        return "\n".join(parts) if parts else ""

    def _extract_code(self, output: str) -> Optional[str]:
        """从 LLM 输出中提取代码块"""
        # 匹配 ```python ... ``` 或 ``` ... ```
        match = re.search(r"```(?:\w+)?\n?(.*?)\n?```", output, re.DOTALL)
        if match:
            return match.group(1).strip()
        # 没有代码块，整个输出当作代码
        if output.strip():
            return output.strip()
        return None
