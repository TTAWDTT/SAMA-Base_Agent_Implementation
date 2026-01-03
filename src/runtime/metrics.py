# ==============================================================================
# 工具指标统计
# ==============================================================================

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.schema import ToolResultStatus


def build_tool_metrics(response: Any) -> Dict[str, Any]:
    """
    从响应中构建工具指标
    """
    summary = {
        "total_calls": 0,
        "success": 0,
        "error": 0,
        "timeout": 0,
        "total_time": 0.0,
    }
    tools: Dict[str, Dict[str, Any]] = {}
    steps = getattr(response, "steps", None) or []

    for step in steps:
        tool_results = getattr(step, "tool_results", None) or []
        for result in tool_results:
            tool_name = getattr(result, "tool_name", None) or "unknown"
            status = getattr(result, "status", None)
            exec_time = float(getattr(result, "execution_time", 0.0) or 0.0)
            error_message = getattr(result, "error_message", None)

            entry = tools.setdefault(
                tool_name,
                {
                    "calls": 0,
                    "success": 0,
                    "error": 0,
                    "timeout": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                    "error_rate": 0.0,
                    "last_status": None,
                    "last_error": None,
                }
            )

            entry["calls"] += 1
            entry["total_time"] += exec_time
            summary["total_calls"] += 1
            summary["total_time"] += exec_time

            if status == ToolResultStatus.SUCCESS:
                entry["success"] += 1
                summary["success"] += 1
            elif status == ToolResultStatus.TIMEOUT:
                entry["timeout"] += 1
                summary["timeout"] += 1
            else:
                entry["error"] += 1
                summary["error"] += 1

            entry["last_status"] = _status_name(status)
            if error_message:
                entry["last_error"] = str(error_message)

    for entry in tools.values():
        calls = entry["calls"]
        entry["avg_time"] = entry["total_time"] / calls if calls else 0.0
        entry["error_rate"] = (entry["error"] + entry["timeout"]) / calls if calls else 0.0

    summary["avg_time"] = summary["total_time"] / summary["total_calls"] if summary["total_calls"] else 0.0
    summary["error_rate"] = (
        (summary["error"] + summary["timeout"]) / summary["total_calls"]
        if summary["total_calls"] else 0.0
    )

    return {
        "summary": summary,
        "tools": tools,
    }


def update_tool_metrics_store(
    task_metrics: Dict[str, Any],
    metrics_path: str,
    csv_path: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    更新全局工具指标
    """
    store = _load_metrics(metrics_path)
    _merge_metrics(store, task_metrics, task_id=task_id)
    _write_json(Path(metrics_path), store)
    if csv_path:
        _write_metrics_csv(Path(csv_path), store)
    return store


def _status_name(status: Any) -> Optional[str]:
    if status is None:
        return None
    if isinstance(status, ToolResultStatus):
        return status.value
    return str(status)


def _load_metrics(metrics_path: str) -> Dict[str, Any]:
    path = Path(metrics_path)
    if not path.exists():
        return _empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _normalize_store(data)
    except Exception:
        return _empty_store()
    return _empty_store()


def _empty_store() -> Dict[str, Any]:
    return {
        "summary": {
            "tasks": 0,
            "total_calls": 0,
            "success": 0,
            "error": 0,
            "timeout": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "error_rate": 0.0,
            "last_updated": None,
            "last_task_id": None,
        },
        "tools": {},
    }


def _normalize_store(store: Dict[str, Any]) -> Dict[str, Any]:
    if "summary" not in store or "tools" not in store:
        return _empty_store()
    return store


def _merge_metrics(store: Dict[str, Any], task_metrics: Dict[str, Any], task_id: Optional[str]) -> None:
    summary = store.setdefault("summary", {})
    tools = store.setdefault("tools", {})

    task_summary = task_metrics.get("summary") or {}
    task_tools = task_metrics.get("tools") or {}

    summary["tasks"] = int(summary.get("tasks", 0)) + 1
    summary["total_calls"] = int(summary.get("total_calls", 0)) + int(task_summary.get("total_calls", 0))
    summary["success"] = int(summary.get("success", 0)) + int(task_summary.get("success", 0))
    summary["error"] = int(summary.get("error", 0)) + int(task_summary.get("error", 0))
    summary["timeout"] = int(summary.get("timeout", 0)) + int(task_summary.get("timeout", 0))
    summary["total_time"] = float(summary.get("total_time", 0.0)) + float(task_summary.get("total_time", 0.0))

    total_calls = summary.get("total_calls", 0)
    summary["avg_time"] = summary["total_time"] / total_calls if total_calls else 0.0
    summary["error_rate"] = (
        (summary.get("error", 0) + summary.get("timeout", 0)) / total_calls
        if total_calls else 0.0
    )
    summary["last_updated"] = datetime.now().isoformat()
    summary["last_task_id"] = task_id

    for tool_name, data in task_tools.items():
        entry = tools.setdefault(
            tool_name,
            {
                "calls": 0,
                "success": 0,
                "error": 0,
                "timeout": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "error_rate": 0.0,
                "last_status": None,
                "last_error": None,
                "last_used": None,
            }
        )

        entry["calls"] += int(data.get("calls", 0))
        entry["success"] += int(data.get("success", 0))
        entry["error"] += int(data.get("error", 0))
        entry["timeout"] += int(data.get("timeout", 0))
        entry["total_time"] += float(data.get("total_time", 0.0))
        entry["last_status"] = data.get("last_status")
        if data.get("last_error"):
            entry["last_error"] = data.get("last_error")
        entry["last_used"] = summary.get("last_updated")

        calls = entry["calls"]
        entry["avg_time"] = entry["total_time"] / calls if calls else 0.0
        entry["error_rate"] = (entry["error"] + entry["timeout"]) / calls if calls else 0.0


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_metrics_csv(path: Path, store: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "tool",
            "calls",
            "success",
            "error",
            "timeout",
            "total_time",
            "avg_time",
            "error_rate",
            "last_status",
            "last_error",
            "last_used",
        ])
        for tool_name, entry in sorted(store.get("tools", {}).items()):
            writer.writerow([
                tool_name,
                entry.get("calls", 0),
                entry.get("success", 0),
                entry.get("error", 0),
                entry.get("timeout", 0),
                f"{entry.get('total_time', 0.0):.4f}",
                f"{entry.get('avg_time', 0.0):.4f}",
                f"{entry.get('error_rate', 0.0):.4f}",
                entry.get("last_status") or "",
                entry.get("last_error") or "",
                entry.get("last_used") or "",
            ])
