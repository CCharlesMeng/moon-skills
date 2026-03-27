---
name: 初始化仓库上下文
description: 用于 AI 首次接手仓库时，创建 `.project-context/` 的最小可用上下文底座，包括仓库地图、共享参考模式、关键特性索引和人类摘要。
---

# 初始化仓库上下文

## 概述

这个 skill 用于在 `.project-context/` 下创建仓库的第一版机器可读上下文。

它的目标是交付一个**最小可用底座**，让后续 AI 工作可以开始，而不是一次性产出“完整真相”。

允许留下明确未知项，但不要把初始化产物写成风险审计、技术债清单或研发路线图。

这是一个初始化型 skill：

- 负责首次建档
- 负责建立共享参考模式入口
- 负责建立关键特性的稀疏索引
- 不负责持续维护
- 不负责完整架构复原

如果仓库已经存在 `.project-context/profile.yaml`，不要使用本 skill，直接使用 `sync-context`。

## 硬门禁

1. **不要臆造仓库结构。** 所有判断必须基于文件、配置、脚本、测试和代码证据。
2. **不要过度建模。** 建立导航和索引即可，不要试图在初始化阶段重建全部架构。
3. **不要把猜测写成权威事实。** 不确定项必须显式标注。
4. **不要跳过机器可读产物。** 人类摘要是辅助，机器索引才是主产物。
5. **不要在已初始化仓库上重建。** 只要 `profile.yaml` 已存在，后续刷新一律交给 `sync-context`。

## 何时使用

适用场景：

- 仓库不存在 `.project-context/profile.yaml`
- AI 第一次接手该仓库
- 需要为一个存量仓库建立首轮 AI 可用上下文
- 需要快速建立仓库地图、共享参考模式和关键特性索引

不适用场景：

- 仓库已经存在 `.project-context/profile.yaml`
- 当前任务只是已初始化仓库中的普通开发、修 bug 或调试
- 你只是需要刷新过期上下文
- 你需要对单个模块做更深的专题分析
- 你需要做深层技术债审计

## 工作流

### Phase 0：优先使用确定性输入

在写任何上下文之前：

1. 从真实文件中识别 repo root、apps、packages、模块边界、入口点和测试入口。
2. 检查 workspace 文件、构建配置、路由配置、依赖声明、CI 配置和现有文档。
3. 如果仓库已经有脚本、索引器或生成产物，优先使用。
4. 只有在确定性输入无法覆盖时，才使用模型判断。

### Phase 1：建立仓库地图

创建 `.project-context/profile.yaml`，只记录仓库级导航信息：

- 仓库身份与类型
- 主要模块边界
- domain / stack 提示
- 入口点与关键 flow
- freshness / provenance 元数据
- confidence 与 uncertainty

目标是让后续任务能快速定位，不是输出完整架构文档。

字段指导见 [references/profile-schema.md](references/profile-schema.md)。

### Phase 2：建立共享参考模式索引

创建 `.project-context/references.yaml`，优先记录全项目共享的高价值模式：

- 公共业务组件
- 典型交互模式
- 典型状态管理 / API 调用模式
- 测试样例入口
- 明确不要模仿的反例
- 容易误导后续任务判断的上下文风险点

优先记录 `refs`，不要堆长篇 prose。

字段指导见 [references/references-schema.md](references/references-schema.md)。

### Phase 3：建立关键特性索引

创建 `.project-context/features/index.yaml`，只建立**稀疏**的关键特性索引：

- 当前高价值或高频特性
- 当前任务相关特性
- 已有 spec / acceptance / code / test refs 明确的特性

不要在初始化阶段强行补全完整 feature tree。

字段指导见 [references/feature-index-schema.md](references/feature-index-schema.md)。

### Phase 3.5：按需起草并确认项目级 lens

当仓库存在默认 lens 覆盖不够、但会在多个产品特性中反复出现的校验维度时，可在初始化阶段提炼候选 lens，并在落盘前直接与用户确认。

触发信号：

- 多个特性共享同一种工作流 / 状态机 / 角色动作边界
- 多个特性反复出现同一种可见性 / 权限 / 租户 / 审计 / 通知约束
- 现有文档、代码、历史事故反复指向同一类产品风险
- 这些维度如果漏检，会在后续 `analysis-spec` 中持续造成验收缺口

约束：

