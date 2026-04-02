---
name: design-pack
description: 在 analysis-spec 之后、slice-plan 之前，通过 5 个渐进式 Phase（业务验收 → 领域建模 → 技术方案 → 测试规格 → 工作量评估）产出设计契约。每个 Phase 有用户确认门，未确认不进入下一步。
---

# 设计与验收包

## 概述

这个 skill 把 analysis-spec 中的目标行为（TB）转化为可实施、可验收、可验证的设计契约。

它通过 5 个 Phase 渐进式展开设计，每个 Phase 只锁定一层决策，上层确认后下层才开始。这样做的目的是：

- 产品角色在 Phase 1 就能审阅验收标准，不需要看技术细节
- 领域概念在 Phase 2 锁定统一语言，避免实现阶段歧义
- 技术方案在 Phase 3 显式确认，争议前置而非在实现时爆发
- 测试规格在 Phase 4 从已确认的 AC 推导，不是凭空编写
- 工作量在 Phase 5 有粗粒度评估，为 slice-plan 提供 effort 上下文

它是 AC、TC、ADR 的唯一归属地。analysis-spec 不写 AC，slice-plan 不写 TC，verify 不定义标准——它们只消费 design-pack 的产出。

## 交互规范

遵守 [Skill-User 交互黄金原则](../../PRINCIPLES.md)。

| Phase | 用户可见内容 | 结束方式 |
| --- | --- | --- |
| 1 — 业务验收 | AC 表 + 不做的事 + 验收方式 | 确认门（P4） |
| 2 — 领域建模 | 实体/状态机/统一语言表；简单需求压缩为一句话 | 确认门（P4） |
| 3 — 技术方案 | 技术栈确认 + ADR + API 契约 + Review Rules | 确认门（P4） |
| 4 — 测试规格 | TC 表（从 AC 推导） | 确认门仅 `migration-strict` 需要（P4） |
| 5 — 工作量 | 工作块表 + Appetite | 确认门（P4） |
| 最终 | 三行索引（P5） | — |

---

## 硬门禁

1. **没有 analysis-spec 不准设计。** 没有稳定的 TB，设计的是空气。
2. **每个 AC 必须映射到 TB。** 无法追溯到目标行为的验收标准是悬空承诺。
3. **每个 TC 必须映射到 AC。** 无法追溯到验收标准的测试是无效劳动。
4. **不要在 design-pack 中做实现。** 这里只定义契约和边界，不写代码。
5. **ADR 只记录非显而易见的决策。** 不要把显然的选择写成 ADR。
6. **未确认的 Phase 不进入下一个 Phase。** 确认门是硬约束，不是建议。

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

## 自适应深度

不是每个需求都需要走满 5 个 Phase。按工作模式和复杂度信号调整：

| 工作模式 | Phase 1 业务验收 | Phase 2 领域建模 | Phase 3 技术方案 | Phase 4 测试规格 | Phase 5 工作量 |
| --- | --- | --- | --- | --- | --- |
| `feature-slice` 简单 | **必做** + 确认 | 压缩为术语表 | 压缩（复用已有模式） | 自动推导 | **必做** |
| `feature-slice` 复杂 | **必做** + 确认 | **必做** + 确认 | **必做** + 确认 | 推导 + 可选确认 | **必做** |
| `migration-strict` | **必做** + 确认 | **必做** + 确认 | **必做** + 确认 | **必做** + 确认 | **必做** + 确认 |

判断 `feature-slice` "简单"还是"复杂"的信号：

- 涉及多实体关系或状态机 → 复杂（Phase 2 必做）
- 涉及新技术选型或架构变化 → 复杂（Phase 3 完整展开）
- 只是在已有架构上加功能 → 简单（Phase 2/3 可压缩）

当 Phase 被压缩时，仍然要在 design-pack.md 中保留对应章节，标注"已压缩"和压缩理由。

## 工作流

### Phase 1 — 业务验收

回答"用户最终能做什么、不能做什么、边界在哪"。

这是整个 design-pack 最重要的 Phase。它的产出必须让非技术人员也能审阅和签收。

动作：

- 对每个 TB，产出一组 AC（验收标准）
- AC 使用业务语言，非技术人员可读
- 明确"不做的事"边界
- 明确验收确认方式（谁确认、怎么确认）

AC 格式策略：

- **行为型验收**：使用 Given / When / Then，但语言必须是业务语言

```markdown
**AC-1.1** (← TB-1)
Given 用户进入订单列表页
When 页面首次加载完成
Then 默认显示第一页 20 条数据，分页器显示总页数
```

