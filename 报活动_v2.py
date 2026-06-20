"""
Temu 报活动 v2 — 完整9步流程（2026-06-12 端到端验证通过）
========================================================
基于 Playwright（connect_over_cdp + 原生 mode）操作 Temu Drawer。

已验证并通过的完整9步流程：
  ① 分析活动列表 → body.innerText 正则提取活动
  ② 打开 Drawer → button.innerText='批量报名活动'
  ③ 勾选专题活动 → Beast UI checkIcon DIV
  ④ 主题弹窗勾选5个 → Table1 tbody 完整名称匹配
  ⑤ 站点选择17站 → 108LI下拉，白名单匹配+安全检查
  ⑥ 选择商品（逐页全选，设100条/页，622→623个全中）
  ⑦ 生成模板并下载 → 记时间戳，验证最新文件
  ⑧ 活动核价过滤 → python3 活动核价.py <模板.xlsx>
  ⑨ 上传过滤模板 → 导入 → 确认并报名活动

⚠️ 文件上传关键发现（2026-06-12 实测）：
  - connect_over_cdp 模式下所有方法均无法上传文件
  - 必须用 Playwright 原生模式（launch_persistent_context）
  - file_chooser.set_files() 后需等2-3秒让 React 更新显示
  - 不要用 fi.files.length 判断上传是否成功

运行前提：
  - Edge 以 CDP 9222 启动并已登录 Temu
  - 页面在营销活动首页: https://agentseller.temu.com/activity/marketing-activity
"""

import json
import re
import sys
from pathlib import Path

# ===== 配置 =====
CDP_URL = "http://127.0.0.1:9222"
TEMU_MARKETING_URL = "https://agentseller.temu.com/activity/marketing-activity"

# 筛选条件
MIN_DISCOUNT = 6.0   # 折扣 ≥ 6折
MAX_DAYS = 20        # 天数 ≤ 20天
EXCLUDE_KEYWORDS = ["爆款", "秒杀"]

# 活动类型（勾选哪个）
ACTIVITY_TYPE = "专题活动"

# 白名单站点（17个欧洲站，已去掉意大利站）
WHITE_LIST_SITES = [
    "波兰站", "匈牙利站", "立陶宛站", "丹麦站", "奥地利站",
    "斯洛伐克站", "德国站", "捷克站", "西班牙站", "葡萄牙站",
    "斯洛文尼亚站", "法国站", "比利时站", "荷兰站", "罗马尼亚站",
    "芬兰站", "瑞典站"
]

# ===== 工具函数 =====

def parse_discount(text: str) -> float:
    """从文本提取折扣数字。'≤ 8折' → 8.0, '≤ 6.5折' → 6.5"""
    m = re.search(r'[≤<]\s*(\d+\.?\d*)\s*折', text)
    return float(m.group(1)) if m else 999

def parse_days(text: str) -> int:
    """从文本提取天数。'（20天）' → 20"""
    m = re.search(r'（(\d+)天）', text)
    return int(m.group(1)) if m else 999

def should_exclude(name: str) -> bool:
    """检查活动名称是否含排除关键词"""
    return any(kw in name for kw in EXCLUDE_KEYWORDS)

def extract_activities(body_text: str) -> list[dict]:
    """
    从页面 body.innerText 中提取活动列表。
    """
    activities = []
    pattern = re.compile(
        r'【(.+?)】(.+?)\n.*?'
        r'(\d{4}-\d{2}-\d{2})～(\d{4}-\d{2}-\d{2})'
        r'（(\d+)天）.*?'
        r'[≤<]\s*(\d+\.?\d*)\s*折',
        re.DOTALL
    )
    for m in pattern.finditer(body_text):
        category = m.group(1)
        name = m.group(2).strip()
        full_name = f"【{category}】{name}"
        days = int(m.group(5))
        discount = float(m.group(6))
        activities.append({
            "category": category,
            "name": name,
            "full_name": full_name,
            "days": days,
            "discount": discount,
            "start": m.group(3),
            "end": m.group(4),
        })
    return activities

