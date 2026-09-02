# {{project}} / {{story_name}} — 单仓实现计划

<!--
  本模板的 HTML 注释是填表指导，不进产物：落盘前全部删除，只留表和正文。
  字段含义见 sdd-dev-frontend/references/execution-contract.md#taskpacket；
  计划写到哪一层见同文件的「计划与实现的分层边界」。
-->

**Goal:** <!-- 本仓这个 Story 让用户能做到什么 -->

**关键结构决策:** <!-- 只写会影响验收或文件划分的决策，例如新建 feature 目录、状态提到哪一层、复用哪套请求封装 -->

**TaskPacket:** project={{project}} | codespec_path= | story={{story_name}} | verification_schema=v2 | test_framework= | component_test_status= | component_test_framework= | browser_test_status= | browser_test_framework= | search_paths= | project_type=frontend | frontend_design_path= | baseline_source= | prototype_dir= | reference_route= | affected_routes= | required_states= | restore_tasks= | risk_triggers=

**知识 trace:** <!-- 上游 consume 的 entries[].id；gaps 非空则一并列出 -->

## 项目边界

| 范围内 | 范围外 |
| --- | --- |

## 页面、路由与组件层级

<!--
  与 affected_routes 一致。只画本 Story 触及的节点，复用既有节点标「复用」。
  组件名按顺序取：上游前端设计已命名的沿用；仓内既有节点用代码里的真名；本 Story 新增且上游未命名的在这里定名，
  定名后与文件的绑定写在「模块与文件」的「职责与对外导出」列，同一个名字不在两处各定义一次。
  只给「模块与文件」里有对应文件行的节点定名；实现时才会拆出的内部子组件不预先起名，那是写法。
  纯逻辑 Story 没有新增或改变节点时，只留路由表，删掉组件树。
-->

| 路由 | 页面 / 入口 | 本 Story 的变化 |
| --- | --- | --- |

```text
<Page>
├── <既有节点>（复用）
└── <新增节点>
    └── <新增子节点>
```

## 模块与文件

<!--
  先看当前 app baseline components.md / routes.md / api.md / data.md / styles.md 的 PATTERN-* 与清单条目，
  再在 search_paths 内找可复用的组件、路由入口、hook、请求封装与样式 token；复用不了的在「职责与对外导出」里写原因。
  样式文件归属还原 Task。新增页面时按 routes.md 写路由注册、布局与守卫；它写着「无路由机制」时不要发明一个。
-->

| 文件 | 类型 | 新建/修改 | 职责与对外导出 | 复用的既有资产 | Task |
| --- | --- | --- | --- | --- | --- |
| <!-- 精确路径 --> | <!-- 组件 / 样式 / hook / 类型 / 测试 --> | | <!-- 实现什么功能；导出什么（组件名与 props 语义、hook 名与返回语义、类型名） --> | <!-- `PATTERN-…` 或精确路径；无则写「无，原因：…」 --> | |

## 状态与数据流

<!--
  纯同步 Story 删除整节。
  有异步取数时默认沿用 data.md 三态规范、api.md 请求出口、components.md 通用构件，写一行「三态沿用：<PATTERN-ID 或路径>」即可。
  data.md 写「无统一做法」时如实写成缺口并按 AT 需要定出本 Story 的做法，不假装沿用不存在的约定。
  第二张表只在本 Story 与既有做法不同、或该态被某条 AT 直接断言时才补，且只补命中的那一态；都不命中就删表。视觉数值不写。
-->

| 状态 | 归属节点 | 来源 | 消费方 | 变化 / 失效时机 |
| --- | --- | --- | --- | --- |

| 态 | 为什么不沿用 / 哪条 AT 断言 | 可观察结果 |
| --- | --- | --- |

## 接口对接

<!-- 后端契约只引用不重定义；字段与枚举以领域 design 为准。 -->

| 方法 + URL | 触发时机 | 请求字段 | 响应字段与枚举 | 失败时的可观察结果 |
| --- | --- | --- | --- | --- |

## 视觉基线来源

<!-- baseline_source = none 时删除本节，并在「项目边界」写明为什么没有还原 Task。 -->

| 项 | 内容 |
| --- | --- |
| 基线档位 | <!-- prototype / reference_page / text_spec --> |
| 视觉来源 | <!-- 原型目录；或待下游确认的参照页候选；或文字规格章节 --> |
| 区块 | <!-- 每页职责单一的区块名；不写 class 锚点，由 Dev 抽取 --> |
| 必测交互状态 | <!-- 与 required_states 一致 --> |
| 已知缺口 | <!-- 无则写「无」 --> |

## testability 锚点

