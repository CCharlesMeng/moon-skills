# 验证批次执行契约

Phase B 开始前完整读取本文件；Phase C / D 只在补采或重跑验证时回读。这里的核心不是缓存，而是**执行前先收集验证意图，按兼容性一次执行，再把结果逐项分发给 Task、AC 与 R/F 行**。

## 一、四个对象

| 对象 | 路径 | 作用 |
| --- | --- | --- |
| 验证意图源 | `<story-dir>/validation-intents.json` | 主 agent 从冻结 R/F、Task 通道、AC 与定向质量检查编译的待验证项 |
| 验证计划 | `<story-dir>/validation-plan.json` | 脚本按执行键与风险边界组成的 `VAL-B-*`；是下一批怎么跑的唯一机器清单 |
| 批次收据 | `<story-dir>/validation-receipts.json` | 每次批量执行的逐 intent、逐 assertion 结果和调用计数；追加不覆盖 |
| 批次状态 | `<story-dir>/validation-status.json` | 当前代码下每个 intent / consumer 的 fresh、stale、failed、blocked、pending 或 passed，以及精确增量重跑清单 |

`alpha-tests.md` 仍是验收追溯的唯一账本，只引用 `VAL-B-*`、消费者、摘要和上述机器工件；不得把逐断言 JSON 复制进去。

## 二、什么时候编译

QA 基线确认并编译还原契约后、进入第一个 Task 的 Step ① 前，主 agent一次列全当前可知的验证意图：

- 每个还原 / 逻辑通道自己的 RED 与 GREEN 行；
- 每个需要浏览器实跑的 R/F/AC 行及其状态、视口、操作；
- 所改范围 test、typecheck、lint 等非行为定向检查；
- Phase C 已能从冻结范围预知的布局 / 功能场景。

实现中出现新状态或新缺口时增量追加 intent 并重编计划，不回头改冻结判据。代码修改后也重编：脚本会重新计算逐文件依赖哈希；旧收据按 `intent_fingerprint` 自动变成 stale，未命中的 intent 仍为 passed。

RED 与 GREEN 必须是不同因果边界：RED assertion 的 `pass` 表示“在改产品代码前按预期原因失败”，GREEN assertion 的 `pass` 表示“实现后满足冻结标准”。二者使用不同 `boundary` 或标 barrier，不能为了批量执行在同一次调用里先改状态、再把两边一起记通过。

```bash
python3 "<skill-dir>/scripts/manage_validation_batches.py" plan \
  --repo-root "<repo-root>" \
  --intents "<story-dir>/validation-intents.json" \
  --output "<story-dir>/validation-plan.json"
```

意图最小结构：

```json
{
  "schema_version": 1,
  "story": "<Story ID>",
  "intents": [
    {
      "id": "workbench-empty-1440",
      "kind": "browser",
      "boundary": "workbench-local-state",
      "barrier": false,
      "cleanup_required": false,
      "consumers": ["T1-r1/restore", "AC-1", "R5-1"],
      "assertions": ["empty-copy", "composer-disabled"],
      "depends_on": ["src/workbench.tsx", "src/workbench.css"],
      "execution": {
        "driver": "in-app-browser",
        "page": "/workbench",
        "fixture": {"name": "empty", "sha256": "<sha256>"},
        "reset_strategy": "reset-fixture-without-reconnect",
        "runtime": {"browser": "Chromium 140", "dpr": 1, "account": "qa"}
      },
      "scenario": {
        "name": "empty-1440",
        "viewport": {"width": 1440, "height": 900},
        "steps": ["reset fixture", "open workbench", "collect facts"]
      }
    }
  ]
}
```

`depends_on` 必须列仓库相对文件，脚本从当前工作区取 SHA-256；runtime 只放非秘密身份键，任何 token、cookie、密码或 credential 字段都会被拒绝。

`VAL-B-*` 的后缀是执行键的稳定短哈希，不是会随插入新批次而整体改号的流水序号。相同页面或命令执行边界在代码依赖变化、或新增兼容 intent 后保持同一 batch ID；fixture、runtime、boundary 或 barrier 变化才生成新 ID。

## 三、合批与强制 flush

批次大小由**兼容性与可归因性**决定，不再由 Impact 档位或“最多两个 Task”决定。Impact 只决定需要哪些验证，不决定相同验证必须重复几次。

### 命令批次

以下字段完全相同才合并：package、命令模板及顺序、toolchain、runtime、`boundary`。每个 intent 的 scope 取并集；命令 `argv` 中单个 `{scope}` 会展开成排序后的 scope 参数。没有 `{scope}` 的 package 级命令保持原样，只执行一次。

### 浏览器批次

以下字段完全相同才合并：driver、页面 / 路由、fixture、reset strategy、runtime、`boundary`。viewport、状态与操作序列留在批次内的 `scenarios[]`，不因它们不同而为每个断言另开会话。

以下情况必须给 intent 标 `barrier: true`，立即 flush 为单独批次：

