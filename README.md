# 前端 AI Workflow Skills

这是一套面向前端仓库的轻量 AI workflow skills。

目录分层约定：

- `skills/`：前端开发流程主链 skill
- `standalone-skills/`：独立分发、正交使用的单个 skill bundle
- `vendor/superpowers/`：为了安装主链 skill 套件而 vendoring 的必需基础依赖

目标不是让 AI 一次性“理解一切”，而是让它先建立**足够可信、足够可用**的上下文，然后在开发、调试和治理过程中持续演进。

核心原则：

- 代码、测试、配置、现有 spec 文档是真源
- `.project-context` 是索引层，不是第二份源码
- 共享参考模式优先于模块细节
- 上下文先做到“可以开始”，再逐步补全

## 核心 Skill

### `initialize`

首次为仓库建立 `.project-context`。

负责：

- 建 `profile.yaml`
- 建 `references.yaml`
- 建 `features/index.yaml`
- 建 `PROFILE.md`
- 可选安装 GitHub `context-check`

不负责：

- 完整架构文档
- 完整 feature tree
- 持续维护

一句话使用方式：

```markdown
请用 initialize 为 <模块> 的 <功能> 建立第一版可开发上下文。
```

### `sync-context`

在已有 `.project-context` 的前提下，按变更增量同步上下文资产。

负责：

- 更新 `profile.yaml`
- 更新 `references.yaml`
- 更新 `features/index.yaml`
- 更新 `PROFILE.md`
- 维护 freshness / confidence / uncertainty
- 可选安装或调整 GitHub `context-check`

不负责：

- 首次初始化
- 事故调试

一句话使用方式：

```markdown
请用 sync-context 为 <模块> 的 <功能> 做开发前预热。
```

GitHub `context-check` 对接说明见：

- [skills/sync-context/references/github-context-check.md](skills/sync-context/references/github-context-check.md)

### `immune-debug`

用于处理 bug、回归、测试失败和异常行为，并在修复后给出免疫决策。

负责：

- 调试闭环
- 结构化复盘
- 免疫决策
- 必要时回推 `initialize` / `sync-context`

不负责：

- 普通功能开发
- 日常上下文维护

一句话使用方式：

```markdown
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
```

### `audit`

用于周期性审查 `.project-context` 资产是否失真、过期、噪音过大或规则失效，并在交付后承担默认的 reflect 入口。

负责审查与最小治理：

- `profile.yaml`
- `references.yaml`
- `features/index.yaml`
- `PROFILE.md`
- `immune-registry.yaml`
- `immune-candidates.yaml`
- `.github/workflows/context-check.yml`
- `impact-rules.yaml`
- 交付后 reflect 的判断与路由
- 必要时对 immune 资产做最小有效治理

一句话使用方式：

```markdown
请用 audit 审查当前 `.project-context` 资产，重点看 <范围> 是否失真。
```

详细指南见：

- [skills/audit/references/asset-review-guide.md](skills/audit/references/asset-review-guide.md)

### `analysis-spec`

把模糊需求压成可执行分析包。内含五步认知链：准备（需求分级 + 上下文预热）→ 摸底 → 自学习 → 多轮澄清 → 目标规格。

负责：

- 需求分级与上下文预热
- 现状摸底与风险识别
- 三色置信度自学习（🔴 / 🟡 / 🟢）
- 用户可控粒度的多轮澄清（全量 / 按需 / 最小）
- 目标行为、风险清单和证据计划
- 内置 4 个领域检查清单（前端 / 后端 / 集成 / 风险记忆），支持仓库级自定义扩展

不负责：

- 技术选型
- 切片设计
- 实现计划

一句话使用方式：

```markdown
请完成 analysis-spec：准备 → 摸底 → 自学习 → 澄清 → 规格，产出 analysis-spec.md。
```

### `slice-plan`

基于 analysis-spec 把需求切成最小可交付 slices。

负责：

- 按用户路径和页面状态切片
- 每个 slice 的验证方式和回滚边界
- 执行顺序和依赖关系
- 迁移类需求的 compatibility slice 和 feature flag 策略

