# runtime.md — 怎么装、怎么起、跑哪些质量命令？

命令只写 script 名，不写展开后的命令行——转述会丢参数。

## 清单

<!-- 覆盖：仓根 package.json、vite.config.ts（2026-08-05） -->

| ID | 指路 | 是什么、何时用 | 被引用 |
| --- | --- | --- | --- |
| `RUN-1` | 仓根 `package.json` 的 `packageManager` 与 `engines` | 包管理器 pnpm，Node 下限已声明；装依赖前先核对本机版本 | — |
| `RUN-2` | 仓根 `package.json` 的 `dev` / `preview` script | 起本地服务；端口写在 script 参数里，**照 script 跑，不要自己拼命令行** | — |
| `RUN-3` | 仓根 `package.json` 的 `test` / `typecheck` / `lint` / `format` / `build` script | 五条质量命令；`targeted-quality` 与全量门都从这里选 | — |
| `RUN-4` | `src/lib/request.ts` 读的两个 `VITE_` 前缀环境变量 | 接口 base 与租户标识，**非敏感、无模板默认值**；缺失时请求会打到相对路径且租户头为空 | 1 处 |

## 质量命令版本

```text
quality_version: 1
```

下游起点命令缓存以这个整数为键。五条质量命令有实质变动（增删、改 scope、改参数）时手动加一。

## 规范

#### `PATTERN-RUN-1` · 质量命令的适用范围

| 项 | 内容 |
| --- | --- |
| 规则 | 五条命令都在仓根跑，都可安全收窄到路径；没有需要先起服务或起 mock 的前置命令 |
| 依据清单 | `RUN-3` |
| 依据样本 | 五条 script 的定义；仓内无 E2E 配置、无 mock server 启动脚本 |
| 违例判定 | 新增质量命令若引入外部服务依赖，必须同时在本节记为不可缓存 |

**本仓没有 E2E 与集成测试命令。** 这不是遗漏：`targeted-quality` 与 `regression` 只能从上面五条里选，不要指望有 E2E 门。
