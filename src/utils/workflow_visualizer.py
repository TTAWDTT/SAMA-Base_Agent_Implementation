# ==============================================================================
# 工作流可视化工具
# ==============================================================================

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.core.schema import AgentResponse, ToolResultStatus


def _escape_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def _build_node(node_id: str, label: str) -> str:
    label_text = _escape_text(label)
    return f'{node_id}["{label_text}"]'


def generate_workflow_diagram(response: AgentResponse, title: Optional[str] = None) -> str:
    """
    生成Mermaid流程图文本
    """
    lines = ["flowchart TD"]

    lines.append(_build_node("Start", "开始"))
    prev_step_id = "Start"

    steps = response.steps or []
    total_steps = len(steps)
    for step in steps:
        step_id = f"S{step.step_number}"
        step_label = f"步骤 {step.step_number}"
        lines.append(_build_node(step_id, step_label))
        lines.append(f"{prev_step_id} --> {step_id}")

        tool_calls = step.tool_calls or []
        tool_results = step.tool_results or []
        if tool_calls:
            for idx, call in enumerate(tool_calls, start=1):
                tool_id = f"T{step.step_number}_{idx}"
                status_text = "未知"
                if idx - 1 < len(tool_results):
                    result = tool_results[idx - 1]
                    if result.status == ToolResultStatus.SUCCESS:
                        status_text = "成功"
                    elif result.status == ToolResultStatus.TIMEOUT:
                        status_text = "超时"
                    elif result.status == ToolResultStatus.ERROR:
                        status_text = "失败"
                tool_label = f"工具: {call.tool_name}\\n状态: {status_text}"
                lines.append(_build_node(tool_id, tool_label))
                lines.append(f"{step_id} --> {tool_id}")
                if step.step_number < total_steps:
                    next_step_id = f"S{step.step_number + 1}"
                    lines.append(f"{tool_id} --> {next_step_id}")
                else:
                    prev_step_id = tool_id
        else:
            prev_step_id = step_id

    if response.final_answer:
        answer_id = "Answer"
        answer_label = "最终回复"
        lines.append(_build_node(answer_id, answer_label))
        lines.append(f"{prev_step_id} --> {answer_id}")
        prev_step_id = answer_id

    lines.append(_build_node("End", "结束"))
    lines.append(f"{prev_step_id} --> End")

    if title:
        title_text = _escape_text(title)
        lines.insert(0, f'%% {title_text}')

    return "\n".join(lines)


def save_workflow_diagram(
    response: AgentResponse,
    output_dir: str,
    title: Optional[str] = None,
    generate_html: bool = True,
) -> Dict[str, str]:
    """
    保存工作流图文件，返回生成的文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"workflow_{timestamp}"

    mermaid_text = generate_workflow_diagram(response, title=title)
    mermaid_path = output_path / f"{base_name}.mmd"
    mermaid_path.write_text(mermaid_text, encoding="utf-8")

    result = {"mermaid": str(mermaid_path)}

    if generate_html:
        html_content = _build_html(mermaid_text, title or "SAMA 工作流")
        html_path = output_path / f"{base_name}.html"
        html_path.write_text(html_content, encoding="utf-8")
        result["html"] = str(html_path)

    return result


def _build_html(mermaid_text: str, title: str) -> str:
    safe_title = _escape_text(title)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
      margin: 0;
      padding: 24px;
      background: #f7f7f8;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }}
    h1 {{
      font-size: 20px;
      margin: 0 0 16px;
      color: #1f2937;
    }}
    .mermaid {{
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{safe_title}</h1>
    <div class="mermaid">
{mermaid_text}
    </div>
  </div>
  <script>
    mermaid.initialize({{ startOnLoad: true }});
  </script>
</body>
</html>
"""
