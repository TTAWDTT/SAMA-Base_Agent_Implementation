#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# AI Agent 主入口 / AI Agent Main Entry Point
# ==============================================================================
# 使用方法 / Usage:
#   python main.py                    # 交互模式 / Interactive mode
#   python main.py --help             # 显示帮助 / Show help
#   python main.py -q "你好"          # 单次查询 / Single query
# ==============================================================================

import argparse
import sys
import io
import os
import shlex
from typing import Optional, List, Tuple

from src import BaseAgent, get_config, init_logging, get_logger

# 修复 Windows 编码问题 / Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def create_agent() -> BaseAgent:
    """
    创建Agent实例 / Create Agent instance
    
    Returns:
        BaseAgent: Agent实例 / Agent instance
    """
    return BaseAgent()


class InteractiveSession:
    """
    交互会话控制器
    """

    def __init__(self, agent: BaseAgent, show_thinking: bool = True, show_steps: bool = True):
        self.agent = agent
        self.show_thinking = show_thinking
        self.show_steps = show_steps
        self.multiline = False
        self.history = []
        self.logger = get_logger("tui")
        self._exit_requested = False
        self._commands = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "reset": self._cmd_reset,
            "status": self._cmd_status,
            "files": self._cmd_files,
            "context": self._cmd_context,
            "thinking": self._cmd_thinking,
            "steps": self._cmd_steps,
            "multiline": self._cmd_multiline,
            "history": self._cmd_history,
            "clear": self._cmd_clear,
        }
        self._aliases = {
            "?": "help",
            "h": "help",
            "quit": "exit",
            "q": "exit",
            "ctx": "context",
            "ml": "multiline",
            "hist": "history",
            "file": "files",
            "退出": "exit",
            "重置": "reset",
            "状态": "status",
            "文件": "files",
            "帮助": "help",
            "上下文": "context",
            "清屏": "clear",
            "多行": "multiline",
            "思考": "thinking",
            "步骤": "steps",
            "历史": "history",
        }
        self._legacy_commands = {
            "exit",
            "quit",
            "reset",
            "status",
            "files",
            "file",
            "help",
            "context",
            "退出",
            "重置",
            "状态",
            "文件",
            "帮助",
            "上下文",
        }

    def run(self) -> None:
        self._print_banner()

        while not self._exit_requested:
            try:
                user_input = self._read_input()
            except KeyboardInterrupt:
                print("\n已中断，输入 /exit 退出或继续输入。")
                continue
            except EOFError:
                print("\n收到结束信号，退出。")
                break

            if user_input is None:
                continue

            if not user_input:
                continue

            if self._handle_command(user_input):
                continue

            try:
                self._handle_query(user_input)
            except KeyboardInterrupt:
                print("\n已中断，输入 /exit 退出或继续输入。")
                continue
            except Exception as e:
                self.logger.error(f"错误 / Error: {str(e)}")
                print(f"\n发生错误: {str(e)}\n")

    def render_response(self, response) -> None:
        if self.show_thinking and response.steps:
            thinking_steps = [step for step in response.steps if step.thinking]
            if thinking_steps:
                self._print_title("思考过程")
                for step in thinking_steps:
                    print(f"[步骤 {step.step_number}]")
                    print(step.thinking)
                    print(self._rule("-"))

        self._print_title("回答")
        print(response.final_answer if response.final_answer else "(空响应)")

        if self.show_steps:
            self._print_title("执行信息")
            status_text = "成功" if response.success else "失败"
            print(f"状态: {status_text}")
            print(f"迭代: {response.total_iterations}")
            print(f"耗时: {response.execution_time:.2f} 秒")

            tool_summary = self._summarize_tools(response.steps)
            if tool_summary:
                print(f"工具: {tool_summary}")

            if not response.success and response.error_message:
                print(f"错误: {response.error_message}")

    def _handle_query(self, user_input: str) -> None:
        print("\n处理中...\n")
        response = self.agent.run(user_input)
        self.render_response(response)
        self._record_history(user_input, response.final_answer)

    def _record_history(self, question: str, answer: str) -> None:
        self.history.append({
            "question": question,
            "answer": answer or ""
        })

    def _handle_command(self, user_input: str) -> bool:
        cmd, args = self._parse_command(user_input)
        if not cmd:
            return False

        if cmd == "__invalid__":
            return True

        handler = self._commands.get(cmd)
        if not handler:
            print(f"未知命令: {cmd}，输入 /help 查看命令列表。")
            return True

        handler(args)
        return True

    def _parse_command(self, user_input: str) -> Tuple[Optional[str], List[str]]:
        raw = user_input.strip()
        if not raw:
            return None, []

        if raw.startswith(("/", ":")):
            raw = raw[1:].strip()
            if not raw:
                return None, []
            try:
                parts = shlex.split(raw)
            except ValueError:
                print("命令解析失败，请检查引号。")
                return "__invalid__", []
            cmd = self._normalize_command(parts[0])
            return cmd, parts[1:]

        if raw in self._legacy_commands or raw.lower() in self._legacy_commands:
            try:
                parts = shlex.split(raw)
            except ValueError:
                print("命令解析失败，请检查引号。")
                return "__invalid__", []
            cmd = self._normalize_command(parts[0])
            return cmd, parts[1:]

        return None, []

    def _normalize_command(self, cmd: str) -> str:
        if cmd in self._aliases:
            return self._aliases[cmd]
        lower_cmd = cmd.lower()
        return self._aliases.get(lower_cmd, lower_cmd)

    def _read_input(self) -> Optional[str]:
        if self.multiline:
            return self._read_multiline_input()
        return input(">> ").strip()

    def _read_multiline_input(self) -> str:
        lines = []
        while True:
            line = input("... ")
            if line.strip() == ".end":
                break
            lines.append(line)
        return "\n".join(lines).strip()

    def _summarize_tools(self, steps) -> str:
        if not steps:
            return ""

        tool_counts = {}
        for step in steps:
            for call in step.tool_calls:
                tool_counts[call.tool_name] = tool_counts.get(call.tool_name, 0) + 1

        if not tool_counts:
            return ""

        parts = []
        for name in sorted(tool_counts.keys()):
            parts.append(f"{name} x{tool_counts[name]}")
        return ", ".join(parts)

    def _truncate(self, text: str, max_length: int = 160) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    def _parse_bool_arg(self, args: List[str]) -> Optional[bool]:
        if not args:
            return None
        value = args[0].strip().lower()
        if value in {"on", "true", "1", "yes", "y", "开", "开启"}:
            return True
        if value in {"off", "false", "0", "no", "n", "关", "关闭"}:
            return False
        return None

    def _print_banner(self) -> None:
        self._print_title("AI Agent 交互模式")
        print("输入问题开始对话，输入 /help 查看命令。")
        print("多行输入模式下使用 .end 结束。")
        print(self._rule())

    def _print_title(self, title: str) -> None:
        print("\n" + self._rule())
        print(title)
        print(self._rule())

    def _rule(self, char: str = "=") -> str:
        width = self._get_line_width()
        return char * width

    def _get_line_width(self) -> int:
        try:
            width = os.get_terminal_size().columns
        except OSError:
            width = 72
        return max(60, min(width, 120))

    def _cmd_help(self, args: List[str]) -> None:
        self._print_title("可用命令")
        print("/help                 显示帮助")
        print("/exit                 退出程序")
        print("/reset                重置对话")
        print("/status               查看Agent状态")
        print("/files                查看文件上下文")
        print("/context [on|off]      切换显式上下文模式")
        print("/thinking [on|off]     切换思考过程展示")
        print("/steps [on|off]        切换步骤概览展示")
        print("/multiline [on|off]    切换多行输入模式")
        print("/history [n]           查看最近n条对话")
        print("/clear                清屏")
        print("\n说明：保留 exit/reset/status/files 等原有命令，不带前缀也可使用。")

    def _cmd_exit(self, args: List[str]) -> None:
        print("\n再见。")
        self._exit_requested = True

    def _cmd_reset(self, args: List[str]) -> None:
        self.agent.reset()
        print("对话已重置。")

    def _cmd_status(self, args: List[str]) -> None:
        status = self.agent.get_status()
        self._print_title("Agent 状态")
        if not status:
            print("无状态信息。")
            return
        width = max(len(str(key)) for key in status.keys())
        for key, value in status.items():
            print(f"{str(key).ljust(width)} : {value}")

    def _cmd_files(self, args: List[str]) -> None:
        files_summary = self.agent.get_files_summary()
        self._print_title("文件上下文")
        print(files_summary)

    def _cmd_context(self, args: List[str]) -> None:
        desired = self._parse_bool_arg(args)
        if desired is None:
            enabled = self.agent.toggle_verbose_context()
        else:
            enabled = self._set_verbose_context(desired)
        status_text = "开启" if enabled else "关闭"
        print(f"显式上下文模式: {status_text}")

    def _set_verbose_context(self, enabled: bool) -> bool:
        if self.agent.verbose_context != enabled:
            self.agent.toggle_verbose_context()
        return self.agent.verbose_context

    def _cmd_thinking(self, args: List[str]) -> None:
        desired = self._parse_bool_arg(args)
        if desired is None:
            self.show_thinking = not self.show_thinking
        else:
            self.show_thinking = desired
        status_text = "开启" if self.show_thinking else "关闭"
        print(f"思考过程展示: {status_text}")

    def _cmd_steps(self, args: List[str]) -> None:
        desired = self._parse_bool_arg(args)
        if desired is None:
            self.show_steps = not self.show_steps
        else:
            self.show_steps = desired
        status_text = "开启" if self.show_steps else "关闭"
        print(f"步骤概览展示: {status_text}")

    def _cmd_multiline(self, args: List[str]) -> None:
        desired = self._parse_bool_arg(args)
        if desired is None:
            self.multiline = not self.multiline
        else:
            self.multiline = desired
        status_text = "开启" if self.multiline else "关闭"
        print(f"多行输入模式: {status_text}")
        if self.multiline:
            print("输入 .end 结束多行输入。")

    def _cmd_history(self, args: List[str]) -> None:
        limit = 5
        if args:
            try:
                limit = max(1, int(args[0]))
            except ValueError:
                print("history 参数必须为数字。")
                return

        if not self.history:
            print("暂无历史记录。")
            return

        self._print_title(f"最近 {min(limit, len(self.history))} 条对话")
        for idx, item in enumerate(self.history[-limit:], 1):
            question = self._truncate(item["question"])
            answer = self._truncate(item["answer"])
            print(f"[{idx}] Q: {question}")
            print(f"    A: {answer}")

    def _cmd_clear(self, args: List[str]) -> None:
        os.system("cls" if sys.platform == 'win32' else "clear")


