# Phase -1 / 0：接入与执行起点

只在进入 Phase -1 或 Phase 0 时读取。本阶段完成仓库 readiness、Story 路径、上游事实与初始验证组合；不预跑未选验证能力。

## Phase -1 — 仓库接入

1. 解析 `<repo-root>`、`<project-sdd-dir>`、`<repo-id>`、`<repo-baseline-dir>`。
2. 走**极轻的门**，只查两件事：

| 判据 | 不满足时 |
| --- | --- |
| `<repo-baseline-dir>` 下八份 baseline 文件在不在 | 全缺或大面积缺 → 完整执行 `sdd-init-frontend` |
| `structure.md` 的栈签名读不读得出一个具名的栈 | 读不出 → 完整执行 `sdd-init-frontend` |

**这道门刻意不精确。** 「本 Story 需要的那几条查得到吗」在 Phase -1 还没有信息可判——`tasks.md` 要到 Phase 0 才读。所以这里只拦住「baseline 根本不存在」这一种情况；具体某条结论不成立由消费点自证并就地修，不在这里预判。

**不查 readiness、不查指纹、不查 stale。** 这三样已随仓库 baseline 改版整体取消：内容指纹只能告诉你文件变了，永远不能告诉你结论变了，为这点信噪比要养账本、stale 状态、readiness 回退和一条「本 Story 自身改动放行」的例外。现在的跟进方式是消费点自证 + 就地修，Phase C/D 重查时**没有任何 baseline 失效需要放行或路由**。

退出：baseline 存在且栈可判。

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

记录 `<base-ref>`、Story 文件范围、Requirement 决策和已知运行限制。只读取当前 Story 实际需要的 `PATTERN-*` / `REQ-DEC-*` 正文，不复制仓库 baseline，也不记录任何 baseline 指纹。

按 `index.md` 的场景索引取 ID，再回读对应文件；读到的清单条目指路失效时**就地修那一条**并随本 Story 提交，不阻塞、不路由；规范条目不成立时攒进 `dev-review.md`，Story 收口时一次确认。规范节只有 `sdd-init-frontend` 能改。

### 5. 编译初始验证组合

完整读取 [validation-policy.md](./validation-policy.md)，从 AC/AT、Task 范围、上游风险事实、仓库 baseline 和运行限制编译初始组合。每条声明初始为 `UNVERIFIED`。

只有组合含命令模块时才读取 [preflight-and-telemetry.md](./preflight-and-telemetry.md) 的缓存节并取得起点失败集合；只有组合含浏览器模块时才解析、实测 `<browser-driver>`。未选能力不探测、不生成空表。

### 6. 写 `dev-baseline.md`

按 [story-artifact-templates.md](./story-artifact-templates.md) 第一节写执行起点与初始组合。若本次明确要为流程优化取数，再读取 telemetry 节并开启 `<execution-telemetry>`；默认关闭。

退出：路径唯一、上游事实已核、初始组合与执行起点已落盘。
