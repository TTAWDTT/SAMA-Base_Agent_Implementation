# Python 新手教学：改进 Agent 上下文管理 / Python Beginner Tutorial

## 📘 课程目标 / Learning Objectives

学习如何：
1. 理解 Python 类和方法
2. 修改现有代码
3. 添加新功能
4. 调试和测试

---

## 第一课：理解当前的代码结构

### 1.1 什么是类（Class）？

类就像一个"模板"或"蓝图"，用来创建对象。

```python
# 比如：汽车类
class Car:
    def __init__(self, color):  # __init__ 是"初始化方法"，创建对象时自动调用
        self.color = color      # self.color 是"属性"，存储汽车颜色
    
    def drive(self):            # drive 是"方法"，汽车的功能
        print(f"开着{self.color}的车")

# 使用类创建对象
my_car = Car("红色")
my_car.drive()  # 输出：开着红色的车
```

### 1.2 我们的 ConversationMemory 类

```python
# 在 src/core/memory.py 中
class ConversationMemory:
    def __init__(self):
        self.messages = []          # 存储对话消息的列表
        self.files = {}             # 存储文件上下文的字典
        self.system_message = None  # 系统消息
```

**关键概念**：
- `self` 表示"这个对象自己"
- `self.messages` 就是"这个对象的消息列表"
- `[]` 表示空列表，`{}` 表示空字典

---

## 第二课：问题分析

### 2.1 问题 1：文件上下文没有被使用

**现状**：
```python
def get_openai_messages(self) -> List[Dict[str, str]]:
    """获取OpenAI格式的消息"""
    return [msg.to_openai_format() for msg in self.get_messages()]
```

这个方法只返回 `self.messages`，没有包含 `self.files`（文件上下文）。

**解决方案**：
我们需要在返回消息之前，把文件上下文也加进去。

### 2.2 问题 2：上下文输出混乱

**现状**：
```python
⚙️ [1] Role: system
Content: 很长很长的系统提示词...

👤 [2] Role: user
Content: 计算 123 + 456

🤖 [3] Role: assistant
...
```

**问题**：系统消息太长，难以阅读。

**解决方案**：
- 系统消息只显示摘要
- 其他消息显示完整内容（但限制长度）

### 2.3 问题 3：上下文顺序不合理

**现状**：
```
系统消息 → 用户消息 → 助手消息 → 工具消息 → ...
```

**更好的顺序**：
```
系统消息（包含文件上下文）→ 文件内容消息 → 对话历史
```

---

## 第三课：动手修改代码

### 3.1 修改 get_openai_messages 方法

**位置**：`src/core/memory.py` 第 212 行

**修改前**：
```python
def get_openai_messages(self) -> List[Dict[str, str]]:
    return [msg.to_openai_format() for msg in self.get_messages()]
```

**修改后**：
```python
def get_openai_messages(self) -> List[Dict[str, str]]:
    """
    获取OpenAI格式的消息列表（包含文件上下文）
    Get messages in OpenAI format (including file context)
    
    消息顺序 / Message order:
    1. 系统消息（包含文件摘要）/ System message (with file summary)
    2. 文件内容消息（如果有）/ File content messages (if any)
    3. 对话历史 / Conversation history
    """
    messages = []
    
    # 1. 添加系统消息 / Add system message
    if self.system_message:
        messages.append(self.system_message.to_openai_format())
    
    # 2. 添加文件内容作为独立消息 / Add file contents as separate messages
    if self.files:
        file_context_msg = self._build_file_context_message()
        if file_context_msg:
            messages.append(file_context_msg)
    
    # 3. 添加对话历史 / Add conversation history
    for msg in self.messages:
        messages.append(msg.to_openai_format())
    
    return messages
```

**解释**：
- `messages = []`：创建一个空列表来存储消息
- `if self.system_message:`：如果有系统消息，就添加
- `if self.files:`：如果有文件上下文，就构建文件消息
- `for msg in self.messages:`：遍历所有对话消息并添加

### 3.2 添加新方法：构建文件上下文消息

**在 ConversationMemory 类中添加这个新方法**：

```python
def _build_file_context_message(self) -> Optional[Dict[str, str]]:
    """
    构建包含文件内容的消息 / Build message containing file contents
    
    Returns:
        Optional[Dict]: 文件上下文消息 / File context message
    """
    if not self.files:
        return None
    
    # 构建文件内容文本
    file_contents = []
    file_contents.append("## 📁 当前文件上下文 / Current File Context\n")
    
    for path, file_ctx in self.files.items():
        file_contents.append(f"\n### 文件 / File: `{path}`")
        file_contents.append(f"**摘要 / Abstract**: {file_ctx.abstract}")
        
        # 如果有内容，显示内容
        if file_ctx.content:
            # 限制内容长度，避免上下文过长
            max_len = 2000  # 最多2000字符
            content = file_ctx.content
            if len(content) > max_len:
                # 显示前面1000字符 + 后面1000字符
                content = content[:1000] + "\n\n[... 省略中间部分 ...]\n\n" + content[-1000:]
            
            file_contents.append(f"```\n{content}\n```")
        
        # 如果有元数据，显示元数据
        if file_ctx.metadata:
            file_contents.append(f"**元数据 / Metadata**: {file_ctx.metadata}")
        
        file_contents.append("\n" + "-" * 60)
    
    # 构建消息
    return {
        "role": "system",
        "content": "\n".join(file_contents)
    }
```

