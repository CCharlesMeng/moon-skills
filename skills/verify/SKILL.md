---
name: verify
description: 在实现完成后，按领域 verify pack 逐项收集证据、标记状态、检测 spec 偏差，产出 verify.md。这是 spec-check 的前置门禁。
---

# 领域验证

## 概述

这个 skill 在实现完成后做一件事：按领域检查清单（verify pack）逐项收集证据，判定每个测试规格是否通过。

它是实现阶段和 `spec-check` 之间的证据收口器。没有通过 `verify`，不允许进入 `spec-check`。

它不做规格对账（那是 `spec-check` 的事），也不做 reflect（那是 `audit` 的事）。它只回答一个问题：**证据够不够，质量过不过线**。

## 硬门禁

1. **没有证据不能标 pass。** 每个必做 TC 必须挂到一条 EV（测试结果、截图、日志、录屏、请求记录），没有 EV 的 TC 只能标 `deferred` 或 `failed`。
2. **不能在 verify 阶段静默吸收 spec 偏差。** 如果实现偏离了 TB 或 AC，必须显式输出 spec deviation，交回上游修正。
3. **deferred 必须附原因和风险。** 不允许空白 defer。
4. **没有通过 verify，不能进入 spec-check。** 这是退出门禁，不是建议。

## 何时使用

适用场景：

- 一个或多个 slice 的实现已完成
- 需要在进入 spec-check 前收集验证证据
- 需要按领域标准逐项检查交付质量

不适用场景：

- 还没有 slice-plan（先用 `slice-plan`）
- 还没有开始实现（先写代码/写测试）
- 需要做 spec 对账（用 `spec-check`）
- 需要做交付 reflect（用 `audit`）

## 前置条件

- `slice-plan.md` 已产出
- `design-pack.md` 已产出（如果当前需求触发了 design-pack）
- 对应 slice 的实现和测试已完成

## 工作流

### Phase 0：读取输入

读取：

- `slice-plan.md` — 本次要验证哪些 slice
- `design-pack.md` — 获取 AC 和 TC 列表（如果存在）
- `analysis-spec.md` — 获取 TB 列表
- 按需加载对应的 verify pack（见 `references/`）

确定本次验证范围：哪些 slice、哪些 TC、哪些 verify pack 检查项。

### Phase 1：收集证据

对每个 slice，逐项收集：

> 如果不存在 `design-pack.md`（如 `patch-lite`），跳过下方 TC 证据部分，仅执行 Verify pack 检查项。

**TC 证据**（来自 design-pack 的 Test Pack）：

对每个 TC，记录：

| 字段 | 说明 |
| --- | --- |
| TC 编号 | 引用 design-pack 中的 `TC-*` |
| 状态 | `pass` / `n/a` / `deferred` / `failed` |
| EV | 证据描述（测试输出、截图路径、日志片段、人工验证记录） |
| 说明 | 仅 `deferred` 和 `failed` 时必填：原因、风险、后续计划 |

**Verify pack 检查项**（来自对应领域 verify pack）：

对每个检查项，记录：

| 字段 | 说明 |
| --- | --- |
| 检查项 | verify pack 中的条目 |
| 状态 | `pass` / `n/a` / `deferred` |
| 证据 | 支持判定的依据 |
| 说明 | 仅 `deferred` 时必填 |

### Phase 2：检测 spec 偏差

在收集证据的过程中，主动检查：

- 实现结果是否偏离了 TB 定义的目标行为
- 实现结果是否偏离了 AC 定义的验收标准
- 是否有 slice-plan 预期范围之外的改动

如果发现偏差，记录到 `Spec Deviations` 区域，标注：

| 字段 | 说明 |
| --- | --- |
| 偏差描述 | 实际行为 vs 预期行为 |
| 影响的 TB/AC | 引用编号 |
| 严重度 | `blocking`（必须修正才能继续）/ `notable`（需要上游确认） |
| 建议 | 回到 analysis-spec / 回到 design-pack / 就地修正 |

### Phase 3：输出 Replan Recommendation

如果出现以下情况，必须给出明确的 replan 建议：

