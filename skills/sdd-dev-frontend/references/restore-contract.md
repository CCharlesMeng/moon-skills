# 还原契约与机器报告

本文件是 Phase B 机器检查工件的格式契约。权威判据仍是用户确认并冻结的 `dev-baseline.md`；JSON 只把其中 R1–R6 变成可重复执行的镜像，不新增维度、不反推实现。

## 一、工件

| 工件 | 生命周期 | 作用 |
| --- | --- | --- |
| `<design-spec-dir>/design-facts.json` | Requirement 级 | 确定性原型事实：归一化 DOM/CSS、资源内容/缺失状态、区块、结构、静态文案、token、布局声明 |
| `<story-dir>/restore-contract.json` | Story 级 | 冻结 R1–R6 与 `dev-baseline.md` SHA-256 |
| `<story-dir>/restore-adapter.json` | Story 级运行适配 | 实现 locator、源码扫描范围、浏览器采集模式；不含期望值 |
| `<story-dir>/restore-report-red.json` | Story 级证据 | Step ① 运行结果 |
| `<story-dir>/restore-report-green.json` | Story 级证据 | Step ④ / ⑤ 运行结果 |

## 二、规则草稿

`recon-spec` 回传 JSON 规则数组，主 agent 只在用户确认基线后用脚本编译正式契约。

```json
{
  "rules": [
    {
      "id": "R3-1",
      "baseline_id": "R3-1",
      "dimension": "R3",
      "block": "订单筛选栏",
      "subject": "筛选行与列表区的垂直间距",
      "expected": {
        "static": "--spacing-lg",
        "render": "24px"
      },
      "check_mode": "numeric",
      "tolerance": {"css_px": 1},
      "state_scenario": {"name": "default"},
      "design_fact_source": {
        "path": "design-facts.json",
        "anchor": ".section-box-106",
        "key": "blocks[].layout_declarations"
      },
      "required_layers": ["static", "render"],
      "static_check": {"kind": "token", "value": "--spacing-lg"}
    }
  ]
}
```

每条规则必含：`id`、`baseline_id`、`dimension`、`block`、`subject`、`expected`、`check_mode`、`tolerance`、`state_scenario`、`design_fact_source`、`required_layers`。

`expected` 可以是字面值，也可以按层给（键取 `static` / `render` / `visual`，如上例）。**编译器与 `validate` 都会拒绝下列写法**，它们的共同点是会让规则在报告里自动变绿或恒为红，却看不出原因：

| 写法 | 为什么拒绝 |
| --- | --- |
| `baseline_id` 在基线的还原侧表格里找不到 | 基线哈希只锁住文档本身；引用一条不存在的基线行，规则就没有判据来源 |
| 基线里某条 R 没有任何规则引用 | 契约全绿不再等于基线全部满足。确实不涉及的维度在基线里写「不适用」，那样的行不要求覆盖 |
| 规则 `id` 重复 | 报告里会出现两条同 `rule_id` 的条目，落账时分不清哪条是哪条 |
| `required_layers` 含 `render`，但该层取到的 `expected` 为空（`{}` / `[]` / `""` / 缺键） | `numeric` 产生不出差异项、`overflow` 家族对空容器取 0，两种都无条件判绿。注意 `0` 与 `false` 是合法期望值 |
| `check_mode: visual` 同时要求 `render` 层 | visual 只能由视觉补证判定，render 层对它恒判不通过，这条规则永远 GREEN 不了 |
| `required_layers` 含 `visual` 但 `visual_blind_spot` 不是下表两值之一 | visual 是唯一没有机器判据的层，必须指名盲区类别；见下节 |
| adapter 里有契约中不存在的规则条目 | 多半是契约改了 adapter 没跟着改；静默丢弃会让人以为旧定位还在生效 |

### `visual_blind_spot`：visual 层只剩两类

| 取值 | 判什么 |
| --- | --- |
| `image-focus` | 裁切后露出的是不是该露的那部分（改 `object-position` 之类） |
| `composite` | `mix-blend-mode` / `backdrop-filter` / 多层透明度叠出来的实际观感 |

**这道门存在的理由是 visual 层末端没有机器判据**——首版不做像素级 diff，所以最后是人看原型与实现两张图。原先的判据是散文里一句「阴影观感、字体栅格、图片裁切、复杂叠层**等**机器盲区」，结尾那个「等」是敞口：任何判不了的规则都能自称盲区溜进 visual 层，然后以「等人看图」的名义无限期停在 YELLOW，而每次未命中缓存要截两张。

撤掉的两类不是「机器判不了」，而是**截了也得不出可行动的结论**：

- **阴影**：`box-shadow` 的计算样式就是字符串，比对器已有分量顺序归一化，走 render 层判值即可；而 layout checklist 本来就写明「阴影不好看且无功能后果 → 不报」，截了也不采纳。
- **字体栅格**：视觉缓存键里含浏览器引擎版本与字体指纹，等于承认它是环境属性——换个小版本整体失效重截，看到的差异是环境不是实现，也改不动。该判的是 `font-family` / `font-size` / `font-weight` / `line-height` 这些 longhand，全部机器可判。

