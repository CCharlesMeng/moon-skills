# Moon-Skills 可视化产品设计

## 产品定位

一个只读的项目仪表盘，从 `.project-context/` 和 `docs/specs/` 的产物中提取数据，帮助开发者和技术负责人在 30 秒内理解一个项目的全貌：它是什么、有什么能力、哪里健康、哪里有风险、当前在做什么、做得怎么样。

不做编辑，不做流程驱动，不替代 IDE 或项目管理工具。

---

## 核心用户场景

| # | 场景 | 用户问题 | 期望体验 |
|---|---|---|---|
| S1 | 刚接手一个仓库 | "这个项目到底是什么？有哪些模块？" | 打开仪表盘就能看到项目简介、模块架构和技术栈，不需要翻代码 |
| S2 | 开始新需求前 | "当前项目有哪些可复用的模式？有什么坑？" | 快速浏览共享模式和反例，避免重复造轮子或踩旧坑 |
| S3 | 需求交付中 | "我的需求分析到哪一步了？TB 都覆盖了吗？" | 看到当前 topic 的工作流进展和追溯链完整度 |
| S4 | 交付结束后 | "这轮交付兑现了多少承诺？有什么遗留？" | 看到 spec-check 的对账统计和 deferred 清单 |
| S5 | 项目治理 | "上下文资产还可信吗？有多少技术债？" | 看到置信度分布、新鲜度衰减和免疫防线状态 |
| S6 | 团队周会 | "项目整体在什么状态？有什么需要关注的？" | 一页看完项目健康度、活跃需求和风险点 |

---

## 信息架构

```
┌─────────────────────────────────────────────────────┐
│  项目仪表盘                                          │
│                                                     │
│  ┌─ 全景 ─┐  ┌─ 特性 ─┐  ┌─ 需求 ─┐  ┌─ 健康 ─┐   │
│  │        │  │        │  │        │  │        │   │
│  │ 项目   │  │ 特性   │  │ 活跃   │  │ 置信度 │   │
│  │ 概览   │  │ 索引   │  │ 需求   │  │ 总览   │   │
│  │        │  │        │  │ 列表   │  │        │   │
│  └────────┘  └────────┘  └────────┘  └────────┘   │
│       │           │           │           │        │
│       ▼           ▼           ▼           ▼        │
│   模块详情    特性详情    需求详情    治理详情       │
│                               │                    │
│                               ▼                    │
│                          追溯链视图                  │
└─────────────────────────────────────────────────────┘
```

一级导航四个视图，每个视图可下钻到详情。以下逐一展开。

---

## 视图一：全景

> 回答："这个项目是什么？结构长什么样？"

### 顶部 — 项目身份卡

展示项目的一句话定义和基本属性。

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 项目名称 | `profile.yaml → repo.name` | 大标题 |
| 项目类型 | `profile.yaml → repo.type` | 标签 (monorepo / single-app / library) |
| 项目简介 | `profile.yaml → repo.summary` | 副标题文本 |
| 领域 | `profile.yaml → context.domains[]` | 标签组 |
| 技术栈 | `profile.yaml → context.stacks[]` | 图标标签组 |
| 上下文生成时间 | `profile.yaml → generated_at` | 相对时间 ("3 天前") |

### 中部 — 模块地图

以卡片阵列或树形结构展示所有模块。

**每张模块卡片包含：**

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 模块名 | `profile.yaml → modules[].id` | 卡片标题 |
| 路径 | `modules[].path` | 灰色副文本 |
| 类型 | `modules[].kind` | 图标 (app / package / service / ...) |
| 领域标签 | `modules[].domain[]` | 小标签 |
| 置信度 | `modules[].confidence` | 色块指示 (绿/黄/红) |
| 信号 | `modules[].signals[]` | 角标 (hotspot 火焰 / legacy 时钟 / needs-sync 刷新) |
| 关键流程数 | `modules[].critical_flows[]` 的长度 | 数字徽标 |
| 关联特性数 | `features/index.yaml` 中 `module_refs` 包含该模块的 feature 数量 | 数字徽标 |

**卡片排列逻辑：**
- 按 `kind` 分组：先 app，再 package/service
- 组内按置信度排序：低置信度的靠前（优先暴露风险）

### 底部 — 不确定项横幅

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 全局不确定项 | `profile.yaml → uncertainty[]` | 黄色横幅列表，每条一行 |

这些不确定项是项目级的认知缺口，应该始终可见，不被隐藏。

---

## 视图二：特性

> 回答："项目有哪些能力？每个能力对应什么代码和测试？"

### 特性列表

