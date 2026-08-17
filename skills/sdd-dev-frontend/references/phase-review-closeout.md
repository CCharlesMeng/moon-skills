# Phase C / D 细则 — 独立检视与收口

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分，进入 Phase C 时完整读取。硬门禁、输出规范 P1–P8、subagent 派发约定与退出门禁以 SKILL.md 为准，本文件不重复。

---

### Phase C — 独立检视

四个角色各自穷尽自己的维度、独立产出分级结论，主 agent 机械聚合进 `<story-dir>/dev-review.md`。**独立的是判断，不是证据采集。** 进入本阶段先完整读取 [Phase C 共享证据契约](./review-evidence.md) 与 [结构化检视结果契约](./review-result-contract.md)；编号、分级与汇总口径以 [review-dimensions.md](./review-dimensions.md) 为准。

#### 1. 派发前自检

主 agent 自己做。前三项缺一不建候选证据；定向检查已经覆盖当前改动、候选代码不再变化后，才跑第四项：

| 项 | 判据 | 不满足时 |
| --- | --- | --- |
| 全部 Task 已 GREEN | `tasks.md` 的 6 步 checkbox 全部勾完，且 `validation-status.json / ready: true` | 回 Phase B，从第一个未完成或 status 未通过的 consumer 继续 |
| `alpha-tests.md` 无缺口 | 每条 AC 有证据链；还原轮记录含契约哈希、RED/GREEN 报告指纹与路径、摘要及适用的视觉缓存引用 | 回 Phase B 补记录 |
| `dev-baseline.md` 已冻结 | 基线头「冻结状态」为 `已冻结 ✅` | 回 Phase A 走确认门 |
| 候选全量质量门 | 按执行起点记录跑一遍全套质量命令，失败集合与 DEMAND-2 起点逐条相同或更好；把命令、退出码、耗时、失败集合与代码指纹写入 `review-evidence.json / quality_gate`，追加 telemetry，并按起点证据契约 `record --source phase-c` | 出现新失败回 Phase B，归属哪个 Task 就从哪个修起；修复期只跑定向检查，候选再次稳定后再进本行 |

全量门完成后，**先提升、再批量补采浏览器证据**：用 `manage_review_pipeline.py promote` 把 `<story-dir>/phase-b-review-evidence.json` 中 runtime 与逐文件依赖哈希仍匹配的原始场景提升到 `review-evidence.json`；再从冻结 R/F 行与两份浏览器检视范围取场景并集，把没有被提升 / 复用覆盖的缺口登记成 validation intents，重编 plan，并按 status 的 browser batches 执行。相同 fixture、页面、runtime 与 reset 边界只连接/打开一次，viewport、状态与步骤在批次内连续跑。质量命令会重载页面或清掉内存态时，这个顺序避免重复造临时页面。证据包只记原始事实，不先判通过/不通过；batch / intent / assertion、browser_calls、promote / run / reuse / stale 与子代理启动、补位、重试分别追加 telemetry。

