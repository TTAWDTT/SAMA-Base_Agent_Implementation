# ==============================================================================
# 待办任务管理工具 / Todo Task Management Tool
# ==============================================================================
# 提供任务规划、跟踪和管理功能
# Provides task planning, tracking and management functionality
#
# 功能说明 / Features:
# - 添加待办任务 / Add todo tasks
# - 更新任务状态（待处理/进行中/已完成）/ Update task status (pending/in_progress/completed)
# - 删除任务 / Delete tasks
# - 列出所有任务 / List all tasks
# - 清空任务列表 / Clear task list
#
# 使用场景 / Usage Scenarios:
# - 规划复杂任务的实施步骤 / Planning implementation steps for complex tasks
# - 跟踪多步骤任务的进度 / Tracking progress of multi-step tasks
# - 向用户清晰展示当前工作进展 / Clearly showing work progress to users
# ==============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from src.tools.base import BaseTool, ToolInput


class TaskStatus(str, Enum):
    """任务状态枚举 / Task Status Enum"""
    PENDING = "pending"          # 待处理 / Pending
    IN_PROGRESS = "in_progress"  # 进行中 / In Progress
    COMPLETED = "completed"      # 已完成 / Completed


class TodoInput(ToolInput):
    """待办任务输入 / Todo Task Input"""
    operation: Literal["add", "update", "delete", "list", "clear"] = Field(
        description="操作类型：add（添加）、update（更新状态）、delete（删除）、list（列出）、clear（清空）/ Operation type: add, update, delete, list, clear"
    )
    tasks: Optional[List[str]] = Field(
        default=None,
        description="待添加的任务列表（仅add操作）/ List of tasks to add (only for add operation)"
    )
    task_id: Optional[int] = Field(
        default=None,
        description="任务ID（update/delete操作需要）/ Task ID (required for update/delete operations)"
    )
    status: Optional[Literal["pending", "in_progress", "completed"]] = Field(
        default=None,
        description="新状态（仅update操作）：pending（待处理）、in_progress（进行中）、completed（已完成）/ New status (only for update operation): pending, in_progress, completed"
    )


