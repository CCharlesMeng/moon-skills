### 人工维护（agent 维护）

#### `PATTERN-TOKEN-1` · 设计 token 与样式落地

| 项 | 内容 |
| --- | --- |
| 适用场景 | 任何新增或修改的样式 |
| 工程入口 | `src/styles/tokens.css` |
| 使用方式 | 样式写在与组件同名的 `*.module.css` 里，颜色、间距、字号、行高、圆角、层级一律引用 `var(--*)`，不写字面量 |
| 不变量 | tokens.css 是取值的唯一来源；没有对应 token 的取值先补 token 再用，不在业务样式里落字面量 |
| 验证 | `pnpm lint` 与人工比对 `src/styles/tokens.css` |
| 标签 | `style`、`token`、`css-modules` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/styles/tokens.css` | 全量 token 定义；无阴影类 token |
| `src/components/StatCard/StatCard.module.css` | 组件样式全部引用 token 的既有样例 |

#### `PATTERN-REQUEST-1` · 请求出口与错误码映射

| 项 | 内容 |
| --- | --- |
| 适用场景 | 一切后端调用 |
| 工程入口 | `src/lib/request.ts` 的 `request<T>()` |
| 使用方式 | 只经 `request()` 发起调用；它统一挂 `Authorization` 与 `X-Tenant-Id`、把后端 `code` 经 `ERROR_MESSAGES` 翻成用户可读文案、透传 `AbortSignal` |
| 不变量 | 不得直接调用 `fetch` / `XMLHttpRequest`；错误一律以 `RequestError` 形式向上抛，不在调用点自拼提示文案 |
| 验证 | `pnpm lint`（`no-restricted-globals` 已禁 `fetch`）、`pnpm typecheck` |
| 标签 | `request`、`error-mapping`、`auth` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/lib/request.ts` | 唯一请求出口、鉴权头、错误码映射表、取消透传 |
| `eslint.config.js` | 仓内以 lint 规则禁止裸 `fetch` |

#### `PATTERN-ASYNC-1` · 异步取数三态与取消

| 项 | 内容 |
| --- | --- |
| 适用场景 | 组件内取数 |
| 工程入口 | `src/features/portfolio/usePortfolioSummary.ts` |
| 使用方式 | 以 `use<领域>` 命名的 hook 承载取数，返回 `{ data, loading, error }` 三态；`useEffect` 内建 `AbortController`，卸载时 `abort` |
| 不变量 | 错误必须落到 `error` 字段并由视图渲染错误态，不得捕获后静默丢弃；`aborted` 的失败不写入 `error` |
| 验证 | `pnpm test` |
| 标签 | `async`、`hooks`、`loading`、`error-state` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/features/portfolio/usePortfolioSummary.ts` | 三态返回、取消、错误转 message 的既有样例 |
| `src/features/portfolio/PortfolioPanel.tsx` | 视图侧 loading / error / empty 三分支渲染 |

#### `PATTERN-FORMAT-1` · 数值展示口径

| 项 | 内容 |
| --- | --- |
| 适用场景 | 百分比、金额、日期的展示 |
| 工程入口 | `src/lib/format.ts` |
| 使用方式 | 展示层调用 `formatPercent` / `formatAmount` / `formatDate`，不自行拼接 |
| 不变量 | 百分比默认一位小数，金额以万元为单位，非有限数一律显示 `--`；口径变更只改本文件 |
| 验证 | `pnpm test` |
| 标签 | `format`、`display`、`shared` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/lib/format.ts` | 三个格式化函数与空值口径 |
| `src/features/portfolio/PortfolioPanel.tsx` | 展示层调用而非自实现 |

#### `PATTERN-COMPONENT-1` · 组件写法与目录命名

| 项 | 内容 |
| --- | --- |
| 适用场景 | 新增组件与特性面板 |
| 工程入口 | `src/components/StatCard/StatCard.tsx` |
| 使用方式 | 通用组件放 `src/components/<PascalCase 目录>/<PascalCase>.tsx`，业务面板放 `src/features/<kebab-case 领域>/<PascalCase>.tsx`；一律具名函数声明 + 具名导出，props 以 `interface <组件名>Props` 就近声明并导出；样式同名 `*.module.css`；跨目录导入走 `@/` 别名 |
| 不变量 | 不使用默认导出；不使用 `React.FC`；文件名与导出的组件名逐字一致 |
| 验证 | `pnpm typecheck`、`pnpm lint` |
| 标签 | `component`、`naming`、`directory` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `src/components/StatCard/StatCard.tsx` | 具名函数 + 具名导出 + `interface StatCardProps` |
| `src/features/portfolio/PortfolioPanel.tsx` | 业务面板目录与命名、`@/` 别名导入 |

#### `PATTERN-TYPING-1` · 类型来源与检查抑制

| 项 | 内容 |
| --- | --- |
| 适用场景 | 类型声明与任何让类型检查/lint 闭嘴的写法 |
| 工程入口 | `tsconfig.json`（`strict: true`） |
| 使用方式 | 接口响应类型手写在消费它的 hook 文件内并导出；确需抑制检查时只用 `@ts-expect-error`，同行或上一行必须写明理由 |
| 不变量 | 禁止 `@ts-ignore`；禁止无理由的 `eslint-disable`；禁止用 `any` 绕过响应类型 |
| 验证 | `pnpm typecheck`、`pnpm lint` |
| 标签 | `typing`、`suppression`、`strict` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `tsconfig.json` | `strict` 与 `noUnusedLocals` 已开 |
| `src/features/portfolio/usePortfolioSummary.ts` | 响应类型就近声明并导出、无任何抑制注释 |
