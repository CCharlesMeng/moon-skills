---
api_version: review.codespec/v1
kind: Checklist
id: dev-frontend-layout
title: 布局与响应式
order: 20
category: layout
inputs:
  - artifact: code_diff
    sections: ["全文"]
    layer: code_diff
  - artifact: qa_baseline
    sections: ["R6", "required_states", "冻结豁免"]
    layer: qa_baseline
  - artifact: browser_evidence
    sections: ["全文"]
    layer: browser_evidence
cell: CODE-LAYOUT
task_statement: 在真实数据与已冻结视口下，布局是否跨页一致、不溢出、不破、对齐成立，交互态与滚动/固定行为可观察。
max_findings: 12
forbidden_reads:
  - other_role_findings
  - restore_contract
  - restore_report
---

# 布局与响应式

只检风险闭包命中的维度。未分配的 L 项 `skipped`。不重判 restore 契约已覆盖的单区块数值。

## 格子边界

本格占 `CODE-LAYOUT`。现象归属见 [SKILL.md 的现象归属表](../SKILL.md#现象归属)。

本格判**跨页、真实数据、多视口**。还原轮已经用冻结契约兜住单区块数值；这里不打开 `restore_contract` / `restore_report`，不重判同一条 R 规则的 RED/GREEN。

R6 已冻结的视口可以用来限定 L3 的检查范围，但结论必须引用**运行时几何 / DOM 事实**，不能引用还原报告条目。

不判 F/REG（test-lens），不判 token 硬编码（convention-lens 的 `style-token-scheme`）。

## 禁止

- 不发明响应式断点或布局结构变化；上游没有规格时只保障「不破」。
- 只取 R6 已冻结且风险闭包命中的视口。
- 机器可检项记录几何 / DOM 事实。截图只补两类：裁切后的焦点构图、混合与背景滤镜的合成结果。阴影与字体栅格不再截图——阴影读计算样式 longhand，字体栅格随引擎版本变化，两者截了都得不出可行动的结论。
- 无证据不得判 P0；浏览器证据不新鲜时 `unexecuted` + `known_gaps`，不绕过重跑全套场景。
- 命中 `EX-n` 的偏差不出 Finding，必须留痕。

## `cross-page-consistency`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及共享样式、跨页组件或同类页对照时记 `skipped`。
- legacy_id: L1

**跨页一致性**：同类元素在不同页面的间距、字号、圆角、控件高度是否一致。
   - 共享组件 / 共享样式在两页表现冲突，且可指出对照页与测量值 → P1。
   - 仅「看起来不太像」而无测量或参照页 → 不报。
   - 历史页未改动、本次也未复制其违规写法 → 不报。

## `real-data-overflow`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: `required_states` 不含 overflow / long-copy / large-list，且无对应冻结 R5 行时记 `skipped`。
- legacy_id: L2

**真实数据溢出与截断**：长文案、长列表、空列表在真实（或声明的 fixture）数据下是否按声明换行、截断或滚动。
   - 关键字段溢出遮挡主操作或造成横向滚动 → **P0**。
   - 长文案撑破卡片 / 列表行但主路径仍可完成 → P1。
   - 空列表无结构变化且基线未要求空态 → 不报（空态声明属 restore / test）。

## `target-viewport-unbroken`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 无已冻结 R6 视口，或本次风险闭包未命中任何视口时记 `skipped`。
- legacy_id: L3

**目标视口不破**：仅在 R6 列出的视口上检查无横向滚动、无重叠、无内容截断。
   - 冻结视口出现横向滚动、重叠或关键内容截断 → **P0**。
   - 非冻结视口的「也应该适配」→ Open Question，不发明断点。
   - 只依据运行时几何 / DOM 事实；不要打开还原报告把同一条契约 RED 再报一遍。canonical_key 用 `route|viewport|现象`，不含 restore rule id。

## `alignment-and-grid`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及栅格、对齐或尺寸规则时记 `skipped`。
- legacy_id: L4

**对齐与栅格**：变更是否遵守已声明的栅格、对齐轴或尺寸规则。
   - 同排元素基线 / 间距错位可被几何事实证明，且基线或参照页给出过规则 → P1。
   - 无数值来源的「感觉没对齐」→ 不报。
   - 栅格计算式（`minmax(220px, 1fr)`）不是硬编码 token 问题，本格只看对齐结果。

## `interaction-state-style`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及 hover / focus / disabled / selected / loading 时记 `skipped`。
- legacy_id: L5

**交互状态样式**：真实交互下状态是否可区分、是否与冻结 R4 的**跨页/运行时**表现一致（单区块契约数值仍归 restore）。
   - 禁用 / 选中 / 焦点态无法区分导致误操作 → P1。
   - 仅缺 hover 且无冻结 R4 行 → P2。
   - 基线未要求的状态不发明。

## `scroll-and-fixed`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及 sticky / fixed / 内滚容器时记 `skipped`。
- legacy_id: L6

**滚动与固定元素**：吸顶、固钉、内滚容器在目标视口下是否遮挡关键操作或无法滚到目标内容。
   - 固定元素遮挡主按钮 / 表单提交 → P1。
   - 内滚容器无法到达声明内容 → P1。
   - 仅「吸顶时阴影不好看」且无功能后果 → 不报。
