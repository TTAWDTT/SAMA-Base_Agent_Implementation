# 非 TUI 优化说明（基于未提交改动）

> 范围：仅整理未提交改动中的“非 TUI”优化；不包含 `main.py` 的界面/交互展示相关调整。

## 工具调用与并行执行
- 工具参数解析与校验：新增工具参数 JSON 解析错误与类型检查；接入 Pydantic 校验，校验失败直接返回错误结果（`src/agents/base.py`）。
- 未知工具与错误流程：遇到未知工具或解析异常时立即回传错误并记录，避免继续执行。
- 并行与串行分流：根据工具是否允许并行执行进行分流，串行工具按顺序执行，并行工具使用线程池执行，结果按原顺序回收。
- 并行能力声明：为工具新增 `can_run_in_parallel` 接口，默认允许并行（`src/tools/base.py`）。
- 具体策略：
  - Python 工具在持久化模式下禁止并行（`src/tools/python_tool.py`）。
  - Todo 工具为共享状态，禁用并行（`src/tools/todo_tool.py`）。

## 上下文与记忆管理
- 分层预算裁剪：将系统/摘要/文件上下文/历史消息进行分层预算分配，并按预算裁剪，避免文件上下文挤压历史（`src/core/memory.py`）。
- 文件上下文相关性分块：
  - 从最近用户消息抽取中英文关键词。
  - 以段落为单位分块并打分筛选，仅注入最相关的块。
  - 支持每文件最大分块数、最小相关性分数、分块大小等配置（`src/core/memory.py`）。

## 工具结果结构化
- 工具结果改为结构化轨迹 JSON：包含 `tool`、`status`、`call_id`、`arguments`、`output`、`error`、`execution_time` 等字段（`src/utils/helpers.py`）。
- 参数与输出清理：参数与输出做长度与深度限制，防止过长内容污染上下文（`src/utils/helpers.py`）。
- 入上下文方式更新：工具结果写入记忆时统一走结构化轨迹（`src/agents/base.py`）。

## 提示词策略
- 系统提示中新增“上下文策略”说明：文件内容按相关性分块注入，预算不足时优先压缩文件上下文，需要完整文件需显式请求（`src/agents/base.py`）。

## 配置项新增
- 并行工具上限：`max_parallel_tools`（`src/core/config.py`）。
- 记忆与文件上下文控制参数：
  - `system_token_ratio` / `file_context_token_ratio` / `history_token_ratio`
  - `file_context_chunk_size` / `file_context_max_chunks_per_file` / `file_context_min_score`
  - `file_context_query_messages`

## 清理项
- 删除 `generate_pdf.py`（不再保留 PDF 生成脚本）。
