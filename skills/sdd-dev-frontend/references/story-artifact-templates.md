# Story 工件模板

只在创建对应工件时读取本文件。QA 基线字段以 [qa-baseline-template.md](./qa-baseline-template.md) 为准；验证组合以 [validation-policy.md](./validation-policy.md) 为准；机器报告与 schema 不在 Markdown 模板重复。

## 一、`dev-baseline.md`

```markdown
# <Story> · 开发基线

## 给人的摘要

- 做什么：<路由、能力与用户可见结果>
- 标准来自哪里：<原型 / 待确认参照页 / 文字规格 / 纯逻辑>
- 本次确认：<适用 QA 声明数、豁免数、工作假设与必须决策项>

## 执行起点

| 项 | 值 |
| --- | --- |
| Story / repo | <...> |
| base ref | <...> |
| 需求路径 | <tasks / alpha-tests / frontend-design> |
| 基线源 | <候选 → 确认结果> |
| 仓库 readiness | <READY / READY_WITH_LIMITS + 相关 limit> |
| Story 限制 | <只列影响已选模块的限制；无则“无”> |

## 起点质量

| 已选模块 | 命令 / scope | cache | exit / failures | 证据键 |
| --- | --- | --- | --- | --- |

## 验证组合（初始）

| 风险触发器 | 模块 | 独立检视与维度 | 依赖声明 |
| --- | --- | --- | --- |

## 工程依据

<勘察模式；采用的 PATTERN-* / REQ-DEC-* 及选择理由>

## 功能理解

<Story 范围、AC、页面/状态/接口映射>

## QA 基线

<按 qa-baseline-template.md 生成适用行>

## 已知缺口

| 缺口 | 来源分类 | 现有证据 | 处理 |
| --- | --- | --- | --- |

## 变更记录

| 时间 | 变更 | 原因 | 用户确认 |
| --- | --- | --- | --- |

## 指纹附录

<REPO section、需求输入、原型、QA baseline、restore contract 的指纹>
```

## 二、`dev-review.md`

```markdown
# <Story> · 开发检视

## 给人的摘要

<交付状态；哪些声明已证、未证或延期；不复制过程>

## 检视基准

| 项 | 值 |
| --- | --- |
| 最终验证组合 | <risk / modules / roles / dimensions> |
| 代码与证据纪元 | <base ref / code fingerprint / evidence epoch> |
| 工件索引 | <dev-baseline / alpha-tests / restore reports / review evidence / results> |

## 执行结果

| 模块 / 角色 | 状态 | coverage / 证据 | 缺口 |
| --- | --- | --- | --- |

## 阻断级

<无；或编号、声明、证据、修复与重跑>

## 建议级

<无；或结构化条目>

## Open Question

<无；或结构化条目>

## Deferred

<无；或 AC、原因与解除条件>

## Handoff

| # | 类型 | 现象 | 影响 | 用户是否需要处理 | 引用 |
| --- | --- | --- | --- | --- | --- |

## 收口

<逐声明状态、阻断清零与退出门禁结论>
```

## 三、Phase 0 自动起草

会话已经明确 Story、AC、基线和文件范围但缺 `tasks.md` 时，直接读取并填写 `<skill-dir>/../sdd-task-frontend/templates/tasks-frontend.md`，不要在本文件维护第二份 tasks 模板。

`alpha-tests.md` 只起草最小骨架：

```markdown
# <Story> · Alpha Tests
## L4 单元测试记录
## L3 单服务单接口集成测试记录
## 还原证据记录
## AC ↔ 证据映射
| AC / AT | 状态 | 证据 | 说明 |
| --- | --- | --- | --- |
## Deferred AC
| AC | 原因 | 解除条件 |
| --- | --- | --- |
```

缺 `story-delta-frontend-design.md` 时只写已知事实，不补设计：

```markdown
# <Story> · Frontend Design Delta
## 目标与 AC 引用
## 对接模式
## 文字规格
## 当前代码事实
## 状态、交互、接口与数据映射
## 风险与依赖
```

会话未定义的字段写“未定义 / 待确认”，进入 Phase A 的已知缺口；不得用合理猜测填满模板。
