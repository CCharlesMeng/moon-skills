# 起点质量证据复用与执行 telemetry

主 agent 在 Phase 0 读取本文件；Phase C / D 只在写回质量证据与执行量账本时回读。这里定义的是**机器执行契约**，不新增 QA 标准，也不替代最终全量门。

## 一、起点质量证据的所有权

`REPO-2` 只保存“当前 app 的规范质量命令是什么”；某次执行的命令结果仍属于 Story 的 `DEMAND-2`。为了让相同仓库状态复用上一轮已经跑过的结果，缓存写在目标仓的 Git metadata：

```bash
git -C "<repo-root>" rev-parse --git-path sdd-dev-frontend/preflight-quality.json
```

这个缓存：

- 不是仓库 baseline，不得写入 `<repo-baseline-dir>`；
- 不是正式 Story 工件，不得提交进 `<repo-root>`；
- 只保存紧凑机器事实，`dev-baseline.md` 仍记录本 Story 实际采用的失败集合、缓存指纹、来源与命中状态；
- 不可读取、记录或哈希 token、密码、cookie、账号凭据等秘密。

非 Git 仓、Git metadata 不可写或缓存损坏时一律按普通 `MISS` 处理，实跑质量门；不得把缓存能力本身变成开工阻断。

## 二、精确命中条件

用 `<skill-dir>/scripts/manage_execution_evidence.py probe` 计算状态。只有下列各项**全部逐字一致**且记录不超过 24 小时，才是 `HIT`：

1. `<repo-root>` 的规范绝对路径；
2. `HEAD`；
3. staged diff 的二进制补丁哈希；
4. unstaged diff 的二进制补丁哈希；
5. 每个 untracked 文件的相对路径、类型与内容哈希；
6. `repo-baseline.md` Section 表中的 `REPO-2` 指纹；
7. 本次选中的质量命令及 scope，保持顺序和完整命令字符串；
8. 这些命令实际使用的 toolchain 名称与版本；
9. 会影响结果的非秘密运行模式，例如 package-manager mode、CI mode、OS/arch。

任一项变化、TTL 超时、结果文件不完整，或本次命令依赖网络 / 外部服务 / 时变数据，都是 `MISS`。命令若依赖 `.gitignore` 排除的本机配置、秘密或其他不能安全进入指纹的状态，也必须标成不可缓存；**不允许为了命中去读取或哈希秘密**。`MISS` 是正常分支，必须把具体原因写进 telemetry；不得凭“看起来没变”手工判命中。

命令：

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" probe \
  --repo-root "<repo-root>" \
  --repo2-fingerprint "<REPO-2 指纹>" \
  --quality-command "<scope>::<完整命令>" \
  --toolchain "<name>=<version>" \
  --runtime "<key>=<非秘密值>" \
  --snapshot-out "<临时目录>/preflight-snapshot.json"
```

`probe` 的 JSON 输出只有 `HIT` / `MISS`，并给出 `unstaged-diff-changed`、`quality-commands-changed` 等具体原因。存在任何不可缓存命令时，它仍要作为 `--quality-command` 传入，并额外用完全相同的字符串追加 `--uncacheable-command "<scope>::<完整命令>"`；本轮固定 `MISS` 并实跑全部选中命令，不做部分复用。

### HIT

- 不再执行 Phase 0 的同一组质量命令；
- 从缓存复用逐命令退出码、耗时与具体失败集合；
- `dev-baseline.md / 起点质量` 写 `复用`、状态指纹、缓存来源（`phase-0` / `phase-c` / `phase-d`）、记录时间和缓存路径；
- telemetry 的 `phase-0.quality-gate` 写 `result: reuse`；
- 这次复用**只替代 Phase 0 起点门**。Phase C 候选全量门仍必须在候选代码稳定后执行；Phase D 是否补最终门仍按最终代码指纹决定。

### MISS

- 实跑 `REPO-2` 中本次适用的全部规范命令，记录逐命令结果与具体失败集合；
- `dev-baseline.md / 起点质量` 写 `实跑` 与 miss 原因；
- telemetry 的 `phase-0.quality-gate` 写 `result: run`；
- 执行结束后用同一份 snapshot 与紧凑结果更新缓存：

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" record \
  --snapshot "<临时目录>/preflight-snapshot.json" \
  --quality-result "<临时目录>/quality-result.json" \
  --source phase-0
```

`quality-result.json` 至少含 `commands[]`；每项含与 snapshot 完全相同的 `spec`、`exit_code`、`duration_ms`、`failures[]`。`record` 会拒绝命令集合不一致、字段缺失或带不可缓存命令的记录。

Phase C 候选全量门和 Phase D 最终全量门完成后，也用它们各自的最终状态 snapshot 与紧凑结果调用 `record --source phase-c|phase-d`。因此，下一个 Story 在仓库状态、命令和环境完全相同时可以直接复用；一次 Story 内 Phase C / D 的门禁语义不变。

