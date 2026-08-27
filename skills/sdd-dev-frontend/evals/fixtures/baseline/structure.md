# structure.md — 这是什么栈、什么形态？代码放哪、怎么命名？

栈签名放在本文件，因为它是「代码放哪、怎么命名」的前置条件：不知道是 React，就无法判断 `.tsx` 里的具名函数返回 JSX 是常态还是异常；不知道形态是普通应用，就无法判断「对外只导出一个挂载入口」是常态还是异常。

## 清单

<!-- 覆盖：仓根、src/（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `STRUCT-1` | 仓根 `package.json` 与 `vite.config.ts` | **栈 = React 18 + TypeScript + Vite；形态 = 应用**。栈的判据是源码里具名函数返回 JSX、构建配置挂 React 插件；形态的判据是 `src/main.tsx` 挂载到 DOM 根节点，且包清单没有对外导出入口、没有远端暴露配置、没有平台配置文件。选检视判据、选测试写法都以这条为准 | 全仓 |
| `STRUCT-2` | `src/` 下三层：`components/`、`features/`、`lib/` | 目录实况：**按角色分层**，通用构件、业务特性、共享底座各一层；没有页面平铺，也没有领域层。**消费单元 = `src/features/<领域>/` 目录**，分层判据按它数引用 | 全仓 |
| `STRUCT-3` | 仓根 `tsconfig.json` | `strict` 与 `noUnusedLocals` 已开；类型检查与检查抑制的基准在这里。本仓抑制注释只见有理由的 `@ts-expect-error`，未见 `@ts-ignore` / `@ts-nocheck` | 全仓 |

## 规范

#### `PATTERN-STRUCT-1` · 类型来源与检查抑制

| 项 | 内容 |
| --- | --- |
| 规则 | 接口响应类型手写在消费它的 hook 文件内并导出；确需抑制检查时只用 `@ts-expect-error`，同行或上一行必须写明理由 |
| 依据清单 | `STRUCT-3` |
| 依据样本 | `src/features/portfolio/usePortfolioSummary.ts`（响应类型就近声明并导出、无任何抑制注释）、`tsconfig.json` |
| 违例判定 | 出现 `@ts-ignore`、`@ts-nocheck`、无理由的 `eslint-disable`，或用 `any` 绕过响应类型 |

#### `PATTERN-STRUCT-2` · 放哪一层

| 项 | 内容 |
| --- | --- |
| 规则 | 被两个以上消费单元用到的放 `src/lib/` 或 `src/components/`；只服务一个消费单元的放 `src/features/<领域>/` |
| 依据清单 | `STRUCT-2` |
| 依据样本 | `src/lib/`（`request`、`format` 两份共享底座）、`src/features/portfolio/`（面板与其专属 hook 同目录） |
| 违例判定 | 新增文件放的层与它的实际引用面不符 |

组件与样式文件的具体命名约定不在本文件重复，见 `PATTERN-COMP-1`。

**本仓没有领域层、没有 i18n 资源、没有监控 SDK 初始化，也不是 monorepo。** 这几类「写在哪个层」的事实确实缺失，不是未勘察；引入任何一样都属新规范。
