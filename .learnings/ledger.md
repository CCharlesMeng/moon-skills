# 复盘台账（session-optimize）

按 Pattern-Key 去重，按 Recurrence-Count 计数。格式见 session-optimize/references/learnings-ledger.md。

本文件独立于同目录下其他工具的 LEARNINGS.md / ERRORS.md 等文件，清理那些文件时不要连带删除本文件。

---

## [RETRO-20260816-001] knowledge.doc-stale

**类别**: 知识缺口（L1）
**严重程度**: 中
**Status**: pending
**Pattern-Key**: knowledge.doc-stale
**Recurrence-Count**: 2
**First-Seen**: 2026-08-16
**Last-Seen**: 2026-08-17

### 问题
目标仓库执行的 vendored skill 停留在旧提交，源仓已经存在的证据复用和收口提速规则没有进入实际执行副本，后续窄改继续支付旧流程成本。

### 证据
- 会话 `019fffb0-b257-7aa2-93b3-9664f2c31420` 的目标副本 `SKILL.md` 哈希与 `58f9b1b` 完全相同，最后一次同步提交为 2026-08-13
- 源仓 `d9c10a2` 已于 2026-08-14 增加共享证据、精确失效和最终全量门上限；目标副本未包含这些规则
- 源仓 `3f8045e` 于 2026-08-16 12:32 增加 Phase B 事实提升、结构化聚合和执行 telemetry；目标副本同样未包含
- 会话 `01a00dd2-3eea-7e71-b43c-595189641ad7` 再次由同一目标副本执行；Story 目录未生成 preflight、telemetry、review evidence、review results 或 validation plan/receipts/status，证明 8 月 14 日之后的优化没有进入运行入口
- DataDashboard 中该 vendored skill 的最后同步提交仍是 2026-08-13 的 `4c6e3b9`；源仓当前还存在尚未提交的 validation batching 改造

### 处置
先显式记录 vendored 副本的来源提交与固定/跟随策略，再以只读 freshness 检查提示版本差异；确认跟随策略后同步并用现有 eval 验证。

### Metadata
- 去向: DataDashboard 的 skill 分发/同步约定（待批准）
- 相关文件: skills/sdd-dev-frontend/；DataDashboard/.agents/skills/sdd-dev-frontend/
- See Also: —

## [RETRO-20260816-002] decision.constraint-drop

**类别**: 流程/决策（L2）
**严重程度**: 中
**Status**: pending
**Pattern-Key**: decision.constraint-drop
**Recurrence-Count**: 2
**First-Seen**: 2026-08-16
**Last-Seen**: 2026-08-17

### 问题
QA 基线已经冻结壳层 token 与统一运行时 token 分域，但首次 GREEN 没有覆盖该不变量，直到规范检视才发现绕过 token 的实现并触发修复与重证据。

### 证据
- Story `dev-baseline.md` 的 R3-2 / F2-2 已要求背景、分隔线消费壳层 token，并保持统一运行时 `--mc-*` 分域
- 正式实施轮先得到 26 条 GREEN；随后规范检视才指出深色边界和文字绕过 token
- 修复后新增 token 分域与 composer 行为回归，再重跑受影响证据和检视
- 会话 `01a00dd2-3eea-7e71-b43c-595189641ad7` 的冻结需求已要求封闭 `money/CNY` 与可执行还原规则，但 grouped query 的类型不变量到规范/质量检视才补入两个范围外文件
- 同一会话的还原契约经历 8 条复合规则 → 18 条原子规则 → 因采集限制缩为 16 条 → 检视后扩为 22 条，说明约束到原子断言和采集能力的映射没有在首次 GREEN 前闭合

### 处置
对明确写成“必须经 token / 不得硬编码”的冻结约束，在首次 GREEN 前建立“约束 → 目标范围 → 定向断言或显式豁免”映射；不把所有色值扩成全局禁令。

本次先把 ADR 冲突扫描和高风险 AC 的“原子断言 + 边界值 + 可采集性”作为可逆试验；18→16 的采集器缺陷另见 `RETRO-20260817-003`，不把它归咎于冻结流程。

