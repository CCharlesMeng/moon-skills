# styling.md — 样式值从哪来，允许怎么写？

## 清单

<!-- 覆盖：src/styles/、src/components/、src/features/（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `STYLE-1` | `src/styles/tokens.css` 的 `:root`，档位前缀 `--color-*`、`--space-*`、`--font-size-*`、`--line-height-*`、`--radius-*`、`--z-*` | **取值的唯一来源**；写任何样式声明前先在这里找对应档位。**具体数值不在本文件复制，打开它 grep 前缀即得** | 全部样式文件 |
| `STYLE-2` | 各组件目录下与组件同名的 `*.module.css` | 样式落地位置：CSS Modules，一个组件一份，与组件文件同目录同名 | 全仓组件 |

## 规范

#### `PATTERN-STYLE-1` · 设计 token 与样式落地

| 项 | 内容 |
| --- | --- |
| 规则 | 样式写在与组件同名的 `*.module.css` 里；颜色、间距、字号、行高、圆角、层级一律引用 `STYLE-1` 的自定义属性，**不写字面量**。没有对应档位的取值先补 token 再用，不在业务样式里落字面值 |
| 依据清单 | `STYLE-1`、`STYLE-2` |
| 依据样本 | `src/components/StatCard/StatCard.module.css`、`src/features/portfolio/PortfolioPanel.module.css`（两份组件样式全部引用 token） |
| 违例判定 | 样式文件里出现 `#hex` / `rgb()` / 字面像素值，而 `STYLE-1` 里有对应档位 |
| 验证 | `lint`，加人工比对 `STYLE-1` |

#### `PATTERN-STYLE-2` · 阴影没有基准

| 项 | 内容 |
| --- | --- |
| 规则 | **`STYLE-1` 没有阴影类档位。** 阴影属基准缺失：出现 `box-shadow` 字面量时**不得按硬编码判阻断**，只能记建议级并问是否补 token |
| 依据清单 | `STYLE-1` |
| 依据样本 | `src/styles/tokens.css` 全量档位里无阴影前缀 |
| 违例判定 | 把阴影字面量当作违反 `PATTERN-STYLE-1` 并升级定级 |

#### `PATTERN-STYLE-3` · 无主题机制

| 项 | 内容 |
| --- | --- |
| 规则 | **只有一套 `:root` 变量，没有主题切换机制、没有暗色变体、没有主题上下文。** 不要为「多主题」预留结构 |
| 依据清单 | `STYLE-1` |
| 依据样本 | `src/styles/tokens.css` 只有一个 `:root` 选择器；全仓无主题提供者 |
| 违例判定 | 计划或实现假设存在主题入口 |
