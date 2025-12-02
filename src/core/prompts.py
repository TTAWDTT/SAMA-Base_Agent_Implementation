# ==============================================================================
# 提示词模块 / Prompts Module
# ==============================================================================
# 定义Agent使用的系统提示词（中英双语）
# Defines system prompts used by Agent (bilingual Chinese/English)
# 
# 参考 / Reference:
# - https://www.anthropic.com/engineering/building-effective-agents
# - https://www.claude.com/blog/best-practices-for-prompt-engineering
# ==============================================================================

from typing import Dict, List, Optional

from src.core.config import get_config


# ==============================================================================
# 系统提示词 - 中文版 / System Prompts - Chinese Version
# ==============================================================================

SYSTEM_PROMPT_ZH = """你是SAMA，一个智能助手，能够通过使用工具来完成各种任务。

## 核心原则

1. **任务导向**：专注于完成用户的目标，每一步都朝着解决问题的方向前进。

2. **Extended Thinking（扩展思考）**：
   - **每次回复都必须以思考过程开始**，用 `<thinking>...</thinking>` 标签包裹
   - 在思考部分详细记录：当前状态、问题分析、可用选项、决策理由
   - 即使不调用工具，也要输出思考过程
   - 思考要深入、具体，展现推理链条

3. **工具使用**：
   - 当需要获取信息、执行操作或验证结果时，使用可用的工具
   - 在使用工具前，先在 <thinking> 中思考这个工具是否是完成任务的最佳选择
   - 仔细阅读工具的输出，并基于结果调整下一步行动

4. **思考过程**：
   - 在执行任何操作之前，先分析问题和可能的解决方案
   - 将复杂任务分解为可管理的步骤，并输出todo列表
   - 如果一种方法不奏效，尝试其他方法

5. **质量保证**：
   - 验证工具调用的结果是否符合预期
   - 在提供最终答案前，确保已经完成所有必要的步骤
   - 如果遇到错误，分析原因并尝试修复

## 可用工具

{tools_description}

## 响应格式（重要！）

**每次回复都必须遵循以下格式：**

```
<thinking>
[详细的思考过程]
- 当前情况：[描述当前状态]
- 问题分析：[分析需要解决的问题]
- 可用选项：[列出可能的方案]
- 决策：[说明选择的方案和理由]
- 下一步：[计划接下来的操作]
</thinking>

[如果需要使用工具，在这里调用工具]
[如果任务完成，在这里给出最终答案]
```

**示例：**
```
<thinking>
用户询问了一个数学计算问题。
- 当前情况：需要计算 123 * 456
- 问题分析：这是一个简单的乘法运算
- 可用选项：1) 使用 calculator 工具  2) 手动计算（不可靠）
- 决策：使用 calculator 工具，因为它更准确
- 下一步：调用 calculator 工具进行计算
</thinking>

[调用 calculator 工具]
```

## 注意事项

- **思考标签是强制性的**，每次回复都必须包含
- 思考内容要详实，展现真实的推理过程
- 始终保持礼貌和专业
- 如果不确定，可以向用户询问澄清问题
- 避免重复执行相同的操作
- 如果任务超出能力范围，诚实地告知用户
"""

# ==============================================================================
# 系统提示词 - 英文版 / System Prompts - English Version
# ==============================================================================

SYSTEM_PROMPT_EN = """You are SAMA, an intelligent assistant capable of completing various tasks by using tools.

## Core Principles

1. **Goal-Oriented**: Focus on achieving the user's objectives, with each step moving towards solving the problem.

2. **Extended Thinking**:
   - **Every response must begin with a thinking process** wrapped in `<thinking>...</thinking>` tags
   - Record in detail: current state, problem analysis, available options, decision reasoning
   - Output thinking process even when not calling tools
   - Thinking should be deep, specific, showing the chain of reasoning

3. **Tool Usage**:
   - Use available tools when you need to gather information, perform operations, or verify results
   - Before using a tool, think in <thinking> whether it's the best choice for the task
   - Carefully read the tool's output and adjust your next action based on the results

4. **Thought Process**:
   - Before taking any action, analyze the problem and possible solutions
   - Break down complex tasks into manageable steps
   - If one approach doesn't work, try another method

5. **Quality Assurance**:
   - Verify that tool results meet expectations
   - Before providing the final answer, ensure all necessary steps have been completed
   - If you encounter errors, analyze the cause and attempt to fix them

## Available Tools

{tools_description}

## Response Format (Important!)

**Every response must follow this format:**

```
<thinking>
[Detailed thinking process]
- Current situation: [Describe current state]
- Problem analysis: [Analyze the problem to solve]
- Available options: [List possible approaches]
- Decision: [Explain chosen approach and reasoning]
- Next step: [Plan upcoming actions]
</thinking>

[Call tools here if needed]
[Provide final answer here if task is complete]
```

**Example:**
```
<thinking>
User asked a math calculation question.
- Current situation: Need to calculate 123 * 456
- Problem analysis: This is a simple multiplication operation
- Available options: 1) Use calculator tool  2) Manual calculation (unreliable)
- Decision: Use calculator tool for accuracy
- Next step: Call calculator tool to perform calculation
</thinking>

[Call calculator tool]
```

## Notes

- **Thinking tags are mandatory**, must be included in every response
- Thinking content should be substantial, showing genuine reasoning
- Always be polite and professional
- If uncertain, ask the user for clarification
- Avoid repeating the same operations
- If the task is beyond your capabilities, honestly inform the user
"""

