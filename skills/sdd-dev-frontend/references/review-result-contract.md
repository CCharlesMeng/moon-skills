# Phase C 结构化检视结果契约

验证组合触发的检视由对应角色独立完成。本契约把 0–4 份适用结果变成可校验 JSON；未触发角色不派发、不生成占位结果。

## 一、唯一输出

检视角色完整读取本文件后，只回传一个 JSON object；不得包 Markdown fence、寒暄、过程说明或第二份报告。主 agent 保存适用角色结果，再运行聚合器生成 `dev-review.md`。

```json
{
  "schema_version": 1,
  "role": "review-layout",
  "evidence_epoch": "review-1",
  "code_fingerprint": "<sha256>",
  "status": "executed",
  "coverage": [
    {
      "dimension": "L1",
      "scope": "<页面 / 视口 / diff 或基线行范围>",
      "evidence_ids": ["BE-1"],
      "result": "clear"
    }
  ],
  "findings": [
    {
      "id": "L3-1",
      "canonical_key": "route:/detail|viewport:720|horizontal-overflow",
      "dimension": "L3",
      "level": "blocker",
      "summary": "<可观察现象>",
      "location": "<页面 / 路由 / 视口，或文件与行号>",
      "basis": "<冻结基线、仓内范式或量化后果>",
      "evidence_ids": ["BE-2"],
      "user_visible_text": "<现象 + 影响 + 建议动作>"
    }
  ],
  "open_questions": [],
  "deferred_candidates": [],
  "evidence_reused": ["BE-1"],
  "evidence_added": [],
  "known_gaps": []
}
```

新流程只为触发角色生成 `executed` 或 `unexecuted` 结果；`not_applicable` 仅为旧工件兼容。`unexecuted` 必须说明 known gap，coverage、finding 与 `evidence_reused/evidence_added` 都必须为空，不得伪造执行痕迹。

## 二、覆盖与发现

- `status=executed` 时，每个角色的 `coverage.dimension` 集合必须恰好等于 `validation_portfolio.review_dimensions.<role>`。未分配的 L/C/Q 分类不生成 coverage。
- `self-test` 的 `dimension` 使用验证组合分配的冻结基线行号（如 `F2-1`、`REG-2`）；执行成功时同样必须精确匹配。
- `status=unexecuted` 时 coverage 必须为空，以 `known_gaps` 解释未执行原因；组合中原分配的维度保留用于把依赖声明标为 `UNVERIFIED`，不得为通过结构校验伪造 coverage。
- `coverage.result` 只有 `clear`、`finding`、`unrun`。`finding` 必须能在 `findings`、`open_questions` 或 `deferred_candidates` 追到对应条目；`unrun` 必须在 `known_gaps` 说明。
- `findings.level` 只有 `blocker`、`suggestion`。编号沿用角色维度编号，不另造全局编号。
- `canonical_key` 描述同一个可观察问题的稳定身份，不含角色名或级别。两个角色报同一问题时必须给相同 key；同 key 的现象、定位或用户可见文本冲突时，聚合器拒绝猜测，由主 agent 回到原始证据消歧。
- `open_questions` 每项必含 `id`、`canonical_key`、`summary`、`user_visible_text`、`needs_decision`、`evidence_ids`。
- `deferred_candidates` 每项必含 `id`、`canonical_key`、`ac`、`reason`、`resume_condition`、`user_visible_text`、`evidence_ids`。

## 三、证据边界

- `evidence_reused` 列实际复用的 `BE-n` / `quality_gate`；`evidence_added` 保存本角色为缺口补采的完整原始 scenario object（没有则空数组），由主 agent 验证后并回共享包。scenario 内仍不得含判断字段。
- 共享 `review-evidence.json` 只保存原始事实；本 JSON 才保存角色判断。不得把 finding、通过/不通过或级别写回共享证据包。
- 每条 finding / OQ / Deferred 候选都必须引用足以复核的 `evidence_ids`。静态检视可引用 `path:Lx-Ly`、`PATTERN-*`、`REQ-DEC-*`；浏览器检视优先引用新鲜 `BE-n`，不复制步骤和观察全文。
- 主 agent 不手抄报告。单份返回时先预校验；若有 `evidence_added`，只合并 raw scenario。`aggregate` 按 `validation_portfolio.review_roles` 与 `review_dimensions` 校验角色集合、纪元、代码状态与覆盖后生成 Markdown。

## 四、独立性

后启动角色只能收到同一纪元的原始证据包，不能收到先完成角色的结果 JSON。两个角色都被触发时仍分别判断；未触发时不为形式独立强行派发。
