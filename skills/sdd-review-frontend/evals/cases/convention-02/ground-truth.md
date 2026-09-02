# convention-02 · ground truth

被测对象：[convention checklist](../../../frontend-code-checklists/convention.md)。派发走 `sdd-dev-frontend/agents/review-convention.md`，它只影响格式合规那一项。评分口径见 [模块与评测.md 第三节](../../../../../docs/skills/frontend-sdd/模块与评测.md)。

这条用例不是 `convention-01` 的重复检查——它专考三件 `convention-01` 没覆盖到的事：**穷尽**（同类违规分散在两个目录里，只找到一处就收敛会漏掉另一处）、**豁免的反向规则**（命中已冻结 `EX-n` 的偏差必须不报，不是报出来再降级）、**规则 4 的边界**（工具函数落在所有 `PATTERN-*` 的适用场景之外，不能靠"看起来像组件规范"就套用 `PATTERN-COMP-1`）。

改动范围：4 个新增文件 + 2 个修改文件（`src/App.tsx`、`src/components/StatCard/StatCard.module.css`），全部为工作区未提交改动。`setup.py` 打印的取值表里给了 `<base-ref>`，因此对应提示词「diff 取法」的**第 1 条**（取该引用到当前工作树的全部改动）。

行号以 `after/` 树内的文件为准，setup 之后即为工作区内的实际行号。

---

## 一、必报项（命中率分母 = 2）

每条要被判为命中，必须同时给出**定位**（文件 + 行号范围，允许 ±1 行偏差）与**基准**（对应的 `PATTERN-*`，升阻断级的还要引用对应基线行）。只报了现象没给基准的不计命中。

这份用例的必报项只有两条，都是同一类违规（硬编码间距）在两个不同目录的体现——**故意只放两条而不是十几条**，让命中率对"漏掉其中一条"极度敏感：漏一条命中率就跌到 0.5，直接不及格。

| # | 维度 | 应判级别 | 定位 | 应引用的基准 | 判定要点 |
| --- | --- | --- | --- | --- | --- |
| GT-1 | C3 | **建议级** | `OrderExportPanel.module.css` L15 | `PATTERN-STYLE-1` | `gap: 16px` → `--space-4`；未违反冻结 token 声明，也无可复现错误结果 |
| GT-2 | C3 | **建议级** | `StatCard.module.css` L4 | `PATTERN-STYLE-1` | `padding: 12px` → `--space-3`；与 GT-1 同类但落在不同文件，两条都要报；问题类型不自动升阻断 |

级别分布：阻断级 **0 条**，建议级 **2 条**。

## 二、不得报项（误报分母 = 4）

判为违规（给了维度编号与级别）即计一次误报。仅在 Open Question 或范围说明里把它作为上下文提及、并明确说明「不在本检视范围」的，不计误报。

| # | 位置 | 为什么不得报 |
| --- | --- | --- |
| NG-1 | `OrderExportPanel.tsx` L23 `String(data.failedCount)` | 命中已冻结豁免 `EX-1`：`R5-1` 要求字段缺失显示 `--`，`EX-1` 明确把「失败批次」卡排除在这条要求之外。规则 3 的反向规则「命中了 `EX-n` 的偏差不报」在这里成立——**不能报成阻断级，也不能报成建议级，任何级别都不报**。这是本用例的核心判别点：判成阻断级说明只学会了规则 3 的正向（基线不成立即阻断），没学会反向（豁免覆盖的不报） |
| NG-2 | `orderExportFormat.ts` L5 默认导出，判为违反 `PATTERN-COMP-1` | `PATTERN-COMP-1` 的适用场景是「新增组件与特性面板」，不含 `src/lib/` 工具函数；引用一个适用场景不覆盖当前文件的 `PATTERN-*` 作为违规基准，属于编造基准，比"无基准不判违规"更严重。允许的报法见下方 OPT-1 |
| NG-3 | `OrderExportPanel.module.css` L7 `border: 1px solid var(--color-border)` | `1px` 描边属提示词明文排除的字面量 |
| NG-4 | `useOrderExportBatches.ts` 或 `OrderExportPanel.tsx` 判出 C6 检查抑制类问题 | 两份文件都没有任何 `@ts-ignore` / `@ts-expect-error` / `eslint-disable` / `any`，不存在可报的抑制写法 |

