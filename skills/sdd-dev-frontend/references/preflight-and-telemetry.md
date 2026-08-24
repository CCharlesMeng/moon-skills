# 起点证据缓存与可选 telemetry

只在初始验证组合选择命令模块，或本次明确需要流程优化取数时读取对应小节。两节的判据都由 `<skill-dir>/scripts/manage_execution_evidence.py` 计算或校验，不在本文件手工比对。

## 一、起点命令缓存

`<preflight-cache>` 是本机 Git metadata 缓存，不是 Story 工件：不写入 `<repo-baseline-dir>`、不提交进 `<repo-root>`、不记录或哈希 token、密码、cookie 等秘密。非 Git 仓、metadata 不可写或缓存损坏时按普通 `MISS` 处理，不让缓存能力本身变成开工阻断。

命中判定只由 `probe` 给出，**不得凭「看起来没变」手工判命中**：

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" probe \
  --repo-root "<repo-root>" \
  --quality-version "<runtime.md 质量命令节的版本号>" \
  --quality-command "<scope>::<完整命令>" \
  --toolchain "<name>=<version>" \
  --runtime "<key>=<非秘密值>" \
  --snapshot-out "<临时目录>/preflight-snapshot.json"
```

脚本比对仓库状态、质量命令版本号、命令与 scope、toolchain 和运行模式并施加 TTL，输出 `HIT` / `MISS` 加具体原因。版本号是 `runtime.md` 质量命令节的整数，命令有实质变动时由 `sdd-init-frontend` 手动加一；它不是内容哈希，人和 agent 都能看出是第几版。依赖网络、外部服务、时变数据或不能安全进入指纹的本机状态的命令，用完全相同的字符串额外传 `--uncacheable-command`；本轮固定 `MISS`，实跑全部选中命令，不做部分复用。

| 结果 | 动作 |
| --- | --- |
| `HIT` | 不再执行同一组命令，复用逐命令退出码、耗时与失败集合；`dev-baseline.md / 起点质量` 写 `复用`、状态指纹与缓存来源 |
| `MISS` | 只实跑验证组合选中的命令；`dev-baseline.md` 写 `实跑` 与 miss 原因，随后按下方 `record` 覆盖对应键 |

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" record \
  --snapshot "<临时目录>/preflight-snapshot.json" \
  --quality-result "<临时目录>/quality-result.json" \
  --source phase-0
```

`quality-result.json` 的 `commands[]` 每项含与 snapshot 相同的 `spec`、`exit_code`、`duration_ms`、`failures[]`；命令集合不一致、字段缺失或含不可缓存命令时 `record` 会拒绝。Phase C / D 实际执行命令模块后用 `--source phase-c|phase-d` 记录；未执行命令模块时不写空记录。不同命令独立判定，不因一条 `MISS` 让全部失效。

## 二、执行 telemetry（可选）

默认不创建 `<execution-telemetry>`。只有用户或本次任务明确要评估流程成本时才开启；缺席不是降级，也不进入门禁。开了就整段记满，不留空文件和半张表。

每个动作完成时追加一行，ID 用 `<phase>.<action>` 稳定命名：

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" telemetry \
  --file "<execution-telemetry>" --story "<Story ID>" \
  --id phase-0.quality-gate --attempt 1 --kind agent \
  --started-at "<ISO-8601>" --ended-at "<ISO-8601>" --result reuse \
  --count commands=3 --evidence "dev-baseline.md#起点质量" \
  --note "cache HIT: <state_fingerprint>"
```

`result` 只用 `run` / `reuse` / `skip` / `blocked`；重试追加新 `attempt`，不覆盖历史。用户等待单独记 `--kind human_wait`，不并入 agent 执行时间。Phase D 只从这份 JSON 机械汇总动作次数与耗时，没有记录就写「未记录」，不用 LOC、回忆或估算补。

**浏览器动作分三类记，不并进 `agent`。** 它们的削减手段完全不同，混成一个数就看不出该动哪一边：

| `--kind` | 记什么 | 削减手段 |
| --- | --- | --- |
| `browser_connect` | 打开或连接一次页面 | 批量——同页面 / fixture / runtime / reset 边界只连一次 |
| `browser_inject` | 注入一次采集脚本 | 契约范围——跨页按页面各一次，不是按规则 |
| `browser_capture` | 截一张图 | 盲区收窄 + visual YELLOW 默认落 `UNVERIFIED` |

浏览器探针只在验证组合选择相关模块时记录（`browser_connect`，`result` 用 `blocked` 表示探针失败）。这三类是当前唯一能把浏览器成本变成实测的入口——在它们落地之前，仓里一条浏览器耗时数据都没有，唯一的次数统计是从事故复盘里捞出来的，不是流程自己产出的。
