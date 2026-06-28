"""
项目全局配置 — config/settings.py
==================================
所有配置集中管理，禁止硬编码路径/端口/目录。
"""
import os
from pathlib import Path

# ===== 项目根目录 =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ===== Edge 浏览器配置 =====
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
USER_DATA_DIR = r"E:\edge"

# ===== Temu 配置 =====
MARKETING_URL = "https://agentseller.temu.com/activity/marketing-activity"

# ===== 下载目录 =====
DOWNLOADS = os.path.expanduser("~/Downloads")

# ===== 活动筛选配置 =====
MIN_DISCOUNT = 6.0          # 最低折扣（折），6折以上
MAX_DAYS = 20                # 最大活动天数
MAX_ACTIVITIES = 6           # 最多选几个活动
EXCLUDE_KEYWORDS = ["爆款", "秒杀", "独立日"]  # 排除关键词

# ===== 下载超时 =====
DOWNLOAD_EVENT_TIMEOUT = 180   # 事件驱动超时（秒）
DOWNLOAD_POLL_TIMEOUT = 240    # 轮询兜底超时（秒）
