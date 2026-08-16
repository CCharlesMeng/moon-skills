# Phase A1 / A2 细则 — 规格抽取与并行勘察

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分，进入 Phase A1（或直接进入 A2）时完整读取。硬门禁、输出规范 P1–P8、路径变量与 subagent 派发约定以 SKILL.md 为准，本文件不重复。

---

### 代码侧勘察模式：Impact S `lite` / 其余 `full`

在第一次需要代码侧工程依据时只判一次模式。`lite` 是对**已经由 REPO-3 定义的范式做机械选读**，不是让主 agent 自行探索代码或创造结论。只有以下九项全部成立才可用：

1. 影响面分级是 `S`；
2. 基线源是 `原型` 或 `文字规格`，不是需要收集候选路由与结构化实测值的 `参照页`；
3. Phase -1 的 REPO-3 validation 有效，Section 表中的指纹仍是当前版本；
4. `tasks.md` 文件清单完整，没有 `TBD` / `TODO` / `未定义`，全部 Story 工程需要能从 Task 与 AC 逐条列出；
5. 不新增 / 修改公共组件、公共样式、路由、schema、codegen、共享状态或其他工程边界；
6. Requirement 工程决策不存在冲突、多个候选或待用户决定项；
7. 每条 Story 工程需要都能通过显式 ID，或一次 `show --tag` 的**唯一结果**，映射到恰好一个现有 `PATTERN-*`；
8. 每个被选 PATTERN 至少一个声明证据定位仍存在，并能机械核对入口、约束与验证方式；
9. 不需要新增 / 改写 PATTERN，也不需要补 Requirement 工程决策。

`lite` 走法：

1. 主 agent 从 tasks / AC 列出 Story 工程需要；
2. 只运行 `manage_repo_baseline.py show --pattern-id <ID>`，或先 `show --tag <tag>` 验证唯一再按 ID 读取；不整段读取 REPO-3，不展开相邻源码；
3. 按 PATTERN 声明逐个检查至少一个证据路径 / locator 仍成立；
4. 把与完整勘察相同结构的“Story 需要 → `REQ-DEC-*` / `PATTERN-*`”和完整 REPO-3 指纹并入 `dev-baseline.md / 工程依据`，标记 `勘察模式：lite`；不复制正文、不创建独立文件；
5. telemetry 的 `phase-a1.recon-codebase` 记 `result: run`、`note: lite` 以及选中 / 核验证据数量。

任一条件不满足、查询为 0 / 多结果、locator 失效或执行中出现不确定性，立即改走 `full`：派 `agents/recon-codebase.md`，telemetry 写明回退原因。这个回退是正常路由，不是阻断，也不允许通过猜一个 PATTERN 强保 `lite`。`full` 回传与现有检验、重试、卡死规则完全不变。

### Phase A1 — 规格抽取

把设计稿的取值一次性搬进 `<design-spec-dir>`，之后全流程只读产物、不读原型（硬门禁 9）。**无决策时不单独占一轮（P6）。**

#### 1. 抽取顺序

| # | 动作 | 谁做 |
| --- | --- | --- |
| 1 | 跑 `python3 "<skill-dir>/scripts/extract_design_spec.py" extract <html> --out-dir "<design-spec-dir>"`，产出 `design-facts.json`、`design-tokens.md`、`interface-inventory.md`、`content-inventory.md`，并算出每个区块的内容哈希。**退出码 4 表示有抽取覆盖缺口**：按硬门禁 14 把每类缺口记进「已知缺口」与执行起点，再带 `--acknowledge-coverage-gaps` 重跑 | 主 agent |
| 2 | 以 `design-facts.json` 的 `prototype_fingerprint` 校验 DOM/CSS + 资源内容/缺失状态；再把脚本切片哈希与 `block-index.md`、本 Story 相关区块规格头的内容哈希逐个比对 | 主 agent |
| 3 | 原型指纹一致、切分表存在、且本 Story 相关区块规格全部命中 → 直接复用，A1 到此结束，零子代理 | 主 agent |
| 4 | 未命中或目录为空 → 按候选段数取切分方式：≤ 3 走第 5 节小稿直通道；4–10 走第 6 节中稿自切；> 10 派 `extract-prototype` 划页面 → 区块、审组件命名 | 主 agent，或子代理 ×1 |
| 5 | 对切分表里**哈希失配与新增的区块**逐个执行脚本 `block --anchor <锚点> --out <临时路径>`，物化单区块切片；切片不是正式工件，不写入 `<design-spec-dir>` | 主 agent |
| 6 | 把每份临时切片作为 `区块切片路径` 派给 `extract-block-spec`，一区块一实例，同一轮并行 | 子代理 ×N |