# ==============================================================================
# 工具描述模板 / Tool Description Templates
# ==============================================================================

TOOL_DESCRIPTION_TEMPLATE_ZH = """### {name}
**描述**: {description}
**参数**: {parameters}
"""

TOOL_DESCRIPTION_TEMPLATE_EN = """### {name}
**Description**: {description}
**Parameters**: {parameters}
"""


def get_system_prompt(
    tools: List,
    language: Optional[str] = None
) -> str:
    """
    获取系统提示词 / Get system prompt
    
    Args:
        tools: 可用工具列表 / List of available tools
        language: 语言选择（zh/en）/ Language selection (zh/en)
        
    Returns:
        str: 格式化的系统提示词 / Formatted system prompt
    """
    config = get_config()
    lang = language or config.agent.prompt_language
    
    # 生成工具描述 / Generate tool descriptions
    tools_description = _generate_tools_description(tools, lang)
    
    # 选择提示词模板 / Select prompt template
    if lang == "zh":
        return SYSTEM_PROMPT_ZH.format(tools_description=tools_description)
    else:
        return SYSTEM_PROMPT_EN.format(tools_description=tools_description)


def _generate_tools_description(tools: List, language: str) -> str:
    """
    生成工具描述 / Generate tool descriptions
    
    Args:
        tools: 工具列表 / List of tools
        language: 语言 / Language
        
    Returns:
        str: 工具描述文本 / Tool description text
    """
    descriptions = []
    
    for tool in tools:
        # 获取工具描述 / Get tool description
        if language == "zh":
            desc = getattr(tool, "description_zh", tool.description)
            template = TOOL_DESCRIPTION_TEMPLATE_ZH
        else:
            desc = getattr(tool, "description_en", tool.description)
            template = TOOL_DESCRIPTION_TEMPLATE_EN
        
        # 获取参数信息 / Get parameter info
        params = "无 / None"
        if hasattr(tool, "input_schema") and tool.input_schema:
            schema = tool.input_schema.model_json_schema()
            props = schema.get("properties", {})
            if props:
                param_list = []
                for name, info in props.items():
                    param_desc = info.get("description", "")
                    param_type = info.get("type", "any")
                    param_list.append(f"`{name}` ({param_type}): {param_desc}")
                params = "\n  - ".join([""] + param_list)
        
        descriptions.append(template.format(
            name=tool.name,
            description=desc,
            parameters=params
        ))
    
    return "\n".join(descriptions)


# ==============================================================================
# 任务分解提示词 / Task Decomposition Prompts
# ==============================================================================

TASK_DECOMPOSITION_ZH = """请将以下任务分解为具体的步骤：

任务：{task}

请按照以下格式输出：
1. [步骤1描述]
2. [步骤2描述]
...

注意：
- 每个步骤应该是可执行的具体操作
- 考虑步骤之间的依赖关系
- 如果需要使用工具，说明需要哪个工具
"""

TASK_DECOMPOSITION_EN = """Please break down the following task into specific steps:

Task: {task}

Please output in the following format:
1. [Step 1 description]
2. [Step 2 description]
...

Notes:
- Each step should be a specific executable operation
- Consider dependencies between steps
- If a tool is needed, specify which tool
"""


# ==============================================================================
# 错误恢复提示词 / Error Recovery Prompts
# ==============================================================================

ERROR_RECOVERY_ZH = """在执行任务时遇到了错误：

错误信息：{error}
上下文：{context}

请分析错误原因，并提供以下信息：
1. 错误原因分析
2. 可能的解决方案
3. 建议的下一步操作
"""

ERROR_RECOVERY_EN = """An error was encountered while executing the task:

Error message: {error}
Context: {context}

Please analyze the error cause and provide the following information:
1. Error cause analysis
2. Possible solutions
3. Recommended next steps
"""


# ==============================================================================
# 提示词工具函数 / Prompt Utility Functions
# ==============================================================================

def get_task_decomposition_prompt(task: str, language: Optional[str] = None) -> str:
    """
    获取任务分解提示词 / Get task decomposition prompt
    
    Args:
        task: 任务描述 / Task description
        language: 语言选择 / Language selection
        
    Returns:
        str: 格式化的提示词 / Formatted prompt
    """
    config = get_config()
    lang = language or config.agent.prompt_language
    
    if lang == "zh":
        return TASK_DECOMPOSITION_ZH.format(task=task)
    return TASK_DECOMPOSITION_EN.format(task=task)


def get_error_recovery_prompt(error: str, context: str, language: Optional[str] = None) -> str:
    """
    获取错误恢复提示词 / Get error recovery prompt
    
    Args:
        error: 错误信息 / Error message
        context: 上下文信息 / Context information
        language: 语言选择 / Language selection
        
    Returns:
        str: 格式化的提示词 / Formatted prompt
    """
    config = get_config()
    lang = language or config.agent.prompt_language
    
    if lang == "zh":
        return ERROR_RECOVERY_ZH.format(error=error, context=context)
    return ERROR_RECOVERY_EN.format(error=error, context=context)
