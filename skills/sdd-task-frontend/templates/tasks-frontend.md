# {{project}} / {{story_name}} - 单仓实现计划

> **For agentic workers:** 使用 `/sdd-dev-frontend` 逐任务执行本计划，checkbox 跟踪。

**Goal:** <!-- 一句话：本仓实现什么 -->

**Architecture:** <!-- 2-3 句：本仓实现方案 -->

**Tech Stack:** <!-- 关键技术栈 -->

**TaskPacket:** project={{project}} | codespec_path= | story={{story_name}} | test_framework= | search_paths= | project_type=frontend | frontend_design_path= | baseline_source= | prototype_dir= | reference_route= | affected_routes= | required_states= | restore_tasks= | risk_triggers=

> `baseline_source` 必填（`prototype` / `reference_page` / `text_spec` / `none`）；`risk_triggers` 填计划事实能直接支持的规范 token，其余按档位与实际情况填。字段语义与缺席行为见 `references/handoff-fields.md`。

---

## 1. 项目边界

| 范围内 | 范围外 |
|--------|--------|

> 实现限于本前端仓 `search_paths[]`；REST 契约引用领域 design，**不改 backend 仓**。

## 2. 文件结构（File Structure）

> 锁定分解决策。每个文件单一职责；变更一起的文件应放在一起。对齐 `story-delta-frontend-design` 的组件树。

| 文件/模块 | 变更（新建/修改） | 职责 |
|-----------|-------------------|------|

## 3. 实现设计要点

> **本章只写契约，不写实现。** 判据：改掉这个细节，AC 或 mock 集成测试的断言会不会变？不会变就不写。类目正反例见 `references/detail-ownership.md`。

### 3.1 API/契约

> IFC 切片（来自 frontend-design）+ 对领域 REST 的引用路径。
> 写：URL 常量、方法、请求/响应字段名与命名风格。不写：用哪个请求实例、拦截器配置、内部转换函数名。

### 3.2 数据/配置

> 写：枚举取值、路由 path、必须存在的 i18n key 与断言会用到的用户可见文案。
> 不写：字典正文全表、对象字面量、key 的分组层级。

### 3.3 错误处理

> 写：失败时的用户可见结果（提示文案、状态迁移）。不写：try/catch 结构与实现表达式。

### 3.4 还原基线（`baseline_source` ≠ `none` 时必填）

| 项 | 内容 |
|----|------|
| 基线档位 | <!-- prototype / reference_page / text_spec，与 TaskPacket 头一致 --> |
| 视觉来源 | <!-- 第 1 档：原型文件路径；第 2 档：参照页路由候选清单 + 倾向项（标「候选，待下游确认」）；第 3 档：文字规格章节号 --> |
| 页面与区块 | <!-- 逐路由列出区块名（名词短语，视觉职责单一） --> |
| 必测状态 | <!-- 与 required_states 一致 --> |
| 承诺范围 | <!-- 第 3 档固定为：仓内 token 一致性 + 「不破」三项（无横向滚动/无重叠/无内容截断） + 文字规格逐条落地 --> |
| 已知缺口 | <!-- 判不出档位、无参照页、规格缺失项 --> |

> **不写 class 锚点**——锚点由下游 Phase A1 的抽取脚本确定性生成，计划阶段另算一份必然冲突。
> **不写具体 px / 色值 / 字号**——视觉数值属 QA 基线与冻结契约，由下游 Phase A2 确认门冻结。第 3 档给数值就是发明规格。
> `baseline_source=none` 时删除本节，并在 Task List 前写一行：`无还原 Task：本 Story 不产生新的静态形态（<一句话>）`。

### 3.5 testability 锚点

| 锚点 `data-automation-id` | 所在元素 | 被哪条 AC / AT- 用例选取 |
|---|---|---|

> 锚点属 Task（测试直接选它，改了断言必变）。class 名不属 Task。

## 4. 用例追溯表

> 执行视角：AT- 用例 → Task（**不含 SC-/BR- 列**——需求锚点覆盖在 alpha-tests.md 覆盖矩阵，此处不重复）。

| AT- 用例标识 | 用例标题 | 覆盖任务 |
|-------------|----------|----------|

## 5. 执行规则

- **声明诚信：** 没有覆盖验收声明的新鲜证据，就不能把它标成 `PROVEN`。
- **No Placeholders 铁规：** 禁止 TBD、TODO、"适当处理错误"、"类似任务 N"、无要点的步骤。
- **不越界铁规：** 禁止对象字面量、模板/JSX 片段、完整函数体、内部 helper 名、指定 API 调用、视觉数值。**越界与占位符同为计划缺陷。**
- **禁止修改测试以适配实现**；测试表达验收契约。
- 仅在确认的 `search_paths[]` 内执行；超出须记录原因并回流 Design。
- 每条任务必须 trace 到 `alpha-tests.md` 的 AT- 用例标识。计划只写因果证据意图；命令、范围、浏览器矩阵、全量门与独立检视由 Dev 根据风险触发器和最终 diff 编译。

### 因果证据形态

| 形态 | Step 1 内容 | Step 4 声明 |
| --- | --- | --- |
| **逻辑** | 受影响 AT-/AC + 行为缺口 + 关键断言 + 候选测试位置 | 哪些声明应变成 `PROVEN` |
| **还原** | 受影响 AT-/AC + 视觉来源 + 页面/区块 + 预期差异 | 哪些声明应由冻结契约证明 |
| **机械** | 类型/构建/引用缺口 + 为什么没有行为分支 | 哪些声明应由编译或构建事实证明 |

