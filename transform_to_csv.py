# 将 outputs 下每个子目录的 answer.txt 内容导出到 CSV
# 输出 CSV 保存在项目根目录

from pathlib import Path
import csv


def collect_answers(output_dir: Path) -> list:
    rows = []
    if not output_dir.exists():
        print(f"目录不存在: {output_dir}")
        return rows

    for child in sorted(output_dir.iterdir()):
        if not child.is_dir():
            continue
        # 忽略日志文件夹或显式名为 logs 的文件夹
        if child.name.lower() == 'logs':
            continue
        ans_file = child / 'answer.txt'
        if ans_file.exists() and ans_file.is_file():
            try:
                text = ans_file.read_text(encoding='utf-8').strip()
            except Exception:
                # 尝试其他编码
                text = ans_file.read_text(encoding='gbk', errors='ignore').strip()
            rows.append((child.name, text))
    return rows


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    outputs_dir = root / 'outputs'
    out_csv = root / 'outputs_answers.csv'

    data = collect_answers(outputs_dir)
    if not data:
        print('未找到任何 answer.txt 或 outputs 目录为空。')
    else:
        with open(out_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'answer'])
            for row in data:
                writer.writerow(row)
        print(f'已导出 {len(data)} 条记录到: {out_csv}')
