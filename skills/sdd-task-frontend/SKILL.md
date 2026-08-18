---
name: sdd-task-frontend
description: 为单个前端仓 × 单个 Story 生成 tasks.md 与 alpha-tests.md：定义可观察验收声明、按形态切分还原/逻辑 Task、烘焙组件树与 IFC、提炼 mock 集成级 AT- 用例，并向 sdd-dev-frontend 输出基线源、必测状态与风险触发事实。由 sdd-task 的 Step 2.4 路由进入，不写代码、不执行验证、不调用 codespec CLI。
disable-model-invocation: true
---

# 前端单仓实现计划

## 概述

`sdd-task` 是部门多技术栈共用入口，它的通用生命周期、后端规则与公共产物语义不为前端让路。前端专有规则（Task 按形态切、还原/逻辑分轨、基线源降级声明、验收声明与风险触发事实）全部落在本 skill，由 `sdd-task` 的 Step 2.4 按 `type=frontend` 路由进入。

一次运行的作用域是**一个前端仓 × 一个 Story**。需求遍历、`(Story, 代码仓)` 组合的构造、以及 `codespec` CLI 的全部调用都在 `sdd-task`，本 skill 只按交接载荷生成内容并落盘。

产物仍是既有两份、既有路径、既有 codespec schema：`tasks.md` + `alpha-tests.md`。**不新增第三份交接文件**——`sdd-dev-frontend` 的硬门禁 1 把 `tasks.md` 定为唯一执行清单与进度真相，`alpha-tests.md` 是唯一证据账本；另立文件会连带改下游的前置条件、工件管理与路径变量三处。接缝以 TaskPacket 头的增量字段承载，**字段缺席即等价于旧格式**，因此不需要版本号、兼容期或 legacy adapter。

## 上下游边界


| 阶段                 | 负责                                                    | 不负责                        |
| ------------------ | ----------------------------------------------------- | -------------------------- |
| `sdd-task`         | FE 变更名、Story 遍历、`codespec` CLI、后端行全流程、Step 3 汇总       | 前端 Task 内容                 |
| **本 skill**        | 基线源判定、Task 切分、验收声明、风险触发事实、前端烘焙、前端框架探测、mock 集成级 AT- 提炼 | 原型区块锚点、验证组合、还原契约 schema、QA 基线分类与取舍 |
| `sdd-dev-frontend` | 核实风险触发器、编译验证组合、区块锚点抽取、契约冻结、实施、取证与收口                    | 改 `tasks.md` 验收内容          |


**刻意不做的三件事**，理由都是「只有下游算得出，两处各算一次必然冲突」：

- **不产出区块 class 锚点。** 锚点由 `sdd-dev-frontend` Phase A1 的 `extract_design_spec.py` 与 `extract-prototype` 确定性生成。计划阶段只给原型文件、页面/路由与区块名清单。
- **不产出设计指纹。** 原型指纹是 Phase A1 复用 `design-spec/` 的判据，算第二份会让复用判定失真。
- **不复制还原契约的维度与 JSON 字段。** R1–R6 / F1–F4 与契约 schema 归下游，且要过人工确认门冻结。
- **不决定验证动作。** 本 skill 只声明“什么必须成立”和已知风险事实；命令范围、浏览器矩阵、全量门与独立检视由下游按最终 diff 编译。计划里写死它们会形成第二套执行策略。

## 细节归属：Task 管契约，Dev 管实现

上一节分的是**产物**边界，这一节分的是**细节**边界——计划写到多细就该停手。

**判据只有一条，逐条细节自问：**

> 改掉这个细节，AC 或 mock 集成测试的断言会不会变？
> **会变 → 属 Task**，它是验收契约的一部分，必须写进计划。
> **不会变 → 属 Dev**，它是实现自由度，写进计划就是越界。

