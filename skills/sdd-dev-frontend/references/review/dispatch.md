# 独立检视的派发

检查项、格子边界、定级与输出契约都在 `<review-pack-dir>`；本 Skill 不留副本。本文件只写两侧的接线：派哪几格、每格对应哪个角色，以及派一格时交给子代理的**参数包**。

`<review-pack-dir>` = `<skill-dir>/../sdd-review-frontend/`

## 一、派格登记

包不规定哪个调用方派哪几格，由调用方自己登记。本 Skill 的登记是：

| 何时 | 派出的格子 | 由谁决定 |
| --- | --- | --- |
| Phase C | 从 CODE-RESTORE / CODE-LAYOUT / CODE-CONVENTION / CODE-QUALITY / CODE-TEST 中选 | [validation-policy.md](../validation-policy.md) 的验证组合 |

派发请求里的 `gate` 固定填 `sdd-dev`。未被组合选中的格不派、不生成占位结果。

## 二、角色映射

| 本 Skill 角色 | lens | checklist | 维度 |
| --- | --- | --- | --- |
| `review-restore` | restore-lens | [restore.md](../../../sdd-review-frontend/frontend-code-checklists/restore.md) | R1–R6 |
| `review-layout` | layout-lens | [layout.md](../../../sdd-review-frontend/frontend-code-checklists/layout.md) | L1–L6 |
| `review-convention` | convention-lens | [convention.md](../../../sdd-review-frontend/frontend-code-checklists/convention.md) | C1–C7 |
| `review-quality` | quality-lens | [quality.md](../../../sdd-review-frontend/frontend-code-checklists/quality.md) | Q1–Q8 |
| `self-test` | test-lens | [self-test.md](../../../sdd-review-frontend/frontend-code-checklists/self-test.md) | 分配的 `F*-n` / `REG-n` |

维度号是 checklist 每条的 `legacy_id`，`validation_portfolio.review_dimensions` 与回传 JSON 都用它。哪些维度进入分配集由 [validation-policy.md](../validation-policy.md) 决定；触发条件写在 checklist 每条的 `skip_when`。

**还原格分两半。** 比对由本 Skill 的 `verify_restore_contract.py` 做（见 [restore/run.md](../restore/run.md)），它产出的是**颜色**；`review-restore` 只把颜色翻成**级别**与处置——同一个 `red`，关键区块缺失与数量越界不是同一件事。

主 agent 在派发前按最终 diff 用 `--phase green` 重跑全部已冻结区块的契约，报告写到 `<evidence-dir>/restore-report-review.json`，子代理只读它。Phase B 的 `render` 只跑当前区块，所以后续 Task 改了公共样式时，先前区块的 GREEN 只在这里才会被推翻。

## 三、派发时给子代理的读取清单

1. 按下节组装请求：格子、维度分配、交付件路径与约束层。
2. 角色提示词（`agents/<角色>.md`）与路径变量取值表。
3. 上表对应的 checklist 全文（含 YAML 头、格子边界与禁止）——判据以它为准。
4. [evidence.md](./evidence.md)：共享证据包与新鲜度。
5. `<review-pack-dir>/references/role-result.md`：回传契约与两档 `level` 映射。
6. convention / quality 需要识别栈内表现且 `PATTERN-*` 未覆盖时，读 `<review-pack-dir>/references/stack-signals.md` 的对应小节。

`role` 字段用本 Skill 角色名，不用 lens id；其余字段按包内契约。级别不由请求下发——需要某条在本 Story 更严重时，把它写进冻结声明。

## 四、请求形状

请求是「非默认约束」的唯一入口：判据默认值在 `<review-pack-dir>`，本契约只传本 Story 特有的事实。派发消息仍只含路径与取值表，不复制项目正文。

```json
{
  "schema_version": 1,
  "gate": "sdd-dev",
  "cell": "CODE-LAYOUT",
  "role": "review-layout",
  "checklist": "<review-pack-dir>/frontend-code-checklists/layout.md",
  "output_schema": "<review-pack-dir>/references/role-result.md",
  "assigned_dimensions": ["L2", "L3"],
  "evidence_epoch": "review-1",
  "code_fingerprint": "<sha256>",
  "review_object": "本 Story 最终 diff 覆盖的页面与组件",
  "anchors": ["/orders", "/orders/:id"],
  "deliverables": {
    "code_diff": "<base-ref>",
    "qa_baseline": "<story-dir>/dev-baseline.md",
    "browser_evidence": "<review-evidence>"
  },
  "constraints": {
    "frozen_claims": ["R5-1", "F3-2"],
    "exemptions": ["EX-1"],
    "risk_closure": ["/orders", "/orders/:id"],
    "required_states": ["overflow"],
    "start_failures": "<story-dir>/dev-baseline.md / 执行起点（环境）",
    "tolerance": {"css_px": 1}
  }
}
```

## 五、字段

| 字段 | 谁定 | 语义 |
| --- | --- | --- |
| `gate` | 本 Skill | 固定 `sdd-dev`；包不枚举 gate，见第一节 |
| `cell` / `role` | 本 Skill | 本次那一格与回填进 `RoleResult` 的角色标识 |
| `checklist` / `output_schema` | 包 | 两条路径，子代理据此取全部判据 |
| `assigned_dimensions` | 本 Skill | 由[验证组合](../validation-policy.md)算出；它是 `coverage` 与 `skipped` 的全集 |
| `evidence_epoch` / `code_fingerprint` | 本 Skill | 新鲜度键，见 [evidence.md](./evidence.md) |
| `review_object` / `anchors` | 本 Skill | 被评审对象与定位锚点 |
| `deliverables` | 本 Skill | 该格 checklist `inputs` 所需层，逐层给路径 |
| `constraints` | 本 Skill | 下节 |

## 六、约束层

`constraints` 是本契约存在的理由：它让包内的升级规则有事实可判，而**不改变**规则本身。

| 键 | 用途 | 缺省时 |
| --- | --- | --- |
| `frozen_claims` | 已冻结且与本格相关的 R/F/AC 行号 | 升级顺序第 1 条无从触发，按 `default_severity` 判 |
| `exemptions` | 已冻结 `EX-n` | 无豁免可命中 |
| `risk_closure` | 本次回归与跨页检查的范围 | REG 与跨页项按 `skip_when` 记 `skipped` |
| `required_states` | 声明要求的 overflow / long-copy / large-list 等状态 | 对应检查项按 `skip_when` 记 `skipped` |
| `start_failures` | `DEMAND-2` 起点失败集合 | 不得声称「无回归」，按 `unrun` 处理 |
| `tolerance` | 还原契约的容差 | 按包内与还原契约的默认容差 |

三条硬约束：

1. **请求只提供事实，不覆盖级别。** `normative_level` / `default_severity` / `max_severity` 只在包内 checklist，本契约没有对应字段；需要「这条在本 Story 更严重」时，正确做法是把它写进冻结声明，让升级顺序第 1 条自然生效。
2. **未给的约束按包内默认判**，不因缺字段就跳过整格。包可被独立调用，缺省必须是安全的。
3. **`assigned_dimensions` 之外的维度不出现在回传里**——既不在 `coverage`，也不在 `skipped`。`skipped` 只记被分配后才发现不适用的那些。

## 七、校验

`<skill-dir>/scripts/manage_review_pipeline.py` 在聚合时核对：回传的 `role` 与请求一致，`coverage` 加 `skipped` 恰好等于 `assigned_dimensions`。不一致按回传不合格退回一次。
