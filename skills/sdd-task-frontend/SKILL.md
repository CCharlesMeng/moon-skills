---
name: sdd-task-frontend
description: 为单个前端仓与 Story 生成 tasks.md 和 alpha-tests.md；定义实现位置、每个文件的功能职责、验收声明与风险事实，不写代码也不执行验证。
disable-model-invocation: true
---

# 前端实现计划

## 边界

一次只处理一个前端仓 × 一个 Story。`sdd-task` 负责遍历、目录与 `codespec` CLI；本 skill 只消费交接载荷并写 `tasks.md`、`alpha-tests.md`。共享所有权、分层边界、扩散承接、声明状态、TaskPacket、基线源与切分规则以 [前端 SDD 执行契约](../../docs/skills/frontend-sdd/执行契约.md) 为唯一事实源。

计划回答四件事：**什么必须成立、改哪些文件、每个文件实现什么功能、按什么顺序**。粒度写到「打开哪个文件、在里面实现什么」；代码写法、命令、浏览器场景、验证广度和证据结论由 `sdd-dev-frontend` 决定，计划没识别到的连带改动也由它按[扩散承接](../../docs/skills/frontend-sdd/执行契约.md#扩散承接)接住——所以计划不必为了保险把文件清单写宽。

## 输入

`sdd-task` Step 2.4 逐项交接下表。目录或 schema 缺失时停止并回 `sdd-task`；设计文档缺失按上游降级规则登记，不自行补造。

| 交接项 | 含义 | 到哪里取 |
| --- | --- | --- |
| `story_dir` | 本 Story 两份产物的落盘目录 | 已由 `codespec new change` 建好的 `codebase/<project>/codespec/changes/<requirement>/<story>/` |
| `schema_tasks` / `schema_alpha_tests` | 两份产物的落盘 schema | 交接的 `codespec instructions` 原文；本 skill 不再调 CLI |
| `project` / `project_type` | 目标前端仓名 / 固定 `frontend` | 交接值 |
| `search_paths` | 本 Story 允许改动的仓内路径 | 交接值，与仓内实际目录结构核对 |
| 需求锚点 | `SC-` 场景、`BR-` 规则、§5 验收场景摘要 GWT | 同 Story 目录 `story-delta-spec.md` |
| 前端设计 | 页级组件树、前端接口契约（IFC，即组件间 props/事件与对后端 API 的调用切片）、路由、testability 锚点 | 同 Story 目录 `story-delta-frontend-design.md`；共享技术栈与路由约定看包根 `requirement-frontend-design.md` |
| 后端契约 | 方法、URL、请求/响应字段、枚举 | `story-delta-design.md` / `requirement-design.md`，**只引用不重定义** |
| `detection_ref` | 测试框架探测规则，判据只有这一份 | [`sdd-task/references/test-framework-detection.md`](../sdd-task/references/test-framework-detection.md) |
| `extraction_ref` | 验收用例提炼规则，判据只有这一份 | [`sdd-task/references/acceptance-criteria-extraction.md`](../sdd-task/references/acceptance-criteria-extraction.md) |
| 知识底座结果 | 已消费的规范 `entries[].id` 与 `gaps` | 交接值，原样写进 `tasks.md` 的知识 trace |

## 工作流

| # | 动作 | 完成条件 |
| --- | --- | --- |
| 1 | 判断本 Story 是否产生或改变静态形态，据此选视觉基线来源 `baseline_source`：有 HTML 原型 → `prototype`；无原型但仓内有同类已上线页面 → `reference_page`；只有可逐条落地的文字规格 → `text_spec`；纯逻辑 → `none` | 档位、来源候选与缺口可追溯 |
| 2 | 从前端设计与仓内代码定出受影响路由、组件层级与挂载点、状态归属、数据流、可复用的既有资产、样式文件归属与 testability 锚点 | 每个受影响文件都能说出它实现什么、导出什么 |
| 3 | 按 `detection_ref` 的规则扫仓根 `package.json` 与测试目录结构，填 `test_framework` | 有仓库证据；探测失败则停止，不默认 Jest/Vitest |
| 4 | 按 `extraction_ref` 的规则把 `SC-`/`BR-`/GWT 提炼为 mock 集成级 AT | 每条需求锚点至少被一条 AT 覆盖 |
| 5 | 按共享契约切还原、逻辑与必要的机械 Task | 顺序、样式文件归属和例外明确 |
| 6 | 按形态给每个 Task 裁步骤（2–5 步），并标出还原轮的取证归属 | 每步可判定；没有为凑步数补的空步骤 |
| 7 | 填 TaskPacket、每个 Task 的「可能扩散」与风险 token | 只写已知事实，未定论的交给 Dev |
| 8 | 用模板自审并落盘两份产物 | 完成标准全部满足，回传路径给 `sdd-task` |

## 硬门禁

1. 使用交接给定的目录与 schema，不调用 `codespec` CLI、不创建替代目录。
2. `tasks.md` 是唯一执行清单，`alpha-tests.md` 是唯一证据账本；不新增交接文件。
3. 每个受影响文件都写清位置、职责与对外契约；这三层缺一就不算计划，不能推给 Dev 现场决定。
4. 不写可以直接粘贴运行的代码：函数体、JSX/模板片段、CSS 规则、对象字面量、具体 API 调用语句、内部 helper 怎么拆，一律属于 Dev。
5. 视觉数值只来自外部基线。无外部基线时不写 px、色值、字号、圆角、阴影，也不自创响应式规格。
6. `baseline_source` 必填但只是下游确认输入；参照页只给候选。
7. 一个 Task 一种形态；切不开时写明理由并分轮。样式集中在还原 Task，不设收尾样式 Task。
8. 步骤按形态裁剪，不把每个 Task 都凑成同样多步；只写声明与因果意图，不写精确命令、浏览器矩阵、状态矩阵、全量回归或独立检视。
9. 还原取证以页面为单位，标明归属轮；不为单个 Task 安排页面级复验。
10. 文件清单只写已确认范围；有风险没定论的写进「可能扩散」，不靠扩大清单兜底。
11. 同一枚举、字段或 URL 契约只定义一次；禁止 TBD、TODO、空步骤和「类似任务」。

## 产物

以 [tasks-frontend.md](./templates/tasks-frontend.md) 生成 `tasks.md`。

`alpha-tests.md` 计划侧只写四节：L4 单元测试记录、L3 单服务单接口集成测试记录（前端即 mock 集成级）、AC ↔ 证据映射、Deferred AC；只写用例与初始 `UNVERIFIED` 状态，不伪造证据。还原证据记录与计划外承接两节由 Dev 追加，计划不建空壳。

## 完成标准

- 所有 `SC-`/`BR-`/GWT 均可追到 AT，再追到具体 Task。
- 每个 Task 都有精确文件范围、每个文件的职责、受影响声明、形态和按形态裁过的步骤。
- 受影响路由、组件层级、状态归属、数据流与复用决策齐全；复用不了的写明原因。
- 静态形态的基线来源、区块、必测状态与缺口明确；纯逻辑 Story 写明没有还原 Task 的理由。
- TaskPacket 字段与正文一致，风险 token 与「可能扩散」只来自可见计划事实。
- 全文没有占位符、可运行代码、重复契约或固定验证动作。

完成后只回传两份路径和降级项，由 `sdd-task` 继续公共汇总。
