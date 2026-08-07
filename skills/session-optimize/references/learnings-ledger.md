# 复盘台账：`.learnings/LEARNINGS.md`

台账存在的唯一理由是让复发可数。没有它，每次复盘都从 n=1 开始，永远只能提"下次注意"，`SKILL.md` 第 5 节的固化门槛也无从判断。

## 位置与初始化

项目根的 `.learnings/LEARNINGS.md`，单文件。不存在时创建：

```bash
mkdir -p .learnings
[ -f .learnings/LEARNINGS.md ] || printf '# Learnings\n\n复盘台账：按 Pattern-Key 去重，按 Recurrence-Count 计数。格式见 session-optimize/references/learnings-ledger.md。\n\n---\n' > .learnings/LEARNINGS.md
```

台账要进版本库。放进 `.gitignore` 会让计数只在本机累积，跨会话、跨机器的复发就再也数不出来。

## 写入权限边界

这是本 skill 唯一免批准的写入，边界要窄：

- **允许**：追加新条目；更新已有条目的 `Recurrence-Count`、`Last-Seen`、`Status`、`See Also`、`Resolution`。
- **不允许**：删除或重写历史条目的事实内容；改 `.learnings/` 下的其他文件；顺手整理格式；用台账写入替代任何需要批准的项目修改。
- **不记**：凭据、令牌、私钥、环境变量值、个人信息、完整日志或完整源文件。证据用短摘要或脱敏摘录，不贴原始输出。
- 子代理不得写台账，只有主 Agent 写。

没有实质问题的复盘不写台账——空跑一轮不该留痕。

## 条目格式

```markdown
## [LRN-20260806-001] decision.unverified-claim

**类别**: 流程/决策（L2）
**严重程度**: 高
**Status**: pending
**Pattern-Key**: decision.unverified-claim
**Recurrence-Count**: 1
**First-Seen**: 2026-08-06
**Last-Seen**: 2026-08-06

### 问题
报告"测试已通过"时本轮没有跑过测试，用户复核后发现测试实际未执行。

### 证据
- 会话第 12 轮宣告完成，该轮及之前没有测试类工具结果
- 第 14 轮用户指出后重跑，3 个用例失败

### 处置
完成声明必须附可观察证据。本次属高危不变量（会产出错误结果），一次即申请固化。

### Metadata
- 去向: 项目流程文档（待批准）
- 相关文件: docs/workflow.md
- See Also: —
```

### 字段说明

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| ID | `LRN-YYYYMMDD-XXX` | XXX 为当日序号或 3 位随机字符 |
| `类别` | 七类之一 + 层号 | 取自 `SKILL.md` 第 2 节地图，一条只有一个主类别 |
| `严重程度` | `高` / `中` / `低` | 与主报告一致 |
| `Status` | 见下表 | 条目的生命周期状态 |
| `Pattern-Key` | `类别.症状` | 去重与计数的唯一依据，标准键见 [failure-map.md](failure-map.md) |
| `Recurrence-Count` | 整数 | 命中同一 `Pattern-Key` 时 +1，不新建条目 |
| `First-Seen` / `Last-Seen` | `YYYY-MM-DD` | 计数窗口和衰减都基于 `Last-Seen` |

### Status 取值

| 值 | 含义 |
| --- | --- |
| `pending` | 已记账，尚未处置 |
| `experiment` | 已作为下次会话的可逆试验提出，等待观察结果 |
| `promoted` | 已固化进长期资产，在 `Resolution` 里写清写到了哪个文件 |
| `resolved` | 对应缺陷已修复并验证通过 |
| `wont-fix` | 判定不值得处置，在 `Resolution` 里写理由 |
| `needs-review` | 已过期待治理，由衰减规则打上 |

处置完成时追加 `### Resolution` 块，写日期、实际改动或提交、一句结论。

## 查重与计数

记账前必须先查重，否则计数不可信：

```bash
grep -n "Pattern-Key: <类别>.<症状>" .learnings/LEARNINGS.md
```

1. **命中**：更新那条已有条目——`Recurrence-Count` +1、刷新 `Last-Seen`、把本次证据要点追加进 `### 证据`（保留原有条目，不覆盖）。严重程度只上调不下调。
2. **未命中但语义相近**：用 `grep -rh "Pattern-Key:" .learnings/LEARNINGS.md | sort -u` 复查一遍。同一问题换了说法时，复用旧键并在新证据里注明措辞差异，优于新造键。
3. **确实是新问题**：新建条目，`Recurrence-Count: 1`，`First-Seen` = `Last-Seen` = 今天。
4. **`Status` 为 `promoted` 或 `resolved` 的条目又复发**：不新建，改回 `pending` 并 +1，在证据里写明"固化后仍复发"——这是固化措施无效的直接信号，比新条目有价值得多。

## 固化门槛与提升目标

门槛见 `SKILL.md` 第 5 节。够门槛时，按主类别选提升目标：

| 主类别 | 提升目标 |
| --- | --- |
| `背景输入不足` | 项目约束文档或任务模板（写"开工前必须提供什么"） |
| `知识缺口` | 出问题的那份文档本身；跨任务常用的写进常驻上下文文件（如 `AGENTS.md`、`rules/`） |
| `流程/决策` | 项目流程文档；属某个 skill 的承重规则则移交 `refine-skill` |
| `工具使用` | 工具选择与调用契约；属某个 skill 的移交 `refine-skill` |
| `项目实现` | 代码修复 + 回归测试；可复用防护资产走 `immune-debug` 登记 |
| `工具本身` / `外部环境` | 不固化进规则，只在文档记"已知限制 + 可接受绕行"，并保留移交记录 |

固化内容写成短的预防规则——下次动手前要做什么，不是事故复述。原条目改 `Status: promoted`，并在 `Resolution` 里写清写进了哪个文件。

## 衰减治理

`Last-Seen` 距今超过 90 天的条目打 `needs-review` 并降低置信度，避免过期规则继续看起来可靠。这与 `audit` 对 `immune-registry.yaml` 的新鲜度衰减是同一套思路，`audit` 做上下文治理时可以一并检视台账。

衰减只看 `Last-Seen`（是否还在复发），不看条目有多老：一条早就固化、之后再没复发的规则，说明它在起作用，不该因为"旧"被降级。