| 属 Task（写） | 属 Dev（不写） |
| --- | --- |
| 对外契约的字面量：枚举取值、URL 常量、请求/响应字段名 | 内部 helper、工具函数、私有方法的名字与调用顺序 |
| 用户可见行为：什么条件下按钮禁用、失败时提示什么 | 达成它的表达式、分支写法、变量命名 |
| 必须存在的 i18n key 与对应的用户可见文案 | key 的分组顺序与字典写法 |
| 精确文件路径与单一职责 | 文件内部结构、导出形态、是否抽 composable |
| 状态迁移的起止态与触发条件 | 用哪个 API 实现跳转 / 清参 / 订阅 |
| testability 锚点（`data-automation-id`） | DOM 层级、class 命名、标签选择 |

**还原轮的视觉细节不走 Step 3。** 间距、色值、字号、状态配色属于 QA 基线与冻结契约（下游 Phase A2 确认门的对象）。在 Step 3 写「PENDING→蓝色、SUCCESS→绿色」会造成两处期望值，而计划里那一处没有外部基线背书。

### 反例（摘自真实前端计划，均为越界）

| 越界写法 | 问题 | 应该写成 |
| --- | --- | --- |
| `{ id: 'DOWNLOAD_CENTER', i18nKey: ..., component: () => import(...), showInMenu: false }` | 对象字面量是实现 | 「新增一条不在侧边栏显示的路由，path 为 `/download-center`」 |
| `<span class="top-bar__user-menu-item" @click="goToDownloadCenter">` | 模板与 class 是实现 | 「用户菜单在『退出登录』上方新增入口，锚点 `top-bar-user-download-center`」 |
| `createAxiosInstance()` + `parseInnerParams` + `parseOuterParams` | 点名内部 helper | 「按仓内既有请求范式发 POST，响应蛇形转驼峰」 |
| 23 个 i18n key 连文案列全 | 字典正文是实现 | 只列断言会用到的用户可见文案 |
| `Modal.alert({ ...onConfirm: () => { window.open(url, '_blank') } })` | 整段调用是实现 | 「成功后弹确认框，含任务编号；确认后在新标签页打开下载中心并携带 taskNo / taskType」 |
| `router.replace({ query: {} })` | 指定 API 是实现 | 「查询完成后清除 URL 上的回填参数」 |

### 与 No Placeholders 铁规的关系

`No Placeholders` 禁的是**待定项**（TBD / TODO / 「适当处理错误」/「类似任务 N」/ 无内容的步骤），**不是要求写得越细越好**。分界就是上面那条判据：

- 缺了会变断言的契约细节 → **占位符缺陷**，计划失败。
- 写了不会变断言的实现细节 → **越界缺陷**，同样是计划失败。

两类都由 Step 8 自审拦截。必须把「越界」也定成缺陷，否则只禁占位符时，模型为了过自审会一路往写代码的方向滑——**多写不受罚、少写受罚，Step 3 就必然退化成实现代码**。

> 按类目（路由 / DOM / 请求 / i18n / 状态 / 视觉）的完整正反例与自审用的机械信号 → [detail-ownership.md](./references/detail-ownership.md)

## 硬门禁

这里的门禁只约束计划阶段的来源、所有权和产物完整性，**不代表执行侧必须跑哪些验证动作**。命令、浏览器、截图、回归与独立检视一律由 `sdd-dev-frontend` 根据声明、风险和最终 diff 缩放。

