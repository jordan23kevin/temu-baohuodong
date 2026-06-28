"""
步骤⑥：商品选择（逐页全选）
"""
import time
from utils.log import log


def select_products(page):
    """打开商品弹窗 → 设100条/页 → 逐页全选 → 确认"""
    # 1. 打开弹窗
    log("打开商品选择弹窗...")
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === '选择商品' && b.offsetParent !== null)
                { b.click(); return; }
        }
    }""")
    time.sleep(3)

    # 2. 设100条/页（先查当前值，不一致才改）
    log("设为 100 条/页...")
    cur = page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        const sv = w && w.querySelector('[class*="PGT_sizeSelect"] [class*="ST_selectValue"]');
        return sv ? sv.textContent.trim() : '?';
    }""")
    log(f"当前每页: {cur}")
    if cur != '100':
        page.evaluate("""() => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            const sv = w.querySelector('[class*="PGT_sizeSelect"] [class*="ST_selectValue"]');
            if (sv) sv.click();
        }""")
        time.sleep(0.5)
        page.evaluate("""() => {
            const lis = document.querySelectorAll('li');
            for (const li of lis) {
                if (li.textContent.trim() === '100') { li.click(); return; }
            }
        }""")
        time.sleep(3)

    # 回到第1页（保证页码正确）
    page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w) return;
        const item = w.querySelector('[class*="PGT_pagerItem"]');
        if (item && item.textContent.trim() !== '1') item.click();
    }""")
    time.sleep(1)

    # 3. 读总页数
    pg_info = page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w) return {total: 1};
        const items = w.querySelectorAll('[class*="PGT_pagerItem"]');
        const nums = [];
        for (const p of items) nums.push(parseInt(p.textContent.trim()));
        return {total: nums.length ? Math.max(...nums) : 1};
    }""")
    total_pages = pg_info.get('total', 1)
    log(f"总页数: {total_pages}")

    # 4. 逐页全选
    log("逐页全选商品...")
    for pg in range(1, total_pages + 1):
        time.sleep(1)  # 等页面加载
        r = page.evaluate("""(pageNum) => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            if (!w) return {ok: false, reason: 'no_modal'};
            const active = w.querySelector('[class*="PGT_pagerItemActive"]');
            const curPg = active ? active.textContent.trim() : '?';
            // 读取已选数
            const t = w.innerText;
            const m = t.match(/已选\((\d+)\)/);
            const count = m ? m[1] : '?';
            // 方式1: 表头 checkbox 直接勾（优先）
            const hdrIcon = w.querySelector('.beast-core-table thead [data-testid="beast-core-checkbox-checkIcon"], table thead [data-testid="beast-core-checkbox-checkIcon"]');
            if (hdrIcon) { hdrIcon.click(); return {ok: true, pg: pageNum, curPg, count}; }
            // 方式2: 文本"全选" → 向上找 checkIcon（fallback）
            const all = w.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '全选' && el.children.length <= 1) {
                    let row = el.parentElement;
                    for (let i = 0; i < 10; i++) {
                        if (!row) break;
                        const icon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                        if (icon) { icon.click(); return {ok: true, pg: pageNum, curPg, count}; }
                        row = row.parentElement;
                    }
                }
            }
            return {ok: false, pg: pageNum, curPg, count};
        }""", pg)
        log(f"第{pg}页: o={r.get('ok')} page={r.get('curPg')} cnt={r.get('count')}")

        if pg < total_pages:
            nr = page.evaluate("""() => {
                const w = document.querySelector('[class*="MDL_innerWrapper"]');
                const next = w && w.querySelector('[class*="PGT_next"]:not([class*="PGT_disabled"])');
                if (next) { next.click(); return true; }
                return false;
            }""")
            if not nr:
                log(f"下一页不可用，停在第{pg}页")
                break
        time.sleep(0.5)

    # 5. 确认
    page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w) return;
        for (const b of w.querySelectorAll('button')) {
            if (b.textContent.trim() === '确定' || b.textContent.trim() === '确认')
                { b.click(); return; }
        }
    }""")
    time.sleep(1)
    log("商品选择完成")
