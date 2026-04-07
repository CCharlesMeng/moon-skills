---
name: audit
description: 用于周期性审查 `.project-context` 下的仓库上下文、共享参考模式、关键特性索引、免疫资产和 GitHub context-check 配置，并在每轮交付后做一次 post-ship reflect，确保资产保持可信、精简且可维护。
---

# 审计项目资产

## 概述

这个 skill 用于审查 `.project-context/` 下的项目资产，确保系统持续学习，但不会变得嘈杂、过期、失真或自相矛盾。

这是一个治理型 skill。它既负责周期性清理资产层，也是当前默认的 post-ship reflect 入口：在一轮交付结束后，用本轮证据回看 context drift、可复用模式、长期防护机会和下轮压力。

它负责先做判断和路由，而不是处理新的线上事故，也不替代 `sync-context` 去批量改写上下文正文。

它审查的对象包括：

- `profile.yaml`
- `references.yaml`
- `features/index.yaml`
- `PROFILE.md`
- `immune-registry.yaml`
- `immune-candidates.yaml`
- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`

## 交互规范

遵守 [Skill-User 交互黄金原则](../../PRINCIPLES.md)。

| Phase | 用户可见内容 | 结束方式 |
| --- | --- | --- |
| 0 — 读取 | 内联进 Phase 0.5，不单独输出（P6） | — |
| 0.5 — 新鲜度预检 | 内联进 Phase 1 的资产状态表，衰减条目单独标注（P6） | — |
| 1 — 上下文资产审查 | 资产状态表（keep / update / deprecate / …） | 无确认门 |
| 2 — 免疫资产审查 | 内联进 Phase 1 的资产状态表（P6） | — |
| 3 — Post-ship reflect | Reflect 摘要表（事实 / learnings / 路由决策） | 无确认门 |
| 4 — 自动化规则审查 | 仅在发现 impact-rules 失效时单独输出（P6） | — |
| 5 — 治理动作 | 内联进 Phase 1/3 的状态表，操作后直接写入文件 | — |
| 最终 | 三行索引（P5） | — |

---

## 硬门禁

1. **不要盲审。** 做判断前必须先读取当前资产和相关代码证据。
2. **不要追求资产数量。** 资产越多不代表越好，可信、精简、可解释才更好。
3. **不要把过期资产继续当真。** freshness、confidence、uncertainty 失真时必须明确记录。
4. **不要用弱证据提升广域防护。** 范围或置信度不清晰时，应继续留在候选区。
5. **不要留下不可追溯资产。** 每条资产都必须能向维护者解释来源、理由和当前价值。

## 何时使用

适用场景：

- 周期性项目资产审计
- 完成一轮功能、修复或发布后的 post-ship reflect
- 清理过期或低价值 context 资产
- 审查共享参考模式是否仍然可信
- 审查关键特性索引是否仍然有用
- 审查候选免疫资产是否应提升、拒绝或继续观察
- 判断本轮交付是否应更新 `references.yaml`、`features/index.yaml` 或 `PROFILE.md`
- 判断本轮 learnings 是否值得沉淀为 immune 资产
- 检查 GitHub context-check 规则是否还匹配当前仓库结构
- 在大规模 AI 接入或多轮变更后做一次治理复核

不适用场景：

- 正在处理新的 bug、回归或线上事故
- 一轮交付尚未结束，只是临时记录零散观察
- 第一次初始化仓库上下文
- 只是做一次局部变更后的增量同步
- 已经明确要写回 context，且不需要先做治理判断

请使用：

- `immune-debug` 处理事故
- `initialize` 首次建档
- `sync-context` 做上下文增量维护

## 工作流

### Phase 0：读取资产层与交付证据

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

如果这次是 post-ship reflect，也要读取本轮确定性证据：

- 本轮 diff 或改动文件
- 本轮测试、验证或发布结果
- 本轮文档、spec 或 README 变化
- `.project-context` 资产在本轮的变化
- 如存在，PR 描述、release note 或任务摘要

优先使用脚本和确定性检查，不要只靠印象审计或回忆复盘。

### Phase 0.5：Periodic Freshness Check（新鲜度预检）

在开始资产审查之前，先对 `immune-registry.yaml` 做自动化新鲜度预检。

1. 扫描所有条目的 `last_checked_at` 字段（缺失时按向后兼容策略处理，见 [immune-registry-schema.md](../immune-debug/references/immune-registry-schema.md)）
2. 按衰减阶梯自动降级：
   - `last_checked_at` 距今 > 90 天，当前 `confidence: high` → 降至 `medium`，在 `governance_tags` 中打上 `needs-review`
   - `last_checked_at` 距今 > 180 天，或当前已是 `medium` 且距今 > 90 天 → 降至 `low`，打上 `needs-review`
   - 项目休眠修正：如果相关代码区域（通过 `scope` 和 `defensive_rule_id` 定位）近 90 天内无改动，阈值放宽至 180 / 360 天
3. 将衰减结果就地写入 `immune-registry.yaml`（更新 `confidence` 和 `governance_tags`）
4. 记录所有被衰减的条目，供 Phase 2 和 Phase 3 使用

衰减基于 `last_checked_at`（是否仍在被使用），不基于 `last_triggered_at`（是否阳性命中），避免高质量规则因人人遵守而被降级。

### Phase 1：审查上下文资产

对 `profile.yaml`、`references.yaml`、`features/index.yaml`、`PROFILE.md` 逐项检查：

- 是否仍与当前仓库结构一致
- 是否仍能帮助后续任务快速定位
- 是否存在明显过期、缺失或重复信息
- confidence / uncertainty 是否诚实
- 人类摘要是否仍和机器索引一致
- 本轮交付是否暴露了新的共享模式、反例或风险热点
- 本轮交付是否说明当前 context 已不足以支撑下一轮任务

重点问题包括：

- `profile.yaml` 是否还反映真实模块边界与关键 flow
- `profile.yaml → uncertainty[]` 中标记为 `[possibly-resolved]` 的条目是否确实已解决（已解决则正式移除，未解决则恢复原状）
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
- 本轮交付中的修复、规则或测试护栏是否已足够稳定，值得纳入长期防护

### Phase 3：提炼 post-ship reflect

只基于已经发生的交付事实做复盘，不写空泛感想。

重点抽取：

- 本轮最值得复用的模式或反例
- 最重要的 context drift
- 最可能转化为长期防护的结论
- 下轮最值得盯住的风险、盲区或待验证点
- Phase 0.5 中被标记 `needs-review` 的免疫条目（在 `reflect.md` 的"长期防护机会"章节中列出，提示技术负责人决定保留、更新或移除）

在这一阶段必须先做判断和路由：

- 只是观察：留在 audit 输出
- 需要写回 context：路由给 `sync-context`
- 需要长期防护：进入 immune 正式区或候选区

### Phase 4：审查自动化规则

重点检查 GitHub context-check 是否仍然可信：

- `impact-rules.yaml` 是否仍匹配当前目录结构
- `context-check.yml` 是否仍指向正确脚本与路径
- 是否存在误报过多或漏报过多的信号
- 是否需要调整为更保守或更严格的检查

### Phase 5：做最小有效治理动作

优先做最小但有效的治理动作：

- 保持不变
- 更新元数据或引用字段
- 合并重复项
- 提升候选
- 弃用正式资产
- 拒绝候选
- 标记某类资产需要后续 `sync-context`
- 标记某类结论只保留在 reflect 输出，不做持久化写回

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

详细检查项见 [references/asset-review-guide.md](references/asset-review-guide.md)。

## 最终输出

```
✓ audit 完成
产出：docs/specs/<topic>/reflect.md（post-ship）/ 资产已就地更新（治理审计）
下一步：[已路由 sync-context（如有 context 更新） / 已路由 immune（如有防护决策） / 无后续动作]
```
