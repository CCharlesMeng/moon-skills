# sdd-dev-frontend 使用说明

> 本文是项目级维护与使用说明，不属于 Skill 运行时上下文。运行时行为以 [`SKILL.md`](../../../skills/sdd-dev-frontend/SKILL.md) 为准。

`sdd-dev-frontend` 用于把上游已经拆好的**一个前端 Story**，从 `tasks.md` 执行成可验收的前端代码、测试结果、机器还原报告、按需视觉证据和检视结论。

从使用者的角度，可以把它理解成一条带验收门禁的开发流水线：

```mermaid
flowchart LR
    U["上游输入<br/>tasks.md + 设计文档"] --> P0["Phase 0<br/>环境探测"]
    P0 --> A1["Phase A1<br/>设计稿规格抽取"]
    A1 --> A2["Phase A2<br/>QA 基线 + 代码事实"]
    A2 --> G{"你确认 QA 基线"}
    G -->|确认| B["Phase B<br/>逐 Task 实现"]
    G -->|修改| A2
    B --> C["Phase C<br/>并行检视"]
    C --> D["Phase D<br/>修复与收口"]
    D --> O["可追溯的代码与证据"]
```

它不只关注“代码有没有写完”，还会在开工前冻结“怎样才算做完”，在实现中保留 RED → GREEN 证据，并在结束前检查布局、代码规范、工程质量、功能和回归。

## 适合什么时候用

以下条件同时成立时，适合使用本 skill：

- `sdd-task` 已为当前 Story 产出 `tasks.md`（没有时，只要已在当前会话中把 Story 范围、AC、还原基线和对接模式聊清楚，Phase 0 也会自动起草一份，见 [团队起步套件.md](./团队起步套件.md)）；
- `tasks.md` 标明目标仓是 frontend；
- 目标前端仓可以访问；
- 至少有一种还原基线：
  1. HTML 原型；
  2. 仓内可类比的已上线页面；
  3. `story-delta-frontend-design.md` 中可直接落地的文字规格。

一次运行只处理：

> **一个独立前端 app × 一个 Story 的 `tasks.md`**

如果一个需求涉及多个 Story、多个 app 或多个仓，请分别运行；跨 app / 跨仓依赖由外层流程协调。

以下情况不应直接使用：

| 当前情况 | 应先做什么 |
| --- | --- |
| 还没有 `tasks.md` | 有 `sdd-task` 就先运行它；没有时，若已在会话中把需求聊清楚可直接调用（Phase 0 会自动判断能否起草），否则见 [团队起步套件.md](./团队起步套件.md) 先手写最小合规版本 |
| 需要修改设计方案，而不是执行现有设计 | 回到 `sdd-design` |
| 是纯后端 Story | 使用对应的后端开发流程 |
| 想在一次运行里覆盖多个仓或多个 Story | 拆成多个独立运行 |

## 开始前要准备什么

### 必需输入

| 文件或目录 | 典型位置 | 作用 |
| --- | --- | --- |
| `tasks.md` | `<story-dir>/tasks.md` | 唯一执行清单，也是唯一进度真相；缺失且会话内容足够时由 Phase 0 自动起草 |
| `alpha-tests.md` | `<story-dir>/alpha-tests.md` | RED / GREEN 与 AC 证据账本 |
| `story-delta-frontend-design.md` | `<story-dir>/story-delta-frontend-design.md` | 当前 Story 的前端增量设计 |
| 目标前端仓 | `<repo-root>` | 实际修改代码、运行测试和启动页面的工程 |

### 推荐输入

| 文件或目录 | 典型位置 | 缺失时会怎样 |
| --- | --- | --- |
| HTML 原型 | `<prototype-dir>` | 改用参照页或文字规格，证据可信度会降级 |
| `requirement-frontend-design.md` | `<requirement-dir>/requirement-frontend-design.md` | 共享组件与对接模式会记为已知缺口 |
| Test Design 用例 | 上游文档引用的位置 | F1 层级对账改用仓内测试命令补证 |

