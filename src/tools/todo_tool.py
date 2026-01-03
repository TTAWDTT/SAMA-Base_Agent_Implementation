from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from src.tools.base import BaseTool, ToolInput


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成


class TodoInput(ToolInput):
    """待办任务输入"""
    operation: Literal["add", "update", "delete", "list", "clear"] = Field(
        description="操作类型：add（添加）、update（更新状态）、delete（删除）、list（列出）、clear（清空）"
    )
    tasks: Optional[List[str]] = Field(
        default=None,
        description="待添加的任务列表（仅add操作）"
    )
    task_id: Optional[int] = Field(
        default=None,
        description="任务ID（update/delete操作需要）"
    )
    status: Optional[Literal["pending", "in_progress", "completed"]] = Field(
        default=None,
        description="新状态（仅update操作）：pending（待处理）、in_progress（进行中）、completed（已完成）"
    )


class TodoTool(BaseTool):
    """
    待办任务管理工具。

    用于规划、跟踪和管理任务，支持添加、更新、删除、列出与清空。
    """
    
    name: str = "todo"
    required_permissions = ["tasks"]
    
    description: str = """待办任务管理工具，用于规划、跟踪和管理任务。

## 使用说明

- **operation**（必填）：add/update/delete/list/clear
- **tasks**（add操作必填）：任务描述列表
- **task_id**（update/delete操作必填）：任务ID（从1开始）
- **status**（update操作必填）：pending/in_progress/completed
"""

    description_zh: str = description
    
    input_schema = TodoInput
    
    # 类级别任务存储（跨实例共享）
    _tasks: Dict[int, Dict[str, Any]] = {}
    _next_id: int = 1
    
    def __init__(self):
        """初始化"""
        super().__init__()

    def can_run_in_parallel(self, arguments: Dict[str, Any]) -> bool:
        """
        待办为共享状态，避免并行
        """
        return False
    
    def _run(
        self,
        operation: str,
        tasks: Optional[List[str]] = None,
        task_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> str:
        """
        执行待办任务操作

        Args:
            operation: 操作类型
            tasks: 待添加的任务列表
            task_id: 任务ID
            status: 新状态

        Returns:
            str: 操作结果
        """
        operation = operation.lower().strip()
        
        if operation == "add":
            return self._add_tasks(tasks)
        elif operation == "update":
            return self._update_task(task_id, status)
        elif operation == "delete":
            return self._delete_task(task_id)
        elif operation == "list":
            return self._list_tasks()
        elif operation == "clear":
            return self._clear_tasks()
        else:
            return f"未知操作类型: {operation}。支持的操作: add, update, delete, list, clear"
    
    def _add_tasks(self, tasks: Optional[List[str]]) -> str:
        """
        添加任务

        Args:
            tasks: 任务描述列表

        Returns:
            str: 添加结果
        """
        if not tasks:
            return "错误：必须提供任务列表"
        
        if not isinstance(tasks, list):
            tasks = [str(tasks)]
        
        added_tasks = []
        for task_desc in tasks:
            task = {
                "id": TodoTool._next_id,
                "description": str(task_desc).strip(),
                "status": TaskStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            TodoTool._tasks[TodoTool._next_id] = task
            added_tasks.append(f"[{TodoTool._next_id}] {task_desc}")
            TodoTool._next_id += 1
        
        result = f"成功添加 {len(added_tasks)} 个任务：\n"
        result += "\n".join(added_tasks)
        return result
    
    def _update_task(self, task_id: Optional[int], status: Optional[str]) -> str:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态

        Returns:
            str: 更新结果
        """
        if task_id is None:
            return "错误：必须提供 task_id"
        
        if status is None:
            return "错误：必须提供 status"
        
        if task_id not in TodoTool._tasks:
            return f"错误：任务不存在: {task_id}"
        
        # 验证状态值
        try:
            new_status = TaskStatus(status.lower())
        except ValueError:
            return f"错误：无效状态: {status}。可选值: pending, in_progress, completed"
        
        task = TodoTool._tasks[task_id]
        old_status = task["status"]
        task["status"] = new_status
        task["updated_at"] = datetime.now().isoformat()
        
        status_text = {
            TaskStatus.PENDING: "待处理",
            TaskStatus.IN_PROGRESS: "进行中",
            TaskStatus.COMPLETED: "已完成"
        }
        
        return f"任务 {task_id} 状态已更新：{status_text[old_status]} → {status_text[new_status]}\n任务: {task['description']}"
    
    def _delete_task(self, task_id: Optional[int]) -> str:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            str: 删除结果
        """
        if task_id is None:
            return "错误：必须提供 task_id"
        
        if task_id not in TodoTool._tasks:
            return f"错误：任务不存在: {task_id}"
        
        task = TodoTool._tasks.pop(task_id)
        return f"任务 {task_id} 已删除: {task['description']}"
    
    def _list_tasks(self) -> str:
        """
        列出所有任务

        Returns:
            str: 任务列表
        """
        if not TodoTool._tasks:
            return "待办列表为空"
        
        # 统计各状态任务数
        total = len(TodoTool._tasks)
        completed = sum(1 for t in TodoTool._tasks.values() if t["status"] == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in TodoTool._tasks.values() if t["status"] == TaskStatus.IN_PROGRESS)
        pending = total - completed - in_progress
        
        # 构建输出
        lines = [
            f"待办任务列表（共{total}项，已完成{completed}）",
            "─" * 50
        ]
        
        # 状态图标
        status_icons = {
            TaskStatus.PENDING: "⬜",
            TaskStatus.IN_PROGRESS: "⏳",
            TaskStatus.COMPLETED: "✅"
        }
        
        # 按编号排序显示
        for task_id in sorted(TodoTool._tasks.keys()):
            task = TodoTool._tasks[task_id]
            icon = status_icons.get(task["status"], "?")
            lines.append(f"[{task_id}] {icon} {task['description']}")
        
        lines.append("─" * 50)
        lines.append(f"进度：待处理{pending} 进行中{in_progress} 已完成{completed}")
        
        return "\n".join(lines)
    
    def _clear_tasks(self) -> str:
        """
        清空所有任务

        Returns:
            str: 清空结果
        """
        count = len(TodoTool._tasks)
        TodoTool._tasks.clear()
        TodoTool._next_id = 1
        return f"已清空所有任务（共删除 {count} 项）"
    
