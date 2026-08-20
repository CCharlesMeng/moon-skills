---
name: sdd-task
description: 基于 requirement-design.md 的「关联 Story 设计」表格,逐个代码仓创建 Story 级单仓实现计划（tasks.md，含框架感知 TDD 任务清单）与 alpha-tests.md（GWT 功能用例 + 红绿灯证据账本）。Use when creating codebase project codespec/changes entries from a confirmed StoryPacket.
license: MIT
compatibility: Requires codespec CLI with sdd-multiple-repo schema.
metadata:
  author: codespec
  version: "3.2"
---

# 前置条件

## 通用前置条件
- **⚠️ 技能启动时必须执行打点上报**：`codespec telemetry track --event-value "sdd-task"`

# TaskPacket 与单仓实现计划

## 使用原则

本 Skill 是自包含能力包。执行时只依赖当前业务 Workspace、用户输入、代码事实和本文件;禁止读取部门私有流程目录、其它 command 文件或其它 Skill。

**CLI 命令强制约束**:
- 必须优先使用 `codespec status --change <fe-change> --json` 查看当前状态
- 必须优先使用 `codespec instructions <artifact> --change <fe-change> --json` 获取 schema 指令
- 在目标代码仓下通过 `codespec new change <story-dir> --path codebase/<project>` 创建 Story 级工作目录
- CLI 不可用时才允许人工替代,必须说明未执行自动校验

---

## 命名与变更识别(强制,极其重要)

本阶段涉及两类"名称",**绝不可混用**:

### 1. FE 变更名 = 唯一真正的 change name

格式固定:

```
<iterative-version>/<requirement-id>-<requirement-name>
```

示例:`11.6.2/FE2023991939391-用户紧急联系人`

- 这是全流程中**唯一**的真正 `<change>`,所有 `codespec status --change ...`、`codespec instructions ... --change ...` 的 `--change` 参数**必须**使用此名称。
- `requirement-id` 为 DevOps 工单号（`FE...`），**不是** Feature 树节点 ID。

- 本阶段**不创建**新的 requirement 变更;若缺失,运行 `codespec list --json` 定位,未果则 Stop。

### 2. Story 工作目录名 = 仅用于落盘路径,不是 change name

格式:

```
<requirement-id>-<requirement-name>/<us-id>-<us-name>
```

示例:`FE2023991939391-用户紧急联系人/US20250510178479-新增用户紧急联系人配置`

- **不含**迭代版本号,**绝不可**作为 `--change` 参数传入。
- 仅用于 `codespec new change <story-dir> --path codebase/<project>` 的第一个位置参数,用来在 project 子目录下开辟 Story 级工作目录 `codebase/<project>/codespec/changes/<story-dir>/`。
- 创建完成后,一切状态/schema 查询仍走 **FE 变更名**。

### 错误对照(必须避免)

| 场景 | 正确 | 错误 |
|------|------|------|
| 查状态 | `codespec status --change 11.6.2/FE2023991939391-用户紧急联系人 --json` | `codespec status --change FE2023991939391-用户紧急联系人/US20250510178479-新增用户紧急联系人配置 --json` |
| 取 schema | `codespec instructions tasks --change 11.6.2/FE2023991939391-用户紧急联系人 --json` | `codespec instructions tasks --change FE2023991939391-用户紧急联系人/US... --json` |
| 建 Story 目录 | `codespec new change FE2023991939391-用户紧急联系人/US20250510178479-新增用户紧急联系人配置 --path codebase/CBCCrmCoreService` | 带上 `11.6.2/` 前缀,或省略 `--path` |

---

## 前置条件

- FE 变更(`<iterative-version>/<requirement-id>-<requirement-name>`)已存在,可通过 `codespec list --json` 或 `codespec status --change <fe-change> --json` 检出。
- `/sdd-design` 已完成,`requirement-design.md` 及「关联 Story 设计」表格已填写完整,`US ID` 已由 `sdd-create-us` 回填,`归属微服务`已按"一个微服务一行"拆分。
- 当前 Story 的 `story-delta-spec.md`（含 SC- 场景锚点、BR- 业务规则、§5 验收场景摘要 GWT）、`story-delta-design.md` 已确认。**不依赖** `story-delta-testdesign.md` / `story-delta-testspec.md` / `story-delta-testcase.md`（测试产物由测试侧独立产出，开发侧不消费）。
- 每个受影响代码仓已存在 `codespec/` 目录与 `codespec/index.md`（`init/` 为参考布局，非强制）。

