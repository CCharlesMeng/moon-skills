# convention-01 · ground truth

被测模块：`agents/review-convention.md`。评分口径见 [模块与评测.md 第三节](../../../../../../docs/skills/frontend-sdd/模块与评测.md)。

改动范围：3 个新增文件 + 1 个修改文件（`src/App.tsx`），全部为工作区未提交改动。`setup.py` 打印的取值表里给了 `<base-ref>`，因此对应提示词「diff 取法」的**第 1 条**（取该引用到当前工作树的全部改动）。

行号以 `after/` 树内的文件为准，setup 之后即为工作区内的实际行号。

---

## 一、必报项（命中率分母 = 16）

每条要被判为命中，必须同时给出**定位**（文件 + 行号范围，允许 ±1 行偏差）与**基准**（对应的 `PATTERN-*`，升阻断级的还要引用对应基线行）。只报了现象没给基准的不计命中。

| # | 维度 | 应判级别 | 定位 | 应引用的基准 | 判定要点 |
| --- | --- | --- | --- | --- | --- |
| GT-1 | C1 | 建议级 | `src/features/risk-brief/riskbrief_panel.tsx`（文件名本身） | `PATTERN-COMPONENT-1` | 业务面板文件名须 PascalCase 且与导出组件名逐字一致，应为 `RiskBriefPanel.tsx`；样式文件同名连带 |
| GT-2 | C1 | 建议级 | `riskbrief_panel.tsx` L2–L3 | `PATTERN-COMPONENT-1` | 跨目录导入未走 `@/` 别名，用了 `../../` |
| GT-3 | C2 | 建议级 | `riskbrief_panel.tsx` L18 | `PATTERN-COMPONENT-1` | 用了 `React.FC`，不变量明文禁止 |
| GT-4 | C2 | 建议级 | `riskbrief_panel.tsx` L46 | `PATTERN-COMPONENT-1` | 默认导出，不变量明文禁止；连带 `App.tsx` L2 的默认导入 |
| GT-5 | C2 | 建议级 | `riskbrief_panel.tsx` L7–L9 | `PATTERN-COMPONENT-1` | props 应为导出的 `interface RiskBriefPanelProps`，实际是未导出的 `type Props` |
| GT-6 | C3 | **阻断级** | `riskbrief_panel.module.css` L5 | `PATTERN-TOKEN-1` | `padding: 16px` → `--space-4` |
| GT-7 | C3 | **阻断级** | `riskbrief_panel.module.css` L25 | `PATTERN-TOKEN-1` | `font-size: 13px` → `--font-size-sm` |
| GT-8 | C3 | **阻断级** | `riskbrief_panel.module.css` L36 | `PATTERN-TOKEN-1` | `color: #dc2626` → `--color-danger` |
| GT-9 | C3 | 建议级 | `riskbrief_panel.module.css` L9 | `PATTERN-TOKEN-1` | `box-shadow: 0 2px 8px rgba(15,23,42,.08)`：`tokens.css` 无阴影类 token，属基准缺失，**不得判阻断级**，且应在 Open Question 里问是否补 token |
| GT-10 | C4 | **阻断级** | `useRiskBrief.ts` L23 | `PATTERN-REQUEST-1` + `F4-1` | 裸 `fetch` 绕过唯一请求出口，因此缺 `Authorization`/`X-Tenant-Id` 与 `ERROR_MESSAGES` 映射，`F4-1` 的请求头与错误码映射两项均不成立 |
| GT-11 | C4 | 建议级 | `useRiskBrief.ts` L22–L33 | `PATTERN-ASYNC-1` | 未建 `AbortController`，卸载不取消；无基线行覆盖取消，**不得升阻断级** |
| GT-12 | C4 | **阻断级** | `useRiskBrief.ts` L30–L32 | `F3-1` | `catch` 把错误吞掉并把 `error` 置 `null`，错误态永远不渲染，已冻结基线 `F3-1` 不成立 |
| GT-13 | C5 | 建议级 | `riskbrief_panel.tsx` L11–L16 | `PATTERN-FORMAT-1` | 自实现 `toPercent`，与 `formatPercent` 语义等价（同为一位小数、非有限数返回 `--`），可直接替换。两者输出逐字相同，没有任何基线行因此不成立，所以取 C5 默认级；**判成阻断级即级别错误**，对比 GT-15 |
| GT-14 | C6 | **阻断级** | `useRiskBrief.ts` L26 | `PATTERN-TYPING-1` | `@ts-ignore` 且未写理由；不变量明文禁止 `@ts-ignore` |
| GT-15 | C5 | **阻断级** | `riskbrief_panel.tsx` L37 | `PATTERN-FORMAT-1` + `R5-1` | `String(data.highRiskCount)` 对非有限数返回 `"NaN"` / `"null"`，同行另两张卡都返回 `--`，已冻结 `R5-1` 不成立。`format.ts` 无计数格式化函数，所以**不能**像 GT-13 那样直接替换，修法需人定。写法系从 `PortfolioPanel.tsx` L27 复制进新文件，属「本 Story 的改动扩大了历史违规」，报的是新增那份 |
| GT-16 | C1 | 建议级 | `src/App.tsx` L2 | `PATTERN-COMPONENT-1` | 跨目录导入未走 `@/` 别名，且同文件 L1 就是 `@/` 写法。与 GT-4 的默认导入是同一行的两个不同问题，各计一条；合并成一条报出、两个问题都点明的，两条都算命中 |