**几何不进 visual。** 「是不是被裁了、裁掉多少」用 `clip`，遮挡用 `overlap`，溢出用 `overflow`——这三个 `check_mode` 都在，别把它们推进盲区。

字面值恰好长得像分层键时（例如 `expected` 就是 `{"visual": "hidden"}`）会命中第二条被拒——改写成 `{"render": {"visual": "hidden"}}` 明确层归属。

### 检查模式

| `check_mode` | 判定 |
| --- | --- |
| `exact` / `structure` / `state` | JSON 精确相等 |
| `numeric` | 数字或 CSS px，默认 ±1 CSS px；非数值叶子先做 CSS 序列化等价比对（见下） |
| `color` | 颜色规范化后精确匹配 |
| `overflow` / `overlap` / `clip` | 最大值不超过 1 CSS px |
| `visual` | 只能由视觉补证结果决定；缺补证为 YELLOW |

### CSS 序列化等价（`numeric` 非数值叶子与 `token` / `state_selector` 针）

**序列化差异不是还原偏差。** 比对器在这两处自动拉平：大小写与空白、`#fff`↔`#ffffff`↔`rgb()/rgba()`、`0px`↔`0`、box-shadow / text-shadow 的颜色分量位置（浏览器序列化把颜色放最前）、简写键 `background`→`background-color`、`flex`→`flex-grow`（采集脚本按同一映射取值）。语义不同的值不会被拉平。

三条写作约定，**不要依赖归一化去救写错的规则**：

- `expected` 的 CSS 键一律写计算样式 longhand（`background-color` 而不是 `background`）；
- **R1 的期望值写实现中立的结构事实**：元素的存在与数量、层级、角色（heading / img 等）、可访问名。**不得把原型 class 名写进 `expected`**——类名是设计稿侧工件，实现没有复刻义务；类名只出现在 `design_fact_source` 锚点与（适用时的）CSS locator 里；
- `exact` / `structure` / `state` 保持精确相等，**R2 文案逐字比对不经过任何归一化**。

### 未覆盖形态：`suspected-tool-equivalence`

上一节的归一化是**枚举**，枚举永远会有下一个未覆盖形态。这类 RED 的危险不在于它是红的，而在于它和真偏差走同一条升级路径：修 3 次不成 → 打断用户 → 补一条豁免。实证是区域流水地图 Story 的 `EX-2`–`EX-5`——四条工具债被写成了冻结基线里「允许与设计稿不一致」的永久记录。

所以比对器另带一个**不依赖枚举**的信号：严格比对失败时，再用一次故意过宽的规范化（在上节归一化之上抹掉 token 顺序、分隔符与 `0` 值单位）。过宽形态一致就把该条标成 `reason_class: "suspected-tool-equivalence"`，写进报告顶层 `tool_equivalence_suspects[]`，`report` 以**退出码 5** 阻断（先于 `--phase green` 的退出码 3）。

| 命中后不许做 | 只能做 |
| --- | --- |
| 改实现去迎合字符串 | 把该形态补进 `verify_restore_contract.py` 的 normalize / canonicalize 函数族与 `collect_restore_facts.js` 的同源别名表后重跑同一契约；补不了时按 P7 上报工具缺口 |
| 为它新增豁免（**硬门禁 16**） | 补不了或形态存疑时按 P7 上报为工具等价缺口，附 `rule_id` 与两侧原值 |
| 把它算进「同一报错修 3 次」的计数 | 补完归一化后重跑同一契约；两端映射必须同步改 |

**过宽规范化只用于怀疑，永远不进判定通道**——它会把 `12px 8px` 与 `8px 12px` 拉平，作为通过判据就会漏掉真偏差。因此它命中时的结论是「这条要人看一眼工具」，不是「这条通过了」。

### 静态预检

规则要求 `static` 层时必须给 `static_check`：

| `kind` | 字段 | 语义 |
| --- | --- | --- |
| `text` / `i18n_key` / `token` / `state_selector` | `value` | 在 adapter 的 `source_files` 中必须出现 |
| `regex` | `pattern` | 至少一份源码匹配 |
| `absent` / `forbidden_literals` | `values` | 所列字面量必须全部不出现 |

`token` / `state_selector` 的针按上节 CSS 序列化等价匹配（命中方式回写在 `matched_via`：`exact` / `css-normalized`）；`text` / `i18n_key` 是逐字文案针，不归一化。静态通过只证明 static 层；规则还要求 render 时，缺结构化渲染不能 GREEN。

### 冻结豁免

已在确认门冻结的豁免可以写：

```json
{"frozen_exemption": {"id": "EX-2", "frozen": true, "reason": "平台能力限制"}}
```

未冻结豁免会被编译器拒绝。

