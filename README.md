# moon-skills

面向 AI 辅助开发的分析驱动 workflow skill 库。

## 问题

AI 写代码很快。但在没有结构化分析的情况下，快是一种隐患：目标行为没有对齐、边界条件没有覆盖、每次 session 学到的东西下一次全部消失。

这套 skill 库是一个 **execution harness**——不是改模型，而是改围绕模型的系统。它把每次开发任务组织成一条有工件交接的流水线，用门禁和可追溯合同限制模型随意发挥。

## 工作流

```
初始化 → 预热 → 需求分析 → 设计验收包 → 交付切片 → [先TC后代码] → 代码检视 → 行为验证 → 规格对账 → 复盘治理
                                                                                  ↓
                                                                         .project-context/
                                                                         (跨 session 持久化)
```

十个 skill，分三层：

- **上下文层**：`initialize` / `sync-context` — 建立并维护仓库的机器可读记忆
- **分析交付层**：`analysis-spec` / `design-pack` / `slice-plan` / `code-review` / `verify` / `spec-check` — 从模糊需求到行为规格，从设计验收到可追溯交付
- **学习闭环层**：`audit` / `immune-debug` — 把每轮交付和事故的结论写回上下文，供下轮使用

## 可追溯合同：TB / AC / TC / EV / ADR

整条流水线由一条稳定的追溯链串联：

```
TB → AC → TC → EV
 \→ ADR（仅在关键设计取舍时出现）
```

| 缩写 | 全称 | 回答的问题 | 归属 skill |
|---|---|---|---|
| TB | Target Behavior | 最终要交付什么 | `analysis-spec` |
| AC | Acceptance Criteria | 什么叫完成 | `design-pack` |
| TC | Test Case / Test Check | 怎么验证 AC | `design-pack` |
| EV | Evidence | 拿什么证明 TC 通过了 | `verify` |
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

`verify` 是 `spec-check` 的前置门禁。没有通过领域验证（每个 TC 必须挂到 EV），不允许进入规格对账。

### Context as memory

`.project-context/` 是跨 session 的仓库记忆。`audit` 和 `immune-debug` 的结论通过 `sync-context` 写回，下一轮任务从已有知识出发，不从零开始。记忆有时间维度：免疫资产按 `last_checked_at` 自动衰减，uncertainty 条目按两阶段协议清理，防止过期上下文继续看起来很可靠。

## 看它如何工作

> 场景：给订单列表加分页