class TodoTool(BaseTool):
    """
    待办任务管理工具 / Todo Task Management Tool
    
    ## 基本描述
    
    用于规划、跟踪和管理任务的工具。帮助将复杂任务拆分为可管理的步骤，
    并实时跟踪每个步骤的完成状态。
    
    This tool is used for planning, tracking and managing tasks. It helps break down
    complex tasks into manageable steps and track the completion status of each step in real-time.
    
    ## 使用步骤
    
    1. **添加任务 (add)**：将待办事项添加到任务列表
       - 可一次添加多个任务
       - 新任务默认状态为"待处理"
    
    2. **更新状态 (update)**：更新指定任务的状态
       - pending（待处理）→ in_progress（进行中）→ completed（已完成）
       - 开始处理任务时标记为 in_progress
       - 任务完成后立即标记为 completed
    
    3. **列出任务 (list)**：查看所有任务及其状态
       - 显示任务ID、描述、状态和创建时间
       - 便于跟踪整体进度
    
    4. **删除任务 (delete)**：删除指定任务
       - 用于移除不再需要的任务
    
    5. **清空列表 (clear)**：清空所有任务
       - 用于开始新的任务规划
    
    ## 使用说明
    
    - **operation** (必填): 操作类型，可选值为 add/update/delete/list/clear
    - **tasks** (add操作必填): 待添加的任务描述列表，如 ["任务1", "任务2"]
    - **task_id** (update/delete操作必填): 要操作的任务ID（从1开始）
    - **status** (update操作必填): 新状态，可选值为 pending/in_progress/completed
    
    ### 最佳实践
    
    - 规划任务时，使用 add 操作添加所有步骤
    - 开始处理某任务时，将其标记为 in_progress
    - 任务完成后**立即**标记为 completed，不要批量标记
    - 定期使用 list 查看进度
    
    ## 示例
    
    ### 示例1：添加多个任务
    ```json
    {
        "operation": "add",
        "tasks": ["分析用户需求", "设计系统架构", "实现核心功能", "编写测试用例"]
    }
    ```
    输出：成功添加 4 个任务
    
    ### 示例2：开始处理任务
    ```json
    {
        "operation": "update",
        "task_id": 1,
        "status": "in_progress"
    }
    ```
    输出：任务 1 状态已更新为：进行中
    
    ### 示例3：完成任务
    ```json
    {
        "operation": "update",
        "task_id": 1,
        "status": "completed"
    }
    ```
    输出：任务 1 状态已更新为：已完成
    
    ### 示例4：列出所有任务
    ```json
    {
        "operation": "list"
    }
    ```
    输出：
    待办任务列表 (共4项，已完成1项)
    ──────────────────────────────
    [1] ✅ 分析用户需求
    [2] ⏳ 设计系统架构
    [3] ⬜ 实现核心功能
    [4] ⬜ 编写测试用例
    
    ### 示例5：删除任务
    ```json
    {
        "operation": "delete",
        "task_id": 3
    }
    ```
    输出：任务 3 已删除：实现核心功能
    
    ### 示例6：清空所有任务
    ```json
    {
        "operation": "clear"
    }
    ```
    输出：已清空所有任务（共删除4项）
    """
    
    name: str = "todo"
    
    description: str = """待办任务管理工具，用于规划、跟踪和管理任务。

## 基本描述

用于规划、跟踪和管理任务的工具。帮助将复杂任务拆分为可管理的步骤，
并实时跟踪每个步骤的完成状态。

## 使用步骤

1. **添加任务 (add)**：将待办事项添加到任务列表
   - 可一次添加多个任务
   - 新任务默认状态为"待处理"

2. **更新状态 (update)**：更新指定任务的状态
   - pending（待处理）→ in_progress（进行中）→ completed（已完成）
   - 开始处理任务时标记为 in_progress
   - 任务完成后立即标记为 completed

3. **列出任务 (list)**：查看所有任务及其状态

4. **删除任务 (delete)**：删除指定任务

5. **清空列表 (clear)**：清空所有任务

## 使用说明

- **operation** (必填): 操作类型，可选值为 add/update/delete/list/clear
- **tasks** (add操作必填): 待添加的任务描述列表，如 ["任务1", "任务2"]
- **task_id** (update/delete操作必填): 要操作的任务ID（从1开始）
- **status** (update操作必填): 新状态，可选值为 pending/in_progress/completed

### 最佳实践

- 规划任务时，使用 add 操作添加所有步骤
- 开始处理某任务时，将其标记为 in_progress
- 任务完成后**立即**标记为 completed，不要批量标记
- 定期使用 list 查看进度

## 示例

### 示例1：添加多个任务
```json
{
    "operation": "add",
    "tasks": ["分析用户需求", "设计系统架构", "实现核心功能"]
}
```

### 示例2：更新任务状态
```json
{
    "operation": "update",
    "task_id": 1,
    "status": "in_progress"
}
```

### 示例3：列出所有任务
```json
{
    "operation": "list"
}
```
"""
    
    description_zh: str = """待办任务管理工具，用于规划、跟踪和管理任务。

## 基本描述

用于规划、跟踪和管理任务的工具。帮助将复杂任务拆分为可管理的步骤，
并实时跟踪每个步骤的完成状态。

## 使用步骤

1. **添加任务 (add)**：将待办事项添加到任务列表
2. **更新状态 (update)**：更新指定任务的状态（pending/in_progress/completed）
3. **列出任务 (list)**：查看所有任务及其状态
4. **删除任务 (delete)**：删除指定任务
5. **清空列表 (clear)**：清空所有任务

## 使用说明

- **operation** (必填): 操作类型（add/update/delete/list/clear）
- **tasks** (add操作必填): 待添加的任务描述列表
- **task_id** (update/delete操作必填): 要操作的任务ID
- **status** (update操作必填): 新状态（pending/in_progress/completed）

## 示例

添加任务：{"operation": "add", "tasks": ["任务1", "任务2"]}
更新状态：{"operation": "update", "task_id": 1, "status": "completed"}
列出任务：{"operation": "list"}
"""
    
    description_en: str = """Todo task management tool for planning, tracking and managing tasks.

## Basic Description

A tool for planning, tracking and managing tasks. Helps break down complex tasks into 
manageable steps and track the completion status of each step in real-time.

## Usage Steps

1. **Add tasks (add)**: Add todo items to the task list
2. **Update status (update)**: Update status of specified task (pending/in_progress/completed)
3. **List tasks (list)**: View all tasks and their status
4. **Delete task (delete)**: Delete specified task
5. **Clear list (clear)**: Clear all tasks

## Usage Instructions

- **operation** (required): Operation type (add/update/delete/list/clear)
- **tasks** (required for add): List of task descriptions to add
- **task_id** (required for update/delete): Task ID to operate on
- **status** (required for update): New status (pending/in_progress/completed)

## Examples

Add tasks: {"operation": "add", "tasks": ["Task 1", "Task 2"]}
Update status: {"operation": "update", "task_id": 1, "status": "completed"}
List tasks: {"operation": "list"}
"""
    
    input_schema = TodoInput
    
    # 类级别的任务存储（跨实例共享）/ Class-level task storage (shared across instances)
    _tasks: Dict[int, Dict[str, Any]] = {}
    _next_id: int = 1
    
    def __init__(self):
        """初始化 / Initialize"""
        super().__init__()
    
    def _run(
        self,
        operation: str,
        tasks: Optional[List[str]] = None,
        task_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> str:
        """
        执行待办任务操作 / Execute todo task operation
        
        Args:
            operation: 操作类型 / Operation type
            tasks: 待添加的任务列表 / List of tasks to add
            task_id: 任务ID / Task ID
            status: 新状态 / New status
            
        Returns:
            str: 操作结果 / Operation result
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
            return f"未知操作类型 / Unknown operation type: {operation}. 支持的操作 / Supported operations: add, update, delete, list, clear"
    
    def _add_tasks(self, tasks: Optional[List[str]]) -> str:
        """
        添加任务 / Add tasks
        
        Args:
            tasks: 任务描述列表 / List of task descriptions
            
        Returns:
            str: 添加结果 / Add result
        """
        if not tasks:
            return "错误：必须提供任务列表 / Error: Must provide tasks list"
        
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
        
        result = f"成功添加 {len(added_tasks)} 个任务 / Successfully added {len(added_tasks)} tasks:\n"
        result += "\n".join(added_tasks)
        return result
    
    def _update_task(self, task_id: Optional[int], status: Optional[str]) -> str:
        """
        更新任务状态 / Update task status
        
        Args:
            task_id: 任务ID / Task ID
            status: 新状态 / New status
            
        Returns:
            str: 更新结果 / Update result
        """
        if task_id is None:
            return "错误：必须提供 task_id / Error: Must provide task_id"
        
        if status is None:
            return "错误：必须提供 status / Error: Must provide status"
        
        if task_id not in TodoTool._tasks:
            return f"错误：任务不存在 / Error: Task not found: {task_id}"
        
        # 验证状态值 / Validate status value
        try:
            new_status = TaskStatus(status.lower())
        except ValueError:
            return f"错误：无效状态 / Error: Invalid status: {status}. 可选值 / Valid values: pending, in_progress, completed"
        
        task = TodoTool._tasks[task_id]
        old_status = task["status"]
        task["status"] = new_status
        task["updated_at"] = datetime.now().isoformat()
        
        status_text = {
            TaskStatus.PENDING: "待处理 / Pending",
            TaskStatus.IN_PROGRESS: "进行中 / In Progress",
            TaskStatus.COMPLETED: "已完成 / Completed"
        }
        
        return f"任务 {task_id} 状态已更新 / Task {task_id} status updated: {status_text[old_status]} → {status_text[new_status]}\n任务 / Task: {task['description']}"
    
    def _delete_task(self, task_id: Optional[int]) -> str:
        """
        删除任务 / Delete task
        
        Args:
            task_id: 任务ID / Task ID
            
        Returns:
            str: 删除结果 / Delete result
        """
        if task_id is None:
            return "错误：必须提供 task_id / Error: Must provide task_id"
        
        if task_id not in TodoTool._tasks:
            return f"错误：任务不存在 / Error: Task not found: {task_id}"
        
        task = TodoTool._tasks.pop(task_id)
        return f"任务 {task_id} 已删除 / Task {task_id} deleted: {task['description']}"
    
    def _list_tasks(self) -> str:
        """
        列出所有任务 / List all tasks
        
        Returns:
            str: 任务列表 / Task list
        """
        if not TodoTool._tasks:
            return "待办列表为空 / Todo list is empty"
        
        # 统计各状态任务数 / Count tasks by status
        total = len(TodoTool._tasks)
        completed = sum(1 for t in TodoTool._tasks.values() if t["status"] == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in TodoTool._tasks.values() if t["status"] == TaskStatus.IN_PROGRESS)
        pending = total - completed - in_progress
        
        # 构建输出 / Build output
        lines = [
            f"待办任务列表 / Todo List (共{total}项 / total {total}，已完成{completed} / completed {completed})",
            "─" * 50
        ]
        
        # 状态图标 / Status icons
        status_icons = {
            TaskStatus.PENDING: "⬜",
            TaskStatus.IN_PROGRESS: "⏳",
            TaskStatus.COMPLETED: "✅"
        }
        
        # 按ID排序显示 / Sort by ID
        for task_id in sorted(TodoTool._tasks.keys()):
            task = TodoTool._tasks[task_id]
            icon = status_icons.get(task["status"], "?")
            lines.append(f"[{task_id}] {icon} {task['description']}")
        
        lines.append("─" * 50)
        lines.append(f"进度 / Progress: ⬜待处理{pending} ⏳进行中{in_progress} ✅已完成{completed}")
        
        return "\n".join(lines)
    
    def _clear_tasks(self) -> str:
        """
        清空所有任务 / Clear all tasks
        
        Returns:
            str: 清空结果 / Clear result
        """
        count = len(TodoTool._tasks)
        TodoTool._tasks.clear()
        TodoTool._next_id = 1
        return f"已清空所有任务 / All tasks cleared (共删除 / deleted {count} 项 / items)"
    
    @classmethod
    def reset(cls) -> None:
        """
        重置任务列表（用于测试）/ Reset task list (for testing)
        """
        cls._tasks.clear()
        cls._next_id = 1
