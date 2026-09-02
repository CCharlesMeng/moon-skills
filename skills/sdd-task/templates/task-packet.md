# TaskPacket（会话 handoff 结构参考）

> 本文件仅供 Agent 对齐输出结构，**不得**落盘为独立 md 文件。

## project

来自 StoryPacket.projects[].project

## project_type

`backend` | `frontend` — 来自 `code-repository-index.yaml` 对该 project 的判定；须与 `tasks.md` TaskPacket 头一致。

## codespec_path

`codebase/<project>/codespec/changes/<requirement-id>-<requirement-name>/<us-id>-<us-name>/`

## task_file

`tasks.md`（单仓实现计划，含实现设计章节与 TDD 任务清单）

## alpha_tests_file

`alpha-tests.md`（单仓功能级 GWT 验收用例 + 红绿灯证据账本，用例标识 `AT-{story_id}-NNN`，向上追溯 `story-delta-spec.md` 的 SC-/BR- 锚点）

## test_framework

来自 sdd-task 测试框架探测结果（见 `references/test-framework-detection.md`）。后端声明主 + 辅助测试框架（如 `JUnit5+Mockito+Karate`）；前端此字段是派生摘要，判据以下面四个通道字段为准。tasks.md Step 1 RED 测试代码须基于探测结果生成。

## component_test_status / component_test_framework / browser_test_status / browser_test_framework

仅 `project_type=frontend` 填写。前端探测输出两条独立通道：组件通道跑模拟 DOM，浏览器通道驱动真实浏览器，一条存在不能推断另一条存在（Cypress 不构成组件测试能力，Vitest 不构成浏览器能力）。

- `*_test_status` 只取 `available` / `absent` / `unknown`；`absent` 是扫描过确认没有，`unknown` 是信号矛盾或无法判定，两者含义不同。
- `*_test_framework` 只在对应 status 为 `available` 时填真实框架名，其余留空。禁止把状态值写进框架字段。

## frontend_design_path

可选。仅 `project_type=frontend` 且已产出 frontend-design 时填写：指向本 Story 的 `story-delta-frontend-design.md`（共享契约可另注 `requirement-frontend-design.md`）。实现细节须已烘焙进 `tasks.md` 正文；Dev/subagent **不**凭此字段扫描变更包其它旁路产物。`project_type=backend` 时留空，禁止填写。

## search_paths

来自 StoryPacket.projects[].search_paths（本仓影响面）

## execution_mode

`subagent` | `inline` — sdd-task 完成 Execution Handoff 后由用户选择：
- `subagent` → `/sdd-dev-subagent`（推荐，每微服务一个 implementer subagent）
- `inline` → `/sdd-dev`（当前会话 executing-plans）
