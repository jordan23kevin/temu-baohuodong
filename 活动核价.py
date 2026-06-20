"""
活动核价 — 过滤报名活动模板：删除低于核价的行，高于活动报名价则降为活动报名价
用法: python 活动核价.py <Excel文件路径> [输出路径]
      python 活动核价.py  # 默认查找最新下载的报名商品信息文件
"""

import sys
import os
import glob

# 核价 = 最低门槛（低于此价 → 删除该行）
PRICE_MIN = {
    '波兰站': 55, '匈牙利站': 61, '立陶宛站': 61,
    '斯洛伐克站': 65, '奥地利站': 65,
    '德国站': 73, '捷克站': 74,
    '荷兰站': 77, '西班牙站': 89, '比利时站': 90, '法国站': 90,
    '丹麦站': 95, '斯洛文尼亚站': 95, '葡萄牙站': 98,
    '罗马尼亚站': 108, '瑞典站': 147, '芬兰站': 176
}

# 活动报名价 = 上限（高于此价 → 降为此价）
PRICE_CAP = {
    '波兰站': 65, '匈牙利站': 71, '立陶宛站': 71,
    '斯洛伐克站': 75, '奥地利站': 75,
    '德国站': 83, '捷克站': 84,
    '荷兰站': 87, '西班牙站': 99, '比利时站': 100, '法国站': 100,
    '丹麦站': 105, '斯洛文尼亚站': 105, '葡萄牙站': 108,
    '罗马尼亚站': 118, '瑞典站': 157, '芬兰站': 186
}


def find_latest_file():
    downloads = os.path.expanduser(r'~\Downloads')
    pattern = os.path.join(downloads, '报名商品信息 (*).xlsx')
    files = glob.glob(pattern)
    if not files:
        # fallback to all files
        pattern = os.path.join(downloads, '报名商品信息*.xlsx')
        files = glob.glob(pattern)
    # 排除已过滤的文件
    files = [f for f in files if '_已过滤' not in f]
    if not files:
        return None
    # 按文件编号排序（取数字最大的，即最新的原始下载）
    import re
    def extract_num(f):
        m = re.search(r'\((\d+)\)', f)
        return int(m.group(1)) if m else 0
    return max(files, key=extract_num)


def filter_activity_prices(input_path, output_path=None):
    import pandas as pd

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f'{base}_已过滤{ext}'

    print(f'读取: {input_path}')

    # 读取两个 Sheet
    xl = pd.ExcelFile(input_path)
    sheet_names = xl.sheet_names
    print(f'Sheet: {sheet_names}')

    df1 = pd.read_excel(input_path, sheet_name=0)
    df2 = pd.read_excel(input_path, sheet_name=1) if len(sheet_names) >= 2 else None

    original_count = len(df1)

    site_col = df1.columns[8]  # 站点
    price_col = df1.columns[9]  # 活动申报价格

    # Step 1: 删除活动申报价格 < 核价 的行
    threshold = df1[site_col].map(PRICE_MIN)
    below = df1[price_col] < threshold
    deleted = below.sum()
    df1 = df1[~below].copy()

    # Step 2: 活动申报价格 > 活动报名价 → 降为活动报名价
    cap = df1[site_col].map(PRICE_CAP)
    above_cap = df1[price_col] > cap
    capped = above_cap.sum()
    df1.loc[above_cap, price_col] = cap[above_cap].astype(float)

    unchanged = len(df1) - capped
    remaining = len(df1)

    print(f'原始: {original_count} 行')
    print(f'删除(价格 < 核价): {deleted} 行')
    print(f'改价(价格 > 活动报名价 → 活动报名价): {capped} 行')
    print(f'保持不变(核价 <= 价格 <= 活动报名价): {unchanged} 行')
    print(f'保留: {remaining} 行')

    if df2 is not None:
        print(f'Sheet2({sheet_names[1]}): {len(df2)} 行, 保持不变')

    # 保存两个 Sheet
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df1.to_excel(writer, sheet_name=sheet_names[0], index=False)
        if df2 is not None:
            df2.to_excel(writer, sheet_name=sheet_names[1], index=False)

    print(f'已保存: {output_path}')
    return deleted, remaining


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = find_latest_file()
        if not input_file:
            print('未找到报名商品信息文件，请指定路径: python 活动核价.py <文件路径>')
            sys.exit(1)
        print(f'自动匹配最新文件: {input_file}')

    output_file = sys.argv[2] if len(sys.argv) >= 3 else None
    filter_activity_prices(input_file, output_file)
