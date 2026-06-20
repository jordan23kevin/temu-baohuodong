"""
Temu 报活动 — 全自动一镜到底（Playwright 原生模式）v3.0.0
======================================================
一条命令跑完整个流程：选主题→选站点→选商品→生成模板→核价过滤→上传→导入→报名。
v3.0 架构升级：HermesBrowser 常驻服务 + DownloadManager 事件驱动 + DOM级提取
"""
import os, sys, time, subprocess, json
from pathlib import Path
from playwright.sync_api import sync_playwright
from download_manager import DownloadManager
from hermes_browser import HermesBrowser

# ===== 配置 =====
USER_DATA_DIR = r"C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data"
MARKETING_URL = "https://agentseller.temu.com/activity/marketing-activity"
DOWNLOADS = os.path.expanduser("~/Downloads")

# 17个欧洲站点白名单
SITE_NAMES = [
    "波兰站","匈牙利站","立陶宛站","丹麦站","奥地利站","斯洛伐克站",
    "德国站","捷克站","西班牙站","葡萄牙站","斯洛文尼亚站",
    "法国站","比利时站","荷兰站","罗马尼亚站","芬兰站","瑞典站"
]

# 核价脚本路径
PRICE_FILTER = os.path.join(os.path.dirname(__file__), "活动核价.py")


def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)


