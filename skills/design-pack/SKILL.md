---
name: design-pack
description: 在 analysis-spec 之后、slice-plan 之前，产出设计方案、验收标准（AC）、测试规格（TC）和关键架构决策（ADR），作为实现和验证的唯一契约来源。
---

# 设计与验收包

## 概述

这个 skill 把 analysis-spec 中的目标行为（TB）转化为可实施、可验收、可验证的设计契约。

它是 AC、TC、ADR 的唯一归属地。analysis-spec 不写 AC，slice-plan 不写 TC，domain-verify 不定义标准——它们只消费 design-pack 的产出。

## 硬门禁

1. **没有 analysis-spec 不准设计。** 没有稳定的 TB，设计的是空气。
2. **每个 AC 必须映射到 TB。** 无法追溯到目标行为的验收标准是悬空承诺。
3. **每个 TC 必须映射到 AC。** 无法追溯到验收标准的测试是无效劳动。
4. **不要在 design-pack 中做实现。** 这里只定义契约和边界，不写代码。
5. **ADR 只记录非显而易见的决策。** 不要把显然的选择写成 ADR。

## 何时使用

### 触发矩阵

| 工作模式 | 默认行为 | 覆盖条件 |
| --- | --- | --- |
| `patch-lite` | 跳过 | 无 |
| `feature-slice` | 按需进入 | 以下任一命中即进入 |
| `migration-strict` | 必做 | 无 |

`feature-slice` 命中条件（任一成立）：

- API 或数据契约变化
- 共享组件 / 公共 hooks / 公共状态变化
- 异步流程 / 状态机 / 多边界联动
- 性能关键路径
- analysis-spec 的 RiskInventory 中有 `high` 级别风险

不适用场景：

- 还没有 analysis-spec（先用 `analysis-spec`）
- 当前是事故排查（用 `immune-debug`）
- 已经有清晰的设计，只需要切片（直接用 `slice-plan`）
- `patch-lite` 需求

## 前置条件

- `analysis-spec.md` 已产出，TargetBehaviors 已编号
- `.project-context/references.yaml` 可访问

## 工作流

### Phase A — Architecture Decisions

回答"用什么方案做"。

动作：

- 识别需要做设计决策的领域（API 契约、数据流、组件边界、兼容策略、性能策略）
- 先检查 `references.yaml` 中的已有模式（Reuse before add）
- 对每个非显而易见的决策，产出 ADR

ADR 最小结构：

```markdown
### ADR-<N>: <决策标题>

**背景**：为什么需要做这个决策
**选项**：考虑过哪些方案（至少两个）
**决定**：选了什么，为什么
**后果**：这个决定带来的约束和风险
**引用**：TB-<N>, Risk-<N>
```

只在以下情况产出 ADR：

- 共享层变更
- API / 数据契约变化
- 兼容层 / 迁移策略
- 性能关键路径
- 存在多种合理方案且取舍不显然

### Phase B — Contract Decisions

回答"边界在哪里"。

动作：

- 定义 API 契约（请求/响应结构、错误处理、版本化）
- 定义组件/模块公共 API 边界
- 对于 `migration-strict`：定义兼容层、双写策略、回填计划、回滚路径
- 标注每个契约：复用已有 / 扩展已有 / 新增

### Phase C — Acceptance Pack

回答"什么叫完成"。

对每个 TB，产出一组 AC。

AC 格式策略：

- **行为型验收**：默认使用 Given / When / Then

```markdown
**AC-1.1** (← TB-1)
Given 用户进入订单列表页
When 页面首次加载完成
Then 默认显示第一页 20 条数据，分页器显示总页数
```

- **非行为型验收**：保留为结构化检查项，不硬塞进 GWT

```markdown
**AC-2.3** (← TB-2) [权限矩阵]
- admin: 可编辑、可删除
- viewer: 只读
- guest: 不可见
```

适用于权限矩阵、性能阈值、埋点规格、可访问性要求、兼容性约束等。

规则：

- 每个 AC 必须引用至少一个 TB
- 🔴 项（未澄清的 TB）不允许产出 AC
- AC 总量与 TB 复杂度成正比，不要过度拆分

### Phase D — Test Pack

回答"怎么验证 AC"。

对每个 AC，产出一组 TC。

```markdown
**TC-1.1.1** (← AC-1.1)
层级: e2e
类型: happy-path
描述: 访问 /orders，断言列表项数量为 20，分页器可见

**TC-1.1.2** (← AC-1.1)
层级: unit
类型: boundary
描述: useOrders hook 传入 pageSize=20 时返回正确切片；传入 pageSize=0 时返回空数组
```

每个 TC 必须标注：

| 字段 | 值域 |
| --- | --- |
| 层级 | `unit` / `integration` / `e2e` / `manual` |
| 类型 | `happy-path` / `boundary` / `failure-path` / `adversarial` |

规则：

- 每个 AC 至少有一个 TC
- `manual` 层级的 TC 必须说明为什么不能自动化
- 高风险 TB 对应的 AC 应覆盖 `failure-path` 类型

### Phase E — Compatibility / Rollback Notes

仅 `migration-strict` 必做，`feature-slice` 按需。

- feature flag 策略
- 兼容层边界
- 回滚路径
- staged rollout 计划

退出门禁：

- 每个 TB 有至少一个 AC
- 每个 AC 有至少一个 TC
- 所有 ADR 有背景、选项、决定、后果
- `migration-strict` 的兼容/回滚策略已明确

## 降级模式

如果 analysis-spec 不完整：

- 标注哪些 TB 缺少细节
- 对缺少细节的 TB 不产出 AC，标记为 `blocked`
- 建议回到 `analysis-spec` 补充

如果跳过 design-pack（patch-lite）：

- slice-plan 可以直接从 TB 切片
- domain-verify 不要求 TC 证据，但仍需 verify pack 证据

## 最终输出

结束时必须包含：

### 设计摘要

- ADR 数量和关键决策
- AC 总数和覆盖的 TB
- TC 总数和层级分布
- 是否有兼容/回滚策略

### 产出文件

- `design-pack.md` 路径

### 下一步

- 进入 `slice-plan`，基于 TB / AC / TC 切片
- 如果 design-pack 过程中发现 analysis-spec 有缺口，建议先补分析再继续

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `design-pack.md` | `docs/specs/<topic>/design-pack.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。
