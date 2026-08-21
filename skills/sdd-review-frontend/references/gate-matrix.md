# 格子边界

本包定义五个格子，格子清单与对应清单见 [SKILL.md](../SKILL.md#五格)。

**派哪几格由调用方决定。** 调用方按自己的风险规则选格，在请求里给出 `gate` 标识；本包不枚举有哪些 gate，也不规定某个 gate 该派哪几格。未派的格不是「未执行」，也不生成占位结果。

本文件只回答一件事：**同一个现象归哪一格。**

## 现象归属（不得跨格重判）

| 现象 | 归属 |
| --- | --- |
| 变更区块相对冻结 R 契约的 RED / YELLOW / GREEN | CODE-RESTORE |
| 跨页不一致、真实数据溢出、目标视口「不破」、栅格、运行时交互态、滚动/固定 | CODE-LAYOUT |
| 命名、组件范式、token、请求封装、公共能力复用、类型抑制、i18n——且有 `PATTERN-*` | CODE-CONVENTION |
| 职责、重复、复杂度、状态放置、副作用、错误边界、死代码、性能——且能说出可观察后果 | CODE-QUALITY |
| 冻结 F 行与已选 REG 行是否成立 | CODE-TEST |

`PATTERN-*` 语义等价的重复实现走 CODE-CONVENTION 的 `shared-capability-reuse`，不走 CODE-QUALITY 的 `duplicated-code`。

各 `ROLE.md` 的「格子边界」只写自己那侧的例外，不复述本表。
