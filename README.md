# Temu 报活动 — 100% 复现操作手册

> 版本：v4.1.3 (Engineering OS) · 最后更新：2026-06-29
> 架构：`ARCHITECTURE.md` · 演进：`CHANGELOG.md`

---

## 一、项目说明

Temu 卖家营销中心"批量报名活动"自动化工具。工程操作系统级架构，clone 即可运行。

**入口：** `python entrypoint/run.py`

---

## 二、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install msedge

# 2. 运行
cd "E:/Claude code/Temu自动化/报活动"
python entrypoint/run.py
```

---

## 三、前置条件

- Windows + Edge 浏览器
- Python 3.11+
- Edge 已登录 `agentseller.temu.com`
- CDP 端口 **9222**（固定）
- Edge profile: `C:\Users\Administrator\Desktop\edge-profile`

---

## 四、9步流程

| # | 步骤 | 说明 |
|:-:|------|------|
| ① | 活动提取筛选 | DOM提取 → ≥6折/≤20天/排除关键词 → 同名去重(最短天数) → 折扣降序排序 → 日期连续 → 最多6个 |
| ② | 打开 Drawer | 点击"Excel批量报名活动" |
| ③ | 勾选专题活动 | Beast UI checkbox + 关确认弹窗 |
| ④ | 主题勾选 | 完整名称匹配（splice防重复勾选） |
| ⑤ | 站点选择 | 17欧洲站 |
| ⑥ | 商品全选 | 100条/页，逐页全选（MDL_innerWrapper + 表头 checkbox） |
| ⑦ | 生成模板 | 事件驱动 + 文件稳定判定 |
| ⑧ | 核价过滤 | 低于下限删除，高于上限降价 |
| ⑨ | 上传导入报名 | file_chooser → 开始导入 → 确认报名 |

---

## 五、关键修复记录

### v4.1.1 — 商品全选 790/1190 条
| 问题 | 修复 |
|------|------|
| 弹窗容器 selector 不匹配 | `[data-testid="beast-core-modal"]` → `[class*="MDL_innerWrapper"]` |
| 每页条数下拉点不中 | `[data-testid="beast-core-select-header"]` → `[class*="ST_selectValue"]` |
| 下一页禁用检测硬编码 | `PGT_disabled_5-120-1` → `[class*="PGT_next"]:not([class*="PGT_disabled"])` |
| 翻页后页码偏移 | 改 100 条/页后强制回到第 1 页 |

### v4.1.3 — 世界杯入选修复
| 问题 | 修复 |
|------|------|
| 天数多算1天（20→21） | `days_between` 去掉 `+1` |
| 独立日夏季大促占名额 | `EXCLUDE_KEYWORDS` 加 `"独立日"` |
| 同日期没按折扣排序 | `sort` 改为 `(start_date, -discount)` |

### v4.1.2 — 活动筛选修复
| 问题 | 修复 |
|------|------|
| 折扣门槛 5→6折 | `MIN_DISCOUNT = 6.0` |
| 全年度日期格式不支持 | `date_parser.py` 加 `YYYY-MM-DD～YYYY-MM-DD` 匹配 |
| 同名活动出现两次（14天+31天） | `extract.py` 同名去重，保留最短天数 |
| 主题弹窗同名活动重复勾选 | `drawer_ops.py` splice 匹配后从列表移除 |
| 弹窗日期全角括号不匹配 | regex `\((\\d+)天\)` → `[（(](\\d+)天[）)]` |

详细见 `CHANGELOG.md`。

| 站点 | 核价下限 | 报名价上限 |
|------|:-------:|:---------:|
| 波兰站 | 55 | 65 |
| 匈牙利站 | 61 | 71 |
| 立陶宛站 | 61 | 71 |
| 斯洛伐克站 | 65 | 75 |
| 奥地利站 | 65 | 75 |
| 德国站 | 73 | 83 |
| 捷克站 | 74 | 84 |
| 荷兰站 | 77 | 87 |
| 西班牙站 | 89 | 99 |
| 比利时站 | 90 | 100 |
| 法国站 | 90 | 100 |
| 丹麦站 | 95 | 105 |
| 斯洛文尼亚站 | 95 | 105 |
| 葡萄牙站 | 98 | 108 |
| 罗马尼亚站 | 108 | 118 |
| 瑞典站 | 147 | 157 |
| 芬兰站 | 176 | 186 |

⚠️ **改价只需改 `config/prices.py`，仅此一处。**

---

## 六、故障排查

| 现象 | 解决 |
|------|------|
| CDP 连不上 | `taskkill /F /IM msedge.exe` 后重跑 |
| 商品翻页崩 | 已修复 null 保护，如有异常检查页面结构 |
| 模板下载失败 | 浏览器保持存活，检查网络 |
| 核价失败 | 检查 `config/prices.py` 价格是否正确 |
| 日志乱码 | 纯文本日志，无 emoji |

---

## 七、回滚

```bash
git tag           # 查看所有版本
git checkout v3.2.0-working   # 回滚到 v3.2.0
```

---

## 八、相关文档

| 文件 | 说明 |
|------|------|
| `ARCHITECTURE.md` | 工程操作系统架构 |
| `CHANGELOG.md` | 版本演进和所有修复记录 |
| `config/prices.py` | 价格表（唯一入口） |
| `报活动_全自动.py` | 旧版入口（兼容） |