**逐行解释**：

```python
if not self.files:
    return None
```
- `not self.files`：如果文件字典为空（没有文件）
- `return None`：返回 None（表示没有文件消息）

```python
file_contents = []
file_contents.append("## 📁 当前文件上下文 / Current File Context\n")
```
- `file_contents = []`：创建一个空列表来存储文本行
- `.append(...)`：向列表添加一行文本

```python
for path, file_ctx in self.files.items():
```
- `for ... in ...`：遍历循环
- `self.files.items()`：获取字典的所有键值对
- `path`：文件路径（键）
- `file_ctx`：文件上下文对象（值）

```python
if len(content) > max_len:
    content = content[:1000] + "\n\n[... 省略 ...]\n\n" + content[-1000:]
```
- `len(content)`：获取字符串长度
- `content[:1000]`：取前1000个字符（切片）
- `content[-1000:]`：取后1000个字符
- `+`：连接字符串

```python
return {
    "role": "system",
    "content": "\n".join(file_contents)
}
```
- `{}`：创建字典
- `"\n".join(file_contents)`：用换行符连接列表中的所有文本

### 3.3 改进 _print_current_context 方法

**位置**：`src/agents/base.py` 第 755 行

**修改思路**：
1. 系统消息只显示前200字符
2. 文件消息突出显示
3. 用户/助手消息显示完整

```python
def _print_current_context(self, messages: List[Dict]) -> None:
    """
    打印当前传入LLM的上下文（改进版）
    Print current context sent to LLM (improved)
    """
    print("\n" + "="*80)
    print("📋 当前上下文 / Current Context")
    print("="*80)
    
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 根据角色使用不同的图标
        role_icons = {
            "system": "⚙️ 系统",
            "user": "👤 用户", 
            "assistant": "🤖 助手",
            "tool": "🔧 工具"
        }
        role_display = role_icons.get(role, f"❓ {role}")
        
        print(f"\n[{i}] {role_display}")
        print("-" * 80)
        
        # 根据角色和内容长度决定显示方式
        if role == "system":
            # 系统消息：检查是否是文件上下文
            if "📁 当前文件上下文" in content:
                print("📁 文件上下文消息")
                # 显示文件列表
                lines = content.split('\n')
                for line in lines[:20]:  # 只显示前20行
                    print(f"  {line}")
                if len(lines) > 20:
                    print(f"  ... 还有 {len(lines) - 20} 行")
            else:
                # 普通系统消息，只显示摘要
                print(f"内容长度: {len(content)} 字符")
                print(f"预览: {content[:200]}...")
        
        elif len(content) > 500:
            # 内容过长，显示前后部分
            print(f"内容长度: {len(content)} 字符")
            print(f"--- 开头部分 ---")
            print(content[:250])
            print(f"\n... [省略 {len(content) - 500} 字符] ...\n")
            print(f"--- 结尾部分 ---")
            print(content[-250:])
        else:
            # 内容不长，完整显示
            print(content)
        
        # 显示工具调用信息
        if "tool_calls" in msg:
            print(f"\n🔧 工具调用: {len(msg['tool_calls'])} 个")
            for tc in msg['tool_calls']:
                func_name = tc.get('function', {}).get('name', 'unknown')
                print(f"   • {func_name}")
        
        # 显示工具名称
        if role == "tool" and "name" in msg:
            print(f"工具名称: {msg['name']}")
    
    # 统计信息
    print("\n" + "="*80)
    print("📊 统计信息 / Statistics")
    print("="*80)
    
    total_chars = sum(len(msg.get("content", "")) for msg in messages)
    system_count = sum(1 for msg in messages if msg.get("role") == "system")
    user_count = sum(1 for msg in messages if msg.get("role") == "user")
    assistant_count = sum(1 for msg in messages if msg.get("role") == "assistant")
    tool_count = sum(1 for msg in messages if msg.get("role") == "tool")
    
    print(f"消息总数 / Total messages: {len(messages)}")
    print(f"  ⚙️  系统消息: {system_count}")
    print(f"  👤 用户消息: {user_count}")
    print(f"  🤖 助手消息: {assistant_count}")
    print(f"  🔧 工具消息: {tool_count}")
    print(f"总字符数 / Total characters: {total_chars:,}")
    print(f"估计token数 / Estimated tokens: ~{total_chars // 4:,}")
    print("="*80 + "\n")
```

