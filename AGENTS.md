# AGENTS.md — Engineering OS 系统规范（持久化内核）

> 版本：v1 · 类型：工程操作系统规范
> 初始化：2026-06-24 · 不可重复覆盖（除非版本升级）

---

## 🎯 总目标

将当前项目维护为：

- ✅ **可复现** — clone 即可运行
- ✅ **可恢复** — 断点续跑
- ✅ **可审计** — 每一步有记录
- ✅ **可扩展** — 分层结构清晰
- ✅ **结构化** — 强约束 OS 架构

---

## 🧱 架构约束（必须遵守）

```
entrypoint/   ← 唯一入口（仅 run.py）
workflow/     ← 流程控制层（不得直接调用外部 API）
services/     ← 外部系统隔离层（不得包含业务逻辑）
core/         ← 核心抽象层（状态机、注册表）
config/       ← 配置集中管理（禁止硬编码）
utils/        ← 工具函数（无副作用）
state/        ← 状态持久化（唯一事实源）
```

### 禁止
- ❌ 硬编码路径 / 端口 / 目录
- ❌ 业务逻辑直接调用底层 API
- ❌ 手动步骤依赖
- ❌ 隐式状态依赖

---

## 🔁 状态机规则

所有流程必须使用 `core/state_machine.py`：

- `state = INIT → RUNNING → (STEP_N) → DONE / FAILED`
- state 必须序列化到 `state/state.json`
- 每个任务必须有 `task_id`
- 每一步完成必须写入 state
- 支持 `get_remaining_steps()` 断点续跑

---

## 📦 自动执行规范

每次修改代码时，必须：

1. **检测架构合规** — 新文件是否在正确的层
2. **检测状态依赖** — 是否破坏了 state machine
3. **检测硬编码** — 配置是否放到了 config/
4. **检测隐式依赖** — 是否引入了未声明的依赖

如果违反 → 自动修复 + 记录到 CHANGELOG

---

## 📚 文档自动维护

| 文件 | 更新条件 |
|------|---------|
| `README.md` | 运行方式变化时 |
| `ARCHITECTURE.md` | 结构变化时 |
| `CHANGELOG.md` | 任何行为变化时 |
| `AGENTS.md` | 规范版本升级时 |

---

## 🔄 版本升级机制

OS 更新方式：

- ❌ 禁止重新发送整套 OS Prompt
- ✅ 正确：版本升级（只追加 diff）

升级流程：
1. 更新 `AGENTS.md` 版本号
2. 记录变更到 `CHANGELOG.md`
3. 更新 `ARCHITECTURE.md`（如果有结构变化）

---

## 🧪 验证标准

每次修改后必须能：

```bash
git clone <repo> && cd project
pip install -r requirements.txt
python entrypoint/run.py
```

无人工步骤，行为一致。

---

## 🧠 自修复规则

检测到以下情况时自动修复：

| 检测项 | 自动行为 |
|--------|---------|
| 结构混乱 | 重建模块边界 |
| state 丢失 | 从 `state.json` 恢复或重新 INIT |
| workflow 越权 | 将底层调用移到 services/ |
| 依赖污染 | 抽取到 config/ 或 utils/ |

修复后必须写入 CHANGELOG。

---

## 🚨 最高优先级

> **OS 不重复加载，但必须持续生效。**

本文件是系统内核，一旦初始化即不可重复覆盖。
