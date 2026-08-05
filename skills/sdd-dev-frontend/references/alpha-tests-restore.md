# `alpha-tests.md` 还原证据扩容

本文描述 `sdd-dev-frontend` 阶段对上游 `sdd-task` 产出的 `alpha-tests.md` 做的两处扩容：**新增一节「还原证据记录」**，**扩展既有的「AC ↔ 证据映射」节**。

**这是扩容既有账本，不是新开一本账。** `alpha-tests.md` 继续是唯一证据账本；冻结契约、机器报告和视觉文件是账本引用的证据工件。账本只记录它们的指纹、路径与摘要，不复制第二份规则表或报告。

V2 还原证据使用冻结机器契约与选择性截图；工件格式见 [restore-contract.md](./restore-contract.md)。

## 一、新增「还原证据记录」

### 1.1 写入位置与时机

- 放在既有 L4 / L3 证据记录之后、「AC ↔ 证据映射」之前。
- 每个还原轮一条记录，编号固定为 `R-<Task 编号>-<轮次>`。
- 在还原轮 Step ⑥ 一次写入。Step ① 的 RED 报告与 Step ④ 的 GREEN 报告都已存在后才落账。
- 若初次报告全部 GREEN，或初次只有 YELLOW、补证后确认无偏差而取消该轮，仍写一条“取消记录”，但不得伪造 RED 报告。

### 1.2 V2 记录结构

每条记录只有四块：**记录头 → RED 报告引用 → GREEN 复核 → 可选视觉证据**。机器报告是完整事实来源，账本不抄逐条结果。

#### 记录头

| 字段 | 填法 |
| --- | --- |
| 记录编号 | `R-<Task 编号>-<轮次>` |
| Task | `<tasks.md 中的 Task 编号与标题>` |
| 区块 | `<block-index.md 中逐字一致的区块名>` |
| 原型事实 | `<design-spec-dir>/design-facts.json` · `<prototype_fingerprint>` |
| 基线 | `<story-dir>/dev-baseline.md` · `<baseline_sha256>` |
| 冻结契约 | `<story-dir>/restore-contract.json` · `<contract_sha256>` |
| 实现适配 | `<story-dir>/restore-adapter.json` |
| 目标视口 | `<宽 × 高 / DPR>` |

`区块`、原型文件与锚点来自抽取层产物 `<design-spec-dir>/block-index.md` 与 `<design-spec-dir>/blocks/<区块名>.md`。锚点主体是 class 结构；行号只允许作为格式化文档的附带坐标。单行导出件不得写 `L1–L1` 冒充范围。

#### RED 报告引用

| 字段 | 填法 |
| --- | --- |
| 报告 | `<story-dir>/restore-report-red.json` |
| 报告指纹 | `<report_sha256>` |
| 汇总 | `RED <N> / YELLOW <N> / GREEN <N>` |
| RED 规则 | `<rule_id 列表；完整期望/实际/出处/locator 在报告中>` |
| YELLOW 补证 | `<无；或 rule_id → required_evidence 与补证结果>` |

进入实现的还原轮必须至少有一条 RED。初次只有 YELLOW 时先补页面、状态 fixture 或结构化采集；只有发现明确偏差并重跑成 RED 后才能实现。初次全 GREEN 或补证后无偏差时填“本轮取消”，不能把 YELLOW 当作 RED 或 GREEN。

#### GREEN 复核

| 字段 | 填法 |
| --- | --- |
| 报告 | `<story-dir>/restore-report-green.json` |
| 报告指纹 | `<report_sha256>` |
| 汇总 | `RED 0 / YELLOW 0 / GREEN <总规则数>` |
| 契约一致性 | `RED / GREEN 报告的 contract_sha256 相同` |
| 回归 | `<test / typecheck / lint / build 摘要，与 DEMAND-2 起点相比无退化>` |
| 处置 | `<本轮 RED rule_id 均已验证通过；或逐条命中冻结豁免>` |

合法 GREEN 只有两种：

1. 所有规则的 required layers 均通过；
2. 未实际匹配的规则逐条命中 `restore-contract.json` 中已冻结的豁免。

有任一 RED、任一未解决 YELLOW、契约或基线哈希不一致、回归变差，都不是 GREEN。

#### 可选视觉证据

没有 visual YELLOW 时写：

```text
视觉证据：不适用。机器可检项目由 static / render 层完成，本轮未截图。
```

只有结构化检查无法可靠判断阴影观感、字体栅格、图片裁切或复杂叠层时才填：

| 规则 | 原型视觉缓存 | 实现截图 | 环境 | 结论 |
| --- | --- | --- | --- | --- |
| `<rule_id>` | `<cache_fingerprint>` · `<design-spec-dir>/visual-baseline/<fingerprint>/prototype.png` | `<story-dir>/evidence/<Task>-r<轮次>/<rule_id>-impl.png` | `<视口 / DPR / 浏览器 / 字体指纹>` | `<转明确 RED；或验证 GREEN>` |

- 原型截图来自 Requirement 级只读缓存；命中复用，失配新建，不覆盖旧版本。
- 实现截图仍放 Story 的 `evidence/`。
- 机器可检项目禁止为了留痕额外截图。
- 视觉观察必须进入 `visual-results.json` 并重跑报告；图片本身不能把 YELLOW 直接写成 GREEN。

