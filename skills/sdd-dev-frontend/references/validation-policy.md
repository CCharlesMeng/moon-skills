# 声明驱动的验证策略

本文件是 `sdd-dev-frontend` 选择验证动作的唯一规则源。进入 Phase 0 编译初始验证组合、进入 Phase C 按最终 diff 重编译时完整读取；其他阶段只引用已经落盘的组合。

## 一、总纲

**门禁约束声明，风险选择动作。** 先确定本 Story 准备对外声称哪些验收声明成立，再为每条声明选择最小充分证据。不得因为某个动作通常存在就默认执行，也不得因为动作未执行就把无关声明一起判失败。

四条声明诚信门在任何 Story 上成立：

1. **来源诚信**：期望值来自上游 AC、外部基线或用户确认的工作假设；当前实现不反向定义期望值。
2. **状态诚信**：声明状态严格按 [共享执行契约的状态表](./execution-contract.md#声明与状态)判定，不新增第四种状态、不用状态位表达进度。
3. **证据诚信**：`PROVEN` 的证据覆盖该声明、使用正确环境，并对最终相关依赖仍新鲜。
4. **缺陷诚信**：声明范围内已确证的阻断缺陷清零；未清零就不能把受影响声明写成 `PROVEN`。

RED/GREEN、命令、浏览器矩阵、截图和独立检视都是证据策略，不是声明诚信门。按下文触发，未触发即不执行、不生成空工件。

每条声明还要选一个 `verification_method`。选法在[第七节](#七验证方法的判定规则)，那是人工资格门禁与自动化强制触发器的唯一事实源；风险选动作、门禁约束声明这条总纲对它同样成立。

## 二、输入与输出

从 `tasks.md` 读取 AC/AT、`affected_routes`、`required_states`、`risk_triggers` 与文件范围；再用当前 app baseline、实际 diff 和运行限制校正。上游字段是候选事实，实测冲突时以实测为准并登记原因。

把结果写入 `dev-baseline.md / 验证组合`，候选稳定后把同一结构写入 `review-evidence.json / validation_portfolio`：

```json
{
  "risk_triggers": ["visual", "interaction"],
  "portfolio_narrowed": [{"trigger": "build-config", "reason": "<收窄理由>"}],
  "modules": ["causal", "render", "targeted-quality"],
  "review_roles": ["review-layout"],
  "review_dimensions": {"review-layout": ["L2", "L3"]},
  "claims": [
    {"id": "AC-1", "modules": ["causal", "render"], "status": "UNVERIFIED"}
  ]
}
```

`review_roles` 只列本 Story 适用且需要独立判断的角色；`review_dimensions` 只列该角色真正被风险触发的维度。未列出的角色或维度不是“未执行”，也不生成占位结果。

## 三、风险触发器

取上游声明、仓库事实与最终 diff 的并集：

| 触发器 | 命中条件 |
| --- | --- |
| `visual` | 改 DOM 静态结构、样式、token 或可见文案 |
| `interaction` | 改用户操作、条件渲染或状态迁移 |
| `navigation` | 改路由、入口、查询参数或跨页流程 |
| `shared-boundary` | 改公共组件、公共样式、全局状态、请求封装或共享类型 |
| `auth` | 改权限、身份、租户或鉴权失败路径 |
| `write` | 产生服务端写入、提交、删除或不可逆副作用 |
| `async-state` | 改并发、取消、竞态、重试、轮询或多阶段异步状态 |
| `new-pattern` | 仓库没有唯一可复用 `PATTERN-*`，或本 Story 引入新范式 |
| `spec-gap` | AC、设计事实、参照页或工作假设冲突/缺失，且会影响判定 |
| `unknown-deps` | 无法可靠确定改动的依赖闭包或回归半径 |
| `build-config` | 改构建、测试、类型、lint、打包或运行配置 |
| `performance` | AC 明示性能目标，或改列表规模、缓存、虚拟化、昂贵计算 |

拿不准是否命中时加入触发器；不得用 Task 数量或文件数量代替风险事实。

`visual` / `navigation` / `shared-boundary` / `build-config` 的下限由 `<skill-dir>/scripts/classify_diff.py --repo-root <repo-root> --base-ref <base-ref> --out <临时目录>/diff-facts.json` 从 diff 机械给出，组合只能在下限之上扩；确要收窄某条下限触发器时写入 `portfolio_narrowed[]` 并给出理由，它会进 `acceptance.md`。聚合器拒绝既不承接也未署名收窄的组合。

## 四、验证模块

| 模块 | 触发 | 最小充分证据 |
| --- | --- | --- |
| `causal` | 每个被实现改动的验收声明 | 改动前能暴露缺口、改动后能证明声明的同一通道；`test_case` 与 `restore_contract` 声明优先测试 RED/GREEN 或冻结契约，类型/构建类可用编译失败→通过，`manual_acceptance` 声明用最终人工证据收口、不要求伪造自动化 RED |
| `render` | `visual` | 变更区块的冻结契约；只执行规则要求的 static/render 层，视觉盲区才截图。机器盲区剩余项留在契约 `visual` 层，只有该区块没有冻结契约时才允许生成 `manual_acceptance` 声明 |
| `story` | `interaction` / `navigation` / `auth` / `write`，且自动化 causal 证据不足以覆盖真实运行时 | 合并后的最短用户操作序列，覆盖受影响 AC 与必要异常路径 |
| `targeted-quality` | 改产品代码 | 覆盖改动依赖闭包的最窄 test/typecheck/lint/build 子集；仓库没有可安全收窄的入口时升级 |
| `regression` | `shared-boundary` / `navigation` / `auth` / `write` / `unknown-deps` / `build-config` | 受影响入口与下游消费者的回归；依赖闭包不可靠时运行 `runtime.md` 记录的全部质量命令 |
| `review-restore` | `visual` 且存在冻结 R 行 | 按最终 diff 重跑**全部已冻结区块**的契约，再从 R1–R6 中分配这些区块涉及的维度 |
| `review-layout` | `visual` 且跨页、跨视口、共享样式或 `required_states` 含 overflow | 从 L1–L6 中只分配命中风险的维度，页面范围只覆盖风险闭包 |
| `review-convention` | `new-pattern`、`shared-boundary`、`build-config`，或 diff 触碰 PATTERN 约束且没有确定性检查覆盖 | 从 C1–C7 中只分配 diff 真正触碰的 PATTERN 维度 |
| `review-quality` | `async-state` / `auth` / `write` / `performance` / `shared-boundary`，或实现引入非平凡状态与副作用 | 从 Q1–Q8 中只分配实际风险维度 |
| `self-test` | **验证组合含 `story` 模块**且现有自动化证据不能直接证明全部受影响声明 | 独立判断对应 F/REG 行；只覆盖验证组合列出的声明 |

模块 key `story` 指的是「当前 Story 的完整用户路径」这一取证动作，不是需求单元本身。散文里引用它一律写作「验证组合含 `story` 模块」，带反引号和量词；需求单元写「Story」不加反引号，TaskPacket 字段仍是 `story=`。它与验收声明的观察范围 `S3_STORY` 分属两轴——前者决定要不要跑真实路径，后者描述某条声明在多大范围内被观察——不得互相替代或当成同义词。

同一原始动作只执行一次。多个模块可引用同一条命令或浏览器场景，但各自保留判断。独立判断只在对应 review 模块被触发时成立，不要求五个角色成套出现，也不要求一个角色扫完它的全部分类。

`render` 与 `review-restore` 跑的是同一套契约，范围不同：`render` 在 Phase B 只跑当前变更区块，`review-restore` 在 Phase C 按最终 diff 重跑全部已冻结区块。后来的 Task 改了公共样式时，先前区块的 GREEN 只有在这里才会被推翻。

## 五、执行时机

- Phase B 只取得当前 Task 的 `causal` 证据；`render` 只跑当前变更区块的契约。把状态矩阵、跨页检查和宽回归留给候选阶段。`story` 模块不在 Phase B 执行。
- Phase B 修复中只运行失败定位所需的最窄动作，不执行候选级全量门。
- Phase C 按最终 diff 重编译验证组合；新增触发器只能增加模块。批量执行候选模块，先命令、后浏览器，再派适用的独立检视。`review-restore` 被选中时，重跑契约属于主 agent 的取证动作，在派发前完成。
- Phase D 只失效依赖命中的证据和判断。修复引入新触发器时把对应模块加入组合；无触发器不得扩大重跑。最终组合没有全量模块时不补「最终全量门」；命令键仍新鲜就继续复用，不为收尾重跑一遍。

## 六、升级与收口

出现以下任一信号时立即重编译组合：依赖闭包无法确定、基线冲突、工具无法判定、实际 diff 超出计划文件、出现新的运行时副作用、定向检查暴露跨范围失败。

收口逐声明判定，判据只用 [共享执行契约的状态表](./execution-contract.md#声明与状态)，本文件不复制一份。

`UNVERIFIED` 与 `DEFERRED` 都不计入已验收。它们必须进入 `alpha-tests.md`、`acceptance.md` 与最终状态限定，但只影响依赖它们的声明，不把无关声明一并降级。

## 七、验证方法的判定规则

本节是 `verification_method` 取值的唯一事实源，计划侧与执行侧都引用它，不各自复制。字段语义与枚举见[共享执行契约的验证模型](./execution-contract.md#验证模型)。

### 7.1 判定顺序

对每条需求锚点：

1. 拆成原子可观察声明，一个声明只验证一个行为点。混合场景拆成多条，不设 `hybrid`。
2. 没有行为分支的，作为机械 Task 写 `quality_gate` 并省略 `verification_scope`，不新增验收声明。
3. 视觉声明且所在区块已进入冻结还原契约的，写 `restore_contract`，到此为止。
4. 命中 §7.2 自动化强制触发器的，必须写 `test_case`；人工验收只能补充，不能替代。
5. 全部满足 §7.3 人工资格门禁的，才允许写 `manual_acceptance`。
6. 其余声明用仓库已有的最窄范围，以 `test_case` 取证。
7. 把判定理由、环境、证据要求和初始状态写进账本。

第 3 步放在第 4 步之前不构成放宽——它把声明推向更强的机器判定。同一区块另带行为风险时拆成独立声明各走各的方法，不把两件事压在一条声明上。

拿不准时用 `test_case`，不静默放宽。

### 7.2 自动化强制触发器

命中任一项时 `manual_acceptance` 只能补充：

- 金额、折扣、日期、排序、格式化、校验和其他确定性计算。
- 等价类、边界值、决策表、状态迁移或多分支错误处理。
- `auth`、`write`、`async-state`、`shared-boundary` 四类风险触发器命中。
- 缺陷修复与已有事故的回归场景。
- 高频核心路径，或需要持续回归的跨页流程。
- 明确量化的性能、无障碍、安全或兼容性指标。
- 依赖闭包不明、回归半径不明，或 `unknown-deps` 命中。
- 自动化已有稳定入口，新增断言成本低且能稳定复跑。

### 7.3 人工资格门禁

六条全部满足才允许 `manual_acceptance`，任一条不满足回到 `test_case`：

1. 期望结果包含机器无法稳定判断的人类感知或语义判断，或依赖无法稳定自动构造的真实设备/外部环境。
2. 可机器判定的确定性子行为已拆出并由 `test_case` 覆盖，机械检查由 `quality_gate` 覆盖，或已明确证明不存在这两类子项。
3. 未命中 §7.2。
4. 变更范围孤立、容易观察、容易回滚，不修改共享边界。
5. 自动化建设与维护成本明显高于该场景的重复验证收益。「赶时间」不是理由。
6. 验收环境、GWT、证据要求和未通过时的处理入口都已明确。

### 7.4 `manual_basis` 枚举

只允许下列值，避免自由文本把例外无限扩大：

| 值 | 适用条件 |
| --- | --- |
| `visual_judgment` | 视觉层级、品牌感、留白、字体观感等主观判断；**仅限该区块未进入冻结还原契约** |
| `motion_judgment` | 动画自然度、眩晕感、体感流畅度；**同样仅限未进入冻结契约** |
| `device_dependency` | 触摸、软键盘、系统权限、摄像头、打印等真机或系统能力 |
| `external_dependency` | SSO、浏览器扩展、外部嵌入页等不可稳定构造的真实接缝 |
| `content_approval` | 文案、运营、法务、业务含义与品牌语气确认 |
| `automation_cost_exception` | 极低风险、孤立、一次性、可回滚且自动化成本明显失衡；必须满足全部门禁 |

不设 `real-browser`、`css`、`performance` 这类过宽理由：真实浏览器是 Playwright/Cypress 的运行环境而不是人工理由；CSS 的静态结构、溢出与遮挡机器可判；有量化阈值的性能必须自动测量。

`automation_cost_exception` 是唯一自认定的口子，使用时必须写明被放弃的具体自动化入口和预估维护成本。

### 7.5 常见场景

| 场景 | 结果 |
| --- | --- |
| 纯类型、import、引用对齐 | `quality_gate`，无声明、无人工项 |
| 组件点击、输入、三态、请求参数 | `S1_COMPONENT + test_case` |
| 跨页普通导航 | `S3_STORY + test_case` |
| 鉴权、租户、提交、删除 | `test_case`，必要时另加人工验收声明 |
| CSS 静态结构、溢出、遮挡 | `test_case`，范围按 tie-break 定 |
| 视觉层级、品牌感、动效自然度（区块已冻结） | `restore_contract`，盲区落契约 `visual` 层 |
| 视觉层级、品牌感、动效自然度（无冻结契约） | `manual_acceptance` |
| 真实软键盘、触摸手势、系统权限 | 本地规则 `test_case` + 接缝 `manual_acceptance`，拆两条声明 |
| 第三方 SSO 真实账号联调 | adapter/错误映射 `test_case` + 接缝 `manual_acceptance` |
| 「滚动是否舒服」 | `S2_PAGE + manual_acceptance + motion_judgment` |
| 「1000 行下交互小于 100ms」 | `test_case`，量化阈值不转人工 |
| 缺陷修复 | `test_case`，必须留回归保护 |

### 7.6 通道缺口的处置

某条 `test_case` 声明的 `verification_scope` 没有对应自动化通道（如需要 `S3_STORY` 但 `browser_test_status` 不是 `available`）时，登记降级理由并把该声明保持 `UNVERIFIED`，不阻断流程——这与「模块不可执行时只降级依赖声明」是同一处置。只有该声明同时命中 §7.2 时才停下回流。

不得因为仓库缺少某条通道就把本可自动化的逻辑改判成 `manual_acceptance`：缺通道是能力缺口，不是人工资格。