1. **不调用** `codespec` **CLI。** 交接载荷里缺 schema 或 Story 目录时 Stop，回 `sdd-task`，不自行 `mkdir` 或猜路径。
2. **不改** `sdd-task` **的公共产物语义。** 后端行的产出与本 skill 存在与否无关。
3. **基线源必须显式判定并写入 TaskPacket 头，但声明不等于冻结。** 判不出来时写 `none` 并进「已知缺口」，**不得留空、不得默认按有原型处理**。写进来的档位是**给下游确认门的输入**，不是替用户做掉的决定：`sdd-dev-frontend` 的 Phase A2 确认门仍是唯一冻结点，用户在那里确认的不只是期望值，还有「本次拿什么当基线」。**尤其是第 2 档的参照页选择，收集候选属事实、选哪一个属决策**——本 skill 可以给候选与倾向，不得把它写成既定结论。
4. **无外部基线时不得写出原型级数值。** 第 3 档下 Task 描述里禁止出现具体 px / 色值 / 字号，只能引用仓内 token 与文字规格原文。这条防的是「计划阶段发明规格，执行阶段照着它报 GREEN」。
5. **一个 Task 只承担一种形态。** 切不开的必须注明理由并走多轮 6 步。
6. **不得产出收尾性质的样式 Task**（「样式微调」「统一优化」「视觉走查修复」）。
7. **保留 6 步 checkbox 形状以兼容 `sdd-task`，只写因果证据意图。** Step ①/④ 分别声明改动前怎样暴露缺口、改动后要证明哪条验收声明；不写精确命令、全量回归、浏览器矩阵或独立检视。具体动作归 `sdd-dev-frontend` 的验证组合。
8. **No Placeholders 铁规沿用** `sdd-task`：禁 TBD / TODO / 「类似任务 N」/ 无要点步骤。
9. **不写实现代码。** Step 3 只写「改哪个文件 + 达成什么可观测行为」，不得出现对象字面量、模板片段、完整函数体、内部 helper 名或指定 API 调用。判据见「细节归属」，越界与占位符同为计划缺陷。
10. **同一契约细节只写一处。** 枚举取值、字段名、URL 常量在 Step 1 的测试要点或 Step 3 的实现要点里出现一次即可，不得两处各列一遍全量清单——那是真实计划里最大的一块冗长来源。



## 最短路径


| #   | 做什么                                   | 到什么算过                   |
| --- | ------------------------------------- | ----------------------- |
| 1   | 校验交接载荷八项齐备                            | 缺项已 Stop 或已注明「未见」       |
| 2   | 判基线源档位 + 判本 Story 有无静态呈现工作            | `baseline_source` 已定    |
| 3   | 烘焙组件树 / IFC / testability 锚点          | §3.4 表填满或已标降级           |
| 4   | 按 `detection_ref` 探测前端测试框架            | `test_framework` 已填     |
| 5   | 按 `extraction_ref` 提炼 mock 集成级 AT- 用例 | 每条 SC-/BR- 至少一条 AT- 覆盖  |
| 6   | 按形态切 Task，排序，归属样式文件                   | 切分自查全过                  |
| 7   | 写验收声明、因果证据意图与风险触发事实；Step ③ 只写可观测行为 | 无固定验证动作、越界与重复扫描无命中   |
| 8   | 写接缝字段 + 落盘两份                          | 完成标准全过，回传路径给 `sdd-task` |




## 执行步骤



### Step 1：交接载荷校验

逐项核对 `sdd-task` Step 2.4 的载荷表。`story-delta-frontend-design.md` 与包根 `requirement-frontend-design.md` 缺失**不 Stop**，按 `sdd-task` 既有降级规则标注 `⚠️ 降级：无 requirement-frontend-design`，并影响 Step 2 的档位判定。

### Step 2：基线源档位与还原轨判定

**两个正交问题，先后回答，不可合并。**

问题一 —— 本 Story 有没有静态呈现要落地？纯逻辑/接口改造（改数据流、换接口、加状态迁移，不新增或改动页面结构与样式）**不出还原 Task**，全部走逻辑 Task。

问题二 —— 有静态呈现时，期望值的外部出处是哪一档？三档取第一个成立的，档位决定承诺强度：


| 档   | 基线源             | 期望值出处                                 | 写进 Task 的承诺                                              |
| --- | --------------- | ------------------------------------- | -------------------------------------------------------- |
| 1   | HTML 原型         | 下游 `design-facts.json` + 区块规格         | 逐区块还原，可给原型级数值                                            |
| 2   | 参照页（仓内已上线同类页面）  | 参照页实测值 + 仓内 token 范式                  | 类比还原，标可信度降级                                              |
| 3   | 文字规格 + 仓内 token | `story-delta-frontend-design.md` 文字规格 | **收窄**为 token 一致性 + 「不破」三项 + 文字规格逐条落地；**禁写原型级数值**（硬门禁 4） |


