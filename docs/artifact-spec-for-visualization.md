# Moon-Skills 产物规格说明（面向可视化设计）

本文档描述 moon-skills 工作流中所有产物的结构、字段和源文件关联，供可视化工具设计使用。

---

## 一、产物总览

### 产物分布地图

```
.project-context/                          ← 上下文层（跨 session 持久化）
├── profile.yaml                           ← initialize 产出，sync-context 维护
├── references.yaml                        ← initialize 产出，sync-context 维护
├── features/
│   └── index.yaml                         ← initialize 产出，sync-context 维护
├── PROFILE.md                             ← initialize 产出，sync-context 维护
├── lenses/
│   └── *.md                               ← initialize Phase 3.5 产出（可选）
├── review-rules/
│   ├── base.md                            ← initialize 产出（可选）
│   ├── <topic>.md                         ← design-pack Phase 3 产出
│   └── defensive.md                       ← immune-debug 追加
├── verify-packs/
│   └── *.md                               ← 用户自定义（可选）
├── immune-registry.yaml                   ← immune-debug 产出
├── immune-candidates.yaml                 ← immune-debug 产出
├── impact-rules.yaml                      ← initialize/sync-context 产出（可选）
└── scripts/
    ├── manage_context.py                  ← initialize/sync-context 产出（可选）
    └── context_common.py                  ← initialize/sync-context 产出（可选）

docs/specs/<topic>/                        ← 分析交付层（per-topic）
├── analysis-spec.md                       ← analysis-spec 产出
├── design-pack.md                         ← design-pack 产出（按需）
├── slice-plan.md                          ← slice-plan 产出
├── spec-check.md                          ← spec-check 产出
├── reflect.md                             ← audit 产出
├── verify-summary.md                      ← verify 产出（可选，整轮汇总）
└── slices/<slice-id>/
    ├── code-review.md                     ← code-review 产出
    ├── verify.md                          ← verify 产出
    └── spec-check.md                      ← spec-check 产出（可选，per-slice）
```

### 产物生命周期分类

| 类别 | 产物 | 特征 |
|---|---|---|
| **持久化资产** | profile.yaml, references.yaml, features/index.yaml, PROFILE.md, lenses, review-rules, immune-* | 跨 session 存在，随 sync-context/audit/immune-debug 演进 |
| **需求级工件** | analysis-spec.md, design-pack.md, slice-plan.md | 随需求创建，交付后归档 |
| **验证级工件** | code-review.md, verify.md, spec-check.md, reflect.md | 随 slice/需求完成后产出 |

---

## 二、持久化资产详解

### 2.1 profile.yaml — 仓库地图

| 属性 | 值 |
|---|---|
| **产出方** | `initialize` Phase 1 |
| **维护方** | `sync-context` |
| **路径** | `.project-context/profile.yaml` |
| **Skill 源文件** | `skills/initialize/SKILL.md` (Phase 1) |
| **Schema 源文件** | `skills/initialize/references/profile-schema.md` |

#### 可提取的可视化数据

| 数据维度 | 字段路径 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 仓库身份 | `repo.name`, `repo.type`, `repo.summary` | 文本 | 项目概览卡片 |
| 领域分类 | `context.domains[]` | 标签数组 | 领域分布标签云 |
| 技术栈 | `context.stacks[]` | 标签数组 | 技术栈标签 |
| 模块列表 | `modules[]` | 对象数组 | 模块架构图 |
| 模块路径 | `modules[].path` | 路径 | 目录树视图 |
| 模块类型 | `modules[].kind` | 枚举 (app/package/...) | 模块分类图标 |
| 模块领域 | `modules[].domain[]` | 标签数组 | 模块-领域关联矩阵 |
| 模块技术栈 | `modules[].stack[]` | 标签数组 | 模块-栈关联矩阵 |
| 入口点 | `modules[].entry_points[]` | 路径数组 | 入口点列表 |
| 关键流程 | `modules[].critical_flows[]` | 字符串数组 | 关键流程列表/流程图 |
| 置信度 | `modules[].confidence` | 枚举 (high/medium/low) | 置信度热力图 |
| 信号标签 | `modules[].signals[]` | 标签数组 (hotspot/legacy/needs-sync) | 模块健康状态指示 |
| 不确定项 | `uncertainty[]` | 文本数组 | 待解决问题清单 |
| 产出时间 | `generated_at` | ISO 时间 | 新鲜度指示 |
| 源提交 | `source_commit` | commit hash | 版本追溯 |

