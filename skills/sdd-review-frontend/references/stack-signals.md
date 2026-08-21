# 栈内信号

检查项的定义在各 checklist 里，与栈无关。本文件只回答：**那些概念在具体技术栈里长什么样。**

1. 只读当前仓那一节。栈由仓库 baseline `structure.md` 的栈签名确定（`STRUCT-*`），那条结论必须是一个具名的栈；读不出具名栈就按第 4 条走。
2. 仓内 `PATTERN-*` 优先于本文件。冲突时按 `PATTERN-*` 判，并在 `basis` 里写规范 ID。**写着「无统一做法」的规范同样优先**：它的结论是本仓没有基准，据此不判违规，不用本文件的信号去补一个仓库没有的基准。
3. 这里是「要出现在结论里」的信号，不是自动违规开关。命中后仍按 [SKILL.md 定级](../SKILL.md#定级) 与该条 `max_severity` 出 Finding。
4. 栈不在下面：按「与栈无关」那一节走，并在 `known_gaps` 写明栈未覆盖。

## 与栈无关

| 检查项 | 信号 |
| --- | --- |
| `complexity-and-nesting` | 条件嵌套 >4 层、单函数分支 >10 条、三元嵌套 >2 层、模板内联条件 >3 层 |
| `state-placement` | 读者与写者不在同一层；同一份数据存两份靠副作用同步；可推导值被单独存储；服务端数据与本地 UI 状态混装 |
| `side-effect-management` | 订阅 / 定时器 / 监听 / 请求取消未清理；旧响应覆盖新响应；销毁后仍写状态；副作用写自己依赖的输入 |
| `dead-code-leftovers` | 调试输出、断点、临时视觉标记、占位实现（`TODO` / 空函数体 / 抛未实现 / 写死样例顶替真实取数） |
| `obvious-performance` | 渲染路径上创建大对象或重计算未缓存；列表缺稳定标识或用可变下标；大列表未虚拟化（参考线 200 条同时渲染）；高频事件未防抖直接请求或重排 |
| `request-and-error-handling` | 绕过仓内统一请求实例直接用底层 HTTP API；捕获了错误却既不上报也不提示 |
| `typing-and-suppression` | 让类型检查或 lint 闭嘴的写法出现且旁边没有理由 |

## React / Preact / Solid

| 检查项 | 表现 |
| --- | --- |
| `state-placement` | 可推导值被 `useState` 存下并用 `useEffect` 同步；状态提到页面顶层导致无关子树重渲染 |
| `side-effect-management` | 依赖数组缺项或多项；`useEffect` 缺 `AbortController` / 清理函数；effect 里 `setState` 自己的依赖 |
| `obvious-performance` | 每次渲染新建函数或对象传给已 `memo` 的子组件；`key` 缺失或用数组下标而列表可重排 |
| `request-and-error-handling` | 直接 `fetch` / `XMLHttpRequest` / 裸 `axios` |
| `typing-and-suppression` | `any`（含隐式）、`@ts-ignore`、`@ts-expect-error`、`@ts-nocheck`、`eslint-disable` |

## Vue

| 检查项 | 表现 |
| --- | --- |
| `state-placement` | 可由 `computed` 推导的值写成 `ref` 并用 `watch` 同步；`provide/inject` 与 props 混用同一份数据 |
| `side-effect-management` | `watch` / `watchEffect` 未在 `onScopeDispose` / `onUnmounted` 清理；`immediate: true` 造成重复请求；`watch` 里改自己监听的源 |
| `obvious-performance` | `v-for` 缺 `key` 或用下标；`v-if` 与 `v-for` 同级；模板里调用函数而非 `computed` |
| `request-and-error-handling` | 直接 `fetch` / 裸 `axios` |
| `typing-and-suppression` | `any`、`@ts-ignore`、`eslint-disable`、`v-html` 无理由使用 |

## Svelte / Angular

| 检查项 | 表现 |
| --- | --- |
| `state-placement` | Svelte：可由 `$derived` / `$:` 推导的值写成独立 store 并手动同步。Angular：可由 `computed` 推导的值存成独立 `signal`，或 `BehaviorSubject` 与组件字段各存一份 |
| `side-effect-management` | Svelte：`$effect` / `onMount` 未返回清理；store 未 `unsubscribe`。Angular：订阅未 `takeUntilDestroyed`；`effect()` 内写自己读的 signal |
| `obvious-performance` | Svelte：`{#each}` 缺 keyed 表达式。Angular：模板里调用方法而非 `computed` / `pipe`；`*ngFor` 缺 `trackBy` |
| `request-and-error-handling` | 绕过封装好的 `HttpClient`（或仓内等价物）直接调底层 HTTP API |
| `typing-and-suppression` | `any`、`@ts-ignore`、`eslint-disable`；Angular 另含无理由 `ngSkipHydration` |

## 样式方案（convention / `style-token-scheme`）

先读仓内实际方案，再对硬编码：

| 方案 | 硬编码信号 |
| --- | --- |
| CSS 自定义属性 / 预处理器变量 | 直接写 `#hex` / `rgb()` / `px` 而不引用 `--*` 或 `$*` |
| 原子化 / 工具类 | 用 `[16px]` 一类任意值转义而 scale 里已有对应档位 |
| CSS-in-JS | 样式字面量里写死色值与间距而不取主题对象 |
| 组件库覆盖 | 用 `!important` 或深选择器穿透，而库提供了 token / 主题入口 |

`z-index`、圆角、阴影、字号行高同一条：**仓内有 scale 就必须引用 scale**。
