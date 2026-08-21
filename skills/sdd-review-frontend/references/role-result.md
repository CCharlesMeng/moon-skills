# RoleResult@v2

五格共用的唯一输出契约。调用方的聚合器现读本契约，线上字段名以本文件为准。

只回传一个 JSON object：不得包 Markdown fence、寒暄、过程说明或第二份报告。缺终止级前置时改为纯文本 `前置缺失：<清单>`。

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
      "basis": "<冻结基线、PATTERN-* 或量化后果>",
      "evidence_ids": ["BE-2"],
      "user_visible_text": "<现象 + 影响 + 建议动作>"
    }
  ],
  "skipped": [
    {
      "dimension": "L6",
      "reason": "<引用 skip_when 说明为什么不适用>"
    }
  ],
  "open_questions": [],
  "deferred_candidates": [],
  "evidence_reused": ["BE-1"],
  "evidence_added": [],
  "known_gaps": []
}
```

`schema_version` 恒为 `1`：`RoleResult@v2` 是契约名，`1` 是聚合器校验的线上版本号。

## 字段

- `role`：调用方在请求里给出的角色标识，原样回填。调用方没给时用 lens id。本包不规定它的取值。
- `dimension`：该检查项的 `legacy_id`（checklist 每条列出，如 `L1`、`C5`、`Q8`）。`self-test` 用分配的冻结基线行号（`F2-1`、`REG-2`）。coverage 与 findings 都用这个值，不写 kebab-case 检查项名。
- `level`：只有 `blocker`、`suggestion`。由 [SKILL.md 定级](../SKILL.md#定级) 的 P 级映射：P0 / P1 → `blocker`，P2 / P3 → `suggestion`。
- `status`：`executed` | `unexecuted`（`not_applicable` 仅为旧工件兼容）。
- `id`：维度加序号（`L3-1`、`C5-2`），不另造全局编号。同一份结果内不得重号。

## 覆盖与发现

- `status=executed` 时，`coverage` 与 `skipped` 的 `dimension` **合起来**必须恰好等于调用方分配的集合，且互不重叠。未分配的维度两边都不出现。
- `skipped` 记被分配、但命中 `skip_when` 的维度，每条必须带引用 `skip_when` 的 `reason`。它会落进 `dev-review.md` 的「判定不适用」节——「看过且不适用」与「漏判」「跑不了」是三件事，不要用它替代 `unrun`：能跑而没跑成的写 coverage `unrun` + `known_gaps`。
- `status=unexecuted` 时 coverage、skipped、findings、`evidence_reused` / `evidence_added` 全为空，只用 `known_gaps` 解释；原分配集由调用方用来把依赖声明标为未验证。不得为通过结构校验伪造 coverage。
- `coverage.result` 只有 `clear`、`finding`、`unrun`。`finding` 必须能在 `findings`、`open_questions` 或 `deferred_candidates` 追到对应条目；`unrun` 必须在 `known_gaps` 说明。
- `canonical_key` 描述同一个可观察问题的稳定身份，不含角色名或级别。两格报同一问题时必须给相同 key——那说明跨格了，删掉不属于本格的那条。同 key 的现象、定位或用户可见文本冲突时聚合器拒绝猜测，由调用方回到原始证据消歧。
- `open_questions` 每项必含 `id`、`canonical_key`、`summary`、`user_visible_text`、`needs_decision`、`evidence_ids`。
- `deferred_candidates` 每项必含 `id`、`canonical_key`、`ac`、`reason`、`resume_condition`、`user_visible_text`、`evidence_ids`。
- Finding 条数不得超过该格 `max_findings`；超了按严重度截断，余下进 `known_gaps`。

## 证据边界

- 每条 finding / OQ / Deferred 候选都必须引用足以复核的 `evidence_ids`。静态检视可引用 `path:Lx-Ly`、`PATTERN-*`、`REQ-DEC-*`；浏览器检视优先引用新鲜 `BE-n`，不复制步骤和观察全文。
- `evidence_reused` 列实际复用的 `BE-n` / `quality_gate`；`evidence_added` 保存本格为缺口补采的完整原始 scenario object（没有则空数组），由调用方验证后并回共享包。scenario 内不得含判断字段。
- 共享证据包只保存原始事实，本 JSON 才保存判断。不得把 finding、通过/不通过或级别写回共享证据包。

## 独立性

后启动的格只能收到同一纪元的原始证据包，不能收到先完成格的结果 JSON。多格都被选中时仍分别判断；未选中时不为形式独立强行派发。
