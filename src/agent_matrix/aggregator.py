"""结果汇总器 - 汇总各 Agent 输出，生成最终报告"""

from dataclasses import dataclass, field
from typing import List

from .agents.base import AgentResult, Task, TaskStatus


@dataclass
class ExecutionReport:
    """执行报告"""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    task_details: List[dict] = field(default_factory=list)
    summary: str = ""


class ResultAggregator:
    """结果汇总器

    收集所有 Agent 的执行结果，生成结构化报告。
    """

    def aggregate(self, tasks: List[Task]) -> ExecutionReport:
        """汇总任务执行结果

        Args:
            tasks: 任务列表（包含执行结果）

        Returns:
            执行报告
        """
        successful = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)

        details = []
        for task in tasks:
            detail = {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "agent": task.assigned_agent,
                "output": task.result.output if task.result else "",
                "error": task.result.error if task.result else None,
            }
            details.append(detail)

        summary = self._generate_summary(tasks, successful, failed, pending)

        return ExecutionReport(
            total_tasks=len(tasks),
            successful_tasks=successful,
            failed_tasks=failed,
            task_details=details,
            summary=summary
        )

    def _generate_summary(
        self,
        tasks: List[Task],
        successful: int,
        failed: int,
        pending: int
    ) -> str:
        """生成文本摘要"""
        lines = [
            "=" * 50,
            "执行报告摘要",
            "=" * 50,
            f"总任务数: {len(tasks)}",
            f"成功: {successful}",
            f"失败: {failed}",
            f"待执行: {pending}",
            "-" * 50,
        ]

        if failed > 0:
            lines.append("失败任务:")
            for task in tasks:
                if task.status == TaskStatus.FAILED:
                    lines.append(f"  - [{task.id}] {task.description}")
                    if task.result and task.result.error:
                        lines.append(f"    错误: {task.result.error}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_markdown(self, report: ExecutionReport) -> str:
        """格式化为 Markdown 报告"""
        lines = [
            "# 执行报告",
            "",
            f"**总任务数**: {report.total_tasks}  |  "
            f"**成功**: {report.successful_tasks}  |  "
            f"**失败**: {report.failed_tasks}",
            "",
            "## 任务详情",
            "",
            "| ID | 描述 | 状态 | Agent |",
            "|---|---|---|---|",
        ]

        for detail in report.task_details:
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
                "pending": "⏳",
            }.get(detail["status"], "❓")

            desc = detail["description"][:50] + "..." if len(detail["description"]) > 50 else detail["description"]
            lines.append(
                f"| {detail['id']} | {desc} | {status_icon} {detail['status']} | "
                f"{detail['agent'] or 'N/A'} |"
            )

        return "\n".join(lines)
