# CHANGELOG — Temu 报活动

> 项目：`E:\Claude code\Temu自动化\报活动`

## v4.5.3（2026-08-22）新增商品信息同步脚本 sync_products.py（报活动前置）

- 新增 `sync_products.py`：报活动前抓取最新商品信息（后台接口方式，不模拟页面勾选）。
- 用法：`python sync_products.py --pages 5`（默认 5 页；支持 `1-3` 区间格式）。
- 流程：连接现有 Edge（CDP 9222 复用登录态）→ `searchForSemiSupplier` 循环抓 N 页（每页 50 商品）基础信息（SPU/SKC/SKU/颜色/尺码/货号）→ `queryProductSkuPriceAndStatus` 逐 SKU 抓完整 17 站价格（页面内 Promise.all 并发 30）→ 生成 Excel + JSON 存 `state/product_sync/`（10 列：SPU ID/SKC ID/SKC货号/SKU ID/SKU货号/颜色属性/尺码属性/站点/活动申报价格/币种）。
- 纯读操作，不动页面状态；通过页面 SDK fetch（anti-content 签名）+ mallid 头（cookie 提取）。
- 实测：1 页 = 50 商品 / 444 颜色 / 2650 SKU / 45050 行，约 57s。
- 结果落盘 `state/product_sync/latest_sync_result.json` 供 Bridge 轮询展示。

## v4.5.2（2026-08-12）离线表命名时间改SPU去重数量

- `services/baseline_store.py`：文件名 `{活动名}_{yyyyMMdd_HHmmss}.xlsx` →
  `{活动名}_{yyyyMMdd}_{SPU去重数量}.xlsx`（如 `半托管活动85折专区_20260812_3255.xlsx`）
- 注意：同日重报同一活动文件名相同，导入记录校验可能匹配到当天较早的同名记录

## v4.5.1（2026-08-12）离线表命名改版 — 活动名+报名日期时间

- `services/baseline_store.py`：`build_activity_table(theme_value, activity_name)`，
  文件名 `报名商品信息_{ts}_已过滤.xlsx` → `{活动名}_{yyyyMMdd_HHmmss}.xlsx`
  （清洗 Windows 非法字符；带时间防同日重报同名导致导入记录校验匹配旧记录）
- `workflow/activity_pipeline.py`：造表时传入面板勾选的活动名（官方大促传活动类型）

## v4.5.0（2026-08-12）准备阶段重构 — 一次性合并基准表+造N张表，循环只剩上传

### 需求
准备工作和报名分离：准备阶段一次性完成「刷新基准表 + 取全部主题值 + 造N张表」，
逐活动循环只剩「开抽屉 + 上传」，不再每活动生成模板。

### 新流程
- 准备1：勾第1个主题 + 最新 REFRESH_PAGES 页(1000条)商品 → 生成模板 → 合并进基准表
  （重叠校验：日志报告 模板键数/重叠数/新增数；零重叠时警告「实际新增或超1000条，
  建议增大 REFRESH_PAGES」——有重叠才说明没漏；基准表保持固定文件名，写回前自动带日期备份）
