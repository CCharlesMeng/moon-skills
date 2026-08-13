# Phase B 细则 — 实现

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分，进入 Phase B 时完整读取。硬门禁、输出规范 P1–P8 与路径变量以 SKILL.md 为准，本文件不重复。

---

### Phase B — 实现

主 agent 亲自做，不派发。逐 Task 推进，**常规不占用户一轮（P6）**，只有第 6 节的两类升级中断才打断。

#### 1. 开工前必读

进入 Phase B 时先读 `dev-baseline.md / 工程依据`，把其中引用的全部 `PATTERN-*` 正文**一次性预读完**（命令见下，逐 ID 执行），Requirement 的 `REQ-DEC-*` 回读 `requirement-frontend-design.md`。之后每个 Task 动手前只回看与当前 Task 命中的那几条，**不重复跑脚本**。

```bash
python3 "<init-skill-dir>/scripts/manage_repo_baseline.py" show \
  --baseline-dir "<repo-baseline-dir>" --pattern-id "<PATTERN-ID>"
```

这是细粒度复用的**第一道防线**，第二道在 Phase C 的代码规范检视。

#### 2. 轮次顺序

| 层级 | 顺序 |
| --- | --- |
| Task 之间 | 按 `tasks.md` 原顺序，不重排 |
| Task 内部 | **固定先还原轮、后逻辑轮** |

一个 Task 内允许多轮 6 步：一个区块走一轮还原，区块还原完再走逻辑轮。每轮独立编号并标注形态，如 `Task 3 · 轮 1（还原）`、`Task 3 · 轮 2（逻辑）`。上游已按 [sdd-task-frontend-split.md](./sdd-task-frontend-split.md) 把整页样式切成独立还原 Task 时，该 Task 只有还原轮、其余 Task 只有逻辑轮，Task 间顺序仍由 `tasks.md` 决定。

#### 3. 6 步与两种失败证据

**6 步的编号、顺序、RED/GREEN 语义完全不变。** 唯一扩展是 Step ① 的失败证据分两形态：

| Step | 逻辑轮 | 还原轮 |
| --- | --- | --- |
| ① RED | 写失败的单测或接口集成测试，给出完整代码 | 运行冻结契约，生成 `restore-report-red.json`；至少一项 RED |
| ② 验 RED | 跑测试，确认按预期失败 | 核对 RED 的外部出处与实现定位；YELLOW 先结构化补证，仍无法判定才截图 |
| ③ GREEN | 最小实现让测试转绿 | 只修报告里的 RED |
| ④ 验 GREEN | 测试转绿 + 作用域回归（判定见下方 ④）；**已知约束核销**（见下） | 重跑同一契约，生成 `restore-report-green.json`；无 RED、无 YELLOW；**已知约束核销**（见下） |
| ⑤ REFACTOR | 按需 | 按需；重构后再跑同一契约 |
| ⑥ 记录证据并提交 | 落 `alpha-tests.md` 的 L4 / L3 记录节 | 账本只记契约/报告/缓存指纹与路径、摘要及可选截图 |

还原轮必须以冻结外部契约为失败证据；机器报告负责可确定判定，截图只用于机器盲区的选择性补证。

**④ 已知约束核销（还原轮与逻辑轮共通）**

Step ④ 不只证明「主要实现完成」。主 agent 必须读 `tasks.md` 中本 Task 的文字描述与 `dev-baseline.md` 已冻结的 QA 基线，列出与本 Task **直接相关、但尚未被契约规则（`restore-contract.json` 的 R 编号）或单测覆盖**的已知约束（典型：四档响应式宽度、状态语义、边界值、类型断言、样式 token 去重）。每条写出：

| 必填 | 内容 |
| --- | --- |
| 约束 | 约束是什么 |
| 检查方式 | 对应契约规则 id / 单测 id / 当场执行的检查动作（布局类当场跑一次冻结视口） |
| 结果 | 通过；或未通过并留下失败证据 |

- **本 Task 确无未覆盖约束时，写一行「无未覆盖约束（已核对 `tasks.md` 本 Task 描述与 QA 基线相关行）」即可**，不建空表。
- **无法在本 Task 内验证的，必须显式写明「推迟到 Phase C 的哪一份检视核实」以及理由**；**禁止用批量 `N/A` 打包清零**。
- 这道检查**不替代**契约与检视，只防止「计划里已经写明的约束」被静默带到收口才第一次发现。
- 未核销完不得勾本轮 GREEN、不得进 Step ⑥。

#### 4. 还原轮 6 步的动作

固定检查层级如下。`required_layers` 由契约逐条声明；静态通过不能替代 render-required 规则的 GREEN。

