# Phase B：按 Task 实现

只在进入 Phase B 时读取。共享 Task 六步与形态见 [前端 SDD 执行契约](../../../docs/skills/frontend-sdd/执行契约.md)；验证动作仍由 [validation-policy.md](./validation-policy.md) 编译。

## 1. 开工前

读取当前 Task、受影响声明、精确文件范围、冻结 QA 行和采用的 PATTERN/REQ-DEC。按分支再读：

| 分支 | 条件引用 |
| --- | --- |
| 还原轮 | [restore-contract.md](./restore-contract.md)；首次落账再读 [alpha-tests-restore.md](./alpha-tests-restore.md) |
| 逻辑/机械轮 | 仓库测试入口与当前声明；不读还原细则 |
| 能力缺口或中断恢复 | 本文件“降级与恢复” |

## 2. Task 与轮次

按 `tasks.md` 顺序执行。一个 Task 通常一种形态；上游明确给出多轮时，每轮独立走六步并引用自己的声明。不同形态可共享一次产品代码修改，但不能互借证据。

Step 1/2 只取得能证明预期缺口存在且原因正确的最窄事实；Step 3 实现 Task 行为；Step 4 取得本 Task 改变声明的因果证据；Step 5 只做不改变契约的必要重构；Step 6 回填账本并勾 checkbox。

宽命令、跨页状态矩阵、回归和独立检视留给 Phase C。Task 阶段已取得且新鲜的原始命令/场景事实直接写入 `review-evidence.json`，后续按依赖复用。

## 3. 逻辑与机械轮

- 逻辑轮优先使用仓库既有最窄测试层级；失败必须对应声明缺口，GREEN 只证明该声明。
- 机械轮只用于确无行为分支的类型、构建或引用对齐；写明为什么不需要行为证据。
- 测试表达冻结契约，不为适配当前实现而放宽断言。
- 命令失败中与当前 Task 无关的既有失败只记录，不把本声明判为失败或通过。

## 4. 还原轮

1. 校验 baseline 与 contract 哈希。
2. 对同一契约运行 validate、static、结构化 render 与 RED 报告；RED 必须来自未实现差异，不来自环境或序列化等价。
3. 只修改 Task 文件范围；实现冻结规则，不从实现反推期望。
4. 重跑同一契约生成 GREEN 报告。机器可检项用结构化事实；仅 visual YELLOW 按需截图。
5. YELLOW 按原因补证、记 `UNVERIFIED`、记 `DEFERRED` 或转真实 RED；不改写 GREEN、不就地新增豁免。
6. `suspected-tool-equivalence` 只补比对器两端映射或按 P7 上报；不改产品代码迎合字符串。

## 5. 落账与新鲜度

每个 Task 的 Step 6：

- 在 `alpha-tests.md` 回填声明、状态、证据 ID/路径、环境和相关依赖；还原记录按 [alpha-tests-restore.md](./alpha-tests-restore.md)。
- 状态按 [共享执行契约的状态表](../../../docs/skills/frontend-sdd/执行契约.md#声明与状态)判定，本文件不复制判据。
- 勾选已实际完成的 checkbox；验证结果不替代实现进度。
- 同一动作可被多条声明引用，不复制输出。依赖文件变化时只失效命中的证据。

## 6. 升级、降级与恢复

连续三次针对同一原因的小修仍失败，或需要修改 Task 文件清单外的文件时，先收集事实再按 P7 一次上报。冻结产物唯一决定的连带修改可直接做，但要登记原因和失效范围。

页面、账号、浏览器或脚本能力缺失时继续处理其他声明；已选模块未执行使依赖声明保持 `UNVERIFIED`。仓库事实失效或实现本身不安全时回 Phase -1。中断续跑以 checkbox 定实现进度、以账本定声明状态，复用仍新鲜证据。

退出：全部 Task 实际完成并勾选；每条改变声明已有因果证据或明确未证原因。
