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
| 仓库 baseline | <目录 + 本次读过的关注点文件；仓库 baseline 不再有 readiness 字段> |
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

## 二、`acceptance.md`

**这份文件的主体由 `manage_review_pipeline.py aggregate` 渲染，不要手写。** 它是**人验收时的入口**，所以顺序固定为「能不能验收 → 有什么必须你处理 → 有什么你该知道但不用动 → 往下追的路径」；机器对账细节（代码指纹、证据纪元、逐条覆盖明细）一律不进这份文件，它们在 `review-results.json` 里。

聚合器渲染的节：

```markdown
# 验收摘要

<第一句就是结论：可验收 / 可验收但有 N 件需要你定 / 暂不可验收，因为 N 条阻断>

## 需要你处理
<阻断级与需要拍板的项；表列固定为「什么问题 / 在哪 / 要你做什么」。全清时整节不出现>

## 你该知道，但不用动
<不需要决定的交接项，一条一行>

## 这次判了什么
<已判并通过的一句话带过；没判到或判不全的逐条给原因；判定不适用的逐条给理由；
 主动收窄的必须署名列出——收窄可见是它存在的全部意义>

## 改进建议（本次不修） / 未决问题 / 暂缓的验收项 / 交 sdd-init-frontend 的规范候选
<各节有内容才出现>

## 要往下追的话
<指向 dev-baseline.md、alpha-tests.md、review-results.json 的路径>
```

主 agent 手写追加的两节：

```markdown
## 计划外承接

<无；或按扩散承接规则直接承接的文件、所属 Task、原因与失效范围>

| 文件 | Task | 为什么必须一并改 | 失效了哪些证据 |
| --- | --- | --- | --- |

## 收口结论

<逐声明状态、阻断清零与退出门禁结论；状态跟用户说话时用中文词，账本值仍是英文常量>
```

## 三、Phase 0 自动起草

会话已经明确 Story、AC、基线和文件范围但缺 `tasks.md` 时，直接读取并填写 `<skill-dir>/../sdd-task-frontend/templates/tasks-frontend.md`，不要在本文件维护第二份 tasks 模板。

`alpha-tests.md` 只起草最小骨架：

```markdown
# <Story> · Alpha Tests
## L4 单元测试记录
## L3 单服务单接口集成测试记录
## 还原证据记录
## 计划外承接
| 文件 | Task | 原因 |
| --- | --- | --- |
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
