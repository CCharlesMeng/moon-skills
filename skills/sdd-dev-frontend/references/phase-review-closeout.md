# Phase C / D 细则 — 候选验证与逐声明收口

本文件是 [SKILL.md](../SKILL.md) 工作流的组成部分。进入 Phase C 时完整读取 [声明驱动的验证策略](./validation-policy.md)、[共享证据契约](./review-evidence.md) 与本文件；有独立检视时再读 [结构化检视结果契约](./review-result-contract.md) 和 [检视维度](./review-dimensions.md)。

---

### Phase C — 候选验证

#### 1. 重编译验证组合

主 agent 先确认全部 Task 的实现 checkbox 已完成，且每条被改变的验收声明已有 Phase B 因果证据或未证原因。然后用最终 diff、仓库 baseline、运行限制与执行中暴露的信号重编译验证组合：

1. 取初始 `risk_triggers`；
2. 按最终 diff 补 `shared-boundary`、`auth`、`write`、`async-state`、`new-pattern`、`unknown-deps`、`build-config` 等实际触发器；
3. 为每条声明重算 `modules`；
4. 得到 0–4 个 `review_roles`，并为每个角色编译 `review_dimensions`；
5. 把同一结构写入 `dev-baseline.md / 验证组合（最终）` 与 `review-evidence.json / validation_portfolio`。

初始触发器被实测否定时可删除，但必须记录反证；新触发器只能扩展组合。最终 diff 超出 Task 文件范围且不是机械连带修改时，按 P7 上报，不自行扩大验收内容。

若重编译后首次出现浏览器相关模块，先按 SKILL.md 的浏览器驱动三档解析并实测；取不到就把该模块记为未执行、依赖声明记 `UNVERIFIED`，不为无关模块回退 Phase -1。

#### 2. 批量执行证据模块

按组合执行，不存在的模块不运行、不生成空记录：

| 模块 | 动作 |
| --- | --- |
| `targeted-quality` | 跑覆盖改动依赖闭包的最窄 test/typecheck/lint/build；能复用新鲜证据就引用 |
| `regression` | 跑风险闭包的入口与下游消费者；依赖闭包不可靠或仓库无安全收窄入口时升级 REPO-2 全量门 |
| `render` | 核 Phase B 契约证据新鲜度，只重采失效规则；额外状态/视口在同页面与 fixture 连接内合并 |
| `journey` | 把受影响 AC 的最短真实操作序列合并成场景；自动化因果证据已充分覆盖的声明不重复点击 |

命令结果与场景原始事实写入 `review-evidence.json`。同一次动作可被多个声明和检视角色引用；原始证据不保存通过/失败判断。

若命令有 DEMAND-2 起点失败集合，比较“相同或更好”；没有起点时只能记录当前结果，不声称“未回归”。某模块做得到但未执行时，把依赖声明标 `UNVERIFIED`，继续处理其他模块。

#### 3. 派发适用检视

只派 `validation_portfolio.review_roles` 中的角色：

| 角色 | 触发规则 |
| --- | --- |
| `review-layout` | 见 validation-policy 的 `review-layout` 模块 |
| `review-convention` | 见 `review-convention` 模块 |
| `review-quality` | 见 `review-quality` 模块 |
| `self-test` | 见 `self-test` 模块 |

未列角色不是“未执行”，不生成 `not_applicable` 占位。列入组合的角色只独立判断 `review_dimensions` 分配的维度；独立的是判断，不是原始证据采集。

按可用槽位动态补位：冻结一个 `evidence_epoch` 与候选代码状态，立即填满可用槽位；任一结果通过预校验后启动下一份。后启动角色只收到更新后的原始证据包，不收到其他角色的判断。

#### 4. 前置缺失与卡死

适用角色返回前置缺失、两次卡死或两次格式不合格时：

- 记录角色、原因和它负责的声明；
- 把这些声明标 `UNVERIFIED`；
- 继续执行其余角色与模块；
- 在 `review-results.json / known_gaps`、`dev-review.md` 与最终状态限定中披露。

不为了凑齐角色伪造 coverage，也不让一个角色失败拖掉无关声明。

#### 5. 证据补采与截图

角色发现证据缺口时先收齐同页面、fixture、runtime 与 reset 边界内的全部缺口，再批量补采；相同新鲜度键已有事实时直接复用。代码或 runtime 变化时结束当前证据纪元。

