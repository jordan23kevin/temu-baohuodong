"""Temu 批量报名活动 — 通过 CDP 连接 Edge 完成营销活动报名流程"""
import asyncio, sys, json, os, time
from playwright.async_api import async_playwright
sys.stdout.reconfigure(encoding='utf-8')

CDP_URL = "http://localhost:9222"

# 默认活动站点（欧洲站）
DEFAULT_SITES = [
    "波兰站", "匈牙利站", "立陶宛站", "丹麦站", "奥地利站",
    "斯洛伐克站", "德国站", "捷克站", "西班牙站",
    "葡萄牙站", "斯洛文尼亚站", "法国站", "比利时站", "荷兰站",
    "罗马尼亚站", "芬兰站", "瑞典站",
]


async def connect():
    """连接 Edge 浏览器，返回 (p, browser, page)"""
    p = await async_playwright().start()
    browser = await p.chromium.connect_over_cdp(CDP_URL)
    page = browser.contexts[0].pages[0]
    return p, browser, page


async def open_batch_registration():
    """打开批量报名活动页面（或连接当前已打开的页面）"""
    p, browser, page = await connect()
    print(f"当前页面: {page.url}")
    print(f"标题: {await page.title()}")
    return p, browser, page


async def check_activity_type(activity_type="专题活动"):
    """勾选活动类型（如 专题活动、限时折扣、秒杀、官方促）"""
    p, browser, page = await connect()
    label = page.locator(f"text={activity_type}").first
    if await label.count() > 0:
        await label.click()
        await asyncio.sleep(0.3)
        # 验证选中状态
        result = await page.evaluate("""(kw) => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === kw) {
                    const cb = el.closest('label')?.querySelector('input[type="checkbox"]') ||
                              el.parentElement?.querySelector('input[type="checkbox"]');
                    if (cb) return cb.checked;
                }
            }
            return null;
        }""", activity_type)
        print(f"已勾选 '{activity_type}' checked={result}")
    else:
        print(f"未找到 '{activity_type}'")
    await browser.close()


async def select_sites(sites: list):
    """在'选择活动站点'下拉框中勾选指定站点

    操作流程:
    1. 找到'选择活动站点'行的'请选择' → 点击打开下拉框
    2. 下拉框是 Beast UI Select 多选组件，选项以 LI 列表呈现
    3. 下拉框有滚动条 (containerH~168, totalH~3024)
    4. 每个站点是 LI 元素，需 scrollIntoView 后点 checkIcon 勾选
    5. 点击页面主区域 (800, 400) 关闭下拉框
    """
    p, browser, page = await connect()

    # Step 1: 点击'请选择'打开下拉框
    await page.evaluate("""() => {
        const formItems = document.querySelectorAll('[data-testid="beast-core-form-item"]');
        for (const item of formItems) {
            if (item.textContent.includes('选择活动站点')) {
                const selectValue = item.querySelector('[class*="ST_selectValue"]');
                if (selectValue) { selectValue.click(); return; }
                const input = item.querySelector('input');
                if (input) { input.click(); return; }
            }
        }
    }""")
    await asyncio.sleep(1)
    print("已打开站点下拉框")

    # Step 2: 滚动勾选目标站点（默认无选中，直接勾选）
    result = await page.evaluate("""(targets) => {
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return {error: 'no dropdown panel'};

        const viewH = 168;
        const totalH = panel.scrollHeight;
        const checked = [];
        const notFound = [];

        for (const target of targets) {
            let found = false;
            for (let st = 0; st <= totalH; st += viewH) {
                panel.scrollTop = st;
                const lis = panel.querySelectorAll('li');
                for (const li of lis) {
                    if (li.textContent.trim() === target) {
                        li.scrollIntoView({block: 'center'});
                        const checkIcon = li.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                        if (checkIcon) checkIcon.click();
                        checked.push(target);
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            if (!found) notFound.push(target);
        }
        panel.scrollTop = 0;
        return {checked, notFound};
    }""", sites)

    print(f"已勾选 {len(result['checked'])} 个站点: {json.dumps(result['checked'], ensure_ascii=False)}")
    if result['notFound']:
        print(f"未找到 {len(result['notFound'])} 个: {json.dumps(result['notFound'], ensure_ascii=False)}")

    # Step 3: 点击页面主区域关闭下拉框（抽屉外左侧）
    await page.mouse.click(800, 400)
    await asyncio.sleep(0.5)
    print("已关闭下拉框")

    await browser.close()
    return result


async def click_modify_theme():
    """点击'选择专题活动主题'行的'修改'按钮"""
    p, browser, page = await connect()
    # 在包含"选择专题活动主题"的 form-item 中找"修改"按钮
    container = page.locator("[class*='Form_item']").filter(has_text="选择专题活动主题").first
    if await container.count() > 0:
        btn = container.locator("button, a, span").filter(has_text="修改").first
        if await btn.count() > 0:
            await btn.click()
            await asyncio.sleep(2)
            print("已点击'修改'按钮")
        else:
            print("未找到'修改'按钮")
    else:
        print("未找到'选择专题活动主题'行")
    await browser.close()