不负责：

- 分析需求
- 实现代码
- 做验证

一句话使用方式：

```markdown
请基于 analysis-spec 产出 slice-plan，每个 slice 写清验证方式和回滚边界。
```

### `spec-check`

在交付结束时逐条对账 analysis-spec 的承诺与实际交付结果。这是每次标准交付的必经步骤，不是治理审计。

负责：

- 逐条标记 TargetBehavior 为 `as_specified` / `intentionally_changed` / `deferred` / `abandoned`
- 检查隐性偏差
- 为后续 `audit` 提供结构化输入

不负责：

- reflect 和 reusable learnings（交给 `audit`）
- context 或 immune 的持久化决策

一句话使用方式：

```markdown
请做 spec-check，逐条对账 analysis-spec 和最终交付。
```

### `reflect`（closing protocol）

这不是一个独立 skill，而是当前技能流里的收尾协议。

如果项目需要保留交付工件，可以记录为 `reflect.md` 一类文档；这不代表仓库里新增了一个独立的 `reflect` skill。

第一版默认通过以下路由实现：

- `audit` 负责做交付后的 post-ship reflect
- `sync-context` 负责把值得保留的 context 结论写回 `.project-context`
- `immune-debug` 只负责事故型 reflect 和 immune 决策

第一版不负责：

- 新建 `skills/reflect/`
- 引入 `reflect-log.yaml` 或独立 retro schema
- 做跨周趋势报表

一句话使用方式：

```markdown
请先用 audit 对这轮交付做 reflect，重点看可复用模式、context 漂移和是否需要沉淀 immune asset；如果输出要求写回 context，再用 sync-context 完成落盘。
```

## 最短上手路径

### 1. 首次接入 AI 的仓库

```markdown
请用 initialize 为 <模块> 的 <功能> 建立第一版可开发上下文。
```

### 2. 已有 `.project-context`，准备做功能

```markdown
请用 sync-context 为 <模块> 的 <功能> 做开发前预热。
```

### 3. 把需求变成可执行分析包

```markdown
请先做 request-classification 和 sync-context 预热，然后完成 analysis-spec。
```

### 4. 把分析包切成可交付 slices

```markdown
请基于 analysis-spec 产出 slice-plan，每个 slice 写清验证方式和回滚边界。
```

### 5. 交付后做 spec 对账

```markdown
请做 spec-check，逐条对账 analysis-spec 和最终交付。
```

### 6. GitHub `context-check` 失败

```markdown
请用 sync-context 修复这次 PR 的 context-check，只更新必要的 `.project-context` 资产。
```

### 7. 出现 bug / 回归 / 测试失败

```markdown
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
```

### 8. 完成一轮交付后做 reflect

```markdown
请先用 audit 对这轮交付做 reflect，重点看可复用模式、context 漂移和是否需要沉淀 immune asset；如果输出要求写回 context，再用 sync-context 完成落盘。
```

### 9. 做周期性治理

```markdown
请用 audit 审查当前 `.project-context` 资产，重点看 references、features、immune assets 和 context-check 是否失真。
```

## 安装 Skills

现在推荐使用 `gstack` 风格的安装方式：

1. 先把本仓库 clone 到宿主的 skills 根目录下，目录名固定为 `moon-skills`
2. 再在这个 checkout 里运行 `./setup`
3. `setup` 会把真正需要被宿主发现的 skill 平铺到同级 skills 根目录

对于 workflow 里依赖的 `superpowers` skills，安装优先级现在是：

1. 复用目标宿主或本机标准 skills 根里已存在的官方 superpowers 安装
2. 若缺失，则尝试通过官方渠道安装：`npx skills add obra/superpowers`
3. 只有官方安装不可用或失败时，才回退到本仓库的 `vendor/superpowers/`

### 1. repo-local 安装到另一个仓库

如果你想让另一个仓库直接可用，推荐 clone 到该仓库的 `.agents/skills/` 或 `.cursor/skills/`：

```bash
git clone https://github.com/CCharlesMeng/moon-skills.git .agents/skills/moon-skills
cd .agents/skills/moon-skills && ./setup --host auto --bundle workflow --write
```