| 层 | 能力 | 是否截图 |
| --- | --- | --- |
| 静态预检 | 必需文案 / i18n key、仓内 token、禁用字面量、状态选择器 | 否 |
| 结构化渲染 | 注入 `<skill-dir>/scripts/collect_restore_facts.js`，读取 DOM、`getComputedStyle`、`getBoundingClientRect`、滚动尺寸和实际状态结果 | 否 |
| 视觉补证 | 阴影观感、字体栅格、图片裁切、复杂叠层等机器盲区 | 是，仅 YELLOW 项 |

**默认容差、检查模式与 R1–R6 的层映射由契约逐条声明，判据在 [restore-contract.md](./restore-contract.md)。** 本层只有一条约束：**无法安全表达容差的规则标 YELLOW，不得自行扩大容差。**

**四步的命令、参数与 JSON 形态只有一份，在 [restore-contract.md](./restore-contract.md) 第四节**（编译校验 → 静态预检 → 结构化渲染 → 报告）。下面只写这四步之上的判定规则。

**① RED — 运行冻结契约**

- 按 restore-contract.md 第四节跑 validate → static → 结构化渲染 → `report --phase red`，输出 `<story-dir>/restore-report-red.json`。**基线哈希不一致立即停止**（硬门禁 10）。
- 页面不可用时如实写 `page_available: false`，**不得伪造实际值**。
- 差异清单只按 [diff-list-template.md](./diff-list-template.md) 摘要该报告，不另写一份判定。
- 至少一项 RED 才能进入 Step ③。首轮全部 GREEN，取消该还原轮并记录「冻结契约已满足」；首轮只有 YELLOW，先走 Step ②，发现偏差转 RED 才进入实现，无偏差则取消还原轮。

**② 验 RED — 核出处、定位与 YELLOW**