角色只可把截图写入临时目录。主 agent 仅归档被 finding、Open Question 或 Deferred 候选引用的截图到 `<story-dir>/evidence/review/`，并在聚合前把临时路径改写为正式路径。缺失的阻断证据使该 finding 无法确证：退回补证，仍缺则改为 Open Question/建议级或把对应声明记 `UNVERIFIED`，不得保留无证据阻断。

#### 6. 结构化聚合

每份适用角色结果通过 schema、角色、`evidence_epoch`、代码状态与证据 ID 校验后聚合。聚合器以 `review-evidence.json / validation_portfolio` 为期望集合：0 个角色合法；1–4 个角色中，`executed` 结果必须与分配维度精确匹配，`unexecuted` 结果必须留空 coverage 并写 known gap；未触发角色不得补空 JSON。

```bash
python3 "<skill-dir>/scripts/manage_review_pipeline.py" aggregate \
  [--result "<临时目录>/<适用角色>.json" ...] \
  --review-evidence "<review-evidence>" \
  --output-json "<story-dir>/review-results.json" \
  --output-markdown "<story-dir>/dev-review.md"
```

聚合器机械去重、取高、生成 Handoff；主 agent 不手抄长报告。零角色或零发现都走 fast path，只保留验证组合、声明状态、实际覆盖与收口占位。

#### 7. 逐声明初判

把 Phase B 因果证据、Phase C 模块证据与适用检视结论映射回每条声明：

- 覆盖充分且新鲜、无确证阻断 → `PROVEN`；
- 本阶段做得到但证据不足/模块未执行 → `UNVERIFIED`；
- 外部依赖未就绪 → `DEFERRED`；
- 有确证阻断 → 保持 `UNVERIFIED`，进入 Phase D 修复。

写入 `alpha-tests.md`，不以 Story 级总体通过覆盖逐声明状态。

---

### Phase D — 收口

#### 1. 阻断级修复

只修影响验收声明的确证阻断。建议级默认交付，不在收口时顺手改码。每条阻断必须有可复现操作或客观静态证据，并映射到受影响声明。

修复不出本 Story 实际 diff 范围；需要扩大范围时按 P7 上报。禁止用检查抑制或无理由类型断言绕过。同一报错连续修 3 次不成就停止。

#### 2. 修完重跑

一轮修复后重新计算风险触发器与依赖交集：

- 只失效依赖命中的命令、场景、检视判断与声明；
- 新增触发器时加入相应模块；
- 没有失效依据的模块不重跑；
- 修复来源角色若仍适用，必须复跑确认；
- 修复—重跑最多两轮，之后仍有阻断则进第 3 节。

不固定“样式就跑两份、逻辑就跑三份”的映射；实际依赖和风险触发器是唯一重跑依据。

#### 3. 待用户输入项按 P7 上报

把同一时刻的范围扩张、修不掉阻断、Open Question 与真正需要用户决定的 `Deferred` 候选合并一轮。每条写明受影响声明、现有证据、需要的决定和建议。

上报后可以交付“部分验收”索引，但不得把相关声明改成 `PROVEN`。用户回答会改变冻结期望时回 Phase A 确认门；只补事实时回 Phase C 对应模块。

#### 4. `DEFERRED` 判定

| 情形 | 状态 |
| --- | --- |
| 接口、权限账号、外部数据或第三方能力未就绪，本阶段无法解除 | `DEFERRED`，写原因与解除条件 |
| 本阶段做得到只是没执行 | `UNVERIFIED` |
| 拿不准是否外部依赖 | Open Question，暂记 `UNVERIFIED` |

豁免是已确认允许差异，不替代 `UNVERIFIED` 或 `DEFERRED`。

#### 5. 落账

一次批量更新：

- `alpha-tests.md`：逐声明状态、证据 ID、未证原因/解除条件；
- `review-evidence.json`：最终验证组合、命令与仍新鲜场景；
- `review-results.json`：适用角色聚合、known gaps 与 Handoff 计数；
- `dev-review.md`：给人的摘要、验证组合、阻断清零、`UNVERIFIED` / `DEFERRED` 清单、Handoff；
- `dev-baseline.md`：经确认的基线变更；
- 可选 telemetry：只在本次开启时汇总。

不重读未变化的大文件，不生成未触发模块的空表。

#### 6. 出门

逐条核对 [退出门禁](../SKILL.md#退出门禁)。所有 `PROVEN` 声明满足诚信门后即可输出交付索引；存在 `UNVERIFIED` / `DEFERRED` 时第一行必须写“交付/部分验收”状态限定，并把每条补验方式带进 Handoff。清单非空时只输出三行仍是门禁失败。