### Metadata
- 去向: sdd-dev-frontend 维护者（建议在本仓用 refine-skill 处理）
- 相关文件: skills/sdd-dev-frontend/agents/recon-spec.md；skills/sdd-dev-frontend/references/restore-contract.md；skills/sdd-dev-frontend/evals/evals.json
- See Also: RETRO-20260817-003

## [RETRO-20260816-003] decision.scope-creep

**类别**: 流程/决策（L2）
**严重程度**: 中
**Status**: experiment
**Pattern-Key**: decision.scope-creep
**Recurrence-Count**: 1
**First-Seen**: 2026-08-16
**Last-Seen**: 2026-08-16

### 问题
颜色续改后的质量检视在无法区分 Story 前用户改动与本 Story 增量时，直接把会话保存/回放竞态纳入视觉 Story 并修改范围外行为。

### 证据
- `tasks.md` 将 AI 编排、接口、会话和页面元数据逻辑列为范围外，并要求保留既有未提交功能改动
- 初次质量检视明确记录 `PageAuthoringWorkbench.svelte` 在 Story 前已有用户改动，且没有独立逐行起点快照
- 用户仅要求浅色 composer 的轮次随后修改 generation/save guard 和对应测试；现有证据不能证明竞态由本 Story 引入或扩大

### 处置
仅对计划修改且起点 dirty 的文件，在第一次写入前保存内容哈希和窄范围 patch；review 默认审 Story-start snapshot 到当前的差异。既存问题单列，只有 Story 引入/扩大、阻塞交付或用户明确授权时才在本 Story 修。

### Metadata
- 去向: sdd-dev-frontend 维护者（建议在本仓用 refine-skill 处理）
- 相关文件: skills/sdd-dev-frontend/references/phase-entry.md；skills/sdd-dev-frontend/agents/review-quality.md；skills/sdd-dev-frontend/agents/review-convention.md
- See Also: —

## [RETRO-20260816-004] decision.silent-assumption

**类别**: 流程/决策（L2）
**严重程度**: 中
**Status**: experiment
**Pattern-Key**: decision.silent-assumption
**Recurrence-Count**: 1
**First-Seen**: 2026-08-16
**Last-Seen**: 2026-08-16

### 问题
流程在没有证实子代理能取得应用内浏览器的情况下继续派发浏览器检视，已确认角色级 IAB 不可用后仍产生重复连接与检视空转。

### 证据
- 已完成的 prototype、正式实施、浅色 composer 三轮共有 186 次浏览器调用，其中 41 次失败；当前轮计入后为 199 次、45 次失败，但这些失败不一定同因
- `dev-review.md` 最终记录 layout 与 self-test 均因 `Browser is not available: iab` 未执行
- 主 agent 已采集可用页面事实，但旧流程没有 Phase B 原始事实提升与结构化共享契约

### 处置
每个角色/运行时组合只做一次能力探测；子代理无 IAB 时立即使用带依赖哈希的主 agent 原始事实，必须独立交互且未覆盖的维度准确标 Deferred，不再同路径重试。角色级 IAB 缺口另行移交平台负责人。

### Metadata
- 去向: sdd-dev-frontend 维护者；角色级 IAB 能力另移交 Codex 平台负责人
- 相关文件: skills/sdd-dev-frontend/references/review-evidence.md；skills/sdd-dev-frontend/references/phase-review-closeout.md
- See Also: —

## [RETRO-20260817-001] decision.unverified-claim

**类别**: 流程/决策（L2）
**严重程度**: 高
**Status**: pending
**Pattern-Key**: decision.unverified-claim
**Recurrence-Count**: 1
**First-Seen**: 2026-08-17
**Last-Seen**: 2026-08-17

### 问题
独立功能自测试未执行，加载中的 skill 明确要求用户批准并把受影响 AC 标 Deferred 才能收口，但最终仍宣告全部完成。

