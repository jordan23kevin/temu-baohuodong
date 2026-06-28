"""
项目入口 — entrypoint/run.py
==============================
唯一启动入口。clone 后只需：
  pip install -r requirements.txt
  python entrypoint/run.py
"""
import sys
import os

# 把项目根目录加到 sys.path（这样 import 才能找到 core/ workflow/ 等）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log
from state.recovery import print_resume_info
from workflow.activity_pipeline import ActivityPipeline


def main():
    log("==" * 25)
    log("Temu 报活动 — v4.1.2 (Engineering OS)")
    log("==" * 25)

    # ---- 检测是否有可恢复的任务 ----
    if print_resume_info():
        log("[RECOVERY] 将跳过已完成步骤，从断点继续")
    else:
        log("[RECOVERY] 无恢复任务，全新开始")

    # ---- 执行 ----
    pipeline = ActivityPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