def kill_edge():
    """杀死所有 Edge 进程"""
    log("关闭旧 Edge...")
    subprocess.run("taskkill //F //IM msedge.exe", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(3)


def run_price_filter(template_path):
    """运行活动核价过滤"""
    log(f"核价过滤: {os.path.basename(template_path)}")
    result = subprocess.run(
        ["python3", PRICE_FILTER, template_path],
        capture_output=True, text=True, timeout=120
    )
    for line in result.stdout.strip().split("\n"):
        log(f"  {line}")
    # 找输出文件名
    for line in result.stdout.split("\n"):
        if "已保存:" in line:
            filtered = line.split("已保存:")[-1].strip()
            if os.path.exists(filtered):
                return filtered
    return None


def main():
    log("=" * 50)
    log("Temu 报活动 — 全自动一镜到底")
    log("=" * 50)

    # 使用 HermesBrowser 常驻服务（启动/连接/保活）
    brw = HermesBrowser()
    brw.start_edge()
    brw.ensure_alive()
    page = brw.get_page()
    context = brw.get_context()
    dl = DownloadManager(context, page)

    # ===== ① 导航 =====
    log("导航到营销活动页面...")
    page.goto(MARKETING_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(8)

    # ===== ① 分析活动列表（DOM级提取，无需 innerText） =====
    log("分析活动列表...")
    theme_names = page.evaluate("""() => {
        // 直接定位活动数据表（CSS选择器，无 innerText 全量扫描）
        const tables = document.querySelectorAll('table.TB_tableWrapper_5-120-1');
        if (tables.length < 2) return [];
        const rows = tables[1].querySelectorAll('tr');
        const names = [];
        for (let i = 0; i < rows.length; i++) {
            const cells = rows[i].querySelectorAll('td');
            if (cells.length < 6) continue;
            const name = cells[0].innerText.trim().split('\\n')[0];
            if (!name) continue;
            // 跳过长期有效的活动
            const dateText = cells[1].innerText;
            if (dateText.includes('长期有效')) continue;
            const daysMatch = dateText.match(/[（(](\\d+)天[）)]/);
            if (!daysMatch) continue;
            const days = parseInt(daysMatch[1]);
            const discText = cells[2].innerText;
            const discMatch = discText.match(/[≤<]\\s*(\\d+\\.?\\d*)\\s*折/);
            if (!discMatch) continue;
            const discount = parseFloat(discMatch[1]);
            // 筛选：≥6折、≤20天、排除爆款/秒杀
            if (discount >= 6.0 && days <= 20 &&
                !name.includes('爆款') && !name.includes('秒杀')) {
                names.push(name);
            }
        }
        return names;
    }""")
    log(f"  符合条件: {len(theme_names)} 个活动")
    if not theme_names:
        log("❌ 没有符合条件的活动，退出")
        # browser stays open for inspection
        return
    for i, n in enumerate(theme_names, 1):
        log(f"  {i}. {n}")

    # ===== ② 打开 Drawer =====
    log("打开批量报名 Drawer...")
    page.locator("button").filter(has_text="批量报名活动").first.click()
    time.sleep(3)

    # ===== ③ 勾选专题活动 =====
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

    # ===== ④ 选主题 =====
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
    log(f"  已勾选 {result} 个主题")

    # 点确认
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
        if (btn) btn.click();
    }""")
    time.sleep(1)

    # ===== ⑤ 选站点 =====
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
    log(f"  已选 {result} 个站点")
    time.sleep(1)

    # ===== ⑥ 选商品 =====
    log("打开商品选择弹窗...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择商品');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(3)

    # 设100条/页
    log("设为 100 条/页...")
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        const sel = modal?.querySelector('[class*="PGT_sizeSelect"] [data-testid="beast-core-select-header"]');
        if (!sel) return;
        sel.click();
        const items = document.querySelectorAll('[class*="ST_dropdownPanel"] li');
        for (let i = 0; i < items.length; i++) {
            if (items[i].innerText.trim() === '100') { items[i].click(); break; }
        }
    }""")
    time.sleep(2)

    # 逐页全选
    log("逐页全选商品...")
    for pg in range(1, 20):
        result = page.evaluate("""() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const ci = modal.querySelector('.add-goods_pagination__73bvr [data-testid="beast-core-checkbox-checkIcon"]');
            if (ci) ci.click();
            const next = modal.querySelector('[data-testid="beast-core-pagination-next"]');
            const disabled = next && next.classList.contains('PGT_disabled_5-120-1');
            const sel = modal.querySelector('.add-goods_right__WAraa')?.innerText?.substring(0, 30) || '?';
            if (disabled) return 'DONE:' + sel;
            next.click();
            return 'NEXT:' + sel;
        }""")
        log(f"  第{pg}页: {result}")
        if result.startswith("DONE"):
            break
        time.sleep(1)

    # 确认关闭
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
        if (btn) btn.click();
    }""")
    time.sleep(1)
    log("商品选择完成")

    # ===== ⑦ 生成模板（DownloadManager v1.2 绝对稳定版） =====
    log("生成模板...")
    template = dl.generate_template(
        trigger_fn=lambda: page.evaluate("""() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText?.trim() === '生成模板');
            if (btn.length) btn[0].click();
        }"""),
        filename=f"报名商品信息_{int(time.time())}.xlsx",
    )
    if not template:
        log("❌ 下载失败，但浏览器保持存活。请检查后手动重试")
        # browser stays open
        return
    log(f"✅ 下载完成: {os.path.basename(template)} ({os.path.getsize(template)//1024}KB)")

    # ===== ⑧ 核价过滤 =====
    filtered = run_price_filter(template)
    if not filtered:
        log("❌ 核价过滤失败")
        # browser stays open
        return
    log(f"✅ 过滤完成: {os.path.basename(filtered)}")

    # ===== ⑨ 上传+导入+报名 =====
    log("上传过滤后的文件...")
    try:
        with page.expect_file_chooser(timeout=15000) as fc_info:
            page.evaluate("""() => {
                const drawer = document.querySelector('[class*="Drawer"]');
                const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择文件');
                if (btn.length) btn[0].click();
            }""")
        fc = fc_info.value
        fc.set_files(filtered)
        time.sleep(3)
    except Exception as e:
        log(f"⚠️ 上传失败: {e}")
        # browser stays open
        return

    status = page.evaluate("""() => {
        const d = document.querySelector('[class*="Drawer"]');
        return d && d.innerText.includes('已过滤') ? 'FILE_FOUND' : 'FILE_NOT_VISIBLE';
    }""")
    log(f"📋 {status}")

    # ===== 安全暂停：等爸爸确认（通过聊天） =====
    log("=" * 50)
    log("⏸️  核价完成！等待爸爸确认")
    log(f"    过滤后文件: {os.path.basename(filtered)}")
    log("    爸爸说「继续」后再开始导入和报名")
    log("=" * 50)

    log("开始导入...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '开始导入');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(3)

    log("确认并报名活动...")
    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].filter(b => b.innerText.trim() === '确认并报名活动');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(2)

    log("=" * 50)
    log("🎉 报活动全流程完成！")
    log("=" * 50)

    # browser stays open for inspection


if __name__ == "__main__":
    main()