def filter_activities(activities: list[dict]) -> list[dict]:
    """按条件筛选活动"""
    result = []
    for a in activities:
        if should_exclude(a["full_name"]):
            continue
        if a["discount"] < MIN_DISCOUNT:
            continue
        if a["days"] > MAX_DAYS:
            continue
        result.append(a)
    return result


# ===== 步骤实现 =====

class TemuMarketingV2:
    """Temu 报活动 v2 自动化"""

    def __init__(self):
        self.activities = []
        self.filtered = []

    # ── 步骤①：分析活动列表 ──

    def analyze_activities(self, body_text: str) -> dict:
        """分析活动列表，返回筛选结果"""
        all_acts = extract_activities(body_text)
        self.activities = all_acts
        self.filtered = filter_activities(all_acts)

        excluded = [a for a in all_acts if a not in self.filtered]

        print(f"\n{'='*60}")
        print(f"活动列表分析")
        print(f"{'='*60}")
        print(f"全部活动: {len(all_acts)} 个")
        print(f"符合条件: {len(self.filtered)} 个")
        print(f"排除: {len(excluded)} 个")
        print()

        if self.filtered:
            print("✅ 符合条件的活动:")
            for i, a in enumerate(self.filtered, 1):
                print(f"  {i}. {a['full_name']}")
                print(f"     ≤{a['discount']}折 | {a['days']}天 | {a['start']}～{a['end']}")
        else:
            print("⚠️ 没有符合条件的活动")

        if excluded:
            print(f"\n❌ 被排除的活动:")
            for a in excluded:
                reasons = []
                if should_exclude(a["full_name"]):
                    reasons.append("含排除关键词")
                if a["discount"] < MIN_DISCOUNT:
                    reasons.append(f"折扣{a['discount']}折<{MIN_DISCOUNT}折")
                if a["days"] > MAX_DAYS:
                    reasons.append(f"天数{a['days']}>{MAX_DAYS}")
                print(f"  - {a['full_name']} ({', '.join(reasons)})")

        return {
            "total": len(all_acts),
            "filtered": len(self.filtered),
            "excluded": len(excluded),
            "activities": self.filtered,
        }

    # ── 步骤②：打开 Drawer ──

    def open_drawer_js(self) -> str:
        """返回点击'批量报名活动'按钮的JS"""
        return """
        (() => {
            const btn = [...document.querySelectorAll('button')]
                .find(b => b.innerText && b.innerText.trim() === '批量报名活动');
            if (!btn) return 'BUTTON_NOT_FOUND';
            btn.scrollIntoView({block: 'center'});
            btn.click();
            return 'CLICKED';
        })()
        """

    def check_drawer_open_js(self) -> str:
        """返回检查Drawer是否打开的JS"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"],[class*="drawer"],[role="dialog"]');
            if (!drawer) return JSON.stringify({open: false});
            const visible = drawer.checkVisibility ? drawer.checkVisibility() : true;
            return JSON.stringify({
                open: true,
                visible: visible,
                text: drawer.innerText.substring(0, 300)
            });
        })()
        """

    # ── 步骤③：勾选专题活动 ──

    def check_activity_type_js(self, activity_type: str = "专题活动") -> str:
        """返回勾选指定活动类型的JS（必须点 checkIcon DIV）"""
        return f"""
        (() => {{
            const target = '{activity_type}';
            const drawer = document.querySelector('[class*="Drawer"],[class*="drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const items = [...drawer.querySelectorAll('*')]
                .filter(e => e.innerText && e.innerText.trim() === target && e.children.length === 0);
            if (!items.length) return 'TEXT_NOT_FOUND';
            const targetEl = items[0];
            const label = targetEl.closest('label');
            const checkIcon = label
                ? label.querySelector('[data-testid="beast-core-checkbox-checkIcon"]')
                : targetEl.parentElement?.querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
            if (checkIcon) {{
                checkIcon.click();
                return 'CLICKED_CHECKICON';
            }}
            targetEl.click();
            return 'CLICKED_TEXT';
        }})()
        """

    def verify_checkbox_checked_js(self, activity_type: str = "专题活动") -> str:
        """返回验证checkbox是否已选中的JS"""
        return f"""
        (() => {{
            const target = '{activity_type}';
            const drawer = document.querySelector('[class*="Drawer"],[class*="drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const items = [...drawer.querySelectorAll('*')]
                .filter(e => e.innerText && e.innerText.trim() === target && e.children.length === 0);
            if (!items.length) return 'TEXT_NOT_FOUND';
            const label = items[0].closest('label');
            const beastCheckbox = label
                ? label.querySelector('[data-testid="beast-core-checkbox"]')
                : null;
            if (beastCheckbox) {{
                return beastCheckbox.getAttribute('data-checked') === 'true' ? 'CHECKED' : 'NOT_CHECKED';
            }}
            const input = label ? label.querySelector('input[type="checkbox"]') : null;
            return input ? (input.checked ? 'CHECKED' : 'NOT_CHECKED') : 'UNKNOWN';
        }})()
        """

    # ── 步骤④：检查\"修改\"按钮 ──

    def check_modify_button_js(self) -> str:
        """返回检查'修改'按钮的JS"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"],[class*="drawer"]');
            if (!drawer) return JSON.stringify({error: 'NO_DRAWER'});
            const text = drawer.innerText;
            const hasThemeRow = text.includes('选择专题活动主题');
            const modifyBtns = [...drawer.querySelectorAll('button, span')]
                .filter(e => e.innerText && e.innerText.trim() === '修改');
            return JSON.stringify({
                hasThemeRow: hasThemeRow,
                modifyBtnCount: modifyBtns.length,
                snippet: text.substring(text.indexOf('专题活动'), text.indexOf('专题活动') + 200)
            });
        })()
        """

    # ── 步骤⑤：主题弹窗勾选（完整名称匹配） ──

    def select_themes_js(self, theme_names: list) -> str:
        """返回在主题弹窗中勾选指定主题的JS"""
        names_json = json.dumps(theme_names, ensure_ascii=False)
        return f"""
        (() => {{
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const rows = modal.querySelectorAll('table')[1].querySelector('tbody').querySelectorAll('tr');
            const names = {names_json};
            let count = 0;
            for (let r = 0; r < rows.length; r++) {{
                const tds = rows[r].querySelectorAll('td');
                if (tds.length < 3) continue;
                const n = tds[2].innerText.split('\\n')[0];
                if (names.indexOf(n) >= 0) {{
                    rows[r].scrollIntoView({{block: 'center'}});
                    const ci = rows[r].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (ci) {{ ci.click(); count++; }}
                }}
            }}
            return '勾选了 ' + count + ' 个主题';
        }})()
        """

    # ── 步骤⑥：站点选择（17站白名单） ──

    def select_sites_js(self) -> str:
        """返回选择17个欧洲站的JS"""
        sites_json = json.dumps(WHITE_LIST_SITES, ensure_ascii=False)
        return f"""
        (() => {{
            const drawer = document.querySelector('[class*="Drawer"]');
            const head = drawer.querySelector('[data-testid="beast-core-select-header"]');
            if (!head) return 'NO_HEAD';
            head.click();
            // 等待面板出现
            const panel = document.querySelector('[class*="ST_dropdownPanel"]');
            if (!panel) return 'NO_PANEL';
            const items = panel.querySelectorAll('li');
            const names = {sites_json};
            let count = 0;
            for (let i = 0; i < items.length; i++) {{
                const n = items[i].innerText.trim();
                if (names.indexOf(n) >= 0) {{
                    items[i].scrollIntoView({{block: 'center'}});
                    const ci = items[i].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (ci) {{ ci.click(); count++; }}
                }}
            }}
            // 安全检查：取消多余站点
            for (let i = 0; i < items.length; i++) {{
                const n = items[i].innerText.trim();
                const checked = items[i].getAttribute('data-checked');
                if (checked === 'true' && names.indexOf(n) < 0) {{
                    const ci = items[i].querySelector('[data-testid="beast-core-checkbox-checkIcon"]');
                    if (ci) ci.click();
                }}
            }}
            head.click();
            return '勾选了 ' + count + ' 个站点';
        }})()
        """

    # ── 步骤⑦：商品选择（逐页全选） ──

    def open_select_goods_js(self) -> str:
        """返回点击'选择商品'按钮的JS"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText.trim() === '选择商品');
            if (btn.length) { btn[0].click(); return 'CLICKED'; }
            return 'NOT_FOUND';
        })()
        """

    def set_page_size_100_js(self) -> str:
        """返回设置每页100条的JS"""
        return """
        (() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const sel = modal.querySelector('[class*="PGT_sizeSelect"] [data-testid="beast-core-select-header"]');
            if (!sel) return 'NO_SIZE_SELECT';
            sel.click();
            const items = document.querySelectorAll('[class*="ST_dropdownPanel"] li');
            for (let i = 0; i < items.length; i++) {
                if (items[i].innerText.trim() === '100') {
                    items[i].click();
                    return 'SET_100';
                }
            }
            return '100_NOT_FOUND';
        })()
        """

    def select_page_all_js(self) -> str:
        """返回全选当前页并翻页的JS。返回 'DONE' + 已选数量 或下一页。"""
        return """
        (() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            // 点全选
            const ci = modal.querySelector('.add-goods_pagination__73bvr [data-testid="beast-core-checkbox-checkIcon"]');
            if (ci) ci.click();
            const next = modal.querySelector('[data-testid="beast-core-pagination-next"]');
            const disabled = next && next.classList.contains('PGT_disabled_5-120-1');
            const sel = modal.querySelector('.add-goods_right__WAraa')?.innerText?.substring(0, 30) || '?';
            if (disabled) return 'DONE:' + sel;
            next.click();
            return 'NEXT:' + sel;
        })()
        """

    def confirm_goods_js(self) -> str:
        """返回确认商品选择的JS"""
        return """
        (() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const btns = modal.querySelectorAll('button');
            for (let i = 0; i < btns.length; i++) {
                if (btns[i].innerText.trim() === '确认') { btns[i].click(); return 'CONFIRMED'; }
            }
            return 'CONFIRM_NOT_FOUND';
        })()
        """

    # ── 步骤⑧：生成模板 ──

    def generate_template_js(self) -> str:
        """返回点击'生成模板'按钮的JS"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText && b.innerText.trim() === '生成模板');
            if (btn.length) { btn[0].click(); return 'CLICKED'; }
            return 'NOT_FOUND';
        })()
        """

    # ── 步骤⑨：上传导入 ──

    def click_select_file_js(self) -> str:
        """返回点击'选择文件'按钮的JS（⚠️ 仅配合 Playwright 原生 mode 使用）"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText.trim() === '选择文件');
            if (btn.length) { btn[0].click(); return 'CLICKED'; }
            return 'NOT_FOUND';
        })()
        """

    def click_start_import_js(self) -> str:
        """返回点击'开始导入'按钮的JS"""
        return """
        (() => {
            const drawer = document.querySelector('[class*="Drawer"]');
            if (!drawer) return 'NO_DRAWER';
            const btn = [...drawer.querySelectorAll('button')]
                .filter(b => b.innerText.trim() === '开始导入');
            if (btn.length) { btn[0].click(); return 'CLICKED'; }
            return 'NOT_FOUND';
        })()
        """

    def click_confirm_import_js(self) -> str:
        """返回点击'确认并报名活动'按钮的JS"""
        return """
        (() => {
            const modal = document.querySelector('[data-testid="beast-core-modal"]');
            if (!modal) return 'NO_MODAL';
            const btns = modal.querySelectorAll('button');
            for (let i = 0; i < btns.length; i++) {
                if (btns[i].innerText.trim() === '确认并报名活动') { btns[i].click(); return 'CLICKED'; }
            }
            return 'NOT_FOUND';
        })()
        """


