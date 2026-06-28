# Temu 报活动 — 系统架构文档

> 版本：v4.1.2 (Engineering OS)
> 最后更新：2026-06-29

---

## 一、工程操作系统架构

```
┌─────────────────────────────────────────────────┐
│                 entrypoint/run.py                │  ← 唯一入口
├─────────────────────────────────────────────────┤
│                  workflow/                        │  ← 流程控制层
│   activity_pipeline.py (9步编排 + 断点恢复)       │
│   ┌───────────────────────────────────────────┐  │
│   │ steps/                                    │  │
│   │  extract.py       (① 活动提取筛选)         │  │
│   │  drawer_ops.py    (②③④⑤ Drawer操作)      │  │
│   │  product_select.py(⑥ 商品选择)            │  │
│   │  download_submit.py(⑦⑧⑨ 下载核价上传)    │  │
│   └───────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│                  services/                        │  ← 外部系统隔离层
│   browser_service.py   (浏览器管理)               │
│   download_manager.py  (下载管理 v2)              │
│   price_filter.py      (核价过滤)                 │
├─────────────────────────────────────────────────┤
│                   core/                           │  ← 核心抽象层
│   state_machine.py  (全局状态机 + 序列化)         │
│   task_registry.py  (任务注册 + task_id)          │
├─────────────────────────────────────────────────┤
│                  config/                          │  ← 配置集中管理
│   settings.py  (全局配置)                         │
│   prices.py    (17站价格表)                       │
│   sites.py     (站点信息)                         │
├─────────────────────────────────────────────────┤
│                  utils/                           │  ← 工具函数
│   log.py          (GBK-safe 日志)                 │
│   date_parser.py  (日期解析)                      │
├─────────────────────────────────────────────────┤
│                  state/                           │  ← 状态持久化
│   recovery.py  (断点恢复逻辑)                     │
│   state.json   (运行时状态, gitignored)           │
└─────────────────────────────────────────────────┘
```

---

## 二、状态机设计

### 全局状态流
```
INIT → RUNNING → [STEP1..STEP9] → DONE / FAILED
```

### 9个步骤
| # | 步骤名 | 说明 |
|:-:|--------|------|
| 1 | EXTRACT_ACTIVITIES | 活动提取 + 条件筛选 + 日期连续 |
| 2 | OPEN_DRAWER | 打开批量报名 Drawer |
| 3 | SELECT_ACTIVITY_TYPE | 勾选专题活动类型 |
| 4 | SELECT_THEMES | 主题弹窗匹配勾选 |
| 5 | SELECT_SITES | 17站勾选 |
| 6 | SELECT_PRODUCTS | 逐页全选商品 |
| 7 | GENERATE_TEMPLATE | 生成并下载模板 |
| 8 | PRICE_FILTER | 核价过滤 |
| 9 | UPLOAD_IMPORT | 上传导入报名 |

---

## 三、可复现系统

### 从空目录重建
```bash
# 1. clone
git clone <repo> Temu报活动
cd Temu报活动

# 2. 安装依赖
pip install -r requirements.txt
playwright install msedge

# 3. 运行
python entrypoint/run.py
```

### 断点恢复
- 每次运行自动写入 `state/state.json`
- 中断后重新运行自动跳过已完成步骤
- 使用 `state/recovery.py` 查询恢复状态

### 回滚
- git tag `v3.2.0-working` 保留之前可工作的版本
- `git checkout v3.2.0-working` 即可回滚

---

## 四、依赖关系

```
entrypoint/run.py
    └── workflow/activity_pipeline.py
            ├── workflow/steps/extract.py → utils/, config/
            ├── workflow/steps/drawer_ops.py → utils/, config/
            ├── workflow/steps/product_select.py → utils/
            ├── workflow/steps/download_submit.py → services/
            ├── core/state_machine.py
            └── core/task_registry.py
services/ → config/, hermes_browser.py
utils/ → (无内部依赖)
config/ → (无内部依赖)
```
