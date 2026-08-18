# Phase -1 / Phase 0 细则 — 仓库接入门与需求执行起点

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分，进入 Phase -1 时完整读取；Phase 0 同时完整读取 [起点质量证据复用与执行 telemetry](./preflight-and-telemetry.md)。硬门禁、输出规范 P1–P8、路径变量、浏览器驱动与 subagent 派发约定以 SKILL.md 为准，本文件不重复。

---

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
| `READY_WITH_LIMITS` | 先分类：会让实现本身不安全/不可执行、或让仓库事实源不可信的 limit 回初始化解除；只影响某种验证动作的 limit 记为候选能力缺口，继续到 Phase 0，由验证组合把依赖声明标 `UNVERIFIED`；未命中当前组合的不探测 |
| `READY` | 继续 Phase 0 |

完成后追加 `phase-1.status` telemetry；若 `<story-dir>` 尚未唯一定位，先保留真实起止时间，Phase 0 第 1 步定位后立即 flush。初始化往返用递增 attempt 保留，不能覆盖或估算。浏览器能力是否需要探测由 Phase 0 的初始验证组合决定，不在仓库接入门固定执行。

路由返回后再次运行 `status` 与 `validate`。未通过不得进入 Phase 0，也不得把仓库未就绪登记成 Story 降级。

**Section 失效的判定以 Story 起点的树为准。** 开工之后再跑 `status`（重跑、Phase C 检视、收口复核），本 Story 自己新增或修改的源码文件同样会让 `REPO-3` 失效——那是本 Story 的产物，不是仓库事实过期，**不回本门**。认定为「自身改动引起」要两条同时成立：

1. `git status --porcelain --untracked-files=all` 列出的文件全部落在本 Story 的改动范围内；
2. `dev-baseline.md` 记录的 REPO-3 指纹（指纹附录，旧产物在工程依据行）与 `repo-baseline.md` 的 `## Section` 表一致。

有一条不成立就是真失效，回本门。**不得为了让 `status` 变绿去刷新 REPO-3**——那会把本 Story 尚未通过检视的代码直接写成仓库范式，检视也就失去了对照物。本 Story 确实产生了值得沉淀的仓库级范式时，走 Phase D 收口后由 `sdd-init-frontend` 刷新。

### Phase 0 — 需求执行起点

主 agent 自己做，不派发。**无决策时不单独占一轮（P6）。**

#### 1. 定位需求路径

按路径表定位 `<story-dir>` / `<requirement-dir>` / `<prototype-dir>`。唯一命中就静默继续；缺失或多候选时按 P7 一轮问完。

`<prototype-dir>` 定位不到时，同一个问题带上参照页或文字规格降级选项。`<design-spec-dir>` 恒为 `<requirement-dir>/design-spec/`，不单独提问。

#### 2. `tasks.md` 缺失时的自动起草分支

`<story-dir>` 里已经有 `tasks.md` 时跳过本步，直接进第 3 步。

没有时，先判断当前会话是否已经把下面四项聊清楚——判据是「读得出来」，不是「大致有印象」：

| 需要的信息 | 对应 `tasks.md` 章节 |
| --- | --- |
| Story 范围、目标页面 / 组件 | 计划头、项目边界 |
| AC 列表，或能从会话原文反推出的验收点 | Story / AC 追溯表 |
| 每个页面 / 区块的还原基线（HTML 原型 / 参照页 / 文字规格三档之一） | Task List 的区块来源 |
| 对接模式（完整对接 / 静态实现） | 计划头 Architecture |

