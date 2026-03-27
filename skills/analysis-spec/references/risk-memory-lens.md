# 风险记忆检查清单

适用信号：需求触达高危模块、历史事故或已有 immune 约束。除 `patch-lite` 外默认开启。

## 输入源

按以下顺序读取：

1. `sync-context` 的 freshness / confidence / uncertainty
2. `.project-context/references.yaml`（共享模式、反例、risk hotspots）
3. `.project-context/features/index.yaml`（相关 feature refs）
4. `.project-context/immune-registry.yaml`（正式防护 → 硬约束）
5. `.project-context/immune-candidates.yaml`（弱信号 → 只影响提问优先级）
6. 最近一轮 `audit` 摘要（learnings、context drift）

## 检查项

- [ ] 之前有哪些反例、risk hotspot 或 immune 规则
- [ ] 哪些旧 learnings 仍然有效
- [ ] 哪些只是弱信号，只能进入 watchlist
- [ ] 本次需求是否踩到既有高风险边界
- [ ] 本次分析是否需要把旧问题转化为新的验证要求

## 优先级规则

直接证据 > 正式 immune > 候选 immune > 历史观察。候选资产不能直接升级为硬门禁。

## 定制

要修改本检查清单，复制本文件到 `.project-context/lenses/risk-memory.md` 并编辑。同名文件仓库版本优先于 skill 默认。不要直接修改本文件。

要新建检查清单，参考 [lens-template.md](lens-template.md)。
