# 前端 Baseline Markdown 契约

## 目录

1. [两层六类模型](#两层六类模型)
2. [仓库级目录与唯一事实源](#仓库级目录与唯一事实源)
3. [Markdown 机器接口](#markdown-机器接口)
4. [三个仓库 Section](#三个仓库-section)
5. [范式生命周期](#范式生命周期)
6. [失效与刷新](#失效与刷新)
7. [需求级消费契约](#需求级消费契约)

## 两层六类模型

| 层级 | ID | 名称 | 生命周期 |
| --- | --- | --- | --- |
| 仓库级 | `REPO-1` | 环境与运行 | 同一前端仓共享；相关配置变化时局部刷新 |
| 仓库级 | `REPO-2` | 工程质量 | 同一前端仓共享；质量配置与命令变化时刷新 |
| 仓库级 | `REPO-3` | 工程范式 | 同一前端仓共享；范式入口或证据变化时刷新 |
| 需求级 | `DEMAND-1` | 设计事实 | Requirement 生命周期；原型指纹或区块哈希变化时刷新 |
| 需求级 | `DEMAND-2` | 执行起点 | Story 的单次执行上下文；开工时生成 |
| 需求级 | `DEMAND-3` | QA 判定 | Story 生命周期；用户确认后冻结 |

Requirement 与 Story 同属需求级，只按自然生命周期落盘。仓库范式不下沉为 Requirement 或 Story 副本。

## 仓库级目录与唯一事实源

```text
<project-sdd-dir>/frontend-baselines/<repo-id>/
├── repo-baseline.md
└── onboarding-report.md
```

- `repo-baseline.md`：仓库身份、readiness、REPO-1～3、输入指纹和人工范式的唯一事实源，人和机器读取同一份内容。
- `onboarding-report.md`：当前机器本次准备与验证结果，不是仓库长期事实。
- 不生成 `manifest.json`、`repo-baseline.json` 或其他 sidecar；迁移旧 baseline 时，人工事实先搬入 Markdown，旧 JSON 留存会使 `validate` 失败。
- baseline 不写进目标业务仓。依赖目录、本地环境文件等准备动作仍按 skill 门禁写入目标仓工作区。

所有持久化事实都直接使用 Markdown 标题、表格、列表和代码标记表达，不在 Markdown 中嵌入 JSON/YAML 作为第二套事实。

呈现规则：

- 只写已确认的正向事实和必须处理的缺口；
- 可选能力不存在时整行、整类或整节省略；
- 必需能力缺失时先准备，仍缺失才生成一条带 ID、影响和补齐动作的“待处理动作”；
- 不使用“未见”“未声明”“0 个”“无”填充版面；
- 当前机器版本、端口、浏览器、运行结果只写 onboarding report。

## Markdown 机器接口

### 固定结构

`repo-baseline.md` 使用以下稳定标题：

```markdown
# Frontend Repository Baseline — <repo-id>
## 状态
## Section
## REPO-1 环境与运行
## REPO-2 工程质量
## REPO-3 工程范式
## 新鲜度账本
```

`状态` 表至少包含：

```text
schema_version
repo_id
repo_root
target_app
readiness
generated_at
```

完成 onboarding 后增加 `verified_at` 与 `report_sha256`。输入变化后 readiness 回到 `DRAFT`，并写 `reason`。

每个 REPO Section 可含：

- `### 自动发现（脚本维护）`：扫描器可替换；
- `### 人工维护（agent 维护）`：扫描器必须原样保留；
- `## 新鲜度账本` 下对应的路径与 SHA-256 表：扫描器维护。

人工维护内容只能用 H4/H5 继续分层，不得另起 H3；否则会越过脚本保存 seam。

### 稳定命令

```bash
python3 manage_repo_baseline.py scan ...
python3 manage_repo_baseline.py status ...
python3 manage_repo_baseline.py validate ...
python3 manage_repo_baseline.py finalize ...
python3 manage_repo_baseline.py show --section REPO-1 ...
python3 manage_repo_baseline.py show --pattern-id PATTERN-STATE-1 ...
python3 manage_repo_baseline.py show --tag persistence ...
```

命令输出也是 Markdown。调用方以退出码判断成功，并读取固定字段表、错误列表或选出的 Markdown 片段；不得依赖 JSON 字段路径。

## 三个仓库 Section

### `REPO-1` 环境与运行

自动发现只呈现实际存在的：

- Node 约束、包管理器、lockfile、workspace、安装命令；
- 目标 app 与包名；
- 环境模板和变量键，不保存任何值；
- 启动、mock、fixture、seed 等运行命令；
- proxy、API、静态资源和配置候选入口。

人工维护补充扫描无法可靠判断且跨 Story 复用的仓库契约：端口、base path、服务拓扑、身份/租户、fixture 场景和浏览器采集要求。

### `REPO-2` 工程质量

只记录实际存在的规范命令：

```text
test
typecheck
lint
format
build
integration
e2e
codegen
```

每条命令包含类别、命令、工作目录和证据。人工维护可补适用范围、前置条件和阻断规则。某类命令不存在时直接省略；只有仓库或上游明确要求该能力时才生成待处理动作。

某次 Story 开工时的退出码、耗时和失败集合属于 `DEMAND-2`，不写入 REPO-2。

### `REPO-3` 工程范式

自动发现只给技术依赖、源码入口与范式证据候选。人工维护只收录已经在仓库中成立、可跨 Requirement 复用的范式。

每条仓库范式使用唯一 ID：

```markdown
#### `PATTERN-STATE-1` · 状态变更与持久化

| 项 | 内容 |
| --- | --- |
| 适用场景 | 状态变更、存档、恢复 |
| 工程入口 | `src/lib/save.ts` |
| 使用方式 | 先经过状态变更函数，再调用存储接口 |
| 不变量 | schema 变化必须增加 migration |
| 验证 | `npm test -- save.test.ts` |
| 标签 | `state`、`persistence`、`save` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/lib/save.ts` | 持久化入口与版本迁移 |
```

准入条件：

- 仓库中已有真实实现和代码证据；
- 预期跨 Requirement 复用；
- 能回答何时使用、从哪里进入、遵守什么不变量、如何验证；
- 不是组件清单、单个 Story 的调用摘录或尚未证实的候选。

## 范式生命周期

| 事实范围 | 保存位置 | 处理方式 |
| --- | --- | --- |
| 跨 Requirement 的仓库惯例 | `repo-baseline.md` / REPO-3 | 保存唯一范式正文 |
| 同一 Requirement 多个 Story 的选择或偏离 | `requirement-frontend-design.md` 的工程决策 | 只引用 `PATTERN-*` ID，不复制正文 |
| 当前 Story 采用哪些范式 | `dev-baseline.md` 的工程依据 | 只保存 ID 与 REPO-3 指纹 |
| 当前 Story 的一次性实现细节 | tasks、代码和验证证据 | 不进入 baseline |

不生成 Story 级范式卡片或 `codebase-brief.md`。代码侧勘察只在上下文中完成“Story 需要 → Requirement 决策 → REPO-3 ID”的选择，并将引用并入已有 `dev-baseline.md`。

新发现按以下规则处理：

- 只影响当前 Story：留在任务与代码证据；
- 影响同一 Requirement 的多个 Story：形成 Requirement 工程决策；
- 已成为跨 Requirement 的仓库惯例：直接刷新 REPO-3；
- 仍是候选：不进入任何 baseline，不长期维护候选清单。

## 失效与刷新

Section 指纹为其新鲜度账本中 `相对路径 + 文件 SHA-256` 的规范文本 SHA-256。文件集合也参与计算。

人工维护段中用反引号声明且真实存在的仓内文件自动加入对应 Section 输入。证据变化后，相关人工事实必须失效，不能继续假装有效。

| 输入变化 | 默认刷新 |
| --- | --- |
| package manifest、lockfile、Node、workspace、env template、dev/proxy 配置 | `REPO-1`；package manifest 也可能影响 `REPO-2/3` |
| test/typecheck/lint/format/build/E2E/CI 配置 | `REPO-2` |
| router/menu/permission、theme/token/style、request/API、hooks/form/state、schema/codegen 和范式证据 | `REPO-3` |

刷新规则：

1. 缺 `repo-baseline.md`：全量初始化。
2. 指纹一致且 readiness 可用：只读复用。
3. 部分失效：用 `scan --section <ID>` 只替换该 Section 的自动发现与账本，保留人工维护段。
4. 任一 Section 输入变化：readiness 回到 `DRAFT`，不得沿用旧 READY。
5. `repo_root`、`target_app` 或 schema version 不匹配：不得局部复用。
6. REPO-3 指纹变化：Story 中的工程依据只重新选择 ID，不复制或同步范式正文。

## 需求级消费契约

### `DEMAND-1` 设计事实

位置：`<requirement-dir>/design-spec/`。包含基线源、设计 token、内容语义、页面/区块与规格。其内部格式不属于本次仓库 baseline Markdown 迁移范围。

### Requirement 工程决策

复用已有 `<requirement-dir>/requirement-frontend-design.md`。只有存在跨 Story 选择或偏离时才增加工程决策；完全沿用仓库范式时省略。

```markdown
## 工程决策

| ID | 适用 Story | 决策 | 仓库依据 |
| --- | --- | --- | --- |
| `REQ-DEC-1` | S1、S2 | 存档统一走现有 store | `PATTERN-STATE-1` |
```

### `DEMAND-2` 执行起点

位置：`<story-dir>/dev-baseline.md`。包含 Story 场景、base ref、起点失败集合，以及轻量工程依据：

```markdown
## 工程依据

| Story 需要 | 采用依据 |
| --- | --- |
| 存档状态 | `PATTERN-STATE-1` |
| Requirement 决策 | `REQ-DEC-1` |
| REPO-3 指纹 | `<sha256>` |
```

这里不复制范式正文、源码片段或证据表。

### `DEMAND-3` QA 判定

位置：`<story-dir>/dev-baseline.md` 的“QA 基线”。包含还原侧、功能侧、豁免、缺口和用户确认记录。

`sdd-dev-frontend` 的最小读取：

| 阶段 | 读取 |
| --- | --- |
| 仓库接入门 | `status` 的 Markdown 输出 |
| Phase 0 | `show --section REPO-1/2` 与 onboarding report |
| 代码侧勘察 | Requirement 工程决策；按 ID/标签选读 REPO-3 |
| 实现与检视 | `dev-baseline.md` 工程依据；按 ID 回读仓库唯一范式正文 |
