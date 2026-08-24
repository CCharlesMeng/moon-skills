# Phase C / D：候选验证与收口

进入 Phase C 时读取 [validation-policy.md](./validation-policy.md)、[review-evidence.md](./review-evidence.md) 和本文件；只有组合触发独立检视时再读 [review-pack-adapter.md](./review-pack-adapter.md) 及它指向的判据与回传契约。

## Phase C — 候选验证

1. 先用 `classify_diff.py` 取最终 diff 的机械事实，再从初始风险、仓库事实、运行限制和已有证据重编译验证组合；下限与收窄规则见 [validation-policy.md](./validation-policy.md#三风险触发器)。结构同时写入 `dev-baseline.md` 与 `review-evidence.json / validation_portfolio`。
2. 计算证据新鲜度，先复用有效命令和 scenario，再执行真正缺失的已选模块。质量命令先于浏览器采集；同页面/fixture/runtime/reset 边界批量执行。
3. 首次新增浏览器模块时解析并实测 `<browser-driver>`；不可用则模块记未执行，依赖声明保持 `UNVERIFIED`。
4. 组合含 `review-restore` 时，先按最终 diff 用 `--phase green` 重跑**全部已冻结区块**的还原契约，报告写 `<story-dir>/restore-report-review.json`。冻结区块跨页面时按页面各注入一次、`--render-results` 重复传，否则其他页面的规则会以「定位不到」冒充实现偏差。Phase B 只跑过当前变更区块，先前区块的 GREEN 在这里才会被最终 diff 推翻。
5. 只派 `review_roles` 中角色，给同一 evidence epoch 和原始证据包；后启动角色不得收到先完成角色的判断。
6. 角色前置缺失或回传不合格时只退回一次；仍失败则生成 `unexecuted` 结果与 known gap，不伪造 coverage。
7. 若角色补采场景，先校验 raw scenario，再由主 agent 合并进证据包。只归档被结论引用的截图。
8. 用 `<skill-dir>/scripts/manage_review_pipeline.py` 校验、聚合 0–5 份适用 JSON，生成 `review-results.json` 和 `dev-review.md`；`aggregate` 需带第 1 步的 `--diff-facts`。同 `canonical_key` 合并取高级别，保留所有证据与来源编号；冲突时回原始证据消歧，不猜测。
9. 逐声明初判，判据用 [共享执行契约的状态表](../../../docs/skills/frontend-sdd/执行契约.md#声明与状态)。

## Phase D — 收口

1. 只修确证 blocker，且未清零的 blocker 只把它命中的声明保持 `UNVERIFIED`，不牵连无关声明。建议级进入 handoff，不在当前 Story 自动修，也不因此扩大命令、浏览器矩阵或检视重跑；Open Question 和 Deferred 候选按 P7 批量上报。
2. 修复后按 `depends_on` 失效命中的命令、场景与声明，按 `judged_files` 失效命中的角色判断，再按实际 diff 重编译组合。出现新风险才扩展；否则精确重跑。
3. 同一 blocker 连续三次修复失败、需要越界改动或会改变冻结期望时停下请求决策。改变期望回 Phase A 重新确认；只补事实则回对应 Phase C 模块。
4. 更新 `alpha-tests.md`、`review-evidence.json`、`review-results.json` 与 `dev-review.md`。Handoff 条数与最终 P8 输出逐类一致。
5. 逐条核对 SKILL.md 的退出门禁。存在 `UNVERIFIED` / `DEFERRED` 时可交付“部分验收”，但必须带状态限定和补验/解除方式。

退出：每条声明状态唯一且诚实；确证阻断与依赖失效已收口；所有遗留项可操作且已对账。
