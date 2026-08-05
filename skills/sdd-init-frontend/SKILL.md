---
name: sdd-init-frontend
description: 初始化或刷新一个前端仓的可复用仓库级 baseline，并主动把依赖、环境变量、服务、身份、fixture、浏览器与质量命令准备到可开发状态。用于前端项目首次接入、仓库 baseline 缺失或失效、用户要求准备前端开发环境，或 sdd-dev-frontend 在 Story 开工前自动路由；不要求 tasks.md，不生成 Requirement/Story 级 QA 基线。
---

# 前端仓初始化

## 目标与边界

以**一个前端仓库及其中一个目标 app**为工作单位，完成：

1. 生成或局部刷新 `REPO-1～REPO-3`；
2. 主动准备当前机器；
3. 实跑页面与质量命令；
4. 输出 `READY`、`READY_WITH_LIMITS` 或 `BLOCKED`。

项目级跨仓拓扑由外层流程管理。本 skill 不要求 `tasks.md`，也不生成需求级 baseline。

| 层级 | Baseline | 本 skill 是否负责 |
| --- | --- | --- |
| 仓库级 | `REPO-1` 环境与运行、`REPO-2` 工程质量、`REPO-3` 工程范式 | 是 |
| 需求级 | `DEMAND-1` 设计事实、`DEMAND-2` 执行起点、`DEMAND-3` QA 判定 | 否，由 `sdd-dev-frontend` 在 Requirement / Story 生命周期生成 |

详细目录、字段和失效契约见 [references/baseline-contract.md](references/baseline-contract.md)。执行前先完整读取该文件。

## 路径

| 变量 | 含义 |
| --- | --- |
| `<repo-root>` | 目标前端仓根目录 |
| `<target-app>` | monorepo 中的目标 app；单 app 仓为 `.` |
| `<project-sdd-dir>` | 外层 SDD 项目产物根目录 |
| `<repo-id>` | 仓库稳定标识；默认取仓库目录名，冲突时加远端仓库名或短哈希 |
| `<repo-baseline-dir>` | `<project-sdd-dir>/frontend-baselines/<repo-id>/` |
| `<skill-dir>` | 本 skill 目录 |

先自动定位。多个 app 同等合理、多个 SDD 根候选或 repo id 冲突时，一轮问完；不要逐项追问。

## 硬门禁

1. **不保存秘密或变量值。** baseline 只记录环境变量键、是否敏感、是否就绪、来源，以及 `has_template_default` 这类布尔标记；真实值和模板默认值文本都不记录，也不记录 cookie、token 或密码。
2. **不覆盖已有配置。** 可从模板创建缺失的非敏感本地配置；已有 `.env*`、代理或构建配置不得静默改写。
3. **先准备再降级。** 固定执行“发现 → 准备 → 重试 → 证明可用”；没有实际尝试不得直接写 `READY_WITH_LIMITS`。
4. **只终止本次启动的进程。** 已存在的端口占用者不能擅自结束。
5. **外部副作用先授权。** 下载/安装、写业务数据、seed、codegen、登录外部账号、修改已有仓库配置、终止既有进程前请求授权。
6. **状态必须有证据。** `READY` 不能来自静态扫描；页面、必需服务、浏览器采集和当前必需的质量命令必须实际运行。
7. **刷新不能抹掉人工事实。** 脚本只替换 Section 的“自动发现（脚本维护）”与新鲜度账本；“人工维护（agent 维护）”由主 agent 维护。失效 Section 的人工事实必须复核后才能再次 READY。
8. **仓库 baseline 不承载 Story 起点。** 某次开工前的失败集合、`base-ref`、账号角色与 fixture 选择属于 `DEMAND-2`。
9. **人机同源。** `repo-baseline.md` 是 REPO-1～3、状态和指纹的唯一事实源，不生成 JSON sidecar；人和机器读取同一套固定标题与表格。只写已确认的有效事实与会影响开发的缺口；可选项不存在时省略，必需项缺失时先准备，仍缺失才写唯一补齐动作；不得用“未见”“未声明”“0 个”“无”填满版面。
10. **范式正文只在仓库级。** REPO-3 只收跨 Requirement 复用的 `PATTERN-*`；不得为 Requirement 或 Story 复制范式卡片，也不得长期保存候选清单。

