#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# GAIA Benchmark 测试启动器
# ==============================================================================
# 使用方法
#   python launch.py                      # 处理默认行（第1行）
#   python launch.py --row 5              # 处理第5行
#   python launch.py --row 1-10           # 处理第1到10行
#   python launch.py --row 1,3,5          # 处理第1、3、5行
#   python launch.py --list               # 列出数据集内容
#   python launch.py --help               # 显示帮助
# ==============================================================================

import argparse
import os
import sys
import io
from pathlib import Path
from typing import Any, List, Optional, Tuple

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src import (
    BaseAgent,
    init_logging,
    get_logger,
)
from src.runtime import (
    snapshot_top_level_files,
    move_top_level_files_to_output,
    update_task_artifact_index,
    TaskRunner,
    TaskSpec,
)


# ==============================================================================
# 常量定义
# ==============================================================================

# 默认数据集路径
DEFAULT_DATASET_PATH = "dataset/data/train-00000-of-00001.parquet"

# 输出目录
OUTPUT_DIR = "outputs"


# ==============================================================================
# 辅助函数
# ==============================================================================

def load_dataset(dataset_path: str) -> Optional[Any]:
    """
    加载数据集 / Load dataset
    
    Args:
        dataset_path: 数据集路径 / Dataset path
        
    Returns:
        DataFrame 或 None / DataFrame or None
    """
    try:
        import pandas as pd
        
        if not os.path.exists(dataset_path):
            print(f"❌ 数据集文件不存在 / Dataset file not found: {dataset_path}")
            return None
        
        # 根据文件类型选择读取方式
        ext = Path(dataset_path).suffix.lower()
        
        if ext == '.parquet':
            try:
                df = pd.read_parquet(dataset_path, engine='fastparquet')
            except ImportError:
                df = pd.read_parquet(dataset_path, engine='pyarrow')
        elif ext == '.csv':
            df = pd.read_csv(dataset_path)
        elif ext == '.json':
            df = pd.read_json(dataset_path)
        else:
            print(f"❌ 不支持的数据集格式 / Unsupported dataset format: {ext}")
            return None
        
        return df
        
    except ImportError as e:
        print(f"❌ 缺少依赖 / Missing dependency: {e}")
        print("   请运行 / Please run: pip install pandas fastparquet pyarrow")
        return None
    except Exception as e:
        print(f"❌ 加载数据集失败 / Failed to load dataset: {e}")
        return None


def parse_row_indices(row_spec: str, max_rows: int) -> List[int]:
    """
    解析行索引规范 / Parse row index specification
    
    支持格式 / Supported formats:
    - 单个数字: "5"
    - 范围: "1-10"
    - 列表: "1,3,5,7"
    - 混合: "1-3,5,7-9"
    
    Args:
        row_spec: 行规范字符串 / Row specification string
        max_rows: 最大行数 / Maximum rows
        
    Returns:
        List[int]: 行索引列表 / List of row indices
    """
    indices = []
    
    for part in row_spec.split(','):
        part = part.strip()
        
        if '-' in part:
            # 范围
            try:
                start, end = map(int, part.split('-'))
                start = max(0, start)
                end = min(max_rows - 1, end)
                indices.extend(range(start, end + 1))
            except ValueError:
                print(f"⚠️  无效的范围格式 / Invalid range format: {part}")
        else:
            # 单个数字
            try:
                idx = int(part)
                if 0 <= idx < max_rows:
                    indices.append(idx)
                else:
                    print(f"⚠️  行索引超出范围 / Row index out of range: {idx} (max: {max_rows - 1})")
            except ValueError:
                print(f"⚠️  无效的行号 / Invalid row number: {part}")
    
    # 去重并排序
    return sorted(set(indices))


def extract_task_info(row: Any) -> Tuple[str, str, List[str]]:
    """
    从数据行提取任务信息 / Extract task info from data row
    
    Args:
        row: 数据行 / Data row
        
    Returns:
        Tuple[str, str, List[str]]: (task_id, prompt, reference_files)
    """
    # 获取任务ID
    task_id = str(row.get('task_id', row.name if hasattr(row, 'name') else 'unknown'))
    
    # 获取提示词
    prompt = str(row.get('prompt', row.get('question', row.get('input', ''))))
    
    # 获取参考文件
    ref_files_raw = row.get('reference_files', row.get('files', row.get('attachments', [])))
    
    # 处理参考文件路径
    reference_files = []
    if isinstance(ref_files_raw, (list, tuple)):
        for file in ref_files_raw:
            if file:  # 过滤空值
                file_path = str(file)
                # 添加 dataset/ 前缀（如果不是绝对路径）
                if not os.path.isabs(file_path) and not file_path.startswith('dataset/'):
                    file_path = f"dataset/{file_path}"
                reference_files.append(file_path)
    elif ref_files_raw and str(ref_files_raw).strip():
        file_path = str(ref_files_raw)
        if not os.path.isabs(file_path) and not file_path.startswith('dataset/'):
            file_path = f"dataset/{file_path}"
        reference_files.append(file_path)
    
    return task_id, prompt, reference_files