---

### 2.2 references.yaml — 共享参考模式索引

| 属性 | 值 |
|---|---|
| **产出方** | `initialize` Phase 2 |
| **维护方** | `sync-context`, `audit` (路由写回) |
| **路径** | `.project-context/references.yaml` |
| **Skill 源文件** | `skills/initialize/SKILL.md` (Phase 2) |
| **Schema 源文件** | `skills/initialize/references/references-schema.md` |

#### 可提取的可视化数据

| 数据维度 | 字段路径 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 参考模式列表 | `reference_patterns[]` | 对象数组 | 模式卡片墙 |
| 模式类型 | `reference_patterns[].kind` | 枚举 (business_component/ui_pattern/interaction_pattern/state_pattern/api_pattern/test_pattern) | 模式分类标签 |
| 模式摘要 | `reference_patterns[].summary` | 文本 | 模式说明 |
| 代码引用 | `reference_patterns[].refs[]` | 路径数组 | 模式-代码关联线 |
| 适用场景 | `reference_patterns[].use_when[]` | 文本数组 | 使用指引 |
| 避免场景 | `reference_patterns[].avoid_when[]` | 文本数组 | 反模式提示 |
| 测试入口 | `reference_patterns[].tests[]` | 路径数组 | 测试覆盖关联 |
| 模式置信度 | `reference_patterns[].confidence` | 枚举 | 模式可信度指示 |
| 最后验证时间 | `reference_patterns[].last_verified_at` | 日期 | 新鲜度指示 |
| 反例列表 | `anti_examples[]` | 对象数组 | 反例警示卡片 |
| 反例原因 | `anti_examples[].reason` | 文本 | 反例说明 |
| 反例引用 | `anti_examples[].refs[]` | 路径数组 | 反例代码定位 |
| 风险热点 | `risk_hotspots[]` | 对象数组 | 风险热力图 |
| 热点摘要 | `risk_hotspots[].summary` | 文本 | 热点说明 |
| 热点引用 | `risk_hotspots[].refs[]` | 路径数组 | 热点代码定位 |
| 测试模式 | `test_patterns[]` | 对象数组 | 测试模式参考 |

---

### 2.3 features/index.yaml — 关键特性索引

| 属性 | 值 |
|---|---|
| **产出方** | `initialize` Phase 3 |
| **维护方** | `sync-context` |
| **路径** | `.project-context/features/index.yaml` |
| **Skill 源文件** | `skills/initialize/SKILL.md` (Phase 3) |
| **Schema 源文件** | `skills/initialize/references/feature-index-schema.md` |

#### 可提取的可视化数据

| 数据维度 | 字段路径 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 特性列表 | `features[]` | 对象数组 | 特性卡片墙/特性树 |
| 特性名称 | `features[].title` | 文本 | 特性标题 |
| 特性状态 | `features[].status` | 枚举 (active/legacy/unknown) | 特性生命周期状态 |
| 规格文档 | `features[].spec_refs[]` | 路径数组 | 特性-文档关联 |
| 验收文档 | `features[].acceptance_refs[]` | 路径数组 | 特性-验收关联 |
| 所属模块 | `features[].module_refs[]` | ID 数组 | 特性-模块关联矩阵 |
| 代码入口 | `features[].code_refs[]` | 路径数组 | 特性-代码关联 |
| 测试引用 | `features[].test_refs[]` | 路径数组 | 特性-测试关联（测试覆盖度） |
| 负责团队 | `features[].owners[]` | 字符串数组 | 特性-团队关联 |
| 置信度 | `features[].confidence` | 枚举 | 特性上下文可信度 |
| 更新时间 | `features[].updated_at` | 日期 | 特性新鲜度 |
| 不确定项 | `features[].uncertainty[]` | 文本数组 | 特性级待解决问题 |

