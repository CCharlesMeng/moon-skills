# sdd-init-frontend 产物分类问题 — Handoff

> **状态：已结案，保留作推导来源。** 第 8 节的未决问题由 [产物分类方案.md](./产物分类方案.md) 定稿解决——主分类维度取「消费者问句」，产出九份文件。该方案的 C1–C7 约束与杂物袋检测器直接引用本文第 5、6 节，所以本文不删。
>
> **本文第 1、3、9 节描述的是改造前的世界，不要当现状读。** 已经不成立的部分：`repo-baseline.md` 与 `onboarding-report.md` 两份产物、`REPO-1/2/3` 三段式、1556 行的 `manage_repo_baseline.py` 及其 9 条单测、内容指纹与 readiness，以及外层 `<project-sdd-dir>/frontend-baselines/<repo-id>/` 路径——全部已删除或迁移。第 9 节的「相关文件位置」表因此有多行指向不存在的路径；现行位置见方案文档第 8 节的迁移记录。
>
> 仍然有效的部分：第 2 节的九条消费者查询（评判任何新分类方案的标准）、第 4 节的 D1–D10 决策、第 5 节的四次失败、第 6 节的七条约束与杂物袋检测器、第 7 节的场景索引结论。

给下一个会话：本文自包含，不要求读过之前的讨论。目标是**为前端仓库 baseline 找到一套分类方案**。已经试过四套，全部失败；失败原因比方案本身有价值，都记在下面。

---

## 1. 背景

`sdd-init-frontend` 是一个 Cursor Agent Skill，职责是：扫描一个前端代码仓，产出**可跨需求复用的仓库级知识**，供下游三个 skill 消费。

它当前产出两份文件在 `<project-sdd-dir>/frontend-baselines/<repo-id>/`：

- `repo-baseline.md` — 分三个 Section：`REPO-1` 环境与运行、`REPO-2` 工程质量、`REPO-3` 工程范式。每个 Section 分「自动发现（脚本维护）」和「人工维护（agent 维护）」两段，外加一份全仓文件 SHA-256「新鲜度账本」。
- `onboarding-report.md` — 当前机器的实证结果（跑了哪些命令、退出码、页面能不能开）。

配套有一个 1556 行的 Python 脚本 `scripts/manage_repo_baseline.py`，提供 `scan / status / validate / finalize / show` 五个子命令。

**要解决的问题是 `repo-baseline.md` 内部怎么分类。** 其余决策（见第 4 节）已定，不要推翻。

---

## 2. 消费者与它们的实际查询

这是评判任何分类方案的唯一标准。四个消费者发出的真实查询：

| # | 消费者 | 查询 | 查询模式 |
| --- | --- | --- | --- |
| 1 | `sdd-task-frontend` 计划期 | 「我要做一个带筛选的列表页，仓里有没有现成的能复用？」 | **按场景找**（跨主题） |
| 2 | `sdd-task-frontend` 计划期 | 「异步取数的加载/空/错误三态，这个仓怎么处理？」 | 按主题找 |
| 3 | `sdd-task-frontend` | 「测试框架是什么？」 | 查单点事实 |
| 4 | `sdd-task-frontend` | 「测试元素定位用什么属性、什么约定？」 | 按主题找 |
| 5 | `sdd-dev-frontend` Phase 0 | 「怎么装、怎么起、跑哪些质量命令？」 | 查单点事实 |
| 6 | `sdd-dev-frontend` Phase A/B | 「`PATTERN-REQUEST-1` 的正文」 | **按 ID 精确回读** |
| 7 | `sdd-review-frontend` convention-lens | 「这段代码绕过统一请求实例了吗？统一实例是哪个？」 | 查基准 |
| 8 | `sdd-review-frontend` | 「这个仓是 React 还是 Vue？」（决定用哪节栈信号） | 查单点事实 |
| 9 | `sdd-review-frontend` | 「样式硬编码了吗？仓内 scale 有哪些档位？」 | 查基准 |

**三种查询模式，只有一种对分类敏感：**

- 按 ID 精确回读（#6）→ ID 全局唯一即可，文件怎么分都行
- 查单点事实（#3 #5 #8）→ 有索引即可，文件怎么分都行
- **按场景找（#1）→ 唯一对分类敏感的**。而它天然跨主题：做一个列表页要同时用到 Table 组件、分页 hook、请求封装、三态处理、定位约定。

---

## 3. 当前产物的实测缺陷（已验证，带证据）

拿仓内 fixture 前端仓（React + Vite，8 个源文件）实跑扫描器得到的真实产出，142 行。

