# sdd-dev 调用 review 包

检查项、格子边界、定级与输出契约都在 `<review-pack-dir>`；本 Skill 不留副本。本文件只写两侧的接线。

`<review-pack-dir>` = `<skill-dir>/../sdd-review-frontend/`

## 派格登记

包不规定哪个调用方派哪几格，由调用方自己登记。本 Skill 的登记是：

| 何时 | 派出的格子 | 由谁决定 |
| --- | --- | --- |
| Phase C | 从 CODE-RESTORE / CODE-LAYOUT / CODE-CONVENTION / CODE-QUALITY / CODE-TEST 中选 | [validation-policy.md](./validation-policy.md) 的验证组合 |

派发请求里的 `gate` 固定填 `sdd-dev`。未被组合选中的格不派、不生成占位结果。

## 角色映射

| 本 Skill 角色 | lens | ROLE + checklist | 维度 |
| --- | --- | --- | --- |
| `review-restore` | restore-lens | [ROLE](../../sdd-review-frontend/roles/restore-lens/ROLE.md) · [restore.md](../../sdd-review-frontend/frontend-code-checklists/restore.md) | R1–R6 |
| `review-layout` | layout-lens | [ROLE](../../sdd-review-frontend/roles/layout-lens/ROLE.md) · [layout.md](../../sdd-review-frontend/frontend-code-checklists/layout.md) | L1–L6 |
| `review-convention` | convention-lens | [ROLE](../../sdd-review-frontend/roles/convention-lens/ROLE.md) · [convention.md](../../sdd-review-frontend/frontend-code-checklists/convention.md) | C1–C7 |
| `review-quality` | quality-lens | [ROLE](../../sdd-review-frontend/roles/quality-lens/ROLE.md) · [quality.md](../../sdd-review-frontend/frontend-code-checklists/quality.md) | Q1–Q8 |
| `self-test` | test-lens | [ROLE](../../sdd-review-frontend/roles/test-lens/ROLE.md) · [self-test.md](../../sdd-review-frontend/frontend-code-checklists/self-test.md) | 分配的 `F*-n` / `REG-n` |

维度号是 checklist 每条的 `legacy_id`，`validation_portfolio.review_dimensions` 与回传 JSON 都用它。哪些维度进入分配集由 [validation-policy.md](./validation-policy.md) 决定；触发条件写在 checklist 每条的 `skip_when`。

**还原格分两半。** 比对由本 Skill 的 `verify_restore_contract.py` 做（见 [restore-contract.md](./restore-contract.md)），它产出的是**颜色**；`review-restore` 只把颜色翻成**级别**与处置——同一个 `red`，关键区块缺失与数量越界不是同一件事。

主 agent 在派发前按最终 diff 用 `--phase green` 重跑全部已冻结区块的契约，报告写到 `<story-dir>/restore-report-review.json`，子代理只读它。Phase B 的 `render` 只跑当前区块，所以后续 Task 改了公共样式时，先前区块的 GREEN 只在这里才会被推翻。

## 派发时给子代理的读取清单

1. 按 [review-request.md](./review-request.md) 组装请求：格子、维度分配、交付件路径与约束层。
2. 角色提示词（`agents/<角色>.md`）与路径变量取值表。
3. 上表对应的 `ROLE.md` 与 checklist 全文——判据以它们为准。
4. [review-evidence.md](./review-evidence.md)：共享证据包与新鲜度。
5. `<review-pack-dir>/references/role-result.md`：回传契约与两档 `level` 映射。
6. convention / quality 需要识别栈内表现且 `PATTERN-*` 未覆盖时，读 `<review-pack-dir>/references/stack-signals.md` 的对应小节。

`role` 字段用本 Skill 角色名，不用 lens id；其余字段按包内契约。级别不由请求下发——需要某条在本 Story 更严重时，把它写进冻结声明。
