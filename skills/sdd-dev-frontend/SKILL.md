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
| 2 | 定四个需求路径；`tasks.md` 缺失且会话已聊清楚时先自动起草并经确认；跑一次 `REPO-2` 的质量命令记起点失败集合，定影响面分级，写 `dev-baseline.md` | 执行起点表写完 |
| 3 | 跑 `extract_design_spec.py extract`；有覆盖缺口先登记再确认；按候选段数取切分（≤ 3 直通道零子代理、4–10 主 agent 自切、> 10 派 `extract-prototype`），再按区块并行派 `extract-block-spec`；**同轮提前派 `recon-codebase`** | `<design-spec-dir>` 里区块规格齐了 |
| 4 | 派 `recon-spec`（`recon-codebase` 通常已提前派出），出 QA 基线与工程依据 | **确认门 → 用户确认 → 冻结 → 编译契约** |
| 5 | 按 `tasks.md` 逐 Task 走 6 步，还原轮用契约报告当 RED/GREEN 证据，每步勾 checkbox | checkbox 全勾完 |
| 6 | 四份检视同一轮并行，汇总进 `dev-review.md` | 四份都回传或已记「未执行」 |
| 7 | 阻断级清零（最多修—重跑两轮），核 [退出门禁](#退出门禁) | 出三行索引 |

三条最容易踩空的：**没有 `tasks.md` 且会话没聊清楚就不准开工**；**基线没冻结不准进 Phase B**；**报告有 YELLOW 不算完成**。

## 输出规范

八条，全文用 P1–P8 指代。

| # | 规则 |
| --- | --- |
| P1 | **单轮单决策。** 一轮输出只放一个决策点：请求确认、批量提问、宣告完成，三者不同轮 |
| P2 | **结构优于散文。** 多项内容一律用表格或列表；散文只用于单行摘要，不超过 2 句；不用「有问题现在提」这类模糊邀请语，换成明确行动指令 |
| P3 | **不解释过程。** 不写「现在我将开始…」「接下来进入 Phase X」，直接给结果 |
| P4 | **确认门用固定格式**（见下） |
| P5 | **最终输出是三行索引，不是报告。** 不重新摘要交互过的内容，不分「产出文件」「下一步」多个子章节；未经交互的新发现按 P8 附人话清单 |
| P6 | **零决策阶段内联**进下一个有决策的阶段，不单独占一轮。例外：结论出乎意料时单独一行告知 |
| P7 | **批量提问。** 同类问题合并一轮，用固定格式（见下），不逐条打散、不在每题后附段落解释 |
| P8 | **新发现必须人话进会话。** 检视与收口产生的、用户尚未在会话中见过的发现（建议级、Open Question、Deferred 判定），逐条用一句人话说清「现象 + 影响 + 要不要用户管」，编号只作句尾括号引用；**不得只给文件路径让用户自己去翻**——需要用户拍板或知悉的内容，会话是唯一界面，文件只是留档 |

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
| 0 执行起点 | 定位需求路径；`tasks.md` 缺失时判断能否自动起草；选择本次场景、记录 `base-ref` 与质量失败集合 | 主 agent | 写 `dev-baseline.md` 执行起点，直接进 A1（P6） |
| A1 规格抽取 | 脚本产出 `design-facts.json` + 三份人类可读清单，再划区块、逐区块出规格 | 主 agent（跑脚本）+ 子代理 ×0–(1+N)，按候选段数；`recon-codebase` 同轮提前派出 | 设计事实与区块规格齐备 → 进 A2。基线源不是 `原型` 时整段跳过 |
| A2 并行勘察 | 产出 QA 基线、还原契约规则草稿、代码事实清单 | 子代理 ×1–2（`recon-codebase` 常已提前派出） | **确认门**：用户确认后冻结基线并编译 `restore-contract.json`，才能进 B |
| B 实现 | 逐 Task 走 6 步 | 主 agent | `tasks.md` checkbox 全勾完 → 进 C |
| C 并行检视 | 布局 / 代码规范 / 质量 / 功能自测试 | 子代理 ×4 | 四份汇总进 `dev-review.md` → 进 D |
| D 收口 | 阻断级清零、落账、核退出门禁 | 主 agent | 退出门禁全过 → 三行索引 |

**只有下面这些时刻打断用户**，其余全程静默（P6）：

| 时刻 | 形式 |
| --- | --- |
| 仓库接入需要网络、秘密、外部账号或破坏性环境动作 | 沿用 `sdd-init-frontend` 的授权门；完成后自动返回 |
| Phase 0：路径变量缺失或有多个候选 | 一轮批量提问（P7） |
| Phase A：有环境降级项 | 输出里单独一行原句告知 |
| Phase A：「已知缺口」中有**无安全默认值、必须先答**的项 | 一轮批量提问，答完再出确认门（P1）；**有安全默认值的缺口不提问**，以工作假设随确认门同轮 |
| Phase A：基线产出完毕 | 确认门（P4） |
| Phase B：同一报错连修 3 次不成，或需改 Task 文件清单外的文件 | 一轮批量提问，同时攒到的合并一轮 |
| Phase C：某份检视未执行 | 单独一行告知 |
| Phase D：阻断级修不掉 / 需越界改动 / Open Question 待决 / `Deferred` 待判 | 一轮批量提问，四类攒在同一轮；上报后停在 Phase D 等回答 |
| 全部通过 | 三行索引（P5） |

---

## 硬门禁

0. **仓库 baseline 先于 Story 执行。** `repo-baseline.md` 不存在、Section 失效、readiness 为 `DRAFT/BLOCKED`，或 `READY_WITH_LIMITS` 的限制影响当前 Story 时，先完整执行 `sdd-init-frontend`；不得把仓库未就绪写成 Story 降级项继续开工。**例外只有一个**：失效由本 Story 自身改动引起，判据见 [Phase -1 细则](./references/phase-entry.md)。
1. **没有 `tasks.md` 不准开工。** 它是唯一执行清单，也是进度真相。缺失时先判断是否满足 [Phase 0 细则](./references/phase-entry.md) 第 2 步「`tasks.md` 缺失时的自动起草分支」的条件，都不满足才路由 `sdd-task`；不得跳过起草与确认直接臆造 Task List 开工。
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
| `tasks.md`（由 `sdd-task` 产出，标注本仓为 frontend；缺失且会话内容足够时，可由 Phase 0 第 2 步自动起草替代） | `<story-dir>` | 是 |
| `story-delta-frontend-design.md` | `<story-dir>` | 是（同上，可随 `tasks.md` 一并自动起草） |
| `alpha-tests.md` | `<story-dir>` | 是（不存在则由 `sdd-task` 补齐，或随 `tasks.md` 一并自动起草空骨架） |
| 目标前端仓可访问 | `<repo-root>` | 是 |
| [基线源](#基线源没有-html-原型时) 三档至少第 3 档成立 | — | 是 |
| HTML 原型 | `<prototype-dir>` | 否，缺失时降到第 2 或第 3 档 |
| `requirement-frontend-design.md` | `<requirement-dir>` | 否，缺失时记为已知缺口 |
| Test Design 用例 | 上游文档中引用的路径 | 否，缺失时记为已知缺口 |

仓库 baseline **不是**进入条件：缺失或失效时由本 skill 自动路由 `sdd-init-frontend`，初始化完成后回到同一 Story。

| 不适用场景 | 改用 |
| --- | --- |
| `tasks.md` 还没产出，且当前会话还没把 Story 范围、AC、还原基线聊清楚 | `sdd-task`；已经聊清楚时改用 Phase 0 第 2 步的自动起草分支，不必先跑 `sdd-task` |
| 需要改设计而不是执行设计 | `sdd-design` |
| 一次要覆盖多个 Story 或多个仓 | 外层调度，逐个 Story 分别运行本 skill |
| 纯后端仓 | 本 skill 不适用 |

本阶段对上游 `tasks.md` 的两份要求由使用者带到 `sdd-task` 落地（[amendments](./references/sdd-task-amendments.md)：Step ① 两种失败证据形态、一个 Task 内多轮 6 步；[frontend-split](./references/sdd-task-frontend-split.md)：前端 Task 的切分方式）。本 skill 只执行、**不改 `tasks.md` 的内容**；不符合这两份要求时照常执行，按各自文档里的兜底走，不回头改上游产物。

对上游 `sdd-design` 的要求（设计稿盘点前移到设计阶段、产出能力映射表）同样只落成文档：[sdd-design-amendments](./references/sdd-design-amendments.md)。**本 skill 不依赖它已落地**——`<design-spec-dir>` 已存在且原型指纹一致时 Phase A1 自动复用，否则照常全量跑。

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
| `<base-ref>` | **可选**。本 Story 起点的 git 引用，供代码规范检视与质量检视取改动 diff | 开工前记录的起点提交，或与基线分支的分叉点；取法见 [Phase C 细则](./references/phase-review-closeout.md) 第 2 节 |
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

**派给 `review-layout` / `self-test` 时，`<browser-driver>` 不是档位名，而是可执行启动说明。** 路径变量取值表必须写明：Phase -1 取到的**具体档位**，以及该档下第 4 步实际验证过的启动方式（命令、端口、目标 URL、健康探针怎么做）。子代理**必须直接使用这份记录启动页面**，**不得自行只探测某一个连接器、发现它为空就判定环境缺失**；只有记录的那一档驱动本身、按记录的方式实际尝试后仍然失败，才能判环境缺失。

## subagent 派发约定

- **只把 `<skill-dir>/agents/<name>.md` 的路径给子代理，让它自己读全文并执行**，不摘要、不改写、不复述要点，也不把全文抄进派发消息——抄一遍等于让主 agent 白付一份提示词的上下文。
- **在路径之后追加一段「路径变量取值」表**，给出 `<repo-root>` / `<repo-baseline-dir>` / `<story-dir>` / `<requirement-dir>` / `<design-spec-dir>` / `<skill-dir>` 的实际值；派 `review-layout` / `self-test` 时再加 `<browser-driver>`，取值必须是**具体档位 + Phase -1 第 4 步实际验证过的启动方式**（命令、端口、目标 URL、健康探针），不能只写「会话内工具」这类笼统描述。提示词文件本身不含硬编码路径。
- **`<prototype-dir>` 只传给 `extract-prototype` 与 `extract-block-spec`。** 其余六份被硬门禁 9 禁止读原型，传给它们等于邀请违规。
- 派 `extract-block-spec` 时，在路径变量表后再追加四行实例输入：`区块名`、`页面 / 路由`、`区块切片路径`、`目标视口`。切片路径必须指向主 agent 用 `block --anchor` 刚生成的那一个临时文件，不得给整份原型。
- **子代理不再委派，不修改项目文件或正式工件。** 布局检视与功能自测试只允许把截图写入临时目录；其他产物以正文回传并由主 agent 落盘——并行子代理写同一个正式工件必然互相覆盖。
- **同一 Phase 内的多个子代理在同一轮并行派发**，不串行。
- 子代理返回 `前置缺失：<清单>` 时**不重跑、不自行补足、不猜测**，按 P7 把清单交给用户（Phase C 有一条细则，见 [Phase C 细则](./references/phase-review-closeout.md) 第 4 节）。
- 回传后按该提示词的「输出格式」逐项校验。不合格退回重跑一次；仍不合格按 P7 上报，不带着缺口往下走。
- `review-layout` / `self-test` 对 `<browser-driver>` 的使用约束见 [浏览器驱动](#浏览器驱动) 末段，此处不重复。

| 提示词 | 职责 | Phase | 回传落盘 |
| --- | --- | --- | --- |
| `agents/extract-prototype.md` | 划页面 → 区块、审组件命名与变体归并 | A1 | `<design-spec-dir>/block-index.md`（原型切分表）；对 `interface-inventory.md` 的命名修订 |
| `agents/extract-block-spec.md` | 单区块规格，**按区块并行多实例** | A1 | `<design-spec-dir>/blocks/<区块名>.md`，一区块一文件 |
| `agents/recon-spec.md` | 规格侧勘察 | A2 | `<story-dir>/dev-baseline.md` |
| `agents/recon-codebase.md` | 代码侧勘察：选择 Requirement 决策与仓库 `PATTERN-*` | A1 提前派出 / A2 | 合并进 `<story-dir>/dev-baseline.md` 的“工程依据”，不创建独立文件 |
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
| 四份检视任一 | 记「未执行（子代理两次卡死）」，按 [Phase C 细则](./references/phase-review-closeout.md) 第 4 节披露；能否收口按 [退出门禁](#退出门禁) 末尾三档表判 |

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

**进入 P7 提问前，必须先判定该问题在 repo（仓库代码）与 prototype（`<design-spec-dir>` 产物）两侧是否已有直接证据；只有判定为 `user-only` 或 `conflict` 的问题才能进入 P7，能从 repo 或 prototype 直接读出答案的不得提问，必须直接把证据写入基线。** 分类判据见 [qa-baseline-template.md](./references/qa-baseline-template.md)。

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

七个 Phase 的执行细则按阶段下沉到四份细则文件，**进入某个 Phase 前完整读取对应文件再动手**；单步入口只读涉及的那份。细则与本文冲突时，以本文的硬门禁与输出规范为准。

| Phase | 细则 |
| --- | --- |
| -1 仓库接入门 · 0 执行起点 | [phase-entry.md](./references/phase-entry.md) |
| A1 规格抽取 · A2 并行勘察 | [phase-spec.md](./references/phase-spec.md) |
| B 实现 | [phase-implementation.md](./references/phase-implementation.md) |
| C 并行检视 · D 收口 | [phase-review-closeout.md](./references/phase-review-closeout.md) |

## 退出门禁

十一条逐条核对，全部满足才出三行索引。**不满足就不是完成**，不得以「大部分都过了」收口。

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
| 11 | 待用户输入项已在会话交代 | 每条 Open Question 已按 P7 问出答案，或已在会话中明确告知并记「用户已知悉」；建议级与 Deferred 判定已按 P8 人话摘要进会话。**落在文件里不算交代** |

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
- **重跑时 `tasks.md` 的 checkbox 是唯一进度真相**，从第一个未完成 Task 继续；中断后重跑的场景 `dev-review.md` 的四份检视一律重跑、不复用旧结论（Phase D 修复后的重跑不在此列，按其冻结映射表取）。

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

**三行之后按 P8 附「新发现清单」**（没有就不附）：建议级与 Open Question 逐条一句人话——现象、影响、要不要处理，编号放句尾括号；有 `Deferred` 判定的写明判了哪几条、为什么。清单不替代 `dev-review.md` 的完整证据，但**用户不开任何文件就能知道有什么事等着拍板**。

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
| `alpha-tests.md` | `<story-dir>/alpha-tests.md` | 缺失时 Phase 0 第 2 步起草空骨架；否则视为上游产出，Phase B Step ⑥、Phase D 回填 | 缺失则新建（起草）；存在则**扩容上游文件**，结构见 [references/alpha-tests-restore.md](./references/alpha-tests-restore.md) |
| `tasks.md` | `<story-dir>/tasks.md` | 缺失且会话内容足够时 Phase 0 第 2 步起草；否则视为上游产出 | 缺失则新建（起草，经确认门）；存在则**只勾 checkbox**，不改内容 |
| `story-delta-frontend-design.md` | `<story-dir>/story-delta-frontend-design.md` | 缺失时随 `tasks.md` 一并由 Phase 0 第 2 步起草；否则视为上游产出 | 缺失则新建（起草）；存在则本 skill 不改 |
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
| 「没有 tasks.md，按我们聊的内容起草」「这个需求没走 sdd-task，直接开始」 | Phase 0 第 2 步的自动起草分支：主 agent 判断会话内容是否够起草，够就起草并过确认门，不够按 P7 先问缺口 |
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

派发前自查：读该提示词的 §一，逐条核对终止级前置。**明知不满足的那一份不派发**，按 [Phase C 细则](./references/phase-review-closeout.md) 第 4 节记「未执行」。自查不替代子代理自己的前置校验，两道叠加；自查只为少花一轮空转。

「diff 可取」按三级取法判定：给了 `<base-ref>` → 用它；没给 → 子代理自己从 git 状态推（未合入基线分支的提交 + 已暂存 + 工作区未暂存的并集）；两条都取不到才算不可取。

- **子代理返回 `前置缺失：<清单>` 时不重跑**，也不自行补足或猜测，按 P7 交用户。唯一细则见 [Phase C 细则](./references/phase-review-closeout.md) 第 4 节。
- **`extract-block-spec` 返回 `切分不合格：<清单>` 时同样不重跑**，但交的是 `extract-prototype`：切分表的锚点或粒度有问题，重派 `extract-prototype` 修切分表，再对受影响区块重派 `extract-block-spec`。两次仍不合格按 P7 上报。
- **不得为了让前置通过而改产物。** 典型是基线没冻结就把冻结状态改成 `已冻结 ✅`——冻结的语义是用户确认过，改状态位不等于确认。
