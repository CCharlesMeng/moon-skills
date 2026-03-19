---
name: 同步仓库上下文
description: 用于在 `.project-context` 已存在时，根据代码变更、共享模式变化或结构变化，增量同步仓库上下文资产。
---

# 同步仓库上下文

## 概述

这个 skill 用于在仓库发生重要变化后，增量更新 `.project-context/`。

它是唯一的上下文维护入口：

- 负责已有 context 的刷新
- 负责 references / feature index 的增量修正
- 负责 freshness / confidence / uncertainty 的维护
- 不负责首次初始化
- 不负责事故调试

如果仓库不存在 `.project-context/profile.yaml`，不要使用本 skill，直接使用 `initialize`。

## 硬门禁

1. **不要盲目重建。** 更新前必须先读取现有 context 资产。
2. **不要无触发地更新上下文。** 任何更新都必须对应代码、结构、共享模式或特性变化。
3. **不要静默重写稳定内容。** 能保留的部分尽量保留。
4. **不要让过期上下文继续看起来很可靠。** confidence 下降时必须明确写出。
5. **不要把 sync 当 initialize 用。** 若没有 `profile.yaml`，先走 `initialize`。

## 何时使用

适用场景：

- 已存在 `.project-context/profile.yaml`
- 模块边界、目录结构、路由骨架或关键 flow 发生变化
- 共享组件、公共 hooks、公共 API 模式发生变化
- 特性相关的 code / test / spec refs 发生变化
- 其他 skill 报告当前 repo context 已过期、失真或与证据不一致

不适用场景：

- 仓库尚未初始化
- 当前变更只是明确的局部小改，且不影响 context 资产
- 当前任务是事故排查与免疫沉淀

## 工作流

### Phase 0：识别触发源

先明确这次为什么需要同步：

- `feature`
- `reference`
- `structure`
- `manual`

优先通过 diff、脚本和显式证据识别，不要靠感觉判断。

### Phase 1：读取现有上下文

读取当前：

- `.project-context/profile.yaml`
- `.project-context/references.yaml`
- `.project-context/features/index.yaml`
- `.project-context/PROFILE.md`

如存在 immune 资产，也可读取：

- `.project-context/immune-registry.yaml`
- `.project-context/immune-candidates.yaml`

### Phase 2：按影响面增量更新

根据触发源，只更新必要资产：

- `feature`
  - 重点更新 `features/index.yaml`
- `reference`
  - 重点更新 `references.yaml`
- `structure`
  - 重点更新 `profile.yaml`
  - 必要时联动修正 `references.yaml` 与 `features/index.yaml`
- `manual`
  - 明确说明人工指定了哪些更新范围

如果同步导致某些判断不再可靠，必须降低 `confidence` 或增加 `uncertainty`。

### Phase 3：保持人类摘要一致

当机器资产发生有效变化时，刷新 `.project-context/PROFILE.md`，确保它仍能帮助维护者快速审查上下文状态。

### Phase 4：可选安装 GitHub context-check

如果当前仓库使用 GitHub，且用户希望启用自动检查，可在本阶段一并安装：

- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`
- `.project-context/scripts/manage_context.py`
- `.project-context/scripts/context_common.py`

建议优先使用 `sync-context` 自带脚本和模板，保持不同仓库间行为一致。

### Phase 5：记录后续补全提示

同步结束时，必须明确：

- 哪些资产已更新
- 哪些区域仍然不确定
- 哪些 context 仍需未来任务继续补全
- 是否建议启用或调整 GitHub context-check 规则

这里只记录 context 维护提示，不要展开为需求排期、技术债清单或审计结论。

## GitHub context-check

这个 skill 自带一套轻量自动化，目标是：

- 在 PR 上检测本次改动是否影响 `.project-context`
- 若影响存在，检查 context 是否已同步
- 给出明确修复提示

它不负责：

- 自动改主分支
- 自动生成 bot PR
- 替开发者偷偷维护 context 正文

推荐实现是：

- `detect-impact` 负责 diff 分类
- `sync --check` 负责只读校验
- GitHub Actions 负责兜底
- Cursor / AI 负责真正执行 `sync-context`

完整对接说明见 [github-context-check.md](github-context-check.md)。

## 最终输出

结束时必须包含：

### Context Sync Summary

- 触发原因
- 更新了哪些资产
- confidence 是上升、下降还是不变

### Files Updated

- `profile.yaml`
- `references.yaml`
- `features/index.yaml`
- `PROFILE.md`
- 可选安装的 GitHub context-check 文件

### 后续补全提示

- 仍未解决、会影响后续判断的歧义
- 需要继续补全的区域或资产
- 建议在后续相关任务中继续验证的上下文风险点