以列表或卡片墙展示所有已索引的特性。

**每个特性条目包含：**

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 特性名称 | `features/index.yaml → features[].title` | 标题 |
| 状态 | `features[].status` | 状态标签 (active 绿色 / legacy 灰色 / unknown 黄色) |
| 置信度 | `features[].confidence` | 色点 |
| 所属模块 | `features[].module_refs[]` | 关联标签（可点击跳转到全景视图对应模块） |
| 负责团队 | `features[].owners[]` | 文本标签 |
| 更新时间 | `features[].updated_at` | 相对时间 |
| 引用完整度 | 基于 code_refs / test_refs / spec_refs / acceptance_refs 是否为空 | 四个图标指示：代码 / 测试 / 规格 / 验收 |

**引用完整度图标说明：**

| 图标含义 | 条件 | 展示 |
|---|---|---|
| 代码引用 | `code_refs[]` 非空 | 实心 / 空心 |
| 测试引用 | `test_refs[]` 非空 | 实心 / 空心 |
| 规格文档 | `spec_refs[]` 非空 | 实心 / 空心 |
| 验收文档 | `acceptance_refs[]` 非空 | 实心 / 空心 |

四个全空的特性视觉上应更弱化，提示该特性索引不完整。

**排序/筛选维度：**
- 按状态筛选
- 按模块筛选
- 按置信度排序
- 按更新时间排序

### 特性详情（下钻）

点击特性展开详情面板：

| 区域 | 内容 |
|---|---|
| 代码入口 | `code_refs[]` 列表，每条可复制路径 |
| 测试入口 | `test_refs[]` 列表 |
| 规格/验收 | `spec_refs[]` + `acceptance_refs[]` 列表 |
| 不确定项 | `uncertainty[]` 列表（黄色） |
| 关联需求 | 扫描 `docs/specs/*/analysis-spec.md` 中引用该特性相关模块的 topic 列表 |

---

## 视图三：需求

> 回答："当前在做什么？做到哪一步了？交付了多少？"

### 需求列表

扫描 `docs/specs/` 目录，每个 `<topic>` 子目录作为一条需求。

**每条需求包含：**

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 需求名称 | `<topic>` 目录名（kebab-case 转可读文本） | 标题 |
| 工作模式 | `analysis-spec.md` 中的工作模式字段 | 标签 (patch-lite / feature-slice / migration-strict) |
| 工作流阶段 | 基于目录下存在哪些文件推断 | 流程进度条 |
| TB 数量 | `analysis-spec.md` 中 TB 的条数 | 数字 |
| 交付兑现率 | `spec-check.md` 中 as_specified 的比例 | 百分比 + 迷你环形图 |
| 风险数量 | `analysis-spec.md` 中风险清单的 high 级数量 | 数字（红色）|

**工作流阶段推断逻辑：**

基于 topic 目录下存在的文件判断当前阶段：

| 已存在的文件 | 推断阶段 |
|---|---|
| 仅 `analysis-spec.md` | 分析完成 |
| + `design-pack.md` | 设计完成 |
| + `slice-plan.md` | 规划完成 |
| + `slices/*/code-review.md` | 检视中 |
| + `slices/*/verify.md` | 验证中 |
| + `spec-check.md` | 对账完成 |
| + `reflect.md` | 复盘完成 |

进度条按上述阶段从左到右排列，已完成阶段填色，当前阶段高亮。

**排序/筛选维度：**
- 按工作模式筛选
- 按阶段筛选（进行中 / 已完成）
- 按时间排序

### 需求详情（下钻）

点击需求进入详情页面，包含两个核心区域。

#### 区域 A — 工作流进度

水平流程图，展示该需求经过的每个 skill 阶段。

```
analysis-spec → design-pack → slice-plan → [S-1] → [S-2] → [S-3] → spec-check → audit
                                            │       │       │
                                         code-rev  code-rev code-rev
                                         verify    verify   verify
```

每个节点的状态：
- 灰色：未开始
- 蓝色填充：已完成
- 蓝色边框：当前进行中
- 红色：有阻塞问题

#### 区域 B — 追溯链全景

这是整个可视化工具的核心视图。以表格或瀑布形式展示一条需求中所有可追溯对象的关系和状态。

**列定义：**

| 列 | 数据源 | 说明 |
|---|---|---|
| TB | `analysis-spec.md → 目标行为` | 目标行为编号和描述 |
| AC | `design-pack.md → Phase 1` | 每个 TB 下挂的验收标准 |
| TC | `design-pack.md → Phase 4` | 每个 AC 下挂的测试规格 |
| EV | `verify.md → Evidence Ledger` | 每个 TC 对应的证据和状态 |
| Slice | `slice-plan.md` | 该 TB 属于哪个切片 |
| 对账 | `spec-check.md → 对账结果` | 最终交付状态 |