保留 6 步 checkbox 兼容形状；每轮标注形态，但不预排双通道、并行或复用策略。细则见 `references/failure-evidence-forms.md`。

## Task List（任务清单）

> 每个 Step 写**要点描述**（不写全量代码），前缀 `- [ ]` checkbox；勾选即代表该 Step 完成。
> 切分口径：公共样式与骨架 Task 最前 → 每页一个还原 Task → 该页逻辑 Task。细则见 `references/task-split.md`。

### Task 1: <页面名> · 还原 [用例: AT-{{story_id}}-001]

**形态:** 还原

**视觉来源:** <!-- 原型文件 / 参照页路由（候选） / 文字规格章节号 -->
**路由:** <!-- 本 Task 覆盖的路由 -->
**区块:** <!-- 逐个列出区块名 -->

**Files:**
- Create: `精确路径`
- Modify: `精确路径`
- Style: `精确样式文件路径` <!-- 还原 Task 独占样式文件 -->

- [ ] **Step 1: 暴露缺口（RED）— 形态：还原** — 受影响声明：<AT-/AC>；视觉来源与页面/区块：<...>；预期差异：<...>

- [ ] **Step 2: 确认原因** — <什么现象才算差异来自未实现，而非基线/工具/环境问题>

- [ ] **Step 3: 写最小实现（GREEN）** — 实现要点：改哪个文件 + 达成什么可观测行为（不写实现代码，YAGNI）

- [ ] **Step 4: 证明声明（GREEN）** — <AT-/AC> 应变成 `PROVEN`；最小可观察结果：<...>

- [ ] **Step 5: （按需）REFACTOR，保持绿色**

- [ ] **Step 6: 记录证据并提交** — 在 `alpha-tests.md` 回填实际证据与声明状态后提交

```bash
git add <files>
# commit message（内联提交规范，见 sdd-task「提交规范」章节）：
#   【问题单号 Defect】{work_item_id}
#   【修改说明 Modification】{type}({scope}): {description}
# variables: work_item_id={需求单号或BUG单号}, type=feat|fix|refactor|docs|test, scope=<module>, description=<task-summary>
git commit -m "【问题单号 Defect】{work_item_id}" -m "【修改说明 Modification】{type}({scope}): {description}"
```

---

### Task 2: <页面名> · <行为分组> [用例: AT-{{story_id}}-002]

**形态:** 逻辑

**Files:**
- Modify: `精确路径`
- Test: `精确测试路径`

<!-- 逻辑 Task 的文件清单不得含样式文件。确有必要时显式登记：
     越界改样式：<文件> — <原因>；影响 Task <编号> 的 GREEN 报告 -->

- [ ] **Step 1: 暴露缺口（RED）— 形态：逻辑** — 受影响声明：<AT-/AC>；行为缺口、关键断言与候选测试位置：<...>

- [ ] **Step 2: 确认原因** — <什么现象才算因正确原因失败>

- [ ] **Step 3: 写最小实现（GREEN）** — 实现要点：改哪个文件 + 达成什么可观测行为

- [ ] **Step 4: 证明声明（GREEN）** — <AT-/AC> 应变成 `PROVEN`；最小可观察结果：<...>

- [ ] **Step 5: （按需）REFACTOR，保持绿色**

- [ ] **Step 6: 提交** — 勾选即代表本轮完成

---

<!-- 一个 Task 内含两种形态时，按下面的形状分轮，两轮各走完整 6 步：

### Task N: <区块名> [用例: AT-...]

**含还原轮的理由:** <!-- 为什么切不开：样式由运行时状态计算得出，静态形态不存在 -->
#### Task N · 轮 1（还原）
… 6 步 …
#### Task N · 轮 2（逻辑）
… 6 步 …
-->

## 6. 计划自审清单

- [ ] **AT- 用例覆盖：** 每条 AT- 用例都指向具体 Task N，且向上追溯 SC-/BR- 锚点完整
- [ ] **占位符扫描：** 无 TBD/TODO/无要点步骤/"类似任务 N"
- [ ] **越界扫描：** Step 3 与第 3 章无对象字面量、模板/JSX 片段、函数体、内部 helper 名、指定 API 调用、`#` 色值 / `px` / `rem`
- [ ] **重复扫描：** 同一枚举 / 字段清单 / URL 常量在全文只出现一处
- [ ] **声明与证据意图：** 每个 Task 引用受影响 AT-/AC 并写明证据形态；还原轮有视觉来源与区块名，且**无 class 锚点**
- [ ] **动作越界：** 全文无精确验证命令、全量回归、浏览器矩阵、独立检视与双通道调度
- [ ] **风险触发事实：** `risk_triggers` 只含规范 token；明显的视觉、交互、导航、公共边界、鉴权或写副作用无漏标
- [ ] **切分口径：** 每页一个还原 Task 且排在该页逻辑 Task 之前；逻辑 Task 无样式文件（例外已登记）；无「样式微调 / 统一优化 / 走查修复」类 Task
- [ ] **基线一致性：** 第 3.4 节的档位与 TaskPacket 头 `baseline_source` 一致；`prototype` 档位的 `prototype_dir` 真实存在且含 HTML；第 3 档未出现原型级数值
- [ ] **类型一致性：** 跨任务的方法签名、类型名、属性名一致
- [ ] **框架一致性：** 逻辑轮 Step 1 的测试要点与 TaskPacket 头 `test_framework` 声明一致

## 7. 风险与回滚

| 风险 | 缓解措施 | 回滚方案 |
|------|----------|----------|
