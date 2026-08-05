---
name: sdd-dev-frontend
description: 执行 SDD 前端 Story：把上游 tasks.md 与 HTML 设计稿变成前端代码和可追溯到 AC 的证据。流程为仓库接入门 → 设计规格抽取 → QA 基线冻结（需用户确认）→ 逐 Task 六步实现 → 四份并行检视 → 收口。用于执行前端 Story、按设计稿还原页面，或续跑其中的抽取、勘察、实现、检视、收口任一步。作用域是一个前端仓 × 一个 Story；仓库 baseline 缺失时自动路由 sdd-init-frontend。
disable-model-invocation: true
---

# 前端开发执行

## 概述

把上游 `tasks.md` 和 HTML 设计稿变成前端代码，并留下能追溯到 AC 的证据。仓库公共事实不再每个 Story 重抽：`sdd-init-frontend` 维护 `REPO-1～REPO-3`，本 skill 只生成当前需求的 `DEMAND-1～DEMAND-3`。两层六类的字段、目录和失效规则见 [baseline contract](../sdd-init-frontend/references/baseline-contract.md)。

两个机制支撑它：

- **Step ① 的失败证据分两形态。** 6 步的编号、顺序、RED/GREEN 语义完全不变。逻辑补全用失败的单测或接口集成测试；还原用**冻结外部设计契约的机器报告**。报告有 RED 才进入实现；YELLOW 必须补证，不能冒充 GREEN；截图只处理机器无法可靠判断的项。契约的基线在设计稿与已确认 QA 基线，而不在自己写的实现断言。
- **开工前冻结 QA 基线。** 标准不冻结，遇到难啃的地方就会被悄悄放宽，最后报告照样被写成 GREEN、AC 照样打勾。所以十个维度固定，用户确认后冻结，开工中要改必须重新确认。

一次运行的作用域是**一个前端仓 × 一个 Story 的 `tasks.md`**，跨仓与多 Story 由外层调度。术语与设计依据见 [CONTEXT.md](./CONTEXT.md)。

## 最短路径

**只有一处必须停下等人：Phase A2 末尾的 QA 基线确认门。** 其余全程静默推进。第一次用本 skill 时按这条主干走，遇到分支再回来查对应小节。

