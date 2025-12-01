# 提示词工程 / Prompt Engineering

## 概述 / Overview

本项目的提示词设计参考了 Anthropic 的官方最佳实践文档。

## 系统提示词结构 / System Prompt Structure

```
┌─────────────────────────────────────────┐
│           系统提示词结构                  │
├─────────────────────────────────────────┤
│                                         │
│  1. 角色定义                             │
│     - 你是一个智能助手                    │
│     - 能够通过工具完成任务                 │
│                                         │
│  2. 核心原则                             │
│     - 任务导向                           │
│     - 工具使用                           │
│     - 思考过程                           │
│     - 质量保证                           │
│                                         │
│  3. 可用工具                             │
│     - 工具列表和描述                      │
│     - 参数说明                           │
│                                         │
│  4. 响应格式                             │
│     - 思考 → 工具调用 → 观察 → 继续/完成   │
│                                         │
│  5. 注意事项                             │
│     - 礼貌专业                           │
│     - 避免重复                           │
│     - 诚实告知限制                        │
│                                         │
└─────────────────────────────────────────┘
```

## 提示词最佳实践 / Best Practices

### 1. 明确角色定义 / Clear Role Definition

```
你是一个智能助手，能够通过使用工具来完成各种任务。
```

**不推荐**：
```
你是一个AI。
```

### 2. 结构化指令 / Structured Instructions

使用标题和列表组织提示词：

```markdown
## 核心原则

1. **任务导向**：专注于完成用户的目标
2. **工具使用**：在需要时使用可用工具
3. **思考过程**：先分析再行动
```

### 3. 提供示例 / Provide Examples

```
当你需要使用工具时，请按照以下格式：
1. 思考：分析当前情况
2. 工具调用：选择合适的工具
3. 观察：分析工具结果
4. 继续或完成：决定下一步
```

### 4. 明确边界 / Clear Boundaries

```
## 注意事项

- 如果不确定，可以向用户询问澄清问题
- 如果任务超出能力范围，诚实地告知用户
```

## 双语提示词 / Bilingual Prompts

本项目支持中英双语提示词：

```python
# src/core/prompts.py

SYSTEM_PROMPT_ZH = """你是一个智能助手..."""
SYSTEM_PROMPT_EN = """You are an intelligent assistant..."""

def get_system_prompt(tools, language=None):
    config = get_config()
    lang = language or config.agent.prompt_language
    
    if lang == "zh":
        return SYSTEM_PROMPT_ZH.format(...)
    else:
        return SYSTEM_PROMPT_EN.format(...)
```

## 上下文工程 / Context Engineering

### 上下文组成 / Context Components

```
┌─────────────────────────────────────┐
│            对话上下文                 │
├─────────────────────────────────────┤
│                                     │
│  [系统消息] System Prompt            │
│  ↓                                  │
│  [用户消息] User: 请帮我计算...       │
│  ↓                                  │
│  [助手消息] Assistant: 好的，让我...  │
│  ↓                                  │
│  [工具结果] Tool: 计算结果是...       │
│  ↓                                  │
│  [助手消息] Assistant: 根据计算...    │
│                                     │
└─────────────────────────────────────┘
```

### 上下文管理策略 / Context Management

1. **记忆窗口** - 限制最大消息数量
2. **摘要压缩** - 对历史对话进行摘要
3. **选择性保留** - 保留重要信息

## 提示词模板 / Prompt Templates

### 任务分解提示词

```python
TASK_DECOMPOSITION_ZH = """请将以下任务分解为具体的步骤：

任务：{task}

请按照以下格式输出：
1. [步骤1描述]
2. [步骤2描述]
...
"""
```

### 错误恢复提示词

```python
ERROR_RECOVERY_ZH = """在执行任务时遇到了错误：

错误信息：{error}
上下文：{context}

请分析错误原因，并提供：
1. 错误原因分析
2. 可能的解决方案
3. 建议的下一步操作
"""
```

## 自定义提示词 / Custom Prompts

您可以在创建 Agent 时提供自定义系统提示词：

```python
custom_prompt = """你是一个专业的数据分析师...

## 你的专长
- 数据清洗
- 统计分析
- 可视化

## 可用工具
{tools_description}
"""

agent = BaseAgent(system_prompt=custom_prompt)
```

## 参考资料 / References

- [Best Practices for Prompt Engineering](https://www.claude.com/blog/best-practices-for-prompt-engineering)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
