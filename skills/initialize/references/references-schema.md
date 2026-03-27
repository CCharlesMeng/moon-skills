# references.yaml Schema 指南

`references.yaml` 用于记录前端项目里**全项目共享、可模仿、值得优先查找**的参考模式。

这份文件回答的问题不是“模块内部怎么实现”，而是“这个项目通常怎么写”。

## 设计原则

- 共享模式优先于模块细节
- `refs` 优先于 prose
- 同时记录正例与反例
- 标记 confidence 和 last verified time
- 只记录高价值模式，不做全量目录抄写

## 建议结构

```yaml
version: 1
generated_at: 2026-03-17T00:00:00Z
source_commit: abc1234
generator: initialize

reference_patterns:
  - id: checkout-summary-card
    kind: business_component
    summary: 结算摘要卡片的标准组合方式
    refs:
      - apps/web/src/components/checkout/SummaryCard.tsx
      - apps/web/src/pages/checkout/OrderSummary.tsx
    use_when:
      - 需要同时展示价格、优惠和会员权益
    avoid_when:
      - 只是纯展示型价格标签
    tests:
      - apps/web/src/components/checkout/__tests__/SummaryCard.test.tsx
    confidence: high
    last_verified_at: 2026-03-17

  - id: async-form-submit
    kind: interaction_pattern
    summary: 异步表单提交与 loading/error/success 状态的标准写法
    refs:
      - apps/web/src/hooks/useSubmitOrder.ts
      - apps/web/src/pages/account/ProfileForm.tsx
    use_when:
      - 表单提交依赖异步接口
    avoid_when: []
    tests:
      - apps/web/src/pages/account/__tests__/ProfileForm.test.tsx
    confidence: medium
    last_verified_at: 2026-03-17

anti_examples:
  - id: legacy-class-checkout-panel
    reason: 历史 class 组件，状态流混乱，不建议继续模仿
    refs:
      - apps/legacy/src/checkout/CheckoutPanel.jsx
    confidence: high

risk_hotspots:
  - id: scattered-price-utils
    summary: 价格计算逻辑分散，后续任务容易重复实现或改漏顺序
    refs:
      - apps/web/src/utils/price/index.ts
      - apps/web/src/utils/price/discount.ts
    confidence: medium

test_patterns:
  - id: checkout-page-integration
    summary: 结算页集成测试的标准入口
    refs:
      - apps/web/src/pages/checkout/__tests__/OrderSummary.test.tsx
    confidence: medium
```

## 最低要求

至少应支持：

- `version`
- `generated_at`
- `source_commit`
- `generator`
- `reference_patterns`
- `anti_examples`
- `risk_hotspots`（可为空，用于记录会误导后续任务判断的上下文风险点）

对每条模式，至少记录：

- `id`
- `kind` 或 `reason`
- `summary`
- `refs`
- `confidence`

若有现成测试或验证入口，优先补：

- `tests`
- `last_verified_at`

## 推荐的 pattern kind

常见 `kind` 可以包括：

- `business_component`
- `ui_pattern`
- `interaction_pattern`
- `state_pattern`
- `api_pattern`
- `test_pattern`

不要求一次性覆盖全部类型，只记录当前仓库里真正高价值的模式。

## 适合放什么

适合放进 `references.yaml` 的内容：

- 公共业务组件入口
- 常见交互写法
- 状态管理模式
- API 调用模式
- 测试样例入口
- 不建议模仿的反例
- 已知上下文风险点

## 不要放什么

不要把 `references.yaml` 变成：

- 全量组件目录
- 设计系统百科
- 主观风格指南
- 没有代码 ref 的口号
- 每个模块都重复一遍的说明书

如果某类写法本身是全项目共享的，优先放在共享层，不要复制到每个模块说明里。

## 写法建议

- `summary` 保持一句话，优先回答“为什么值得模仿”
- `use_when` / `avoid_when` 只写关键判断条件
- `refs` 选最能代表该模式的 1 到 3 个入口
- `anti_examples` 只写明确不建议继续模仿的旧模式
- `risk_hotspots` 用于提示会误导后续任务判断的上下文风险，不等于风险审计或治理决策
