# Agent 概念 / Agent Concept

## 什么是 Agent？ / What is an Agent?

根据 Anthropic 的定义：

> **An LLM agent runs tools in a loop to achieve a goal.**
> 
> 一个 LLM Agent 在循环中运行工具来实现目标。

### 核心特征 / Core Characteristics

1. **目标导向** - Agent 有明确的任务目标
2. **工具使用** - Agent 可以调用工具来完成任务
3. **循环执行** - Agent 在循环中不断思考和行动
4. **环境反馈** - Agent 根据工具执行结果调整策略

### Agent 循环 / Agent Loop

```
┌─────────────────────────────────────┐
│                                     │
│   ┌──────────┐                      │
│   │  用户输入  │                      │
│   └────┬─────┘                      │
│        │                            │
│        ▼                            │
│   ┌──────────┐                      │
│   │   思考    │ ◄──────┐            │
│   └────┬─────┘        │            │
│        │              │            │
│        ▼              │            │
│   ┌──────────┐        │            │
│   │ 选择工具  │        │            │
│   └────┬─────┘        │            │
│        │              │            │
│        ▼              │            │
│   ┌──────────┐        │            │
│   │ 执行工具  │        │            │
│   └────┬─────┘        │            │
│        │              │            │
│        ▼              │            │
│   ┌──────────┐        │            │
│   │ 观察结果  │────────┘            │
│   └────┬─────┘                      │
│        │                            │
│        ▼                            │
│   ┌──────────┐                      │
│   │ 任务完成？│                      │
│   └────┬─────┘                      │
│        │                            │
│        ▼                            │
│   ┌──────────┐                      │
│   │  最终响应  │                      │
│   └──────────┘                      │
│                                     │
└─────────────────────────────────────┘
```

## 为什么不使用工作流？ / Why Not Workflows?

工作流（Workflows）会限制 Agent 的灵活性：

| 特征 | 工作流 | Agent |
|------|--------|-------|
| 执行路径 | 预定义 | 动态 |
| 灵活性 | 低 | 高 |
| 复杂任务 | 需要预设所有路径 | 自适应 |
| 错误恢复 | 依赖预设 | 自主决策 |

## 本项目的 Agent 实现 / Agent Implementation

```python
class BaseAgent:
    def run(self, user_input: str) -> AgentResponse:
        # Agent 主循环
        while self.current_step < self.max_iterations:
            # 1. 调用 LLM 思考
            response = self._call_llm(messages)
            
            # 2. 检查是否有工具调用
            if response.tool_calls:
                # 3. 执行工具
                results = self._process_tool_calls(response.tool_calls)
                # 4. 将结果加入上下文
                self._add_results_to_context(results)
            else:
                # 5. 没有工具调用，任务完成
                return AgentResponse(final_answer=response.content)
        
        # 达到最大迭代次数
        return AgentResponse(error="Max iterations reached")
```

## 参考资料 / References

- [Building Effective Agents - Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
