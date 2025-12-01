# AGENT.md - AI Agent 指导文件 / AI Agent Guidance File

此文件为 AI 编码助手（如 GitHub Copilot）提供项目指导信息。

## 项目概述 / Project Overview

这是一个基于 Anthropic 官方定义实现的 Python AI Agent 框架：
- **核心理念**：Agent 是在循环中使用工具来实现目标的 LLM
- **设计原则**：简单、可扩展、不使用工作流限制 Agent 自由度

## 代码约定 / Code Conventions

### 注释风格 / Comment Style
- 使用中英双语注释
- 格式：`# 中文说明 / English description`
- 文档字符串使用双语

### 命名约定 / Naming Conventions
- 类名：PascalCase（如 `BaseAgent`, `ToolResult`）
- 函数/方法：snake_case（如 `get_config`, `run_tool`）
- 常量：UPPER_SNAKE_CASE（如 `DEFAULT_TOOLS`）
- 私有方法：前缀下划线（如 `_init_client`）

### 文件组织 / File Organization
```
src/
├── agents/     # Agent 实现
├── tools/      # 工具模块
├── core/       # 核心功能（配置、日志、记忆等）
└── utils/      # 辅助函数
```

## 开发指南 / Development Guidelines

### 添加新工具 / Adding New Tools
1. 在 `src/tools/` 创建新文件
2. 继承 `BaseTool` 类
3. 实现 `_run` 方法
4. 在 `src/tools/__init__.py` 中导出
5. 添加到 `ALL_TOOLS` 或 `DEFAULT_TOOLS`

### 修改提示词 / Modifying Prompts
- 提示词定义在 `src/core/prompts.py`
- 提供中英双版本（`_ZH` 和 `_EN` 后缀）
- 参考 Claude 官方最佳实践

### 配置管理 / Configuration
- 配置定义在 `src/core/config.py`
- 使用 Pydantic 进行验证
- 支持 YAML 配置文件和环境变量

## 常用命令 / Common Commands

```bash
# 运行 Agent（交互模式）
python main.py

# 单次查询
python main.py -q "你的问题"

# 安装依赖
pip install -r requirements.txt

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

## 边界和限制 / Boundaries and Limitations

### 不要做 / Don't
- 不要创建工作流来限制 Agent 行为
- 不要硬编码 API 密钥
- 不要删除双语注释

### 可以做 / Do
- 使用 LangChain 内置工具
- 扩展工具集合
- 优化提示词
- 添加新的 Agent 变体

## 架构决策记录 / Architecture Decision Records

### ADR-001: 使用 OpenAI 兼容接口
- **决策**：使用 OpenAI SDK 调用模型
- **原因**：Kimi K2 等模型支持 OpenAI 兼容接口
- **影响**：需要配置 `base_url`

### ADR-002: 不使用 LangChain Agent/Chain
- **决策**：自行实现 Agent 循环
- **原因**：保持最大灵活性，避免工作流限制
- **影响**：可以使用 LangChain 工具，但不使用其 Agent 框架

### ADR-003: 双语支持
- **决策**：所有注释和提示词提供中英双语
- **原因**：便于中英文用户理解和使用
- **影响**：代码略长，但可读性更好
