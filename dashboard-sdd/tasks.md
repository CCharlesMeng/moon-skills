# dashboard-sdd / 风险客户看板体验 — 单仓实现计划

**Goal:** 让使用者在风险客户看板中快速浏览高密度列表、展开详情，并理解风险摘要。

**关键结构决策:** 人工验收只覆盖机器无法稳定判断的动效体感与业务文案；滚动容器、展开状态和键盘可达等确定性行为仍应由自动化通道覆盖，不在本样例中用人工项替代。

**TaskPacket:** project=dashboard-sdd | codespec_path=dashboard-sdd | story=US1 | verification_schema=v2 | test_framework= | component_test_status=unknown | component_test_framework= | browser_test_status=unknown | browser_test_framework= | search_paths=dashboard-sdd | project_type=frontend | frontend_design_path=未见 | baseline_source=text_spec | prototype_dir= | reference_route= | affected_routes=dashboard-sdd/demo.html | required_states=overflow | restore_tasks= | risk_triggers=interaction

## 项目边界

| 范围内 | 范围外 |
| --- | --- |
| `demo.html` 的列表滚动体感、卡片展开动效、风险摘要文案 | 后端数据、风险算法、账号权限与生产发布 |

## 页面、路由与组件层级

| 路由 | 页面 / 入口 | 本 Story 的变化 |
| --- | --- | --- |
| `dashboard-sdd/demo.html` | 风险客户看板候选页 | 提供可滚动客户列表、可展开风险卡片和待业务确认的摘要文案 |

## 模块与文件

| 文件 | 类型 | 新建/修改 | 职责与对外导出 | 复用的既有资产 | Task |
| --- | --- | --- | --- | --- | --- |
| `dashboard-sdd/demo.html` | 页面 | 新建 | 提供本地可打开的人工验收候选页面 | 无，原因：独立演示样例 | T1 |
| `dashboard-sdd/alpha-tests.md` | 验收账本 | 新建 | 登记待人工验收项与声明状态 | `sdd-dev-frontend` 现有表头 schema | T1 |

## 用例追溯

| AT | 标题 | 验证范围 | 验证方法 | Task |
| --- | --- | --- | --- | --- |
| AT-US1-001 | 高密度列表滚动与卡片展开动效自然 | S2_PAGE | manual_acceptance | T1 |
| AT-US1-002 | 风险摘要文案符合业务表达 | S2_PAGE | manual_acceptance | T1 |

## Task List

### Task 1: 准备风险客户看板人工验收候选 [用例: AT-US1-001, AT-US1-002]

**形态:** 逻辑（人工验收）

**受影响声明:** AT-US1-001、AT-US1-002

**人工依据:** `motion_judgment` 用于判断滚动与展开是否自然；`content_approval` 用于确认业务文案含义和语气。两项都不替代可机器判定的交互行为。

**验收环境与所需证据:** Chrome、1920×1080、浏览器缩放 100%；动效项留 15 秒录屏，文案项留业务审批记录或截图。

**Files:**

- Create: `dashboard-sdd/demo.html` — 人工验收候选页面
- Create: `dashboard-sdd/alpha-tests.md` — 待人工验收权威登记

- [x] **Step 1: 实现人工验收候选** — 页面可滚动并可展开卡片，风险摘要已展示；本 Task 不新增自动化测试文件
- [x] **Step 2: 让受影响范围的静态页面加载通过**
- [x] **Step 3: 登记待人工验收并提交** — `manual_outcome=NOT_RUN`、`claim_status=UNVERIFIED`；不填验收人与验收时间

## 风险与回滚

- 风险：人工结论可能因设备、浏览器缩放或数据密度不同而变化，因此验收环境必须随证据一起记录。
- 回滚：删除本演示目录即可，不影响仓库中的 Skill 实现。
