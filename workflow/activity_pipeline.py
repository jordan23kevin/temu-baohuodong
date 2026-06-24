"""
活动报名流程编排 — workflow/activity_pipeline.py
===================================================
9 步流程编排，支持断点恢复。
"""
from utils.log import log
from core.state_machine import StateMachine, STEPS
from core.task_registry import generate_task_id
from services.browser_service import BrowserService
from workflow.steps.extract import extract_and_filter
from workflow.steps.drawer_ops import open_drawer, select_activity_type, select_themes, select_sites
from workflow.steps.product_select import select_products
from workflow.steps.download_submit import generate_template, run_price_filter, upload_and_submit

# ===== 步骤名称映射 =====
STEP_FUNCS = {
    "EXTRACT_ACTIVITIES": "filter_and_select",
    "OPEN_DRAWER": "step_open_drawer",
    "SELECT_ACTIVITY_TYPE": "step_select_type",
    "SELECT_THEMES": "step_select_themes",
    "SELECT_SITES": "step_select_sites",
    "SELECT_PRODUCTS": "step_select_products",
    "GENERATE_TEMPLATE": "step_generate_template",
    "PRICE_FILTER": "step_price_filter",
    "UPLOAD_IMPORT": "step_upload_import",
}


class ActivityPipeline:
    """活动报名 9 步流程"""

    def __init__(self):
        self.state = StateMachine()
        self.browser = None
        self.page = None
        self.context = None
        self.theme_names = []
        self.template_path = None
        self.filtered_path = None

    def run(self):
        """运行完整流程（自动检测恢复）"""
        task_id = generate_task_id("activity")
        self.state.start(task_id)
        log(f"任务ID: {task_id}")

        # 浏览器
        self.browser = BrowserService()
        self.browser.start()
        self.page = self.browser.get_page()
        self.context = self.browser.get_context()

        # 导航
        log("导航到营销活动页面...")
        self.browser.navigate()

        # ---- 执行各步（状态机驱动） ----
        self._execute("EXTRACT_ACTIVITIES", self._step_extract)
        self._execute("OPEN_DRAWER", lambda: open_drawer(self.page))
        self._execute("SELECT_ACTIVITY_TYPE", lambda: select_activity_type(self.page))
        self._execute("SELECT_THEMES", lambda: select_themes(self.page, self.theme_names))
        self._execute("SELECT_SITES", lambda: select_sites(self.page))
        self._execute("SELECT_PRODUCTS", lambda: select_products(self.page))
        self._execute("GENERATE_TEMPLATE", self._step_generate)
        self._execute("PRICE_FILTER", self._step_filter)
        self._execute("UPLOAD_IMPORT", self._step_upload)

        self.state.done()
        log("全部完成！")
        return True

    def _execute(self, step_name, func):
        """执行一个步骤（状态机记录）"""
        if step_name in self.state.completed_steps:
            log(f"[SKIP] {step_name} 已完成，跳过")
            return

        self.state.enter_step(step_name)
        log(f"[RUN] {step_name}")
        try:
            func()
            self.state.complete_step(step_name)
        except Exception as e:
            self.state.fail(str(e))
            log(f"[FAIL] {step_name}: {e}")
            raise

    def _step_extract(self):
        self.theme_names = extract_and_filter(self.page)
        if not self.theme_names:
            raise RuntimeError("没有符合条件的活动，终止流程")

    def _step_generate(self):
        self.template_path = generate_template(self.page, self.context)

    def _step_filter(self):
        self.filtered_path = run_price_filter(self.template_path)

    def _step_upload(self):
        upload_and_submit(self.page, self.filtered_path)
