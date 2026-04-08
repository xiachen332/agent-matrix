"""任务分解器 - 使用 LLM 自动分析任务并拆解成子任务"""

import json
import uuid
from typing import List, Optional

from .agents.base import Task
from .llm.minimax import MiniMaxAdapter


SYSTEM_PROMPT = """你是一个任务分解专家。用户会输入一个开发任务，你需要将其分解为可执行的子任务。

要求：
1. 识别任务涉及的关键步骤（分析、编码、测试、审查等）
2. 确定子任务之间的依赖关系
3. 每个子任务描述要清晰、具体

输出格式（仅输出 JSON，不要有其他内容）：
{
  "subtasks": [
    {
      "id": "task-1",
      "description": "子任务描述",
      "dependencies": []
    },
    {
      "id": "task-2", 
      "description": "子任务描述",
      "dependencies": ["task-1"]
    }
  ]
}

注意：
- id 只能使用小写字母、数字、连字符
- dependencies 是依赖任务的 id 列表
- 分析任务应该是第一个，且没有依赖
- 编码任务依赖分析任务
- 测试任务依赖编码任务
- 审查任务依赖编码任务"""


USER_PROMPT = """分解以下任务：

{task}"""


class TaskDecomposer:
    """任务分解器

    使用 LLM 分析任务，自动拆解为可执行的子任务列表。
    """

    def __init__(
        self,
        llm_adapter: Optional[MiniMaxAdapter] = None,
        api_key: Optional[str] = None,
    ):
        """初始化分解器

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
        """
        if llm_adapter:
            self._llm = llm_adapter
        elif api_key or True:  # 优先使用传入的或环境变量的
            self._llm = MiniMaxAdapter(api_key=api_key)
        else:
            self._llm = None

    async def decompose(self, task_description: str) -> List[Task]:
        """分解任务

        Args:
            task_description: 原始任务描述

        Returns:
            分解后的子任务列表
        """
        if self._llm is None or not self._llm.is_configured:
            return self._mock_decompose(task_description)

        try:
            return await self._llm_decompose(task_description)
        except Exception as e:
            # LLM 调用失败时 fallback 到简单分解
            print(f"[Decomposer] LLM failed: {e}, using fallback")
            return self._mock_decompose(task_description)

    async def _llm_decompose(self, task_description: str) -> List[Task]:
        """使用 LLM 分解任务"""
        prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT.format(task=task_description)}"

        response = await self._llm.complete(prompt)

        # 尝试解析 JSON
        response_clean = response.strip()
        # 去掉可能的 markdown 代码块
        if response_clean.startswith("```"):
            lines = response_clean.split("\n")
            response_clean = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        data = json.loads(response_clean)
        tasks = []
        for item in data.get("subtasks", []):
            tasks.append(Task(
                id=item["id"],
                description=item["description"],
                dependencies=item.get("dependencies", []),
            ))
        return tasks

    def _mock_decompose(self, task_description: str) -> List[Task]:
        """简单的 fallback 分解（无 LLM 时使用）"""
        tasks = []
        task_id_prefix = str(uuid.uuid4())[:8]

        tasks.append(Task(
            id=f"{task_id_prefix}-analysis",
            description=f"分析任务需求：{task_description}",
            dependencies=[],
        ))

        if any(k in task_description.lower() for k in ["实现", "开发", "写", "code", "实现", "创建"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-coding",
                description=f"编写代码：{task_description}",
                dependencies=[f"{task_id_prefix}-analysis"],
            ))

        if any(k in task_description.lower() for k in ["测试", "test", "验证"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-testing",
                description=f"测试验证：{task_description}",
                dependencies=[f"{task_id_prefix}-coding"],
            ))

        if any(k in task_description.lower() for k in ["审查", "review", "检查"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-review",
                description=f"代码审查：{task_description}",
                dependencies=[f"{task_id_prefix}-coding"],
            ))

        if len(tasks) == 1:
            tasks.append(Task(
                id=f"{task_id_prefix}-execute",
                description=f"执行任务：{task_description}",
                dependencies=[f"{task_id_prefix}-analysis"],
            ))

        return tasks
