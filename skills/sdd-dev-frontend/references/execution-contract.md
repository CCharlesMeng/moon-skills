# 前端 SDD 执行契约

本文件是 `sdd-task-frontend` 与 `sdd-dev-frontend` 的共享事实源。前者定义计划与验收声明，后者实现并取证；两边都不复制这里的字段语义。

它落在 `sdd-dev-frontend/references/` 而不是仓库文档区，因为 skill 被单独安装时只会拿到自己的目录——运行期读不到的规则等于没有规则。`sdd-task-frontend` 按兄弟 skill 的相对路径引用同一份，不留副本。

## 所有权

| 所有者 | 负责 | 不负责 |
| --- | --- | --- |
| `sdd-task-frontend` | `tasks.md`、`alpha-tests.md` 初始骨架、Task 切分、每个文件的职责与对外契约、可观察验收声明、候选风险事实 | 代码写法、命令、浏览器矩阵、QA 维度取舍、证据结论、计划未识别到的连带改动 |
| `sdd-dev-frontend` | 代码、计划外扩散的承接与登记、QA 基线冻结、验证组合、证据、声明状态、交付收口 | 改写上游验收内容与文件职责划分 |

## 计划与实现的分层边界

计划的粒度不由「改掉它会不会改变 AC」决定，而由**层次**决定。计划要把执行者带到「打开哪个文件、在里面实现什么功能」，但不替他写代码。

| 层次 | 内容 | 归属 |
| --- | --- | --- |
| 位置 | 模块目录、精确文件路径、在组件层级里的挂载点、样式文件归属 | 计划必写 |
| 职责 | 每个文件实现什么功能、对外导出什么（组件名与 props 语义、hook 名与返回语义、类型名）、状态放在哪个节点、数据从哪来到哪去 | 计划必写 |
| 契约 | 路由、方法与 URL、请求/响应字段、枚举、状态迁移、用户可见结果与必要文案、testability 锚点名与它定位什么 | 计划必写 |
| 复用 | 该复用哪个既有组件、hook、请求封装、样式 token；复用不了时写原因 | 计划必写 |
| 写法 | 函数体、JSX 结构、CSS 规则、DOM 层级、class 名、锚点挂在哪个元素上、具体 API 调用语句、内部子组件与 helper 怎么拆 | Dev |
| 视觉数值 | px、色值、字号、圆角、阴影、断点 | 冻结基线；没有外部基线时任何人都不得发明 |
| 未识别扩散 | 计划没列出、但为达成同一声明必须一并改的文件 | Dev 承接 |

**计划不靠扩大文件清单兜底。** 只写已确认的范围；已知有风险但没有定论的写进 Task 的「可能扩散」，由 Dev 落定。

**既有做法默认沿用，只写引用。** 当前 app 已成立的做法——app baseline 的 `PATTERN-*`、公共请求封装、通用列表/表格/骨架组件、既有的加载空错三态处理、既有的测试定位约定——在计划里只写一行「沿用 + ID 或路径」。只有本 Story 偏离既有做法，或某条 AC/AT 直接断言它，才展开描述。把每个 Story 都当第一个 Story 写，产出的不是计划而是 app 说明书的副本。

## 扩散承接

Dev 遇到计划文件清单之外的必要改动时按下表处理，不默认回流：

| 情形 | 处理 |
| --- | --- |
| 同一 Story 范围内、不改变验收契约的连带改动（类型对齐、引用更新、公共组件签名、样式归属修正） | 直接承接，在 `alpha-tests.md` 登记为计划外承接，写明文件、所属 Task 与原因 |
| 改动会改变 AC、AT 断言或对外契约 | 先按 P7 上报，得到确认后再动 |
| 跨仓、需要新增 AC，或影响其他 Story | 回流上游 |

两条不放松：承接必须**登记**，未登记的计划外改动仍按越界处理；承接不豁免证据，被承接的文件同样进入依赖闭包与失效判断。

**权威登记只有 `alpha-tests.md` 一处。** `acceptance.md` 里那份摘要由 `manage_review_pipeline.py aggregate --unplanned-carry` 从同一批数据渲染，不手写——那个文件是聚合器整文件覆盖的，往里手写的内容会被下一次 aggregate（Phase C 生成、Phase D 更新各一次）冲掉。一个文件一个写入者，这条问题才不会靠纪律去防。

## 验证模型

一条验收声明要回答三个互相独立的问题，所以用三个字段而不是一个层级值。把它们塞进同一个字段，就无法表达「同一个页面范围既可以写自动化用例，也可以做人工体验验收」，也看不出证据取自多宽的范围。