---

### 2.4 PROFILE.md — 人类可读摘要

| 属性 | 值 |
|---|---|
| **产出方** | `initialize` Phase 4 |
| **维护方** | `sync-context` |
| **路径** | `.project-context/PROFILE.md` |
| **Skill 源文件** | `skills/initialize/SKILL.md` (Phase 4) |

#### 内容结构

非结构化 Markdown，但应包含以下信息区块：

| 信息区块 | 可视化用途 |
|---|---|
| 仓库概述 | 项目介绍文本 |
| 主要结构描述 | 结构说明文本 |
| 当前共享参考模式 | 模式概览 |
| 当前关键特性 | 特性概览 |
| 低置信区域 / 上下文缺口 | 待补全区域高亮 |
| 项目级 lens 说明（如有） | lens 覆盖范围说明 |

---

### 2.5 lenses/*.md — 项目级领域检查清单

| 属性 | 值 |
|---|---|
| **产出方** | `initialize` Phase 3.5 |
| **消费方** | `analysis-spec` Phase D |
| **路径** | `.project-context/lenses/*.md` |
| **Skill 源文件** | `skills/initialize/SKILL.md` (Phase 3.5) |
| **格式模板** | `skills/analysis-spec/references/lens-template.md` |

#### 可提取的可视化数据

| 数据维度 | 数据类型 | 可视化用途 |
|---|---|---|
| lens 名称 | 文件名 | 检查维度标签 |
| 检查项列表 (4-8 项/lens) | Checkbox 文本 | 产品校验维度清单 |
| 覆盖的领域 | 文本 (workflow/tenant-visibility/audit-notify 等) | 领域覆盖图 |

---

### 2.6 review-rules/ — 代码检视规则

| 属性 | 值 |
|---|---|
| **路径** | `.project-context/review-rules/` |
| **消费方** | `code-review` Phase 0 |

#### 三层规则来源

| 文件 | 产出方 | 层级 | Skill 源文件 |
|---|---|---|---|
| `base.md` | `initialize` | 仓库级 | `skills/initialize/SKILL.md` |
| `<topic>.md` | `design-pack` Phase 3 | 需求级 | `skills/design-pack/SKILL.md` (Phase 3 Review Rules 提炼) |
| `defensive.md` | `immune-debug` Phase 3 | 防御级 | `skills/immune-debug/SKILL.md` (Review Rules 追加) |
| **格式模板** | — | — | `skills/code-review/references/review-rules-template.md` |

#### 可提取的可视化数据

| 数据维度 | 数据类型 | 可视化用途 |
|---|---|---|
| 规则总数 (按层级) | 数值 | 规则累积统计 |
| 仓库级规则列表 | Checkbox 文本 | 基础规范清单 |
| 需求级规则列表 (per-topic) | Checkbox 文本 | 需求级约束清单 |
| 防御级规则列表 | Checkbox 文本 | 事故防护清单 |
| 规则来源关联 | ADR/事故引用 | 规则溯源图 |

---

### 2.7 immune-registry.yaml — 免疫注册表（正式区）

| 属性 | 值 |
|---|---|
| **产出方** | `immune-debug` Phase 3 |
| **维护方** | `audit` Phase 2 |
| **路径** | `.project-context/immune-registry.yaml` |
| **Skill 源文件** | `skills/immune-debug/SKILL.md` (Phase 3) |
| **决策矩阵** | `skills/immune-debug/references/immune-decision-matrix.md` |

#### 可提取的可视化数据

