---
name: sdd-review-frontend
description: >-
  按五格独立 lens 检视前端改动：restore（单区块冻结契约）、layout（跨页/真实数据/视口）、convention（PATTERN 规范）、quality（可观察工程质量）、test（F/REG 功能声明）。
  Use when reviewing frontend diffs, PRs, or 前端 Story 验收；when the user names sdd-review-frontend / restore-lens / layout-lens / convention-lens / quality-lens / test-lens.
---

# 前端通用 Review 包

**本包只做判断。** 检查项、格子边界、定级与回传契约都在这里，调用方不留副本。

调用方负责三件事：选派哪几格、采集证据、聚合落盘。请求里只下发**当前格子**的交付件、`task_statement` 与 `checklist`；本包不关心调用方是谁、有几个阶段。同一缺陷不得在两个 lens 各出一次 Finding。

判据默认值在本包，Story 特有的约束由调用方在请求里传入：冻结声明、豁免、容差、风险闭包与级别覆盖。调用方不传时按本包默认值判。

**restore 的机器执行器在调用方那一侧**（契约编译与三色报告）。本包的 restore-lens 判的是同一套 R1–R6 的级别与处置，不重做比对。

## 五格

一格一份 checklist，格子边界、禁止项、`task_statement`、`max_findings`、`forbidden_reads` 与检查项都在同一个文件里，没有单独的角色卡。

| lens | cell | 检查清单 | 适用条件 |
| --- | --- | --- | --- |
| restore-lens | CODE-RESTORE | [restore](frontend-code-checklists/restore.md) | 变更区块有冻结 R 契约与设计事实 |
| layout-lens | CODE-LAYOUT | [layout](frontend-code-checklists/layout.md) | 改了可见结构，且风险跨页、跨视口或涉及真实数据 |
| convention-lens | CODE-CONVENTION | [convention](frontend-code-checklists/convention.md) | 仓内有 `PATTERN-*` / `REQ-DEC-*`，且 diff 落在其适用场景 |
| quality-lens | CODE-QUALITY | [quality](frontend-code-checklists/quality.md) | 引入非平凡状态、副作用、复杂度或性能面 |
| test-lens | CODE-TEST | [self-test](frontend-code-checklists/self-test.md) | 有冻结 F 行或已选 REG 行需要实跑 |

回传形状见 [role-result.md](references/role-result.md)。栈内信号（非自动违规开关）见 [stack-signals.md](references/stack-signals.md)。

## 现象归属

**派哪几格由调用方决定。** 调用方按自己的风险规则选格，在请求里给出 `gate` 标识；本包不枚举有哪些 gate，也不规定某个 gate 该派哪几格。未派的格不是「未执行」，也不生成占位结果。

同一个现象只归一格，不得跨格重判：

| 现象 | 归属 |
| --- | --- |
| 变更区块相对冻结 R 契约的 RED / YELLOW / GREEN | CODE-RESTORE |
| 跨页不一致、真实数据溢出、目标视口「不破」、栅格、运行时交互态、滚动/固定 | CODE-LAYOUT |
| 命名、组件范式、token、请求封装、公共能力复用、类型抑制、i18n——且有 `PATTERN-*` | CODE-CONVENTION |
| 职责、重复、复杂度、状态放置、副作用、错误边界、死代码、性能——且能说出可观察后果 | CODE-QUALITY |
| 冻结 F 行与已选 REG 行是否成立 | CODE-TEST |

`PATTERN-*` 语义等价的重复实现走 CODE-CONVENTION 的 `shared-capability-reuse`，不走 CODE-QUALITY 的 `duplicated-code`。各 checklist 的「格子边界」只写自己那侧的例外，不复述本表。

## 派发

对调用方选出的每一格，按顺序做完再派下一格。完成标准：该格 checklist 全文已读，回传一份 `RoleResult@v2`。

1. 读该格 checklist 的 YAML：`task_statement`、`inputs`、`forbidden_reads`、`max_findings`。
2. 读正文的「格子边界」与「禁止」，再逐条判检查项；未触发的项记 `skipped` 并引用 `skip_when`。
3. 只读 `inputs` 列出的层。缺终止级输入时回传 `前置缺失：<清单>`，不猜测补齐。
4. 按 checklist 每条的 `normative_level` / `default_severity` / `max_severity` 出 Finding；定级规则见下。
5. 回传裸 JSON，符合 [role-result.md](references/role-result.md)。不复制命令或截图全文。

未选出的格不派、不生成占位结果。

调用方若使用自己的角色名与维度号，映射由**调用方一侧**登记；回传契约仍是同一份 [role-result.md](references/role-result.md)，两边不各留一套。

## 定级

两档事实映射到 P 级，不另造第三档「风格偏好」：

| 两档 | P 级 | 何时 |
| --- | --- | --- |
| 阻断级 | **P0** 或 **P1** | 冻结声明被证伪且未命中 `EX-n`；或能给出触发序列且已产生错误结果 |
| 建议级 | **P2** | 有证据、有价值，但未证伪任何冻结声明，也没有当前错误结果 |
| 不记 | `skipped` / 不出 Finding | 命中 `skip_when`、命中 `EX-n`、找不到基准、说不出可观察后果 |

升级顺序（先匹配先停）：

1. 违反冻结 R/F/AC 且未命中 `EX-n` → 至少 P1；破坏主路径或契约 → **P0**。
2. 确证错误结果（具体操作序列或客观静态反例）→ 至少 P1；竞态覆盖、泄漏、无限循环、核心流程不可完成 → **P0**。
3. 调用方已选回归闭包，且相对可比起点变差 → P1。
4. 其余有证据的问题 → `default_severity`，不得超过该条 `max_severity`。

无证据不得判 P0。`evidence_ids` 必须指向文件与行号、锚点或证据 ID。

## 全局禁止

- 不评论文风与排版。
- 后启动的格不得读取其他格的 Finding。

各格自己的禁止项写在对应 checklist 的「禁止」节，此处不复述。
