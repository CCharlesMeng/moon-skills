# Skill 缺陷台账：`.learnings/skills/<skill-name>.md`

台账存在的唯一理由是让 skill 缺陷的复发可数。判据三要分"系统性还是一次性偶然",而每次复盘都是新会话——上一次的判断不在上下文里,`evals/` 里的观察用例只说明"见过",不说明这是第 2 次还是第 5 次。没有计数,判据三只能凭感觉答。

## 位置：为什么在源仓，而不在 skill 目录里

放在 **skill 源仓**的 `.learnings/skills/<skill-name>.md`,按 skill 分文件。不存在时创建：

```bash
mkdir -p .learnings/skills
[ -f .learnings/skills/<skill-name>.md ] || printf '# <skill-name> 缺陷台账\n\n按 Pattern-Key 去重，按 Recurrence-Count 计数。格式见 refine-skill/references/skill-ledger.md。\n\n---\n' > .learnings/skills/<skill-name>.md
```

**不放进 `skills/<skill-name>/` 里面**,尽管 `evals/` 就在那里。因为 skill 会以两种形态部署:符号链接到源仓(一份共享),或 vendored 实体副本(N 份各自分叉)。放在 skill 目录内,vendored 那条路会把台账复制进每个消费仓库,在那里分叉、被提交进别人的代码库,还把"这个 skill 老在哪出错"的内部记录一起带走,下次同步又被覆盖。放在源仓的 `.learnings/skills/` 下,它在 `skills/` 之外,永远不会被 vendored 带出去,而计数天然汇总——这正是它要解决的问题:同一个缺陷在 3 个仓库各出现 1 次,只有一个跨仓库的计数器能看出它已经复发 3 次。

源仓自己作为一个项目,它的项目级台账仍是 `.learnings/ledger.md`(由 `session-optimize` 维护),两者不混。

## 谁写

**只有维护者在跑 `refine-skill` 时写。** 使用者跑 `session-optimize` 发现某个 skill 的缺陷时够不着这个文件(通常也没有源仓的写权限),他的产出是移交证据包;计数在维护者这一侧累加,这也是移交包里要带"复发情况"的原因。

写入时机在第三步用户确认之后,和改写一起落盘,记账内容在确认清单里一并说明。**即使结论是"判为偶然,不改 skill"也要记账**——否则下一次仍然从 n=1 开始,判据三永远升不上去。

## 条目格式

```markdown
## [SKL-20260821-001] decision.summary-loss

**Status**: pending
**Pattern-Key**: decision.summary-loss
**Recurrence-Count**: 2
**First-Seen**: 2026-08-06
**Last-Seen**: 2026-08-21
**来源**: 会话 2026-08-06(仓库 A)、会话 2026-08-21(仓库 B)

### 触发情境
需要逐字比对两份文档的差异时。

### 错误行为
把两份文档摘要后交给子代理判断,结论建立在有损摘要上,漏掉了格式层面的差异。

### 期望行为
依赖逐字原文的判断由主 agent 自己做。

### 归因
判断错误(判据一);被反驳的假设是"比对类工作都适合委派"(判据二);不该拆拆了(判据五)。

### Resolution
2026-08-21 · 第五节改为按"摘要是否无损"分流,回归验证 3/3 通过 · commit abc1234
```

### 字段说明

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| ID | `SKL-YYYYMMDD-XXX` | 与项目级台账的 `RETRO-` 前缀区分开,一眼能看出这条数的是 skill 而不是项目 |
| `Pattern-Key` | `类别.症状` | 去重与计数的唯一依据。类别沿用 `session-optimize` 的 [failure-map.md](../../session-optimize/references/failure-map.md),这样移交包里的键不用翻译 |
| `Recurrence-Count` | 整数 | 命中同一键时 +1,不新建条目 |
| `来源` | 会话日期 + 仓库；收件则记 sink 标识 | 会话证据仍用日期 + 仓库代号,前后一致即可。从投递路径收来的包记 `<sink>#<id>`(未投递则记文件名),用来去重,见「收件与去重」。别把客户或内部系统名写进源仓 |

