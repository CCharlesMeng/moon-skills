# Phase C / D：候选验证与收口

进入 Phase C 时读取 [review/evidence.md](../review/evidence.md) 和本文件；只有组合触发独立检视时再读 [review/dispatch.md](../review/dispatch.md) 及它指向的判据与回传契约。验证组合由脚本复编译，不通读 [validation-policy.md](../validation-policy.md)。

## Phase C — 候选验证

1. 先跑 `classify_diff.py` 取最终 diff 的机械事实写 `<work-dir>/diff-facts.json`，再跑 `compile_portfolio.py --phase final --previous <evidence-dir>/portfolio.json --out <evidence-dir>/portfolio.json`（命令见 [validation-policy.md 第二节](../validation-policy.md#二编译)）；同一文件原地覆盖，Phase 0 的快照留在 `previous` 字段。脚本复判[执行档位](../execution-contract.md#执行档位)与组合，只允许升；退出码 3 说明结果比 Phase 0 还少，先查输入再重跑，不得手工调低。升为 `standard` 时补齐 Phase A2 被省掉的勘察产物。实现期读代码发现的判断型触发器用 `--trigger` 传入，要收窄某条 diff 下限用 `--narrow` 署名。`--markdown` 输出更新 `dev-baseline.md`，JSON 写入 `review-evidence.json / validation_portfolio`。
2. 计算证据新鲜度，先复用有效命令和 scenario，再执行真正缺失的已选模块。质量命令先于浏览器采集；同页面/fixture/runtime/reset 边界批量执行。
3. 首次新增浏览器模块时解析并实测 `<browser-driver>`；不可用则模块记未执行，依赖声明保持 `UNVERIFIED`。
4. 组合含 `restore-final` 时，把当前 `code_fingerprint` 与 `alpha-tests.md` 对应 GREEN 行记录的完整 `code=<sha256>` 比较（该值取自 GREEN 时 `review-evidence.json / code.code_fingerprint`）：未变才复用 `<evidence-dir>/restore-report-green.json`；缺值或变化则按最终 diff 重跑**全部已冻结区块**并覆盖该文件。聚合器直接把三色按维度映射为级别，不派还原检视角色。
5. 只派 `review_roles` 中其余角色，给同一 evidence epoch 和原始证据包；后启动角色不得收到先完成角色的判断。
6. 角色前置缺失或回传不合格时只退回一次；仍失败则生成 `unexecuted` 结果与 known gap，不伪造 coverage。
7. 若角色补采场景，先校验 raw scenario，再由主 agent 合并进证据包。子代理的截图先落 `<work-dir>`，只有被结论引用的才搬进 `<evidence-dir>/artifacts/` 并把 scenario 的 `artifacts[]` 指到新位置；其余随 `<work-dir>` 一起删。
8. 把同页面、同设备、同账号边界的待人工验收项合并成最短人工操作序列，写回 `alpha-tests.md` 的人工验收记录；这是人工项的权威登记。
9. 用 `<skill-dir>/scripts/manage_review_pipeline.py aggregate` 校验、聚合 `<work-dir>` 里 0–4 份适用的 RoleResult JSON，并在 `restore-final` 被选中时读取同目录 GREEN 报告，生成 `<evidence-dir>/review-results.json` 和 `<story-dir>/acceptance.md`。带第 1 步的 `--diff-facts`，再传 `--alpha-tests <story-dir>/alpha-tests.md --tasks <story-dir>/tasks.md`。同 `canonical_key` 合并取高级别，冲突时回原始证据消歧。**`acceptance.md` 是整文件覆盖的，任何内容都必须经由参数进来，不手写。**
10. 逐声明初判，判据用 [共享执行契约的状态表](../execution-contract.md#声明与状态)。待人工验收项保持 `UNVERIFIED`，不当作 Open Question 或 Deferred。

## Phase D — 收口

1. 只修确证 blocker，且未清零的 blocker 只把它命中的声明保持 `UNVERIFIED`，不牵连无关声明。建议级进入 handoff，不在当前 Story 自动修，也不因此扩大命令、浏览器矩阵或检视重跑；Open Question 和 Deferred 候选按 P7 批量上报。**上报要在对话里问成可回答的问题**（每条给可选项与后果），拿到答复后按 `aggregate --decisions` 重渲染，把答复与时间就地记回 `acceptance.md` 的对应条目——只报不问会让同一件事下一轮重复出现。
2. 修复后按 `depends_on` 失效命中的命令、场景与声明，按 `judged_files` 失效命中的角色判断，再按实际 diff 重编译组合。出现新风险才扩展；否则精确重跑。
3. 同一 blocker 连续三次修复失败、需要越界改动或会改变冻结期望时停下请求决策。改变期望回 Phase A 重新确认；只补事实则回对应 Phase C 模块。
4. 更新 `alpha-tests.md`、`review-evidence.json`、`review-results.json` 与 `acceptance.md`。Handoff 条数与最终 P8 输出逐类一致。
5. 收到真实人工验收结果后，先把 `manual_outcome`、`manual_checked_by`、`manual_checked_at` 与 `evidence_refs` 回填 `alpha-tests.md`，再重跑 `aggregate --alpha-tests`。`PASSED` 且证据齐全才进 `PROVEN`；`PASSED` 但证据不足保留人工判断并登记缺失证据；`FAILED` 保持 `UNVERIFIED` 并形成确证阻断。agent 不得代签，`--decisions` 也不能把人工声明改成 `PROVEN`。
6. 逐条核对 SKILL.md 的退出门禁。存在 `UNVERIFIED` / `DEFERRED` 时可交付“部分验收”，但必须带状态限定和补验/解除方式；存在待人工验收项时不写无条件“可验收”。
7. 退出门禁全部通过后整目录删除 `<work-dir>`。里面只有过程件（static/render 采集结果、diff 事实、RoleResult、未被引用的截图），每一份都已并入 `<evidence-dir>` 的正式工件或可重算；门禁没过就不删，续跑还要用。

退出：每条声明状态唯一且诚实；确证阻断与依赖失效已收口；所有遗留项可操作且已对账；`<work-dir>` 已清。

## 解除 DEFERRED

`DEFERRED` 是唯一在 Story 收口后仍会变化的状态。没有专门入口时它会永久沉淀——Story 已经交付，没人会为了几条接缝声明重走一遍 Phase A/B。所以这是一条独立的、只碰证据的短路径：

1. **入口条件**：用户说明某个外部依赖已就绪（后端部署到测试环境、测试租户开通、可回滚数据就位），或续跑时 `alpha-tests.md` Deferred 表非空且解除条件可核。只处理 Deferred 表里的声明，不重开 Phase A/B，不改 `tasks.md`、不改冻结基线。
2. **核解除条件**：逐行看 Deferred 表的「解除条件」是否成立。不成立的原样留下，不猜。
3. **只编译受影响模块**：从 `review-evidence.json / validation_portfolio.claims` 取这些声明的 `modules` 与 `required_profile`，只执行它们（通常是 `story` + `self-test`，`write` 类再加 `regression`）。先跑 `classify_diff.py`（重建 `<work-dir>`）确认前端代码相对上次收口没有变化；变了就不是解除 DEFERRED，回 Phase C 完整复编译。
4. **按所需档取证**：`live` 档要真实后端、真实身份、可重复且写后可清理的数据（入口见 app baseline `runtime.md` 的「服务与身份」节）；`contract` 档对照仓内正式契约并把契约文件加进 `depends_on`。scenario 的 `profile` 记实际档。写操作没有 sandbox 或回滚手段时不跑，留 `DEFERRED` 并把缺口写进解除条件。
5. **回填**：`alpha-tests.md` 对应行改状态、填「执行环境」，从 Deferred 表删掉已解除的行；`actual_profile` 仍低于 `required_profile` 的不得写 `PROVEN`。
6. **重聚合**：`aggregate --alpha-tests --tasks` 重渲染 `acceptance.md`，首句从「前端已验证，N 条真实接缝待…」变为「可验收」或剩余项的表述。最终三行照常输出，再删 `<work-dir>`。

不接受的做法：用 mock 场景「顺便」把 `DEFERRED` 改成 `PROVEN`；为了解除一条声明重跑全量门；把解除不了的声明改成 `UNVERIFIED` 让它从暂缓表消失。
