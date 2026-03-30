# moon-skills

面向 AI 辅助开发的分析驱动 workflow skill 库。

## 问题

AI 写代码很快。但在没有结构化分析的情况下，快是一种隐患：目标行为没有对齐、边界条件没有覆盖、每次 session 学到的东西下一次全部消失。

这套 skill 库是一个 **execution harness**——不是改模型，而是改围绕模型的系统。它把每次开发任务组织成一条有工件交接的流水线，用门禁和可追溯合同限制模型随意发挥。

## 工作流

```
初始化 → 预热 → 需求分析 → 设计验收包 → 交付切片 → [先TC后代码] → 领域验证 → 规格对账 → 复盘治理
                                                                                    ↓
                                                                           .project-context/
                                                                           (跨 session 持久化)
```

九个 skill，分三层：

- **上下文层**：`initialize` / `sync-context` — 建立并维护仓库的机器可读记忆
- **分析交付层**：`analysis-spec` / `design-pack` / `slice-plan` / `domain-verify` / `spec-check` — 从模糊需求到行为规格，从设计验收到可追溯交付
- **学习闭环层**：`audit` / `immune-debug` — 把每轮交付和事故的结论写回上下文，供下轮使用

## 可追溯合同：TB / AC / TC / EV / ADR

整条流水线由一条稳定的追溯链串联，限制每一步的输入输出：

```
TB → AC → TC → EV
 \→ ADR（仅在关键设计取舍时出现）
```

| 缩写 | 全称 | 回答的问题 | 归属 skill |
|---|---|---|---|
| TB | Target Behavior | 最终要交付什么 | `analysis-spec` |
| AC | Acceptance Criteria | 什么叫完成 | `design-pack` |
| TC | Test Case / Test Check | 怎么验证 AC | `design-pack` |
| EV | Evidence | 拿什么证明 TC 通过了 | `domain-verify` |
| ADR | Architecture Decision Record | 为什么选这个方案 | `design-pack` |

每个对象只有一个归属地，不允许双写。

## 四条核心设计

### Study before ask

`analysis-spec` 的自学习阶段先读取仓库代码、文档和历史 context，对每个关键问题标注置信度，再进入澄清。AI 不问用户已经能自己回答的问题。

| 状态 | 含义 |
| --- | --- |
| 🔴 | 自学习无法回答，必须向用户澄清 |
| 🟡 | 有证据但未确认，展示推理，由用户决定是否澄清 |
| 🟢 | 通过代码、文档或历史 context 已确认 |

### Test before code

`slice-plan` 要求每个 slice 列出测试先行清单（TC 编号）。实现时先写测试，再写代码。没有 TC 的 slice 不是合格切片。

### Evidence before done

`domain-verify` 是 `spec-check` 的前置门禁。没有通过领域验证（每个 TC 必须挂到 EV），不允许进入规格对账。

### Context as memory

`.project-context/` 是跨 session 的仓库记忆。`audit` 和 `immune-debug` 的结论通过 `sync-context` 写回，下一轮任务从已有知识出发，不从零开始。

## 看它如何工作

> 场景：给订单列表加分页