# ==============================================================================
# 主处理函数
# ==============================================================================

def process_task(
    task_id: str,
    prompt: str,
    reference_files: List[str],
    runner: TaskRunner,
    logger: Any
) -> Any:
    """
    处理单个任务 / Process single task
    
    Args:
        task_id: 任务ID / Task ID
        prompt: 提示词 / Prompt
        reference_files: 参考文件列表 / Reference file list
        runner: 任务运行器 / Task runner
        logger: 日志器 / Logger
        
    Returns:
        Agent响应 / Agent response
    """
    print(f"\n{'=' * 60}")
    print(f"📋 任务 / Task: {task_id}")
    print(f"{'=' * 60}")
    
    existing_files = []
    if reference_files:
        print(f"?? 发现 {len(reference_files)} 个参考文件 / Found {len(reference_files)} reference files")
        for file_path in reference_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
                print(f"   ? {file_path}")
            else:
                print(f"   ? {file_path} (不存在 / not found)")
    # 显示提示词
    print(f"\n📝 提示词 / Prompt:")
    print(f"   {prompt[:200]}..." if len(prompt) > 200 else f"   {prompt}")
    
    # 运行智能体
    print(f"\n🤖 Agent开始处理... / Agent processing...")
    
    try:
        task = TaskSpec(task_id=task_id, prompt=prompt, reference_files=existing_files)
        result = runner.run_task(task, preprocess=True)
        response = result.response
        
        # 显示结果
        print(f"\n{'=' * 60}")
        print("📊 处理结果 / Result:")
        print(f"{'=' * 60}")
        print(f"✅ 成功 / Success: {response.success}")
        print(f"🔄 迭代次数 / Iterations: {response.total_iterations}")
        print(f"⏱️  耗时 / Time: {response.execution_time:.2f}s")
        print(f"\n💬 最终答案 / Final Answer:")
        print(f"   {response.final_answer[:500]}..." if len(response.final_answer) > 500 else f"   {response.final_answer}")
        
        if result.processed_files:
            print(f"   ?? 已处理 {result.processed_files.get('file_count', 0)} 个文档")
            print(f"   ???  已处理 {result.processed_files.get('image_count', 0)} 张图片")

        runner.save_result(result)
        
        return response
        
    except Exception as e:
        logger.error(f"Agent执行失败 / Agent execution failed: {e}")
        print(f"\n❌ 执行失败 / Execution failed: {e}")
        raise


def list_dataset(df: Any, start: int = 0, count: int = 10) -> None:
    """
    列出数据集内容 / List dataset content
    
    Args:
        df: DataFrame
        start: 起始行 / Start row
        count: 显示数量 / Display count
    """
    print(f"\n📋 数据集信息 / Dataset Info")
    print(f"{'=' * 60}")
    print(f"总行数 / Total rows: {len(df)}")
    print(f"列名 / Columns: {list(df.columns)}")
    print(f"\n{'=' * 60}")
    print(f"数据预览 / Data Preview (rows {start} - {min(start + count, len(df))})")
    print(f"{'=' * 60}\n")
    
    for idx in range(start, min(start + count, len(df))):
        row = df.iloc[idx]
        task_id, prompt, ref_files = extract_task_info(row)
        
        print(f"[{idx}] Task: {task_id}")
        print(f"    Prompt: {prompt[:80]}..." if len(prompt) > 80 else f"    Prompt: {prompt}")
        print(f"    Files: {len(ref_files)} 个")
        print()


# ==============================================================================
# 主函数
# ==============================================================================

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="GAIA Benchmark 测试启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python launch.py                      # 处理第0行
  python launch.py --row 5              # 处理第5行
  python launch.py --row 1-10           # 处理第1到10行
  python launch.py --row 1,3,5          # 处理指定行
  python launch.py --list               # 列出数据集
  python launch.py --list --start 10    # 从第10行开始列出