### 3.1 REPO-1 / REPO-2 信息增量约等于零

全部内容来自 `package.json` + `.nvmrc` + `.env.example` + `vite.config.ts` 存在性。agent 读一次 `package.json` 就有。而且转述有损：原文 `"dev": "vite --port 5178"` 变成 `pnpm run dev`，端口丢了。

### 3.2 REPO-3（唯一值钱的部分）识别率 1/5

「范式证据入口」只识别出 `src/lib/request.ts` 一条。漏掉的：

| 文件 | 是什么 | 为什么漏 |
| --- | --- | --- |
| `src/components/StatCard/` | 通用组件 | 判据词表里根本没有「组件」这一类 |
| `usePortfolioSummary.ts` | hook 范式 | 判据是路径含 `hook`，但 React hook 叫 `useXxx` |
| `src/lib/format.ts` | 工具函数 | 判据是路径含 `util` |
| `src/styles/tokens.css` | 设计 token | 判据是分词匹配 `token`，被复数的 `s` 挡掉 |

根因：**扫的是文件名里有没有出现指定英文单词，也就是命名巧合，不是代码结构。**

### 3.3 失效机制过度触发

决定「哪些文件进新鲜度账本」用**子串**匹配，决定「哪些文件进候选表」用**分词**匹配，两套判据不一致。实测：

```
src/features/portfolio/PortfolioPanel.tsx   进 REPO-3 账本  命中词=['feature']
src/features/checkout/CartRow.tsx           进 REPO-3 账本  命中词=['feature']
src/lib/format.ts                           进 REPO-3 账本  命中词=['form']
src/styles/tokens.css                       进 REPO-3 账本  命中词=['style','token']
src/components/StatCard/StatCard.tsx        不进账本
```

**任何 React 项目的整棵 `src/features/**` 都会被吸进账本**（`features` 含 `feature`）。改一行 `format.ts` → 指纹变 → readiness 掉回 `DRAFT` → 按门禁要求人重新复核全部手写范式。而 baseline 里没有任何关于 `format.ts` 的结论。

这个 bug 在下游留下四处化石：`sdd-dev-frontend` Phase -1 的「本 Story 自身改动放行」例外、`evals.json` id 12/13、三份 ground-truth 里的「本现场 `status` 会报 REPO-3 失效，不得据此终止」。修好失效机制后这四处整体作废。

### 3.4 其他

- `build_discovery` 构造了 `rendering_contract`（8 个字段全填 `unknown`），渲染函数根本不用它——死代码。但 SKILL Phase 1 要求 agent 填这些字段。
- `stack-signals.md` 写「栈由仓库 baseline 的框架字段确定」，但 baseline 里没有名叫「框架」的字段，只有一张把 `@types/react`、`@vitejs/plugin-react`、`react-dom` 并列为 `framework` 类别的候选表。**这句话是悬空的。**
- 产物里**一个组件都没有**。而 `sdd-task-frontend` 已经把「找可复用组件」的事实源指向了 REPO-3。

---

## 4. 已定的决策（不要推翻）

这些在本次讨论中已经拍板，构成 Q1 解空间的边界：

| # | 决策 | 理由 |
| --- | --- | --- |
| D1 | **采集手段用规则集 + agent，不写扫描脚本** | 唯一非脚本不可的是「产出稳定的机器可消费哈希」，而 D3 取消指纹后这个需求消失。agent 可用 grep/glob。代价是可重放性下降，但最值钱的范式正文本来就是 agent 写的，这个性质已被接受 |
| D2 | **组件清单分层标注，只有通用层进详表**；业务组件只进按路由的索引 | 判定不靠目录名，靠「被 ≥2 个特性引用」 |
| D3 | **完全取消指纹、readiness、stale 状态**。跟进改成「消费点自证 + 就地修」 | 指纹只能告诉你文件变了，永远不能告诉你结论变了。为这个信噪比要养账本、stale、readiness 回退、Phase -1 例外、两道评测题 |
| D4 | **浏览器实证移出 `sdd-init-frontend`**，交给 `sdd-dev-frontend` Phase 0 按需做 | 现在是「不管这次 Story 要不要截图，接入时先把浏览器全套验一遍」，是 init 显得重的最大单一来源 |
| D5 | 首次生成**只扫通用层候选目录**（`components/`、`shared/`、`common/`、`ui/`）**加上本次业务已知涉及的模块**；业务组件靠增量长 | 压掉大仓首次全量成本，又不让第一个 Story 面对空清单 |
| D6 | `sdd-dev-frontend` Phase -1 保留一道**极轻的门**：文件在不在、框架读不读得出。读不出就路由到 init | 完全删门会让每个 Story 现场重建工程事实；精确判据（「本 Story 需要的几条查得到吗」）在 Phase -1 还没有信息 |
| D7 | **每份文件强制至少一节，不存在的节整节删掉**，不用「无」「未见」填版面 | 与现有门禁一致 |
| D8 | **同一条事实只能出现在一节**。规范引用清单条目的 ID，不重述路径 | 防膨胀 |
| D9 | 写权限分级：init 独占**规范**与全量重建；task / dev 可**追加和修正清单单条**；review **只读** | 让判断者能改判据就没有判断了 |
| D10 | 确认走**攒批 + 异步，不阻塞任何 Task**。清单改动就地做并进提交；规范改动攒进 `acceptance.md` handoff，Story 收口时一次确认 | 分界线是「看一眼代码就能验」还是「要看多个样本才能判」 |