| 数据维度 | 数据类型 | 可视化用途 |
|---|---|---|
| 防护资产列表 | 对象数组 | 免疫防线卡片墙 |
| 主决策类型 | 枚举 (文档/提示词规则/测试/Lint静态检查) | 防护类型分布饼图 |
| 作用范围 | 枚举 (模块/仓库/领域/技术栈/全局) | 防护覆盖范围图 |
| 置信度 | 枚举 (低/中/高) | 防护可靠度指示 |
| 根因摘要 | 文本 | 事故教训列表 |
| 创建时间 | `added_at` ISO datetime | 资产年龄指示 |
| 最后检视时间 | `last_checked_at` ISO datetime | 新鲜度衰减指示（超 90 天未检视则显示衰减色） |
| 最后触发时间 | `last_triggered_at` ISO datetime | 规则活跃度指示 |
| 防御规则关联 | `defensive_rule_id` 字符串 | 与 defensive.md 规则的追溯链接 |
| 治理状态标签 | `governance_tags` 字符串数组 | `needs-review` 等标签的可视化徽标 |

---

### 2.8 immune-candidates.yaml — 免疫候选区

| 属性 | 值 |
|---|---|
| **产出方** | `immune-debug` Phase 3 |
| **维护方** | `audit` Phase 2 (promote/reject/keep) |
| **路径** | `.project-context/immune-candidates.yaml` |
| **Skill 源文件** | `skills/immune-debug/SKILL.md` (Phase 3) |

#### 可提取的可视化数据

| 数据维度 | 数据类型 | 可视化用途 |
|---|---|---|
| 候选资产列表 | 对象数组 | 候选队列 |
| 候选状态 | 枚举 (观察中/待提升/待拒绝) | 候选状态流转 |
| 进入原因 | 文本 | 候选理由说明 |
| 审查历史 | audit 结果记录 | 候选资产治理时间线 |

---

## 三、需求级工件详解

### 3.1 analysis-spec.md — 分析规格

| 属性 | 值 |
|---|---|
| **产出方** | `analysis-spec` Phase D |
| **消费方** | `design-pack`, `slice-plan`, `spec-check` |
| **路径** | `docs/specs/<topic>/analysis-spec.md` |
| **Skill 源文件** | `skills/analysis-spec/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| **现状摸底** | 当前行为、入口点、共享依赖、风险点、验证缺口 | 结构化文本 | 现状概览面板 |
| **自学习状态表** | `Q-N`, 问题, 状态 (🔴/🟡/🟢), 依据/推理 | 表格 | 三色置信度仪表盘 |
| **澄清结论** | 每轮澄清结果, 用户确认, 🟡已接受项 | 记录列表 | 澄清过程时间线 |
| **激活的领域检查清单** | 前端/后端/集成/风险记忆 (checkbox) | 布尔数组 | 检查清单覆盖状态 |
| **目标行为 (TB)** | `TB-N`, 行为描述 | 编号表格 | TB 卡片列表 — **核心追溯起点** |
| **不做的事** | NonGoals 列表 | 文本列表 | 范围边界清单 |
| **风险清单** | 风险, 严重度 (high/medium/low), 缓解方式 | 表格 | 风险矩阵/风险雷达图 |
| **证据计划** | TB 编号, 验证思路 | 映射表 | TB-验证关联图 |
| **下一步路由** | 是否进入 design-pack + 判断依据 | 文本 | 工作流路由指示 |

#### 关键关联

```
TB-N  →  AC-N.M (design-pack)  →  TC-N.M.K (design-pack)  →  EV (verify)
  ↘  Risk-N (analysis-spec)
  ↘  ADR-N (design-pack，仅在关键取舍时)