## 三、实现 adapter

```json
{
  "schema_version": 1,
  "rules": {
    "R3-1": {
      "locators": [
        {"strategy": "role", "role": "group", "name": "订单筛选"},
        {"strategy": "text", "text": "全部状态"},
        {"strategy": "testid", "testid": "order-filters"},
        {"strategy": "css", "selector": ".order-filters"}
      ],
      "source_files": ["src/pages/orders/OrderList.tsx", "src/pages/orders/order-list.module.css"],
      "collect": {
        "kind": "style",
        "single": true,
        "properties": ["gap"]
      }
    }
  }
}
```

`locators` 按 `role/name` → 精确文案 → 稳定 test id → CSS 排序；数组可以提前结束。CSS 禁止构建生成随机 class。期望值、容差和设计事实出处不得写入 adapter。

浏览器采集 `kind` 支持：`count`、`text`、`order`、`structure`、`style`、`rect`、`state`、`overflow`、`overlap`、`clip`。状态必须先由浏览器驱动实际触发；采集脚本只读，不代替 hover、focus、loading 或 fixture。

## 四、执行

### 1. 编译与校验

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" contract \
  --baseline <story-dir>/dev-baseline.md \
  --baseline-ref dev-baseline.md \
  --rules <临时规则草稿.json> \
  --out <story-dir>/restore-contract.json

python3 "<skill-dir>/scripts/verify_restore_contract.py" validate \
  --baseline <story-dir>/dev-baseline.md \
  --contract <story-dir>/restore-contract.json \
  --adapter <story-dir>/restore-adapter.json
```

`dev-baseline.md` 任一字节变化都会使校验硬失败。确需修改时，先走基线变更记录与重新确认，再带 `--after-reconfirmation` 重新编译——没有这个开关时，`contract` 拒绝覆盖一份记录了不同基线哈希的既有契约（基线正文里的「已冻结 ✅」不会因为内容被改就消失，拦不住就等于冻结名存实亡）。基线没变时重复编译是幂等的，不需要开关。

### 2. 静态预检

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" static \
  --baseline <story-dir>/dev-baseline.md \
  --contract <story-dir>/restore-contract.json \
  --adapter <story-dir>/restore-adapter.json \
  --repo-root <repo-root> \
  --out <临时目录>/static-results.json
```

### 3. 结构化渲染

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

### 4. 报告

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

退出码：

| 码 | 含义 | 动作 |
| --- | --- | --- |
| `0` | 报告已写出且无需阻断。RED 阶段出现 RED 是预期证据，仍返回 0 | 照常进 Step ② |
| `3` | `--phase green` 下 `overall` 不是 `green` | 不得当成完成；按状态语义处理 RED / YELLOW |
| `5` | 存在 `suspected-tool-equivalence`，两个 phase 都阻断 | 走硬门禁 16：补比对器映射或上报工具缺口，**不修实现、不补豁免** |

退出码 `5` 先于 `3` 判定——工具缺口没排除前，`overall` 是什么都不可信。

## 五、状态语义

| 单条状态 | 必含 |
| --- | --- |
| `red` | 期望值、实际值、契约出处、实现定位、失败原因 |
| `yellow` | 无法判定原因、要求的补证方式 |
| `green` | 已验证层清单，或命中的冻结豁免 |

汇总：有 RED 即 RED；无 RED 但有 YELLOW 即 YELLOW；全部规则 GREEN 才 GREEN。页面不可用时 render-required 规则为 YELLOW；页面可用但结构化采集已经尝试并报错时为 RED。

## 六、视觉缓存

**visual YELLOW 默认落 `UNVERIFIED` 并写补验方式，不默认截图。** 要把该声明收成 `PROVEN` 才走本节，且同一页面的多条 visual 只截一张整页图共用——逐规则截图付的是每处两张（原型 + 实现）的成本，换来的仍然是同一个人看同一个页面。

需要截图时调 `python3 "<skill-dir>/scripts/extract_design_spec.py" visual-cache --report <restore-report-red.json>`。脚本自行只数当前区块锚点且 `required_layers` 含 visual 的 YELLOW，机器可检 YELLOW 不会触发截图。缓存键固定包含：

1. 原型指纹；
2. 区块锚点；
3. 视口；
4. DPR；
5. 浏览器引擎与版本；
6. 字体指纹。

命中只读复用；未命中先返回 `needs-capture`，截图后带 `--png` 创建 `<design-spec-dir>/visual-baseline/<缓存指纹>/prototype.png` 与 `manifest.json`。不覆盖旧目录。报告中当前锚点没有 visual YELLOW 时返回 `not-needed`，不创建目录。

## 七、历史兼容

已有 Story 没有 `restore-contract.json` 时，用：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" evidence-format \
  --alpha-tests <story-dir>/alpha-tests.md
```

`legacy-screenshot-v1` 表示继续旧截图流程；不要求迁移。新 Story 不得主动跳过契约。
