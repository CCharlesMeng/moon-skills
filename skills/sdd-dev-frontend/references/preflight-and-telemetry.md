# 起点证据缓存与可选 telemetry

只在初始验证组合选择命令模块，或本次明确需要流程优化取数时读取对应小节。

## 一、起点命令缓存

`<preflight-cache>` 是本机 Git metadata 缓存，不是 Story 工件。每条命令记录 command、scope、toolchain/runtime、代码状态、exit code、duration 与 failures。

缓存命中必须同时满足：

- 24 小时内；
- base/HEAD、暂存、未暂存、未跟踪文件及相关内容哈希一致；
- REPO-2 指纹、实际 command、scope、toolchain/runtime 一致；
- 记录含完整退出码和失败集合。

任一字段缺失或不同即 MISS。HIT 复用整条失败集合，不重跑；MISS 只执行验证组合选中的命令并覆盖对应键。不同命令独立判定，不因一条 MISS 让全部失效。

Phase C/D 若同一命令键仍新鲜可继续复用；最终组合没有命令模块时不补“最终全量门”。

## 二、执行 telemetry（可选）

默认不创建 `<execution-telemetry>`。只有用户或本次任务明确要评估流程成本时才开启；缺席不是降级，也不进入门禁。

每个动作追加紧凑记录：

```json
{
  "id": "phase.action",
  "attempt": 1,
  "result": "run | reuse | skip",
  "started_at": "<ISO-8601>",
  "duration_ms": 0,
  "human_wait_ms": 0,
  "input_fingerprint": "<sha256>",
  "output": "<path or short fact>"
}
```

重试追加新 attempt，不覆盖历史；用户等待只记入 `human_wait_ms`，不混入 agent 执行时间。Phase D 从 JSON 机械汇总动作次数、运行/复用/跳过与耗时，不用 LOC、回忆或估算。
