#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件上下文管理演示 / File Context Management Demo

展示如何在Agent对话中管理文件上下文
Demonstrates how to manage file context in Agent conversations
"""

import sys
from pathlib import Path

# 添加项目根目录到路径 / Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src import BaseAgent, FileContext
from src.core.logger import get_logger

logger = get_logger("demo")


def main():
    """主函数 / Main function"""
    print("=" * 60)
    print("文件上下文管理演示 / File Context Management Demo")
    print("=" * 60)
    
    # 创建Agent / Create Agent
    agent = BaseAgent()
    print(f"\n[OK] Agent已创建 / Agent created")
    print(f"工作区 / Workspace: {agent.workspace}")
    
    # ============================================================
    # 1. 添加文件到上下文 / Add files to context
    # ============================================================
    print("\n--- 添加文件到上下文 / Adding files to context ---")
    
    agent.add_file_to_context(
        path="data_analysis.py",
        content="""import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('data.csv')
df.describe()
""",
        abstract="数据分析脚本，读取CSV并生成统计信息",
        metadata={"type": "script", "language": "python"}
    )
    
    agent.add_file_to_context(
        path="config.json",
        content='{"api_key": "xxx", "timeout": 30}',
        abstract="配置文件，包含API密钥和超时设置",
        metadata={"type": "config", "format": "json"}
    )
    
    agent.add_file_to_context(
        path="results.txt",
        content="",
        abstract="输出结果文件（待生成）",
        metadata={"type": "output", "status": "pending"}
    )
    
    print(f"\n{agent.get_files_summary()}")
    
    # ============================================================
    # 2. 更新文件内容 / Update file content
    # ============================================================
    print("\n--- 更新文件内容 / Updating file content ---")
    
    agent.update_file_in_context(
        path="results.txt",
        content="Analysis complete: 100 rows processed",
        abstract="输出结果文件（已完成）",
        metadata={"status": "completed"}
    )
    
    print(f"\n{agent.get_files_summary()}")
    
    # ============================================================
    # 3. 模拟文件替换（删除旧版本，添加新版本）/ Simulate file replacement
    # ============================================================
    print("\n--- 文件替换示例 / File replacement example ---")
    
    # 更新脚本后，删除旧版本
    agent.update_file_in_context(
        path="data_analysis.py",
        content="""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns  # 新增

df = pd.read_csv('data.csv')
df.describe()
sns.heatmap(df.corr())  # 新增：相关性热图
""",
        abstract="数据分析脚本v2，增加了相关性热图可视化",
        metadata={"type": "script", "language": "python", "version": "2"}
    )
    
    print(f"\n{agent.get_files_summary()}")
    
    # ============================================================
    # 4. 移除不需要的文件 / Remove unnecessary files
    # ============================================================
    print("\n--- 移除文件 / Removing files ---")
    
    # 配置文件已经被使用，可以移除
    agent.remove_file_from_context("config.json")
    
    print(f"\n{agent.get_files_summary()}")
    
    # ============================================================
    # 5. 列出所有文件路径 / List all file paths
    # ============================================================
    print("\n--- 当前文件列表 / Current file list ---")
    files = agent.list_context_files()
    for i, file_path in enumerate(files, 1):
        print(f"{i}. {file_path}")
    
    # ============================================================
    # 6. 获取特定文件的详细信息 / Get specific file details
    # ============================================================
    print("\n--- 文件详细信息 / File details ---")
    file_ctx = agent.memory.get_file("data_analysis.py")
    if file_ctx:
        print(f"路径 / Path: {file_ctx.path}")
        print(f"摘要 / Abstract: {file_ctx.abstract}")
        print(f"元数据 / Metadata: {file_ctx.metadata}")
        print(f"内容长度 / Content length: {len(file_ctx.content) if file_ctx.content else 0} chars")
    
    # ============================================================
    # 7. 在实际对话中使用 / Use in actual conversation
    # ============================================================
    print("\n--- 在对话中使用文件上下文 / Using file context in conversation ---")
    print("(示例：Agent会在系统提示词中看到这些文件)")
    print("(Example: Agent will see these files in system prompt)")
    
    # Agent的系统提示词已经包含了文件信息
    # 当用户提问时，Agent能够引用这些文件
    print("\n系统提示词包含的文件信息 / File info in system prompt:")
    print(agent.get_files_summary())
    
    print("\n" + "=" * 60)
    print("演示完成 / Demo completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
