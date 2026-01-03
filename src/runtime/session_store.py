# ==============================================================================
# 会话持久化
# ==============================================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def save_session_snapshot(session_id: str, snapshot: Dict[str, Any], base_dir: str) -> str:
    """
    保存会话快照
    """
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    target = base_path / f"{session_id}.json"
    payload = dict(snapshot or {})
    payload["session_id"] = session_id
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def load_session_snapshot(session_id: str, base_dir: str) -> Optional[Dict[str, Any]]:
    """
    读取会话快照
    """
    if not session_id:
        return None
    target = Path(base_dir) / f"{session_id}.json"
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None