## 三、执行 telemetry

`<execution-telemetry>` 恒为 `<story-dir>/execution-telemetry.json`。它是紧凑机器账本，由主 agent 在动作完成时增量追加；不保存命令 stdout/stderr、原文报告或推测时间。

Phase -1 开始时 `<story-dir>` 可能尚未唯一定位：此时只把 `phase-1.status` / `phase-1.browser-probe` 的真实起止时间暂存在主 agent 当前上下文或临时目录，Phase 0 第 1 步定位成功后立即原样 flush；不得因此丢掉两步，也不得事后估算时间。

```json
{
  "schema_version": 1,
  "story": "<Story ID>",
  "steps": [
    {
      "id": "phase-0.quality-gate",
      "attempt": 1,
      "kind": "agent",
      "started_at": "<ISO-8601>",
      "ended_at": "<ISO-8601>",
      "duration_ms": 1234,
      "result": "run",
      "counts": {"commands": 3},
      "evidence": ["dev-baseline.md#起点质量"],
      "note": "cache MISS: unstaged-diff-changed"
    }
  ]
}
```

`result` 只用 `run` / `reuse` / `skip` / `blocked`；重试追加新行并递增 `attempt`，不得覆盖前一轮。`kind` 只用 `agent` / `human_wait`，用户等待必须单独记，不能并入 agent 主动执行时间。

前半程最少记录这些稳定 ID：

| ID | 记录边界 |
| --- | --- |
| `phase-1.status` | baseline `status` + `validate` 路由 |
| `phase-1.browser-probe` | browser driver 能力与启动探针 |
| `phase-0.context` | 路径、场景、base-ref、Impact 定级 |
| `phase-0.quality-gate` | 起点质量门实跑 / 复用与 miss 原因 |
| `phase-a1.extract` | 设计事实抽取 / 哈希复用 |
| `phase-a1.block-specs` | 切分与区块规格生成 / 复用 |
| `phase-a1.recon-codebase` | `lite` / `full` / `skip` 及回退原因 |
| `phase-a2.recon-spec` | 规格侧勘察与重试 |
| `phase-a2.merge-validate` | 跨份校验、落盘与契约编译前准备 |
| `human.qa-confirmation` | 等待 QA 基线确认，`kind: human_wait` |
| `phase-b.task.<task>.<channel>.red` | 还原 / 逻辑通道的 RED；双通道时各写一行，counts 记 commands，不因共享波次合并 |
| `phase-b.task.<task>.<channel>.green` | 对应通道的 GREEN 与受影响重跑；counts 记 commands / reused_results |
| `phase-b.validation.<n>` | `VAL-B-<n>` 非行为定向检查的 run / reuse / blocked；counts 记 commands / tasks / consumers / reused_results |
| `phase-b.browser-evidence` | Step ④ 已执行场景写入可提升原始事实；counts 记 capture / update |
| `phase-c.quality-gate` | 候选全量门 run / reuse |
| `phase-c.browser-evidence` | Phase B 场景 promote / stale 与缺口 run / reuse |
| `phase-c.review.<role>` | 每个角色独立的 start / complete / retry；attempt 递增 |
| `phase-c.review-refill` | 任一槽位释放后启动下一待派角色；counts 记 refill |
| `phase-c.aggregate` | 四份 JSON 校验与确定性聚合 |

追加动作使用：

```bash
python3 "<skill-dir>/scripts/manage_execution_evidence.py" telemetry \
  --file "<execution-telemetry>" --story "<Story ID>" \
  --id phase-0.quality-gate --attempt 1 --kind agent \
  --started-at "<ISO-8601>" --ended-at "<ISO-8601>" --result reuse \
  --count commands=3 --evidence "dev-baseline.md#起点质量" \
  --note "cache HIT: <state_fingerprint>"
```

双通道共享一次产品实现时，两条 RED 与两条 GREEN telemetry 仍分别存在，`note` 可引用同一个 implementation fingerprint；不要伪造成一个通道。验证批次复用时用 `result: reuse`，在 `evidence` 引用同一个 `VAL-B-<n>`，并用 `counts` 区分 `commands`、`tasks`、`consumers` 与 `reused_results`。代码变化导致失效时追加新 attempt 和失效原因，不覆盖旧行。

Phase B / C / D 至少按上述稳定边界续记；质量门、定向检查、验证批次、浏览器场景 promote / run / reuse / stale、子代理启动 / 动态补位 / 重试要能从 `steps[]` 的 ID / `counts` 机械汇总。Phase D 从这份 JSON 生成 `dev-review.md / 执行量账本`，没有记录就写“未记录”，禁止凭 LOC 或回忆估算。
