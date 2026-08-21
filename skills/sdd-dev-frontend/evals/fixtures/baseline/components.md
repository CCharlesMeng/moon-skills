# components.md — 拼界面时有哪些现成构件可用？

## 清单

### 通用构件

<!-- 覆盖：src/components/（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `COMP-1` | `src/components/StatCard/` 的 `StatCard` | 展示**单个**指标数值的卡片。指标名 + 数值 + 语气色。**不要拿它做多值对比或表格行**，那需要新构件 | 2 处特性 |

### 业务组件路由索引

<!-- 覆盖：src/features/（2026-08-05） -->

| ID | 路由 / 特性 | 入口 | 何时看它 |
| --- | --- | --- | --- |
| `COMP-2` | `portfolio` 组合概览 | `src/features/portfolio/` 的 `PortfolioPanel` | 需要一个「取数 + 三态 + 多张指标卡」的现成样例时；它是本仓面板写法的参照页 |

### 渲染辅助

<!-- 覆盖：src/lib/（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `COMP-3` | `src/lib/format.ts` 的 `formatPercent` / `formatAmount` / `formatDate` | 展示层取数值文案的唯一入口，三个纯函数分别管百分比、金额、日期 | 1 处 |

## 规范

#### `PATTERN-COMP-1` · 组件写法与目录命名

| 项 | 内容 |
| --- | --- |
| 适用场景 | **新增组件与特性面板。** 不含 `src/lib/` 下的工具函数与渲染辅助 |
| 规则 | 通用组件放 `src/components/<PascalCase 目录>/<PascalCase>.tsx`，业务面板放 `src/features/<kebab-case 领域>/<PascalCase>.tsx`；一律具名函数声明 + 具名导出；props 以 `interface <组件名>Props` 就近声明并导出；样式同名 `*.module.css`；跨目录导入走 `@/` 别名 |
| 不变量 | 不使用默认导出；不使用 `React.FC`；文件名与导出的组件名逐字一致 |
| 依据清单 | `COMP-1`、`COMP-2` |
| 依据样本 | `src/components/StatCard/StatCard.tsx`（具名函数 + 具名导出 + 就近 props 接口）、`src/features/portfolio/PortfolioPanel.tsx`（业务面板目录与命名、`@/` 别名导入） |
| 违例判定 | 文件名与导出名不一致、默认导出、`React.FC`、props 未导出或未按 `<组件名>Props` 命名、跨目录用相对路径而非 `@/` |
| 验证 | `typecheck`、`lint` |

#### `PATTERN-COMP-2` · 数值展示口径

| 项 | 内容 |
| --- | --- |
| 适用场景 | 百分比、金额、日期的展示 |
| 规则 | 展示层调用 `COMP-3` 的三个函数，**不自行拼接**。口径变更只改 `src/lib/format.ts` 一处 |
| 不变量 | 非有限数一律显示占位符而不是 `NaN` / `null`；同一屏上同类数值的空值形态必须一致 |
| 依据清单 | `COMP-3` |
| 依据样本 | `src/lib/format.ts`（三个函数的空值口径一致）、`src/features/portfolio/PortfolioPanel.tsx`（展示层调用而非自实现） |
| 违例判定 | 展示层自实现等价格式化；或对可能非有限的数值直接做字符串转换 |
| 验证 | `test` |

**`COMP-3` 没有计数类格式化函数。** 整数计数的展示口径属基准缺失：直接字符串化会在非有限数时露出 `NaN`，但仓内没有现成函数可替换，**修法需人定**，不要当成能直接替换的重复实现。
