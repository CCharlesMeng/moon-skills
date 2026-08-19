# `alpha-tests.md` 的执行证据扩展

只在首次记录还原证据或 Phase D 对账时读取。`alpha-tests.md` 是唯一证据账本；机器报告保留完整事实，账本只保存可追溯索引。

## 还原证据记录

每个还原轮追加一条：

```markdown
### R-<Task>-<轮次> · <区块>

| 项 | 值 |
| --- | --- |
| 受影响声明 | <AC / AT / R 行> |
| 基线与契约 | <baseline fingerprint / contract sha256> |
| 环境 | <route / fixture / viewport / runtime> |
| RED | <report path + fingerprint + 三色摘要> |
| GREEN | <report path + fingerprint + 三色摘要> |
| 视觉补证 | <无；或 cache/screenshot path + fingerprint> |
| 相关依赖 | <depends_on + captured hashes> |
| 状态 | PROVEN / UNVERIFIED / DEFERRED |
| 说明 | <未证原因或解除条件；无则“无”> |
```

RED/GREEN 必须来自同一冻结契约；哈希不一致、真实 RED 或未解决 YELLOW 都不能支持 `PROVEN`。视觉截图只在契约要求 visual 且结构化事实不足时记录。

## AC ↔ 证据映射

```markdown
| AC / AT | 声明 | 状态 | 证据记录 | 新鲜度 | 说明 |
| --- | --- | --- | --- | --- | --- |
```

每条声明恰有一个状态。同一证据可被多条声明引用，不复制报告内容。依赖变化时把命中声明改回 `UNVERIFIED`，重取证后再更新。

## Deferred

```markdown
| AC / AT | 外部依赖 | 当前证据 | 解除条件 | 恢复入口 |
| --- | --- | --- | --- | --- |
```

本阶段做得到但没执行属于 `UNVERIFIED`，不写 Deferred。旧 Story 缺还原节时按上述形状增量新增，不迁移既有 L4/L3 记录。

## 自检

- [ ] 每条记录有声明、契约/环境、证据路径、依赖与状态。
- [ ] `PROVEN` 的证据覆盖声明且对最终依赖新鲜。
- [ ] RED/YELLOW 没有被摘要成 GREEN。
- [ ] `UNVERIFIED` 与 `DEFERRED` 原因和下一步明确。
