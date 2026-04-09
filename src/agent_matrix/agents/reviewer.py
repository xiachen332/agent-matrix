"""Reviewer Agent 实现"""

import subprocess
from pathlib import Path
from typing import AsyncIterator, List, Optional

from agent_matrix.agents.base import Agent, AgentResult, Task
from agent_matrix.llm import create_adapter
from agent_matrix.security import SecurityScanner, Vulnerability


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
        llm_adapter=None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """初始化 Reviewer Agent

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
            provider: 提供商名称
        """
        self._llm = llm_adapter
        if not self._llm:
            self._llm = create_adapter(provider=provider, api_key=api_key)

    @property
    def role(self) -> str:
        return "reviewer"

    @property
    def description(self) -> str:
        return "代码审查、review、检查代码质量"

    async def execute_stream(self, task: Task) -> AsyncIterator[str]:
        """流式执行审查任务"""
        if self._llm is None or not self._llm.is_configured:
            output = f"[Reviewer] 已审查(模拟): {task.description}"
            for char in output:
                yield char
            return

        prompt = f"{SYSTEM_PROMPT}\n\n待审查代码/任务：{task.description}"
        async for token in self._llm.complete_stream(prompt, temperature=0.5):
            yield token

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
            output, _ = await self._llm.complete(prompt, temperature=0.5)
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

    async def review_file(self, file_path: str | Path) -> AgentResult:
        """审查单个文件

        Args:
            file_path: 文件路径

        Returns:
            审查结果
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return AgentResult(
                success=False,
                output="",
                error=f"文件不存在: {file_path}",
            )

        try:
            # 读取文件内容
            content = file_path.read_text(encoding="utf-8")

            # 使用 LLM 审查
            if self._llm is None or not self._llm.is_configured:
                return AgentResult(
                    success=True,
                    output=f"[Reviewer] 文件审查(模拟): {file_path.name}\n\n文件大小: {len(content)} 字节",
                    metadata={"agent": "reviewer", "mode": "mock", "file": str(file_path)}
                )

            prompt = f"""{SYSTEM_PROMPT}

请审查以下文件：{file_path.name}

文件内容：
```{file_path.suffix[1:] or 'text'}
{content}
```"""

            output, _ = await self._llm.complete(prompt, temperature=0.3)
            return AgentResult(
                success=True,
                output=output,
                metadata={"agent": "reviewer", "mode": "llm", "file": str(file_path)}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "reviewer", "file": str(file_path)}
            )

    async def review_pr(self, pr_url: str) -> AgentResult:
        """审查 GitHub PR

        Args:
            pr_url: GitHub PR URL，例如 https://github.com/owner/repo/pull/123

        Returns:
            审查结果
        """
        # 解析 PR URL
        # 支持格式: https://github.com/owner/repo/pull/123
        #           git@github.com:owner/repo/pull/123
        try:
            # 提取 owner/repo/pr_number
            parts = pr_url.replace("https://github.com/", "").replace("git@github.com:", "").replace(":", "/").split("/")
            if len(parts) < 4 or "pull" not in parts:
                return AgentResult(
                    success=False,
                    output="",
                    error="无效的 PR URL 格式",
                )

            owner, repo = parts[0], parts[1]
            pr_number = parts[3].split("?")[0]  # 去掉可能的查询参数

            # 使用 gh cli 获取 PR 信息
            try:
                # 获取 PR 详情
                result = subprocess.run(
                    ["gh", "pr", "view", pr_number, "--repo", f"{owner}/{repo}", "--json", "title,body,files,additions,deletions"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return AgentResult(
                        success=False,
                        output="",
                        error=f"gh cli 错误: {result.stderr}",
                    )

                import json
                pr_data = json.loads(result.stdout)

                # 获取 PR 文件列表
                files_result = subprocess.run(
                    ["gh", "pr", "view", pr_number, "--repo", f"{owner}/{repo}", "--json", "files"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                files_data = json.loads(files_result.stdout) if files_result.returncode == 0 else {"files": []}

                # 使用 LLM 审查 PR
                if self._llm is None or not self._llm.is_configured:
                    return AgentResult(
                        success=True,
                        output=f"[Reviewer] PR #{pr_number} 审查(模拟)\n\n标题: {pr_data.get('title', 'N/A')}",
                        metadata={"agent": "reviewer", "mode": "mock", "pr": pr_url}
                    )

                prompt = f"""{SYSTEM_PROMPT}

请审查以下 GitHub Pull Request：

标题：{pr_data.get('title', 'N/A')}
描述：{pr_data.get('body', 'N/A') or '无描述'}
变更文件数：{len(files_data.get('files', []))}
代码行变化：+{pr_data.get('additions', 0)} -{pr_data.get('deletions', 0)}

变更的文件：
{chr(10).join([f.get('path', 'unknown') for f in files_data.get('files', [])])}

请提供：
1. PR 整体评价
2. 主要变更点分析
3. 发现的问题（如有）
4. 改进建议
"""

                output, _ = await self._llm.complete(prompt, temperature=0.3)
                return AgentResult(
                    success=True,
                    output=output,
                    metadata={
                        "agent": "reviewer",
                        "mode": "llm",
                        "pr": pr_url,
                        "pr_title": pr_data.get("title", "N/A"),
                        "files_count": len(files_data.get("files", [])),
                    }
                )

            except FileNotFoundError:
                return AgentResult(
                    success=False,
                    output="",
                    error="gh cli 未安装，请先安装 GitHub CLI: https://cli.github.com/",
                )

        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
            )

    async def security_scan(self, target: str | Path) -> AgentResult:
        """安全扫描

        Args:
            target: 文件或目录路径

        Returns:
            扫描结果
        """
        scanner = SecurityScanner(project_root=Path.cwd())
        target_path = Path(target)

        try:
            if target_path.is_file():
                vulnerabilities = scanner.scan_file(target_path)
            else:
                vulnerabilities = scanner.scan_directory(target_path)

            if not vulnerabilities:
                return AgentResult(
                    success=True,
                    output=f"✓ 安全扫描完成: {target} 未发现问题",
                    metadata={"agent": "reviewer", "scan_target": str(target), "vulnerabilities": 0}
                )

            # 按严重等级分组
            by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
            for v in vulnerabilities:
                by_severity[v.severity.value].append(v)

            # 构建输出
            lines = [f"安全扫描完成: {target}"]
            lines.append(f"发现 {len(vulnerabilities)} 个问题:\n")

            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                vulns = by_severity[severity]
                if vulns:
                    lines.append(f"\n## {severity} ({len(vulns)} 个)")

                    for v in vulns:
                        lines.append(f"\n### {v.location}")
                        lines.append(f"**问题**: {v.description}")
                        lines.append(f"**修复**: {v.fix}")
                        if v.test_id:
                            lines.append(f"**测试 ID**: {v.test_id}")

            output = "\n".join(lines)
            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "agent": "reviewer",
                    "scan_target": str(target),
                    "vulnerabilities": len(vulnerabilities),
                    "by_severity": {k: len(v) for k, v in by_severity.items()},
                }
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e),
                metadata={"agent": "reviewer", "scan_target": str(target)}
            )
