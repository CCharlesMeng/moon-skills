# Fixture: feature-slice

## 需求

给订单列表加分页，默认每页 20 条，页码同步到 URL。

## 预期 harness 行为检查点

### analysis-spec

- [ ] 分级为 `feature-slice`
- [ ] 摸底：定位到 OrderListPage → useOrders → /api/orders
- [ ] 自学习：usePagination 可复用 🟢，后端分页 🟡，默认条数 🔴，URL 同步 🔴
- [ ] 澄清：至少 2 个 🔴 需要用户回答
- [ ] TB 数量：4-6 条
- [ ] 下一步路由：涉及共享 hook，命中触发矩阵，进入 design-pack

### design-pack

- [ ] 已进入
- [ ] Phase 1（业务验收）：AC 数量 >= TB 数量，语言非技术人员可读，有"不做的事"和验收确认方式
- [ ] Phase 1 确认门：等待用户确认后才进入 Phase 2
- [ ] Phase 2（领域建模）：根据复杂度决定完整展开或压缩为术语表
- [ ] Phase 2 确认门：等待用户确认后才进入 Phase 3
- [ ] Phase 3（技术方案）：ADR（页码写入 URL vs 本地状态），API 契约定义
- [ ] Phase 3 确认门：等待用户确认后才进入 Phase 4
- [ ] Phase 4（测试规格）：TC 覆盖 happy-path 和 failure-path
- [ ] Phase 5（工作量评估）：有整体规模评估和工作块拆分

### slice-plan

- [ ] 2-4 个 slice
- [ ] 每个 slice 有测试先行清单（TC 编号）
- [ ] 每个 slice 有回滚方式

### code-review

- [ ] 收集 rules：base.md（仓库级）+ design-pack 产出的需求级 rules
- [ ] 检视领域命名一致性（统一语言表对照）
- [ ] 检视架构约束遵守（ADR 决策是否被正确实现）
- [ ] 无 blocking issue

### verify

- [ ] 使用 frontend-verify-pack
- [ ] 每个 TC 有 EV
- [ ] 检查 6 种状态覆盖（loading / empty / error / permission / success）
- [ ] 无 blocking 级别 spec deviation

### spec-check

- [ ] 所有 TB 有归宿
- [ ] 无隐性偏差

### audit

- [ ] 产出 `reflect.md`
- [ ] 如有可复用模式（如 usePagination 的使用范式），路由 sync-context 写回 references
- [ ] 如有风险教训，评估是否生成 immune-candidates