```

---

### 3.2 design-pack.md — 设计与验收包

| 属性 | 值 |
|---|---|
| **产出方** | `design-pack` Phase 1-5 |
| **消费方** | `slice-plan`, `code-review`, `verify`, `spec-check` |
| **路径** | `docs/specs/<topic>/design-pack.md` |
| **Skill 源文件** | `skills/design-pack/SKILL.md` |
| **模板** | `skills/design-pack/references/design-pack-template.md` |

#### 文件内部结构与可提取数据

| Phase | 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|---|
| **Phase 1** | 业务验收 | `AC-N.M` (← TB-N), Given/When/Then 或检查项 | 编号表格 | AC 卡片列表，AC↔TB 追溯线 |
| Phase 1 | 不做的事 (细化) | NonGoals 列表 | 文本列表 | 范围边界清单 |
| Phase 1 | 验收确认方式 | TB 编号 → 确认方式 | 映射表 | 验收方式矩阵 |
| **Phase 2** | 实体与关系 | 实体名, 核心属性, 生命周期, 归属 | 表格 | 实体关系图 (ER) |
| Phase 2 | 状态机 | 状态流转图 | 有向图 | 状态机可视化 |
| Phase 2 | 领域事件 | 事件名, 触发条件, 消费方 | 表格 | 事件流图 |
| Phase 2 | 统一语言 | 术语, 定义, 注意 | 字典表 | 领域词汇表 |
| **Phase 3** | 技术栈确认 | 层, 选择, 状态 (已有/新增) | 表格 | 技术栈面板 |
| Phase 3 | ADR | 背景, 选项, 决定, 后果, 引用 TB/Risk | 结构化记录 | ADR 决策卡片 |
| Phase 3 | API/接口契约 | 请求/响应结构, 错误处理, 版本化 | 接口描述 | API 契约面板 |
| Phase 3 | Review Rules | 领域命名/架构约束/契约/组件边界规则 | 规则列表 | 规则提炼来源图 |
| **Phase 4** | 测试规格 | `TC-N.M.K` (← AC-N.M), 层级, 类型, 描述 | 编号表格 | TC 卡片列表，TC↔AC 追溯线 |
| Phase 4 | TC 层级 | unit/integration/e2e/manual | 枚举 | 测试层级分布 |
| Phase 4 | TC 类型 | happy-path/boundary/failure-path/adversarial | 枚举 | 测试类型分布 |
| **Phase 5** | 工作量评估 | 整体规模 (S/M/L/XL), 工作块, 复杂度, 风险, 预估 | 表格 | 工作量估算面板 |
| Phase 5 | Appetite | 时间不足时的砍法建议 | 文本 | 范围取舍指引 |

---

### 3.3 slice-plan.md — 切片计划

| 属性 | 值 |
|---|---|
| **产出方** | `slice-plan` |
| **消费方** | `code-review`, `verify`, `spec-check` |
| **路径** | `docs/specs/<topic>/slice-plan.md` |
| **Skill 源文件** | `skills/slice-plan/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 切片列表 | `S-N`, 目标行为, 引用 TB, 引用 AC, 测试先行清单 (TC), 受影响文件, 风险, 验证方式, 回滚方式 | 编号表格 | 切片甘特图/看板 |
| 执行顺序 | S-N 排序 + 依赖关系说明 | 有向图 | Slice 依赖关系图 |
| 延后项 | deferred 条目 + 原因 | 列表 | 延后项清单 |
| 工作模式策略 | patch-lite/feature-slice/migration-strict 额外要求 | 文本 | 模式适配说明 |

---

## 四、验证级工件详解

### 4.1 code-review.md — 代码检视报告

| 属性 | 值 |
|---|---|
| **产出方** | `code-review` |
| **路径** | `docs/specs/<topic>/slices/<slice-id>/code-review.md` |
| **Skill 源文件** | `skills/code-review/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 检视范围 | 改动文件数, 应用 rules 数 (按层级) | 数值 | 检视范围面板 |
| Blocking Issues | 编号, 文件, Rule, 问题描述, 建议修正 | 表格 | 阻塞问题清单 (红色) |
| Suggestions | 编号, 文件, Rule, 建议 | 表格 | 改进建议清单 (黄色) |
| 按文件明细 | 文件 → Rule → 判定 (pass/n/a/blocking/suggestion) | 矩阵 | 文件-规则检视矩阵 |
| 统计 | pass/n/a/blocking/suggestion 各多少 | 数值 | 检视通过率环形图 |

---

### 4.2 verify.md — 行为验证报告

| 属性 | 值 |
|---|---|
| **产出方** | `verify` |
| **路径** | `docs/specs/<topic>/slices/<slice-id>/verify.md` |
| **Skill 源文件** | `skills/verify/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| Evidence Ledger | TC 编号, AC 编号, 状态 (pass/n/a/deferred/failed), EV 描述, 说明 | 表格 | TC 证据台账 — **核心追溯终点** |
| Verify Pack Results | 检查项, 状态, 证据, 说明 | 表格 (per-pack) | 领域验证状态矩阵 |
| Spec Deviations | 偏差描述, 影响 TB/AC, 严重度 (blocking/notable), 建议 | 表格 | Spec 偏差警示 |
| Open Risks | 风险描述 | 列表 | 开放风险标记 |
| Replan Recommendation | 回到 analysis-spec / design-pack / slice-plan | 文本 | Replan 路由指示 |
| 统计 | TC pass/failed/deferred/n/a, Verify pack pass/deferred, Spec deviations (blocking/notable) | 数值 | 验证通过率仪表盘 |