---

## 读取范围

1. 需求级 spec/design（含 `requirement-design.md` 中「关联 Story 设计」表格,用于驱动遍历）。**不读** requirement-testspec/testdesign/testcase。
2. 当前 Story 的 `story-delta-spec.md`（SC- 场景锚点、BR- 业务规则、§5 验收场景摘要 GWT）、`story-delta-design.md` 增量。**不读** story-delta-testspec/testdesign/testcase。
3. 基线 `story-spec.md`、`story-design.md`。
4. `code-repository-index.yaml`(核对代码仓路径；用 `backend[]`/`frontend[]` 判定 `type`)。
5. 每个受影响代码仓的 `codespec/index.md`（及 `init/` 参考布局若存在）与 Design 已确认的必要代码切片。
6. **前端产物（仅当本行 `归属微服务` 对应 `type=frontend` 时读取；backend 行禁止读取）**：
   - 包根 `requirement-frontend-design.md`（共享技术栈/IFC/路由；若缺失则降级：仅用领域 design 的 API 引用，并在 tasks.md 标注 `⚠️ 降级：无 requirement-frontend-design`）
   - 同 Story 目录 `story-delta-frontend-design.md`（页级组件树/IFC 切片；若缺失同上降级）
   - 可选：同目录 `testability-map.md`、包根 `style-reference/style-reference.md`（仅写入路径提示，不把样式正文抄进 backend tasks）
7. **知识底座（consume 三步，stage=task）**：
   1. `codespec knowledge consume --stage task --projects "<关联 Story 设计表格中的代码仓>" --keywords "<组件/技术关键词>" --json`（引擎从 code-repository-index 查各 repo 的 `language`，按 `(stage=task, kind=specification, scope=coding|testing, language=<repo>)` 过滤——Java 仓只命中 Java 规范，TS 仓只命中 TS 规范）
   2. 按 `must_read` 读原文；`browse` 条目已带 `summary`/`retrieval_hint`，据此判断是否需要进入目录精读，不必先手工 ls；裁剪规范写入 tasks.md「知识 trace」小节（列出 `entries[].id`）
   3. `gaps` 非空 → 记入 knowledge-gaps 降级继续。Dev 阶段会直接 consume 语言规范主规范原文（不再只依赖 trace）。**禁止**手工过滤 index entries。
8. **测试框架探测（新增）**：对每个目标代码仓，按 `references/test-framework-detection.md` 的探测规则扫描构建文件（pom.xml/build.gradle/go.mod/package.json）与测试目录结构，识别测试框架（后端 JUnit/Mockito/Karate/Spock/TestNG/RestAssured；前端 Jest/Vitest/Mocha/Cypress/Playwright/@testing-library），将探测结果写入 tasks.md TaskPacket 头的 `test_framework` 字段。探测失败 → Stop 并回流 Design。
9. **验收标准提炼（新增）**：按 `references/acceptance-criteria-extraction.md` 的业界需求分析方法，从 `story-delta-spec.md` 的 SC-/BR- 提炼单仓功能级验收用例（后端=API 接口级契约，前端=mock 集成级），分配 `AT-{story_id}-NNN` 标识，写入 alpha-tests.md 的 GWT 用例章节。

---

## 执行步骤

### Step 0: 锁定 FE 变更名

运行 `codespec list --json`,定位形如 `<iterative-version>/<requirement-id>-<requirement-name>` 的 active 变更,记为 `<fe-change>`;并 `codespec status --change <fe-change> --json` 确认存在。未果则 Stop。

**本阶段所有 `--change` 参数固定使用 `<fe-change>`,严禁替换。**

### Step 1: 解析「关联 Story 设计」表格

从 `requirement-design.md` 的 `## 关联 Story 设计` 章节提取每行,构造 `(Story, 代码仓)` 任务:

| 字段 | 用途 |
|------|------|
| `US 标题` | Story 工作目录名的 `<us-name>` |
| `US ID` | Story 工作目录名的 `<us-id>` |
| `FE ID` | Story 工作目录名的 `<requirement-id>`(须与 `<fe-change>` 内 requirement-id 一致) |
| `归属微服务` | 目标代码仓,用于 `--path codebase/<project>`；须用 `code-repository-index.yaml` 判定 `type=backend|frontend` |

requirement-name 从 `requirement-design.md` 上下文或变更目录名获取。

**前后端隔离**：`type=backend` 行不得读取或引用 `*frontend-design*` / `ux-decode` / `style-reference`；`type=frontend` 行必须按下方「前端烘焙」写入本仓 `tasks.md`。

