---
name: 切片计划
description: 基于 analysis-spec.md 把需求切成最小可交付 slices，每个 slice 包含目标行为、受影响文件、风险、验证方式和回滚边界，产出 slice-plan.md。
---

# 切片计划

## 概述

这个 skill 把 `analysis-spec.md` 中的目标行为和风险清单，收敛成一组最小可交付切片。

每个切片必须：

- 可独立验证
- 可独立评审
- 可独立回滚

它在 `analysis-spec` 之后执行，在实现与验证之前执行。

## 硬门禁

1. **没有 analysis-spec 不准切片。** 没有分析包就无法判断切片是否完整。
2. **每个 slice 必须有回滚边界。** 说不清怎么回滚的不算合格切片。
3. **每个 slice 必须引用 TargetBehavior 编号。** 无法追溯到分析包的切片是孤立任务。
4. **不要把"全部做完才能验证"写成一个 slice。** 如果切不开，说明分析包不够细，应回到 `analysis-spec`。
5. **不要在切片中做技术选型决策。** 切片只划定边界和验证方式，实现细节在开发阶段决定。

## 何时使用

适用场景：

- `analysis-spec` 已完成且退出门禁已通过
- 需要把分析包转化为可执行的开发计划
- 需要为多 slice 需求划定交付顺序和验证边界

不适用场景：

- 还没有 analysis-spec（先用 `analysis-spec`）
- 当前是事故排查（用 `immune-debug`）
- 已经有清晰的切片，只需要做验证（直接进入实现阶段）

## 前置条件

- `analysis-spec.md` 已产出
- TargetBehaviors、RiskInventory、EvidencePlan 已定义

## 工作流

### Phase 0：读取分析包

读取 `analysis-spec.md`，重点确认：

- TargetBehaviors 列表及编号
- RiskInventory 中的高风险项
- EvidencePlan 中的验证方式约束
- NonGoals（确保切片不越界）
- 🟡 Accepted 项（切片时需要为这些假设预留验证或回滚空间）

### Phase 1：划定切片

按以下原则切片：

- **按用户路径和页面状态切**，不按技术层切。先切行为边界，再考虑文件边界。
- **先做兼容缝，再做行为改动。** 迁移类需求优先切出 compatibility slice（adapter / flag / fallback）。
- **高风险改动单独成 slice。** 不要把高风险改动和低风险改动混在一个 slice 里。
- **共享层改动单独成 slice。** 改共享组件 / hooks / 状态的 slice 不要同时改业务逻辑。

每个 slice 至少包含：

| 字段 | 说明 |
| --- | --- |
| slice id | 唯一标识，如 S-1、S-2 |
| 目标行为 | 这个 slice 完成后用户能看到什么 |
| 引用 TB | 对应 analysis-spec 的 TargetBehavior 编号 |
| 受影响文件 / 模块 | 预期改动范围 |
| 风险 | 这个 slice 最可能出问题的地方 |
| 验证方式 | 怎么证明这个 slice 做对了 |
| 回滚方式 | 如果出问题怎么退回去 |

### Phase 2：确定执行顺序

考虑因素：

- 依赖关系：如果 S-2 依赖 S-1 的输出，S-1 必须先做
- 风险前置：高风险 slice 尽量前置，早验证早发现
- 兼容优先：compatibility slice 必须在行为变更 slice 之前

产出排序后的切片列表和依赖关系说明。

### Phase 3：标记延后项

对 analysis-spec 中 deferred 或 🟡 Accepted 的条目：

- 如果本轮不做，显式标记为 `deferred`，说明原因
- 如果本轮做但有风险，在对应 slice 的风险栏中标注

### Phase 4：按工作模式补充策略

| 模式 | 额外要求 |
| --- | --- |
| `patch-lite` | 通常只有 1 个 slice，可压缩格式 |
| `feature-slice` | 正常切片，每个 slice 都要验证方式和回滚 |
| `migration-strict` | 必须有 compatibility slice、feature flag / fallback 策略、staged rollout 计划 |

> **什么是 compatibility slice？**
> 在改动行为之前，先切一个只做兼容层的 slice——比如加 adapter、加 feature flag、加 fallback。这个 slice 上线后旧行为不变，但新代码路径已就绪。后续 slice 才真正切换行为，出问题可以通过 flag 回退到旧路径。

退出门禁：

- 每个 slice 能单独验证
- 没有"必须全部完成才知道对不对"的巨型任务
- 高风险改造有 compatibility slice 或 feature flag slice
- 每个 slice 的回滚方式已明确
- 切片总和覆盖了所有非 deferred 的 TargetBehaviors

## 降级模式

如果 analysis-spec 不完整：

- 标注哪些 TargetBehavior 缺少细节
- 对缺少细节的切片标记为 `tentative`
- 建议回到 `analysis-spec` 补充后再确认

## 最终输出

结束时必须包含：

### 切片摘要

- 总共几个 slices
- 执行顺序
- 关键依赖关系
- deferred 的 TargetBehaviors

### 产出文件

- `slice-plan.md` 路径
- 如有 per-slice 的 `plan.md`，列出路径

### 下一步

- 按 slice 顺序进入开发和验证
- 每个 slice 完成实现与验证后，产出 `verify.md` 作为 `spec-check` 的输入
- 如果切片过程中发现 analysis-spec 有缺口，建议先补分析再继续

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `slice-plan.md` | `docs/specs/<topic>/slice-plan.md` |
| per-slice plan（可选） | `docs/specs/<topic>/slices/<slice-id>/plan.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。所有属于同一需求的工件统一归入 `docs/specs/<topic>/`。