- **非行为型验收**：保留为结构化检查项

```markdown
**AC-2.3** (← TB-2) [权限矩阵]
- admin: 可编辑、可删除
- viewer: 只读
- guest: 不可见
```

适用于权限矩阵、性能阈值、埋点规格、可访问性要求、兼容性约束等。

- **边界说明**：显式列出不做的事

```markdown
## 不做的事（Phase 1 细化）
- 不支持自定义每页条数（固定 20 条）
- 不支持跳页输入（只有上一页/下一页和首尾页）
```

- **验收确认方式**：

```markdown
## 验收确认方式
- TB-1 ~ TB-3: demo 演示 + 截图签收
- TB-4 ~ TB-6: 自动测试覆盖 + 控制台检查
```

规则：

- 每个 AC 必须引用至少一个 TB
- 🔴 项（未澄清的 TB）不允许产出 AC
- AC 总量与 TB 复杂度成正比，不要过度拆分
- AC 的语言标准：产品经理能读懂，不包含代码、类名、函数名

**确认门**：向用户展示全部 AC、不做的事、验收确认方式，等待确认。

```
---
**[Phase 1 确认门]** 以上是本次交付的验收标准和不做的事。
→ 请确认继续 / 或指出需要修改的地方。
---
```

未确认不进入 Phase 2。

---

### Phase 2 — 领域建模

回答"这个需求涉及哪些核心概念、它们之间什么关系、状态怎么流转"。

动作：

- 识别核心实体及其属性、生命周期
- 画出实体关系（谁拥有谁、谁引用谁）
- 如果涉及状态流转，画出状态机
- 如果涉及异步或跨边界，识别领域事件
- 建立统一语言表，消除术语歧义

产出结构：

```markdown
## 实体与关系

| 实体 | 核心属性 | 生命周期 | 归属 |
| --- | --- | --- | --- |
| Order | id, status, items[], total, createdAt | created → paid → shipped → completed | 独立聚合根 |
| OrderItem | productId, quantity, price | 随 Order 创建 | Order 的值对象 |

## 状态机（如涉及）

Order: draft → submitted → paid → shipping → delivered → closed
                                                      ↘ cancelled（paid 之后任意状态可触发）

## 领域事件（如涉及）

| 事件 | 触发条件 | 消费方 |
| --- | --- | --- |
| OrderPaid | 支付回调确认 | 库存服务、通知服务 |

## 统一语言

| 术语 | 定义 | 注意 |
| --- | --- | --- |
| 分页 | 服务端分页，每次请求一页数据 | 与"无限滚动"（前端虚拟化）是不同方案 |
```

**压缩模式**（feature-slice 简单）：跳过实体关系和状态机，只保留统一语言表。在 design-pack.md 中标注"Phase 2 已压缩：需求不涉及多实体关系或状态流转"。

**确认门**：向用户展示领域模型，等待确认。

```
---
**[Phase 2 确认门]** 以上是领域概念、实体关系和统一语言。
→ 请确认继续 / 或指出需要修改的地方。
---
```

未确认不进入 Phase 3。

---

### Phase 3 — 技术方案

回答"用什么技术栈、关键架构决策是什么、接口契约长什么样"。

动作：

**技术栈确认**（新项目必做，已有项目按需）：

```markdown
## 技术栈确认

| 层 | 选择 | 状态 |
| --- | --- | --- |
| 前端框架 | React 18 + Next.js 14 | 已有（沿用） |
| 状态管理 | Zustand | 新增（见 ADR-1） |
| API 层 | REST + SWR | 已有（沿用） |
```

**架构决策（ADR）**：

只在以下情况产出 ADR：

- 共享层变更
- API / 数据契约变化
- 兼容层 / 迁移策略
- 性能关键路径
- 存在多种合理方案且取舍不显然

ADR 最小结构：

```markdown
### ADR-<N>: <决策标题>

**背景**：为什么需要做这个决策
**选项**：考虑过哪些方案（至少两个）
**决定**：选了什么，为什么
**后果**：这个决定带来的约束和风险
**引用**：TB-<N>, Risk-<N>
```

**API / 接口契约**：

- 请求/响应结构
- 错误处理
- 版本化策略
- 标注每个契约：复用已有 / 扩展已有 / 新增

**组件/模块边界**：

- 定义公共 API 边界
- 对于 `migration-strict`：兼容层、双写策略、回填计划、回滚路径

先检查 `references.yaml` 中的已有模式（Reuse before add）。

**Review Rules 提炼**：

Phase 3 确认后，从统一语言表（Phase 2）+ ADR + 架构约束 + API 契约中自动提炼需求级 review rules：