### Step 2: 按微服务依次处理(不跨仓并行)

对每个 `(Story, 代码仓)` 组合:

```bash
# 1) 查 FE 变更状态(--change 用 FE 变更名,带迭代版本号)
codespec status --change <iterative-version>/<requirement-id>-<requirement-name> --json

# 2) 取 schema 指令(--change 同样用 FE 变更名)
codespec instructions tasks        --change <iterative-version>/<requirement-id>-<requirement-name> --json
codespec instructions alpha-tests  --change <iterative-version>/<requirement-id>-<requirement-name> --json

# 3) 在目标代码仓下创建 Story 级工作目录
codespec new change <requirement-id>-<requirement-name>/<us-id>-<us-name> \
    --path codebase/<project>

# 4) 分流：
#    type=frontend → 路由 `sdd-task-frontend`（见 Step 2.4），本 Skill 不生成该行计划
#    type=backend  → 按 schema outputPath 落盘 tasks.md / alpha-tests.md
#                    到 codebase/<project>/codespec/changes/<requirement-id>-<requirement-name>/<us-id>-<us-name>/
# 5) type=backend 仅领域 design；前端烘焙归 sdd-task-frontend
```

### Step 2.4: 前端路由（仅 `type=frontend`）

`type=frontend` 的行**不在本 Skill 内生成计划**，整行交由 `sdd-task-frontend` 处理。前端 Task 的切分方式、失败证据形态、还原/逻辑分轨与基线源声明都是前端专有规则；写进公共主干会让后端行跟着承担前端语义。

**路由前 Step 2 的 1)～3) 必须已完成**：`<fe-change>` 已锁定、`codespec instructions tasks|alpha-tests` 已取到 schema、`codespec new change` 已建好 Story 工作目录。**`codespec` CLI 的全部调用留在本 Skill**，`sdd-task-frontend` 不碰 CLI，只按交接载荷生成内容并落盘。

交接载荷：把 Step 0-2 的 CLI 产出（fe_change、story_dir、project、schema 原文）、读取范围内收集的需求侧路径与知识底座结果、以及 `references/` 内两个 ref 文件路径，传给 `sdd-task-frontend`。agent 按"使下游无需 CLI 即可工作"的原则自行推导具体项。

返回后本 Skill 只做一件事：把它落盘的 `tasks.md` / `alpha-tests.md` 路径并入 Step 3 汇总，**不复核前端内容、不改写前端 Task**。前端行的产物质量由 `sdd-task-frontend` 自己的完成标准负责。

路由成功后，在 `tasks.md` TaskPacket 头写入 `routed=sdd-task-frontend`。后续 Step 2.5/2.6/4 通过读取此变量判断是否跳过，不依赖上下文记忆。

**兜底**：`sdd-task-frontend` 不可用时，按 Step 2.5～2.6 与 Step 4 的既有内联前端路径处理本行，在 TaskPacket 头写 `routed=inline-fallback`，并在 `tasks.md` 标注 `⚠️ 降级：未经 sdd-task-frontend`。降级产出不含前端切分规则与基线源声明，下游 `sdd-dev-frontend` 会退回「一个 Task 内多轮 6 步」执行。

### Step 2.5: 前端烘焙（仅 `type=frontend` 且 Step 2.4 走兜底）

> **TaskPacket `routed=sdd-task-frontend` 的行跳过本步。** 本步仅在 `routed=inline-fallback` 时执行。

将变更包内前端设计**固化进本仓 `tasks.md`**，使 Dev 无需再读变更包前端文档：

1. TaskPacket 头填写 `frontend_design_path=`（指向 `story-delta-frontend-design.md`，共享契约注明 `requirement-frontend-design.md`）。
2. §文件结构 / 实现设计：写入页级组件树、IFC 切片、testability 锚点；REST 对外 API **只引用**领域 `requirement-design` / `story-delta-design`，不在 FE tasks 重定义后端契约。
3. 若存在 `style-reference/style-reference.md`，在实现设计中写明对照路径（不整份粘贴）。
4. IFC↔API 缺口需后端补齐 → 记入 tasks 风险并回流 Design，**禁止**在 FE 仓改 BE 代码。

`type=backend`：**跳过本步**；tasks 只含服务/API/持久化/领域调用链。

### Step 2.6: 测试框架探测（新增，所有 project_type）

> TaskPacket `routed=sdd-task-frontend` 的行跳过本步。

