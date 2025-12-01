# ==============================================================================
# 日期时间工具 / DateTime Tool
# ==============================================================================
# 提供日期时间相关功能
# Provides date and time related functionality
# ==============================================================================

from datetime import datetime, timedelta
from typing import Optional

from pydantic import Field

from src.tools.base import BaseTool, ToolInput


class DateTimeInput(ToolInput):
    """日期时间输入 / DateTime Input"""
    format: str = Field(default="%Y-%m-%d %H:%M:%S", description="日期时间格式 / DateTime format")
    timezone: Optional[str] = Field(default=None, description="时区 / Timezone")


class GetCurrentTimeTool(BaseTool):
    """
    获取当前时间工具 / Get Current Time Tool
    
    返回当前日期和时间
    Returns current date and time
    """
    
    name: str = "get_current_time"
    description: str = "获取当前日期和时间。可选参数：format（日期时间格式）/ Get current date and time. Optional parameters: format (datetime format)"
    description_zh: str = "获取当前日期和时间。可选参数：format（日期时间格式）"
    description_en: str = "Get current date and time. Optional parameters: format (datetime format)"
    
    def _run(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        获取当前时间 / Get current time
        
        Args:
            format: 日期时间格式 / DateTime format
            
        Returns:
            str: 格式化的当前时间 / Formatted current time
        """
        try:
            now = datetime.now()
            return f"当前时间 / Current time: {now.strftime(format)}"
        except Exception as e:
            return f"获取时间出错 / Error getting time: {str(e)}"


class DateCalculatorInput(ToolInput):
    """日期计算输入 / Date Calculation Input"""
    date: str = Field(description="基准日期（YYYY-MM-DD格式）/ Base date (YYYY-MM-DD format)")
    days: int = Field(default=0, description="添加的天数（可为负数）/ Days to add (can be negative)")
    months: int = Field(default=0, description="添加的月数（可为负数）/ Months to add (can be negative)")
    years: int = Field(default=0, description="添加的年数（可为负数）/ Years to add (can be negative)")


class DateCalculatorTool(BaseTool):
    """
    日期计算工具 / Date Calculator Tool
    
    计算日期加减
    Calculates date addition and subtraction
    """
    
    name: str = "date_calculator"
    description: str = "计算日期加减。参数：date（基准日期，YYYY-MM-DD格式），days/months/years（要添加的天/月/年数）/ Calculate date addition/subtraction. Parameters: date (base date, YYYY-MM-DD format), days/months/years (days/months/years to add)"
    description_zh: str = "计算日期加减。参数：date（基准日期，YYYY-MM-DD格式），days/months/years（要添加的天/月/年数）"
    description_en: str = "Calculate date addition/subtraction. Parameters: date (base date, YYYY-MM-DD format), days/months/years (days/months/years to add)"
    input_schema = DateCalculatorInput
    
    def _run(self, date: str, days: int = 0, months: int = 0, years: int = 0) -> str:
        """
        计算日期 / Calculate date
        
        Args:
            date: 基准日期 / Base date
            days: 天数 / Days
            months: 月数 / Months
            years: 年数 / Years
            
        Returns:
            str: 计算结果 / Calculation result
        """
        try:
            # 解析基准日期 / Parse base date
            base_date = datetime.strptime(date, "%Y-%m-%d")
            
            # 计算新日期 / Calculate new date
            # 处理年月（简化处理）/ Handle years and months (simplified)
            new_year = base_date.year + years
            new_month = base_date.month + months
            
            # 处理月份溢出 / Handle month overflow
            while new_month > 12:
                new_month -= 12
                new_year += 1
            while new_month < 1:
                new_month += 12
                new_year -= 1
            
            # 处理日期溢出 / Handle day overflow
            try:
                result_date = base_date.replace(year=new_year, month=new_month)
            except ValueError:
                # 如果日期无效（如2月30日），使用月末
                # If date is invalid (e.g., Feb 30), use end of month
                import calendar
                last_day = calendar.monthrange(new_year, new_month)[1]
                result_date = base_date.replace(year=new_year, month=new_month, day=min(base_date.day, last_day))
            
            # 添加天数 / Add days
            result_date += timedelta(days=days)
            
            return f"计算结果 / Result: {result_date.strftime('%Y-%m-%d')}\n原始日期 / Original date: {date}\n调整 / Adjustment: {years}年/years, {months}月/months, {days}天/days"
            
        except ValueError as e:
            return f"日期格式错误 / Date format error: {str(e)}. 请使用YYYY-MM-DD格式 / Please use YYYY-MM-DD format"
        except Exception as e:
            return f"计算出错 / Calculation error: {str(e)}"


class TimeDifferenceInput(ToolInput):
    """时间差计算输入 / Time Difference Input"""
    date1: str = Field(description="第一个日期（YYYY-MM-DD格式）/ First date (YYYY-MM-DD format)")
    date2: str = Field(description="第二个日期（YYYY-MM-DD格式）/ Second date (YYYY-MM-DD format)")


class TimeDifferenceTool(BaseTool):
    """
    时间差计算工具 / Time Difference Tool
    
    计算两个日期之间的差异
    Calculates difference between two dates
    """
    
    name: str = "time_difference"
    description: str = "计算两个日期之间的差异。参数：date1, date2（两个日期，YYYY-MM-DD格式）/ Calculate difference between two dates. Parameters: date1, date2 (two dates, YYYY-MM-DD format)"
    description_zh: str = "计算两个日期之间的差异。参数：date1, date2（两个日期，YYYY-MM-DD格式）"
    description_en: str = "Calculate difference between two dates. Parameters: date1, date2 (two dates, YYYY-MM-DD format)"
    input_schema = TimeDifferenceInput
    
    def _run(self, date1: str, date2: str) -> str:
        """
        计算时间差 / Calculate time difference
        
        Args:
            date1: 第一个日期 / First date
            date2: 第二个日期 / Second date
            
        Returns:
            str: 时间差结果 / Time difference result
        """
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            
            diff = d2 - d1
            days = diff.days
            
            # 计算年月周 / Calculate years, months, weeks
            weeks = abs(days) // 7
            years = abs(days) // 365
            months = abs(days) // 30
            
            direction = "后" if days > 0 else "前" if days < 0 else ""
            direction_en = "after" if days > 0 else "before" if days < 0 else ""
            
            return f"日期差异 / Date difference:\n{date1} 到 / to {date2}\n\n总天数 / Total days: {abs(days)} 天/days\n约 / Approximately: {weeks} 周/weeks, {months} 月/months, {years} 年/years\n\n{date2} 在 {date1} 的 {abs(days)} 天{direction}\n{date2} is {abs(days)} days {direction_en} {date1}"
            
        except ValueError as e:
            return f"日期格式错误 / Date format error: {str(e)}. 请使用YYYY-MM-DD格式 / Please use YYYY-MM-DD format"
        except Exception as e:
            return f"计算出错 / Calculation error: {str(e)}"
