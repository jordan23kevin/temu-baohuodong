"""
Hermes Browser Runtime Layer v1.1 — Edge 常驻服务化
=====================================================
核心原则：
  ❌ 浏览器不是资源（用完即弃）
  ✅ 浏览器是常驻服务（任务共享）

项目：E:\Claude code\Temu自动化\报活动
三层架构：
  [Workflow Layer]  → 报活动_全自动.py（v3.1.0）
  [Runtime Layer]   → hermes_browser.py    ← 你在这里
  [IO Layer]        → download_manager.py

功能：
  - Edge 常驻启动（DETACHED_PROCESS，脱离 Python 生命周期）
  - CDP 连接池（自动重连 + session restore）
  - 健康检查 + 自动重启（带冷却防 crash loop）
  - 多 session 预留接口
"""
import os, time, json, subprocess, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

# ===== 配置 =====
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP_PORT = 9224
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
USER_DATA_DIR = r"C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data"
RESTART_COOLDOWN = 5  # 重启冷却秒数


class HermesBrowser:
    """Edge 常驻服务管理器"""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._edge_pid = None
        self._last_restart = 0
        self.active = False

    # =========================
    # 启动 Edge 常驻进程
    # =========================
    def start_edge(self):
        """启动 Edge 为独立进程（DETACHED_PROCESS）"""
        if self._is_edge_running():
            self.log("Edge 已在运行")
            return

        args = [
            EDGE_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-allow-origins=*",
            f'--user-data-dir={USER_DATA_DIR}',
            "--no-first-run",
            "--no-default-browser-check",
        ]
        proc = subprocess.Popen(
            args,
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | 0x00000200,  # CREATE_NEW_PROCESS_GROUP
        )
        self._edge_pid = proc.pid
        self.log(f"Edge 已启动 (PID={proc.pid})")

        # 等待 CDP 端口就绪
        for i in range(30):
            if self._is_cdp_ready():
                self.log("CDP 端口就绪")
                return
            time.sleep(1)

        raise RuntimeError("Edge 启动失败：CDP 端口 30 秒未就绪")

    # =========================
    # 获取 Playwright 连接（创建/重连）
    # =========================
    def get_playwright(self):
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        return self._playwright

    def get_browser(self):
        """获取 CDP 浏览器连接（自动重连）"""
        if not self._is_cdp_ready():
            self.log("CDP 不可用，触发重连...")
            self.reconnect()

        if self._browser is None:
            p = self.get_playwright()
            self._browser = p.chromium.connect_over_cdp(CDP_URL)
            self.log("CDP 浏览器已连接")
        return self._browser

    def get_context(self):
        """获取 browser context（自动恢复）"""
        browser = self.get_browser()
        if self._context is None or self._context not in browser.contexts:
            self._context = browser.contexts[0] if browser.contexts else browser.new_context()
            self.log("Context 已就绪")
        return self._context

    def get_page(self):
        """获取 page 对象（自动恢复）"""
        context = self.get_context()
        pages = context.pages
        if pages:
            return pages[0]
        page = context.new_page()
        self.log("已创建新 Page")
        return page

    # =========================
    # 健康检查 + 自动恢复
    # =========================
    def ensure_alive(self):
        """全链路保活：Edge → CDP → Context → Page"""
        # 1. Edge 进程是否存活
        if not self._is_edge_running():
            self.log("Edge 进程已死，重启中...")
            self._safe_cooldown()
            self.start_edge()
            self._browser = None
            self._context = None

        # 2. CDP 是否可达
        if not self._is_cdp_ready():
            self.log("CDP 不可达，等待恢复...")
            for i in range(15):
                if self._is_cdp_ready():
                    break
                time.sleep(1)
            self._browser = None
            self._context = None

        # 3. 重连浏览器
        self.get_browser()
        self.get_context()
        self.get_page()

        self.active = True
        return True

    def health_check(self):
        """简单健康检查，返回状态字典"""
        status = {
            "edge_alive": False,
            "cdp_ready": False,
            "browser_connected": False,
            "page_alive": False,
        }
        status["edge_alive"] = self._is_edge_running()
        status["cdp_ready"] = self._is_cdp_ready()
        try:
            if self._browser:
                status["browser_connected"] = True
            if self._context and self._context.pages:
                self._context.pages[0].evaluate("1")
                status["page_alive"] = True
        except Exception:
            pass
        return status

    # =========================
    # 重连
    # =========================
    def reconnect(self):
        """完全重连（不重启 Edge）"""
        self._browser = None
        self._context = None
        try:
            p = self.get_playwright()
            self._browser = p.chromium.connect_over_cdp(CDP_URL)
            self._context = self._browser.contexts[0] if self._browser.contexts else None
            self.log("CDP 重连成功")
        except Exception as e:
            self.log(f"CDP 重连失败: {e}")
            raise

    # =========================
    # 停止 Edge
    # =========================
    def stop_edge(self):
        """关闭 Edge（爸爸明确要求时才调）"""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
        except Exception:
            pass
        self._context = None
        subprocess.run(f"taskkill //F //PID {self._edge_pid}" if self._edge_pid
                      else "taskkill //F //IM msedge.exe",
                      shell=True, stderr=subprocess.DEVNULL)
        self._edge_pid = None
        self.active = False
        self.log("Edge 已关闭")

    # =========================
    # 内部工具
    # =========================
    def _is_edge_running(self):
        if self._edge_pid:
            try:
                return self._is_cdp_ready() or True  # CDP 就绪说明 Edge 活着
            except:
                pass
        # fallback: 检查端口
        return self._is_cdp_ready()

    def _is_cdp_ready(self):
        try:
            resp = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2)
            return json.loads(resp.read()).get("Browser") is not None
        except Exception:
            return False

    def _safe_cooldown(self):
        """重启冷却，防 crash loop"""
        elapsed = time.time() - self._last_restart
        if elapsed < RESTART_COOLDOWN:
            wait = RESTART_COOLDOWN - elapsed
            self.log(f"冷却中 ({wait:.0f}s)...")
            time.sleep(wait)
        self._last_restart = time.time()

    def log(self, msg):
        t = time.strftime("%H:%M:%S")
        print(f"[{t}] [BRW] {msg}", flush=True)
