---
status: accepted
---

# 实现不外包给 subagent，subagent 只承担勘察与检视

把 SDD-Dev 的九项能力平铺成九个 subagent 是最直觉的做法，但 subagent 的价值是**隔离上下文**，不是**拆步骤**。还原与逻辑补全是需要累积上下文、连续走 6 步、逐条记账的主线；把它们塞进 subagent，主 agent 只能拿回一份摘要，后续的检视裁决和收口判断都会失准。因此我们决定由主 agent 亲自执行还原与逻辑补全，subagent 只承担两类天然只读、视角独立、可并行、产出结构化报告的工作：勘察（2 个）与检视（4 个）。

## Consequences

- 主 agent 的上下文压力集中在实现阶段。作用域因此限定为「一个前端仓 × 一个 Story 的 `tasks.md`」，跨仓与多 Story 交给外层调度。
- 若将来单 Story 的 Task 量大到主 agent 撑不住，正确的做法是收窄作用域或拆 Story，而不是把实现改成 subagent——那会重新引入本 ADR 要避免的上下文断裂。
