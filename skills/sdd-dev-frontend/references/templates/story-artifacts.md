# Story 工件模板

只在创建对应工件时读取本文件的对应小节。QA 基线字段以 [qa-baseline.md](./qa-baseline.md) 为准；验证组合以 [validation-policy.md](../validation-policy.md) 为准；机器报告与 schema 不在 Markdown 模板重复。

## 一、`dev-baseline.md`

```markdown
# dev-baseline — <Story>

| 字段 | 值 |
| --- | --- |
| Story / repo | <...> |
| 基线源 | <候选 → 确认结果；原型 / 参照页 <路由> / 文字规格> |
| 来源指纹 | <...> |
| 冻结状态 | 待确认 / 已冻结 ✅ |
| 确认时间 | <YYYY-MM-DD> |
| 声明状态 | 冻结时全部为 `UNVERIFIED`；逐条状态见 `alpha-tests.md` 的 AC ↔ 证据映射 |
| 执行档位 | lite / standard；附三项判据取值（还原 Task、命中的触发器、文件数）。Phase C 升档时同行追加原因 |
| app baseline | <目录 + 本次读过的关注点文件；app baseline 没有 readiness 字段> |
| 设计事实 / 区块规格 | <路径；基线源非原型时写“无（基线源为 …）”> |
| 还原契约 | <evidence-dir>/restore-contract.json；无还原声明时写“无” |

## 给人的摘要

- 做什么：<路由、能力与用户可见结果>
- 标准来自哪里：<原型 / 待确认参照页 / 文字规格 / 纯逻辑>
- 本次确认：<适用 QA 声明数、豁免数、工作假设与必须决策项>

## 执行起点（环境）

| 项 | 值 |
| --- | --- |
| `base-ref` | <...> |
| 需求路径 | <tasks / alpha-tests / frontend-design> |
| 起点质量命令 | <命令与起点失败集合；全通过写“失败集合为空”> |
| 场景 | <dev server、账号 / 角色 / 租户、fixture、API 或 mock 模式> |
| Story 限制 | <只列影响已选模块的限制；无则“无”> |

## 起点质量

| 已选模块 | 命令 / scope | exit / failures | 证据键 |
| --- | --- | --- | --- |

## 验证组合（初始）

| 风险触发器 | 模块 | 独立检视与维度 | 依赖声明 |
| --- | --- | --- | --- |

## 工程依据

| Story 需要 | 采用依据 |
| --- | --- |
| <能力，如“后端取数”> | `PATTERN-*` / `REQ-DEC-*` |

<勘察模式；选择理由。只保存采用的 ID，不复制 app baseline 正文>

## 功能理解

<Story 范围、AC、页面/状态/接口映射；不超过 200 字>

## QA 基线

<按 qa-baseline.md 生成：基线头、实际适用的 R/F 表、### 豁免表、### 已知缺口、### 变更记录>
```

没有「指纹附录」：来源指纹在文档头表一行，还原契约与证据包各自带自己的哈希，第三份只会不一致。

**`lite` 档只写**：头表、执行起点、起点质量、验证组合、QA 基线；「工程依据」缩成一行「采用：`PATTERN-…`、`REQ-DEC-…`」，「给人的摘要」与「功能理解」省略——`tasks.md` 的 Goal 和用例追溯已经回答。Phase C 升为 `standard` 时补齐，不回头改历史节。

「已知缺口」「变更记录」「豁免表」是 `## QA 基线` 之下的 `### `，不另起顶级节——它们随基线一起被冻结和重新确认，摆成平级会让人以为改它们不用走确认门。

## 二、`alpha-tests.md`

