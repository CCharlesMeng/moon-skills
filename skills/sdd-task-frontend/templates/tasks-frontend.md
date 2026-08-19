# {{project}} / {{story_name}} — 单仓实现计划

**Goal:** <!-- 本仓实现什么 -->

**Architecture:** <!-- 只写影响验收的结构决策 -->

**TaskPacket:** project={{project}} | codespec_path= | story={{story_name}} | test_framework= | search_paths= | project_type=frontend | frontend_design_path= | baseline_source= | prototype_dir= | reference_route= | affected_routes= | required_states= | restore_tasks= | risk_triggers=

字段语义见 [前端 SDD 执行契约](../../../docs/skills/frontend-sdd/执行契约.md)。

## 项目边界

| 范围内 | 范围外 |
| --- | --- |

## 文件结构

| 文件/模块 | 新建/修改 | 单一职责 |
| --- | --- | --- |

## 验收契约

只写会改变 AC 或 mock 集成断言的细节：URL、字段、状态迁移、用户可见结果、必要文案和 testability 锚点。实现组织与视觉数值留给 Dev 和冻结基线。

### API、数据与错误结果

<!-- 方法、URL、请求/响应字段、枚举、失败时的可观察结果 -->

### 还原来源（`baseline_source != none` 时）

| 项 | 内容 |
| --- | --- |
| 基线档位 | <!-- prototype / reference_page / text_spec --> |
| 视觉来源 | <!-- 原型；或待确认的参照页候选；或文字规格章节 --> |
| 页面与区块 | <!-- 路由 + 职责单一的区块名；不写 class 锚点 --> |
| 必测状态 | <!-- 与 required_states 一致 --> |
| 已知缺口 | <!-- 无则写“无” --> |

### testability 锚点

| `data-automation-id` | 所在元素 | AC / AT |
| --- | --- | --- |

## 用例追溯

| AT | 标题 | Task |
| --- | --- | --- |

## Task List

顺序：跨页公共骨架 → 每页还原 → 该页逻辑。复制下面形状生成 Task；机械 Task 仅在变化确无行为分支时使用。

### Task N: <名称> [用例: AT-...]

**形态:** 还原 / 逻辑 / 机械

**视觉来源、路由、区块:** <!-- 仅还原轮 -->

**Files:**

- Create: `<精确路径>`
- Modify: `<精确路径>`
- Test/Style: `<精确路径>`

- [ ] **Step 1: 暴露缺口** — 受影响声明：<...>；形态与改动前可观察缺口：<...>
- [ ] **Step 2: 确认原因** — <什么现象说明原因判断正确>
- [ ] **Step 3: 写最小实现** — <改哪些文件，达成什么可观察行为>
- [ ] **Step 4: 证明声明** — <哪些声明应为 PROVEN，最小可观察结果是什么>
- [ ] **Step 5: 按需重构**
- [ ] **Step 6: 记录证据并提交** — 回填 `alpha-tests.md`，沿用 `sdd-task` 提交规范

## 计划自审

- [ ] 每条需求锚点 → AT → Task 的追溯完整。
- [ ] 每个 Task 只有一种形态；多轮有不可拆理由并分别引用声明。
- [ ] 每页还原先于逻辑；还原 Task 独占样式文件；没有收尾样式 Task。
- [ ] Step 3 只有文件与可观察行为，没有实现代码、内部 helper、指定 API 或视觉数值。
- [ ] 全文没有精确验证命令、全量回归、浏览器矩阵或独立检视安排。
- [ ] 同一契约只写一次；没有 TBD、TODO、空步骤或“类似任务”。
- [ ] TaskPacket 与正文一致，风险 token 有直接计划事实。

## 风险与回滚

| 风险 | 缓解 | 回滚 |
| --- | --- | --- |
