# 接缝字段：语义、取值与缺席行为

本文件是 [SKILL.md](../SKILL.md)「接缝字段」一节的细则。消费端的对应规则在 `sdd-dev-frontend/references/phase-entry.md` 的「上游接缝字段」小节。

## 一、为什么是字段而不是新文件

产物仍是 `tasks.md` + `alpha-tests.md` 两份，接缝只是 TaskPacket 头上的几个 `key=value`。三个理由：

- 下游硬门禁 1 把 `tasks.md` 定为**唯一执行清单与进度真相**，`alpha-tests.md` 是**唯一证据账本**；另立第三份文件要连带改下游的前置条件、工件管理与路径变量三处。
- **字段缺席即等价于旧格式**，所以不需要版本号、兼容期或 legacy adapter。旧 `tasks.md` 与走了降级内联路径的 `tasks.md` 都不带这些字段，下游按既有兜底执行即可。
- TaskPacket 头已经有 `frontend_design_path=` 这个先例，格式与位置都不用新发明。

## 二、七个字段

写在 TaskPacket 头，与既有 `project=` / `test_framework=` 同行、`|` 分隔。

### `baseline_source`（必填）

| 取值 | 含义 |
| --- | --- |
| `prototype` | 有 HTML 原型且确含本 Story 页面 |
| `reference_page` | 无原型，用仓内同类已上线页面类比 |
| `text_spec` | 只有可逐条落地的文字规格 |
| `none` | 三者皆无（同时进「已知缺口」） |

判定细则见 [baseline-source.md](./baseline-source.md)。**这是唯一必填的接缝字段**，因为它在下游触发的是结构性分支（决定整个 Phase A1 跑不跑）。

### `prototype_dir`（第 1 档必填）

原型目录路径。下游拿它作 `<prototype-dir>` 的候选值——唯一命中就不占提问位，省用户一轮。

### `reference_route`（第 2 档必填）

倾向作参照的路由，**并注明「候选，待下游确认」**。选参照页是决策，归下游 Phase A2 确认门；本 skill 只给候选与倾向。

### `affected_routes`

逗号分隔的路由清单。下游用于目标页面识别、风险闭包与候选阶段跨页验证范围。

### `required_states`

取 `hover,focus,disabled,selected,loading,empty,overflow` 的子集，只列**AC、AT 或设计输入明确要求**的状态。下游把它作为验证组合输入，决定在哪个候选场景合并采集；字段本身不要求逐 Task 执行。

不要把七个全写上凑数——每个状态在下游都要真的造出来并采集一次，多写一个就多一次浏览器动作。

### `restore_tasks`

还原轮的 Task 编号清单。下游用它少猜形态。问题一判「无静态呈现」时**留空**，不写 `none` 字样。

### `risk_triggers`

逗号分隔的规范 token 清单。token 与判据以 [`sdd-dev-frontend/references/validation-policy.md`](../../sdd-dev-frontend/references/validation-policy.md#三风险触发器) 为唯一来源；本 skill 只填写计划事实能直接证明的项。典型映射：

- 改静态结构或样式 → `visual`
- 改交互或状态迁移 → `interaction`
- 改路由/入口 → `navigation`
- 明示修改公共组件/样式/共享类型 → `shared-boundary`
- 权限或租户规则 → `auth`
- 服务端写入/删除 → `write`

`new-pattern`、`unknown-deps` 等需要代码勘察才能判断的 token 不猜，由下游补充。缺席表示“上游未声明”，不表示低风险。

## 三、三条消费约定

写清这三条，字段才不会变成第二个真相源。

**1. 索引不是判据。** `restore_tasks` 与实际切分冲突时以 Task 内容为准——那个 Task 的文件清单里有没有样式文件才是判据。下游本来就能从切分推断形态，字段只是省一次推断。

**2. 输入不是冻结。** `baseline_source` 与 `reference_route` 进的是下游 Phase A2 确认门的**输入**，不是冻结结果。用户在那个门里确认的不只是期望值，还有「本次拿什么当基线」。本 skill 不得把它写成既定结论（硬门禁 3）。

**3. 字段不复制正文。** `affected_routes` / `required_states` / `risk_triggers` 喂的是下游已经在读 `tasks.md` 的验证编译器。Task 描述仍是内容来源，字段只作索引；下游用仓库事实与最终 diff 校正，不把字段当冻结结论。

## 四、下游会核实，但这不是可以随便填的理由

下游 Phase 0 会核 `prototype_dir` 是否真的存在且含 HTML，核不上就自行重判并记一行「上游声明 `<值>`，实测不成立，改判 `<档>`」。

这个机制是最后一道网，不是免责条款。填错的实际代价：

| 错误 | 后果 |
| --- | --- |
| 无原型却写 `prototype` | 下游按第 1 档跑抽取管线，取不到取值再回退，白跑一轮 |
| 有原型却写 `text_spec` | 下游**跳过整个 Phase A1**，把有基线的 Story 按无基线执行，还原承诺被无故收窄 |
| `required_states` 写多了 | 候选验证组合会加入无验收来源的状态，扩大浏览器场景 |
| `reference_route` 写成结论 | 越过用户确认门替用户选了基线 |
| `risk_triggers` 漏掉明显事实 | 下游初始组合偏窄；最终 diff 会纠正，但会增加返工与重编译 |

## 五、示例

第 1 档，两个页面：

```
**TaskPacket:** project=RcpWebsite | codespec_path=... | story=下载中心 | test_framework=Playwright | search_paths=src/shared | project_type=frontend | frontend_design_path=... | baseline_source=prototype | prototype_dir=prototype/download-center/ | affected_routes=/download-center,/probe-record | required_states=loading,empty,disabled | restore_tasks=T1,T2 | risk_triggers=visual,interaction,navigation
```

第 3 档，无原型（本仓最常见的形态）：

```
**TaskPacket:** ... | project_type=frontend | frontend_design_path=... | baseline_source=text_spec | affected_routes=/download-center | required_states=loading,empty,disabled | restore_tasks=T1 | risk_triggers=visual,interaction
```

无静态呈现（纯逻辑改造）：

```
**TaskPacket:** ... | project_type=frontend | baseline_source=none | affected_routes=/probe-record | required_states= | restore_tasks= | risk_triggers=interaction
```

最后一例里两个空值是有意义的，不是漏填：`required_states=` 表示本 Story 不需要状态验证，`restore_tasks=` 表示没有还原轮。Task 正文里另有一行说明为什么没有还原 Task。
