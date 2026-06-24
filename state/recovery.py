"""
断点恢复 — state/recovery.py
==============================
基于 state.json 的任务恢复逻辑。
"""
from core.state_machine import StateMachine


def can_resume():
    """检查是否有可恢复的任务"""
    sm = StateMachine()
    return sm.is_resumable()


def get_resume_info():
    """获取恢复信息"""
    sm = StateMachine()
    if not sm.is_resumable():
        return None
    return {
        "task_id": sm.task_id,
        "completed_steps": [s for s in sm.completed_steps],
        "next_step": sm.get_next_step(),
        "remaining_steps": sm.get_remaining_steps(),
        "state": sm.state,
    }


def clear_state():
    """清除状态（全新开始）"""
    sm = StateMachine()
    sm._reset()
    sm.save()


def print_resume_info():
    """打印恢复信息到日志"""
    info = get_resume_info()
    if not info:
        return False
    print(f"[RECOVERY] 检测到未完成任务: {info['task_id']}")
    print(f"[RECOVERY] 已完成: {', '.join(info['completed_steps'])}")
    print(f"[RECOVERY] 下一步: {info['next_step']}")
    return True
