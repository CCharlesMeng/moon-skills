# dashboard-sdd 人工验收样例

这个目录是一组可演示的 Story 产物，用来说明 `manual_acceptance` 怎样交给真实人员验收。它不是已通过的验收记录，也不会预造截图、录屏或验收人。

阅读顺序：

1. 打开 `acceptance.md`，先看结论和「需要你处理」。
2. 按其中步骤打开 `demo.html` 完成人工验收。
3. 把真实结果回填到 `alpha-tests.md` 的「人工验收记录」。
4. 证据文件落到 `evidence/artifacts/` 后，再运行聚合脚本重写 `acceptance.md` 与 `evidence/review-results.json`。

当前有两项待验收：

- `AT-US1-001`：滚动与卡片展开动效是否自然，属于 `motion_judgment`。
- `AT-US1-002`：风险摘要文案是否符合业务表达，属于 `content_approval`。

初始状态均为 `manual_outcome=NOT_RUN`、`claim_status=UNVERIFIED`；`manual_checked_by`、`manual_checked_at`、`evidence_refs` 留空。只有实际执行验收的人可以填写这些字段。
