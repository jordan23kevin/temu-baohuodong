# Temu 报活动 — 快速操作手册 v3.0

> 项目: `E:\Hermes\项目\报活动`
> 架构: `架构.md`

## 触发词
报活动、活动核价、批量报名、temu营销

## 前置条件
- Python 3.11+ with `playwright`, `pandas`, `openpyxl`
- Edge profile 已有 Temu 登录态

## 快速命令

```bash
cd /e/Hermes/项目/报活动 && python3 报活动_全自动.py
```

Edge 首次启动后即为常驻服务。后续再次运行会自动重连 CDP。

## 核心流程 v3.0

① 分析活动列表（DOM级提取，毫秒级）→ ② 打开 Drawer → ③ 勾选专题活动
→ ④ 主题弹窗勾选（动态分析结果）→ ⑤ 选17站 → ⑥ 选商品（逐页全选）
→ ⑦ 生成模板（DownloadManager 事件驱动，不 sleep）→ ⑧ 核价过滤
→ ⑨ 等爸爸确认 → 上传导入报名

## 三层架构

```
报活动_全自动.py      ← Workflow层
hermes_browser.py    ← Runtime层（Edge常驻服务）
download_manager.py  ← IO层（文件管理）
```

## 安全规则
1. 跑脚本前必须问爸爸「可以开始吗？」
2. 步骤⑨核价完成后在聊天中等爸爸说「继续」
3. 浏览器常驻，永不关闭（`context.close()` 已全删）
4. 下载失败返回 None，不抛异常，不关浏览器

## 关键坑点
1. **主题匹配**：两边都用 `split('\n')[0]` 去尾部标签
2. **JS反斜杠**：Python `"""...` 中 `\\d` → JS `\d`（数字），`\\n` → JS `\n`（换行）
3. **生成模板**：DownloadManager 事件驱动180s + 文件轮询兜底240s
4. **商品全选**：必须逐页 sleep(1)，React 合并快速 click
5. **浏览器关闭**：不要用 `launch_persistent_context`（子进程），用 `DETACHED_PROCESS` + CDP
