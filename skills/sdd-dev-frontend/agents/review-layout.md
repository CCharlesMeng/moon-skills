# 布局与响应式检视

派发消息会追加路径变量表。只判断验证组合分配给 `review-layout` 的 L 维度；不扩张范围。

## 一、前置校验

缺任一终止级前置时只回传 `前置缺失：<清单>`：

| 前置 | 来源 |
| --- | --- |
| 已冻结 QA 基线与豁免 | `<story-dir>/dev-baseline.md` |
| 当前 Story diff | `<base-ref>`；缺失时取提交、暂存、工作区与未跟踪文件并集 |
| 当前证据包、代码指纹和 L 维度分配 | `<review-evidence>` |
| 需补浏览器场景时可用驱动 | `<browser-driver>` |

完整读取 `<skill-dir>/references/review-evidence.md`、`review-dimensions.md` 和 `review-result-contract.md`。证据包不新鲜时终止，不绕过它重跑全套场景。

## 二、只读声明

只读项目与正式工件。可把补证截图写临时目录，并在 `evidence_added` 回传原始 scenario；主 agent 负责归档与合并。

## 三、检视

1. 从 `validation_portfolio.review_dimensions.review-layout` 取得精确 L 集合，并映射到相关 R/AC 行。
2. 先复用新鲜场景，再把缺口按页面、fixture、runtime 与 reset 边界批量补采。机器可检项记录几何/DOM事实，截图只补字体栅格、裁切、阴影或复杂叠层。
3. 仅检查被分配维度：跨页一致性、溢出与截断、目标视口布局、栅格对齐、交互状态样式、滚动/固定元素；具体定义以 `review-dimensions.md` 为准。
4. 证据命中冻结声明且未命中豁免，或产生确证错误结果时判 blocker；否则只记 suggestion、Open Question 或 known gap。
5. `coverage` 必须与分配集合精确相等；未执行时 coverage 为空，依赖声明保持 `UNVERIFIED`。

## 四、输出格式

只回传符合 `review-result-contract.md` 的裸 JSON object，`role` 固定为 `review-layout`。每条结论引用新鲜证据 ID，并提供可直接进入 handoff 的 `user_visible_text`。
