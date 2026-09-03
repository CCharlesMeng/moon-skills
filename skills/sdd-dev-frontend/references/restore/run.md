# 还原契约：怎么跑

RED 与 GREEN 始终运行同一份冻结契约和 adapter；只改变实现。规则字段与采集模式见 [contract.md](./contract.md)。

## 一、采集

有 static 规则时运行：

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" static \
  --baseline <story-dir>/dev-baseline.md \
  --contract <evidence-dir>/restore-contract.json \
  --adapter <evidence-dir>/restore-adapter.json \
  --repo-root <repo-root> \
  --out <work-dir>/static-results.json
```

没有 static 规则时跳过此调用，`report` 也不传 `--static-results`。

打开规则所属页面、进入 `scenario` 并准备 fixture 后注入：

```js
window.__SDD_RESTORE_INPUT__ = {
  contract: RESTORE_CONTRACT,
  adapter: RESTORE_ADAPTER,
  fixture_status: {"R5-1-table-scroll": "ready"}
};
```

再注入 `<skill-dir>/scripts/collect_restore_facts.js`，把结果保存为 `<work-dir>/render-results-<页面>.json`。采集结果顶层 `observed` 记录实际 viewport 与 route；以它为准，不在 `scenario` 里发明机器字段。

页面不可用时仍写一份可解析结果：

```json
{"contract_sha256":"<sha>","page_available":false,"reason":"dev server unavailable","rules":{}}
```

跨页契约必须逐页注入，报告命令重复传 `--render-results`。合并时任何一页给出的可用状态优先于其他页的定位失败；所有页面都失败才判失败。

## 二、报告

```bash
python3 "<skill-dir>/scripts/verify_restore_contract.py" report \
  --phase red \
  --baseline <story-dir>/dev-baseline.md \
  --contract <evidence-dir>/restore-contract.json \
  --adapter <evidence-dir>/restore-adapter.json \
  --static-results <work-dir>/static-results.json \
  --render-results <work-dir>/render-results-<页面>.json \
  --out <evidence-dir>/restore-report-red.json
```

无 static 规则时删去相应参数。GREEN 只把 `--phase` 改成 `green`、输出改成 `restore-report-green.json`；页面集合与采集方式保持不变。每个子命令都会重新校验 baseline、contract 与 adapter，三者未变化时 GREEN 前不必另跑一次 `validate`。

单条状态：

| 状态 | 含义 |
| --- | --- |
| `red` | 已取得判据，实际不符或采集明确失败；条目就地保留 expected、actual、comparison、reasons |
| `yellow` | 页面、fixture 或必要能力未就绪，当前无法判断 |
| `green` | 判据通过或命中冻结豁免 |

汇总优先级为 RED > YELLOW > GREEN。退出码只有：`0`（命令成功；RED 阶段出现 RED 仍为 0）、`2`（工件或输入错误）、`3`（GREEN 阶段 overall 不是 green）。字符串不等时先按报告 `hint` 目视两侧是否只是序列化差异；确认是工具缺口再补归一化，不改产品实现迎合字符串。

## 三、Phase C 复核与人工盲区

Phase C 组合含 `restore-final` 时，把当前 `code_fingerprint` 与 `alpha-tests.md` 对应 GREEN 行「说明」里的完整 `code=<sha256>` 比较；该值在 GREEN 时逐字取自 `review-evidence.json / code.code_fingerprint`。未变才直接复用 `restore-report-green.json`；缺值或变化都按最终 diff 重跑全部冻结区块并覆盖同一文件。聚合器直接把报告三色映射成级别，不再生成 `restore-report-review.json`，也不派还原检视子代理。

图片裁切焦点、透明叠层观感等机器盲区不进入契约，拆成保留原 R 行追溯的 `manual_acceptance`；把路由、目视动作与证据要求交给 `acceptance.md` 的「需要你处理」，真实人员回填前保持 `UNVERIFIED`。不另建 visual 缓存或 visual-results。
