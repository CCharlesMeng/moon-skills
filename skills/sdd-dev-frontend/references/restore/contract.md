# 还原契约：怎么写

本文件是 Phase A2 从冻结 QA 行编译还原契约时的格式契约——**期望值这一侧**。契约怎么跑、报告怎么判、退出码怎么处置在 [run.md](./run.md)。

权威判据仍是用户确认并冻结的 `dev-baseline.md`；JSON 只把其中 R1–R6 变成可重复执行的镜像，不新增维度、不反推实现。

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

**几何与层叠都不进 visual。** 「是不是被裁了、裁掉多少」用 `clip`，遮挡量用 `overlap`，溢出用 `overflow`，「谁压在谁上面」用 `stacking`——这四个 `check_mode` 都在，别把它们推进盲区。

字面值恰好长得像分层键时（例如 `expected` 就是 `{"visual": "hidden"}`）会命中第二条被拒——改写成 `{"render": {"visual": "hidden"}}` 明确层归属。

### 检查模式

| `check_mode` | 判定 |
| --- | --- |
| `exact` / `structure` / `state` | JSON 精确相等 |
| `numeric` | 数字或 CSS px，默认 ±1 CSS px；非数值叶子先做 CSS 序列化等价比对（见下） |
| `color` | 颜色规范化后精确匹配 |
| `overflow` / `overlap` / `clip` | 最大值不超过 1 CSS px |
| `stacking` | 相交区域的实际命中顺序等于 `expected.subject_on_top` |
| `visual` | 只能由视觉补证结果决定；缺补证为 YELLOW |

### `stacking`：`overlap` 答不了「谁在上面」

`overlap` 量的是矩形相交多少，而蒙层、下拉、吸顶、tooltip **本来就该重叠**——相交量不为 0 是它们的正常表现，所以 z-index 事故恰好全落在 `overlap` 判不动的地方。读 `z-index` 的计算样式也不行：最常见的事故是祖先的 `transform` / `opacity` / `filter` 建了新层叠上下文把子树整块关进去，此时 z-index 写多大都没用，而它的计算值完全正常。

判据因此取**浏览器合成后的真实命中顺序**：在两者相交区域中心打点，看 `elementsFromPoint` 先返回谁。

```json
{
  "id": "R6-2",
  "check_mode": "stacking",
  "expected": {"subject_on_top": true},
  "required_layers": ["render"]
}
```

对应 adapter 侧 `collect`：

```json
{"kind": "stacking", "with_selector": ".page-content"}
```

四条约束：

| 约束 | 理由 |
| --- | --- |
| `expected.subject_on_top` 必须是布尔值，编译期校验 | 「谁必须在上」就是这条规则的全部判据，缺了它规则没有内容 |
| 必须要求 `render` 层，不得走 `visual` | 命中顺序是机器可判的；允许它进 visual 就是把「谁盖住谁」推回人看图 |
| `with_selector` 必填 | 层叠是二元关系，不说和谁比就无从判起 |
| 采集器给不出结论时返回 `subject_on_top: null`，报告判 RED | 两者不重叠、或 `with_selector` 命中面过宽被截断时，「没量到」不能算「没问题」 |

`subject_on_top: false` 同样是合法期望——装饰层必须压在内容之下，和 tooltip 必须浮在最上是同一类可冻结事实。

判不通过时报告带 `stacking_hints`，直接写出 z-index 为什么不生效（`本元素 position: static，z-index: 10 不生效` / `祖先 div.card 建立了新层叠上下文：transform: …`）。**它是提示不是判据**：建立层叠上下文的条件是一份还在变的长枚举，这里只覆盖实测最常撞上的两条，结论永远由命中顺序给出。

两条已知边界：`containsNode` 与 `closest()` 同样不跨 shadow 边界；驱动只有 `elementFromPoint` 时退化为「只知道最顶上那个」，此时 `probe_method` 会回传实际用的是哪一种。