- 任何 `blocking` 级别的 spec deviation
- 同一 slice 连续 3 轮 TC 失败
- 多个 TC 失败指向同一个根因，且根因不在当前 slice 范围内

Replan 方向：

- 根因是目标不清 → 回到 `analysis-spec`
- 根因是方案不对 → 回到 `design-pack`
- 根因是切片粒度问题 → 回到 `slice-plan`

### Phase 4：产出 verify.md

```markdown
# Verify: <topic> / <slice-id>

## Evidence Ledger

| TC # | AC # | 状态 | EV | 说明 |
| --- | --- | --- | --- | --- |
| TC-1.1 | AC-1.1 | pass / n/a / deferred / failed | ... | ... |

## Verify Pack Results

### <verify-pack-name>

| 检查项 | 状态 | 证据 | 说明 |
| --- | --- | --- | --- |

## Spec Deviations

| 偏差 | 影响 TB/AC | 严重度 | 建议 |
| --- | --- | --- | --- |
<!-- 无偏差时写"无" -->

## Open Risks

## Replan Recommendation
<!-- 无需 replan 时写"无" -->

## 统计

- TC pass: N
- TC failed: N
- TC deferred: N
- TC n/a: N
- Verify pack pass: N
- Verify pack deferred: N
- Spec deviations: N (blocking: N, notable: N)
```

退出门禁：

- 所有必做 TC 有状态和 EV
- 所有 deferred 有原因和风险
- 所有 spec deviations 有处置建议
- 无 blocking 级别偏差未处理

## 工作模式适配

| 模式 | 要求 |
| --- | --- |
| `patch-lite` | 可压缩格式，但不可跳过；允许人工验证作为 EV，但必须说明理由 |
| `feature-slice` | 完整 TC 验证 + 至少一个领域 verify pack |
| `migration-strict` | 完整 TC 验证 + `integration-verify-pack` 必做 + 回滚/兼容证据必做 |

### 按工作模式的最小证据

| 模式 | 最小验证证据 |
| --- | --- |
| `patch-lite` | 前后截图、关键交互人工验证、控制台无新增报错、一个最关键回归点 |
| `feature-slice` | 截图 / 录屏、状态矩阵验证、控制台与网络检查、目标断点、埋点与错误处理 |
| `migration-strict` | feature-slice 全部 + 兼容边界记录 + flag / 回滚路径 + 共享行为回归 + 性能对比 |

## 与 spec-check 的边界

- `verify` 看"证据是否足够、领域质量是否过线"
- `spec-check` 看"承诺是否兑现、有没有偏离 spec"

verify 的 spec deviation 检测是辅助发现，不是最终裁定。最终的承诺对账由 spec-check 完成。

## 最终输出

结束时必须包含：

### 验证摘要

- 验证了哪些 slice
- TC 通过率
- spec deviation 数量和严重度
- 是否需要 replan

### 产出文件

- `verify.md` 路径

### 下一步

- 无 blocking 偏差 → 进入 `spec-check`
- 有 blocking 偏差 → 根据 replan recommendation 回到对应上游 skill
- 有大量 deferred → 建议在 spec-check 中重点标注

---

## Verify Pack 自定义与扩展

内置三个 verify pack 在 `references/` 下：`frontend-verify-pack.md` / `backend-verify-pack.md` / `integration-verify-pack.md`。

项目可在仓库的 `.project-context/verify-packs/` 目录下自定义：

- **覆盖默认**：复制 `references/` 下的同名文件到 `.project-context/verify-packs/`，修改内容。同名文件优先使用仓库版本。
- **新增领域**：在 `.project-context/verify-packs/` 下新建 `.md` 文件，Phase 0 自动扫描并作为可选 verify pack。

> 此机制与 `analysis-spec` 的 `.project-context/lenses/` 对称——lenses 守护分析阶段的问题覆盖，verify packs 守护验证阶段的证据覆盖。

**优先级**：`.project-context/verify-packs/` > `references/`（同名覆盖）。

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `verify.md` | `docs/specs/<topic>/slices/<slice-id>/verify.md` |
| 整轮汇总（可选） | `docs/specs/<topic>/verify-summary.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。
