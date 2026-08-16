# Phase C 共享证据契约

Phase C 的检视必须**判断独立**，不要求**采集重复**。主 agent 先把质量命令与浏览器场景的原始事实收进一个证据包；四个检视角色各自按自己的判据下结论，只补证据包覆盖不到或已经失效的场景。

## 一、证据纪元与代码指纹

一次 Phase C 使用一个 `evidence_epoch`。同一纪元允许容量感知的动态补位，不要求四份检视处于同一个墙钟并发批次；它们必须引用同一个有效代码指纹。

代码指纹至少包含：

- `<base-ref>`、当前 `HEAD`；
- 本 Story 改动文件的仓库相对路径与内容 SHA-256（含未跟踪文件），以及所有待提升 / 当前有效 scenario 的 `depends_on` 文件哈希；
- 由上述字段确定性计算的 `code_fingerprint`。

只记 `HEAD` 不合格：工作区与未跟踪文件可能还没提交；只列 diff 文件也不足以精确验证未改但被 scenario 依赖的公共文件。主 agent 把包写入 `<story-dir>/review-evidence.json`，机器细节只在这里保存，不复制进 `dev-review.md`。

## 二、最小结构

```json
{
  "schema_version": 1,
  "evidence_epoch": "review-1",
  "code": {
    "base_ref": "<ref>",
    "head": "<sha>",
    "files": [{"path": "src/view.tsx", "sha256": "<sha256>"}],
    "code_fingerprint": "<sha256>"
  },
  "quality_gate": {
    "code_fingerprint": "<sha256>",
    "commands": [
      {"name": "test", "command": "<实际命令>", "exit_code": 0, "duration_ms": 0, "failures": []}
    ]
  },
  "runtime": {
    "driver": "<具体档位与启动方式>",
    "url": "<目标 URL>",
    "browser": "<引擎与版本>",
    "dpr": 1,
    "font_fingerprint": "<值>",
    "account": "<非秘密身份键>",
    "role": "<角色>",
    "tenant": "<租户>",
    "api_mode": "<真实 API / mock 模式>"
  },
  "scenarios": [
    {
      "id": "BE-1",
      "consumers": ["review-layout", "self-test"],
      "page": "<页面与路由>",
      "fixture": {"name": "<名称>", "sha256": "<sha256>"},
      "viewport": {"width": 1200, "height": 800},
      "steps": ["<实际执行步骤>"],
      "observations": ["<原始文案、数值、网络请求或几何事实>"],
      "artifacts": ["<截图或结构化结果路径>"],
      "depends_on": ["src/view.tsx", "src/view.module.css"],
      "captured_dependency_hashes": {
        "src/view.tsx": "<sha256>",
        "src/view.module.css": "<sha256>"
      },
      "captured_runtime": {
        "driver": "<具体档位与启动方式>",
        "url": "<目标 URL>",
        "browser": "<引擎与版本>",
        "dpr": 1,
        "font_fingerprint": "<值>",
        "account": "<非秘密身份键>",
        "role": "<角色>",
        "tenant": "<租户>",
        "api_mode": "<真实 API / mock 模式>"
      },
      "captured_at_code_fingerprint": "<sha256>",
      "source": "phase-b / phase-c"
    }
  ]
}
```

证据包只保存**原始事实**，不保存 `通过 / 不通过` 或级别。否则后来的检视只是复述证据所有者的判断，不再独立。

## 三、Phase B 事实提升

Phase B Step ④ 已实际执行的浏览器 / 结构化渲染场景，不等 Phase C 再点一次。Step ⑥ 把这些**原始事实**追加到 `<story-dir>/phase-b-review-evidence.json`，每条必须包含上节 scenario 字段以及：

- `captured_dependency_hashes`：完整覆盖 `depends_on`，记录采集当时每个依赖文件的内容 SHA-256；
- `captured_runtime`：复制采集当时的非秘密 runtime 键；不能只依赖证据包顶部的当前 runtime，否则环境变化后旧场景会被误认成新环境事实；
- 与 Phase C 相同形态的 runtime、fixture、page、viewport、steps、observations、artifacts；
- 不含 `result`、`pass/fail`、finding、级别或结论。

Phase C 的候选全量门完成、页面状态稳定后，若该文件存在就先运行：

