---
api_version: review.codespec/v1
kind: Checklist
id: dev-frontend-self-test
title: 功能自测
order: 50
category: functional
inputs:
  - artifact: qa_baseline
    sections: ["F1-F4", "冻结豁免"]
    layer: qa_baseline
  - artifact: browser_evidence
    sections: ["全文"]
    layer: browser_evidence
  - artifact: quality_gate
    sections: ["全文"]
    layer: quality_gate
  - artifact: demand2_baseline
    sections: ["起点失败集合"]
    layer: demand2_baseline
---

# 功能自测

只跑验证组合分配的 F/REG。先对账 F1，再实跑 F2–F4 与 REG。coverage 的 `dimension` 用基线行号（如 `F2-1`），本清单条目是检查类，不是行号本身。

## `ac-test-layer-mapping`

- normative_level: MUST
- default_severity: P1
- max_severity: P1
- skip_when: 验证组合未分配任何 F1 行时记 `skipped`。
- legacy_id: F1

**AC ↔ 测试层级映射**：每条已分配 AC 是否写明最小测试层级，以及该层级为什么能观察结果；声明的层级是否真有对应测试或等价证据。
   - 声明了 L4 / L3（或仓内等价的组件 / 集成层）却查无对应测试 → P1。
   - F1 与 F2 复制同一句话、没有层级信息 → P1。
   - 未分配的 AC 不补映射。

## `ac-observable-assertion`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 验证组合未分配任何 F2 行时记 `skipped`。
- legacy_id: F2

**每条 AC 的可观察判定**：Given / When / Then、页面或状态、成功与失败结果是否在真实运行时可判定。
   - 按冻结步骤执行后成功结果不成立 → **P0**。
   - 失败结果与声明不符（该失败却成功、该成功却失败）→ **P0**。
   - 跑不了（驱动、账号、fixture）→ `unrun` + `known_gaps`，声明保持未验证，不伪造 clear。

## `required-exception-branches`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 验证组合未分配任何 F3 行时记 `skipped`。
- legacy_id: F3

**必测异常与边界**：只跑基线或风险实际列出的错误、空值、超时、重复操作等分支。
   - 已冻结 F3 行在界面或请求结果上不成立 → **P0**。
   - 未列入 F3 的分支不发明、不因「通常还应该测 403」补报。
   - 命中 `EX-n` 的分支 → `skipped` 并留痕。

## `data-api-contract`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 验证组合未分配任何 F4 行时记 `skipped`。
- legacy_id: F4

**数据与接口契约**：受影响方法、URL、字段、状态码、权限或副作用是否与冻结 F4 一致。
   - 请求头、字段映射或错误码与冻结契约不符 → **P0**。
   - 未受影响的接口不扫全量契约。
   - 外部接口不可用 → Deferred 候选，写解除条件，不计已验收。

## `existing-main-path-regression`

- normative_level: MUST
- default_severity: P1
- max_severity: P0
- skip_when: 验证组合未选 `regression` / 未分配 REG 行时记 `skipped`。
- legacy_id: REG

**既有主路径回归**：只比较验证组合明确选中的风险闭包；判据是 `DEMAND-2` 起点失败集合。
   - 相对可比起点新增失败 → **P0**。
   - 没有可比起点 → 不得声称「无回归」；`unrun` + `known_gaps`。
   - 起点已失败、本次未变差 → 不作为本 Story 新增回归。
