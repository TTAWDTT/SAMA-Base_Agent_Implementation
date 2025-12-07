# ==============================================================================
# 文档处理器模块 / Document Processor Module
# ==============================================================================
# 提供多种文档格式的解析和转换功能
# Provides parsing and conversion for various document formats
#
# 支持格式 / Supported Formats:
# - PDF: 文本提取和图片提取 / Text and image extraction
# - Word (.docx/.doc): 文本和图片提取 / Text and image extraction
# - PowerPoint (.pptx): 幻灯片内容提取 / Slide content extraction
# - Excel (.xlsx/.xls): 表格数据读取 / Spreadsheet data reading
# - 图片 (png/jpg/gif等): Base64编码和描述 / Base64 encoding and description
# - 纯文本 (txt/md): 直接读取 / Direct reading
#
# 基于 GAIA Benchmark 需求设计
# Designed based on GAIA Benchmark requirements
# ==============================================================================

import base64
import csv
import os
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.logger import get_logger

logger = get_logger("utils.document_processor")

# 尝试导入可选依赖 / Try importing optional dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow 未安装，图片处理功能受限 / Pillow not installed, image processing limited")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pptx
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ==============================================================================
# 辅助函数 / Helper Functions
# ==============================================================================

def encode_image_to_base64(image_path: str) -> str:
    """
    将图片文件编码为Base64字符串 / Encode image file to Base64 string
    
    Args:
        image_path: 图片文件路径 / Image file path
        
    Returns:
        str: Base64编码的字符串 / Base64 encoded string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_size(image_path: str) -> Tuple[int, int]:
    """
    获取图片尺寸 / Get image dimensions
    
    Args:
        image_path: 图片文件路径 / Image file path
        
    Returns:
        Tuple[int, int]: (宽度, 高度) / (width, height)
        
    Raises:
        FileNotFoundError: 文件不存在 / File not found
        ValueError: 无法读取图片 / Cannot read image
    """
    if not PIL_AVAILABLE:
        raise ImportError("Pillow 未安装 / Pillow is not installed")
    
    try:
        with Image.open(image_path) as img:
            return img.size
    except FileNotFoundError:
        raise FileNotFoundError(f"图片文件未找到 / Image file not found: {image_path}")
    except Exception as e:
        raise ValueError(f"无法读取图片 / Cannot read image {image_path}: {str(e)}")


def check_dependencies(file_ext: str) -> Optional[str]:
    """
    检查处理特定文件类型所需的依赖 / Check dependencies for specific file type
    
    Args:
        file_ext: 文件扩展名（不含点）/ File extension (without dot)
        
    Returns:
        Optional[str]: 缺失的依赖名称，None表示依赖已满足 / Missing dependency name, None if satisfied
    """
    ext = file_ext.lower().lstrip('.')
    
    if ext == 'pdf':
        if not PDFPLUMBER_AVAILABLE:
            return "pdfplumber"
    elif ext in ['docx', 'doc']:
        if not DOCX_AVAILABLE:
            return "python-docx"
    elif ext == 'pptx':
        if not PPTX_AVAILABLE:
            return "python-pptx"
    elif ext in ['xlsx', 'xls']:
        if not PANDAS_AVAILABLE:
            return "pandas"
    elif ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp']:
        if not PIL_AVAILABLE:
            return "Pillow"
    
    return None


# ==============================================================================
# 文档转换器类 / Document Converter Class
# ==============================================================================

class DocumentConverter:
    """
    文档转换器 / Document Converter
    
    将各种文档格式转换为统一的文本/Markdown格式，便于Agent处理
    Converts various document formats to unified text/Markdown format for Agent processing
    
    使用方法 / Usage:
        converter = DocumentConverter(task_id="task_001", output_dir="./temp")
        result = converter.convert("document.pdf")
        # result = {"content": "...", "output_path": "...", "images": [...]}
    """
    
    # 支持的文件扩展名 / Supported file extensions
    SUPPORTED_EXTENSIONS = {
        'document': ['.pdf', '.docx', '.doc', '.pptx', '.txt', '.md'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
        'spreadsheet': ['.xlsx', '.xls', '.csv'],
    }
    
    def __init__(
        self,
        task_id: str,
        output_dir: Optional[str] = None,
        image_description_func: Optional[callable] = None
    ):
        """
        初始化文档转换器 / Initialize document converter
        
        Args:
            task_id: 任务ID，用于组织输出目录 / Task ID for organizing output directory
            output_dir: 输出目录，默认为 ./workspace/temp/{task_id}/input
                       Output directory, default is ./workspace/temp/{task_id}/input
            image_description_func: 图片描述函数，用于生成图片的文字描述
                                   Image description function for generating text descriptions
        """
        self.task_id = task_id
        
        # 设置输出目录 / Set output directory
        if output_dir:
            self.output_dir = Path(output_dir) / task_id / "input"
        else:
            self.output_dir = Path("./workspace/temp") / task_id / "input"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 图片CSV路径 / Image CSV path
        self.image_csv_path = self.output_dir / "images.csv"
        
        # 图片计数器 / Image counter
        self.image_counter = 1
        
        # 图片描述函数 / Image description function
        self.image_description_func = image_description_func
        
        # 初始化图片CSV / Initialize image CSV
        self._init_image_csv()
        
        logger.info(f"文档转换器初始化 / Document converter initialized: {self.output_dir}")
    
    def _init_image_csv(self) -> None:
        """初始化图片信息CSV文件 / Initialize image info CSV file"""
        # 如果文件已存在，删除重建 / Delete and recreate if exists
        if self.image_csv_path.exists():
            self.image_csv_path.unlink()
        
        with open(self.image_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "source_path", "base64", "description", "size"])
    
    def _save_image_info(
        self,
        name: str,
        source: str,
        base64_str: str,
        description: str,
        size: Union[str, Tuple[int, int]]
    ) -> None:
        """
        保存图片信息到CSV / Save image info to CSV
        
        Args:
            name: 图片名称 / Image name
            source: 来源路径 / Source path
            base64_str: Base64编码 / Base64 encoding
            description: 图片描述 / Image description
            size: 尺寸（宽x高或字符串）/ Size (WxH or string)
        """
        if isinstance(size, tuple):
            size_str = f"{size[0]}x{size[1]}"
        else:
            size_str = str(size)
        
        with open(self.image_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([name, source, base64_str, description, size_str])
    
    def _image_to_base64(self, image_data: bytes) -> Tuple[str, str]:
        """
        将图片数据转换为Base64 / Convert image data to Base64
        
        Args:
            image_data: 图片二进制数据 / Image binary data
            
        Returns:
            Tuple[str, str]: (Base64字符串, 尺寸字符串) / (Base64 string, size string)
        """
        if not PIL_AVAILABLE:
            # 没有PIL时，直接编码原始数据 / Encode raw data without PIL
            return base64.b64encode(image_data).decode('utf-8'), "unknown"
        
        try:
            img = Image.open(BytesIO(image_data))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8'), f"{img.size[0]}x{img.size[1]}"
        except Exception as e:
            # 处理损坏或无法识别的图片 / Handle corrupted or unrecognizable images
            logger.warning(f"无法处理图片，使用占位符 / Cannot process image, using placeholder: {e}")
            # 创建占位图片 / Create placeholder image
            placeholder = Image.new('RGB', (100, 100), color='gray')
            buffered = BytesIO()
            placeholder.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8'), "100x100"
    
    # ==========================================================================
    # 各类型文件转换方法 / Conversion Methods for Each Type
    # ==========================================================================
    
    def convert_pdf(self, file_path: str) -> str:
        """
        转换PDF文件 / Convert PDF file
        
        提取PDF中的文本和图片
        Extracts text and images from PDF
        
        Args:
            file_path: PDF文件路径 / PDF file path
            
        Returns:
            str: Markdown格式的内容 / Markdown formatted content
        """
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber 未安装，请运行: pip install pdfplumber")
        
        md_content = []
        file_name = Path(file_path).stem
        
        # 使用pdfplumber提取文字 / Extract text with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    md_content.append(f"--- Page {page_num} ---\n{text}")
                
                # 提取表格 / Extract tables
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables, 1):
                    if table:
                        md_content.append(f"\n[表格 {page_num}-{table_idx}]\n")
                        # 简单的表格转文本 / Simple table to text
                        for row in table:
                            md_content.append(" | ".join(str(cell or '') for cell in row))
        
        # 使用PyMuPDF提取图片（如果可用）/ Extract images with PyMuPDF if available
        if FITZ_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list, 1):
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            base64_str, size = self._image_to_base64(image_bytes)
                            img_name = f"{file_name}_page{page_num + 1}_img{img_index}.{image_ext}"
                            self._save_image_info(
                                img_name,
                                file_path,
                                base64_str,
                                f"从PDF第{page_num + 1}页提取 / Extracted from PDF page {page_num + 1}",
                                size
                            )
                            self.image_counter += 1
                        except Exception as e:
                            logger.warning(f"PDF图片提取失败 / Failed to extract PDF image: {e}")
                doc.close()
            except Exception as e:
                logger.warning(f"PyMuPDF处理失败 / PyMuPDF processing failed: {e}")
        
        return "\n\n".join(md_content)
    
    def convert_word(self, file_path: str) -> str:
        """
        转换Word文档 / Convert Word document
        
        Args:
            file_path: Word文件路径 / Word file path
            
        Returns:
            str: Markdown格式的内容 / Markdown formatted content
        """
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx 未安装，请运行: pip install python-docx")
        
        doc = docx.Document(file_path)
        file_name = Path(file_path).stem
        md_content = []
        
        # 提取段落文本 / Extract paragraph text
        for para in doc.paragraphs:
            if para.text.strip():
                md_content.append(para.text)
        
        # 提取表格 / Extract tables
        for table_idx, table in enumerate(doc.tables, 1):
            md_content.append(f"\n[表格 {table_idx}]")
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                md_content.append(row_text)
        
        # 提取图片 / Extract images
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_data = rel.target_part.blob
                    base64_str, size = self._image_to_base64(img_data)
                    img_name = f"{file_name}_word_image_{self.image_counter}"
                    self._save_image_info(
                        img_name,
                        file_path,
                        base64_str,
                        "从Word文档提取 / Extracted from Word document",
                        size
                    )
                    self.image_counter += 1
                except Exception as e:
                    logger.warning(f"Word图片提取失败 / Failed to extract Word image: {e}")
        
        return "\n\n".join(md_content)
    
    def convert_ppt(self, file_path: str) -> str:
        """
        转换PowerPoint文件 / Convert PowerPoint file
        
        Args:
            file_path: PPT文件路径 / PPT file path
            
        Returns:
            str: Markdown格式的内容 / Markdown formatted content
        """
        if not PPTX_AVAILABLE:
            raise ImportError("python-pptx 未安装，请运行: pip install python-pptx")
        
        prs = pptx.Presentation(file_path)
        file_name = Path(file_path).stem
        md_content = []
        
        for slide_num, slide in enumerate(prs.slides, 1):
            md_content.append(f"\n--- Slide {slide_num} ---\n")
            
            for shape in slide.shapes:
                # 提取文本 / Extract text
                if hasattr(shape, "text") and shape.text:
                    md_content.append(shape.text)
                
                # 提取图片 / Extract images
                if shape.shape_type == 13:  # Picture shape
                    try:
                        img_data = shape.image.blob
                        base64_str, size = self._image_to_base64(img_data)
                        img_name = f"{file_name}_slide{slide_num}_img_{self.image_counter}"
                        self._save_image_info(
                            img_name,
                            file_path,
                            base64_str,
                            f"从幻灯片第{slide_num}页提取 / Extracted from slide {slide_num}",
                            size
                        )
                        self.image_counter += 1
                    except Exception as e:
                        logger.warning(f"PPT图片提取失败 / Failed to extract PPT image: {e}")
        
        return "\n\n".join(md_content)
    
    def convert_excel(self, file_path: str) -> Tuple[str, str]:
        """
        转换Excel文件 / Convert Excel file
        
        Args:
            file_path: Excel文件路径 / Excel file path
            
        Returns:
            Tuple[str, str]: (内容预览, 复制后的文件路径) / (content preview, copied file path)
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas 未安装，请运行: pip install pandas openpyxl")
        
        # 复制文件到输出目录 / Copy file to output directory
        output_path = self.output_dir / Path(file_path).name
        shutil.copy2(file_path, output_path)
        
        # 读取所有工作表 / Read all sheets
        try:
            xls = pd.ExcelFile(file_path)
            content_parts = []
            
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=10)
                content_parts.append(f"=== Sheet: {sheet_name} ===")
                content_parts.append(f"行数: {len(df)}, 列数: {len(df.columns)}")
                content_parts.append(df.to_markdown(index=False))
            
            content = "\n\n".join(content_parts)
        except Exception as e:
            # 尝试CSV格式 / Try CSV format
            try:
                df = pd.read_csv(file_path, nrows=10)
                content = f"CSV文件预览 (前10行):\n{df.to_markdown(index=False)}"
            except Exception as e2:
                content = f"无法读取文件: {e}"
        
        return content, str(output_path)
    
    def convert_txt(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        转换纯文本文件 / Convert plain text file
        
        Args:
            file_path: 文本文件路径 / Text file path
            encoding: 文件编码 / File encoding
            
        Returns:
            str: 文件内容 / File content
        """
        # 尝试多种编码 / Try multiple encodings
        encodings = [encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # 最后尝试二进制读取 / Last resort: binary read
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    
    def convert_markdown(self, file_path: str) -> str:
        """
        转换Markdown文件 / Convert Markdown file
        
        Args:
            file_path: Markdown文件路径 / Markdown file path
            
        Returns:
            str: 文件内容 / File content
        """
        return self.convert_txt(file_path)
    
    def convert_image(self, file_path: str) -> Tuple[str, str]:
        """
        处理图片文件 / Process image file
        
        复制图片到输出目录，生成Base64编码和描述
        Copy image to output directory, generate Base64 encoding and description
        
        Args:
            file_path: 图片文件路径 / Image file path
            
        Returns:
            Tuple[str, str]: (图片描述, 复制后的文件路径) / (image description, copied file path)
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安装，请运行: pip install Pillow")
        
        # 复制图片到输出目录 / Copy image to output directory
        output_path = self.output_dir / Path(file_path).name
        shutil.copy2(file_path, output_path)
        
        # 获取图片信息 / Get image info
        file_name = Path(file_path).stem
        ext = Path(file_path).suffix.lstrip('.')
        
        base64_image = encode_image_to_base64(file_path)
        size = get_image_size(file_path)
        
        # 生成图片描述 / Generate image description
        if self.image_description_func:
            try:
                description = self.image_description_func(base64_image, ext)
            except Exception as e:
                logger.warning(f"图片描述生成失败 / Image description generation failed: {e}")
                description = f"图片文件 / Image file: {file_name}.{ext}, 尺寸 / Size: {size[0]}x{size[1]}"
        else:
            description = f"图片文件 / Image file: {file_name}.{ext}, 尺寸 / Size: {size[0]}x{size[1]}"
        
        # 保存图片信息 / Save image info
        self._save_image_info(file_name, file_path, base64_image, description, size)
        
        return f"{file_name} 的图片描述: {description}", str(output_path)
    
    # ==========================================================================
    # 主转换方法 / Main Conversion Methods
    # ==========================================================================
    
    def convert(self, file_path: str) -> Tuple[str, str]:
        """
        转换单个文件 / Convert single file
        
        根据文件扩展名自动选择转换方法
        Automatically selects conversion method based on file extension
        
        Args:
            file_path: 文件路径 / File path
            
        Returns:
            Tuple[str, str]: (转换后的内容, 输出路径) / (converted content, output path)
            
        Raises:
            FileNotFoundError: 文件不存在 / File not found
            ValueError: 不支持的文件类型 / Unsupported file type
        """
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在 / File not found: {file_path}")
        
        file_name = Path(file_path).stem
        ext = Path(file_path).suffix.lower()
        
        # 检查依赖 / Check dependencies
        missing_dep = check_dependencies(ext)
        if missing_dep:
            raise ImportError(f"缺少依赖 / Missing dependency: {missing_dep}. 请运行 / Please run: pip install {missing_dep}")
        
        # 根据扩展名选择转换方法 / Select conversion method by extension
        if ext == '.pdf':
            content = self.convert_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            content = self.convert_word(file_path)
        elif ext == '.pptx':
            content = self.convert_ppt(file_path)
        elif ext == '.txt':
            content = self.convert_txt(file_path)
        elif ext == '.md':
            content = self.convert_markdown(file_path)
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg']:
            return self.convert_image(file_path)
        elif ext in ['.xlsx', '.xls', '.csv']:
            return self.convert_excel(file_path)
        else:
            raise ValueError(f"不支持的文件类型 / Unsupported file type: {ext}")
        
        # 保存转换后的Markdown文件 / Save converted Markdown file
        output_path = self.output_dir / f"{file_name}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"文件已转换 / File converted: {file_path} -> {output_path}")
        
        return content, str(output_path)
    
    def process(self, file_list: List[str]) -> Dict[str, Any]:
        """
        批量处理文件列表 / Process file list in batch
        
        Args:
            file_list: 文件路径列表 / List of file paths
            
        Returns:
            Dict[str, Any]: 处理结果 / Processing result
                - file_count: 文档文件数量 / Document file count
                - image_count: 图片文件数量 / Image file count
                - files: 输出文件路径列表 / Output file path list
                - content: 合并的内容 / Merged content
        """
        contents = []
        output_paths = []
        image_count = 0
        
        # 图片扩展名列表 / Image extension list
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
        
        for file_path in file_list:
            try:
                # 统计图片数量 / Count images
                ext = Path(file_path).suffix.lower()
                if ext in image_exts:
                    image_count += 1
                
                # 转换文件 / Convert file
                content, output_path = self.convert(file_path)
                output_paths.append(output_path)
                
                # 构建内容（去除换行以节省空间）/ Build content (remove newlines to save space)
                contents.append(f"文件 {output_path} 的内容:\n{content.replace(chr(10), ' ')}")
                
            except Exception as e:
                logger.error(f"文件处理失败 / File processing failed: {file_path}, 错误 / Error: {e}")
                contents.append(f"文件 {file_path} 处理失败: {e}")
        
        # 如果没有图片，删除图片CSV / Delete image CSV if no images
        if image_count == 0 and self.image_csv_path.exists():
            self.image_csv_path.unlink()
        
        return {
            "file_count": len(output_paths) - image_count,
            "image_count": image_count,
            "files": output_paths,
            "content": " ".join(contents)
        }
    
    def cleanup(self) -> None:
        """
        清理输出目录 / Clean up output directory
        """
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            logger.info(f"输出目录已清理 / Output directory cleaned: {self.output_dir}")


# ==============================================================================
# 便捷函数 / Convenience Functions
# ==============================================================================

def preprocess_files(
    task_id: str,
    file_paths: List[str],
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    预处理文件列表 / Preprocess file list
    
    便捷函数，创建DocumentConverter并处理文件
    Convenience function that creates DocumentConverter and processes files
    
    Args:
        task_id: 任务ID / Task ID
        file_paths: 文件路径列表 / File path list
        output_dir: 输出目录 / Output directory
        
    Returns:
        Dict[str, Any]: 处理结果 / Processing result
    """
    converter = DocumentConverter(task_id=task_id, output_dir=output_dir)
    return converter.process(file_paths)


def get_supported_extensions() -> Dict[str, List[str]]:
    """
    获取支持的文件扩展名 / Get supported file extensions
    
    Returns:
        Dict[str, List[str]]: 按类型分组的扩展名 / Extensions grouped by type
    """
    return DocumentConverter.SUPPORTED_EXTENSIONS.copy()


def is_file_supported(file_path: str) -> bool:
    """
    检查文件是否受支持 / Check if file is supported
    
    Args:
        file_path: 文件路径 / File path
        
    Returns:
        bool: 是否支持 / Whether supported
    """
    ext = Path(file_path).suffix.lower()
    all_exts = []
    for exts in DocumentConverter.SUPPORTED_EXTENSIONS.values():
        all_exts.extend(exts)
    return ext in all_exts
