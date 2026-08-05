# 各栈的具体表现形式

检视维度的定义在 [review-dimensions.md](./review-dimensions.md) 与各检视提示词里，都是与栈无关的。本文件只回答一件事：**那些概念在具体技术栈里长什么样。**

四条使用规则：

1. **只读你要检视的那个栈那一节**，其余不看。栈由 `REPO-1` 的框架字段确定。
2. **`REPO-3` 的 `PATTERN-*` 优先于本文件。** 本文件是通用参考线，仓内已确立的范式是客观基准；两者冲突时按 `PATTERN-*` 判，并在结论里注明基准来源。
3. **本文件列的是「要出现在结论里」的信号，不是自动违规开关。** 命中后仍需按 review-dimensions 的四条规则定级。
4. **你的栈不在下面**：按「与栈无关的判据」那一节走，并在结论的检索范围里写明栈未覆盖。

## 与栈无关的判据

这几类在任何前端栈里都成立，是各维度的最低覆盖：

| 维度 | 判据 |
| --- | --- |
| Q3 复杂度 | 条件嵌套超过 4 层、单函数分支超过 10 条、三元嵌套超过 2 层、模板/视图层内联条件超过 3 层 |
| Q4 状态放置 | 状态的读者与写者不在同一层；同一份数据存了两份并靠副作用同步；可从其他状态算出的值被单独存储；服务端数据与本地 UI 状态混在同一容器 |
| Q5 副作用 | 订阅 / 定时器 / 事件监听 / 请求取消未清理；并发请求返回顺序不定时旧响应覆盖新响应；组件销毁后仍写状态；副作用写了自己依赖的输入 |
| Q7 死代码 | 调试输出语句、断点语句、临时视觉标记（红框、背景色）、占位实现（`TODO` / 空函数体 / 抛未实现 / 写死样例数据顶替真实取数） |
| Q8 性能 | 渲染路径上创建大对象或做重计算而未缓存；列表项标识缺失或用可变下标；大列表未虚拟化（参考线 200 条同时渲染）；高频事件（输入、滚动、resize）未防抖直接触发请求或重排 |
| C4 请求层 | 绕过仓内统一请求实例直接用底层 HTTP API；捕获了错误却既不上报也不提示 |
| C6 检查抑制 | 让类型检查或 lint 闭嘴的写法出现且旁边没有理由 |

## React / Preact / Solid 一类（JSX + hooks）

| 维度 | 具体表现 |
| --- | --- |
| Q4 | 可推导值被 `useState` 存下并用 `useEffect` 同步；状态提到页面顶层导致无关子树重渲染 |
| Q5 | 依赖数组缺项（读到旧值）或多项（重复执行）；`useEffect` 里缺 `AbortController` / 清理函数；effect 里 `setState` 自己的依赖 |
| Q8 | 每次渲染新建函数或对象传给已 `memo` 的子组件；`key` 缺失或用数组下标而列表可重排 |
| C1 命名 | 组件、hook（`use` 前缀）、工具函数各自的命名规则 |
| C2 / C6 写法与类型 | props 类型声明位置与默认值写法、`export` 形式、接口响应类型是手写还是生成 |
| C4 | 绕过仓内请求实例直接 `fetch` / `XMLHttpRequest` / 裸 `axios` |
| C6 | `any`（含隐式）、`@ts-ignore`、`@ts-expect-error`、`@ts-nocheck`、`eslint-disable`（行内与文件级） |

## Vue 一类（SFC + 组合式或选项式）

| 维度 | 具体表现 |
| --- | --- |
| Q4 | 可由 `computed` 推导的值被写成 `ref` 并用 `watch` 同步；`provide/inject` 与 props 混用同一份数据 |
| Q5 | `watch` / `watchEffect` 未用 `onScopeDispose` 或 `onUnmounted` 清理；`immediate: true` 造成的重复请求；`watch` 里改自己监听的源 |
| Q8 | `v-for` 缺 `key` 或用下标；`v-if` 与 `v-for` 同级；深层 `reactive` 大对象；模板里调用函数而非 `computed` |
| C1 命名 | 组件文件名与注册名、组合式函数（`use` 前缀）、`emits` 事件名风格 |
| C2 / C6 写法与类型 | `defineProps` / `defineEmits` 的类型声明方式、`withDefaults` 用法 |
| C4 | 绕过仓内请求实例直接 `fetch` / 裸 `axios` |
| C6 | `any`、`@ts-ignore`、`eslint-disable`、`// @ts-nocheck`、`v-html` 无理由使用 |

## Svelte / Angular 一类

| 维度 | 具体表现 |
| --- | --- |
| Q4 | Svelte：可由 `$derived` / `$:` 推导的值被写成独立 store 并手动同步。Angular：可由 `computed` 推导的值存成独立 `signal`，或 `BehaviorSubject` 与组件字段各存一份 |
| Q5 | Svelte：`$effect` / `onMount` 未返回清理函数，store 订阅未 `unsubscribe`。Angular：订阅未 `takeUntilDestroyed` 或未 `unsubscribe`；`effect()` 内写自己读的 signal |
| Q8 | Svelte：`{#each}` 缺 keyed 表达式。Angular：模板里调用方法而非 `computed` / `pipe`；`*ngFor` 缺 `trackBy`；未用 `OnPush` 而在高频输入上重渲染 |
| C4 | 绕过仓内请求实例（Angular 常见是绕过封装好的 `HttpClient` 服务）直接调底层 HTTP API |
| C6 | `any`、`@ts-ignore`、`eslint-disable`；Angular 额外含 `@SuppressWarnings` 类注解与 `ngSkipHydration` 无理由使用 |

## 样式方案

C3 要判「选的是不是仓内既有那套」，先从 `REPO-3` 读该仓实际用的方案，再按下表看它的硬编码长什么样：

| 方案 | 硬编码信号 |
| --- | --- |
| CSS 自定义属性 / 预处理器变量 | 直接写 `#hex` / `rgb()` / `px` 而不引用 `--*` 或 `$*` |
| 原子化 / 工具类（Tailwind 一类） | 用 `[16px]` 一类任意值转义而 scale 里已有对应档位；同一组类反复复制而未抽成组件或 `@apply` |
| CSS-in-JS | 在样式字面量里写死色值与间距而不取主题对象 |
| 组件库覆盖 | 用 `!important` 或深选择器穿透覆盖，而库本身提供了 token 或主题入口 |

层级值（`z-index`）、圆角、阴影、字号行高都按同一条判：**仓内有 scale 就必须引用 scale**。
