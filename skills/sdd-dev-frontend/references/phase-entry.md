# Phase -1 / 0：接入与执行起点

只在进入 Phase -1 或 Phase 0 时读取。本阶段完成仓库 readiness、Story 路径、上游事实与初始验证组合；不预跑未选验证能力。

## Phase -1 — 仓库接入

1. 解析 `<repo-root>`、`<project-sdd-dir>`、`<repo-id>`、`<repo-baseline-dir>`。
2. 运行 `<init-skill-dir>/scripts/manage_repo_baseline.py status`。按脚本输出处理：

| readiness | 动作 |
| --- | --- |
| `READY` | 继续 Phase 0 |
| `READY_WITH_LIMITS` | 影响实现安全/事实可信的 limit 回 `sdd-init-frontend`；仅影响验证能力的 limit 留给组合逐声明处理 |
| `DRAFT/BLOCKED`、缺失或不可解析 | 完整执行 `sdd-init-frontend` 后重跑 status |

Phase C/D 重查时，REPO-3 失效只有同时满足以下两条才按“本 Story 自身改动”放行：当前全部改动文件均在 Story 范围内；`dev-baseline.md` 记录的原 REPO-3 section 指纹仍与 baseline 表一致。任一不满足就回 Phase -1 刷新，不把真失效伪装成 Story 降级。

退出：readiness 可安全实现，相关限制已分类。

## Phase 0 — 执行起点

### 1. 定位需求

解析 `<story-dir>`、`<requirement-dir>`、`<prototype-dir>`、`<design-spec-dir>`。唯一命中时静默继续；缺失或多候选按 P7 一次问完。`<design-spec-dir>` 由 Requirement 目录推导，不单独询问。

### 2. 缺 `tasks.md` 的分支

仅当会话已明确 Story 范围、AC、基线来源和文件范围时，读取 [story-artifact-templates.md](./story-artifact-templates.md) 第三节，起草 `tasks.md`、缺失的 `alpha-tests.md` 与 `story-delta-frontend-design.md`，展示草稿并确认后落盘。缺任一核心信息时回 `sdd-task` 或按 P7 问缺口；不带分歧开工。

### 3. 核实上游事实

按 [共享执行契约](../../../docs/skills/frontend-sdd/执行契约.md) 读取 TaskPacket。核实 `baseline_source`、目录、路由、状态、还原 Task 与风险 token：

- 字段是候选索引；缺席不表示低风险。
- `prototype` 必须实测目录存在且包含相关 HTML，否则重新判档并记录冲突。
- `reference_route` 仍是待确认候选。
- 风险 token 与 Task 正文、仓库事实冲突时以可验证事实为准。

### 4. 建立执行上下文

记录 `<base-ref>`、Story 文件范围、REPO section 指纹、Requirement 决策和已知运行限制。只读取当前 Story 实际需要的 `PATTERN-*` / `REQ-DEC-*` 正文，不复制仓库 baseline。

### 5. 编译初始验证组合

完整读取 [validation-policy.md](./validation-policy.md)，从 AC/AT、Task 范围、上游风险事实、仓库 baseline 和运行限制编译初始组合。每条声明初始为 `UNVERIFIED`。

只有组合含命令模块时才读取 [preflight-and-telemetry.md](./preflight-and-telemetry.md) 的缓存节并取得起点失败集合；只有组合含浏览器模块时才解析、实测 `<browser-driver>`。未选能力不探测、不生成空表。

### 6. 写 `dev-baseline.md`

按 [story-artifact-templates.md](./story-artifact-templates.md) 第一节写执行起点、初始组合和指纹。若本次明确要为流程优化取数，再读取 telemetry 节并开启 `<execution-telemetry>`；默认关闭。

退出：路径唯一、上游事实已核、初始组合与执行起点已落盘。