---

### 4.3 spec-check.md — 规格对账

| 属性 | 值 |
|---|---|
| **产出方** | `spec-check` |
| **路径** | `docs/specs/<topic>/spec-check.md` |
| **Skill 源文件** | `skills/spec-check/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 对账结果 | TB 编号, Behavior, 状态 (as_specified/intentionally_changed/deferred/abandoned), 说明 | 表格 | **TB 交付状态仪表盘** |
| 隐性偏差 | 偏差描述, 发现来源, 影响 | 表格 | 隐性偏差列表 |
| 统计 | as_specified/intentionally_changed/deferred/abandoned/unplanned 各多少 | 数值 | 交付兑现率环形图 |
| 交给 audit 的输入 | 偏差项、可复用 learning、context 更新信号 | 列表 | audit 路由输入 |

---

### 4.4 reflect.md — 交付复盘

| 属性 | 值 |
|---|---|
| **产出方** | `audit` Phase 3 |
| **路径** | `docs/specs/<topic>/reflect.md` |
| **Skill 源文件** | `skills/audit/SKILL.md` |

#### 文件内部结构与可提取数据

| 章节 | 内部字段 | 数据类型 | 可视化用途 |
|---|---|---|---|
| 资产状态表 | 资产名, 审查结果 (keep/update/merge/promote/deprecate/reject) | 表格 | 资产治理看板 |
| 可复用模式 | 本轮发现的正例/反例 | 列表 | 可复用 learning 沉淀 |
| Context drift | 上下文漂移描述 | 列表 | 漂移警示 |
| 长期防护机会 | 免疫候选/提升信号 | 列表 | 免疫沉淀管道 |
| 下轮关注点 | 风险/盲区/待验证 | 列表 | 下轮压力清单 |
| 路由决策 | → sync-context / → immune / → 仅观察 | 枚举 | 路由决策指示器 |

---

## 五、追溯链全景

这条追溯链是整套工作流的核心数据主线，贯穿所有需求级和验证级工件：

```
TB (analysis-spec)
 ├── → AC (design-pack Phase 1)         每个 TB 至少一个 AC
 │     ├── → TC (design-pack Phase 4)   每个 AC 至少一个 TC
 │     │     └── → EV (verify)          每个 TC 挂到一条 EV
 │     └── → 验收确认方式
 ├── → Risk (analysis-spec)
 ├── → ADR (design-pack Phase 3)        仅关键取舍
 ├── → Slice (slice-plan)               Slice 引用 TB + AC + TC
 └── → 对账状态 (spec-check)            as_specified / changed / deferred / abandoned
