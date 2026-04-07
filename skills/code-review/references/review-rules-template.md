# Review Rules: <层级名>

<!-- 层级：base（仓库级）/ <topic>（需求级）/ defensive（防御级） -->

## 规则列表

### <规则类别>

| # | 规则 | 检查方式 | 严重度 |
| --- | --- | --- | --- |
| R-1 | <规则描述> | <如何检查：代码搜索 / 静态分析 / 人工审查> | blocking / suggestion |

## 示例

### 命名规范（仓库级 base.md 示例）

| # | 规则 | 检查方式 | 严重度 |
| --- | --- | --- | --- |
| R-1 | React 组件使用 PascalCase，hooks 使用 use 前缀 | 文件名和导出名检查 | blocking |
| R-2 | API 请求函数统一使用 fetch 前缀（fetchOrders, fetchUsers） | 函数名搜索 | suggestion |
| R-3 | 状态变量使用 is/has/should 前缀表示布尔值 | 变量名检查 | suggestion |

### 领域命名（需求级 <topic>.md 示例）

| # | 规则 | 检查方式 | 严重度 |
| --- | --- | --- | --- |
| R-1 | "订单"统一使用 Order，不用 Trade/Transaction | 代码搜索 | blocking |
| R-2 | 分页参数使用 page/pageSize，不用 offset/limit | 接口调用检查 | blocking |

### 反模式（防御级 defensive.md 示例）

防御级规则额外增加 `immune_ref` 列，引用 `immune-registry.yaml` 中对应资产的 `id`，用于 `code-review` 反写触发记录。

| # | 规则 | 检查方式 | 严重度 | immune_ref |
| --- | --- | --- | --- | --- |
| DEF-R-1 | 禁止在 useEffect 中直接调用未包装的 fetch（历史 race condition 根因） | hook 代码审查 | blocking | no-bare-fetch-in-effect |
| DEF-R-2 | 分页请求必须处理 stale response（上次事故根因：快速翻页导致旧页数据覆盖新页） | 请求逻辑审查 | blocking | guard-stale-pagination |

**防御级规则编号约定**：使用 `DEF-R-N` 格式（区别于仓库级和需求级的 `R-N`），确保跨层级唯一。`immune_ref` 填写 `immune-registry.yaml` 中对应条目的 `id`，若暂无对应条目可留空。
