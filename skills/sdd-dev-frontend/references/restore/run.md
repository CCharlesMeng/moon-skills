# 还原契约：怎么跑

本文件是 Phase B 还原轮与 Phase C 重跑时的执行契约——**证据这一侧**。规则字段、`check_mode` 语义与 adapter 形状在 [contract.md](./contract.md)，编译与 `validate` 也在那里。

跑的对象永远是已冻结的同一份 `restore-contract.json`：RED 与 GREEN 之间契约、adapter 和采集方式都不变，变的只有实现。

## 一、执行

### 1. 静态预检

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" static \
  --baseline <story-dir>/dev-baseline.md \
  --contract <story-dir>/restore-contract.json \
  --adapter <story-dir>/restore-adapter.json \
  --repo-root <repo-root> \
  --out <临时目录>/static-results.json
```

### 2. 结构化渲染

实际打开页面、进入 `state_scenario`，设置：

```js
window.__SDD_RESTORE_INPUT__ = {
  contract: RESTORE_CONTRACT,
  adapter: RESTORE_ADAPTER,
  fixture_status: {"R5-1": "ready"}
};
```

然后注入 `<skill-dir>/scripts/collect_restore_facts.js`，把返回 JSON 保存为 `render-results.json`。页面无法启动时如实写：

```json
{
  "contract_sha256": "<restore-contract.json 中的值>",
  "page_available": false,
  "reason": "dev server unavailable",
  "rules": {}
}
```

**契约跨页面时按页面各注入一次，`--render-results` 重复传。** 采集脚本是单 DOM 的：一次注入遍历契约里全部 render 规则，属于其他页面的那些会拿到 `no implementation locator matched`，而报告把它算成 RED。所以单次注入配多页契约，GREEN 相里必然出现一批**和真偏差长得完全一样的假 RED**——报告写「定位不到」，与「选择器真写错了」在输出上无法区分，接着就会走「修 3 次 → 打断用户 → 补豁免」那条路，把工具缺口写进冻结基线。

脚本按 `rule_id` 合并：**任何一份给出可用状态就采信它**，其余份的「定位不到」是它不在那一页的正常表现。全部份都报错才判 RED，所以真正的定位断裂不会被合并拼没。某条规则在每一份里都缺席时，报告直接说「都没有覆盖本规则」，提示补该页面的注入而不是去改实现。

### 3. 报告

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" report \
  --phase red \
  --baseline <story-dir>/dev-baseline.md \
  --contract <story-dir>/restore-contract.json \
  --adapter <story-dir>/restore-adapter.json \
  --static-results <临时目录>/static-results.json \
  --render-results <临时目录>/render-results.json \
  --visual-results <临时目录>/visual-results.json \
  --out <story-dir>/restore-report-red.json
```

跨页时把 `--render-results` 按页面重复传（顺序不影响结论）：

```bash
  --render-results <临时目录>/render-results-<页面A>.json \
  --render-results <临时目录>/render-results-<页面B>.json \
```

GREEN 阶段只改 `--phase green` 与输出路径，契约、adapter 和采集方式保持相同——**包括注入了哪几个页面**。GREEN 相少注入一页会让那一页的规则从「已绿」变成 RED。

Phase C 组合含 `review-restore` 时，按最终 diff 用 `--phase green` 重跑**全部已冻结区块**，报告写 `<story-dir>/restore-report-review.json`。

### 4. 退出码

| 码 | 含义 | 动作 |
| --- | --- | --- |
| `0` | 报告已写出且无需阻断。RED 阶段出现 RED 是预期证据，仍返回 0 | 照常进 Step ② |
| `3` | `--phase green` 下 `overall` 不是 `green` | 不得当成完成；按状态语义处理 RED / YELLOW |
| `5` | 存在 `suspected-tool-equivalence`，两个 phase 都阻断 | 走硬门禁 16：补比对器映射或上报工具缺口，**不修实现、不补豁免** |

退出码 `5` 先于 `3` 判定——工具缺口没排除前，`overall` 是什么都不可信。

