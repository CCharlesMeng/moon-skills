# {{project}} / {{story_name}} - 单仓实现计划

> **For agentic workers:** 使用 `/sdd-dev-subagent`（推荐，每微服务一个 subagent）或 `/sdd-dev`（当前会话 inline TDD）逐任务执行本计划，checkbox 跟踪。

**Goal:** <!-- 一句话：本仓实现什么 -->

**Architecture:** <!-- 2-3 句：本仓实现方案 -->

**Tech Stack:** <!-- 关键技术栈 -->

**TaskPacket:** project={{project}} | codespec_path= | story={{story_name}} | test_framework= | search_paths= | project_type=backend|frontend | frontend_design_path=

<!-- project_type=frontend 时另填两条测试通道（判据见 sdd-task/references/test-framework-detection.md §2）：
     component_test_status= | component_test_framework= | browser_test_status= | browser_test_framework= -->

---

## 1. 项目边界

| 范围内 | 范围外 |
|--------|--------|

> `project_type=frontend`：实现限于本前端仓 `search_paths[]`；REST 契约引用领域 design，不改 backend 仓。  
> `project_type=backend`：实现限于本后端仓；**禁止**写入前端组件树/IFC/样式任务。

## 2. 文件结构（File Structure）

> 锁定分解决策。每个文件单一职责；变更一起的文件应放在一起。  
> frontend：对齐 `story-delta-frontend-design` 组件树；backend：对齐领域 design 调用链。

| 文件/模块 | 变更（新建/修改） | 职责 |
|-----------|-------------------|------|

## 3. 实现设计要点

### 3.1 API/契约

> frontend：IFC 切片（来自 frontend-design）+ 对领域 REST 的引用路径。  
> backend：对外/对内 API 与持久化（来自 requirement/story-delta-design）。

### 3.2 数据/配置

### 3.3 错误处理

### 3.4 前端烘焙（仅 project_type=frontend）

| 项 | 内容 |
|----|------|
| 组件树摘要 | |
| IFC 切片 | |
| testability 锚点 | |
| style-reference 路径（可选） | |
| 降级标记（若无 frontend-design） | |

## 4. 用例追溯表

> 执行视角：AT- 用例 → Task（**不含 SC-/BR- 列**——需求锚点覆盖在 alpha-tests.md 覆盖矩阵，此处不重复）。

| AT- 用例标识 | 用例标题 | 覆盖任务 |
|-------------|----------|----------|

## 5. 执行规则

- **Iron Law：** 没有失败的测试，就不写实现代码。
- **No Placeholders 铁规：** 禁止 TBD、TODO、"适当处理错误"、"类似任务 N"、无要点的步骤；每步必须含可执行要点（文件路径 + 行为/逻辑要点），但不要求全量代码。
- **禁止修改测试以适配实现**；测试表达验收契约。
- 仅在确认的 `search_paths[]` 内执行；超出须记录原因并回流 Design。
- 每条任务必须 trace 到 `alpha-tests.md` 的 AT- 用例标识；Step 1 RED 测试要点须基于 TaskPacket 头声明的 `test_framework`（后端=API 接口级测试，前端=mock 集成级测试）。具体代码由 Dev 阶段基于要点 + alpha-tests GWT 用例 + 探测框架现写。

## Task List（任务清单）

> 每个 Step 写**要点描述**（不写全量代码），前缀 `- [ ]` checkbox；勾选即代表该 Step 完成。

### Task 1: <组件名> [用例: AT-{{story_id}}-001]

**Files:**
- Create: `精确路径`
- Modify: `精确路径:行号`
- Test: `精确测试路径`

- [ ] **Step 1: 写失败测试（RED）** — 测试要点：测什么行为 + 关键断言 + 测试文件路径（不写完整测试代码）

- [ ] **Step 2: 运行测试，确认因正确原因失败**

Run: `精确测试命令`
Expected: FAIL — <一句话预期失败点>

- [ ] **Step 3: 写最小实现（GREEN）** — 实现要点：改哪个类/方法 + 核心逻辑（不写完整实现代码，YAGNI）

- [ ] **Step 4: 运行测试确认通过 + 全量回归仍绿**

Run: `精确测试命令`
Expected: PASS

- [ ] **Step 5: （按需）REFACTOR，保持绿色**

- [ ] **Step 6: 提交** — 勾选即代表 Task 完成（含红绿验证通过）

```bash
git add <files>
# commit message（内联提交规范，见 sdd-task「提交规范」章节）：
#   【问题单号 Defect】{work_item_id}
#   【修改说明 Modification】{type}({scope}): {description}
# variables: work_item_id={需求单号或BUG单号}, type=feat|fix|refactor|docs|test, scope=<module>, description=<task-summary>
git commit -m "【问题单号 Defect】{work_item_id}" -m "【修改说明 Modification】{type}({scope}): {description}"
```

---

## 6. 计划自审清单

- [ ] **AT- 用例覆盖：** 每条 AT- 用例都指向具体 Task N，且向上追溯 SC-/BR- 锚点完整
- [ ] **占位符扫描：** 无 TBD/TODO/无代码步骤/"类似任务 N"
- [ ] **类型一致性：** 跨任务的方法签名、类型名、属性名一致
- [ ] **框架一致性：** Step 1 RED 测试代码使用的框架与 TaskPacket 头 `test_framework` 声明一致

## 7. 风险与回滚

| 风险 | 缓解措施 | 回滚方案 |
|------|----------|----------|