```
你：给订单列表加分页

AI (sync-context 预热):
  已定位目标模块：OrderListPage → useOrders → /api/orders
  当前行为：全量加载，无分页
  发现可复用资产：usePagination hook 已存在于 UserList，references.yaml 有记录

AI (analysis-spec — 自学习):

  | # | 问题               | 状态 | 依据                                     |
  |---|-------------------|------|------------------------------------------|
  | Q-1 | usePagination 可复用 | 🟢 | 已在 UserList 使用，references.yaml 有记录 |
  | Q-2 | 后端支持分页参数      | 🟡 | 接口返回含 total 字段，推测支持标准分页       |
  | Q-3 | 默认每页条数          | 🔴 | 无任何上下文提及                            |
  | Q-4 | 页码是否需要同步到 URL | 🔴 | 产品未明确                                 |

  🔴 Q-3 和 Q-4 需要回答才能继续。
  🟡 Q-2 是推测，你可以确认或要求澄清。

你：默认 20 条，需要 URL 同步。Q-2 确认。

AI (analysis-spec — 规格):
  产出 analysis-spec.md，含 6 条 TB：
  TB-1 默认显示第一页 20 条 / TB-2 分页器切换 / TB-3 页码同步 URL
  TB-4 loading 骨架屏 / TB-5 空态提示 / TB-6 失败重试
  → 触发矩阵：涉及共享 hook，进入 design-pack

AI (design-pack):
  AC-1.1 (← TB-1)
  Given 用户进入订单列表页
  When 页面首次加载完成
  Then 默认显示第一页 20 条数据，分页器显示总页数

  TC-1.1.1 (← AC-1.1) [e2e / happy-path]
  访问 /orders，断言列表项数量为 20，分页器可见

  ADR-1: 页码写入 URL（支持分享和刷新恢复），而非仅本地状态

AI (slice-plan):
  切出 3 个 slice，每个附测试先行清单和回滚边界：
  S-1 接入 usePagination + 后端分页参数 | TC: TC-1.1.1, TC-1.1.2 | 回滚：移除 hook 调用
  S-2 分页器 UI + URL 同步 | TC: TC-2.1.1 | 回滚：移除分页器组件
  S-3 loading / empty / error 状态 | TC: TC-4.1.1, TC-5.1.1 | 回滚：还原原有简单态

（实现完成后）

AI (domain-verify):
  使用 frontend-verify-pack 逐项验证：
  TC-1.1.1 → pass (EV: e2e 截图，列表 20 条 + 分页器可见)
  TC-2.1.1 → pass (EV: URL 含 ?page=2，刷新后页码保持)
  TC-4.1.1 → pass (EV: loading 骨架屏截图)
  TC-5.1.1 → pass (EV: 空态提示截图)
  verify pack：6 种状态覆盖 ✓ / 控制台无新增报错 ✓ / 响应式布局 ✓
  spec deviation: 无
  → 产出 verify.md，可进入 spec-check

AI (spec-check):
  逐条对账 analysis-spec：
  TB-1 ~ TB-6 → 全部 as_specified
  偏差项：无
  → 产出 spec-check.md，建议进入 audit 做复盘沉淀
```

## Skills

| Skill | 流程阶段 | 触发方式 | 核心产出 |
|---|---|---|---|
| `initialize` | **仓库知识库初始化** | **手动**：`请用 initialize 为这个仓库建立首版上下文`<br>`请用 initialize 为 <模块> 建立首版上下文` | `.project-context/` 底座（profile + references + features index + PROFILE.md + 可选 lenses） |
| `sync-context` | **上下文预热 / 增量同步** | **手动（预热）**：`请用 sync-context 为 <模块> 做开发前预热`<br>**自动（写回）**：由 `audit` / `immune-debug` 路由触发 | context 资产增量更新（按影响面刷新 profile / references / features index） |
| `analysis-spec` | **需求分析 → 行为规格** | **手动**：`请完成 analysis-spec：摸底 → 自学习 → 澄清 → 规格` | `analysis-spec.md`（TB + RiskInventory + EvidencePlan） |
| `design-pack` | **设计方案 + 验收标准 + 测试规格** | **手动**：`请基于 analysis-spec 产出 design-pack`<br>按触发矩阵决定是否进入（见下方工作模式） | `design-pack.md`（AC + TC + ADR + 兼容策略） |
| `slice-plan` | **交付切片 / 任务分解** | **手动**：`请基于 analysis-spec 产出 slice-plan` | `slice-plan.md`（每个 slice：目标 / TB / AC / TC / 风险 / 回滚） |
| `domain-verify` | **领域验证 / 证据收口** | **手动**：`请用 domain-verify 验证当前 slice` | `verify.md`（TC 证据台账 + verify pack 结果 + spec 偏差检测） |
| `spec-check` | **规格对账 / 交付验收** | **手动**：`请做 spec-check，逐条对账 analysis-spec 和最终交付` | `spec-check.md`（每条 TB：as_specified / intentionally_changed / deferred / abandoned） |
| `audit` | **交付复盘 / 上下文治理** | **手动（复盘）**：`请用 audit 做本轮交付的 post-ship reflect`<br>**手动（治理）**：`请用 audit 审查当前 .project-context 资产` | `reflect.md` + 路由决策（→ sync-context / immune assets / 仅观察） |
| `immune-debug` | **事故根因 + 防护决策** | **手动**：`请用 immune-debug 处理这个 <问题>，并给出免疫决策`<br>依赖 `superpowers:systematic-debugging`（见下方） | 修复验证 + 免疫决策（→ `immune-registry.yaml` 或 `immune-candidates.yaml`） |

