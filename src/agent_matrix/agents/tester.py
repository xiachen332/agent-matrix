"""Tester Agent 实现"""

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import AsyncIterator, Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm import create_adapter


SYSTEM_PROMPT = """你是一个测试专家，负责为代码编写测试用例。

输入会提供源文件路径和待测试的功能描述。
请为该文件编写完整的 pytest 测试用例。

要求：
1. 使用 pytest 框架
2. 覆盖正常路径和边界情况
3. 测试文件命名：tests/test_<源文件名>
4. 测试要可运行，用 pytest 能直接执行
5. 输出格式：只输出测试代码，用 ```python 代码块 ``` 包裹"""


class TesterAgent(Agent):
    """Tester Agent - 负责测试验证"""

    def __init__(
        self,
        llm_adapter=None,
        api_key: Optional[str] = None,
        output_dir: Optional[str] = ".",
        provider: Optional[str] = None,
    ):
        """初始化 Tester Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
            output_dir: 项目根目录（默认为当前目录）
            provider: 提供商名称
        """
        self._llm = llm_adapter
        if not self._llm:
            self._llm = create_adapter(provider=provider, api_key=api_key)
        self._output_dir = output_dir or "."

    @property
    def role(self) -> str:
        return "tester"

    @property
    def description(self) -> str:
        return "测试、test、验证功能"

    async def execute_stream(self, task: Task) -> AsyncIterator[str]:
        """流式执行测试任务"""
        if self._llm is None or not self._llm.is_configured:
            output = f"[Tester] 已测试(模拟): {task.description}"
            for char in output:
                yield char
            return

        prompt = f"{SYSTEM_PROMPT}\n\n待测试功能：{task.description}"
        async for token in self._llm.complete_stream(prompt, temperature=0.5):
            yield token

    async def execute(self, task: Task) -> AgentResult:
        """执行测试任务"""
        file_path = task.file_path

        if self._llm is None or not self._llm.is_configured:
            return AgentResult(
                success=True,
                output=f"[Tester] 已测试(模拟): {task.description}",
                metadata={"agent": "tester", "mode": "mock"}
            )

        try:
            # 读取源文件内容（如果存在）
            source_code = ""
            if file_path:
                src_file = Path(self._output_dir) / file_path
                if src_file.exists():
                    source_code = src_file.read_text(encoding="utf-8")

            # 生成测试
            prompt = f"""{SYSTEM_PROMPT}

源文件路径：{file_path}
源文件内容：
```python
{source_code}
```

待测试功能：{task.description}"""
            output, _ = await self._llm.complete(prompt, temperature=0.5)

            # 提取测试代码
            test_code = self._extract_code(output)

            # 写入测试文件
            test_file_written = None
            test_result = ""
            if test_code and file_path:
                # 从源文件路径生成测试文件名
                src_name = Path(file_path).stem
                test_file = Path(self._output_dir) / "tests" / f"test_{src_name}.py"
                test_file.parent.mkdir(parents=True, exist_ok=True)
                test_file.write_text(test_code, encoding="utf-8")
                test_file_written = str(test_file)

                # 运行 pytest
                test_result = await self._run_pytest(test_file)

            return AgentResult(
                success=True,
                output=output + "\n\n[测试执行结果]\n" + test_result,
                metadata={
                    "agent": "tester",
                    "mode": "llm",
                    "test_file_written": test_file_written,
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "tester", "mode": "llm"}
            )

    def _extract_code(self, output: str) -> Optional[str]:
        """从 LLM 输出中提取代码块"""
        match = re.search(r"```python\n?(.*?)\n?```", output, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"```\n?(.*?)\n?```", output, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    async def _run_pytest(self, test_file: Path) -> str:
        """运行 pytest"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pytest", str(test_file), "-v",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self._output_dir,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode("utf-8", errors="replace") if stdout else ""
        except Exception as e:
            return f"pytest 运行失败: {e}"
