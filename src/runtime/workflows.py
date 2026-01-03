# ==============================================================================
# 工作流编排器
# ==============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.runtime.tasks import TaskRunner, TaskSpec, TaskResult


@dataclass
class WorkflowNode:
    node_id: str
    prompt: str
    reference_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    when: List[Dict[str, Any]] = field(default_factory=list)
    on_success: List[str] = field(default_factory=list)
    on_failure: List[str] = field(default_factory=list)


@dataclass
class WorkflowSpec:
    workflow_id: str
    title: str = "工作流"
    nodes: List[WorkflowNode] = field(default_factory=list)


@dataclass
class WorkflowNodeResult:
    node_id: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    output_dir: Optional[str] = None
    response: Optional[Any] = None


@dataclass
class WorkflowResult:
    workflow_id: str
    title: str
    started_at: str
    finished_at: Optional[str]
    nodes: List[WorkflowNodeResult]


def load_workflow_spec(path: str) -> WorkflowSpec:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"工作流文件不存在: {path}")
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    else:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    return _build_spec(data, file_path)


def run_workflow(
    path: str,
    runner: TaskRunner,
    output_dir: Optional[str] = None
) -> WorkflowResult:
    spec = load_workflow_spec(path)
    return WorkflowRunner(runner, output_dir=output_dir).run(spec)


def render_workflow_spec(spec: WorkflowSpec) -> str:
    lines = ["flowchart TD"]
    lines.append(f'Start["开始"]')
    node_map = {node.node_id: node for node in spec.nodes}

    for node in spec.nodes:
        label = f"{node.node_id}\\n{node.prompt[:20]}"
        lines.append(f'{node.node_id}["{_escape(label)}"]')
        if node.depends_on:
            for dep in node.depends_on:
                if dep in node_map:
                    lines.append(f"{dep} --> {node.node_id}")
        else:
            lines.append(f"Start --> {node.node_id}")

        for nxt in node.on_success:
            if nxt in node_map:
                lines.append(f"{node.node_id} --> {nxt}")
        for nxt in node.on_failure:
            if nxt in node_map:
                lines.append(f"{node.node_id} -.失败.-> {nxt}")

    lines.append('End["结束"]')
    for node in spec.nodes:
        if not node.on_success and not node.on_failure:
            lines.append(f"{node.node_id} --> End")
    return "\n".join(lines)


def save_workflow_diagram(
    spec: WorkflowSpec,
    output_dir: str,
    title: Optional[str] = None
) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    mermaid_text = render_workflow_spec(spec)
    mermaid_path = output_path / f"{spec.workflow_id}.mmd"
    header = f"%% {title or spec.title}"
    mermaid_path.write_text(header + "\n" + mermaid_text, encoding="utf-8")
    return str(mermaid_path)


class WorkflowRunner:
    def __init__(self, runner: TaskRunner, output_dir: Optional[str] = None) -> None:
        self.runner = runner
        self.output_dir = output_dir or "outputs/workflows"

    def run(self, spec: WorkflowSpec) -> WorkflowResult:
        start_time = datetime.now().isoformat()
        results: Dict[str, WorkflowNodeResult] = {}
        ordered = _resolve_order(spec.nodes)

        for node in ordered:
            result = WorkflowNodeResult(node_id=node.node_id, status="pending")
            results[node.node_id] = result

            if not _deps_satisfied(node, results):
                result.status = "skipped"
                result.finished_at = datetime.now().isoformat()
                continue

            if node.when and not _check_conditions(node.when, results):
                result.status = "skipped"
                result.finished_at = datetime.now().isoformat()
                continue

            result.status = "running"
            result.started_at = datetime.now().isoformat()
            try:
                task = TaskSpec(
                    task_id=node.node_id,
                    prompt=node.prompt,
                    reference_files=node.reference_files,
                    metadata={**node.metadata, "workflow_id": spec.workflow_id},
                )
                task_result = self.runner.run_task(task, preprocess=True)
                result.response = task_result.response
                output_dir = self.runner.save_result(task_result, print_result=False)
                result.output_dir = output_dir
                if getattr(task_result.response, "success", False):
                    result.status = "completed"
                else:
                    result.status = "failed"
                    result.error = getattr(task_result.response, "error_message", None)
            except Exception as exc:
                result.status = "failed"
                result.error = str(exc)
            result.finished_at = datetime.now().isoformat()

        workflow_result = WorkflowResult(
            workflow_id=spec.workflow_id,
            title=spec.title,
            started_at=start_time,
            finished_at=datetime.now().isoformat(),
            nodes=list(results.values())
        )
        self._save_result(spec, workflow_result)
        return workflow_result

    def _save_result(self, spec: WorkflowSpec, result: WorkflowResult) -> None:
        output_dir = Path(self.output_dir) / spec.workflow_id
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "workflow_id": result.workflow_id,
            "title": result.title,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "nodes": [
                {
                    "node_id": item.node_id,
                    "status": item.status,
                    "started_at": item.started_at,
                    "finished_at": item.finished_at,
                    "error": item.error,
                    "output_dir": item.output_dir,
                }
                for item in result.nodes
            ],
        }
        (output_dir / "workflow_result.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        save_workflow_diagram(spec, str(output_dir), title=spec.title)


def _build_spec(data: Dict[str, Any], path: Path) -> WorkflowSpec:
    workflow_id = str(data.get("workflow_id") or path.stem)
    title = str(data.get("title") or workflow_id)
    nodes = []
    for item in data.get("nodes", []):
        nodes.append(
            WorkflowNode(
                node_id=str(item.get("id") or item.get("node_id")),
                prompt=str(item.get("prompt") or ""),
                reference_files=list(item.get("reference_files") or []),
                metadata=dict(item.get("metadata") or {}),
                depends_on=list(item.get("depends_on") or []),
                when=list(item.get("when") or []),
                on_success=list(item.get("on_success") or []),
                on_failure=list(item.get("on_failure") or []),
            )
        )
    return WorkflowSpec(workflow_id=workflow_id, title=title, nodes=nodes)


def _resolve_order(nodes: List[WorkflowNode]) -> List[WorkflowNode]:
    order = []
    visited = set()

    def visit(node: WorkflowNode) -> None:
        if node.node_id in visited:
            return
        visited.add(node.node_id)
        for dep in node.depends_on:
            dep_node = next((n for n in nodes if n.node_id == dep), None)
            if dep_node:
                visit(dep_node)
        order.append(node)

    for node in nodes:
        visit(node)
    return order


def _deps_satisfied(node: WorkflowNode, results: Dict[str, WorkflowNodeResult]) -> bool:
    for dep in node.depends_on:
        dep_result = results.get(dep)
        if not dep_result or dep_result.status not in {"completed", "failed"}:
            return False
    return True


def _check_conditions(conditions: List[Dict[str, Any]], results: Dict[str, WorkflowNodeResult]) -> bool:
    for condition in conditions:
        if "success" in condition:
            target = results.get(condition["success"])
            if not target or target.status != "completed":
                return False
        if "failure" in condition:
            target = results.get(condition["failure"])
            if not target or target.status != "failed":
                return False
        if "contains" in condition:
            payload = condition["contains"]
            node_id = payload.get("node")
            text = payload.get("text", "")
            target = results.get(node_id)
            response_text = getattr(target.response, "final_answer", "") if target else ""
            if text not in (response_text or ""):
                return False
    return True


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
