# 功能自测试

派发消息会追加路径变量表。只判断验证组合分配给 `self-test` 的 F/REG 声明；不自行补分类或扩大用户旅程。

## 一、前置校验

缺任一终止级前置时只回传 `前置缺失：<清单>`：

| 前置 | 来源 |
| --- | --- |
| 已冻结 F/AC 声明与豁免 | `<story-dir>/dev-baseline.md`、`tasks.md`、`alpha-tests.md` |
| 当前证据包、代码指纹和 F/REG 分配 | `<review-evidence>` |
| 需补浏览器场景时可用驱动 | `<browser-driver>` |

完整读取 `<skill-dir>/references/review-evidence.md`、`review-dimensions.md` 和 `review-result-contract.md`。证据包不新鲜时终止，不绕过它重跑全套场景或命令。

## 二、只读声明

只读项目与正式工件。可把补证截图写临时目录，并在 `evidence_added` 回传无判断的原始 scenario；主 agent 负责合并。

## 三、检视

1. 从 `validation_portfolio.review_dimensions.self-test` 取得精确 F/REG 集合。
2. 先复用新鲜场景与已选命令，再把缺口按页面、fixture、runtime 与 reset 边界批量补采。
3. F1 核测试层级映射，F2 核可观察结果，F3 只跑已冻结的异常/边界，F4 只核受影响接口契约；REG 只比较验证组合明确选中的风险闭包。
4. 证据证明声明不成立或产生确证错误结果时判 blocker；外部依赖未就绪写 Deferred 候选；跑不了或证据不足写 known gap，使声明保持 `UNVERIFIED`。
5. `coverage` 必须与分配集合精确相等；没有可比起点时不得声称“无回归”。

## 四、输出格式

只回传符合 `review-result-contract.md` 的裸 JSON object，`role` 固定为 `self-test`。每条结论引用新鲜证据 ID，并提供可直接进入 handoff 的 `user_visible_text`。
