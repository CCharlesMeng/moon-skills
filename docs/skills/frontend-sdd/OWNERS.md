# 前端 SDD 链路共建分工

覆盖 `skills/sdd-init-frontend/`、`skills/sdd-dev-frontend/`，以及从后者拆出的设计事实抽取能力（见[第五节](#五规划中的第三个-skill)）。

配套文档：接缝契约在 [接缝契约.md](./接缝契约.md)，改任何一条接缝前先读它。

---

## 一、划分原则

三条，按优先级：

1. **owner 边界 = 产物生命周期边界。** 仓库级（`REPO-1~3`）、Requirement 级（`DEMAND-1`）、Story 级（`DEMAND-2/3`）三层的产物本来就不在同一个 PR 里一起改。按这条线切，git 冲突面天然最小。
2. **一条判据只有一个 owner。** 判据指「什么情况判什么级别」「什么算通过」这类会被别处引用的规则。同一条判据出现在两个文件里，其中一个必须是指针，不能是副本——两份判据必然漂移，而漂移的那一次会让执行侧做出错误判定。
3. **标准与量具分家。** 定义「怎样算做完」的人，不同时拥有「判定做到没做到」的那台机器。两者合一时，机器测不了的维度会被悄悄从标准里删掉——这正是本链路花最大力气防的 `YELLOW → GREEN` 洗白。

按角色名（「样式还原」「验收」）划分**不适用**：样式还原横跨设计事实、契约引擎和 Story 期望值三层，按它切会让三个人同时改同一批文件。

---

## 二、分工

推荐**三名 owner + 一名整合者**，整合者可由三人之一兼任。

### A · 存量与仓库事实

拥有「这个仓库既有什么、新代码跟没跟上」这条线。

| 项 | 内容 |
| --- | --- |
| 独占文件 | `skills/sdd-init-frontend/**`（整个 skill）<br>`sdd-dev-frontend/agents/recon-codebase.md`<br>`sdd-dev-frontend/agents/review-convention.md`<br>`sdd-dev-frontend/agents/review-quality.md`<br>`sdd-dev-frontend/references/stack-antipatterns.md` |
| 拥有的判据 | `PATTERN-*` 准入条件与生命周期；`REPO-1~3` 字段、失效与刷新规则；`C1–C7` 与 `Q1–Q8` 的维度定义；各技术栈的具体表现形式 |
| 产物生命周期 | 仓库级，跨 Requirement |
| 典型工作 | 新增一个栈的适配、调整范式准入门槛、改 baseline 扫描器 |

### B · 设计事实（抽取层）

拥有「设计稿里客观上有什么」这条线。**它的产物同时被 design、task、dev 三个阶段消费**，是三条线里 schema 变更代价最高的一条。

| 项 | 内容 |
| --- | --- |
| 独占文件 | `sdd-dev-frontend/scripts/extract_design_spec.py` + 对应 evals<br>`sdd-dev-frontend/agents/extract-prototype.md`<br>`sdd-dev-frontend/agents/extract-block-spec.md`<br>`sdd-dev-frontend/references/block-spec-template.md` |
| 拥有的判据 | 抽取覆盖缺口的口径与退出码；锚点格式；区块粒度；原型指纹算法；视觉缓存键；`IC-nn` 编号规则 |
| 产物生命周期 | Requirement 级，跨 Story |
| 典型工作 | 支持新的设计稿导出格式、扩大可解析的 CSS 范围、能力映射表格式 |

### C · 判定标准

拥有「怎样算做完」这条线。**只定标准，不造量具。**

| 项 | 内容 |
| --- | --- |
| 独占文件 | `sdd-dev-frontend/agents/recon-spec.md`<br>`sdd-dev-frontend/agents/review-layout.md`<br>`sdd-dev-frontend/agents/self-test.md`<br>`sdd-dev-frontend/references/qa-baseline-template.md`<br>`sdd-dev-frontend/references/review-dimensions.md` |
| 拥有的判据 | QA 基线十维与三道栅栏；`R1–R6` / `F1–F4` / `L1–L6` 的维度定义；阻断级与建议级两档；四条定级规则；豁免 `EX-n` 的可接受理由；退出门禁十条的判据 |
| 产物生命周期 | Story 级 |
| 典型工作 | 收紧某个维度的措辞黑名单、调整默认级别、增删门禁项 |

### D · 验证引擎（量具）

拥有「怎么机械地判定做到没做到」这条线。

| 项 | 内容 |
| --- | --- |
| 独占文件 | `sdd-dev-frontend/scripts/verify_restore_contract.py`<br>`sdd-dev-frontend/scripts/collect_restore_facts.js`<br>`sdd-dev-frontend/references/restore-contract.md`<br>`sdd-dev-frontend/references/diff-list-template.md`<br>`sdd-dev-frontend/references/alpha-tests-restore.md` |
| 拥有的判据 | 契约与 adapter 的字段和模式；默认容差；`required_layers` 层映射；`RED/YELLOW/GREEN` 的机器语义；浏览器驱动分档；证据落账格式 |
| 产物生命周期 | Story 级执行期 |
| 典型工作 | 新增一种 `check_mode`、支持新的浏览器驱动、改报告 schema |

### 0 · 整合者

| 项 | 内容 |
| --- | --- |
| 独占文件 | `sdd-dev-frontend/SKILL.md`<br>`sdd-dev-frontend/CONTEXT.md`<br>`sdd-dev-frontend/references/degradation-and-recovery.md`<br>`sdd-dev-frontend/references/story-artifact-templates.md`<br>`sdd-dev-frontend/references/sdd-task-amendments.md`、`sdd-task-frontend-split.md`、`sdd-design-amendments.md`<br>本目录下两份治理文档 |
| 拥有的判据 | Phase 顺序与出口；硬门禁编号；路径变量；派发协议；`P1–P7` 输出规范；降级与失败恢复；单步入口路由 |
| 职责 | 审所有契约变更；维护术语表；**其余三人不直接编辑 `SKILL.md`** |

### 按人手收缩

| 人手 | 合并方式 |
| --- | --- |
| 3 人 + 整合者兼任 | **B + D 合并为「机器侧」**（脚本与 schema 都在这），C 为「标准侧」，A 为「存量侧」。这样仍然满足原则 3 |
| 2 人 | 「机器侧 + 存量侧」/「标准侧 + 整合者」 |
| 1 人 | 不需要本文档，但接缝契约仍然要维护——它防的是自己三个月后的漂移 |

**不要把 C 和 D 合并。** 那是原则 3 唯一守不住的合法：`review-dimensions.md` 说某维度必须验证，`restore-contract.md` 说这个维度机器测不了，两份文件在两个人手里时，结论只能是「记 YELLOW 并披露」；在一个人手里时，最省事的写法是把那条维度删掉。

---

## 三、四处需要明确归属的跨界文件

这几处天然横跨两个 owner，已按下表定死，不要再各自解释。

| 文件 | 归属 | 边界 |
| --- | --- | --- |
| `agents/recon-spec.md` | **C** | 它同时产出 QA 基线（C 的资产）与还原契约规则草稿（D 的 schema）。文件归 C；**规则草稿的字段与模式只以指针形式引用 `restore-contract.md`**，D 改 schema 时不动这个文件 |
| `references/review-dimensions.md` | **C** | 表里的 `C1–C7` / `Q1–Q8` **维度名与基准来源列归 A**，**默认级别列归 C**（分级体系是 C 的）。A 改维度定义时改 `agents/review-convention.md` 与 `stack-antipatterns.md`，只在本表同步一行摘要 |
| `references/stack-antipatterns.md` | **A** | 里面同时有 `C*` 与 `Q*` 的栈特定表现，两者都是 A 的维度定义，无跨界 |
| `SKILL.md` | **0** | 其余三人提「指针请求」：说明要指向自己文件里的哪一节、为什么现有指针不够，由整合者落 |

---

## 四、协作机制

**1. 一个 PR 只动一个 owner 的目录，外加至多一处接缝。** 跨两个 owner 的改动拆成两个 PR，先合被依赖的那个。

**2. 接缝变更走双签。** 契约清单里的任何一条，改动必须：同一个 PR 内改掉契约本身与**全部消费方**；由整合者 + 受影响 owner 共同批准；带一条能失败的 eval。

**3. 每个 owner 对自己的判据负责回归。** 现状是只有抽取器有单测（`evals/test_extract_design_spec.py`，31 条），A、C、D 三侧的判据是纯提示词、零保护。提示词侧的做法是黄金样例：给定「一份冻结基线 + 一段 diff」，断言期望的结论编号与级别。**没有 eval 的判据变更不合并。**

**4. 机械一致性检查每个 PR 都跑。** 链接与锚点可达、路径变量已定义、门禁编号存在、维度名跨文件一致、ID 前缀在白名单内、每份 agent 提示词都有「前置校验 / 只读声明 / 输出格式」三节。今天已验证过这几项，需要固化成 `evals/` 里的脚本。

**5. 术语先行。** 新概念先进 `CONTEXT.md` 再进任何提示词。术语表里带 `_Avoid_` 的词是硬约束，不是建议。

---

## 五、规划中的第三个 skill

抽取层被 design、task、dev 三个阶段共同消费之后，它留在 `sdd-dev-frontend` 里就不成立了：design 阶段只想做一次设计稿盘点，却要加载一份 900 行、通篇讲 Story 执行的 `SKILL.md`。

建议拆为 **`sdd-extract-frontend`**，与现有两个 skill 构成三层对应：

| skill | 产出 | 生命周期 | owner |
| --- | --- | --- | --- |
| `sdd-init-frontend` | `REPO-1~3` | 仓库级 | A |
| `sdd-extract-frontend`（待建） | `DEMAND-1` | Requirement 级 | B |
| `sdd-dev-frontend` | `DEMAND-2` / `DEMAND-3` | Story 级 | C + D + 0 |

拆分后 `sdd-dev-frontend` 的 Phase A1 改为路由，与 Phase -1 路由 `sdd-init-frontend` 完全同构；`<design-spec-dir>` 本来就是 Requirement 级、按哈希增量复用，所以这是归属权变更，不是重写。

未拆分前的过渡入口：`sdd-dev-frontend` 的[单步入口路由](../../../skills/sdd-dev-frontend/SKILL.md#单步入口路由)中的「重抽设计稿规格」。