## 二、`suspected-tool-equivalence`：工具缺口不是还原偏差

[contract.md 的 CSS 序列化等价](./contract.md#css-序列化等价numeric-非数值叶子与-token--state_selector-针)是一份枚举，枚举永远会有下一个未覆盖形态。这类 RED 的危险不在于它是红的，而在于它和真偏差走同一条升级路径：修 3 次不成 → 打断用户 → 补一条豁免。实证是区域流水地图 Story 的 `EX-2`–`EX-5`——四条工具债被写成了冻结基线里「允许与设计稿不一致」的永久记录。

所以比对器另带一个**不依赖枚举**的信号：严格比对失败时，再用一次故意过宽的规范化（在已有归一化之上抹掉 token 顺序、分隔符与 `0` 值单位）。过宽形态一致就把该条标成 `reason_class: "suspected-tool-equivalence"`，写进报告顶层 `tool_equivalence_suspects[]`，`report` 以**退出码 5** 阻断（先于 `--phase green` 的退出码 3）。

| 命中后不许做 | 只能做 |
| --- | --- |
| 改实现去迎合字符串 | 把该形态补进 `verify_restore_contract.py` 的 normalize / canonicalize 函数族与 `collect_restore_facts.js` 的同源别名表后重跑同一契约；补不了时按 P7 上报工具缺口 |
| 为它新增豁免（**硬门禁 16**） | 补不了或形态存疑时按 P7 上报为工具等价缺口，附 `rule_id` 与两侧原值 |
| 把它算进「同一报错修 3 次」的计数 | 补完归一化后重跑同一契约；两端映射必须同步改 |

**过宽规范化只用于怀疑，永远不进判定通道**——它会把 `12px 8px` 与 `8px 12px` 拉平，作为通过判据就会漏掉真偏差。因此它命中时的结论是「这条要人看一眼工具」，不是「这条通过了」。

## 三、状态语义

| 单条状态 | 必含 |
| --- | --- |
| `red` | 期望值、实际值、契约出处、实现定位、失败原因 |
| `yellow` | 无法判定原因、要求的补证方式 |
| `green` | 已验证层清单，或命中的冻结豁免 |

汇总：有 RED 即 RED；无 RED 但有 YELLOW 即 YELLOW；全部规则 GREEN 才 GREEN。页面不可用时 render-required 规则为 YELLOW；页面可用但结构化采集已经尝试并报错时为 RED。

三色如何落进 `alpha-tests.md` 见[还原证据记录](../templates/story-artifacts.md#还原证据记录)；`review-restore` 把颜色翻成级别与处置，见 [review/dispatch.md](../review/dispatch.md#二角色映射)。

## 四、视觉缓存

**visual YELLOW 默认落 `UNVERIFIED` 并写补验方式，不默认截图。** 要把该声明收成 `PROVEN` 才走本节，且同一页面的多条 visual 只截一张整页图共用——逐规则截图付的是每处两张（原型 + 实现）的成本，换来的仍然是同一个人看同一个页面。

需要截图时调 `python3 "<skill-dir>/scripts/extract_design_spec.py" visual-cache --report <restore-report-red.json>`。脚本自行只数当前区块锚点且 `required_layers` 含 visual 的 YELLOW，机器可检 YELLOW 不会触发截图。缓存键固定包含：

1. 原型指纹；
2. 区块锚点；
3. 视口；
4. DPR；
5. 浏览器引擎与版本；
6. 字体指纹。

命中只读复用；未命中先返回 `needs-capture`，截图后带 `--png` 创建 `<design-spec-dir>/visual-baseline/<缓存指纹>/prototype.png` 与 `manifest.json`。不覆盖旧目录。报告中当前锚点没有 visual YELLOW 时返回 `not-needed`，不创建目录。

## 五、历史兼容

已有 Story 没有 `restore-contract.json` 时，用：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" evidence-format \
  --alpha-tests <story-dir>/alpha-tests.md
```

`legacy-screenshot-v1` 表示继续旧截图流程；不要求迁移。新 Story 不得主动跳过契约。