对当前 `(Story, 代码仓)` 组合，执行测试框架探测：

1. 按 `references/test-framework-detection.md` 扫描仓根构建文件（pom.xml/build.gradle/go.mod/package.json）与测试目录结构。
2. 识别主测试框架 + 辅助测试框架 + 测试目录结构（后端双轨：集成框架用于 L3 API 测试，单测框架用于 L4 UT；前端组件测试框架）。
3. 将探测结果记为 `test_framework` 字段，写入 tasks.md TaskPacket 头（如 `test_framework=JUnit5+Mockito+Karate`）。
4. 探测失败（仓内无可识别测试框架信号）→ Stop 并回流 Design，标注"仓内无可识别测试框架"；不得默认 JUnit/Jest。

### Step 3: 汇总产物路径与执行结果

### Step 4: 验收用例提炼与 alpha-tests.md 生成（新增）

> TaskPacket `routed=sdd-task-frontend` 的行跳过本步。

对当前 `(Story, 代码仓)` 组合，按 `references/acceptance-criteria-extraction.md`：

1. 从 `story-delta-spec.md` §3 的 SC- 场景锚点提炼功能级验收场景（正常流程→主成功场景，异常/分支→扩展场景）。
2. 从 §4 的 BR- 业务规则提炼规则级验收条件（满足规则→正向，违反规则→反向）。
3. 从 §5 验收场景摘要 GWT 提炼端到端验收路径（交叉验证）。
4. 按 `project_type` 生成 GWT 用例（**框架无关，只写 What to test**）：
   - backend：API 接口级契约用例（Given 请求方法+路径+请求体+预置数据 / When 调用 API / Then 响应码+响应体+副作用断言）
   - frontend：mock 集成级用例（Given 组件状态+mock API 响应 / When 用户交互 / Then 渲染结果+API 调用断言）
5. 分配 `AT-{story_id}-NNN` 标识，建立 AT- → SC-/BR- 覆盖矩阵（alpha-tests.md §3）。
6. 落盘 alpha-tests.md（§1 测试框架声明 + §2 GWT 用例 + §3 覆盖矩阵 + §4 红绿灯证据表骨架）。
7. 覆盖完整性检查：每条 SC-/BR- 至少被一条 AT- 覆盖；缺口无法覆盖时 Stop 并回流。

---

## 输出边界

```text
codebase/<project>/codespec/changes/<requirement-id>-<requirement-name>/<us-id>-<us-name>/
├── tasks.md        # 单仓实现计划（含实现设计章节 + 框架感知 TDD 任务清单）
└── alpha-tests.md  # 单仓功能级 GWT 验收用例 + 开发侧红绿灯证据账本
```

路径中的 `<requirement-id>-<requirement-name>/<us-id>-<us-name>` 是 **Story 工作目录名**,仅为文件路径,**不是** change name。

---

## 提交规范（内联，写入 tasks.md Step 6）

提交规范由 sdd-task 内联定义，生成 tasks.md 时写入每个任务的 Step 6 指引。Dev 阶段（`/sdd-dev` inline 或 `/sdd-dev-subagent` implementer）直接从注入的 tasks.md 任务全文读到，**不走 consume、不从 coding 主规范或 repo-specification 提取**。

### 标准模板

提交信息使用规范格式，提交必须关联需求单号或 BUG 单号：

```text
【问题单号 Defect】{work_item_id}
【修改说明 Modification】{type}({scope}): {description}
```

### 变量

| 变量 | 来源 |
|------|------|
| `{work_item_id}` | 需求单号或 BUG 单号（Story 目录名 / TaskPacket 中的 US ID，如 `US20250510178479`） |
| `{type}` | 提交类型，见下表 |
| `{scope}` | 变更模块或服务名（如 project 名） |
| `{description}` | Task 标题或一句话摘要 |

### type 取值

| type | 场景 |
|------|------|
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `refactor` | 重构（无行为变化） |
| `docs` | 文档 |
| `test` | 测试相关（新增/修改测试） |

### 多行 message

两行内容是同一 message 的连续行（无空行分隔），用单个 `-m` 字符串内换行实现：

```bash
git commit -m "【问题单号 Defect】{work_item_id}
【修改说明 Modification】{type}({scope}): {description}"
```

> git `-m` 语义：每个 `-m` 是一个独立段落，段落间自动插入空行；单 `-m` 内换行是同段连续行，不产生空行。本规范要求两行紧邻，故用单 `-m`。

### alpha-tests.md §6 记录

