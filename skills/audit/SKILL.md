---
name: 审计项目资产
description: 用于周期性审查 `.project-context` 下的仓库上下文、共享参考模式、关键特性索引、免疫资产和 GitHub context-check 配置，确保资产保持可信、精简且可维护。
---

# 审计项目资产

## 概述

这个 skill 用于审查 `.project-context/` 下的项目资产，确保系统持续学习，但不会变得嘈杂、过期、失真或自相矛盾。

这是一个治理型 skill。它负责审查和清理资产层，而不是处理新的线上事故或普通开发任务。

它审查的对象包括：

- `profile.yaml`
- `references.yaml`
- `features/index.yaml`
- `PROFILE.md`
- `immune-registry.yaml`
- `immune-candidates.yaml`
- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`

## 硬门禁

1. **不要盲审。** 做判断前必须先读取当前资产和相关代码证据。
2. **不要追求资产数量。** 资产越多不代表越好，可信、精简、可解释才更好。
3. **不要把过期资产继续当真。** freshness、confidence、uncertainty 失真时必须明确记录。
4. **不要用弱证据提升广域防护。** 范围或置信度不清晰时，应继续留在候选区。
5. **不要留下不可追溯资产。** 每条资产都必须能向维护者解释来源、理由和当前价值。

## 何时使用

适用场景：

- 周期性项目资产审计
- 清理过期或低价值 context 资产
- 审查共享参考模式是否仍然可信
- 审查关键特性索引是否仍然有用
- 审查候选免疫资产是否应提升、拒绝或继续观察
- 检查 GitHub context-check 规则是否还匹配当前仓库结构
- 在大规模 AI 接入或多轮变更后做一次治理复核

不适用场景：

- 正在处理新的 bug、回归或线上事故
- 第一次初始化仓库上下文
- 只是做一次局部变更后的增量同步

请使用：

- `immune-debug` 处理事故
- `initialize` 首次建档
- `sync-context` 做上下文增量维护

## 工作流

### Phase 0：读取资产层

读取当前：

- `.project-context/profile.yaml`
- `.project-context/references.yaml`
- `.project-context/features/index.yaml`
- `.project-context/PROFILE.md`
- `.project-context/immune-registry.yaml`
- `.project-context/immune-candidates.yaml`

如果存在，也检查：

- `.project-context/assets/`
- `.project-context/candidates/`
- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`

优先使用脚本和确定性检查，不要只靠印象审计。

### Phase 1：审查上下文资产

对 `profile.yaml`、`references.yaml`、`features/index.yaml`、`PROFILE.md` 逐项检查：

- 是否仍与当前仓库结构一致
- 是否仍能帮助后续任务快速定位
- 是否存在明显过期、缺失或重复信息
- confidence / uncertainty 是否诚实
- 人类摘要是否仍和机器索引一致

重点问题包括：

- `profile.yaml` 是否还反映真实模块边界与关键 flow
- `references.yaml` 里的共享模式是否仍值得模仿
- `features/index.yaml` 是否只保留关键而不是机械登记全部页面
- `PROFILE.md` 是否变成了过期散文

### Phase 2：审查免疫资产

对正式区和候选区逐项检查：

- 范围是否仍然正确
- 证据是否仍然成立
- 资产是否仍有价值
- 是否与更强或更新的资产重叠
- 是否应保持激活、合并、弃用、拒绝或提升

### Phase 3：审查自动化规则

重点检查 GitHub context-check 是否仍然可信：

- `impact-rules.yaml` 是否仍匹配当前目录结构
- `context-check.yml` 是否仍指向正确脚本与路径
- 是否存在误报过多或漏报过多的信号
- 是否需要调整为更保守或更严格的检查

### Phase 4：做最小有效治理动作

优先做最小但有效的治理动作：

- 保持不变
- 更新元数据或 refs
- 合并重复项
- 提升候选
- 弃用正式资产
- 拒绝候选
- 标记某类资产需要后续 `sync-context`

## 审查结果类型

允许的结果：

- `keep`
- `update`
- `merge`
- `promote`
- `deprecate`
- `reject`

只有在证据、范围和收益都足够强时，才允许 `promote`。

## 审查重点

优先审这三类问题：

1. **上下文漂移**
   - 代码已经变了，但 `profile` / `references` / `features` 没跟上
2. **模式失真**
   - 旧的 canonical example 已不再值得模仿
3. **资产噪音**
   - 低价值、重复、长期无人使用或长期无人复核的资产

详细检查项见 [asset-review-guide.md](asset-review-guide.md)。

## 最终输出

结束时必须包含：

### Audit Summary

- 审查了哪些资产
- 最高风险发现
- 最重要的漂移、重叠或失真

### Context Decisions

- 保持不变的 context 资产
- 需要更新的 context 资产
- 需要后续 `sync-context` 的区域

### Immune Decisions

- 保持不变的 immune 资产
- 提升的资产
- 合并的资产
- 弃用的资产
- 拒绝的资产

### Follow-Up

- 需要人工复核的高风险项
- 需要调整的 context-check 规则
- 需要未来继续补全的区域