**新概念解释**：

```python
for i, msg in enumerate(messages, 1):
```
- `enumerate(..., 1)`：遍历时同时获取索引，从1开始计数
- `i`：索引（1, 2, 3, ...）
- `msg`：消息内容

```python
role_icons = {
    "system": "⚙️ 系统",
    "user": "👤 用户"
}
role_display = role_icons.get(role, f"❓ {role}")
```
- 创建一个字典，存储角色和对应的图标
- `.get(role, default)`：从字典获取值，如果找不到就用默认值

```python
if "📁 当前文件上下文" in content:
```
- `in`：检查字符串是否包含某个子字符串

```python
lines = content.split('\n')
```
- `.split('\n')`：按换行符分割字符串，返回一个列表

---

## 第四课：实际操作步骤

### 步骤 1：打开文件

1. 打开 VS Code（或其他编辑器）
2. 打开项目文件夹 `SAMA-Base_Agent_Implementation`
3. 在左侧文件树中找到 `src/core/memory.py`

### 步骤 2：找到要修改的位置

1. 按 `Ctrl + F`（Windows）或 `Cmd + F`（Mac）打开搜索
2. 搜索 `def get_openai_messages`
3. 找到第 212 行左右的方法

### 步骤 3：修改代码

1. 选中整个 `get_openai_messages` 方法
2. 删除旧代码
3. 粘贴新代码（从上面复制）

### 步骤 4：添加新方法

1. 在 `get_openai_messages` 方法下面
2. 添加一个空行
3. 粘贴 `_build_file_context_message` 方法

### 步骤 5：保存和测试

1. 按 `Ctrl + S`（Windows）或 `Cmd + S`（Mac）保存
2. 在终端运行：`python main.py -q "测试"`
3. 检查是否有错误

---

## 第五课：调试技巧

### 5.1 如果出现错误

**常见错误 1：缩进错误**
```
IndentationError: expected an indented block
```

**解决**：检查代码缩进，Python 使用4个空格缩进。

**常见错误 2：语法错误**
```
SyntaxError: invalid syntax
```

**解决**：检查括号、引号是否配对。

### 5.2 添加调试输出

在代码中添加 `print()` 来查看变量值：

```python
def _build_file_context_message(self):
    print(f"[DEBUG] 文件数量: {len(self.files)}")  # 调试输出
    
    if not self.files:
        return None
    
    # ... 其他代码
```

### 5.3 使用 Python 交互式测试

```bash
python
>>> from src.core.memory import ConversationMemory
>>> memory = ConversationMemory()
>>> memory.add_user_message("测试")
>>> print(len(memory.messages))
1
```

---

## 第六课：完整的修改清单

为了帮助你，我把所有要修改的地方列成清单：

### ✅ 任务清单

- [ ] 修改 `src/core/memory.py` 的 `get_openai_messages` 方法
- [ ] 添加 `src/core/memory.py` 的 `_build_file_context_message` 方法
- [ ] 修改 `src/agents/base.py` 的 `_print_current_context` 方法
- [ ] 保存所有文件
- [ ] 运行测试：`python main.py -q "测试"`
- [ ] 检查没有错误
- [ ] 完成！🎉

---

## 附录：Python 基础知识速查

### 数据类型

```python
# 字符串
name = "SAMA"
greeting = f"你好，{name}"  # f-string，格式化字符串

# 数字
count = 10
price = 19.99

# 列表
items = ["苹果", "香蕉", "橙子"]
items.append("葡萄")  # 添加元素

# 字典
person = {"name": "张三", "age": 25}
print(person["name"])  # 输出：张三
```

### 条件语句

```python
if age >= 18:
    print("成年人")
elif age >= 13:
    print("青少年")
else:
    print("儿童")
```

### 循环

```python
# for 循环
for i in range(5):  # 0, 1, 2, 3, 4
    print(i)

# 遍历列表
for item in items:
    print(item)

# 遍历字典
for key, value in person.items():
    print(f"{key}: {value}")
```

### 函数

```python
def add(a, b):
    """计算两数之和"""
    return a + b

result = add(3, 5)  # 8
```

### 类和对象

```python
class Dog:
    def __init__(self, name):
        self.name = name
    
    def bark(self):
        print(f"{self.name}：汪汪！")

my_dog = Dog("旺财")
my_dog.bark()  # 输出：旺财：汪汪！
```

---

## 总结 / Summary

恭喜你完成了这个教程！你学会了：

1. ✅ 理解 Python 类和方法
2. ✅ 修改现有代码
3. ✅ 添加新功能
4. ✅ 基本的调试技巧

继续加油！💪

---

**下一步学习资源**：
- [Python 官方教程](https://docs.python.org/zh-cn/3/tutorial/)
- [廖雪峰 Python 教程](https://www.liaoxuefeng.com/wiki/1016959663602400)
