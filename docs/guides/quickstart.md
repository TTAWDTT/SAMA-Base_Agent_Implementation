# 快速入门指南 / Quick Start Guide

本指南将帮助您快速上手使用 AI Agent。

## 前提条件 / Prerequisites

- Python 3.9+
- pip 包管理器
- API 密钥（支持 Kimi、OpenAI 等）

## 安装步骤 / Installation Steps

### 步骤 1: 克隆项目 / Clone Project

```bash
git clone https://github.com/TTAWDTT/SAMA-Base_Agent_Implementation.git
cd SAMA-Base_Agent_Implementation
```

### 步骤 2: 创建虚拟环境 / Create Virtual Environment

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 步骤 3: 安装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```

### 步骤 4: 配置 API / Configure API

复制配置文件并编辑：

```bash
cp config.yaml config.local.yaml
```

编辑 `config.local.yaml`：

```yaml
model:
  api_key: "your-actual-api-key"  # 替换为真实密钥
  base_url: "https://api.moonshot.cn/v1"
  model_name: "moonshot-v1-128k"
```

或者使用环境变量：

```bash
export OPENAI_API_KEY="your-actual-api-key"
```

### 步骤 5: 运行 Agent / Run Agent

```bash
python main.py
```

## 使用示例 / Usage Examples

### 示例 1: 数学计算 / Math Calculation

```
👤 You: 请帮我计算 (123 + 456) * 789
🤖 Agent: 计算结果是 456831
```

### 示例 2: 代码执行 / Code Execution

```
👤 You: 写一个Python程序打印1到10的偶数
🤖 Agent: [执行代码并返回结果]
```

### 示例 3: 文件操作 / File Operations

```
👤 You: 在 ./workspace 目录下创建一个名为 hello.txt 的文件，内容是 "Hello World"
🤖 Agent: 文件已创建成功
```

### 示例 4: 日期计算 / Date Calculation

```
👤 You: 今天是什么日期？30天后是哪一天？
🤖 Agent: 今天是 2024-XX-XX，30天后是 2024-XX-XX
```

## 常见问题 / FAQ

### Q: API 调用失败怎么办？
A: 请检查：
1. API 密钥是否正确
2. 网络连接是否正常
3. base_url 是否匹配您的模型提供商

### Q: 如何更换模型？
A: 修改 `config.yaml` 中的 `model` 配置：
- `base_url`: 模型 API 地址
- `model_name`: 模型名称

### Q: 如何添加自定义工具？
A: 参见 README.md 中的"添加自定义工具"章节

## 下一步 / Next Steps

- 阅读 [README.md](../../README.md) 了解完整功能
- 查看 [AGENT.md](../../AGENT.md) 了解开发指南
- 探索 `src/tools/` 了解内置工具实现