<!--
  只为 AT 需要定位的对象建锚点。仓内已有定位约定时沿用，本节只列本 Story 新增的锚点。
  「定位什么」写语义（提交按钮、批次列表的一行），不写 DOM 结构；锚点挂在哪个元素上是 Dev 的写法。
  列表类只给一个锚点并说明按什么区分行。没有新增锚点时删除整节。
-->

| 锚点 | 定位什么 | 用它的 AT |
| --- | --- | --- |

## 用例追溯

<!--
  这张表是 AT 的 verification_scope / verification_method 的唯一作者；alpha-tests.md 只按 AT 引用，不再抄这两列。
  范围写 S1_COMPONENT / S2_PAGE / S3_STORY，方法写 test_case / restore_contract / manual_acceptance；
  判据见 sdd-dev-frontend/references/validation-policy.md#七验证方法的判定规则。机械 Task 的 quality_gate 不产生 AT。
  manual_acceptance 的 AT 另在 alpha-tests.md 的人工验收记录里写依据、验收环境与需留下的证据。
-->

| AT | 标题 | 验证范围 | 验证方法 | Task |
| --- | --- | --- | --- | --- |

## Task List

<!--
  顺序：跨页公共骨架 → 每页还原 → 该页逻辑。规模按 execution-contract.md#规模：一个 Story ≤ 7 个 Task（1 个也可以），
  单 Task ≤ 5 个文件、2–5 步，每个 Task 都改到产品代码或测试代码。
  下面四种形状按 Task 形态与验证方法选一份复制；步骤数不凑齐。改造既有行为或修缺陷时可在暴露缺口后追加「确认原因」，
  实现后确有必要重构时可追加「重构」。「可能扩散」只在确有没定论的连带范围时写，无则删行。
-->

### Task N: <名称> [用例: AT-...]

**形态:** 逻辑

**受影响声明:** <!-- AC / AT -->

**Files:**

- Create: `<精确路径>` — <实现什么>
- Modify: `<精确路径>` — <改什么>
- Test: `<精确路径>`

**可能扩散:** <!-- 已知有风险但没定论的文件或模块，由 Dev 落定；无则删这行 -->

- [ ] **Step 1: 暴露缺口** — 在哪个测试文件断言什么行为，改动前应该怎么失败
- [ ] **Step 2: 实现并转绿** — 改哪些文件、达成什么可观察行为；同一断言转绿后哪些声明应为 `PROVEN`
- [ ] **Step 3: 记录证据并提交** — 回填 `alpha-tests.md`，沿用 `sdd-task` 提交规范

### Task N: <名称> [用例: AT-...]

**形态:** 逻辑（人工验收）

**受影响声明:** <!-- AC / AT，全部为 verification_method=manual_acceptance -->

**人工依据:** <!-- manual_basis 枚举值 + 为什么这条声明机器判不了 -->

**验收环境与所需证据:** <!-- required_environment / required_evidence，与 alpha-tests.md 一致 -->

**Files:**

- Create / Modify: `<精确路径>` — <实现什么>

**可能扩散:** <!-- 无则删这行 -->

- [ ] **Step 1: 实现人工验收候选** — 达成哪些可观察结果；本 Task 不新增自动化测试文件
- [ ] **Step 2: 让受影响范围的编译/类型/lint/构建通过**
- [ ] **Step 3: 登记待人工验收并提交** — 回填 `alpha-tests.md`，`manual_outcome=NOT_RUN`、`claim_status=UNVERIFIED`；不填验收人与验收时间，agent 不代签

### Task N: <名称> [用例: AT-...]

**形态:** 还原

**受影响声明:** <!-- AC / AT -->

**视觉来源、路由、区块:** <!-- 与「视觉基线来源」一致 -->

**取证归属:** <!-- 本轮取 RED；或复用 Task M 的同一份 RED 报告 -->

**Files:**

- Create / Modify: `<精确路径>` — <实现哪些区块>
- Style: `<精确路径>` — <哪些区块的样式，本轮独占>

- [ ] **Step 1: 对冻结契约取 RED** — 哪些区块、哪些规则应为红（取证归属在他轮时删掉本步，按两步执行）
- [ ] **Step 2: 实现并复跑转绿** — 只改上面的文件，哪些区块应转绿；不从实现反推期望
- [ ] **Step 3: 记录证据并提交** — 回填 `alpha-tests.md`，沿用 `sdd-task` 提交规范

### Task N: <名称>

**形态:** 机械

**为什么不需要行为证据:** <!-- 确无行为分支的类型、构建或引用对齐 -->

**Files:**

- Modify: `<精确路径>` — <改什么>

- [ ] **Step 1: 改动并让编译/类型/引用通过**
- [ ] **Step 2: 记录证据并提交** — 回填 `alpha-tests.md`，沿用 `sdd-task` 提交规范

## 风险与回滚

| 风险 | 缓解 | 回滚 |
| --- | --- | --- |
