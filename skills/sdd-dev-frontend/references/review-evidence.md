# Phase C 共享证据契约

Phase C 的检视必须**判断独立**，不要求**采集重复**。主 agent 先把质量命令与浏览器场景的原始事实收进一个证据包；四个检视角色各自按自己的判据下结论，只补证据包覆盖不到或已经失效的场景。

## 一、证据纪元与代码指纹

一次 Phase C 使用一个 `evidence_epoch`。同一纪元允许容量感知的多波派发，不要求四份检视处于同一个墙钟并发批次；它们必须引用同一个有效代码指纹。

代码指纹至少包含：

- `<base-ref>`、当前 `HEAD`；
- 本 Story 改动文件的仓库相对路径与内容 SHA-256（含未跟踪文件）；
- 由上述字段确定性计算的 `code_fingerprint`。

只记 `HEAD` 不合格：工作区与未跟踪文件可能还没提交。主 agent 把包写入 `<story-dir>/review-evidence.json`，机器细节只在这里保存，不复制进 `dev-review.md`。

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
    "font_fingerprint": "<值>"
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
      "captured_at_code_fingerprint": "<sha256>"
    }
  ]
}
```

证据包只保存**原始事实**，不保存 `通过 / 不通过` 或级别。否则后来的检视只是复述证据所有者的判断，不再独立。

## 三、场景规划与所有权

1. 主 agent 从冻结的 R/F 行与两份浏览器检视范围取并集，先列场景，再执行；相同页面、fixture、viewport、步骤合并为一个 `BE-n`。
2. 会重载页面或清空内存态的质量命令先跑，浏览器场景后采集。不得在两者之间反复生成同一个临时页面。
3. 主 agent 是证据包所有者；布局检视与功能自测试是独立判定者。两者收到包后先做新鲜度与覆盖检查，**有效场景不得重跑**。
4. 检视角色只有在下列情况才补跑：缺目标行需要的场景；原始事实不足以下结论；证据已按第四节失效。补跑后回传完整场景记录，由主 agent并入同一证据包。

检视独立性的判据是「各自回到冻结基线与本角色规则作判断」，不是「各自重新点击一次页面」。

## 四、新鲜度与精确失效

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

## 五、质量门梯度

- Phase 0 的全量命令只负责冻结起点失败集合。
- Phase B 与 Phase D 修复进行中只跑能覆盖当前改动的定向测试、所改范围 typecheck / lint 与对应契约；不为每次小修改跑全量。
- Phase C 候选代码稳定后，主 agent跑一次全量门并写入 `quality_gate`，然后采集浏览器证据。检视角色读取这份原始命令结果，不重复执行同一套全量命令。
- 阻断修复改变代码指纹后，修复期仍只跑定向检查；阻断清零时**最多补一次**最终全量门。若代码指纹自 Phase C 全量门后未变，直接复用，不再补跑。
- 最终全量门改变或重载页面状态时，先完成它，再只重采第四节判定失效的浏览器场景。

## 六、Impact S 的呈现预算

Impact S 不删判据，只压缩重复呈现：

- `restore-report-*.json`、本证据包等机器工件继续完整保存，human-facing 工件只引用路径、指纹与三色/命令摘要；
- 四份检视仍逐维度判断，但无发现维度只回一行覆盖矩阵，只有发现、Open Question、Deferred 候选展开证据表；
- `dev-review.md` 不复制浏览器步骤、命令输出或逐规则机器报告。

M / L 沿用各提示词的完整逐维度报告。任何档位都不压缩 QA 基线的确认对象、AC ↔ 证据映射、阻断发现或最终 handoff。
