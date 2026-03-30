# Fixture: migration-strict

## 需求

将全局状态管理从 Redux 迁移到 Zustand，影响订单、用户、设置三个模块，需要兼容期。

## 预期 harness 行为检查点

### analysis-spec

- [ ] 分级为 `migration-strict`
- [ ] 摸底：覆盖三个模块的共享状态边界、现有测试覆盖、兼容风险
- [ ] 自学习：大量 🔴 / 🟡（跨模块影响面不确定）
- [ ] 澄清：全量澄清模式
- [ ] TB 数量：8+ 条
- [ ] 下一步路由：必须进入 design-pack

### design-pack

- [ ] 已进入，全部 Phase 必做
- [ ] ADR：为什么选 Zustand、迁移策略（渐进 vs 一次性）、兼容层设计
- [ ] AC 覆盖兼容期行为：旧 Redux 路径仍可工作
- [ ] TC 覆盖回归：迁移前后行为一致性测试
- [ ] Compatibility / Rollback Notes 已填写

### slice-plan

- [ ] 有 compatibility slice（先加兼容层 / feature flag）
- [ ] compatibility slice 排在行为变更 slice 之前
- [ ] 共享层改动独立成 slice
- [ ] 每个 slice 有测试先行清单
- [ ] staged rollout 计划

### domain-verify

- [ ] 使用 frontend-verify-pack + integration-verify-pack
- [ ] 回滚/兼容证据：feature flag 可切回旧路径
- [ ] 性能对比：迁移前后关键路径无明显退化
- [ ] 共享行为回归：跨模块回归测试通过

### spec-check

- [ ] 所有 TB 有归宿
- [ ] `intentionally_changed` 项有变更原因和确认方
- [ ] `deferred` 项（如有）有后续计划

### audit

- [ ] 产出 `reflect.md`
- [ ] 路由 sync-context 写回：迁移模式、共享层变更、兼容期策略
- [ ] 评估是否将迁移中的关键教训（如跨模块兼容陷阱）写入 `immune-registry.yaml` 或 `immune-candidates.yaml`
- [ ] 如果存在 `deferred` TB，记录后续跟进计划和责任方