### 证据
- `dev-review.md` 明记独立 `self-test` 因浏览器列表为空未执行，功能结论由主线程补采
- 实际加载的 8 月 13 日 `SKILL.md` 已写明：功能自测试未执行时不能收口，除非 Phase D 用户明确同意且受影响 AC 全部标 Deferred
- 会话没有该批准，报告写 Deferred AC 为 0，最终答复仍称 `sdd-dev-frontend 完成`

### 处置
让机器收口检查读取四角色状态、用户批准记录与 Deferred AC；缺独立 self-test 且缺批准/Deferred 时以非零退出阻断完成声明，主线程补采不得替代独立角色。

### Metadata
- 去向: sdd-dev-frontend 维护者（待批准）
- 相关文件: skills/sdd-dev-frontend/scripts/manage_review_pipeline.py；skills/sdd-dev-frontend/references/phase-review-closeout.md
- See Also: RETRO-20260816-004

## [RETRO-20260817-002] decision.wrong-default

**类别**: 流程/决策（L2）
**严重程度**: 高
**Status**: pending
**Pattern-Key**: decision.wrong-default
**Recurrence-Count**: 1
**First-Seen**: 2026-08-17
**Last-Seen**: 2026-08-17

### 问题
浏览器验收默认复用一个只通过健康探针的长期开发进程，没有核对它是否来自当前 checkout，导致旧页面触发重复刷新、换端口复验，并让用户在完成后继续看到旧结果。

### 证据
- `dev-baseline.md` 把既有 PID 34810、端口 5173 固化为 browser driver，只记录 URL 与 curl 健康探针
- 实施轮确认 5173 提供旧模块后另启 5174；后续用户现场仍在 5173 看不到语义数字
- 新实例 5187 对同一路由显示 10 行共 20 个 `<data>`，而旧 5173 为 0；旧进程后来确认于 8 月 13 日启动且未重启

### 处置
复用服务前校验 pid、cwd、启动时间与代码指纹；不匹配就从当前 checkout 启隔离端口。把唯一 base URL 与 runtime identity 写进 validation runtime key，并要求 B/C/D 每次使用前核对。

### Metadata
- 去向: sdd-dev-frontend 维护者（待批准）
- 相关文件: skills/sdd-dev-frontend/SKILL.md；skills/sdd-dev-frontend/references/phase-entry.md；skills/sdd-dev-frontend/references/validation-batches.md
- See Also: —

## [RETRO-20260817-003] project.contract-collector-mismatch

**类别**: 项目实现（L4）
**严重程度**: 中
**Status**: pending
**Pattern-Key**: project.contract-collector-mismatch
**Recurrence-Count**: 1
**First-Seen**: 2026-08-17
**Last-Seen**: 2026-08-17

### 问题
还原契约允许 `expected: 0` 且采集器声明支持 `kind: count`，但 CSS 零匹配在进入 count 采集前就被当成定位错误，无法表达“禁止出现某元素”的机器断言。

### 证据
- 本次实现因 `no implementation locator matched` 删除了两条“期望 0”子规则，之后以其他结构证据补覆盖
- `references/restore-contract.md` 明确 0 是合法期望值，`collect_restore_facts.js` 的 `count` 分支也会返回节点数
- 当前采集器在节点数为 0 时先返回 error，现有 eval 没有覆盖零匹配 count

### 处置
仅对 `collect.kind=count` 且稳定父级 scope / 页面 runtime 已验证的零匹配返回 `actual: 0/status: ok`；保留 locator diagnostics，其他采集保持定位错误。补合法零节点、非零节点、拼错 selector、错误页面/scope 与非 count 零匹配的回归用例，防止负向断言再次被迫删除或误判 GREEN。

### Metadata
- 去向: moon-skills 项目实现（待批准）
- 相关文件: skills/sdd-dev-frontend/scripts/collect_restore_facts.js；skills/sdd-dev-frontend/evals/test_collect_restore_facts.mjs；skills/sdd-dev-frontend/evals/test_verify_restore_contract.py
- See Also: —