## 工件链

```
analysis-spec.md → design-pack.md → slice-plan.md → verify.md → spec-check.md → reflect.md
       TB              AC/TC/ADR        slice→TB/AC/TC    TC→EV       TB对账          沉淀
                                                              ↓
                                                  .project-context/（sync-context 写回）
```

`patch-lite` 需求可以跳过 `design-pack`，把 analysis-spec、slice-plan、verify 合并成一份精简记录，但 spec-check 和 audit 的语义不可跳过。

## 三种工作模式

根据需求复杂度，工作深度自动调整：

| 模式 | 适用场景 | design-pack | 最小要求 |
|---|---|---|---|
| `patch-lite` | 只影响单个叶子组件，不改路由 / 共享层 / 权限 | 跳过 | 压缩版全链路，格式可合并 |
| `feature-slice` | 完整用户路径的新增或调整 | 按需（触发矩阵） | 完整主链 + 至少一个领域 lens |
| `migration-strict` | 跨模块改造、共享层迁移、需要兼容期 | 必做 | 完整主链 + integration lens + 明确回滚策略 |

`feature-slice` 触发 `design-pack` 的条件（任一成立）：API/数据契约变化、共享层变化、异步流程/状态机、性能关键路径、RiskInventory 有 high 级风险。

## 门禁与回路

| 门禁 | 规则 |
|---|---|
| **测试先行** | 如果存在 design-pack，每个 slice 必须有测试先行清单（TC 编号），先 TC 后代码 |
| **验证前置** | 没有通过 `domain-verify`，不能进入 `spec-check` |
| **偏差回路** | `domain-verify` 发现实现偏离 TB/AC 时，必须回到上游修正，不能静默吸收 |
| **Replan 阈值** | 连续 3 轮 TC 失败 → 回到 `design-pack`；根因是目标不清 → 回到 `analysis-spec` |

## Installation

安装整个仓库：

```bash
npx skills add ccharlesmeng/moon-skills
```

只安装单个 skill：

```bash
npx skills add ccharlesmeng/moon-skills --skill analysis-spec
```

先查看仓库内可安装的 skills：

```bash
npx skills add ccharlesmeng/moon-skills --list
```

## Superpowers Dependency

`immune-debug` 依赖 `superpowers:systematic-debugging` 处理根因调查阶段。建议额外安装：

```bash
npx skills add obra/superpowers
```

最小安装（仅 immune-debug 所需）：

```bash
npx skills add obra/superpowers --skill systematic-debugging
```

## Quick Use

```markdown
# 首次接手仓库
请用 initialize 为这个仓库建立首版上下文。

# 开始一个新任务（每次开发前）
请用 sync-context 为 <模块> 做开发前预热。

# 完成预热后，进入需求分析
请完成 analysis-spec：摸底 → 自学习 → 澄清 → 规格，产出 analysis-spec.md。

# 如果触发了 design-pack（非 patch-lite，且命中触发矩阵）
请基于 analysis-spec 产出 design-pack，包含 AC、TC 和必要的 ADR。

# 分析/设计完成后，规划切片
请基于 analysis-spec 产出 slice-plan，每个 slice 写清测试先行清单和回滚边界。

# 实现完成后，领域验证
请用 domain-verify 验证当前 slice，收集 TC 证据。

# 验证通过后，规格对账
请做 spec-check，逐条对账 analysis-spec 和最终交付。

# 交付后，复盘与沉淀
请用 audit 做本轮交付的 post-ship reflect。

# 出现 bug 或回归时
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
```

## Repository Layout

- `skills/` — first-party workflow skills
- `analysis-driven-sdd.md` — 方法论文档（分析驱动 SDD 的完整设计哲学、示例与 skill 架构说明）

## Notes

- `reflect` 不单独建立 skill 目录，通过 `audit`、`sync-context`、`immune-debug` 的路由协作实现。
- `sync-context` 是唯一被其他 skill 路由触发的 skill——`audit` 和 `immune-debug` 在产出决策后会指示运行 `sync-context` 写回。
- 独立的集成类或正交能力 skill 已迁移到其他仓库维护，这里只保留 workflow 主链。