- 公共 API、schema / migration、鉴权 / 权限或跨进程协议；
- 真实数据写入、外部时变状态或并发时序；真实写入 intent 还必须设 `cleanup_required: true`；
- 状态无法可靠复位；
- 合批后无法把失败定位回具体 intent / assertion；
- RED/GREEN 的因果关系会被另一个 intent 污染。

如果两个 Task 只是文件不同，但命令、页面、fixture、环境与风险边界相同，应合批；如果同一个 Task 横跨上述边界，也必须拆批。

## 四、浏览器批次怎么执行

浏览器批次的固定顺序：

1. 按 `validation-status.json / next_batches[]` 取一个 browser batch；只执行其中列出的 intent，不把已经 passed 的场景带回来；
2. 按执行起点记录连接并打开页面一次；同批次内靠 `reset_strategy` 复位，不重连、不反复新建临时页面；
3. 能由一次 `Runtime.evaluate` / 仓内 e2e runner 连续触发和采集的状态矩阵，一次注入执行，返回逐 scenario、逐 assertion 数组；必须使用真实用户事件的交互（如 IME、文件选择、拖拽）才拆成少量连续调用；
4. 视口切换、fixture reset 与截图沿计划顺序连续执行；截图只为 visual-required 或结论引用项生成；
5. 同一路径连续失败两次时停止逐调用碰运气：先检查定位器、reset 与环境；仍无法归因则拆批或记 blocked。

目标是“一次进入一个场景族、批量取回所有结果”，不是承诺任何驱动都能用一次物理 tool call 完成。每份收据仍记录实际 `browser_calls` 与 `retries`，让执行成本可审计。

## 五、结果必须逐项，不能只有总通过

批次执行后把实际结果写成临时 JSON，再由脚本追加收据：

```json
{
  "batch_id": "VAL-B-a1b2c3d4e5f6",
  "executed_at": "2026-08-16T18:00:00+08:00",
  "metrics": {"browser_calls": 3, "commands": 0, "retries": 0},
  "items": [
    {
      "intent_id": "workbench-empty-1440",
      "results": [
        {"assertion": "empty-copy", "status": "pass", "evidence": ["text=暂无消息"]},
        {"assertion": "composer-disabled", "status": "pass", "evidence": ["disabled=true"]}
      ]
    }
  ]
}
```

```bash
python3 "<skill-dir>/scripts/manage_validation_batches.py" record \
  --plan "<story-dir>/validation-plan.json" \
  --result "<临时目录>/VAL-B-a1b2c3d4e5f6-result.json" \
  --receipts "<story-dir>/validation-receipts.json"
```

脚本拒绝：空 items、只有总体 pass、漏 assertion、重复 assertion、没有 evidence 的结论、browser batch 的 `browser_calls=0`、command batch 的 `commands=0`。共享执行不等于共享结论；一个 Task 只有在映射给它的全部 assertion 都 fresh + passed 后才能完成 Step ④/⑥。

`cleanup_required: true` 的 browser intent 还必须在对应 result item 记录 `cleanup.status=cleaned|not-cleaned` 与非空 evidence（测试数据标识、清理动作，或无法清理的环境/原因）。脚本拒绝缺失清理披露的收据；`not-cleaned` 事实必须进入检视 known gaps 与最终 handoff，不能因 assertions 通过而隐去。

## 六、状态与精确增量重跑

每次编译计划或追加收据后运行：

```bash
python3 "<skill-dir>/scripts/manage_validation_batches.py" status \
  --plan "<story-dir>/validation-plan.json" \
  --receipts "<story-dir>/validation-receipts.json" \
  --output "<story-dir>/validation-status.json"
```

状态文件的 `next_batches[]` 已按当前 intent 过滤执行清单：

- 依赖文件变更只让命中它的 intent stale；
- 一个 assertion fail 只让其 intent 与 consumer failed；
- 同一批其他 passed intent 继续有效；
- 代码精确回退到曾通过的 intent fingerprint 时，复用最近一条完全匹配的旧结果；
- 补跑可只提交一个批次中的 stale / failed 子集，旧的未受影响结果继续保留；
- `ready: true` 才表示全部 consumer 的 assertion 新鲜且通过。

Phase B 进入 C、Phase D 收口都必须检查 `ready: true`；不得用 batch 总退出码、Task checkbox 或旧 `VAL-B-*` 文本收据替代。

## 七、遥测与初始实验阈值

每个 `VAL-B-*` 向 `<execution-telemetry>` 记录 kind、intents、consumers、assertions、commands / browser_calls、retries、passed / failed / blocked / stale / reused。Phase D 从收据与 status 机械汇总，不靠回忆估算。

先把下面三条作为**告警阈值，不是完成门禁**：

- 单路由、单 Task、三个视口的普通场景矩阵，整个实现与补证阶段浏览器调用目标不超过 25；
- prototype 已选定后，connect / open / recover 合计目标不超过 3；
- 同一路径失败两次仍继续逐调用尝试，必须在 telemetry 写明拆批或阻断理由。

积累至少三次真实 Story 后再决定是否把数值变成硬限制；当前硬约束只有批量计划、逐项结果、风险 flush 与精确重跑。
