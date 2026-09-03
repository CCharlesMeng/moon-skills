# dev-baseline — US1 风险客户看板体验

| 字段 | 值 |
| --- | --- |
| Story / repo | `US1` / `dashboard-sdd` |
| 基线源 | 文字规格：`tasks.md` 与 `alpha-tests.md` |
| 来源指纹 | 示例基线 `dashboard-sdd-manual-v1` |
| 冻结状态 | 已冻结 ✅（仅作为演示夹具） |
| 确认时间 | 2026-09-03 |
| 声明状态 | 冻结时全部为 `UNVERIFIED`；逐条状态见 `alpha-tests.md` 的 AC ↔ 证据映射 |
| 执行档位 | lite；还原 Task=0、风险触发器=interaction、产品文件=1 |
| app baseline | 无：该目录是独立演示夹具，不代表真实业务仓库 |
| 设计事实 / 区块规格 | 无（基线源为文字规格） |
| 还原契约 | 无：两条声明均为通过资格门禁的 `manual_acceptance` |

## 执行起点（环境）

| 项 | 值 |
| --- | --- |
| `base-ref` | `example-base` |
| 需求路径 | `tasks.md`、`alpha-tests.md` |
| 起点质量命令 | 静态 HTML 可直接打开；本示例不把人工判断伪装成自动化结果 |
| 场景 | Chrome、1920×1080、浏览器缩放 100%；打开 `dashboard-sdd/demo.html` |
| Story 限制 | 只用于演示人工验收登记与回填，不代表生产系统验收结论 |

## 起点质量

| 已选模块 | 命令 / scope | exit / failures | 证据键 |
| --- | --- | --- | --- |
| causal、targeted-quality | 由真实人员按 `acceptance.md` 执行；页面文件做定向质量检查 | 人工项待执行 | `AT-US1-001`、`AT-US1-002` |

## 验证组合（初始）

| 风险触发器 | 模块 | 独立检视与维度 | 依赖声明 |
| --- | --- | --- | --- |
| interaction | causal、targeted-quality | 无；本示例只展示人工验收通道 | `AT-US1-001`、`AT-US1-002` |

## QA 基线

两条运行时可观察判定及人工验收环境已冻结在 `alpha-tests.md`。本示例没有额外的还原规则、接口契约或豁免；是否通过仍要以真实人员留下的录屏或审批记录为准。