```

### 追溯链数据源映射

| 追溯节点 | 编号规则 | 所在文件 | 所在章节 |
|---|---|---|---|
| TB | `TB-N` | `analysis-spec.md` | 目标行为 |
| AC | `AC-N.M` (← TB-N) | `design-pack.md` | Phase 1 业务验收 |
| TC | `TC-N.M.K` (← AC-N.M) | `design-pack.md` | Phase 4 测试规格 |
| EV | 与 TC 编号对应 | `verify.md` | Evidence Ledger |
| ADR | `ADR-N` | `design-pack.md` | Phase 3 技术方案 |
| Risk | `Risk-N` | `analysis-spec.md` | 风险清单 |
| Slice | `S-N` | `slice-plan.md` | 切片列表 |
| 对账状态 | 与 TB-N 对应 | `spec-check.md` | 对账结果 |

---

## 六、跨产物关联矩阵

| 源产物 | 消费产物 | 关联字段 |
|---|---|---|
| `profile.yaml` | `analysis-spec` (Phase 0 上下文预热) | modules, critical_flows, uncertainty |
| `references.yaml` | `analysis-spec` (Phase B 自学习), `design-pack` (Phase 3 Reuse check) | reference_patterns, risk_hotspots |
| `features/index.yaml` | `analysis-spec` (Phase A 摸底) | features[].code_refs, test_refs |
| `lenses/*.md` | `analysis-spec` (Phase D 领域检查) | 检查项列表 |
| `analysis-spec.md` | `design-pack`, `slice-plan`, `spec-check` | TB-N, Risk-N, NonGoals |
| `design-pack.md` | `slice-plan`, `code-review`, `verify` | AC-N.M, TC-N.M.K, ADR-N, Review Rules |
| `review-rules/*.md` | `code-review` (Phase 0 收集 Rules) | 规则列表 (仓库级+需求级+防御级) |
| `slice-plan.md` | `code-review`, `verify`, `spec-check` | S-N, 受影响文件, TC 先行清单 |
| `code-review.md` | `verify` (前置门禁) | blocking issue 数量 |
| `verify.md` | `spec-check` (前置门禁) | Evidence Ledger, Spec Deviations |
| `spec-check.md` | `audit` (输入) | 对账状态, 隐性偏差 |
| `reflect.md` | `sync-context` (路由写回) | context drift, 可复用模式 |
| `immune-registry.yaml` | `analysis-spec` (Phase B 硬约束), `code-review` (防御级) | 防护资产列表 |
| `immune-candidates.yaml` | `analysis-spec` (Phase B 弱信号) | 候选资产列表 |

---

## 七、工作模式对产物的影响

| 产物 | patch-lite | feature-slice | migration-strict |
|---|---|---|---|
| `analysis-spec.md` | 压缩版，Phase 可合并 | 完整 | 完整 + 兼容承诺 |
| `design-pack.md` | **跳过** | 按触发矩阵决定 | **必做** |
| `slice-plan.md` | 通常 1 个 slice | 正常切片 | 必须有 compatibility slice |
| `code-review.md` | 压缩，只做仓库级 | 完整三层 | 完整 + 兼容层审查 |
| `verify.md` | 压缩，允许人工 EV | 完整 TC + verify pack | 完整 + integration pack 必做 |
| `spec-check.md` | 语义不可跳过 | 完整 | 完整 |
| `reflect.md` | 语义不可跳过 | 完整 | 完整 |

---

## 八、可视化场景建议

基于以上产物数据，以下是高价值的可视化场景：

| 场景 | 核心数据源 | 视觉形式 |
|---|---|---|
| **项目全景** | profile.yaml + features/index.yaml | 模块架构图 + 特性树 |
| **模块健康度** | profile.yaml (confidence, signals, uncertainty) | 模块热力图/仪表盘 |
| **共享模式库** | references.yaml | 模式卡片墙 (含正例/反例/风险热点) |
| **特性-模块关联** | features/index.yaml + profile.yaml | 关联矩阵/桑基图 |
| **需求追溯链** | analysis-spec → design-pack → slice-plan → verify → spec-check | TB→AC→TC→EV 追溯瀑布 |
| **交付进展** | spec-check.md (对账状态统计) | 交付兑现率仪表盘 |
| **风险雷达** | analysis-spec (风险清单) + references (risk_hotspots) + immune-* | 风险矩阵/雷达图 |
| **测试覆盖** | design-pack (TC) + verify (EV) | 测试层级/类型分布 + 通过率 |
| **代码质量** | code-review (统计) + review-rules (累积) | 检视通过率 + 规则累积趋势 |
| **免疫防线** | immune-registry + immune-candidates | 免疫资产管道 (候选→正式) |
| **上下文新鲜度** | profile.yaml (generated_at) + references (last_verified_at) + features (updated_at) | 新鲜度时间线/衰减指示 |
| **工作模式分布** | analysis-spec (工作模式字段) | 需求类型分布 |