| 轴 | 回答什么 | 取值 |
| --- | --- | --- |
| `verification_scope` | 在多大的 Story 内部范围取得证据 | `S1_COMPONENT` / `S2_PAGE` / `S3_STORY` |
| `verification_method` | 用什么工件或活动取得证据 | `test_case` / `restore_contract` / `quality_gate` / `manual_acceptance` |
| `claim_status` | 当前是否已被充分证明 | `PROVEN` / `UNVERIFIED` / `DEFERRED`，判据见下一节 |

### 验证范围

| 范围 | 边界 | 典型对象 |
| --- | --- | --- |
| `S1_COMPONENT` | 一个组件或组件切片，外部接口可 mock | 组件交互、三态、请求参数、条件渲染 |
| `S2_PAGE` | 一个完整页面及其页面内协作 | 页面布局、溢出、页面状态、页面级交互 |
| `S3_STORY` | 当前 Story 涉及的完整用户路径 | Story 内跨页面、跨路由、鉴权、提交链路和真实接缝 |

每条声明取能覆盖它的**最小**范围。范围更宽只表示覆盖更多协作边界、更慢、更接近真实运行时，不表示质量天然更高。三个值都限制在当前 Story 内，不扩展到其他 Story。

`S1_COMPONENT` 与 `S2_PAGE` 重叠时的 tie-break：**能在单组件挂载下观察到的写 `S1_COMPONENT`，必须整页渲染才能观察的写 `S2_PAGE`。** 单条声明不写 `S1_COMPONENT/S2_PAGE` 这种二选一。

没有 `MODULE` 层。module 是代码组织边界而不是验收观察边界——同一个 hook、store、selector 或 formatter 可能服务一个组件、一个页面或整个 Story，无法稳定排在 component 上面或下面。这类代码仍可用最窄的自动化测试实现，但证据回挂到它实际证明的那条 UI 声明上。完全没有 UI 观察边界的前端 SDK 或工具库 Story 不适用这三层，走通用任务契约，不为兼容它们再造第四层。