- 领域命名规则（来自 Phase 2 统一语言表）
- 架构约束规则（来自 ADR 的"后果"和"约束"）
- 契约遵守规则（来自 API 契约定义）
- 组件边界规则（来自模块边界定义）

输出到 `design-pack.md` 的 `## Review Rules` 章节，同时写入 `.project-context/review-rules/<topic>.md`。这些 rules 供 `code-review` 消费。

**压缩模式**（feature-slice 简单）：跳过 ADR 和详细契约，只确认技术栈沿用和复用的已有模式。Review rules 压缩为仅领域命名规则。标注"Phase 3 已压缩：完全复用已有架构模式"。

**确认门**：向用户展示技术方案和提炼的 review rules，等待确认。

```
---
**[Phase 3 确认门]** 以上是技术方案、关键决策和 Review Rules。
→ 请确认继续 / 或指出需要修改的地方。
---
```

未确认不进入 Phase 4。

---

### Phase 4 — 测试规格

回答"怎么验证每个 AC"。

基于 Phase 1 的 AC + Phase 2 的领域模型 + Phase 3 的技术方案，推导 TC。

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
- TC 的描述应引用 Phase 2 的领域术语（统一语言）

**确认门**（可选，`migration-strict` 必做）：

```
---
**[Phase 4 确认门]** 以上是测试覆盖策略和 TC 列表。
→ 请确认继续 / 或指出覆盖缺口。
---
```

---

### Phase 5 — 工作量评估

回答"大概要多久、最重的部分在哪"。

产出：

```markdown
## 工作量评估

整体规模: M（预估 3-5 人天）

| 工作块 | 复杂度 | 风险 | 预估 | 说明 |
| --- | --- | --- | --- | --- |
| 后端分页接口 | S | 低 | 0.5d | 已有 pagination 中间件可复用 |
| 前端分页 + URL 同步 | M | 中 | 1.5-2d | usePagination hook 复用，URL 同步需新增 |
| 状态矩阵覆盖 | S | 低 | 1d | loading/empty/error 走现有设计系统 |
| 测试编写 | S | 低 | 0.5-1d | e2e + unit |

## 高风险项

- URL 同步方案：需要与路由系统集成，可能有兼容性问题

## Appetite

如果只有 2 人天，建议砍掉 TB-5（空态提示）和 TB-6（失败重试），先保 TB-1 ~ TB-4 核心路径。
```

规模尺码定义：

| 尺码 | 人天范围 | 典型场景 |
| --- | --- | --- |
| S | 0.5-1d | 单组件、单接口、无状态变化 |
| M | 2-5d | 完整用户路径、涉及 2-3 个模块 |
| L | 5-15d | 跨模块功能、需要新架构模式 |
| XL | 15d+ | 大型迁移、新子系统 |

Appetite 部分回答：如果时间不够全做，哪些 TB 可以先砍、核心路径是什么。这帮助 `slice-plan` 确定优先级。

**确认门**：向用户展示工作量评估和 appetite，等待确认。

```
---
**[Phase 5 确认门]** 以上是工作量评估和 Appetite（时间不足时的砍法建议）。
→ 请确认继续 / 或告知时间预算以调整范围。
---
```

---

## 退出门禁

- 每个 TB 有至少一个 AC
- 每个 AC 有至少一个 TC
- 所有 ADR 有背景、选项、决定、后果
- `migration-strict` 的兼容/回滚策略已明确
- 所有必做 Phase 的确认门已通过
- 工作量评估已完成

## 降级模式

如果 analysis-spec 不完整：

- 标注哪些 TB 缺少细节
- 对缺少细节的 TB 不产出 AC，标记为 `blocked`
- 建议回到 `analysis-spec` 补充

如果跳过 design-pack（patch-lite）：

- slice-plan 可以直接从 TB 切片
- verify 不要求 TC 证据，但仍需 verify pack 证据

如果用户在某个 Phase 确认门拒绝：

- 记录拒绝原因
- 修改当前 Phase 产出后重新提交确认
- 如果拒绝原因指向上游问题（如 TB 不清晰），建议回到 `analysis-spec`

## 最终输出

```
✓ design-pack 完成
产出：docs/specs/<topic>/design-pack.md
下一步：进入 slice-plan，基于 TB / AC / TC 切片
```

---

## 工件管理

| 工件 | 路径约定 |
| --- | --- |
| `design-pack.md` | `docs/specs/<topic>/design-pack.md` |

`<topic>` 与 `analysis-spec.md` 使用相同的目录。
