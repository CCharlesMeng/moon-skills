---
status: accepted
---

# 设计稿解读外包给 subagent，还原实现仍由主 agent 亲自做

看起来与 [ADR-0002](0002-implementation-stays-with-main-agent.md) 冲突，实际是补足：ADR-0002 给的判据是「天然只读、视角独立、可并行、产出结构化报告」，设计稿解读四条全中——不改原型、视角独立于实现、可按区块并行、产出的就是结构化规格；而它从实现里剥出去的不是实现，是实现的**输入准备**。直接触发原因是 [`agents/recon-spec.md`](../../../../skills/sdd-dev-frontend/agents/recon-spec.md) L84：它要求「行号范围必须实读原型文件核对，不得估算」，同时还要写 QA 基线十个维度；大稿子读文件会截断，它拿不到完整内容却被禁止估算，实际结果是静默违规或回传行号对不上的切分表。原设计的防通读机制（原型切分表 + 「只精读行号范围」）保护的是 Phase B 的还原轮，切分表自身的产出成本无人保护——**上下文在 Phase A 就爆了，不是 Phase B。** 剥出去之后：脚本做确定性抽取，两个 `extract-*` subagent 各只看自己那一段，压缩后的区块规格一区块一文件，主 agent 每个还原轮只读当前那一份。

适用边界要说清楚，不是万能收益。标准版规模的稿子（[`evals/设计稿原型-标准版.html`](../../../../skills/sdd-dev-frontend/evals/设计稿原型-标准版.html)，55,697 字符 ≈ 16K token）通读技术上可行，这一层省的是精度而非生死；导出件规模（[`evals/设计稿导出件.html`](../../../../skills/sdd-dev-frontend/evals/设计稿导出件.html)，269,198 字符）通读不可能。**价值随稿子体积增长。**

## Consequences

- 主 agent 在 Phase B 只消费结构化规格，不再直读原型——对应 SKILL.md 新增的硬门禁第 9 条。
- 抽取产物落 requirement 级，跟着设计稿的生命周期，可跨 Story 复用；Story 级增量填充，命中哈希的区块零开销。
- `recon-spec` 不再自产原型切分表，改为消费切分表与区块规格，因此必须排在抽取段之后，Phase A 分两段。
- ADR-0002 的结论「若 Task 量大到主 agent 撑不住就收窄作用域或拆 Story」**不受本决策影响**：本决策只降低单个还原轮的开销，不改变作用域。
- [ADR-0001](0001-restore-uses-diff-list-as-red-evidence.md) 的关键理由是「差异清单的基线在外部」，而主 agent 现在看的是 subagent 的报告而非原型本身。靠取值溯源补回：**区块规格里凡充当差异清单期望值的取值，必须逐字来自脚本的确定性产物，不得由 LLM 重新推导**——R1 层级取自结构树、R2 文案取自 `content-inventory.md`、R3 间距与 token 取自 `design-tokens.md` 与具名类布局值。`extract-block-spec` 行使判断的只剩区块边界与命名、以及 R4/R5/R6 的定性，而 R4/R5 在静态设计稿下本来就写「未见」。期望值这一侧仍是机械抽取的外部事实。
- **残余风险是遗漏而不是放宽。** Step ② 只校验「清单里列出的项能否在截图上指认」，抓不住压根没被列进清单的偏差，`extract-block-spec` 漏一个元素会静默传导到 GREEN。两道约束落在 `references/block-spec-template.md` 与 `agents/extract-block-spec.md`：区块规格要对脚本 `--block` 切片的节点做数量对账，不允许只挑一部分写；Step ② 的截图对照仍直接打在原型的真实渲染结果上，那一侧的外部性未受削弱。
- 占位符标注与 token / 布局值二分是**正确性特性而非压缩特性**（主 agent 直读原型会把 `XX客户名称` 当作 R2 期望文案冻结进基线），所以不设「小稿子跳过抽取段」的阈值，抽取段恒定执行。requirement 级缓存的收益在单 Story 需求下可以为零，抽取本身不可跳过。
