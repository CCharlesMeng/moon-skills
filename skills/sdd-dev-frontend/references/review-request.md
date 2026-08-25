# 检视请求契约

派发一格检视时，主 agent 交给子代理的**参数包**。它是「非默认约束」的唯一入口：判据默认值在 `<review-pack-dir>`，本契约只传本 Story 特有的事实。

派发消息仍只含路径与取值表，不复制项目正文。

## 形状

```json
{
  "schema_version": 1,
  "gate": "sdd-dev",
  "cell": "CODE-LAYOUT",
  "role": "review-layout",
  "role_card": "<review-pack-dir>/roles/layout-lens/ROLE.md",
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

## 字段

| 字段 | 谁定 | 语义 |
| --- | --- | --- |
| `gate` | 本 Skill | 固定 `sdd-dev`；包不枚举 gate，见[派格登记](./review-pack-adapter.md) |
| `cell` / `role` | 本 Skill | 本次那一格与回填进 `RoleResult` 的角色标识 |
| `role_card` / `checklist` / `output_schema` | 包 | 三条路径，子代理据此取全部判据 |
| `assigned_dimensions` | 本 Skill | 由[验证组合](./validation-policy.md)算出；它是 `coverage` 与 `skipped` 的全集 |
| `evidence_epoch` / `code_fingerprint` | 本 Skill | 新鲜度键，见 [review-evidence.md](./review-evidence.md) |
| `review_object` / `anchors` | 本 Skill | 被评审对象与定位锚点 |
| `deliverables` | 本 Skill | 该格 `ROLE.md` 的 `reads` 所需层，逐层给路径 |
| `constraints` | 本 Skill | 下节 |

## 约束层

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

## 校验

`<skill-dir>/scripts/manage_review_pipeline.py` 在聚合时核对：回传的 `role` 与请求一致，`coverage` 加 `skipped` 恰好等于 `assigned_dimensions`。不一致按回传不合格退回一次。
