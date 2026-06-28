# Temu 报活动 — 快速操作手册 v3.2.0

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
cd "E:/Claude code/Temu自动化/报活动" && python entrypoint/run.py
```

Edge 首次启动后即为常驻服务。后续再次运行自动重连 CDP（状态机自动推进）。

## 核心流程 v4.1.2

① 分析活动列表（DOM级提取）→ 条件筛选(≥6折/≤20天/非爆款秒杀/不过期/同名去重/日期连续/最多6个)
→ ② 打开 Drawer → ③ 勾选专题活动
→ ④ 主题弹窗勾选（名称匹配）→ ⑤ 选17站 → ⑥ 选商品（逐页全选，null保护）
→ ⑦ 生成模板（DownloadManager v2 事件驱动 + 文件稳定判定）
→ ⑧ 核价过滤 → ⑨ 上传过滤文件 → 开始导入 → 确认并报名活动

## 三层架构

```
报活动_全自动.py      ← Workflow层（v3.2.0）
hermes_browser.py    ← Runtime层（Edge 状态机 v2）
download_manager.py  ← IO层（下载管理器 v2）
```

## 安全规则
1. 提交无法撤回，用错价格会导致亏损
2. 一次 Drawer 从头到尾，不可中途关闭重开
3. 浏览器常驻，永不关闭（永不主动关 Edge）

## 关键坑点
1. **主题匹配**：两边都用 `split('\n')[0]` 去尾部标签
2. **JS反斜杠**：Python `"""...` 中 `\\d` → JS `\d`（数字），`\\n` → JS `\n`（换行）
3. **生成模板**：DownloadManager v2 事件驱动180s + 轮询240s + 文件稳定判定(连续3次size不变)
4. **商品全选**：必须逐页 sleep(1)，React 合并快速 click；已加 `!next` null 保护
5. **浏览器关闭**：不要用 `launch_persistent_context`（子进程），用 `DETACHED_PROCESS` + CDP
6. **文件上传**：仅 Playwright 原生 mode file_chooser 有效，等2-3秒 React 更新
7. **终端编码**：所有 log 已替换 emoji 为纯文本，防 GBK 炸
8. **商品全选选择器（v4.1.1 fix）**：
   - 弹窗容器用 `[class*="MDL_innerWrapper"]` 而非 `[data-testid="beast-core-modal"]`
   - 每页条数用 `[class*="ST_selectValue"]` 点值文本
   - 翻页检测用 `[class*="PGT_next"]:not([class*="PGT_disabled"])` 而非硬编码 class
   - 改 100 条/页后必须回到第 1 页
   - 从分页器读取真实总页数，不写死
9. **活动筛选（v4.1.2）**：
   - `MIN_DISCOUNT` 在 `config/settings.py`，当前 6.0 折
   - 日期解析已支持 `YYYY-MM-DD～YYYY-MM-DD` 完整格式
   - 同名活动（14天NEW + 31天旧版）自动去重保留最短天数
   - 主题弹窗每名称只勾一次（splice 移除已勾选的）
   - 弹窗日期全角括号 `（N天）` 已兼容
10. **回滚命令**：
   - `git tag` 查看版本
   - `git checkout v4.1.2` 回滚到此版本（当前稳定版）
