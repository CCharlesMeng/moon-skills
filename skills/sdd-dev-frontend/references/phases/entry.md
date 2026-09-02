# Phase -1 / 0：接入与执行起点

只在进入 Phase -1 或 Phase 0 时读取。本阶段完成仓库 readiness、Story 路径、上游事实与初始验证组合；不预跑未选验证能力。

## Phase -1 — 仓库接入

1. 解析 `<repo-root>`，再按 TaskPacket 的 `search_paths`、前端设计与仓内 app 边界确定唯一 `<frontend-root>`；按 `sdd-init-frontend/references/baseline-contract.md` 得到 `<repo-baseline-dir>=<frontend-root>/frontend-baselines/`。单 app 仓静默取仓根；monorepo 多候选按 P7 一次确认。当前 Story 横跨多个独立 app 时回流 `sdd-task` 拆分，不把 monorepo 根当作混合 baseline。
2. 先查命名 schema：目录里出现旧名 `routing.md` / `styling.md` / `testing.md` 任一项时，先路由 `sdd-init-frontend` 做原位迁移；这不触发全量重扫。
3. canonical 缺失但发现旧外层 baseline 目录时，路由 `sdd-init-frontend` 做位置迁移；本 skill 不长期 fallback 读取旧目录。
4. 走**极轻的门**，只查两件事：

| 判据 | 不满足时 |
| --- | --- |
| `<repo-baseline-dir>/index.md` 在不在 | 不在 → 完整执行 `sdd-init-frontend` |
| `structure.md` 的栈签名读不读得出一个具名的框架**和**一个具名的形态 | 读不出 → 完整执行 `sdd-init-frontend` |

**命名归一后不按份数查。** 空文件按规定整份删，`组件库` 形态下 `routes.md` 与 `api.md` 本就不该存在，按份数查会把正确产物判成不合格。`index.md` 恒存在（它只做路由）、`structure.md` 恒非空（栈签名恒存在），这两条才是可靠判据。

**形态要一起读出来**，因为它决定本 Story 后续判据是否适用：`微前端子应用` 里查不到统一请求出口不等于没有出口，`组件库` 里没有路由是正常的。

**这道门刻意不精确。** 「本 Story 需要的那几条查得到吗」在 Phase -1 还没有信息可判——`tasks.md` 要到 Phase 0 才读。所以这里只拦住「baseline 根本不存在」这一种情况；具体某条结论不成立由消费点自证并就地修，不在这里预判。

**不查 readiness、不查指纹、不查 stale。** 这三样已随 app baseline 改版整体取消：内容指纹只能告诉你文件变了，永远不能告诉你结论变了，为这点信噪比要养账本、stale 状态、readiness 回退和一条「本 Story 自身改动放行」的例外。现在的跟进方式是消费点自证 + 就地修，Phase C/D 重查时**没有任何 baseline 失效需要放行或路由**。

退出：baseline 入口存在，栈与形态均可判。

## Phase 0 — 执行起点

### 1. 定位需求

解析 `<story-dir>`、`<requirement-dir>`、`<prototype-dir>`、`<design-spec-dir>`。唯一命中时静默继续；缺失或多候选按 P7 一次问完。`<design-spec-dir>` 由 Requirement 目录推导，不单独询问。

### 2. 缺 `tasks.md` 的分支

仅当会话已明确 Story 范围、AC、基线来源和文件范围时，读取 [templates/story-artifacts.md](../templates/story-artifacts.md) 第四节，起草 `tasks.md`、缺失的 `alpha-tests.md` 与 `story-delta-frontend-design.md`，展示草稿并确认后落盘。缺任一核心信息时回 `sdd-task` 或按 P7 问缺口；不带分歧开工。

### 3. 核实上游事实

按 [共享执行契约](../execution-contract.md) 读取 TaskPacket。核实 `baseline_source`、目录、路由、状态、还原 Task 与风险 token：

- 字段是候选索引；缺席不表示低风险。
- `prototype` 必须实测目录存在且包含相关 HTML，否则重新判档并记录冲突。
- `reference_route` 仍是待确认候选。
- 风险 token 与 Task 正文、仓库事实冲突时以可验证事实为准。
- 读 `verification_schema`：缺席或非 `v2` 按 v1 原语义读，不把旧 L3/L4 记录映射成三层范围、也不推断为人工验收。
- `v2` 时校验每条声明的 `verification_scope` 与 `verification_method` 齐全，人工验收声明另校验 `manual_basis`、`required_environment`、`required_evidence`。环境或所需证据缺失的保持 `UNVERIFIED` 并回流计划补齐；`manual_checked_by` 未填不阻断进入实现，也不写人名占位符。
- 两条测试通道字段缺席按 `unknown` 处理；某条 `test_case` 声明的范围没有对应通道时按 [validation-policy 第七节](../validation-policy.md#七验证方法的判定规则)登记降级，不因此停下。

### 4. 建立执行上下文

记录 `<base-ref>`、Story 文件范围、Requirement 决策和已知运行限制。只读取当前 Story 实际需要的 `PATTERN-*` / `REQ-DEC-*` 正文，不复制 app baseline，也不记录任何 baseline 指纹。

按 `index.md` 的场景索引取 ID，再回读对应文件；读到的清单条目指路失效时**就地修那一条**并随本 Story 提交，不阻塞、不路由；规范条目不成立时攒进 `acceptance.md`，Story 收口时一次确认。规范节只有 `sdd-init-frontend` 能改。

### 5. 判档并编译初始验证组合

档位与组合都由脚本算，命令见 [validation-policy.md 第二节](../validation-policy.md#二编译)：

```bash
python3 "<skill-dir>/scripts/compile_portfolio.py" --tasks "<story-dir>/tasks.md" --phase initial \
  --plan-files <计划文件数> [--trigger <判断型触发器>]... --out "<story-dir>/portfolio-initial.json" --markdown
```

进脚本前只做一件判断：按 [validation-policy.md 第三节](../validation-policy.md#三风险触发器)看本 Story 是否命中 `async-state` / `new-pattern` / `spec-gap` / `unknown-deps` / `performance`，命中的以 `--trigger` 传入。其余触发器、档位、模块、角色与维度不手判。`--markdown` 的输出直接贴进 `dev-baseline.md`。每条声明初始为 `UNVERIFIED`。

只有组合含命令模块时才实跑已选的质量命令一次，取得**起点失败集合**（REG 判据的可比起点）；只有组合含浏览器模块时才解析、实测 `<browser-driver>`。未选能力不探测、不生成空表。续跑时 `dev-baseline.md` 已有起点失败集合就直接沿用，不重跑。

### 6. 写 `dev-baseline.md`

按 [templates/story-artifacts.md](../templates/story-artifacts.md) 第一节写执行起点与初始组合；`lite` 档只写该节标明的必需部分。

退出：路径唯一、上游事实已核、档位已判、初始组合与执行起点已落盘。
