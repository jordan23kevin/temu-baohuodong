"""
日志工具 — utils/log.py
=========================
GBK-safe 日志，纯文本无 emoji。
"""
import time


def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)


def log_step(step_name, status="开始"):
    log(f"[STEP] {step_name} — {status}")


def log_result(label, value):
    log(f"  {label}: {value}")
