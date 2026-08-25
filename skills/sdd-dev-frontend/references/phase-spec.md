# Phase A：规格与冻结基线

只在进入 Phase A 时读取。基线源语义来自 [共享执行契约](./execution-contract.md)，QA 声明形状来自 [qa-baseline-template.md](./qa-baseline-template.md)。

## 代码侧勘察模式

`lite` 只在 Story 范围明确、采用规范均可按 ID 定位且其依据清单条目指路仍有效、无公共边界/新规范/未知依赖、无需参照页实测且没有冲突时使用。主 agent 机械收集相关路径、采用的 `PATTERN-*` / `REQ-DEC-*` 与证据。任一条件不满足即 `full`，派 `recon-codebase`；不得为了少派角色压低风险。

## Phase A1 — 规格抽取

仅 `baseline_source=prototype` 执行；其他档位跳过整段。

1. 用 `<skill-dir>/scripts/extract_design_spec.py` 生成或复用 `design-facts.json`、token、界面和内容清单。退出码 4 的每类覆盖缺口先登记，再显式确认后重跑；不直接绕过。
2. 按原型内容哈希判断复用。哈希一致的设计事实和区块规格保留；失配只更新受影响部分。
3. 根据脚本候选段选择分支：
   - 小稿且候选段已是职责单一区块：主 agent 只读切片头生成 `block-index.md`。
   - 需要归并或命名审订：派 `extract-prototype`。
4. 对新增或哈希失配区块派 `extract-block-spec`；一区块一份，正文严格匹配 `block-spec-template.md`。
5. 主 agent 不读原型正文。只有两个抽取角色可读；争议补证只回查单一区块并登记。

A1 完成后再派 `recon-spec`，因为它的期望来源是完整设计事实，而不是未完成切片。

退出：设计事实、区块索引、受影响区块规格和覆盖缺口对账齐全。

## Phase A2 — 勘察与确认

1. 派 `recon-spec`；代码侧 `full` 时并行派 `recon-codebase`，`lite` 时由主 agent提交机械结果。无原型档先完成代码侧，再把参照页事实或采用 token 交给规格侧。
2. 校验回传：范围、来源、适用 QA 行、豁免、已知缺口和自检齐全；不合格只退回一次。
3. 合并到 `dev-baseline.md`：工程依据、功能理解、适用 QA 声明、已知缺口、摘要与指纹。Story 只保存采用的 PATTERN/REQ-DEC ID，不复制正文。
4. 对每个缺口按 QA 模板完成 `repo / prototype / user-only / conflict / 工作假设` 分类。只有 user-only/conflict 进入 P7；工作假设随确认门展示。
5. 确认门只展示用户需要判断的内容：做什么、标准来源、适用声明、豁免、工作假设和未决问题。用户确认后记录时间与摘要并冻结；指出修改则更新后重新确认。
6. 有还原声明时，按 [restore-contract.md](./restore-contract.md) 从冻结 QA 行编译 `restore-contract.json`，实现 locator 单独写 `restore-adapter.json`。无还原声明时不生成空契约。

退出：QA 基线已由用户确认，指纹已冻结，适用还原契约通过脚本校验。