async def get_all_themes():
    """滚动读取全部专题活动主题列表"""
    p, browser, page = await connect()

    themes = await page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="select-theme"]');
        if (items.length === 0) return [];

        // 找到滚动容器
        let container = items[0];
        for (let i = 0; i < 10; i++) {
            container = container.parentElement;
            if (!container) break;
            const s = window.getComputedStyle(container);
            if (s.overflowY === 'auto' || s.overflowY === 'scroll') break;
        }

        const seen = new Set();
        const results = [];
        const viewH = container.clientHeight;
        const totalH = container.scrollHeight;

        for (let scrollTo = 0; scrollTo <= totalH; scrollTo += viewH) {
            container.scrollTop = scrollTo;
            const visible = document.querySelectorAll('[class*="select-theme"]');
            for (const v of visible) {
                const text = v.textContent.trim();
                if (!seen.has(text) && text.length > 2) {
                    seen.add(text);
                    results.push(text.slice(0, 200));
                }
            }
        }

        // 滚回顶部
        container.scrollTop = 0;
        return results;
    }""")

    print(f"共 {len(themes)} 个专题活动主题:")
    for i, t in enumerate(themes):
        print(f"  {i+1}. {t}")

    # 返回 JSON 供后续处理
    print(f"\\nJSON: {json.dumps(themes, ensure_ascii=False)}")
    await browser.close()
    return themes


async def select_themes(keywords: list):
    """根据关键词勾选专题活动主题

    主题列表是 TABLE 结构，每行 TR 含4个 TD:
      TD[0] — checkbox (TB_checkCell) 内有 [data-testid='beast-core-checkbox-checkIcon']
      TD[1] — 类别
      TD[2] — 主题名 (select-theme_activityThematicName)
      TD[3] — 标签 (NEW/报名Deals专享资源)

    关键:
    1. 必须点击 [data-testid='beast-core-checkbox-checkIcon'] div，点 label 或 input 无效！
    2. 必须先用 scrollIntoView 滚动到可见区域，否则在滚动区外的元素点击无效！
    """
    p, browser, page = await connect()

    selected = await page.evaluate("""(kwList) => {
        const items = document.querySelectorAll('[class*="select-theme"][class*="activityThematicName"]');
        const selected = [];
        for (const item of items) {
            const text = item.textContent.trim();
            for (const kw of kwList) {
                if (text.includes(kw)) {
                    // 向上找 TR
                    let row = item;
                    while (row && row.tagName !== 'TR') row = row.parentElement;
                    if (!row) continue;

                    // 滚动到可见区域（关键！否则点击无效）
                    row.scrollIntoView({block: 'center'});

                    // 找 checkbox icon（点这个才有效！不能点 label 或 input）
                    const checkIcon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (checkIcon) {
                        // 检查是否已勾选
                        const label = row.querySelector('[data-testid="beast-core-checkbox"]');
                        const wasChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                        if (!wasChecked) {
                            checkIcon.click();
                        }
                        selected.push(text.slice(0, 80));
                    }
                    break;
                }
            }
        }
        return selected;
    }""", keywords)

    print(f"已勾选 {len(selected)} 个主题: {json.dumps(selected, ensure_ascii=False)}")
    await browser.close()
    return selected


async def select_theme_by_criteria(
    exclude_keywords: list = None,
    min_discount: float = None,
    require_deals: bool = False,
    max_days: int = None,
):
    """按条件筛选并勾选专题活动主题

    参数:
        exclude_keywords: 排除含这些关键词的主题（如 ['秒杀', '爆款']）
        min_discount: 最低折扣（如 6.0 表示 >= 6折）
        require_deals: 是否必须有"报名Deals专享资源"标签
        max_days: 最大活动天数（如 10 表示 <= 10天）

    返回: 匹配的主题名称列表
    """
    p, browser, page = await connect()

    result = await page.evaluate("""(params) => {
        const tableMap = {};
        // 从主页表格获取时长/折扣数据
        const allTrs = document.querySelectorAll('tr');
        for (const tr of allTrs) {
            const tds = tr.querySelectorAll('td');
            if (tds.length >= 6) {
                const name = tds[0].textContent.trim();
                const time = tds[1]?.textContent.trim() || '';
                const discount = tds[2]?.textContent.trim() || '';
                const dayMatch = time.match(/(\\d+)天/);
                const discMatch = discount.match(/(\\d+\\.?\\d*)折/);
                if (name && dayMatch) {
                    tableMap[name.slice(0, 60)] = {
                        days: parseInt(dayMatch[1]),
                        discount: discMatch ? parseFloat(discMatch[1]) : null
                    };
                }
            }
        }

        const items = document.querySelectorAll('[class*="select-theme"][class*="activityThematicName"]');
        const matched = [];
        for (const item of items) {
            const nameSpan = item.querySelector('span');
            const name = nameSpan ? nameSpan.textContent.trim() : '';
            const tagEl = item.querySelector('[class*="act-label-tag"]');
            const tag = tagEl ? tagEl.textContent.trim() : '';
            const hasDeals = tag.includes('Deals') || tag.includes('专享资源');

            // 条件1: 排除关键词
            if (params.excludeKeywords) {
                let skip = false;
                for (const kw of params.excludeKeywords) {
                    if (name.includes(kw)) { skip = true; break; }
                }
                if (skip) continue;
            }

            // 条件3: 必须有Deals
            if (params.requireDeals && !hasDeals) continue;

            // 从名称提取折扣
            const dm = name.match(/(\\d+\\.?\\d*)\\s*折/);
            let discount = dm ? parseFloat(dm[1]) : null;

            // 从主页表格补充
            if (discount === null) {
                for (const [k, v] of Object.entries(tableMap)) {
                    if (name.length >= 8 && (name.slice(0, 8) === k.slice(0, 8) || name.slice(0, 12) === k.slice(0, 12))) {
                        discount = v.discount;
                        break;
                    }
                }
            }

            // 条件2: 折扣 >= min
            if (params.minDiscount !== null && (discount === null || discount < params.minDiscount)) continue;

            // 获取时长
            let days = null;
            for (const [k, v] of Object.entries(tableMap)) {
                if (name.length >= 8 && (name.slice(0, 8) === k.slice(0, 8) || name.slice(0, 12) === k.slice(0, 12))) {
                    days = v.days;
                    break;
                }
            }

            // 条件4: 时长 <= max
            if (params.maxDays !== null && (days === null || days > params.maxDays)) continue;

            // 勾选
            let row = item;
            while (row && row.tagName !== 'TR') row = row.parentElement;
            if (row) {
                const checkIcon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                if (checkIcon) {
                    checkIcon.click();
                    matched.push(name.slice(0, 80));
                }
            }
        }
        return matched;
    }""", {
        "excludeKeywords": exclude_keywords or [],
        "minDiscount": min_discount,
        "requireDeals": require_deals,
        "maxDays": max_days,
    })

    print(f"按条件筛选，已勾选 {len(result)} 个主题:")
    for i, r in enumerate(result):
        print(f"  {i+1}. {r}")

    await browser.close()
    return result


async def filter_and_select(
    exclude_keywords: list = None,
    min_discount: float = 6.0,
    max_days: int = 20,
):
    """通过主页+弹窗数据交叉匹配，筛选并勾选专题活动主题 (v2)

    匹配逻辑:
    1. 读取主页活动表格（含完整折扣、天数）
    2. 读取弹窗主题列表
    3. 对每个弹窗主题，模糊匹配到最相似的主页活动
    4. 用主页数据补全弹窗中缺失的折扣信息
    5. 应用 C1(弹窗名不含爆款/秒杀) + C2(折扣>=min) + C4(天数<=max)
    6. 勾选通过的主题（使用 scrollIntoView 确保可见）

    参数:
        exclude_keywords: 排除含这些关键词的主题（默认 ['爆款', '秒杀']）
        min_discount: 最低折扣（默认 6.0）
        max_days: 最大活动天数（默认 20）

    返回: 勾选的主题名称列表
    """
    if exclude_keywords is None:
        exclude_keywords = ["爆款", "秒杀"]

    p, browser, page = await connect()

    result = await page.evaluate("""(params) => {
        // === 1. 读取主页活动表格 (6列) ===
        const tables = document.querySelectorAll('table');
        const mainData = [];
        for (const t of tables) {
            const trs = t.querySelectorAll('tr');
            for (const tr of trs) {
                const tds = tr.querySelectorAll('td');
                if (tds.length === 6) {
                    let name = tds[0].textContent.trim();
                    name = name.replace(/\\.[\\w-]+\\{[^}]+\\}/g, '').replace(/\\s+/g, ' ');
                    const timeText = tds[1].textContent.trim();
                    const discountText = tds[2].textContent.trim();
                    const dayMatch = timeText.match(/(\\d+)天/);
                    const discMatch = discountText.match(/(\\d+\\.?\\d*)/);
                    if (name.length > 5 && name.includes('【')) {
                        mainData.push({
                            name: name.slice(0, 200),
                            days: dayMatch ? parseInt(dayMatch[1]) : 999,
                            discount: discMatch ? parseFloat(discMatch[1]) : null
                        });
                    }
                }
            }
        }

        // === 2. 读取弹窗主题列表 ===
        let container = null;
        const items = document.querySelectorAll('[class*="select-theme"][class*="activityThematicName"]');
        if (items.length > 0) {
            container = items[0];
            for (let i = 0; i < 15; i++) {
                container = container.parentElement;
                if (!container) break;
                const s = window.getComputedStyle(container);
                if (s.overflowY === 'auto' || s.overflowY === 'scroll') break;
            }
        }

        const seen = new Set();
        const modalData = [];
        const validCats = ['清仓进阶', '秒杀进阶', '大促进阶-限时活动'];

        if (container) {
            const vh = container.clientHeight;
            const th = container.scrollHeight;
            for (let st = 0; st <= th + vh; st += vh) {
                container.scrollTop = st;
                const trs = document.querySelectorAll('tr');
                for (const tr of trs) {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length >= 4) {
                        const nameEl = tr.querySelector('[class*="select-theme"][class*="activityThematicName"]');
                        const cat = tds[1]?.textContent.trim() || '';
                        const timeNote = tds[3]?.textContent.trim() || '';
                        const name = nameEl ? nameEl.textContent.trim() : '';
                        if (name.length > 3 && !seen.has(name) && validCats.includes(cat)) {
                            seen.add(name);
                            const dm = timeNote.match(/(\\d+)天/);
                            const discm = name.match(/(\\d+\\.?\\d*)\\s*折/);
                            modalData.push({
                                name: name,
                                cat: cat,
                                days: dm ? parseInt(dm[1]) : 999,
                                discount: discm ? parseFloat(discm[1]) : null,
                            });
                        }
                    }
                }
            }
            container.scrollTop = 0;
        }

        // === 3. 模糊匹配 ===
        function tokenize(name) {
            const tokens = new Set();
            const brackets = name.match(/【([^】]+)】/g);
            if (brackets) for (const b of brackets) tokens.add(b);
            for (const kw of ['周末48','48H','48h','大流量','大折扣','满减','父亲节',
                '早夏','年中','世界杯','Temu Week','品牌','专属','新品','清仓','Deals',
                '6折','7折','8折','85折','9折','95折','75折','5.5折','限时额外加补',
                '短期助力','高爆发']) {
                if (name.toLowerCase().includes(kw.toLowerCase())) tokens.add(kw.toLowerCase());
            }
            return tokens;
        }

        function similarity(a, b) {
            const ta = tokenize(a), tb = tokenize(b);
            if (!ta.size || !tb.size) return 0;
            let inter = 0, union = 0;
            for (const t of ta) { if (tb.has(t)) inter++; union++; }
            for (const t of tb) { if (!ta.has(t)) union++; }
            return union ? inter / union : 0;
        }

        // 为每个弹窗主题匹配最佳主页活动
        const checked = [];
        for (const m of modalData) {
            let bestScore = 0, bestMain = null;
            for (const main of mainData) {
                let score = similarity(m.name, main.name);
                if (m.days === main.days && m.days < 999) score += 0.4;
                if (score > bestScore) { bestScore = score; bestMain = main; }
            }

            // === 4. 应用筛选条件 ===
            // C1: 弹窗名称不含排除关键词
            let c1 = true;
            for (const kw of params.excludeKeywords) {
                if (m.name.includes(kw)) { c1 = false; break; }
            }

            // C2: 折扣 >= min（优先弹窗自身折扣，其次主页匹配）
            let discount = m.discount;
            if (discount === null && bestMain && bestScore >= 0.10) {
                discount = bestMain.discount;
            }
            const c2 = discount !== null && discount >= params.minDiscount;

            // C4: 天数 <= max（弹窗天数）
            const c4 = m.days <= params.maxDays;

            if (c1 && c2 && c4) {
                // 勾选
                const nameEl = document.querySelector('[class*="select-theme"][class*="activityThematicName"]');
                // Re-find matching element
                const allItems = document.querySelectorAll('[class*="select-theme"][class*="activityThematicName"]');
                for (const item of allItems) {
                    if (item.textContent.trim() === m.name) {
                        let row = item;
                        while (row && row.tagName !== 'TR') row = row.parentElement;
                        if (!row) continue;
                        // 滚动到可见
                        row.scrollIntoView({block: 'center'});
                        const checkIcon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                        if (checkIcon) {
                            const label = row.querySelector('[data-testid="beast-core-checkbox"]');
                            const wasChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                            if (!wasChecked) checkIcon.click();
                        }
                        checked.push(m.name.slice(0, 80));
                        break;
                    }
                }
            }
        }
        return checked;
    }""", {
        "excludeKeywords": exclude_keywords,
        "minDiscount": min_discount,
        "maxDays": max_days,
    })

    print(f"按条件筛选，已勾选 {len(result)} 个主题:")
    for i, r in enumerate(result):
        print(f"  {i+1}. {r}")

    await browser.close()
    return result


async def select_all_products(page_size: int = 100):
    """在商品选择弹窗中，设置每页条数→逐页全选→确认

    操作流程:
    1. 点击抽屉中'选择商品'按钮，打开'选择您要报名活动的商品'弹窗
    2. 设置每页条数为 100（通过 PGT_sizeSelect 下拉框）
    3. 从第 1 页开始，点击'全选'→ 点击'下一页'，循环直到最后一页
    4. 点击弹窗底部'确定'按钮确认选择

    弹窗结构:
    - 容器: DIV.MDL_innerWrapper, 约 1000x611, 居中
    - 全选: 文本"全选" → 向上找 row → 点 checkIcon
    - 分页: UL.PGT_outerWrapper
      - PGT_totalText: "共 N 条"
      - PGT_sizeChanger + PGT_sizeSelect: 每页条数下拉 (ST_selectValue)
      - PGT_prev / PGT_next: 上/下一页 (LI, disabled 时含 PGT_disabled)
      - PGT_pagerItem: 页码 (active 时含 PGT_pagerItemActive)
    - 确定按钮: button text='确定'
    """
    p, browser, page = await connect()

    # Step 1: 点击'选择商品'按钮打开弹窗
    result = await page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === '选择商品' && b.offsetParent !== null) {
                b.click();
                return {clicked: true};
            }
        }
        return {clicked: false};
    }""")
    print(f"点击'选择商品': {result}")
    await asyncio.sleep(2)

    # Step 2: 设置每页条数
    # 先获取当前每页条数
    info = await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w || !w.offsetParent) return {error: 'modal not open'};
        const sv = w.querySelector('[class*="PGT_sizeSelect"] [class*="ST_selectValue"]');
        const curSize = sv ? sv.textContent.trim() : '?';
        const totalEl = w.querySelector('[class*="PGT_totalText"]');
        const total = totalEl ? totalEl.textContent.trim() : '?';
        return {curSize, total};
    }""")
    print(f"当前每页: {info.get('curSize')}, 总数: {info.get('total')}")

    cur_size = info.get('curSize', '?')
    target_size = str(page_size)

    if cur_size != target_size:
        # 点击下拉框
        await page.evaluate("""(size) => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            const sv = w.querySelector('[class*="PGT_sizeSelect"] [class*="ST_selectValue"]');
            if (sv) sv.click();
        }""", target_size)
        await asyncio.sleep(0.5)

        # 选择目标条数
        sel_result = await page.evaluate("""(size) => {
            const lis = document.querySelectorAll('li');
            for (const li of lis) {
                if (li.textContent.trim() === size) {
                    li.click();
                    return {clicked: true};
                }
            }
            return {clicked: false};
        }""", target_size)
        print(f"选择每页{target_size}条: {sel_result}")
        await asyncio.sleep(1)

    # Step 3: 获取总页数
    page_info = await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w || !w.offsetParent) return {error: 'modal not open'};
        const pagers = w.querySelectorAll('[class*="PGT_pagerItem"]');
        const nums = [];
        for (const p of pagers) nums.push(parseInt(p.textContent.trim()));
        const totalPages = nums.length > 0 ? Math.max(...nums) : 1;
        const active = w.querySelector('[class*="PGT_pagerItemActive"]');
        const curPage = active ? active.textContent.trim() : '1';
        return {totalPages, curPage};
    }""")
    total_pages = page_info.get('totalPages', 1)
    print(f"总页数: {total_pages}, 当前页: {page_info.get('curPage')}")

    # Step 4: 如果不在第1页，先跳回第1页
    if page_info.get('curPage') != '1':
        await page.evaluate("""() => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            const pagers = w.querySelectorAll('[class*="PGT_pagerItem"]');
            for (const p of pagers) {
                if (p.textContent.trim() === '1') { p.click(); return; }
            }
        }""")
        await asyncio.sleep(0.5)

    # Step 5: 逐页全选
    for pg in range(1, total_pages + 1):
        await asyncio.sleep(0.5)

        r = await page.evaluate("""(pageNum) => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            if (!w || !w.offsetParent) return {error: 'modal not open'};
            const active = w.querySelector('[class*="PGT_pagerItemActive"]');
            const curPg = active ? active.textContent.trim() : '?';

            const all = w.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '全选' && el.children.length <= 1) {
                    let row = el.parentElement;
                    for (let i = 0; i < 10; i++) {
                        if (!row) break;
                        const icon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                        if (icon) {
                            icon.scrollIntoView({block: 'center'});
                            icon.click();
                            return {clicked: true, targetPage: pageNum, actualPage: curPg};
                        }
                        row = row.parentElement;
                    }
                }
            }
            return {clicked: false, targetPage: pageNum, actualPage: curPg};
        }""", pg)
        await asyncio.sleep(0.3)

        print(f"  第{pg}页 全选={r.get('clicked')} (实际页={r.get('actualPage')})")

        if pg < total_pages:
            nr = await page.evaluate("""() => {
                const w = document.querySelector('[class*="MDL_innerWrapper"]');
                const nextBtn = w.querySelector('[class*="PGT_next"]:not([class*="PGT_disabled"])');
                if (nextBtn) { nextBtn.click(); return {clicked: true}; }
                return {clicked: false};
            }""")
            if not nr.get('clicked'):
                print(f"  下一页按钮不可用，停止在第{pg}页")
                break
            await asyncio.sleep(0.5)

    # Step 6: 点击确定
    await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w) return;
        const btns = w.querySelectorAll('button');
        for (const btn of btns) {
            const t = btn.textContent.trim();
            if ((t === '确定' || t === '确认') && btn.offsetParent) {
                btn.click();
                return;
            }
        }
    }""")
    await asyncio.sleep(0.5)
    print("已点击确定，商品选择完成")

    await browser.close()


async def click_button_by_text(page, text: str):
    """在页面上找可见的 button/span 包含指定文字并点击"""
    result = await page.evaluate("""(kw) => {
        const all = document.querySelectorAll('button, span[class*="BTN_"]');
        for (const el of all) {
            if (el.textContent.trim() === kw && el.offsetParent !== null) {
                el.click();
                return {clicked: true, tag: el.tagName};
            }
        }
        return {clicked: false};
    }""", text)
    return result


async def full_flow():
    """完整流程 v1: 仅在已打开抽屉的情况下使用"""
    print("=== 批量报名活动全流程 ===")
    p, browser, page = await connect()
    print(f"当前页面: {page.url}")

    print("\n--- 勾选专题活动 ---")
    label = page.locator("text=专题活动").first
    if await label.count() > 0:
        await label.click()
        print("已勾选专题活动")
    else:
        print("未找到'专题活动'，尝试点击'批量报名活动'打开抽屉...")
        await click_button_by_text(page, "批量报名活动")
        await asyncio.sleep(1.5)
        label2 = page.locator("text=专题活动").first
        if await label2.count() > 0:
            await label2.click()
            print("已勾选专题活动")
    await asyncio.sleep(0.5)

    print("\n--- 点击修改 ---")
    container = page.locator("[class*='Form_item']").filter(has_text="选择专题活动主题").first
    if await container.count() > 0:
        btn = container.locator("button, a, span").filter(has_text="修改").first
        if await btn.count() > 0:
            await btn.click()
            print("已点击修改")
    await asyncio.sleep(2)

    print("\n--- 获取全部主题 ---")
    # 内联获取主题（使用已有的 page 连接）
    themes = await page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="select-theme"]');
        if (items.length === 0) return [];
        let container = items[0];
        for (let i = 0; i < 10; i++) {
            container = container.parentElement;
            if (!container) break;
            const s = window.getComputedStyle(container);
            if (s.overflowY === 'auto' || s.overflowY === 'scroll') break;
        }
        const seen = new Set();
        const results = [];
        const viewH = container.clientHeight;
        const totalH = container.scrollHeight;
        for (let st = 0; st <= totalH; st += viewH) {
            container.scrollTop = st;
            const visible = document.querySelectorAll('[class*="select-theme"]');
            for (const v of visible) {
                const text = v.textContent.trim();
                if (!seen.has(text) && text.length > 2) {
                    seen.add(text);
                    results.push(text.slice(0, 200));
                }
            }
        }
        container.scrollTop = 0;
        return results;
    }""")
    print(f"共 {len(themes)} 个专题活动主题:")
    for i, t in enumerate(themes):
        print(f"  {i+1}. {t}")
    await browser.close()
    return themes


