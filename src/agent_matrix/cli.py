"""CLI 入口 - 命令行交互界面"""
# -*- coding: utf-8 -*-
import asyncio
import sys
import io

# Windows 控制台 UTF-8 模式
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from typing import Optional

from .master import MasterAgent
from .pool import AgentPool
from .agents.coder import CoderAgent
from .agents.reviewer import ReviewerAgent
from .agents.tester import TesterAgent
from .llm.minimax import MiniMaxAdapter


def create_master(api_key: Optional[str] = None) -> MasterAgent:
    """创建配置好的 Master Agent 实例

    Args:
        api_key: MiniMax API Key（默认从环境变量读取）
    """
    pool = AgentPool()

    # 创建共享的 LLM adapter
    llm = MiniMaxAdapter(api_key=api_key)

    # 注册默认 Agent（共享同一个 LLM adapter）
    pool.register(CoderAgent(llm_adapter=llm))
    pool.register(ReviewerAgent(llm_adapter=llm))
    pool.register(TesterAgent(llm_adapter=llm))

    return MasterAgent(pool=pool)


async def run_interactive():
    """交互模式"""
    print("=" * 50)
    print("Agent Matrix - 多Agent协作开发框架")
    print("=" * 50)
    print("输入任务描述，系统自动分解并执行")
    print("输入 'quit' 或 'exit' 退出")
    print()

    master = create_master()

    print(f"已注册 Agent: {', '.join(master.pool.list_agents())}")
    print()

    while True:
        try:
            task_input = input(">>> ").strip()

            if task_input.lower() in ("quit", "exit", "q"):
                print("再见!")
                break

            if not task_input:
                continue

            print("\n正在分解任务...")
            report = await master.execute_task(task_input)

            print("\n" + report.summary)

        except KeyboardInterrupt:
            print("\n\n已取消")
            break
        except Exception as e:
            print(f"\n错误: {e}")


async def run_single(task_description: str, markdown: bool = False):
    """单任务模式"""
    master = create_master()

    report = await master.execute_task(task_description)

    if markdown:
        print(master._aggregator.format_markdown(report))
    else:
        print(report.summary)

    # 返回退出码：0 成功，1 部分失败，2 完全失败
    if report.failed_tasks == report.total_tasks:
        sys.exit(2)
    elif report.failed_tasks > 0:
        sys.exit(1)
    sys.exit(0)


def main():
    """CLI 主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Agent Matrix - 多Agent协作开发框架"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="任务描述（省略则进入交互模式）"
    )
    parser.add_argument(
        "--markdown", "-m",
        action="store_true",
        help="输出 Markdown 格式报告"
    )

    args = parser.parse_args()

    if args.task:
        asyncio.run(run_single(args.task, args.markdown))
    else:
        asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
