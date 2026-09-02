---
api_version: review.codespec/v1
kind: Checklist
id: dev-frontend-convention
title: 代码规范
order: 30
category: convention
inputs:
  - artifact: code_diff
    sections: ["全文"]
    layer: code_diff
  - artifact: code_rules
    sections: ["全文"]
    layer: code_rules
  - artifact: qa_baseline
    sections: ["冻结声明", "冻结豁免"]
    layer: qa_baseline
cell: CODE-CONVENTION
task_statement: 代码变更是否遵守工程依据选中的 PATTERN-* / REQ-DEC-*；无基准不判违规；命中冻结声明或 EX-n 时按正向/反向规则定级。
max_findings: 16
forbidden_reads:
  - other_role_findings
  - full_repo_code
---

# 代码规范

只检 diff 实际触碰、且工程依据已选 `PATTERN-*` 的维度。找不到对应 PATTERN 时该条 `skipped` 或只记 Open Question，不升 P0/P1。

硬编码、检查抑制、裸请求、调试残留**不按类型自动升级**。只有证伪冻结声明或产生确证错误结果时才升到 `max_severity`。

## 格子边界

本格占 `CODE-CONVENTION`。现象归属见 [SKILL.md 的现象归属表](../SKILL.md#现象归属)。

**基准是工程依据选中的 `PATTERN-*` / `REQ-DEC-*`。** 结论必须能被验证对错：每条 Finding 引用范式 ID 与文件行号。升 P0/P1 还要引用被证伪的冻结 R/F 行。

与仓内公共能力 `PATTERN-*` 语义等价的重复实现在本格报（`shared-capability-reuse`），不在 quality-lens 报。无 `PATTERN-*` 覆盖的局部重复、复杂度、状态、副作用属 quality-lens。

栈内信号见 [stack-signals.md](../references/stack-signals.md)；只在 PATTERN 未覆盖且需要识别栈内表现时读对应小节。

## 禁止

- 不把通用最佳实践冒充仓库规范。
- 不把 `PATTERN-*` 套到其「适用场景」未覆盖的文件（例如组件范式不约束 `src/lib/` 工具函数）。
- 仓内无对应机制时该维度 `skipped`（例如无 i18n 机制），不建议「引入一套」。
- 命中 `EX-n` 的偏差任何级别都不报，但必须留痕——沉默无法区分「核过豁免」与「没看见那一行」。
- 仓内历史违规、本 Story 未改动也未复制进新文件 → 不报。
- 同类违规分散在多个目录时必须穷尽，找到一处不收敛。
- 无证据不得判 P0。

## `directory-file-naming`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及新增/重命名文件或跨目录导入时记 `skipped`。
- legacy_id: C1

**目录与文件命名**：文件名、目录、导入别名是否符合所选组件/目录 `PATTERN-*`。
   - 业务面板 / 组件文件名大小写或与导出组件名不一致 → P2。
   - 跨目录导入不走仓内约定别名（如 `@/`）→ P2。
   - 适用场景不覆盖的路径（工具函数目录）套用组件命名 PATTERN → 不报（编造基准）。

## `component-paradigm`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及新增/变更组件或特性面板时记 `skipped`。
- legacy_id: C2

**组件写法范式**：导出形式、props 类型位置、组件声明方式是否与所选 `PATTERN-*` 不变量一致。
   - 违反明文不变量（如禁止 `React.FC`、禁止默认导出、props 必须导出 `interface <Name>Props`）→ P2。
   - 把组件范式套到非组件文件 → 不报。
   - 无 PATTERN 覆盖的写法差异 → Open Question 或不记，不升 P1。

## `style-token-scheme`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P0
- skip_when: diff 不涉及样式 / token 时记 `skipped`。
- legacy_id: C3

**样式方案与 token**：是否走仓内既有方案；颜色、间距、字号、行高、圆角、层级是否引用 scale。硬编码信号见 [stack-signals.md](../references/stack-signals.md)「样式方案」。
   - 有对应 token / scale 仍写字面量（`#hex` / `px` / Tailwind 任意值）→ P2。
   - 同一硬编码证伪冻结 token / 视觉声明 → P1；造成主题或对比度错误结果 → **P0**。
   - 仓内无对应 token（如无阴影 token）→ P2 + Open Question「是否补 token」，**不得**升 P0/P1。
   - **排除**：`1px` 描边、栅格计算式（`minmax()` / `repeat()` 里的轨道宽）不当硬编码报。
   - 穷尽：同类硬编码出现在多个文件时每一处都报，找到一处不收敛。

## `request-and-error-handling`

- normative_level: MUST
- default_severity: P2
- max_severity: P0
- skip_when: diff 不涉及请求、错误映射或异步取消时记 `skipped`。
- legacy_id: C4

**请求与错误处理**：是否走仓内唯一请求出口与错误码映射；是否按异步 PATTERN 取消。
   - 裸 `fetch` / 裸 `axios` / 底层 HTTP 绕过封装 → 默认 P2。
   - 因此缺少鉴权头、租户头或错误码映射，证伪冻结 F4 → **P0**。
   - `catch` 吞错导致冻结错误态永不渲染（F3 不成立）→ **P0**。
   - 未建 `AbortController` / 等价取消，且无基线行覆盖取消 → P2，不升。

## `shared-capability-reuse`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P0
- skip_when: diff 不涉及展示口径、格式化、公共 hooks 或可复用组件时记 `skipped`。
- legacy_id: C5

**公共能力复用**：是否复用工程依据选中的公共方法 / hooks / 组件，而不是语义等价的再实现。
   - 与所选 `PATTERN-*` 语义等价（同单位、同空值口径）可直接替换 → P2。
   - 再实现使冻结展示声明不成立（如非有限数显示 `NaN` 而非 `--`）→ **P0**。
   - 历史文件里的同类违规未被本 Story 复制 → 不报；复制进新文件的报新的那份。
   - 命中 `EX-n` 的展示偏差 → `skipped` 并留痕，任何级别都不报。

## `typing-and-suppression`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P1
- skip_when: diff 不涉及类型声明或检查抑制时记 `skipped`。
- legacy_id: C6

**类型定义与检查抑制**：类型来源是否符合 PATTERN；`any` / `@ts-ignore` / `@ts-expect-error` / `eslint-disable` 是否有理由。
   - `@ts-ignore` 或无理由 `eslint-disable` / `any` → P2。
   - 抑制遮蔽了已选 typecheck/lint 失败或冻结声明 → P1。
   - `@ts-expect-error` 且同行/上一行有 PATTERN 认可的理由 → 可报 P2 或不报；报成 P0/P1 算越级。

## `i18n-copy-mechanism`

- normative_level: SHOULD
- default_severity: P2
- max_severity: P2
- skip_when: 仓内无国际化或文案集中管理 `PATTERN-*` 时记 `skipped`（写明「不适用」，不建议引入）。
- legacy_id: C7

**国际化与文案机制**：新增用户可见文案是否走仓内既有机制。
   - 有 i18n PATTERN 却硬编码用户可见文案 → P2。
   - 无机制时中文字面量 → 不报。
