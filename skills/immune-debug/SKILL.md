---
name: immune-debug
description: 用于调试 bug、回归、重复事故、测试失败或异常行为，并在修复后判断是否应沉淀为可复用工程防护资产。
---

# 免疫调试

## 概述

这个 skill 用于在调试结束后补上闭环：一旦问题已经被调查、修复并验证，你必须继续判断这次事故是否值得沉淀为可复用工程防护资产。

它处理的是 incident reflect，而不是一轮交付结束后的 sprint-level reflect。

这是一个刚性流程型 skill。

**必需基础 skill：** 使用 `superpowers:systematic-debugging` 负责根因调查、假设验证、修复实施和修复验证。

当 `.project-context/profile.yaml` 不存在时，使用 `initialize`。
当 repo 上下文存在但已过期或与证据冲突时，使用 `sync-context`。

## 硬门禁

1. **没有证据，不准修改。** 不允许基于猜测改代码。
2. **没有验证，不准宣布修复成功。** 在相关检查通过前，不得宣称问题已解决。
3. **没有免疫决策，不准结束流程。** 每次调试都必须输出明确的免疫决策，即使结论是 `无动作`。
4. **高影响规则不得直接扩散。** 影响范围大或不确定性高的防护资产，必须先进入候选区再考虑转正。

## 何时使用

适用场景：

- 测试失败
- 生产 bug
- 回归问题
- 重复性事故
- 运行时异常行为
- 集成失败
- 构建或发布异常
- 在大型或陌生代码库中排障

不适用场景：

- 没有故障信号的普通功能开发
- 与事故无关的常规重构
- 纯文档工作
- 没有 bug、失败或回归前提的试探性清理
- 没有事故，只是想回顾一轮交付

## 工作流

你必须按顺序完成每个阶段。

### Phase 0：加载上下文

开始调试前：

1. 先读取确定性的 repo 上下文：
   - `.project-context/profile.yaml`
   - `.project-context/references.yaml`
   - `.project-context/features/index.yaml`
   - `.project-context/immune-registry.yaml`
   - `.project-context/immune-candidates.yaml`
2. 如果仓库提供脚本或生成索引，优先使用它们，而不是自由推断。
3. 应用上下文时遵循：
   - `profile.yaml` 负责仓库边界、模块边界和关键 flow
   - `references.yaml` 负责共享参考模式、反例和风险热点
   - `features/index.yaml` 负责能力定位，以及 code / test / spec refs
   - 正式 immune 资产优先于候选 immune 资产
4. 在同一层级内，优先使用更窄范围的命中。
5. 候选 immune 资产只能作为弱参考，不能视为正式生效防护。
6. 直接证据覆盖所有已加载上下文。

如果 repo 上下文缺失、过期、含糊，或被直接证据否定：

- 以降级模式继续
- 用证据压过上下文
- 在结尾加入初始化或同步 repo 上下文的后续动作

### Phase 1：调试并验证

使用 `superpowers:systematic-debugging` 作为基础调试工作流。

当仓库提供脚本和 CI 检查时，优先依赖这些确定性能力，而不是只靠模型判断。

### Phase 2：写调试摘要

按下面的固定输出契约写摘要。

写法要求：

- `触发条件` 写复现条件，不写猜测
- `证据` 写观察到的事实，不写方案
- `根因` 写根因链路，不写“可能是”
- `修复动作` 写实际修复动作，不写备选方案
- `验证` 写实际执行过的验证，不写“理论上应该通过”

### Phase 3：做免疫决策

你必须判断这次事故是否应该生成或更新一个可复用防护资产。

规则：

1. 选择一个 `主决策`。
2. 允许选择 `无动作`，但必须给出理由。
3. 选择能有效预防复发的最小持久防护。
4. 广域、高风险或不确定防护必须先进候选区。

参考 [references/immune-decision-matrix.md](references/immune-decision-matrix.md)。

### Review Rules 追加

如果根因涉及代码规范问题（命名混乱、架构违反、已知反模式未防护），在免疫决策的同时将教训转化为防御级 review rule，追加到 `.project-context/review-rules/defensive.md`。

追加条件：

- 根因可以通过代码检视发现（不是纯运行时问题）
- 规则可复用（不是一次性的特定修复）
- 规则足够具体（不是"注意代码质量"这类空泛表述）

追加规则时：

- 使用 `DEF-R-N` 编号格式（N 在整个 `defensive.md` 内递增），确保跨层级唯一
- 填写 `immune_ref` 列，引用本次写入 `immune-registry.yaml` 的资产 `id`
- 将同一个 `DEF-R-N` 编号记录到 `immune-registry.yaml` 对应条目的 `defensive_rule_id` 字段

这些 rules 供 `code-review` 在后续开发中消费，防止同类问题复发。`code-review` 通过 `immune_ref` 和 `defensive_rule_id` 的双向关联，实现检视触发记录的自动反写。

## 与交付后 reflect 的边界

- 本 skill 的结构化复盘属于 incident reflect：围绕一次具体故障、修复和免疫决策收束
- 如果一次交付里出现了多个事故、多模块联动修复，或结论已经超出单次事故范围，应在交付结束后再用 `audit` 做一次 sprint-level reflect
- `immune-debug` 负责决定是否沉淀长期防护；`audit` 负责总结整轮交付的 reusable learnings、context drift 和 next sprint pressure

## 降级模式

如果 `.project-context/profile.yaml` 缺失或过期：

- 继续使用通用调试纪律
- 不得臆造领域确定性
- 在后续动作中加入初始化或同步仓库上下文

如果 `references.yaml` 或 `features/index.yaml` 缺失：

- 不要阻塞调试
- 优先依赖代码、测试和直接证据
- 在后续动作中指出上下文索引缺口

如果上下文与直接证据冲突：

- 相信证据
- 记录冲突
- 添加修正仓库上下文的后续工作

如果作用范围不清：

- 不要写广域正式防护
- 优先进入候选区，或选择 `无动作`

如果验证不完整：

- 不得声称修复成功
- 不得产出强防护资产

## 必须以这个固定结构结束

```markdown
## 调试摘要

触发条件:
- ...

证据:
- ...

根因:
- ...

修复动作:
- ...

验证:
- ...

## 免疫决策

主决策:
- 无动作 | 文档 | 提示词/规则 | 测试 | Lint/静态检查

决策理由:
- ...
- ...

附带动作:
- ...

作用范围:
- 模块 | 仓库 | 领域 | 技术栈 | 全局

路由:
- 正式区 | 候选区 | 无

置信度:
- 低 | 中 | 高

## 资产记录

added_at: <当前 ISO datetime>
last_checked_at: <同 added_at>
last_triggered_at: <同 added_at>
defensive_rule_id: <DEF-R-N | null>
governance_tags: []

## 后续动作
- 仓库上下文: initialize | sync-context | 无
- 资产写入: 正式区 | 候选区 | 无
- 人工复核: 是 | 否
```

如果这次事故只是某轮交付的一部分，且结论需要跨模块或跨问题汇总，完成本 skill 后应额外运行一次 `audit` 做交付后 reflect。

完整黄金输出见 [references/examples.md](references/examples.md)。
维护者验证见 [references/validation-scenarios.md](references/validation-scenarios.md)。
