"""
步骤⑥：商品选择（逐页全选 + null保护）
"""
import time
from utils.log import log


def select_products(page):
    """打开商品弹窗 → 设100条/页 → 逐页全选 → 确认"""
    log("打开商品选择弹窗...")
    page.evaluate("""() => {
        const drawer = document.querySelector('[class*="Drawer"]');
        const btn = [...drawer.querySelectorAll('button')].filter(b => b.innerText.trim() === '选择商品');
        if (btn.length) btn[0].click();
    }""")
    time.sleep(3)

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

    log("逐页全选商品...")
    for pg in range(1, 20):
        result = page.evaluate("""() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const ci = modal.querySelector('.add-goods_pagination__73bvr [data-testid="beast-core-checkbox-checkIcon"]');
            if (ci) ci.click();
            const next = modal.querySelector('[data-testid="beast-core-pagination-next"]');
            if (!next) return 'DONE:ONEPAGE';
            const disabled = next.classList.contains('PGT_disabled_5-120-1');
            const sel = modal.querySelector('.add-goods_right__WAraa')?.innerText?.substring(0, 30) || '?';
            if (disabled) return 'DONE:' + sel;
            next.click();
            return 'NEXT:' + sel;
        }""")
        log(f"第{pg}页: {result}")
        if result.startswith("DONE"):
            break
        time.sleep(1)

    page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btn = [...modal.querySelectorAll('button')].find(b => b.innerText.trim() === '确认');
        if (btn) btn.click();
    }""")
    time.sleep(1)
    log("商品选择完成")
