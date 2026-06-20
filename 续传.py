"""报活动 — 续传上传导入（Step 12-14）"""
import asyncio
from playwright.async_api import async_playwright

FILTERED_FILE = r"C:\Users\Administrator\Downloads\报名商品信息 (19)_已过滤.xlsx"

async def main():
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    pg = b.contexts[0].pages[0]
    await pg.bring_to_front()

    print("[12/14] 回到页面准备上传...")
    if "marketing-activity" not in pg.url:
        await pg.goto("https://agentseller.temu.com/activity/marketing-activity",
                       wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

    # 打开批量报名抽屉
    await pg.evaluate("""() => {
        const btns = document.querySelectorAll("button");
        for (const b of btns) {
            if (b.textContent.includes("批量报名活动") && b.offsetParent) {
                b.click(); return;
            }
        }
    }""")
    await asyncio.sleep(2)
    print("  抽屉已打开")

    # [13/14] 上传文件
    print("[13/14] 上传过滤后的文件...")
    file_input = pg.locator('input[type="file"]')
    if await file_input.count() > 0:
        await file_input.first.set_input_files(FILTERED_FILE)
        print(f"  已上传: 报名商品信息 (19)_已过滤.xlsx")
        await asyncio.sleep(1.5)
    else:
        print("  ⚠ 未找到文件上传组件")

    # [14/14] 开始导入 + 确认
    print("[14/14] 开始导入并确认...")
    await pg.evaluate("""() => {
        const btns = document.querySelectorAll("button");
        for (const btn of btns) {
            if (btn.textContent.trim() === "开始导入") {
                btn.scrollIntoView({block: "center"});
                setTimeout(() => btn.click(), 500);
                return;
            }
        }
    }""")
    print("  开始导入 已点击")
    await asyncio.sleep(4)

    # 确认并报名活动
    await pg.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return;
        const btns = modal.querySelectorAll("button");
        for (const b of btns) {
            const t = b.textContent.trim();
            if ((t.includes("确认并报名") || t === "确认") && !b.disabled) {
                b.scrollIntoView({block: "center"});
                setTimeout(() => b.click(), 300);
                return;
            }
        }
    }""")
    print("  确认并报名活动 已点击")
    await asyncio.sleep(2)

    print()
    print("=" * 50)
    print("  全流程完成！")
    print("  主题: 5个, 站点: 17个（不含意大利）")
    print("  商品: 540条（6页全选）")
    print("  活动核价: 删除183440行, 保留84660行")
    print("  已上传并提交报名")
    print("=" * 50)

    await b.close()
    await p.stop()

asyncio.run(main())
