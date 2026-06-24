"""
任务注册表 — core/task_registry.py
====================================
task_id 生成 + 追踪，所有任务必须注册。
"""
import time


def generate_task_id(prefix="task"):
    """生成唯一 task_id：task_<timestamp>"""
    return f"{prefix}_{int(time.time())}"


class TaskRegistry:
    """任务注册表（内存 + state.json 双重记录）"""

    def __init__(self):
        self._tasks = {}  # task_id -> info

    def register(self, task_id, meta=None):
        self._tasks[task_id] = {
            "task_id": task_id,
            "created_at": time.time(),
            "meta": meta or {},
        }
        return task_id

    def get(self, task_id):
        return self._tasks.get(task_id)

    def list_active(self):
        return {k: v for k, v in self._tasks.items()}

    def __len__(self):
        return len(self._tasks)
