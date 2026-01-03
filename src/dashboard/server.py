# ==============================================================================
# 本地任务仪表盘
# ==============================================================================

from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from src.core.logger import get_logger

logger = get_logger("dashboard")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/markdown", ".mmd")


def run_dashboard(
    output_dir: str = "outputs",
    host: str = "127.0.0.1",
    port: int = 8765,
    title: str = "SAMA Dashboard",
    static_dir: Optional[str] = None,
    background: bool = False,
    auto_open: bool = False,
    max_port_tries: int = 10,
    quiet: bool = False
) -> ThreadingHTTPServer:
    """
    启动仪表盘服务
    """
    handler = _build_handler(
        output_dir=Path(output_dir),
        title=title,
        static_dir=Path(static_dir) if static_dir else _default_static_dir()
    )
    server = _create_server(host, port, handler, max_port_tries=max_port_tries)
    actual_port = server.server_address[1]
    display_host = _resolve_display_host(host)
    url = _build_url(display_host, actual_port)
    server.dashboard_url = url
    server.display_host = display_host
    server.display_port = actual_port

    if port != 0 and actual_port != port:
        message = f"端口 {port} 被占用，已切换到 {actual_port}"
        if not quiet:
            print(message)
        logger.warning(message)

    if not quiet:
        print(f"仪表盘已启动: {url}")
    logger.info(f"仪表盘已启动: {url}")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    else:
        server.serve_forever()
    return server


def _default_static_dir() -> Path:
    return Path(__file__).parent / "assets"


def _resolve_display_host(host: str) -> str:
    if not host or host in {"0.0.0.0", "::"}:
        return "localhost" if host == "::" else "127.0.0.1"
    return host


def _build_url(host: str, port: int) -> str:
    display = host
    if ":" in host and not host.startswith("["):
        display = f"[{host}]"
    return f"http://{display}:{port}"


def _create_server(host: str, port: int, handler, max_port_tries: int = 10) -> ThreadingHTTPServer:
    if max_port_tries < 1:
        max_port_tries = 1
    last_error: Optional[Exception] = None
    for offset in range(max_port_tries):
        try_port = 0 if port == 0 else port + offset
        try:
            return ThreadingHTTPServer((host, try_port), handler)
        except OSError as exc:
            last_error = exc
            if port == 0:
                break
    if last_error:
        raise last_error
    raise OSError("无法启动仪表盘服务")


def _build_handler(output_dir: Path, title: str, static_dir: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/" or path == "/index.html":
                return self._send_static_file("index.html", static_dir)
            if path.startswith("/assets/"):
                return self._send_static_file(path[len("/assets/"):], static_dir)
            if path == "/api/index":
                return self._send_json(_load_task_index(output_dir))
            if path == "/api/history":
                return self._send_json(_load_task_history(output_dir))
            if path.startswith("/api/task/"):
                task_id = path.split("/api/task/")[-1]
                return self._send_json(_load_task_detail(output_dir, task_id))
            if path == "/api/metrics":
                return self._send_json(_load_metrics(output_dir))
            if path == "/api/workflows":
                return self._send_json(_list_workflows(output_dir))
            if path.startswith("/files/"):
                return self._send_task_file(path, output_dir)
            if path.startswith("/workflows/"):
                return self._send_workflow_file(path, output_dir)

            self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:
            logger.debug(format % args)

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_static_file(self, name: str, base: Path) -> None:
            base_root = base.resolve()
            file_path = (base / name).resolve()
            if not str(file_path).startswith(str(base_root)):
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            if file_path.is_dir():
                file_path = (file_path / "index.html").resolve()
                if not str(file_path).startswith(str(base_root)):
                    return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            if not file_path.exists():
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

            mime, _ = mimetypes.guess_type(file_path.name)
            if not mime:
                mime = "application/octet-stream"
            if file_path.name == "index.html":
                text = file_path.read_text(encoding="utf-8")
                text = text.replace("{{DASHBOARD_TITLE}}", title)
                data = text.encode("utf-8")
            else:
                data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text/") else mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_task_file(self, path: str, output_dir: Path) -> None:
            safe_path = _resolve_task_file(output_dir, path[len("/files/"):])
            if not safe_path or not safe_path.exists():
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            mime, _ = mimetypes.guess_type(safe_path.name)
            if not mime:
                mime = "application/octet-stream"
            data = safe_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text/") else mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_workflow_file(self, path: str, output_dir: Path) -> None:
            safe_path = _resolve_workflow_file(output_dir, path[len("/workflows/"):])
            if not safe_path or not safe_path.exists():
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            mime, _ = mimetypes.guess_type(safe_path.name)
            if not mime:
                mime = "application/octet-stream"
            data = safe_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text/") else mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return DashboardHandler


def _load_task_index(output_dir: Path) -> Dict[str, Any]:
    index_path = output_dir / "task_index.json"
    if not index_path.exists():
        return {"tasks": []}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"tasks": data}
    except Exception:
        return {"tasks": []}
    return {"tasks": []}


