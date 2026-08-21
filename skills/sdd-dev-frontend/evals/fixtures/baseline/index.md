# risk-console — 入口

本目录八份文件，每份回答一个问句。本文件只做路由，没有事实正文。

## 场景索引

| 要做的事 | 读这几条 |
| --- | --- |
| 新增一个通用构件 | `PATTERN-COMP-1`、`PATTERN-STYLE-1` |
| 新增一个业务面板 | `PATTERN-COMP-1`、`COMP-2`、`PATTERN-STYLE-1` |
| 加一个后端调用 | `PATTERN-API-1`、`API-2` |
| 组件内异步取数与三态 | `PATTERN-DATA-1`、`DATA-1`、`PATTERN-API-1` |
| 展示百分比 / 金额 / 日期 | `PATTERN-COMP-2` |
| 写样式取值 | `PATTERN-STYLE-1`、`STYLE-1` |
| 声明接口响应类型或抑制类型检查 | `PATTERN-STRUCT-1` |
| 写测试 | `TEST-1`、`PATTERN-TEST-1` |

## 单点事实速查

| 问 | 答 | 定义在 |
| --- | --- | --- |
| 什么栈 | React 18 + TypeScript + Vite | `STRUCT-1` |
| 包管理器 | pnpm | `RUN-1` |
| 启动 | `dev` script | `RUN-2` |
| 质量命令 | `test` / `typecheck` / `lint` / `format` / `build` | `RUN-3` |
| 测试框架 | Vitest | `TEST-1` |

## 文件导航

| 文件 | 判定问句 |
| --- | --- |
| `structure.md` | 这是什么栈？代码放哪、怎么命名？ |
| `runtime.md` | 怎么装、怎么起、跑哪些质量命令？ |
| `components.md` | 拼界面时有哪些现成构件可用？ |
| `api.md` | 怎么跟后端说话？ |
| `data.md` | 拿到的数据在前端怎么持有、怎么流到界面？ |
| `styling.md` | 样式值从哪来，允许怎么写？ |
| `testing.md` | 测试用什么写、怎么定位元素、怎么跑？ |
