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
import json
import sys
import io
import os
import shlex
import atexit
import time
import threading
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict

try:
    import readline as _readline
except ImportError:
    try:
        import pyreadline3 as _readline
    except ImportError:
        _readline = None

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


LOGO = [
    " ##### " + "  " + "  ###  " + "  " + "##   ##" + "  " + "  ###  ",
    "##   ##" + "  " + " ## ## " + "  " + "### ###" + "  " + " ## ## ",
    "##     " + "  " + "##   ##" + "  " + "#######" + "  " + "##   ##",
    " ##### " + "  " + "#######" + "  " + "## # ##" + "  " + "#######",
    "     ##" + "  " + "##   ##" + "  " + "##   ##" + "  " + "##   ##",
    "##   ##" + "  " + "##   ##" + "  " + "##   ##" + "  " + "##   ##",
    " ##### " + "  " + "##   ##" + "  " + "##   ##" + "  " + "##   ##",
]

SPRITE = [
    "            .-====-.",
    "         .-##########-.",
    "       .-##############-.",
    "      /#######  @  #######\\",
    "     /######## #### ########\\",
    "    |######### #### #########|",
    "    |######### #### #########|",
    "    |######### ##@# #########|",
    "    |######### #### #########|",
    "    |######### #### #########|",
    "    |######### #### #########|",
    "     \\######## #### ########/",
    "      \\#######  ##  #######/",
    "       '-##############-'",
    "          '-########-'",
    "             '-##-'",
    "             .-**-.",
    "              '--'",
]


