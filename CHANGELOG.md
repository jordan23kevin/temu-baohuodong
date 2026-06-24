# CHANGELOG — Temu 报活动

> 项目：`E:\Claude code\Temu自动化\报活动`

## v4.0.0（2026-06-24）Engineering OS 架构重构

### 核心变更
- **工程操作系统架构**：从"脚本项目"升级为分层 OS 架构
- **状态机系统**：`core/state_machine.py` 全局状态机，state 序列化到 `state/state.json`
- **任务注册表**：`core/task_registry.py`，每次运行生成唯一 task_id
- **配置集中管理**：`config/settings.py` + `config/prices.py` + `config/sites.py`，不再散落
- **流程编排**：`workflow/activity_pipeline.py` 9步编排，支持断点恢复
- **步骤拆分**：9步拆到 `workflow/steps/` 独立文件
- **服务层**：`services/browser_service.py` 浏览器单例 + `services/price_filter.py` 核价独立
- **唯一入口**：`entrypoint/run.py`，clone 即可运行
- **可恢复**：中断后重跑自动跳过已完成步骤
- **可回滚**：v3.2.0-working tag 保留

### 新目录结构
```
报活动/
├── entrypoint/run.py        ← 唯一入口
├── workflow/                ← 流程控制层
│   ├── activity_pipeline.py
│   └── steps/               ← 9步独立文件
├── services/                ← 外部系统隔离层
├── core/                    ← 核心抽象层
├── config/                  ← 配置集中管理
├── utils/                   ← 工具函数
├── state/                   ← 状态持久化
├── requirements.txt
└── ARCHITECTURE.md          ← 架构文档
```

### 向后兼容
- 旧入口 `报活动_全自动.py` 保留，可直接运行
- 旧文件 `download_manager.py` / `hermes_browser.py` 保留
- git tag `v3.2.0-working` 可随时回滚

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `entrypoint/run.py` | **新建** | 唯一启动入口 |
| `ARCHITECTURE.md` | **新建** | 系统架构文档 |
| `requirements.txt` | **新建** | 依赖清单 |
| `.gitignore` | 修改 | 添加 state/state.json |
| `core/state_machine.py` | **新建** | 全局状态机 + 序列化 |
| `core/task_registry.py` | **新建** | 任务注册表 |
| `services/browser_service.py` | **新建** | 浏览器服务层 |
| `services/price_filter.py` | **新建** | 核价服务层 |
| `services/download_manager.py` | 复制 | v2 保持不变 |
| `workflow/activity_pipeline.py` | **新建** | 流程编排 |
| `workflow/steps/extract.py` | **新建** | 步骤①活动提取 |
| `workflow/steps/drawer_ops.py` | **新建** | 步骤②③④⑤ Drawer操作 |
| `workflow/steps/product_select.py` | **新建** | 步骤⑥商品选择 |
| `workflow/steps/download_submit.py` | **新建** | 步骤⑦⑧⑨下载核价上传 |
| `config/settings.py` | **新建** | 全局配置 |
| `config/prices.py` | **新建** | 17站价格表(唯一入口) |
| `config/sites.py` | **新建** | 站点信息 |
| `utils/log.py` | **新建** | GBK-safe 日志 |
| `utils/date_parser.py` | **新建** | 日期解析工具 |
| `state/recovery.py` | **新建** | 断点恢复逻辑 |
| `README.md` | 重写 | v4.0.0 操作手册 |

---

## v3.2.0（2026-06-24）HermesBrowser 状态机 + DownloadManager v2 + 动态筛选

### 核心升级

#### Runtime 层：HermesBrowser v2（状态机）
- **状态机重构**：`HermesBrowserV2`，六态确定性流转（`EDGE_OFF → EDGE_STARTING → CDP_READY → BROWSER_CONNECTED → CONTEXT_READY → PAGE_READY`）
- **CDP 探活替代 sleep**：`_wait_cdp_ready()` 0.5s 循环检测，不固定等 30s
- **更精准的 CDP 检测**：检查 `webSocketDebuggerUrl` 字段而非简单 HTTP 200
- **防重复启动**：`start_edge()` 先查 CDP 是否已就绪，已就绪则跳过
- **修复 bug**：去掉 `_is_edge_running()` 中的 `or True` 假 alive 逻辑
- **简化 API**：`get_page()` 唯一主入口全链路自动推进；`health()` 替代 `health_check()`
- **向后兼容**：`HermesBrowser = HermesBrowserV2` 别名，调用方零改动

