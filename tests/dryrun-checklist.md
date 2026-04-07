# Dry-run 走查检查清单

每次走查从 fixture 需求出发，按 skill 链顺序手动触发全流程，对照检查点逐项标记。

## 使用方法

1. 复制下方对应 fixture 的模板到 `tests/dryrun-results/<mode>-<date>.md`
2. 以 fixture 的"需求"启动新 session
3. 按 skill 链顺序执行，在每个 skill 完成时逐项打勾
4. 偏差记录填入末尾表格
5. 完成后写结论

---

## patch-lite 模板

```markdown
# Dry-run: patch-lite — <date>

需求：订单列表页的"已发货"状态标签颜色从灰色改为绿色。

## 检查点结果

### analysis-spec
- [ ] 分级为 patch-lite
- [ ] 摸底：定位到 OrderListPage 中的 StatusBadge 组件
- [ ] 自学习：StatusBadge 的颜色映射在 statusColorMap 中，🟢 可自行确认
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
- [ ] 如有 defensive rules：last_checked_at 已反写

### verify
- [ ] 使用 frontend-verify-pack
- [ ] 最小证据：前后截图 + 控制台无新增报错
- [ ] 无 spec deviation

### spec-check
- [ ] 唯一 TB 标记为 as_specified

### audit
- [ ] 产出 reflect.md
- [ ] 无需路由 sync-context 或仅 observation_only

## 偏差记录

| 阶段 | 偏差描述 | 原因分类（skill 描述不清 / AI 理解偏差 / 其他） | 建议修正 |
|------|---------|----------------------------------------------|---------|

## 结论

```

---

## feature-slice 模板

```markdown
# Dry-run: feature-slice — <date>

需求：给订单列表加分页，默认每页 20 条，页码同步到 URL。

## 检查点结果

### analysis-spec
- [ ] 分级为 feature-slice
- [ ] 摸底：定位到 OrderListPage → useOrders → /api/orders
- [ ] 自学习：usePagination 可复用 🟢，后端分页 🟡，默认条数 🔴，URL 同步 🔴
- [ ] 澄清：至少 2 个 🔴 需要用户回答
- [ ] TB 数量：4-6 条
- [ ] 下一步路由：涉及共享 hook，命中触发矩阵，进入 design-pack

### design-pack
- [ ] 已进入
- [ ] AC 数量 >= TB 数量
- [ ] TC 覆盖 happy-path 和 failure-path
- [ ] ADR：页码写入 URL vs 本地状态的决策记录

### slice-plan
- [ ] 2-4 个 slice
- [ ] 每个 slice 有测试先行清单（TC 编号）
- [ ] 每个 slice 有回滚方式

### code-review
- [ ] 收集 rules：base.md（仓库级）+ 需求级 rules
- [ ] 检视领域命名一致性
- [ ] 检视架构约束遵守
- [ ] 无 blocking issue
- [ ] 如有 defensive rules：Phase 3 反写 last_checked_at（如有 blocking 则同时更新 last_triggered_at）
- [ ] 最终输出包含免疫触发记录行

### verify
- [ ] 使用 frontend-verify-pack
- [ ] 每个 TC 有 EV
- [ ] 检查状态覆盖（loading / empty / error / success）
- [ ] 无 blocking 级别 spec deviation

### spec-check
- [ ] 所有 TB 有归宿
- [ ] 无隐性偏差

### audit
- [ ] Phase 0.5 执行 Periodic Freshness Check（检查 immune 资产新鲜度）
- [ ] 超 90 天未 checked 的 high confidence 资产已降级为 medium + needs-review
- [ ] 产出 reflect.md
- [ ] reflect.md 的"长期防护机会"章节列出 needs-review 条目
- [ ] 如有可复用模式，路由 sync-context 写回 references
- [ ] 如有风险教训，评估是否生成 immune-candidates
- [ ] 如有 [possibly-resolved] uncertainty 条目，确认或恢复

## 偏差记录

| 阶段 | 偏差描述 | 原因分类（skill 描述不清 / AI 理解偏差 / 其他） | 建议修正 |
|------|---------|----------------------------------------------|---------|

## 结论

```

---

## migration-strict 模板

```markdown
# Dry-run: migration-strict — <date>

需求：将全局状态管理从 Redux 迁移到 Zustand，影响订单、用户、设置三个模块，需要兼容期。

## 检查点结果

### analysis-spec
- [ ] 分级为 migration-strict
- [ ] 摸底：覆盖三个模块的共享状态边界、现有测试覆盖、兼容风险
- [ ] 自学习：大量 🔴 / 🟡（跨模块影响面不确定）
- [ ] 澄清：全量澄清模式
- [ ] TB 数量：8+ 条
- [ ] 下一步路由：必须进入 design-pack

### design-pack
- [ ] 已进入，全部 Phase 必做
- [ ] ADR：为什么选 Zustand、迁移策略、兼容层设计
- [ ] AC 覆盖兼容期行为：旧 Redux 路径仍可工作
- [ ] TC 覆盖回归：迁移前后行为一致性测试
- [ ] Compatibility / Rollback Notes 已填写

### slice-plan
- [ ] 有 compatibility slice（先加兼容层 / feature flag）
- [ ] compatibility slice 排在行为变更 slice 之前
- [ ] 共享层改动独立成 slice
- [ ] 每个 slice 有测试先行清单
- [ ] staged rollout 计划

### code-review
- [ ] 收集 rules：base.md + 需求级 rules + defensive.md（如有）
- [ ] 重点检视兼容层代码、双写逻辑、feature flag 实现
- [ ] 检视领域命名和架构约束
- [ ] 无 blocking issue
- [ ] 如有 defensive rules：Phase 3 反写 last_checked_at / last_triggered_at
- [ ] 最终输出包含免疫触发记录行

### verify
- [ ] 使用 frontend-verify-pack + integration-verify-pack
- [ ] 回滚/兼容证据：feature flag 可切回旧路径
- [ ] 性能对比：迁移前后关键路径无明显退化
- [ ] 共享行为回归：跨模块回归测试通过

### spec-check
- [ ] 所有 TB 有归宿
- [ ] intentionally_changed 项有变更原因和确认方
- [ ] deferred 项（如有）有后续计划

### audit
- [ ] Phase 0.5 执行 Periodic Freshness Check
- [ ] 产出 reflect.md
- [ ] reflect.md 列出 needs-review 的免疫条目（如有）
- [ ] 路由 sync-context 写回：迁移模式、共享层变更、兼容期策略
- [ ] 评估是否将关键教训写入 immune 资产
- [ ] deferred TB 有后续跟进计划
- [ ] 如有 [possibly-resolved] uncertainty 条目，确认或恢复

## 偏差记录

| 阶段 | 偏差描述 | 原因分类（skill 描述不清 / AI 理解偏差 / 其他） | 建议修正 |
|------|---------|----------------------------------------------|---------|

## 结论

```