```
你：给订单列表加分页

AI (sync-context 预热):
  已定位目标模块：OrderListPage → useOrders → /api/orders
  当前行为：全量加载，无分页
  发现可复用资产：usePagination hook 已存在于 UserList，references.yaml 有记录

AI (analysis-spec — 自学习 + 澄清):

  | # | 问题 | 状态 | 依据 |
  |---|------|------|------|
  | Q-1 🟢 | usePagination 可复用 | 🟢 | 已在 UserList 使用，references.yaml 有记录 |
  | Q-2 🟡 | 后端支持分页参数 | 🟡 | 接口返回含 total 字段，推测支持标准分页 |
  | Q-3 🔴 | 默认每页条数 | 🔴 | 无任何上下文提及 |
  | Q-4 🔴 | 页码是否需要同步到 URL | 🔴 | 产品未明确 |

  以下 2 个问题需要你回答：

  | # | 问题 | 我的推测（如有） |
  |---|------|-----------------|
  | Q-3 🔴 | 默认每页条数？ | — |
  | Q-4 🔴 | 页码是否需要同步到 URL？ | — |

  🟡 Q-2 是推测，可确认、纠正或跳过（标为工作假设）。

你：默认 20 条，需要 URL 同步。Q-2 确认。

AI (analysis-spec — 规格):
  产出 analysis-spec.md，含 6 条 TB：
  TB-1 默认显示第一页 20 条 / TB-2 分页器切换 / TB-3 页码同步 URL
  TB-4 loading 骨架屏 / TB-5 空态提示 / TB-6 失败重试

  ✓ analysis-spec 完成
  产出：docs/specs/order-list-pagination/analysis-spec.md
  下一步：进入 design-pack（涉及共享 hook，命中触发矩阵）

AI (design-pack — Phase 1 业务验收):
  AC-1.1 (← TB-1)
  Given 用户进入订单列表页
  When 页面首次加载完成
  Then 默认显示第一页 20 条数据，分页器显示总页数

  不做的事：不支持自定义每页条数、不支持跳页输入
  验收方式：TB-1~3 demo 演示 + 截图，TB-4~6 自动测试

  ---
  **[Phase 1 确认门]** 以上是本次交付的验收标准和不做的事。
  → 请确认继续 / 或指出需要修改的地方。
  ---

你：确认。

AI (design-pack — Phase 2 领域建模):
  已压缩（不涉及多实体关系），统一语言：
  "分页" = 服务端分页，非前端虚拟滚动

  ---
  **[Phase 2 确认门]** 以上是领域概念、实体关系和统一语言。
  → 请确认继续 / 或指出需要修改的地方。
  ---

你：确认。

AI (design-pack — Phase 3 技术方案):
  技术栈：沿用 React + SWR，复用 usePagination hook
  ADR-1: 页码写入 URL（支持分享和刷新恢复），而非仅本地状态
  API 契约：GET /api/orders?page=1&pageSize=20 → { data, total }

  ---
  **[Phase 3 确认门]** 以上是技术方案、关键决策和 Review Rules。
  → 请确认继续 / 或指出需要修改的地方。
  ---

你：确认。

AI (design-pack — Phase 4 + 5):
  TC-1.1.1 (← AC-1.1) [e2e / happy-path] 访问 /orders，断言列表项数量为 20，分页器可见
  整体规模: M（3-5 人天）
  后端接口 S 0.5d / 前端分页+URL M 1.5-2d / 状态覆盖 S 1d / 测试 S 0.5-1d

  ---
  **[Phase 5 确认门]** 以上是工作量评估和 Appetite。
  → 请确认继续 / 或告知时间预算以调整范围。
  ---

你：确认。

AI (slice-plan):
  S-1 接入 usePagination + 后端分页参数 | TC: TC-1.1.1, TC-1.1.2 | 回滚：移除 hook 调用
  S-2 分页器 UI + URL 同步 | TC: TC-2.1.1 | 回滚：移除分页器组件
  S-3 loading / empty / error 状态 | TC: TC-4.1.1, TC-5.1.1 | 回滚：还原原有简单态

  ✓ slice-plan 完成
  产出：docs/specs/order-list-pagination/slice-plan.md
  下一步：按 S-1 → S-3 顺序进入实现，先写 TC 再写代码

（实现完成后）

AI (code-review):
  rules：base.md (仓库级) + order-pagination.md (需求级)

  | 文件 | 判定 | 说明 |
  |------|------|------|
  | useOrders.ts | pass | 命名、架构、领域命名全部符合 |
  | OrderList.tsx | suggestion | 建议分页器组件抽取为独立文件 |
  | orderApi.ts | pass | |

  ✓ code-review 完成
  产出：docs/specs/order-list-pagination/slices/S-1/code-review.md
  下一步：无 blocking → 进入 verify

AI (verify):
  | TC # | 状态 | EV |
  |------|------|----|
  | TC-1.1.1 | pass | e2e 截图，列表 20 条 + 分页器可见 |
  | TC-2.1.1 | pass | URL 含 ?page=2，刷新后页码保持 |
  | TC-4.1.1 | pass | loading 骨架屏截图 |
  | TC-5.1.1 | pass | 空态提示截图 |

  verify pack：6 种状态覆盖 ✓ / 控制台无新增报错 ✓ / 响应式布局 ✓

  ✓ verify 完成
  产出：docs/specs/order-list-pagination/slices/S-1/verify.md
  下一步：进入 spec-check

AI (spec-check):
  | TB # | 行为 | 状态 |
  |------|------|------|
  | TB-1~6 | （全部） | as_specified |

  ✓ spec-check 完成
  产出：docs/specs/order-list-pagination/spec-check.md
  下一步：进入 audit 做 post-ship reflect
```

## Skills

