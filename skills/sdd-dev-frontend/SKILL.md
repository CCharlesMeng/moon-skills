---
name: sdd-dev-frontend
description: 在 sdd-task 产出 tasks.md 后，把「一个前端仓 × 一个 Story」执行成可验收的代码与证据；开工前复用仓库级 REPO-1～REPO-3，baseline 缺失或失效时自动路由 sdd-init-frontend 并在初始化后返回。流程为仓库接入门 → Story 执行起点 → 设计事实 → QA 判定 → 逐 Task 六步实现 → 并行检视 → 收口。用于执行前端 Story、按 HTML 原型还原页面，或续跑其中的规格抽取、勘察、实现与检视步骤；还原轮以冻结外部契约的红黄绿机器报告为主要失败证据。
---

# 前端开发执行

## 概述

把上游 `tasks.md` 和 HTML 原型变成前端代码，并留下能追溯到 AC 的证据。仓库公共事实不再每个 Story 重抽：`sdd-init-frontend` 维护 `REPO-1～REPO-3`，本 skill 只生成当前需求的 `DEMAND-1～DEMAND-3`。两层六类的字段、目录和失效规则见 [baseline contract](../sdd-init-frontend/references/baseline-contract.md)。

两个机制支撑它：

- **Step ① 的失败证据分两形态。** 6 步的编号、顺序、RED/GREEN 语义完全不变。逻辑补全用失败的单测或接口集成测试；还原用**冻结外部设计契约的机器报告**。报告有 RED 才进入实现；YELLOW 必须补证，不能冒充 GREEN；截图只处理机器无法可靠判断的项。契约的基线在原型与已确认 QA 基线，而不在自己写的实现断言。
- **开工前冻结 QA 基线。** 标准不冻结，遇到难啃的地方就会被悄悄放宽，最后报告照样被写成 GREEN、AC 照样打勾。所以十个维度固定，用户确认后冻结，开工中要改必须重新确认。

一次运行的作用域是**一个前端仓 × 一个 Story 的 `tasks.md`**，跨仓与多 Story 由外层调度。术语见 [CONTEXT.md](./CONTEXT.md)，两条关键决策见 [docs/adr/](./docs/adr/)。

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
4. **需求执行限制必须显式。** 仅 Story 特有且仓库初始化无法预先消除的限制可写入 `dev-baseline.md` 执行起点。页面或浏览器等仓库必需能力失效时回 Phase -1；可继续的限制仍按影响让 render/visual 规则保持 YELLOW。**不得用源码检查把渲染规则写成 GREEN，不得假装做过截图。**
5. **带 `Deferred` 标记的 AC 不计为已验收。** 不得静默通过，不得算进覆盖率。
6. **subagent 只读。** 不改任何文件、不再委派。产物由主 agent 落盘。
7. **不修改上游设计、不发明响应式规格、不决定对接模式、不跨仓改动。** 对接模式严格执行 `requirement-frontend-design.md` 的声明；上游没有响应式规格时只承诺「不破」。
8. **开工后放宽任何标准，必须在 `dev-baseline.md` 记录变更内容与理由并重新请用户确认。** 禁止静默修改。
9. **除 `extract-prototype` / `extract-block-spec` 外，任何角色不得读取原型 HTML 源码。** 主 agent 与其余六份子代理一律以 `<design-spec-dir>` 的产物为准。两个例外：用浏览器打开原型作选择性视觉补证（图像进上下文，源码不进）；Step ② / ④ 出现争议时按锚点回查**单个**区块，且必须在报告对应规则的补证记录里登记回查了哪一段。用 `wc` / `rg` 取统计量（行数、引用计数、class 命中位置）不算读取源码，取回正文才算。
10. **`dev-baseline.md` 与 `restore-contract.json` 哈希不一致时拒绝执行。** 不得自动重写哈希、不得以当前实现反推期望值；基线确需变更时走硬门禁 8。
11. **还原报告状态只有 RED / YELLOW / GREEN。** 有 RED 即整体 RED；无 RED 但有 YELLOW 即整体 YELLOW；全部规则已验证或命中冻结豁免才 GREEN。YELLOW 不是较轻的 RED，也不是基本通过。
12. **机器可检项目不截图。** 只有阴影观感、字体栅格、图片裁切、复杂叠层等机器无法可靠判断的规则进入视觉补证；视觉缓存只在存在这类 YELLOW 时生成。
13. **仓库范式只有一个所有者。** `PATTERN-*` 正文只在仓库级 `repo-baseline.md / REPO-3`；Requirement 只保存跨 Story 决策引用，Story 只在 `dev-baseline.md` 保存采用的 ID 与 REPO-3 指纹。不得生成 Story 级范式卡片或 `codebase-brief.md`。

## 何时使用

进入条件（全部满足）：

