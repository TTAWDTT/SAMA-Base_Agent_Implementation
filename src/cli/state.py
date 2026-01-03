# ==============================================================================
# 会话状态
# ==============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SessionState:
    multiline: bool = False
    history: List[Dict[str, str]] = field(default_factory=list)
    exit_requested: bool = False
    manual_input_active: bool = False
    manual_buffer: List[str] = field(default_factory=list)
    manual_cursor: int = 0
    manual_render_lines: int = 1
    manual_cursor_display: Optional[str] = None
    input_history: List[str] = field(default_factory=list)
    input_history_idx: Optional[int] = None
