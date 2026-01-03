# SAMA-Base_Agent_Implementation
一个基于 Anthropic 官方 Agent 定义实现的 AI Agent 。

> **Agent 定义**：An LLM agent runs tools in a loop to achieve a goal.
> 
> 智能体可以处理复杂的任务，但它们的实现通常很简单。它们通常只是基于环境反馈循环使用工具的逻辑模型（LLM）。

## ✨ 特性 / Features

- 🔄 **工具循环模式** - 实现标准的 Agent 工具循环（observe → think → act）
- 🛠️ **可扩展工具系统** - 易于添加自定义工具
- 🌐 **OpenAI 兼容接口** - 支持 Kimi K2 Thinking 等模型
- 📝 **双语支持** - 中英文提示词和注释
- 💾 **对话记忆** - 支持上下文管理
- 📂 **文件上下文管理** - 动态管理对话中涉及的文件，支持增删改查（NEW! 🎉）
- 🏢 **独立工作区** - Agent 专属工作目录，管理中间文件
- 📊 **详细日志** - 完整的执行过程记录
- 🚦 **任务队列** - 支持批量任务与断点续跑
- 🛰️ **任务仪表盘** - 本地Web面板检索与预览产物
- 🕹️ **赛博像素聊天前端** - 本地网页与 SAMA 实时交互
- 📈 **工具指标统计** - 记录工具调用次数、耗时与错误率
- 📦 **产物归档与清理** - 任务产物打包与清理策略

- 🔔 **通知与回调** - 支持Webhook/命令/提示音
- 📚 **本地知识库** - 索引与检索工作区资料
- 🧩 **流程编排器** - YAML/JSON工作流编排与执行
## 📁 项目结构 / Project Structure

```
SAMA-Base_Agent_Implementation/
├── README.md                      # 项目文档
├── LICENSE                        # MIT 许可证
├── .gitignore                     # Git 忽略配置
├── requirements.txt               # Python 依赖
├── config.yaml                    # 配置文件
├── main.py                        # 主入口
├── launch.py                      # GAIA 批处理入口
├── src/                           # 源代码
│   ├── __init__.py
│   ├── agents/                    # Agent 实现
│   │   ├── __init__.py
│   │   └── base.py               # 基础 Agent
│   ├── cli/                       # CLI 与交互界面
│   │   ├── __init__.py
│   │   ├── entry.py              # CLI 入口逻辑
│   │   ├── session.py            # 交互会话与渲染
│   │   ├── commands.py           # 命令路由
│   │   ├── renderer.py           # 输出渲染
│   │   └── state.py              # 会话状态
│   ├── dashboard/                  # 仪表盘模块
│   │   ├── __init__.py
│   │   ├── server.py               # 仪表盘服务端
│   │   └── assets/                 # 前端资源
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
│   ├── webui/                       # 聊天前端模块
│   │   ├── __init__.py
│   │   ├── server.py                # 聊天前端服务端
│   │   └── assets/                  # 前端资源
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
│   ├── tools/                     # 工具模块
│   │   ├── __init__.py
│   │   ├── base.py               # 工具基类
│   │   ├── shell_tool.py         # Shell 命令工具
│   │   ├── unified_file_tool.py  # 文件工具（read/write/list）
│   │   ├── python_tool.py        # Python 执行工具
│   │   ├── search_tool.py        # 搜索工具
│   │   └── todo_tool.py          # 任务管理工具
│   ├── core/                      # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理
│   │   ├── logger.py             # 日志管理
│   │   ├── memory.py             # 对话记忆
│   │   ├── schema.py             # 数据结构
│   │   └── prompts.py            # 提示词模板
│   ├── runtime/                   # 运行时与产物管理
│   │   ├── __init__.py
│   │   ├── artifacts.py          # 任务结果与产物处理
│   │   └── tasks.py              # 任务封装与执行
│   │   ├── metrics.py            # 工具指标统计
│   │   └── queue.py              # 任务队列
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── helpers.py
│       └── document_processor.py
├── dataset/                       # 数据集（可选）
├── workspace/                     # Agent 工作区（运行时生成）
└── outputs/                       # 输出目录（运行时生成）
```

## 🚀 快速开始 / Quick Start

### 1. 安装依赖 / Install Dependencies

```bash
# 克隆项目 / Clone the project
git clone https://github.com/TTAWDTT/SAMA-Base_Agent_Implementation.git
cd SAMA-Base_Agent_Implementation

# 创建虚拟环境（推荐）/ Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖 / Install dependencies
pip install -r requirements.txt
```

如需按模块安装：

```bash
# 仅核心依赖
pip install -r requirements-core.txt

# 工具依赖（搜索等）
pip install -r requirements-tools.txt

# GAIA 与文档处理依赖
pip install -r requirements-gaia.txt

# 开发依赖
pip install -r requirements-dev.txt

# 可选依赖
pip install -r requirements-optional.txt
```

### 2. 配置 API 密钥 / Configure API Key

编辑 `config.yaml` 文件，填入您的 API 密钥：

```yaml
model:
  api_key: "your-api-key-here"  # 替换为您的 API 密钥
  base_url: "https://api.moonshot.cn/v1"  # Kimi API
  model_name: "moonshot-v1-128k"
```

