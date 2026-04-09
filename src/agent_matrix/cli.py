"""CLI 入口 - 命令行交互界面"""
# -*- coding: utf-8 -*-
import asyncio
import sys
import io
from pathlib import Path

# Windows 控制台 UTF-8 模式
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from typing import Optional

from .session import SessionManager, SessionConfig
from .llm import create_adapter
from .knowledge import ProjectIndexer
from .job_manager import get_job_manager, JobStatus


def create_master_for_session(session: "Session"):
    """根据会话配置创建 MasterAgent"""
    from .master import MasterAgent
    from .pool import AgentPool
    from .agents.coder import CoderAgent
    from .agents.reviewer import ReviewerAgent
    from .agents.tester import TesterAgent

    pool = AgentPool()
    llm = create_adapter(
        provider=session.config.provider,
        api_key=session.config.api_key,
        model=session.config.model,
    )
    pool.register(CoderAgent(llm_adapter=llm, output_dir=session.config.output_dir))
    pool.register(ReviewerAgent(llm_adapter=llm))
    pool.register(TesterAgent(llm_adapter=llm, output_dir=session.config.output_dir))
    return MasterAgent(pool=pool)


async def run_interactive(
    initial_api_key: Optional[str] = None,
    initial_output_dir: Optional[str] = None,
    initial_provider: Optional[str] = None,
    storage_dir: Optional[str] = None,
):
    """交互模式"""
    # 初始化会话管理器
    sm = SessionManager() if not storage_dir else SessionManager(storage_dir=Path(storage_dir).expanduser())

    # 加载已有会话
    sm.load_sessions()

    # 确保至少有一个会话
    if not sm.list_sessions():
        session = sm.create_session(name="default")
        sm.set_current(session.id)
    else:
        session = sm.get_current()
        if session is None:
            session = sm.list_sessions()[0]
            sm.set_current(session.id)

    def refresh_master():
        """根据当前会话配置刷新 Master"""
        session._master = create_master_for_session(session)
        return session._master

    master = refresh_master()

    def show_help():
        print("""
╔══════════════════════════════════════════════════╗
║           Agent Matrix - 可用指令               ║
╠══════════════════════════════════════════════════╣
║  [会话]                                         ║
║    /session              列出所有会话           ║
║    /session new [name]   新建会话               ║
║    /session <id>         切换到某会话           ║
║    /session delete <id>  删除会话               ║
║    /context              查看会话元数据         ║
║    /context clear        清空会话元数据         ║
║                                               ║
║  [项目]                                         ║
║    /project <dir>        关联项目目录           ║
║    /project show         显示项目上下文         ║
║    /project clear        清除项目关联           ║
║                                               ║
║  [配置]                                         ║
║    /provider <name>   切换提供商               ║
║    /key <api_key>     设置 API Key             ║
║    /model <model>     设置模型（可选）         ║
║    /output <dir>      设置代码输出目录          ║
║                                               ║
║  [操作]                                         ║
║    /config            显示当前配置             ║
║    /restart           重新初始化 Master        ║
║    /providers         列出支持的提供商          ║
║    /review <file>     审查本地文件             ║
║    /review-pr <url>   审查 GitHub PR           ║
║    /security <path>    安全扫描                ║
║    /run <task>        后台运行任务             ║
║    /jobs              列出后台任务             ║
║    /log <job_id>      查看任务日志             ║
║    /help              显示本帮助               ║
║    /quit              退出（自动保存）         ║
╚══════════════════════════════════════════════════╝
""")

    def show_config():
        cur = session
        key_display = '*' * 20 + cur.config.api_key[-8:] if cur.config.api_key else '(未设置，从环境变量读取)'
        print(f"""
╔══════════════════════════════════════════════════╗
║           当前会话配置                           ║
╠══════════════════════════════════════════════════╣
║  Session : {cur.name} ({cur.id[:8]}){' ' * 19}║
║  Provider : {cur.config.provider:<30}║
║  API Key  : {key_display:<31}║
║  Model    : {(cur.config.model or '(默认)'):<30}║
║  Output   : {cur.config.output_dir:<30}║
║  Reports  : {len(cur.reports)} 个{' ' * 25}║
╚══════════════════════════════════════════════════╝
""")

    def show_providers():
        print("""
╔══════════════════════════════════════════════════╗
║           支持的提供商                           ║
╠══════════════════════════════════════════════════╣
║  minimax     - MiniMax-M2（默认）               ║
║  openai      - GPT-4o-mini                       ║
║  openrouter  - Claude/GPT/Llama 等（支持中转）  ║
║  deepseek    - DeepSeek Chat                    ║
║  siliconflow - Qwen/DeepSeek 等（国内可用）     ║
║  claude      - Anthropic Claude（官方）          ║
╚══════════════════════════════════════════════════╝
""")

    def show_sessions():
        sessions = sm.list_sessions()
        current_id = sm.get_current().id if sm.get_current() else None
        if not sessions:
            print("暂无会话")
            return
        print("╔══════════════════════════════════════════════════╗")
        print("║           会话列表                               ║")
        print("╠══════════════════════════════════════════════════╣")
        for s in sessions:
            marker = " ◄" if s.id == current_id else ""
            print(f"║  {s.name} ({s.id[:8]}){marker}")
            print(f"║      创建: {s.created_at.strftime('%Y-%m-%d %H:%M')} | 任务: {len(s.reports)} 个 | Provider: {s.config.provider}")
        print("╚══════════════════════════════════════════════════╝")

    def select_session_interactive() -> Optional[str]:
        """交互式会话选择（数字键选择）"""
        sessions = sm.list_sessions()
        if not sessions:
            print("暂无会话，请先用 /session new 创建")
            return None

        sessions_sorted = sorted(sessions, key=lambda s: s.last_active, reverse=True)
        current_id = sm.get_current().id if sm.get_current() else None

        print("\n╔══════════════════════════════════════════════════╗")
        print("║           会话选择（输入编号回车）               ║")
        print("╠══════════════════════════════════════════════════╣")
        for i, s in enumerate(sessions_sorted):
            marker = " ◄" if s.id == current_id else ""
            print(f"║  [{i+1}] {s.name} ({s.id[:8]}){marker}")
            print(f"║      创建:{s.created_at.strftime('%m-%d %H:%M')}  任务:{len(s.reports)}个  Provider:{s.config.provider}")
        print("╚══════════════════════════════════════════════════╝")

        try:
            choice = input("选择会话 (1-{}) 或按 Enter 取消: ".format(len(sessions_sorted))).strip()
            if not choice:
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(sessions_sorted):
                return sessions_sorted[idx].id
            else:
                print("无效选择")
                return None
        except (KeyboardInterrupt, ValueError):
            print("\n已取消")
            return None

    def handle_command(cmd: str) -> bool:
        """处理配置指令，返回是否退出"""
        nonlocal session, master
        parts = cmd.split(maxsplit=2)
        action = parts[0].lower() if parts else ""

        # 会话管理指令
        if action == "/session" or action == "/s":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "":
                # 交互式选择会话
                selected_id = select_session_interactive()
                if selected_id:
                    s = sm.get_session(selected_id)
                    if s:
                        sm.set_current(s.id)
                        session = s
                        master = refresh_master()
                        print(f"✓ 已切换到: {s.name} ({s.id[:8]})")
            elif sub == "new":
                name = parts[2] if len(parts) > 2 else None
                new_session = sm.create_session(name=name)
                sm.set_current(new_session.id)
                session = new_session
                master = refresh_master()
                print(f"✓ 已创建并切换到新会话: {new_session.name} ({new_session.id[:8]})")
            elif sub == "delete" or sub == "del":
                if len(parts) < 3:
                    print("用法: /session delete <id>")
                else:
                    target_id = parts[2]
                    if target_id == session.id:
                        print("不能删除当前会话，先 /session <another_id> 切换")
                    elif sm.delete_session(target_id):
                        print(f"✓ 已删除会话: {target_id[:8]}")
                    else:
                        print(f"✗ 会话不存在: {target_id[:8]}")
            elif sub == "switch":
                if len(parts) < 3:
                    print("用法: /session switch <id>")
                else:
                    target_id = parts[2]
                    s = sm.get_session(target_id)
                    if s:
                        sm.set_current(s.id)
                        session = s
                        master = refresh_master()
                        print(f"✓ 已切换到: {s.name} ({s.id[:8]})")
                    else:
                        print(f"✗ 会话不存在: {target_id[:8]}")
            else:
                # 尝试作为 session id
                s = sm.get_session(sub)
                if s:
                    sm.set_current(s.id)
                    session = s
                    master = refresh_master()
                    print(f"✓ 已切换到: {s.name} ({s.id[:8]})")
                else:
                    print(f"用法: /session [new [name] | <id> | delete <id> | switch <id>]")
            return True

        elif action == "/context" or action == "/ctx":
            if session.metadata:
                print("╔══════════════════════════════════════════════════╗")
                print("║           会话元数据                             ║")
                print("╠══════════════════════════════════════════════════╣")
                for k, v in session.metadata.items():
                    print(f"║  {k}: {v}")
                print("╚══════════════════════════════════════════════════╝")
            else:
                print("会话元数据为空（使用 /context clear 可清空）")
            return True

        elif action == "/context" and len(parts) > 1 and parts[1].lower() == "clear":
            session.metadata.clear()
            print("✓ 会话元数据已清空")
            return True

        # 项目上下文指令
        elif action == "/project" or action == "/proj":
            if len(parts) < 2:
                print("用法: /project <dir> | show | clear")
                return True

            sub = parts[1].lower()
            if sub == "show":
                # 显示项目上下文
                ctx = session.get_project_context()
                if ctx:
                    indexer = ProjectIndexer()
                    indexer.set_root(ctx.root)
                    print("╔══════════════════════════════════════════════════╗")
                    print("║           项目上下文                             ║")
                    print("╠══════════════════════════════════════════════════╣")
                    print(f"║  项目根目录: {ctx.root}")
                    print(f"║  关键模块: {', '.join(ctx.key_modules) if ctx.key_modules else '(无)'}")
                    print("╠══════════════════════════════════════════════════╣")
                    print("║  文件结构:                                       ║")
                    for line in indexer.get_file_tree_display().split("\n"):
                        print(f"║    {line}")
                    print("╚══════════════════════════════════════════════════╝")
                else:
                    print("未关联项目目录（使用 /project <dir> 关联）")
                return True
            elif sub == "clear":
                session.project_context = None
                # 清除所有 Agent 的项目上下文
                for agent_name in master.pool.list_agents():
                    agent = master.pool.get(agent_name)
                    if agent:
                        agent.set_project_context(None)
                print("✓ 已清除项目关联")
                return True
            else:
                # 设置项目目录
                proj_dir = parts[1] if len(parts) > 1 else ""
                if not proj_dir:
                    print("用法: /project <dir>")
                    return True
                try:
                    ctx = session.set_project_root(proj_dir)
                    indexer = ProjectIndexer()
                    indexer.set_root(proj_dir)
                    print(f"✓ 已关联项目: {ctx.root}")
                    print(f"  关键模块: {', '.join(ctx.key_modules) if ctx.key_modules else '(无)'}")

                    # 将项目上下文注入到所有 Agent
                    for agent_name in master.pool.list_agents():
                        agent = master.pool.get(agent_name)
                        if agent:
                            agent.set_project_context(ctx)
                except ValueError as e:
                    print(f"✗ {e}")
                return True

        # 配置指令
        elif action == "/quit" or action == "/exit":
            # 保存所有会话
            for s in sm.list_sessions():
                sm.save_session(s)
            print("再见! 会话已自动保存。")
            return False
        elif action == "/help" or action == "/h":
            show_help()
        elif action == "/config" or action == "/cfg":
            show_config()
        elif action == "/providers" or action == "/list":
            show_providers()
        elif action == "/restart" or action == "/reload":
            master = refresh_master()
            print(f"✓ Master 已重新初始化 (provider={session.config.provider})")
        elif action == "/provider" or action == "/p":
            if len(parts) < 2:
                print("用法: /provider <name>")
            else:
                session.config.provider = parts[1].lower()
                session.config.model = None  # 重置模型
                master = refresh_master()
                print(f"✓ Provider 已切换为: {session.config.provider}")
        elif action == "/key" or action == "/k":
            if len(parts) < 2:
                print("用法: /key <api_key>")
            else:
                session.config.api_key = parts[1]
                master = refresh_master()
                print(f"✓ API Key 已更新")
        elif action == "/model" or action == "/m":
            if len(parts) < 2:
                session.config.model = None
                print("✓ 模型已重置为默认")
            else:
                session.config.model = parts[1]
                master = refresh_master()
                print(f"✓ 模型已设置为: {session.config.model}")
        elif action == "/output" or action == "/o":
            if len(parts) < 2:
                print("用法: /output <directory>")
            else:
                session.config.output_dir = parts[1]
                master = refresh_master()
                print(f"✓ 输出目录已设置为: {session.config.output_dir}")

        # === 审查和安全扫描指令 ===
        elif action == "/review":
            # 审查本地文件
            if len(parts) < 2:
                print("用法: /review <file>")
            else:
                file_path = parts[1]
                reviewer = master.pool.get("reviewer")
                if not reviewer:
                    print("✗ Reviewer Agent 未注册")
                else:
                    import asyncio
                    result = asyncio.run(reviewer.review_file(file_path))
                    if result.success:
                        print(f"\n{'='*50}")
                        print(f"审查结果: {file_path}")
                        print(f"{'='*50}")
                        print(result.output)
                    else:
                        print(f"✗ 审查失败: {result.error}")

        elif action == "/review-pr":
            # 审查 GitHub PR
            if len(parts) < 2:
                print("用法: /review-pr <url>")
            else:
                pr_url = parts[1]
                reviewer = master.pool.get("reviewer")
                if not reviewer:
                    print("✗ Reviewer Agent 未注册")
                else:
                    import asyncio
                    result = asyncio.run(reviewer.review_pr(pr_url))
                    if result.success:
                        print(f"\n{'='*50}")
                        print(f"PR 审查结果")
                        print(f"{'='*50}")
                        print(result.output)
                    else:
                        print(f"✗ 审查失败: {result.error}")

        elif action == "/security" or action == "/scan":
            # 安全扫描
            if len(parts) < 2:
                print("用法: /security <file_or_dir>")
            else:
                target = parts[1]
                reviewer = master.pool.get("reviewer")
                if not reviewer:
                    print("✗ Reviewer Agent 未注册")
                else:
                    import asyncio
                    result = asyncio.run(reviewer.security_scan(target))
                    if result.success:
                        print(f"\n{'='*50}")
                        print(f"安全扫描结果: {target}")
                        print(f"{'='*50}")
                        print(result.output)
                    else:
                        print(f"✗ 扫描失败: {result.error}")

        # === 后台任务指令 ===
        elif action == "/run":
            # 后台运行任务
            if len(parts) < 2:
                print("用法: /run <task_description>")
            else:
                task_desc = " ".join(parts[1:])
                jm = get_job_manager()

                # 创建后台任务
                async def run_task():
                    return await master.execute_task(task_desc, session_config=session.config)

                job_id = jm.submit_async_task(run_task(), name=task_desc[:50])
                print(f"✓ 任务已提交: {job_id}")
                print(f"  使用 /jobs 查看任务列表")
                print(f"  使用 /log {job_id} 查看日志")

        elif action == "/jobs":
            # 列出后台任务
            jm = get_job_manager()
            jobs = jm.list_jobs()

            if not jobs:
                print("暂无后台任务")
            else:
                print("╔══════════════════════════════════════════════════╗")
                print("║           后台任务列表                           ║")
                print("╠══════════════════════════════════════════════════╣")
                print("║ ID       名称                           状态      ║")
                print("╠══════════════════════════════════════════════════╣")
                for job in jobs:
                    status_icon = {
                        JobStatus.PENDING: "⏳",
                        JobStatus.RUNNING: "🔄",
                        JobStatus.COMPLETED: "✅",
                        JobStatus.FAILED: "❌",
                        JobStatus.CANCELLED: "🚫",
                    }.get(job.status, "?")
                    name = job.name[:28] if len(job.name) > 28 else job.name
                    print(f"║ {job.id}  {name:<30} {status_icon} {job.status.value:<8}║")
                print("╚══════════════════════════════════════════════════╝")
                print(f"共 {len(jobs)} 个任务")

        elif action == "/log":
            # 查看任务日志
            if len(parts) < 2:
                print("用法: /log <job_id>")
            else:
                job_id = parts[1]
                jm = get_job_manager()
                log = jm.get_job_log(job_id)
                if log:
                    print(f"\n{'='*50}")
                    print(f"任务日志: {job_id}")
                    print(f"{'='*50}")
                    print(log)
                else:
                    print(f"✗ 任务不存在: {job_id}")

        elif action == "/cancel":
            # 取消任务
            if len(parts) < 2:
                print("用法: /cancel <job_id>")
            else:
                job_id = parts[1]
                jm = get_job_manager()
                if jm.cancel_job(job_id):
                    print(f"✓ 任务已取消: {job_id}")
                else:
                    print(f"✗ 无法取消任务: {job_id}")

        else:
            print(f"未知指令: {cmd}，输入 /help 查看可用指令")
        return True

    # 启动
    print("=" * 50)
    print("Agent Matrix - 多Agent协作开发框架")
    print("=" * 50)
    print("输入 /help 查看可用指令")
    print()
    show_sessions()
    print()
    show_config()
    print(f"已注册 Agent: {', '.join(master.pool.list_agents())}")
    print()

    while True:
        try:
            task_input = input(">>> ").strip()

            if not task_input:
                continue

            # 处理配置指令
            if task_input.startswith("/"):
                if not handle_command(task_input):
                    break
                continue

            print("\n正在分解任务...")
            report = await master.execute_task(task_input, session_config=session.config)

            # 追加到会话历史
            session.reports.append(report)
            session.last_active = datetime.now()

            print("\n" + report.summary)

        except KeyboardInterrupt:
            print("\n\n已取消")
            break
        except Exception as e:
            print(f"\n错误: {e}")