**待用户澄清（暂缓）**：「代码里已明确表达的，baseline 只指路不复制」要不要立为硬门禁。候选理由是 baseline 的价值只在表达代码里没有显式写出来的东西（「所有请求必须走 `request.ts`」靠归纳），而代码里写得清楚的（`request.ts` 导出了哪几个方法）抄进来就是第二事实源，必然漂移。

---

## 5. 四次失败的尝试（核心资产）

### 尝试 1：按生命周期切 —— 2 份

`repo-assets.md`（跨 Requirement 长期）+ `repo-runtime.md`（当天有效、机器相关）。

**失败原因**：除了「这台机器这一次的实证结果」之外，**几乎所有东西都是跨需求长期复用的**——怎么装、怎么起、跑哪些质量命令、端口是多少，这些在需求之间同样复用。生命周期没有区分度，只能切出「实证」和「其余一切」，而「其余一切」正是装不下的那坨。

附带损失：这个方案把 REPO-1/2（稳定契约）和 `onboarding-report`（一次性实证）合并，毁掉了现有设计里唯一做对的那条界线。

### 尝试 2：按查询单元切 —— 5 份

`engineering-facts` / `runtime-contract` / `component-inventory` / `shared-modules` / `patterns`。

**失败原因（两个）**：

1. `engineering-facts.md` 是**杂物袋**——把框架、构建工具、目录命名约定、测试框架、i18n、环境变量六种不同性质的东西塞一起。
2. `shared-modules.md` 是**跨维度袋**——横跨应用层的 hook 和基础设施层的请求封装，必然和别的文件重合。
3. `patterns.md` 太大——因为它同时装了「统一请求实例是 `src/lib/request.ts`」（事实）和「所有请求必须走统一实例」（规则），两种性质混在同一条 `PATTERN-*` 里，没有自然分割点。

### 尝试 3：按分层架构 + 横切关注点切 —— 6 份

`presentation` / `application` / `infrastructure` / `tooling` / `testing` / `runtime`，每份内部分「清单 / 规范」两节。领域层设为条件文件。

**失败原因**：**对差架构不鲁棒。** 一个 `pages/` 平铺、状态全在组件里、各处裸 `axios`、样式全硬编码的仓，按分层切会得到三份近乎空的文件。更糟的是它会**诱导 agent 把仓库描述成它应该的样子，而不是它实际的样子**——这跟「没有外部基线时不得发明视觉规格」是同一类错误，只是发明对象从 px 变成了架构。

根因：**「层次」这个维度对架构质量敏感。** 问「表现层有什么」，差架构答案是空；问「这个仓里发请求怎么做」，差架构答案是「没有统一做法，各处自己 axios」——**这不是空，这是极有价值的结论**，`review` 正是靠它决定不能拿「绕过统一实例」判违规。

### 尝试 4：按关注点切 + 独立资产清单 + 场景索引 —— 9 份

`inventory` / `structure` / `data-access` / `state-and-forms` / `styling` / `testing` / `runtime` / `index` / `onboarding-report`。

**失败原因**：`inventory.md` **又是杂物袋**——用一个「类型」列硬并了组件、hook、composable、工具、service、指令、管道、守卫、请求实例、token 集共 9 种东西。杂物袋只是从 `engineering-facts` 换了个位置。

关注点这一维本身是成立的（对差架构鲁棒），失败的是「把所有资产并成一张表」这个决定。

---

## 6. 从失败中提炼的约束

任何候选方案必须同时满足：