| 判断结果 | 动作 |
| --- | --- |
| 四项都聊清楚了 | 照 [story-artifact-templates.md](./story-artifact-templates.md) 第三节的模板，从会话内容起草 `tasks.md`；同时缺 `alpha-tests.md` / `story-delta-frontend-design.md` 时一并起草。会话没提到的字段一律写「未定义 / 待确认」，**不得替用户做设计决策，不得编造响应式规格或状态样式**（同硬门禁 7） |
| 缺某一项，但只是没问过 | 按 P7 一轮问完缺的那几项，答完再起草，不拿会话之外的内容替用户填 |
| 需求横跨多个 Story 或多个仓 | **不自动起草**：这类拆分工作量本身就需要 `sdd-task` / `sdd-design`，提示改用正式上游 |
| 会话里的信息本来就模糊（状态样式、异常分支从没讨论过） | **不自动起草**：先澄清缺口或改用 `sdd-task` 走正式设计评审，起草不能替代还没做过的设计思考 |

起草稿写好后过一轮独立确认门，不与其他决策同轮：

```
---
**[Phase 0 确认门]** 已按本次会话内容起草 `tasks.md`（<N> 个 Task、<M> 条 AC）<、alpha-tests.md 骨架><、story-delta-frontend-design.md>，全文如下：
<起草文件全文，不摘要>
→ 请确认可以落盘继续 / 或指出需要修改的地方。
---
```

用户确认后落盘到 `<story-dir>`，视为满足硬门禁 1，继续第 3 步；指出要改的地方则改完重新走这道确认门，不落盘、不带着分歧继续。

**这条分支只解决「文件从哪来」，不降低标准。** 起草稿一样要经过 Phase A2 的 QA 基线确认门；「未定义」字段照常按硬门禁 14 类规则登记进「已知缺口」，不因为是起草出来的就被放行。

#### 3. 按需读取仓库 baseline

此时只读两个 section，**`--baseline-dir` 是必填参数**：

```bash
python3 "<init-skill-dir>/scripts/manage_repo_baseline.py" show \
  --baseline-dir "<repo-baseline-dir>" --section REPO-1
```

- `REPO-1`：当前 Story 所需的启动、账号/角色/租户、fixture、API/mock、浏览器契约；
- `REPO-2`：当前 app 实际存在的规范质量命令；
- `onboarding-report.md`：当前机器实证、limits、仍保留进程。

不要在 Phase 0 读取 `REPO-3`；代码侧勘察再按当前需求选读。

#### 4. 固定本次执行上下文

从 `tasks.md`、AC、仓库 baseline 与 onboarding report 得到：

- Story 范围、目标页面与路由；
- Git `base-ref`、起点 SHA、工作区初始状态；
- 本次账号、角色、租户、fixture、API/mock 模式；
- 若验证组合选择浏览器相关模块：`<browser-driver>` 取到哪一档，目标路由能否打开、截图与结构化采集能否使用；未选择时记 `not-selected`，不探测。

事实能从仓库或上游读出就直接记录；多个场景都合理且会改变验收结果时才按 P7 请用户决定。

##### 上游接缝字段（`sdd-task-frontend` 产出时才有）

`tasks.md` 的 TaskPacket 头可能带 `baseline_source` / `prototype_dir` / `reference_route` / `affected_routes` / `required_states` / `restore_tasks` / `risk_triggers`。它们由 `sdd-task-frontend` 写入，**全部是候选输入：缺席不代表低风险，也不是降级项**。