- 默认生成 `0-3` 个项目级 lens；如果默认 lens 足够，就不要创建自定义 lens
- 每个 lens 保持 `4-8` 条检查项，只描述跨多个特性的产品校验维度
- 不要把页面细节、一次性需求、实现方案或空泛口号写进 lens
- 项目级 lens 本体只允许写入已确认、可长期复用的检查项
- 不要在 lens 文件中写 `draft` 时间、`待确认`、`assumption` 等过程性信息
- 会影响 lens 是否成立的低置信前提，必须在初始化过程中直接向用户确认；未确认前不得写入 lens 本体

执行步骤：

1. 基于代码、文档和已有上下文提炼候选 lens
2. 抽取会影响 lens 成立范围的低置信前提
3. 在初始化过程中直接向用户确认这些前提
4. 仅将确认后的 lens 写入 `.project-context/lenses/`
5. 未确认内容保留在 `PROFILE.md` 的上下文缺口中，不进入 lens 本体

输出形式：

- 在对话中先展示候选 lens 与待确认点
- 确认后在 `.project-context/lenses/` 下创建正式文件
- 在 `PROFILE.md` 中说明为什么创建这些 lens、它们覆盖哪些特性级风险、以及仍未收敛的上下文缺口

### Phase 4：生成人类摘要与可选骨架

创建 `.project-context/PROFILE.md`，帮助维护者快速审查首轮结果是否明显失真。

`PROFILE.md` 是首轮上下文摘要，不是 backlog、技术债审计或完整 onboarding 文档。

该摘要应简洁回答：

- 这个仓库是什么
- 主要结构是什么
- 当前识别到哪些共享参考模式
- 当前识别到哪些关键特性
- 哪些地方目前仍低置信或待后续验证

如果当前仓库使用 GitHub，且用户希望启用自动上下文检查，建议在初始化阶段一并安装：

- `.github/workflows/context-check.yml`
- `.project-context/impact-rules.yaml`
- `.project-context/scripts/manage_context.py`
- `.project-context/scripts/context_common.py`

优先复用 `sync-context` 自带的模板和脚本，保持不同仓库间行为一致。

完整对接方式见 `sync-context` 下的 [references/github-context-check.md](../sync-context/references/github-context-check.md)。

如有必要，可顺手创建以下空骨架以稳定后续工作流输入：

- `.project-context/immune-registry.yaml`
- `.project-context/immune-candidates.yaml`

### Phase 5：记录后续补全提示

初始化结束时，必须显式记录：

- 哪些模块或区域仍然低置信
- 哪些高频场景暂时缺少参考模式
- 哪些关键特性缺少 spec / acceptance / test refs
- 哪些资产建议在后续任务中交由 `sync-context` 持续刷新

这里只记录上下文维护提示，不要展开为具体研发排期、方案决策或大段治理建议。

## 必需产物

本 skill 默认应产出：

- `.project-context/profile.yaml`
- `.project-context/references.yaml`
- `.project-context/features/index.yaml`
- `.project-context/PROFILE.md`

可选骨架 / 产物：

- `.github/workflows/context-check.yml`
- `.project-context/lenses/*.md`
- `.project-context/impact-rules.yaml`
- `.project-context/scripts/manage_context.py`
- `.project-context/scripts/context_common.py`
- `.project-context/immune-registry.yaml`
- `.project-context/immune-candidates.yaml`

## 停止条件

满足以下条件后就应该停止，不再继续深挖：

- 仓库结构已经足够导航
- 至少找到一批项目级共享参考模式
- 当前高价值区域已有最小特性索引
- 项目级 lens 已明确为"无需新增"或已完成直接确认并生成少量正式文件
- 重要未知项已经显式写出
- 下一次 AI 任务已经可以基于这些资产开始工作

## 最终输出

结束时必须包含：

### 初始化摘要

- 仓库类型与主要模块
- 已识别共享参考模式概览
- 关键特性覆盖概览
- 是否创建了项目级 lens、它们覆盖的主题、以及是否经过直接确认
- 最重要的未知项

### Files Created

- profile 路径
- references 路径
- feature index 路径
- summary 路径
- lens 草稿路径（若生成）
- 可选骨架路径

### 后续补全提示

- 仍低置信、但会影响后续判断的模块或区域
- 缺少 spec / acceptance / tests 的关键特性
- 建议在未来任务中由 `sync-context` 持续维护的内容