### CSS 序列化等价（`numeric` 非数值叶子与 `token` / `state_selector` 针）

**序列化差异不是还原偏差。** 比对器在这两处自动拉平：大小写与空白、`#fff`↔`#ffffff`↔`rgb()/rgba()`、`0px`↔`0`、box-shadow / text-shadow 的颜色分量位置（浏览器序列化把颜色放最前）、简写键 `background`→`background-color`、`flex`→`flex-grow`（采集脚本按同一映射取值）。语义不同的值不会被拉平。

三条写作约定，**不要依赖归一化去救写错的规则**：

- `expected` 的 CSS 键一律写计算样式 longhand（`background-color` 而不是 `background`）；
- **R1 的期望值写实现中立的结构事实**：元素的存在与数量、层级、角色（heading / img 等）、可访问名。**不得把原型 class 名写进 `expected`**——类名是设计稿侧工件，实现没有复刻义务；类名只出现在 `design_fact_source` 锚点与（适用时的）CSS locator 里；
- `exact` / `structure` / `state` 保持精确相等，**R2 文案逐字比对不经过任何归一化**。

上面这份归一化是**枚举**，枚举永远会有下一个未覆盖形态。写规则时不必为此预留什么；命中时的信号与处置在 [run.md 的 `suspected-tool-equivalence`](./run.md#二suspected-tool-equivalence工具缺口不是还原偏差)。

### `static_check`：静态层的针

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

浏览器采集 `kind` 支持：`count`、`text`、`order`、`structure`、`style`、`rect`、`state`、`overflow`、`overlap`、`clip`、`stacking`。`overlap` 与 `stacking` 的 `with_selector` 与主定位走同一条 shadow 规则（逐 root 查再合并）。状态必须先由浏览器驱动实际触发；采集脚本只读，不代替 hover、focus、loading 或 fixture。

### 三件与组件库形态相关的行为

采集器读的是**渲染后的 DOM 与计算样式**，所以框架换成 Vue / Svelte / Angular、样式换成 CSS Modules / CSS-in-JS / Tailwind 都不构成新场景——它们都收敛到同一棵 DOM 和同一份 `getComputedStyle` 输出。真正会让它失效的是下面这几种 DOM 层面的现象，按现象处理，不按栈处理。

| 现象 | 行为 |
| --- | --- |
| **open shadow root** | 四种定位策略都逐个 root 查再合并。选择器不跨 shadow 边界，不这么做的话 web-component 形态的组件库会让每条规则都返回「定位不到」 |
| **closed shadow root** | 从外部无法枚举也无法读取。定位失败且页面上存在「自定义元素既无 `shadowRoot` 又无子节点」时，`reason` 报 `possible closed shadow root: <标签名>`，与选择器写错区分开 |
| **伪元素** | `collect.pseudo` 取 `::before` / `::after`，走 `getComputedStyle(el, pseudo)`。不给这个入口的话，图标字体与设计系统放在伪元素里的内容是**静默不可见**，比报错危险 |
| **虚拟列表** | `count` 发现容器声明了 `aria-rowcount` / `aria-setsize` 且与渲染行数不符时，返回 `{"rendered": n, "declared": m, "windowed": true}` 而不是一个数 |

**虚拟列表那条会让原本写成数字的期望值判不通过，这是故意的。** DOM 里只有窗口内的行，直接返回 `nodes.length` 会给出一个「看起来对」的错数——那比报错危险得多。两个数都交出去，由契约那侧决定判哪一个，采集器不替它选。

两条已知边界：`closest()` 同样不跨 shadow 边界，所以 `aria-rowcount` 容器与行不在同一个 root 时读不到声明数；closed shadow root 的判据是启发式的，只能提示怀疑，不能证明。

## 四、编译与校验

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

编译通过后，契约的执行、报告与落账见 [run.md](./run.md)。
