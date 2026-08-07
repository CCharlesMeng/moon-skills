## 环境实证

本现场是评测用 fixture，不是真实开发机。以下为如实记录，**不要把它当成一次成功的 onboarding**。

| 项 | 结果 |
| --- | --- |
| 依赖安装 | 未执行。仓内无 `node_modules`，`package.json` 声明的依赖均未下载 |
| 目标页面启动 | 未执行 |
| `pnpm test` / `pnpm typecheck` / `pnpm lint` / `pnpm build` | 未执行 |
| 浏览器采集能力 | 未探测 |

REPO-1～3 的自动发现全部来自静态配置文件解析，不依赖上述动作；REPO-3 的人工维护范式由 `baseline/repo-3-patterns.md` 冻结，证据路径在仓内均真实存在，可逐条打开核对。