| 字段 | 怎么用 |
| --- | --- |
| `baseline_source` | 作为 [基线源](../SKILL.md#基线源没有-html-原型时) 三档判定的**候选答案**，省掉一轮探测 |
| `prototype_dir` | 作为 `<prototype-dir>` 的候选值，唯一命中则不占提问位 |
| `reference_route` | 第 2 档时作为参照页**候选**交给 `recon-codebase` 与确认门 |
| `affected_routes` | 目标页面、路由与风险闭包输入 |
| `required_states` | 候选验证组合的状态输入，不表示逐 Task 执行 |
| `restore_tasks` | 还原轮索引，供 Phase B 少猜形态 |
| `risk_triggers` | 上游从计划事实识别出的候选风险触发器 |

三条约束，缺一条这些字段就会变成第二个真相源：

- **验证，不采信。** 按 `baseline_source` 行动前必须核实：声明 `prototype`（或给了 `prototype_dir`）时，该目录要真的存在且含 HTML。核不上就按本文既有方式重新判档，并在执行起点记一行「上游声明 `<值>`，实测不成立，改判 `<档>`」。**判错的后果是整个 Phase A1 被错误跳过**（判据见 [Phase A 细则](./phase-spec.md)），这个核实很便宜，不得省。
- **不替代确认门。** `baseline_source` 与 `reference_route` 进的是 Phase A2 确认门的输入，**不是冻结结果**。参照页收集候选属事实、选哪一个仍属决策，照原规则进确认门——用户确认的不只是期望值，还有本次拿什么当基线。
- **Task 内容优先，最终 diff 收口。** 字段与正文冲突时以正文为准；实现后的风险触发器再与最终 diff 取并集。字段只是索引，不冻结验证组合。

完整读取 [声明驱动的验证策略](./validation-policy.md)，从 AC/AT、Task 文件范围、`affected_routes`、`required_states`、上游 `risk_triggers` 与仓库 baseline 编译**初始验证组合**。拿不准依赖闭包时加入 `unknown-deps`，不按 Task 数或文件数猜低风险。

把以下内容写入 `dev-baseline.md / 验证组合`：

- 验收声明列表，初始状态均为 `UNVERIFIED`；
- 风险触发器及其证据来源；
- 每条声明需要的验证模块；
- 初始 `review_roles`；
- 因能力缺失暂时无法执行的模块及受影响声明。

若初始组合含 `render`、`journey`、`review-layout` 或需要浏览器的 `self-test`，此时按 [浏览器驱动](../SKILL.md#浏览器驱动) 三档解析并实际打开目标路由；失败只让依赖模块未执行、相关声明保持 `UNVERIFIED`。组合未选择浏览器模块时写 `browser-driver: not-selected`，不启动页面、不生成探测记录。Phase C 因最终 diff 新增浏览器模块时再走同一解析。

完成路径、场景、工作区与初始组合后追加 `phase-0.context` telemetry。

#### 5. 提取或精确复用开工失败集合

只为初始验证组合选中的 `targeted-quality` / `regression` 命令取得起点失败集合。命令入口来自 `REPO-2`；组合未选择命令模块时跳过本节，不生成空表。选中时按 [起点质量证据复用与执行 telemetry](./preflight-and-telemetry.md) 执行 `probe`。

| probe | 动作 |
| --- | --- |
| `HIT` | 不再执行同一组命令；复用缓存里的逐命令退出码、耗时和**具体失败集合**，在起点质量表注明 `复用`、状态指纹、来源、记录时间与缓存路径 |
| `MISS` | 实跑组合选中的命令，记录范围、退出码、耗时和具体失败集合；用同一 snapshot + 紧凑结果 `record --source phase-0` |

不存在的类别不生成表格行。任何网络 / 外部 / 时变命令使整组证据固定 `MISS`，不得只复用其中一部分后拼出一套新结果。

这组结果属于 `DEMAND-2`，与状态指纹和命令 scope 绑定。Phase C 按最终 diff 重编译组合：相同命令若证据仍新鲜可复用；新增模块只补相应命令。只有 `regression` 升级到全量时才执行 REPO-2 全套。

#### 6. 设计事实预检

原型存在时只取统计与路径事实：

- 用 `wc` 判断格式化档或单行导出件，不读正文；
- A1 的抽取脚本负责资源完整性和原型指纹；
- 格式化档锚点可附行号，单行档只用 class 结构。

#### 7. 写执行起点

新建 `<story-dir>/dev-baseline.md`，先写 `DEMAND-2`；Phase A2 再追加 `DEMAND-3`。**模板与两条约束在 [story-artifact-templates.md](./story-artifact-templates.md) 第一节。** 起点质量表必须区分 `实跑` / `复用`，不能只抄结果让后续读者猜来源。
