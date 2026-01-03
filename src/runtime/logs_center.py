from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_combined_logs(paths: Dict[str, str], limit: int = 200) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    entries.extend(_load_jsonl(paths.get("audit"), "audit"))
    entries.extend(_load_jsonl(paths.get("webhook"), "webhook"))
    entries.extend(_load_jsonl(paths.get("reminder"), "reminder"))
    entries.extend(_load_jsonl(paths.get("tasks"), "task"))
    entries.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    if limit > 0:
        entries = entries[:limit]
    return {"entries": entries, "total": len(entries)}


def _load_jsonl(path: str, source: str) -> List[Dict[str, Any]]:
    if not path:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    items = []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                data.setdefault("source", source)
                items.append(data)
        except Exception:
            items.append({"source": source, "raw": line})
    return items