| Skill | 流程阶段 | 触发方式 | 核心产出 |
|---|---|---|---|
| `initialize` | **仓库知识库初始化** | 手动：`请用 initialize 为这个仓库建立首版上下文` | `.project-context/` 底座（profile + references + features index + PROFILE.md + 可选 lenses） |
| `sync-context` | **上下文预热 / 增量同步 / uncertainty 清理** | 手动（预热）：`请用 sync-context 为 <模块> 做开发前预热`<br>自动（写回）：由 `audit` / `immune-debug` 路由触发 | context 资产增量更新（按影响面刷新 profile / references / features index）+ uncertainty 两阶段清理（标记 `[possibly-resolved]` → 确认移除） |
| `analysis-spec` | **需求分析 → 行为规格** | 手动：`请完成 analysis-spec` | `analysis-spec.md`（TB + RiskInventory + EvidencePlan） |
| `design-pack` | **渐进式设计契约（5 Phase）** | 手动：`请基于 analysis-spec 产出 design-pack`<br>按触发矩阵决定是否进入 | `design-pack.md`（业务验收 → 领域建模 → 技术方案 → 测试规格 → 工作量评估，每步确认门） |
| `slice-plan` | **交付切片 / 任务分解** | 手动：`请基于 analysis-spec 产出 slice-plan` | `slice-plan.md`（每个 slice：目标 / TB / AC / TC / 风险 / 回滚） |
| `code-review` | **代码检视（规则驱动）+ 免疫触发反写** | 手动：`请用 code-review 检视当前 slice 的代码` | `code-review.md`（基于累积 review rules 的结构化检视，blocking / suggestion）+ 自动反写 `immune-registry.yaml` 的 `last_checked_at` / `last_triggered_at` |
| `verify` | **行为验证 / 证据收口** | 手动：`请用 verify 验证当前 slice` | `verify.md`（TC 证据台账 + verify pack 结果 + spec 偏差检测） |
| `spec-check` | **规格对账 / 交付验收** | 手动：`请做 spec-check，逐条对账 analysis-spec 和最终交付` | `spec-check.md`（每条 TB：as_specified / intentionally_changed / deferred / abandoned） |
| `audit` | **交付复盘 / 上下文治理 / 免疫衰减** | 手动（复盘）：`请用 audit 做本轮交付的 post-ship reflect`<br>手动（治理）：`请用 audit 审查当前 .project-context 资产` | `reflect.md` + 路由决策（→ sync-context / immune assets / 仅观察）+ Periodic Freshness Check（免疫资产 90/180 天衰减降级） |
| `immune-debug` | **事故根因 + 防护决策** | 手动：`请用 immune-debug 处理这个 <问题>，并给出免疫决策` | 修复验证 + 免疫决策（→ `immune-registry.yaml` 或 `immune-candidates.yaml`），含时间治理字段（`added_at` / `last_checked_at` / `last_triggered_at` / `defensive_rule_id`） |

## 工件链

```
analysis-spec.md → design-pack.md ──→ slice-plan.md → code-review.md → verify.md → spec-check.md → reflect.md
       TB          Phase1: AC              slice→TB/AC/TC   rules检视        TC→EV       TB对账         沉淀
                   Phase2: 领域模型                              ↑               ↓
                   Phase3: ADR/契约 + review rules    .project-context/review-rules/
                   Phase4: TC                          (initialize + design-pack + immune-debug 累积)
                   Phase5: 工作量评估
```

`patch-lite` 需求可以跳过 `design-pack`，把 analysis-spec、slice-plan、verify 合并成一份精简记录，但 spec-check 和 audit 的语义不可跳过。

## 三种工作模式

| 模式 | 适用场景 | design-pack | 最小要求 |
|---|---|---|---|
| `patch-lite` | 只影响单个叶子组件，不改路由 / 共享层 / 权限 | 跳过 | 压缩版全链路，格式可合并 |
| `feature-slice` | 完整用户路径的新增或调整 | 按需（触发矩阵） | 完整主链 + 至少一个领域 lens |
| `migration-strict` | 跨模块改造、共享层迁移、需要兼容期 | 必做 | 完整主链 + integration lens + 明确回滚策略 |

`feature-slice` 触发 `design-pack` 的条件（任一成立）：API/数据契约变化、共享层变化、异步流程/状态机、性能关键路径、RiskInventory 有 high 级风险。

## 门禁与回路

