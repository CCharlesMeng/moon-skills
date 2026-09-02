# 共享证据契约

适用检视必须**判断独立**，不要求**采集重复**。`review-evidence.json` 是验证组合、浏览器与命令原始事实的唯一共享包：Phase B 写实际因果场景，Phase C 按最终组合补适用命令与场景；只有被触发的检视角色作判断。

本文件的第五节「新鲜度与精确失效」同时是 Phase B 复用同一次执行的判据，两处不另立第二套定义。

## 一、证据纪元与代码指纹

一次 Phase C 使用一个 `evidence_epoch`。适用角色可动态补位，不要求处于同一个墙钟批次；它们必须引用同一个有效候选代码状态。

代码指纹至少包含：

- `<base-ref>`、当前 `HEAD`；
- 本 Story 改动文件的仓库相对路径与内容 SHA-256（含未跟踪文件），以及所有待提升 / 当前有效 scenario 的 `depends_on` 文件哈希；
- 由上述字段确定性计算的 `code_fingerprint`。

只记 `HEAD` 不合格：工作区与未跟踪文件可能还没提交；只列 diff 文件也不足以精确验证未改但被 scenario 依赖的公共文件。主 agent 把包写入 `<story-dir>/review-evidence.json`，机器细节只在这里保存，不复制进 `acceptance.md`。

## 二、最小结构

```json
{
  "schema_version": 1,
  "evidence_epoch": "review-1",
  "validation_portfolio": {
    "risk_triggers": ["visual"],
    "portfolio_narrowed": [],
    "modules": ["causal", "render", "targeted-quality"],
    "review_roles": ["review-layout"],
    "review_dimensions": {"review-layout": ["L2", "L3"]},
    "claims": [{"id": "AC-1", "modules": ["causal", "render"], "status": "UNVERIFIED"}]
  },
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

## 三、Phase B 场景就地入包

Phase B Step ④ 已实际执行的浏览器 / 结构化渲染场景，不等 Phase C 再点一次，**也不另存一份「可提升事实」**。Step ⑥ 直接把原始事实写进 `review-evidence.json` 的 `scenarios[]`，标 `source: "phase-b"`，每条必须含上节全部 scenario 字段以及：

- `captured_dependency_hashes`：完整覆盖 `depends_on`，记录采集当时每个依赖文件的内容 SHA-256；
- `captured_runtime`：复制采集当时的非秘密 runtime 键；不能只依赖证据包顶部的当前 runtime，否则环境变化后旧场景会被误认成新环境事实；
- `captured_at_code_fingerprint`：采集当时的代码指纹；
- 不含 `result`、`pass/fail`、finding、级别或结论。

**一份工件、一套字段、一套新鲜度键**：此前的两文件加提升流程（`phase-b-review-evidence.json` + `promote` 子命令）只是把同一批字段搬一次家，搬运本身不产生任何判据。取消它之后：

- Phase B 写入时就按第五节的键做幂等覆盖，同一键不写第二条；
- Phase C 命令模块完成、页面状态稳定后，主 agent 做一次**新鲜度核对**：仍匹配的 Phase B 场景继续有效，失效的只按验证组合需要重采；
- 全局代码指纹因无关文件变化，不让精确依赖仍匹配的场景失效；一个依赖变化，也只让命中它的场景失效；
- Phase B 没有这类场景时 `scenarios[]` 里就没有 `source: "phase-b"` 的条目，这是正常情形，不是缺产物。

Phase B 的行为结论（RED/GREEN、逐项失败集合）仍只在 `alpha-tests.md` 的证据链里；**证据包永远不保存 pass / fail**。

## 四、场景规划与所有权

1. 主 agent 从验证组合的 `render` / `story` 声明与适用浏览器检视范围取并集，减去仍新鲜场景，剩下的才采；相同页面、fixture、runtime 与 reset 边界只连接/打开一次。
2. 会重载页面或清空内存态的质量命令先跑，浏览器场景后采集；不得在两者之间反复生成同一个临时页面。
3. 主 agent 是证据包所有者；被触发的布局检视与功能自测试是独立判定者。收到包后先核新鲜度与覆盖，**有效场景不得重跑**。
4. 检视角色只有在下列情况才补跑：缺目标行需要的场景；原始事实不足以下结论；证据已按第五节失效。角色先收齐自己的全部缺口，按页面 / fixture / runtime / reset 边界组成批次后再启动浏览器；不得发现一行就调用一次。补跑后把完整原始场景记录放进结构化结果的 `evidence_added`，由聚合脚本校验、分配 `BE-n` 并入同一证据包。

检视独立性的判据是「各自回到冻结基线与本角色规则作判断」，不是「各自重新点击一次页面」。

telemetry 开启时，每次连接、注入与截图各记一条 `browser_connect` / `browser_inject` / `browser_capture`（见 [preflight-and-telemetry.md](../preflight-and-telemetry.md)）。浏览器是这条流程最贵的一笔，而它此前唯一的次数统计来自事故复盘而不是流程自身——不记就永远只能靠推导判断该削哪一边。

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
| 只改文档或与运行时无关的测试说明 | 浏览器场景不失效；`quality_gate` 中已选命令按自己的输入另判 |

拿不准依赖是否覆盖时扩大 `depends_on` 或让受影响场景失效，**不得把整个证据包无条件作废**。未受影响的场景继续复用；新代码指纹下重跑过的场景更新自己的 `captured_at_code_fingerprint`。

## 六、命令证据

各 Phase 该跑多宽只定义在 [validation-policy.md 的执行时机](../validation-policy.md#五执行时机)，本文件不复制一份分阶段清单。

这里只定义命令的**记录形状**：每条命令保存完整 command、scope、toolchain/runtime 与相关代码状态；相同键复用，变化时只失效该命令。

## 七、呈现预算

- 机器工件完整保存，human-facing 工件只引用路径、证据 ID 与摘要。
- 适用检视逐维度判断；无发现维度只有 coverage，只有发现、Open Question 与 Deferred 候选展开。
- 未触发模块不留空表；`acceptance.md` 不复制浏览器步骤、命令输出或逐规则报告。
- AC ↔ 证据映射、`UNVERIFIED` / `DEFERRED`、确证阻断与 handoff 不压缩。