| 字段 | 说明 |
|------|------|
| `commit_sha` | git commit SHA |
| `commit_message` | 完整 resolved message |
| `commit_spec_source` | `inline`（来自 tasks.md Step 6 内联模板） |

### 禁止

- 跳过 tasks.md Step 6 直接 `git commit`
- 使用 tasks.md 占位符 message 原文
- 从 coding 主规范、repo-specification 或 consume 提取提交规范

---

## 计划写作纪律（writing-plans，强制）

假设执行者对代码库零上下文、对问题域了解有限。计划必须自包含：

1. **计划头**：Goal（一句话）、Architecture（2-3 句）、Tech Stack、TaskPacket 字段（project/`project_type`/codespec_path/story/`test_framework`/search_paths；**frontend 行另填 `frontend_design_path=`**）。
2. **项目边界**：范围内/外（不扩大 StoryPacket 工程影响面）；明确本仓为 backend 或 frontend，禁止跨仓任务。
3. **文件结构（File Structure）**：新建/修改/测试文件 + 单一职责说明；锁定分解决策。**frontend 行**须对齐 `story-delta-frontend-design` 组件树。
4. **实现设计要点**：API/契约、数据/配置、错误处理。**frontend 行**须含 IFC 切片 + 对领域 REST 的引用；**backend 行**禁止写入前端组件树/IFC/样式。
5. **用例追溯表**：AT- 用例标识、用例标题、覆盖任务（**执行视角：用例→Task**；SC-/BR- 需求锚点在 alpha-tests.md 覆盖矩阵，此处不重复）。
6. **执行规则**：Iron Law + No Placeholders 铁规 + 禁改测试。
7. **Task List**：每个任务含 Files（Create/Modify/Test 精确路径）+ 强制 6 步 TDD checkbox（**每步写要点描述，不写全量代码**；具体代码由 Dev 阶段基于要点 + alpha-tests GWT 用例 + 探测框架现写）：
   - Step 1 RED：**测试要点**（测什么行为 + 关键断言 + 测试文件路径，**不写完整测试代码**）；基于 TaskPacket 头 `test_framework` 字段——后端须为 API 接口级测试（非内部类单测），前端须为 mock 集成级测试
   - Step 2 验证 RED：精确命令 + 预期失败点（一句话）
   - Step 3 GREEN：**实现要点**（改哪个类/方法 + 核心逻辑，**不写完整实现代码**，YAGNI）
   - Step 4 验证 GREEN + 全量回归：精确命令 + 预期通过
   - Step 5 REFACTOR（按需）
   - Step 6 提交：按本 Skill「提交规范（内联）」章节的标准模板生成 commit message（`【问题单号 Defect】{work_item_id}` + `【修改说明 Modification】{type}({scope}): {description}`）；**勾选即代表 Task 完成（含红绿验证通过）**，Dev 阶段直接从 tasks.md 读到，不走 consume
8. **计划自审三查**：AT- 用例覆盖 / 占位符扫描 / 类型一致性 / 框架一致性（Step 1 RED 测试要点与 `test_framework` 声明一致）；frontend 行另查组件树/IFC 是否已烘焙。
9. **风险与回滚**。

**bite-size 粒度**：每步 2-5 分钟的一个动作。"写失败测试"是一步，"运行确认失败"是一步，不可合并。Step 写要点描述，不写全量代码；具体代码由 Dev 阶段基于要点 + alpha-tests GWT 用例 + 探测框架生成。

**No Placeholders 铁规**（计划失败，必须修复）：
- 禁止 TBD、TODO、"implement later"、"适当处理错误"、"add validation"
- 禁止"类似任务 N"（必须重复完整要点）
- 禁止无要点的步骤（每步必须有可执行内容：文件路径 + 行为/逻辑要点，但不要求全量代码）
- 禁止引用未在任何任务中定义的类型/函数/方法

---

## TDD 红绿灯纪律（必读 `references/tdd-discipline.md`）

- **Iron Law**：没有失败的测试，就不写实现代码。
- `alpha-tests.md` 定位为**单仓功能级 GWT 验收用例（What to test，框架无关）**：承载 L3 单服务单接口集成测试（后端=API 接口级契约，前端=mock 集成级，**主**）与 L4 UT（公共代码/算法代码等，**辅助**）的功能级 GWT 用例。**不承载红绿灯证据/提交记录**（由 tasks.md Step checkbox 承载完成状态）。具体测试代码（How to test）由 Dev 阶段基于 tasks.md Step 1 要点 + alpha-tests GWT 用例 + 探测框架现写。黑盒 testcase 由测试人员手工执行（*-testcase.md，测试侧独立产出）。
- 每条 AT- 用例至少有一个 RED→GREEN 任务覆盖；无法为关键 AT- 用例设计可失败测试时 Stop 并回流。

