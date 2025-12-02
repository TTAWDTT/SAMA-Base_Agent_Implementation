#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# AI Agent 主入口 / AI Agent Main Entry Point
# ==============================================================================
# 使用方法 / Usage:
#   python main.py                    # 交互模式 / Interactive mode
#   python main.py --help             # 显示帮助 / Show help
#   python main.py -q "你好"          # 单次查询 / Single query
# ==============================================================================

import argparse
import sys
import io
from typing import Optional

from src import BaseAgent, get_config, init_logging, get_logger

# 修复 Windows 编码问题 / Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def create_agent() -> BaseAgent:
    """
    创建Agent实例 / Create Agent instance
    
    Returns:
        BaseAgent: Agent实例 / Agent instance
    """
    return BaseAgent()


def interactive_mode(agent: BaseAgent) -> None:
    """
    交互模式 / Interactive mode
    
    Args:
        agent: Agent实例 / Agent instance
    """
    logger = get_logger("main")
    
    print("\n" + "=" * 60)
    print("🤖 AI Agent 交互模式 / Interactive Mode")
    print("=" * 60)
    print("输入您的问题，输入 'exit' 或 'quit' 退出")
    print("Enter your question, type 'exit' or 'quit' to exit")
    print("输入 'reset' 重置对话 / Type 'reset' to reset conversation")
    print("输入 'status' 查看状态 / Type 'status' to view status")
    print("输入 '/context' 切换显式上下文模式 / Type '/context' to toggle verbose context")
    print("输入 'files' 查看文件上下文 / Type 'files' to view file context")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # 获取用户输入 / Get user input
            user_input = input("👤 You: ").strip()
            
            # 检查退出命令 / Check exit command
            if user_input.lower() in ["exit", "quit", "退出"]:
                print("\n再见！/ Goodbye! 👋")
                break
            
            # 检查重置命令 / Check reset command
            if user_input.lower() in ["reset", "重置"]:
                agent.reset()
                print("✅ 对话已重置 / Conversation reset\n")
                continue
            
            # 检查状态命令 / Check status command
            if user_input.lower() in ["status", "状态"]:
                status = agent.get_status()
                print(f"\n📊 Agent状态 / Status:")
                for key, value in status.items():
                    print(f"  - {key}: {value}")
                print()
                continue
            
            # 检查显式上下文命令 / Check verbose context command
            if user_input.lower() in ["/context", "/ctx"]:
                is_enabled = agent.toggle_verbose_context()
                status_text = "开启 / ENABLED" if is_enabled else "关闭 / DISABLED"
                print(f"\n📋 显式上下文模式已{status_text}")
                print("   Verbose context mode {status_text}")
                if is_enabled:
                    print("   每次迭代都会显示传入LLM的上下文")
                    print("   Context sent to LLM will be displayed in each iteration\n")
                else:
                    print()
                continue
            
            # 检查文件命令 / Check files command
            if user_input.lower() in ["files", "文件"]:
                files_summary = agent.get_files_summary()
                print(f"\n📁 {files_summary}\n")
                continue
            
            # 空输入跳过 / Skip empty input
            if not user_input:
                continue
            # 简单防护：如果用户只输入 'file' 等易触发的单词，给出提示并跳过
            if user_input.strip().lower() in ["file", "文件"]:
                print("⚠️  检测到可能的命令：请使用 'files' 查看文件上下文或 '/context' 切换上下文模式。示例：files 或 /context")
                continue
            
            # 运行Agent / Run Agent
            print("\n🤔 思考中... / Thinking...\n")
            response = agent.run(user_input)
            
            # 显示思考过程 / Display thinking process
            if response.steps:
                for step in response.steps:
                    if step.thinking:
                        print(f"\n💭 【思考过程 / Thinking Process - 步骤 {step.step_number}】")
                        print(f"{step.thinking}")
                        print("-" * 60)
            
            # 显示响应 / Display response
            print(f"\n🤖 Agent: {response.final_answer}")
            
            # 显示执行信息 / Display execution info
            if response.steps:
                print(f"\n📝 执行了 {response.total_iterations} 次迭代，"
                      f"耗时 {response.execution_time:.2f} 秒")
                print(f"   Executed {response.total_iterations} iterations, "
                      f"took {response.execution_time:.2f} seconds\n")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 中断 / Interrupted")
            print("输入 'exit' 退出或继续输入 / Type 'exit' to quit or continue")
            continue
        except Exception as e:
            logger.error(f"错误 / Error: {str(e)}")
            print(f"\n❌ 发生错误 / Error occurred: {str(e)}\n")


def single_query(agent: BaseAgent, query: str) -> None:
    """
    单次查询模式 / Single query mode
    
    Args:
        agent: Agent实例 / Agent instance
        query: 用户查询 / User query
    """
    response = agent.run(query)
    
    # 显示思考过程 / Display thinking process
    if response.steps:
        print("\n" + "=" * 60)
        print("💭 思考过程 / Thinking Process:")
        print("=" * 60)
        for step in response.steps:
            if step.thinking:
                print(f"\n【步骤 {step.step_number}】")
                print(step.thinking)
                print("-" * 60)
    
    print("\n" + "=" * 60)
    print("🤖 Agent Response:")
    print("=" * 60)
    print(response.final_answer)
    print("=" * 60)
    
    if response.success:
        print(f"✅ 成功 / Success | 迭代 / Iterations: {response.total_iterations} | "
              f"耗时 / Time: {response.execution_time:.2f}s")
    else:
        print(f"❌ 失败 / Failed: {response.error_message}")


def main():
    """
    主函数 / Main function
    """
    # 解析命令行参数 / Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Agent - 一个基于LLM的智能助手 / An LLM-based intelligent assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  python main.py                    # 交互模式 / Interactive mode
  python main.py -q "计算 2+2"      # 单次查询 / Single query
  python main.py --verbose          # 详细输出模式 / Verbose mode

更多信息请参阅 README.md / For more information, see README.md
        """
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="单次查询模式，直接处理指定问题 / Single query mode, directly process the specified question"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出 / Enable verbose output"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="AI Agent v0.1.0"
    )
    
    args = parser.parse_args()
    
    # 初始化日志 / Initialize logging
    init_logging()
    logger = get_logger("main")
    
    # 检查配置 / Check configuration
    config = get_config()
    if not config.model.api_key or config.model.api_key == "your-api-key-here":
        print("\n⚠️  警告 / Warning:")
        print("请在 config.yaml 中配置您的 API 密钥")
        print("Please configure your API key in config.yaml")
        print("或设置环境变量 OPENAI_API_KEY / Or set environment variable OPENAI_API_KEY\n")
        
        # 在非查询模式下仍然允许进入交互模式，方便测试
        # Still allow entering interactive mode in non-query mode for testing
        if args.query:
            sys.exit(1)
    
    try:
        # 创建Agent / Create Agent
        logger.info("正在初始化Agent / Initializing Agent...")
        agent = create_agent()
        
        # 根据参数选择模式 / Select mode based on arguments
        if args.query:
            # 单次查询模式 / Single query mode
            single_query(agent, args.query)
        else:
            # 交互模式 / Interactive mode
            interactive_mode(agent)
            
    except KeyboardInterrupt:
        print("\n\n👋 再见 / Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序错误 / Program error: {str(e)}")
        print(f"\n❌ 程序错误 / Program error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