**每个单元格的状态色：**

| 对象 | 完整 | 缺失 | 异常 |
|---|---|---|---|
| TB | 绿 (已定义) | — (必定存在) | — |
| AC | 绿 (已定义) | 灰 (patch-lite 无 design-pack) | — |
| TC | 绿 (已定义) | 灰 (无 design-pack) | — |
| EV | 绿 (pass) | 灰 (deferred) | 红 (failed) |
| 对账 | 绿 (as_specified) | 黄 (deferred/changed) | 红 (abandoned) |

**交互：** 点击任意单元格展开详情气泡，显示该对象的完整内容（Given/When/Then、测试描述、证据描述等）。

#### 区域 C — 需求概况侧边栏

| 信息项 | 数据源 |
|---|---|
| 风险清单 | `analysis-spec.md → 风险清单` |
| 不做的事 | `analysis-spec.md → NonGoals` |
| ADR 列表 | `design-pack.md → Phase 3 ADR` |
| 延后项 | `slice-plan.md → deferred` + `spec-check.md → deferred` |
| 工作量评估 | `design-pack.md → Phase 5` |

---

## 视图四：健康

> 回答："项目上下文还可信吗？有多少风险？免疫防线怎么样？"

### 区域 A — 置信度总览

三个环形图并排，分别展示三类资产的置信度分布。

| 环形图 | 数据源 | 统计方式 |
|---|---|---|
| 模块置信度 | `profile.yaml → modules[].confidence` | 统计 high / medium / low 各多少 |
| 模式置信度 | `references.yaml → reference_patterns[].confidence` | 同上 |
| 特性置信度 | `features/index.yaml → features[].confidence` | 同上 |

### 区域 B — 新鲜度时间线

一条水平时间线，标注各资产的最后更新/验证时间。

| 数据点 | 数据源 | 含义 |
|---|---|---|
| 仓库上下文 | `profile.yaml → generated_at` | 仓库地图上次生成/同步时间 |
| 各参考模式 | `references.yaml → reference_patterns[].last_verified_at` | 每个模式上次验证时间 |
| 各特性 | `features/index.yaml → features[].updated_at` | 每个特性上次更新时间 |

超过 30 天未更新的数据点用衰减色标注（越久越暗淡）。

### 区域 C — 共享模式与反例

两栏布局：

**左栏 — 可复用模式：**

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 模式名 | `reference_patterns[].id` | 卡片标题 |
| 类型 | `reference_patterns[].kind` | 类型图标 |
| 摘要 | `reference_patterns[].summary` | 描述文本 |
| 代码引用 | `reference_patterns[].refs[]` | 路径链接 |
| 何时用 | `reference_patterns[].use_when[]` | 绿色标签 |
| 何时避免 | `reference_patterns[].avoid_when[]` | 黄色标签 |
| 置信度 | `reference_patterns[].confidence` | 色点 |

**右栏 — 反例与风险热点：**

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 反例 | `anti_examples[]` | 红色边框卡片，含 reason 和 refs |
| 风险热点 | `risk_hotspots[]` | 橙色边框卡片，含 summary 和 refs |

### 区域 D — 免疫防线

两列管道视图，展示免疫资产从候选到正式的流转。

```
候选区                              正式区
┌──────────────────┐               ┌──────────────────┐
│ 候选 1: ...      │  ──promote──▶ │ 防护 1: ...      │
│ 候选 2: ...      │               │ 防护 2: ...      │
│ 候选 3: ...      │               │ 防护 3: ...      │
└──────────────────┘               └──────────────────┘
```

**候选区卡片：**

| 信息项 | 数据源 |
|---|---|
| 进入原因 | `immune-candidates.yaml` 条目 |
| 观察状态 | 观察中 / 待提升 / 待拒绝 |

**正式区卡片：**

| 信息项 | 数据源 |
|---|---|
| 防护类型 | 文档 / 提示词规则 / 测试 / Lint 静态检查 |
| 作用范围 | 模块 / 仓库 / 领域 / 技术栈 / 全局 |
| 置信度 | 低 / 中 / 高 |
| 根因摘要 | 事故教训简述 |
| 最后检视时间 | `last_checked_at`，相对时间展示，超 90 天显示衰减色 |
| 最后触发时间 | `last_triggered_at`，相对时间展示 |
| 治理状态 | `governance_tags`，`needs-review` 时显示黄色徽标 |

