"""
全局状态机 — core/state_machine.py
====================================
所有流程/状态集中管理，state 可序列化、可恢复。

状态流：
  INIT → RUNNING → (STEP_N) → DONE / FAILED
"""
import json, time, os
from pathlib import Path

# ===== 状态定义 =====
STATE_INIT = "INIT"
STATE_RUNNING = "RUNNING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"

# ===== 步骤定义 =====
STEPS = [
    "EXTRACT_ACTIVITIES",
    "OPEN_DRAWER",
    "SELECT_ACTIVITY_TYPE",
    "SELECT_THEMES",
    "SELECT_SITES",
    "SELECT_PRODUCTS",
    "GENERATE_TEMPLATE",
    "PRICE_FILTER",
    "UPLOAD_IMPORT",
]

STEP_LABELS = {
    "EXTRACT_ACTIVITIES": "分析活动列表",
    "OPEN_DRAWER": "打开 Drawer",
    "SELECT_ACTIVITY_TYPE": "勾选专题活动",
    "SELECT_THEMES": "选择主题",
    "SELECT_SITES": "选择站点",
    "SELECT_PRODUCTS": "选择商品",
    "GENERATE_TEMPLATE": "生成模板",
    "PRICE_FILTER": "核价过滤",
    "UPLOAD_IMPORT": "上传导入报名",
}


class StateMachine:
    """可序列化的全局状态机"""

    def __init__(self, state_dir=None):
        if state_dir is None:
            state_dir = Path(__file__).resolve().parent.parent / "state"
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self._load()

    def _load(self):
        if self.state_path.exists():
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.task_id = data.get("task_id")
            self.state = data.get("state", STATE_INIT)
            self.current_step = data.get("current_step")
            self.completed_steps = data.get("completed_steps", [])
            self.errors = data.get("errors", [])
            self.meta = data.get("meta", {})
        else:
            self._reset()

    def _reset(self):
        self.task_id = None
        self.state = STATE_INIT
        self.current_step = None
        self.completed_steps = []
        self.errors = []
        self.meta = {}

    def save(self):
        data = {
            "task_id": self.task_id,
            "state": self.state,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "errors": self.errors,
            "meta": self.meta,
        }
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def start(self, task_id):
        """开始一个新任务"""
        self.task_id = task_id
        self.state = STATE_RUNNING
        self.completed_steps = []
        self.errors = []
        self.meta["start_time"] = time.time()
        self.save()
        return self

    def enter_step(self, step_name):
        """进入一个步骤"""
        self.current_step = step_name
        self.meta["step_start"] = time.time()
        self.save()

    def complete_step(self, step_name):
        """完成一个步骤"""
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
        self.current_step = None
        self.save()

    def fail(self, error_msg):
        """标记失败"""
        self.state = STATE_FAILED
        self.errors.append({"step": self.current_step, "error": error_msg, "time": time.time()})
        self.save()

    def done(self):
        """标记完成"""
        self.state = STATE_DONE
        self.meta["end_time"] = time.time()
        if self.meta.get("start_time"):
            elapsed = time.time() - self.meta["start_time"]
            self.meta["elapsed_seconds"] = round(elapsed)
        self.save()

    # ========== 恢复相关 ==========
    def is_resumable(self):
        """是否可以恢复"""
        return (self.task_id is not None
                and self.state in (STATE_RUNNING, STATE_FAILED)
                and self.completed_steps)

    def get_last_completed_step(self):
        """获取最后完成的步骤"""
        if not self.completed_steps:
            return None
        return self.completed_steps[-1]

    def get_next_step(self):
        """获取下一个要执行的步骤"""
        last = self.get_last_completed_step()
        if last is None:
            return STEPS[0]
        try:
            idx = STEPS.index(last)
            if idx + 1 < len(STEPS):
                return STEPS[idx + 1]
        except ValueError:
            pass
        return None

    def get_remaining_steps(self):
        """获取剩余未完成的步骤"""
        return [s for s in STEPS if s not in self.completed_steps]

    # ========== 查询 ==========
    def summary(self):
        return {
            "task_id": self.task_id,
            "state": self.state,
            "completed": len(self.completed_steps),
            "total": len(STEPS),
            "current": self.current_step,
            "errors": len(self.errors),
        }