- 上游 `sdd-task` 已产出本 Story 的 `tasks.md`，且标注本仓为 frontend
- 目标前端仓可访问
- [基线源](#基线源没有-html-原型时) 三档中至少第 3 档成立：有 HTML 原型，或有可类比的存量参照页，或 `story-delta-frontend-design.md` 里有可落地的文字规格

仓库 baseline 不是进入条件：缺失或失效时由本 skill 自动路由 `sdd-init-frontend`，初始化完成后回到同一 Story。

| 不适用场景 | 改用 |
| --- | --- |
| `tasks.md` 还没产出 | `sdd-task` |
| 需要改设计而不是执行设计 | `sdd-design` |
| 一次要覆盖多个 Story 或多个仓 | 外层调度，逐个 Story 分别运行本 skill |
| 纯后端仓 | 本 skill 不适用 |

## 前置条件

| 文件 | 位置 | 必需 |
| --- | --- | --- |
| `tasks.md` | `<story-dir>` | 是 |
| `story-delta-frontend-design.md` | `<story-dir>` | 是 |
| HTML 原型 | `<prototype-dir>` | 否，缺失时按 [基线源](#基线源没有-html-原型时) 降到第 2 或第 3 档 |
| `alpha-tests.md` | `<story-dir>` | 是（不存在则由 `sdd-task` 补齐后再来） |
| `requirement-frontend-design.md` | `<requirement-dir>` | 否，缺失时记为已知缺口 |
| Test Design 用例 | 上游文档中引用的路径 | 否，缺失时记为已知缺口 |

本阶段对上游 `tasks.md` 的两份要求由使用者带到 `sdd-task` 落地，本 skill 只执行、**不改 `tasks.md` 的内容**：

| 文档 | 要求什么 |
| --- | --- |
| [references/sdd-task-amendments.md](./references/sdd-task-amendments.md) | Step ① 支持两种失败证据形态，一个 Task 内允许多轮 6 步 |
| [references/sdd-task-frontend-split.md](./references/sdd-task-frontend-split.md) | 前端 Task 的切分方式：整页样式集中成一个独立还原 Task 等 |

拿到的 `tasks.md` 不符合这两份要求时照常执行，按各自文档里的兜底走，不回头改上游产物。

## 路径变量

全文引用变量，**不硬编码路径**。

| 变量 | 含义 | 定位线索 |
| --- | --- | --- |
| `<repo-root>` | 目标前端仓根目录 | `tasks.md` 计划头的 `project` 字段；目录内有 `package.json` |
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

- 仓库接入门先定位 `<repo-root>`、`<project-sdd-dir>` 与 `<repo-baseline-dir>`；Phase 0 再定位需求侧四个目录。**全部唯一命中则静默继续**，不为此占一轮。
- **任何一个缺失或有多个候选，走一轮 P7 批量提问**，一次问完。
- **`<design-spec-dir>` 随 `<requirement-dir>` 一并确定**，不占一个提问位——多问一个可推导的值只是多耗用户注意力。
- **`<base-ref>` 不进这一轮提问。** 取不到时两份检视能自己从 git 状态推改动范围：能定位就传，不确定就不传。
- 确认结果记入 `<story-dir>/dev-baseline.md` 的“执行起点（环境）”，后续全部引用变量。
- 新产物 `dev-baseline.md` / `restore-contract.json` / `restore-adapter.json` / `restore-report-red.json` / `restore-report-green.json` / `dev-review.md` **一律写入 `<story-dir>`**，`design-spec/` 下的设计事实与视觉缓存**一律写入 `<design-spec-dir>`**；实现侧可选视觉截图挂 `<story-dir>` 下。两者的分界与理由见 [工件管理](#工件管理)。

## subagent 派发约定

- **读取 `<skill-dir>/agents/<name>.md` 全文作为子代理 prompt**，不摘要、不改写、不只传要点。
- **在提示词全文之后追加一段「路径变量取值」表**，给出 `<repo-root>` / `<repo-baseline-dir>` / `<story-dir>` / `<requirement-dir>` / `<prototype-dir>` / `<design-spec-dir>` / `<skill-dir>` 的实际值。提示词文件本身不含硬编码路径。
- 派 `extract-block-spec` 时，在路径变量表后再追加四行实例输入：`区块名`、`页面 / 路由`、`区块切片路径`、`目标视口`。切片路径必须指向主 agent 用 `block --anchor` 刚生成的那一个临时文件，不得给整份原型。
- **子代理只读、不再委派、不改任何文件**，产物以正文回传由主 agent 落盘——并行子代理写同一个文件必然互相覆盖。
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
- **第一类的收集一律走子代理，主 agent 不边做边查。** 主 agent 在 Phase B 手上有实现上下文，边实现边探事实会把「仓内本来怎么做」和「我刚才怎么做的」混在一起。

### 基线源：没有 HTML 原型时

还原轮需要**外部基线**——契约期望值的出处必须在 Agent 之外，否则退化成自己写的断言。基线源三档，取第一个可用的：

| 档 | 基线源 | 还原侧期望值取自 | 取证方式 | 登记 |
| --- | --- | --- | --- | --- |
| 1 | HTML 原型 | `design-facts.json` + 本区块规格 | 契约机器检查；仅 visual YELLOW 对照原型缓存 | — |
| 2 | **参照页**：仓内已上线的同类页面 | 参照页的结构化实测值与 REPO-3 token 范式 ID | 契约机器检查；仅 visual YELLOW 对照参照页 | `基线源：参照页 <路由>`，可信度降级 |
| 3 | 文字规格 + 仓内 token | `story-delta-frontend-design.md` 的文字规格；R3 / R4 降为「取自选定的 REPO-3 token 范式，不得出现字面量」 | 静态预检 + 可用的结构化渲染；无外部视觉事实 | `基线源：文字规格`，可信度降级 |

第 2 档是「缺设计稿又要与存量体验一致」的正解，走法五条：

- **参照页候选由 `recon-codebase` 收集**（属事实，不打断用户）：同类页面的路由、区块构成、间距与字号实测值、状态样式、空态处理、用到的仓库范式 ID
- **选哪个页面作参照是决策**，并进 Phase A 已有的确认门一起确认，不额外占一轮
- 这条路径上 **Phase A 的两份勘察改为串行**：先 `recon-codebase` 收参照页事实，再把它作为输入派 `recon-spec` 写基线。正常路径仍并行
- QA 基线还原侧的取证方式写「冻结契约 · 参照页 `<路由>` 的 `<区块>`」；**R1 / R2 的结构与文案只能取自 `story-delta-frontend-design.md` 的文字规格，不得从参照页照抄业务文案**
- 「与现有页面保持一致」这种写法本身不合格，与「与原型一致」同类：必须落到参照页的具体路由、区块名与实测数值

第 3 档把承诺收窄到**仓内 token 一致性 + 「不破」三项 + 文字规格逐条落地**。R3 / R4 / R5 不得写出原型级的具体数值——没有基线还给数值就是发明规格。

**降到第 2 或第 3 档必须在确认门里说明。** 用户确认的不只是期望值，还有「本次拿什么当基线」。

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

路由返回后再次运行 `status` 与 `validate`。未通过不得进入 Phase 0，也不得把仓库未就绪登记成 Story 降级。

### Phase 0 — 需求执行起点

主 agent 自己做，不派发。**无决策时不单独占一轮（P6）。**

#### 1. 定位需求路径

按路径表定位 `<story-dir>` / `<requirement-dir>` / `<prototype-dir>`。唯一命中就静默继续；缺失或多候选时按 P7 一轮问完。

`<prototype-dir>` 定位不到时，同一个问题带上参照页或文字规格降级选项。`<design-spec-dir>` 恒为 `<requirement-dir>/design-spec/`，不单独提问。

#### 2. 按需读取仓库 baseline

此时只读：

- 用 `show --section REPO-1` 读取当前 Story 所需的启动、账号/角色/租户、fixture、API/mock、浏览器契约；
- 用 `show --section REPO-2` 读取当前 app 实际存在的规范质量命令；
- `onboarding-report.md`：当前机器实证、limits、仍保留进程。

不要在 Phase 0 读取 `REPO-3`；代码侧勘察再按当前需求选读。

#### 3. 固定本次执行上下文

从 `tasks.md`、AC、仓库 baseline 与 onboarding report 得到：

- Story 范围、目标页面与路由；
- Git `base-ref`、起点 SHA、工作区初始状态；
- 本次账号、角色、租户、fixture、API/mock 模式；
- 目标路由能否打开、截图与结构化采集能否使用。

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

新建 `<story-dir>/dev-baseline.md`，先写 `DEMAND-2`；Phase A2 再追加 `DEMAND-3`。

```markdown
# Dev Baseline — <Story 编号与名称>

## 执行起点（环境）

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 仓库 baseline | `<repo-baseline-dir>` | `REPO-1/2/3` 指纹 + readiness |
| `<repo-root>` / `<story-dir>` / `<requirement-dir>` | `<取值>` | 自动命中 / 用户确认 |
| `<prototype-dir>` / `<design-spec-dir>` | `<取值>` | 自动命中 / 推导 |
| Story 范围与目标路由 | `<取值>` | tasks / AC |
| `base-ref` / 起点 SHA / 工作区 | `<取值>` | git 只读命令 |
| 账号 / 角色 / 租户 | `<取值>` | REPO-1 + 本次选择 |
| fixture / API 模式 | `<取值>` | REPO-1 + 本次选择 |
| 起页面 | 可 / 不可（原因） | 路由 + 健康检查 |
| 截图 / 结构化采集 | 可 / 不可（原因） | onboarding 实证 + 本次复核 |
| 原型形态 | 格式化 / 单行导出件 / 不适用 | 行数与平均行长 |
| 降级项 | 无 / `<逐条列出>` | |

## 起点质量

| 类别 | 命令 | 结果 | 证据 |
| --- | --- | --- | --- |
| `<仅列 REPO-2 中实际存在且本次适用的类别>` | `<命令>` | 通过 / 失败集合 | 退出码、耗时、失败项 |
```

只有 Story 特有且初始化阶段无法预先消除的限制才能进入“降级项”。页面或浏览器等仓库必需能力失效时回 Phase -1，不得直接降级。

---

### Phase A1 — 规格抽取

把设计稿的取值一次性搬进 `<design-spec-dir>`，之后全流程只读产物、不读原型（硬门禁 9）。**无决策时不单独占一轮（P6）。**

#### 1. 抽取顺序

| # | 动作 | 谁做 |
| --- | --- | --- |
| 1 | 跑 `<skill-dir>/scripts/extract_design_spec.py extract <html> --out-dir <design-spec-dir>`，产出 `design-facts.json`、`design-tokens.md`、`interface-inventory.md`、`content-inventory.md`，并算出每个区块的内容哈希 | 主 agent |
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

**`recon-spec` 必须排在抽取之后，这是 Phase A 分两段的唯一理由。** 它写还原侧期望值要的是设计稿的具体取值——间距、字号、色值、静态文案，原来它自己读原型拿。取值搬进区块规格后它不再有读原型的权限（硬门禁 9），A1 没跑完它就没有输入。`recon-codebase` 不依赖设计稿，仍与它并行放在 A2，让确认门只等一处。

#### 3. 回传校验

`extract-prototype` 与每一份 `extract-block-spec` 都逐项核对下表。不合格退回重跑一次，仍不合格按 P7 上报。

| 检查项 | 查谁的回传 | 判据 |
| --- | --- | --- |
| 切分表可用 | `extract-prototype` | 每个区块有锚点与内容哈希；粒度过「一屏可截 + 一个名词短语说得清」两条，跨度偏大的写了不拆理由 |
| 页面无遗漏 | `extract-prototype` | 切分表覆盖本 Story `tasks.md` 涉及的全部页面，未覆盖的写了理由 |
| 哈希覆盖完整 | `extract-prototype` | 归属某区块的每个候选段都位于该区块锚点子树内；没有用一条代表实例锚点代替一组重复实例 |
| 组件编号可引 | `extract-prototype` | 界面清单每个模式有编号（`IC-nn`）与实例数，变体归并写了归并理由 |
| 锚点形态正确 | 两者 | 锚点主体是 class 结构；环境段「原型形态」为格式化档时附行号范围，单行档不得编造行号 |
| 一区块一文件 | `extract-block-spec` | 每份区块规格只写一个区块，不跨区块合并 |
| 六维度覆盖 | `extract-block-spec` | R1–R6 逐条出现；静态设计稿读不出的（典型是 R4 状态样式、R5 空态）写 `未见`，**不得推断** |
| 动态数据位已标 | `extract-block-spec` | 占位符文案标为「动态数据位」并只给格式模板，未混进静态标签 |
| 无仓内 token | `extract-block-spec` | 全文不出现 `PATTERN-*`；引用的是设计稿侧的 token 名与取值，仓内映射留到 Step ③ |

**`未见` 是合法结论，不是缺陷。** 静态设计稿里确实没有 hover / focus / disabled / loading 与空态，回传里出现具体取值反而是发明规格。这些维度由主 agent 记入 A2 的「已知缺口」。

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
| 规格侧勘察 | `<skill-dir>/agents/recon-spec.md` 全文 + 路径变量取值表 |
| 代码侧勘察 | `<skill-dir>/agents/recon-codebase.md` 全文 + 路径变量取值表 |

取值表里追加一行 `基线源`，取值为 `原型` / `参照页` / `文字规格`（按 [基线源](#基线源没有-html-原型时) 判）。**基线源不是 `原型` 时两份改为串行**：先派 `recon-codebase` 收参照页事实，回传后把参照页那一节连同选定的路由一起追加进 `recon-spec` 的取值表再派它。串行只发生在这条降级路径上。

#### 2. 回传校验

规格侧逐项核对下表。不合格退回重跑一次，仍不合格按 P7 上报。

| 检查项 | 判据 |
| --- | --- |
| 维度齐全 | 还原侧 R1-R6、功能侧 F1-F4 十个标题都在，无增删 |
| 无空表 | 不涉及的维度写了 `不适用` 加理由 |
| 措辞黑名单 | 全文搜 QA 基线模板列的禁用措辞，零命中 |
| 取证可定位 | 还原侧每条期望值都带区块规格路径与锚点 |
| 两表对齐 | QA 基线引用的区块名都能在 `block-index.md` 里找到 |
| 契约规则一一映射 | 每条 R1–R6 期望值都有同 `baseline_id` 的规则；规则含维度、区块、判定对象、期望值、检查模式、容差、状态场景、设计事实出处与 required layers |
| 不从实现反推 | 契约期望值只来自 QA 基线 / `design-facts.json` / 区块规格；实现 locator 只出现在独立 adapter 草稿，不进入契约 |
| 静态动态已分 | R2 的期望值只取区块规格里的静态标签；动态数据位登记为格式模板，不当文案期望值 |
| 豁免有理由 | 每条豁免命中三类可接受理由之一并附证据；无「时间不够」「差异很小」这类 |
| AC 无遗漏 | F2 覆盖本 Story 全部 AC 锚点 |

代码侧的校验项由 `recon-codebase` 定义，核心三条：每个采用项都引用真实存在的 Requirement 决策或仓库 `PATTERN-*`；记录当次 REPO-3 完整指纹；子代理已经打开范式证据复核，但不把范式正文、源码片段或证据表复制进 Story。

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

- QA 基线全文：还原侧 R1-R6 与功能侧 F1-F4 的表格原样呈现（确认对象就是这些期望值，摘要掉等于没确认）
- 豁免表全文
- 原型切分表**只展示页面与区块名两级**，锚点、内容哈希与视觉职责不展开
- 基线源不是 `原型` 时，**参照页候选表与选定的那一个**（用户确认的不只是期望值，还有拿什么当基线）
- 有降级项时，前置一行降级告知

`dev-baseline.md` 的“工程依据”不是新的确认对象；它只记录已经由 Requirement 决策或仓库 REPO-3 确立的引用。确认门仅说明采用了多少条工程依据，不展开范式正文。

```
---
**[Phase A 确认门]** QA 基线已产出：基线源 <原型 / 参照页 <路由> / 文字规格>、还原侧 6 维 <N> 条期望值、功能侧 4 维覆盖 <M> 条 AC、豁免 <K> 条；区块规格 <X> 份（复用 <Y> 份），工程依据引用 Requirement 决策 <R> 条、仓库范式 <P> 条。确认后即冻结，开工中放宽任何一条都需重新确认。
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

主 agent 亲自做，不派发（见 [ADR-0002](./docs/adr/0002-implementation-stays-with-main-agent.md)）。逐 Task 推进，**常规不占用户一轮（P6）**，只有第 6 节的两类升级中断才打断。

#### 1. 开工前必读

每个 Task 动手前，先读 `dev-baseline.md / 工程依据`。对当前 Task 命中的 ID 调用 `manage_repo_baseline.py show --pattern-id <ID>`，从仓库唯一 REPO-3 正文读取公共方法、token、请求封装和编码范式；Requirement 的 `REQ-DEC-*` 回读 `requirement-frontend-design.md`。

这是细粒度复用的**第一道防线**，第二道在 Phase C 的代码规范检视。防线前置是因为返工成本：检视阶段才发现「本可复用却自己实现」，改动落在全部 Task 完成之后。

#### 2. 轮次顺序

| 层级 | 顺序 |
| --- | --- |
| Task 之间 | 按 `tasks.md` 原顺序，不重排 |
| Task 内部 | **固定先还原轮、后逻辑轮** |

Task 内固定顺序的理由是物理依赖：行为要挂在 DOM 上，没有结构就没有挂点。

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

外部基线原则来自 [ADR-0001](./docs/adr/0001-restore-uses-diff-list-as-red-evidence.md)；机器报告取代固定截图的决策见 [ADR-0005](./docs/adr/0005-external-contract-is-primary-restore-evidence.md)。

#### 4. 还原轮 6 步的动作

固定检查层级如下。`required_layers` 由契约逐条声明；静态通过不能替代 render-required 规则的 GREEN。

| 层 | 能力 | 是否截图 |
| --- | --- | --- |
| 静态预检 | 必需文案 / i18n key、仓内 token、禁用字面量、状态选择器 | 否 |
| 结构化渲染 | 注入 `scripts/collect_restore_facts.js`，读取 DOM、`getComputedStyle`、`getBoundingClientRect`、滚动尺寸和实际状态结果 | 否 |
| 视觉补证 | 阴影观感、字体栅格、图片裁切、复杂叠层等机器盲区 | 是，仅 YELLOW 项 |

默认容差与映射固定：

- 文案、数量、顺序、token、枚举值精确匹配；颜色规范化后精确匹配。
- 尺寸、间距、对齐允许 ±1 CSS px；横向溢出、裁切、重叠超过 1 CSS px 判 RED。
- 无法安全表达容差的规则标 YELLOW，不得自行扩大容差。
- R1：DOM 存在性、数量、顺序、父子结构；R2：渲染文案与格式模板；R3：token 静态预检 + computed style / 几何；R4：状态选择器预检 + 实际触发后的计算样式；R5：指定 fixture 下的结构、文案和布局，造不出 fixture 则 YELLOW；R6：指定视口的滚动、重叠、裁切，纯源码不得判 GREEN。

**① RED — 运行冻结契约**

1. 运行 `verify_restore_contract.py validate`；基线哈希不一致立即停止。
2. 运行 `static` 子命令生成临时 `static-results.json`。
3. 页面可用时，按契约的 `state_scenario` 进入状态，把契约与 adapter 放进 `window.__SDD_RESTORE_INPUT__`，注入 `collect_restore_facts.js`，保存返回值为临时 `render-results.json`。页面不可用时写 `{ "contract_sha256": "<契约哈希>", "page_available": false, "reason": "<原因>", "rules": {} }`，不得伪造实际值。
4. 运行 `report --phase red`，输出 `<story-dir>/restore-report-red.json`。差异清单只按 [references/diff-list-template.md](./references/diff-list-template.md) 摘要该报告。
5. 至少一项 RED 才能进入 Step ③。首轮全部 GREEN，取消该还原轮并记录“冻结契约已满足”；首轮只有 YELLOW，先走 Step ②，发现偏差转 RED 才进入实现，无偏差则取消还原轮。

**② 验 RED — 核出处、定位与 YELLOW**

- 每条 RED 必须同时有期望值、实际值、`baseline_id` / `design_fact_source` 和实现 locator；缺一视为报告执行失败，不进 ③。
- YELLOW 先补页面、fixture 或状态触发，再重跑结构化采集。仍无法结构化判定且契约要求 visual 层时，查询视觉缓存：

```bash
python3 "<skill-dir>/scripts/extract_design_spec.py" visual-cache \
  --facts "<design-spec-dir>/design-facts.json" \
  --design-spec-dir "<design-spec-dir>" \
  --anchor "<区块锚点>" --viewport "<宽>x<高>" --dpr "<DPR>" \
  --browser-engine "<引擎>" --browser-version "<版本>" \
  --font-fingerprint "<字体指纹>" \
  --report "<story-dir>/restore-report-red.json"
```

- 脚本从报告中只统计当前锚点、`required_layers` 含 visual 的 YELLOW；为 0 时返回 `not-needed`。缓存命中只读复用；未命中才截原型并用 `--png` 写入新缓存目录。实现侧截图写 `<story-dir>/evidence/<Task 编号>-r<轮次>/`。机器可检项不截图。
- 视觉补证发现偏差时，把 `visual-results.json` 对应规则写成 `red`，给出实际表现与截图引用，再重跑 RED 报告；不得把主观观察直接塞进实现清单而绕过报告。

**③ GREEN — 只修 RED**

- 只改 `restore-report-red.json` 中属于当前 Task 的 RED；YELLOW 不是实现任务，先补证。
- 取值走 `dev-baseline.md / 工程依据` 引用的仓库范式：间距、颜色、字号用仓内 token，不硬编码；有可复用的公共方法或 hook 就用既有的。

**④ 验 GREEN — 同一契约重跑 + 回归**

- 重新运行 ① 的 validate / static / structured render / report，唯一差别是 `report --phase green --out <story-dir>/restore-report-green.json`。不得编辑 RED 报告得到 GREEN 报告；该命令在 `overall` 非 `green` 时以退出码 3 阻断。
- 合法结论只有：全部规则已验证；或未实际匹配的规则逐条命中契约内的冻结豁免。任何 RED、任何未解决 YELLOW 都不是 GREEN；不得为收口就地新增豁免。
- 跑执行起点记录的 test / typecheck / lint / build 命令。**判定基准是 DEMAND-2 的起点失败集合，不是「全绿」**：

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
| 页面无法启动 | 静态支持项照常执行；R6、级联/字体、实际状态等 render-required 规则保持 YELLOW，不得降成源码 GREEN |
| 无截图能力 | 不影响静态与结构化规则；visual-required 规则保持 YELLOW |
| 已有 Story 没有 `restore-contract.json` | 继续按 ADR-0001 的旧截图证据流程读取与续跑，不迁移历史证据；新 Story 不得主动选择旧流程 |

#### 5. 编译硬约束

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出本 Task 的文件清单** | 停下上报，不自行扩大范围 |
| 2 | 禁止用 `any`、`@ts-ignore`、`eslint-disable` 绕过 | 仓内既有范式就是如此才可用，且必须在代码旁写明理由；无理由绕过是 Phase C 的阻断级 |
| 3 | **同一个报错连续修 3 次不成就停止** | 停下上报 |

第 3 条以「同一个报错」计数：改了写法但报错文本不变，算同一次链条的延续，不重新计数。

#### 6. 两类升级中断

| 触发 | 判据 |
| --- | --- |
| 编译修不动 | 同一个报错连续修 3 次未成 |
| 需越界改动 | 修好它必须改本 Task 文件清单之外的文件 |

两者都按 P7 上报，**不自行决定**。同一时刻攒到的多个问题合并一轮：

```
以下 2 个问题需要你回答：

| # | 问题 | 我的推测（如有） |
|---|------|-----------------|
| Q-1 | 🔴 T4 的 `Property 'sortKey' does not exist on type 'Column'` 已连续修 3 次未成。补字段要改 `src/types/table.ts`，它在本 Task 文件清单外，是否允许改？ | 推测允许，理由：仓内所有列表页的列定义都取自该类型，不改无法接上排序 |
| Q-2 | 🟡 T4 的排序参数需要 `src/api/order.ts` 新增一个可选字段，同样在文件清单外，是否纳入本 Task？ | 推测纳入，理由：仅新增可选字段，既有调用点不受影响 |

🔴 标记的问题必须回答才能继续；🟡 标记的是推测，可确认、纠正或跳过（标为工作假设）。
```

等待回答期间**停在当前 Task**：不跳过它做下一个、不用 `any` 之类手段临时糊过去、不把改动范围先扩出去再补问。

#### 7. 进度真相与落账

- **`tasks.md` 的 checkbox 是唯一进度真相。** 完成一步勾一步，不批量补勾，不在别处另记一份进度
- Step ⑥ 把证据落进 `alpha-tests.md`：还原轮进「还原证据记录」节，逻辑轮进 L4 / L3 记录节，两者都回填 AC ↔ 证据映射。**不另开第二本账**
- 上游未声明对接模式且接口实际不可用时，降级为静态实现模式，把受影响的 AC 标 `Deferred` 并写明原因与解除条件。**不得拿豁免顶替 `Deferred`**
- 全部 Task 的 checkbox 勾完、`alpha-tests.md` 无缺口，才进 Phase C

#### 8. 无截图能力时的降级

截图能力与页面能力分开判：

| 能力缺失 | 还原轮处理 |
| --- | --- |
| 截图不可，页面可 | 静态预检与结构化渲染照常；机器可检规则照常得出 RED/GREEN。只有 visual-required 规则保持 YELLOW |
| 页面不可 | 静态预检照常；所有 render-required / visual-required 规则保持 YELLOW，尤其 R6 不得源码判 GREEN |
| 结构化渲染已尝试但采集脚本报错 | 判 RED（执行失败），不是 YELLOW；修采集入口或实现定位后重跑 |

源码级结果只能作为 static 层事实，不能越级替代 render / visual 层。Step ⑥ 按实际报告状态落账；有未解决 YELLOW 就不能勾本轮 GREEN。

---

### Phase C — 并行检视

四个子代理同一轮并行，各自穷尽自己的维度、产出分级结论，主 agent 汇总进 `<story-dir>/dev-review.md`。**维度清单与分级口径的单一事实源是 [references/review-dimensions.md](./references/review-dimensions.md)**，判级、去重、汇总一律按它。

#### 1. 派发前自检

主 agent 自己做。三项缺一不进 Phase C：

| 项 | 判据 | 不满足时 |
| --- | --- | --- |
| 全部 Task 已 GREEN | `tasks.md` 的 6 步 checkbox 全部勾完 | 回 Phase B，从第一个未完成 Task 继续 |
| `alpha-tests.md` 无缺口 | 每条 AC 有证据链；还原轮记录含契约哈希、RED/GREEN 报告指纹与路径、摘要及适用的视觉缓存引用 | 回 Phase B 补记录 |
| `dev-baseline.md` 已冻结 | 基线头「冻结状态」为 `已冻结 ✅` | 回 Phase A 走确认门 |

再按 [前置产物校验表](#前置产物校验表) 核对四份检视各自的终止级前置。**明知不满足的那一份不派发**——派出去也只会返回一行前置缺失；不派发的按第 4 节记为「未执行」。

自检不替代子代理的前置校验，两道叠加。

#### 2. `<base-ref>` 的追加

`review-convention` 与 `review-quality` 需要本 Story 的改动 diff，两者都实现了三级取法：给了 `<base-ref>` 就用它，没给自己从 git 状态推，都取不到才返回前置缺失。**能拿到就传**，只追加进这两份的取值表，另外两份不加。

| 情形 | 动作 |
| --- | --- |
| 本 Story 开工前记录过起点提交 | 追加，取值为该提交 |
| 能定位与基线分支的分叉点，且分支上只有本 Story 的提交 | 追加，取值为分叉点提交 |
| 分支上混有其他 Story 的提交，切不干净 | 不追加，让子代理走第 2 级自推 |
| 目标仓不是 git 仓，或 git 状态读不到 | 不追加 |

**不确定就不传。** 传错的 `<base-ref>` 比不传更糟：子代理会把它当权威取法，检视范围直接错到别的 Story 上，而回传表头写出来的取法看起来完全正常。

#### 3. 并行派发

同一轮发出，不串行：

| 子代理 | prompt |
| --- | --- |
| 布局与响应式检视 | `<skill-dir>/agents/review-layout.md` 全文 + 路径变量取值表 |
| 代码规范检视 | `<skill-dir>/agents/review-convention.md` 全文 + 取值表（含 `<base-ref>`，按第 2 节） |
| 质量检视 | `<skill-dir>/agents/review-quality.md` 全文 + 取值表（含 `<base-ref>`，按第 2 节） |
| 功能自测试 | `<skill-dir>/agents/self-test.md` 全文 + 路径变量取值表 |

代码规范检视与质量检视拆开并行是刻意的：前者以 `dev-baseline.md / 工程依据` 指向的 REPO-3 范式作客观基准，后者靠通用工程判断，合在一个子代理里，客观判断会被主观判断稀释。

#### 4. 前置缺失与「未执行」

子代理返回 `前置缺失：<清单>` 时**不重跑**，按来源分两条路：

| 来源 | 处理 |
| --- | --- |
| DEMAND-2 已记录、已按硬门禁 4 告知过用户的 Story 特有限制 | **不再走 P7 追问**，直接记「未执行」并写明原因，进第 7 节汇总 |
| 其余前置缺失（产物真的不在、基线没冻结、Task 没勾完） | 按 P7 把缺失清单交给用户 |

第一条的理由：那个降级用户已经知道了，再问一遍等于同一件事打断两次（P1）。哪份降级、哪份终止见 [环境降级](#环境降级)。

**「未执行」必须一路显式带到收口**——`dev-review.md` 的检视基准表、Phase D 的收口结论、最终输出的第一行，三处都要出现。**不得静默跳过，不得因为少一份检视就宣告全部通过。**

#### 5. 回传校验

四份各按自己提示词的「输出格式」逐项核对。不合格退回重跑一次，仍不合格按 P7 上报。

| 检查项 | 判据 |
| --- | --- |
| 维度小节齐全 | 布局 6 个、代码规范 7 个、质量 8 个、功能自测试 5 个，一个不少；无发现的写了「无发现」加检索范围 |
| 级别二选一 | 每条结论标了阻断级或建议级，不设第三档 |
| 编号沿用 | `L1`–`L6` / `C1`–`C7` / `Q1`–`Q8` / `F1`–`F4` 加 `REG-n`；引用基线与仓库范式时 `R<n>-<m>` / `F<n>-<m>` / `EX-n` / `PATTERN-*` / `REQ-DEC-*` 原样引用，不转述 |
| 定位可复算 | 静态检视给文件路径 + 行号范围；实跑检视给页面与路由、区块名、视口、复现路径 |
| 阻断级有证据 | 布局检视与功能自测试的阻断级附了截图文件名（有截图能力时）；质量检视的阻断级给了触发操作序列或原文行 |
| 兜底节保留 | 「Open Question」「已知缺口」标题在，无内容写了「无」；功能自测试的「Deferred 候选」同 |
| 功能自测试逐行 | 基线功能侧有几行就有几行，结果只有 `通过` / `不通过` / `未跑（原因）` 三值 |

**`待主 agent 核豁免` 是主 agent 的活，不是子代理的缺陷。** 收到这个标记，对着 `dev-baseline.md` 豁免表逐条定夺：命中 `EX-n` 的从报告里删掉并记一行「命中 `EX-n`，不报」；未命中的按 review-dimensions 规则 3 判阻断级。

#### 6. 截图归档

子代理唯一允许的写入是截图文件，写在临时目录，路径在回传表头给出。临时目录随时会被清掉，所以由主 agent 归档：

- 把被结论引用到的截图逐个复制到 `<story-dir>/evidence/review/`，未被引用的不归档
- 文件名加检视前缀避免撞名：`layout-<结论编号>.png`、`self-test-<基线编号>.png`
- 复制完把 `dev-review.md` 的截图列改写为归档路径，**不保留临时路径**

复制不到（文件已不在）时，该条结论的截图列写 `截图丢失：<临时路径>`；丢的是**阻断级**结论的截图，退回重跑那一份检视——阻断级没有证据就没有让人复核的余地。

#### 7. 汇总落盘

按 [review-dimensions.md](./references/review-dimensions.md) 第五节的口径合并四份回传，写入 `<story-dir>/dev-review.md`：

- **去重取高。** 同一处代码被多份报出，合并成一条，编号并列写出（`C3-1 / L1-2`），级别取最高的那一档，各自的证据都保留
- **不改级别。** 只按 review-dimensions 第二节四条规则判级，不因条数多降级、不因观感扎眼升级
- **Open Question 与 Deferred 候选单独成节**，不计入阻断级条数，但必须出现——它们是需要人决定的事，被折叠掉就等于替人做了决定

结构：

```markdown
# Dev Review — <Story 编号与名称>

## 检视基准

| 项 | 值 |
| --- | --- |
| 检视时间 | `<YYYY-MM-DD>` |
| diff 范围 | `<取法与提交区间，改动文件数>` |
| 布局与响应式检视 | 已执行 / **未执行（原因）** |
| 代码规范检视 | 已执行 / **未执行（原因）** |
| 质量检视 | 已执行 / **未执行（原因）** |
| 功能自测试 | 已执行 / 已执行（降级：无截图能力）/ **未执行（原因）** |
| 截图归档目录 | `<story-dir>/evidence/review/` |

## 结论汇总

| 来源检视 | 阻断级 | 建议级 | Open Question |
| --- | --- | --- | --- |

## 阻断级

| 编号 | 来源 | 发现 | 定位 | 依据 | 修复状态 |
| --- | --- | --- | --- | --- | --- |
| `L3-2` | 布局 | | | `R6-1` / 规则 1 / 规则 2 / 规则 3 | 待修 / 已修（复跑结论） |

## 建议级

<同上表结构，去掉修复状态列；每条完整保留证据，不摘要>

## Open Question

## Deferred 候选与判定

## 收口结论

<由 Phase D 填写>
```

**建议级不等于可以不写。** 它的定义是「不阻断收口」，不是「不进报告」。

---

### Phase D — 收口

主 agent 自己做，不派发。目标只有一个：**把 `dev-review.md` 的阻断级清零，或者在清不掉时把决定权交回用户。**

#### 1. 阻断级修复

逐条修，顺序按阻断级表的编号。三条约束与 Phase B 第 5 节同源：

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出 Phase C 的 diff 范围**（本 Story 改动过的文件） | 停下，进第 3 节上报 |
| 2 | 禁止用 `any`、`@ts-ignore`、`eslint-disable` 绕过 | 这本身就是 `C6` 的阻断级，绕过等于自造一条新的 |
| 3 | 同一个报错连续修 3 次不成就停止 | 停下，进第 3 节 |

**不得把改不动的阻断级降为建议级。** 级别只由 review-dimensions 第二节的四条规则决定。

#### 2. 修完重跑

一轮修完，**回 Phase C 重跑四份检视**（未执行的那份仍不执行）。代码已经变了，旧结论一律作废；只重跑「自认为被波及」的那几份，等于用修复者的判断替代检视。

**修复—重跑最多两轮。** 第二轮结束仍有阻断级未清零，进第 3 节，不开第三轮。

#### 3. 修不掉时按 P7 上报

阻断级修不掉、需越界改动、Open Question 待决、`Deferred` 待判，这四类攒在同一轮一次问完（P1）：

```
以下 3 个问题需要你回答：

| # | 问题 | 我的推测（如有） |
|---|------|-----------------|
| Q-1 | 🔴 阻断级 `C6-2`（`src/api/order.ts` L42 的 `@ts-ignore` 无理由）要修掉必须改 `src/types/order.ts`，它不在本 Story 的 diff 范围内，是否允许改？ | 推测允许，理由：缺的那个字段就是本 Story 新接口的响应字段，类型缺失是本次引入的 |
| Q-2 | 🔴 阻断级 `F3-4`（离线态无错误提示）连修 3 次未成：全局拦截器先于页面捕获，绕开它必须改 `src/utils/request.ts`，那是本 Story diff 范围之外的公共文件。允许改，还是本 Story 到此为止、把 `F3-4` 单独拆出去修？ | — |
| Q-3 | 🟡 Open Question `L3-1`：1280px 下筛选栏换行导致内容截断，唯一解法是改栅格列数，属于改变布局结构。是否回问上游补响应式规格？ | 推测回问，理由：R6 只承诺「不破」，本阶段不发明响应式规格 |

🔴 标记的问题必须回答才能继续；🟡 标记的是推测，可确认、纠正或跳过（标为工作假设）。
```

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
| 2 | 还原报告 GREEN | `restore-report-green.json` 无 RED、无 YELLOW；全部规则已验证或逐条命中契约内冻结豁免 |
| 3 | 阻断级为 0 | `dev-review.md` 阻断级表全部为「已修（复跑结论）」 |
| 4 | 门禁兜底九项无命中 | AC 未覆盖、占位符（TBD / TODO / 无代码步骤）、编译期类型错误、还原报告非 GREEN、测试红、回归相对 Phase 0 基线变差、公共样式硬编码、调试语句残留、无理由的 `any` / `@ts-ignore` / `eslint-disable`（review-dimensions 规则 1） |
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

## 降级模式

**任何需求级降级都必须可见**：在 `dev-baseline.md` 执行起点的「降级项」登记、在受影响证据中标注、在最终输出里带出来（硬门禁 4）。仓库级能力失效不适用本节，必须回 Phase -1。

### 环境降级

| 探测项 | Phase B 还原轮 | 布局与响应式检视 | 功能自测试 | 代码规范 / 质量检视 |
| --- | --- | --- | --- | --- |
| 截图不可 | 静态/结构化规则照常；visual-required 规则保持 YELLOW | **未执行**（Phase C 规则不变） | 照常实跑，截图列填 `降级：无截图能力` | 不受影响 |
| 起不了页面 | 静态规则照常；render/visual-required 规则保持 YELLOW，不能完成还原轮 | **未执行** | **未执行** | 不受影响 |
| 起点质量命令跑不起来 | Step ④ 的回归判定无基准 | 不受影响 | `REG-n` 记 `无基线可比`，**不得判定「回归未变差」** | 不受影响 |

布局检视对无截图判终止、功能自测试判降级，**两者相反是刻意的**：布局检视的判据是渲染结果，源码读不出溢出与重叠，没有渲染结果就没有判据；功能自测试的判据是实跑中观察到的行为，截图只是留证手段，少了它证据力下降、结论仍成立。

### 产物降级

| 缺什么 | 后果 | 处理 |
| --- | --- | --- |
| HTML 原型 | 还原侧失去视觉基线 | 按 [基线源](#基线源没有-html-原型时) 降到第 2 档（参照页）或第 3 档（文字规格 + token），在基线头登记基线源、在确认门里说明、最终输出带状态限定 |
| 脚本执行能力（跑不了 `extract_design_spec.py`） | A1 拿不到区块切分与 token 二分，抽取层不成立 | **格式化档**：`rg` 按 class 名逐个定位凑出区块边界，区块规格改由 `extract-block-spec` 按定位到的行号范围实读现取，`design-tokens.md` 与 `interface-inventory.md` 不产出；登记进环境段降级项。**单行档不降级执行**：`rg` 分不了段，判基线源不可用，按 P7 请用户提供可执行环境或改走第 2 / 3 档。两种情形下主 agent 仍不直读原型（硬门禁 9） |
| 某个区块的区块规格 | 该区块的 Step ① 没有期望值来源 | 重派一次 `extract-block-spec`；仍拿不到按 P7 上报，**不得由主 agent 直读原型顶替**，也不得跳过该区块直接判 GREEN |
| `requirement-frontend-design.md` | 拿不到共享组件清单与对接模式声明 | 记入「已知缺口」；对接模式未声明且接口实际不可用 → 降级为静态实现模式 + `Deferred` |
| Test Design 用例 | F1 层级对账少一个证据来源 | 记入「已知缺口」，改跑仓内测试命令核对，写明命令与输出关键行 |
| `dev-baseline.md / 工程依据` 缺失或引用失效 | 代码规范检视**终止**；布局检视拿不到 token 范式；质量检视判不了某条发现是否违反仓内约定 | 重新执行代码侧勘察，只回填 ID 与 REPO-3 指纹，不创建范式副本 |
| `alpha-tests.md` 还原证据 | 检视核不了哪些偏差已命中冻结豁免 | 子代理标 `待主 agent 核豁免`，主 agent 对着豁免表定夺 |
| 接口实际不可用 | F4 与部分 F2 / F3 跑不了 | 逐条记 `未跑（接口不可用）`，走 `Deferred`。**不得写成通过，不得自行判为豁免** |

### 失败恢复

中断后重跑，先读进度再决定从哪继续。**`tasks.md` 的 checkbox 是唯一进度真相。**

| 产物 | 重跑时 | 理由 |
| --- | --- | --- |
| 仓库 `repo-baseline.md` | 最先运行 `status` / `validate`；失效即回 Phase -1 | 不能在过期仓库事实上续跑 Story |
| `tasks.md` checkbox + `alpha-tests.md` | 先读，从**第一个未完成 Task** 继续 | 已勾的步骤有证据可查，重做只会覆盖掉证据 |
| `<design-spec-dir>` 的 `design-facts.json`、三份 Markdown、切分表与区块规格 | 重跑脚本算原型指纹与区块哈希；指纹一致全量只读复用，指纹变化后只重抽失配/新增区块 | 原型指纹覆盖 DOM/CSS、资源内容与缺失状态；区块增量仍按内容哈希，不用 mtime |
| `<design-spec-dir>/visual-baseline/` | 缓存键全量一致只读命中；任一环境维度变化创建新指纹目录 | 不覆盖旧版本；没有 visual YELLOW 不查询、不截图 |
| `restore-contract.json` | `dev-baseline.md` 未变则复用；基线哈希不一致硬失败 | 只有重新确认基线后才能重新编译 |
| `dev-baseline.md / 工程依据` | Story 未变且记录的 REPO-3 指纹仍一致时**跳过重跑** | 选择引用仍指向同一版仓库范式；指纹变化只重选引用，不复制正文 |
| `dev-baseline.md` 的确认门 | 已冻结时**不重新走** | 重走一次等于让用户对同一份基线确认两次（P1） |
| `dev-review.md` | **四份检视一律重跑，不复用旧结论** | 代码已经变了，旧结论作废 |

Story 变更了（上游改了 `tasks.md` 或设计文档）时，勘察与基线都要重来，并重新走 Phase A 确认门——冻结的是那一版 Story 的判定标准。

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
| 还原存在 YELLOW | **不得完成**；补齐页面/fixture/视觉能力后重跑同一契约 |
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

设计稿通常是整个需求一起给的，复用面在 requirement 级：下一个 Story 直接拿哈希一致的区块规格用，零成本。**这条区分必须写明**——否则 `design-spec/` 会被当成「新产物」按老约定挪回 `<story-dir>`，每个 Story 把同一份设计稿重抽一遍。

五条约定：

- **四份全局产物只写一次。** `design-facts.json` 是纯机器事实，内容变化时确定性重写；三份 Markdown 可能含人工命名审订，文档哈希一致时只读保留。区块规格一区块一文件，按内容哈希增量更新。
- **脚本输出由主 agent 落盘。** 脚本由主 agent 调用，输出由主 agent 写入 `<design-spec-dir>`——脚本不是 subagent，这与「subagent 只读」不冲突。两个 `extract-*` 仍只回传正文，一个字节都不自己写。
- **subagent 不落盘。** 产物以正文回传由主 agent 写入。
- **`alpha-tests.md` 是验收追溯的唯一证据账本。** 机器报告是被账本按指纹引用的证据工件，不是第二本账；不得把报告内容复制进账本。
- **Requirement 级原型缓存、Story 级实现补证、Phase C 检视截图不混放**，各自按上表归档。
- **Story 不持有仓库范式正文。** `dev-baseline.md / 工程依据` 只保存 `PATTERN-*` / `REQ-DEC-*` 与 REPO-3 指纹；实现与检视按 ID 回读仓库唯一正文。

## 单步入口路由

**八个 subagent 不注册为独立 skill。** 它们的前置很强，但 description 写出来会是「检视前端布局与响应式」「解析 HTML 设计稿」这类通用句，极易被无关请求自动匹配走，被单独触发时前置全缺只能空转。改由本 SKILL.md 路由：用户用自然语言说要做哪一步，主 agent 先按 [前置产物校验表](#前置产物校验表) 校验，齐了就派发，缺了就明确告知缺什么。

| 用户意图（示例说法） | 派发目标 |
| --- | --- |
| 「初始化前端仓」「刷新仓库 baseline」「项目第一次接入」 | 路由 `sdd-init-frontend`；完成后若当前有 Story 则回 Phase -1，否则结束 |
| 「重抽设计稿规格」「重新解析设计稿」 | 走完 Phase A1：跑脚本 → `extract-prototype` → `extract-block-spec` ×N。**哈希一致的区块照常复用**，说「重抽」不等于强制全量重来 |
| 「`<区块名>` 的规格重来一份」「这个区块的规格不对」 | `extract-block-spec` 单实例，只覆写该区块那一份，切分表与其余区块不动 |
| 「只做勘察」「重跑勘察」 | `recon-spec` + `recon-codebase`，同一轮并行 |
| 「只做规格侧勘察」「重出 QA 基线」 | `recon-spec` |
| 「只做代码侧勘察」「重出代码事实」 | `recon-codebase` |
| 「重跑还原验证」「重新生成 GREEN 报告」 | 校验冻结契约 → 静态预检 → 结构化渲染 → 按需视觉补证 → 更新对应报告；不改契约与基线 |
| 「只补 YELLOW」「补视觉证据」 | 只处理报告中 YELLOW 的 `required_evidence`；机器可检项不截图，补证后重跑同一契约 |
| 「重跑布局检视」「再看一遍响应式」 | `review-layout` |
| 「重跑代码规范检视」 | `review-convention` |
| 「重跑质量检视」 | `review-quality` |
| 「只跑功能自测试」「重跑一遍自测」 | `self-test` |
| 「重跑全部检视」「重新收口」 | 四份并行，走完 Phase C → Phase D |
| 「继续跑」「从上次断的地方接着来」 | 完整流程，按 [失败恢复](#失败恢复) 定起点 |

五条规则：

1. **前置不齐不派发。** 按 P7 一轮告知缺什么、期望在哪，不逐个问、不自行补足、不拿相近文件顶替。
2. **派发方式与 Phase A / C 完全一致**：提示词全文 + 路径变量取值表；`review-convention` 与 `review-quality` 按 Phase C 第 2 节追加 `<base-ref>`；卡死巡检同样适用。
3. **单步检视的结果覆盖 `dev-review.md` 里对应那一份的小节**，并更新检视基准表中该份的执行状态与时间，其余小节不动。**不追加成第二份报告。**
4. **单步入口不动 `tasks.md` 的 checkbox。** 进度只由 Phase B 的实现推进。
5. **单步入口跑完照样出三行索引**（P5），产出行指向被更新的那份产物。

**单步入口不是绕过门禁的口子。** 单跑一份检视不构成收口，`dev-review.md` 的阻断级仍要走完 Phase D 的清零流程。

## 前置产物校验表

八份提示词各自开头都有一段前置校验，不满足则**立即返回 `前置缺失：<清单>` 并终止，不做任何猜测性工作**。本表供主 agent 派发前自查；**判据以各提示词为准，不一致时以提示词为准。**

| subagent | 终止级前置（缺一即返回前置缺失） | 可选前置（缺失记入「已知缺口」，不终止） |
| --- | --- | --- |
| `extract-prototype` | `<design-spec-dir>/design-facts.json`、`design-tokens.md`、`interface-inventory.md`、`content-inventory.md` 齐全且可读；环境段「原型形态」已探明 | `<story-dir>/tasks.md`（缺则按整稿划区块，不做 Story 范围裁剪）；已有的 `block-index.md`（有则按哈希增量补，无则全量划） |
| `extract-block-spec` | 本实例负责的那**一个**区块切片；`<skill-dir>/references/block-spec-template.md`；`<design-spec-dir>/design-tokens.md` 与 `interface-inventory.md`（规格要引用 token 名与组件编号） | `content-inventory.md`（缺则占位符判定退化为逐条现判，误判风险记入「已知缺口」） |
| `recon-spec` | `<story-dir>/tasks.md`；`<story-dir>/story-delta-frontend-design.md`；`<skill-dir>/references/qa-baseline-template.md`；**基线源**——`design-facts.json` + 本 Story 相关区块规格与 `block-index.md`，或参照页事实，或文字规格 | `<requirement-dir>/requirement-frontend-design.md`；Test Design 用例 |
| `recon-codebase` | `<repo-root>` 可访问；`status` / `validate` 通过；`repo-baseline.md` 的 REPO-3 可读 | `requirement-frontend-design.md`；`tasks.md`（缺则不能生成 Story 选择） |
| `review-layout` | `dev-baseline.md` 存在且冻结状态为 `已冻结 ✅`；环境段「截图」为「可」；环境段「起页面」为「可」且能按其命令与端口实际打开目标页面；`tasks.md` 全部 Task 已 GREEN | `dev-baseline.md / 工程依据`（缺则给不出应当用的 token 范式）；`alpha-tests.md` 还原证据（缺则可能重复报已豁免项） |
| `review-convention` | `dev-baseline.md / 工程依据` 存在、其 REPO-3 指纹有效；本 Story 改动 diff 可取 | `tasks.md` |
| `review-quality` | `<repo-root>` 可访问；本 Story 改动 diff 可取 | `dev-baseline.md / 工程依据`；`tasks.md` |
| `self-test` | `dev-baseline.md` 存在且冻结状态为 `已冻结 ✅`；功能侧 F1–F4 四张表齐全；执行起点「起页面」为「可」且能实际打开目标页面；`tasks.md` 全部 Task 已 GREEN | `alpha-tests.md`；执行起点「截图」为「可」；`DEMAND-2` 起点失败集合 |

「diff 可取」按三级取法判定：给了 `<base-ref>` → 用它；没给 → 子代理自己从 git 状态推（未合入基线分支的提交 + 已暂存 + 工作区未暂存的并集）；两条都取不到才算不可取。

主 agent 侧三条：

- **自查不替代子代理的前置校验**，两道叠加。自查是为了少花一轮空转。
- **子代理返回前置缺失时不重跑**，也不自行补足或猜测，按 P7 交用户。唯一细则见 Phase C 第 4 节。
- **不得为了让前置通过而改产物。** 典型是基线没冻结就把冻结状态改成 `已冻结 ✅`——冻结的语义是用户确认过，改状态位不等于确认。
