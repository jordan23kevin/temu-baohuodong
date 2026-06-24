"""
步骤①：分析活动列表 — 条件筛选 + 日期连续 + 最多6个
"""
import json
from datetime import date, timedelta
from config.settings import MIN_DISCOUNT, MAX_DAYS, MAX_ACTIVITIES, EXCLUDE_KEYWORDS
from utils.date_parser import parse_discount, parse_activity_dates, days_between, is_expired
from utils.log import log


def extract_and_filter(page):
    """DOM 提取活动 → 基础筛选 → 日期排序 → 连续无空挡 → 最多6个"""
    log("分析活动列表...")

    # ---- DOM 提取 ----
    raw = page.evaluate("""() => {
        const tables = document.querySelectorAll('table.TB_tableWrapper_5-120-1');
        if (tables.length < 2) return [];
        const rows = tables[1].querySelectorAll('tr');
        const acts = [];
        for (let i = 0; i < rows.length; i++) {
            const cells = rows[i].querySelectorAll('td');
            if (cells.length < 6) continue;
            const name = cells[0].innerText.trim().split('\\n')[0];
            if (!name) continue;
            acts.push({name, dateText: cells[1].innerText, discText: cells[2].innerText});
        }
        return acts;
    }""")
    log(f"页面共 {len(raw)} 个活动")

    # ---- 基础筛选 ----
    today = date.today()
    candidates = []

    for a in raw:
        name = a["name"]
        if "长期有效" in a["dateText"]:
            continue
        discount = parse_discount(a["discText"])
        if discount is None or discount < MIN_DISCOUNT:
            continue
        if any(kw in name for kw in EXCLUDE_KEYWORDS):
            continue

        dr = parse_activity_dates(a["dateText"], name)
        if dr is None:
            log(f"  无法解析日期，跳过: {name}")
            continue
        start_d, end_d = dr
        days = days_between(start_d, end_d)
        if days > MAX_DAYS:
            continue
        if is_expired(end_d, today):
            log(f"  已过期，跳过: {name} ({start_d}~{end_d})")
            continue

        candidates.append({
            "name": name, "start": start_d, "end": end_d,
            "days": days, "discount": discount,
        })

    log(f"符合条件: {len(candidates)} 个活动")
    for c in candidates:
        log(f"  {c['name']} ({c['start']}~{c['end']}, {c['days']}天, {c['discount']}折)")

    # ---- 日期排序 + 连续无空挡 ----
    candidates.sort(key=lambda x: x["start"])
    selected = []
    for c in candidates:
        if not selected:
            selected.append(c)
        else:
            last_end = selected[-1]["end"]
            if c["start"] <= last_end + timedelta(days=1):
                selected.append(c)
            else:
                log(f"  日期不连续，跳过: {c['name']} ({c['start']}~{c['end']})")
        if len(selected) >= MAX_ACTIVITIES:
            break

    theme_names = [s["name"] for s in selected]
    log(f"最终选定: {len(theme_names)} 个活动")
    return theme_names
