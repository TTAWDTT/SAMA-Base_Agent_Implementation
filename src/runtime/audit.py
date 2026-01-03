# ==============================================================================
# 审计日志
# ==============================================================================

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def append_audit_event(
    event: Dict[str, Any],
    file_path: str,
    redact_fn: Optional[callable] = None
) -> None:
    """
    写入审计事件
    """
    payload = dict(event or {})
    payload["timestamp"] = payload.get("timestamp") or datetime.now().isoformat()
    if redact_fn:
        payload = redact_fn(payload)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
