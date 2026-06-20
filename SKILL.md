# Temu 报活动 — 快速操作手册 v3.1.0

> 项目：`E:\Claude code\Temu自动化\报活动`
> 架构：`架构.md`
> 版本演进：`CHANGELOG.md`

## 触发词
报活动、活动核价、批量报名、temu营销

## 前置条件
- Python 3.11+ with `playwright`, `pandas`, `openpyxl`
- Edge profile 已有 Temu 登录态

## 快速命令

```bash
cd "E:/Claude code/Temu自动化/报活动" && python3 报活动_全自动.py
```

Edge 首次启动后即为常驻服务。后续再次运行会自动重连 CDP。

## 核心流程 v3.1.0

① 分析活动列表（DOM级提取，毫秒级）→ ② 打开 Drawer → ③ 勾选专题活动
→ ④ 主题弹窗勾选（白名单6个）→ ⑤ 选17站 → ⑥ 选商品（逐页全选）
→ ⑦ 生成模板（DownloadManager 事件驱动，不 sleep）→ ⑧ 核价过滤
→ ⑨ 上传过滤文件 → 开始导入 → 确认并报名活动

## 三层架构

```
报活动_全自动.py      ← Workflow层（v3.1.0）
hermes_browser.py    ← Runtime层（Edge常驻服务）
download_manager.py  ← IO层（文件管理）
```

## 安全规则
1. 提交无法撤回，用错价格会导致亏损
2. 一次 Drawer 从头到尾，不可中途关闭重开
3. 浏览器常驻，永不关闭（永不主动关 Edge）

## 关键坑点
1. **主题匹配**：两边都用 `split('\n')[0]` 去尾部标签
2. **JS反斜杠**：Python `"""...` 中 `\\d` → JS `\d`（数字），`\\n` → JS `\n`（换行）
3. **生成模板**：DownloadManager 事件驱动180s + 文件轮询兜底240s
4. **商品全选**：必须逐页 sleep(1)，React 合并快速 click
5. **浏览器关闭**：不要用 `launch_persistent_context`（子进程），用 `DETACHED_PROCESS` + CDP
6. **文件上传**：仅 Playwright 原生 mode file_chooser 有效，等2-3秒 React 更新
