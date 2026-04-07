# 免疫资产审查提示词

当可视化仪表盘中免疫资产被标记为 `needs-review`（衰减降级）时，通过 Deep Link 唤起 IDE 并注入此提示词。

---

## 提示词模板

```
仪表盘显示以下免疫资产已被标记为待治理（needs-review）：

**资产 ID**：{{asset_id}}
**当前置信度**：{{confidence}}
**最后检视时间**：{{last_checked_at}}
**降级原因**：超过衰减阈值未被检视

请用 audit 审查这条免疫资产，决定：
1. 保留（keep）— 规则仍有价值，更新 last_checked_at
2. 更新（update）— 规则需要修正范围或内容
3. 弃用（deprecate）— 规则已过时，标记为 deprecated
```

## 变量说明

| 变量 | 来源 | 说明 |
| --- | --- | --- |
| `asset_id` | Deep Link 参数 | immune-registry.yaml 中的条目 id |
| `confidence` | Deep Link 参数 | 当前置信度（衰减后的值） |
| `last_checked_at` | Deep Link 参数 | 最后检视时间 |