`verification_scope` 与验证模块 `story`（见 [validation-policy.md](./validation-policy.md#四验证模块)）分属两轴：`S3_STORY` 描述某条声明在多宽的范围内被观察，`story` 模块决定要不要跑一次真实用户路径。不互相替代。

### 验证方法

四种方法与既有三种 Task 形态一一对齐，所以不新增第四种形态：

| 方法 | 证据 | 对应形态 |
| --- | --- | --- |
| `test_case` | 自动化测试用例的 RED/GREEN | 逻辑 |
| `restore_contract` | 冻结还原契约的 RED/GREEN 报告，不产生测试文件 | 还原 |
| `quality_gate` | 编译、类型、lint、引用或构建检查 | 机械 |
| `manual_acceptance` | 真实人员执行验收后的结构化证据 | 逻辑（人工分支） |

`quality_gate` 只用于没有行为分支、因此**不创建验收声明**的机械 Task；它不豁免需求覆盖，需求锚点仍必须由真正承载用户行为的声明覆盖。

`manual_acceptance` 表示不写自动化测试代码，**不表示不需要验收声明**——它同样要有 GWT、预期结果和追溯关系。允许它的门禁与自动化强制触发器只定义在 [validation-policy.md](./validation-policy.md)，本文件不复制一份。

**已进入冻结还原契约的视觉声明写 `restore_contract`，机器盲区剩余项由契约的 `visual` 层承接并落 YELLOW，不转 `manual_acceptance`。** 这条防的是同一条视觉声明出现两条合法路径：人工那条成本更低，分类会稳定偏向它，结果是绕过 R1–R6、冻结哈希与契约校验器。

### 人工验收声明的附加字段

`verification_method=manual_acceptance` 的声明必须补齐下列字段；其他方法留空：

| 字段 | 写法 |
| --- | --- |
| `manual_basis` | 人工例外的标准依据，枚举见 [validation-policy.md](./validation-policy.md)；不接受自由文本 |
| `required_environment` | 路由、设备、浏览器、账号或第三方前置；只写真正影响判定的部分 |
| `required_evidence` | 截图、录屏、审批记录、操作记录等；不能只写「人工看一下」 |
| `manual_outcome` | `NOT_RUN` / `PASSED` / `FAILED`；计划阶段一律 `NOT_RUN` |
| `manual_checked_by` | 实际执行验收的人员标识，只在人工真的执行后回填；不是计划阶段负责人，不写人名占位符 |
| `manual_checked_at` | 实际执行时间，带时区，同样只在执行后回填 |
| `evidence_refs` | 证据 ID、路径或审批记录 ID；初始为空 |

计划阶段不分派验收人、不建组织角色模型、不设多人会签。待人工项由 `acceptance.md` 统一列出，交付团队按自己的流程认领。

`manual_outcome` 与还原、检视流水线的三色是两套词汇，对账只有两条：`FAILED` 与 RED 同级，受「三色真实」门禁约束，不得改写为 `PASSED`；还原契约 `visual` 层的 YELLOW 在人工维度上等价于 `NOT_RUN + UNVERIFIED`。

`manual_acceptance` 声明只能由真实人员执行。agent、自测试与独立检视都不得用自己的观察替代签字，只能准备候选实现并把待验收项交出去；审批记录可以作为 `evidence_refs`。

### schema 版本

`tasks.md` 的 TaskPacket 头写 `verification_schema=v2` 表示使用本节模型。读不到该字段的按 v1 原语义处理：不强行把旧的 L3/L4 记录映射到三层范围，也不得自动推断为 `manual_acceptance`；只有该 Story 再次进入实现并需要新增或修改声明时，才按可观察边界重新分类并升到 v2。

本节字段名与枚举值是权威词汇。Markdown 表格可以用中文列名，但派生的结构化数据必须投影回这些名称；不再新增 `level`、`test_level`、`evidence_method`，也不用裸 `status` 或裸 `result` 当字段名。

`verification_schema` 与 `manage_review_pipeline.py` 的 `SCHEMA_VERSION` 是两个互不联动的版本号：前者描述 TaskPacket 与账本的字段代数，后者约束角色回传 result 的结构。人工项进入 `review-results.json` 不升 `SCHEMA_VERSION`。

## 声明与状态

每条 AC/AT/QA 行都是验收声明，最终状态只有：

| 状态 | 对人怎么说 | 判据 |
| --- | --- | --- |
| `PROVEN` | 已验证 | 有覆盖该声明、环境正确、对最终相关依赖仍新鲜的证据，且没有未清零的确证阻断 |
| `UNVERIFIED` | 未验证 | 本阶段做得到但未执行、证据不足或工具能力不可用 |
| `DEFERRED` | 已暂缓 | 外部依赖未就绪；必须写明解除条件 |

`UNVERIFIED` 与 `DEFERRED` 都不计已验收。缺少某种证据只影响依赖它的声明，不扩大到无关声明。

**没有第四种状态。** `MANUAL` 不是状态而是验证方法，写进本列即非法：人工验收在计划阶段生成时同样是 `UNVERIFIED`，只有拿到合格人工证据后才进 `PROVEN`。`manual_outcome` 是人工执行结果，与本列各自独立，不得互相代替。合法配对只有 `PASSED + PROVEN`、`PASSED + UNVERIFIED`（证据不足）、`FAILED + UNVERIFIED`、`NOT_RUN + UNVERIFIED`，以及外部依赖未就绪时的 `NOT_RUN + DEFERRED`。`PROVEN` 还要求 `manual_checked_by`、`manual_checked_at`、`required_environment` 齐全且至少有一条 `evidence_refs`。

**两列分工不能混。** 左列是**账本里的值**——`alpha-tests.md` 逐条写它，退出门禁按它判，跨 skill 按它对账，所以它是英文常量、不翻译。中列是**跟用户说话时用的词**，只出现在给人读的产物里（最终三行、`acceptance.md`、handoff 条目）。`acceptance.md` 由 `manage_review_pipeline.py` 的词表统一渲染，不必手写；散文里提到状态时用中列。

这条界线的作用是让读的人不必学三个英文常量，同时不把账本值变成会随文案漂移的东西。

## TaskPacket

接缝沿用 `tasks.md` 的 `TaskPacket` 头，不新增第三份文件。字段缺席表示旧格式输入，由 Dev 按实际事实补判；不表示低风险。

| 字段 | 含义 | 计划侧写法 | Dev 侧消费 |
| --- | --- | --- | --- |
| `project` / `project_type` | 目标前端仓名 / 固定 `frontend` | 抄 `sdd-task` 交接值 | 解析 `<repo-root>` |
| `codespec_path` | 本 Story 的 codespec 工作目录 | 抄交接的 story 目录 | 定位 `<story-dir>` |
| `story` | Story ID（形如 `US<数字>`） | 抄交接值 | 账本与提交信息引用 |
| `verification_schema` | 验收字段代数版本 | 使用[验证模型](#验证模型)时写 `v2`；旧计划留空 | 缺席按 v1 读，不推断为低风险或人工 |
| `search_paths` | 本 Story 允许改动的仓内路径 | 从设计文档与既有目录结构得出 | 越界改动的判据 |
| `test_framework` | 派生摘要，供 v1 消费者读取 | 必须有仓库证据，禁止默认值 | 与下面四个字段冲突时按四字段 |
| `component_test_status` | 组件通道能力 | `available` / `absent` / `unknown`，判据只有 [test-framework-detection.md](../../sdd-task/references/test-framework-detection.md) | 组件级证据是否可取 |
| `component_test_framework` | 组件通道框架身份 | 仅 `available` 时填真实框架名，否则留空 | 选择组件测试通道 |
| `browser_test_status` | 浏览器通道能力 | 同上三值 | 真实浏览器证据是否可取 |
| `browser_test_framework` | 浏览器通道框架身份 | 仅 `available` 时填真实框架名，否则留空 | 优先作为 `<browser-driver>` 候选 |
| `frontend_design_path` | 前端设计文档路径 | 指向 `story-delta-frontend-design.md`，缺失时写「未见」 | 追溯组件树与接口契约来源 |
| `baseline_source` | 视觉基线来源档位 | 必填：`prototype` / `reference_page` / `text_spec` / `none` | 作为候选输入，Phase A2 确认后才冻结 |
| `prototype_dir` | HTML 原型所在目录 | `prototype` 时填写真实目录 | 定位 `<prototype-dir>` 并实测 |
| `reference_route` | 参照页路由候选 | `reference_page` 时写候选，不写成既定结论 | Phase A2 让用户确认 |
| `affected_routes` | 本 Story 受影响的路由 | 逗号分隔 | 页面识别与风险闭包 |
| `required_states` | 必测交互状态 | 只列明确要求的 `hover,focus,disabled,selected,loading,empty,overflow` 子集 | 合并候选场景，不自动逐 Task 执行 |
| `restore_tasks` | 还原轮 Task 编号 | 无还原轮留空 | 形态索引；冲突时以 Task 内容为准 |
| `risk_triggers` | 风险触发器 token | 只写计划事实直接支持的 token | 与仓库事实、实际 diff 合并后编译验证组合 |

风险 token 的唯一完整注册表在 [validation-policy.md](./validation-policy.md#三风险触发器)。计划侧通常只会直接识别 `visual`、`interaction`、`navigation`、`shared-boundary`、`auth`、`write`；需要代码勘察的 token 留给 Dev。

两条测试通道分字段记录，是因为一条通道存在证明不了另一条：只装 Vitest 的仓库没有浏览器通道，只装 Cypress 的仓库没有组件通道。状态字段与框架字段也必须分开——把 `未识别` 这类状态值写进框架名，下游就无法区分「探测过但没有」和「框架就叫这个名字」。四个字段缺席时按 `unknown` 处理，由 Dev 按实际事实补判，不解释成 `absent`。

## 基线源

先判断 Story 是否产生或改变静态形态，再选第一个成立的来源：

| 档位 | 成立条件 | 计划承诺 |
| --- | --- | --- |
| `prototype` | HTML 原型确含对应页面 | 给出原型、路由和区块名；锚点与数值由下游抽取、冻结 |
| `reference_page` | 无原型，但仓内有同类已上线页面 | 给候选参照页，等待下游确认 |
| `text_spec` | 只有可逐条落地的文字规格 | 只承诺仓内 token、一致性、无横向滚动/重叠/截断及文字规格 |
| `none` | 没有外部基线，或 Story 纯逻辑 | 写明原因与缺口；不发明视觉规格 |

没有原型不等于没有还原 Task。只要静态形态发生变化，仍需还原 Task；`text_spec` / `none` 只是收窄可证明的范围。

## Task 切分与步骤形状

1. 跨页公共骨架先成 Task。
2. 每页静态结构和样式集中为一个还原 Task，排在该页逻辑 Task 前；还原 Task 独占样式文件。
3. 逻辑 Task 按紧邻 AC 分组。确需改样式时登记文件、原因和被失效的还原 Task。
4. 每个还原 Task 写视觉来源、路由和职责单一的区块名；class 锚点由 Dev 抽取。
5. 不创建「样式微调」「统一优化」「走查修复」类收尾 Task。

证据形态只有逻辑、还原、机械三类。优先按形态拆 Task；确实切不开时在同一 Task 分轮，每轮独立引用声明，不互借证据。

### 规模

| 项 | 判据 | 越界了怎么办 |
| --- | --- | --- |
| 一个 Story 的 Task 数 | 3–7 | 先合并同页机械 Task；仍超过 8 说明 Story 本身太大，回流上游拆 Story，不靠计划硬塞 |
| 一个 Task 的文件数 | ≤ 5，还原 Task 的样式文件计入 | 按页面或按声明再切一刀 |
| 一个 Task 的步骤数 | 2–5 | 写不下 5 步就拆 Task |

**Task 层面不设非编码 Task。** 确认基线、勘察代码、评审走查、补文档、跑回归都不占 Task 编号：勘察在计划期就已完成，确认与检视属于 Dev 的 Phase A/C，证据登记是每个 Task 的末步。tasks.md 里每个 Task 都必须改到产品代码或测试代码。

步骤分三类，比例失衡本身就是切分出了问题的信号：

| 类 | 内容 | 每个 Task 的量 |
| --- | --- | --- |
| 编码步 | 写会失败的断言、实现、机械改动 | 逻辑 2、还原 1、机械 1 |
| 收口步 | 回填账本并提交 | 恰好 1 |
| 判断步 | 取 RED 报告、确认原因 | ≤ 1，且只在条件追加步成立时才有 |

典型 Story（1 机械 + 2 还原 + 3 逻辑，共 6 个 Task、16 步）的分布约为 **编码 9 : 收口 6 : 判断 1**。收口步是每 Task 一次的固定成本，压不下去；判断步一多，说明计划把该在计划期定完的事推给了执行期。

### 步骤按形态裁剪

步骤数**不固定**。每个 Task 2–5 步，只写声明与因果意图，不写命令。写不下 5 步说明该拆 Task；把每个 Task 都凑成同样多步只会制造空步骤和重复验证。

| 形态 | 必需步骤 | 为什么是这个数 |
| --- | --- | --- |
| 逻辑 · `test_case` | ① 写会失败的断言并确认失败（点明受影响声明与改动前缺口） ② 最小实现并让同一断言转绿 ③ 回填账本并提交 | 测试通道便宜且精确，逐 Task 保留完整因果 |
| 逻辑 · `manual_acceptance` | ① 实现人工验收候选（在文件范围内达成可观察声明，不新增自动化测试文件） ② 让受影响范围的编译/类型/lint/构建保持通过 ③ 登记待人工验收并提交（`manual_outcome=NOT_RUN`、`claim_status=UNVERIFIED`） | 没有自动化断言可取，因果由人工验收卡承载；agent 到「登记」为止，不代签 |
| 还原 · `restore_contract` | ① 对冻结还原契约取一次 RED 报告 ② 在 Task 文件范围内实现，复跑同一契约转绿 ③ 回填账本并提交 | 期望值已在冻结基线里，再用散文重述一遍不产生新信息 |
| 机械 · `quality_gate` | ① 改动并让编译/类型/引用通过（写明为什么不需要行为证据） ② 回填账本并提交 | 没有行为分支，因果只有编译这一条 |

「不新增自动化测试文件」这句只允许出现在已经通过人工资格门禁的 Task 里。普通逻辑 Task 继续用 `test_case` 的三步形状；人工分支仍属逻辑形态，不新增第四种形态。

条件追加步，只在成立时才占编号：

| 追加步 | 成立条件 |
| --- | --- |
| 确认原因 | 改动前的缺口可能由多个原因造成（改造既有行为、修缺陷），必须先定位才能确定实现方向 |
| 重构 | 实现后确有不改变契约的必要重构；否则并入实现步，不单独占编号 |

### 取证归属

计划只声明「哪一步应该让哪些声明变成 `PROVEN`」，不安排验证动作。

- 还原取证以**页面**为单位。同页的多个还原轮（不论分在一个 Task 内还是拆成多个 Task）共用同一份冻结契约和同一次 RED 取证；计划写明取证归属哪一轮，其余轮只引用，省去 RED 步按 2 步执行。转绿仍逐轮取得，不互借。
- 逻辑取证以**声明**为单位，走仓库既有最窄测试层级。
- 人工验收取证也以**声明**为单位，但 Task 的 checkbox 只表示实现完成，不表示该声明已通过验收；账本状态独立演进。同页面、同设备、同账号边界的人工项在 Phase C 合并成最短人工操作序列，减少往返。
- 交互状态矩阵、跨页检查、回归和独立检视一律属于 Phase C。计划不为单个 Task 安排页面级复验——页面每多验一轮就多一次浏览器往返，而 Phase C 会按最终 diff 一次编译到位。
