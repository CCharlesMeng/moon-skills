# moon-skills

面向 AI 辅助开发的分析驱动 workflow skill 库。

## 问题

AI 写代码很快。但在没有结构化分析的情况下，快是一种隐患：目标行为没有对齐、边界条件没有覆盖、每次 session 学到的东西下一次全部消失。

这套 skill 库把每次开发任务组织成一条有工件交接的流水线——从模糊需求到行为规格，从切片计划到交付对账，从事故复盘到知识持久化。每一步产出都是下一步的输入，每一轮学习都写回仓库记忆。

## 工作流

```
初始化 → 预热 → 需求分析 → 交付切片 → [实现] → 规格对账 → 复盘治理
                                                       ↓
                                              .project-context/
                                              (跨 session 持久化)
```

七个 skill，分三层：

- **上下文层**：`initialize` / `sync-context` — 建立并维护仓库的机器可读记忆
- **分析交付层**：`analysis-spec` / `slice-plan` / `spec-check` — 需求从模糊到规格，再到可追溯交付
- **学习闭环层**：`audit` / `immune-debug` — 把每轮交付和事故的结论写回上下文，供下轮使用

## 三个核心设计

### Study before ask

`analysis-spec` 的自学习阶段先读取仓库代码、文档和历史 context，对每个关键问题标注置信度，再进入澄清。AI 不问用户已经能自己回答的问题。

| 状态 | 含义 |
| --- | --- |
| 🔴 | 自学习无法回答，必须向用户澄清 |
| 🟡 | 有证据但未确认，展示推理，由用户决定是否澄清 |
| 🟢 | 通过代码、文档或历史 context 已确认 |

### Slice before build

`slice-plan` 要求每个切片可独立验证、可独立回滚。说不清回滚边界的改动不能进入实施。

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
  产出 analysis-spec.md，含 6 条 TargetBehaviors：
  TB-1 默认显示第一页 20 条 / TB-2 分页器切换 / TB-3 页码同步 URL
  TB-4 loading 骨架屏 / TB-5 空态提示 / TB-6 失败重试

AI (slice-plan):
  切出 3 个 slice，每个附验证方式和回滚边界：
  S-1 接入 usePagination + 后端分页参数（回滚：移除 hook 调用）
  S-2 分页器 UI + URL 同步（回滚：移除分页器组件）
  S-3 loading / empty / error 状态（回滚：还原原有简单态）
```

## Skills

| Skill | 流程阶段 | 触发方式 | 核心产出 |
|---|---|---|---|
| `initialize` | **仓库知识库初始化** | **手动**：`请用 initialize 为这个仓库建立首版上下文`<br>`请用 initialize 为 <模块> 建立首版上下文` | `.project-context/` 底座（profile + references + features index + PROFILE.md + 可选 lenses） |
| `sync-context` | **上下文预热 / 增量同步** | **手动（预热）**：`请用 sync-context 为 <模块> 做开发前预热`<br>**自动（写回）**：由 `audit` / `immune-debug` 路由触发 | context 资产增量更新（按影响面刷新 profile / references / features index） |
| `analysis-spec` | **需求分析 → 行为规格** | **手动**：`请完成 analysis-spec：摸底 → 自学习 → 澄清 → 规格` | `analysis-spec.md`（TargetBehaviors + RiskInventory + EvidencePlan） |
| `slice-plan` | **交付切片 / 任务分解** | **手动**：`请基于 analysis-spec 产出 slice-plan` | `slice-plan.md`（每个 slice：目标 / 受影响文件 / 风险 / 验证 / 回滚） |
| `spec-check` | **规格对账 / 交付验收** | **手动**：`请做 spec-check，逐条对账 analysis-spec 和最终交付` | `spec-check.md`（每条 TB：as_specified / intentionally_changed / deferred / abandoned） |
| `audit` | **交付复盘 / 上下文治理** | **手动（复盘）**：`请用 audit 做本轮交付的 post-ship reflect`<br>**手动（治理）**：`请用 audit 审查当前 .project-context 资产` | `reflect.md` + 路由决策（→ sync-context / immune assets / 仅观察） |
| `immune-debug` | **事故根因 + 防护决策** | **手动**：`请用 immune-debug 处理这个 <问题>，并给出免疫决策`<br>⚠️ 依赖 `superpowers:systematic-debugging`（见下方） | 修复验证 + 免疫决策（→ `immune-registry.yaml` 或 `immune-candidates.yaml`） |

## 工件链

每个 skill 的产出是下一个 skill 的输入：

```
analysis-spec.md → slice-plan.md → verify.md → spec-check.md → reflect.md
                                                      ↓
                                          .project-context/（sync-context 写回）
```

`patch-lite` 需求可以把 analysis-spec、slice-plan、verify 合并成一份精简记录，但 spec-check 和 audit 的语义不可跳过。

## 三种工作模式

根据需求复杂度，工作深度自动调整：

| 模式 | 适用场景 | 最小要求 |
|---|---|---|
| `patch-lite` | 只影响单个叶子组件，不改路由 / 共享层 / 权限 | 压缩版全链路，格式可合并 |
| `feature-slice` | 完整用户路径的新增或调整 | 完整主链 + 至少一个领域 lens |
| `migration-strict` | 跨模块改造、共享层迁移、需要兼容期 | 完整主链 + integration lens + 明确回滚策略 |

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

# 分析完成后，规划切片
请基于 analysis-spec 产出 slice-plan，每个 slice 写清验证方式和回滚边界。

# 实现完成后，规格对账
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
- `domain-verify`（交付验证阶段）计划作为独立 skill 纳入，目前通过 verify pack 内嵌在 `analysis-driven-sdd.md` 中描述。
- 独立的集成类或正交能力 skill 已迁移到其他仓库维护，这里只保留 workflow 主链。
