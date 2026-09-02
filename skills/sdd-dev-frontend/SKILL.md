---
name: sdd-dev-frontend
description: 执行或续跑单个前端 Story：冻结验收基线、实现 tasks.md，并按声明与风险编译最小充分验证，留下可追溯证据。用于用户要求实现、继续或收口前端 Story，按 HTML 原型、参照页或文字规格还原页面，或执行其中的勘察、验证与检视阶段；只规划不写代码时路由 sdd-task 或 sdd-task-frontend。
---

# 前端 Story 执行

## 核心契约

一次只处理一个独立前端 app × 一个 Story。计划/执行所有权、TaskPacket、基线源、[验证模型](./references/execution-contract.md#验证模型)（验证范围、验证方法、人工验收字段）、声明状态与[执行档位](./references/execution-contract.md#执行档位)以 [前端 SDD 执行契约](./references/execution-contract.md) 为共享事实源。验证组合（档位、触发器、模块、角色、维度、逐声明挂载）由 `<skill-dir>/scripts/compile_portfolio.py` 按 `<skill-dir>/scripts/portfolio-rules.json` 编译，agent 只识别判断型触发器；规则为什么这样、以及[验证方法判定](./references/validation-policy.md#七验证方法的判定规则)在 [validation-policy.md](./references/validation-policy.md)。

`tasks.md` 是实现进度真相，`alpha-tests.md` 是声明状态与证据账本。当前 app 的公共事实来自 `sdd-init-frontend` 产出的九份按问句分类的 baseline 文件；本 skill 只产生当前需求的 `DEMAND-1～3`。

## 工作流

进入某阶段时只读取对应细则；续跑或单步入口同样按当前阶段定位，不预读后续阶段。

| Phase | 动作与出口 | 细则 |
| --- | --- | --- |
| -1 / 0 | 校验 app baseline；定位 Story；核实上游字段；按机械判据定[执行档位](./references/execution-contract.md#执行档位)；编译初始验证组合；只为已选模块取得起点证据 | [phases/entry.md](./references/phases/entry.md) |
| A1 / A2 | 按基线源抽取规格；按档位与风险决定勘察由主 agent 自做还是派子代理；生成 QA 基线；用户确认后冻结并编译还原契约 | [phases/spec.md](./references/phases/spec.md) |
| B | 按 Task 实现，只取得本 Task 改变声明的因果证据；checkbox 与证据账本同步 | [phases/implementation.md](./references/phases/implementation.md) |
| C / D | 按最终 diff 复判档位（只升不降）并重编译组合；执行适用模块和角色；修确证阻断；按依赖重取失效证据；逐声明收口 | [phases/review-closeout.md](./references/phases/review-closeout.md) |
| 解除 DEFERRED | 已收口 Story 的外部依赖就绪后单独进入：只对 Deferred 表里的声明重取证、重聚合，不重开 A/B | [phases/review-closeout.md#解除-deferred](./references/phases/review-closeout.md#解除-deferred) |

正常主干只有 QA 基线确认需要用户决策。路径歧义、外部授权、无安全默认值的规格缺口、连续三次修复失败、越界改动和未决阻断按所在阶段一次性批量上报。

## 输出规范

| # | 规则 |
| --- | --- |
| P1 | 一轮只放一个决策点：确认、批量提问或完成 |
| P2 | 多项用表格/列表；散文摘要最多两句 |
| P3 | 直接给结果，不播报阶段过程 |
| P4 | 确认门写“Phase、产物一句话、请确认继续或指出修改” |
| P5 | 最终先给状态、`acceptance.md` 路径、下一步三行；有遗留项必须继续输出 handoff |
| P6 | 无决策阶段静默衔接；结论意外时才单行告知 |
| P7 | 同类问题一轮批量问；区分必须回答与带安全默认的推测 |
| P8 | handoff 与 `acceptance.md` 清单逐条对账，以“现象 + 影响 + 是否需要用户处理”表达 |

## 硬门禁

这些门禁保护来源、所有权和状态诚信；它们本身不触发固定验证动作。

0. **仓库事实就绪。** baseline 出现旧名 `routing.md` / `styling.md` / `testing.md` 时先由 `sdd-init-frontend` 原位迁移；`index.md` 缺失或 `structure.md` 读不出「具名框架 + 具名形态」时再完整执行 init。仅验证能力受限时继续，但依赖声明保持 `UNVERIFIED`。**命名归一后不按份数查**——空文件按规定整份删，`组件库` 形态下 `routes.md` 与 `api.md` 本就不该存在。单条结论不成立不是就绪问题，按消费点自证就地修。
1. **执行清单存在。** 没有 `tasks.md` 时，仅在会话已明确 Story、AC、基线和文件范围时按 Phase 0 起草并确认；否则回 `sdd-task`。
2. **期望先冻结。** QA 基线未经用户确认不得进入 Phase B。
3. **声明按需生成。** R/F 是分类表；只生成需求与风险实际要求的行，不造 N/A 空壳。
4. **限制可见。** 只登记影响已选模块的 Story 限制；模块不可执行时只降级依赖声明，不用源码检查冒充浏览器或截图证据。
5. **状态诚实。** `PROVEN / UNVERIFIED / DEFERRED` 严格遵守共享契约；`MANUAL` 不是状态。
5b. **人工验收不代签。** `manual_acceptance` 声明只能由真实人员执行并回填 `manual_checked_by` / `manual_checked_at` / `evidence_refs`；agent、自测试与独立检视只能准备候选实现并交出待验收项，不得用自己的观察替代签字。存在人工验收 `UNVERIFIED` 时只能交付部分验收。
6. **子代理只读。** 子代理只回传正文；检视截图可写 `<work-dir>`，正式工件由主 agent 落盘。
7. **范围受控。** 执行上游设计和对接模式，不改设计、不发明响应式规格、不跨仓。计划文件清单外的连带改动按共享契约的扩散承接规则处理并登记；未登记的计划外改动仍按越界处理。
8. **冻结可追溯。** 开工后放宽期望必须记录理由并重新确认。
9. **原型隔离。** 仅 `extract-prototype` / `extract-block-spec` 读取原型源码；其他角色只读 `<design-spec-dir>` 产物。争议时只回查一个区块并登记。
10. **哈希一致。** `dev-baseline.md` 与 `restore-contract.json` 哈希不一致时拒绝执行，不从当前实现反推期望。
11. **三色真实。** 还原报告只用 RED/YELLOW/GREEN；YELLOW 不能改写为 GREEN。
12. **证据分层。** 机器可检项用结构化事实；截图只补机器无法可靠判断的视觉项。
13. **规范单一所有者。** `PATTERN-*` 正文只在 app baseline，且规范节只有 `sdd-init-frontend` 能改；Story 只保存采用的 ID，不记录 baseline 指纹。清单条目指路失效可就地修单条。
14. **抽取缺口先登记。** 抽取器退出码 4 的每类覆盖缺口先进入已知缺口，再显式确认重跑。
15. **浏览器按需解析。** 组合首次选择浏览器模块时才确定并实测 `<browser-driver>`；不可用只影响依赖声明。
16. **工具缺口不变豁免。** `suspected-tool-equivalence` 退出码 5 只补比对器或上报工具缺口，不改产品实现、不加冻结豁免。

## 路径变量

| 变量 | 解析 |
| --- | --- |
| `<repo-root>` | TaskPacket 的 project 对应 Git 仓或 monorepo 根 |
| `<frontend-root>` | 当前 Story 唯一命中的独立前端 app 根；单 app 仓等于 `<repo-root>`，monorepo 由 `search_paths` 与前端设计定位 |
| `<repo-baseline-dir>` | `<frontend-root>/frontend-baselines/`；公式以 `<init-skill-dir>/references/baseline-contract.md` 为唯一事实源 |
| `<story-dir>` | `tasks.md` 所在目录 |
| `<requirement-dir>` | Requirement 设计文档所在目录 |
| `<prototype-dir>` | 已核实的 HTML 原型目录；无原型时为空 |
| `<design-spec-dir>` | `<requirement-dir>/design-spec/` |
| `<skill-dir>` | 本 skill 目录 |
| `<init-skill-dir>` | `<skill-dir>/../sdd-init-frontend/` |
| `<review-pack-dir>` | `<skill-dir>/../sdd-review-frontend/` |
| `<base-ref>` | 可选 Story 起点 git 引用 |
| `<browser-driver>` | 被选浏览器能力及已验证启动方式 |
| `<evidence-dir>` | `<story-dir>/evidence/`；本 skill 产出的全部机器工件（JSON 与归档截图） |
| `<work-dir>` | `<story-dir>/.work/`；只活在阶段内的过程件，收口后整目录删 |
| `<review-evidence>` | `<evidence-dir>/review-evidence.json` |

唯一命中时静默继续；不可推导或多候选的变量按 P7 一次问完。`search_paths` 横跨多个独立 app 时不选 monorepo 根兜底，回流 `sdd-task` 拆分 app 范围。给人读的 Story Markdown 写 `<story-dir>` 根，机器工件写 `<evidence-dir>`，过程件写 `<work-dir>`；Requirement 级设计事实写 `<design-spec-dir>`，app baseline 写 `<repo-baseline-dir>`。

## 浏览器驱动

只在验证组合含 `render`、`story`、`review-layout` 或浏览器型 `self-test` 时解析。按可用性依次选择现有浏览器控制工具、仓内既有 E2E 驱动、用户提供的可复现实测方式；必须能打开页面、触发状态、注入采集并在需要时截图。缺任一能力就把相应模块记为未执行。

同页面、fixture、runtime 与 reset 边界尽量单连接批量采集；每个 scenario 仍记录独立步骤、断言和 `depends_on`，便于精确失效。

## subagent 派发约定

主 agent 只把角色提示词路径和“路径变量取值”表传给子代理，不复制项目正文。进入派发前读目标提示词的“前置校验”；终止级前置不齐则不派。子代理返回前置缺失时不猜测补齐，按 P7 上报；回传结构不合格只退回一次。

| 分支 | 角色 |
| --- | --- |
| 原型切分 / 区块规格 | `extract-prototype` / `extract-block-spec` |
| 规格 / 代码勘察 | `recon-spec` / 风险触发时的 `recon-codebase` |
| 独立检视 | 只派验证组合选中的 `review-restore`、`review-layout`、`review-convention`、`review-quality`、`self-test` |

Phase C 角色共享 [review/evidence.md](./references/review/evidence.md) 的原始事实；派哪几格、参数怎么组装见 [review/dispatch.md](./references/review/dispatch.md)，检查项、定级与回传契约都不在本 Skill，按同一份指向 `sdd-review-frontend`。并发槽位不足时完成一份立即补派下一份，不等待整波。

## 工件管理

`<story-dir>` 只分两层：根下全是给人读的 Markdown，`evidence/` 里全是机器件，`.work/` 里全是过程件。分法的判据是「验收的人要不要主动打开它」，不是「哪条流水线产的」。

```text
<story-dir>/
├── tasks.md · story-delta-frontend-design.md      上游：做什么、怎么设计
├── dev-baseline.md                                怎样算做完（Phase A 冻结的标准）
├── alpha-tests.md                                 做到哪了（证据账本）
├── acceptance.md                                  能不能验收（收口入口）
├── evidence/                                      机器件；acceptance.md 会指路进来
│   ├── restore-contract.json · restore-adapter.json
│   ├── restore-report-red.json · restore-report-green.json · restore-report-review.json
│   ├── portfolio.json · review-evidence.json · review-results.json
│   └── artifacts/                                 被结论引用的截图与结构化结果
└── .work/                                         过程件；Phase D 退出后整目录删
```

| 工件 | 所有权与生命周期 |
| --- | --- |
| 九份 app baseline 文件 | `sdd-init-frontend` 所有；本 skill 按 ID 选读，只可就地修清单单条 |
| `tasks.md` | 只勾 checkbox，不改验收内容 |
| `alpha-tests.md` | 回填证据、声明状态与 Deferred |
| `dev-baseline.md` | Phase 0 写执行起点（环境），A2 追加冻结 QA 基线 |
| `acceptance.md` | 给人的收口摘要，由 `aggregate` 整文件渲染，不手写 |
| `design-spec/*` | Requirement 级确定性事实；原型或区块哈希变化时更新。`visual-baseline/` 下原型指纹已不匹配当前 `design-facts.json` 的缓存目录，在下一次 A1 抽取时删除 |
| `evidence/restore-contract.json` / `restore-adapter.json` | A2 冻结后编译；Phase B / C 跑的永远是这一份 |
| `evidence/restore-report-{red,green,review}.json` | Phase B 的 RED / GREEN 与 Phase C 的重跑。三份都被 `alpha-tests.md` 的还原证据记录按路径与指纹引用，是证据不是过程件，不删 |
| `evidence/portfolio.json` | `compile_portfolio.py` 的唯一输出：Phase 0 写 initial，Phase C 以同一文件为 `--previous` 原地覆盖成 final，被比较过的 Phase 0 快照留在 `previous` 字段。`validation_portfolio` 抄进 `review-evidence.json`，`--markdown` 抄进 `dev-baseline.md` |
| `evidence/review-evidence.json` | 验证组合、命令和场景原始事实；不保存判断 |
| `evidence/review-results.json` | 适用角色聚合与结构化结论；`acceptance.md` 的机器侧 |
| `evidence/artifacts/` | 被 scenario `artifacts[]` 引用的截图与结构化结果；未被任何结论引用的不归档 |

模板只在创建对应工件时读取 [templates/story-artifacts.md](./references/templates/story-artifacts.md)。还原契约、QA 基线和证据字段分别以其 reference 或脚本 schema 为唯一事实源，不在本文件展开。

### 过程件

过程件只在一个阶段内活着，写 `<work-dir>`。它们全部能从正式工件与代码重算，丢了不构成证据缺口。**Phase D 退出门禁全部通过后整目录删除**；中断续跑期间保留，续跑从上次阶段接着用。

| 文件 | 创建 | 消费点 | 之后 |
| --- | --- | --- | --- |
| `restore-contract-rules.json` | A2 `recon-spec` 回传的规则草稿落盘 | `verify_restore_contract.py contract` | 契约已含全部规则 |
| `static-results.json` / `render-results*.json` / `visual-results.json` | 每次还原轮 | 同轮 `report` | 报告已含逐规则结论；下一轮直接覆盖 |
| `diff-facts.json` | Phase C 第 1 步 | `compile_portfolio.py --phase final`、`aggregate --diff-facts` | 解除 DEFERRED 时重算 |
| `code-manifest.json` / `runtime.json` | 每次采集前 | `manage_review_pipeline.py scenarios` | 已并入 `review-evidence.json` |
| `review-<角色>.json`（RoleResult） / `norm-candidates.json` / `decisions.json` | 子代理回传、用户答复后落盘 | `aggregate` | 已并入 `review-results.json` 与 `acceptance.md` |
| 子代理补证截图 | 检视期间 | `merge-additions` 校验后归档到 `evidence/artifacts/` | 未被引用的随目录删 |

## 退出门禁

| # | 判据 |
| --- | --- |
| 1 | `tasks.md` checkbox 与实际实现一致 |
| 2 | 每条声明恰有一个合法状态 |
| 3 | 每条 `PROVEN` 都有覆盖它且仍新鲜的证据 |
| 4 | 未清零阻断不影响任何 `PROVEN` 声明 |
| 5 | 验证组合、模块执行状态、`UNVERIFIED`、`DEFERRED`、Open Question 和建议级均已对账 |
| 6 | 待人工验收项已逐条对账；每条 `manual_acceptance` 的 `manual_outcome` 与 `claim_status` 是合法配对，`PROVEN` 的四项人工字段齐全 |

YELLOW 按原因转为补证、`UNVERIFIED`、`DEFERRED` 或真实 RED；不就地新增豁免。修复只失效依赖改动文件的证据，出现新风险触发器时才扩大组合。

## 最终输出

先输出三行：带验收限定的完成状态、`<story-dir>/acceptance.md`、唯一下一步。全部 `PROVEN` 时写“可验收”；有 `UNVERIFIED` 时写「部分验证：N 条声明未验证」并给补验方式；只有 `DEFERRED` 时写「前端已验证，N 条真实接缝待 <外部依赖>」并给解除条件——**两者不许压成一个「部分验收」**，前者不能合并、后者可以先合并，读的人要靠这一句决定。

**存在待人工验收项时不写无条件“可验收”**，只写「实现完成，待 N 项人工验收」或「部分验收」，且唯一下一步优先指向具体的人工验收动作而不是泛化的「补测试」。

**跟用户说话时用中文状态词**（已验证 / 未验证 / 已暂缓），账本里的值仍是英文常量；两列对照见[执行契约的状态表](./references/execution-contract.md#声明与状态)。

**有待决项时当场问，不要只给路径。** `acceptance.md` 的「需要你处理」里每条待决项都要在对话里问出来：一轮问完（P1、P7），每条给出可选项与各自后果，别让用户自己去文档里找该决定什么。用户答完后按 `aggregate --decisions` 重渲染，答复连同时间就地记回该条目下——**同一件事不许下一轮再问一遍**，而三个月后「当时为什么这么定」也查得到。给不出选项的（需要外部信息才能判）照实说明缺什么。

`acceptance.md` 的「需要你处理」或「你该知道，但不用动」非空时，再逐条输出 P8 人话条目；条数必须与建议级、Open Question、Deferred、规范候选逐类一致。
