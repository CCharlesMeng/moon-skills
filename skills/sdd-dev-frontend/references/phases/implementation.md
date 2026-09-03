# Phase B：按 Task 实现

只在进入 Phase B 时读取。共享 Task 步骤形状、形态与扩散承接规则见 [前端 SDD 执行契约](../execution-contract.md)；验证动作仍由 [validation-policy.md](../validation-policy.md) 编译。

## 1. 开工前

读取当前 Task、受影响声明、精确文件范围、冻结 QA 行和采用的 PATTERN/REQ-DEC。按分支再读：

| 分支 | 条件引用 |
| --- | --- |
| 还原轮 | [restore/run.md](../restore/run.md)；首次落账再读 [templates/story-artifacts.md](../templates/story-artifacts.md) 第二节 |
| 逻辑/机械轮 | 仓库测试入口与当前声明；不读还原细则 |
| 能力缺口或中断恢复 | 本文件“降级与恢复” |

## 2. Task 与轮次

按 `tasks.md` 顺序执行。一个 Task 通常一种形态；上游明确给出多轮时，每轮独立走自己的步骤并引用自己的声明。不同形态可共享一次产品代码修改，但不能互借证据。

步骤数由形态决定，逐 Task 按上游写的步骤走，不补齐成统一步数、也不合并已写出的步骤。上游标了「取证归属」的还原轮负责取 RED 报告，引用它的轮次直接进入实现与转绿。缺口步只取能证明缺口存在（必要时加上原因正确）的最窄事实；实现步只做 Task 行为；转绿步取得本 Task 改变声明的因果证据；末步回填账本并勾 checkbox。

宽命令、跨页状态矩阵、回归和独立检视留给 Phase C。Task 阶段已取得且新鲜的原始命令/场景事实直接写入 `review-evidence.json`，后续按依赖复用。

## 3. 逻辑与机械轮

- 逻辑轮（`test_case`）优先使用仓库既有最窄测试层级；失败必须对应声明缺口，GREEN 只证明该声明。
- 逻辑轮（`manual_acceptance`）实现候选产品代码并让受影响范围的质量门通过，然后只登记待验收：`manual_outcome` 保持 `NOT_RUN`、`claim_status` 保持 `UNVERIFIED`，写清验收入口。**agent 不代签**，不写 `manual_checked_by`。
- 机械轮只用于确无行为分支的类型、构建或引用对齐；写明为什么不需要行为证据。
- 测试表达冻结契约，不为适配当前实现而放宽断言。
- 命令失败中与当前 Task 无关的既有失败只记录，不把本声明判为失败或通过。
- 人工验收 Task 中出现可确定断言、新的高风险触发器或共享边界改动时，立即按 [validation-policy 第七节](../validation-policy.md#七验证方法的判定规则)重分类为 `test_case` 或拆出独立声明，不沿用原分类。

## 4. 还原轮

1. 校验 baseline 与 contract 哈希。
2. 对同一契约运行 validate、按需 static、结构化 render 与 RED 报告；RED 必须来自未实现差异，不来自环境或序列化等价。同页多轮共用一次 RED。新建页面在改动前不存在时免 RED，在 `alpha-tests.md` 明记“新建页面，免 RED”，不制造全 YELLOW 报告。
3. 只修改 Task 文件范围与按扩散承接规则登记的连带文件；实现冻结规则，不从实现反推期望。
4. 重跑同一契约生成 GREEN 报告。机器可检项用结构化事实。
5. YELLOW 按原因补证、记 `UNVERIFIED`、记 `DEFERRED` 或转真实 RED；不改写 GREEN、不就地新增豁免。字符串 RED 先看报告 `hint`，确认只是序列化差异时补比对器归一化并重跑同一契约。

## 5. 落账与新鲜度

每个 Task 的末步（回填账本并提交）：

- 在 `alpha-tests.md` 回填声明、状态、证据 ID/路径、环境和相关依赖；还原记录按[还原证据记录](../templates/story-artifacts.md#还原证据记录)。
- 「执行环境」列写本次取证实际处在的档（`mock` / `contract` / `live`）。它低于 portfolio 里该声明的 `required_profile` 时**不得写 `PROVEN`**：环境本可搭建写 `UNVERIFIED`，后端/身份/数据不可用写 `DEFERRED` 并在 Deferred 表补外部依赖与解除条件。判据见[执行契约的执行环境档](../execution-contract.md#执行环境档)。
- 状态按 [共享执行契约的状态表](../execution-contract.md#声明与状态)判定，本文件不复制判据。
- 先回填账本、后勾 checkbox；checkbox 是本 Task 的 commit point。勾选已实际完成的项，验证结果不替代实现进度。人工验收 Task 的 checkbox 只表示实现完成，**不表示该声明已通过验收**；账本状态继续独立演进。
- 同一动作可被多条声明引用，不复制输出。依赖文件变化时只失效命中的证据。

## 6. 升级、降级与恢复

计划的文件清单是已确认范围，不是穷举。需要动清单外的文件时按[执行契约的扩散承接规则](../execution-contract.md#扩散承接)分流：同 Story 内、不改变验收契约的连带改动直接承接并登记文件与原因，不为此中断；会改变 AC/AT 断言或对外契约的先按 P7 上报；跨仓或需要新增 AC 的回流上游。承接的文件同样进入依赖闭包，失效范围一并登记。

连续三次针对同一原因的小修仍失败时，先收集事实再按 P7 一次上报。

页面、账号、浏览器或脚本能力缺失时继续处理其他声明；已选模块未执行使依赖声明保持 `UNVERIFIED`。仓库事实失效或实现本身不安全时回 Phase -1。中断续跑以 checkbox 定实现进度、以账本定声明状态，复用仍新鲜证据；两者不一致时按 commit point 裁决——勾了但账本无该 Task 记录即末步未完成，重做末步；账本有记录未勾则补勾。

退出：全部 Task 实际完成并勾选；每条改变声明已有因果证据或明确未证原因。
