# STATE_SPEC.md — 状态定义规范

> 版本：v1 · 最后更新：2026-06-24

---

## 一、状态文件位置

**唯一文件：** `state/state.json`（gitignored，不提交到仓库）

---

## 二、状态结构

```json
{
  "task_id": "activity_1687000000",
  "state": "RUNNING",
  "current_step": "SELECT_PRODUCTS",
  "completed_steps": [
    "EXTRACT_ACTIVITIES",
    "OPEN_DRAWER",
    "SELECT_ACTIVITY_TYPE",
    "SELECT_THEMES",
    "SELECT_SITES"
  ],
  "errors": [
    {
      "step": "GENERATE_TEMPLATE",
      "error": "下载超时",
      "time": 1687000000.0
    }
  ],
  "meta": {
    "start_time": 1687000000.0,
    "step_start": 1687000000.0,
    "end_time": null,
    "elapsed_seconds": null
  }
}
```

---

## 三、状态定义

| 状态 | 说明 |
|------|------|
| `INIT` | 初始化，新任务 |
| `RUNNING` | 运行中 |
| `DONE` | 正常完成 |
| `FAILED` | 执行失败 |

---

## 四、步骤定义

| 步骤名 | 说明 | 模块 |
|--------|------|------|
| `EXTRACT_ACTIVITIES` | 活动提取筛选 | `workflow/steps/extract.py` |
| `OPEN_DRAWER` | 打开 Drawer | `workflow/steps/drawer_ops.py` |
| `SELECT_ACTIVITY_TYPE` | 勾选专题活动 | `workflow/steps/drawer_ops.py` |
| `SELECT_THEMES` | 选择主题 | `workflow/steps/drawer_ops.py` |
| `SELECT_SITES` | 选择站点 | `workflow/steps/drawer_ops.py` |
| `SELECT_PRODUCTS` | 选择商品 | `workflow/steps/product_select.py` |
| `GENERATE_TEMPLATE` | 生成模板 | `workflow/steps/download_submit.py` |
| `PRICE_FILTER` | 核价过滤 | `workflow/steps/download_submit.py` |
| `UPLOAD_IMPORT` | 上传导入报名 | `workflow/steps/download_submit.py` |

---

## 五、恢复规则

1. 新运行时检测 `state/state.json` 是否存在
2. 如果存在且 `state` 为 `RUNNING` 或 `FAILED` → 自动恢复
3. 恢复时跳过 `completed_steps` 中的步骤
4. 从 `get_next_step()` 开始执行
5. 如果不存在或全部完成 → 全新开始
