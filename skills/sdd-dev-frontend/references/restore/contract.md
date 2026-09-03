# 还原契约：怎么写

在 Phase A2 用户确认 `dev-baseline.md` 后，把每条 R1–R6 基线行里机器能判的事实编译成 v3 契约。基线行保留完整期望与出处；JSON 只保存执行判据，不从实现反推期望。

## 一、字段

契约顶层：

| 字段 | 谁读它 | 含义 |
| --- | --- | --- |
| `schema_version` | 校验器、采集器 | 新契约固定为 `3`；校验器兼容读取 `2` |
| `baseline_sha256` | 校验器 | 当前冻结 `dev-baseline.md` 的 SHA-256 |
| `contract_sha256` | 采集结果、报告 | 契约与证据的链接键；不作自哈希防篡改 |
| `rules` | 校验器、采集器 | 非空规则数组 |

每条规则字段（前三项必有，其余按形态取用）：

| 字段 | 谁读它 | 含义 |
| --- | --- | --- |
| `id` | 全链路 | 以 `baseline_id` 开头，再接小写连字符 slug；每个独立可判事实一条 |
| `baseline_id` | 校验器 | 指向冻结基线行；一行可对应多条规则，所有非“不适用”行必须被覆盖 |
| `subject` | 人、契约审阅 | 被判定的事实 |
| `scenario` | 驾驭浏览器的人 | 可选自由字符串，只写进入状态的方法；机器不解析 |
| `fixture_required` | 采集器 | 可选布尔值；需要 fixture 时写 `true` |
| `check_mode` | 校验器、报告器 | render 规则的比较模式 |
| `expected` | 报告器 | render 规则的非空期望；阈值家族除外 |
| `tolerance` | 报告器 | 可选 `css_px` 偏差；省略时按模式取默认值 |
| `static_check` | 静态预检 | static 规则的源码判据 |
| `frozen_exemption` | 校验器、报告器 | exempt 规则已确认的豁免编号与理由 |

一条规则只能属于一种形态；有 `static_check` 即 static，否则有 `check_mode` 即 render，有 `frozen_exemption` 即 exempt。不写 `required_layers`。

## 二、三种规则

```json
{
  "schema_version": 3,
  "baseline_sha256": "ceef0a70…",
  "contract_sha256": "1e303bc9…",
  "rules": [
    {
      "id": "R1-1-sections",
      "baseline_id": "R1-1",
      "subject": "默认可见主体三段",
      "check_mode": "exact",
      "expected": 3
    },
    {
      "id": "R2-6-no-unit-ren",
      "baseline_id": "R2-6",
      "subject": "机会点数单位不得是「人」",
      "static_check": {"kind": "forbidden_literals", "values": ["\"unit\": \"人\""]}
    },
    {
      "id": "R3-9-shadow",
      "baseline_id": "R3-9",
      "subject": "卡片投影",
      "frozen_exemption": {"id": "EX-2", "reason": "平台能力限制"}
    }
  ]
}
```

Render 规则必须有非空 `expected`，但 `0` 与 `false` 是合法值。`overflow`、`overlap`、`clip` 不写 `expected`，阈值取可选 `tolerance.css_px`，缺省为 1。`numeric` 的容差同样缺省为 1，其余模式缺省为 0。

`check_mode` 只有六种：

| 模式 | 判据 |
| --- | --- |
| `exact` | JSON 精确相等；结构、状态与文案都用它 |
| `numeric` | 数字按容差；非数值叶子只拉平 CSS 序列化差异 |
| `overflow` / `overlap` / `clip` | 实测最大值不超过容差 |
| `stacking` | `expected.subject_on_top` 与浏览器命中顺序一致 |

`numeric` 可识别颜色写法、`0px`/`0`、shadow 分量顺序、`background`/`background-color`、`flex`/`flex-grow` 和 `BlinkMacSystemFont`/`-apple-system`/`system-ui` 等价。字符串 RED 仍在报告里保留两侧原值并提示先目视序列化差异。

`stacking` 对应 adapter 的 `{"kind":"stacking","with_selector":"…"}`。两者不重叠或探针截断时返回 `subject_on_top: null` 并判 RED；`stacking_hints` 只辅助定位，不参与判定。

Static 规则的 `static_check.kind` 支持：

| kind | 字段 | 判据 |
| --- | --- | --- |
| `text` / `i18n_key` / `token` / `state_selector` | `value` | 至少一份 `source_files` 命中；后两种允许 CSS 序列化等价 |
| `regex` | `pattern` | 至少一份源码匹配 |
| `absent` / `forbidden_literals` | `values` | 所列字面量全部不出现 |

Static 是否有意义取决于仓库能否提供稳定源码针；不要按 R 维度默认添加。

## 三、实现 adapter

```json
{
  "schema_version": 2,
  "rules": {
    "R1-1-sections": {
      "locators": [{"strategy": "css", "selector": "header[data-dashboard-toolbar], [data-section-id]"}],
      "collect": {"kind": "count"}
    },
    "R2-6-no-unit-ren": {
      "source_files": ["pages/ioc-project-overview.json"]
    }
  }
}
```

Render 规则提供非空 `locators` 与 `collect`；static 规则只提供非空 `source_files`；exempt 规则不采集，也不在 adapter 中建条目。Locator 支持 `role`、`text`、`testid`、`css`，顺序不限；疑似构建随机 class 只产生 warning。Adapter 中多出的 rule id 仍拒绝。

`collect.kind` 支持 `count`、`text`、`order`、`style`、`rect`、`state`、`overflow`、`overlap`、`clip`、`stacking`。`count` 定位到 0 个元素时返回正常事实 `actual: 0`；其他模式定位失败才报错。状态由浏览器驱动先触发，采集器只读。

Open shadow root 会逐 root 定位；closed shadow root 只给怀疑提示；伪元素通过 `collect.pseudo` 读取；虚拟列表发现 ARIA 声明数与渲染数不同时返回 `{rendered, declared, windowed}`，不拿窗口节点数冒充总数。

## 四、编译与校验

规则草稿直接走 stdin，不落一份与正式契约重复的过程文件；stdin 可传裸规则数组或 `{"rules":[...]}`，`recon-spec` 默认回传后者：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" contract \
  --baseline <story-dir>/dev-baseline.md \
  --rules - \
  --out <evidence-dir>/restore-contract.json

python3 "<skill-dir>/scripts/verify_restore_contract.py" validate \
  --baseline <story-dir>/dev-baseline.md \
  --contract <evidence-dir>/restore-contract.json \
  --adapter <evidence-dir>/restore-adapter.json
```

基线变化后先登记变更并重新确认，再加 `--after-reconfirmation` 编译。脚本在覆盖契约前把同目录的活动报告改名为 `restore-report-*.stale-<旧契约sha8>.json`；基线未变时重复编译免费。既有 v2 契约继续读取，不强制迁移。