建议将真实密钥写入 `config.local.yaml`（已在 `.gitignore` 中），避免提交到仓库，`config.yaml` 保持占位值即可。

或者设置环境变量：

```bash
export OPENAI_API_KEY="your-api-key-here"
# 或者
export KIMI_API_KEY="your-api-key-here"
```

### 3. 运行 / Run

```bash
# 交互模式 / Interactive mode
python main.py

# 单次查询 / Single query
python main.py -q "计算 123 * 456"

# 查看帮助 / Show help
python main.py --help
```

## 📖 使用指南 / Usage Guide

### 交互模式命令 / Interactive Commands

| 命令 / Command | 说明 / Description |
|----------------|-------------------|
| `exit` / `quit` | 退出程序 / Exit program |
| `reset` | 重置对话 / Reset conversation |
| `status` | 查看 Agent 状态 / View Agent status |
| `files` | 查看文件上下文 / View file context (NEW! 🎉) |

### 任务队列 / Task Queue

```
/queue add "写一份周报"
/queue import tasks.jsonl
/queue run
/queue status
```

### 仪表盘 / Dashboard

```
python main.py --dashboard
/dashboard
```

### 聊天前端 / Chat UI

```
python main.py --chat-ui
/chatui
```

### 模板切换 / Profiles

```
/profile list
/profile use coder
```

### 产物管理 / Artifacts

```
/artifacts archive <task_id>
/artifacts cleanup 50 30
```

### 文件上下文管理 / File Context Management

Agent 支持在对话过程中动态管理文件上下文，适用于需要跨多轮对话引用、更新文件的场景。

Agent supports dynamic file context management during conversations, suitable for scenarios requiring file references and updates across multiple turns.

```python
from src import BaseAgent

# 创建 Agent（自动创建工作区）
agent = BaseAgent()
print(f"工作区: {agent.workspace}")

# 添加文件到上下文
agent.add_file_to_context(
    path="analysis.py",
    content="import pandas as pd",
    abstract="数据分析脚本"
)

# 更新文件
agent.update_file_in_context(
    path="analysis.py",
    content="import pandas as pd\nimport matplotlib.pyplot as plt",
    abstract="数据分析脚本（增加可视化）"
)

# 移除不需要的文件
agent.remove_file_from_context("old_config.json")

# 查看文件摘要
print(agent.get_files_summary())
```

### 代码集成 / Code Integration

```python
from src import BaseAgent

# 创建 Agent
agent = BaseAgent()

# 运行查询
response = agent.run("请帮我计算 2 的 10 次方")

# 获取结果
print(response.final_answer)
print(f"执行了 {response.total_iterations} 次迭代")
```

### 添加自定义工具 / Add Custom Tool

```python
from src.tools import BaseTool, ToolInput
from pydantic import Field

class MyToolInput(ToolInput):
    param1: str = Field(description="参数1描述")

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的自定义工具"
    description_zh = "我的自定义工具"
    description_en = "My custom tool"
    input_schema = MyToolInput
    
    def _run(self, param1: str) -> str:
        # 实现工具逻辑
        return f"处理结果: {param1}"

# 添加到 Agent
agent = BaseAgent()
agent.add_tool(MyTool)
```

### 任务产物与历史 / Task Artifacts & History

默认会在 `outputs/` 目录生成任务产物与索引：

- `outputs/{task_id}/result.json`：任务执行结果
- `outputs/{task_id}/answer.txt`：最终回复文本
- `outputs/task_history.jsonl`：历史任务流水
- `outputs/task_index.json`：任务索引与产物清单
- `outputs/workflows/`：工作流图（可在配置中关闭）

## 🛠️ 内置工具 / Built-in Tools

| 工具 / Tool | 说明 / Description |
|-------------|-------------------|
| `shell` | 执行 Shell 命令（支持白名单） |
| `file` | 文件读写与列目录 |
| `python` | Python 代码执行 |
| `web_search` | 网络搜索（需配置） |
| `todo` | 任务管理 |

## ⚙️ 配置说明 / Configuration

支持多层配置加载：`config.yaml` + `config.local.yaml` + `config.d/*.yaml`，后者优先级更高。

角色模板可在 `profiles` 配置段或 `profiles/` 目录中定义，并通过 `active_profile` 或 `/profile use <name>` 切换。



详细配置请参见 `config.yaml` 文件中的注释。

主要配置项：

- **model**: 模型配置（API密钥、URL、参数等）
- **agent**: Agent配置（最大迭代次数、语言等）
- **tools**: 工具配置（启用/禁用、参数等）
- **logging**: 日志配置（级别、输出等）
- **memory**: 记忆配置（是否启用、最大条数等）

## 📚 参考文档 / References

- [Building Effective Agents - Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
- [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Best Practices for Prompt Engineering](https://www.claude.com/blog/best-practices-for-prompt-engineering)
- [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)

## 🤝 贡献 / Contributing

欢迎提交 Issue 和 Pull Request！

## 📄 许可证 / License

MIT License - 详见 [LICENSE](LICENSE) 文件