只在首次记录还原证据或 Phase D 对账时读取本节。`alpha-tests.md` 是唯一证据账本；机器报告保留完整事实，账本只保存可追溯索引。计划外承接的权威登记也在这里，规则见[执行契约的扩散承接](../execution-contract.md#扩散承接)。

### 还原证据记录

每个还原轮追加一张两行表；契约只抄 sha8，报告指纹不抄。唯一例外是 GREEN 行在「说明」中保存完整代码指纹，供 Phase C 判断能否复用：

```markdown
### R-<Task>-<轮次> · <区块>

| 轮 | 契约 | 报告文件 | 三色 | 说明 |
| --- | --- | --- | --- | --- |
| RED | `<contract sha8>` | `evidence/restore-report-red.json`；新建页面写“—（新建页面，免 RED）” | `<green / yellow / red>` | `<route / viewport / fixture；无则—>` |
| GREEN | `<contract sha8>` | `evidence/restore-report-green.json` | `<green / yellow / red>` | `<route / viewport / fixture；code=<GREEN 时 review-evidence.json / code.code_fingerprint 的完整值>>` |
```

RED/GREEN 必须来自同一冻结契约；哈希不一致、真实 RED 或未解决 YELLOW 都不能支持 `PROVEN`。状态与证据依赖仍分别写入 AC ↔ 证据映射和 `review-evidence.json`，不在这里复制。

### 人工验收记录

只在本 Story 有 `verification_method=manual_acceptance` 的声明时才建这一节。**这里是待人工验收项的权威登记**，`acceptance.md` 里那份由聚合器 `aggregate --alpha-tests --tasks` 直接读本表渲染，不手写、不另做 JSON 投影。

```markdown
| 声明 | 追溯 | 依据 | 验收环境 | 需留下的证据 | 人工结果 | 声明状态 | 验收人 | 验收时间 | 证据引用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

**列名与列序是聚合器的解析契约，不要改。** 脚本把它们映射回契约字段名 `id`、`trace`、`manual_basis`、`required_environment`、`required_evidence`、`manual_outcome`、`claim_status`、`manual_checked_by`、`manual_checked_at`、`evidence_refs`；`verification_scope` 从 `tasks.md` 的「用例追溯」取，账本不抄；`DEFERRED` 项的解除条件从下面「Deferred」表取。空格写 `—`，多条证据引用用逗号分隔。字段语义见[执行契约的验证模型](../execution-contract.md#验证模型)，`manual_basis` 枚举与资格门禁见 [validation-policy 第七节](../validation-policy.md#七验证方法的判定规则)。

计划阶段落 `NOT_RUN` + `UNVERIFIED`，验收人与验收时间留空——**不写人名占位符**。只有真实人员执行后才回填后三列；agent 不代签。`PASSED` 但证据不齐仍是 `UNVERIFIED`，`FAILED` 与 RED 同级、不得改写为通过。

### AC ↔ 证据映射

```markdown
| AT | 状态 | 执行环境 | 证据记录 | 新鲜度 | 说明 |
| --- | --- | --- | --- | --- | --- |
```

每条声明恰有一个状态。同一证据可被多条声明引用，不复制报告内容。依赖变化时把命中声明改回 `UNVERIFIED`，重取证后再更新。

「执行环境」写实际取证的档 `mock` / `contract` / `live`（语义见[执行契约的执行环境档](../execution-contract.md#执行环境档)），未取证写 `—`。它与 portfolio 里的 `required_profile` 对账：**低于所需档的声明不得写 `PROVEN`**，`aggregate --alpha-tests` 会拒绝。列名与列序是聚合器的解析契约。

**声明的范围与方法只在 `tasks.md` 的「用例追溯」写一次**，这里按 AT 编号引用；`quality_gate` 机械 Task 没有 AT，不进本表。三处各抄一份范围与方法的代价是改一处漏两处，而账本要回答的只有「证到哪了、在什么环境证的」。

### Deferred

```markdown
| AT | 外部依赖 | 当前证据 | 解除条件 | 恢复入口 |
| --- | --- | --- | --- | --- |
```

状态为 `DEFERRED` 的每条 AT 在这里必须有一行，聚合器核对。「外部依赖」写具体是什么不在（订单后端测试环境、SSO 测试租户、可回滚的写入数据），它会原样进 `acceptance.md` 首句；「解除条件」写可判真假的事件；「恢复入口」固定写「解除 DEFERRED」并注明只需重跑哪些模块。本阶段做得到但没执行属于 `UNVERIFIED`，不写 Deferred。旧 Story 缺还原节时按上述形状增量新增，不迁移既有 L4/L3 记录。

账本的合格判据是 [SKILL.md 的退出门禁](../../SKILL.md#退出门禁)，不在这里再放一份自检。

## 三、`acceptance.md`

**这份文件的主体由 `manage_review_pipeline.py aggregate` 渲染，不要手写。** 它是**人验收时的入口**，所以顺序固定为「能不能验收 → 有什么必须你处理 → 有什么你该知道但不用动 → 往下追的路径」；机器对账细节（代码指纹、证据纪元、逐条覆盖明细）一律不进这份文件，它们在 `evidence/review-results.json` 里。

聚合器渲染的节：

```markdown
# 验收摘要

<第一句就是结论：可验收 / 可验收但有 N 件需要你定 / 暂不可验收，因为 N 条阻断>

## 需要你处理
<阻断级与需要拍板的项；表列固定为「什么问题 / 在哪 / 要你做什么」。全清时整节不出现>

## 你该知道，但不用动
<不需要决定的交接项，一条一行>

## 这次判了什么
<已判并通过的一句话带过；没判到或判不全的逐条给原因；判定不适用的逐条给理由；
 主动收窄的必须署名列出——收窄可见是它存在的全部意义>

## 改进建议（本次不修） / 未决问题 / 暂缓的验收项 / 交 sdd-init-frontend 的规范候选
<各节有内容才出现>

## 要往下追的话
<指向 dev-baseline.md、alpha-tests.md、evidence/review-results.json 的路径>
```

**这个文件没有手写节。** 聚合器整文件覆盖它，所以往里手写的东西会被下一次 aggregate（Phase C 生成、Phase D 更新各一次）冲掉——一个文件只能有一个写入者。

原先要手写的两样各自有了正确的归处：

| 原先手写在这里的 | 现在在哪 |
| --- | --- |
| 计划外承接 | 权威登记在 `alpha-tests.md`；`aggregate --alpha-tests` 直接读那张表渲染 |
| 待人工验收 | 同上：权威登记在 `alpha-tests.md` 的人工验收记录，`aggregate --alpha-tests --tasks` 直接读表，渲染成「需要你处理」里的动作条目。未收口的人工项会让摘要首行不再是无条件「可验收」 |
| 收口结论 | 逐声明状态在 `alpha-tests.md`，阻断清零与退出门禁结论走[最终三行](../../SKILL.md#最终输出)；聚合器不再留「待 Phase D 填写」这类占位，因为占位本身就会被重跑冲掉 |

## 四、Phase 0 自动起草

会话已经明确 Story、AC、基线和文件范围但缺 `tasks.md` 时，直接读取并填写 `<skill-dir>/../sdd-task-frontend/templates/tasks-frontend.md`，不要在本文件维护第二份 tasks 模板。

`alpha-tests.md` 只起草最小骨架，各节逐条填什么见第二节：

```markdown
# <Story> · Alpha Tests
## 每条 AC 的可观察判定
| AC / AT | 页面与路由 | 操作 | 可观察结果 |
| --- | --- | --- | --- |
## AC ↔ 证据映射
| AT | 状态 | 执行环境 | 证据记录 | 新鲜度 | 说明 |
| --- | --- | --- | --- | --- | --- |
## Deferred
| AT | 外部依赖 | 当前证据 | 解除条件 | 恢复入口 |
| --- | --- | --- | --- | --- |
```

有 `manual_acceptance` 声明时再加「人工验收记录」；还原证据记录与计划外承接由 Phase B 首次落账时追加，不预建空节。

缺 `story-delta-frontend-design.md` 时只写已知事实，不补设计：

```markdown
# <Story> · Frontend Design Delta
## 目标与 AC 引用
## 对接模式
## 文字规格
## 当前代码事实
## 状态、交互、接口与数据映射
## 风险与依赖
```

会话未定义的字段写“未定义 / 待确认”，进入 Phase A 的已知缺口；不得用合理猜测填满模板。