```bash
python3 "<skill-dir>/scripts/manage_review_pipeline.py" promote \
  --review-evidence "<review-evidence>" \
  --code-manifest "<临时代码指纹 JSON>" \
  --phase-b-scenarios "<story-dir>/phase-b-review-evidence.json" \
  --runtime "<临时运行时 JSON>" \
  --evidence-epoch "<evidence_epoch>"
```

脚本只提升 runtime 键仍一致、且全部逐文件依赖哈希仍匹配的场景。全局代码指纹因无关文件变化，不会让精确依赖仍匹配的场景失效；一个依赖变化，也只把命中它的场景列为 stale。随后主 agent 只执行 `promoted / reused` 仍未覆盖的场景缺口。文件不存在代表 Phase B 没有可提升场景，记 telemetry `skip` 后照常规划 Phase C，不把缺少可选工件判成阻断。

## 四、场景规划与所有权

1. 主 agent 从冻结的 R/F 行与两份浏览器检视范围取并集，先列场景，再执行；相同页面、fixture、viewport、步骤合并为一个 `BE-n`。
2. 会重载页面或清空内存态的质量命令先跑，浏览器场景后采集。不得在两者之间反复生成同一个临时页面。
3. 主 agent 是证据包所有者；布局检视与功能自测试是独立判定者。两者收到包后先做新鲜度与覆盖检查，**有效场景不得重跑**。
4. 检视角色只有在下列情况才补跑：缺目标行需要的场景；原始事实不足以下结论；证据已按第五节失效。补跑后把完整原始场景记录放进结构化结果的 `evidence_added`，由聚合脚本校验、分配 `BE-n` 并入同一证据包。

检视独立性的判据是「各自回到冻结基线与本角色规则作判断」，不是「各自重新点击一次页面」。

## 五、新鲜度与精确失效

一个场景可复用，当且仅当以下字段全相同：

- 它的 `depends_on` 文件内容哈希；
- fixture 名称与内容哈希；
- 页面 / 路由、viewport、DPR、浏览器引擎与版本、字体指纹；
- 会影响观察结果的账号、角色、租户与 API/mock 模式。

代码变化后按依赖交集失效：

| 变化 | 失效范围 |
| --- | --- |
| 仅某页面私有文件 | `depends_on` 命中该文件的场景 |
| 公共组件、公共样式、路由壳或全局状态 | 引用它的全部下游场景 |
| fixture / 账号 / API 模式 | 使用该输入的场景 |
| 只改文档或与运行时无关的测试说明 | 浏览器场景不失效；质量门按命令输入另判 |

拿不准依赖是否覆盖时扩大 `depends_on` 或让受影响场景失效，**不得把整个证据包无条件作废**。未受影响的场景继续复用；新代码指纹下重跑过的场景更新自己的 `captured_at_code_fingerprint`。

## 六、质量门梯度

- Phase 0 的全量命令只负责冻结起点失败集合。
- Phase B 与 Phase D 修复进行中只跑能覆盖当前改动的定向测试、所改范围 typecheck / lint 与对应契约；不为每次小修改跑全量。
- Phase C 候选代码稳定后，主 agent跑一次全量门并写入 `quality_gate`，然后采集浏览器证据。检视角色读取这份原始命令结果，不重复执行同一套全量命令。
- 阻断修复改变代码指纹后，修复期仍只跑定向检查；阻断清零时**最多补一次**最终全量门。若代码指纹自 Phase C 全量门后未变，直接复用，不再补跑。
- 最终全量门改变或重载页面状态时，先完成它，再只重采第五节判定失效的浏览器场景。

## 七、Impact S 的呈现预算

Impact S 不删判据，只压缩重复呈现：

- `restore-report-*.json`、本证据包等机器工件继续完整保存，human-facing 工件只引用路径、指纹与三色/命令摘要；
- 四份检视仍逐维度判断，但统一按 [结构化检视结果契约](./review-result-contract.md) 回传；无发现维度只有一条 coverage 记录，只有发现、Open Question、Deferred 候选展开；
- `dev-review.md` 不复制浏览器步骤、命令输出或逐规则机器报告。

M / L 扩大实际检视范围，但仍沿用同一结构化结果契约，不恢复四份长 Markdown。任何档位都不压缩 QA 基线的确认对象、AC ↔ 证据映射、阻断发现或最终 handoff。