`tasks.md` 最好已经遵循这三项前端约定（完整口径见[执行契约的 Task 切分与步骤形状](../../../skills/sdd-dev-frontend/references/execution-contract.md#task-切分与步骤形状)）：

- Task 按「逻辑 / 还原 / 机械」三种形态切分，步骤数随形态 2–5 步，不凑成统一步数；
- 还原 Task 独占样式文件，其 Step ① 对冻结的外部设计契约取一次 RED 报告作为失败证据；
- TaskPacket 头带 `verification_schema=v2`，「用例追溯」表为每条 AT 写 `验证范围` 与 `验证方法`。

即使没有遵循，skill 也会继续执行，但不会修改 `tasks.md` 的内容；它会在同一 Task 内分轮、每轮独立引用声明，取证成本通常更高。

## 如何调用

### 最简调用

当目录结构清晰、路径能自动定位时，可以直接说：

```text
请使用 sdd-dev-frontend 执行 Story FE-123。
按该 Story 的 tasks.md 完成前端实现、证据记录、并行检视和收口。
```

### 推荐调用

明确给出路径，可以减少首次定位时的来回确认：

```text
请使用 sdd-dev-frontend 执行订单列表 Story。

目标前端仓：/workspace/apps/order-web
Story 目录：/workspace/specs/order-management/stories/ST-03
Requirement 目录：/workspace/specs/order-management
HTML 原型目录：/workspace/specs/order-management/prototypes

请按 tasks.md 原顺序执行；QA 基线产出后先让我确认，再进入实现。
```

不需要另行要求“保留证据”或“做 review”，它们本来就是完整流程的一部分。

### 没有 HTML 原型时

可以直接说明希望使用哪种基线：

```text
请使用 sdd-dev-frontend 执行 ST-03。
本 Story 没有 HTML 原型，请先勘察仓内同类列表页，给出 2–3 个参照页候选，
把最终基线源并入 Phase A 确认门，由我确认后再实现。
```

或者：

```text
请使用 sdd-dev-frontend 执行 ST-03。
本 Story 不产出 HTML 原型，按 story-delta-frontend-design.md 的文字规格
和仓内 token 执行，并显式标记证据降级。
```

## 你会在哪些时刻被打断

流程会尽量自动推进。通常只有以下情况需要你参与：

| 时刻 | 你需要做什么 |
| --- | --- |
| 仓库首次接入需要下载、秘密、登录或外部数据 | 完成一次授权或登录；随后自动返回当前 Story |
| 路径无法唯一定位 | 一次性确认缺失或冲突的路径 |
| 基线中存在无法由仓库事实回答的设计决策 | 批量回答必须由人决定的问题 |
| Phase A 完成 | 确认 QA 基线；这是进入实现前的硬门禁 |
| 同一报错连续修 3 次不成 | 决定是否扩大改动范围或调整方案 |
| 必须修改当前 Task 文件清单以外的文件 | 明确授权或拒绝越界改动 |
| Phase D 存在阻断项、Open Question 或 Deferred 候选 | 决定处理方式或外部依赖归属 |
| 全部完成 | 接收最终三行索引和 `acceptance.md` 路径 |

最重要的一次交互是 **Phase A 确认门**。你确认的是具体、可判定的 QA 基线，而不是一句“按原型实现”。确认后基线会被冻结；后续如果要放宽任何标准，必须登记变更并再次请你确认。

## 完整流程与每一步的交接产物

### Phase -1：仓库接入门

先把旧版 `routing.md` / `styling.md` / `testing.md` 原位迁成 `routes.md` / `styles.md` / `tests.md`，再走一道极轻的门：当前 app baseline 的 `index.md` 在不在、`structure.md` 的栈签名读不读得出一个具名的框架加一个具名的形态。不在或读不出时自动路由 `sdd-init-frontend`，主动完成依赖、配置、服务、登录、fixture 和质量命令准备，再返回当前 Story。命名归一后不按份数查——`组件库` 形态下 `routes.md` 与 `api.md` 本就不该存在。单条结论不成立不是就绪问题，读到时就地修。

当前 app 的 baseline 保存在 `<frontend-root>/frontend-baselines/`，不会每个 Story 重抽。单应用仓的 `<frontend-root>` 就是仓根；monorepo 由 Story 的 `search_paths` 与前端设计定位到一个 app 根。

### Phase 0：需求执行起点

这一阶段回答“这个 Story 从什么提交、什么场景和什么失败集合开始”。

`<story-dir>` 下没有 `tasks.md` 时，本阶段第一件事是判断能不能自动起草：当前会话已经把 Story 范围、AC、还原基线和对接模式聊清楚就直接起草并请你确认（模板见 [团队起步套件.md](./团队起步套件.md)）；聊得不够就先问缺口，不替你编。

主要检查：

1. Story 范围、目标路由、`base-ref`、起点 SHA 和工作区状态；
2. TaskPacket 的上游事实：`baseline_source`、原型目录是否真实存在、两条测试通道能力、风险 token；
3. 执行档位（`lite` / `standard`）与初始验证组合——由 `compile_portfolio.py` 按机械判据算出，agent 只补判断型触发器；
4. **只为已选模块**取起点：组合含命令模块才实跑质量命令取起点失败集合，含浏览器模块才解析 `<browser-driver>`；
5. 本次账号、角色、租户、fixture 与 API/mock 模式。

**交接产物**

| 产物 | 写入位置 | 交给下一步什么信息 |
| --- | --- | --- |
| `dev-baseline.md` 的头表、“执行起点（环境）”与“验证组合（初始）” | `<story-dir>/dev-baseline.md` | 执行档位、app baseline 引用、场景、`base-ref`、起点失败集合、Story 特有限制 |
| `evidence/portfolio.json` | `<evidence-dir>/` | 机器编译的档位、触发器、模块、角色、维度与逐声明挂载；Phase C 复编译时作为只升不降的基准并原地覆盖 |

起点失败集合非常关键：后续回归不是要求仓库“从此全绿”，而是要求本 Story 不引入起点之外的新失败。未选的能力不探测、不生成空表。

页面能力与截图能力分开判定：

- 页面可用但不能截图：结构化渲染仍可判定机器可检规则；只有 visual 规则保持 YELLOW。
- 页面不可用：只执行静态预检；依赖计算样式、几何、真实状态和视觉的规则保持 YELLOW。

不会用源码阅读冒充浏览器实测，也不会把未验证维度写成 GREEN。

### Phase A1：设计稿规格抽取

这一阶段把 HTML 原型中的事实搬成结构化规格。完成后，后续实现以区块规格为入口，不需要反复通读整份原型。

处理顺序：

1. 脚本抽取 design tokens、界面模式、文案分类和 `design-facts.json`；
2. 将页面划分为“一屏可截、一个名词短语说得清”的区块；
3. 为每个区块生成独立规格；
4. 用内容哈希判断已有规格能否复用，只重抽变化或新增的区块。

**交接产物**

| 产物 | 写入位置 | 下游如何使用 |
| --- | --- | --- |
| `design-tokens.md` | `<design-spec-dir>/` | 提供设计稿侧共享颜色、间距、字号等事实 |
| `interface-inventory.md` | `<design-spec-dir>/` | 提供重复界面模式、`IC-nn` 编号、名称和变体关系 |
| `content-inventory.md` | `<design-spec-dir>/` | 区分静态标签与动态数据位，避免把样例数据当成固定文案 |
| `design-facts.json` | `<design-spec-dir>/` | 提供结构、静态文案、token、布局声明、资源内容/缺失状态和完整原型指纹 |
| `block-index.md` | `<design-spec-dir>/` | 页面 → 区块切分表，记录锚点与内容哈希 |
| `blocks/<区块名>.md` | `<design-spec-dir>/blocks/` | 当前区块的组件引用、token、布局值、文案、资源和 R1–R6 规格 |

`<design-spec-dir>` 恒为：

```text
<requirement-dir>/design-spec/
```

这些是 **Requirement 级设计事实**，可以被同一 Requirement 下的其他 Story 复用。它们不写进代码仓，也不随单个 Story 的代码提交进入 PR。

如果基线源不是 HTML 原型，而是参照页或文字规格，整个 A1 会跳过。

### Phase A2：规格与代码勘察

这一阶段形成两份互补的开工输入：

- 规格侧回答“怎样才算做完”；
- 代码侧回答“这个仓本来应该怎么写”。

正常情况下两路并行：

| 勘察方向 | 关注内容 | 产物 |
| --- | --- | --- |
| 规格侧 | Story 功能理解、还原侧 R1–R6、功能侧 F1–F4、豁免、已知缺口 | `dev-baseline.md` |
| 代码侧 | 当前 Story 应采用的 Requirement 决策与仓库 `PATTERN-*` | 并入 `dev-baseline.md / 工程依据`，只保存引用 |

**交接产物**

| 产物 | 写入位置 | 交给下一步什么信息 |
| --- | --- | --- |
| 完整 `dev-baseline.md` | `<story-dir>/dev-baseline.md` | 已确认的 QA 基线、豁免、环境能力，以及 `PATTERN-*` / `REQ-DEC-*` 工程依据引用 |

QA 基线的分类法固定为下面十个维度，不能增删；但它们是**候选分类**，每个 Story 只生成 AC、设计输入或风险触发器实际要求的行，不适用的分类直接省略：

| 还原侧 | 功能侧 |
| --- | --- |
| R1 区块与层级完整性 | F1 AC ↔ 测试层级映射 |
| R2 文案一致性 | F2 每条 AC 的可观察判定 |
| R3 间距与对齐 | F3 异常与边界分支 |
| R4 状态样式 | F4 数据与接口契约 |
| R5 空态与边界内容 |  |
| R6 指定视口下的布局完整性 |  |

这一阶段最后会展示 QA 基线全文和豁免表，请你确认。确认后，`dev-baseline.md` 冻结，并编译 Story 级 `restore-contract.json`。契约保存基线哈希，后续每次运行先校验一致性；实现定位另存 `restore-adapter.json`，优先级固定为 role/name → 精确文案 → 稳定 test id → CSS：

```text
冻结状态：已冻结 ✅
```

未确认不能进入 Phase B。

### 样式还原：先确定 Task 归属，再执行还原轮

这里的“样式还原”首先是一种 **Task 切分与文件归属规则**，不只是“在某个 Task 里跑一次还原轮”。推荐的 `tasks.md` 顺序是：

```text
公共样式与骨架 Task（多页面共享时才需要）
                  ↓
页面还原 Task（默认每个页面一个）
                  ↓
逻辑 Task × N（按 AC 分组）
```

| Task 类型 | 负责什么 | 完成后交接什么 |
| --- | --- | --- |
| 公共样式与骨架 Task | 新增或修改 token、公共布局组件、跨页复用的展示组件 | 稳定的公共视觉底座，供所有页面还原 Task 使用 |
| 页面还原 Task | 一次落完页面全部区块的静态结构与样式，包括 hover / focus / disabled / 选中 / loading、空态和边界内容的静态呈现 | 页面骨架与样式文件；RED / GREEN 机器报告；按需视觉证据；`alpha-tests.md` 中的 `R-<Task>-<轮次>` 记录 |
| 逻辑 Task | 按 AC 接入状态迁移、条件渲染、数据变换和接口交互 | 逻辑代码、测试与 `test_case`（或登记待验收的 `manual_acceptance`）证据；原则上不再改样式文件 |
| 机械 Task | 确无行为分支的类型、构建或引用对齐 | 编译 / 类型 / lint 通过即 `quality_gate`；不创建验收声明 |

这种切法的目的，是让页面还原 Task 的冻结契约能够整体 GREEN，并让后续逻辑 Task 不再推翻已 GREEN 的机器证据。

#### 使用者应在 `tasks.md` 中检查什么

1. **共享内容先落地。** 多个页面共用布局骨架、展示组件或新 token 时，应先有一个公共样式与骨架 Task，并排在全部页面 Task 之前。
2. **一个页面默认一个还原 Task。** 只有在原型分散于多个文件，或区块多到一轮冻结契约无法完成时，才按区块边界拆分；不得拆成“先骨架、后细化样式”两遍。
3. **区块要能独立取证。** 每个区块都应注明原型文件与稳定 class 锚点，有单一视觉职责，并能由一组 R1–R6 契约规则完整覆盖。
4. **还原 Task 独占样式文件。** 页面样式和组件骨架文件应列在还原 Task；逻辑 Task 的文件清单不应包含样式文件。
5. **没有收尾样式 Task。** 不应出现“样式微调”“统一优化样式”“视觉走查修复”等 Task；偏差必须在所属区块的还原轮当轮让同一契约无 RED、无 YELLOW。

逻辑 Task 确实必须改样式时，按[执行契约的扩散承接](../../../skills/sdd-dev-frontend/references/execution-contract.md#扩散承接)处理：同 Story 内、不改变验收契约的连带改动直接承接，并在 `alpha-tests.md` 的「计划外承接」表登记文件、所属 Task 与原因。这意味着对应的还原证据已经失效，相关区块必须重跑同一冻结契约，不能沿用之前的 GREEN 结论；未登记的计划外改动仍按越界处理。

#### 上游没有这样切时

本 skill 只执行现有 `tasks.md`，不会回头改写它。若上游仍按功能点切分、多个 Task 都带一点样式，执行时会在同一 Task 内分轮，固定先还原轮、后逻辑轮，每轮独立引用自己的声明、不互借证据。它仍能执行，但同一区块会被反复运行契约，后续改样式也可能使早先的 GREEN 报告失效。

> 样式还原发生在 Phase B，目标是让当前区块的冻结外部契约无 RED、无 YELLOW；Phase C 的布局与响应式检视保持现有流程，仍是完成后的只读复核，关注跨页一致性、真实数据、多视口和交互态，不能代替还原 Task，也不能成为延后修样式的出口。

### Phase B：逐 Task 实现

主 agent 按 `tasks.md` 原顺序执行，不重排 Task。每个 Task 动手前先读 `dev-baseline.md / 工程依据`，按 ID 回读当前 app baseline 里那条唯一正文，优先复用 app 内已有 token、方法、hooks、请求封装和代码规范。

步骤数由 Task 形态决定，逐 Task 按上游写的步骤走，不补齐成统一步数：

| 形态 · 验证方法 | 步骤 | 因果证据 |
| --- | --- | --- |
| 逻辑 · `test_case` | ① 写会失败的断言并确认失败 ② 最小实现让同一断言转绿 ③ 回填账本并提交 | 测试 RED → GREEN，只证明该声明 |
| 逻辑 · `manual_acceptance` | ① 实现人工验收候选 ② 让受影响范围的编译 / 类型 / lint 通过 ③ 登记待人工验收并提交 | 无自动化断言；账本落 `NOT_RUN + UNVERIFIED`，**agent 不代签** |
| 还原 · `restore_contract` | ① 对冻结契约取一次 RED 报告 ② 在文件范围内实现，复跑同一契约转绿 ③ 回填账本并提交 | 同一契约的 RED / GREEN 报告；同页多轮共用一次 RED |
| 机械 · `quality_gate` | ① 改动并让编译 / 类型 / 引用通过 ② 回填账本并提交 | 编译失败 → 通过；不产生验收声明 |

Phase B 只取得当前 Task 改变声明的因果证据；交互状态矩阵、跨页检查、宽回归和独立检视全部留给 Phase C。已实际执行的浏览器场景直接写进 `review-evidence.json`（标 `source: phase-b`），Phase C 按新鲜度复用。

**交接产物**

| 产物 | 写入位置 | 交给下一步什么信息 |
| --- | --- | --- |
| 实现代码与测试 | `<repo-root>` | 当前 Story 的实际代码改动 |
| 已勾选的 `tasks.md` | `<story-dir>/tasks.md` | 唯一进度真相；checkbox 是每个 Task 的 commit point，中断后从第一个未完成 Task 继续 |
| 回填后的 `alpha-tests.md` | `<story-dir>/alpha-tests.md` | 还原证据记录、AC ↔ 证据映射（含执行环境 `mock` / `contract` / `live`）、Deferred、计划外承接、待人工验收 |
| `restore-adapter.json` | `<evidence-dir>/` | 实现 locator 与采集方式；RED 与 GREEN 之间不变 |
| `restore-report-red.json` / `restore-report-green.json` | `<evidence-dir>/` | 同一契约在实现前后的三色结果 |
| `review-evidence.json` 的 `phase-b` 场景 | `<evidence-dir>/review-evidence.json` | 带依赖哈希与运行时键的原始事实，供 Phase C 复用 |
| 三层采集结果（static / render / visual） | `<work-dir>/` | 过程件，同轮 `report` 合并后没人再读；收口时随目录删 |
| 按需原型视觉缓存 | `<design-spec-dir>/visual-baseline/<缓存指纹>/` | 仅在要把某条 visual YELLOW 收成 `PROVEN` 时才截 |

还原轮中的“差异清单”只是机器报告的人类摘要。末步只把契约与报告的指纹、路径、摘要和可选视觉证据写进 `alpha-tests.md`；它始终是 AC 证据追溯的唯一账本。**visual YELLOW 默认落 `UNVERIFIED` 并写补验方式，不默认截图。**

本阶段有三条保护边界：

- 计划文件清单外的改动按扩散承接分流：不改验收契约的直接承接并登记，会改 AC / AT 的先上报，跨仓的回流上游；
- 不使用无理由的 `any`、`@ts-ignore`、`eslint-disable` 绕过问题；
- 同一原因连续修 3 次不成就停止并向你升级。

### Phase C：并行检视

全部 Task 实际完成并勾选、每条改变声明有因果证据或明确未证原因后，才进入检视。

进入时先跑 `classify_diff.py` 取最终 diff 的机械事实，再用 `compile_portfolio.py --phase final --previous evidence/portfolio.json --out evidence/portfolio.json` 复判档位与组合——**只允许比 Phase 0 更多，不允许更少**；同一文件原地覆盖，Phase 0 的快照留在 `previous` 字段。派哪几路由这份最终组合决定，**不是每个 Story 都跑满**：没触发的角色不派、也不生成占位结果。每一路检查什么、怎么定级，全部来自 [`sdd-review-frontend`](../../../skills/sdd-review-frontend/SKILL.md)；本 skill 只负责选角色、备证据和汇总。

组合含 `review-restore` 时，派发前主 agent 先按最终 diff 重跑**全部已冻结区块**的契约——Phase B 只跑过当前变更区块，后来的 Task 改了公共样式，先前区块的 GREEN 只在这里才会被推翻。

每条结论只有两级：

- **阻断级**：必须修复后才能收口；
- **建议级**：进入报告，但不阻断收口。

Open Question 与 Deferred 候选单独列出，不混进这两级。待人工验收项保持 `UNVERIFIED`，不当作 Open Question 或 Deferred。

**交接产物**

| 产物 | 写入位置 | 交给下一步什么信息 |
| --- | --- | --- |
| `portfolio.json`（final） | `<evidence-dir>/` | 按最终 diff 复编译的验证组合，原地覆盖 Phase 0 版本并保留其快照；抄进 `review-evidence.json` 与 `dev-baseline.md` |
| `restore-report-review.json` | `<evidence-dir>/` | 全部已冻结区块在最终 diff 下的三色结果，`review-restore` 只读它 |
| `review-evidence.json` | `<evidence-dir>/` | 验证组合、代码指纹、命令与浏览器场景的原始事实；**不保存判断** |
| `review-results.json` | `<evidence-dir>/` | 0–5 份角色回传的机器聚合与对账细节 |
| `artifacts/` | `<evidence-dir>/` | 被结论引用的截图与结构化结果；未被引用的不归档 |
| `acceptance.md` | `<story-dir>/` | 给人的收口摘要：能不能验收、需要你处理什么、你该知道什么、往下追去哪；**整文件由聚合器渲染，不手写** |
| `diff-facts.json`、RoleResult JSON、规范候选、决策文件 | `<work-dir>/` | 过程件；Phase D 退出门禁通过后整目录删 |

如果某份检视因为已知环境限制无法执行，它不会被静默跳过：执行状态、收口结论和最终状态都会显式注明。角色补证的截图只归档被结论引用的那些，路径记在对应 scenario 的 `artifacts[]`。

### Phase D：修复、复跑与收口

这一阶段把阻断级结论清零，并把最终状态回填到证据账本。

处理方式：

1. 主 agent 按编号逐条修复确证的阻断级；
2. 修复后按依赖精确失效：只作废依赖被改文件的证据与判断，未受影响的继续复用；出现新触发器才扩大组合；
3. 同一阻断连续三次修不掉、需要越界改动、或会改变冻结期望时停下；
4. 存在 Open Question 或 Deferred 待判时，**在对话里问成可回答的问题**（每条给选项与后果），答复按 `aggregate --decisions` 就地记回 `acceptance.md`，同一件事不会下一轮再问；
5. 收到真实人工验收结果后回填 `alpha-tests.md` 再重聚合；`PASSED` 且证据齐全才进 `PROVEN`；
6. 逐条核对退出门禁后，才宣告完成。

**交接产物**

| 产物 | 最终更新内容 |
| --- | --- |
| `alpha-tests.md` | 每条声明的最终状态与执行环境、人工验收回填、Deferred 的外部依赖与解除条件 |
| `review-evidence.json` / `review-results.json` | 失效后重取的证据与重聚合结果 |
| `acceptance.md` | 首句结论、需要你处理的项及其答复、你该知道的项、规范候选、往下追的路径 |
| `dev-baseline.md` | 如收口期间调整过基线，保留变更记录和再次确认结果 |

完成时你会看到三行索引：

```text
<带验收限定的完成状态>
产出：<story-dir>/acceptance.md
下一步：<按当前状态给出的唯一动作>
```

第一行不会伪装成全部通过：全部 `PROVEN` 才写「可验收」；有 `UNVERIFIED` 写「部分验证：N 条声明未验证」（前端没做完，不能合并）；只有 `DEFERRED` 写「前端已验证，N 条真实接缝待 <外部依赖>」（可以先合并）；有待人工验收项写「实现完成，待 N 项人工验收」。

#### 解除 DEFERRED

`DEFERRED` 是唯一在 Story 收口后仍会变化的状态。外部依赖（后端测试环境、测试租户、可回滚数据）就绪后，直接说「后端已部署到测试环境，请解除 <Story> 的 DEFERRED」：只对 Deferred 表里的声明按所需环境档重取证、回填账本、重渲染 `acceptance.md`，不重开 Phase A / B，不改冻结基线。前端代码相对上次收口有变化时不走这条路，回 Phase C 完整复编译。

## 产物之间如何交接

可以从下面这张表快速判断“某个文件是谁产出的、下游拿它做什么”。

| 产物 | 生命周期 | 生产阶段 | 主要消费者 |
| --- | --- | --- | --- |
| `<frontend-root>/frontend-baselines/` 九份按问句 baseline | app 级 | Phase -1 / `sdd-init-frontend` | 该 app 的所有 Requirement / Story |
| `design-spec/design-tokens.md` | Requirement 级 | A1 | 区块规格抽取、QA 基线 |
| `design-spec/interface-inventory.md` | Requirement 级 | A1 | 区块规格抽取 |
| `design-spec/content-inventory.md` | Requirement 级 | A1 | 静态标签 / 动态数据位判定 |
| `design-spec/design-facts.json` | Requirement 级 | A1 | 冻结契约的结构、文案、token、布局和资源事实 |
| `design-spec/block-index.md` | Requirement 级 | A1 | QA 基线、还原轮、证据定位 |
| `design-spec/blocks/*.md` | Requirement 级 | A1 | QA 基线与还原轮的设计取值入口 |
| `design-spec/visual-baseline/<fingerprint>/` | Requirement 级 | B 按需 | visual YELLOW 的只读原型缓存 |
| `dev-baseline.md` | Story 级 | Phase 0 + A2 + C | Phase B 实现、Phase C 派发约束、`verify_restore_contract.py` 哈希锁 |
| `evidence/portfolio.json` | Story 级 | Phase 0 写，C 原地覆盖 | `review-evidence.json / validation_portfolio`、`aggregate` 对账、解除 DEFERRED 时只编译受影响模块；`previous` 字段保留 Phase 0 快照 |
| `evidence/restore-contract.json` | Story 级 | A2 | Phase B 还原轮、Phase C `review-restore` |
| `evidence/restore-adapter.json` | Story 级 | A2 + B | 将实现元素映射到契约规则 |
| `evidence/restore-report-red/green.json` | Story 级 | B | 同一契约实现前后的三色结果 |
| `evidence/restore-report-review.json` | Story 级 | C | 全部已冻结区块在最终 diff 下的三色结果 |
| `tasks.md` checkbox | Story 级 | B | 失败恢复、Phase C 前置检查 |
| `alpha-tests.md` | Story 级 | B + C + D | 唯一证据账本；`aggregate --alpha-tests` 直读它渲染 `acceptance.md` |
| `evidence/review-evidence.json` | Story 级 | B + C | 检视角色共享的原始事实与新鲜度键 |
| `evidence/review-results.json` | Story 级 | C + D | 机器聚合与对账细节 |
| `evidence/artifacts/` | Story 级 | B + C | 被结论引用的截图与结构化结果 |
| `acceptance.md` | Story 级 | C + D | 最终收口与使用者验收 |
| `.work/*` | 过程件 | 各阶段 | 同阶段内的脚本消费；Phase D 退出门禁通过后整目录删 |

每个产物的背景、目的、关注点与对应模板 / 脚本见 [产物清单.md](./产物清单.md)。

`<story-dir>` 只分两层，判据是「验收的人要不要主动打开它」：根下全是给人读的 Markdown（做什么 → 怎么设计 → 怎样算做完 → 做到哪了 → 能不能验收），`evidence/` 里全是机器件，`.work/` 里全是过程件。

典型目录布局：

```text
<frontend-root>/frontend-baselines/
├── index.md
├── structure.md / runtime.md / components.md / routes.md
└── api.md / data.md / styles.md / tests.md

<requirement-dir>/
├── requirement-frontend-design.md
├── design-spec/                         # Requirement 级设计事实
│   ├── design-tokens.md
│   ├── interface-inventory.md
│   ├── content-inventory.md
│   ├── design-facts.json
│   ├── block-index.md
│   ├── visual-baseline/
│   │   └── <fingerprint>/
│   │       ├── prototype.png
│   │       └── manifest.json
│   └── blocks/
│       └── <区块名>.md
└── <story-dir>/
    ├── tasks.md                          # 给人读：做什么
    ├── story-delta-frontend-design.md    # 给人读：怎么设计
    ├── dev-baseline.md                   # 给人读：怎样算做完
    ├── alpha-tests.md                    # 给人读：做到哪了
    ├── acceptance.md                     # 给人读：能不能验收（入口）
    ├── evidence/                         # 机器件；acceptance.md 会指路进来
    │   ├── restore-contract.json
    │   ├── restore-adapter.json
    │   ├── restore-report-red.json
    │   ├── restore-report-green.json
    │   ├── restore-report-review.json
    │   ├── portfolio.json
    │   ├── review-evidence.json
    │   ├── review-results.json
    │   └── artifacts/                    # 被结论引用的截图与结构化结果
    └── .work/                            # 过程件；Phase D 退出门禁通过后整目录删

<repo-root>/                              # 只放实际前端代码与测试
```

截图先落 `.work/`，只有被结论引用的才搬进 `evidence/artifacts/`，路径记在 `review-evidence.json` 对应 scenario 的 `artifacts[]`；其余随 `.work/` 一起删。`.work/` 里还有规则草稿、三层采集结果、`diff-facts.json`、RoleResult JSON 与决策文件——每一份都已并入 `evidence/` 的正式工件或可重算，丢了不构成证据缺口。

## 怎样判断是否真的完成

“代码能编译”不是本 skill 的完成条件。退出门禁六条（原文见 [`SKILL.md#退出门禁`](../../../skills/sdd-dev-frontend/SKILL.md#退出门禁)）：

- `tasks.md` checkbox 与实际实现一致；
- 每条声明恰有一个合法状态：`PROVEN` / `UNVERIFIED` / `DEFERRED`，没有第四种，`MANUAL` 不是状态；
- 每条 `PROVEN` 都有覆盖它、执行环境不低于所需档、且对最终依赖仍新鲜的证据；
- 未清零的阻断不影响任何 `PROVEN` 声明；
- 验证组合、模块执行状态、`UNVERIFIED`、`DEFERRED`、Open Question 和建议级均已对账；
- 待人工验收项逐条对账，`manual_outcome` 与 `claim_status` 是合法配对。

其中：

> **`UNVERIFIED` 是“前端还没做完”，`DEFERRED` 是“前端做完了、等外部接缝”。两者都不计已验收，但对读的人意义不同，最终三行必须分开说。**

## 常见降级场景

| 场景 | skill 会怎么处理 | 对最终结果的影响 |
| --- | --- | --- |
| 没有 HTML 原型，但有同类参照页 | 先给出参照页候选，由你在确认门选择 | 还原基线为类比基线，可信度降级 |
| 既无原型也无参照页 | 使用文字规格 + 仓内 token | 无视觉基线，只承诺文字规格、token 一致性和“不破” |
| 无截图能力 | static / render 正常执行；visual 规则保持 YELLOW | 机器可检项不受影响；未补齐 visual 前还原轮不能 GREEN |
| 页面无法启动 | 只执行 static；render-required 与 visual 规则保持 YELLOW | 结构、计算样式、几何和实际状态未验证，不能伪装成 GREEN |
| 接口不可用 | 前端声明在 `mock` 档照样可 `PROVEN`；需要 `contract` / `live` 档的接缝声明记 `DEFERRED` 并写解除条件 | 整条 Story 不会全绿也不会全灰；后端就绪后走「解除 DEFERRED」 |
| 缺起点失败集合 | 无法判断回归是否变差 | 不得声称「无回归」，REG 按 `unrun` 处理 |
| 原型资源缺失 | 原型侧缺失的图标不参与 R1 差异判定 | 资源缺口与影响进入区块规格的「资源与降级」和 QA 基线的「已知缺口」 |
| 比对器报 `suspected-tool-equivalence`（退出码 5） | 只补比对器两端映射或上报工具缺口 | 不改实现、不加豁免、不计入「修 3 次」 |

降级只改变证据强度或可执行范围，不会偷偷放宽已经确认的 QA 基线。

## 中断后如何继续

直接说：

```text
请继续运行 sdd-dev-frontend，从上次中断的位置接着做。
```

恢复规则：

- `tasks.md` checkbox 是唯一进度真相，从第一个未完成 Task 继续；
- `alpha-tests.md` 中已有的 RED / GREEN 报告引用不会被无故覆盖；
- Story 未变化时复用 `dev-baseline.md` 的工程依据；仓库规范有变动时只重选 ID，不复制正文；
- 已冻结且内容未变的 QA 基线不会要求你重复确认；
- 设计规格按区块内容哈希复用；原型指纹覆盖 DOM/CSS 与资源内容/缺失状态，视觉缓存按完整环境键只读复用；
- `acceptance.md` 的检视结论按依赖失效：代码变化只作废依赖被改文件的那部分，未受影响的继续复用。

如果上游修改了 `tasks.md` 或 Story 设计文档，视为 Story 已变化：勘察、QA 基线和确认门都需要重来。

## 只重跑某一个步骤

完整流程之外，也可以用自然语言触发单步入口：

| 你可以这样说 | 会执行什么 |
| --- | --- |
| “重抽设计稿规格” | 重跑 A1；哈希一致的区块仍然复用 |
| “订单筛选栏的区块规格重来一份” | 只重抽该区块，不动其他区块 |
| “只做勘察” | 规格侧与代码侧勘察 |
| “只做规格侧勘察” | 重出 QA 基线 |
| “只做代码侧勘察” | 重出代码事实 |
| “重跑还原契约” | 校验基线哈希，重跑 static / render / 按需 visual，更新同阶段报告 |
| “补还原 YELLOW” | 按 `required_evidence` 补页面、状态 fixture、结构化采集或最后的视觉证据 |
| “重跑布局检视” | 只更新 `acceptance.md` 的布局检视部分 |
| “重跑代码规范检视” | 只更新代码规范检视部分 |
| “重跑质量检视” | 只更新质量检视部分 |
| “只跑功能自测试” | 只更新功能自测试结果 |
| “重跑全部检视”或“重新收口” | 按当前验证组合重新派出全部适用检视，再进入 Phase D |

单步入口不会绕过前置条件。例如 QA 基线未冻结时，不能直接运行功能自测试；单跑一份检视也不等于整个 Story 已完成。

## 使用建议

- 路径明确时，在首次调用中直接提供 `<repo-root>`、`<story-dir>`、`<requirement-dir>` 和 `<prototype-dir>`。
- 开工前先看 `tasks.md` 的样式归属：公共样式与骨架是否在前、每个页面是否有还原 Task、逻辑 Task 是否避开样式文件。
- 认真审阅 Phase A 的 QA 基线。它是后续所有 RED / GREEN、检视分级和收口判断的共同依据。
- 不要把“接口还没好”写成豁免；应使用 Deferred，并提供可观察的解除条件。
- 如果要改变响应式布局结构，先补上游规格。上游没有响应式规格时，本 skill 只承诺“不破”：无横向滚动、无重叠、无内容截断。
- 验收时先看 `acceptance.md`，再沿其中的路径追到 `dev-baseline.md`、`alpha-tests.md`，需要机器细节时才进 `evidence/`；只有报告引用 visual 项时才查看截图。

## 进一步阅读

- [产物清单.md](./产物清单.md)：每个产物的背景、目的、生产与消费时机、关注点，以及对应的模板与脚本索引
- [团队起步套件.md](./团队起步套件.md)：没有 `sdd-task` / `sdd-design` 时，如何手写最小合规产物快速试跑
- [背景介绍.md](./背景介绍.md)：框架形成时的项目与流程背景
- [SKILL.md](../../../skills/sdd-dev-frontend/SKILL.md)：完整编排规则、硬门禁和失败处理
- [前端 SDD 执行契约](../../../skills/sdd-dev-frontend/references/execution-contract.md)：跨 Skill 的所有权、状态与 TaskPacket 语义
- [方案设计.md](./方案设计.md)：设计取舍与流程蓝图
- [样式还原验证改造计划.md](./样式还原验证改造计划.md)：V2 契约化还原的已实施计划
- [ADR](./adr/)：关键架构决策记录
- [QA 基线模板](../../../skills/sdd-dev-frontend/references/templates/qa-baseline.md)：十个固定维度
- [前端 Task 切分与步骤形状](../../../skills/sdd-dev-frontend/references/execution-contract.md#task-切分与步骤形状)：还原 Task、样式文件归属与计划边界
- [还原契约怎么写](../../../skills/sdd-dev-frontend/references/restore/contract.md) 与 [怎么跑](../../../skills/sdd-dev-frontend/references/restore/run.md)：JSON 工件与规则字段，以及命令和三色语义
- [Story 工件模板](../../../skills/sdd-dev-frontend/references/templates/story-artifacts.md)：`dev-baseline.md` / `alpha-tests.md` / `acceptance.md` 的形状，含还原证据和 AC 映射
- [检视派发](../../../skills/sdd-dev-frontend/references/review/dispatch.md)：派哪几格、角色 ↔ lens 映射与请求参数包；检查项、定级与回传契约都在 [`sdd-review-frontend`](../../../skills/sdd-review-frontend/SKILL.md)
