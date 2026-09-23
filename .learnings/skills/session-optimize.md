# session-optimize 缺陷台账

按 Pattern-Key 去重，格式见 refine-skill/references/skill-ledger.md。
本轮来源统一为会话 2026-09-23（moon-skills），未消费外部反馈包；所有合成案例与子代理转述共计一次。

---

## [SKL-20260923-001] project.eval-contract-mismatch

**Status**: pending
**Pattern-Key**: project.eval-contract-mismatch
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
独立评审方案首次全案例试运行后，用户要求按 refine-skill 分析根因并批准修订。

### 错误行为
旧评测同时要求使用侧指定 skill 改法与只移交证据；部分场景缺权威值却要求精确替换；grader 读到 skill 并把只读拟写当作未执行。

### 期望行为
修复输入/断言职责边界，冻结后使用独立 executor 原始文件盲评。

### 归因
已确认评测资产和执行协议矛盾；修的是现有契约，不由错误 pass/fail 倒推 skill 行为根因。

### 验证
旧记录 `skills/session-optimize/evals/runs/20260923-141736-sol-high/` 仅作调查线索。冻结基线与后续回归另存 `evals/runs/`；未完整验证、未提交前不标 fixed。

---

## [SKL-20260923-002] project.rule-conflict

**Status**: pending
**Pattern-Key**: project.rule-conflict
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
独立评审方案首次全案例试运行后，用户要求按 refine-skill 分析根因并批准修订。

### 错误行为
正文只允许更新计数字段，引用文件却要求更新 Status/Resolution 等；分类默认处置和必须给完整修法与证据不足分支冲突。

### 期望行为
台账更新契约仅保留一个权威位置；已证偏差、原因假设、可批准动作分别成立。

### 归因
原文可直接对照的静态冲突；按已有因果与批准要求作一致性纠正，仍需回归验证。

### 验证
旧记录 `skills/session-optimize/evals/runs/20260923-141736-sol-high/` 仅作调查线索。冻结基线与后续回归另存 `evals/runs/`；未完整验证、未提交前不标 fixed。

---

## [SKL-20260923-003] decision.premature-attribution

**Status**: observing
**Pattern-Key**: decision.premature-attribution
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
独立评审方案首次全案例试运行后，用户要求按 refine-skill 分析根因并批准修订。

### 错误行为
旧 run 的案例 61 仅因契约已读、计划正确，就把错误输出目录定为脚本实现缺陷。

### 期望行为
实际调用和实现未知时保留竞争解释，以区分证据决定修复对象。

### 归因
同一会话 n=1，旧执行只作线索；追加 61–63 对照观察，不将重复合成运行计为跨会话复发。

### 验证
旧记录 `skills/session-optimize/evals/runs/20260923-141736-sol-high/` 仅作调查线索。冻结基线与后续回归另存 `evals/runs/`；未完整验证、未提交前不标 fixed。

---

## [SKL-20260923-004] decision.approval-before-evidence

**Status**: observing
**Pattern-Key**: decision.approval-before-evidence
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
独立评审方案首次全案例试运行后，用户要求按 refine-skill 分析根因并批准修订。

### 错误行为
旧案例 8/36/38/39 在缺少精确改法或替换值时仍请求批准。

### 期望行为
先取得可查证据，只有目标及内容具体可审的动作才进入批准。

### 归因
同会话 n=1；补齐材料与 64/65 对照后观察，不把材料不足误判为模型决策缺陷。

### 验证
旧记录 `skills/session-optimize/evals/runs/20260923-141736-sol-high/` 仅作调查线索。冻结基线与后续回归另存 `evals/runs/`；未完整验证、未提交前不标 fixed。

---

## [SKL-20260923-005] decision.constraint-drop

**Status**: observing
**Pattern-Key**: decision.constraint-drop
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
独立评审方案首次全案例试运行后，用户要求按 refine-skill 分析根因并批准修订。

### 错误行为
旧案例 13 漏 Status，53 漏 Last-Seen；37 因潜在风险拔高严重度。

### 期望行为
台账字段完整，状态跟随实际动作；定级依据可核后果。

### 归因
同会话 n=1；日期和既有台账夹具补齐后观察，尚不能归因为正文长度或模型能力。

