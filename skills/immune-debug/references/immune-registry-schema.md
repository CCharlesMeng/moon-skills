# immune-registry.yaml Schema 指南

`immune-registry.yaml` 是免疫防线的正式资产索引，记录所有经过验证、已转正的可复用防护资产。

它应该精简、可追溯、可治理。每条资产都必须能解释来源、理由和当前价值。

## 设计原则

- 每条资产必须有事故来源和决策理由，不接受无来源的规则
- 显式记录时间维度（创建时间、最后检视时间、最后触发时间），支持新鲜度衰减治理
- 防护范围宁窄勿广，范围不清时应留在候选区
- 允许被降级、合并或弃用，不要让过期资产继续看起来很可靠
- 与 `defensive.md` 的规则保持可追溯关联

## 建议结构

```yaml
version: 1
generated_at: 2026-03-17T00:00:00Z
source_commit: abc1234

assets:
  - id: guard-checkout-reentry
    title: 结账状态机重入保护
    decision_type: 测试
    scope: 仓库
    summary: 结账重算阶段的状态流转保护，防止同一轮结账重复进入冲突分支
    source_case: 2026-03-15 结账集成测试失败，根因是状态机缺少重算阶段的 guard
    confidence: high
    status: active
    added_at: 2026-03-15T00:00:00Z
    last_checked_at: 2026-03-17T00:00:00Z
    last_triggered_at: 2026-03-15T00:00:00Z
    defensive_rule_id: null
    governance_tags: []

  - id: no-bare-fetch-in-effect
    title: 禁止在 useEffect 中直接调用未包装的 fetch
    decision_type: 提示词/规则
    scope: 仓库
    summary: 历史 race condition 根因，要求所有 effect 内的请求使用包装过的 hook
    source_case: 2026-02-20 快速翻页导致旧页数据覆盖新页
    confidence: high
    status: active
    added_at: 2026-02-20T00:00:00Z
    last_checked_at: 2026-03-17T00:00:00Z
    last_triggered_at: 2026-02-20T00:00:00Z
    defensive_rule_id: DEF-R-1
    governance_tags: []
```

## 字段说明

### 核心字段（必填）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 唯一标识，使用 kebab-case |
| `title` | string | 人类可读的防护名称 |
| `decision_type` | enum | `文档` / `提示词/规则` / `测试` / `Lint/静态检查` |
| `scope` | enum | `模块` / `仓库` / `领域` / `技术栈` / `全局` |
| `summary` | string | 一句话说明防护内容和原因 |
| `source_case` | string | 来源事故的简要描述（日期 + 现象 + 根因） |
| `confidence` | enum | `high` / `medium` / `low` |
| `status` | enum | `active` / `deprecated` / `merged` |
| `added_at` | ISO datetime | 资产创建时间，immune-debug 写入时必填 |

### 时间治理字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `last_checked_at` | ISO datetime | 等于 `added_at` | 最后一次被纳入检视范围的时间。`code-review` 每次扫描 defensive rules 时更新此字段 |
| `last_triggered_at` | ISO datetime | 等于 `added_at` | 最后一次阳性命中时间（因该规则产生 blocking issue）。仅在 `code-review` 发现 blocking 时更新 |

### 关联字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `defensive_rule_id` | string / null | `null` | 对应 `defensive.md` 中的规则标识（如 `DEF-R-1`）。仅当该资产产生了 defensive rule 时填写 |
| `governance_tags` | string[] | `[]` | 治理状态标签数组。当前支持 `needs-review`（待治理，由 audit 衰减逻辑自动打上） |

## 向后兼容

所有读取端 skill 遇到字段缺失时，按以下策略处理：

| 缺失字段 | 兼容行为 |
| --- | --- |
| `added_at` | 视为当前时间（即不触发衰减） |
| `last_checked_at` | 视为等于 `added_at`（若 `added_at` 也缺失则视为当前时间） |
| `last_triggered_at` | 视为等于 `added_at`（同上） |
| `defensive_rule_id` | 视为 `null`（该资产未产生 defensive rule） |
| `governance_tags` | 视为 `[]`（无治理标签） |

## 衰减治理规则

`audit` 在执行 Periodic Freshness Check 时，依据 `last_checked_at` 判断新鲜度：

| 条件 | 动作 |
| --- | --- |
| `last_checked_at` 距今 > 90 天，当前 `confidence: high` | 降至 `medium`，打上 `needs-review` |
| `last_checked_at` 距今 > 180 天，或当前已是 `medium` 且距今 > 90 天 | 降至 `low`，打上 `needs-review` |
| 相关代码区域近 90 天内无改动（项目休眠） | 阈值放宽至 180 / 360 天 |

衰减基于 `last_checked_at`（是否仍在被使用），不基于 `last_triggered_at`（是否阳性命中），避免高质量规则因人人遵守而被降级。

## 适合放什么

适合放进 `immune-registry.yaml` 的内容：

- 经过验证、已转正的可复用防护资产
- 有明确事故来源和修复验证的防护决策
- 范围明确、证据充分、防护风险低的规则

## 不要放什么

不要把 `immune-registry.yaml` 变成：

- 未经验证的预防性规则（应放在 `immune-candidates.yaml`）
- 与具体一次修复绑定的临时措施
- 没有事故来源的主观最佳实践
- 范围过广或不确定的防护（应先进候选区）

## 与 immune-candidates.yaml 的边界

`immune-registry.yaml` 存放已转正的正式防护。`immune-candidates.yaml` 存放待观察的候选防护。

从候选区到正式区的提升由 `audit` Phase 2 判断，条件见 [immune-decision-matrix.md](immune-decision-matrix.md) 的路由门槛。
