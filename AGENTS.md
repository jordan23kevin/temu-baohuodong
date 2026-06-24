# AGENTS.md — Hermes Autonomous Kernel v3

> 版本：v3 · 类型：自治执行内核
> 初始化：2026-06-24 · 不可重复覆盖（版本升级使用 diff）

---

## 🧠 系统本质

本系统是一个**持续运行的工程执行工厂（Execution Factory）**，不是脚本，不是框架。

核心组成：
- **Execution Engine** — 执行引擎（自动执行任务）
- **State Kernel** — 状态内核（唯一事实源）
- **Workflow Graph** — 流程图（DAG 依赖驱动）
- **Repair System** — 自修复系统（自动纠偏）
- **Evolution System** — 进化系统（自动升级）

---

## 🔁 自动执行规则

Agent 执行任何任务时必须：
- ✅ 自动识别任务类型，映射到对应 workflow
- ✅ 自动更新 state
- ✅ 自动记录 trace（task_id + 时间戳）

禁止：
- ❌ 手动状态管理
- ❌ 非结构化流程
- ❌ 隐式执行路径（每一步必须显式）

---

## 🧠 状态内核

唯一事实源：**`state/state.json`**

规则：
- 所有任务绑定 `task_id`
- 所有行为写入 state
- state 必须可 replay（回放）
- state 必须可恢复执行

状态流：`INIT → RUNNING → PROCESSING → DONE / FAILED`

---

## 🔄 自修复系统

检测到以下异常时自动触发：

| 检测项 | 自动行为 |
|--------|---------|
| workflow 偏离 | rollback 到最近稳定 state |
| state 不一致 | 从 state.json 修复 |
| 文件结构污染 | 重建模块边界 |
| 执行失败 > 阈值 | 记录 root cause，写 CHANGELOG |

---

## 🧱 架构自对齐

持续监控：
- `workflow/` 是否被 services 层代码污染
- `core/` 是否被业务逻辑侵入
- `services/` 是否被 workflow 直接绕过
- `state/` 是否被跳过写入

发现偏移 → 自动修复 + 记录 CHANGELOG。

---

## 📊 Workflow Graph

所有执行必须转化为 DAG（有向无环图）：
- **Node** = 步骤（step）
- **Edge** = 依赖关系
- **Execution** = 拓扑顺序执行

禁止随机顺序执行和非结构化调用链。

---

## 📦 自进化系统

触发条件：
- 重复失败模式（同一 step 连续失败）
- 架构冲突频繁
- state 回滚过多

自动行为：
- 重构 workflow
- 优化 state schema
- 重写 module boundary
- 升级版本号

---

## 📚 自动文档系统

| 文件 | 更新条件 |
|------|---------|
| `README.md` | 运行方式变化 |
| `ARCHITECTURE.md` | 架构变化 |
| `CHANGELOG.md` | 任何行为变化 |
| `STATE_SPEC.md` | 状态定义变化 |
| `AGENTS.md` | 规范版本升级（diff 追加） |

---

## 🔁 执行生命周期

每个任务必须经过：

```
INIT → PLAN → EXECUTE → VERIFY → COMMIT → TRACE
```

---

## 🚨 最高原则

系统必须保证：
1. **可重建** — clone 即可运行
2. **可回放** — state 可完整重放
3. **可恢复** — 断点续跑
4. **可审计** — 每一步有记录
5. **可进化** — 自动升级版本

---

## 🏭 结论

> 本系统不再依赖"人类提示词驱动"，而是持续自我维护的工程执行内核。
> Agent 自己知道结构、自己修复错误、自己维护状态、自己进化架构。
