"""上传过滤后的活动模板到 Drawer + 导入 — 全自动版"""
import os, sys, time
from playwright.sync_api import sync_playwright

FILTERED_FILE = os.path.expanduser("~/Downloads/报名商品信息 (25)_已过滤.xlsx")
USER_DATA_DIR = r"C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data"
MARKETING_URL = "https://agentseller.temu.com/activity/marketing-activity"

def main():
    if not os.path.exists(FILTERED_FILE):
        print(f"❌ 文件不存在: {FILTERED_FILE}")
        sys.exit(1)
    print(f"📄 文件名: {os.path.basename(FILTERED_FILE)} ({os.path.getsize(FILTERED_FILE)//1024}KB)")

    with sync_playwright() as p:
        print("🚀 启动 Edge（原生模式）...")
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            channel='msedge',
            args=['--remote-debugging-port=9224', '--remote-allow-origins=*'],
            no_viewport=True,
            bypass_csp=True
        )
        page = context.pages[0] if context.pages else context.new_page()
        print("📄 导航到营销页...")
        page.goto(MARKETING_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(8)

        # 打开 Drawer
        drawer_open = page.evaluate("""() => document.querySelector('[class*="Drawer"][class*="visible"]') ? true : false""")
        if not drawer_open:
            print("🔘 点批量报名活动...")
            page.locator("button").filter(has_text="批量报名活动").first.click()
            time.sleep(3)

        # 勾选专题活动
        print("🔘 勾选专题活动...")
        page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const items = [...drawer.querySelectorAll('*')].filter(e => e.innerText && e.innerText.trim() === '专题活动' && e.children.length === 0);
            if (!items.length) return;
            const ci = items[0].closest('label')?.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
            if (ci) ci.click();
        }""")
        time.sleep(2)
        # 关确认弹窗
        page.evaluate("""() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (modal) {
                const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
                if (btn) btn.click();
            }
        }""")
        time.sleep(1)

        # 上传文件
        print("🔘 上传文件...")
        try:
            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.evaluate("""() => {
                    const drawer = document.querySelector('[class*="Drawer"]');
                    const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择文件');
                    if (btn.length) btn[0].click();
                }""")
            fc = fc_info.value
            fc.set_files(FILTERED_FILE)
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ file_chooser: {e}")
            fi = page.locator('input[type="file"]').first
            if fi.count() > 0:
                fi.set_input_files(FILTERED_FILE)
                time.sleep(3)

        # 验证
        status = page.evaluate("""() => {
            const d = document.querySelector('[class*="Drawer"]');
            if (!d) return 'NO_DRAWER';
            return d.innerText.includes('已过滤') ? 'FILE_FOUND' : 'FILE_NOT_VISIBLE';
        }""")
        print(f"📋 {status}")

        # 开始导入
        print("🔘 开始导入...")
        page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '开始导入');
            if (btn.length) btn[0].click();
        }""")
        time.sleep(3)

        # 确认并报名活动
        print("🔘 确认并报名活动...")
        page.evaluate("""() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return;
            const btn = [...modal.querySelectorAll('button')].filter(b => b.innerText.trim() === '确认并报名活动');
            if (btn.length) btn[0].click();
        }""")
        time.sleep(3)

        print("🎉 报名成功提交！")
        context.close()

if __name__ == "__main__":
    main()
