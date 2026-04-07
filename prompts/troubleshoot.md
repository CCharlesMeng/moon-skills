# 排障伴随提示词

当可视化仪表盘通过 Deep Link 唤起 IDE 时，将以下内容注入到用户剪贴板，引导 AI 进入结构化排障流程。

---

## 提示词模板

```
我在仪表盘上发现了以下问题，请帮我排查：

**问题来源**：{{source_view}}（全景 / 特性 / 需求 / 健康）
**问题对象**：{{object_id}}（模块 ID / 特性 ID / 需求 topic / 免疫资产 ID）
**问题现象**：{{symptom}}

请先用 sync-context 预热相关模块上下文，然后：
1. 如果是 bug 或回归 → 使用 immune-debug 进行结构化排障
2. 如果是上下文过期 → 使用 sync-context 做增量同步
3. 如果是免疫资产降级 → 使用 audit 审查后决定保留、更新或移除
```

## 变量说明

| 变量 | 来源 | 说明 |
| --- | --- | --- |
| `source_view` | Deep Link 参数 | 用户点击的仪表盘视图 |
| `object_id` | Deep Link 参数 | 被点击对象的标识 |
| `symptom` | Deep Link 参数或用户填写 | 问题的简要描述 |
