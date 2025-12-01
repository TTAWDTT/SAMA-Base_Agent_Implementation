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
- 📊 **详细日志** - 完整的执行过程记录

## 📁 项目结构 / Project Structure

```
ai-agent-project/
├── README.md                      # 项目文档
├── LICENSE                        # MIT 许可证
├── .gitignore                     # Git 忽略配置
├── requirements.txt               # Python 依赖
├── config.yaml                    # 配置文件
├── AGENT.md                       # AI 代理指导文件
├── main.py                        # 主入口
├── src/                           # 源代码
│   ├── __init__.py
│   ├── agents/                    # Agent 实现
│   │   ├── __init__.py
│   │   └── base.py               # 基础 Agent
│   ├── tools/                     # 工具模块
│   │   ├── __init__.py
│   │   ├── base.py               # 工具基类
│   │   ├── file_tool.py          # 文件操作工具
│   │   ├── code_executor.py      # 代码执行工具
│   │   ├── calculator.py         # 计算器工具
│   │   ├── search_tool.py        # 搜索工具
│   │   └── datetime_tool.py      # 日期时间工具
│   ├── core/                      # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理
│   │   ├── logger.py             # 日志管理
│   │   ├── memory.py             # 对话记忆
│   │   ├── schema.py             # 数据结构
│   │   └── prompts.py            # 提示词模板
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       └── helpers.py
├── docs/                          # 文档
│   └── guides/
│       └── quickstart.md
└── outputs/                       # 输出目录
    └── logs/
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

### 2. 配置 API 密钥 / Configure API Key

编辑 `config.yaml` 文件，填入您的 API 密钥：

```yaml
model:
  api_key: "your-api-key-here"  # 替换为您的 API 密钥
  base_url: "https://api.moonshot.cn/v1"  # Kimi API
  model_name: "moonshot-v1-128k"
```

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

## 🛠️ 内置工具 / Built-in Tools

| 工具 / Tool | 说明 / Description |
|-------------|-------------------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件内容 |
| `list_directory` | 列出目录内容 |
| `execute_code` | 执行代码 |
| `python_repl` | Python REPL |
| `calculator` | 数学计算 |
| `get_current_time` | 获取当前时间 |
| `date_calculator` | 日期计算 |
| `time_difference` | 时间差计算 |
| `web_search` | 网络搜索（需配置） |
| `duckduckgo_search` | DuckDuckGo 搜索 |

## ⚙️ 配置说明 / Configuration

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