def interactive_mode(agent: BaseAgent, show_thinking: bool = True, show_steps: bool = True) -> None:
    """
    交互模式 / Interactive mode
    
    Args:
        agent: Agent实例 / Agent instance
    """
    session = InteractiveSession(agent, show_thinking=show_thinking, show_steps=show_steps)
    session.run()


def single_query(agent: BaseAgent, query: str, show_thinking: bool = True, show_steps: bool = True) -> None:
    """
    单次查询模式 / Single query mode
    
    Args:
        agent: Agent实例 / Agent instance
        query: 用户查询 / User query
    """
    response = agent.run(query)
    session = InteractiveSession(agent, show_thinking=show_thinking, show_steps=show_steps)
    session.render_response(response)


def main():
    """
    主函数 / Main function
    """
    # 解析命令行参数 / Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Agent - 一个基于LLM的智能助手 / An LLM-based intelligent assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  python main.py                    # 交互模式 / Interactive mode
  python main.py -q "计算 2+2"      # 单次查询 / Single query
  python main.py --verbose          # 详细输出模式 / Verbose mode

更多信息请参阅 README.md / For more information, see README.md
        """
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="单次查询模式，直接处理指定问题 / Single query mode, directly process the specified question"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出 / Enable verbose output"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="AI Agent v0.1.0"
    )
    
    args = parser.parse_args()
    
    # 初始化日志 / Initialize logging
    init_logging()
    logger = get_logger("main")
    
    # 检查配置 / Check configuration
    config = get_config()
    if not config.model.api_key or config.model.api_key == "your-api-key-here":
        print("\n警告 / Warning:")
        print("请在 config.yaml 中配置您的 API 密钥")
        print("Please configure your API key in config.yaml")
        print("或设置环境变量 OPENAI_API_KEY / Or set environment variable OPENAI_API_KEY\n")
        
        # 在非查询模式下仍然允许进入交互模式，方便测试
        # Still allow entering interactive mode in non-query mode for testing
        if args.query:
            sys.exit(1)
    
    try:
        # 创建Agent / Create Agent
        logger.info("正在初始化Agent / Initializing Agent...")
        agent = create_agent()
        show_thinking = args.verbose or config.agent.verbose
        show_steps = True
        
        # 根据参数选择模式 / Select mode based on arguments
        if args.query:
            # 单次查询模式 / Single query mode
            single_query(agent, args.query, show_thinking=show_thinking, show_steps=show_steps)
        else:
            # 交互模式 / Interactive mode
            interactive_mode(agent, show_thinking=show_thinking, show_steps=show_steps)
            
    except KeyboardInterrupt:
        print("\n\n再见 / Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序错误 / Program error: {str(e)}")
        print(f"\n程序错误 / Program error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
