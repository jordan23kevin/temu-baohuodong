"""
17站价格表 — config/prices.py
================================
价格统一入口：活动核价.py 从此文件读取，不再散落三处。
改价只需改这一个文件。
"""
from dataclasses import dataclass


@dataclass
class SitePrice:
    name: str
    price_min: float   # 核价下限（低于此价删除）
    price_cap: float   # 报名价上限（高于此价降价到此）


# ===== 17站价格表 =====
ALL_SITES = [
    SitePrice("波兰站", 55, 65),
    SitePrice("匈牙利站", 61, 71),
    SitePrice("立陶宛站", 61, 71),
    SitePrice("斯洛伐克站", 65, 75),
    SitePrice("奥地利站", 65, 75),
    SitePrice("德国站", 73, 83),
    SitePrice("捷克站", 74, 84),
    SitePrice("荷兰站", 77, 87),
    SitePrice("西班牙站", 89, 99),
    SitePrice("比利时站", 90, 100),
    SitePrice("法国站", 90, 100),
    SitePrice("丹麦站", 95, 105),
    SitePrice("斯洛文尼亚站", 95, 105),
    SitePrice("葡萄牙站", 98, 108),
    SitePrice("罗马尼亚站", 108, 118),
    SitePrice("瑞典站", 147, 157),
    SitePrice("芬兰站", 176, 186),
]

# ===== 快速查找 =====
PRICE_MIN = {s.name: s.price_min for s in ALL_SITES}
PRICE_CAP = {s.name: s.price_cap for s in ALL_SITES}
SITE_NAMES = [s.name for s in ALL_SITES]
