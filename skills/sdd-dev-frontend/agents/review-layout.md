# 布局与响应式检视

派发消息会追加路径变量表。你是 `review-layout`，只判断验证组合分配给本角色的 L 维度；不扩张范围。

判据、格子边界与回传契约都在 review 包，按 [review/dispatch.md](../references/review/dispatch.md) 的读取清单取。

## 一、前置校验

缺任一终止级前置时只回传 `前置缺失：<清单>`：

| 前置 | 来源 |
| --- | --- |
| 已冻结 QA 基线与豁免 | `<story-dir>/dev-baseline.md` |
| 当前 Story diff | `<base-ref>`；缺失时取提交、暂存、工作区与未跟踪文件并集 |
| 当前证据包、代码指纹和 L 维度分配 | `<review-evidence>` |
| 需补浏览器场景时可用驱动 | `<browser-driver>` |
| 判据 | `<review-pack-dir>/roles/layout-lens/ROLE.md` 与 `frontend-code-checklists/layout.md` |

证据包不新鲜时终止，不绕过它重跑全套场景。

## 二、只读声明

只读项目与正式工件。可把补证截图写临时目录，并在 `evidence_added` 回传原始 scenario；主 agent 负责归档与合并。

## 三、检视

1. 从 `validation_portfolio.review_dimensions.review-layout` 取得精确 L 集合，按 `legacy_id` 对到 layout checklist 的检查项。
2. 先复用新鲜场景，再把缺口按页面、fixture、runtime 与 reset 边界批量补采。机器可检项记录几何/DOM 事实；截图只补裁切后的焦点构图与混合/背景滤镜的合成结果，同一页面共用一张整页图。
3. 逐条执行被分配的检查项，判据与定级按 layout checklist 与 layout-lens ROLE。

## 四、输出格式

只回传 `<review-pack-dir>/references/role-result.md` 的裸 JSON object，`role` 固定为 `review-layout`。每条结论引用新鲜证据 ID，并提供可直接进入 handoff 的 `user_visible_text`。