更多信息请参阅 GAIA_Benchmark_Preparation_Guide.md
        """
    )
    
    parser.add_argument(
        "-r", "--row",
        type=str,
        default="0",
        help="要处理的行号（支持范围和列表）"
    )
    
    parser.add_argument(
        "-d", "--dataset",
        type=str,
        default=DEFAULT_DATASET_PATH,
        help="数据集路径"
    )
    
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="列出数据集内容"
    )
    
    parser.add_argument(
        "-s", "--start",
        type=int,
        default=0,
        help="列表起始行（与--list一起使用）"
    )
    
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=10,
        help="列表显示数量（与--list一起使用）"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="GAIA Launcher v0.1.0"
    )
    
    args = parser.parse_args()
    
    # 初始化日志
    init_logging()
    logger = get_logger("launch")
    
    # 加载数据集
    print(f"\n📂 加载数据集 / Loading dataset: {args.dataset}")
    df = load_dataset(args.dataset)
    
    if df is None:
        sys.exit(1)
    
    print(f"   ✓ 加载成功 / Loaded successfully: {len(df)} 行 / rows")
    
    # 列表模式
    if args.list:
        list_dataset(df, args.start, args.count)
        return
    
    # 解析行索引
    row_indices = parse_row_indices(args.row, len(df))
    
    if not row_indices:
        print("❌ 未找到有效的行索引 / No valid row indices found")
        sys.exit(1)
    
    print(f"📌 将处理 {len(row_indices)} 个任务 / Will process {len(row_indices)} tasks")
    print(f"   行号 / Rows: {row_indices}")
    
    # 创建智能体
    print(f"\n🤖 初始化Agent / Initializing Agent...")
    
    try:
        agent = BaseAgent()
        runner = TaskRunner(agent, logger=logger, output_dir=OUTPUT_DIR)
        print("   ✓ Agent初始化成功 / Agent initialized successfully")
    except Exception as e:
        print(f"❌ Agent初始化失败 / Agent initialization failed: {e}")
        sys.exit(1)
    
    # 处理任务
    results = []
    
    for idx in row_indices:
        try:
            # 快照 workspace/ 根目录在任务开始前的文件列表（仅顶层文件）
            workspace_dir = project_root / "workspace"
            _before_snapshot = snapshot_top_level_files(workspace_dir)
            _root_before_snapshot = snapshot_top_level_files(project_root)

            row = df.iloc[idx]
            task_id, prompt, reference_files = extract_task_info(row)

            response = process_task(task_id, prompt, reference_files, runner, logger)
            results.append({
                "row": idx,
                "task_id": task_id,
                "success": response.success,
            })

            # 快照任务结束后 workspace/ 根目录文件列表，移动新增的顶层文件到 outputs/{task_id}
            _after_snapshot = snapshot_top_level_files(workspace_dir)
            _root_after_snapshot = snapshot_top_level_files(project_root)
            new_files = set(_after_snapshot) - set(_before_snapshot)
            root_new_files = set(_root_after_snapshot) - set(_root_before_snapshot)
            if new_files:
                print(f"\n📦 发现 {len(new_files)} 个新文件在 workspace/ 根目录，将移动到 outputs/{task_id}...")
                move_top_level_files_to_output(
                    workspace_dir,
                    new_files,
                    task_id,
                    project_root,
                    "workspace",
                    output_dir=OUTPUT_DIR
                )
            if root_new_files:
                print(f"\n📦 发现 {len(root_new_files)} 个新文件在根目录，将移动到 outputs/{task_id}...")
                move_top_level_files_to_output(
                    project_root,
                    root_new_files,
                    task_id,
                    project_root,
                    "",
                    output_dir=OUTPUT_DIR
                )

            update_task_artifact_index(task_id, output_dir=OUTPUT_DIR)
            # 重置智能体状态
            agent.reset()

        except Exception as e:
            logger.error(f"任务处理失败 / Task processing failed: row={idx}, error={e}")
            results.append({
                "row": idx,
                "task_id": task_id if 'task_id' in locals() else 'unknown',
                "success": False,
                "error": str(e),
            })
    
    # 显示汇总
    print(f"\n{'=' * 60}")
    print("📊 处理汇总 / Processing Summary")
    print(f"{'=' * 60}")
    
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"总任务数 / Total tasks: {len(results)}")
    print(f"成功 / Success: {success_count}")
    print(f"失败 / Failed: {len(results) - success_count}")
    
    if len(results) > 0:
        print(f"\n详细结果 / Detailed results:")
        for r in results:
            status = "✅" if r.get('success', False) else "❌"
            print(f"   {status} Row {r['row']}: {r['task_id']}")
    
    print(f"\n{'=' * 60}")
    print(f"🎉 处理完成 / Processing complete!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
