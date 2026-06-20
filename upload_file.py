"""上传过滤后的活动模板到 Drawer — Playwright 原生模式"""
import os, time, sys

from playwright.sync_api import sync_playwright

FILTERED_FILE = os.path.expanduser("~/Downloads/报名商品信息 (25)_已过滤.xlsx")
USER_DATA_DIR = r"C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data"
MARKETING_URL = "https://agentseller.temu.com/activity/marketing-activity"

def main():
    if not os.path.exists(FILTERED_FILE):
        print(f"❌ 文件不存在: {FILTERED_FILE}")
        sys.exit(1)
    print(f"📄 准备上传: {os.path.basename(FILTERED_FILE)} ({os.path.getsize(FILTERED_FILE)//1024}KB)")

    with sync_playwright() as p:
        print("🚀 启动 Edge（原生模式，保持登录态）...")
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            channel='msedge',
            args=['--remote-debugging-port=9223', '--remote-allow-origins=*'],
            no_viewport=True,
            bypass_csp=True
        )
        page = context.pages[0] if context.pages else context.new_page()
        print(f"📄 导航到营销活动页面...")
        page.goto(MARKETING_URL, wait_until="domcontentloaded", timeout=30000)
        print("⏳ 等待页面加载（10秒给你登录/确认页）...")
        time.sleep(10)

        # Check if drawer is already open
        drawer_visible = page.evaluate("""() => {
            const d = document.querySelector('[class*="Drawer"][class*="visible"]');
            return d ? true : false;
        }""")
        
        if not drawer_visible:
            print("🔘 点击「批量报名活动」按钮...")
            btn = page.locator("button").filter(has_text="批量报名活动").first
            if btn.count() > 0:
                btn.click()
                time.sleep(3)
            else:
                print("❌ 找不到批量报名活动按钮")
                context.close()
                return

        # Check if 专题活动 is checked
        zt_checked = page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const items = [...drawer.querySelectorAll('*')].filter(e => e.innerText && e.innerText.trim() === '专题活动' && e.children.length === 0);
            if (!items.length) return false;
            const label = items[0].closest('label');
            const cb = label ? label.querySelector('[data-testid="beast-core-checkbox"]') : null;
            return cb ? cb.getAttribute('data-checked') === 'true' : false;
        }""")

        if not zt_checked:
            print("🔘 勾选专题活动...")
            page.evaluate("""() => {
                const drawer = document.querySelector('[class*="Drawer"]');
                const items = [...drawer.querySelectorAll('*')].filter(e => e.innerText && e.innerText.trim() === '专题活动' && e.children.length === 0);
                if (!items.length) return;
                const label = items[0].closest('label');
                const ci = label ? label.querySelector('[data-testid="beast-core-checkbox-checkIcon"]') : null;
                if (ci) ci.click();
            }""")
            time.sleep(2)
            # Close any confirmation modal
            page.evaluate("""() => {
                const modal = document.querySelector('[data-testid="beast-core-modal"]');
                if (modal) {
                    const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
                    if (btn) btn.click();
                }
            }""")
            time.sleep(1)

        # Click file upload button
        print("🔘 点击「选择文件」...")
        upload_btn = page.locator("button").filter(has_text="选择文件").first
        if upload_btn.count() == 0:
            # Try locating inside the drawer
            page.evaluate("""() => {
                const drawer = document.querySelector('[class*="Drawer"]');
                const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择文件');
                if (btn.length) btn[0].click();
            }""")
            time.sleep(2)

        # Use file chooser
        print("📂 等待文件选择器...")
        try:
            with page.expect_file_chooser(timeout=15000) as fc_info:
                if upload_btn.count() > 0:
                    upload_btn.click()
                else:
                    # Already clicked via evaluate above
                    pass
            file_chooser = fc_info.value
            print(f"📎 设置文件: {FILTERED_FILE}")
            file_chooser.set_files(FILTERED_FILE)
            print("⏳ 等待 React 更新（2秒）...")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ file_chooser 失败: {e}")
            # Fallback: try direct set_input_files
            fi = page.locator('input[type="file"]').first
            if fi.count() > 0:
                print("📎 回退: set_input_files...")
                fi.set_input_files(FILTERED_FILE)
                time.sleep(3)

        # Verify upload
        upload_ok = page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const text = drawer.innerText;
            const hasUpload = text.includes('已过滤') || text.includes('.xlsx');
            return hasUpload ? 'FILE_FOUND' : 'NO_FILE_VISIBLE';
        }""")
        print(f"📋 上传状态: {upload_ok}")

        # Wait for user to confirm
        print("\n✅ 文件已上传！请检查 Drawer 是否显示文件名。")
        print("如需继续导入，告诉我后我点「开始导入」和「确认并报名活动」。")
        
        input("\n按 Enter 继续下一步（开始导入）...")
        
        # Click "开始导入"
        print("🔘 点击「开始导入」...")
        page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '开始导入');
            if (btn.length) { btn[0].click(); return true; }
            return false;
        }""")
        time.sleep(3)

        # Click "确认并报名活动" in the confirmation modal
        print("🔘 点击「确认并报名活动」...")
        page.evaluate("""() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return false;
            const btn = [...modal.querySelectorAll('button')].filter(b => b.innerText.trim() === '确认并报名活动');
            if (btn.length) { btn[0].click(); return true; }
            return false;
        }""")
        time.sleep(2)

        print("🎉 活动报名已提交！")
        input("\n按 Enter 退出...")
        context.close()

if __name__ == "__main__":
    main()
