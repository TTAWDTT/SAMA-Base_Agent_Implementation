# ==============================================================================
# 运行产物
# ==============================================================================

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def save_task_result(
    task_id: str,
    prompt: str,
    response: Any,
    processed_files: Optional[Dict[str, Any]] = None,
    output_dir: str = "outputs",
    print_result: bool = True,
    record_history: bool = True,
    record_index: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    context_snapshot: Optional[Dict[str, Any]] = None,
    tool_metrics: Optional[Dict[str, Any]] = None,
    version_tag: Optional[str] = None
) -> str:
    """
    保存任务结果产物
    """
    output_path = Path(output_dir) / task_id
    output_path.mkdir(parents=True, exist_ok=True)

    version_tag = version_tag or datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "version_tag": version_tag,
        "prompt": prompt,
        "success": getattr(response, "success", False),
        "final_answer": getattr(response, "final_answer", str(response)),
        "total_iterations": getattr(response, "total_iterations", 0),
        "execution_time": getattr(response, "execution_time", 0),
        "error_message": getattr(response, "error_message", None),
    }

    if processed_files:
        result["processed_files"] = {
            "file_count": processed_files.get("file_count", 0),
            "image_count": processed_files.get("image_count", 0),
            "files": processed_files.get("files", []),
        }

    result_path = output_path / "result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    answer_path = output_path / "answer.txt"
    answer_path.write_text(result["final_answer"], encoding="utf-8")

    context_path = None
    if context_snapshot is not None:
        context_path = output_path / "context_snapshot.json"
        context_path.write_text(
            json.dumps(context_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    metrics_path = None
    metrics_summary = None
    if tool_metrics is not None:
        metrics_path = output_path / "tool_metrics.json"
        metrics_path.write_text(
            json.dumps(tool_metrics, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        metrics_summary = tool_metrics.get("summary") if isinstance(tool_metrics, dict) else None
        if metrics_summary:
            result["tool_metrics_summary"] = metrics_summary

    record = _build_task_record(
        result,
        output_path,
        metadata or {},
        context_path=str(context_path) if context_path else None,
        tool_metrics_summary=metrics_summary
    )
    if record_history:
        append_task_history(record, output_dir=output_dir)
    if record_index:
        append_task_index(record, output_dir=output_dir)

    if print_result:
        print(f"结果已保存到: {output_path}")

    return str(output_path)


def append_task_history(record: Dict[str, Any], output_dir: str = "outputs") -> None:
    """
    追加任务记录到 JSONL 历史文件
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    history_path = output_path / "task_history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_task_index(record: Dict[str, Any], output_dir: str = "outputs") -> None:
    """
    追加任务记录到 JSON 索引
    """
    index_path = Path(output_dir) / "task_index.json"
    entries = _load_task_index(index_path)
    entries.append(record)
    _write_task_index(index_path, entries)


def update_task_artifact_index(task_id: str, output_dir: str = "outputs") -> None:
    """
    刷新索引中任务的产物列表
    """
    index_path = Path(output_dir) / "task_index.json"
    entries = _load_task_index(index_path)
    if not entries:
        return

    updated = False
    output_path = Path(output_dir) / task_id
    artifacts = _list_artifacts(output_path)
    for entry in reversed(entries):
        if entry.get("task_id") == task_id:
            entry["artifacts"] = artifacts
            updated = True
            break
    if updated:
        _write_task_index(index_path, entries)


def load_task_index(output_dir: str = "outputs") -> List[Dict[str, Any]]:
    """
    读取任务索引
    """
    index_path = Path(output_dir) / "task_index.json"
    return _load_task_index(index_path)


def get_task_record(task_id: str, output_dir: str = "outputs") -> Optional[Dict[str, Any]]:
    """
    获取指定任务记录
    """
    if not task_id:
        return None
    entries = load_task_index(output_dir=output_dir)
    for entry in reversed(entries):
        if entry.get("task_id") == task_id:
            return entry
    return None


def list_task_artifacts(task_id: str, output_dir: str = "outputs") -> List[str]:
    """
    获取任务产物列表
    """
    if not task_id:
        return []
    output_path = Path(output_dir) / task_id
    return _list_artifacts(output_path)


def search_task_records(
    query: str,
    output_dir: str = "outputs",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    检索任务记录
    """
    records = load_task_index(output_dir=output_dir)
    query_lower = (query or "").lower()
    results = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        if not _record_match(entry, query_lower, filters or {}):
            continue
        results.append(entry)
    results.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return results[:limit]


def diff_text_files(
    left_path: Path,
    right_path: Path,
    max_lines: int = 400
) -> List[str]:
    """
    生成文本文件差异
    """
    import difflib
    left_text = left_path.read_text(encoding="utf-8", errors="replace").splitlines()
    right_text = right_path.read_text(encoding="utf-8", errors="replace").splitlines()
    diff = difflib.unified_diff(
        left_text,
        right_text,
        fromfile=left_path.name,
        tofile=right_path.name,
        lineterm="",
    )
    return list(diff)[:max_lines]


def snapshot_top_level_files(path: Path) -> Set[str]:
    """
    获取目录顶层文件快照（不递归子目录）
    """
    files: Set[str] = set()
    try:
        if not path.exists() or not path.is_dir():
            return files
        for entry in path.iterdir():
            try:
                if entry.is_file():
                    files.add(entry.name)
            except Exception:
                continue
    except Exception:
        return set()
    return files


def move_top_level_files_to_output(
    source_dir: Path,
    new_files: Set[str],
    task_id: str,
    root: Path,
    source_label: str,
    output_dir: str = "outputs"
) -> None:
    """
    将新增的顶层文件移动到输出目录
    """
    out_base = Path(root) / output_dir / task_id
    out_base.mkdir(parents=True, exist_ok=True)
    prefix = f"{source_label}/" if source_label else ""

    for name in sorted(new_files):
        src = source_dir / name
        if not src.exists() or not src.is_file():
            continue
        dest = out_base / name
        try:
            shutil.move(str(src), str(dest))
            print(f"   已移动 {prefix}{name} -> {dest}")
        except Exception as exc:
            print(f"   移动失败 {prefix}{name}: {exc}")


def _build_task_record(
    result: Dict[str, Any],
    output_path: Path,
    metadata: Dict[str, Any],
    context_path: Optional[str] = None,
    tool_metrics_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    record = {
        "task_id": result.get("task_id"),
        "timestamp": result.get("timestamp"),
        "version_tag": result.get("version_tag"),
        "success": result.get("success"),
        "prompt": result.get("prompt"),
        "final_answer": result.get("final_answer"),
        "output_dir": str(output_path),
        "artifacts": _list_artifacts(output_path),
        "metadata": metadata,
    }
    if context_path:
        record["context_snapshot"] = context_path
    if tool_metrics_summary:
        record["tool_metrics_summary"] = tool_metrics_summary
    return record


def _list_artifacts(output_path: Path) -> List[str]:
    if not output_path.exists():
        return []
    artifacts = []
    for entry in output_path.iterdir():
        try:
            if entry.is_file():
                artifacts.append(entry.name)
        except Exception:
            continue
    artifacts.sort()
    return artifacts


def _load_task_index(index_path: Path) -> List[Dict[str, Any]]:
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _write_task_index(index_path: Path, entries: List[Dict[str, Any]]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_match(entry: Dict[str, Any], query_lower: str, filters: Dict[str, Any]) -> bool:
    if query_lower:
        hay = " ".join([
            str(entry.get("prompt") or ""),
            str(entry.get("final_answer") or ""),
            json.dumps(entry.get("metadata", {}), ensure_ascii=False),
        ]).lower()
        if query_lower not in hay:
            return False
    success = filters.get("success")
    if success is not None:
        if bool(entry.get("success")) != bool(success):
            return False
    source = filters.get("source")
    if source:
        meta_source = (entry.get("metadata") or {}).get("source")
        if meta_source != source:
            return False
    tag = filters.get("tag")
    if tag:
        tags = (entry.get("metadata") or {}).get("tags") or []
        if tag not in tags:
            return False
    date_from = filters.get("from")
    date_to = filters.get("to")
    ts = entry.get("timestamp")
    if ts:
        if date_from and ts < date_from:
            return False
        if date_to and ts > date_to:
            return False
    return True


def create_task_archive(
    task_id: str,
    output_dir: str = "outputs",
    archive_dir: str = "outputs/archives"
) -> Optional[str]:
    """
    将任务产物打包为zip
    """
    output_path = Path(output_dir) / task_id
    if not output_path.exists() or not output_path.is_dir():
        return None

    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = archive_path / f"{task_id}_{timestamp}"
    zip_path = shutil.make_archive(str(base_name), "zip", root_dir=str(output_path))
    return zip_path


def cleanup_task_outputs(
    output_dir: str = "outputs",
    keep_recent: int = 50,
    max_age_days: Optional[int] = None,
    keep_failed: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    清理历史任务产物
    """
    output_path = Path(output_dir)
    index_path = output_path / "task_index.json"
    entries = _load_task_index(index_path)
    if not entries:
        return {"removed": [], "kept": [], "errors": []}

    now = datetime.now()
    sorted_entries = sorted(entries, key=lambda item: item.get("timestamp", ""), reverse=True)
    keep_ids = set()

    if keep_recent > 0:
        keep_ids.update([item.get("task_id") for item in sorted_entries[:keep_recent]])

    if max_age_days is not None and max_age_days > 0:
        cutoff = now.timestamp() - max_age_days * 86400
        for item in sorted_entries:
            ts = _parse_timestamp(item.get("timestamp"))
            if ts and ts.timestamp() >= cutoff:
                keep_ids.add(item.get("task_id"))

    if keep_failed:
        for item in sorted_entries:
            if item.get("success") is False:
                keep_ids.add(item.get("task_id"))

    removed = []
    kept = []
    errors = []
    retained_entries = []

    for item in sorted_entries:
        task_id = item.get("task_id")
        if not task_id:
            continue
        if task_id in keep_ids:
            kept.append(task_id)
            retained_entries.append(item)
            continue
        target = output_path / task_id
        try:
            if not dry_run and target.exists() and target.is_dir():
                shutil.rmtree(target)
            removed.append(task_id)
        except Exception as exc:
            errors.append(f"{task_id}: {exc}")
            retained_entries.append(item)

    if not dry_run:
        _write_task_index(index_path, retained_entries)

    return {
        "removed": removed,
        "kept": kept,
        "errors": errors,
    }


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None