| 门禁 | 规则 |
|---|---|
| **渐进确认** | `design-pack` 每个 Phase 有确认门，未确认不进入下一 Phase |
| **测试先行** | 如果存在 design-pack，每个 slice 必须有测试先行清单（TC 编号），先 TC 后代码 |
| **代码检视** | `code-review` blocking issue 未清零不进入 `verify`；rules 来自 initialize + design-pack + immune-debug 累积 |
| **免疫触发反写** | `code-review` 使用 defensive rules 后必须反写 `immune-registry.yaml` 的 `last_checked_at`；产生 blocking 时同时更新 `last_triggered_at` |
| **验证前置** | 没有通过 `verify`，不能进入 `spec-check` |
| **偏差回路** | `verify` 发现实现偏离 TB/AC 时，必须回到上游修正，不能静默吸收 |
| **Replan 阈值** | 连续 3 轮 TC 失败 → 回到 `design-pack`；根因是目标不清 → 回到 `analysis-spec` |
| **免疫衰减** | `audit` 的 Periodic Freshness Check 自动降级超 90 天未检视的免疫资产（high → medium → low），打上 `needs-review` |
| **uncertainty 保护** | `sync-context` 不直接移除 uncertainty，只能标记 `[possibly-resolved]`，由 `audit` 或下次 `sync-context` 确认后移除 |

## Installation

安装整个仓库：

```bash
npx skills add CCharlesMeng/moon-skills
```

只安装单个 skill：

```bash
npx skills add CCharlesMeng/moon-skills --skill analysis-spec
```

先查看仓库内可安装的 skills：

```bash
npx skills add CCharlesMeng/moon-skills --list
```

## Cursor 插件

