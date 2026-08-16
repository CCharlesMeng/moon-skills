# Phase C 结构化检视结果契约

四份检视的**判断仍由四个独立角色完成**。本契约只把回传从重复的长 Markdown 改成可校验 JSON，供主 agent 机械合并；它不共享判断，也不替角色裁定级别。

## 一、唯一输出

检视角色完整读取本文件后，只回传一个 JSON object；不得包 Markdown fence、寒暄、过程说明或第二份报告。主 agent 把四份正文分别保存为临时 JSON，再运行 `scripts/manage_review_pipeline.py aggregate` 生成 `dev-review.md`。

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

`status` 只有 `executed`、`not_applicable`、`unexecuted`。后两者必须在 `known_gaps` 写明原因，且不得伪造 coverage 或 finding。

## 二、覆盖与发现

- `review-layout` 必须覆盖 `L1`–`L6`；`review-convention` 必须覆盖 `C1`–`C7`；`review-quality` 必须覆盖 `Q1`–`Q8`。
- `self-test` 的 `dimension` 使用冻结基线的真实行号（如 `F2-1`、`REG-2`），且 F1–F4 / REG 每个存在的行都必须出现；不得把多行折成一个笼统结论。
- `coverage.result` 只有 `clear`、`finding`、`unrun`。`finding` 必须能在 `findings`、`open_questions` 或 `deferred_candidates` 追到对应条目；`unrun` 必须在 `known_gaps` 说明。
- `findings.level` 只有 `blocker`、`suggestion`。编号沿用角色维度编号，不另造全局编号。
- `canonical_key` 描述同一个可观察问题的稳定身份，不含角色名或级别。两个角色报同一问题时必须给相同 key；同 key 的现象、定位或用户可见文本冲突时，聚合器拒绝猜测，由主 agent 回到原始证据消歧。
- `open_questions` 每项必含 `id`、`canonical_key`、`summary`、`user_visible_text`、`needs_decision`、`evidence_ids`。
- `deferred_candidates` 每项必含 `id`、`canonical_key`、`ac`、`reason`、`resume_condition`、`user_visible_text`、`evidence_ids`。

## 三、证据边界

- `evidence_reused` 列实际复用的 `BE-n` / `quality_gate`；`evidence_added` 保存本角色为缺口补采的完整原始 scenario object（没有则空数组），由主 agent 验证后并回共享包。scenario 内仍不得含判断字段。
- 共享 `review-evidence.json` 只保存原始事实；本 JSON 才保存角色判断。不得把 finding、通过/不通过或级别写回共享证据包。
- 每条 finding / OQ / Deferred 候选都必须引用足以复核的 `evidence_ids`。静态检视可引用 `path:Lx-Ly`、`PATTERN-*`、`REQ-DEC-*`；浏览器检视优先引用新鲜 `BE-n`，不复制步骤和观察全文。
- 主 agent 不手抄四份报告。单份返回时先预校验；若有 `evidence_added`，用 `merge-additions` 只合并 raw scenario 并改写该份临时 JSON，随后才能把更新后的共享证据交给补位角色。`aggregate` 再校验四份的 `evidence_epoch`、`code_fingerprint`、角色和覆盖完整性后生成 Markdown；失败就退回缺失角色，不带缺口收口。

## 四、独立性

后启动的角色只能收到同一纪元的原始证据包，不能收到先完成角色的结果 JSON。主 agent 只可把先完成角色补采的**原始事实**合并进证据包。结构化输出减少传输和文书成本，不改变规范检视与质量检视必须由不同角色独立判断的规则。