#### IO 层：DownloadManager v2（文件稳定判定）
- **`_wait_file_stable()`**：连续3次检测文件大小不变才确认下载完成，替代 v1 的简单存在检查
- **task_id 注册表**：全链路追踪 WAITING → TRIGGERED → DOWNLOADING → DONE/FAILED
- **`get_status()` / `get_active_tasks()`**：实时查询下载状态
- 接口向后兼容，调用方无需改代码

#### Workflow 层：活动筛选逻辑重构
- **去掉硬编码白名单**：不再写死6个活动名，改为条件动态筛选
- **过期自动过滤**：结束日期 < 当天的活动自动跳过
- **日期连续检查**：按开始日期排序，前一个结束日+1 < 下一个开始日则跳过（不允许空挡）
- **最多选6个**：从最早开始的活动依次选取
- **动态日期**：`TODAY = date.today()` 替代硬编码

### Bug 修复
| # | 问题 | 文件 | 行 | 根因 | 修复 |
|:-:|------|:----|:--:|------|------|
| B1 | 商品翻页 `next.click()` 崩 | `报活动_全自动.py` | 326 | 商品只有1页时 `next` 为 null，漏判 `!next` | 加 `if (!next) return 'DONE'` |
| B2 | 日志 `🎉` 表情 GBK 炸 | `报活动_全自动.py` | 411 | 中文 Windows 终端 GBK 编码不支持 emoji | 全替换为纯文本 |
| B3 | 日志 `⏭` / `📋` 表情 GBK 炸 | `报活动_全自动.py` | 159,390 | 同上 | 全替换为纯文本 |
| B4 | HermesBrowser `_is_edge_running()` `or True` | `hermes_browser.py` | 207 | 逻辑 bug，永远返回 True | 已重构为状态机，该行已删除 |

### 本次成功运行（2026-06-24 SEMEMS 店）
```
页面活动: 50个 → 基础筛选: 7个 → 最终选定: 6个（连续无空挡）
商品全选: 12页, 1193件全部选中
模板下载: 3.4MB（DownloadManager v2 文件稳定判定通过）
核价过滤: 84600行 → 1085行（删83515，降550，不动535）
上传导入: 已确认并报名活动 ✅
```

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `hermes_browser.py` | **重写** | v1 → v2 状态机架构 |
| `download_manager.py` | **重写** | v1 → v2 文件稳定判定 + task_id 追踪 |
| `报活动_全自动.py` | 修改 | 活动筛选重构(去白名单+日期连续), 修复B1/B2/B3, 版本头v3.2.0 |
| `活动核价.py` | 修改 | 版本头 v3.1.0 → v3.2.0 |
| `架构.md` | 重写 | 完整 v3.2.0 架构同步 |
| `README.md` | 重写 | 完整 v3.2.0 操作手册 |
| `SKILL.md` | 更新 | v3.2.0 核心流程 + 新坑点 |
| `CHANGELOG.md` | 修改 | 本文 |

---

## v3.1.0（2026-06-20）全流程锁定

### 变更
- **版本统一**：所有脚本和文档版本号对齐为 v3.1.0
- **路径统一**：所有文档路径从 `E:\Hermes\项目\报活动` 修正为 `E:\Claude code\Temu自动化\报活动`
- **全踩坑记录**：架构.md 新增完整 20 个问题的记录表（问题/根因/解决/版本）
- **100% 复现条件**：架构.md 新增完整前置条件、运行命令、故障排查章节
- **CHANGELOG 新建**：版本演进记录
- **README 新建**：100%复现操作手册
- **安全规则更新**：去掉步骤⑨"等爸爸确认"暂停（直接自动提交）
- **废弃标记**：`报活动.py` 和 `报活动_v2.py` 顶部加 DEPRECATED 标记

### 文件变更清单
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `报活动_全自动.py` | 修改 | v3.0.0→v3.1.0，去掉安全暂停日志 |
| `架构.md` | 重写 | 统一路径、补v3.0.1、20个踩坑表、复现条件 |
| `SKILL.md` | 更新 | 版本路径统一 |
| `站点信息.md` | 重写 | 17站价格同步最新值 |
| `hermes_browser.py` | 修改 | 头部版本与项目对齐 |
| `download_manager.py` | 修改 | 头部版本与项目对齐 |
| `活动核价.py` | 修改 | 添加版本头 |
| `报活动.py` | 修改 | 加 DEPRECATED 标记 |
| `报活动_v2.py` | 修改 | 加 DEPRECATED 标记 |
| `CHANGELOG.md` | **新建** | 版本演进记录 |
| `README.md` | **新建** | 100%复现操作手册 |

