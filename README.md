# Temu 报活动 — 100% 复现操作手册

> 版本：v4.0.0 (Engineering OS) · 最后更新：2026-06-24
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
| ① | 活动提取筛选 | DOM级提取 → 条件筛选 → 过期过滤 → 日期连续 → 最多6个 |
| ② | 打开 Drawer | 点击"Excel批量报名活动" |
| ③ | 勾选专题活动 | Beast UI checkbox + 关确认弹窗 |
| ④ | 主题勾选 | 完整名称匹配 |
| ⑤ | 站点选择 | 17欧洲站 |
| ⑥ | 商品全选 | 100条/页，逐页全选（null保护） |
| ⑦ | 生成模板 | 事件驱动 + 文件稳定判定 |
| ⑧ | 核价过滤 | 低于下限删除，高于上限降价 |
| ⑨ | 上传导入报名 | file_chooser → 开始导入 → 确认报名 |

---

## 五、核价价格表

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
