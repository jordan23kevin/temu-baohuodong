"""
Hermes Download Manager v2.0 — 常驻事件 + 文件稳定判定
=====================================================
项目：E:\Claude code\Temu自动化\报活动（v3.2.0）
核心原则：
  下载 = 状态流，不是事件点
  事件驱动是主通道，文件轮询是兜底
  所有下载绑定 task_id，全链路追踪
"""
import os, time, glob
from pathlib import Path


class DownloadManagerV2:
    """下载管理器 v2 — 事件驱动 + 文件稳定判定 + 状态注册"""

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

        # 任务注册表：task_id -> state
        self.tasks = {}

    # =========================
    # 主入口
    # =========================
    def generate_template(self, trigger_fn, timeout=180, poll_timeout=240,
                          filename=None):
        """
        触发下载 → ①事件驱动 → ②文件稳定判定 → ③轮询兜底

        trigger_fn:  触发下载的 Callable
        timeout:     事件驱动超时(秒)
        poll_timeout: 轮询兜底超时(秒)
        filename:    自定义文件名（可选）
        返回:        文件路径 / None（失败不崩）
        """
        task_id = filename or f"task_{int(time.time())}"
        self.tasks[task_id] = {"state": "WAITING", "path": None}

        # =========================
        # 策略①：事件驱动（主通道）
        # =========================
        try:
            with self.page.expect_download(timeout=timeout * 1000) as dl_info:
                self.tasks[task_id]["state"] = "TRIGGERED"
                trigger_fn()
            download = dl_info.value
            self.tasks[task_id]["state"] = "DOWNLOADING"
            return self._save_download(download, task_id, filename)
        except Exception as e:
            self.tasks[task_id]["last_error"] = str(e)
            print(f"[DL] 事件驱动超时 → 转入轮询: {e}")

        # =========================
        # 策略②：轮询兜底
        # =========================
        file = self._poll_new_file(pattern="*.xlsx", timeout=poll_timeout)
        if file:
            self.tasks[task_id]["state"] = "DONE"
            self.tasks[task_id]["path"] = str(file)
            return self._save_copy(file, filename)

        # =========================
        # ③安全失败
        # =========================
        self.tasks[task_id]["state"] = "FAILED"
        print(f"[DL] 下载失败但 browser 保持存活")
        return None

    # =========================
    # 事件保存 + 文件稳定判定
    # =========================
    def _save_download(self, download, task_id, filename=None):
        """保存下载文件，等待文件稳定"""
        save_name = filename or download.suggested_filename or f"dl_{int(time.time())}.xlsx"
        save_path = str(self.download_dir / save_name)
        download.save_as(save_path)
        self.tasks[task_id]["state"] = "DOWNLOADING"

        # 文件稳定判定（核心改进：连续3次大小不变才确认完成）
        path = Path(save_path)
        if self._wait_file_stable(path):
            self.tasks[task_id]["state"] = "DONE"
            self.tasks[task_id]["path"] = save_path
            size = os.path.getsize(save_path) // 1024
            print(f"[DL] 下载完成: {save_name} ({size}KB)")
            return save_path

        self.tasks[task_id]["state"] = "FAILED"
        return None

    def _wait_file_stable(self, path, timeout=30):
        """
        文件稳定判定（防 .crdownload / 写入未完成）
        连续3次检测大小不变 = 完成
        """
        last_size = -1
        stable_count = 0
        start = time.time()

        while True:
            if not path.exists():
                time.sleep(0.2)
                continue

            # 跳过临时文件
            if str(path).endswith(".crdownload"):
                time.sleep(0.3)
                continue

            size = path.stat().st_size
            if size == 0:
                time.sleep(0.3)
                continue

            if size == last_size:
                stable_count += 1
            else:
                stable_count = 0
                last_size = size

            # 连续稳定 3 次 = 完成
            if stable_count >= 3:
                return True

            if time.time() - start > timeout:
                print(f"[DL] 文件稳定超时: {path}")
                return False

            time.sleep(0.3)

    # =========================
    # 策略②：轮询兜底
    # =========================
    def _poll_new_file(self, pattern="*.xlsx", timeout=240):
        """轮询下载目录，找出点击后出现的新文件"""
        seen = set(glob.glob(str(self.download_dir / pattern)))
        start = time.time()

        print(f"[DL] 文件轮询开始（超时{timeout}s）...")

        while time.time() - start < timeout:
            current = set(glob.glob(str(self.download_dir / pattern)))
            current = {f for f in current if not f.endswith(".crdownload")}
            new_files = current - seen

            if new_files:
                latest = max(new_files, key=os.path.getmtime)
                if self._wait_file_stable(Path(latest)):
                    return latest

            time.sleep(2)

        print(f"[DL] 文件轮询超时（{timeout}s）")
        return None

    def _save_copy(self, src, filename=None):
        """复制轮询到的文件"""
        if not filename:
            return str(src)
        dest = str(self.download_dir / filename)
        import shutil
        shutil.copy2(src, dest)
        size = os.path.getsize(dest) // 1024
        print(f"[DL] 文件已复制: {filename} ({size}KB)")
        return dest

    # =========================
    # 状态查询
    # =========================
    def get_status(self, task_id):
        return self.tasks.get(task_id, {"state": "UNKNOWN"})

    def get_active_tasks(self):
        return {k: v for k, v in self.tasks.items()
                if v["state"] in ("WAITING", "TRIGGERED", "DOWNLOADING")}

    def status(self):
        """兼容 v1 的 status() 接口"""
        active = self.get_active_tasks()
        return {
            "state": "DONE" if not active else list(active.values())[0]["state"],
            "active_tasks": len(active),
            "total_tasks": len(self.tasks),
        }


# =========================
# 向后兼容别名
# =========================
DownloadManager = DownloadManagerV2
