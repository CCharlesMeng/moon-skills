# sdd-dev 调用 review 包

检查项、格子边界、定级与输出契约都在 `<review-pack-dir>`；本 Skill 不留副本。本文件只写两侧的接线。

`<review-pack-dir>` = `<skill-dir>/../sdd-review-frontend/`

## 角色映射

| 本 Skill 角色 | lens | ROLE + checklist | 维度 |
| --- | --- | --- | --- |
| `review-layout` | layout-lens | [ROLE](../../sdd-review-frontend/roles/layout-lens/ROLE.md) · [layout.md](../../sdd-review-frontend/frontend-code-checklists/layout.md) | L1–L6 |
| `review-convention` | convention-lens | [ROLE](../../sdd-review-frontend/roles/convention-lens/ROLE.md) · [convention.md](../../sdd-review-frontend/frontend-code-checklists/convention.md) | C1–C7 |
| `review-quality` | quality-lens | [ROLE](../../sdd-review-frontend/roles/quality-lens/ROLE.md) · [quality.md](../../sdd-review-frontend/frontend-code-checklists/quality.md) | Q1–Q8 |
| `self-test` | test-lens | [ROLE](../../sdd-review-frontend/roles/test-lens/ROLE.md) · [self-test.md](../../sdd-review-frontend/frontend-code-checklists/self-test.md) | 分配的 `F*-n` / `REG-n` |

维度号是 checklist 每条的 `legacy_id`，`validation_portfolio.review_dimensions` 与回传 JSON 都用它。哪些维度进入分配集由 [validation-policy.md](./validation-policy.md) 决定；触发条件写在 checklist 每条的 `skip_when`。

**还原不走 Phase C 角色。** `restore-lens` 是同一套 R1–R6 的判断卡；本 Skill 的执行器仍是 Phase B 的 `verify_restore_contract.py` 与 [restore-contract.md](./restore-contract.md)。不要给 `manage_review_pipeline.py` 增加第五个 role。

## 派发时给子代理的读取清单

1. 角色提示词（`agents/<角色>.md`）与路径变量取值表。
2. 上表对应的 `ROLE.md` 与 checklist 全文——判据以它们为准。
3. [review-evidence.md](./review-evidence.md)：共享证据包与新鲜度。
4. `<review-pack-dir>/references/role-result.md`：回传契约与两档 `level` 映射。
5. convention / quality 需要识别栈内表现且 `PATTERN-*` 未覆盖时，读 `<review-pack-dir>/references/stack-signals.md` 的对应小节。

`role` 字段用本 Skill 角色名，不用 lens id；其余字段按包内契约。
