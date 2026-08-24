# 声明驱动的验证策略

本文件是 `sdd-dev-frontend` 选择验证动作的唯一规则源。进入 Phase 0 编译初始验证组合、进入 Phase C 按最终 diff 重编译时完整读取；其他阶段只引用已经落盘的组合。

## 一、总纲

**门禁约束声明，风险选择动作。** 先确定本 Story 准备对外声称哪些验收声明成立，再为每条声明选择最小充分证据。不得因为某个动作通常存在就默认执行，也不得因为动作未执行就把无关声明一起判失败。

四条声明诚信门在任何 Story 上成立：

1. **来源诚信**：期望值来自上游 AC、外部基线或用户确认的工作假设；当前实现不反向定义期望值。
2. **状态诚信**：声明状态严格按 [共享执行契约的状态表](../../../docs/skills/frontend-sdd/执行契约.md#声明与状态)判定，不新增第四种状态、不用状态位表达进度。
3. **证据诚信**：`PROVEN` 的证据覆盖该声明、使用正确环境，并对最终相关依赖仍新鲜。
4. **缺陷诚信**：声明范围内已确证的阻断缺陷清零；未清零就不能把受影响声明写成 `PROVEN`。

RED/GREEN、命令、浏览器矩阵、截图和独立检视都是证据策略，不是声明诚信门。按下文触发，未触发即不执行、不生成空工件。

## 二、输入与输出

从 `tasks.md` 读取 AC/AT、`affected_routes`、`required_states`、`risk_triggers` 与文件范围；再用仓库 baseline、实际 diff 和运行限制校正。上游字段是候选事实，实测冲突时以实测为准并登记原因。

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

`visual` / `navigation` / `shared-boundary` / `build-config` 的下限由 `<skill-dir>/scripts/classify_diff.py --repo-root <repo-root> --base-ref <base-ref> --out <临时目录>/diff-facts.json` 从 diff 机械给出，组合只能在下限之上扩；确要收窄某条下限触发器时写入 `portfolio_narrowed[]` 并给出理由，它会进 `dev-review.md`。聚合器拒绝既不承接也未署名收窄的组合。

## 四、验证模块

| 模块 | 触发 | 最小充分证据 |
| --- | --- | --- |
| `causal` | 每个被实现改动的验收声明 | 改动前能暴露缺口、改动后能证明声明的同一通道；优先测试 RED/GREEN，还原用冻结契约，类型/构建类可用编译失败→通过 |
| `render` | `visual` | 变更区块的冻结契约；只执行规则要求的 static/render 层，视觉盲区才截图 |
| `journey` | `interaction` / `navigation` / `auth` / `write`，且自动化 causal 证据不足以覆盖真实运行时 | 合并后的最短用户操作序列，覆盖受影响 AC 与必要异常路径 |
| `targeted-quality` | 改产品代码 | 覆盖改动依赖闭包的最窄 test/typecheck/lint/build 子集；仓库没有可安全收窄的入口时升级 |
| `regression` | `shared-boundary` / `navigation` / `auth` / `write` / `unknown-deps` / `build-config` | 受影响入口与下游消费者的回归；依赖闭包不可靠时运行 `runtime.md` 记录的全部质量命令 |
| `review-restore` | `visual` 且存在冻结 R 行 | 按最终 diff 重跑**全部已冻结区块**的契约，再从 R1–R6 中分配这些区块涉及的维度 |
| `review-layout` | `visual` 且跨页、跨视口、共享样式或 `required_states` 含 overflow | 从 L1–L6 中只分配命中风险的维度，页面范围只覆盖风险闭包 |
| `review-convention` | `new-pattern`、`shared-boundary`、`build-config`，或 diff 触碰 PATTERN 约束且没有确定性检查覆盖 | 从 C1–C7 中只分配 diff 真正触碰的 PATTERN 维度 |
| `review-quality` | `async-state` / `auth` / `write` / `performance` / `shared-boundary`，或实现引入非平凡状态与副作用 | 从 Q1–Q8 中只分配实际风险维度 |
| `self-test` | `journey` 存在且现有自动化证据不能直接证明全部受影响声明 | 独立判断对应 F/REG 行；只覆盖验证组合列出的声明 |

同一原始动作只执行一次。多个模块可引用同一条命令或浏览器场景，但各自保留判断。独立判断只在对应 review 模块被触发时成立，不要求五个角色成套出现，也不要求一个角色扫完它的全部分类。

`render` 与 `review-restore` 跑的是同一套契约，范围不同：`render` 在 Phase B 只跑当前变更区块，`review-restore` 在 Phase C 按最终 diff 重跑全部已冻结区块。后来的 Task 改了公共样式时，先前区块的 GREEN 只有在这里才会被推翻。

## 五、执行时机

- Phase B 只取得当前 Task 的 `causal` 证据；`render` 只跑当前变更区块的契约。把状态矩阵、跨页检查和宽回归留给候选阶段。
- Phase B 修复中只运行失败定位所需的最窄动作，不执行候选级全量门。
- Phase C 按最终 diff 重编译验证组合；新增触发器只能增加模块。批量执行候选模块，先命令、后浏览器，再派适用的独立检视。`review-restore` 被选中时，重跑契约属于主 agent 的取证动作，在派发前完成。
- Phase D 只失效依赖命中的证据和判断。修复引入新触发器时把对应模块加入组合；无触发器不得扩大重跑。最终组合没有全量模块时不补「最终全量门」；命令键仍新鲜就继续复用，不为收尾重跑一遍。

## 六、升级与收口

出现以下任一信号时立即重编译组合：依赖闭包无法确定、基线冲突、工具无法判定、实际 diff 超出计划文件、出现新的运行时副作用、定向检查暴露跨范围失败。

收口逐声明判定，判据只用 [共享执行契约的状态表](../../../docs/skills/frontend-sdd/执行契约.md#声明与状态)，本文件不复制一份。

`UNVERIFIED` 与 `DEFERRED` 都不计入已验收。它们必须进入 `alpha-tests.md`、`dev-review.md` 与最终状态限定，但只影响依赖它们的声明，不把无关声明一并降级。
