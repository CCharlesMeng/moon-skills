---
api_version: review.codespec/v1
kind: Checklist
id: dev-frontend-restore
title: 样式还原（冻结契约）
order: 10
category: visual-restore
inputs:
  - artifact: restore_contract
    sections: ["全文"]
    layer: restore_contract
  - artifact: restore_report
    sections: ["全文"]
    layer: restore_report
  - artifact: qa_baseline
    sections: ["R1-R6", "冻结豁免"]
    layer: qa_baseline
---

# 样式还原（冻结契约）

只判变更区块对已冻结 R 行的机器结果。基线里没有的 R 分类整条 `skipped`。

## `block-hierarchy-complete`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 基线未生成 R1（未改静态结构）时记 `skipped`。
- legacy_id: R1

**区块与层级完整性**：必须出现的区块、顺序、父子关系与数量约束是否与冻结 R1 一致。
   - 契约 `structure` / `exact` 规则 RED，且未命中 `EX-n` → **P0**。
   - 关键区块缺失或父子关系颠倒 → **P0**。
   - 数量约束越界但主路径仍可完成 → P1。
   - 把原型 class 名当作实现义务（R1 期望值写了设计稿 class）→ 记 Open Question，不升 P0。

## `copy-consistency`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 基线未生成 R2（未改静态标签或格式）时记 `skipped`。
- legacy_id: R2

**文案一致性**：静态文案是否与冻结逐字值一致；动态位是否满足字段 / 格式 / 边界，而不是原型样例值。
   - 静态文案 `exact` RED 且未豁免 → **P0**。
   - 动态位格式 / 边界与冻结声明不符（如非有限数应显示 `--` 却显示 `NaN`）→ **P0**。
   - 用原型里的示例数字 / 姓名去要求真实接口返回同样的值 → 不报；那不是冻结对象。

## `spacing-alignment`

- normative_level: MUST
- default_severity: P1
- max_severity: P1
- skip_when: 基线未生成 R3（无外部数值或参照事实）时记 `skipped`。
- legacy_id: R3

**间距与对齐**：元素对、方向、期望值 / 容差是否落在冻结 R3 与契约 `numeric` 规则内。
   - `numeric` RED 且超出声明容差、未豁免 → P1。
   - 无外部数值来源却用「看起来空一点」判违规 → 不报。
   - CSS 序列化等价（`#fff`↔`#ffffff`、`0px`↔`0`）不是还原偏差。

## `state-style-fidelity`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 基线未生成 R4（未要求 hover/focus/disabled/selected/loading）时记 `skipped`。
- legacy_id: R4

**状态样式**：冻结的状态触发条件与可观察视觉结果是否成立。
   - 声明的状态在契约 / 报告中 RED → P1；导致无法识别可操作控件 → **P0**。
   - `check_mode: visual` 缺补证 → YELLOW，记 `known_gaps`，不改 GREEN、不降为 clear。
   - 基线没要求的状态（如从未声明的 `active`）不发明检查。

## `empty-overflow-content`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 基线未生成 R5（未要求 empty/overflow/long-copy/large-list）时记 `skipped`。
- legacy_id: R5

**空态与边界内容**：冻结的 fixture 与结构 / 换行 / 截断 / 滚动结果是否成立。
   - 空态文案或结构 RED → **P0**（主路径可完成但声明不成立仍是 P0）。
   - overflow / long-copy 规则 RED 且未豁免 → P1。
   - 命中 `EX-n` 的字段（例如某张卡被明确排除 `--` 口径）→ `skipped` 并留痕，任何级别都不报。

## `target-viewport-integrity`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 基线未生成 R6（无目标视口）时记 `skipped`。
- legacy_id: R6

**指定视口下的布局完整性**：仅检查 R6 已冻结的视口与关键区块；判据是滚动 / 重叠 / 截断，不是「应改成另一套布局」。
   - 冻结视口下横向滚动 / 重叠 / 截断 RED → **P0**。
   - 需要改变布局结构才能适应的缺口 → Open Question，回上游，不自行断点设计。
   - 未写入 R6 的视口不检；那不是本格漏检。