最后按 [前置产物校验](../SKILL.md#前置产物校验) 核对四份检视各自的终止级前置，并把 `<review-evidence>` 的实际路径与 `evidence_epoch` 追加到四份取值表。

#### 2. `<base-ref>` 的追加

`review-convention` 与 `review-quality` 需要本 Story 的改动 diff，两者都实现了三级取法：给了 `<base-ref>` 就用它，没给自己从 git 状态推，都取不到才返回前置缺失。**能拿到就传**，只追加进这两份的取值表，另外两份不加。

| 情形 | 动作 |
| --- | --- |
| 本 Story 开工前记录过起点提交 | 追加，取值为该提交 |
| 能定位与基线分支的分叉点，且分支上只有本 Story 的提交 | 追加，取值为分叉点提交 |
| 分支上混有其他 Story 的提交，切不干净 | 不追加，让子代理走第 2 级自推 |
| 目标仓不是 git 仓，或 git 状态读不到 | 不追加 |

**不确定就不传。** 传错的 `<base-ref>` 比不传更糟：子代理会把它当权威取法，检视范围直接错到别的 Story 上，而回传表头的取法看起来完全正常。

#### 3. 检视力度与容量感知派发

**检视力度按 Story 特征取，映射冻结如下**，不由临场判断增删；规范检视与质量检视任何情况必跑（它们是静态检视，也是 [退出门禁](../SKILL.md#退出门禁) 三档表判「不能收口」的两份）：

| Story 特征 | 力度调整 |
| --- | --- |
| 纯逻辑：无还原轮且 diff 不含样式文件 | 布局与响应式检视**不派发**，记「不适用（无样式改动）」，照退出门禁第 10 条在检视基准表、收口结论与最终输出三处披露 |
| 影响面分级 S | 布局页面范围限波及页 + 一个对照页；功能 REG 限波及页面主路径与直接入口；四份仍逐维度判断，但按结构化契约只回 coverage 与实际发现 / OQ / Deferred；机器细节只引用 `review-evidence.json` |
| 其余 | 四份全量 |

四份角色不变：

| 子代理 | prompt |
| --- | --- |
| 布局与响应式检视 | `agents/review-layout.md` + 路径变量取值表（含 `<review-evidence>`） |
| 代码规范检视 | `agents/review-convention.md` + 取值表（含 `<base-ref>`，按第 2 节） |
| 质量检视 | `agents/review-quality.md` + 取值表（含 `<base-ref>`，按第 2 节） |
| 功能自测试 | `agents/self-test.md` + 路径变量取值表（含 `<review-evidence>`） |

**代码规范检视与质量检视不得合并成一个子代理**：前者以 REPO-3 范式作客观基准，后者靠通用工程判断，合并会让客观判断被主观判断稀释。

派发采用**容量感知的动态补位**，不把物理上不可能的墙钟同轮当失败，也不等整波都结束才用空槽：

1. 建立一个 `evidence_epoch`，冻结本轮代码指纹与证据包；
2. 把适用角色放入待派队列，立即填满当前全部可用槽位；有浏览器场景缺口的长任务优先启动，其余顺序冻结后不再临场调整；
3. **任一角色完成且 JSON 通过预校验，释放的槽位就立即进入补位流程**，不得等待同时在跑的其他角色完成。只有 3 个子代理槽位时，合法时序是先启动 3 份、其中任一完成就启动第 4 份；
4. 完成结果没有 `evidence_added` 时直接补位；有时主 agent 先归档其中被结论引用的 artifact，再运行 `manage_review_pipeline.py merge-additions`，把原始 scenario 并入共享包并将该角色临时 JSON 的证据 ID 改写为正式 `BE-n`，然后立刻补位。这个机械步骤不得等待其他判断；
5. 后启动角色继续引用同一纪元。已完成角色的**判断 JSON 不传给它**，避免结论污染；只允许它读取刚并入共享包的原始证据；
6. 某份检视发现证据缺口时，先收齐该角色全部缺口并在相同页面 / fixture / runtime / reset 边界内批量补跑；不得逐基线行启动浏览器。相同新鲜度键已存在的场景不得重跑；代码或 runtime 变化则结束当前纪元，不能把新旧结果拼接。

中间合并命令（没有 `evidence_added` 就跳过）：

```bash
python3 "<skill-dir>/scripts/manage_review_pipeline.py" merge-additions \
  --review-evidence "<review-evidence>" \
  --result "<临时目录>/<role>.json" \
  --output-result "<临时目录>/<role>.json"
```

同一纪元内的四份判断仍是一次 Phase C；“同一轮”指同一代码指纹与基线，不指同一墙钟批次。

#### 4. 前置缺失与「未执行」

子代理返回 `前置缺失：<清单>` 时**不重跑**，按来源分两条路：

| 来源 | 处理 |
| --- | --- |
| DEMAND-2 已记录、已按硬门禁 4 告知过用户的 Story 特有限制 | **不再走 P7 追问**，直接记「未执行」并写明原因，进第 7 节汇总 |
| 其余前置缺失（产物真的不在、基线没冻结、Task 没勾完） | 按 P7 把缺失清单交给用户 |

第一条的理由：那个降级用户已经知道了，再问一遍等于同一件事打断两次（P1）。哪份降级、哪份终止见 [环境降级](./degradation-and-recovery.md#二环境降级)。

**「未执行」必须一路显式带到收口**——`dev-review.md` 的检视基准表、Phase D 的收口结论、最终输出的第一行，三处都要出现。**不得静默跳过，不得因为少一份检视就宣告全部通过。**

#### 5. 回传校验

四份正文先分别保存为临时 JSON；每份完成时即做 schema、角色、覆盖维度、`evidence_epoch`、代码指纹与重复编号预校验，四份齐后再用 `manage_review_pipeline.py aggregate` 做跨份校验。不合格只退回对应角色重跑一次，仍不合格按 P7 上报。**不接受 Markdown 回传，也不允许主 agent 手工补齐缺失维度。**

两份浏览器检视还要核一条：JSON 的 `evidence_reused` 必须列出实际 `BE-n`，`evidence_added` 必须是完整原始 scenario。已存在且新鲜的场景被无理由重跑，回传不合格；补跑场景由聚合脚本按 [共享证据契约](./review-evidence.md) 分配 `BE-n` 并回 `review-evidence.json`。任何影响面档位都不得缺维度或缺发现证据。

**`待主 agent 核豁免` 是主 agent 的活，不是子代理的缺陷。** 收到这个标记，对着 `dev-baseline.md` 豁免表逐条定夺：命中 `EX-n` 的从报告里删掉并记一行「命中 `EX-n`，不报」；未命中的按 [review-dimensions.md](./review-dimensions.md) 规则 3 判阻断级。

#### 6. 截图归档

子代理唯一允许的写入是截图文件，写在临时目录，路径在回传表头给出。临时目录随时会被清掉，所以由主 agent 归档：

- 从四份 JSON 的 finding / OQ / Deferred `evidence_ids` 反查 `review-evidence.json` 与 `evidence_added`，把被结论引用到的截图逐个复制到 `<story-dir>/evidence/review/`，未被引用的不归档
- 文件名加检视前缀避免撞名：`layout-<结论编号>.png`、`self-test-<基线编号>.png`
- 复制完先把共享 scenario 或 `evidence_added.artifacts` 改写为归档路径，再运行聚合器；聚合器从证据 ID 生成 `dev-review.md` 的「截图 / 工件」列，**不保留临时路径**

复制不到（文件已不在）时，该条结论的截图列写 `截图丢失：<临时路径>`；丢的是**阻断级**结论的截图，退回重跑那一份检视——阻断级没有证据就没有让人复核的余地。

#### 7. 汇总落盘

四份 JSON 通过校验后运行：

```bash
python3 "<skill-dir>/scripts/manage_review_pipeline.py" aggregate \
  --result "<临时目录>/review-layout.json" \
  --result "<临时目录>/review-convention.json" \
  --result "<临时目录>/review-quality.json" \
  --result "<临时目录>/self-test.json" \
  --review-evidence "<review-evidence>" \
  --output-json "<story-dir>/review-results.json" \
  --output-markdown "<story-dir>/dev-review.md"
```

脚本先校验并确定性并入 `evidence_added` 的原始 scenario、把角色临时证据 ID 改写为主包内 `BE-n`，再按 [review-dimensions.md](./review-dimensions.md) 第五节机械去重取高、分开 Open Question / Deferred 候选，并从结构化项生成 Handoff。相同 `canonical_key` 的现象、定位或用户可见文本冲突时脚本拒绝猜测，主 agent 回到原始证据消歧后重跑聚合。生成的 `dev-review.md` 再由 Phase D 填收口与执行量账本；**不得手工复制四份长报告。模板边界见 [story-artifact-templates.md](./story-artifact-templates.md) 第二节。**

**「给人的摘要」节写在最顶部**（模板已含）：每条发现一句业务语言——现象、影响、建议动作，编号放句尾括号；机器细节表全部在摘要之后。再从建议级、Open Question 与 Deferred 候选生成结构化 `Handoff 清单`；Phase D 只从这张表生成 P8，不再靠回忆扫全文。

零发现时聚合器走 fast path：仍保留检视执行、覆盖矩阵、Handoff 与收口占位，但不生成四套空的逐维度表。Impact S 与 M / L 的发现都只展开实际发现；浏览器步骤、命令输出和逐规则报告不复制进 `dev-review.md`。

**建议级不等于可以不写。** 它的定义是「不阻断收口」，不是「不进报告」。

---

### Phase D — 收口

主 agent 自己做，不派发。目标只有一个：**把 `dev-review.md` 的阻断级清零，或者在清不掉时把决定权交回用户。建议级默认只交付，不触发改码。**

#### 1. 阻断级修复

动代码前先重审级别。每条发现依次对照：冻结 AC / QA 基线、核心流程是否可完成、键盘操作与可访问名等核心可访问性、展示或提交的数据是否正确。能给出具体复现，且任一项不成立的，按 [review-dimensions.md](./review-dimensions.md) 升为阻断级；仍为建议级的只进入 Handoff 清单，**即使容易修也不得在本 Story 收口时顺手修改**。

逐条修阻断级，顺序按阻断级表的编号。三条约束与 [Phase B 细则](./phase-implementation.md) 第 5 节同源：

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出 Phase C 的 diff 范围**（本 Story 改动过的文件） | 停下，进第 3 节上报 |
| 2 | 禁止用检查抑制手段绕过（同 [Phase B 细则](./phase-implementation.md) 第 5 节第 2 条） | 这本身就是 `C6` 的阻断级，绕过等于自造一条新的 |
| 3 | 同一个报错连续修 3 次不成就停止 | 停下，进第 3 节 |

**不得把改不动的阻断级降为建议级。** 级别只由 review-dimensions 第二节的四条规则决定。

#### 2. 修完重跑

一轮修完，回 Phase C 重跑受影响检视。**重跑哪几份不由修复者临场判断，按下面这张冻结映射表定**——代码已经变了，命中的那几份旧结论作废；无失效依据不得多跑，少跑禁止。

| 本轮修复改动的类型 | 必重跑 |
| --- | --- |
| 仅样式 / token / 类名 / 静态文案 | 代码规范检视 + 布局与响应式检视 |
| 仅逻辑 / 类型 / 请求 / 状态 | 代码规范检视 + 质量检视 + 功能自测试 |
| 新增文件、改公共组件或公共样式，或一轮内两类混合 | 四份全部 |

四条执行规则：

- 归类按本轮修复实际触碰的文件与 diff 内容判定；归类结果与依据（改了哪些文件）记入 `dev-review.md` 检视基准表，拿不准归哪类时按更重的一档走。
- **重跑集合必须覆盖本轮所修全部阻断级的来源检视**——修了它报的问题，就得让它复跑确认，映射表不豁免这一条。
- 未执行的那份仍不执行；被映射表跳过的检视，其旧结论继续有效并保留在 `dev-review.md`。
- **修复—重跑最多两轮。** 第二轮结束仍有阻断级未清零，进第 3 节，不开第三轮。

验证与证据更新另守四条：

- 每次修复先更新 validation intents 的 `depends_on` 并重编 plan，只执行 status `next_batches[]` 中覆盖所改范围的 command / browser 子批次；不在修复尚未稳定时跑全量门。
- 批次 intent 与 `BE-n` 都按 `depends_on`、fixture 与运行时键精确失效；未受影响的消费者和浏览器场景继续复用。公共组件 / 公共样式改动才扩大到实际引用它的下游 intent，不把整个 batch 一刀切作废。
- 阻断清零、定向检查与受影响检视都稳定后，若代码指纹不同于 Phase C 候选全量门，主 agent**只补一次**最终全量门，并按起点证据契约 `record --source phase-d`；指纹未变直接复用候选门，不重复写一份等价缓存记录。两种情况都进 telemetry，分别记 `run` / `reuse`。
- 最终全量门先于浏览器补证；它之后只重采 status 列出的 stale / failed / blocked / pending browser intents，并按兼容性合批，不重跑整个浏览器清单。检视角色读取最终门原始结果，不再各自跑一套 test / check / build。

#### 3. 待用户输入项按 P7 上报

**进入本节的条件不只是修不掉——存在任何待用户输入项就走本节，阻断级为 0 也不例外。** 五类攒在同一轮一次问完（P1）：阻断级修不掉、需越界改动、Open Question 待决、`Deferred` 待判、[还原 YELLOW 请求放行](../SKILL.md#还原-yellow-的放行通道)。每条写出：结论编号、为什么修不掉或放不下、要改哪个文件且它为什么在范围外、推测与理由。**Open Question 不允许静默落盘**（退出门禁第 11 条）：要么在这里问出答案，要么在会话中明确告知并在 `dev-review.md` 对应行记「用户已知悉」。

**上报之后停在 Phase D**：不出三行索引、不写收口结论、不勾任何东西。**不得自行降级为建议级，不得静默收口。**

#### 4. `Deferred` 判定

功能自测试回传的「Deferred 候选」只是候选，判不判由主 agent 定：

| 情形 | 判定 |
| --- | --- |
| 卡在外部依赖（接口未就绪、需后端造错误码、缺权限账号），本阶段解除不了 | 判 `Deferred`，在 `alpha-tests.md` 的 AC ↔ 证据映射状态列标注，写明原因与解除条件 |
| 本阶段跑得通，只是没跑 | 不判，跑完再说 |
| 拿不准是不是外部依赖 | 进第 3 节的 P7，交用户定 |

**带 `Deferred` 标记的 AC 不计为已验收**（硬门禁 5），不进覆盖率。**不得拿豁免 `EX-n` 顶替 `Deferred`**：豁免是「已经决定就这么做，且这么做是对的」，`Deferred` 是「想做但外部依赖没就绪」。

#### 5. 落账

| 文件 | 动作 |
| --- | --- |
| `<story-dir>/dev-review.md` | 阻断级表的「修复状态」逐条填「已修（复跑结论）」；写「收口结论」节 |
| `<story-dir>/alpha-tests.md` | 功能自测试实测结果贴回对应 `F<n>-<m>` 行；AC ↔ 证据映射填状态，`Deferred` 附原因与解除条件 |
| `<story-dir>/dev-baseline.md` | 收口期间动过基线的，变更记录已登记且已重新请用户确认（硬门禁 8） |
| `<story-dir>/validation-plan.json` / `validation-receipts.json` / `validation-status.json` | plan 对应最终代码依赖；收据逐 assertion 可追溯；status `ready: true`，无待重跑 intent |
| `<story-dir>/review-evidence.json` | 最终代码指纹、最终全量门与仍有效 / 已提升 / 已补采的 `BE-n` 齐全；不含检视判断 |
| `<story-dir>/review-results.json` | 四份结构化结果同一 evidence epoch / 代码指纹；聚合计数与 `dev-review.md`、Handoff 一致 |
| `<story-dir>/execution-telemetry.json` | 每次动作 / 重试已增量追加；QA 人工等待与 agent 主动时间分开；没有估算时长或 verbose log |
| `<story-dir>/evidence/review/` | 归档完成，`dev-review.md` 中无临时截图路径残留 |

**落账一次批量完成。** 上表各产物一次性写完，不逐文件反复读-写-再读；退出门禁核对（第 6 节）以本轮上下文里已有的检视回传、报告 JSON 与账本内容为准，**只重读本轮之后被修改过的工件**——重读未变化的大文件是纯粹的收口时延（实证：阻断级为 0 的收口曾耗 20 分钟，全在文书往返上）。

「收口结论」节固定三块：**四份检视的执行状态**（未执行的写原因）、**阻断级清零情况**、**未验收项清单**（`Deferred` 的 AC、因检视未执行而未覆盖的维度）。同时完成两张短表：

- `Handoff 清单`：建议级、Open Question、Deferred 判定逐条一行，包含用户可见文本与是否需用户决定；三类来源计数必须与正文一致。
- `执行量账本`：从 `execution-telemetry.json`、validation receipts / status 机械生成子步骤与 Phase 汇总；agent 主动时间和人工等待分开，全量门 run / reuse、command / browser 批次、intent 结果、browser calls / retries、场景 promote / run / reuse / stale、子代理启动 / 动态补位 / 重试都有计数。拿不到写「未记录」，不估算，不用 LOC 推断时间占比。

#### 6. 出门

逐条核对 [退出门禁](../SKILL.md#退出门禁)，全部满足才出 [最终输出](../SKILL.md#最终输出) 的三行索引；`Handoff 清单` 非空时必须继续输出 P8。输出前按建议级 / Open Question / Deferred 三类逐项计数，任一条没进会话都不出门。有一条不满足而又不属于第 3 节的上报情形，回第 1 节。

**收口被打断必须恢复。** 收口期间用户插入其他请求（验收、提问、临时任务），回应完成后必须回到本节继续核退出门禁，直到交付索引与应有的 Handoff 全部发出。**只有三行但清单非空同样不是完成**。
