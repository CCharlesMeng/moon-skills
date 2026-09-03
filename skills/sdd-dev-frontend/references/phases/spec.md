# Phase A：规格与冻结基线

只在进入 Phase A 时读取。基线源语义来自 [共享执行契约](../execution-contract.md)，QA 声明形状来自 [qa-baseline.md](../templates/qa-baseline.md)。

## 勘察模式

执行档位为 `lite`（判据见[执行契约的执行档位](../execution-contract.md#执行档位)）时，规格侧与代码侧都由主 agent 自做：按 [agents/recon-spec.md](../../agents/recon-spec.md) 的产物形状直接生成适用的 F 表、已知缺口与豁免表，按下面的代码侧 `lite` 机械收集依据。不派子代理，产物形状与校验标准不变。

`standard` 档一律派 `recon-spec`；代码侧再分两种：`lite` 只在 Story 范围明确、采用规范均可按 ID 定位且其依据清单条目指路仍有效、无公共边界/新规范/未知依赖、无需参照页实测且没有冲突时使用，主 agent 机械收集相关路径、采用的 `PATTERN-*` / `REQ-DEC-*` 与证据。任一条件不满足即 `full`，派 `recon-codebase`；不得为了少派角色压低风险。

## Phase A1 — 规格抽取

仅 `baseline_source=prototype` 执行；其他档位跳过整段。

1. 用 `<skill-dir>/scripts/extract_design_spec.py` 生成或复用 `design-facts.json` 与 `design-inventory.md`。退出码 4 的每类覆盖缺口先登记，再显式确认后重跑；不直接绕过。
2. 按原型内容哈希判断复用；失配只更新受影响事实。主 agent 读取脚本切片头并直接生成 `block-index.md`，这是默认直通道。
3. 只有候选段需要跨段归并时派 `extract-prototype`。只有单区块切片超过 12k 字符或用户点名时，才对该区块派 `extract-block-spec`；其他区块由后续直接读取 `design-facts.json` 锚点事实。
4. 主 agent 不读原型正文。抽取角色只读所需切片；争议补证只回查单一区块并登记。

A1 完成后再派 `recon-spec`，因为它的期望来源是完整设计事实，而不是未完成切片。

退出：设计事实、区块索引、受影响区块规格和覆盖缺口对账齐全。

## Phase A2 — 勘察与确认

1. 按上节勘察模式取得规格侧与代码侧结果：`standard` 派 `recon-spec`，代码侧 `full` 时并行派 `recon-codebase`；执行档位 `lite` 或代码侧 `lite` 的部分由主 agent 提交机械结果。无原型档先完成代码侧，再把参照页事实或采用 token 交给规格侧。
2. 校验回传：范围、来源、适用 QA 行、豁免、已知缺口齐全，逐行符合 [qa-baseline.md](../templates/qa-baseline.md) 的填写规则；不合格只退回一次。
3. 合并到 `dev-baseline.md`：工程依据、功能理解、适用 QA 声明、已知缺口、摘要与指纹。Story 只保存采用的 PATTERN/REQ-DEC ID，不复制正文。
4. 对每个缺口按 QA 模板完成 `repo / prototype / user-only / conflict / 工作假设` 分类。只有 user-only/conflict 进入 P7；工作假设随确认门展示。
5. 确认门只展示用户需要判断的内容：做什么、标准来源、适用声明、豁免、工作假设和未决问题。用户确认后记录时间与摘要并冻结；指出修改则更新后重新确认。
6. 有还原声明时，把 `recon-spec` 回传的规则 JSON 通过 `contract --rules -` stdin 直接编译为 `<evidence-dir>/restore-contract.json`，实现 locator 单独写 `<evidence-dir>/restore-adapter.json`。无还原声明时不生成空契约。

退出：QA 基线已由用户确认，指纹已冻结，适用还原契约通过脚本校验。