如果目标宿主是 Cursor：

```bash
git clone https://github.com/CCharlesMeng/moon-skills.git .cursor/skills/moon-skills
cd .cursor/skills/moon-skills && ./setup --host auto --bundle workflow --write
```

### 2. user-global 安装

如果你想装到当前用户级别：

```bash
git clone https://github.com/CCharlesMeng/moon-skills.git ~/.agents/skills/moon-skills
cd ~/.agents/skills/moon-skills && ./setup --host auto --bundle workflow --write
```

也可以先 clone 到任意目录，再显式指定宿主：

```bash
git clone https://github.com/CCharlesMeng/moon-skills.git ~/moon-skills
cd ~/moon-skills && ./setup --host agents --bundle workflow --write
```

### 3. 安装哪些 bundle

默认推荐安装 `workflow`：

```bash
./setup --host auto --bundle workflow --write
```

它会完整装入：

- `initialize`
- `sync-context`
- `immune-debug`
- `audit`
- `analysis-spec`
- `slice-plan`
- `spec-check`
- `brainstorming`
- `systematic-debugging`
- `writing-plans`
- `subagent-driven-development`
- `executing-plans`
- `test-driven-development`
- `verification-before-completion`
- `using-git-worktrees`
- `requesting-code-review`
- `finishing-a-development-branch`

如果你只想安装独立的 OpenClaw skill：

```bash
./setup --host auto --bundle openclaw-feishu-multi-agent --write
```

如果你想 workflow 和 standalone 一起装：

```bash
./setup --host auto --all --write
```

### 4. 常用参数

先看 dry-run：

```bash
./setup --host auto --bundle workflow
```

真正写入：

```bash
./setup --host auto --bundle workflow --write
```

强制覆盖并备份：

```bash
./setup --host auto --bundle workflow --write --force --backup
```

如需复制目录而不是软链接：

```bash
./setup --host auto --bundle workflow --mode copy --write
```

如果你只想使用本机或目标目录里已经存在的官方 superpowers，不允许 fallback 到 vendor：

```bash
./setup --host auto --bundle workflow --write --no-vendor-fallback
```

如果你明确不想使用官方 superpowers 渠道，直接走 vendored fallback：

```bash
./setup --host auto --bundle workflow --write --no-official
```

兼容旧入口：

```bash
python "scripts/install_workflow_skills.py" --write
```

## 仓库结构

当前核心目录：

- `skills/initialize/`
- `skills/sync-context/`
- `skills/immune-debug/`
- `skills/audit/`
- `skills/analysis-spec/`
- `skills/slice-plan/`
- `skills/spec-check/`
- `standalone-skills/openclaw-feishu-multi-agent/`
- `vendor/superpowers/`

`reflect` 不单独建立 skill 目录，通过 `audit`、`sync-context`、`immune-debug` 的路由协作实现。

## 说明

这套技能当前刻意保持克制：

- 不额外拆出 `implement`
- `reflect` 先不拆成独立 skill
- 不要求完整 feature tree
- 不默认生成全量架构文档
- 不默认用 bot PR 偷偷改主分支

如果一个 skill 需要你写很长的提示词，通常说明这个 skill 还不够好。

日常目标应该始终是：**一句话就能用。**

独立的集成类或正交能力 skill 不再混放在 `skills/` 里，而是放在 `standalone-skills/` 下；当前示例是 `openclaw-feishu-multi-agent`。

## 方法论文档

- [analysis-driven-sdd.md](analysis-driven-sdd.md)：分析驱动 SDD 方法论全文。
- 稳定基座：`initialize`、`sync-context`、`immune-debug`、`audit`。
- 中段核心：`analysis-spec`（5-phase：准备 → 摸底 → 自学习 → 澄清 → 规格）、`slice-plan`、`spec-check`。
- 内置 4 个领域检查清单（前端 / 后端 / 集成 / 风险记忆），支持仓库级自定义扩展。
- 所有工件统一归入 `docs/specs/<topic>/`，不散放。