### 1.3 完整示例

```markdown
### R-T3-1 · T3 订单列表区还原

| 字段 | 值 |
| --- | --- |
| 区块 | 订单列表区 |
| 原型事实 | `<design-spec-dir>/design-facts.json` · `pf-7b0…` |
| 基线 | `<story-dir>/dev-baseline.md` · `b7d…` |
| 冻结契约 | `<story-dir>/restore-contract.json` · `c41…` |
| 实现适配 | `<story-dir>/restore-adapter.json` |
| 目标视口 | 1440 × 900 / DPR 2 |

RED 报告：`<story-dir>/restore-report-red.json` · `9af…`
汇总：RED 2 / YELLOW 0 / GREEN 4；RED 规则：R2-1、R3-2。

GREEN 报告：`<story-dir>/restore-report-green.json` · `e23…`
汇总：RED 0 / YELLOW 0 / GREEN 6；契约哈希仍为 `c41…`。
回归：test / typecheck / lint / build 与 DEMAND-2 起点相同。

视觉证据：不适用。机器可检项目由 static / render 层完成，本轮未截图。
```

### 1.4 能力降级的记法

| 环境能力 | 可执行范围 | 账本必须写明 |
| --- | --- | --- |
| 页面可用、截图不可用 | static + render 正常执行；visual 保持 YELLOW | `无截图能力；机器报告仍覆盖可检项；visual 未验证` |
| 页面不可用 | 只执行 static；render / visual 保持 YELLOW | `无页面能力；未验证结构、计算样式、几何和实际状态` |
| 状态 fixture 缺失 | 其他规则正常；对应 R5 为 YELLOW | 缺失 fixture 与 `required_evidence` |

降级不能通过源码对照把 render-required 规则写成 GREEN，也不能留下并不存在的图片路径。最终报告仍有 YELLOW 时还原轮不能完成。

### 1.5 旧 Story 兼容

没有 `restore-contract.json` 的既有 Story 继续读取旧版四块证据：

1. 记录头；
2. RED 差异清单；
3. RED 双方截图；
4. GREEN 复核与实现截图。

不要求迁移或重写历史账本。可用以下命令判定证据格式：

```bash
python3 <skill-dir>/scripts/verify_restore_contract.py evidence-format \
  --alpha-tests <story-dir>/alpha-tests.md
```

输出为 `legacy-screenshot-v1` 时只能按旧流程读取；新 Story 不得选择旧格式绕过冻结契约和 YELLOW 语义。

## 二、扩展「AC ↔ 证据映射」

既有列全部保留。本次只增加：

- `证据类型` 允许值新增 `还原`；
- `证据链` 对还原类填写记录编号 `R-<Task 编号>-<轮次>`，不直接填报告或截图路径；
- `状态` 只允许 `GREEN` 或 `Deferred`。

| AC 锚点 | 覆盖 Task | 证据类型 | 证据链 | 状态 |
| --- | --- | --- | --- | --- |
| AC-1.1 | T3 | 还原 | R-T3-1 | GREEN |
| AC-1.2 | T3, T4 | 还原, L4 | R-T3-1；`UT-order-filter-reset-01` | GREEN |
| AC-2.3 | T6 | L3 | `IT-order-export-01` | Deferred |

状态口径：

| 值 | 含义 |
| --- | --- |
| `GREEN` | 该 AC 的全部证据链已闭环；还原记录的最终机器报告无 RED、无 YELLOW |
| `Deferred` | 仅因不可控外部条件延期，且已写入 Deferred AC 表 |

既不到 GREEN、又不满足 Deferred 条件的 AC 是阻断项，不能进入映射表冒充完成。

## 三、Deferred AC 表

沿用上游 `alpha-tests.md` 的 Deferred AC 结构，不新增第二张表：

| AC 锚点 | 延期原因 | 补证触发条件 |
| --- | --- | --- |
| AC-2.3 | 上游未声明对接模式，导出接口不可用 | 接口可用后补一轮 L3 集成证据，状态改为 `GREEN` |

还原规则不能只因没有截图能力而 Deferred：机器可检项继续执行，visual 项保持 YELLOW；要么补齐能力，要么由用户冻结明确豁免。

## 四、交付前自检

- [ ] 每个还原轮恰有一条 `R-<Task>-<轮次>` 记录
- [ ] 记录引用冻结契约、RED / GREEN 报告的路径与指纹
- [ ] RED / GREEN 报告使用同一 contract hash，且 baseline hash 校验通过
- [ ] GREEN 汇总为 RED 0、YELLOW 0
- [ ] 账本没有复制第二份逐规则报告
- [ ] 没有 visual YELLOW 的轮次未截图
- [ ] 有视觉补证时同时记录缓存指纹、实现截图和同环境信息
- [ ] 页面或截图降级没有伪装成视觉 GREEN
- [ ] AC 映射引用记录编号，不引用散落文件
- [ ] 旧 Story 仍可识别为 `legacy-screenshot-v1`，没有被强制迁移