本仓库同时是一个 **[Cursor 插件](https://cursor.com/cn/docs/plugins)**：清单文件为 [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json)。捆绑内容如下：

| 组件 | 路径 |
| --- | --- |
| 技能（Skills） | [`skills/`](skills/) |
| 规则（Rules） | [`rules/`](rules/)（`.mdc`） |
| 命令（Commands） | [`commands/`](commands/)（仪表盘 Deep Link 伴随场景，与 [`prompts/`](prompts/) 意图一致） |

### 一键安装（插件 + Superpowers 排障 skill）

以下方式会：**把本仓库注册为 Cursor 本地插件**（`~/.cursor/plugins/local/` 符号链接），并 **`npx skills add` 安装 `obra/superpowers` 中的 `systematic-debugging`**（`immune-debug` 依赖）。需要已安装 **Git** 与 **Node.js（含 npx）**。

**方式 A：`curl` 直装（需 GitHub 上已存在该脚本）**

```bash
curl -fsSL https://raw.githubusercontent.com/CCharlesMeng/moon-skills/main/scripts/install-cursor-plugin-with-deps.sh | bash
```

若返回 **404**：多半是远程还没有包含 `scripts/install-cursor-plugin-with-deps.sh` 的提交（例如尚未执行 `git push`）。请先在本地推送本仓库，或改用 **方式 B** / **方式 A′**。

若默认分支不是 `main`，把 URL 里的 `main` 改成实际分支名。

**方式 A′：`git clone` 后执行（同样依赖远程已有该脚本；不经过 raw.githubusercontent.com）**

```bash
git clone --depth 1 https://github.com/CCharlesMeng/moon-skills.git "${TMPDIR:-/tmp}/moon-skills-install" \
  && MOON_SKILLS_CHECKOUT="${TMPDIR:-/tmp}/moon-skills-install" \
     bash "${TMPDIR:-/tmp}/moon-skills-install/scripts/install-cursor-plugin-with-deps.sh"
```

**方式 B：已克隆本仓库时，在仓库根目录执行**

```bash
bash scripts/install-cursor-plugin-with-deps.sh
```

**方式 C：使用本地已有副本（不重新克隆）**

```bash
export MOON_SKILLS_CHECKOUT=/你的/绝对路径/moon-skills
bash /你的/绝对路径/moon-skills/scripts/install-cursor-plugin-with-deps.sh
```

环境变量（可选）：

| 变量 | 含义 | 默认 |
| --- | --- | --- |
| `MOON_SKILLS_REPO_URL` | Git 克隆地址 | `https://github.com/CCharlesMeng/moon-skills.git` |
| `MOON_SKILLS_CHECKOUT` | 插件根目录（含 `.cursor-plugin/`）；若设置则**不会**自动克隆，仅校验并链接 | `${XDG_DATA_HOME:-~/.local/share}/moon-skills/checkout` |
| `MOON_SKILLS_PLUGIN_NAME` | `~/.cursor/plugins/local/` 下目录名 | `moon-skills` |

安装结束后在 Cursor 中执行 **Developer: Reload Window**，并在 **Settings → Rules** 中确认插件与技能已加载。

### 本地安装（发布前自测）

1. 克隆本仓库，或直接使用本仓库所在路径。
2. 将**插件根目录**（包含 `.cursor-plugin/` 的那一层目录）**符号链接或复制**到：

   `~/.cursor/plugins/local/moon-skills`

   示例：

   ```bash
   mkdir -p ~/.cursor/plugins/local
   ln -sf /path/to/moon-skills ~/.cursor/plugins/local/moon-skills
   ```

3. 在 Cursor 中执行 **Developer: Reload Window**（重新加载窗口）。
4. 打开 **Settings → Rules**，确认插件带来的规则与技能已出现；在对话中可按 Cursor 文档使用 `/skill-name` 等形式手动触发技能。

### 分发方式

- **公开市场**：在 [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) 提交本 Git 仓库（需开源并接受审核）。提交清单见 [插件参考 — Submitting](https://cursor.com/docs/reference/plugins.md)。
- **团队 / 企业版**：在 Dashboard → **Settings → Plugins** 将本 GitHub 仓库导入为**团队插件市场**；可为分发组配置**必装**或**可选**插件（[说明](https://cursor.com/cn/docs/plugins)）。
- **单仓多插件**：若日后拆成多个插件根目录，可在仓库根增加 `.cursor-plugin/marketplace.json`（[参考](https://cursor.com/docs/reference/plugins.md)）。

### 可选：随自有 VS Code 扩展分发

若你在自有扩展中打包资源，可通过 `vscode.cursor.plugins.registerPath()` 以编程方式注册本插件目录（[插件文档 — 扩展 API](https://cursor.com/cn/docs/plugins)）。

## Superpowers Dependency

`immune-debug` 依赖 `superpowers:systematic-debugging` 处理根因调查阶段。**使用上文「一键安装」时会自动安装**；若只用手动方式安装插件，可单独执行：

```bash
npx skills add obra/superpowers --skill systematic-debugging
```

## Quick Use

```
# 首次接手仓库
请用 initialize 为这个仓库建立首版上下文。

# 开始一个新任务（每次开发前）
请用 sync-context 为 <模块> 做开发前预热。

# 进入需求分析
请完成 analysis-spec。

# （如触发 design-pack）
请基于 analysis-spec 产出 design-pack。

# 规划切片
请基于 analysis-spec 产出 slice-plan。

# 实现完成后，代码检视
请用 code-review 检视当前 slice 的代码。

# 行为验证
请用 verify 验证当前 slice。

# 规格对账
请做 spec-check，逐条对账 analysis-spec 和最终交付。

# 复盘与沉淀
请用 audit 做本轮交付的 post-ship reflect。

# 出现 bug 或回归时
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
```

## Repository Layout

- `.cursor-plugin/` — Cursor 插件清单（`plugin.json`）
- `skills/` — 工作流 skill（本仓库主链）
- `rules/` — Cursor 插件规则（`.mdc`），工作流级 AI 指引
- `commands/` — Cursor 插件命令（仪表盘 Deep Link 伴随场景）
- `scripts/` — 维护脚本（如 [`install-cursor-plugin-with-deps.sh`](scripts/install-cursor-plugin-with-deps.sh) 一键安装插件与 Superpowers 依赖）
- `prompts/` — 可视化仪表盘 Deep Link 唤起时注入的伴随式提示词（按场景组织）
- `dashboard/` — 可视化仪表盘前端项目
- `docs/` — 产品设计与产物规格文档
- `PRINCIPLES.md` — Skill-User 交互黄金原则（所有 skill 的输出规范基准）
- `analysis-driven-sdd.md` — 方法论文档（分析驱动 SDD 的完整设计哲学、示例与 skill 架构说明）

## Notes

- `reflect` 不单独建立 skill 目录，通过 `audit`、`sync-context`、`immune-debug` 的路由协作实现。
- `sync-context` 是唯一被其他 skill 路由触发的 skill——`audit` 和 `immune-debug` 在产出决策后会指示运行 `sync-context` 写回。
- 免疫治理闭环：`immune-debug` 写入 → `code-review` 反写触发时间 → `audit` 周期性衰减 → 技术负责人决策保留/更新/移除。完整 schema 见 `skills/immune-debug/references/immune-registry-schema.md`。
- 独立的集成类或正交能力 skill 已迁移到其他仓库维护，这里只保留 workflow 主链。
