# 差异清单模板

还原轮 Step ① / ② 的**机器报告人类摘要**。机器事实的单一来源是同轮 `restore-report-red.json` / `restore-report-green.json`；本清单不重新判定、不复制完整报告、不另开证据账。

差异清单以冻结外部契约的机器报告为准，截图只补机器盲区；JSON 格式见 [restore-contract.md](./restore-contract.md)。

## 一、状态语义

| 状态 | 含义 | 人类摘要怎么写 |
| --- | --- | --- |
| RED | 冻结契约已有明确反例 | 列期望、实际、契约出处、实现 locator 与失败原因 |
| YELLOW | 暂时无法可靠判定 | 列原因与 `required_evidence`；不能改写成轻微偏差或基本通过 |
| GREEN | 规则已验证或命中冻结豁免 | 摘要只写数量；需定位时引用报告规则 id |

汇总固定：有 RED 即 RED；无 RED 但有 YELLOW 即 YELLOW；全部规则 GREEN 才 GREEN。

## 二、清单头

| 字段 | 值 |
| --- | --- |
| 记录编号 | `R-<Task 编号>-<轮次>` |
| Task / 区块 | `<tasks.md 标题>` / `<block-index.md 区块名>` |
| 契约 | `<story-dir>/restore-contract.json` · `<contract_sha256>` |
| RED 报告 | `<story-dir>/restore-report-red.json` · `<report_sha256>` |
| 实现 adapter | `<story-dir>/restore-adapter.json` |
| 原型事实 | `<design-spec-dir>/design-facts.json` · `<prototype_fingerprint>` |

区块名逐字沿用切分表。锚点主体仍是 class 结构；格式化档可附 `L起–L止` 引用坐标，单行档写 `无行号`，不得编 `L1–L1`。

## 三、报告摘要

| 汇总 | RED | YELLOW | GREEN | 总数 |
| --- | --- | --- | --- | --- |
| `restore-report-red.json` | `<N>` | `<N>` | `<N>` | `<N>` |

### RED

只抄报告中的 RED；编号直接用 `rule_id`，不另造 `D-Rn-n`。

| 规则 | 维度 | 判定对象 | 期望 | 实际 | 契约出处 | 实现定位 | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R3-1` | R3 | `<区块 / 元素 / 属性>` | `<expected>` | `<actual>` | `<baseline_id + design_fact_source>` | `<locator_used；未命中时列 adapter locators>` | `<reasons>` |

RED 行缺以下任一项即不合格，不得进入 Step ③：

- 期望值；
- 实际值；
- `baseline_id` 与 `design_fact_source`；
- 实现定位；
- 明确失败原因。

### YELLOW

| 规则 | 维度 | 判定对象 | 无法判定原因 | 要求的补证 | 补证状态 |
| --- | --- | --- | --- | --- | --- |
| `R5-1` | R5 | `<区块 / 状态>` | `<reasons>` | `<required_evidence>` | 待补 / 已补，待重跑 |

YELLOW 处理顺序固定：

1. 补页面能力；
2. 补状态触发或 fixture；
3. 重跑无图片结构化采集；
4. 仍无法判定、且契约要求 visual 层时才查原型视觉缓存并截实现侧。

无法安全表达容差时保持 YELLOW，不得自行放宽到一个“看起来合理”的范围。

## 四、视觉补证（可选）

没有 visual YELLOW 时整节写：

```text
不适用：本轮机器可检项目全部由 static / render 层判定，未截图。
```

存在 visual YELLOW 时逐条记录：

| 规则 | 原型缓存指纹与路径 | 实现截图 | 同视口环境 | 观察结果 |
| --- | --- | --- | --- | --- |
| `<rule_id>` | `<cache_fingerprint>` · `<design-spec-dir>/visual-baseline/<fingerprint>/prototype.png` | `<story-dir>/evidence/<Task>-r<轮次>/<rule_id>-impl.png` | `<视口 / DPR / 浏览器 / 字体指纹>` | 明确偏差 / 无偏差 |

- 缓存命中只读复用；失配创建新指纹目录，不覆盖旧版本。
- 明确偏差写进 `visual-results.json` 为 `red` 后重跑报告；无偏差写 `green` 后重跑。
- 截图必须同区块、同视口、同 DPR、同浏览器环境。只写“观感不同”不成立，必须点名阴影、栅格、裁切或叠层的具体观察对象。
- 机器可检规则禁止为了“留证”补截图。

## 五、GREEN 复核

Step ④ 重跑同一契约后填写：

| 字段 | 值 |
| --- | --- |
| GREEN 报告 | `<story-dir>/restore-report-green.json` · `<report_sha256>` |
| 契约哈希 | `<与 RED 完全相同的 contract_sha256>` |
| 汇总 | RED 0 / YELLOW 0 / GREEN `<总规则数>` |
| 回归 | test / typecheck / lint / build 与 `DEMAND-2` 起点相同或更好 |

合法 GREEN 只有：

1. 全部 required layers 已验证；
2. 未实际匹配的规则逐条命中契约内已冻结豁免。

任何 RED、任何未解决 YELLOW、契约哈希变化、基线哈希变化、回归变差，都不是 GREEN。

## 六、特殊分支

| 初次报告 | 处理 |
| --- | --- |
| 全部 GREEN | 取消该还原轮，记录“冻结契约初次已满足” |
| 只有 YELLOW | 先补证；发现明确偏差才转 RED 进入实现，无偏差则取消还原轮 |
| 页面不可用 | static 支持项照常；render / visual 规则保持 YELLOW |
| 无截图能力 | static / render 不受影响；visual 规则保持 YELLOW |
| 无 `restore-contract.json` 的旧 Story | 继续旧截图证据流程；不迁移历史证据 |

## 七、落账映射

Step ⑥ 只把以下摘要写进 `alpha-tests.md`：

- 记录编号、Task、区块；
- 契约哈希；
- RED / GREEN 报告路径、指纹、三色摘要；
- 视觉缓存指纹与路径（如有）；
- 实现截图（如有）；
- 回归摘要。

完整 RED / YELLOW 行不复制进账本。`alpha-tests.md` 是唯一证据账本；机器报告是被它引用的证据工件。

## 八、交付前自检

- [ ] 契约与 `dev-baseline.md` 哈希校验通过
- [ ] 摘要数字与报告 `summary` 逐项一致
- [ ] RED 每条都有期望、实际、契约出处、实现定位、原因
- [ ] YELLOW 每条都有原因与要求的补证；没有被写成 GREEN
- [ ] static 通过没有替代 render-required 的 GREEN
- [ ] R6 没有用纯源码检查判 GREEN
- [ ] 没有 visual YELLOW 时未截图
- [ ] 有视觉补证时缓存键六要素齐全，命中只读、失配未覆盖旧版本
- [ ] GREEN 报告与 RED 报告引用同一契约哈希
- [ ] `alpha-tests.md` 只记指纹、路径、摘要与可选截图，没有复制第二本报告