档位与三档的语义**与** `sdd-dev-frontend` **的基线源表一一对应**，本 skill 只负责在计划阶段把它声明出来，让下游不必重新推断，也不会在无基线时伪称完成了视觉还原。

> 判据细则、第 3 档的「不破」三项定义、以及档位与 `restore_tasks` 的联动 → [baseline-source.md](./references/baseline-source.md)



### Step 3：前端烘焙

承接 `sdd-task` 原 Step 2.5 的四项：组件树摘要、IFC 切片、testability 锚点、`style-reference` 路径。IFC↔API 缺口需后端补齐时记入风险并回流 Design，**禁止**在前端仓改后端代码。

### Step 4：前端测试框架探测

按 `detection_ref` 指向的 `sdd-task/references/test-framework-detection.md` 扫描 `package.json` 与测试目录结构，识别组件测试框架，填 TaskPacket 头 `test_framework`。**判据只读那一份，不在本 skill 复制正文。** 探测失败即 Stop，不得默认 Jest。

### Step 5：AT- 用例提炼

按 `extraction_ref` 从 SC-/BR-/§5 GWT 提炼 **mock 集成级**用例（Given 组件状态 + mock API 响应 / When 用户交互 / Then 渲染结果 + API 调用断言），分配 `AT-{story_id}-NNN`，落盘 `alpha-tests.md` 四节结构。

### Step 6：Task 切分

五条要求，全部吸收自现有说明书 `sdd-dev-frontend/references/sdd-task-frontend-split.md`（该文原为「带到上游求人改」的需求说明，本 skill 落地后它降为设计依据）：


| #   | 要求                                                            |
| --- | ------------------------------------------------------------- |
| 1   | 一个页面的样式集中成一个独立的还原 Task，含五态与空态/超长/超多条目的静态呈现                    |
| 2   | 跨页公共样式与骨架单独一个 Task，排在全部页面 Task 之前                             |
| 3   | 还原 Task 独占样式文件；逻辑 Task 的文件清单不含样式文件，例外须写 `越界改样式：<文件> — <原因>`   |
| 4   | 还原 Task 逐区块注明**原型文件 + 页面/路由 + 区块名**（锚点留给下游 Phase A1，见「上下游边界」） |
| 5   | 禁止收尾性质的样式 Task                                                |


同一页面的还原 Task 必须排在它的全部逻辑 Task 之前——行为要挂在 DOM 上，没有结构就没有挂点。

> 五条要求的完整文案、正反例、区块粒度判据 → [task-split.md](./references/task-split.md)



### Step 7：验收声明、因果证据意图与风险触发事实

保留上游 6 步 checkbox 的兼容形状，但计划只写**因果证据意图**，不替执行侧选择命令或宽验证范围。每个 Task 标注它改变的 AT-/AC，并选择能直接证明该变化的通道：

- **逻辑类**：指出要暴露的行为缺口、关键断言与候选测试位置；框架来自 `test_framework`。
- **还原类**：指出视觉来源、页面与区块；下游冻结契约后取得 RED/GREEN。
- **机械类**：仅当变化本质是类型、构建或引用对齐时，允许用编译/构建失败→通过证明；写明为什么没有行为分支。

一个 Task 内无法按形态切开时允许多轮，默认先还原后逻辑。每轮分别引用受影响的验收声明，但不复制同一份期望值。

**六步各自写到哪一层**（配合硬门禁 9 / 10）：

| 步 | 写 | 不写 |
| --- | --- | --- |
| ① RED | 受影响声明 + 证据形态 + 要暴露的缺口 | 完整测试代码、精确命令、宽回归 |
| ② 验证 RED | 一句话写“什么现象才算原因正确” | 命令与环境编排 |
| ③ GREEN | 改哪个文件 + 达成什么**可观测行为** | 对象字面量、模板片段、函数体、内部 helper 名、指定 API 调用 |
| ④ 验证 GREEN | 要变成 `PROVEN` 的声明与最小可观察结果 | 全量门、状态矩阵、独立检视 |
| ⑤ REFACTOR | 按需，一句话 | — |
| ⑥ 提交 | 沿用 `sdd-task` 的内联提交规范 | — |

