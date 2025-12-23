
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from src.utils.pdf_fonts import register_cjk_font

# 注册中文字体（优先系统字体，其次内置CJK字体）
font_name = register_cjk_font()

# 创建PDF文档
pdf_path = 'SAMA_介绍.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                        rightMargin=72, leftMargin=72, 
                        topMargin=72, bottomMargin=72)

# 获取样式
styles = getSampleStyleSheet()

# 自定义样式
title_style = ParagraphStyle(
    'title',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#2E86AB'),
    spaceAfter=30,
    fontName=font_name
)

heading_style = ParagraphStyle(
    'heading',
    parent=styles['Heading2'],
    fontSize=18,
    textColor=colors.HexColor('#A23B72'),
    spaceBefore=20,
    spaceAfter=10,
    fontName=font_name
)

body_style = ParagraphStyle(
    'body',
    parent=styles['Normal'],
    fontSize=12,
    leading=16,
    spaceAfter=12,
    fontName=font_name
)

# PDF内容
content = []

# 标题
content.append(Paragraph("关于 SAMA", title_style))
content.append(Spacer(1, 20))

# 简介
content.append(Paragraph("你好！我是 SAMA，一个智能助手。", heading_style))
content.append(Paragraph(
    "我是罗臻开发的高级AI助手，专门设计用于帮助用户完成各种现实世界任务。"
    "我能够通过使用各种工具来执行复杂的操作，包括文件操作、网络搜索、代码执行等。",
    body_style
))
content.append(Spacer(1, 10))

# 核心能力
content.append(Paragraph("核心能力", heading_style))
capabilities = [
    "智能任务规划与管理",
    "文件操作（读取、写入、目录管理）",
    "代码执行（Python、Shell）",
    "网络搜索与信息获取",
    "复杂问题分析与解决"
]

for cap in capabilities:
    content.append(Paragraph(f"• {cap}", body_style))
content.append(Spacer(1, 10))

# 特点
content.append(Paragraph("我的特点", heading_style))
features = [
    "任务导向：使用todo工具进行任务规划与跟踪",
    "工具丰富：集成多种实用工具完成任务",
    "思考深入：在行动前进行充分思考分析",
    "结果导向：专注于完成用户目标",
    "学习适应：能够从交互中不断改进"
]

for feature in features:
    content.append(Paragraph(f"• {feature}", body_style))
content.append(Spacer(1, 10))

# 使用说明
content.append(Paragraph("如何使用我", heading_style))
content.append(Paragraph(
    "只需告诉我你需要完成的任务，无论是：",
    body_style
))

usages = [
    "搜索信息并整理成文档",
    "编写和执行代码",
    "批量处理文件",
    "分析数据",
    "解决技术问题",
    "...任何你能想到的任务"
]

for usage in usages:
    content.append(Paragraph(f"• {usage}", body_style))

content.append(Spacer(1, 20))
content.append(Paragraph(
    "我会自动规划任务步骤，使用合适的工具，并向你展示清晰的进度和结果。",
    body_style
))

# 生成PDF
doc.build(content)
print(f"PDF已生成：{pdf_path}")
