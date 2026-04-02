---
name: code-review
description: 在实现完成后、行为验证之前，基于累积的 review rules 对改动代码做结构化检视。rules 由 initialize（仓库级）、design-pack（需求级）、immune-debug（防御级）分布式生成。产出 code-review.md。
---

# 代码检视

## 概述

这个 skill 在实现完成后、`verify`（行为验证）之前，对改动代码做结构化检视。

`verify` 看"行为对不对"——TC 通过了没有、verify pack 过线了没有。`code-review` 看"代码写得好不好"——命名是否符合领域模型、架构约束是否被遵守、已知反模式是否被避免。

检视标准不是凭感觉，而是基于一组累积的 **review rules**。这些 rules 在工作流的不同阶段被生成和补充：

| 层级 | 生成方 | 内容 | 生命周期 |
| --- | --- | --- | --- |
| 仓库级 | `initialize` | 命名规范、目录结构、导入规则、通用编码标准、设计系统用法 | 长期，随 `sync-context` 演进 |
| 需求级 | `design-pack` Phase 3 | 领域命名（统一语言）、架构约束（ADR 派生）、API 契约规范、组件边界 | 随需求存在，实现期有效 |
| 防御级 | `immune-debug` | 踩过的坑 → 反模式规则、已知陷阱 → 检查项 | 长期累积，每次事故后追加 |

## 交互规范

遵守 [Skill-User 交互黄金原则](../../PRINCIPLES.md)。

| Phase | 用户可见内容 | 结束方式 |
| --- | --- | --- |
| 0 — 收集 Rules | 内联进 Phase 1，不单独输出（P6） | — |
| 1 — 逐文件检视 | Issue 汇总表（blocking / suggestion） + 按文件明细 | 无确认门 |
| 最终 | 三行索引（P5） | — |

---

## 硬门禁

1. **没有 rules 不准检视。** 至少要有仓库级 base rules 或 design-pack 产出的需求级 rules。没有标准的检视是主观评价，不是结构化检视。
2. **blocking issue 未清零不进入 verify。** blocking 级别的问题必须修正后才能进入行为验证。
3. **不要在 code-review 中做行为验证。** TC 通过与否是 `verify` 的事，这里只看代码质量。
4. **不要在 code-review 中做技术选型。** 技术决策在 `design-pack` Phase 3 已锁定，这里只检查是否遵守。

## 何时使用

适用场景：

- 一个或多个 slice 的实现已完成
- 需要在进入 `verify` 前检视代码质量
- 已有可用的 review rules（仓库级 / 需求级 / 防御级，至少一种）

不适用场景：

- 还没有开始实现（先写代码）
- 还没有 slice-plan（先用 `slice-plan`）
- 已经在做行为验证（那是 `verify` 的事）
- `patch-lite` 模式下可压缩（见工作模式适配）

## 前置条件

- `slice-plan.md` 已产出
- 对应 slice 的实现已完成
- 至少有一种 review rules 可用：
  - `.project-context/review-rules/base.md`（仓库级）
  - `.project-context/review-rules/<topic>.md`（需求级）
  - `.project-context/review-rules/defensive.md`（防御级）
  - 或 `design-pack.md` 中的 Review Rules 章节

## 工作流

### Phase 0 — 收集 Rules

读取所有可用的 review rules：

1. `.project-context/review-rules/` 下所有 `.md` 文件
2. `design-pack.md` 中的 `## Review Rules` 章节（如果存在）
3. `slice-plan.md` 中当前 slice 的受影响文件/模块范围

将 rules 合并为一份检视清单。如果同一条规则在多个来源中重复，去重。

确认检视范围：哪些文件是当前 slice 改动的。

### Phase 1 — 逐文件检视

对 slice 涉及的每个改动文件，按 rules 逐条检查：

**检视维度**（按 rule 来源组织）：

仓库级 rules：
- 命名规范（变量、函数、组件、文件名）
- 目录结构（文件放对了位置没有）
- 导入规则（循环依赖、层级违反）
- 通用编码标准（错误处理、类型安全、日志规范）

需求级 rules（来自 design-pack）：
- 领域命名一致性（代码中的术语是否与 Phase 2 统一语言表一致）
- 架构约束遵守（ADR 中的决策是否被正确实现）
- API 契约符合度（接口签名、请求响应结构是否与 Phase 3 契约一致）
- 组件边界（是否越界访问了不该直接依赖的模块）