再从 Task 事实填 `risk_triggers`。只使用 [handoff-fields.md](./references/handoff-fields.md) 的规范 token；拿不准或需要代码勘察才能判断的风险不猜，交给下游补充。Step ③ 的读者是能读代码的 Dev，写清“达成什么”，怎么达成和怎么验证都交给它。

> 兼容 6 步的最小写法、三种证据形态与多轮规则 → [failure-evidence-forms.md](./references/failure-evidence-forms.md)



### Step 8：计划自审

沿用 `sdd-task` 三查主干（AT- 覆盖 / 占位符扫描 / 类型一致性 / 框架一致性），**前端行另查七条**：

1. 组件树 / IFC 是否已烘焙。
2. 每个前端 Task 是否引用了受影响验收声明并写明因果证据意图；全文是否没有精确命令、全量回归、浏览器矩阵与独立检视安排。
3. 每个页面的样式是否集中在一个还原 Task 内；逻辑 Task 文件清单是否不含样式文件，例外是否已登记。
4. 有无「样式微调」「统一优化」「走查」这类无原型对照范围的 Task；`baseline_source=text_spec` 时全文有无原型级数值。
5. **越界扫描**：Step ③ 有无对象字面量、模板片段、完整函数体、内部 helper 名或指定 API 调用（硬门禁 9）。逐条按「细节归属」的判据复核，命中即改写成可观测行为。
6. **重复扫描**：同一份枚举 / 字段 / URL 清单有无在 Step ① 与 Step ③ 各列一遍全量（硬门禁 10）。
7. `risk_triggers` 是否只含计划事实能直接支持的规范 token；视觉、导航、鉴权、写副作用等明显事实有无漏标。

第 5、6 条是**降重的主力**。占位符扫描只往「写得更细」推，这两条是反方向的唯一拦截点；缺了它们，计划长度只会单向增长。



### Step 9：落盘与回传

`tasks.md` 的骨架取 [templates/tasks-frontend.md](./templates/tasks-frontend.md)——它派生自上游 `sdd-task/templates/task.md`，章节编号一致，只把 §3.4 换成还原基线、Task 块加形态标注、自审清单加越界与重复两条。`alpha-tests.md` 仍用上游模板，四节结构不变。

按 `schema_tasks` / `schema_alpha_tests` 的 outputPath 落盘到 `story_dir`，向 `sdd-task` 回传两条路径与降级标注清单。

## 接缝字段

写入 `tasks.md` 的 TaskPacket 头，与既有 `project=` / `test_framework=` / `frontend_design_path=` 同行同格式。**全部可选，缺席即等价于旧格式**，下游 `sdd-dev-frontend` 按既有兜底执行。


| 字段                | 取值                                                        | 下游用途                                       |
| ----------------- | --------------------------------------------------------- | ------------------------------------------ |
| `baseline_source` | `prototype` / `reference_page` / `text_spec` / `none`     | Phase A2 直接取档位，不再重新推断；`text_spec` 时不承诺原型对照 |
| `prototype_dir`   | 路径，第 1 档必填                                                | Phase A1 定位 `<prototype-dir>`              |
| `reference_route` | 路由，第 2 档必填                                                | Phase A2 取参照页实测值                           |
| `affected_routes` | 逗号分隔路由清单                                                  | Phase C 布局检视的跨页范围                          |
| `required_states` | `hover,focus,disabled,selected,loading,empty,overflow` 子集 | 下游验证组合的状态输入；不表示逐 Task 执行               |
| `restore_tasks`   | Task 编号清单                                                 | Phase B 快速定位还原轮，不必逐 Task 猜形态               |
| `risk_triggers`   | 规范 token 的逗号清单                                             | 下游编译验证组合的候选触发事实                         |

三条消费约定，写在这里是为了不让字段变成第二个真相源：