class AnimatedIndicator:
    """
    加载动画控制器
    """

    STYLES = ("gloss", "prism", "square", "block", "dots", "bar", "scan", "pulse", "wave", "spark", "orbit", "comet")

    def __init__(
        self,
        message: str = "thinking",
        interval: float = 0.12,
        enabled: bool = True,
        style: str = "gloss",
        use_color: bool = False,
        message_style: Optional[str] = None
    ):
        self.message = message
        self.interval = interval
        self.enabled = enabled
        self.style = style
        self.use_color = use_color
        self.message_style = message_style
        self._stop = threading.Event()
        self._thread = None
        self._gloss_width = 14
        self._prism_width = 12
        self._frames = self._get_frames(style)
        self._frame_width = self._get_frame_width(style)
        self._line_width = len(message) + 1 + self._frame_width

    def start(self) -> None:
        if not self.enabled:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join()
        self._clear_line()

    def _run(self) -> None:
        idx = 0
        while not self._stop.is_set():
            frame = self._frames[idx % len(self._frames)]
            message = self._style(self.message, self.message_style) if self.message_style else self.message
            frame_text = self._render_frame(frame, idx)
            text = f"{message} {frame_text}"
            pad = self._line_width - self._visible_len(text)
            if pad > 0:
                text += " " * pad
            print("\r" + text, end="", flush=True)
            time.sleep(self.interval)
            idx += 1

    def _clear_line(self) -> None:
        print("\r" + (" " * self._line_width) + "\r", end="", flush=True)

    def _get_frames(self, style: str) -> List[Any]:
        if style == "gloss":
            return self._build_gloss_positions(width=self._gloss_width)
        if style == "prism":
            return self._build_prism_positions(width=self._prism_width)
        if style == "square":
            return self._build_dot_square_frames(width=8, dot_count=3)
        if style == "block":
            return self._build_block_frames(width=12, block="[]")
        if style == "dots":
            return [".  ", ".. ", "...", " ..", "  ."]
        if style == "bar":
            return self._build_bar_frames(width=10, fill="=")
        if style == "scan":
            return self._build_block_frames(width=12, block="<>")
        if style == "pulse":
            return ["( )", "(-)", "(=)", "(*)", "(=)", "(-)"]
        if style == "wave":
            return self._build_wave_frames(width=8)
        if style == "spark":
            return self._build_spark_frames(width=6)
        if style == "orbit":
            return self._build_orbit_frames(width=8, core="o")
        if style == "comet":
            return self._build_comet_frames(width=8, head="*", tail=".")
        return ["..."]

    def _get_frame_width(self, style: str) -> int:
        if style == "gloss":
            return self._gloss_width + 2
        if style == "prism":
            return self._prism_width + 2
        return max(len(frame) for frame in self._frames)

    def _render_frame(self, frame: Any, idx: int) -> str:
        if self.style == "gloss":
            return self._render_gloss_frame(int(frame))
        if self.style == "prism":
            return self._render_prism_frame(int(frame))
        return frame if isinstance(frame, str) else str(frame)

    def _style(self, text: str, style: Optional[str]) -> str:
        if not self.use_color or not style:
            return text
        styles = {
            "bold": "\x1b[1m",
            "dim": "\x1b[2m",
            "cyan": "\x1b[36m",
            "blue": "\x1b[34m",
            "magenta": "\x1b[35m",
            "green": "\x1b[32m",
            "yellow": "\x1b[33m",
            "gray": "\x1b[90m",
        }
        prefix = styles.get(style)
        if not prefix:
            return text
        return f"{prefix}{text}\x1b[0m"

    def _strip_ansi(self, text: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    def _visible_len(self, text: str) -> int:
        return len(self._strip_ansi(text))

    def _build_gloss_positions(self, width: int) -> List[int]:
        positions = list(range(width))
        positions.extend(range(width - 2, 0, -1))
        return positions

    def _build_prism_positions(self, width: int) -> List[int]:
        positions = list(range(width))
        positions.extend(range(width - 1, -1, -1))
        return positions

    def _render_gloss_frame(self, pos: int) -> str:
        width = self._gloss_width
        chars = []
        for idx in range(width):
            distance = abs(idx - pos)
            if distance == 0:
                ch = "#"
                color = "cyan"
            elif distance == 1:
                ch = "="
                color = "blue"
            elif distance == 2:
                ch = "-"
                color = "blue"
            else:
                ch = "."
                color = "gray"
            chars.append(self._style(ch, color))
        left = self._style("[", "blue")
        right = self._style("]", "blue")
        return left + "".join(chars) + right

    def _render_prism_frame(self, offset: int) -> str:
        width = self._prism_width
        palette = ["magenta", "blue", "cyan", "green", "yellow"]
        chars = []
        for idx in range(width):
            if idx == offset % width:
                ch = ">"
                color = "cyan"
            elif idx == (offset - 1) % width:
                ch = "="
                color = "blue"
            else:
                ch = "-"
                color = palette[(idx + offset) % len(palette)]
            chars.append(self._style(ch, color))
        left = self._style("[", "magenta")
        right = self._style("]", "magenta")
        return left + "".join(chars) + right

    def _build_block_frames(self, width: int, block: str) -> List[str]:
        block_len = len(block)
        track_len = max(width, block_len + 2)
        max_pos = track_len - block_len
        frames = []
        for pos in range(0, max_pos + 1):
            left = " " * pos
            right = " " * (max_pos - pos)
            frames.append("[" + left + block + right + "]")
        for pos in range(max_pos - 1, 0, -1):
            left = " " * pos
            right = " " * (max_pos - pos)
            frames.append("[" + left + block + right + "]")
        return frames

    def _build_bar_frames(self, width: int, fill: str) -> List[str]:
        frames = []
        for size in range(1, width + 1):
            frames.append("[" + fill * size + " " * (width - size) + "]")
        for size in range(width - 1, 1, -1):
            frames.append("[" + fill * size + " " * (width - size) + "]")
        return frames

    def _build_dot_square_frames(self, width: int, dot_count: int) -> List[str]:
        frames = []
        inner = [" "] * width
        for pos in range(width):
            inner = [" "] * width
            for i in range(dot_count):
                inner[(pos + i) % width] = "."
            frames.append("[" + "".join(inner) + "]")
        return frames

    def _build_wave_frames(self, width: int) -> List[str]:
        base = ["~", "^", "~", " "]
        frames = []
        for shift in range(len(base)):
            line = "".join(base[(i + shift) % len(base)] for i in range(width))
            frames.append("[" + line + "]")
        return frames

    def _build_spark_frames(self, width: int) -> List[str]:
        frames = []
        for pos in range(width):
            inner = [" "] * width
            inner[pos] = "*"
            frames.append("[" + "".join(inner) + "]")
        for pos in range(width - 2, 0, -1):
            inner = [" "] * width
            inner[pos] = "*"
            frames.append("[" + "".join(inner) + "]")
        return frames

    def _build_orbit_frames(self, width: int, core: str) -> List[str]:
        frames = []
        for pos in range(width):
            inner = [" "] * width
            inner[pos] = core
            frames.append("(" + "".join(inner) + ")")
        for pos in range(width - 2, 0, -1):
            inner = [" "] * width
            inner[pos] = core
            frames.append("(" + "".join(inner) + ")")
        return frames

    def _build_comet_frames(self, width: int, head: str, tail: str) -> List[str]:
        frames = []
        tail_len = 3
        total = width + tail_len
        for pos in range(total):
            inner = [" "] * width
            head_pos = min(pos, width - 1)
            inner[head_pos] = head
            for offset in range(1, tail_len + 1):
                idx = head_pos - offset
                if idx >= 0:
                    inner[idx] = tail
            frames.append("<" + "".join(inner) + ">")
        for pos in range(total - 2, 0, -1):
            inner = [" "] * width
            head_pos = min(pos, width - 1)
            inner[head_pos] = head
            for offset in range(1, tail_len + 1):
                idx = head_pos - offset
                if idx >= 0:
                    inner[idx] = tail
            frames.append("<" + "".join(inner) + ">")
        return frames


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
        self._prompt_label = "sama"
        self._prompt_multiline_label = "..."
        self._prompt_suffix = " "
        self._prompt_multiline_suffix = " "
        self._prompt_pad = 1
        self.prompt = self._prompt_label
        self.prompt_multiline = self._prompt_multiline_label
        self._missing_key_warned = False
        self._exit_requested = False
        self._readline = _readline
        self._history_path = Path(self.agent.workspace) / ".sama_history"
        self._use_color = self._should_use_color()
        self._enable_windows_ansi()
        self._supports_ansi = self._should_use_ansi()
        self._ascii_frame = bool(os.getenv("SAMA_ASCII_FRAME"))
        self._frame_chars = self._get_frame_chars()
        self._frame_enabled = sys.stdout.isatty() and not os.getenv("SAMA_NO_FRAME")
        self._frame_title = "SAMA"
        self._frame_title_suffix = "LIVE"
        self._frame_title_offset = 2
        self._frame_shimmer_span = 6
        self._frame_shimmer_speed = 2
        self._frame_glow_span = 3
        self._frame_ripple_span = 10
        self._output_title = "ASSISTANT"
        self._output_title_suffix = ""
        self._output_title_offset = 2
        self._output_pad = 1
        self._apply_prompt_style()
        self._animation_enabled = self._should_use_animation()
        self._animation_style = "gloss"
        self._animation_index = 0
        self._intro_enabled = self._animation_enabled and self._supports_ansi and not os.getenv("SAMA_NO_INTRO")
        self._manual_input_enabled = self._should_use_manual_input()
        self._manual_input_active = False
        self._manual_buffer = []
        self._manual_cursor = 0
        self._manual_render_lines = 1
        self._input_history = []
        self._input_history_idx = None
        self._stream_enabled = self._should_use_streaming()
        self._stream_delay = self._get_stream_delay()
        self._stream_chunk = self._get_stream_chunk()
        self._stream_line_delay = self._get_stream_line_delay()
        self._tracker_enabled = self._should_use_tracker()
        self._tracker_interval = 0.03
        self._tracker_current_x = 0.0
        self._tracker_phase = 0
        self._tracker_direction = -1
        self._tracker_stop = threading.Event()
        self._tracker_thread = None
        self._tracker_lock = threading.Lock()
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
            "log": self._cmd_log,
            "anim": self._cmd_anim,
            "stream": self._cmd_stream,
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
            "logs": "log",
            "animation": "anim",
            "streaming": "stream",
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
            "日志": "log",
            "动画": "anim",
            "流式": "stream",
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
            "log",
            "anim",
            "stream",
            "退出",
            "重置",
            "状态",
            "文件",
            "帮助",
            "上下文",
            "日志",
            "动画",
            "流式",
        }
        self._init_readline()

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
        thinking_steps = [step for step in response.steps if step.thinking] if response.steps else []
        printed_section = False

        if self.show_thinking and thinking_steps:
            print()
            self._render_thinking_block(thinking_steps)
            printed_section = True

        tool_lines, read_files, write_files = self._collect_tool_activity(response.steps)
        if self.show_steps and (tool_lines or read_files or write_files):
            if not printed_section:
                print()
            else:
                print()
            self._render_tool_activity(tool_lines)
            self._render_file_activity(read_files, write_files)
            printed_section = True

        output_text = response.final_answer or "(空响应)"
        if self._frame_enabled:
            print()
            self._render_output_frame(output_text)
        else:
            print(self._style("\nassistant:", "bold"))
            if self._stream_enabled:
                self._stream_print(output_text)
            else:
                print(output_text)

        self._render_final_file_mentions(output_text, read_files, write_files)

        if self.show_steps:
            status_text = "ok" if response.success else "fail"
            meta_parts = [
                f"status={status_text}",
                f"iter={response.total_iterations}",
                f"time={response.execution_time:.2f}s"
            ]
            tool_summary = self._summarize_tools(response.steps)
            if tool_summary:
                meta_parts.append(f"tools={tool_summary}")

            print(self._style("[" + " | ".join(meta_parts) + "]", "dim"))
            if not response.success and response.error_message:
                print(self._style(f"[error] {response.error_message}", "error"))

    def _handle_query(self, user_input: str) -> None:
        if not self._has_valid_api_key():
            self._print_missing_key_hint()
            return
        if self._animation_enabled:
            print()
            style = self._resolve_animation_style()
            indicator = AnimatedIndicator(
                enabled=True,
                style=style,
                use_color=self._use_color and self._supports_ansi,
                message_style="cyan"
            )
            indicator.start()
            try:
                response = self.agent.run(user_input)
            finally:
                indicator.stop()
        else:
            print(self._style("\n...", "dim"))
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
        if self._tracker_enabled:
            if self._manual_input_enabled and not self._readline:
                return self._read_input_manual_with_tracker()
            return self._read_input_with_tracker()
        if self._frame_enabled:
            return self._read_input_with_frame()
        return input(self.prompt).strip()

    def _read_multiline_input(self) -> str:
        lines = []
        while True:
            line = input(self.prompt_multiline)
            if line.strip() == ".end":
                break
            lines.append(line)
        return "\n".join(lines).strip()

    def _read_input_with_tracker(self) -> Optional[str]:
        self._print_tracker_anchor()
        self._start_tracker()
        try:
            user_input = input(self.prompt)
        finally:
            self._stop_tracker()
        self._finalize_input_frame(user_input)
        self._print_input_frame_bottom()
        return user_input.strip()

    def _read_input_with_frame(self) -> Optional[str]:
        self._print_frame_top()
        try:
            user_input = input(self.prompt)
        finally:
            self._finalize_input_frame(user_input)
            self._print_input_frame_bottom()
        return user_input.strip()

    def _read_input_manual_with_tracker(self) -> Optional[str]:
        self._manual_input_active = True
        self._manual_buffer = []
        self._manual_cursor = 0
        self._manual_render_lines = 1
        self._print_tracker_anchor()
        self._start_tracker()
        try:
            user_input = self._read_input_manual()
        finally:
            self._stop_tracker()
            self._manual_input_active = False
        self._finalize_input_frame(user_input)
        self._print_input_frame_bottom()
        return user_input.strip()

    def _read_input_manual(self) -> str:
        if sys.platform != "win32":
            return input(self.prompt)
        import msvcrt

        buffer = []
        cursor = 0
        self._input_history_idx = None
        self._render_manual_input(buffer, cursor)
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x1a":
                raise EOFError
            if ch == "\x08":
                if cursor > 0:
                    buffer.pop(cursor - 1)
                    cursor -= 1
            elif ch in ("\x00", "\xe0"):
                key = msvcrt.getwch()
                if key == "K":
                    cursor = max(0, cursor - 1)
                elif key == "M":
                    cursor = min(len(buffer), cursor + 1)
                elif key == "G":
                    cursor = 0
                elif key == "O":
                    cursor = len(buffer)
                elif key == "S":
                    if cursor < len(buffer):
                        buffer.pop(cursor)
                elif key == "H":
                    buffer, cursor = self._history_move(-1)
                elif key == "P":
                    buffer, cursor = self._history_move(1)
            elif ch == "\t":
                buffer.insert(cursor, " ")
                cursor += 1
                buffer.insert(cursor, " ")
                cursor += 1
            elif ch.isprintable():
                buffer.insert(cursor, ch)
                cursor += 1
            self._manual_cursor = cursor
            self._manual_buffer = buffer
            self._render_manual_input(buffer, cursor)

        text = "".join(buffer)
        if text:
            self._input_history.append(text)
        return text

    def _history_move(self, delta: int) -> Tuple[List[str], int]:
        if not self._input_history:
            return self._manual_buffer, self._manual_cursor
        if self._input_history_idx is None:
            self._input_history_idx = len(self._input_history)
        self._input_history_idx = max(0, min(len(self._input_history), self._input_history_idx + delta))
        if self._input_history_idx >= len(self._input_history):
            return [], 0
        item = self._input_history[self._input_history_idx]
        return list(item), len(item)

    def _render_manual_input(self, buffer: List[str], cursor: int) -> None:
        width = self._get_terminal_columns()
        prompt = self.prompt
        full = prompt + "".join(buffer)
        full_width = self._display_width(full)
        total_lines = max(1, (full_width + width - 1) // width)
        prev_lines = max(1, self._manual_render_lines)
        cursor_width = self._display_width(prompt + "".join(buffer[:cursor]))
        cursor_row = cursor_width // width if width > 0 else 0
        cursor_col = cursor_width % width if width > 0 else 0
        end_row = max(0, (full_width - 1) // width) if full_width > 0 and width > 0 else 0

        with self._tracker_lock:
            sys.stdout.write("\r")
            if prev_lines > 1:
                sys.stdout.write(f"\x1b[{prev_lines - 1}A")
            for idx in range(prev_lines):
                sys.stdout.write("\x1b[2K")
                if idx < prev_lines - 1:
                    sys.stdout.write("\x1b[1B\r")
            if prev_lines > 1:
                sys.stdout.write(f"\x1b[{prev_lines - 1}A")
                sys.stdout.write("\r")
            sys.stdout.write(full)
            if end_row > cursor_row:
                sys.stdout.write(f"\x1b[{end_row - cursor_row}A")
            sys.stdout.write("\r")
            sys.stdout.write(f"\x1b[{cursor_col + 1}G")
            sys.stdout.flush()

        self._manual_render_lines = total_lines

    def _stream_print(self, text: str) -> None:
        buffer = []
        chunk = max(1, self._stream_chunk)
        for ch in text:
            buffer.append(ch)
            if ch == "\n" or len(buffer) >= chunk:
                print("".join(buffer), end="", flush=True)
                buffer.clear()
                if ch == "\n":
                    time.sleep(self._stream_line_delay)
                else:
                    time.sleep(self._stream_delay)
        if buffer:
            print("".join(buffer), end="", flush=True)
        if not text.endswith("\n"):
            print()

    def _render_output_frame(self, text: str) -> None:
        if self._stream_enabled:
            self._stream_output_frame(text)
        else:
            self._print_output_frame(text)

    def _wrap_text_lines(self, text: str, width: int) -> List[str]:
        if width <= 0:
            return [text] if text else [""]
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
        raw_lines = normalized.split("\n")
        lines = []
        for raw in raw_lines:
            if raw == "":
                lines.append("")
                continue
            current = []
            current_width = 0
            for ch in raw:
                w = self._char_width(ch)
                if current and current_width + w > width:
                    lines.append("".join(current))
                    current = [ch]
                    current_width = w
                elif not current and w > width:
                    lines.append(ch)
                    current = []
                    current_width = 0
                else:
                    current.append(ch)
                    current_width += w
            if current:
                lines.append("".join(current))
        if not lines:
            lines.append("")
        return lines

    def _print_output_frame(self, text: str) -> None:
        width = self._get_terminal_columns()
        inner_width = max(1, width - 2)
        pad = max(0, min(self._output_pad, inner_width // 2))
        content_width = max(1, inner_width - pad * 2)
        left_border = self._frame_chars["vertical"]
        right_border = self._frame_chars["vertical"]
        if self._use_color:
            left_border = self._style(left_border, "blue")
            right_border = self._style(right_border, "blue")

        print(self._build_output_border(width, top=True, phase=self._tracker_phase))
        for line in self._wrap_text_lines(text, content_width):
            visible = self._display_width(line)
            if visible > content_width:
                line = self._clip_to_width(line, content_width)
                visible = self._display_width(line)
            padding = " " * max(0, content_width - visible)
            print(f"{left_border}{' ' * pad}{line}{padding}{' ' * pad}{right_border}")
        print(self._build_output_border(width, top=False, phase=self._tracker_phase))

    def _stream_output_frame(self, text: str) -> None:
        width = self._get_terminal_columns()
        inner_width = max(1, width - 2)
        pad = max(0, min(self._output_pad, inner_width // 2))
        content_width = max(1, inner_width - pad * 2)
        left_border = self._frame_chars["vertical"]
        right_border = self._frame_chars["vertical"]
        if self._use_color:
            left_border = self._style(left_border, "blue")
            right_border = self._style(right_border, "blue")

        print(self._build_output_border(width, top=True, phase=self._tracker_phase))
        sys.stdout.write(left_border + (" " * pad))
        sys.stdout.flush()

        line_len = 0
        chunk_count = 0
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
        for ch in normalized:
            if ch == "\n":
                if line_len < content_width:
                    sys.stdout.write(" " * (content_width - line_len))
                sys.stdout.write((" " * pad) + right_border + "\n")
                sys.stdout.flush()
                sys.stdout.write(left_border + (" " * pad))
                sys.stdout.flush()
                line_len = 0
                chunk_count = 0
                time.sleep(self._stream_line_delay)
                continue
            w = self._char_width(ch)
            if line_len + w > content_width and line_len > 0:
                sys.stdout.write((" " * pad) + right_border + "\n")
                sys.stdout.write(left_border + (" " * pad))
                sys.stdout.flush()
                line_len = 0
                chunk_count = 0
            sys.stdout.write(ch)
            line_len += w
            chunk_count += 1
            if chunk_count >= max(1, self._stream_chunk):
                sys.stdout.flush()
                time.sleep(self._stream_delay)
                chunk_count = 0

        if line_len < content_width:
            sys.stdout.write(" " * (content_width - line_len))
        sys.stdout.write((" " * pad) + right_border + "\n")
        sys.stdout.flush()
        print(self._build_output_border(width, top=False, phase=self._tracker_phase))

    def _format_status_prefix(self, label: str, color: str) -> str:
        dot = "*" if self._ascii_frame else "\u25cf"
        label = label or ""
        if not self._use_color:
            return f"{dot} {label}".strip()
        return f"{self._style(dot, color)} {self._style(label, color)}".strip()

    def _print_status_line(self, label: str, text: str, color: str) -> None:
        prefix = self._format_status_prefix(label, color)
        if text:
            print(f"{prefix} {text}")
        else:
            print(prefix)

    def _append_line_hint(self, path_text: str) -> str:
        if not path_text:
            return path_text
        if path_text.endswith(("\\", "/")):
            return path_text
        _, sep, tail = path_text.rpartition(":")
        if sep and tail.isdigit():
            return path_text
        return f"{path_text}:1"

    def _format_clickable_path(self, path: str) -> str:
        try:
            resolved = Path(path).expanduser().resolve()
            text = str(resolved)
            if resolved.is_dir():
                return text
            return self._append_line_hint(text)
        except Exception:
            return self._append_line_hint(str(path))

    def _render_block_lines(self, text: str) -> None:
        prefix = self._frame_chars["vertical"] if self._frame_enabled else "|"
        if self._use_color:
            prefix = self._style(prefix, "gray")
        lines = text.splitlines() if text else [""]
        for line in lines:
            if line:
                print(f"{prefix} {line}")
            else:
                print(f"{prefix}")

    def _render_thinking_block(self, steps: List) -> None:
        if not steps:
            return
        multi = len(steps) > 1
        for step in steps:
            suffix = f"{step.step_number}" if multi else ""
            self._print_status_line("thinking", suffix, "cyan")
            self._render_block_lines((step.thinking or "").strip())

    def _parse_json_payload(self, payload: Any) -> Optional[Dict[str, Any]]:
        if payload is None:
            return None
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            text = payload.strip()
            if not text:
                return None
            if not (text.startswith("{") or text.startswith("[")):
                return None
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        return None

    def _format_tool_detail(self, tool_name: str, result: Optional[Any]) -> str:
        parts = []
        if result and getattr(result, "error_message", None):
            parts.append(f"error: {result.error_message}")
        if tool_name == "web_search" and result:
            payload = self._parse_json_payload(result.output)
            if isinstance(payload, dict):
                for key in ("error", "notice", "tavily_error", "hint"):
                    value = payload.get(key)
                    if value:
                        parts.append(f"{key}: {value}")
        if not parts:
            return ""
        detail = "; ".join(dict.fromkeys(parts))
        return self._truncate(detail)

    def _line_may_contain_path(self, line: str) -> bool:
        lowered = line.lower()
        keywords = (
            "保存", "输出", "生成", "文件", "路径",
            "path", "file", "saved", "save", "output", "export", "write"
        )
        return any(keyword in lowered for keyword in keywords)

    def _clean_path_token(self, text: str) -> str:
        cleaned = text.strip().strip("`\"'")
        return cleaned.rstrip(".,;)]}>")

    def _looks_like_path(self, text: str) -> bool:
        if not text:
            return False
        candidate = text.strip().strip("`\"'")
        if candidate.startswith(("http://", "https://")):
            return False
        if candidate.startswith("/"):
            cmd = candidate[1:].lower()
            if cmd in self._commands:
                return False
        if re.match(r"^[A-Za-z]:[\\/]", candidate):
            return True
        if candidate.startswith(("/", "./", "../", ".\\", "..\\")):
            return True
        if re.match(r"^(workspace|outputs|dataset)[/\\\\]", candidate, re.IGNORECASE):
            return True
        return False

    def _extract_paths_from_text(self, text: str) -> List[str]:
        if not text:
            return []
        paths = []
        seen = set()
        patterns = [
            r"(?P<path>[A-Za-z]:[\\/][^\s\"'<>|]+(?:[\\/][^\s\"'<>|]+)*(?::\d+)?)",
            r"(?P<path>(?:\.\.?[\\/])[^\s\"'<>|]+(?::\d+)?)",
            r"(?P<path>(?:workspace|outputs|dataset)[/\\\\][^\s\"'<>|]+(?::\d+)?)",
            r"(?P<path>/(?:[^\s\"'<>|]+/)*[^\s\"'<>|]+(?::\d+)?)",
        ]
        prefixes = ("file:", "path:", "文件:", "路径:", "输出文件:", "保存到:", "保存为:", "output:", "saved:", "save to:")

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            for prefix in prefixes:
                if lowered.startswith(prefix):
                    candidate = self._clean_path_token(stripped[len(prefix):].strip())
                    if self._looks_like_path(candidate):
                        key = self._normalize_path_key(candidate)
                        if key not in seen:
                            paths.append(candidate)
                            seen.add(key)
                    stripped = ""
                    break
            if not stripped:
                continue
            candidate = self._clean_path_token(stripped)
            if self._looks_like_path(candidate):
                key = self._normalize_path_key(candidate)
                if key not in seen:
                    paths.append(candidate)
                    seen.add(key)
                continue
            if not self._line_may_contain_path(stripped):
                continue
            for pattern in patterns:
                for match in re.finditer(pattern, stripped):
                    candidate = self._clean_path_token(match.group("path"))
                    if not candidate:
                        continue
                    if not self._looks_like_path(candidate):
                        continue
                    key = self._normalize_path_key(candidate)
                    if key in seen:
                        continue
                    paths.append(candidate)
                    seen.add(key)
        return paths

    def _normalize_path_key(self, path: str) -> str:
        raw = str(path).strip()
        raw = re.sub(r":\d+$", "", raw)
        try:
            resolved = Path(raw).expanduser().resolve()
            return str(resolved).lower()
        except Exception:
            return raw.lower()

    def _render_final_file_mentions(self, output_text: str, read_files: List[str], write_files: List[str]) -> None:
        extracted = self._extract_paths_from_text(output_text)
        if not extracted:
            return
        known = set()
        for path in read_files + write_files:
            known.add(self._normalize_path_key(path))
        for path in extracted:
            key = self._normalize_path_key(path)
            if key in known:
                continue
            known.add(key)
            self._print_status_line("file", self._format_clickable_path(path), "magenta")

    def _collect_tool_activity(self, steps: List) -> Tuple[List[str], List[str], List[str]]:
        tool_lines = []
        read_files = []
        write_files = []
        seen_reads = set()
        seen_writes = set()
        if not steps:
            return tool_lines, read_files, write_files
        for step in steps:
            results = step.tool_results or []
            for idx, call in enumerate(step.tool_calls):
                tool_name = call.tool_name
                args = call.arguments or {}
                op = str(args.get("operation", "")).lower()
                if tool_name == "read_file":
                    op = "read"
                elif tool_name == "write_file":
                    op = "write"
                is_file_tool = tool_name in ("file", "read_file", "write_file")
                path = None
                if is_file_tool:
                    path = args.get("path") or args.get("file_path") or args.get("file")
                    if path:
                        path = str(path)
                        if op == "write":
                            if path not in seen_writes:
                                write_files.append(path)
                                seen_writes.add(path)
                        else:
                            if path not in seen_reads:
                                read_files.append(path)
                                seen_reads.add(path)
                if tool_name == "python":
                    run_file = args.get("run_file")
                    if run_file and run_file not in seen_reads:
                        run_file = str(run_file)
                        if run_file not in seen_reads:
                            read_files.append(run_file)
                            seen_reads.add(run_file)
                    save_to = args.get("save_to")
                    if save_to and save_to not in seen_writes:
                        save_to = str(save_to)
                        if save_to not in seen_writes:
                            write_files.append(save_to)
                            seen_writes.add(save_to)
                if tool_name:
                    result = results[idx] if idx < len(results) else None
                    detail = self._format_tool_detail(tool_name, result)
                    if is_file_tool and path:
                        continue
                    if detail:
                        tool_lines.append(f"{tool_name} ({detail})")
                    else:
                        tool_lines.append(tool_name)
        return tool_lines, read_files, write_files

    def _render_tool_activity(self, tool_lines: List[str]) -> None:
        for tool_name in tool_lines:
            self._print_status_line("tool", tool_name, "cyan")

    def _render_file_activity(self, read_files: List[str], write_files: List[str]) -> None:
        for path in read_files:
            self._print_status_line("file", self._format_clickable_path(path), "green")
        for path in write_files:
            self._print_status_line("file", self._format_clickable_path(path), "magenta")

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
        print(self._banner_rule())
        width = self._get_line_width()
        if self._intro_enabled and self._supports_ansi:
            self._play_ambient_wave(width)
            self._play_scan_bar(width)
            self._play_title_reveal(width)
        else:
            print(self._build_header_line(width))

        print(self._style("SAMA 交互模式  /help 查看命令  /exit 退出", "bold"))
        print(self._style("多行输入: /multiline on  使用 .end 结束", "dim"))
        print(self._style("Tab 补全命令，历史记录保存在 workspace/.sama_history", "dim"))
        print(self._banner_rule())

    def _print_title(self, title: str) -> None:
        print("\n" + self._rule())
        print(title)
        print(self._rule())

    def _build_logo_block(self, dim: bool = False, palette: Optional[List[str]] = None) -> List[str]:
        """
        构建立体Logo文本块
        """
        palette = palette or ["cyan", "blue", "magenta", "blue", "cyan"]
        block = []
        max_width = max(len(line) for line in LOGO)
        for idx, line in enumerate(LOGO):
            color = palette[idx % len(palette)]
            base = line.ljust(max_width)
            if dim:
                block.append(self._style(base, "gray"))
            else:
                block.append(self._style(base, color))
            shadow = " " + base.replace("#", ".")
            block.append(self._style(shadow, "gray"))
        return block

    def _build_sprite_block(self, dim: bool = False) -> List[str]:
        """
        构建精灵文本块
        """
        block = []
        color_map = {
            "#": "green",
            "@": "yellow",
            "*": "magenta",
            ".": "gray",
            "-": "blue",
            "=": "blue",
            "/": "cyan",
            "\\": "cyan",
            "|": "cyan",
            "'": "gray",
        }
        for line in SPRITE:
            if dim:
                block.append(self._style(line, "gray"))
                continue
            colored = []
            for ch in line:
                style = color_map.get(ch)
                if style:
                    colored.append(self._style(ch, style))
                else:
                    colored.append(ch)
            block.append("".join(colored))
        return block

    def _merge_blocks(
        self,
        left: List[str],
        right: List[str],
        gap: int,
        width_limit: int,
        right_offset: int = 0
    ) -> List[str]:
        """
        合并两个文本块，必要时降级为上下排列
        """
        left_width = max(self._visible_len(line) for line in left) if left else 0
        right_width = max(self._visible_len(line) for line in right) if right else 0
        combined_width = left_width + gap + right_width

        if combined_width > width_limit and width_limit > 0:
            return left + [""] + right

        top_shift = -min(0, right_offset)
        left_start = top_shift
        right_start = top_shift + right_offset
        total_height = max(left_start + len(left), right_start + len(right))
        lines = []
        for idx in range(total_height):
            left_line = left[idx - left_start] if left_start <= idx < left_start + len(left) else ""
            right_line = right[idx - right_start] if right_start <= idx < right_start + len(right) else ""
            left_padding = max(0, left_width - self._visible_len(left_line))
            line = left_line + (" " * left_padding)
            if right_line:
                line += (" " * gap) + right_line
            lines.append(line.rstrip())
        return lines

    def _build_header_line(self, width: int, title: str = "SAMA", title_rendered: Optional[str] = None) -> str:
        label_visible = len(title) + 4
        side_len = max(0, (width - label_visible - 2) // 2)
        side = self._repeat_pattern("~", side_len)
        rendered = title_rendered if title_rendered is not None else title
        label = f"[ {rendered} ]"
        line = f"{side} {label} {side}"
        pad = width - self._visible_len(line)
        if pad > 0:
            line += self._repeat_pattern("~", pad)
        return line

    def _format_title(self, title: str, reveal: int) -> str:
        if reveal >= len(title):
            return title
        if not self._use_color:
            return title[:reveal] + ("." * (len(title) - reveal))
        rendered = []
        for idx, ch in enumerate(title):
            if idx < reveal:
                rendered.append(self._style(ch, "cyan"))
            else:
                rendered.append(self._style(ch, "gray"))
        return "".join(rendered)

    def _play_title_reveal(self, width: int) -> None:
        title = "SAMA"
        if not self._supports_ansi:
            print(self._build_header_line(width, title=title))
            return
        for step in range(1, len(title) + 1):
            rendered = self._format_title(title, step)
            frame = self._build_header_line(width, title=title, title_rendered=rendered)
            print("\r" + frame, end="", flush=True)
            time.sleep(0.04)
        print("\r" + self._build_header_line(width, title=title))

    def _banner_rule(self) -> str:
        line = self._repeat_pattern("=-~", self._get_line_width())
        return self._apply_rule_gradient(line, ["cyan", "blue", "magenta"])

    def _repeat_pattern(self, pattern: str, width: int) -> str:
        if not pattern:
            pattern = "-"
        if len(pattern) == 1:
            return pattern * width
        return (pattern * (width // len(pattern) + 1))[:width]

    def _apply_rule_gradient(self, text: str, colors: List[str]) -> str:
        if not self._use_color or not colors:
            return text
        seg = max(6, len(text) // len(colors))
        parts = []
        for idx in range(0, len(text), seg):
            color = colors[(idx // seg) % len(colors)]
            parts.append(self._style(text[idx:idx + seg], color))
        return "".join(parts)

    def _rule(self, char: str = "-") -> str:
        width = self._get_line_width()
        return self._repeat_pattern(char, width)

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
        print("/log [n]              查看最近n行日志")
        print("/anim [style|auto|off] 设置动画样式")
        print("/stream [on|off]       切换流式输出")
        print("\n说明：保留 exit/reset/status/files 等原有命令，不带前缀也可使用。")
        print("      支持 Tab 补全命令，历史记录保存在 workspace/.sama_history。")

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
        self._print_title("文件上下文")
        memory = getattr(self.agent, "memory", None)
        if not memory or not hasattr(memory, "list_files"):
            print(self.agent.get_files_summary())
            return
        files = memory.list_files()
        if not files:
            print("当前无文件 / No files currently")
            return
        print(f"当前文件数量 / Current files: {len(files)}")
        for file_ctx in files:
            size_info = f"({len(file_ctx.content)} chars)" if file_ctx.content else "(no content)"
            abstract = (file_ctx.abstract or "").strip()
            path = self._format_clickable_path(file_ctx.path)
            if abstract:
                print(f"  - {path} {size_info}: {abstract}")
            else:
                print(f"  - {path} {size_info}")

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

    def _cmd_anim(self, args: List[str]) -> None:
        """
        配置动画样式
        """
        if not args:
            styles = ", ".join(AnimatedIndicator.STYLES)
            status = "开启" if self._animation_enabled else "关闭"
            current = self._animation_style
            print(f"动画状态: {status}, 当前样式: {current}")
            print(f"可用样式: {styles}, auto")
            return

        value = args[0].strip().lower()
        if value in {"off", "disable", "0"}:
            self._animation_enabled = False
            print("动画已关闭。")
            return
        if value in {"on", "enable", "1"}:
            self._animation_enabled = self._should_use_animation()
            print("动画已开启。")
            return
        if value == "auto":
            self._animation_style = "auto"
            print("动画样式已设置为 auto。")
            return
        if value in AnimatedIndicator.STYLES:
            self._animation_style = value
            print(f"动画样式已设置为 {value}。")
            return

        styles = ", ".join(AnimatedIndicator.STYLES)
        print(f"未知样式: {value}，可用样式: {styles}, auto")

    def _cmd_stream(self, args: List[str]) -> None:
        """
        切换流式输出
        """
        if not args:
            status = "开启" if self._stream_enabled else "关闭"
            print(f"流式输出: {status}")
            return
        desired = self._parse_bool_arg(args)
        if desired is None:
            print("stream 参数必须为 on/off。")
            return
        self._stream_enabled = desired and self._should_use_streaming()
        status = "开启" if self._stream_enabled else "关闭"
        print(f"流式输出: {status}")

    def _cmd_log(self, args: List[str]) -> None:
        """
        查看日志
        """
        limit = 50
        if args:
            try:
                limit = max(1, int(args[0]))
            except ValueError:
                print("log 参数必须为数字。")
                return

        log_path = Path(self.agent.config.logging.file_path)
        if not log_path.exists():
            print("日志文件不存在。")
            return

        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            print("无法读取日志文件。")
            return

        tail = lines[-limit:] if lines else []
        self._print_title(f"最近 {len(tail)} 行日志")
        for line in tail:
            print(line)

    def _init_readline(self) -> None:
        """
        初始化命令历史与补全
        """
        if not self._readline:
            return
        try:
            self._readline.read_history_file(str(self._history_path))
        except FileNotFoundError:
            pass
        except OSError:
            return

        try:
            self._readline.set_history_length(500)
            self._readline.set_completer(self._complete_input)
            self._readline.parse_and_bind("tab: complete")
        except Exception:
            return

        atexit.register(self._save_history)

    def _save_history(self) -> None:
        """
        保存历史记录
        """
        if not self._readline:
            return
        try:
            self._readline.write_history_file(str(self._history_path))
        except OSError:
            return

    def _complete_input(self, text: str, state: int) -> Optional[str]:
        """
        命令补全
        """
        if not self._readline:
            return None
        buffer = self._readline.get_line_buffer()
        stripped = buffer.lstrip()
        if not stripped.startswith(("/", ":")):
            return None

        prefix = stripped[1:]
        options = [f"/{cmd}" for cmd in sorted(self._commands.keys()) if cmd.startswith(prefix)]
        if state < len(options):
            return options[state]
        return None

    def _should_use_color(self) -> bool:
        """
        判断是否启用颜色
        """
        if os.getenv("NO_COLOR"):
            return False
        return sys.stdout.isatty()

    def _enable_windows_ansi(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                mode_value = mode.value | 0x0004
                kernel32.SetConsoleMode(handle, mode_value)
        except Exception:
            return

    def _should_use_ansi(self) -> bool:
        """
        判断是否启用ANSI控制
        """
        if os.getenv("SAMA_NO_ANSI"):
            return False
        return sys.stdout.isatty()

    def _should_use_streaming(self) -> bool:
        if os.getenv("SAMA_NO_STREAM"):
            return False
        return sys.stdout.isatty()

    def _get_stream_delay(self) -> float:
        value = os.getenv("SAMA_STREAM_DELAY")
        if not value:
            return 0.004
        try:
            return max(0.0, min(0.05, float(value)))
        except ValueError:
            return 0.004

    def _get_stream_line_delay(self) -> float:
        value = os.getenv("SAMA_STREAM_LINE_DELAY")
        if not value:
            return 0.015
        try:
            return max(0.0, min(0.2, float(value)))
        except ValueError:
            return 0.015

    def _get_stream_chunk(self) -> int:
        value = os.getenv("SAMA_STREAM_CHUNK")
        if not value:
            return 3
        try:
            return max(1, min(20, int(value)))
        except ValueError:
            return 3

    def _should_use_manual_input(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._readline:
            return False
        if not self._supports_ansi:
            return False
        if not sys.stdout.isatty():
            return False
        return True

    def _should_use_animation(self) -> bool:
        """
        判断是否启用加载动画
        """
        if not sys.stdout.isatty():
            return False
        if self.agent.config.logging.console_output:
            return False
        return True

    def _get_frame_chars(self) -> dict:
        if os.getenv("SAMA_ASCII_FRAME"):
            return {
                "top_left": "+",
                "top_right": "+",
                "bottom_left": "+",
                "bottom_right": "+",
                "horizontal": "-",
                "vertical": "|",
            }
        return {
            "top_left": "\u256d",
            "top_right": "\u256e",
            "bottom_left": "\u2570",
            "bottom_right": "\u256f",
            "horizontal": "\u2500",
            "vertical": "\u2502",
        }

    def _apply_prompt_style(self) -> None:
        accent = ">" if self._ascii_frame else "\u203a"
        multi_accent = ":" if self._ascii_frame else "\u00b7"
        pad = " " * max(1, self._prompt_pad)
        prompt_text = f"{accent} {self._prompt_label}{self._prompt_suffix}"
        multiline_text = f"{multi_accent} {self._prompt_multiline_label}{self._prompt_multiline_suffix}"
        if self._frame_enabled:
            vert = self._frame_chars["vertical"]
            self.prompt = f"{vert}{pad}{prompt_text}"
            self.prompt_multiline = f"{vert}{pad}{multiline_text}"
        else:
            self.prompt = prompt_text
            self.prompt_multiline = multiline_text
        self._prompt_visible_len = self._visible_len(self.prompt)

    def _should_use_tracker(self) -> bool:
        """
        判断是否启用输入跟随动效
        """
        if os.getenv("SAMA_NO_TRACKER"):
            return False
        if not self._frame_enabled:
            return False
        if not self._supports_ansi:
            return False
        if not sys.stdout.isatty():
            return False
        if not self._readline and not self._manual_input_enabled:
            return False
        return True

    def _get_terminal_columns(self) -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    def _get_cursor_index(self) -> int:
        if self._manual_input_active:
            cursor = max(0, min(self._manual_cursor, len(self._manual_buffer)))
            buffer = "".join(self._manual_buffer)
            return self._display_width(buffer[:cursor])
        if not self._readline:
            return 0
        idx = None
        try:
            getter = getattr(self._readline, "get_point", None)
            if callable(getter):
                value = getter()
                if isinstance(value, int):
                    idx = max(0, value)
        except Exception:
            pass
        try:
            buffer = self._readline.get_line_buffer()
        except Exception:
            return 0
        if idx is None:
            try:
                endidx = self._readline.get_endidx()
                if isinstance(endidx, int) and 0 <= endidx <= len(buffer):
                    idx = endidx
            except Exception:
                idx = None
        if idx is None:
            idx = len(buffer)
        return self._display_width(buffer[:idx])

    def _get_tracker_target(self, width: int) -> Tuple[int, int]:
        prompt_len = getattr(self, "_prompt_visible_len", self._visible_len(self.prompt))
        cursor_idx = self._get_cursor_index()
        if width <= 0:
            width = 1
        absolute = prompt_len + cursor_idx
        column = min(absolute % width, width - 1)
        lines_up = 1 + (absolute // width)
        return column, lines_up

    def _render_tracker_line(self, width: int, pos: int, direction: int) -> str:
        if width <= 1:
            return self._frame_chars["horizontal"] * max(1, width)
        inner_width = width - 2
        inner_pos = max(0, min(inner_width - 1, pos - 1))
        base_char = self._frame_chars["horizontal"]
        base = [base_char] * inner_width

        title_text = self._get_frame_title_text()
        title_positions = set()
        title_start = max(0, min(self._frame_title_offset, inner_width - 1))
        if title_text and len(title_text) < inner_width:
            for offset, ch in enumerate(title_text):
                idx = title_start + offset
                if idx < inner_width:
                    base[idx] = ch
                    title_positions.add(idx)

        shimmer_positions = set()
        shimmer_span = min(self._frame_shimmer_span, inner_width)
        shimmer_pos = (self._tracker_phase * self._frame_shimmer_speed) % inner_width
        for offset in range(shimmer_span):
            idx = (shimmer_pos + offset) % inner_width
            if idx not in title_positions:
                shimmer_positions.add(idx)

        if self._ascii_frame:
            head = "*" if (self._tracker_phase % 10) < 5 else "+"
            tail_chars = [".", ".", ":", "-", "-"]
        else:
            head = "\u25cf" if (self._tracker_phase % 10) < 5 else "\u25c9"
            tail_chars = ["\u25cc", "\u2219", "\u00b7", "\u00b7", "\u00b7", "\u00b7"]
        base[inner_pos] = head
        tail_colors = {}
        tail_positions = set()
        for offset, ch in enumerate(tail_chars, start=1):
            idx = inner_pos + (direction * offset)
            if 0 <= idx < inner_width:
                if idx in title_positions:
                    continue
                base[idx] = ch
                tail_positions.add(idx)
                if offset <= 2:
                    tail_colors[idx] = "cyan"
                elif offset <= 4:
                    tail_colors[idx] = "blue"
                else:
                    tail_colors[idx] = "gray"
            else:
                break

        left = self._frame_chars["top_left"]
        right = self._frame_chars["top_right"]
        if not self._use_color:
            return left + "".join(base) + right
        corner_style = "cyan" if (self._tracker_phase % 12) < 6 else "blue"
        colored = [self._style(left, corner_style)]
        for idx, ch in enumerate(base):
            if idx == inner_pos:
                style = "cyan"
            elif idx in tail_positions:
                style = tail_colors[idx]
            elif idx in title_positions:
                style = "magenta"
            elif idx in shimmer_positions:
                style = "cyan"
            else:
                style = self._frame_base_style(idx, inner_width)
            colored.append(self._style(ch, style))
        colored.append(self._style(right, corner_style))
        return "".join(colored)

    def _draw_tracker_line(
        self,
        line: str,
        lines_up: int,
        width: int,
        right_style: str
    ) -> None:
        if not self._supports_ansi:
            return
        if lines_up < 1:
            lines_up = 1
        with self._tracker_lock:
            sys.stdout.write("\x1b[s")
            sys.stdout.write(f"\x1b[{lines_up}A")
            sys.stdout.write("\r\x1b[2K" + line)
            if width >= 2:
                sys.stdout.write("\x1b[1B")
                sys.stdout.write(f"\x1b[{width}G")
                right_char = self._frame_chars["vertical"]
                if self._use_color:
                    right_char = self._style(right_char, right_style)
                sys.stdout.write(right_char)
            sys.stdout.write("\x1b[u")
            sys.stdout.flush()

    def _print_tracker_anchor(self) -> None:
        width = self._get_terminal_columns()
        print(self._render_tracker_line(width, 1, self._tracker_direction), flush=True)

    def _print_frame_top(self) -> None:
        width = self._get_terminal_columns()
        if self._supports_ansi and self._use_color:
            self._play_frame_shimmer(width)
            return
        print(self._build_frame_border(width, top=True, phase=self._tracker_phase))

    def _finalize_input_frame(self, user_input: str) -> None:
        if not self._frame_enabled or not self._supports_ansi:
            return
        width = self._get_terminal_columns()
        prompt_len = getattr(self, "_prompt_visible_len", self._visible_len(self.prompt))
        total_width = prompt_len + self._display_width(user_input)
        lines = max(1, (total_width + width - 1) // width)
        if width < 2:
            return
        right_char = self._frame_chars["vertical"]
        if self._use_color:
            right_char = self._style(right_char, "blue")
        with self._tracker_lock:
            sys.stdout.write("\x1b[s")
            sys.stdout.write(f"\x1b[{lines}A")
            for _ in range(lines):
                sys.stdout.write("\r")
                sys.stdout.write(f"\x1b[{width}G")
                sys.stdout.write(right_char)
                sys.stdout.write("\x1b[1B")
            sys.stdout.write("\x1b[u")
            sys.stdout.flush()

    def _play_frame_shimmer(self, width: int) -> None:
        inner_width = width - 2
        if inner_width < 6:
            print(self._build_frame_border(width, top=True, phase=self._tracker_phase))
            return
        span = min(self._frame_shimmer_span, inner_width)
        steps = 3
        for step in range(steps):
            pos = (self._tracker_phase + step * (span + 2)) % inner_width
            line = self._build_frame_border(
                width,
                top=True,
                highlight=(pos, span),
                phase=self._tracker_phase + step
            )
            if step == 0:
                sys.stdout.write(line + "\n")
            else:
                sys.stdout.write("\x1b[1A\r\x1b[2K" + line + "\n")
            sys.stdout.flush()
            time.sleep(0.02)

    def _build_frame_border(
        self,
        width: int,
        top: bool,
        highlight: Optional[Tuple[int, int]] = None,
        phase: int = 0,
        title_text: Optional[str] = None,
        title_offset: Optional[int] = None
    ) -> str:
        if width <= 0:
            return ""
        if width == 1:
            return self._frame_chars["horizontal"]
        inner_width = width - 2
        left = self._frame_chars["top_left"] if top else self._frame_chars["bottom_left"]
        right = self._frame_chars["top_right"] if top else self._frame_chars["bottom_right"]
        base_char = self._frame_chars["horizontal"]
        inner = [base_char] * inner_width
        title_positions = set()
        if top:
            if title_text is None:
                title_text = self._get_frame_title_text()
            offset = self._frame_title_offset if title_offset is None else title_offset
            if title_text and len(title_text) < inner_width:
                start = max(0, min(offset, inner_width - 1))
                for offset, ch in enumerate(title_text):
                    idx = start + offset
                    if idx < inner_width:
                        inner[idx] = ch
                        title_positions.add(idx)
        highlight_positions = set()
        if highlight:
            start, span = highlight
            span = max(1, min(span, inner_width))
            for idx in range(span):
                pos = (start + idx) % inner_width
                highlight_positions.add(pos)
        if not self._use_color:
            return left + "".join(inner) + right
        corner_style = "cyan" if (phase % 12) < 6 else "blue"
        colored = [self._style(left, corner_style)]
        for idx, ch in enumerate(inner):
            if idx in title_positions:
                style = "magenta"
            elif idx in highlight_positions:
                style = "cyan"
            else:
                style = self._frame_base_style(idx, inner_width)
            colored.append(self._style(ch, style))
        colored.append(self._style(right, corner_style))
        return "".join(colored)

    def _play_bottom_ripple(self, width: int) -> None:
        if not self._frame_enabled or not self._supports_ansi or not self._use_color:
            return
        inner_width = width - 2
        if inner_width < 8:
            return
        span = min(self._frame_ripple_span, max(6, inner_width // 4))
        start = (self._tracker_phase * 3) % inner_width
        for step in range(3):
            pos = (start + step * (span // 2 + 1)) % inner_width
            line = self._build_frame_border(
                width,
                top=False,
                highlight=(pos, span),
                phase=self._tracker_phase + step
            )
            sys.stdout.write("\x1b[s")
            sys.stdout.write("\x1b[1A\r\x1b[2K" + line)
            sys.stdout.write("\x1b[u")
            sys.stdout.flush()
            time.sleep(0.015)

    def _print_input_frame_bottom(self) -> None:
        if not self._frame_enabled:
            return
        width = self._get_terminal_columns()
        print(self._build_frame_border(width, top=False, phase=self._tracker_phase))
        self._play_bottom_ripple(width)

    def _build_output_border(
        self,
        width: int,
        top: bool,
        highlight: Optional[Tuple[int, int]] = None,
        phase: int = 0
    ) -> str:
        title_text = self._get_output_title_text() if top else ""
        return self._build_frame_border(
            width,
            top,
            highlight=highlight,
            phase=phase,
            title_text=title_text,
            title_offset=self._output_title_offset
        )

    def _get_frame_title_text(self) -> str:
        if not self._frame_title:
            return ""
        marker = "*" if self._ascii_frame else "\u25cf"
        sep = "/" if self._ascii_frame else "\u00b7"
        title = self._frame_title
        suffix = self._frame_title_suffix
        if suffix:
            return f" {marker} {title} {sep} {suffix} "
        return f" {marker} {title} "

    def _get_output_title_text(self) -> str:
        if not self._output_title:
            return ""
        marker = "*" if self._ascii_frame else "\u25cf"
        sep = "/" if self._ascii_frame else "\u00b7"
        title = self._output_title
        suffix = self._output_title_suffix
        if suffix:
            return f" {marker} {title} {sep} {suffix} "
        return f" {marker} {title} "

    def _frame_base_style(self, idx: int, inner_width: int) -> str:
        if inner_width <= 0:
            return "blue"
        band = max(1, inner_width // 3)
        if idx < band:
            return "blue"
        if idx < band * 2:
            return "cyan"
        return "blue"

    def _start_tracker(self) -> None:
        if not self._tracker_enabled:
            return
        if self._tracker_thread and self._tracker_thread.is_alive():
            return
        self._tracker_stop.clear()
        self._tracker_current_x = 0.0
        self._tracker_phase = 0
        self._tracker_thread = threading.Thread(target=self._run_tracker, daemon=True)
        self._tracker_thread.start()

    def _stop_tracker(self) -> None:
        if not self._tracker_thread:
            return
        self._tracker_stop.set()
        self._tracker_thread.join(timeout=0.2)
        self._tracker_thread = None

    def _run_tracker(self) -> None:
        while not self._tracker_stop.is_set():
            width = self._get_terminal_columns()
            column, lines_up = self._get_tracker_target(width)
            prev_x = self._tracker_current_x
            self._tracker_current_x += (column - self._tracker_current_x) * 0.35
            delta = self._tracker_current_x - prev_x
            if abs(delta) > 0.01:
                self._tracker_direction = -1 if delta > 0 else 1
            pos = int(round(self._tracker_current_x))
            line = self._render_tracker_line(width, pos, self._tracker_direction)
            inner_width = max(1, width - 2)
            inner_pos = max(0, min(inner_width - 1, pos - 1))
            distance = inner_width - 1 - inner_pos
            if distance <= 1:
                right_style = "cyan"
            elif distance <= self._frame_glow_span:
                right_style = "blue"
            else:
                right_style = "blue"
            self._draw_tracker_line(line, lines_up, width, right_style)
            self._tracker_phase += 1
            time.sleep(self._tracker_interval)

    def _resolve_animation_style(self) -> str:
        """
        获取当前动画样式
        """
        if self._animation_style != "auto":
            return self._animation_style
        style = AnimatedIndicator.STYLES[self._animation_index % len(AnimatedIndicator.STYLES)]
        self._animation_index += 1
        return style

    def _style(self, text: str, style: str) -> str:
        """
        简单样式输出
        """
        if not self._use_color:
            return text
        styles = {
            "bold": "\x1b[1m",
            "dim": "\x1b[2m",
            "error": "\x1b[31m",
            "cyan": "\x1b[36m",
            "blue": "\x1b[34m",
            "magenta": "\x1b[35m",
            "green": "\x1b[32m",
            "yellow": "\x1b[33m",
            "gray": "\x1b[90m",
        }
        prefix = styles.get(style)
        if not prefix:
            return text
        return f"{prefix}{text}\x1b[0m"

    def _strip_ansi(self, text: str) -> str:
        """
        清除ANSI颜色码
        """
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    def _char_width(self, ch: str) -> int:
        if ch == "\t":
            return 4
        if unicodedata.combining(ch):
            return 0
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            return 2
        return 1

    def _display_width(self, text: str) -> int:
        stripped = self._strip_ansi(text)
        width = 0
        for ch in stripped:
            width += self._char_width(ch)
        return width

    def _clip_to_width(self, text: str, width: int) -> str:
        if width <= 0:
            return ""
        result = []
        used = 0
        for ch in text:
            w = self._char_width(ch)
            if used + w > width:
                break
            result.append(ch)
            used += w
        return "".join(result)

    def _visible_len(self, text: str) -> int:
        """
        获取可见长度
        """
        return self._display_width(text)

    def _play_scan_bar(self, width: int) -> None:
        """
        入场扫描条
        """
        bar_width = min(28, max(14, width // 4))
        frames = []
        for i in range(bar_width + 1):
            inner = [" "] * bar_width
            if i > 0:
                for j in range(i - 1):
                    inner[j] = "="
                inner[i - 1] = ">"
            frames.append("[" + "".join(inner) + "]")
        for i in range(bar_width - 1, 0, -1):
            inner = [" "] * bar_width
            for j in range(i, bar_width):
                inner[j] = "="
            inner[i - 1] = "<"
            frames.append("[" + "".join(inner) + "]")
        colors = ["cyan", "blue", "magenta"]
        for idx, frame in enumerate(frames):
            if self._use_color:
                text = self._style(frame, colors[idx % len(colors)])
            else:
                text = frame
            print("\r" + text, end="", flush=True)
            time.sleep(0.01)
        print("\r" + (" " * (bar_width + 2)) + "\r", end="", flush=True)

    def _play_ambient_wave(self, width: int) -> None:
        """
        Ambient wave animation
        """
        if not self._supports_ansi:
            return
        height = 3
        patterns = [" .-~^~-. ", "  .:*:*.  ", " .-~^~-. "]
        colors = ["cyan", "blue", "magenta"]
        frames = 18
        for frame in range(frames):
            lines = []
            for idx in range(height):
                speed = idx + 2
                line = self._build_wave_line(width, frame * speed, patterns[idx % len(patterns)])
                if self._use_color:
                    line = self._style(line, colors[idx % len(colors)])
                lines.append(line)
            if frame == 0:
                for line in lines:
                    print(line)
            else:
                print(f"\x1b[{height}A", end="")
                for line in lines:
                    print("\x1b[2K" + line)
            time.sleep(0.02)
        print(f"\x1b[{height}A", end="")
        for _ in range(height):
            print("\x1b[2K")

    def _build_wave_line(self, width: int, offset: int, pattern: str) -> str:
        if not pattern:
            return " " * width
        return "".join(pattern[(i + offset) % len(pattern)] for i in range(width))

    def _play_logo_glow(
        self,
        sprite_block: List[str],
        width: int,
        height: int,
        base_offset: int
    ) -> None:
        """
        Logo glow pulse
        """
        if not self._supports_ansi:
            return
        palettes = [
            ["cyan", "blue", "magenta", "blue", "cyan"],
            ["magenta", "cyan", "blue", "cyan", "magenta"],
            ["blue", "magenta", "cyan", "magenta", "blue"],
        ]
        for palette in palettes:
            logo_block = self._build_logo_block(palette=palette)
            frame = self._merge_blocks(
                logo_block,
                sprite_block,
                gap=4,
                width_limit=width,
                right_offset=base_offset
            )
            self._redraw_block(frame, height)
            time.sleep(0.04)

    def _redraw_block(self, lines: List[str], height: int) -> None:
        """
        使用ANSI重绘文本块
        """
        if not self._supports_ansi:
            for line in lines:
                print(line)
            return
        print(f"\x1b[{height}A", end="")
        for line in lines:
            print("\x1b[2K" + line)
        sys.stdout.flush()

    def _play_sprite_jump(
        self,
        logo_block: List[str],
        sprite_block: List[str],
        width: int,
        height: int,
        base_offset: int
    ) -> None:
        """
        精灵跳动动画
        """
        offsets = [0, -1, -2, -1, 0]
        for offset in offsets:
            frame = self._merge_blocks(
                logo_block,
                sprite_block,
                gap=4,
                width_limit=width,
                right_offset=base_offset + offset
            )
            self._redraw_block(frame, height)
            time.sleep(0.05)

    def _has_valid_api_key(self) -> bool:
        key = (self.agent.config.model.api_key or "").strip()
        return bool(key and key != "your-api-key-here")

    def _print_missing_key_hint(self) -> None:
        if self._missing_key_warned:
            print(self._style("未检测到有效的 API Key，请先配置后再试。", "error"))
            return
        self._missing_key_warned = True
        print(self._style("assistant:", "bold"))
        print("未检测到有效的 API Key。")
        print("建议在 config.local.yaml 中配置：")
        print("model:")
        print("  api_key: \"your-real-api-key\"")


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
    
    # 检查配置 / Check configuration
    config = get_config()
    if not args.verbose:
        config.logging.console_output = False

    # 初始化日志 / Initialize logging
    init_logging()
    logger = get_logger("main")
    if not config.model.api_key or config.model.api_key == "your-api-key-here":
        if args.query or args.verbose:
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
        if args.query:
            show_thinking = args.verbose or config.agent.verbose
        else:
            show_thinking = args.verbose
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