### Status 取值

| 值 | 含义 |
| --- | --- |
| `pending` | 已记账,尚未处置 |
| `observing` | 判为一次性偶然,情境已入 `evals/` 观察,未改规则 |
| `fixed` | 已改写并通过回归验证,在 `Resolution` 里写清提交 |
| `wont-fix` | 判定不值得改,在 `Resolution` 里写理由 |
| `stale-copy` | 报告来自陈旧的 vendored 副本,上游已修;不改 skill,在 `Resolution` 里写清修复提交 |

## 查重与计数

记账前先查重,否则计数不可信：

```bash
grep -n '\*\*Pattern-Key\*\*: <类别>\.<症状>' .learnings/skills/<skill-name>.md
```

1. **命中**:`Recurrence-Count` +1、刷新 `Last-Seen`、把本次来源追加进 `来源`、本次证据要点追加进对应小节。不覆盖原有内容。
2. **未命中**:新建条目,`Recurrence-Count: 1`,`First-Seen` = `Last-Seen` = 今天。
3. **一次会话只计一次**:同一个问题被用户、子代理反复提起仍是 1 次。数的是复发,不是有几个人说过。一个 feedback 包计一次——N 个包来自 N 个会话就是 N 次。
4. **`Status` 为 `fixed` 的条目又复发**:不新建,改回 `pending` 并 +1,在证据里写明"改写后仍复发"。这是改法无效的直接信号,比一条新条目有价值得多——它说明上次找的假设找错了,回判据二重找。

## 收件与去重

同会话接力不经过本文件:证据还在上下文里。本节省的是另一条——使用者的包已经落到 [feedback-sink.md](../../session-optimize/references/feedback-sink.md) 定的三条路径上,维护者跑 `refine-skill` 时把它们收进台账。路径、字段、状态、命令只以那份契约为准;这里只写台账这一侧。

扫本地时跳过 `status: forwarded` 的文件。权威副本在平台上,本地那份是投递痕迹。不跳过,同一份证据会被消费两次,`Recurrence-Count` 凭空多一,而判据三"第 2 次即可判系统性"直接吃这个计数。

去重完全靠台账。收件前查 `来源` 是否已记录该包的标识,命中就跳过——不 +1,不改条目。`来源` 记 sink 标识,形如 `<sink>#<id>`,与契约里 `sink` 字段同一形状。未投递的本地包 `sink` 是 `none`:`none` 不是标识,用它去重会把所有未投递的包当成同一份,这类包记文件名。

一个 feedback 包计一次。同一 `Pattern-Key` 下的 N 个包就是 N 次——它们来自 N 个会话,那正是判据三要的第 N 个数据点。把 N 个包合成 1 次,等于在收件侧做了投递侧明确禁止的查重,系统性永远升不上去。

消费后就地改,不删不移动。本地文件把 `status` 改为 `consumed`,并追加 `ledger: SKL-...`(收件方才写的第六个字段,值为本次写入或命中的台账 ID)。权威副本在平台上的,打 `consumed` label,评论里写同一 ID。label 和评论是给人看的凭证和第二层过滤,不承担去重职责。不得关闭:契约没有 `close`,收件只 `list` / `comment` / `label`;关掉就把计数依据藏进另一个列表。

就地标即可。文件留在原处,下次扫描凭 `status` 跳过,不指定给别的 skill 去清理。

第三步确认清单已经要说明台账记哪几条;消费项属于台账内容,列在对应条目旁边——每个待记 `Pattern-Key` 附上本次消费的包(sink 标识或本地文件名)。用户批准前能看见"+1 是因为哪一份",也能拦住 `来源` 里已经有的包。没有消费任何包就写"无",不要略过这一栏:略过和"忘了收件"分不开。

## 与 `evals/` 的分工

`evals/` 是测试集,回答"这个行为对不对";台账是计数器,回答"这个问题出现过几次"。不要把计数塞进 `evals.json` 的 `note` 字段:那会让一个文件同时承担两件事,而它们的生命周期不同——用例修好之后长期留着防退化,台账条目 `fixed` 之后只在复发时才被翻出来。
