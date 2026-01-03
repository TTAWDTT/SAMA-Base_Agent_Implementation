# -*- coding: utf-8 -*-
# ==============================================================================
# CLI 入口
# ==============================================================================

from __future__ import annotations

import argparse
import io
import sys
from typing import Optional

from src import BaseAgent, get_config, init_logging, get_logger
from src.cli.session import interactive_mode, single_query, queue_mode
from src.dashboard import run_dashboard
from src.webui import run_chat_ui


def _configure_windows_encoding() -> None:
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def create_agent(profile: Optional[str] = None) -> BaseAgent:
    """
    创建 Agent 实例
    """
    return BaseAgent(profile=profile)


def run_cli() -> None:
    """
    CLI 入口
    """
    _configure_windows_encoding()

    parser = argparse.ArgumentParser(
        description="AI Agent - 一个基于LLM的智能助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py                    # 交互模式
  python main.py -q "计算 2+2"      # 单次查询
  python main.py --verbose          # 详细输出模式

更多信息请参阅 README.md
        """
    )

    parser.add_argument(
        "-q", "--query",
        type=str,
        help="单次查询模式，直接处理指定问题"
    )

    parser.add_argument(
        "--profile",
        type=str,
        help="指定模板名称"
    )

    parser.add_argument(
        "--queue-run",
        action="store_true",
        help="执行任务队列并退出"
    )

    parser.add_argument(
        "--queue-import",
        type=str,
        help="从文件导入任务到队列"
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="启动仪表盘服务"
    )

    parser.add_argument(
        "--chat-ui",
        action="store_true",
        help="启动聊天前端服务"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="AI Agent v0.1.0"
    )

    args = parser.parse_args()

    config = get_config()
    if not args.verbose:
        config.logging.console_output = False

    init_logging()
    logger = get_logger("main")
    if not config.model.api_key or config.model.api_key == "your-api-key-here":
        if args.query or args.verbose:
            print("\n警告 / Warning:")
            print("请在 config.yaml 中配置您的 API 密钥")
            print("Please configure your API key in config.yaml")
            print("或设置环境变量 OPENAI_API_KEY / Or set environment variable OPENAI_API_KEY\n")
        if args.query:
            sys.exit(1)

    try:
        logger.info("正在初始化Agent / Initializing Agent...")
        agent = create_agent(profile=args.profile)
        show_steps = True

        if args.dashboard:
            output_dir = getattr(getattr(config, "artifacts", None), "output_dir", "outputs")
            dash_cfg = getattr(config, "dashboard", None)
            host = getattr(dash_cfg, "host", "127.0.0.1")
            port = getattr(dash_cfg, "port", 8765)
            title = getattr(dash_cfg, "title", "SAMA 任务仪表盘")
            auto_open = bool(getattr(dash_cfg, "auto_open", False))
            run_dashboard(
                output_dir=output_dir,
                host=host,
                port=port,
                title=title,
                background=False,
                auto_open=auto_open
            )
            return

        if args.chat_ui:
            chat_cfg = getattr(config, "chat_ui", None)
            host = getattr(chat_cfg, "host", "127.0.0.1")
            port = getattr(chat_cfg, "port", 8790)
            title = getattr(chat_cfg, "title", "sama")
            auto_open = bool(getattr(chat_cfg, "auto_open", False))
            max_port_tries = getattr(chat_cfg, "max_port_tries", 10)
            max_body_size = getattr(chat_cfg, "max_body_size", 20000)
            profile = getattr(chat_cfg, "profile", None)
            run_chat_ui(
                host=host,
                port=port,
                title=title,
                background=False,
                auto_open=auto_open,
                max_port_tries=max_port_tries,
                max_body_size=max_body_size,
                profile=profile
            )
            return

        if args.queue_import:
            from src.runtime.queue import TaskQueue
            queue_cfg = getattr(config, "queue", None)
            queue_path = getattr(queue_cfg, "queue_file", "outputs/task_queue.json")
            queue_auto_resume = bool(getattr(queue_cfg, "auto_resume", True))
            queue = TaskQueue(path=queue_path, auto_resume=queue_auto_resume)
            session = None
            try:
                from src.cli.session import InteractiveSession
                session = InteractiveSession(agent, show_steps=show_steps)
                items = session._import_queue_file(args.queue_import)
                if items:
                    queue.add_items(items)
                    print(f"已导入 {len(items)} 个任务。")
                else:
                    print("未导入任何任务。")
            except Exception as exc:
                print(f"导入失败: {exc}")

        if args.queue_run:
            queue_mode(agent, show_steps=show_steps)
            return

        if args.query:
            single_query(agent, args.query, show_steps=show_steps)
        else:
            interactive_mode(agent, show_steps=show_steps)

    except KeyboardInterrupt:
        print("\n\n再见 / Goodbye!")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"程序错误 / Program error: {str(exc)}")
        print(f"\n程序错误 / Program error: {str(exc)}")
        sys.exit(1)