| # | 做什么 | 到什么算过 |
| --- | --- | --- |
| 1 | 跑 `manage_repo_baseline.py status`，不 `READY` 就先跑完 `sdd-init-frontend`；定 `<browser-driver>` | Phase -1 出 `READY` |
| 2 | 定四个需求路径，跑一次 `REPO-2` 的质量命令记起点失败集合，写 `dev-baseline.md` | 执行起点表写完 |
| 3 | 跑 `extract_design_spec.py extract`；有覆盖缺口先登记再确认；派 `extract-prototype`，再按区块并行派 `extract-block-spec` | `<design-spec-dir>` 里区块规格齐了 |
| 4 | 并行派 `recon-spec` + `recon-codebase`，出 QA 基线与工程依据 | **确认门 → 用户确认 → 冻结 → 编译契约** |
| 5 | 按 `tasks.md` 逐 Task 走 6 步，还原轮用契约报告当 RED/GREEN 证据，每步勾 checkbox | checkbox 全勾完 |
| 6 | 四份检视同一轮并行，汇总进 `dev-review.md` | 四份都回传或已记「未执行」 |
| 7 | 阻断级清零（最多修—重跑两轮），核 [退出门禁](#退出门禁) | 出三行索引 |

三条最容易踩空的：**没有 `tasks.md` 不准开工**；**基线没冻结不准进 Phase B**；**报告有 YELLOW 不算完成**。

## 输出规范

七条，全文用 P1–P7 指代。

| # | 规则 |
| --- | --- |
| P1 | **单轮单决策。** 一轮输出只放一个决策点：请求确认、批量提问、宣告完成，三者不同轮 |
| P2 | **结构优于散文。** 多项内容一律用表格或列表；散文只用于单行摘要，不超过 2 句；不用「有问题现在提」这类模糊邀请语，换成明确行动指令 |
| P3 | **不解释过程。** 不写「现在我将开始…」「接下来进入 Phase X」，直接给结果 |
| P4 | **确认门用固定格式**（见下） |
| P5 | **最终输出是三行索引，不是报告。** 不重新摘要交互过的内容，不分「产出文件」「下一步」多个子章节 |
| P6 | **零决策阶段内联**进下一个有决策的阶段，不单独占一轮。例外：结论出乎意料时单独一行告知 |
| P7 | **批量提问。** 同类问题合并一轮，用固定格式（见下），不逐条打散、不在每题后附段落解释 |

确认门格式：

```
---
**[Phase N 确认门]** <本阶段产出的一句话描述>
→ 请确认继续 / 或指出需要修改的地方。
---
```

批量提问格式：

```
以下 N 个问题需要你回答：

| # | 问题 | 我的推测（如有） |
|---|------|-----------------|
| Q-1 | 🔴 <必须回答的问题> | — |
| Q-2 | 🟡 <可确认的推测> | 推测为 X，理由：… |

🔴 标记的问题必须回答才能继续；🟡 标记的是推测，可确认、纠正或跳过（标为工作假设）。
```

## Phase 概览

| Phase | 做什么 | 谁做 | 出口 |
| --- | --- | --- | --- |
| -1 仓库接入门 | 校验仓库 baseline；缺失或失效时路由 `sdd-init-frontend` | 主 agent | `READY`，或当前 Story 不受 limits 影响的 `READY_WITH_LIMITS` |
| 0 执行起点 | 定位需求路径、选择本次场景、记录 `base-ref` 与质量失败集合 | 主 agent | 写 `dev-baseline.md` 执行起点，直接进 A1（P6） |
| A1 规格抽取 | 脚本产出 `design-facts.json` + 三份人类可读清单，再划区块、逐区块出规格 | 主 agent（跑脚本）+ 子代理 ×(1+N) | 设计事实与区块规格齐备 → 进 A2。基线源不是 `原型` 时整段跳过 |
| A2 并行勘察 | 产出 QA 基线、还原契约规则草稿、代码事实清单 | 子代理 ×2 | **确认门**：用户确认后冻结基线并编译 `restore-contract.json`，才能进 B |
| B 实现 | 逐 Task 走 6 步 | 主 agent | `tasks.md` checkbox 全勾完 → 进 C |
| C 并行检视 | 布局 / 代码规范 / 质量 / 功能自测试 | 子代理 ×4 | 四份汇总进 `dev-review.md` → 进 D |
| D 收口 | 阻断级清零、落账、核退出门禁 | 主 agent | 退出门禁全过 → 三行索引 |

**只有下面这些时刻打断用户**，其余全程静默（P6）：

| 时刻 | 形式 |
| --- | --- |
| 仓库接入需要网络、秘密、外部账号或破坏性环境动作 | 沿用 `sdd-init-frontend` 的授权门；完成后自动返回 |
| Phase 0：路径变量缺失或有多个候选 | 一轮批量提问（P7） |
| Phase A：有环境降级项 | 输出里单独一行原句告知 |
| Phase A：「已知缺口」中有必须回答才能冻结基线的项 | 一轮批量提问，答完再出确认门，**不与确认门同轮**（P1） |
| Phase A：基线产出完毕 | 确认门（P4） |
| Phase B：同一报错连修 3 次不成，或需改 Task 文件清单外的文件 | 一轮批量提问，同时攒到的合并一轮 |
| Phase C：某份检视未执行 | 单独一行告知 |
| Phase D：阻断级修不掉 / 需越界改动 / Open Question 待决 / `Deferred` 待判 | 一轮批量提问，四类攒在同一轮；上报后停在 Phase D 等回答 |
| 全部通过 | 三行索引（P5） |

---

## 硬门禁

0. **仓库 baseline 先于 Story 执行。** `repo-baseline.md` 不存在、Section 失效、readiness 为 `DRAFT/BLOCKED`，或 `READY_WITH_LIMITS` 的限制影响当前 Story 时，先完整执行 `sdd-init-frontend`；不得把仓库未就绪写成 Story 降级项继续开工。
1. **没有 `tasks.md` 不准开工。** 它是唯一执行清单，也是进度真相。
2. **QA 基线未经用户确认不得进入 Phase B。**
3. **QA 基线的十个维度不可增删。** 还原侧 6 维、功能侧 4 维，只能填期望值与豁免。
4. **需求执行限制必须显式。** 仅 Story 特有且仓库初始化无法预先消除的限制可写入 `dev-baseline.md` 执行起点。页面或 `<browser-driver>` 等仓库必需能力失效时回 Phase -1；可继续的限制仍按影响让 render/visual 规则保持 YELLOW。**不得用源码检查把渲染规则写成 GREEN，不得假装做过截图。**
5. **带 `Deferred` 标记的 AC 不计为已验收。** 不得静默通过，不得算进覆盖率。
6. **subagent 不改项目与正式工件。** 不再委派；只允许把检视截图写入临时目录，其他产物均以正文回传并由主 agent 落盘。
7. **不修改上游设计、不发明响应式规格、不决定对接模式、不跨仓改动。** 对接模式严格执行 `requirement-frontend-design.md` 的声明；上游没有响应式规格时只承诺「不破」。
8. **开工后放宽任何标准，必须在 `dev-baseline.md` 记录变更内容与理由并重新请用户确认。** 禁止静默修改。
9. **除 `extract-prototype` / `extract-block-spec` 外，任何角色不得读取原型 HTML 源码。** 主 agent 与其余六份子代理一律以 `<design-spec-dir>` 的产物为准。两个例外：用浏览器打开原型作选择性视觉补证（图像进上下文，源码不进）；Step ② / ④ 出现争议时按锚点回查**单个**区块，且必须在报告对应规则的补证记录里登记回查了哪一段。用 `wc` / `rg` 取统计量（行数、引用计数、class 命中位置）不算读取源码，取回正文才算。
10. **`dev-baseline.md` 与 `restore-contract.json` 哈希不一致时拒绝执行。** 不得自动重写哈希、不得以当前实现反推期望值；基线确需变更时走硬门禁 8。
11. **还原报告状态只有 RED / YELLOW / GREEN。** 有 RED 即整体 RED；无 RED 但有 YELLOW 即整体 YELLOW；全部规则已验证或命中冻结豁免才 GREEN。YELLOW 不是较轻的 RED，也不是基本通过；环境能力缺失导致的 YELLOW 走 [放行通道](#还原-yellow-的放行通道)，不是改判 GREEN。
12. **机器可检项目不截图。** 只有阴影观感、字体栅格、图片裁切、复杂叠层等机器无法可靠判断的规则进入视觉补证；视觉缓存只在存在这类 YELLOW 时生成。
13. **仓库范式只有一个所有者。** `PATTERN-*` 正文只在仓库级 `repo-baseline.md / REPO-3`；Requirement 只保存跨 Story 决策引用，Story 只在 `dev-baseline.md` 保存采用的 ID 与 REPO-3 指纹。不得生成 Story 级范式卡片或 `codebase-brief.md`。
14. **抽取覆盖缺口必须登记后才能进确认门。** `extract_design_spec.py extract` 以退出码 4 报出的每一类缺口（外链样式表、`@media` 等 at 规则、行内 `style`、非单类选择器、运行时生成的 CSS），逐条进「已知缺口」并在确认门里说明，再带 `--acknowledge-coverage-gaps` 重跑。**不得直接加这个参数跳过。** 缺口意味着那些维度的期望值在设计稿里读不到，会以 `未见` 的形式从冻结基线里消失——这是 GREEN 报告最容易骗过人的一种方式。
15. **`<browser-driver>` 在 Phase -1 确定。** 取不到时记为能力缺失并进 `REPO-1` limits，不得留到 Step ① 才发现，也不得因为没有驱动就把 render / visual 层规则按源码判 GREEN。

## 何时使用与前置条件

| 前置 | 位置 | 必需 |
| --- | --- | --- |
| `tasks.md`（由 `sdd-task` 产出，标注本仓为 frontend） | `<story-dir>` | 是 |
| `story-delta-frontend-design.md` | `<story-dir>` | 是 |
| `alpha-tests.md` | `<story-dir>` | 是（不存在则由 `sdd-task` 补齐后再来） |
| 目标前端仓可访问 | `<repo-root>` | 是 |
| [基线源](#基线源没有-html-原型时) 三档至少第 3 档成立 | — | 是 |
| HTML 原型 | `<prototype-dir>` | 否，缺失时降到第 2 或第 3 档 |
| `requirement-frontend-design.md` | `<requirement-dir>` | 否，缺失时记为已知缺口 |
| Test Design 用例 | 上游文档中引用的路径 | 否，缺失时记为已知缺口 |

仓库 baseline **不是**进入条件：缺失或失效时由本 skill 自动路由 `sdd-init-frontend`，初始化完成后回到同一 Story。

| 不适用场景 | 改用 |
| --- | --- |
| `tasks.md` 还没产出 | `sdd-task` |
| 需要改设计而不是执行设计 | `sdd-design` |
| 一次要覆盖多个 Story 或多个仓 | 外层调度，逐个 Story 分别运行本 skill |
| 纯后端仓 | 本 skill 不适用 |

本阶段对上游 `tasks.md` 的两份要求由使用者带到 `sdd-task` 落地（[amendments](./references/sdd-task-amendments.md)：Step ① 两种失败证据形态、一个 Task 内多轮 6 步；[frontend-split](./references/sdd-task-frontend-split.md)：前端 Task 的切分方式）。本 skill 只执行、**不改 `tasks.md` 的内容**；不符合这两份要求时照常执行，按各自文档里的兜底走，不回头改上游产物。

## 路径变量

全文引用变量，**不硬编码路径**。

| 变量 | 含义 | 定位线索 |
| --- | --- | --- |
| `<repo-root>` | 目标前端仓根目录 | `tasks.md` 计划头的 `project` 字段；目录内有该栈的依赖清单（`package.json` / `deno.json` / `composer.json` / `Gemfile` 等，取 `REPO-1` 已探明的那个） |
| `<project-sdd-dir>` | 外层 SDD 项目产物根目录 | `<requirement-dir>` 所属的 SDD 根；已有 baseline 时由 `repo-baseline.md` 的 `repo_root` 反查 |
| `<repo-id>` | 仓库稳定标识 | 已有 `repo-baseline.md` 的 `repo_id`；首次接入默认取仓库目录名 |
| `<repo-baseline-dir>` | 仓库 baseline 目录 | `<project-sdd-dir>/frontend-baselines/<repo-id>/` |
| `<story-dir>` | Story 的 SDD 产物目录 | `tasks.md` / `alpha-tests.md` / `story-delta-frontend-design.md` 所在目录 |
| `<requirement-dir>` | Requirement 级产物目录 | `requirement-frontend-design.md` 所在目录，通常是 `<story-dir>` 的上级 |
| `<prototype-dir>` | HTML 原型目录。**基线源降到第 2 / 3 档时为空** | 上游设计文档中引用的原型路径 |
| `<design-spec-dir>` | 设计稿规格产物目录，取值恒为 `<requirement-dir>/design-spec/` | 由 `<requirement-dir>` 推得，不单独定位、不进提问 |
| `<skill-dir>` | 本 skill 自身目录 | 内部变量，不向用户确认 |
| `<init-skill-dir>` | `sdd-init-frontend` 目录 | 默认 `<skill-dir>/../sdd-init-frontend/` |
| `<base-ref>` | **可选**。本 Story 起点的 git 引用，供代码规范检视与质量检视取改动 diff | 开工前记录的起点提交，或与基线分支的分叉点；取法见 Phase C 第 2 节 |
| `<browser-driver>` | 打开页面、触发状态、注入采集脚本、截图的那一套工具。**还原轮 render / visual 层与两份实跑检视全靠它** | 见 [浏览器驱动](#浏览器驱动) |

- 仓库接入门先定位 `<repo-root>`、`<project-sdd-dir>` 与 `<repo-baseline-dir>`；Phase 0 再定位需求侧四个目录。**全部唯一命中则静默继续**，不为此占一轮。
- **任何一个缺失或有多个候选，走一轮 P7 批量提问**，一次问完。
- **`<design-spec-dir>` 随 `<requirement-dir>` 一并确定**，不占一个提问位——多问一个可推导的值只是多耗用户注意力。
- **`<base-ref>` 不进这一轮提问。** 取不到时两份检视能自己从 git 状态推改动范围：能定位就传，不确定就不传。
- 确认结果记入 `<story-dir>/dev-baseline.md` 的“执行起点（环境）”，后续全部引用变量。
- 新产物 `dev-baseline.md` / `restore-contract.json` / `restore-adapter.json` / `restore-report-red.json` / `restore-report-green.json` / `dev-review.md` **一律写入 `<story-dir>`**，`design-spec/` 下的设计事实与视觉缓存**一律写入 `<design-spec-dir>`**；实现侧可选视觉截图挂 `<story-dir>` 下。两者的分界见 [工件管理](#工件管理)。

## 浏览器驱动

**`<browser-driver>` 必须在 Phase -1 就确定，不能等到 Step ① 才发现没有。** 按顺序取第一个可用的，取到哪一档记进 `dev-baseline.md` 执行起点：

| 档 | 驱动 | 三件事怎么做 |
| --- | --- | --- |
| 1 | **会话内的浏览器工具**（Cursor 内为 `cursor-ide-browser` MCP） | 打开页面 `browser_navigate`；注入与状态触发 `browser_cdp` 的 `Runtime.evaluate`，交互用 `browser_click` / `browser_type` / `browser_scroll`，视口用 `browser_cdp` 的 `Emulation.setDeviceMetricsOverride`；截图 `browser_take_screenshot` |
| 2 | **仓内既有的 e2e / 浏览器测试框架**（`REPO-1` 已探明的那个，如 Playwright / Cypress / WebdriverIO） | 写一个一次性只读脚本：起页面 → 进状态 → `page.evaluate` 注入 → 存 JSON → 截图。脚本写在临时目录，**不进项目** |
| 3 | 都没有 | 记为**能力缺失**，进 `REPO-1` 的 limits。render / visual 层规则按 [环境降级](./references/degradation-and-recovery.md#二环境降级) 保持 YELLOW，收口走 [放行通道](#还原-yellow-的放行通道) |

注入协议只有一份，在 [restore-contract.md](./references/restore-contract.md)：先把契约与 adapter 放进 `window.__SDD_RESTORE_INPUT__`，再注入 `<skill-dir>/scripts/collect_restore_facts.js`，取返回值存 `render-results.json`。**采集脚本只读，不代替状态触发**——hover / focus / loading / fixture 必须由 `<browser-driver>` 先真正做出来。

## subagent 派发约定

- **只把 `<skill-dir>/agents/<name>.md` 的路径给子代理，让它自己读全文并执行**，不摘要、不改写、不复述要点，也不把全文抄进派发消息——抄一遍等于让主 agent 白付一份提示词的上下文。
- **在路径之后追加一段「路径变量取值」表**，给出 `<repo-root>` / `<repo-baseline-dir>` / `<story-dir>` / `<requirement-dir>` / `<design-spec-dir>` / `<skill-dir>` 的实际值，实跑类再加 `<browser-driver>`。提示词文件本身不含硬编码路径。
- **`<prototype-dir>` 只传给 `extract-prototype` 与 `extract-block-spec`。** 其余六份被硬门禁 9 禁止读原型，传给它们等于邀请违规。
- 派 `extract-block-spec` 时，在路径变量表后再追加四行实例输入：`区块名`、`页面 / 路由`、`区块切片路径`、`目标视口`。切片路径必须指向主 agent 用 `block --anchor` 刚生成的那一个临时文件，不得给整份原型。
- **子代理不再委派，不修改项目文件或正式工件。** 布局检视与功能自测试只允许把截图写入临时目录；其他产物以正文回传并由主 agent 落盘——并行子代理写同一个正式工件必然互相覆盖。
- **同一 Phase 内的多个子代理在同一轮并行派发**，不串行。
- 子代理返回 `前置缺失：<清单>` 时**不重跑、不自行补足、不猜测**，按 P7 把清单交给用户（Phase C 有一条细则，见 Phase C 第 4 节）。
- 回传后按该提示词的「输出格式」逐项校验。不合格退回重跑一次；仍不合格按 P7 上报，不带着缺口往下走。

| 提示词 | 职责 | Phase | 回传落盘 |
| --- | --- | --- | --- |
| `agents/extract-prototype.md` | 划页面 → 区块、审组件命名与变体归并 | A1 | `<design-spec-dir>/block-index.md`（原型切分表）；对 `interface-inventory.md` 的命名修订 |
| `agents/extract-block-spec.md` | 单区块规格，**按区块并行多实例** | A1 | `<design-spec-dir>/blocks/<区块名>.md`，一区块一文件 |
| `agents/recon-spec.md` | 规格侧勘察 | A2 | `<story-dir>/dev-baseline.md` |
| `agents/recon-codebase.md` | 代码侧勘察：选择 Requirement 决策与仓库 `PATTERN-*` | A2 | 合并进 `<story-dir>/dev-baseline.md` 的“工程依据”，不创建独立文件 |
| `agents/review-layout.md` | 布局与响应式检视 | C | `<story-dir>/dev-review.md` |
| `agents/review-convention.md` | 代码规范检视 | C | `<story-dir>/dev-review.md` |
| `agents/review-quality.md` | 质量检视 | C | `<story-dir>/dev-review.md` |
| `agents/self-test.md` | 功能自测试 | C | `<story-dir>/dev-review.md` |

### 卡死巡检

**派发完不能一直等。**

| 项 | 规则 |
| --- | --- |
| 巡检间隔 | 每 3 分钟查一次全部在跑子代理的状态，并记下当前进展点 |
| 判卡死 | 连续两次巡检无新进展，或单份挂钟超过 15 分钟仍无回传 |
| 首次卡死 | 终止该份，**原样重派一次**（同一提示词、同一取值表，不改内容） |
| 二次卡死 | 不再重派，按下表定性 |

| 卡死的那份 | 定性 |
| --- | --- |
| `extract-prototype` | **不可继续**：切分表是全部区块规格的入口，没有它派不出 `extract-block-spec`。按 P7 上报，停在 A1 |
| `extract-block-spec` 某一实例 | 并行的其余实例照常收；该区块无规格可用，按 P7 上报——缺规格的区块不能编译可追溯契约，也不得改由主 agent 直读原型顶替（硬门禁 9） |
| `recon-spec` | **不可继续**：QA 基线是确认门的对象。按 P7 上报，停在 Phase A |
| `recon-codebase` | **不可继续**：没有工程依据就不能确定当前 Story 应遵循哪些仓库范式。按 P7 上报，停在 A2 |
| 四份检视任一 | 记「未执行（子代理两次卡死）」，按 Phase C 第 4 节披露；能否收口按 [退出门禁](#退出门禁) 末尾三档表判 |

两条约束：

- **「回传不合格重跑一次」与「卡死重派一次」各计一次，不叠加。** 一份子代理最多派两次。
- **一份卡死不影响并行的其余几份**：已回传的照常校验，未回传的继续巡检，不整批终止重来。

## 缺背景知识时的分流

任何阶段发现缺一块本该有的背景知识，先判它属于哪一类再动作。**判据是「读不读得出来」，不是「重不重要」。**

| 缺的是 | 怎么认 | 动作 |
| --- | --- | --- |
| **事实** — 项目里客观存在，只是还没读 | 说得出它在哪类文件里，读一遍就有确定答案 | **起子代理去读，不打断用户**（P6）。需求事实落进 `dev-baseline.md`；仓库范式只引用 `PATTERN-*`，不复制正文 |
| **决策** — 有多个候选，选哪个要人拍板 | 读完之后仍有两个以上都说得通的答案 | **按 P7 问用户**，或并进最近的确认门。不自己选一个往下走 |
| **真缺** — 项目里确实没有 | 穷尽检索后写得出「检索方式 + 未见」 | **分层处理**：仓库必需能力回 Phase -1；需求规格缺口进「已知缺口」；Story 特有限制进执行起点。最终输出带状态限定。不发明，不拿通用最佳实践顶替 |

两条容易踩的：

- **读不出来不等于「由我来定」。** 第三类最常见的失手是被当成第二类的反面自行填空——冻结基线防的就是这件事。
- **第一类的收集一律走子代理，主 agent 不边做边查**，否则「仓内本来怎么做」会和「我刚才怎么做的」混在一起。

### 基线源：没有 HTML 原型时

还原轮需要**外部基线**——契约期望值的出处必须在 Agent 之外，否则退化成自己写的断言。基线源三档，取第一个可用的：

| 档 | 基线源 | 还原侧期望值取自 | 取证方式 | 登记 |
| --- | --- | --- | --- | --- |
| 1 | HTML 原型 | `design-facts.json` + 本区块规格 | 契约机器检查；仅 visual YELLOW 对照原型缓存 | — |
| 2 | **参照页**：仓内已上线的同类页面 | 参照页的结构化实测值与 REPO-3 token 范式 ID | 契约机器检查；仅 visual YELLOW 对照参照页 | `基线源：参照页 <路由>`，可信度降级 |
| 3 | 文字规格 + 仓内 token | `story-delta-frontend-design.md` 的文字规格；R3 / R4 降为「取自选定的 REPO-3 token 范式，不得出现字面量」 | 静态预检 + 可用的结构化渲染；无外部视觉事实 | `基线源：文字规格`，可信度降级 |

主 agent 在这两档上只管三件事，**期望值怎么写的完整判据在 [recon-spec.md](./agents/recon-spec.md) §一**：

- **参照页候选由 `recon-codebase` 收集**（属事实，不打断用户）；**选哪个页面作参照是决策**，并进 Phase A 已有的确认门，不额外占一轮。
- 这两档上 **Phase A 的两份勘察改为串行**：先 `recon-codebase` 收参照页事实，再把它作为输入派 `recon-spec`。正常路径仍并行。
- **降级必须在确认门里说明。** 用户确认的不只是期望值，还有「本次拿什么当基线」。

第 3 档把承诺收窄到**仓内 token 一致性 + 「不破」三项 + 文字规格逐条落地**。R3 / R4 / R5 不得写出原型级的具体数值——没有基线还给数值就是发明规格。

---

## 工作流

### Phase -1 — 仓库接入门

主 agent 自己做。这里只运行 `status` 读取稳定的 Markdown 状态摘要，不把整份仓库 baseline 灌入上下文。

1. 定位 `<repo-root>`、`<project-sdd-dir>`、`<repo-id>`、`<repo-baseline-dir>`。
2. 运行：

```bash
python3 "<init-skill-dir>/scripts/manage_repo_baseline.py" status \
  --repo-root "<repo-root>" \
  --baseline-dir "<repo-baseline-dir>"
```

3. 按结果路由：

| 结果 | 动作 |
| --- | --- |
| baseline 缺失、`DRAFT`、section 失效 | 完整读取 `<init-skill-dir>/SKILL.md` 和其 baseline contract，执行 `sdd-init-frontend`；完成后回到本门 |
| `BLOCKED` | 尝试按 onboarding report 的解除动作继续初始化；仍需外部输入时停在本门 |
| `READY_WITH_LIMITS` | 对照当前 Story 的页面、视觉、接口和质量需求；任一 limit 命中则回初始化解除，否则记录影响后继续 |
| `READY` | 继续 Phase 0 |

4. 按 [浏览器驱动](#浏览器驱动) 三档确定 `<browser-driver>`，取到第 1 或第 2 档时实际打开一次目标路由验证，不只看 `REPO-1` 的声明（硬门禁 15）。

路由返回后再次运行 `status` 与 `validate`。未通过不得进入 Phase 0，也不得把仓库未就绪登记成 Story 降级。

### Phase 0 — 需求执行起点

主 agent 自己做，不派发。**无决策时不单独占一轮（P6）。**

#### 1. 定位需求路径

按路径表定位 `<story-dir>` / `<requirement-dir>` / `<prototype-dir>`。唯一命中就静默继续；缺失或多候选时按 P7 一轮问完。

`<prototype-dir>` 定位不到时，同一个问题带上参照页或文字规格降级选项。`<design-spec-dir>` 恒为 `<requirement-dir>/design-spec/`，不单独提问。

#### 2. 按需读取仓库 baseline

此时只读两个 section，**`--baseline-dir` 是必填参数**：

```bash
python3 "<init-skill-dir>/scripts/manage_repo_baseline.py" show \
  --baseline-dir "<repo-baseline-dir>" --section REPO-1
```

- `REPO-1`：当前 Story 所需的启动、账号/角色/租户、fixture、API/mock、浏览器契约；
- `REPO-2`：当前 app 实际存在的规范质量命令；
- `onboarding-report.md`：当前机器实证、limits、仍保留进程。

不要在 Phase 0 读取 `REPO-3`；代码侧勘察再按当前需求选读。

#### 3. 固定本次执行上下文

从 `tasks.md`、AC、仓库 baseline 与 onboarding report 得到：

- Story 范围、目标页面与路由；
- Git `base-ref`、起点 SHA、工作区初始状态；
- 本次账号、角色、租户、fixture、API/mock 模式；
- `<browser-driver>` 取到哪一档，目标路由能否打开、截图与结构化采集能否使用。

事实能从仓库或上游读出就直接记录；多个场景都合理且会改变验收结果时才按 P7 请用户决定。

#### 4. 提取开工失败集合

按 `REPO-2` 实跑其中实际存在且适用于当前 app 的规范命令。记录命令、范围、退出码、耗时和**具体失败集合**；不存在的类别不生成表格行。若上游明确要求但 REPO-2 没有对应能力，回 Phase -1 补齐，不在 Story 中写“未提供”。

这组结果属于 `DEMAND-2`，与当前起点提交绑定。`REPO-2` 只说明命令怎么跑，不保存这组失败。

#### 5. 设计事实预检

原型存在时只取统计与路径事实：

- 用 `wc` 判断格式化档或单行导出件，不读正文；
- A1 的抽取脚本负责资源完整性和原型指纹；
- 格式化档锚点可附行号，单行档只用 class 结构。

#### 6. 写执行起点

新建 `<story-dir>/dev-baseline.md`，先写 `DEMAND-2`；Phase A2 再追加 `DEMAND-3`。**模板与两条约束在 [story-artifact-templates.md](./references/story-artifact-templates.md) 第一节。**

---

### Phase A1 — 规格抽取

把设计稿的取值一次性搬进 `<design-spec-dir>`，之后全流程只读产物、不读原型（硬门禁 9）。**无决策时不单独占一轮（P6）。**

#### 1. 抽取顺序

| # | 动作 | 谁做 |
| --- | --- | --- |
| 1 | 跑 `python3 "<skill-dir>/scripts/extract_design_spec.py" extract <html> --out-dir "<design-spec-dir>"`，产出 `design-facts.json`、`design-tokens.md`、`interface-inventory.md`、`content-inventory.md`，并算出每个区块的内容哈希。**退出码 4 表示有抽取覆盖缺口**：按硬门禁 14 把每类缺口记进「已知缺口」与执行起点，再带 `--acknowledge-coverage-gaps` 重跑 | 主 agent |
| 2 | 以 `design-facts.json` 的 `prototype_fingerprint` 校验 DOM/CSS + 资源内容/缺失状态；再把脚本切片哈希与 `block-index.md`、本 Story 相关区块规格头的内容哈希逐个比对 | 主 agent |
| 3 | 原型指纹一致、切分表存在、且本 Story 相关区块规格全部命中 → 直接复用，A1 到此结束，零子代理 | 主 agent |
| 4 | 未命中或目录为空 → 派 `extract-prototype` 划页面 → 区块、审组件命名 | 子代理 ×1 |
| 5 | 对切分表里**哈希失配与新增的区块**逐个执行脚本 `block --anchor <锚点> --out <临时路径>`，物化单区块切片；切片不是正式工件，不写入 `<design-spec-dir>` | 主 agent |
| 6 | 把每份临时切片作为 `区块切片路径` 派给 `extract-block-spec`，一区块一实例，同一轮并行 | 子代理 ×N |

#### 2. 分支与跳过

| 情形 | 走法 |
| --- | --- |
| 基线源不是 `原型`（第 2 / 3 档） | **整个 A1 跳过**：没有设计稿就没有可抽的取值，还原侧期望值按 [基线源](#基线源没有-html-原型时) 取自参照页或文字规格 |
| `<design-spec-dir>/design-facts.json` 原型指纹一致，且本 Story 相关区块在切分表与区块规格里全部哈希一致 | 全量复用，不派子代理 |
| 部分区块哈希失配 | **只重抽失配的那几个**，其余复用；全局的 `design-tokens.md`、`interface-inventory.md`、`content-inventory.md` 按 [工件管理](#工件管理) 的并发写规则处理 |
| 本 Story 的 `tasks.md` 涉及切分表之外的新区块 | 只对新区块派 `extract-block-spec`，增量填进同一目录 |

**整稿时效用原型指纹，区块增量用内容哈希，都不用文件 mtime。** 原型指纹覆盖归一化 DOM/CSS、资源内容与缺失状态；只重排 HTML 空白不失效。指纹变化后仍只重抽哈希失配与新增的区块。

**A1 必须跑完才能派 `recon-spec`**（理由见 [CONTEXT.md](./CONTEXT.md#分段依据a1-必须跑完才能派-recon-spec)）。`recon-codebase` 不依赖设计稿，仍与它并行放在 A2，让确认门只等一处。

#### 3. 回传校验

按各提示词「输出格式」节的自检清单逐项核对回传。不合格退回重跑一次，仍不合格按 P7 上报。主 agent 额外只查一条跨份一致性：**切分表覆盖本 Story `tasks.md` 涉及的全部页面**，未覆盖的写了理由。

**`未见` 是合法结论，不是缺陷。** 静态设计稿里确实没有 hover / focus / disabled / loading 与空态，回传里出现具体取值反而是发明规格。这些维度由主 agent 记入 A2 的「已知缺口」，与第 1 节的抽取覆盖缺口合并成一份。

#### 4. 落盘

| 文件 | 动作 |
| --- | --- |
| `<design-spec-dir>/design-tokens.md` | 脚本输出，主 agent 写入；已存在时按 [工件管理](#工件管理) 的并发写规则处理 |
| `<design-spec-dir>/interface-inventory.md` | 同上，再并入 `extract-prototype` 的命名修订 |
| `<design-spec-dir>/content-inventory.md` | 脚本输出，主 agent 写入；已存在时按 [工件管理](#工件管理) 的并发写规则处理 |
| `<design-spec-dir>/design-facts.json` | 脚本确定性输出；包含原型指纹、资源内容/缺失哈希、区块、结构、静态文案、token 与布局声明 |
| `<design-spec-dir>/block-index.md` | `extract-prototype` 回传的切分表，含每个区块的锚点与内容哈希 |
| `<design-spec-dir>/blocks/<区块名>.md` | 每个 `extract-block-spec` 实例回传的区块规格，一区块一文件 |

临时区块切片只用于一次 `extract-block-spec` 派发，规格落盘后不进入工件清单；后续需要时按 `block-index.md` 的锚点重新生成，避免缓存两份可能漂移的设计稿事实。

---

### Phase A2 — 并行勘察

#### 1. 并行派发

同一轮发出两个子代理，不串行：

| 子代理 | prompt |
| --- | --- |
| 规格侧勘察 | `agents/recon-spec.md` + 路径变量取值表 |
| 代码侧勘察 | `agents/recon-codebase.md` + 路径变量取值表 |

取值表里追加一行 `基线源`，取值为 `原型` / `参照页` / `文字规格`（按 [基线源](#基线源没有-html-原型时) 判）。**基线源不是 `原型` 时两份改为串行**：先派 `recon-codebase` 收参照页事实，回传后把参照页那一节连同选定的路由一起追加进 `recon-spec` 的取值表再派它。串行只发生在这条降级路径上。

#### 2. 回传校验

两份都按各自提示词「输出格式」节的自检清单逐项核对（规格侧的完整判据在 [qa-baseline-template.md](./references/qa-baseline-template.md) 的交付前自检）。不合格退回重跑一次，仍不合格按 P7 上报。

主 agent 额外只查两条跨份一致性，因为子代理各自看不到对方的产物：

- **两表对齐**：QA 基线引用的区块名都能在 `block-index.md` 里找到。
- **契约规则一一映射**：每条 R1–R6 期望值都有同 `baseline_id` 的规则，无多余规则。

回传是 `前置缺失：<清单>` 时**不重跑**，直接按 P7 交给用户。

#### 3. 落盘

| 文件 | 动作 |
| --- | --- |
| `<story-dir>/dev-baseline.md` | 在“执行起点（环境）”之后追加「工程依据」「功能理解」「QA 基线」「已知缺口」；工程依据只保存 Story 需要、采用的 `PATTERN-*` / `REQ-DEC-*` 和 REPO-3 指纹，不复制正文 |
| 还原契约规则草稿 | `recon-spec` 回传的 JSON 工件；主 agent 暂存到临时目录，确认门前不编译正式契约、不写进 Story |

**原型切分表不再落进 `dev-baseline.md`。** 它是 Requirement 级事实，跟着设计稿走而不是跟着 Story 走，落在 `<design-spec-dir>/block-index.md`（见 [工件管理](#工件管理)）；`dev-baseline.md` 只引用区块名。

#### 4. 已知缺口先行

「已知缺口」中有**必须回答才能冻结基线**的项（典型：上游未定义的响应式诉求、对接模式未声明、区块规格里 R4 / R5 写 `未见` 而 AC 又要求状态反馈），先单独走一轮 P7 提问，答完再进确认门（P1）。

#### 5. 展示与确认门

用户可见内容：

- **「先看这几条」**：从下面五类里挑出实际存在的，逐条列在 QA 基线全文之前。平铺 N 条期望值让人扫一眼，等于把确认门变成橡皮章；用户的注意力要先落在最可能被误批的地方
  - 期望值来自 `未见` 或抽取覆盖缺口的（这些维度实际没有基线）
  - 命中豁免 `EX-n` 的（这些偏差被允许了）
  - 基线源降级到参照页或文字规格的
  - `<browser-driver>` 缺失、页面或截图不可用而注定 YELLOW 的规则
  - 与上游 AC 有出入或上游未定义的（典型是响应式与状态反馈）
- QA 基线全文：还原侧 R1-R6 与功能侧 F1-F4 的表格原样呈现（确认对象就是这些期望值，摘要掉等于没确认）
- 豁免表全文
- 原型切分表**只展示页面与区块名两级**，锚点、内容哈希与视觉职责不展开
- 基线源不是 `原型` 时，**参照页候选表与选定的那一个**（用户确认的不只是期望值，还有拿什么当基线）
- 有降级项时，前置一行降级告知

`dev-baseline.md` 的“工程依据”不是新的确认对象；它只记录已经由 Requirement 决策或仓库 REPO-3 确立的引用。确认门仅说明采用了多少条工程依据，不展开范式正文。

```
---
**[Phase A 确认门]** QA 基线已产出：基线源 <原型 / 参照页 <路由> / 文字规格>、还原侧 6 维 <N> 条期望值、功能侧 4 维覆盖 <M> 条 AC、豁免 <K> 条、上面「先看这几条」<H> 项；区块规格 <X> 份（复用 <Y> 份），工程依据引用 Requirement 决策 <R> 条、仓库范式 <P> 条。确认后即冻结，开工中放宽任何一条都需重新确认。
→ 请确认继续 / 或指出需要修改的地方。
---
```

#### 6. 冻结

用户确认后：

1. 一次性完成 `dev-baseline.md` 基线头：把「冻结状态」改为 `已冻结 ✅`、填确认时间，并把「还原契约」从 `待编译` 改为固定路径 `<story-dir>/restore-contract.json`。此后再编译；不要把 `contract_sha256` 回填进基线造成自循环。
2. 用同一份规则草稿执行：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" contract \
  --baseline "<story-dir>/dev-baseline.md" \
  --baseline-ref "dev-baseline.md" \
  --rules "<临时规则草稿.json>" \
  --out "<story-dir>/restore-contract.json"
```

3. 根据 `tasks.md` 文件清单、Requirement 工程决策和 `dev-baseline.md` 的工程依据写 `<story-dir>/restore-adapter.json`。每条规则的实现定位是有序 `locators`：`role/name` → 精确文案 → 稳定 `data-testid` → CSS；能用前者就不降到后者，禁止构建生成随机 class。源码静态扫描范围写进 `source_files`。
4. 执行 `verify_restore_contract.py validate` 校验契约、基线哈希和 adapter。任一失败都停在 A2 修正，**未确认或未通过校验不进入 Phase B。**

用户指出要改的地方 → 改完重新走同一个确认门，不跳过、不进 Phase B。

---

### Phase B — 实现

主 agent 亲自做，不派发。逐 Task 推进，**常规不占用户一轮（P6）**，只有第 6 节的两类升级中断才打断。

#### 1. 开工前必读

每个 Task 动手前，先读 `dev-baseline.md / 工程依据`。对当前 Task 命中的 ID 按下面取 REPO-3 正文里的公共方法、token、请求封装与编码范式；Requirement 的 `REQ-DEC-*` 回读 `requirement-frontend-design.md`。

```bash
python3 "<init-skill-dir>/scripts/manage_repo_baseline.py" show \
  --baseline-dir "<repo-baseline-dir>" --pattern-id "<PATTERN-ID>"
```

这是细粒度复用的**第一道防线**，第二道在 Phase C 的代码规范检视。

#### 2. 轮次顺序

| 层级 | 顺序 |
| --- | --- |
| Task 之间 | 按 `tasks.md` 原顺序，不重排 |
| Task 内部 | **固定先还原轮、后逻辑轮** |

一个 Task 内允许多轮 6 步：一个区块走一轮还原，区块还原完再走逻辑轮。每轮独立编号并标注形态，如 `Task 3 · 轮 1（还原）`、`Task 3 · 轮 2（逻辑）`。上游已按 [sdd-task-frontend-split.md](./references/sdd-task-frontend-split.md) 把整页样式切成独立还原 Task 时，该 Task 只有还原轮、其余 Task 只有逻辑轮，Task 间顺序仍由 `tasks.md` 决定。

#### 3. 6 步与两种失败证据

**6 步的编号、顺序、RED/GREEN 语义完全不变。** 唯一扩展是 Step ① 的失败证据分两形态：

| Step | 逻辑轮 | 还原轮 |
| --- | --- | --- |
| ① RED | 写失败的单测或接口集成测试，给出完整代码 | 运行冻结契约，生成 `restore-report-red.json`；至少一项 RED |
| ② 验 RED | 跑测试，确认按预期失败 | 核对 RED 的外部出处与实现定位；YELLOW 先结构化补证，仍无法判定才截图 |
| ③ GREEN | 最小实现让测试转绿 | 只修报告里的 RED |
| ④ 验 GREEN | 测试转绿 + 全量回归对齐 DEMAND-2 起点失败集合 | 重跑同一契约，生成 `restore-report-green.json`；无 RED、无 YELLOW |
| ⑤ REFACTOR | 按需 | 按需；重构后再跑同一契约 |
| ⑥ 记录证据并提交 | 落 `alpha-tests.md` 的 L4 / L3 记录节 | 账本只记契约/报告/缓存指纹与路径、摘要及可选截图 |

还原轮必须以冻结外部契约为失败证据；机器报告负责可确定判定，截图只用于机器盲区的选择性补证。

#### 4. 还原轮 6 步的动作

固定检查层级如下。`required_layers` 由契约逐条声明；静态通过不能替代 render-required 规则的 GREEN。

| 层 | 能力 | 是否截图 |
| --- | --- | --- |
| 静态预检 | 必需文案 / i18n key、仓内 token、禁用字面量、状态选择器 | 否 |
| 结构化渲染 | 注入 `<skill-dir>/scripts/collect_restore_facts.js`，读取 DOM、`getComputedStyle`、`getBoundingClientRect`、滚动尺寸和实际状态结果 | 否 |
| 视觉补证 | 阴影观感、字体栅格、图片裁切、复杂叠层等机器盲区 | 是，仅 YELLOW 项 |

**默认容差、检查模式与 R1–R6 的层映射由契约逐条声明，判据在 [restore-contract.md](./references/restore-contract.md)。** 本层只有一条约束：**无法安全表达容差的规则标 YELLOW，不得自行扩大容差。**

**四步的命令、参数与 JSON 形态只有一份，在 [restore-contract.md](./references/restore-contract.md) 第四节**（编译校验 → 静态预检 → 结构化渲染 → 报告）。下面只写这四步之上的判定规则。

**① RED — 运行冻结契约**

- 按 restore-contract.md 第四节跑 validate → static → 结构化渲染 → `report --phase red`，输出 `<story-dir>/restore-report-red.json`。**基线哈希不一致立即停止**（硬门禁 10）。
- 页面不可用时如实写 `page_available: false`，**不得伪造实际值**。
- 差异清单只按 [diff-list-template.md](./references/diff-list-template.md) 摘要该报告，不另写一份判定。
- 至少一项 RED 才能进入 Step ③。首轮全部 GREEN，取消该还原轮并记录「冻结契约已满足」；首轮只有 YELLOW，先走 Step ②，发现偏差转 RED 才进入实现，无偏差则取消还原轮。

**② 验 RED — 核出处、定位与 YELLOW**

- 每条 RED 必须同时有期望值、实际值、`baseline_id` / `design_fact_source` 和实现 locator；缺一视为报告执行失败，不进 ③。
- YELLOW 先补页面、fixture 或状态触发，再重跑结构化采集。仍无法结构化判定且契约要求 visual 层时，按 restore-contract.md 第六节查视觉缓存：命中只读复用，未命中才截原型写入新缓存目录。**机器可检项不截图**（硬门禁 12）。实现侧截图写 `<story-dir>/evidence/<Task 编号>-r<轮次>/`。
- 视觉补证发现偏差时，把 `visual-results.json` 对应规则写成 `red` 再重跑 RED 报告；**不得把主观观察直接塞进实现清单而绕过报告**。

**③ GREEN — 只修 RED**

- 只改 `restore-report-red.json` 中属于当前 Task 的 RED；YELLOW 不是实现任务，先补证。
- 取值走 `dev-baseline.md / 工程依据` 引用的仓库范式：间距、颜色、字号用仓内 token，不硬编码；有可复用的公共方法就用既有的。

**④ 验 GREEN — 同一契约重跑 + 回归**

- 重跑 ① 的同一条链，唯一差别是 `report --phase green`。**不得编辑 RED 报告得到 GREEN 报告**；该命令在 `overall` 非 `green` 时以退出码 3 阻断。
- 合法结论只有：全部规则已验证；或未实际匹配的规则逐条命中契约内的冻结豁免。任何 RED、任何未解决 YELLOW 都不是 GREEN；**不得为收口就地新增豁免**。
- 跑执行起点记录的质量命令。**判定基准是 DEMAND-2 的起点失败集合，不是「全绿」**：

| 与基线对照 | 判定 |
| --- | --- |
| 失败项集合与基线逐条相同 | 通过 |
| 出现基线之外的新失败项 | 不通过，修到消失为止 |
| 基线里本来红的项转绿 | 通过，在 Step ⑥ 记一行，不回滚也不追查 |

基线之内的既有失败项**不去修**——那是本 Story 之外的代码，动它就出了本 Task 的文件清单。

**⑤ REFACTOR — 按需**

- 只在本 Task 的文件清单内。重构后重跑 ④ 的同一契约与回归判定。
- 无可重构就写「无」，不为凑步骤造改动

**⑥ 记录证据并提交**

- 按 [references/alpha-tests-restore.md](./references/alpha-tests-restore.md) 在 `alpha-tests.md` 新增一条：契约哈希、RED/GREEN 报告指纹与路径、三色摘要、视觉缓存指纹与路径、可选实现截图。
- `alpha-tests.md` 不复制完整报告，不保存第二份偏差表；`restore-report-*.json` 是机器细节的唯一来源。
- 回填「AC ↔ 证据映射」：证据类型加「还原」，证据链填记录编号，状态填 `GREEN` 或 `Deferred`
- 勾 `tasks.md` 的 checkbox，提交

**特殊分支**

| 情形 | 处理 |
| --- | --- |
| 页面或截图能力缺失 | 按 [环境降级](./references/degradation-and-recovery.md#二环境降级) 表处理，**源码级结果只作 static 层事实，不得越级替代 render / visual 层** |
| 结构化渲染已尝试但采集脚本报错 | 判 RED（执行失败），不是 YELLOW；修采集入口或实现定位后重跑 |
| 已有 Story 没有 `restore-contract.json` | 继续按 `legacy-screenshot-v1` 旧截图证据流程读取与续跑，不迁移历史证据；新 Story 不得主动选择旧流程 |

#### 5. 编译硬约束

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出本 Task 的文件清单** | 停下上报，不自行扩大范围 |
| 2 | 禁止用**检查抑制手段**绕过（按仓库栈取值：`any` / `@ts-ignore` / `eslint-disable` / `# type: ignore` / `@SuppressWarnings` / `// @ts-nocheck` 等一切让类型检查或 lint 闭嘴的写法） | 仓内既有范式就是如此才可用，且必须在代码旁写明理由；无理由绕过是 Phase C 的阻断级 |
| 3 | **同一个报错连续修 3 次不成就停止** | 停下上报 |

第 3 条以「同一个报错」计数：改了写法但报错文本不变，算同一次链条的延续，不重新计数。

#### 6. 两类升级中断

| 触发 | 判据 |
| --- | --- |
| 编译修不动 | 同一个报错连续修 3 次未成 |
| 需越界改动 | 修好它必须改本 Task 文件清单之外的文件 |

两者都按 P7 上报，**不自行决定**，同一时刻攒到的多个问题合并一轮。每个问题必须写出：报错原文或阻塞点、要改的文件、它为什么在清单外、推测与理由。

等待回答期间**停在当前 Task**：不跳过它做下一个、不用检查抑制手段临时糊过去、不把改动范围先扩出去再补问。

#### 7. 进度真相与落账

- **`tasks.md` 的 checkbox 是唯一进度真相。** 完成一步勾一步，不批量补勾，不在别处另记一份进度
- Step ⑥ 把证据落进 `alpha-tests.md`：还原轮进「还原证据记录」节，逻辑轮进 L4 / L3 记录节，两者都回填 AC ↔ 证据映射。**不另开第二本账**
- 上游未声明对接模式且接口实际不可用时，降级为静态实现模式，把受影响的 AC 标 `Deferred` 并写明原因与解除条件。**不得拿豁免顶替 `Deferred`**
- 全部 Task 的 checkbox 勾完、`alpha-tests.md` 无缺口，才进 Phase C
- Step ⑥ 按实际报告状态落账：**有未解决 YELLOW 就不能勾本轮 GREEN**，按 [还原 YELLOW 的放行通道](#还原-yellow-的放行通道) 处理

---

### Phase C — 并行检视

四个子代理同一轮并行，各自穷尽自己的维度、产出分级结论，主 agent 汇总进 `<story-dir>/dev-review.md`。**编号、默认级别、覆盖规则与汇总口径以 [references/review-dimensions.md](./references/review-dimensions.md) 为准；具体检查动作、前置校验和输出格式以各子代理提示词为准。**

#### 1. 派发前自检

主 agent 自己做。三项缺一不进 Phase C：

| 项 | 判据 | 不满足时 |
| --- | --- | --- |
| 全部 Task 已 GREEN | `tasks.md` 的 6 步 checkbox 全部勾完 | 回 Phase B，从第一个未完成 Task 继续 |
| `alpha-tests.md` 无缺口 | 每条 AC 有证据链；还原轮记录含契约哈希、RED/GREEN 报告指纹与路径、摘要及适用的视觉缓存引用 | 回 Phase B 补记录 |
| `dev-baseline.md` 已冻结 | 基线头「冻结状态」为 `已冻结 ✅` | 回 Phase A 走确认门 |

再按 [前置产物校验](#前置产物校验) 核对四份检视各自的终止级前置。

#### 2. `<base-ref>` 的追加

`review-convention` 与 `review-quality` 需要本 Story 的改动 diff，两者都实现了三级取法：给了 `<base-ref>` 就用它，没给自己从 git 状态推，都取不到才返回前置缺失。**能拿到就传**，只追加进这两份的取值表，另外两份不加。

| 情形 | 动作 |
| --- | --- |
| 本 Story 开工前记录过起点提交 | 追加，取值为该提交 |
| 能定位与基线分支的分叉点，且分支上只有本 Story 的提交 | 追加，取值为分叉点提交 |
| 分支上混有其他 Story 的提交，切不干净 | 不追加，让子代理走第 2 级自推 |
| 目标仓不是 git 仓，或 git 状态读不到 | 不追加 |

**不确定就不传。** 传错的 `<base-ref>` 比不传更糟：子代理会把它当权威取法，检视范围直接错到别的 Story 上，而回传表头的取法看起来完全正常。

#### 3. 并行派发

同一轮发出，不串行：

| 子代理 | prompt |
| --- | --- |
| 布局与响应式检视 | `agents/review-layout.md` + 路径变量取值表 |
| 代码规范检视 | `agents/review-convention.md` + 取值表（含 `<base-ref>`，按第 2 节） |
| 质量检视 | `agents/review-quality.md` + 取值表（含 `<base-ref>`，按第 2 节） |
| 功能自测试 | `agents/self-test.md` + 路径变量取值表 |

**代码规范检视与质量检视不得合并成一个子代理**：前者以 REPO-3 范式作客观基准，后者靠通用工程判断，合并会让客观判断被主观判断稀释。

#### 4. 前置缺失与「未执行」

子代理返回 `前置缺失：<清单>` 时**不重跑**，按来源分两条路：

| 来源 | 处理 |
| --- | --- |
| DEMAND-2 已记录、已按硬门禁 4 告知过用户的 Story 特有限制 | **不再走 P7 追问**，直接记「未执行」并写明原因，进第 7 节汇总 |
| 其余前置缺失（产物真的不在、基线没冻结、Task 没勾完） | 按 P7 把缺失清单交给用户 |

第一条的理由：那个降级用户已经知道了，再问一遍等于同一件事打断两次（P1）。哪份降级、哪份终止见 [环境降级](./references/degradation-and-recovery.md#二环境降级)。

**「未执行」必须一路显式带到收口**——`dev-review.md` 的检视基准表、Phase D 的收口结论、最终输出的第一行，三处都要出现。**不得静默跳过，不得因为少一份检视就宣告全部通过。**

#### 5. 回传校验

四份各按自己提示词「输出格式」节的自检清单逐项核对。不合格退回重跑一次，仍不合格按 P7 上报。

**`待主 agent 核豁免` 是主 agent 的活，不是子代理的缺陷。** 收到这个标记，对着 `dev-baseline.md` 豁免表逐条定夺：命中 `EX-n` 的从报告里删掉并记一行「命中 `EX-n`，不报」；未命中的按 [review-dimensions.md](./references/review-dimensions.md) 规则 3 判阻断级。

#### 6. 截图归档

子代理唯一允许的写入是截图文件，写在临时目录，路径在回传表头给出。临时目录随时会被清掉，所以由主 agent 归档：

- 把被结论引用到的截图逐个复制到 `<story-dir>/evidence/review/`，未被引用的不归档
- 文件名加检视前缀避免撞名：`layout-<结论编号>.png`、`self-test-<基线编号>.png`
- 复制完把 `dev-review.md` 的截图列改写为归档路径，**不保留临时路径**

复制不到（文件已不在）时，该条结论的截图列写 `截图丢失：<临时路径>`；丢的是**阻断级**结论的截图，退回重跑那一份检视——阻断级没有证据就没有让人复核的余地。

#### 7. 汇总落盘

按 [review-dimensions.md](./references/review-dimensions.md) 第五节的口径合并四份回传（去重取高、不改级别、Open Question 与 Deferred 候选单独成节），写入 `<story-dir>/dev-review.md`。**模板在 [story-artifact-templates.md](./references/story-artifact-templates.md) 第二节。**

**建议级不等于可以不写。** 它的定义是「不阻断收口」，不是「不进报告」。

---

### Phase D — 收口

主 agent 自己做，不派发。目标只有一个：**把 `dev-review.md` 的阻断级清零，或者在清不掉时把决定权交回用户。**

#### 1. 阻断级修复

逐条修，顺序按阻断级表的编号。三条约束与 Phase B 第 5 节同源：

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出 Phase C 的 diff 范围**（本 Story 改动过的文件） | 停下，进第 3 节上报 |
| 2 | 禁止用检查抑制手段绕过（同 Phase B 第 5 节第 2 条） | 这本身就是 `C6` 的阻断级，绕过等于自造一条新的 |
| 3 | 同一个报错连续修 3 次不成就停止 | 停下，进第 3 节 |

**不得把改不动的阻断级降为建议级。** 级别只由 review-dimensions 第二节的四条规则决定。

#### 2. 修完重跑

一轮修完，**回 Phase C 重跑四份检视**（未执行的那份仍不执行）。代码已经变了，旧结论一律作废；只重跑「自认为被波及」的那几份，等于用修复者的判断替代检视。

**修复—重跑最多两轮。** 第二轮结束仍有阻断级未清零，进第 3 节，不开第三轮。

#### 3. 修不掉时按 P7 上报

五类攒在同一轮一次问完（P1）：阻断级修不掉、需越界改动、Open Question 待决、`Deferred` 待判、[还原 YELLOW 请求放行](#还原-yellow-的放行通道)。每条写出：结论编号、为什么修不掉或放不下、要改哪个文件且它为什么在范围外、推测与理由。

**上报之后停在 Phase D**：不出三行索引、不写收口结论、不勾任何东西。**不得自行降级为建议级，不得静默收口。**

#### 4. `Deferred` 判定

功能自测试回传的「Deferred 候选」只是候选，判不判由主 agent 定：

| 情形 | 判定 |
| --- | --- |
| 卡在外部依赖（接口未就绪、需后端造错误码、缺权限账号），本阶段解除不了 | 判 `Deferred`，在 `alpha-tests.md` 的 AC ↔ 证据映射状态列标注，写明原因与解除条件 |
| 本阶段跑得通，只是没跑 | 不判，跑完再说 |
| 拿不准是不是外部依赖 | 进第 3 节的 P7，交用户定 |

**带 `Deferred` 标记的 AC 不计为已验收**（硬门禁 5），不进覆盖率。**不得拿豁免 `EX-n` 顶替 `Deferred`**：豁免是「已经决定就这么做，且这么做是对的」，`Deferred` 是「想做但外部依赖没就绪」。

#### 5. 落账

| 文件 | 动作 |
| --- | --- |
| `<story-dir>/dev-review.md` | 阻断级表的「修复状态」逐条填「已修（复跑结论）」；写「收口结论」节 |
| `<story-dir>/alpha-tests.md` | 功能自测试实测结果贴回对应 `F<n>-<m>` 行；AC ↔ 证据映射填状态，`Deferred` 附原因与解除条件 |
| `<story-dir>/dev-baseline.md` | 收口期间动过基线的，变更记录已登记且已重新请用户确认（硬门禁 8） |
| `<story-dir>/evidence/review/` | 归档完成，`dev-review.md` 中无临时截图路径残留 |

「收口结论」节固定三块：**四份检视的执行状态**（未执行的写原因）、**阻断级清零情况**、**未验收项清单**（`Deferred` 的 AC、因检视未执行而未覆盖的维度）。

#### 6. 出门

逐条核对 [退出门禁](#退出门禁)，全部满足才出 [最终输出](#最终输出) 的三行索引。有一条不满足而又不属于第 3 节的上报情形，回第 1 节。

---

## 退出门禁

十条逐条核对，全部满足才出三行索引。**不满足就不是完成**，不得以「大部分都过了」收口。

| # | 门禁项 | 判据 |
| --- | --- | --- |
| 1 | Task 全部完成 | `tasks.md` 的 6 步 checkbox 全部勾完，无批量补勾、无别处另记的第二本进度 |
| 2 | 还原报告 GREEN | `restore-report-green.json` 无 RED、无 YELLOW；全部规则已验证或逐条命中契约内冻结豁免。因环境能力缺失而无法消除的 YELLOW 走 [放行通道](#还原-yellow-的放行通道) |
| 3 | 阻断级为 0 | `dev-review.md` 阻断级表全部为「已修（复跑结论）」 |
| 4 | 门禁兜底九项无命中 | 判据在 [review-dimensions.md](./references/review-dimensions.md) 规则 1，逐条核对 |
| 5 | 确证的功能缺陷为 0 | 能给出**具体触发操作序列**且会产生错误结果的发现，一条不剩（规则 2） |
| 6 | 冻结基线无一行不成立 | 未命中 `EX-n` 却证明某条 `R<n>-<m>` / `F<n>-<m>` 不成立的发现，一条不剩（规则 3） |
| 7 | 回归未变差 | test / typecheck / lint / build 的失败项集合与 DEMAND-2 起点逐条相同或更好；`REG-n` 无「变差」；缺起点记录时为 `无基线可比`，**不得判定为通过** |
| 8 | 证据可追溯 | `alpha-tests.md` 每条 AC 都有证据链与状态；还原记录能追到契约/报告指纹与路径及适用的视觉缓存；`dev-review.md` 的截图全部指向 `<story-dir>/evidence/review/` |
| 9 | `Deferred` 未混进已验收 | 不进覆盖率、不拿豁免顶替，原因与解除条件已写明 |
| 10 | 未执行的检视已显式披露 | `dev-review.md` 检视基准表与收口结论都写明了哪份未执行、为什么；最终输出第一行带状态限定 |

第 4 条的九项**不是穷举**，第 5 与第 6 条补足其余情形。

第 5 条的**「确证」是硬条件**，两个方向都要守：给不出触发序列的推测不适用本条，不得拿「万一将来出问题」拖住收口；反过来，能复现的错误行为也不许因为「还没写出序列」被推出门禁——写出来即可。

四份检视未执行时能不能出门，分三档：

| 未执行的检视 | 能否收口 | 理由 |
| --- | --- | --- |
| 代码规范检视 / 质量检视 | **不能** | 两份都是静态检视，不依赖环境；跑不了说明工程依据、仓库范式或 diff 真的缺失，补得回来 |
| 布局与响应式检视 | 可以，但必须显式披露 | 还原轮 Step ④ 已逐区块对过原型，缺的是跨页、真实数据、多视口这一层。报告中**不得声称 R3 / R4 / R5 / R6 在这一层已验证** |
| 功能自测试 | **不能**，除非用户在 Phase D 第 3 节的 P7 中明确同意，且受影响 AC 全部标 `Deferred` | F2 是 AC 的直接判定，没跑就是 AC 未验证，直接命中第 4 条的「AC 未覆盖」 |

### 还原 YELLOW 的放行通道

YELLOW 的成因分两类，**只有第一类可以放行**：

| 成因 | 能否放行 |
| --- | --- |
| **环境能力缺失**：没有 `<browser-driver>`、起不了页面、无截图能力，且已按 [环境降级](./references/degradation-and-recovery.md#二环境降级) 登记进 `dev-baseline.md` 降级项并告知过用户 | 可以，按下面四条 |
| **本阶段做得到只是没做**：fixture 造得出却没造、状态触发没实现、locator 没接对、采集脚本报错 | **不能**。补齐后重跑同一契约，这是实现任务不是环境限制 |

第一类的放行四条缺一不可：

1. **用户在 Phase D 第 3 节的 P7 中明确同意**，问题里逐条列出要放行哪些规则、缺的是哪项能力、补上后怎么验。
2. **每条被放行的规则在 `alpha-tests.md` 里标 `Deferred`**，写明原因与解除条件；受影响的 AC 同样标 `Deferred`，**不计为已验收**（硬门禁 5）。
3. **`dev-review.md` 的收口结论与检视基准表逐条列出**放行的规则编号。
4. **最终输出第一行带状态限定**，写明「还原 <N> 条规则未验证」。

**不得用放行通道处理第二类，不得就地新增豁免顶替，不得把 YELLOW 改写成 GREEN。** 放行的语义是「这条没验证，且大家都知道它没验证」，不是「这条通过了」。

## 降级与失败恢复

**判据全在 [degradation-and-recovery.md](./references/degradation-and-recovery.md)**，缺能力、缺产物或中断重跑时读它。本节只留三条不查表也要记住的：

- **任何需求级降级都必须可见**：在 `dev-baseline.md` 的「降级项」登记、在受影响证据中标注、在最终输出里带出来（硬门禁 4）。
- **仓库级能力失效回 Phase -1**，不得写成 Story 降级项继续开工（硬门禁 0）。
- **重跑时 `tasks.md` 的 checkbox 是唯一进度真相**，从第一个未完成 Task 继续；`dev-review.md` 的四份检视一律重跑，不复用旧结论。

## 最终输出

三行索引（P5）：

```
✓ sdd-dev-frontend 完成
产出：<story-dir>/dev-review.md
下一步：<按下表取一条>
```

第一行在有降级或未验收项时**带一句状态限定**，仍是三行：

| 状态 | 第一行 |
| --- | --- |
| 全部通过 | `✓ sdd-dev-frontend 完成` |
| 有检视未执行 | `✓ sdd-dev-frontend 完成（布局检视未执行：执行起点截图为「不可」— <原因>）` |
| 有 `Deferred` | `✓ sdd-dev-frontend 完成（<N> 条 AC 标记 Deferred，不计为已验收）` |
| 还原存在 YELLOW，成因是本阶段做得到只是没做 | **不得完成**；补齐页面 / fixture / 状态触发后重跑同一契约 |
| 还原 YELLOW 已按 [放行通道](#还原-yellow-的放行通道) 经用户同意 | `✓ sdd-dev-frontend 完成（还原 <N> 条规则未验证：缺 <能力>，已标 Deferred）` |
| 基线源降级 | `✓ sdd-dev-frontend 完成（无 HTML 原型，还原基线为参照页 <路由> 类比 / 文字规格，非原型对照）` |
| 多项并存 | 括号内用 `；` 连写 |

状态限定不算「重新摘要」，它是硬门禁 4 与硬门禁 5 的落点：**这两件事被折叠掉，用户就会以为全部通过。**

「下一步」只给一条指令，按优先级取第一条命中的：

| 优先级 | 条件 | 文案 |
| --- | --- | --- |
| 1 | 有检视未执行 | `补齐<缺的能力>后说「重跑<该检视>」` |
| 2 | 有 `Deferred` | `<解除条件>满足后说「只跑功能自测试」，回填 <编号> 的 AC 状态` |
| 3 | 有建议级结论 | `复核 dev-review.md 的 <N> 条建议级，决定要不要另开一个 Story 处理` |
| 4 | 均无 | `本 Story 已可验收，回外层调度取下一个 Story` |

产出行只给 `dev-review.md` 一条路径——它的检视基准表指得到其余全部产物。

## 工件管理

| 工件 | 路径 | 产出阶段 | 新建 / 扩容 |
| --- | --- | --- | --- |
| 仓库 baseline 两份 Markdown | `<repo-baseline-dir>/repo-baseline.md`、`onboarding-report.md` | Phase -1 由 `sdd-init-frontend` 生成 | 本 skill 只校验并按 Section / ID 选读 |
| `dev-baseline.md` | `<story-dir>/dev-baseline.md` | Phase 0 写 `DEMAND-2`，Phase A2 追加 `DEMAND-3` | 新建 |
| `restore-contract.json` | `<story-dir>/restore-contract.json` | Phase A2 确认后由脚本编译 | 新建；基线哈希不一致时拒绝执行 |
| `restore-adapter.json` | `<story-dir>/restore-adapter.json` | Phase A2 确认后 | 新建；只存实现 locator、源码范围与采集模式 |
| `restore-report-red.json` / `restore-report-green.json` | `<story-dir>/` | Phase B Step ① / ④ | 同一契约生成的机器报告 |
| `dev-review.md` | `<story-dir>/dev-review.md` | Phase C 汇总，Phase D 写收口结论 | 新建 |
| `design-facts.json` | `<design-spec-dir>/design-facts.json` | Phase A1 脚本输出 | 确定性重生成；相同内容不重写 |
| `design-tokens.md` / `interface-inventory.md` / `content-inventory.md` | `<design-spec-dir>/` | Phase A1 脚本输出 | 新建；已存在时按下方并发写规则 |
| 原型切分表 | `<design-spec-dir>/block-index.md` | Phase A1 `extract-prototype` | 新建，按哈希增量补行 |
| 区块规格 | `<design-spec-dir>/blocks/<区块名>.md` | Phase A1 `extract-block-spec` | 新建，一区块一文件；哈希失配才重写 |
| `alpha-tests.md` | `<story-dir>/alpha-tests.md` | Phase B Step ⑥、Phase D 回填 | **扩容上游文件**，结构见 [references/alpha-tests-restore.md](./references/alpha-tests-restore.md) |
| `tasks.md` | `<story-dir>/tasks.md` | Phase B | **只勾 checkbox**，不改内容 |
| 原型视觉缓存 | `<design-spec-dir>/visual-baseline/<缓存指纹>/` | Phase B Step ② | 仅 visual YELLOW 懒生成；`prototype.png` + `manifest.json`，不可变 |
| 实现侧视觉补证 | `<story-dir>/evidence/<Task 编号>-r<轮次>/` | Phase B Step ② / ④ | 仅 visual YELLOW 新建，命名按报告规则编号 |
| 检视截图 | `<story-dir>/evidence/review/` | Phase C 归档 | 新建，命名 `layout-<结论编号>.png` / `self-test-<基线编号>.png` |

**baseline 只有仓库级与需求级两层，都不写进 `<repo-root>`。** Requirement 和 Story 同属需求级，只按自然生命周期落盘：

| ID | 生命周期与产物 | 路径 | 何时作废 |
| --- | --- | --- | --- |
| `REPO-1～3` | 仓库环境/运行、质量、工程范式 | `<repo-baseline-dir>` | 对应 section 输入指纹变化 |
| `DEMAND-1` | Requirement 设计事实、区块规格、视觉缓存 | `<design-spec-dir>` | 原型指纹、区块哈希或视觉缓存键变化 |
| `DEMAND-2` | Story 范围、场景、`base-ref`、起点失败集合 | `<story-dir>/dev-baseline.md` | Story 或开工起点变化 |
| `DEMAND-3` | R1–R6、F1–F4、豁免与确认记录 | `<story-dir>/dev-baseline.md` | Story 变更，或经用户确认的基线变更 |

**`design-spec/` 属 Requirement 级，不得挪进 `<story-dir>`**——设计稿是整个需求一起给的，下一个 Story 直接拿哈希一致的区块规格用；挪错了每个 Story 会把同一份设计稿重抽一遍。

四条约定：

- **`design-facts.json` 内容变化时确定性重写；三份 Markdown 可能含人工命名审订，文档哈希一致时只读保留。** 区块规格一区块一文件，按内容哈希增量更新。
- **脚本输出由主 agent 落盘，subagent 一律只回传正文。** 脚本不是 subagent，主 agent 写入 `<design-spec-dir>` 与「subagent 不修改正式工件」不冲突。
- **`alpha-tests.md` 是验收追溯的唯一证据账本。** 机器报告是被账本按指纹引用的证据工件，不是第二本账；不得把报告内容复制进账本。
- **Story 不持有仓库范式正文。** `dev-baseline.md / 工程依据` 只保存 `PATTERN-*` / `REQ-DEC-*` 与 REPO-3 指纹；实现与检视按 ID 回读仓库唯一正文。

## 单步入口路由

**八个 subagent 不注册为独立 skill**（理由见 [CONTEXT.md](./CONTEXT.md#八个-subagent-不注册为独立-skill)）。用户用自然语言说要做哪一步，主 agent 先按 [前置产物校验](#前置产物校验) 校验，齐了就派发，缺了就明确告知缺什么。

| 用户意图（示例说法） | 派发目标 |
| --- | --- |
| 「初始化前端仓」「刷新仓库 baseline」「项目第一次接入」 | 路由 `sdd-init-frontend`；完成后若当前有 Story 则回 Phase -1，否则结束 |
| 「重抽设计稿规格」「重新解析设计稿」 | 走完 Phase A1：跑脚本 → `extract-prototype` → `extract-block-spec` ×N。**哈希一致的区块照常复用**，说「重抽」不等于强制全量重来 |
| 「`<区块名>` 的规格重来一份」「这个区块的规格不对」 | `extract-block-spec` 单实例，只覆写该区块那一份，切分表与其余区块不动 |
| 「只做勘察」「重跑勘察」 | `recon-spec` + `recon-codebase` 同一轮并行；说明只要一侧时派对应那一份 |
| 「重跑还原验证」「重新生成 GREEN 报告」 | 校验冻结契约 → 静态预检 → 结构化渲染 → 按需视觉补证 → 更新对应报告；不改契约与基线 |
| 「只补 YELLOW」「补视觉证据」 | 只处理报告中 YELLOW 的 `required_evidence`；机器可检项不截图，补证后重跑同一契约 |
| 「重跑布局检视 / 代码规范检视 / 质量检视 / 功能自测试」 | 对应的那一份：`review-layout` / `review-convention` / `review-quality` / `self-test` |
| 「重跑全部检视」「重新收口」 | 四份并行，走完 Phase C → Phase D |
| 「继续跑」「从上次断的地方接着来」 | 完整流程，按 [失败恢复](./references/degradation-and-recovery.md#四失败恢复) 定起点 |

六条规则：

1. **前置不齐不派发。** 按 P7 一轮告知缺什么、期望在哪，不逐个问、不自行补足、不拿相近文件顶替。
2. **派发方式与 Phase A / C 完全一致**，卡死巡检同样适用。
3. **说「重抽」不等于强制全量重来**：哈希一致的区块照常复用。
4. **单步检视的结果覆盖 `dev-review.md` 里对应那一份的小节**，并更新检视基准表中该份的执行状态与时间，其余小节不动。**不追加成第二份报告。**
5. **不动 `tasks.md` 的 checkbox**（进度只由 Phase B 推进），**跑完照样出三行索引**（P5），产出行指向被更新的那份产物。
6. **不是绕过门禁的口子。** 单跑一份检视不构成收口，`dev-review.md` 的阻断级仍要走完 Phase D 的清零流程。

## 前置产物校验

**前置判据只有一份，在各提示词的 §一。** 本 SKILL.md 不复制一份副本——两份判据必然漂移，而漂移的那一次会让主 agent 派出一个注定返回前置缺失的子代理。

派发前自查：读该提示词的 §一，逐条核对终止级前置。**明知不满足的那一份不派发**，按第 4 节记「未执行」。自查不替代子代理自己的前置校验，两道叠加；自查只为少花一轮空转。

「diff 可取」按三级取法判定：给了 `<base-ref>` → 用它；没给 → 子代理自己从 git 状态推（未合入基线分支的提交 + 已暂存 + 工作区未暂存的并集）；两条都取不到才算不可取。

- **子代理返回 `前置缺失：<清单>` 时不重跑**，也不自行补足或猜测，按 P7 交用户。唯一细则见 Phase C 第 4 节。
- **`extract-block-spec` 返回 `切分不合格：<清单>` 时同样不重跑**，但交的是 `extract-prototype`：切分表的锚点或粒度有问题，重派 `extract-prototype` 修切分表，再对受影响区块重派 `extract-block-spec`。两次仍不合格按 P7 上报。
- **不得为了让前置通过而改产物。** 典型是基线没冻结就把冻结状态改成 `已冻结 ✅`——冻结的语义是用户确认过，改状态位不等于确认。
