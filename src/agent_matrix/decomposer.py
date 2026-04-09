"""任务分解器 - 使用 LLM 自动分析任务并拆解成子任务"""

import json
import re
import uuid
from typing import List, Optional, Tuple

from .agents.base import Task
from .llm import create_adapter


# 图片URL提取正则：支持 Markdown ![alt](url) 和纯URL
IMAGE_URL_PATTERN = re.compile(
    r'!\[.*?\]\((https?://[^\s\)]+)\)|(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|svg)(?:\?[^\s<\()"]*)?)',
    re.IGNORECASE
)


def extract_image_urls(text: str) -> Tuple[str, List[str]]:
    """从文本中提取图片URL

    Args:
        text: 原始文本

    Returns:
        (清理后的文本, 图片URL列表)
    """
    urls = []
    cleaned = text

    for match in IMAGE_URL_PATTERN.finditer(text):
        url = match.group(1) or match.group(2)
        if url and url not in urls:
            urls.append(url)
            # 移除 Markdown 图片语法，保留纯URL
            cleaned = cleaned.replace(match.group(0), url)

    return cleaned.strip(), urls


SYSTEM_PROMPT = """你是一个任务分解专家。用户会输入一个开发任务，你需要将其分解为可执行的子任务。

要求：
1. 识别任务涉及的关键步骤（分析、编码、测试、审查等）
2. 确定子任务之间的依赖关系
3. 每个子任务描述要清晰、具体
4. 编码任务必须包含目标文件路径，格式：@[文件路径]@[任务描述]

输出格式（仅输出 JSON，不要有其他内容）：
{
  "subtasks": [
    {
      "id": "task-1",
      "description": "子任务描述（分析类任务不需要文件路径）",
      "dependencies": []
    },
    {
      "id": "task-2", 
      "description": "@[src/xxx.py]@[具体要写的代码描述]",
      "dependencies": ["task-1"]
    }
  ]
}

注意：
- id 只能使用小写字母、数字、连字符
- dependencies 是依赖任务的 id 列表
- 编码任务的 description 格式：@[目标文件路径]@[要实现的功能描述]
- 文件路径用相对路径，从项目根目录开始
- 分析任务应该是第一个，且没有依赖
- 编码任务依赖分析任务
- 测试任务依赖编码任务，description 格式：@[待测文件或模块路径]@[测试验证内容]
- 审查任务依赖编码任务"""


USER_PROMPT = """分解以下任务：

{task}"""


class TaskDecomposer:
    """任务分解器

    使用 LLM 分析任务，自动拆解为可执行的子任务列表。
    """

    def __init__(
        self,
        llm_adapter=None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """初始化分解器

        Args:
            llm_adapter: LLM 适配器实例
            api_key: API Key（从环境变量或显式传入）
            provider: 提供商名称 (minimax/openai/openrouter/claude/deepseek/siliconflow)
        """
        if llm_adapter:
            self._llm = llm_adapter
        else:
            self._llm = create_adapter(provider=provider, api_key=api_key)

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
        # 提取图片URL
        clean_desc, image_urls = extract_image_urls(task_description)

        prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT.format(task=clean_desc)}"

        response, _ = await self._llm.complete(prompt, image_urls=image_urls if image_urls else None)

        # 尝试解析 JSON
        response_clean = response.strip()
        # 去掉可能的 markdown 代码块
        if response_clean.startswith("```"):
            lines = response_clean.split("\n")
            response_clean = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        data = json.loads(response_clean)
        tasks = []
        for item in data.get("subtasks", []):
            desc = item["description"]
            file_path = None

            # 解析 @[file_path]@[description] 格式
            if desc.startswith("@[") and "]@[" in desc:
                parts = desc[2:].split("]@[", 1)
                file_path = parts[0].strip()
                desc = parts[1].strip()

            tasks.append(Task(
                id=item["id"],
                description=desc,
                dependencies=item.get("dependencies", []),
                file_path=file_path,
                image_urls=image_urls,  # 所有子任务继承相同的图片上下文
            ))
        return tasks

    def _mock_decompose(self, task_description: str) -> List[Task]:
        """简单的 fallback 分解（无 LLM 时使用）"""
        # 提取图片URL
        clean_desc, image_urls = extract_image_urls(task_description)

        tasks = []
        task_id_prefix = str(uuid.uuid4())[:8]

        tasks.append(Task(
            id=f"{task_id_prefix}-analysis",
            description=f"分析任务需求：{clean_desc}",
            dependencies=[],
            image_urls=image_urls,
        ))

        if any(k in clean_desc.lower() for k in ["实现", "开发", "写", "code", "实现", "创建"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-coding",
                description=f"编写代码：{clean_desc}",
                dependencies=[f"{task_id_prefix}-analysis"],
                image_urls=image_urls,
            ))

        if any(k in clean_desc.lower() for k in ["测试", "test", "验证"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-testing",
                description=f"测试验证：{clean_desc}",
                dependencies=[f"{task_id_prefix}-coding"],
                image_urls=image_urls,
            ))

        if any(k in clean_desc.lower() for k in ["审查", "review", "检查"]):
            tasks.append(Task(
                id=f"{task_id_prefix}-review",
                description=f"代码审查：{clean_desc}",
                dependencies=[f"{task_id_prefix}-coding"],
                image_urls=image_urls,
            ))

        if len(tasks) == 1:
            tasks.append(Task(
                id=f"{task_id_prefix}-execute",
                description=f"执行任务：{clean_desc}",
                dependencies=[f"{task_id_prefix}-analysis"],
                image_urls=image_urls,
            ))

        return tasks
