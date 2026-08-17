# {{project}} / {{story_name}} - Alpha 测试（单仓功能级 GWT 验收用例）

> 范围：单仓功能级验收用例（GWT 结构，框架无关）。**以 L3 接口级功能验证用例为主**（后端=API 接口级契约，前端=mock 集成级）；公共代码/算法代码等辅助 L4 UT。
> 用例标识 `AT-{{story_id}}-NNN`，向上追溯 `story-delta-spec.md` 的 SC-/BR- 锚点。
> 本文件只承载 What to test（验收场景/标准）；具体测试代码（How to test）与完成状态由 `tasks.md` Step 要点 + checkbox 承载。
> 黑盒（用户视角）测试用例由测试人员手工执行（`*-testcase.md`，测试侧独立产出），不在本文件。

## 1. 测试框架声明

> 来自 tasks.md TaskPacket 头的 `test_framework` 字段（sdd-task 探测结果，见 `references/test-framework-detection.md`）。

| project_type | 主测试框架 | 辅助测试框架 | 测试目录 | 探测信号 |
|--------------|-----------|-------------|----------|----------|
| backend\|frontend |  |  |  |  |

## 2. GWT 功能验收用例

> 框架无关的功能级用例（What to test）。**以 L3 接口级功能验证为主**；公共代码/算法代码等辅助 L4 UT。
> 每条用例分配 `AT-{story_id}-NNN` 标识，向上追溯 SC-/BR- 锚点（见 `references/acceptance-criteria-extraction.md`）。

### 2.1 后端 API 接口级用例（仅 project_type=backend，主）

> 格式：Given 请求（方法+路径+请求体/参数+预置数据） / When 调用 API / Then 响应（状态码+响应体+副作用断言）

#### AT-{{story_id}}-001: <用例标题>

- **追溯**: SC-<X>, BR-<Y>
- **层级**: L3 单服务单接口集成
- **Given**:
  - 请求方法: `POST`
  - 请求路径: `/api/v1/<资源>`
  - 请求体: `{ "<字段>": "<值>" }`
  - 预置数据: <数据库/缓存预置状态>
- **When**: 调用上述 API
- **Then**:
  - 响应状态码: `201`
  - 响应体: `{ "<字段>": "<非空>" }`
  - 副作用: <数据库/消息/缓存变化断言>

#### AT-{{story_id}}-002: <异常/反向场景用例标题>

- **追溯**: SC-<X>, BR-<Y>
- **层级**: L3 单服务单接口集成
- **Given**:
  - 请求方法: `POST`
  - 请求路径: `/api/v1/<资源>`
  - 请求体: `{ "<字段>": "<非法值>" }`
- **When**: 调用上述 API
- **Then**:
  - 响应状态码: `400`
  - 响应体: `{ "error": "<错误码>", "message": "<错误消息>" }`
  - 副作用: 无（数据库无新增）

### 2.2 前端 mock 集成级用例（仅 project_type=frontend，主）

> 格式：Given 组件状态+mock API 响应 / When 用户交互 / Then 渲染结果+API 调用断言

#### AT-{{story_id}}-001: <用例标题>

- **追溯**: SC-<X>, BR-<Y>
- **层级**: L3 mock 集成
- **Given**:
  - 组件: `<组件名>`
  - 初始状态: <组件/表单初始状态>
  - mock: `<METHOD> <API路径>` → 返回 `<状态码> { <响应体> }`
- **When**: 用户<交互动作>（输入/点击/路由跳转）
- **Then**:
  - 渲染: <渲染结果断言>
  - API 调用断言: `<METHOD> <API路径>` 被调用 <N> 次，请求体含 `<字段>=<值>`
  - 路由: <跳转目标（如适用）>

### 2.3 L4 单元测试用例（按需，辅助——公共代码/算法/状态机）

> 仅当 L3 接口级用例无法覆盖的内部逻辑（公共工具/算法计算/状态机转换/纯函数）时补充。

#### AT-{{story_id}}-NNN: <用例标题>

- **追溯**: BR-<Y>
- **层级**: L4 UT
- **Given**: <内部状态/输入>
- **When**: <调用内部方法>
- **Then**: <返回值/状态变化>

## 3. 覆盖矩阵

> 验收场景视角：SC-/BR- 需求锚点 → AT- 用例（**不含 Task 列**——Task 覆盖在 tasks.md 追溯表）。每条 SC-/BR- 至少被一条 AT- 覆盖；缺口须 Stop 回流。

| SC-/BR- 锚点 | 锚点描述 | 覆盖用例(AT-) | 缺口 |
|--------------|----------|--------------|------|

## 4. 完成前验证门禁（verification-before-completion）

- [ ] 每条 SC-/BR- 锚点至少被一条 AT- 用例覆盖（覆盖矩阵无缺口）
- [ ] AT- 用例与 tasks.md Task 可追溯（AT- → Task N 在 tasks.md 追溯表）
- [ ] tasks.md 每个 Task 的 Step 1-6 checkbox 全部勾选（红绿验证通过）
- [ ] 未通过修改测试来适配实现
