# features/index.yaml Schema 指南

`features/index.yaml` 用于记录仓库里的**关键特性稀疏索引**。

它不是完整 feature tree，也不是产品需求数据库。它的目标是建立最小可用关联，让 AI 和维护者知道“这类能力落在哪、对应哪些代码和测试”。

## 设计原则

- 只记录高价值、高频或当前任务相关的特性
- 优先记录 `refs`，不要强行补 prose
- 允许不完整，允许低置信，允许空数组
- 不为了好看去猜 spec、acceptance 或 owner
- 对人可以呈现为树，对机器优先保持索引表

## 建议结构

```yaml
version: 1
generated_at: 2026-03-17T00:00:00Z
source_commit: abc1234
generator: initialize

features:
  - id: checkout-pricing
    title: 结算页价格展示
    status: active
    spec_refs:
      - docs/specs/checkout-pricing.md
    acceptance_refs:
      - docs/specs/checkout-pricing.md#acceptance
    module_refs:
      - web-app
      - shared-ui
    code_refs:
      - apps/web/src/pages/checkout/OrderSummary.tsx
      - packages/shared-ui/src/components/PriceTag.tsx
    test_refs:
      - apps/web/src/pages/checkout/__tests__/OrderSummary.test.tsx
    owners:
      - checkout-team
    confidence: medium
    updated_at: 2026-03-17

  - id: account-login
    title: 登录流程
    status: active
    spec_refs: []
    acceptance_refs: []
    module_refs:
      - web-app
    code_refs:
      - apps/web/src/pages/auth/LoginPage.tsx
    test_refs: []
    owners: []
    confidence: low
    updated_at: 2026-03-17
    uncertainty:
      - 缺少显式 spec 文档
```

## 最低要求

至少应支持：

- `version`
- `generated_at`
- `source_commit`
- `generator`
- `features[].id`
- `features[].title`
- `features[].status`
- `features[].module_refs`
- `features[].code_refs`
- `features[].confidence`
- `features[].updated_at`

如有证据，优先补：

- `spec_refs`
- `acceptance_refs`
- `test_refs`
- `owners`
- `uncertainty`

## status 建议

常见 `status` 可以包括：

- `active`
- `legacy`
- `unknown`

初始化阶段不需要设计太多状态，保持简单即可。

## 适合放什么

适合放进 `features/index.yaml` 的内容：

- 高价值关键特性
- 高频业务能力
- 当前任务相关特性
- 已有 code/test/spec 显式证据支撑的特性

## 不要放什么

不要把 `features/index.yaml` 变成：

- 全量产品 roadmap
- 完整 feature tree
- 叙事型需求文档
- 没有 ref 支撑的抽象能力树
- 每个页面都机械登记一次的清单

如果一个“特性”只是目录名、页面名或组件名的另一种写法，就先不要收进去。

## 写法建议

- `id` 使用稳定 slug，不要写展示文案
- `title` 给人看，`id` 给机器用
- `module_refs` 优先引用 `profile.yaml` 里的模块 id
- `code_refs` 只写最能代表该特性的入口
- `test_refs` 没有就留空，不要编造
- 若以后确有必要，再从索引升级到 per-feature 文件，不要在初始化阶段直接铺开
