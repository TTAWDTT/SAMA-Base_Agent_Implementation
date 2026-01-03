# ==============================================================================
# 命令路由
# ==============================================================================

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class CommandRouter:
    handlers: Dict[str, Callable[[List[str]], None]]
    aliases: Dict[str, str] = field(default_factory=dict)
    legacy_commands: List[str] = field(default_factory=list)
    on_unknown: Optional[Callable[[str], None]] = None
    on_parse_error: Optional[Callable[[], None]] = None

    def dispatch(self, user_input: str) -> bool:
        cmd, args = self._parse_command(user_input)
        if not cmd:
            return False
        if cmd == "__invalid__":
            return True
        handler = self.handlers.get(cmd)
        if not handler:
            if self.on_unknown:
                self.on_unknown(cmd)
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
                if self.on_parse_error:
                    self.on_parse_error()
                return "__invalid__", []
            cmd = self._normalize_command(parts[0])
            return cmd, parts[1:]

        if raw in self.legacy_commands or raw.lower() in self.legacy_commands:
            try:
                parts = shlex.split(raw)
            except ValueError:
                if self.on_parse_error:
                    self.on_parse_error()
                return "__invalid__", []
            cmd = self._normalize_command(parts[0])
            return cmd, parts[1:]

        return None, []

    def _normalize_command(self, cmd: str) -> str:
        if cmd in self.aliases:
            return self.aliases[cmd]
        lower_cmd = cmd.lower()
        return self.aliases.get(lower_cmd, lower_cmd)
