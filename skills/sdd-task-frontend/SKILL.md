---
name: sdd-task-frontend
description: 为单个前端仓与 Story 生成 tasks.md 和 alpha-tests.md；只定义实现顺序、验收声明与风险事实，不写代码或执行验证。
disable-model-invocation: true
---

# 前端实现计划

## 边界

一次只处理一个前端仓 × 一个 Story。`sdd-task` 负责遍历、目录与 `codespec` CLI；本 skill 只消费交接载荷并写 `tasks.md`、`alpha-tests.md`。共享所有权、状态、TaskPacket、基线源与切分规则以 [前端 SDD 执行契约](../../docs/skills/frontend-sdd/执行契约.md) 为唯一事实源。

计划回答“什么必须成立、按什么顺序实现、哪些事实提示风险”。命令、浏览器场景、验证广度、独立检视和证据结论都由 `sdd-dev-frontend` 根据仓库事实与最终 diff 决定。

## 输入

校验 `sdd-task` Step 2.4 交接的 Story 目录、项目类型、目标仓、搜索路径、需求锚点、设计文档路径、测试框架探测入口与 AT 提炼入口。目录或 schema 缺失时停止并回 `sdd-task`；设计文档缺失按上游降级规则登记，不自行补造。

## 工作流

| # | 动作 | 完成条件 |
| --- | --- | --- |
| 1 | 判断是否有静态形态变化，并按共享契约选择 `baseline_source` | 档位、来源候选与缺口可追溯 |
| 2 | 烘焙组件树、IFC、testability 锚点和样式引用 | 需求内的接口与 UI 接缝齐全 |
| 3 | 按 `detection_ref` 探测测试框架 | `test_framework` 有仓库证据；探测失败则停止 |
| 4 | 按 `extraction_ref` 把 SC/BR/GWT 提炼为 mock 集成级 AT | 每条需求锚点至少被一条 AT 覆盖 |
| 5 | 按共享契约切还原、逻辑与必要的机械 Task | 顺序、样式文件归属和例外明确 |
| 6 | 为每个 Task 写六步因果意图 | 每步可判定，无执行命令和实现代码 |
| 7 | 填 TaskPacket 与风险 token | 只写已知事实，未知风险留给 Dev 补判 |
| 8 | 用模板自审并落盘两份产物 | 完成标准全部满足，回传路径给 `sdd-task` |

## 硬门禁

1. 使用交接给定的目录与 schema，不调用 `codespec` CLI、不创建替代目录。
2. `tasks.md` 是唯一执行清单，`alpha-tests.md` 是唯一证据账本；不新增交接文件。
3. `baseline_source` 必填但只是下游确认输入；参照页只给候选。
4. 无外部基线时不写 px、色值、字号、圆角、阴影或自创响应式规格。
5. 一个 Task 一种形态；切不开时写明理由并分轮。样式集中在还原 Task，不设收尾样式 Task。
6. 六步只写声明与因果证据意图，不写精确命令、浏览器矩阵、全量回归或独立检视。
7. Step 3 只写文件与可观察行为；对象字面量、模板片段、函数体、内部 helper 和指定 API 调用属于 Dev。
8. 同一枚举、字段或 URL 契约只定义一次；禁止 TBD、TODO、空步骤和“类似任务”。

## 产物

以 [tasks-frontend.md](./templates/tasks-frontend.md) 生成 `tasks.md`。`alpha-tests.md` 沿用 `sdd-task` 的四节结构：L4、L3、AC ↔ 证据映射、Deferred AC；计划阶段只写用例与初始 `UNVERIFIED` 状态，不伪造证据。

## 完成标准

- 所有 SC/BR/GWT 均可追到 AT，再追到具体 Task。
- 每个 Task 都有精确文件范围、受影响声明、形态和六步因果意图。
- 静态形态的基线来源、路由、区块、状态与缺口明确；纯逻辑 Story 写明没有还原 Task 的理由。
- TaskPacket 字段与正文一致，风险 token 只来自可见计划事实。
- 全文没有占位符、实现代码、重复契约或固定验证动作。

完成后只回传两份路径和降级项，由 `sdd-task` 继续公共汇总。