## 工作流

### Phase 0 — 定位与扫描

1. 定位 `<repo-root>`、`<target-app>`、`<project-sdd-dir>` 和 `<repo-id>`。
2. 创建 `<repo-baseline-dir>`。
3. 执行：

```bash
python3 "<skill-dir>/scripts/manage_repo_baseline.py" scan \
  --repo-root "<repo-root>" \
  --target-app "<target-app>" \
  --baseline-dir "<repo-baseline-dir>" \
  --repo-id "<repo-id>"
```

扫描器只读取模板环境文件，不读取真实 `.env`；只提取仓库事实，不宣告当前机器已就绪。

若 baseline 已存在，先运行 `status`。仅刷新 `stale_sections`，不要因为一个 lockfile 变化重做全部工程范式勘察；把每个失效 ID 作为一个 `--section` 传给 `scan`。

```bash
python3 "<skill-dir>/scripts/manage_repo_baseline.py" status \
  --repo-root "<repo-root>" \
  --baseline-dir "<repo-baseline-dir>"

python3 "<skill-dir>/scripts/manage_repo_baseline.py" scan \
  --repo-root "<repo-root>" \
  --target-app "<target-app>" \
  --baseline-dir "<repo-baseline-dir>" \
  --repo-id "<repo-id>" \
  --section "<stale section；可重复>"
```

### Phase 1 — 完成 `REPO-1` 环境与运行

以 `repo-baseline.md` 的 `REPO-1 / 自动发现（脚本维护）` 为起点，只为当前仓库实际适用或当前开发必需的能力补充 `人工维护（agent 维护）`：

- 目标 app、Node、包管理器、lockfile、workspace、安装命令；
- 存在模板或运行确实需要时的环境变量契约；
- 启动命令、端口、base path、proxy、API/mock/WebSocket、静态资源；
- 登录、角色、租户要求；
- seed / fixture 能力；
- 浏览器要求、视口、DPR、字体、locale、timezone、截图和结构化采集契约。

然后主动准备：

| 缺口 | 默认动作 |
| --- | --- |
| 依赖缺失 | 确认包管理器和 lockfile；需要下载时请求一次授权，执行确定性安装后重试 |
| 本地环境文件缺失 | 从模板生成不含秘密的骨架；敏感键合并成一次请求 |
| 端口冲突 | 先识别占用者；仓内支持安全换端口则换，否则请求用户决定 |
| API / 后端不可用 | 优先启动仓内 mock、MSW、fixture server 或文档声明的本地服务 |
| 需要登录 | 打开可复用浏览器会话，让用户只完成登录动作，然后继续验证 |
| 缺测试数据 | 优先使用已有 fixture；seed 会写业务仓或外部数据时先请求授权 |
| 浏览器或字体缺失 | 定位或协助安装；当前 Story 需要视觉能力时不得直接降级 |

实际机器状态只写入 `onboarding-report.md`，不要混入仓库契约。

不要为了覆盖清单而记录不存在的服务、身份、fixture、环境变量或浏览器约束。不存在且不需要就省略；需要但缺失则执行上表的准备动作，仍无法完成时才进入限制或阻断。

### Phase 2 — 完成 `REPO-2` 工程质量

从扫描出的规范命令中识别并实际运行适用项：

- test
- typecheck
- lint
- format-check
- build
- integration
- E2E smoke
- codegen check

`REPO-2` 保存“规范命令、运行范围、前置条件与能力”；本次运行的退出码、耗时、失败摘要写进 `onboarding-report.md`。

人读产物只列实际存在的命令。某个类别或整个质量 section 不存在都不自动构成异常，直接省略；只有仓库约定、上层调用方或当前开发明确要求某项质量能力时，才引导用户补齐并实跑。

首次接入允许已有代码失败，但必须证明命令可运行并如实记录。是否能给 `READY_WITH_LIMITS` 取决于失败是否阻断当前开发能力；不能用“仓库本来就红”掩盖工具链不可用。

