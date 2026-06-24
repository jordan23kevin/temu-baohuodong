"""
浏览器服务 — services/browser_service.py
===========================================
HermesBrowser 的 service 层封装，提供统一的浏览器接入接口。
"""
from hermes_browser import HermesBrowser
from config.settings import MARKETING_URL


class BrowserService:
    """浏览器服务（单例，整个系统共享一个浏览器实例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.brw = HermesBrowser()
        self.page = None
        self.context = None

    def start(self):
        """启动 Edge + 获取 page"""
        self.brw.start_edge()
        self.page = self.brw.get_page()
        self.context = self.page.context
        return self

    def navigate(self, url=None):
        """导航到目标页面"""
        target = url or MARKETING_URL
        self.page.goto(target, wait_until="domcontentloaded", timeout=30000)

    def get_page(self):
        return self.page

    def get_context(self):
        return self.context

    def get_playwright(self):
        return self.brw._playwright