**首轮处理代码侧勘察。** 它不依赖设计稿：只要 A1 未整段跳过——全量管线、中稿自切、小稿直通道、全量复用都算——就在 A1 第一轮先按上节判模式；`lite` 由主 agent 机械取证，`full` 才派 `recon-codebase`，回传暂存。A2 只补派 `recon-spec`，确认门仍只等一处。基线源不是 `原型` 时 A1 整段跳过，代码侧在 A2 先完成再派 `recon-spec`。

#### 2. 分支与跳过

| 情形 | 走法 |
| --- | --- |
| 基线源不是 `原型`（第 2 / 3 档） | **整个 A1 跳过**：没有设计稿就没有可抽的取值，还原侧期望值按 [基线源](../SKILL.md#基线源没有-html-原型时) 取自参照页或文字规格 |
| 小设计稿：脚本候选段 ≤ 3 | 走第 5 节小稿直通道，全程零子代理 |
| 中稿：候选段 4–10 | 走第 6 节中稿自切，免 `extract-prototype` 一轮派发；`extract-block-spec` ×N 照常并行 |
| `<design-spec-dir>/design-facts.json` 原型指纹一致，且本 Story 相关区块在切分表与区块规格里全部哈希一致 | 全量复用，不派子代理 |
| 部分区块哈希失配 | **只重抽失配的那几个**，其余复用；全局的 `design-tokens.md`、`interface-inventory.md`、`content-inventory.md` 按 [工件管理](../SKILL.md#工件管理) 的并发写规则处理 |
| 本 Story 的 `tasks.md` 涉及切分表之外的新区块 | 只对新区块派 `extract-block-spec`，增量填进同一目录 |

**整稿时效用原型指纹，区块增量用内容哈希，都不用文件 mtime。** 原型指纹覆盖归一化 DOM/CSS、资源内容与缺失状态；只重排 HTML 空白不失效。指纹变化后仍只重抽哈希失配与新增的区块。

**A1 必须跑完才能派 `recon-spec`**（理由见 [CONTEXT.md](../CONTEXT.md#分段依据a1-必须跑完才能派-recon-spec)）。代码侧不依赖设计稿，所以 A1 内先完成 `lite` 或提前派 `full`，让 A2 确认门只等一处。

#### 3. 回传校验

按各提示词「输出格式」节的自检清单逐项核对回传。不合格退回重跑一次，仍不合格按 P7 上报。主 agent 额外只查一条跨份一致性：**切分表覆盖本 Story `tasks.md` 涉及的全部页面**，未覆盖的写了理由。

**`未见` 是合法结论，不是缺陷。** 静态设计稿里确实没有 hover / focus / disabled / loading 与空态，回传里出现具体取值反而是发明规格。这些维度由主 agent 记入 A2 的「已知缺口」，与第 1 节的抽取覆盖缺口合并成一份。

#### 4. 落盘

| 文件 | 动作 |
| --- | --- |
| `<design-spec-dir>/design-tokens.md` | 脚本输出，主 agent 写入；已存在时按 [工件管理](../SKILL.md#工件管理) 的并发写规则处理 |
| `<design-spec-dir>/interface-inventory.md` | 同上，再并入 `extract-prototype` 的命名修订 |
| `<design-spec-dir>/content-inventory.md` | 脚本输出，主 agent 写入；已存在时按 [工件管理](../SKILL.md#工件管理) 的并发写规则处理 |
| `<design-spec-dir>/design-facts.json` | 脚本确定性输出；包含原型指纹、资源内容/缺失哈希、区块、结构、静态文案、token 与布局声明 |
| `<design-spec-dir>/block-index.md` | `extract-prototype` 回传的切分表，含每个区块的锚点与内容哈希 |
| `<design-spec-dir>/blocks/<区块名>.md` | 每个 `extract-block-spec` 实例回传的区块规格，一区块一文件 |

临时区块切片只用于一次 `extract-block-spec` 派发，规格落盘后不进入工件清单；后续需要时按 `block-index.md` 的锚点重新生成，避免缓存两份可能漂移的设计稿事实。

本节结束时分别追加 `phase-a1.extract`、`phase-a1.block-specs` 与 `phase-a1.recon-codebase` telemetry：哈希命中写 `reuse`，没有对应动作写 `skip`，实际执行写 `run`；代码侧 note 固定写 `lite` / `full` / `fallback-to-full: <原因>`。

#### 5. 小稿直通道

同时满足两条时，A1 不派任何子代理：

1. `interface-inventory.md` 的候选段 ≤ 3；
2. 对每个候选段跑一次 `block --anchor`，切片头显示的字符数都 ≤ 12,000。

走法：主 agent 以候选段为最终区块，从各切片头**逐字抄录**锚点、行号坐标、内容哈希与节点数生成 `block-index.md`，头表加一行 `切分来源：直通道（脚本切分）`；区块名按「一屏可截 + 一个名词短语说得清」从候选段的文案摘要命名。**切片正文自始至终不读**——硬门禁 9 在直通道下同样成立，主 agent 只取切片头。

区块规格不生成：`recon-spec` 见到 `切分来源：直通道` 时，还原侧期望值直接取 `design-facts.json` 中对应区块锚点下的结构、文案、token 与布局事实（其 §一有对应豁免行）。Interface Inventory 保持脚本原文、名称未审订，引用时沿用 `IC-nn`。

任一条件不满足，或直通道生成的切分表覆盖不了本 Story `tasks.md` 涉及的全部页面，回第 1 节走正常管线。

#### 6. 中稿自切

候选段 4–10 时归并判断空间不大，主 agent 亲自切分以免一轮派发等待：

- **完整读取 [extract-prototype.md](../agents/extract-prototype.md) 第三节**，按同一套规则执行：候选段归并、`block --anchor` 锚点验证、候选段覆盖对账，一条不减。
- 产出同格式 `block-index.md`，头表加一行 `切分来源：主 agent 归并`；Interface Inventory 保持脚本原文、名称未审订（`extract-block-spec` 对未审订名称有既定兜底：沿用 `IC-nn`）。
- **切片正文仍不读**（硬门禁 9），归并依据只有脚本产物与切片头。
- 后续照常：物化失配 / 新增区块的切片，`extract-block-spec` 一区块一实例同轮并行。
- 按规则归不出「一屏可截 + 一个名词短语说得清」的区块、或候选段归宿有争议时，**不硬切**——退回派 `extract-prototype`，不降低切分质量换速度。

---

### Phase A2 — 并行勘察

#### 1. 派发

基线源为 `原型` 时代码侧 `lite` / `full` 已在 A1 处理，本阶段只补派 `recon-spec`；A1 整段跳过（基线源为参照页 / 文字规格）时，先按本文件开头选模式：参照页固定 `full`，文字规格满足九项才可 `lite`。代码侧完成后再派 `recon-spec`：

| 子代理 | prompt |
| --- | --- |
| 规格侧勘察 | `agents/recon-spec.md` + 路径变量取值表 |
| 代码侧完整勘察 | `agents/recon-codebase.md` + 路径变量取值表，仅 `full` 模式 |

取值表里追加一行 `基线源`，取值为 `原型` / `参照页` / `文字规格`（按 [基线源](../SKILL.md#基线源没有-html-原型时) 判）。**基线源不是 `原型` 时两侧串行**：先完成代码侧（`lite` 机械选读或 `full` 子代理）；参照页把候选事实和选定路由追加进 `recon-spec` 取值表，文字规格把选定的 token PATTERN ID 追加进去，再派 `recon-spec`。不得为了并行让规格侧在基线来源未定时先猜期望值。

#### 2. 回传校验

`recon-spec` 与 `full` 代码勘察按各自提示词「输出格式」节的自检清单逐项核对（规格侧的完整判据在 [qa-baseline-template.md](./qa-baseline-template.md) 的交付前自检）。`lite` 则对照本文件九项与五步走法；任一项验不实就回退 `full`，不能把它当作“不合格重跑”。子代理回传不合格退回重跑一次，仍不合格按 P7 上报。

主 agent 额外只查三条跨份一致性，因为子代理各自看不到对方的产物：

- **两表对齐**：QA 基线引用的区块名都能在 `block-index.md` 里找到。
- **契约规则一一映射**：每条 R1–R6 期望值都有同 `baseline_id` 的规则，无多余规则。
- **R1 期望值不含原型类名**：对照 `block-index.md` 锚点与 `interface-inventory.md` 的类名，R1 规则的 expected 出现任何设计稿侧 class 名即退回 `recon-spec` 重写（计入「不合格退回重跑一次」）——类名是设计稿侧工件，写进期望值就是修不掉的 RED。

回传是 `前置缺失：<清单>` 时**不重跑**，直接按 P7 交给用户。

#### 3. 落盘

| 文件 | 动作 |
| --- | --- |
| `<story-dir>/dev-baseline.md` | 在“执行起点（环境）”之后追加「工程依据」「功能理解」「QA 基线」「已知缺口」；工程依据标明 `勘察模式：lite / full`，只保存 Story 需要、采用的 `PATTERN-*` / `REQ-DEC-*`，不复制正文。**同时补写顶部「给人的摘要」**（模板见 story-artifact-templates 第一节：人话说清做什么、标准哪来、确认对象的数量），**并把 REPO-1～3、原型指纹等全部哈希收进文末「指纹附录」**——正文行只写「见指纹附录」 |
| 还原契约规则草稿 | `recon-spec` 回传的 JSON 工件；主 agent 暂存到临时目录，确认门前不编译正式契约、不写进 Story |

**原型切分表不再落进 `dev-baseline.md`。** 它是 Requirement 级事实，跟着设计稿走而不是跟着 Story 走，落在 `<design-spec-dir>/block-index.md`（见 [工件管理](../SKILL.md#工件管理)）；`dev-baseline.md` 只引用区块名。

`recon-spec` 每次派发 / 重试追加 `phase-a2.recon-spec`；两侧合并、跨份一致性校验与确认门前的一次性落盘追加 `phase-a2.merge-validate`。不得把子代理等待、主 agent 合并与用户确认揉成一条时长。

#### 4. 已知缺口的两条通道

「已知缺口」按**有没有安全默认值**分两条通道，不再一律先行提问：

| 通道 | 判据 | 走法 |
| --- | --- | --- |
| 工作假设 | 存在一个不需要用户输入就能安全采用的默认处理（典型：R4 / R5 写 `未见` 且 AC 未要求该状态 → 默认不做；上游未定义响应式 → 只承诺「不破」） | **随确认门同轮**：逐条列入「先看这几条」的工作假设小节，写明「缺口 → 采用的默认 → 事后要改走硬门禁 8」；用户确认基线即同时确认假设 |
| 必须先答 | 答案会改变基线内容或验收结果，且没有安全默认值（典型：对接模式未声明、AC 要求状态反馈而设计稿 `未见`、参照页有多个候选） | 先单独走一轮 P7 提问，答完再进确认门（P1） |

**进入 P7 前先做证据来源判定**：该问题在 repo 与 prototype 两侧是否已有直接证据；**只有 `user-only` 或 `conflict` 才能进 P7**，能从 repo 或 prototype 直接读出的不得提问，必须把证据写入基线。分类判据见 [qa-baseline-template.md](./qa-baseline-template.md)。

#### 5. 展示与确认门

用户可见内容：

- **「先看这几条」**：从下面六类里挑出实际存在的，逐条列在 QA 基线全文之前。平铺 N 条期望值让人扫一眼，等于把确认门变成橡皮章；用户的注意力要先落在最可能被误批的地方。**每条用人话写**：现象与后果说清楚，不以编号或维度代号开头，代号放句尾括号——用户确认的是内容，不是代号
  - **工作假设**（第 4 节第一条通道的产物）：逐条写「缺口 → 采用的默认 → 事后要改走硬门禁 8」
  - 期望值来自 `未见` 或抽取覆盖缺口的（这些维度实际没有基线）
  - 命中豁免 `EX-n` 的（这些偏差被允许了）
  - 基线源降级到参照页或文字规格的
  - `<browser-driver>` 缺失、页面或截图不可用而注定 YELLOW 的规则
  - 与上游 AC 有出入或上游未定义的（典型是响应式与状态反馈）
- QA 基线全文：还原侧 R1-R6 与功能侧 F1-F4 的表格呈现，**「具体期望」列原样不摘要**（确认对象就是这些期望值）；「取证方式」列与指纹类字段是机器校验用的，**呈现时省略**，文件里保留
- 豁免表全文
- 原型切分表**只展示页面与区块名两级**，锚点、内容哈希与视觉职责不展开
- 基线源不是 `原型` 时，**参照页候选表与选定的那一个**（用户确认的不只是期望值，还有拿什么当基线）
- 有降级项时，前置一行降级告知

`dev-baseline.md` 的“工程依据”不是新的确认对象；它只记录已经由 Requirement 决策或仓库 REPO-3 确立的引用。确认门仅说明采用了多少条工程依据，不展开范式正文。

```
---
**[Phase A 确认门]** 完成标准已备好，确认后冻结。三件事：

1. **会检查什么**：<一两句业务语言，点名对照标准与检查对象，数量放句尾括号>
2. **不会检查什么**：<设计稿没覆盖的部分怎么处理，一两句>
3. **替你先做的决定，要你点头**：<豁免与工作假设逐条一句人话——本来 vs 实际 vs 为什么；没有写「无」>

基线源 <原型 / 参照页 <路由> / 文字规格>。细节在 dev-baseline.md（表格里的机器列不用读）。确认即同时冻结标准与假设，开工中放宽任何一条都需重新确认。
→ 请确认继续 / 或指出需要修改的地方。
---
```

门里的三件事与「给人的摘要」内容同源，但**口吻不同、各归其位**：确认门是会话文本，用第二人称、可以催促（「要你点头」「现在提出来」）；用户确认后落盘的「给人的摘要」改用文档口吻陈述（「已确认的偏差与假设」），**不把会话语句抄进文件**——文件冻结后会被长期阅读，「现在提出来」在那时是失效的对话残片。两处共同的写法判据（见 story-artifact-templates 第一节摘要槽位说明）：**禁止用行数统计代替内容，禁止以编号或内部词开头**，编号只作句尾括号。

#### 6. 冻结

用户确认后：

1. 一次性完成 `dev-baseline.md` 基线头：把「冻结状态」改为 `已冻结 ✅`、填确认时间，并把「还原契约」从 `待编译` 改为固定路径 `<story-dir>/restore-contract.json`。此后再编译；不要把 `contract_sha256` 回填进基线造成自循环。
2. 用同一份规则草稿执行：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" contract \
  --baseline "<story-dir>/dev-baseline.md" \
  --baseline-ref "dev-baseline.md" \
  --rules "<临时规则草稿.json>" \
  --out "<story-dir>/restore-contract.json"
```

3. 根据 `tasks.md` 文件清单、Requirement 工程决策和 `dev-baseline.md` 的工程依据写 `<story-dir>/restore-adapter.json`。每条规则的实现定位是有序 `locators`：`role/name` → 精确文案 → 稳定 `data-testid` → CSS；能用前者就不降到后者，禁止构建生成随机 class。源码静态扫描范围写进 `source_files`。
4. 执行 `verify_restore_contract.py validate` 校验契约、基线哈希和 adapter。任一失败都停在 A2 修正，**未确认或未通过校验不进入 Phase B。**

用户指出要改的地方 → 改完重新走同一个确认门，不跳过、不进 Phase B。

发出确认门前开始 `human.qa-confirmation`，收到用户回答后结束；`kind` 固定为 `human_wait`。确认后主 agent 冻结、编译与 validate 的时间另记在 `phase-a2.merge-validate` 新 attempt，不算进人的等待。