### Phase 3 — 完成 `REPO-3` 工程范式

扫描器只给候选。主 agent 必须用代码证据复核，并在 `REPO-3 / 人工维护（agent 维护）` 中补充仓库级 `PATTERN-*`：

- 技术栈、目录与命名；
- 公共 hooks、工具与数据变换；
- 状态管理、表单、列表、loading/error；
- UI 库、主题、仓内 token、样式落地方式；
- 请求实例、鉴权、响应体与错误处理；
- 路由、菜单、权限、埋点、feature flag；
- API schema 与 codegen；
- 可作为参照页的页面目录。

每条范式必须给适用场景、工程入口、使用方式、不变量、验证方式、标签和相对路径证据。不要为“完整”枚举每个组件；只记录跨 Requirement 复用的范式与入口。
依赖或范式类别没有证据时直接省略，不输出空类别。

准入判断：只影响当前 Story 的事实留在任务与代码证据；影响同一 Requirement 多个 Story 的选择进入上游 `requirement-frontend-design.md` 工程决策；只有跨 Requirement 的仓库惯例才进入 REPO-3。仍是候选就不落盘。

### Phase 4 — 页面与浏览器实证

使用 Phase 1 确认的命令启动目标 app，只管理本次启动的进程。至少验证：

1. 健康页或目标路由能打开；
2. 必需 API/mock 可达；
3. 登录、角色、租户满足；
4. 约定 fixture 可进入；
5. 截图可用；
6. 能注入脚本并读取 DOM、computed style 和几何；
7. 实际浏览器版本、视口、DPR、字体、locale、timezone 已记录。

完成后停止本次启动且不再需要的临时进程；若服务需留给紧接着的 `sdd-dev-frontend`，在报告中明确 PID、端口与所有权。

### Phase 5 — 报告与定级

按 [references/onboarding-report-template.md](references/onboarding-report-template.md) 填写 `<repo-baseline-dir>/onboarding-report.md`，删除所有草稿占位和不适用的行、表、章节。没有限制、阻断或进程交接时，不生成对应章节。

| 状态 | 判据 |
| --- | --- |
| `READY` | 当前开发必需的依赖、配置、页面、服务、身份、fixture、浏览器采集和质量命令均已实证 |
| `READY_WITH_LIMITS` | 可以开发，但一个或多个**当前非必需**能力不可用；每项限制写影响范围和解除条件 |
| `BLOCKED` | 目标 app 不明确、依赖无法准备、页面不能启动，或缺少当前必需的秘密、账号、服务、数据、浏览器能力 |

用脚本冻结状态：

```bash
python3 "<skill-dir>/scripts/manage_repo_baseline.py" finalize \
  --repo-root "<repo-root>" \
  --baseline-dir "<repo-baseline-dir>" \
  --status "<READY|READY_WITH_LIMITS|BLOCKED>" \
  --limit "<可重复；仅 READY_WITH_LIMITS>" \
  --blocker "<可重复；仅 BLOCKED>"
```

最后运行 `status` 与 `validate`。任一失败都不能宣告完成。

## 刷新与路由

| `status` 结果 | 动作 |
| --- | --- |
| baseline 不存在 | 全量执行本 skill |
| `stale_sections` 非空 | 只重扫、复核和重验这些 section 及其受影响能力 |
| `DRAFT` | 从尚未完成的 Phase 继续 |
| `BLOCKED` | 尝试解除报告中的 blocker；仍需外部输入时只给唯一解除动作 |
| `READY_WITH_LIMITS` | 当前 Story 不受 limits 影响才可返回 `sdd-dev-frontend` |
| `READY` | 直接返回调用方 |

从 `sdd-dev-frontend` 路由而来时，完成后自动返回原 Story，不要求用户再次发起命令。

## 最终输出

```text
✓ sdd-init-frontend <READY|READY_WITH_LIMITS|BLOCKED>
产出：<repo-baseline-dir>/repo-baseline.md + onboarding-report.md
下一步：<返回原 Story / 唯一解除动作 / 可开始 sdd-dev-frontend>
```
