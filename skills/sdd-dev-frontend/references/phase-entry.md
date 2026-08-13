# Phase -1 / Phase 0 细则 — 仓库接入门与需求执行起点

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分，进入 Phase -1 时完整读取。硬门禁、输出规范 P1–P8、路径变量、浏览器驱动与 subagent 派发约定以 SKILL.md 为准，本文件不重复。

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
| `READY_WITH_LIMITS` | 对照当前 Story 的页面、视觉、接口和质量需求；任一 limit 命中则回初始化解除，否则记录影响后继续 |
| `READY` | 继续 Phase 0 |

4. 按 [浏览器驱动](../SKILL.md#浏览器驱动) 三档确定 `<browser-driver>`，取到第 1 或第 2 档时实际打开一次目标路由验证，不只看 `REPO-1` 的声明（硬门禁 15）。

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
- `<browser-driver>` 取到哪一档，目标路由能否打开、截图与结构化采集能否使用。

事实能从仓库或上游读出就直接记录；多个场景都合理且会改变验收结果时才按 P7 请用户决定。

再按下表从 `tasks.md` 事实定出**影响面分级**，记入执行起点。分级只影响明示引用它的条款（布局与响应式检视的页面范围等），**不改变任何门禁语义**；拿不准时取更大的一档。

| 级 | 判据 |
| --- | --- |
| S | 同时满足：Task ≤ 2、无新增页面 / 路由、涉及区块 ≤ 2 |
| L | 任一满足：新增页面 / 路由、Task ≥ 5、改动仓库公共组件或公共样式 |
| M | 其余 |

#### 5. 提取开工失败集合

按 `REPO-2` 实跑其中实际存在且适用于当前 app 的规范命令。记录命令、范围、退出码、耗时和**具体失败集合**；不存在的类别不生成表格行。若上游明确要求但 REPO-2 没有对应能力，回 Phase -1 补齐，不在 Story 中写“未提供”。

这组结果属于 `DEMAND-2`，与当前起点提交绑定。`REPO-2` 只说明命令怎么跑，不保存这组失败。

#### 6. 设计事实预检

原型存在时只取统计与路径事实：

- 用 `wc` 判断格式化档或单行导出件，不读正文；
- A1 的抽取脚本负责资源完整性和原型指纹；
- 格式化档锚点可附行号，单行档只用 class 结构。

#### 7. 写执行起点

新建 `<story-dir>/dev-baseline.md`，先写 `DEMAND-2`；Phase A2 再追加 `DEMAND-3`。**模板与两条约束在 [story-artifact-templates.md](./story-artifact-templates.md) 第一节。**