## 三、可报可不报项（不计入任何分母）

| # | 位置 | 说明 |
| --- | --- | --- |
| OPT-1 | `orderExportFormat.ts` L5 默认导出（不引用 `PATTERN-COMP-1`，只客观描述并存现状） | 按规则 4：`src/lib/` 现有两份样例（`request.ts`、`format.ts`）都用具名导出，"现有代码已成规模"这条件勉强够格，可记建议级并引用这两份路径作证据，不升级；不记也不扣分。**唯一的红线是不能把 `PATTERN-COMP-1` 点名为基准**（见 NG-2） |
| OPT-2 | `OrderExportPanel.tsx` L20–L21 两行几乎相同的 `Number.isFinite(...) ? String(...) : '--'` | 无 `PATTERN-*` 覆盖是否要抽成小工具，且这属于复杂度/重复维度（Q1/Q2），不在 `review-convention` 的 C1–C7 范围内；作为范围外说明提及不计误报，但不应作为 C 维度违规升级 |
| OPT-3 | 在 Open Question 或已知缺口里提及「`failedCount` 那一行依赖 `EX-1`，若后端契约变化需重新确认」 | 主动点出这条依赖关系是加分行为，不是必须项；不提不扣分 |
| OPT-4 | `<evidence-dir>/restore-contract.json` 不存在 | `dev-baseline.md` 表头引用了它，但本现场不生成还原契约（见 [fixture README 第三节](../../../../sdd-dev-frontend/evals/fixtures/README.md)）。记进「已知缺口」是正确行为，不记也不扣分 |

## 四、必须出现的行为（格式合规，7 项）

逐项通过才算格式合规满分。

- [ ] **没有以「前置缺失」终止。** 九份 app baseline 与 `dev-baseline.md` 均存在且可读；本 Story 新增的源码文件不构成任何 baseline 失效
- [ ] 回传是 schema v1 裸 JSON，`role=review-convention`，coverage 恰好包含 C1–C7；无发现维度用 `result=clear` 并给出 scope
- [ ] **穷尽性：C3 小节同时点出 `OrderExportPanel.module.css` 与 `StatCard.module.css` 两处硬编码，不因为先找到一处就收敛**（对应 GT-1、GT-2）
- [ ] **豁免核对：结论里明确提到 `EX-1` 并说明「失败批次卡的 `String()` 因豁免不报」，而不是保持沉默**——沉默无法区分"检查过豁免表后判定不报"与"根本没检查 `failedCount` 那一行"，这条要求显式留痕
- [ ] **不把 `PATTERN-COMP-1` 引用为 `orderExportFormat.ts` 违规基准**（对应 NG-2）
- [ ] coverage scope 写明 diff 取法（第 1 条，因为取值表给了 `<base-ref>`）与改动文件数 6
- [ ] `open_questions` 与 `known_gaps` 字段都存在，没有内容时为空数组

## 五、四项分计算

| 指标 | 计算 | 及格线 |
| --- | --- | --- |
| 命中率 | 命中的必报项 / 2 | ≥ 0.80（样本只有 2 条，漏 1 条即跌到 0.5，不及格；这是刻意设计） |
| 误报率 | 报出的不得报项 / 4 | ≤ 0.17（样本小，1 条即超线） |
| 级别正确率 | 命中项中级别判对的 / 命中数 | ≥ 0.90 |
| 格式合规 | 第四节 7 项中通过的 / 7 | = 1.0 |

**这份用例最核心的判别点是 NG-1。** 命中 `EX-1` 的偏差如果被报成阻断级或建议级，说明规则 3 只学会了正向，没学会反向——这正是 `convention-01` 的 GT-15 没能测到的方向：那条用例只有"该升级"没有"该整条豁免"。第二判别点是 GT-1/GT-2 是否**同时**命中：只报一条说明检视没有跨目录穷尽同类违规，这个失败模式在 `convention-01`（改动集中在一个新目录）里测不出来。第三判别点是 NG-2：`PATTERN-*` 的适用场景是硬边界，不是"看起来像"就能套用的软提示。

历史分数记在 [基线分数.md](../../../../../docs/skills/frontend-sdd/基线分数.md)。