### 区域 E — 检视规则累积

按三层展示规则数量和内容。

| 层级 | 文件 | 展示 |
|---|---|---|
| 仓库级 | `review-rules/base.md` | 规则数量 + 可展开列表 |
| 需求级 | `review-rules/<topic>.md` | 按 topic 分组，规则数量 |
| 防御级 | `review-rules/defensive.md` | 规则数量 + 可展开列表 |

底部统计栏：规则总数、最近新增的规则、规则来源分布。

### 区域 F — 领域检查清单

| 信息项 | 数据源 | 展示形式 |
|---|---|---|
| 内置 lens | `skills/analysis-spec/references/` 下的 frontend/backend/integration/risk-memory | 四个固定图标 |
| 项目级 lens | `.project-context/lenses/*.md` | 自定义图标标签 |
| 每个 lens 的检查项 | lens 文件内容 | 可展开列表 |

---

## 交互原则

### 信息密度策略

| 层级 | 策略 | 信息量 |
|---|---|---|
| 列表/总览 | 只展示状态和关键数值 | 一行一个对象 |
| 卡片/条目 | 展示核心属性和状态指示 | 一张卡片一个对象 |
| 详情/下钻 | 展示完整内容和关联 | 全部字段 |

### 色彩语义

全局统一的色彩语义，不随视图变化：

| 颜色 | 含义 | 使用场景 |
|---|---|---|
| 绿色 | 健康/完成/高置信 | confidence: high, status: pass, as_specified |
| 黄色 | 需关注/中等/推测 | confidence: medium, deferred, 🟡, legacy |
| 红色 | 异常/阻塞/低置信 | confidence: low, failed, blocking, abandoned, hotspot |
| 灰色 | 缺失/不适用/未开始 | 空数组, n/a, 未到达的阶段 |
| 蓝色 | 进行中/当前 | 当前活跃阶段 |

### 关联跳转

产物之间的引用关系应支持点击跳转：

| 起点 | 终点 | 触发 |
|---|---|---|
| 模块卡片 | 该模块关联的特性列表 | 点击模块卡片上的特性数量徽标 |
| 特性条目 | 引用该特性的需求列表 | 点击特性详情中的"关联需求" |
| 需求条目 | 需求详情 → 追溯链视图 | 点击需求行 |
| 追溯链中的 TB | 展开 TB 的完整描述 | 点击 TB 单元格 |
| 追溯链中的 AC | 展开 Given/When/Then | 点击 AC 单元格 |
| 追溯链中的 EV | 展开证据描述 | 点击 EV 单元格 |
| 免疫卡片 | 展开完整免疫决策记录 | 点击卡片 |
| 反例/风险热点 | 显示代码路径（可复制） | 点击 refs |

### 空状态处理

当某类产物不存在时的处理方式：

| 缺失产物 | 处理 |
|---|---|
| `.project-context/` 完全不存在 | 显示引导提示："请先运行 initialize 为仓库建立上下文" |
| `features/index.yaml` 为空 | 特性视图显示："尚未建立特性索引" |
| `docs/specs/` 为空 | 需求视图显示："暂无活跃需求" |
| `immune-*.yaml` 不存在 | 免疫区域显示："暂无免疫资产" |
| 某个 topic 缺少部分工件 | 进度条对应阶段显示灰色，追溯链对应列显示灰色 |

---

## 数据聚合指标

以下是可以在全局顶部或概览页面展示的聚合数值：

| 指标 | 计算方式 | 展示位置 |
|---|---|---|
| 模块总数 | `profile.yaml → modules[]` 长度 | 全景顶部 |
| 特性总数 | `features/index.yaml → features[]` 长度 | 特性顶部 |
| 活跃特性占比 | status=active 的比例 | 特性顶部 |
| 活跃需求数 | `docs/specs/` 下未完成 reflect.md 的 topic 数 | 需求顶部 |
| 已交付需求数 | `docs/specs/` 下已有 reflect.md 的 topic 数 | 需求顶部 |
| 整体交付兑现率 | 所有 spec-check 中 as_specified 的汇总比例 | 需求顶部 |
| 高置信模块占比 | confidence=high 的模块比例 | 健康顶部 |
| 免疫资产总数 | immune-registry 条目数 | 健康 → 免疫 |
| 待审候选数 | immune-candidates 条目数 | 健康 → 免疫 |
| 检视规则总数 | review-rules 下所有规则条目数 | 健康 → 规则 |
| 上下文年龄 | 当前时间 - profile.yaml.generated_at | 健康 → 新鲜度 |