- 每条 RED 必须同时有期望值、实际值、`baseline_id` / `design_fact_source` 和实现 locator；缺一视为报告执行失败，不进 ③。
- **语义等价核对**：expected 与 actual 语义相同、仅序列化不同（颜色写法、分量顺序、简写属性、空白）的 RED，是比对器归一化没覆盖的新形态——**不进 ③、不改实现去迎合字符串、不得为它新增豁免**，按 P7 上报为工具等价缺口，定位方法见 [CONTEXT.md 的问题分流](../CONTEXT.md#设计稿链路的问题分流)。已知等价形态比对器会自动拉平（见 [restore-contract.md](./restore-contract.md)），能走到这里的都值得上报。
- YELLOW 先补页面、fixture 或状态触发，再重跑结构化采集。仍无法结构化判定且契约要求 visual 层时，按 restore-contract.md 第六节查视觉缓存：命中只读复用，未命中才截原型写入新缓存目录。**机器可检项不截图**（硬门禁 12）。实现侧截图写 `<story-dir>/evidence/<Task 编号>-r<轮次>/`。
- 视觉补证发现偏差时，把 `visual-results.json` 对应规则写成 `red` 再重跑 RED 报告；**不得把主观观察直接塞进实现清单而绕过报告**。

**③ GREEN — 只修 RED**

- 只改 `restore-report-red.json` 中属于当前 Task 的 RED；YELLOW 不是实现任务，先补证。
- 取值走 `dev-baseline.md / 工程依据` 引用的仓库范式：间距、颜色、字号用仓内 token，不硬编码；有可复用的公共方法就用既有的。

**④ 验 GREEN — 同一契约重跑 + 回归**

- 重跑 ① 的同一条链，唯一差别是 `report --phase green`。**不得编辑 RED 报告得到 GREEN 报告**；该命令在 `overall` 非 `green` 时以退出码 3 阻断。
- 合法结论只有：全部规则已验证；或未实际匹配的规则逐条命中契约内的冻结豁免。任何 RED、任何未解决 YELLOW 都不是 GREEN；**不得为收口就地新增豁免**。
- 跑与本 Task 改动**直接相关**的质量检查：相关测试文件（或所改包 / 目录的测试）、所改范围的 typecheck 与 lint。**不必每个 Task 全量跑一遍**——全量对账 DEMAND-2 起点失败集合收口在 Phase C 派发前自检做一次，功能自测试的 REG 再独立复核一次。**影响面分级为 S 时本项整体可跳过**（本轮测试转绿与契约 GREEN 照常要求），全量对账由 Phase C 派发前自检兜底；M / L 级照跑。跑的时候，**判定基准是 DEMAND-2 的起点失败集合，不是「全绿」**：

| 作用域内与基线对照 | 判定 |
| --- | --- |
| 失败项集合与基线逐条相同 | 通过 |
| 出现基线之外的新失败项 | 不通过，修到消失为止 |
| 基线里本来红的项转绿 | 通过，在 Step ⑥ 记一行，不回滚也不追查 |

基线之内的既有失败项**不去修**——那是本 Story 之外的代码，动它就出了本 Task 的文件清单。

- **已知约束核销**：按 #### 3 的共通子项，对本 Task 相关、尚未被本轮契约规则覆盖的已知约束逐条写出「约束 → 检查方式 → 结果」；无法当场验证的写明推迟到 Phase C 哪一份检视及理由，**禁止批量 `N/A`**。

**⑤ REFACTOR — 按需**

- 只在本 Task 的文件清单内。重构后重跑 ④ 的同一契约与回归判定。
- 无可重构就写「无」，不为凑步骤造改动

**⑥ 记录证据并提交**

- 按 [alpha-tests-restore.md](./alpha-tests-restore.md) 在 `alpha-tests.md` 新增一条：契约哈希、RED/GREEN 报告指纹与路径、三色摘要、视觉缓存指纹与路径、可选实现截图。
- `alpha-tests.md` 不复制完整报告，不保存第二份偏差表；`restore-report-*.json` 是机器细节的唯一来源。
- 回填「AC ↔ 证据映射」：证据类型加「还原」，证据链填记录编号，状态填 `GREEN` 或 `Deferred`
- 勾 `tasks.md` 的 checkbox，提交

**特殊分支**

| 情形 | 处理 |
| --- | --- |
| 页面或截图能力缺失 | 按 [环境降级](./degradation-and-recovery.md#二环境降级) 表处理，**源码级结果只作 static 层事实，不得越级替代 render / visual 层** |
| 结构化渲染已尝试但采集脚本报错 | 判 RED（执行失败），不是 YELLOW；修采集入口或实现定位后重跑 |
| 已有 Story 没有 `restore-contract.json` | 继续按 `legacy-screenshot-v1` 旧截图证据流程读取与续跑，不迁移历史证据；新 Story 不得主动选择旧流程 |

#### 5. 编译硬约束

| # | 约束 | 违反时 |
| --- | --- | --- |
| 1 | 修复动作**不出本 Task 的文件清单** | 停下上报，不自行扩大范围 |
| 2 | 禁止用**检查抑制手段**或**没有理由的类型断言**绕过（按仓库栈取值：`any` / `@ts-ignore` / `eslint-disable` / `# type: ignore` / `@SuppressWarnings` / `// @ts-nocheck` 等一切让类型检查或 lint 闭嘴的写法；以及 TypeScript 的 `as` 类型转换、非空断言 `!`） | 仓内既有范式就是如此才可用，且必须在代码旁写明理由；断言须有结构守卫（先做 `typeof` / `in` 等判断再断言）或旁注理由，否则与检查抑制同类，是 Phase C 的阻断级 |
| 3 | **同一个报错连续修 3 次不成就停止** | 停下上报 |

第 3 条以「同一个报错」计数：改了写法但报错文本不变，算同一次链条的延续，不重新计数。

#### 6. 两类升级中断

| 触发 | 判据 |
| --- | --- |
| 编译修不动 | 同一个报错连续修 3 次未成 |
| 需越界改动 | 修好它必须改本 Task 文件清单之外的文件 |

两者都按 P7 上报，**不自行决定**，同一时刻攒到的多个问题合并一轮。每个问题必须写出：报错原文或阻塞点、要改的文件、它为什么在清单外、推测与理由。

等待回答期间**停在当前 Task**：不跳过它做下一个、不用检查抑制手段临时糊过去、不把改动范围先扩出去再补问。

#### 7. 进度真相与落账

- **`tasks.md` 的 checkbox 是唯一进度真相。** 完成一步勾一步，不批量补勾，不在别处另记一份进度
- Step ⑥ 把证据落进 `alpha-tests.md`：还原轮进「还原证据记录」节，逻辑轮进 L4 / L3 记录节，两者都回填 AC ↔ 证据映射。**不另开第二本账**
- 上游未声明对接模式且接口实际不可用时，降级为静态实现模式，把受影响的 AC 标 `Deferred` 并写明原因与解除条件。**不得拿豁免顶替 `Deferred`**
- 全部 Task 的 checkbox 勾完、`alpha-tests.md` 无缺口，才进 Phase C
- Step ⑥ 按实际报告状态落账：**有未解决 YELLOW 就不能勾本轮 GREEN**，按 [还原 YELLOW 的放行通道](../SKILL.md#还原-yellow-的放行通道) 处理