防御级 rules（来自 immune-debug）：
- 已知反模式是否被避免
- 历史踩坑点是否有防护
- 高危操作是否有安全措施

对每个文件，每条 rule 产出判定：

| 判定 | 含义 |
| --- | --- |
| `pass` | 符合规则 |
| `n/a` | 规则不适用于该文件 |
| `issue:blocking` | 违反规则，必须修正 |
| `issue:suggestion` | 不违反硬规则，但建议优化 |

### Phase 2 — 汇总报告

产出 `code-review.md`：

```markdown
# Code Review: <topic> / <slice-id>

## 检视范围

- 改动文件数：N
- 应用 rules 数：N（仓库级: N, 需求级: N, 防御级: N）

## Issue 汇总

### Blocking

| # | 文件 | Rule | 问题描述 | 建议修正 |
| --- | --- | --- | --- | --- |
| 1 | src/orders/useOrders.ts | 领域命名 | `fetchAll` 应为 `fetchPage`（统一语言） | 重命名函数 |

### Suggestion

| # | 文件 | Rule | 建议 |
| --- | --- | --- | --- |
| 1 | src/orders/OrderList.tsx | 错误处理 | 建议增加 retry 逻辑的指数退避 |

## 按文件明细

### src/orders/useOrders.ts

| Rule | 判定 | 说明 |
| --- | --- | --- |
| 命名规范 | pass | |
| 领域命名 | issue:blocking | `fetchAll` 应为 `fetchPage` |
| 架构约束 | pass | |
| ... | ... | ... |

## 统计

- 总检查项：N
- pass: N
- n/a: N
- blocking: N
- suggestion: N
```

退出门禁：

- 所有改动文件已检视
- blocking issue 数量已确认
- 如果有 blocking issue，标注为"需要修正后重新检视"

## 工作模式适配

| 模式 | 要求 |
| --- | --- |
| `patch-lite` | 可压缩：只做仓库级 rules 快速检查，跳过需求级（因为没有 design-pack）。如果防御级 rules 命中则仍需检查 |
| `feature-slice` | 完整检视：仓库级 + 需求级 + 防御级 |
| `migration-strict` | 完整检视 + 额外关注：兼容层代码审查、双写逻辑、feature flag 实现、回滚路径代码 |

## 与 verify 的边界

- `code-review` 看**代码质量**：命名、结构、架构遵守、反模式
- `verify` 看**行为正确性**：TC 是否通过、verify pack 是否过线、spec 是否偏离

两者都是 `spec-check` 之前的门禁，但检视的维度不同。`code-review` 在前（先保证代码质量），`verify` 在后（再验证行为正确性）。

## 降级模式

如果没有任何 review rules：

- 标注"无可用 review rules"
- 建议先用 `initialize` 建立 base rules，或手动创建 `.project-context/review-rules/base.md`
- 不做主观检视，而是跳过并在 `verify` 阶段标注"code-review 已跳过（无 rules）"

如果只有部分 rules：

- 用已有的 rules 做检视
- 标注缺少哪些层级的 rules
- 建议后续补全

## 最终输出

```
✓ code-review 完成
产出：docs/specs/<topic>/slices/<slice-id>/code-review.md
下一步：[无 blocking → 进入 verify / 有 N 个 blocking → 修正后重新检视]
```

---

## Review Rules 存储

所有 review rules 累积存放在 `.project-context/review-rules/`：

```
.project-context/review-rules/
├── base.md              ← initialize 生成（仓库级）
├── <topic>.md           ← design-pack 生成（需求级，per-topic）
└── defensive.md         ← immune-debug 追加（防御级）
```

### 自定义与扩展

- **手动新增**：直接在 `.project-context/review-rules/` 下创建 `.md` 文件，Phase 0 会自动扫描
- **格式**：每个 rule 文件包含一组检查项，每项有"规则描述"和"检查方式"
- **命名**：仓库级用 `base.md`，需求级用 topic 名（如 `order-pagination.md`），防御级用 `defensive.md`

格式模板见 [references/review-rules-template.md](references/review-rules-template.md)。

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `code-review.md` | `docs/specs/<topic>/slices/<slice-id>/code-review.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。
