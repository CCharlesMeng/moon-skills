# GitHub context-check 对接指南

这份文档说明如何把 `sync-context` 自带的 GitHub context-check 安装到其他仓库中。

目标是：

- 在 PR 上自动检测本次变更是否影响 `.project-context`
- 若命中影响，检查 context 资产是否已经同步
- 若未同步，阻断 PR 并给出明确修复指引

它不负责：

- 自动改主分支
- 自动创建 bot PR
- 代替开发者维护所有 context 资产正文

## 适用前提

对接前，目标仓库最好已经满足：

- 已存在 `.project-context/profile.yaml`
- 已存在或计划使用 `references.yaml`
- 已存在或计划使用 `features/index.yaml`
- 代码托管在 GitHub

如果仓库尚未初始化，先运行 `initialize`。

## 会安装哪些文件

安装后，目标仓库会新增：

- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`
- `.project-context/scripts/manage_context.py`
- `.project-context/scripts/context_common.py`

其中：

- `context-check.yml` 负责 GitHub Actions 检查
- `impact-rules.yaml` 负责 diff 分类规则
- `manage_context.py` 负责 `detect-impact` 和 `sync --check`
- `context_common.py` 负责共享辅助逻辑

## 快速安装

先 dry-run 看看会安装什么：

```bash
python "skills/sync-context/scripts/install_context_check.py" --repo-root "."
```

确认无误后再真正写入：

```bash
python "skills/sync-context/scripts/install_context_check.py" --repo-root "." --write
```

如果目标仓库里已经有同名文件，需要覆盖时：

```bash
python "skills/sync-context/scripts/install_context_check.py" \
  --repo-root "." \
  --write \
  --force \
  --backup
```

## GitHub workflow 行为

默认 workflow 为：

- 触发：`pull_request`
- 忽略：只修改 `.project-context/**` 时不重复触发
- 行为：
  1. checkout PR 代码
  2. 基于 `base` / `head` 计算 diff
  3. 运行 `detect-impact`
  4. 若 impact 为 `none`，直接通过
  5. 若 impact 不为 `none`，运行 `sync --check`
  6. 若检查失败，阻断 PR

当前不会：

- 自动生成 PR
- 自动推送 context 文件
- 自动合并

## diff 分类

默认支持四类 impact：

- `none`
- `feature`
- `reference`
- `structure`

默认规则写在：

- `.project-context/impact-rules.yaml`

示例：

```yaml
feature:
  - "apps/*/src/pages/**"
  - "apps/*/src/features/**"
  - "docs/specs/**"
  - "**/__tests__/**"

reference:
  - "packages/shared-ui/**"
  - "packages/shared-hooks/**"
  - "packages/api-client/**"

structure:
  - "pnpm-workspace.yaml"
  - "package.json"
  - "apps/*/src/routes/**"
```

你应该根据目标仓库实际结构调整这份规则。

## 脚本接口

### 1. `detect-impact`

用于分类本次 diff 是否影响 context：

```bash
python ".project-context/scripts/manage_context.py" detect-impact \
  --base "<base-sha>" \
  --head "<head-sha>" \
  --rules ".project-context/impact-rules.yaml"
```

支持输出格式：

- `text`
- `json`
- `github-output`

### 2. `sync --check`

用于只读检查当前 PR 是否已经同步必需的 context 文件：

```bash
python ".project-context/scripts/manage_context.py" sync \
  --base "<base-sha>" \
  --head "<head-sha>" \
  --impact "reference" \
  --check
```

当前版本只支持 `--check`。

它不会改文件，只会：

- 检查 `profile.yaml` 是否存在
- 判断当前 impact 对应的必需资产是否已在当前 diff 中同步
- 缺失时返回失败并打印修复提示

## 返回码约定

- `0`：检查通过
- `1`：脚本本身执行错误
- `2`：需要同步 context，但当前 PR 尚未补齐

## 当前行为边界

这一版是**轻量兜底**，不是全自动维护系统。

它目前能做到：

- 检测当前 PR 是否命中上下文影响
- 检查必需 context 文件是否跟着一起改了
- 在 GitHub 上阻断明显过期的 context

它目前还不会：

- 自动理解代码语义并重建索引
- 自动生成 bot PR
- 自动修改 `.project-context`
- 自动帮你解决误报

真正的同步动作仍然应由开发者或 AI 在 Cursor 中运行 `sync-context` 完成。

## 推荐工作流

推荐在目标仓库里这样使用：

1. 先运行 `initialize` 建立第一版 `.project-context`
2. 安装 GitHub context-check
3. 正常开发、提 PR
4. 如果 check 失败，在 Cursor 中运行 `sync-context`
5. 把同步后的 `.project-context` 一起提交
6. 重新推送并通过检查

## 何时需要调整规则

当出现以下情况时，应优先调整 `impact-rules.yaml`：

- 误报太多，开发者频繁被无意义阻断
- 漏报太多，重要 context 漂移没有被发现
- 仓库目录结构与默认规则差异很大
- 共享组件、测试入口、路由骨架路径不在默认命中范围内

## 建议的 rollout

建议分两阶段：

### Phase 1：只做提醒或非 required check

先观察：

- 误报率
- 漏报率
- `impact-rules.yaml` 是否符合仓库结构

### Phase 2：升级为 required check

当规则基本稳定、团队已接受 `.project-context` 工作流后，再把它设成必过检查。

## 与 skill 的关系

这个能力不应该单独拆成一个新 skill。

更合理的归属是：

- 作为 `sync-context` 的配套自动化能力
- 由 `initialize` 在首次建档时按需安装

原因：

- 它本质上服务的是 context 维护
- 它不生产新资产模型，只检查现有模型是否已同步
- 它不值得成为第 5 个顶层入口

一句话总结：

**GitHub context-check 是 `sync-context` 的自动化外壳，不是独立 skill。**
