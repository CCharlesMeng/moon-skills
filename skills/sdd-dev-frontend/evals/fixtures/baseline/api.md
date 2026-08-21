# api.md — 怎么跟后端说话？

只装跨需求稳定的通信约定。**具体端点的 URL、请求响应字段与枚举不在这里**，那是 Story 级契约，事实源在上游设计文档。

## 清单

<!-- 覆盖：src/lib/、src/features/（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `API-1` | `src/lib/request.ts` 的 `request` | **全仓唯一 HTTP 出口**；任何后端调用都从这里进。它统一挂鉴权头与租户头、把后端错误码翻成用户可读文案、透传取消信号 | 1 处（`usePortfolioSummary`） |
| `API-2` | 同文件的 `RequestError` 与 `ERROR_MESSAGES` | 错误对象与错误码到文案的映射表；判断某个后端错误码有没有对应文案、要不要补，看这张表 | 随 `API-1` |
| `API-3` | `eslint.config.js` 的 `no-restricted-globals` | 仓内以 lint 规则禁止裸 `fetch`；这条规则是 `PATTERN-API-1` 的机器执行面 | — |

## 规范

#### `PATTERN-API-1` · 请求统一出口

| 项 | 内容 |
| --- | --- |
| 规则 | 一切后端调用只经 `API-1`；不得直接用 `fetch` / `XMLHttpRequest` / 裸 HTTP 客户端。错误一律以 `API-2` 的错误对象向上抛，**不在调用点自拼提示文案** |
| 依据清单 | `API-1`、`API-2`、`API-3` |
| 依据样本 | `src/lib/request.ts`（出口内部完成鉴权、租户、错误翻译、取消透传）、`eslint.config.js`（lint 层禁裸 `fetch`）、`src/features/portfolio/usePortfolioSummary.ts`（唯一调用点，走出口） |
| 违例判定 | 源码里出现 `fetch(` / `XMLHttpRequest` 而所在文件未从 `API-1` 导入；或调用点自己拼错误文案而不用 `API-2` |
| 验证 | `lint`（已禁 `fetch`）、`typecheck` |

#### `PATTERN-API-2` · 无 mock 层

| 项 | 内容 |
| --- | --- |
| 规则 | **本仓没有请求拦截层，也没有 mock server。** 需要脱离后端跑时只能在测试里替换出口，不要去找不存在的 handler 目录 |
| 依据清单 | `API-3` |
| 依据样本 | 仓内无 MSW、无 fixture server、无 `vite.config.ts` 代理配置 |
| 违例判定 | 计划或实现假设存在 mock 约定 |
