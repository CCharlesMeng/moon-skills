---
name: sdd-review-frontend
description: >-
  按五格独立 lens 检视前端改动：restore（单区块冻结契约）、layout（跨页/真实数据/视口）、convention（PATTERN 规范）、quality（可观察工程质量）、test（F/REG 功能声明）。
  Use when reviewing frontend diffs, PRs, or sdd-dev 验收；when the user names sdd-review-frontend / restore-lens / layout-lens / convention-lens / quality-lens / test-lens.
---

# 前端通用 Review 包

从 `sdd-dev-frontend` 抽出的验收能力。本包只做**判断**。

| 能力 | 原实现怎么处理 |
| --- | --- |
| layout / convention / quality / test | 判据、定级与回传契约**只在本包**；`sdd-dev-frontend` 已删掉自己的副本，Phase C 四角色的提示词只剩派发与取证，判断读本包。 |
| restore | **机器执行器未搬**：`verify_restore_contract.py`、`restore-contract.md`、Phase B 还原轮仍在 `sdd-dev-frontend`。本包的 restore-lens 是同一套 R1–R6 的判断卡，不进入 `manage_review_pipeline.py`。 |

调用方采集证据、编译验证组合、落盘。门面只下发**当前格子**的交付件、`task_statement` 与 `checklist`。同一缺陷不得在两个 lens 各出一次 Finding。

## 五格

| lens | cell | 检查清单 | 何时选它 |
| --- | --- | --- | --- |
| [restore-lens](roles/restore-lens/ROLE.md) | CODE-RESTORE | [restore](frontend-code-checklists/restore.md) | 变更区块有冻结 R 契约与设计事实 |
| [layout-lens](roles/layout-lens/ROLE.md) | CODE-LAYOUT | [layout](frontend-code-checklists/layout.md) | 改了可见结构，且风险跨页、跨视口或涉及真实数据 |
| [convention-lens](roles/convention-lens/ROLE.md) | CODE-CONVENTION | [convention](frontend-code-checklists/convention.md) | 仓内有 `PATTERN-*` / `REQ-DEC-*`，且 diff 落在其适用场景 |
| [quality-lens](roles/quality-lens/ROLE.md) | CODE-QUALITY | [quality](frontend-code-checklists/quality.md) | 引入非平凡状态、副作用、复杂度或性能面 |
| [test-lens](roles/test-lens/ROLE.md) | CODE-TEST | [self-test](frontend-code-checklists/self-test.md) | 有冻结 F 行或已选 REG 行需要实跑 |

哪个现象归哪一格、`restore` 与 `layout` 为什么不重叠，只在 [gate-matrix.md](references/gate-matrix.md) 定义，各 ROLE 的「格子边界」只写自己那侧的例外。回传形状见 [role-result.md](references/role-result.md)。栈内信号（非自动违规开关）见 [stack-signals.md](references/stack-signals.md)。

## 派发

对调用方选出的每一格，按顺序做完再派下一格。完成标准：该格 `ROLE.md` 的当前 `checklist_set` 已读，对应 checklist 全文已读，回传一份 `RoleResult@v2`。

1. 读该格 `ROLE.md` 的 YAML：`task_statement`、`reads`、`forbidden_reads`、`max_findings`。
2. 读 `checklist_sets.directory` 下、`id` 对应该格的 checklist。只判清单里的检查项；未触发的项记 `skipped` 并引用 `skip_when`。
3. 只读 `reads` 列出的层。缺终止级输入时回传 `前置缺失：<清单>`，不猜测补齐。
4. 按 checklist 每条的 `normative_level` / `default_severity` / `max_severity` 出 Finding；定级规则见下。
5. 回传裸 JSON，符合 [role-result.md](references/role-result.md)。不复制命令或截图全文。

未选出的格不派、不生成占位结果。

`sdd-dev-frontend` Phase C 的接线（角色名 ↔ lens、维度号 ↔ `legacy_id`）见该 Skill 的 [review-pack-adapter.md](../sdd-dev-frontend/references/review-pack-adapter.md)；回传契约是同一份 [role-result.md](references/role-result.md)，两边不各留一套。

## 定级

两档事实映射到 P 级，不另造第三档「风格偏好」：

| 原 sdd-dev 档 | 本包 | 何时 |
| --- | --- | --- |
| 阻断级 | **P0** 或 **P1** | 冻结声明被证伪且未命中 `EX-n`；或能给出触发序列且已产生错误结果 |
| 建议级 | **P2** | 有证据、有价值，但未证伪任何冻结声明，也没有当前错误结果 |
| 不记 | `skipped` / 不出 Finding | 命中 `skip_when`、命中 `EX-n`、找不到基准、说不出可观察后果 |

升级顺序（先匹配先停）：

1. 违反冻结 R/F/AC 且未命中 `EX-n` → 至少 P1；破坏主路径或契约 → **P0**。
2. 确证错误结果（具体操作序列或客观静态反例）→ 至少 P1；竞态覆盖、泄漏、无限循环、核心流程不可完成 → **P0**。
3. 验证组合已选 `regression` 且相对可比起点变差 → P1。
4. 其余有证据的问题 → `default_severity`，不得超过该条 `max_severity`。

无证据不得判 P0。`evidence_ids` 必须指向文件与行号、锚点或证据 ID。

## 全局禁止

- 不评论文风与排版。
- 后启动的格不得读取其他格的 Finding。

各格自己的禁止项写在对应 `ROLE.md` 的「全局禁止」，此处不复述。