| # | 约束 | 来自 |
| --- | --- | --- |
| C1 | **对差架构鲁棒**：每份文件在一个架构很差的仓里也要有非空且有用的内容 | 尝试 3 |
| C2 | **无杂物袋**：一份文件里的条目必须共享同一个「为什么它们在一起」的理由，且这个理由要能判定新条目该不该进来 | 尝试 2、4 |
| C3 | **无跨维度袋**：不能出现横跨主分类维度的 `shared` / `common` 类文件 | 尝试 2 |
| C4 | **生命周期不能做切分维度** | 尝试 1 |
| C5 | **场景不能做切分维度**（无穷 + 重叠 → 同一资产重复定义），但**可以做索引** | 见第 7 节 |
| C6 | **清单与规范必须分离**：事实和规则混在同一条目里就没有自然分割点，必然膨胀 | 尝试 2 |
| C7 | **按 ID 精确回读必须成立**：`PATTERN-*` ID 全局唯一，跨文件可 grep 到 | 消费者查询 #6 |

### 可操作的杂物袋检测器

> **如果一份文件需要靠「类型」列来区分内部条目的性质，说明它应该被那个类型列切开。**

这条同时判死了尝试 2 的 `engineering-facts` 和尝试 4 的 `inventory`。用它检查任何候选方案。

---

## 7. 一个已确认成立的部件：场景索引

消费者查询 #1（「我要做列表页，有什么能用」）是唯一对分类敏感的查询，而它天然跨主题。结论：

- **场景不能用来切文件**：场景无穷且重叠，同一个 Table 组件会出现在列表页、详情页、弹窗三个场景里，切文件就是重复定义。
- **场景应该用来做索引**：一份 `index.md`，按场景组织入口（「要做列表页 → 读这几条」），指向各文件里的具体条目。

原则是**分类用稳定维度，检索用索引**。这一条与主分类方案正交，无论第 8 节怎么定都保留。

---

## 8. 未决问题

**主分类维度是什么？**

已知：
- 层次不行（C1）
- 生命周期不行（C4）
- 场景不行（C5）
- 查询单元不行（会切出杂物袋和跨维度袋，尝试 2）
- 关注点这一维**通过了 C1**（差架构下每个关注点都有非空答案），但尝试 4 在「资产怎么组织」上翻了车

所以更精确的未决问题是两个：

1. **关注点是不是最终答案？** 如果是，关注点的清单该是哪些、边界怎么定（要能判定新条目归属）？如果不是，什么维度能同时满足 C1–C7？
2. **可复用资产怎么组织，才不变成杂物袋？** 候选思路（都未验证）：
   - 资产不独立成文件，按它服务的关注点分散到各文件的清单节（但要防止跨关注点的资产重复出现，且会牺牲「一次扫完找复用」的能力）
   - 按资产的**消费方式**切（「渲染时用的」vs「取数时用的」vs「校验时用的」）
   - 按资产的**稳定性/所有权**切（框架提供的 / 团队维护的公共层 / 业务沉淀的）
   - 干脆承认组件和非组件是两类东西，只切这一刀

评判任何新方案时，用第 2 节的九条消费者查询逐条走一遍，再用第 6 节的七条约束和杂物袋检测器过一遍。

---

## 9. 相关文件位置

| 用途 | 路径 |
| --- | --- |
| skill 本体 | `skills/sdd-init-frontend/SKILL.md` |
| 现行产物契约 | `skills/sdd-init-frontend/references/baseline-contract.md` |
| 扫描器 | `skills/sdd-init-frontend/scripts/manage_repo_baseline.py` |
| 单测（改脚本会红） | `skills/sdd-init-frontend/evals/test_manage_repo_baseline.py` |
| 下游共享契约 | `skills/sdd-dev-frontend/references/execution-contract.md`、`docs/skills/frontend-sdd/接缝契约.md` |
| 消费点：计划 | `skills/sdd-task-frontend/SKILL.md`「输入」表、`templates/tasks-frontend.md` |
| 消费点：执行 | `skills/sdd-dev-frontend/references/phase-entry.md`、`agents/recon-codebase.md` |
| 消费点：检视 | `skills/sdd-review-frontend/references/stack-signals.md` |
| fixture 前端仓（可实跑验证） | `skills/sdd-dev-frontend/evals/fixtures/repo/` |
| fixture 构建器（硬依赖现有标题格式） | `skills/sdd-dev-frontend/evals/fixtures/setup.py` |

改动的机械代价：硬依赖脚本退出码/输出格式的有 8 处，硬依赖 REPO-1/2/3 三段式切分的有 9 处。`sdd-review-frontend` 几乎不受影响——它不读 `repo-baseline.md`、不调脚本，只要求两件事仍成立：能按 ID 回读 `PATTERN-*` 正文，能判出 React/Vue/Svelte。