- **`restore_tasks` 与实际切分冲突时，以 Task 内容为准。** 它只是索引，不是判据——`sdd-dev-frontend` 本来就能从「该 Task 有没有样式文件」推断形态。
- **`baseline_source` 是确认门的输入，不是冻结结果**（硬门禁 3）。下游按它省掉探测，但仍要核 `prototype_dir` 是否真的存在且含 HTML 再据此决定跳不跳 Phase A1——判错的后果是整段抽取被跳过。
- **字段不复制正文。** `affected_routes` / `required_states` / `risk_triggers` 只让下游少猜；Task 描述与 AC/AT 仍是内容来源。下游必须用仓库事实与最终 diff 校正，字段不冻结验证组合。


> 字段语义、缺席时的下游行为、与 `sdd-dev-frontend` 路径变量的对应 → [handoff-fields.md](./references/handoff-fields.md)



## Stop If

- 交接载荷缺 `fe_change` / `story_dir` / schema 任一项。
- 前端测试框架探测失败且无法降级标注。
- 任一 AT- 用例无 Task 覆盖，或关键 AT- 用例无法写成可独立判定的验收声明。
- 计划含占位符（TBD / TODO / 无要点步骤 / 「类似任务 N」）。
- `baseline_source` 判不出且无法写 `none` + 已知缺口。
- IFC↔API 缺口需后端补齐（回流 Design，不在前端仓改后端）。



## 完成标准

- 产物为 `tasks.md` + `alpha-tests.md` 两份，路径与 schema 符合交接载荷，未新增第三份文件。
- TaskPacket 头含 `test_framework`、`baseline_source` 与 `risk_triggers`；第 1/2 档另含对应的 `prototype_dir` / `reference_route`。
- 每个前端 Task 只承担一种形态；含还原轮的逻辑 Task 已注明理由。
- 每个页面有且只有一个还原 Task 覆盖该页全部区块（或按区块边界拆出的多个）；无静态呈现工作时无还原 Task 且已说明。
- 还原 Task 排在同页逻辑 Task 之前；公共样式与骨架 Task 排在全部页面 Task 之前。
- 逻辑 Task 文件清单无样式文件，或例外已按要求 3 登记。
- 全文搜「微调」「优化样式」「走查」无命中；`baseline_source=text_spec` 时全文无原型级数值。
- **Step ③ 无实现代码**：无对象字面量、模板片段、完整函数体、内部 helper 名或指定 API 调用。
- **无重复全量清单**：同一份枚举 / 字段 / URL 未在 Step ① 与 Step ③ 各列一遍。
- 前端行另查六条全过。
- 未调用 `codespec` CLI；未改写 `sdd-task` 的后端产物。



## 文件清单


| 文件                                                                             | 何时读                    |
| ------------------------------------------------------------------------------ | ---------------------- |
| [references/baseline-source.md](./references/baseline-source.md)               | Step 2 判档位与还原轨         |
| [references/task-split.md](./references/task-split.md)                         | Step 6 切 Task          |
| [references/failure-evidence-forms.md](./references/failure-evidence-forms.md) | Step 7 标形态、分轮          |
| [references/detail-ownership.md](./references/detail-ownership.md)             | Step 7 写 Step ③、Step 8 越界扫描 |
| [references/handoff-fields.md](./references/handoff-fields.md)                 | Step 9 填接缝字段           |
| [templates/tasks-frontend.md](./templates/tasks-frontend.md)                   | Step 9 落盘骨架            |

外部单一来源，**不在本 skill 复制正文**：

| 文件                                             | 用途                    |
| ---------------------------------------------- | --------------------- |
| `sdd-task/references/test-framework-detection.md`  | Step 4 框架探测判据（`detection_ref`）  |
| `sdd-task/references/acceptance-criteria-extraction.md` | Step 5 AT- 提炼判据（`extraction_ref`） |
| `sdd-task/templates/alpha-tests.md`                | `alpha-tests.md` 骨架   |

设计依据（已由本 skill 执行，**不再需要带到上游**）：`sdd-dev-frontend/references/sdd-task-frontend-split.md`、`sdd-dev-frontend/references/sdd-task-amendments.md`。
