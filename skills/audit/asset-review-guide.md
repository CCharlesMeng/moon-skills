# 项目资产审计指南

这份文档用于指导 `audit` 如何审查 `.project-context` 下的项目资产。

目标不是把所有资产越审越多，而是让资产保持：

- 可信
- 精简
- 可追溯
- 可维护

## 审计对象

默认审计对象：

- `profile.yaml`
- `references.yaml`
- `features/index.yaml`
- `PROFILE.md`
- `immune-registry.yaml`
- `immune-candidates.yaml`
- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`

## 1. `profile.yaml`

重点检查：

- 模块路径是否仍然存在
- 模块边界是否仍与代码一致
- `critical_flows` 是否仍然有意义
- `generated_at` / `source_commit` / `confidence` 是否过期
- `uncertainty` 是否诚实，而不是假装全知

典型失败信号：

- 路径已经迁移，但模块 id 仍指向旧目录
- `critical_flows` 记录的是已经不存在的流转
- 几乎没有 `uncertainty`，但仓库明显复杂
- 所有模块都被机械标成高置信

常见治理动作：

- `update`
- `deprecate` 某些字段或条目
- 标记后续 `sync-context`

## 2. `references.yaml`

重点检查：

- 参考模式是否仍值得模仿
- `refs` 是否仍然存在且具有代表性
- `anti_examples` 是否仍然真的是反例
- `risk_hotspots` 是否仍然真实
- 是否出现大量空泛 summary、没有 ref 的“口号型模式”

典型失败信号：

- canonical example 已被重构为旧代码
- 共享模式和当前项目主流写法已经脱节
- 反例区域已经修复，却还被长期标成反例
- `reference_patterns` 开始变成全量组件清单

常见治理动作：

- `update`
- `merge`
- `deprecate`

## 3. `features/index.yaml`

重点检查：

- 是否仍然只保留关键 feature
- `code_refs` / `test_refs` 是否仍然有效
- spec / acceptance refs 是否真实存在
- 是否把目录、页面、组件名机械当成 feature
- 是否出现重复或过细分条目

典型失败信号：

- 每个页面都被登记成 feature
- feature 与代码、测试没有真实关联
- 同一个 feature 有多个重复 id
- 多数 feature 没有任何 `code_refs`

常见治理动作：

- `update`
- `merge`
- `deprecate`
- 标记需要后续 `sync-context`

## 4. `PROFILE.md`

重点检查：

- 是否仍和机器索引一致
- 是否仍能帮助维护者快速审查
- 是否膨胀为过期的架构散文

典型失败信号：

- 和 `profile.yaml` / `references.yaml` 已不一致
- 介绍很长，但没有未知项和风险提示
- 看起来完整，实际上不能指导后续任务

常见治理动作：

- `update`
- 压缩内容，回归摘要定位

## 5. `immune-registry.yaml`

重点检查：

- active 资产是否仍有价值
- 范围是否仍然正确
- 是否与其他资产重复
- 是否缺少来源追溯
- 是否长期无人复核

典型失败信号：

- active 资产已经不适配当前仓库
- 同一问题模式被多条规则覆盖
- 大范围规则证据很弱

常见治理动作：

- `keep`
- `merge`
- `deprecate`
- `update`

## 6. `immune-candidates.yaml`

重点检查：

- 候选是否长期停在 `draft`
- 证据是否已经足够提升
- scope 是否已清晰
- 是否与正式资产重复

典型失败信号：

- 大量候选永远不流转
- 候选和正式资产重复
- 明明需要 reject，却长期观察不决

常见治理动作：

- `promote`
- `merge`
- `reject`
- `update`

## 7. `context-check.yml`

重点检查：

- 工作流路径是否仍然正确
- 是否仍使用正确脚本位置
- 触发时机是否匹配当前团队节奏
- 是否出现大量误报或漏报

典型失败信号：

- 工作流指向不存在的脚本
- 只改 `.project-context/**` 仍会反复触发
- 团队已经频繁绕过或忽略这个 check

常见治理动作：

- `update`
- 调整触发条件和说明文字

## 8. `impact-rules.yaml`

重点检查：

- 规则是否仍匹配当前目录结构
- 是否缺少共享组件、测试入口、路由骨架等关键路径
- 是否存在太宽泛的 glob 导致误报

典型失败信号：

- 新的共享目录不在规则里
- 普通局部改动总被误判为 `structure`
- 重要的 feature / reference 变更却经常漏报

常见治理动作：

- `update`
- 收窄或扩展 path globs

## 高优先级失败信号

如果出现以下情况，应优先审计：

- 代码结构已经变化，但 `.project-context` 长时间没变
- `references.yaml` 中的 canonical example 已失效
- `features/index.yaml` 开始变成机械登记清单
- active immune 资产与现有仓库现实冲突
- candidate 资产长期堆积
- GitHub context-check 被频繁误报或频繁绕过

## 推荐审计顺序

建议按这个顺序走：

1. `profile.yaml`
2. `references.yaml`
3. `features/index.yaml`
4. `PROFILE.md`
5. `immune-registry.yaml`
6. `immune-candidates.yaml`
7. `context-check.yml`
8. `impact-rules.yaml`

原因：

- 先看上下文骨架是否还可信
- 再看共享模式和特性索引是否还有效
- 最后再看免疫资产和自动化规则是否需要治理

## 一句判断标准

如果一个资产已经不能帮助“下一个 AI 任务更快开始”，或者已经开始误导维护者，它就需要被更新、压缩或退场。
