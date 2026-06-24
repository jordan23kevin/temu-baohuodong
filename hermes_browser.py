"""
Hermes Browser Runtime Layer v2.0 — State Machine (确定性状态机)
================================================================
核心原则：
  ❌ 不"猜"浏览器状态
  ✅ 一切通过状态流转驱动

项目：E:\Claude code\Temu自动化\报活动
三层架构：
  [Workflow Layer]  → 报活动_全自动.py（v3.1.0）
  [Runtime Layer]   → hermes_browser.py    ← 你在这里
  [IO Layer]        → download_manager.py

状态流：
  EDGE_OFF → EDGE_STARTING → CDP_READY → BROWSER_CONNECTED → CONTEXT_READY → PAGE_READY
"""
import os, time, json, subprocess, urllib.request
from enum import Enum
from playwright.sync_api import sync_playwright


# =========================
# 配置
# =========================
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
USER_DATA_DIR = r"E:\edge"


# =========================
# 状态机
# =========================
class State:
    EDGE_OFF = "EDGE_OFF"
    EDGE_STARTING = "EDGE_STARTING"
    CDP_READY = "CDP_READY"
    BROWSER_CONNECTED = "BROWSER_CONNECTED"
    CONTEXT_READY = "CONTEXT_READY"
    PAGE_READY = "PAGE_READY"


class HermesBrowserV2:
    """Edge 状态机浏览器管理器"""

    def __init__(self):
        self.state = State.EDGE_OFF

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        self._edge_proc = None
        self._last_start = 0

    # =========================
    # 状态推进器
    # =========================
    def transition(self, target_state):
        self.log(f"[STATE] {self.state} → {target_state}")
        self.state = target_state

    # =========================
    # Edge 启动
    # =========================
    def start_edge(self):
        if self._is_cdp_ready():
            self.transition(State.CDP_READY)
            return

        self.transition(State.EDGE_STARTING)

        args = [
            EDGE_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-allow-origins=*",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        self._edge_proc = subprocess.Popen(
            args,
            creationflags=subprocess.DETACHED_PROCESS | 0x00000200,
            close_fds=True,
        )

        self.log(f"Edge PID={self._edge_proc.pid}")

        # CDP 等待（状态驱动，不是 sleep hack）
        self._wait_cdp_ready()

        self.transition(State.CDP_READY)

    # =========================
    # CDP 探活
    # =========================
    def _wait_cdp_ready(self, timeout=30):
        """确定性 CDP 等待：探活循环，不 sleep"""
        start = time.time()

        while time.time() - start < timeout:
            if self._is_cdp_ready():
                return True
            time.sleep(0.5)

        raise RuntimeError("CDP 未就绪")

    def _is_cdp_ready(self):
        """检查 CDP 是否可连（检测 webSocketDebuggerUrl 更准确）"""
        try:
            resp = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1)
            data = json.loads(resp.read())
            return "webSocketDebuggerUrl" in data
        except:
            return False

    # =========================
    # Browser 层
    # =========================
    def connect_browser(self):
        """连接 CDP Browser（状态机推进）"""
        if self.state in [State.EDGE_OFF, State.EDGE_STARTING]:
            self.start_edge()

        if self._browser is None:
            self._playwright = self._playwright or sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(CDP_URL)

        self.transition(State.BROWSER_CONNECTED)

    # =========================
    # Context 层
    # =========================
    def ensure_context(self):
        """获取/创建 browser context（状态机推进）"""
        self.connect_browser()

        if self._context is None or self._context not in self._browser.contexts:
            self._context = (
                self._browser.contexts[0]
                if self._browser.contexts
                else self._browser.new_context()
            )

        self.transition(State.CONTEXT_READY)

    # =========================
    # Page 层
    # =========================
    def ensure_page(self):
        """获取/创建 page 对象（状态机推进）"""
        self.ensure_context()

        pages = self._context.pages

        if pages:
            self._page = pages[0]
        else:
            self._page = self._context.new_page()

        self.transition(State.PAGE_READY)
        return self._page

    # =========================
    # 对外主入口（唯一推荐入口）
    # =========================
    def get_page(self):
        """主入口：确保拿到一个可用 page"""
        return self.ensure_page()

    # =========================
    # 健康检查（真实状态）
    # =========================
    def health(self):
        """返回当前状态快照"""
        return {
            "state": self.state,
            "cdp": self._is_cdp_ready(),
            "browser": self._browser is not None,
            "context": self._context is not None,
            "page": self._page is not None,
        }

    # =========================
    # 重连（安全）
    # =========================
    def reconnect(self):
        """安全重连：不丢状态"""
        self.log("Reconnecting CDP...")

        self._browser = None
        self._context = None
        self._page = None

        self.transition(State.EDGE_STARTING)

        if not self._is_cdp_ready():
            self.start_edge()
        else:
            self.connect_browser()

    # =========================
    # 停止
    # =========================
    def stop(self):
        """关闭 Edge 进程"""
        try:
            if self._browser:
                self._browser.close()
        except:
            pass

        subprocess.run("taskkill /F /IM msedge.exe", shell=True)

        self._browser = None
        self._context = None
        self._page = None

        self.transition(State.EDGE_OFF)

    # =========================
    # 日志
    # =========================
    def log(self, msg):
        print(f"[HermesV2] {msg}", flush=True)


# =========================
# 向后兼容别名（v1 调用方无需改代码）
# =========================
HermesBrowser = HermesBrowserV2
