---
api_version: review.codespec/v1
kind: Checklist
id: dev-frontend-quality
title: 工程质量
order: 40
category: code-quality
inputs:
  - artifact: code_diff
    sections: ["全文"]
    layer: code_diff
  - artifact: qa_baseline
    sections: ["F3", "冻结豁免"]
    layer: qa_baseline
  - artifact: code_rules
    sections: ["全文"]
    layer: code_rules
---

# 工程质量

只检风险实际命中的 Q 项。每条结论必须带可观察后果。栈内表现见 [stack-signals.md](../references/stack-signals.md)。

## `component-responsibility-size`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: 无新增非平凡组件、也未显著扩大既有职责时记 `skipped`。
- legacy_id: Q1

**组件职责与体积**：新增 / 变更组件是否承担过多不相干职责。
   - 同时承担三类及以上（状态编排、业务规则、呈现；取数另计）→ P2。命中阈值**必须出现在结论里**，判「超了但合理，理由是…」也算覆盖；写「无发现」才算漏检。
   - God 组件继续膨胀且无法指出内聚边界 → P1。

## `duplicated-code`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P2
- skip_when: 未引入新重复、也未改 `shared-boundary` 时记 `skipped`。
- legacy_id: Q2

**重复代码**：本次 diff 是否引入可抽取的重复。
   - 两处以上独立实现且无 `PATTERN-*` 覆盖 → P2。
   - 与所选公共能力 `PATTERN-*` 语义等价 → **不在本格报**，属 convention `shared-capability-reuse`。提及须标注「可能与规范检视重叠」。

## `complexity-and-nesting`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P2
- skip_when: diff 未新增复杂分支 / 循环时记 `skipped`。
- legacy_id: Q3

**复杂度与嵌套**：条件嵌套、分支数、三元嵌套、模板内联条件是否超出参考线。
   - 条件嵌套 >4 层（含防御性 `isFinite` / 早退）→ P2。
   - 单函数分支 >10 条、三元嵌套 >2 层、模板内联条件 >3 层 → P2。
   - 未超线 → `clear`，不要为「有点复杂」凑 Finding。

## `state-placement`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: 未新增共享、派生或跨页状态时记 `skipped`。
- legacy_id: Q4

**状态放置**：状态是否放在正确的一层；可推导值是否被重复存储。
   - 可从已有状态算出的值另存一份并用副作用同步 → P2。
   - 服务端数据与本地 UI 状态混在同一容器且造成错误写入 → P1。
   - 「更新后有一帧不一致」**不得**升 P0/P1：次帧闪烁不是确证的功能缺陷。

## `side-effect-management`

- normative_level: MUST
- default_severity: P2
- max_severity: P0
- skip_when: 无 `async-state` / `write` / 订阅 / 计时器时记 `skipped`。
- legacy_id: Q5

**副作用管理**：订阅、定时器、监听、请求取消是否清理；并发是否会旧响应覆盖新响应。
   - 能给出触发序列（例如先选慢区再切快区）且界面与所选条件不一致 → **P0**。
   - 泄漏 / 无限循环（effect 写自己的依赖）可复现 → **P0**。
   - 仅「没写 AbortController」而无覆盖后果 → P2，不升。缺取消可作为竞态根因的附注，不单开一条 P0。

## `error-boundary-handling`

- normative_level: MUST
- default_severity: P2
- max_severity: P0
- skip_when: 无 `auth` / `write`、也无已列 F3 声明时记 `skipped`。
- legacy_id: Q6

**错误与边界处理**：已冻结的异常 / 空态 / 权限分支是否有对应 UI 或错误路径。
   - 冻结 F3/F4 声明的空态、错误态、权限态未处理 → **P0**。
   - 基线未列出的分支不发明（例如未声明的 403 行）。
   - 请求封装已统一映射的错误码，本 Story 未引入新缺口 → 不报。

## `dead-code-leftovers`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P2
- skip_when: 无新增代码时记 `skipped`。
- legacy_id: Q7

**死代码与遗留**：调试输出、断点、临时视觉标记、占位实现。
   - `console.log` / 红框 / `TODO` 空实现 / 写死样例顶替真实取数 → P2。
   - 未证明违反冻结声明或产生错误结果时**不得**升 P0/P1。

## `obvious-performance`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: 无 `performance` 触发、也无列表规模 / 昂贵计算变更时记 `skipped`。
- legacy_id: Q8

**明显性能问题**：渲染路径上的无缓存重计算、不稳定 list key、大列表未虚拟化、高频事件未防抖。
   - 规格或任务给出的量级超过虚拟化参考线（200 条同时渲染）仍全量渲染 → P2。
   - 每次渲染新建数组并排序 / 重计算，且有量级依据 → P2；与「未虚拟化」是两条，找到大的之后仍要报小的。
   - 模块级常量、不在渲染路径内的分配 → 不报。
   - 无量级、无 AC 性能目标、只有「可能会慢」→ 不报。
