"""
日期解析工具 — utils/date_parser.py
=====================================
从 Temu 活动页面的 dateText 中解析日期范围。
"""
import re
import calendar
from datetime import date


def parse_discount(text):
    """解析折扣文本 → float（折）"""
    m = re.search(r'[≤<]\s*(\d+\.?\d*)\s*折', text)
    return float(m.group(1)) if m else None


def parse_activity_dates(date_text, name=""):
    """
    从 dateText 解析 (开始日期, 结束日期)，支持多种格式。
    分析策略：dateText → 活动名(兜底)
    """
    body = re.split(r'[（(]\d+天[）)]', date_text)[0].strip()
    if not body:
        return None

    return (_parse_date_range(body) or _parse_date_range(name) or None)


def _parse_date_range(text):
    """从文本中提取日期范围 (start, end)"""
    text = text.replace("(", "（").replace(")", "）")

    # "2026-06-30～2026-07-20" 完整日期格式
    m = re.search(r'(\d{4})[-.](\d{1,2})[-.](\d{1,2})\s*[～~\-–]\s*(\d{4})[-.](\d{1,2})[-.](\d{1,2})', text)
    if m:
        sy, sm, sd, ey, em, ed = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
        return (date(sy, sm, sd), date(ey, em, ed))

    # "2026-06-30～07-20" 省略结束年份
    m = re.search(r'(\d{4})[-.](\d{1,2})[-.](\d{1,2})\s*[～~\-–]\s*(\d{1,2})[-.](\d{1,2})', text)
    if m:
        y, sm, sd, em, ed = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        return (date(y, sm, sd), date(y, em, ed))

    # "6.23-6.25" / "06/27-06/28" 等跨日格式
    m = re.search(r'(\d{1,2})[./](\d{1,2})\s*[-–]\s*(\d{1,2})[./](\d{1,2})', text)
    if m:
        sm, sd, em, ed = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        return (date(2026, sm, sd), date(2026, em, ed))

    # "6月" 整月格式
    m = re.search(r'(\d{1,2})月', text)
    if m:
        month = int(m.group(1))
        last = calendar.monthrange(2026, month)[1]
        return (date(2026, month, 1), date(2026, month, last))

    return None


def days_between(start, end):
    """计算活动天数"""
    return (end - start).days + 1


def is_expired(end_date, today=None):
    """检查活动是否已过期"""
    if today is None:
        today = date.today()
    return end_date < today