---

## 关键约束

- **FE 变更名唯一性**: 本阶段不创建新 change;所有 `--change` 参数一律使用 `<iterative-version>/<requirement-id>-<requirement-name>`。
- **Story 工作目录创建**: 仅通过 `codespec new change` 完成;**禁止** `mkdir -p` 手工拼接。
- **`--path`**: 必须是微服务仓根目录 `codebase/<project>`。
- **粒度**: 表格一行 = 一个微服务,依次处理。
- Task 阶段不得扩展影响工程(缺仓回流 `/sdd-design`);超出 `search_paths[]` 须记录并回流。
- **前后端隔离**：frontend 行烘焙前端产物；backend 行零前端文档依赖；两仓 tasks 互不写入对方实现。

---

## Stop If

- 无法定位有效的 FE 变更名,或 `codespec status --change <fe-change>` 异常且无法恢复。
- 「关联 Story 设计」表格缺失、字段不全,或未按"一个微服务一行"拆分。
- `US ID` 未回填(需先 `sdd-create-us`)。
- `归属微服务`在 `code-repository-index.yaml` 中找不到对应代码仓。
- `codespec new change` 失败且无法恢复。
- 计划含占位符（TBD/TODO/无代码步骤/"类似任务 N"）。
- 任一 AT- 用例无任务覆盖,或无法为关键 AT- 用例设计可失败测试。
- 测试框架探测失败（仓内无可识别测试框架信号），且无法通过降级（标注"框架未识别，测试代码用伪代码"）处理。

---

## 下一阶段：Execution Handoff

全部 `(Story, 微服务)` 的两件套（`tasks.md` + `alpha-tests.md`）经用户确认后，**必须用 AskQuestion 显式让用户选择执行方式**：

```text
计划已完成并确认（共 N 个微服务 × tasks.md）。两种执行方式：

1. Subagent 开发（推荐）→ /sdd-dev-subagent
   每个微服务派发一个独立 implementer subagent 执行其 tasks.md；
   跨仓可并行，单仓内逐任务串行红绿灯；
   主会话作 controller：注入任务全文、处理四态状态、每任务后两段评审。

2. 当前会话 TDD 开发 → /sdd-dev
   按 executing-plans 纪律在本会话逐微服务、逐任务执行红绿灯：
   批判性审读 → 严格按 checkbox 步骤 → 遇阻即停。

选择哪种方式？
```

- 用户选择 `subagent` → 路由 `/sdd-dev-subagent`，TaskPacket `execution_mode=subagent`
- 用户选择 `inline` → 路由 `/sdd-dev`，TaskPacket `execution_mode=inline`
- `--change` 继续沿用 `<fe-change>`

---

## 完成标准

- 所有 `codespec status` / `codespec instructions` 的 `--change` 均为 FE 变更名。
- Story 工作目录均通过 `codespec new change` 创建。
- 产物结构符合「输出边界」；`tasks.md` 含实现设计章节 + Task List（每个 Step 为要点描述 + checkbox，非全量代码）；TaskPacket 头含 `test_framework` 字段（探测结果声明）。
- 计划自审三查通过；无占位符；每条 AT- 用例有任务覆盖；`alpha-tests.md` 含完整 GWT 用例 + 覆盖矩阵（不含证据表/提交记录）。
- `alpha-tests.md`（SC-/BR- → AT- 用例）与 `tasks.md`（AT- 用例 → Task）追溯视角互补、零重复；AT- 与 Task 双向可追溯。
- Execution Handoff 已完成，TaskPacket 含 `execution_mode`。
- 未依赖外部流程组件,未跳过 Stop If。
- **frontend 行**：TaskPacket `routed=sdd-task-frontend`（路由成功）或 `routed=inline-fallback`（兜底）。路由成功时本 Skill 收到 `sdd-task-frontend` 落盘路径，未改写前端 Task 内容；兜底时 `tasks.md` 已烘焙组件树/IFC（或已显式降级标注）、TaskPacket 含 `frontend_design_path`（有产物时），并带 `⚠️ 降级：未经 sdd-task-frontend` 标注。
- **backend 行**：`tasks.md` 不含前端设计正文，未引用 `*frontend-design*`；产出与本次路由改动前逐字一致。