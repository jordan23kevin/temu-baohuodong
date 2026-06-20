"""
Hermes Download Manager v1.2 — 工业级绝对稳定版
=================================================
项目：E:\Claude code\Temu自动化\报活动（v3.1.0）
核心原则：
  ✔ 下载失败 = 任务失败
  ❌ 但 ≠ 系统失败
  ❌ 但 ≠ 浏览器关闭
  ❌ 但 ≠ workflow 中断

架构：
  Trigger Action → 策略①: 事件驱动(短路径)
                  → 策略②: 轮询兜底(长路径)
                  → 失败: 返回None，浏览器保持存活
"""
import os, time, hashlib
from pathlib import Path


class DownloadManager:
    """下载管理器 — 事件驱动 + 轮询兜底 + 永不崩浏览器"""

    def __init__(self, context, page, download_dir=None):
        """
        context: BrowserContext（用于事件监听）
        page:    Page（用于触发点击）
        download_dir: 下载目录（默认 ~/Downloads）
        """
        self.context = context
        self.page = page
        self.download_dir = Path(download_dir or os.path.expanduser("~/Downloads"))
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.state = "IDLE"   # IDLE → WAITING → SAVING → DONE / FAILED
        self.last_path = None
        self.last_error = None

    # =========================
    # 主入口（绝对稳定版）
    # =========================
    def generate_template(self, trigger_fn, timeout=180, poll_timeout=240,
                          filename=None):
        """
        触发下载 → ①事件驱动 → ②轮询兜底 → ③安全失败

        trigger_fn:  触发下载的 Callable
        timeout:     事件驱动超时(秒)
        poll_timeout: 轮询兜底超时(秒)
        filename:    自定义文件名（可选）
        返回:        文件路径 / None（失败不崩）
        """
        self.state = "WAITING"
        self.last_path = None
        self.last_error = None

        # =========================
        # 策略①：事件驱动（短路径）
        # =========================
        try:
            with self.page.expect_download(timeout=timeout * 1000) as dl_info:
                trigger_fn()
            download = dl_info.value
            return self._save_download(download, filename)
        except Exception as e:
            self.last_error = e
            print(f"[DL] 事件驱动超时 → 转入轮询: {e}")

        # =========================
        # 策略②：轮询兜底（长路径）
        # =========================
        file = self._poll_new_file(pattern="*.xlsx", timeout=poll_timeout)
        if file:
            return self._save_copy(file, filename)

        # =========================
        # ③安全失败（不影响 browser）
        # =========================
        self.state = "FAILED"
        print(f"[DL] ❌ 下载失败但 browser 保持存活")
        return None

    # =========================
    # 策略①：事件保存
    # =========================
    def _save_download(self, download, filename=None):
        self.state = "SAVING"
        save_name = filename or download.suggested_filename or f"dl_{int(time.time())}.xlsx"
        save_path = str(self.download_dir / save_name)
        download.save_as(save_path)
        self.last_path = save_path
        self.state = "DONE"
        size = os.path.getsize(save_path) // 1024
        print(f"[DL] ✅ 事件驱动完成: {save_name} ({size}KB)")
        return save_path

    # =========================
    # 策略②：轮询
    # =========================
    def _poll_new_file(self, pattern="*.xlsx", timeout=240):
        """轮询下载目录，找出点击后出现的新文件（带 seen set 防重复）"""
        import glob
        seen = set(glob.glob(str(self.download_dir / pattern)))
        start = time.time()

        print(f"[DL] 文件轮询开始（超时{timeout}s, 模式={pattern}）...")

        while time.time() - start < timeout:
            current = set(glob.glob(str(self.download_dir / pattern)))
            # 排除 crdownload 临时文件
            current = {f for f in current if not f.endswith(".crdownload")}
            new_files = current - seen

            if new_files:
                # 按修改时间取最新的
                latest = max(new_files, key=os.path.getmtime)
                # 等待文件就绪（大小稳定）
                if self._wait_file_ready(latest, timeout=30):
                    self.state = "DONE"
                    self.last_path = latest
                    size = os.path.getsize(latest) // 1024
                    print(f"[DL] ✅ 文件轮询完成: {os.path.basename(latest)} ({size}KB)")
                    return latest

            seen.update(current)
            time.sleep(2)

        print(f"[DL] ⏰ 文件轮询超时（{timeout}s）")
        return None

    # =========================
    # 文件就绪检测
    # =========================
    def _wait_file_ready(self, path, timeout=30, interval=0.5):
        """等待文件完全落地（存在、非临时、大小>0）"""
        path = Path(path)
        start = time.time()
        while time.time() - start < timeout:
            if not path.exists():
                time.sleep(interval); continue
            if str(path).endswith(".crdownload"):
                time.sleep(interval); continue
            if path.stat().st_size == 0:
                time.sleep(interval); continue
            return True
        return False

    # =========================
    # 文件复制（轮询到的文件改名保存）
    # =========================
    def _save_copy(self, src, filename=None):
        if not filename:
            return str(src)
        dest = str(self.download_dir / filename)
        import shutil
        shutil.copy2(src, dest)
        self.last_path = dest
        size = os.path.getsize(dest) // 1024
        print(f"[DL] ✅ 文件已复制: {filename} ({size}KB)")
        return dest

    # =========================
    # 安全关闭判断
    # =========================
    def can_close(self):
        return self.state in ["DONE", "IDLE"]

    # =========================
    # 状态
    # =========================
    def status(self):
        return {
            "state": self.state,
            "path": self.last_path,
            "error": str(self.last_error) if self.last_error else None,
        }