---

## v3.0.1（2026-06-13）

### 变更
- **折扣门槛**：≥6.0折 → **≥5.0折**，扩大活动覆盖
- **活动白名单**：限 **6 个指定活动**（原来动态筛选不限量）
  - 限时6折专区（6月）
  - 周末48H大折扣专区（06/20-06/21）
  - 72小时计划】夏促爆单专属链接（6.20-6.22）
  - 72小时计划】夏促爆单专属链接（6.23-6.25）
  - 周末48H大折扣专区（06/27-06/28）
  - 72小时计划】夏促爆单专属链接（6.29-7.1）
- **GBK 编码修复**：`subprocess` 调用核价脚本强制 `encoding="utf-8"` + `PYTHONIOENCODING=utf-8`

### 修复的问题
| # | 问题 | 根因 | 解决 |
|:-:|------|------|------|
| 19 | GBK 编码乱码 | subprocess 输出含中文时解码失败 | 强制 UTF-8 |
| 20 | 活动选不上 | 6折门槛太严 | 下调为 5 折 |

---

## v3.0.0（2026-06-13）三层架构升级

### 核心升级
- **三层架构**：Workflow（报活动_全自动.py）→ Runtime（hermes_browser.py）→ IO（download_manager.py）
- **浏览器常驻化**：`DETACHED_PROCESS` 独立进程，Edge 脱离 Python 生命周期
- **自动保活**：`HermesBrowser.ensure_alive()` 全链路保活
- **事件驱动下载**：`DownloadManager` 双策略（事件驱动 180s + 文件轮询 240s）
- **DOM 级提取**：`table.TB_tableWrapper` 替代 `document.body.innerText`
- **零 close**：删除所有 `context.close()`，永不主动关浏览器

### 修复的问题
| # | 问题 | 根因 | 解决 |
|:-:|------|------|------|
| 7 | body.innerText 提取慢 | 全量文本扫描 | DOM 级提取，只返回几十字节 |
| 11 | 下载超时 | expect_download 默认60秒 | 改为180秒 + 轮询240秒 |
| 12 | 浏览器自己关闭 | with sync_playwright 退出杀子进程 | CDP 连接 + 常驻进程 |
| 16 | JS 正则 `\d` 不匹配 | Python 字符串转义 | \\\\d→\\d |
| 17 | JS split('\\n') 断裂 | Python 三重引号转义 | \\\\n→\\n |
| 18 | input() 阻塞 | 非交互模式抛 EOFError | 全自动运行 |

### 文件变更
| 文件 | 说明 |
|------|------|
| `报活动_全自动.py` | 重写为三层架构 |
| `hermes_browser.py` | **新建** — Edge 常驻服务管理器 |
| `download_manager.py` | **新建** — 事件驱动下载管理器 |

---

## v2.0（2026-06-12）新版 Drawer 流程

- 适配 Temu 全面改版后的 Drawer 流程
- 完整9步端到端验证通过 ✅
- 发现并解决 React 翻页更新陷阱
- 文件上传方案锁定为 Playwright 原生模式 `file_chooser.set_files()`
- 主题匹配锁定为完整名称 + `split('\n')[0]`

### 修复的问题
| # | 问题 | 根因 |
|:-:|------|------|
| 1 | 旧脚本全部失效 | 页面全面改版 |
| 2 | 主题勾选数量不对 | 前15字符匹配混淆 |
| 3 | 主题只勾了1个 | innerText 含 \n 标签 |
| 4 | 商品全选翻页太快丢数据 | React 合并 click |
| 5 | Drawer 确认弹窗拦截 | 勾选后有关确认弹窗 |
| 8 | 文件上传所有方法失效 | CDP 安全限制 |
| 9 | 上传后不显示文件名 | React 未即时刷新 |
| 10 | 模板文件误用旧版本 | 没验证时间戳 |
| 13 | Drawer 重开失败 | 要求一次会话完成 |
| 14 | 浏览器风控 | 新会话触发风控 |

### 文件变更
| 文件 | 说明 |
|------|------|
| `报活动_v2.py` | **新建** — v2 脚本 |
| `报活动_全自动.py` | **新建** — 全自动一镜到底脚本（首版） |

---

## v1.0（~2026-06-09）旧版 UI

- 基于旧版 Temu 营销页表格 UI
- 1614 行单片脚本
- 2026-06-11 Temu 改版后全部失效