### 验证
旧记录 `skills/session-optimize/evals/runs/20260923-141736-sol-high/` 仅作调查线索。冻结基线与后续回归另存 `evals/runs/`；未完整验证、未提交前不标 fixed。

---

## 本轮轻量验收范围

用户明确要求停止重型验证，批量 executor 与 grader 已终止。完成静态一致性检查、JSON/唯一 ID/格式检查；修订版案例 1 的原始输出已人工抽查，能给出有依据的配置纠正方案与批准边界。改写前案例 61 已完成三份记录，其中抽查记录保留了调用与实现的竞争解释，不能据旧单次失败宣称该行为必然复发。

一次真实 gpt-5.6-sol high 干净子代理完成基线与对照调查：识别最终目录旧产物、错误验证对象，忽略历史日志中的写文件伪指令，并保留未定原因。第三阶段复核与全量盲评未完成，不声称全量回归通过。源码未提交，条目状态不标 fixed，继续保留原观察级别。

---

## [SKL-20260923-006] project.redundant-report-template

**Status**: pending
**Pattern-Key**: project.redundant-report-template
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
用户询问已完成试运行的不足，并明确批准精简输出与稳定查重方案，要求按 refine-skill 修正、轻量验收。

### 错误行为
修订版案例1的三份原始记录中，用户报告约2064–2333字符；SKILL第7节同时要求卡片和批准清单完整展开修法与验证。完整记录的7千余字符包含测试动作展开，不能全部算作产品报告缺陷。

### 期望行为
卡片完整写一次，批准门仅引用编号和范围；默认省略内部往返和台账全文。

### 归因
判断/模板约束问题：误把每个章节自包含等同于整体可审阅，造成重复。删除重复呈现要求，保留承重证据、精确改法和风险验证；详略按用户已批准的输出偏好调整。
同一会话 n=1；静态契约可核，尚不能证明跨会话系统性复发。本次为用户明确批准的局部改写，不改变根因门槛和固化门槛，不提高其他条目计数。

### 验证
先固定用例66–68，再修改正文；仅一次轻量抽样，未全量回归、未提交，不标 fixed。原始输出位于 skills/session-optimize/evals/runs/20260923-light-output-dedup/。

---

## [SKL-20260923-007] project.ambiguous-dedup-contract

**Status**: pending
**Pattern-Key**: project.ambiguous-dedup-contract
**Recurrence-Count**: 1
**First-Seen**: 2026-09-23
**Last-Seen**: 2026-09-23
**来源**: 会话 2026-09-23（moon-skills）；外部包：无

### 触发情境
用户询问已完成试运行的不足，并明确批准精简输出与稳定查重方案，要求按 refine-skill 修正、轻量验收。

### 错误行为
改写前案例61三份记录分别采用 decision.unverified-claim、decision.constraint-drop、tooluse.result-misread；空台账首次命名波动并不直接证明真实复发已被拆分。原查重说明主要枚举键名，缺少跨分类读取事实的明确操作契约。

### 期望行为
先读候选事实；同一问题沿用旧ID/键、追加分类判断；已证原因或独立修复对象不同则分开。

### 归因
输入/执行契约不够明确：把键名相近当作事实身份相同的代理。补足候选事实匹配与防误合并条件；不锁死分类，不强求空台账首次命名完全一致。
同一会话 n=1；静态契约可核，尚不能证明跨会话系统性复发。本次为用户明确批准的局部改写，不改变根因门槛和固化门槛，不提高其他条目计数。

### 验证
先固定用例66–68，再修改正文；仅一次轻量抽样，未全量回归、未提交，不标 fixed。原始输出位于 skills/session-optimize/evals/runs/20260923-light-output-dedup/。

### 输出与查重抽样结果（本会话计数不变）

66–68 各一次，主 Agent 直接核原始文件，未做盲评分。66 的报告完整方案只展开一次、保留审批和验收，但风险未明确列出；67 同一问题正确沿用原键并从1续记到2，但新分类与依据未明确追加；68 不误合并不同原因，旧计数保持1。两项部分满足、一项满足，不能写三例全过。原始记录及逐项局限见 evals/runs/20260923-light-output-dedup/executor-original.md 和 light-review.json。这些细节是本次单样本观察，现有正文已要求，不再追加规则或增加复发次数。