def _load_task_history(output_dir: Path) -> Dict[str, Any]:
    history_path = output_dir / "task_history.jsonl"
    if not history_path.exists():
        return {"history": []}
    records = []
    try:
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        return {"history": []}
    return {"history": records}


def _load_metrics(output_dir: Path) -> Dict[str, Any]:
    metrics_path = output_dir / "tool_metrics.json"
    metrics: Dict[str, Any] = {"summary": {}, "tools": {}}
    try:
        if metrics_path.exists():
            data = json.loads(metrics_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                metrics.update(data)
    except Exception:
        metrics = {"summary": {}, "tools": {}}
    metrics.setdefault("summary", {})
    metrics.setdefault("tools", {})
    metrics["recent"] = _load_recent_durations(output_dir)
    return metrics


def _load_task_detail(output_dir: Path, task_id: str) -> Dict[str, Any]:
    result = {}
    task_dir = output_dir / task_id
    if not task_dir.exists():
        return {"error": "task_not_found", "task_id": task_id}

    result_path = task_dir / "result.json"
    if result_path.exists():
        result["result"] = _read_json(result_path)

    context_path = task_dir / "context_snapshot.json"
    if context_path.exists():
        result["context_snapshot"] = _read_json(context_path)

    metrics_path = task_dir / "tool_metrics.json"
    if metrics_path.exists():
        result["tool_metrics"] = _read_json(metrics_path)

    result["artifacts"] = _list_artifacts(task_dir, output_dir)
    result["task_id"] = task_id
    return result


def _list_artifacts(task_dir: Path, output_dir: Path) -> list:
    artifacts = []
    for entry in sorted(task_dir.iterdir()):
        if not entry.is_file():
            continue
        mime, _ = mimetypes.guess_type(entry.name)
        if not mime:
            mime = "application/octet-stream"
        artifacts.append({
            "name": entry.name,
            "size": entry.stat().st_size,
            "mime": mime,
            "url": f"/files/{task_dir.name}/{entry.name}",
        })
    return artifacts


def _load_recent_durations(output_dir: Path, limit: int = 24) -> list:
    history = _load_task_history(output_dir).get("history", [])
    if not isinstance(history, list) or not history:
        return []
    items = []
    for record in reversed(history):
        if len(items) >= limit:
            break
        if not isinstance(record, dict):
            continue
        task_id = record.get("task_id")
        execution_time = record.get("execution_time")
        if execution_time is None and task_id:
            result_path = output_dir / task_id / "result.json"
            if result_path.exists():
                result = _read_json(result_path)
                if isinstance(result, dict):
                    execution_time = result.get("execution_time")
        items.append({
            "task_id": task_id,
            "timestamp": record.get("timestamp"),
            "execution_time": execution_time,
            "success": record.get("success"),
        })
    items.reverse()
    return items


def _list_workflows(output_dir: Path) -> Dict[str, Any]:
    workflow_dir = output_dir / "workflows"
    if not workflow_dir.exists():
        return {"workflows": []}
    grouped: Dict[str, Dict[str, Any]] = {}
    for entry in workflow_dir.iterdir():
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if ext not in {".html", ".mmd"}:
            continue
        stat = entry.stat()
        stem = entry.stem
        info = grouped.setdefault(stem, {"name": stem, "updated_at": stat.st_mtime, "files": {}})
        if stat.st_mtime > info.get("updated_at", 0):
            info["updated_at"] = stat.st_mtime
        info["files"][ext.lstrip(".")] = {
            "name": entry.name,
            "size": stat.st_size,
            "url": f"/workflows/{entry.name}",
        }
    items = []
    for item in grouped.values():
        updated_at = item.get("updated_at")
        if updated_at:
            item["updated_at"] = datetime.fromtimestamp(updated_at).isoformat()
        items.append(item)
    items.sort(key=lambda entry: entry.get("updated_at") or "", reverse=True)
    return {"workflows": items}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_task_file(base_dir: Path, relative_path: str) -> Optional[Path]:
    safe_root = base_dir.resolve()
    target = (base_dir / relative_path.lstrip("/")).resolve()
    if not str(target).startswith(str(safe_root)):
        return None
    return target


def _resolve_workflow_file(base_dir: Path, relative_path: str) -> Optional[Path]:
    workflow_root = (base_dir / "workflows").resolve()
    target = (workflow_root / relative_path.lstrip("/")).resolve()
    if not str(target).startswith(str(workflow_root)):
        return None
    return target
