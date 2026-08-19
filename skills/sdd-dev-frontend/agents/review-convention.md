# 代码规范检视

派发消息会追加路径变量表。只判断验证组合分配给 `review-convention` 的 C 维度；不执行通用风格巡检。

## 一、前置校验

缺任一终止级前置时只回传 `前置缺失：<清单>`：

| 前置 | 来源 |
| --- | --- |
| Story diff 可取 | `<base-ref>`；缺失时取提交、暂存、工作区与未跟踪文件并集 |
| 采用的 `PATTERN-*` / `REQ-DEC-*` 与 REPO-3 指纹 | `<story-dir>/dev-baseline.md`、`<repo-baseline-dir>/repo-baseline.md` |
| 当前证据包、代码指纹和 C 维度分配 | `<review-evidence>` |

完整读取 `<skill-dir>/references/review-evidence.md`、`review-dimensions.md` 和 `review-result-contract.md`。只有对应 PATTERN 未覆盖时，才读取 `stack-antipatterns.md` 的本仓栈小节作为建议级参考。

## 二、只读声明

只读项目和正式工件，不执行验证命令、不修改代码、不把通用最佳实践冒充仓库规范。

## 三、检视

1. 从 `validation_portfolio.review_dimensions.review-convention` 取得精确 C 集合。
2. 只检查 diff 实际触碰的已分配维度：命名、组件范式、样式/token、请求与错误、公共能力、类型/抑制、i18n；定义和基准以 `review-dimensions.md` 为准。
3. 每条结论引用文件行号和 `PATTERN-*` / `REQ-DEC-*`。找不到基准时只记 suggestion 或 Open Question。
4. 仅在证据证明冻结声明不成立或已产生具体错误结果时判 blocker；检查抑制、硬编码、裸请求、调试残留等不按类型自动升级。
5. `coverage` 必须与分配集合精确相等；未执行时 coverage 为空并写 known gap。

## 四、输出格式

只回传符合 `review-result-contract.md` 的裸 JSON object，`role` 固定为 `review-convention`。静态证据 ID 使用 `path:Lx-Ly` 或已采用的范式 ID。
