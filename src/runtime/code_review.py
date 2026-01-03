from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def review_paths(paths: List[str]) -> Dict[str, Any]:
    issues = []
    for raw in paths:
        path = Path(raw)
        if not path.exists() or not path.is_file():
            issues.append({"path": str(path), "error": "file_not_found"})
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            issues.append({"path": str(path), "error": str(exc)})
            continue
        issues.extend(_scan_text(text, str(path)))
    return {"issues": issues, "total": len(issues)}


def review_text(text: str, name: Optional[str] = None) -> Dict[str, Any]:
    issues = _scan_text(text or "", name or "snippet")
    return {"issues": issues, "total": len(issues)}


def _scan_text(text: str, path: str) -> List[Dict[str, Any]]:
    lines = text.splitlines()
    issues: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        if "TODO" in line or "FIXME" in line:
            issues.append({"path": path, "line": idx, "type": "todo", "detail": line.strip()})
        if line.rstrip("\n") != line.rstrip():
            issues.append({"path": path, "line": idx, "type": "trailing_whitespace", "detail": ""})
        if len(line) > 140:
            issues.append({"path": path, "line": idx, "type": "long_line", "detail": str(len(line))})
        if "eval(" in line or "exec(" in line:
            issues.append({"path": path, "line": idx, "type": "dangerous_call", "detail": line.strip()})
    if len(lines) > 1200:
        issues.append({"path": path, "line": None, "type": "large_file", "detail": str(len(lines))})
    return issues