async def run_single(
    task_description: str,
    markdown: bool = False,
    output_dir: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
):
    """单任务模式"""
    from .master import MasterAgent
    from .pool import AgentPool
    from .agents.coder import CoderAgent
    from .agents.reviewer import ReviewerAgent
    from .agents.tester import TesterAgent

    pool = AgentPool()
    llm = create_adapter(provider=provider, api_key=api_key)
    pool.register(CoderAgent(llm_adapter=llm, output_dir=output_dir))
    pool.register(ReviewerAgent(llm_adapter=llm))
    pool.register(TesterAgent(llm_adapter=llm, output_dir=output_dir))
    master = MasterAgent(pool=pool)

    # 单任务模式不使用 Webhook（无会话配置）
    report = await master.execute_task(task_description, session_config=None)

    if markdown:
        print(master._aggregator.format_markdown(report))
    else:
        print(report.summary)

    # 返回退出码
    if report.failed_tasks == report.total_tasks:
        sys.exit(2)
    elif report.failed_tasks > 0:
        sys.exit(1)
    sys.exit(0)


def main():
    """CLI 主入口"""
    import argparse
    from datetime import datetime

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
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="代码输出目录（默认为当前目录）"
    )
    parser.add_argument(
        "--provider", "-p",
        default=None,
        help="LLM 提供商: minimax/openai/openrouter/claude/deepseek/siliconflow（默认 minimax）"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help="API Key（默认从环境变量读取）"
    )
    parser.add_argument(
        "--model", "-M",
        default=None,
        help="模型名称（覆盖默认模型）"
    )
    parser.add_argument(
        "--storage-dir", "-s",
        default=None,
        help="会话存储目录（默认 ~/.agent-matrix/sessions）"
    )

    args = parser.parse_args()

    if args.task:
        asyncio.run(run_single(
            args.task,
            args.markdown,
            args.output_dir,
            args.api_key,
            args.provider,
        ))
    else:
        asyncio.run(run_interactive(
            initial_api_key=args.api_key,
            initial_output_dir=args.output_dir,
            initial_provider=args.provider,
            storage_dir=args.storage_dir,
        ))


if __name__ == "__main__":
    main()