async def full_flow_v2(
    min_discount: float = 6.0,
    max_days: int = 20,
    sites: list = None,
):
    """完整流程 v2/v3: 从 Seller Central 首页开始，自动导航+全流程

    步骤:
    1. 侧边栏点击"店铺营销"→"营销活动"进入页面（已在则跳过）
    2. 读取活动列表（用于filter2交叉匹配）
    3. 点击"批量报名活动"打开右侧抽屉
    4. 勾选"专题活动"
    5. 点击"修改"打开主题弹窗
    6. filter2 交叉匹配筛选勾选主题
    7. 确认主题选择
    8. 选择活动站点
    9. 选择商品（逐页全选）
    10. 点击"生成模板"
    （以上为 full2，以下为 full3 新增）
    11. 活动核价（删除低于核价的行，高于活动报名价的降为活动报名价）
    12. 回到页面，打开抽屉
    13. 上传过滤后的文件
    14. 点击"开始导入"→"确认并报名活动"

    参数:
        min_discount: 最低折扣（默认 6.0）
        max_days: 最大天数（默认 20）
        sites: 站点列表（默认 DEFAULT_SITES）
    """
    if sites is None:
        sites = DEFAULT_SITES

    print("=" * 50)
    print("  批量报名活动 - 全自动流程")
    print(f"  折扣 >= {min_discount}折, 天数 <= {max_days}天, 站点 {len(sites)}个")
    print("=" * 50)

    p, browser, page = await connect()

    # === Step 1: 导航到营销活动页面 ===
    print("\n[1/10] 导航到营销活动页面...")

    # 如果当前不在 Temu 页面（如跳到了下载页），或卡在登录/认证页，先导航到首页
    if 'temu.com' not in page.url or 'authentication' in page.url:
        print("  当前不在Temu卖家页面，导航到Seller Central首页...")
        try:
            await page.goto('https://agentseller.temu.com/', wait_until='domcontentloaded', timeout=15000)
        except:
            # 如果tab已关闭，用新的context/page
            pass
        await asyncio.sleep(3)

    if 'marketing-activity' not in page.url:
        # 智能导航：先检查"营销活动"子菜单是否已可见
        # 先检查"营销活动"子菜单是否已可见（无需展开）
        direct = await page.evaluate("""() => {
            const anchors = document.querySelectorAll('a');
            for (const a of anchors) {
                if (a.innerText.trim().includes('营销活动') && a.offsetParent !== null) {
                    a.click();
                    return true;
                }
            }
            return false;
        }""")

        if not direct:
            # 子菜单未展开，先点击"店铺营销"
            expand = await page.evaluate("""() => {
                const anchors = document.querySelectorAll('a');
                for (const a of anchors) {
                    if (a.innerText.trim().includes('店铺营销') && a.offsetParent !== null) {
                        a.click();
                        return true;
                    }
                }
                return false;
            }""")
            print(f"  {'已点击店铺营销' if expand else '未找到店铺营销'}")
            # yield 让浏览器渲染子菜单
            await asyncio.sleep(1.0)

            # 再点击"营销活动"
            direct = await page.evaluate("""() => {
                const anchors = document.querySelectorAll('a');
                for (const a of anchors) {
                    if (a.innerText.trim().includes('营销活动') && a.offsetParent !== null) {
                        a.click();
                        return true;
                    }
                }
                return false;
            }""")
            print(f"  {'已点击营销活动' if direct else '未找到营销活动子菜单'}")

        if not direct:
            print("  ⚠ 侧边栏导航失败，尝试在当前页面继续")

        # 等待页面跳转
        await asyncio.sleep(2)
        try:
            await page.wait_for_url('**/marketing-activity**', timeout=10000)
            print(f"  已到达: {page.url}")
        except:
            print(f"  ⚠ 页面未跳转，当前: {page.url}")
    else:
        print("  已在营销活动页面")

    # 刷新页面确保干净状态（无残留抽屉/弹窗）
    if 'temu.com' in page.url:
        try:
            await page.reload(wait_until="domcontentloaded", timeout=15000)
        except:
            print("  刷新失败，尝试继续...")
        await asyncio.sleep(2)
        # 等待活动表格渲染完成
        try:
            await page.wait_for_selector('table tr td', timeout=15000)
            await asyncio.sleep(1)
        except:
            pass
        print("  页面已刷新，状态已重置")

    # === Step 2: 读取活动列表（活动主题/活动时间/申报价格条件） ===
    print("\n[2/10] 读取活动列表...")
    activities = await page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        const results = [];
        for (const t of tables) {
            const trs = t.querySelectorAll('tr');
            for (const tr of trs) {
                const tds = tr.querySelectorAll('td');
                if (tds.length === 6) {
                    let name = tds[0].textContent.trim();
                    const lastBrace = name.lastIndexOf('}');
                    if (lastBrace >= 0) name = name.slice(lastBrace + 1).trim();
                    name = name.replace(/\\s+/g, ' ').slice(0, 120);
                    const time = tds[1].textContent.trim().slice(0, 60);
                    const price = tds[2].textContent.trim().slice(0, 30);
                    if (name.length > 5 && name.includes('【')) {
                        results.push({name, time, price});
                    }
                }
            }
        }
        return results;
    }""")
    print(f"  共 {len(activities)} 个活动:")
    import re
    for i, a in enumerate(activities):
        # 提取天数
        day_m = re.search(r'(\d+)天', a['time'])
        days = int(day_m.group(1)) if day_m else 99
        # 截取时间前半段显示
        time_short = a['time'].split(')')[0] + ')' if ')' in a['time'] else a['time'][:40]
        print(f"  {i+1:2d}. {a['name'][:50]}")
        print(f"      折扣: {a['price']} | 天数: {days}天 | 时间: {time_short[:45]}")
    print()

    # === Step 3: 点击"批量报名活动"打开抽屉 ===
    print("\n[3/10] 打开批量报名抽屉...")
    # 检查抽屉是否已打开
    has_drawer = await page.evaluate("""() => {
        const labels = document.querySelectorAll('*');
        for (const el of labels) {
            if (el.textContent.trim() === '专题活动') return true;
        }
        return false;
    }""")
    if not has_drawer:
        r = await click_button_by_text(page, "批量报名活动")
        if r.get('clicked'):
            print("  已点击'批量报名活动'")
        else:
            print("  ⚠ 未找到'批量报名活动'按钮，尝试在当前页面继续")
        await asyncio.sleep(1.5)
    else:
        print("  抽屉已打开")

    # === Step 4: 勾选"专题活动" ===
    print("\n[4/10] 勾选活动类型...")
    label = page.locator("text=专题活动").first
    if await label.count() > 0:
        await label.click(force=True)
        await asyncio.sleep(0.8)

    # 处理可能弹出的 modal（如规则确认弹窗）
    modal = page.locator('[data-testid="beast-core-modal"]').first
    if await modal.count() > 0:
        try:
            if await modal.is_visible():
                btns = modal.locator('button')
                if await btns.count() > 0:
                    await btns.first.click()
                    print("  已关闭确认弹窗")
                    await asyncio.sleep(0.5)
        except:
            pass

    print("  专题活动 已点击")

    # === Step 5: 点击"修改"打开主题弹窗 ===
    print("\n[5/10] 打开主题弹窗...")
    container = page.locator("[class*='Form_item']").filter(has_text="选择专题活动主题").first
    if await container.count() > 0:
        btn = container.locator("button, a, span").filter(has_text="修改").first
        if await btn.count() > 0:
            await btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await btn.click()
            print("  已点击'修改'")
        else:
            print("  ⚠ 未找到'修改'按钮")
    else:
        print("  ⚠ 未找到'选择专题活动主题'行")
    await asyncio.sleep(2)

    # 验证弹窗真实打开
    modal_open = await page.evaluate("""() => {
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal) return false;
        const r = modal.getBoundingClientRect();
        const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
        const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
        return w > 300 && h > 100 && modal.checkVisibility?.();
    }""")
    if not modal_open:
        print("  ⚠ 弹窗未真实打开，尝试重新点击")
        if await container.count() > 0:
            btn = container.locator("button, a, span").filter(has_text="修改").first
            if await btn.count() > 0:
                await btn.click(force=True)
                await asyncio.sleep(2)

    # === Step 6: filter2 筛选勾选（用 Step 2 的活动数据匹配弹窗主题） ===
    print(f"\n[6/10] filter2 筛选 (折扣>={min_discount}折, 天数<={max_days}天, 排除含爆款/秒杀)...")

    import re
    parsed_activities = []
    for a in activities:
        disc_m = re.search(r'(\d+\.?\d*)', a['price'])
        day_m = re.search(r'(\d+)天', a['time'])
        parsed_activities.append({
            'name': a['name'],
            'discount': float(disc_m.group(1)) if disc_m else None,
            'days': int(day_m.group(1)) if day_m else 999,
        })

    exclude_keywords = ["爆款", "秒杀"]

    result = await page.evaluate("""(params) => {
        // === visibleArea 复用核价的真实可见检测 ===
        function visibleArea(el) {
            if (!el) return {w:0,h:0,area:0};
            const r = el.getBoundingClientRect();
            const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
            const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
            return {w: Math.round(w), h: Math.round(h), area: Math.round(w*h)};
        }

        // === 第一步：从弹窗读取所有主题 ===
        const modal = document.querySelector('[data-testid="beast-core-modal"]');
        if (!modal || !modal.checkVisibility?.()) return {error:'modal_not_open', selected:[]};

        const rows = [...modal.querySelectorAll('tr')];
        const modalThemes = [];

        for (const row of rows) {
            const tds = row.querySelectorAll('td');
            if (tds.length < 4) continue;
            const cat = (tds[1]?.innerText || '').trim();
            const name = (tds[2]?.innerText || '').trim();
            if (!name || name.length < 3) continue;
            const timeText = (tds[3]?.innerText || '').trim();
            const dm = timeText.match(/(\\d+)天/);
            const days = dm ? parseInt(dm[1]) : 999;
            modalThemes.push({name, cat, days, timeText, row});
        }

        // === 第二步：匹配条件（折扣>=min, 天数<=max, 不含排除词）===
        const matchedNames = [];

        for (const mt of modalThemes) {
            // C1: 不含排除关键词
            let c1 = true;
            for (const kw of params.excludeKeywords) {
                if (mt.name.includes(kw)) { c1 = false; break; }
            }
            if (!c1) continue;

            // 从 Step2 活动数据中找名字最匹配的活动
            let matchedAct = null;
            let bestScore = 0;
            for (const act of params.activities) {
                // 名字包含匹配（不要求完全一致）
                const a = act.name.replace(/[（）]/g, '()');
                const m = mt.name.replace(/[（）]/g, '()');
                const score = (a.includes(m.slice(0,15)) || m.includes(a.slice(0,15))) ? 1 : 0;
                if (score > bestScore) { bestScore = score; matchedAct = act; }
            }
            if (!matchedAct) continue;

            // C2: 折扣>=min（从活动列表取）
            const discount = matchedAct.discount;
            const c2 = discount !== null && discount >= params.minDiscount;
            if (!c2) continue;

            // C3: 天数<=max
            const c3 = mt.days <= params.maxDays;
            if (!c3) continue;

            // 全部条件满足 → 勾选
            const checkIcon = mt.row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
            if (checkIcon) {
                const label = mt.row.querySelector('[data-testid="beast-core-checkbox"]');
                const wasChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                if (!wasChecked) {
                    mt.row.scrollIntoView({block: 'center'});
                    checkIcon.click();
                }
                matchedNames.push(mt.name.slice(0, 80));
            }
        }

        return {selected: matchedNames};
    }""", {
        "activities": parsed_activities,
        "excludeKeywords": exclude_keywords,
        "minDiscount": min_discount,
        "maxDays": max_days,
    })

    selected = result.get('selected', [])
    print(f"  已勾选 {len(selected)} 个主题:")
    for i, s in enumerate(selected):
        print(f"    {i+1}. {s}")

    # === Step 7: 确认主题 ===
    print("\n[7/10] 确认主题选择...")
    await page.evaluate("""() => {
        function visibleArea(el) {
            if (!el) return {w:0,h:0,area:0};
            const r = el.getBoundingClientRect();
            const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
            const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
            return {w: Math.round(w), h: Math.round(h), area: Math.round(w*h)};
        }
        const btns = [...document.querySelectorAll('button')]
            .filter(b => b.textContent.trim() === '确认' && !b.disabled && visibleArea(b).area > 0)
            .sort((a,b) => visibleArea(b).area - visibleArea(a).area);
        if (btns.length) {
            btns[0].dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window,button:0}));
            btns[0].dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window,button:0}));
            btns[0].dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window,button:0}));
        }
    }""")
    await asyncio.sleep(1.5)
    print("  已确认")

    # === Step 8: 选择站点 ===
    print(f"\n[8/10] 选择站点 ({len(sites)}个)...")
    # 打开站点下拉框（用 dispatchEvent 触发 React Select）
    await page.evaluate("""() => {
        const formItems = document.querySelectorAll('[data-testid="beast-core-form-item"]');
        for (const item of formItems) {
            if (item.textContent.includes('选择活动站点')) {
                const head = item.querySelector('[class*="ST_head"]') || item.querySelector('[tabindex]');
                if (head) {
                    head.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window,button:0}));
                    head.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window,button:0}));
                    head.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window,button:0}));
                    return;
                }
            }
        }
    }""")
    await asyncio.sleep(1.5)

    # 用 visibleArea 确认下拉面板已打开
    panel_ready = await page.evaluate("""() => {
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return false;
        const r = panel.getBoundingClientRect();
        const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
        const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
        return w > 50 && h > 50 && panel.checkVisibility?.();
    }""")
    if not panel_ready:
        print("  ⚠ 下拉面板未打开，重试...")
        await page.evaluate("""() => {
            const formItems = document.querySelectorAll('[data-testid="beast-core-form-item"]');
            for (const item of formItems) {
                if (item.textContent.includes('选择活动站点')) {
                    const head = item.querySelector('[class*="ST_head"]');
                    if (head) { head.dispatchEvent(new Event('mousedown',{bubbles:true})); head.dispatchEvent(new Event('click',{bubbles:true})); return; }
                }
            }
        }""")
        await asyncio.sleep(1)

    # 先读取下拉框中所有可选站点
    all_available = await page.evaluate("""() => {
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return [];
        const viewH = 168;
        const totalH = panel.scrollHeight;
        const names = [];
        for (let st = 0; st <= totalH; st += viewH) {
            panel.scrollTop = st;
            const lis = panel.querySelectorAll('li');
            for (const li of lis) {
                const name = li.textContent.trim();
                if (name && !names.includes(name)) names.push(name);
            }
        }
        panel.scrollTop = 0;
        return names;
    }""")
    print(f"  下拉框共 {len(all_available)} 个站点: {json.dumps(all_available, ensure_ascii=False)}")

    # 匹配目标站点
    matched = [s for s in sites if any(a == s for a in all_available)]
    not_matched = [s for s in sites if s not in matched]
    if not_matched:
        print(f"  ⚠ 以下站点未在下拉框中找到: {not_matched}")
    if not matched:
        print("  ⚠ 没有匹配到任何目标站点")
        return {"error": "no matching sites", "step": 6}

    # 勾选目标站点（先取消全选，再逐个勾选 checkIcon）
    site_result = await page.evaluate("""(targets) => {
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return {error: 'no dropdown panel'};
        const viewH = 168;
        const totalH = panel.scrollHeight;

        // 第一步：遍历所有 li，取消"全选"
        for (let st = 0; st <= totalH; st += viewH) {
            panel.scrollTop = st;
            const lis = panel.querySelectorAll('li');
            for (const li of lis) {
                const text = li.textContent.trim();
                if (text === '全选') {
                    const checkIcon = li.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (checkIcon) {
                        const label = li.querySelector('[data-testid="beast-core-checkbox"]');
                        const wasChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                        if (wasChecked) {
                            li.scrollIntoView({block: 'center'});
                            checkIcon.click();
                        }
                    }
                    continue;
                }
            }
        }

        // 第二步：逐个勾选目标站点（用 checkIcon，不用 input.click）
        const targetArr = Array.from(targets);
        for (let st = 0; st <= totalH; st += viewH) {
            panel.scrollTop = st;
            const lis = panel.querySelectorAll('li');
            for (const li of lis) {
                const text = li.textContent.trim();
                if (!targetArr.includes(text)) continue;

                const checkIcon = li.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                if (checkIcon) {
                    const label = li.querySelector('[data-testid="beast-core-checkbox"]');
                    const wasChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                    if (!wasChecked) {
                        li.scrollIntoView({block: 'center'});
                        checkIcon.click();
                    }
                }
                const idx = targetArr.indexOf(text);
                if (idx !== -1) targetArr.splice(idx, 1);
                if (targetArr.length === 0) break;
            }
            if (targetArr.length === 0) break;
        }
        panel.scrollTop = 0;
        return {checked: targetArr.length === 0, remaining: targetArr};
    }""", list(matched))

    print(f"  已勾选 {len(matched)} 个站点")

    # 第三步：扫描并取消不在白名单中的已勾选站点（防止残留选中）
    cleanup = await page.evaluate("""(whitelist) => {
        const panel = document.querySelector('[class*="ST_dropdownPanel"]');
        if (!panel) return {error: 'no dropdown panel'};
        const viewH = 168;
        const totalH = panel.scrollHeight;
        const removed = [];
        for (let st = 0; st <= totalH; st += viewH) {
            panel.scrollTop = st;
            const lis = panel.querySelectorAll('li');
            for (const li of lis) {
                const text = li.textContent.trim();
                if (text === '全选') continue;
                const label = li.querySelector('[data-testid="beast-core-checkbox"]');
                const isChecked = label ? label.getAttribute('data-checked') === 'true' : false;
                if (isChecked && !whitelist.includes(text)) {
                    const checkIcon = li.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (checkIcon) {
                        li.scrollIntoView({block: 'center'});
                        checkIcon.click();
                        removed.push(text);
                    }
                }
            }
        }
        panel.scrollTop = 0;
        return {removed};
    }""", list(matched))

    if cleanup.get('removed') and len(cleanup['removed']) > 0:
        print(f"  ⚠ 已取消 {len(cleanup['removed'])} 个非白名单站点: {json.dumps(cleanup['removed'], ensure_ascii=False)}")
    else:
        print("  ✅ 无多余站点，校验通过")

    # 关闭下拉框
    await page.mouse.click(800, 400)
    await asyncio.sleep(0.5)

    # === Step 9: 选择商品 ===
    print("\n[9/10] 选择商品...")
    # 点击"选择商品"按钮
    await page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.trim() === '选择商品' && b.offsetParent !== null) {
                b.click();
                return;
            }
        }
    }""")
    await asyncio.sleep(2)

    # 设置每页100条
    await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w || !w.offsetParent) return;
        const sv = w.querySelector('[class*="PGT_sizeSelect"] [class*="ST_selectValue"]');
        const curSize = sv ? sv.textContent.trim() : '?';
        if (curSize !== '100') {
            if (sv) sv.click();
        }
    }""")
    await asyncio.sleep(0.5)

    # 选择100
    await page.evaluate("""() => {
        const lis = document.querySelectorAll('li');
        for (const li of lis) {
            if (li.textContent.trim() === '100') { li.click(); return; }
        }
    }""")
    await asyncio.sleep(1)

    # 获取总页数
    page_info = await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w || !w.offsetParent) return {error: 'modal not open'};
        const pagers = w.querySelectorAll('[class*="PGT_pagerItem"]');
        const nums = [];
        for (const p of pagers) nums.push(parseInt(p.textContent.trim()));
        const totalPages = nums.length > 0 ? Math.max(...nums) : 1;
        const active = w.querySelector('[class*="PGT_pagerItemActive"]');
        const curPage = active ? active.textContent.trim() : '1';
        const totalEl = w.querySelector('[class*="PGT_totalText"]');
        const total = totalEl ? totalEl.textContent.trim() : '?';
        return {totalPages, curPage, total};
    }""")
    total_pages = page_info.get('totalPages', 1)
    print(f"  商品 {page_info.get('total')}, 每页100条, 共{total_pages}页")

    # 跳到第1页
    if page_info.get('curPage') != '1':
        await page.evaluate("""() => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            const pagers = w.querySelectorAll('[class*="PGT_pagerItem"]');
            for (const p of pagers) {
                if (p.textContent.trim() === '1') { p.click(); return; }
            }
        }""")
        await asyncio.sleep(0.5)

    # 逐页全选
    for pg in range(1, total_pages + 1):
        # 等待当前页渲染
        await asyncio.sleep(0.5)

        # 点击"全选"按钮（找到"全选"文字 → 向上找 checkIcon → 点击）
        r = await page.evaluate("""(pageNum) => {
            const w = document.querySelector('[class*="MDL_innerWrapper"]');
            if (!w || !w.offsetParent) return {error: 'modal not open'};

            const all = w.querySelectorAll('*');
            for (const el of all) {
                if (el.textContent.trim() === '全选' && el.children.length <= 1) {
                    let row = el.parentElement;
                    for (let i = 0; i < 10; i++) {
                        if (!row) break;
                        const icon = row.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                        if (icon) {
                            icon.scrollIntoView({block: 'center'});
                            icon.click();
                            return {clicked: true, page: pageNum};
                        }
                        row = row.parentElement;
                    }
                }
            }
            return {clicked: false, page: pageNum};
        }""", pg)
        await asyncio.sleep(0.3)

        print(f"  第{pg}/{total_pages}页 全选={r.get('clicked')}")

        if pg < total_pages:
            nr = await page.evaluate("""() => {
                const w = document.querySelector('[class*="MDL_innerWrapper"]');
                const nextBtn = w.querySelector('[class*="PGT_next"]:not([class*="PGT_disabled"])');
                if (nextBtn) { nextBtn.click(); return {clicked: true}; }
                return {clicked: false};
            }""")
            if not nr.get('clicked'):
                print(f"  下一页不可用，停止在第{pg}页")
                break
            await asyncio.sleep(0.5)

    # 点击确定关闭商品弹窗
    await page.evaluate("""() => {
        const w = document.querySelector('[class*="MDL_innerWrapper"]');
        if (!w) return;
        const btns = w.querySelectorAll('button');
        for (const btn of btns) {
            const t = btn.textContent.trim();
            if ((t === '确定' || t === '确认') && btn.offsetParent) {
                btn.click();
                return;
            }
        }
    }""")
    await asyncio.sleep(0.5)
    print("  商品选择完成")

    # === Step 10: 生成模板 ===
    print("\n[10/14] 生成模板...")
    start_time = time.time()  # 记录生成时间用于检测新文件
    r = await click_button_by_text(page, "生成模板")
    if r.get('clicked'):
        print("  已点击'生成模板'，模板文件正在下载...")
    else:
        print("  ⚠ 未找到'生成模板'按钮")

    await browser.close()

    # === Step 11: 活动核价 ===
    print("\n[11/14] 活动核价 — 等待模板下载完成...")
    from 活动核价 import find_latest_file, filter_activity_prices

    # 记录生成模板前的最新文件，用于检测新下载
    existing_files = set(os.listdir(os.path.expanduser(r'~\Downloads')))

    # 等待新文件出现（最多等120秒）
    latest = None
    for attempt in range(60):
        await asyncio.sleep(2)
        latest = find_latest_file()
        if latest:
            basename = os.path.basename(latest)
            if basename not in existing_files:
                break
            mtime = os.path.getmtime(latest)
            if mtime > start_time:
                break
        if attempt % 5 == 0:
            print(f"  等待下载... ({attempt * 2}s)")

    if not latest:
        print("  ⚠ 未找到下载的模板文件")
        return result
    print(f"  文件: {os.path.basename(latest)}")
    deleted, remaining = filter_activity_prices(latest)
    filtered_file = latest.replace('.xlsx', '_已过滤.xlsx')

    # ⛔ 安全防护：没用户指令，自动停止在上传前
    print("\n" + "=" * 50)
    print("  ⛔ 活动核价完成！")
    print(f"  已生成: {os.path.basename(filtered_file)}")
    print("  ⚠ 需要你确认后才能继续上传和导入。")
    print("  输入 go 继续上传并导入，直接 Enter 取消：")
    print("=" * 50)
    ans = input("  > ").strip().lower()
    if ans != 'go':
        print("  ⛔ 已取消，未上传/导入。过滤文件已保存，需要时告诉我。")
        await browser.close()
        return result
    print("  继续上传导入...")

    # === Step 12: 回到页面打开抽屉 ===
    print("\n[12/14] 回到页面准备上传...")
    p, browser, page = await connect()

    if 'temu.com' not in page.url:
        await page.goto('https://agentseller.temu.com/activity/marketing-activity', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(2)
        try:
            await page.wait_for_selector('table tr td', timeout=15000)
        except:
            pass

    # 打开批量报名抽屉
    batch_btn = page.locator('text=批量报名活动').first
    if await batch_btn.count() > 0:
        await batch_btn.click(force=True)
        await asyncio.sleep(2)
        print("  抽屉已打开")

    # === Step 13: 上传文件 ===
    print("\n[13/14] 上传过滤后的文件...")
    file_input = page.locator('input[type="file"]')
    if await file_input.count() > 0:
        await file_input.first.set_input_files(filtered_file)
        print(f"  已上传: {os.path.basename(filtered_file)}")
        await asyncio.sleep(1.5)

    # === Step 14: 开始导入 + 确认 ===
    print("\n[14/14] 开始导入并确认...")

    # 点"开始导入" — 用JS滚动到按钮再点击
    r = await page.evaluate('''() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.trim() === '开始导入') {
                let el = btn;
                for (let i = 0; i < 10; i++) {
                    el.scrollIntoView({block: 'center'});
                    el = el.parentElement;
                    if (!el) break;
                }
                setTimeout(() => btn.click(), 500);
                return 'clicked';
            }
        }
        return 'not found';
    }''')
    print(f"  开始导入: {r}")

    # 等弹窗出现
    await asyncio.sleep(4)

    # 点"确认并报名活动"
    modal = page.locator('[data-testid="beast-core-modal"]')
    if await modal.count() > 0:
        confirm_btn = modal.locator('button', has_text='确认并报名')
        if await confirm_btn.count() == 0:
            confirm_btn = modal.locator('button', has_text='确认')
        if await confirm_btn.count() > 0:
            await confirm_btn.first.click()
            print("  已点击确认并报名活动")
            await asyncio.sleep(2)

    print("\n" + "=" * 50)
    print("  全流程完成!")
    print(f"  主题: {len(result)}个, 站点: {len(matched)}个")
    print(f"  商品: {page_info.get('total')}, 共{total_pages}页全选")
    print(f"  活动核价: 删除{deleted}行, 保留{remaining}行")
    print(f"  已上传并提交报名")
    print("=" * 50)

    await browser.close()


def main():
    if len(sys.argv) < 2:
        print("用法: python 报活动.py <action> [args...]")
        print("  open              - 连接并查看当前页面")
        print("  check <类型>      - 勾选活动类型（默认: 专题活动）")
        print("  modify            - 点击'修改'按钮打开主题列表")
        print("  themes            - 滚动读取全部专题活动主题")
        print("  select <kw1,kw2>  - 按关键词勾选主题（逗号分隔）")
        print("  filter <参数>      - 按条件筛选勾选（旧版，仅用弹窗数据）")
        print("       --exclude 秒杀,爆款  排除关键词")
        print("       --min-discount 6.0   最低折扣")
        print("       --deals              必须有Deals资源")
        print("       --max-days 10        最大天数")
        print("  filter2 [参数]    - 按条件筛选勾选（新版，主页+弹窗交叉匹配）")
        print("       --exclude 爆款,秒杀  排除关键词（默认: 爆款,秒杀）")
        print("       --min-discount 6.0   最低折扣（默认: 6.0）")
        print("       --max-days 20        最大天数（默认: 20）")
        print("  sites <站1,站2>  - 勾选活动站点（逗号分隔）")
        print("  products [条数]   - 打开商品选择弹窗→设每页条数→逐页全选→确认（默认100）")
        print("  confirm           - 点击确认按钮")
        print("  full              - 完整流程 v1（需抽屉已打开）")
        print("  full2 [折扣] [天数] [站点] - 完整流程 v2：首页→抽屉→筛选→站点→商品→生成模板")
        print("       默认: 折扣6.0 天数20 站点=18个欧洲站")
        print("  full3 [折扣] [天数]       - 完整流程 v3：full2 + 活动核价 + 上传 + 开始导入 + 确认报名")
        print("       默认: 折扣6.0 天数20")
        return

    action = sys.argv[1]

    if action == "open":
        asyncio.run(open_batch_registration())
    elif action == "check":
        atype = sys.argv[2] if len(sys.argv) > 2 else "专题活动"
        asyncio.run(check_activity_type(atype))
    elif action == "modify":
        asyncio.run(click_modify_theme())
    elif action == "themes":
        asyncio.run(get_all_themes())
    elif action == "select":
        kws = sys.argv[2].split(",") if len(sys.argv) > 2 else []
        asyncio.run(select_themes(kws))
    elif action == "sites":
        sites = sys.argv[2].split(",") if len(sys.argv) > 2 else DEFAULT_SITES
        asyncio.run(select_sites(sites))
    elif action == "products":
        page_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        asyncio.run(select_all_products(page_size))
    elif action == "confirm":
        asyncio.run(click_confirm())
    elif action == "filter":
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--exclude" and i + 1 < len(sys.argv):
                kwargs["exclude_keywords"] = sys.argv[i + 1].split(",")
                i += 2
            elif sys.argv[i] == "--min-discount" and i + 1 < len(sys.argv):
                kwargs["min_discount"] = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--deals":
                kwargs["require_deals"] = True
                i += 1
            elif sys.argv[i] == "--max-days" and i + 1 < len(sys.argv):
                kwargs["max_days"] = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        asyncio.run(select_theme_by_criteria(**kwargs))
    elif action == "filter2":
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--exclude" and i + 1 < len(sys.argv):
                kwargs["exclude_keywords"] = sys.argv[i + 1].split(",")
                i += 2
            elif sys.argv[i] == "--min-discount" and i + 1 < len(sys.argv):
                kwargs["min_discount"] = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--max-days" and i + 1 < len(sys.argv):
                kwargs["max_days"] = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        asyncio.run(filter_and_select(**kwargs))
    elif action == "full":
        asyncio.run(full_flow())
    elif action == "full2":
        min_d = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
        max_d = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        sites = sys.argv[4].split(",") if len(sys.argv) > 4 else DEFAULT_SITES
        asyncio.run(full_flow_v2(min_d, max_d, sites))
    elif action == "full3":
        min_d = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
        max_d = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        asyncio.run(full_flow_v2(min_d, max_d))
    else:
        print(f"未知操作: {action}")


if __name__ == "__main__":
    main()