# ===== CLI =====

def print_usage():
    print("""
Temu 报活动 v2 — 完整9步流程（2026-06-12 端到端验证通过 ✅）

用法:
  python3 报活动_v2.py analyze    # 步骤①：分析活动列表（只读）
  python3 报活动_v2.py step2      # 步骤②~③：打开Drawer + 勾选专题活动
  python3 报活动_v2.py steps4-9   # 步骤④~⑨：显示所有JS命令
  python3 报活动_v2.py full       # 完整流程参考（JS命令列表）

完整验证状态（2026-06-12 实测）：
  ① 分析活动列表   ✅  body.innerText 正则提取46个→筛选5个
  ② 打开 Drawer    ✅  button文本匹配
  ③ 勾选专题活动   ✅  checkIcon DIV
  ④ 主题弹窗勾选   ✅  Table1完整名称匹配5个
  ⑤ 站点选择17站   ✅  108LI白名单+安全检查
  ⑥ 选择商品       ✅  设100条/页，逐页全选，623个全部选中
  ⑦ 生成模板       ✅  下载298425行/12MB
  ⑧ 核价过滤       ✅  活动核价.py → 保留77735行
  ⑨ 上传导入       ✅  2570条校验成功，0失败

⚠️ 文件上传需配合 Playwright 原生 mode：
  不要用 connect_over_cdp，要用 launch_persistent_context。
  详见架构.md 第2.4节。
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1]
    v2 = TemuMarketingV2()

    if cmd == "analyze":
        print("分析活动列表（需要先手动复制 body.innerText）...")
        print("请在浏览器控制台运行: document.body.innerText")
        print("然后粘贴到这里（Ctrl+D 结束）:")
        text = sys.stdin.read()
        v2.analyze_activities(text)

    elif cmd == "step2":
        print("步骤②~③：打开Drawer + 勾选专题活动")
        print("=" * 40)
        print("在浏览器控制台依次运行:")
        print()
        print("1. 打开Drawer:")
        print(v2.open_drawer_js())
        print()
        print("2. 检查Drawer:")
        print(v2.check_drawer_open_js())
        print()
        print("3. 勾选专题活动:")
        print(v2.check_activity_type_js())
        print()
        print("4. 验证勾选:")
        print(v2.verify_checkbox_checked_js())
        print()
        print("5. 检查修改按钮:")
        print(v2.check_modify_button_js())

    elif cmd in ("steps4-9", "full"):
        print("步骤④~⑨：完整流程JS命令")
        print("=" * 60)
        print()
        print("── 步骤④：主题弹窗勾选 ──")
        print("JS:")
        print(v2.select_themes_js([
            "【大流量扶持】周末48H大折扣专区（06/20-06/21）",
            "【营销热点】独立日X夏季大促8折专场",
            "【营销热点】独立日X夏季大促85折大促",
            "【大流量扶持】周末48H大折扣专区（06/13-06/14）",
            "【大流量扶持】限时6折专区（6月）",
        ]))
        print()
        print("然后点'确认'关闭弹窗:")
        print('browser_console: var btns=modal.querySelectorAll("button"); for(var i=0;i<btns.length;i++){if(btns[i].innerText.trim()==="确认"){btns[i].click();break;}}')
        print()
        print("── 步骤⑤：站点选择 ──")
        print("JS:")
        print(v2.select_sites_js())
        print()
        print("── 步骤⑥：商品选择 ──")
        print("JS (开商品弹窗):")
        print(v2.open_select_goods_js())
        print()
        print("JS (设100条/页):")
        print(v2.set_page_size_100_js())
        print()
        print("JS (逐页全选，每步确认):")
        print("  每页执行一次，直到底部显示 DONE:")
        print("  " + v2.select_page_all_js())
        print()
        print("JS (确认关闭):")
        print(v2.confirm_goods_js())
        print()
        print("── 步骤⑦：生成模板 ──")
        print("先记时间: date '+%Y-%m-%d %H:%M:%S'")
        print("JS:")
        print(v2.generate_template_js())
        print("等下载完成，ls -la 检查最新文件")
        print()
        print("── 步骤⑧：核价过滤 ──")
        print("python3 活动核价.py ~/Downloads/报名商品信息 (N).xlsx")
        print()
        print("── 步骤⑨：上传导入 ──")
        print("⚠️ 必须用 Playwright 原生模式上传文件")
        print("JS (点击选择文件后配合 file_chooser.set_files):")
        print(v2.click_select_file_js())
        print("等2-3秒让 React 更新显示文件名")
        print("JS (开始导入):")
        print(v2.click_start_import_js())
        print("JS (确认并报名):")
        print(v2.click_confirm_import_js())
        print()
        print("✅ 完成!")

    else:
        print(f"未知命令: {cmd}")
        print_usage()
