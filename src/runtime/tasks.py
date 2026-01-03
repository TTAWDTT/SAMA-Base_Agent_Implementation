# ==============================================================================
# 任务运行器
# ==============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from src.utils import preprocess_files
from src.runtime.artifacts import save_task_result
from src.runtime.metrics import build_tool_metrics, update_tool_metrics_store
from src.runtime.notifications import dispatch_notification


@dataclass
class TaskSpec:
    task_id: str
    prompt: str
    reference_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    task: TaskSpec
    response: Any
    enhanced_prompt: str
    processed_files: Optional[Dict[str, Any]] = None
    output_dir: Optional[str] = None


class TaskRunner:
    def __init__(self, agent, logger=None, output_dir: Optional[str] = None, config=None) -> None:
        self.agent = agent
        self.logger = logger
        self.config = config or getattr(agent, "config", None)
        if output_dir is None:
            output_dir = getattr(getattr(self.config, "artifacts", None), "output_dir", "outputs")
        self.output_dir = output_dir

    def run_task(
        self,
        task: TaskSpec,
        preprocess: bool = True,
        before_run: Optional[Callable[[], None]] = None,
        after_run: Optional[Callable[[], None]] = None
    ) -> TaskResult:
        processed_files = None
        enhanced_prompt = task.prompt

        if preprocess and task.reference_files:
            existing_files = [path for path in task.reference_files if os.path.exists(path)]
            if existing_files:
                try:
                    processed_files = preprocess_files(task.task_id, existing_files)
                    file_content = processed_files.get("content", "") if processed_files else ""
                    if file_content:
                        enhanced_prompt = f"""{task.prompt}

## 参考文件内容

{file_content}
"""
                except Exception as exc:
                    if self.logger:
                        self.logger.error(f"文件预处理失败: {exc}")

        if before_run:
            before_run()
        try:
            response = self.agent.run(enhanced_prompt)
        finally:
            if after_run:
                after_run()

        return TaskResult(
            task=task,
            response=response,
            enhanced_prompt=enhanced_prompt,
            processed_files=processed_files,
        )

    def save_result(
        self,
        result: TaskResult,
        record_history: bool = True,
        record_index: bool = True,
        print_result: bool = True
    ) -> str:
        artifacts_config = getattr(self.config, "artifacts", None)
        observability_config = getattr(self.config, "observability", None)
        notifications_config = getattr(self.config, "notifications", None)
        metadata = dict(result.task.metadata or {})
        if result.task.reference_files:
            metadata.setdefault("reference_files", result.task.reference_files)

        context_snapshot = None
        if artifacts_config and getattr(artifacts_config, "save_context_snapshot", False):
            memory = getattr(self.agent, "memory", None)
            if memory and hasattr(memory, "export_snapshot"):
                context_snapshot = memory.export_snapshot(
                    max_messages=getattr(artifacts_config, "context_snapshot_max_messages", 50),
                    include_messages=getattr(artifacts_config, "context_snapshot_include_messages", True),
                    include_files=getattr(artifacts_config, "context_snapshot_include_files", True),
                    include_summary=getattr(artifacts_config, "context_snapshot_include_summary", True),
                )

        tool_metrics = None
        if artifacts_config and getattr(artifacts_config, "save_tool_metrics", False):
            tool_metrics = build_tool_metrics(result.response)

        output_dir = save_task_result(
            result.task.task_id,
            result.task.prompt,
            result.response,
            result.processed_files,
            output_dir=self.output_dir,
            print_result=print_result,
            record_history=record_history,
            record_index=record_index,
            metadata=metadata,
            context_snapshot=context_snapshot,
            tool_metrics=tool_metrics
        )
        result.output_dir = output_dir

        if observability_config and getattr(observability_config, "enabled", False) and tool_metrics:
            csv_path = None
            if getattr(observability_config, "export_csv", False):
                csv_path = getattr(observability_config, "metrics_csv_file", None)
            update_tool_metrics_store(
                tool_metrics,
                metrics_path=getattr(observability_config, "metrics_file", "outputs/tool_metrics.json"),
                csv_path=csv_path,
                task_id=result.task.task_id
            )

        if notifications_config:
            context = {
                "task_id": result.task.task_id,
                "prompt": result.task.prompt,
                "success": getattr(result.response, "success", False),
                "error_message": getattr(result.response, "error_message", None),
                "execution_time": getattr(result.response, "execution_time", 0),
                "output_dir": result.output_dir,
            }
            event = "success" if context["success"] else "failure"
            dispatch_notification(event, notifications_config, context)
        return output_dir
