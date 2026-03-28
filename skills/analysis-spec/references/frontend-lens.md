# 前端检查清单

适用信号：需求涉及 UI、交互、布局、客户端体验。

## 检查项

在 Phase D 中逐项回答：

- [ ] 用户可见状态是否完整（loading / empty / error / permission / success / stale / retry / partial）
- [ ] 关键交互行为是否明确（hover / active / disabled / focus、表单提交、去抖、防重入）
- [ ] 弹窗 / 抽屉 / 浮层 / toast 交互闭环是否完整
- [ ] 目标断点与移动端布局是否可用
- [ ] 深色模式、缩放、长文案是否需要考虑
- [ ] 键盘可操作性、focus 顺序、语义标签、ARIA
- [ ] 是否存在需要跨视图保活的重状态组件（销毁 vs 隐藏的决策是否明确）
- [ ] 状态是否需要与 URL 同步（深链、分享、回退）
- [ ] 是否存在大数据量渲染场景或昂贵计算需要特殊处理
- [ ] 富文本或用户生成内容是否存在注入风险（XSS / sanitize）
- [ ] 新增 / 变更的 analytics 事件
- [ ] 关键失败路径的日志 / 监控信号
- [ ] 是否有明显 bundle 膨胀或渲染性能风险
- [ ] 与设计稿 / 设计系统的一致性

## 定制

要修改本检查清单，复制本文件到 `.project-context/lenses/frontend.md` 并编辑。同名文件仓库版本优先于 skill 默认。不要直接修改本文件（skill 更新会覆盖）。

要新建检查清单，参考 [lens-template.md](lens-template.md)。
