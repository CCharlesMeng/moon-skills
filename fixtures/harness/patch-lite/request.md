# Fixture: patch-lite

## 需求

订单列表页的"已发货"状态标签颜色从灰色改为绿色。

## 预期 harness 行为检查点

### analysis-spec

- [ ] 分级为 `patch-lite`
- [ ] 摸底：定位到 OrderListPage 中的 StatusBadge 组件
- [ ] 自学习：StatusBadge 的颜色映射在 `statusColorMap` 中，🟢 可自行确认
- [ ] TB 数量：1-2 条
- [ ] 下一步路由：跳过 design-pack，直接进入 slice-plan

### design-pack

- [ ] 未进入（patch-lite 跳过）

### slice-plan

- [ ] 只有 1 个 slice
- [ ] 无测试先行清单（或标注人工验证替代理由）
- [ ] 回滚方式：还原 statusColorMap 中的映射值

### code-review

- [ ] 压缩模式：仅仓库级 base rules 快速检查
- [ ] 无 blocking issue

### verify

- [ ] 使用 frontend-verify-pack
- [ ] 最小证据：前后截图 + 控制台无新增报错
- [ ] 无 spec deviation

### spec-check

- [ ] 唯一 TB 标记为 `as_specified`

### audit

- [ ] 产出 `reflect.md`，含本轮决策和观察
- [ ] 无需路由 sync-context（影响面极小）或仅标记 `observation_only`