级别分布：阻断级 **7 条**（GT-6、GT-7、GT-8、GT-10、GT-12、GT-14、GT-15），建议级 **9 条**（其余）。

**GT-15 与 GT-13 的级别差异是这份用例最核心的判别点**：两条都落在 C5（默认建议级），差别只在有没有让某条已冻结基线不成立。`review-dimensions.md` 规则 3 明写「不管它落在哪个维度、默认级别是什么」，所以 GT-15 必须升阻断级、GT-13 必须不升。把两条判成同一级别的，说明定级规则没被理解。

## 二、不得报项（误报分母 = 6）

判为违规（给了维度编号与级别）即计一次误报。仅在 Open Question 或范围说明里把它作为上下文提及、并明确说明「不在本检视范围」的，不计误报——那正是提示词要求的行为。

| # | 位置 | 为什么不得报 |
| --- | --- | --- |
| NG-1 | `riskbrief_panel.module.css` L7 `border: 1px solid var(--color-border)` | `1px` 描边属提示词明文排除的字面量 |
| NG-2 | `riskbrief_panel.module.css` L20 `minmax(220px, 1fr)` | 栅格计算式，不适用 token |
| NG-3 | `src/features/portfolio/PortfolioPanel.module.css` L30 `color: #b91c1c` | 仓内历史违规，本 Story 未改动该文件，改动也未扩大它。注意与 GT-15 的区别：那条的坏写法被复制进了新文件，这条没有 |
| NG-4 | C7 判出任何违规 | 仓内无国际化机制，`PATTERN-*` 未收录国际化范式，本维度只能写「不适用」 |
| NG-5 | `App.tsx` L9 中文字面量 `"示例租户"` | 同 NG-4；仓内无文案集中管理机制 |
| NG-6 | `riskbrief_panel.tsx` L22 / L30 的中文占位文案 | 同 NG-4 |

## 三、可报可不报项（不计入任何分母）

| # | 位置 | 说明 |
| --- | --- | --- |
| OPT-1 | `useRiskBrief.ts` L39 `@ts-expect-error 后端 openapi 尚未声明 trend 字段…见工单 482` | 有理由且理由属 `PATTERN-TYPING-1` 认可的形式。**报成建议级正确；报成阻断级计一次级别错误；不报不扣分。** |
| OPT-2 | `riskbrief_panel.tsx` L1 `import React from 'react'` | 与 GT-3 同源，单独报出不计误报也不计命中 |
| OPT-3 | `riskbrief_panel.tsx` L18 用箭头函数常量而非具名函数声明 | `PATTERN-COMPONENT-1` 的另一条不变量，与 GT-3 同源（都由 `React.FC` 那一行引起），合并报或单独报都不影响计分 |
| OPT-4 | `useRiskBrief.ts` L24–L27 `response.json()` 带来的隐式 `any` | 与 GT-10 同源（走 `request<T>()` 后自动消解），报成建议级正确，报成阻断级计一次级别错误 |
| OPT-5 | `riskbrief_panel.module.css` L20 `repeat(auto-fill, …)` 与仓内 `repeat(3, …)` 的写法差异 | 无 `PATTERN-*` 覆盖栅格模板，按规则 4 记建议级或不记都可以，判成违规并升阻断级计一次级别错误。注意与 NG-2 的区别：NG-2 禁的是把 `220px` 当硬编码报 |
| OPT-6 | `<story-dir>/restore-contract.json` 不存在 | `dev-baseline.md` 表头引用了它，但本现场不生成还原契约（见 [fixture README 第三节](../../README.md)）。记进「已知缺口」是正确行为，不记也不扣分 |

## 四、必须出现的行为（格式合规，6 项）

逐项通过才算格式合规满分。

- [ ] **没有以「前置缺失」终止。** 本现场的 `status` 会报 `REPO-3` 失效——那是本 Story 新增源码文件造成的，不是仓库事实过期。据此终止即本项判否，且整轮记零分
- [ ] C1–C7 七个维度小节全部出现，无发现的写「无发现」并给出检索范围
- [ ] C7 写明「仓内无国际化机制，不适用」而不是建议引入
- [ ] C3 小节写出「已排除的字面量」，至少点名 1px 描边与栅格计算式两类
- [ ] 表头写明 diff 取法（第 1 条，因为取值表给了 `<base-ref>`）与改动文件数 4
- [ ] 「Open Question」与「已知缺口」两个标题都在，没有内容时写「无」

## 五、四项分计算

| 指标 | 计算 | 及格线 |
| --- | --- | --- |
| 命中率 | 命中的必报项 / 16 | ≥ 0.80 |
| 误报率 | 报出的不得报项 / 6 | ≤ 0.17（即至多 1 条） |
| 级别正确率 | 命中项中级别判对的 / 命中数 | ≥ 0.90 |
| 格式合规 | 第四节 6 项中通过的 / 6 | = 1.0 |

**级别正确率单独盯四条**：GT-9（无 token 不得判阻断）、GT-11（无基线覆盖不得升阻断）、GT-13（等价实现不得升阻断）、GT-15（基线不成立必须升阻断）。前三条守的是「不许乱升级」，GT-15 守的是「该升的必须升」——只盯一侧会把提示词调成一味保守或一味激进。这四条判错说明定级规则没被理解，比漏检更值得改。

历史分数记在 [基线分数.md](../../../../../../docs/skills/frontend-sdd/基线分数.md)。
