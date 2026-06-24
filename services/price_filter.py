"""
核价过滤服务 — services/price_filter.py
=========================================
对已下载的模板执行核价过滤，逻辑集中管理。
"""
import os
import sys
import pandas as pd
from config.prices import PRICE_MIN, PRICE_CAP


def filter_template(input_path, output_path=None):
    """
    对模板执行核价过滤。
    返回：过滤后文件路径 / None
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_已过滤{ext}"

    print(f"读取: {input_path}")

    xl = pd.ExcelFile(input_path)
    sheet_names = xl.sheet_names
    print(f"Sheet: {sheet_names}")

    df1 = pd.read_excel(input_path, sheet_name=0)
    df2 = pd.read_excel(input_path, sheet_name=1) if len(sheet_names) >= 2 else None

    original_count = len(df1)

    site_col = df1.columns[8]    # 站点列
    price_col = df1.columns[9]   # 活动申报价格列

    # Step 1: 删除低于核价的行
    threshold = df1[site_col].map(PRICE_MIN)
    below = df1[price_col] < threshold
    deleted = below.sum()
    df1 = df1[~below].copy()

    # Step 2: 超过上限的降为上限
    cap = df1[site_col].map(PRICE_CAP)
    above_cap = df1[price_col] > cap
    capped = above_cap.sum()
    df1.loc[above_cap, price_col] = cap[above_cap].astype(float)

    unchanged = len(df1) - capped
    remaining = len(df1)

    print(f"原始: {original_count} 行")
    print(f"删除(价格 < 核价): {deleted} 行")
    print(f"改价(价格 > 上限 → 上限): {capped} 行")
    print(f"保持不变: {unchanged} 行")
    print(f"保留: {remaining} 行")

    if df2 is not None:
        print(f"Sheet2({sheet_names[1]}): {len(df2)} 行, 保持不变")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name=sheet_names[0], index=False)
        if df2 is not None:
            df2.to_excel(writer, sheet_name=sheet_names[1], index=False)

    print(f"已保存: {output_path}")
    return output_path
