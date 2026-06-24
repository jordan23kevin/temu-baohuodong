"""
步骤②③④⑤：Drawer 操作（打开→勾选专题→选主题→选站点）
"""
import json, time
from utils.log import log
from config.sites import SITE_NAMES


def open_drawer(page):
    """② 打开批量报名 Drawer"""
    log("打开批量报名 Drawer...")
    page.locator("button").filter(has_text="批量报名活动").first.click()
    time.sleep(3)


def select_activity_type(page):
    """③ 勾选专题活动类型 + 关确认弹窗"""
    log("勾选专题活动类型...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const items = [...drawer.querySelectorAll('*')].filter(e =>
            e.innerText && e.innerText.trim() === '专题活动' && e.children.length === 0);
        if (!items.length) return;
        const label = items[0].closest('label');
        const ci = label?.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
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


def select_themes(page, theme_names):
    """④ 主题弹窗勾选"""
    log("打开主题弹窗...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const btn = [...drawer.querySelectorAll('button, span')].filter(e =>
            e.innerText && e.innerText.trim() === '修改');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(2)

    log(f"勾选 {len(theme_names)} 个主题...")
    result = page.evaluate(f"""() => {{
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return 'NO_MODAL';
        const rows = modal.querySelector('tbody').querySelectorAll('tr');
        const names = {json.dumps(theme_names)};
        let count = 0;
        for (let r = 0; r < rows.length; r++) {{
            const tds = rows[r].querySelectorAll('td');
            if (tds.length < 3) continue;
            const n = (tds[2].innerText || '').split('\\n')[0];
            if (names.indexOf(n) >= 0) {{
                rows[r].scrollIntoView({{block: 'center'}});
                const ci = rows[r].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                if (ci) {{ ci.click(); count++; }}
            }}
        }}
        return count;
    }}""")
    log(f"已勾选 {result} 个主题")

    # 点确认
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
        if (btn) btn.click();
    }""")
    time.sleep(1)


def select_sites(page):
    """⑤ 选择17个欧洲站点"""
    log("选择 17 个欧洲站点...")
    result = page.evaluate(f"""() => {{
        const drawer = document.querySelector('[class*="Drawer"]');
        const head = drawer.querySelector('[data-testid="beast-core-select-header"]');
        if (!head) return 'NO_HEAD';
        head.click();
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return 'NO_PANEL';
        const items = panel.querySelectorAll('li');
        const names = {json.dumps(SITE_NAMES)};
        let count = 0;
        for (let i = 0; i < items.length; i++) {{
            const n = items[i].innerText.trim();
            if (names.indexOf(n) >= 0) {{
                items[i].scrollIntoView({{block: 'center'}});
                const ci = items[i].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                if (ci) {{ ci.click(); count++; }}
            }}
        }}
        // 安全检查：取消不在白名单的已选项
        for (let i = 0; i < items.length; i++) {{
            const n = items[i].innerText.trim();
            const checked = items[i].getAttribute('data-checked');
            if (checked === 'true' && names.indexOf(n) < 0) {{
                const ci = items[i].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                if (ci) ci.click();
            }}
        }}
        head.click();
        return count;
    }}""")
    log(f"已选 {result} 个站点")
    time.sleep(1)
