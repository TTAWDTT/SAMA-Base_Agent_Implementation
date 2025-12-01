# 工具系统 / Tool System

## 概述 / Overview

工具是 Agent 与外部世界交互的接口。Agent 通过调用工具来：
- 获取信息（如搜索、读取文件）
- 执行操作（如写入文件、运行代码）
- 进行计算（如数学计算、日期计算）

## 工具架构 / Tool Architecture

```
┌──────────────────────────────────────┐
│             BaseTool                 │
├──────────────────────────────────────┤
│ - name: str                          │
│ - description: str                   │
│ - description_zh: str                │
│ - description_en: str                │
│ - input_schema: Type[ToolInput]      │
├──────────────────────────────────────┤
│ + _run(**kwargs) -> Any    [抽象]    │
│ + run(**kwargs) -> ToolResult        │
│ + get_schema() -> Dict               │
└──────────────────────────────────────┘
           ▲
           │ 继承
    ┌──────┴───────┬─────────────┬─────────────┐
    │              │             │             │
┌───┴───┐    ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐
│ File  │    │  Code    │  │ Calc     │  │ Search   │
│ Tools │    │ Executor │  │ ulator   │  │ Tool     │
└───────┘    └──────────┘  └──────────┘  └──────────┘
```

## 内置工具 / Built-in Tools

### 文件工具 / File Tools

| 工具 | 功能 | 示例 |
|------|------|------|
| `read_file` | 读取文件 | `read_file(file_path="./test.txt")` |
| `write_file` | 写入文件 | `write_file(file_path="./test.txt", content="Hello")` |
| `list_directory` | 列出目录 | `list_directory(directory_path="./")` |

### 代码执行工具 / Code Execution Tools

| 工具 | 功能 | 示例 |
|------|------|------|
| `execute_code` | 执行代码文件 | `execute_code(code="print('hi')", language="python")` |
| `python_repl` | Python REPL | `python_repl(code="2 + 2")` |

### 计算工具 / Calculator Tools

| 工具 | 功能 | 示例 |
|------|------|------|
| `calculator` | 数学计算 | `calculator(expression="sqrt(16) + 2")` |

### 日期时间工具 / DateTime Tools

| 工具 | 功能 | 示例 |
|------|------|------|
| `get_current_time` | 获取当前时间 | `get_current_time()` |
| `date_calculator` | 日期计算 | `date_calculator(date="2024-01-01", days=30)` |
| `time_difference` | 计算时间差 | `time_difference(date1="2024-01-01", date2="2024-12-31")` |

### 搜索工具 / Search Tools

| 工具 | 功能 | 说明 |
|------|------|------|
| `web_search` | 网络搜索 | 需要配置API |
| `duckduckgo_search` | DuckDuckGo搜索 | 免费，需安装库 |

## 创建自定义工具 / Creating Custom Tools

### 步骤 1: 定义输入Schema

```python
from pydantic import Field
from src.tools.base import ToolInput

class WeatherInput(ToolInput):
    """天气查询输入"""
    city: str = Field(description="城市名称")
    unit: str = Field(default="celsius", description="温度单位")
```

### 步骤 2: 创建工具类

```python
from src.tools.base import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取指定城市的天气信息"
    description_zh = "获取指定城市的天气信息"
    description_en = "Get weather information for a specified city"
    input_schema = WeatherInput
    
    def _run(self, city: str, unit: str = "celsius") -> str:
        # 实现天气查询逻辑
        # 这里是示例，实际需要调用天气API
        return f"{city}的天气：晴，温度：25°C"
```

### 步骤 3: 注册工具

```python
# 在 src/tools/__init__.py 中添加
from src.tools.weather_tool import WeatherTool

# 添加到工具列表
ALL_TOOLS.append(WeatherTool)
```

### 步骤 4: 使用工具

```python
from src import BaseAgent
from src.tools.weather_tool import WeatherTool

agent = BaseAgent()
agent.add_tool(WeatherTool)

response = agent.run("北京今天天气怎么样？")
```

## 工具执行流程 / Tool Execution Flow

```
┌─────────────────────────────────────────────────┐
│                 工具调用流程                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. LLM 返回工具调用请求                          │
│     {                                           │
│       "tool_calls": [{                          │
│         "function": {                           │
│           "name": "calculator",                 │
│           "arguments": "{\"expression\":\"2+2\"}"│
│         }                                       │
│       }]                                        │
│     }                                           │
│                                                 │
│  2. Agent 解析工具调用                           │
│     tool_name = "calculator"                    │
│     arguments = {"expression": "2+2"}           │
│                                                 │
│  3. Agent 执行工具                              │
│     result = tool.run(**arguments)              │
│                                                 │
│  4. 返回 ToolResult                             │
│     ToolResult(                                 │
│       tool_name="calculator",                   │
│       status=SUCCESS,                           │
│       output="4"                                │
│     )                                           │
│                                                 │
│  5. 将结果加入对话上下文                          │
│     messages.append({                           │
│       "role": "tool",                           │
│       "content": "4"                            │
│     })                                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 安全注意事项 / Security Considerations

1. **路径限制** - 文件工具只能访问配置的目录
2. **代码沙箱** - 代码执行有超时限制
3. **输入验证** - 使用 Pydantic 验证输入
4. **错误处理** - 所有工具都有错误捕获机制
