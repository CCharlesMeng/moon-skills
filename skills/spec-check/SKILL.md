---
name: spec-check
description: 在交付结束时，逐条对账 analysis-spec.md 中的 TargetBehaviors 与最终交付结果，产出 spec-check.md。这是每次标准交付的必经步骤，不是治理审计。
---

# 规格对账

## 概述

这个 skill 在交付结束时做一件事：对账 analysis-spec 中承诺的行为和实际交付的结果。

它是每次标准交付流程的必经步骤，位于实现与验证之后、`audit`（reflect）之前。

它不是 `audit` 的变体。`spec-check` 回答"承诺了什么，交付了什么"；`audit` 回答"学到了什么，哪些值得长期保留"。前者是后者的输入。

## 硬门禁

1. **不要跳过对账。** 即使所有 verify 都 pass，也必须逐条确认 TargetBehavior 的归宿。
2. **不要把 deferred 伪装成 as_specified。** 没做完就写"按 spec 交付"是最常见的 spec 漂移来源。
3. **不要在 spec-check 中做 reflect。** 对账只管"做了没有"，"学到了什么"是 `audit` 的事。
4. **不要替代 audit 做持久化决策。** spec-check 不决定哪些结论写回 context 或 immune。

## 何时使用

适用场景：

- 一个或多个 slice 的实现和验证已完成
- 需要在进入 audit / reflect 前确认 spec 兑现情况
- 多 slice 需求中每个 slice 完成后做一次 per-slice spec-check

不适用场景：

- 还没有 analysis-spec（先用 `analysis-spec`）
- 还没有完成实现与验证（先完成验证）
- 需要做整轮交付的 reflect 和治理（用 `audit`）
- 正在处理事故（用 `immune-debug`）

## 前置条件

- `analysis-spec.md` 已产出，TargetBehaviors 已编号
- 对应 slice 的 `verify.md` 已产出

## 工作流

### Phase 0：读取输入

读取：

- `analysis-spec.md` 的 TargetBehaviors 列表
- `slice-plan.md` 的 slice 到 TB 的映射
- 对应的 `verify.md`

### Phase 1：逐条对账

对 analysis-spec 中的每条 TargetBehavior，标记一个状态：

| 状态 | 含义 |
| --- | --- |
| `as_specified` | 按原始 spec 交付，verify 证据支持 |
| `intentionally_changed` | 交付结果和原始 spec 不同，但已与相关方确认，说明变更原因 |
| `deferred` | 本轮未交付，说明原因、风险和计划 |
| `abandoned` | 不再计划交付，说明原因 |

规则：

- 每条 TB 必须有且只有一个状态
- `intentionally_changed` 必须附变更原因和确认方
- `deferred` 必须附原因、风险评估和后续计划
- `abandoned` 必须附原因

### Phase 2：检查隐性偏差

除了逐条对账，还要检查：

- 是否有 verify 中发现的问题没有反映在对账表中
- 是否有 analysis-spec 中的 NonGoals 被意外实现了
- 是否有 RiskInventory 中的风险项变成了现实但未记录
- 是否有改动超出了 slice-plan 的预期范围

如果发现隐性偏差，新增条目到对账表中，标注为 `unplanned`。

### Phase 3：产出 spec-check.md

```markdown
# Spec Check: <topic>

## 对账结果

| TB # | Behavior | 状态 | 说明 |
| --- | --- | --- | --- |
| TB-1 | ... | as_specified / intentionally_changed / deferred / abandoned | ... |

## 隐性偏差

| # | 描述 | 发现来源 | 影响 |
| --- | --- | --- | --- |
<!-- 如果没有隐性偏差，写"无" -->

## 统计

- as_specified: N
- intentionally_changed: N
- deferred: N
- abandoned: N
- unplanned: N

## 交给 audit 的输入

- 需要 reflect 关注的偏差项
- 可能值得沉淀为 reusable learning 的发现
- 可能需要更新 context 的信号
```

退出门禁：

- 每条 TargetBehavior 都有归宿
- 无隐性偏差遗漏
- `intentionally_changed` 和 `deferred` 都有充分说明

## 多 slice 需求的处理

- 每个 slice 完成后可以做一次 per-slice spec-check
- 所有 slice 完成后，再做一次整轮 spec-check，合并所有 per-slice 结果
- 整轮 spec-check 完成后才进入 `audit`

## 降级模式

如果 analysis-spec 不完整或 TargetBehaviors 编号不连续：

- 仍按已有条目逐条对账
- 标注哪些条目缺少原始 spec 定义
- 建议后续补全 analysis-spec

如果 verify.md 不完整：

- 对缺少验证证据的 TB，不允许标记为 `as_specified`
- 标记为 `deferred` 并说明验证缺口

## 最终输出

结束时必须包含：

### 对账摘要

- 总目标行为数
- 各状态的数量
- 关键偏差项

### 产出文件

- `spec-check.md` 路径

### 下一步

- 进入 `audit` 做 post-ship reflect
- 如果有大量 deferred 或 unplanned 项，建议在 audit 中重点 review

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `spec-check.md` | `docs/specs/<topic>/spec-check.md` |
| per-slice spec-check（可选） | `docs/specs/<topic>/slices/<slice-id>/spec-check.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。所有属于同一需求的工件统一归入 `docs/specs/<topic>/`。
