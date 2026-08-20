# 门禁矩阵

本包只在 `sdd-dev` 派格。`sdd-prd` / `sdd-design` 不派前端代码格；`sdd-archive-workspace` 是 rollup 门禁，不派任何格子。

| Gate | 本包格子 | 角色 |
| --- | --- | --- |
| sdd-prd | — | — |
| sdd-design | — | — |
| sdd-dev | CODE-RESTORE | restore-lens |
| sdd-dev | CODE-LAYOUT | layout-lens |
| sdd-dev | CODE-CONVENTION | convention-lens |
| sdd-dev | CODE-QUALITY | quality-lens |
| sdd-dev | CODE-TEST | test-lens |
| sdd-archive-workspace | — | — |

调用方可以只派风险命中的格子。未派的格不是「未执行」，也不生成占位结果。

## 格子边界（不得跨格重判）

| 现象 | 归属 |
| --- | --- |
| 变更区块相对冻结 R 契约的 RED / YELLOW / GREEN | CODE-RESTORE |
| 跨页不一致、真实数据溢出、目标视口「不破」、栅格、运行时交互态、滚动/固定 | CODE-LAYOUT |
| 命名、组件范式、token、请求封装、公共能力复用、类型抑制、i18n——且有 `PATTERN-*` | CODE-CONVENTION |
| 职责、重复、复杂度、状态放置、副作用、错误边界、死代码、性能——且能说出可观察后果 | CODE-QUALITY |
| 冻结 F 行与已选 REG 行是否成立 | CODE-TEST |

`PATTERN-*` 语义等价的重复实现走 CODE-CONVENTION 的 `shared-capability-reuse`，不走 CODE-QUALITY 的 `duplicated-code`。