- 准备2：勾全部 N 个主题 + 1 页(100条)商品 → 生成模板 → 取 N 个「活动类型(活动主题）」值
  （distinct 数量==N 且每个勾选主题唯一匹配，不满足即报错）→ 离线造 N 张表
- 循环：每活动 开抽屉 → 上传该活动的表 → 开始导入 → 导入成功 → 确认 → 导入记录校验

### 修改
- `services/baseline_store.py`：`extract_theme_value` → `extract_theme_values`（取全部
  distinct 主题值）；`merge_template` 新增重叠校验日志 + 零重叠警告
- `workflow/activity_pipeline.py`：重构为 `_prepare`（准备1+准备2 共14步）+
  纯上传循环（OPEN_DRAWER#i + UPLOAD_IMPORT#i）；`built_tables` 字典按主题存表
- `core/state_machine.py`：STEPS/标签更新为准备阶段步骤名（旧名保留兼容）
- Bridge `activity.html`：进度估算 3+8N → 16+2N

## v4.4.2（2026-08-12）开始导入/确认报名改真实鼠标点击 — JS click 触发不了框架事件

### 问题
v4.4.1 修复抽屉定位后「开始导入」仍未点中：JS `el.click()` 只派发 click 事件，
Temu 前端框架的按钮处理器监听的是完整鼠标事件序列（mousedown/mouseup），合成点击不触发。

### 修复（`workflow/steps/download_submit.py`）
- 「开始导入」：`evaluate_handle` 取到按钮元素后改用 Playwright `element.click()`——
  真实鼠标点击（自动滚动到元素 + mousedown/mouseup），保留 60s 等按钮可用的轮询
- 「确认并报名活动」同样改真实鼠标点击

## v4.4.1（2026-08-12）开始导入点击失效修复 — 定位可见抽屉 + 等按钮可用

### 问题
上传表格成功后「开始导入」没点上。真因：DOM 里一个抽屉拆成多个节点（外层/遮罩/内容），
且上一个活动的旧抽屉残留未销毁；`querySelector('[class*="Drawer"]')` 取第一个可能命中
旧抽屉或遮罩节点，按钮点击无效。文件状态检查用「已过滤」文本匹配，旧抽屉里上个活动的
已过滤文件也会误判为 FILE_FOUND。

### 修复（`workflow/steps/download_submit.py`，连 CDP 9222 抓真实 DOM 验证）
- 新增 `_JS_PICK_DRAWER`：统一抽屉定位——优先 `Drawer_visible` 类 + 含本次文件名，
  兜底取含「批量报名活动」文本的可见抽屉；上传/文件检查/开始导入/导入记录校验四处全部改用
- 文件状态检查从匹配「已过滤」改为匹配本次完整文件名，未出现即抛错
- 「开始导入」点击前等按钮可用（disabled/aria-disabled/BTN_disabled 检测），60s 轮询

## v4.4.0（2026-08-12）基准表离线造表 — 不再全量勾选商品，每活动只传离线造的表

### 需求
商品全量勾选+全量模板下载太重。改为：以 `E:\Kimi Code\temu分析\活动报名基准表.xlsx`
（模板格式，约3320个商品）为商品主数据，每次运行只下载最新 1000 条合并进去；
每个活动只勾 1 页商品生成模板取「活动类型(活动主题）」值，然后用基准表离线造该活动的
完整报名表（申报价=站点核价底价 price_min，库存=基准表 SPU 库存），抽屉里直接上传该表。

### 修改
- `config/settings.py`：新增 `BASELINE_TABLE`（env `TEMU_BASELINE_TABLE` 可覆盖）、
  `REFRESH_PAGES=10`、`BUILD_DIR`
- `services/baseline_store.py`（新增）：`load_baseline`（mtime 缓存）、
  `merge_template`（以 SKU ID+站点 / SPU ID 为键只增不改，写回前备份 .bak）、
  `extract_theme_value`、`build_activity_table`（活动类型列覆盖、申报价=PRICE_MIN）
- `workflow/steps/product_select.py`：`select_products(page, max_pages=None)`，
  限页时跳过 已选vs总数 完整性校验
- `workflow/activity_pipeline.py`：每活动步骤 `PRICE_FILTER` → `BUILD_TABLE`；
  首个活动（i==1）`SELECT_PRODUCTS` 勾 REFRESH_PAGES 页并执行 `REFRESH_BASELINE` 合并基准表，
  其余活动只勾 1 页；`filtered_path` → `built_path`
- `core/state_machine.py`：STEPS 新增 `REFRESH_BASELINE`/`BUILD_TABLE`（PRICE_FILTER 保留兼容）
- Bridge `activity.html`：进度估算 2+8N → 3+8N（首个活动多 1 步合并基准表）
- 砍掉的环节：全量商品逐页全选、核价过滤（造表时已按底价填好）

## v4.3.2（2026-08-12）上传提交防静默跳过 — 开始导入/确认报名逐步校验，失败即抛错

### 问题
逐活动循环报名时，上传完表格后没点「开始导入」和「确认并报名活动」就进入下一个活动，
活动实际没报上但步骤被标记完成。根因：`upload_and_submit` 全部是「发了就不管」的 JS 点击——
按钮不存在时 `if (btn.length)` 静默跳过；确认弹窗固定 sleep(3) 不等异步导入校验；
且 `_step_upload` 忽略返回值，上传失败也照常标记完成。

### 修复
- `workflow/steps/download_submit.py` `upload_and_submit`（已对照真实页面 DOM 验证）：
  - 上传失败从 `return False` 改为 `raise RuntimeError`
  - 「开始导入」按钮未找到（NO_DRAWER/NOT_FOUND）→ 抛错
  - 点击后按钮进入长时间加载态：轮询等待弹窗显示「导入成功」（最长 180s），
    弹窗含「失败」字样立即抛错并带弹窗文本
  - 等「确认并报名活动」按钮可点（非禁用）再点击，30s 内找不到抛错
  - 弹窗关闭后做最终校验：抽屉「导入记录」必须出现该上传文件名
    （状态 处理中/已完成 = 报名成功），30s 内未出现抛错
- `workflow/activity_pipeline.py` `_step_upload`：检查返回值，False 即抛错
- 效果：任一环节失败 → 该活动记入 `meta.failed_themes` 并重置页面，不再带着"假成功"进入下一个活动

## v4.3.1（2026-08-12）候选活动排序改版 — 按折扣降序，9折排最上面

### 需求
候选活动列表原来按开始日期排序（同日期按折扣降序），改为按折扣从高到低排序（9折在最上面），同折扣按开始日期升序。

### 修改
- `workflow/steps/extract.py`：`extract_candidates` 排序键 `(start, -discount)` → `(-discount, start)`

## v4.3.0（2026-08-11）逐活动报名 — 勾选 N 个 = 循环 N 次，每次单独报 1 个

### 需求
v4.2.0 是「勾选多个主题 → 一次提交全部」；改为「勾选 N 个活动 → 逐个单独报名」：
每个活动独立走完整流程（开抽屉→选类型→选主题(仅1个)→选站点→选品→生成模板→核价→上传提交）。

### 修改
- `workflow/activity_pipeline.py`：勾选后按主题循环，步骤名带 `#序号` 后缀（如 `SELECT_PRODUCTS#2`，
  completed_steps 逐活动断点跳过）；单个活动失败**不中断**，记入 `meta.failed_themes` 继续下一个，
  结尾汇总成功/失败；每个活动前（i>1）先 `navigate()` 重置页面，失败后也重置，避免页面残留；
  `meta.total_themes` 供面板计算进度条总步数（2 + 8×N）
- `workflow/steps/drawer_ops.py` `select_themes`：新增勾选状态检测——目标已勾则保持不再点击
  （防反勾掉），非目标已勾则取消（防上次残留混入本次报名）；返回增加 already/cleared 统计
- `activity.html`：进度条总步数按 `meta.total_themes` 动态计算（2 + 8×N）
- 官方大促（无主题）模式不变：单次流程，失败即终止

## v4.2.0（2026-08-11）手动勾选活动 — 列出 6~9 折候选，面板勾选几个报几个

### 需求
不再自动选定活动（旧逻辑：≥8.5折 + 日期连续 + 最多6个自动报名）。
改为：列出 6~9 折的全部候选活动 → Bridge 面板手动勾选 → 点「继续」→ 勾选几个就报几个。
其他筛选条件不变（排除关键词、天数 ≤32、已过期/长期有效不列出）。

### 修改
- `config/settings.py`：`MIN_DISCOUNT`（≥8.5）→ `LIST_MIN_DISCOUNT`/`LIST_MAX_DISCOUNT`（默认 6.0~9.0，env 可覆盖）；
  删除 `MAX_ACTIVITIES`；新增 `USER_SELECT_TIMEOUT = 3600`（等待勾选超时 1 小时）
- `workflow/steps/extract.py`：`extract_and_filter` → `extract_candidates`，只提取+基础筛选+去重+排序，
  返回 JSON 可序列化候选列表（含日期/天数/折扣），不再做连续性筛选与自动选定
- `workflow/steps/user_select.py`（新增）：轮询等待 `state/user_selection.json`（Bridge 面板写入），
  校验勾选必须在候选内，消费后删除文件；超时抛错
- `core/state_machine.py`：新增步骤 `WAIT_USER_SELECT`（位于 EXTRACT_ACTIVITIES 之后）
- `workflow/activity_pipeline.py`：`_step_extract` 把候选写入 `state.meta["candidates"]`；
  新增 `_step_wait_select`；任务启动时清除残留勾选文件
- Bridge（ZCodeProject）：`/api/activity/status` 新增 `waiting_select` + `candidates`；
  新增 `POST /api/activity/select`（校验引擎在等待中 + 勾选在候选内，原子写入 user_selection.json）；
  启动任务时清除残留勾选文件
- `activity.html`：新增活动勾选面板（复选框列表 + 全选/全不选 + ▶继续），
  等待勾选时状态徽章显示「等待勾选活动」；步骤总数 9 → 10

## v4.1.8（2026-08-10）OOM 缓解 — V8 堆上限提到 4GB + 单页崩溃只刷新不重启

### 问题
Edge 标签页报「错误代码： Out of Memory」。排查确认物理内存充足（32GB/空闲16GB），
真因是 Temu 页面 JS 堆随运行时间增长，撞 V8 默认 ~2GB 上限，渲染进程崩溃。

### 修复
- `hermes_browser.py`：Edge 启动参数加 `--js-flags=--max-old-space-size=4096`
  （4GB 为 V8 指针压缩模式上限，需重启 Edge 生效；手动/bat 启动也要带此参数）
- `services/browser_service.py`：`ensure_alive` 分级恢复——先按单标签页崩溃处理
  （`page.reload` 刷新），仍不通才走 `restart_edge()` 重启整个浏览器
- 另建议：Windows 页面文件（当前仅 4.6GB）改为「系统管理的大小」（系统设置，需用户自行修改）

## v4.1.7（2026-08-10）浏览器看门狗 — 假死自动重启 + 下载失败正确报错

### 问题
Edge 主进程假死（CDP WebSocket 连上后无任何响应）时，「生成模板」点击从未到达页面，
下载事件+轮询双超时后 `generate_template` 静默 `return None`，`GENERATE_TEMPLATE` 被误标完成，
任务崩在下一步 `PRICE_FILTER`（`expected str, bytes or os.PathLike object, not NoneType`），
日志完全看不出真因是浏览器死了。

### 修复
- `hermes_browser.py`：新增 `is_alive()`（`wait_for_function` 探活，假死时 8s 超时返回 False；
  不能用子线程 probe——Playwright sync API 非线程安全）和 `restart_edge()`
  （taskkill Edge → 以 user-data-dir 重开保留登录态 → 重连 CDP，返回新 page；
  不走 `stop()`，旧连接已死时 `browser.close()` 会卡死）
- `services/browser_service.py`：新增 `ensure_alive()`——探活失败自动重启 Edge 并重新导航
- `workflow/activity_pipeline.py`：`_execute` 每步执行前先 `ensure_alive()`，自动换新 page/context
- `workflow/steps/download_submit.py`：模板下载失败 / 核价过滤失败改为 `raise RuntimeError`，
  任务停在正确的步骤，不再带着 None 崩到下一步

## v4.1.6（2026-07-18）商品选择提速 — 按真实DOM修正状态读取选择器

### 问题
v4.1.4 上线后每页都等满 15 秒超时（18页≈4.5分钟）：`_JS_STATE` 的行选择器
`.beast-core-table tbody tr` 匹配不到元素——商品弹窗的列表不是 `<table>`，
是 div 虚拟列表；且「已选」「共N条」正则在旧文本格式上失效，已选数一直 -1。

### 修复（`workflow/steps/product_select.py`，连 CDP 9222 抓真实 DOM 验证）
- 行容器改用 `[class*="MTX_matrixRowItem"]`（div 虚拟列表，只渲染可见行，保留 table 选择器做兜底）
- 已选正则 `已选(...)` → `已选择?\s*\(\s*(\d+)\s*\)`（实际文本「已选择(1800)」）
- 总数正则 `共\s*(\d+)\s*条` → `共有?\s*(\d+)\s*条`（实际文本「共有 1820 条」）
- 实测验证：curPg/selected/total/rowCount/firstRow 全部一次读对，翻页等待从 15s 超时变为秒级返回

## v4.1.5（2026-07-18）核价改版 — 不删行保SKU完整 + 上限下调5% + 排除无资质活动

### 问题（三轮「报名活动失败原因」统计，约5800条失败）
- 资质类 ~2989 条：`直营品牌专属活动`、`重点品牌扶持专区` 均要求品牌资质为直营/授权，本店无资质必败；后者名字不含"直营"，关键词挡不住
- 价格类 ~2595 条：`申报价高于参考申报价格`，静态上限对大量 SPU 仍高于 Temu 动态参考价
- SKU完整性 ~195 条：旧核价按行删低价 SKU，把 SPU 的 SKU 删残（57% 的活动×SPU×站点组合整体消失），触发「站点缺失SKU数据」「SKC/SKU不全」整品失败

### 修改
- `config/prices.py`：`PRICE_CAP` 整体下调 5%（原值×0.95）；新增 `FLOOR_RELAX = 0.95`（有效下限=核价下限×0.95，利润底线最多放宽 5%）
- `services/price_filter.py`：不再删行。价格 < 有效下限 → 提价到有效下限；价格 > 上限 → 降为上限。SKU 完整性 100% 保留（真实模板验证：397325 行进出一致，活动×SPU×站点 组合完全一致）
- `活动核价.py`：同步上限与"不删行"逻辑（legacy 入口 `报活动.py`/`报活动_全自动.py` 仍引用）
- `config/settings.py`：`EXCLUDE_KEYWORDS` 新增 `"重点品牌扶持"`
- `价格表.md`：同步新上限与有效下限说明

## v4.1.4（2026-07-18）商品选择防漏选 — 翻页等待+勾选校验+失败即停

### 问题
1782 个商品只选中 1600 个（正好 16 页 × 100 条）：翻页靠固定 `sleep`，第 16→17 页时
"下一页"按钮处于加载禁用态，循环直接 `break`，尾部两页漏选后仍点"确定"继续报名。
证据：两轮模板 Excel 对比，缺失的 175 个 SPU 在上一轮名单里恰好是整段尾部。

### 修复（`workflow/steps/product_select.py`）
- 翻页后等待表格真正刷新（页码对 + 有行 + 首行内容变化），替代固定盲等
- 每页点全选后校验"已选"数量增加，未增加自动重试 3 次
- "下一页"暂时禁用时等待重试 6 次，不再直接 `break`
- 结束前对比 已选数 vs 总条数（共N条），不一致抛错终止，不点确定、不生成模板
- 读总页数时过滤 NaN（省略号页码项）
- `config/settings.py`：`EXCLUDE_KEYWORDS` 新增 `"直营"`（活动名含"直营"字样的均不报）

## v4.1.3（2026-06-29）世界杯入选修复 — 天数计算+折扣排序+排除独立日

### 问题
1. **世界杯7折嘉年华（20天）没被勾选** — `days_between` 多算1天（20→21），超了 MAX_DAYS=20
2. **独立日夏季大促8折/85折占了最早名额** — 06-15 开始但用户不想要
3. **同日期活动没按折扣排序** — 世界杯7折排在6折后面，先用折扣低的占了名额
4. **排除关键词写错** — 写了"夏日"但活动名是"夏季"

### 修复
| # | 文件 | 修复 |
|:-:|------|------|
| 1 | `utils/date_parser.py` | `days_between` 去掉 `+1`，与 Temu UI 天数显示一致 |
| 2 | `config/settings.py` | `EXCLUDE_KEYWORDS` 添加 `"独立日"` |
| 3 | `workflow/steps/extract.py` | 排序改为 `(start_date, -discount)`，同日期先选高折扣 |
| 4 | `config/settings.py` | `"夏日"` → `"独立日"`（更精准定位目标活动） |

### 排序逻辑
```
改前: candidates.sort(key=lambda x: x["start"])
改后: candidates.sort(key=lambda x: (x["start"], -x["discount"]))
```

### 验证
```
8候选 → 6选定（含世界杯7折嘉年华 ✅）
主题勾选: 6/6 ✅
商品全选: 12页 ✅
核价: 98640行 → 17300保留
上传导入: ✅
```

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `config/settings.py` | 修改 | EXCLUDE_KEYWORDS +"独立日" |
| `utils/date_parser.py` | 修改 | days_between 去掉+1 |
| `workflow/steps/extract.py` | 修改 | 排序改为(日期, -折扣) |
| `entrypoint/run.py` | 修改 | 版本头 v4.1.3 |

---

## v4.1.2（2026-06-29）活动筛选修复 — 6折门槛+日期解析+去重+防重复勾选

### 问题
1. **活动折扣门槛从 5 折改为 6 折** — 用户要求只选 ≥6折 活动
2. **全年度日期格式无法解析** — `2026-06-30～2026-07-14（14天）` 格式不匹配原有 regex
3. **同名活动重复选中** — 主页表格同名活动出现两次（14天 NEW + 31天旧版），都被加入勾选
4. **主题弹窗同名活动重复勾选** — 所有匹配行都被勾上
5. **日期括号格式不匹配** — 弹窗使用全角 `（6天）` 但 regex 用 `\(` 匹配半角

### 修复
| # | 文件 | 修复 |
|:-:|------|------|
| 1 | `config/settings.py` | `MIN_DISCOUNT = 5.0` → `6.0` |
| 2 | `utils/date_parser.py` | 新增 `YYYY-MM-DD～YYYY-MM-DD` 完整日期格式 regex |
| 3 | `workflow/steps/extract.py` | 候选列表按 name 去重，同名保留天数最短的 |
| 4 | `workflow/steps/drawer_ops.py` | `indexOf` 匹配后 `splice` 从列表移除，防止二次勾选 |
| 5 | `workflow/steps/drawer_ops.py` | regex 改用 `[（(](\\d+)天[）)]` 兼容全角/半角括号 |

### 验证
```
6折门槛: 7候选 → 6选定
主题勾选: 6/6 ✅
商品全选: 12页 ✅
核价过滤: 98610行 → 16645保留
上传导入: ✅
```

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `config/settings.py` | 修改 | MIN_DISCOUNT 5→6 |
| `utils/date_parser.py` | 修改 | 加完整日期格式 |
| `workflow/steps/extract.py` | 修改 | 加同名去重 |
| `workflow/steps/drawer_ops.py` | 修改 | splice 防重复勾选 |
| `entrypoint/run.py` | 修改 | 版本头 v4.1.2 |
| `README.md` | 修改 | v4.1.2 修复记录 |
| `ARCHITECTURE.md` | 修改 | 版本同步 |
| `SKILL.md` | 修改 | 新坑点 |

---

## v4.1.1（2026-06-29）商品全选修复 — Selector 大修

### 问题
**商品全选只勾到 790/1190 个商品**，漏了约 4 页。

### 根因
三个 selector 不匹配实际 Temu DOM：
| # | 问题选择器 | 误 | 正 |
|:-:|-----------|-----|------|
| 1 | 弹窗容器 | `[data-testid="beast-core-modal"]` | `[class*="MDL_innerWrapper"]` |
| 2 | 每页条数下拉 | `[data-testid="beast-core-select-header"]` | `[class*="ST_selectValue"]` |
| 3 | 下一页禁用检测 | `PGT_disabled_5-120-1` 硬编码类 | `[class*="PGT_next"]:not([class*="PGT_disabled"])` |

此外：
- 切换 100 条/页后未回到第 1 页 → 起始页码偏移
- 固定 20 页循环上限 → 页数不够
- 第 1 页全选后 DOM 未完全加载 → 加 wait

### 修复
1. **弹窗容器** → `[class*="MDL_innerWrapper"]`（DOM 实测有效）
2. **页面尺寸** → `[class*="ST_selectValue"]` 点值文本而非 header
3. **全选方式** → 优先 `.beast-core-table thead [data-testid="beast-core-checkbox-checkIcon"]` 直接勾表头，fallback 文本"全选"搜索
4. **翻页检测** → `[class*="PGT_next"]:not([class*="PGT_disabled"])` 通用类匹配
5. **读取真实总页数** → 从分页组件 `PGT_pagerItem` 解析最大页码，动态循环
6. **切回第 1 页** → 改 100 条/页后强制回到 page 1
7. **等待** → sleep(3) 等页面尺寸切换完成，每页 sleep(1) 等 DOM 渲染
8. **debug 日志** → 输出当前页码 + 已选计数追踪

### 验证
```
每页: 20 → 100 ✅  总页数: 12  全部 12 页 全选=True
模板: 98340 行原始数据
核价过滤: 1625 条保留 → 上传导入成功
```

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `workflow/steps/product_select.py` | **重写** | 全选逻辑大修，Temu DOM 选择器对齐 |

---

## v4.1.0（2026-06-24）Hermes Autonomous Kernel v3

### 核心升级
- **AGENTS.md v3**：从"规范文件"升级为"自治执行内核"
- **STATE_SPEC.md 新建**：状态定义规范文档
- **自修复系统**：自动检测 workflow 偏离、state 不一致、文件结构污染
- **架构自对齐**：持续监控分层是否被污染，发现偏移自动修复
- **Workflow Graph**：DAG 依赖驱动，禁止随机执行
- **自进化系统**：重复失败时自动重构、优化、升级版本

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `AGENTS.md` | **重写** | v1 → v3 自治执行内核 |
| `STATE_SPEC.md` | **新建** | 状态定义规范 |

---

## v4.0.1（2026-06-24）Self-Updating Agent System

### 变更
- **AGENTS.md 初始化**：OS 规范持久化，不再重复加载
- **自维护架构**：AGENTS.md 作为系统内核，Agent 自动遵守规范
- **自修复规则**：检测结构混乱/状态丢失/workflow越权/依赖污染时自动修复
- **版本升级机制**：禁止重新发送 OS Prompt，改为版本升级（追加 diff）
- **修复**：`browser_service.navigate()` 缺少 `sleep(8)` 导致提取 0 个活动
- **修复**：`activity_pipeline._step_extract()` 没有检查空活动列表，导致空跑全程

### 文件变更
| 文件 | 操作 | 说明 |
|------|:----:|------|
| `AGENTS.md` | **新建** | OS 规范持久化内核 |
| `services/browser_service.py` | 修改 | navigate() 加 sleep(8) 等页面渲染 |
| `workflow/activity_pipeline.py` | 修改 | _step_extract 加空活动检查 |

---

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
