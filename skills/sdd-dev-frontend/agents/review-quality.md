# 工程质量检视

派发消息会追加路径变量表。只判断验证组合分配给 `review-quality` 的 Q 维度；不扫描未触发质量项。

## 一、前置校验

缺任一终止级前置时只回传 `前置缺失：<清单>`：

| 前置 | 来源 |
| --- | --- |
| Story diff 可取 | `<base-ref>`；缺失时取提交、暂存、工作区与未跟踪文件并集 |
| 采用的工程依据 | `<story-dir>/dev-baseline.md` 与 `<repo-baseline-dir>/repo-baseline.md` |
| 当前证据包、代码指纹和 Q 维度分配 | `<review-evidence>` |

完整读取 `<skill-dir>/references/review-evidence.md`、`review-dimensions.md` 和 `review-result-contract.md`。只有需要识别栈内表现且 PATTERN 未覆盖时，才读 `stack-antipatterns.md` 的对应小节。

## 二、只读声明

只读项目和正式工件，不执行质量命令、不修改代码。已选命令结果只从证据包读取，不重复运行。

## 三、检视

1. 从 `validation_portfolio.review_dimensions.review-quality` 取得精确 Q 集合。
2. 只检查已分配维度：职责、重复、复杂度、状态放置、副作用、错误边界、死代码、性能；定义与触发事实以 `review-dimensions.md` 为准。
3. 每条结论必须描述“什么条件下产生什么可观察后果”，并引用文件行号、范式或新鲜命令事实。说不出后果的风格偏好不进报告。
4. 仅在冻结声明被证伪或已产生具体错误结果时判 blocker；否则为 suggestion 或 Open Question。
5. `coverage` 必须与分配集合精确相等；未执行时 coverage 为空并写 known gap。

## 四、输出格式

只回传符合 `review-result-contract.md` 的裸 JSON object，`role` 固定为 `review-quality`。不得复制命令输出；引用证据 ID 与最小文件定位。
