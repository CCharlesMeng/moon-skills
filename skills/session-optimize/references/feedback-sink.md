# 投递：证据包去哪

[handoff-prompt.md](handoff-prompt.md) 定证据包写什么、落盘长什么样；本文件定它去哪。投递侧（`session-optimize` 的执行者）、收件侧（维护者跑 `refine-skill`）和部署方（写投递配置的人）以本文件为唯一事实源。

## 路由

`SKILL.md` 第 6 节的判据问**本会话在开发目标 skill 还是在使用它**（角色）；本文件的判据问**目标 skill 的源仓在不在当前仓库内**（位置）。两者正交，先答角色：答"使用"才继续问位置，答"开发"时证据还在上下文里，不落盘。在源仓里使用某个 skill 仍然算"使用"。

### 源仓探测

```bash
skill_path=$(readlink -f "<skill 安装路径>" 2>/dev/null || echo "<skill 安装路径>")
src_repo=$(git -C "$(dirname "$skill_path")" rev-parse --show-toplevel 2>/dev/null)
cur_repo=$(git rev-parse --show-toplevel 2>/dev/null)
```

`$src_repo` 非空且等于 `$cur_repo` → 源仓在当前仓库内；否则按公共 skill 处理。

三行照抄，`readlink -f` 必须保留：skill 常以符号链接部署，链接本身位于消费仓库内，不先解析链接会把每个 symlink 部署都判成"源仓在当前仓库内"。`$src_repo` 或 `$cur_repo` 为空（探测不出源仓，或当前目录不在任何仓库里）时按"不在"处理。

## 三条投递路径

| 路径 | 触发条件 | 落到哪 | git 归属 |
| --- | --- | --- | --- |
| 当前仓 | `$src_repo` 非空且 `= $cur_repo` | `<cur_repo>/.learnings/skill-feedback/` | 进 git，同事可见 |
| 外部 issue | 源仓不在当前仓库内，且配置把该 skill 列进白名单 | issue 为权威副本，本地留一份在用户级目录 | issue 在平台上，本地副本不在任何仓库 |
| 用户级 | 源仓不在当前仓库内，且无配置、不在白名单或投递失败 | `~/.learnings/skill-feedback/` | 不在任何仓库 |

目录不存在就先建（`mkdir -p`）。一个包一个文件，文件名见 [handoff-prompt.md](handoff-prompt.md)。

**永不跨仓库写入。** 探测解出了 `$src_repo` 的路径也不写进去——那个仓库不在本轮的批准范围里。报告里给出命令，由人自己执行：

```bash
cp ~/.learnings/skill-feedback/<包文件名> <源仓路径>/.learnings/skill-feedback/
```

## 状态机

顺序固定：**先落本地文件，再尝试投递。** 投递只改 front matter 的 `status` 和 `sink`。

| `status` | 谁写 | 含义 |
| --- | --- | --- |
| `pending` | 投递方 | 已落本地，未投出去。**它同时就是重试队列**——下次在同一台机器上跑 `session-optimize` 或维护者收件时，它还在那里 |
| `forwarded` | 投递方 | 已投成 issue，`sink` 记下标识。权威副本在平台上，收件方扫描本地目录时跳过它 |
| `consumed` | 收件方 | 已被 `refine-skill` 消费并记入台账，同时追加 `ledger: SKL-...`。就地改，不删不移动 |

front matter 的五个字段 `skill` / `status` / `created` / `pattern-key` / `sink` 由投递方写（取值见 [handoff-prompt.md](handoff-prompt.md)）；`ledger` 是第六个字段，只由收件方在消费时追加。

`sink` 形如 `<sink>#<id>`：`<sink>` 是配置声明的短标识，`<id>` 原样取自 `create` 的输出，投递方不自己拼装。未投递写 `sink: none`——`none` 是一个可 grep 的事实，留空和"忘了写"分不开。

## 部署方契约：`.feedback-sink.md`

配置是单一文件 `skills/session-optimize/.feedback-sink.md`，由部署方提供，不进 git（根 `.gitignore` 已有一条），打包分发时不包含它。一份管全仓：平台、仓库、CLI、认证对每个 skill 都一样，只有 label 随 skill 变，而这个差异由 `{{skill}}` 承担；按 skill 各配一份，改一次平台地址要改 N 处，漏掉的那几处只会在下一次使用时静默降级。收件侧读的是同一份，从 `refine-skill` 的目录看是 `../session-optimize/.feedback-sink.md`；两个 skill 没部署在同一个父目录下时这条相对路径断掉，那时按无配置处理。

**白名单**：`## skills` 小节一行一个名字，声明哪些 skill 的反馈投到平台。在名单上走 issue 投递；不在名单上与"无配置"同样处理，只落用户级目录。默认不投、列进来才投——投递把内容送出本仓，而不是每个 skill 的维护者都在这个平台上收件。

### 四条命令

`create` / `list` / `comment` / `label`，**没有 `close`**，全仓只写一份、所有白名单 skill 共用。投递方只调 `create`；收件方只调 `list`、`comment` 和打 `consumed` label，把 issue 留在打开状态——判据三要数复发次数，关闭等于把计数依据挪进另一个列表。

| 命令 | 谁调用 | agent 替换的占位符 | 输出如何使用 |
| --- | --- | --- | --- |
| `create` | 投递方 | `{{skill}}`、`{{body_file}}` | stdout 最后一行是 `<sink>#<id>`，原样存进 `sink` |
| `list` | 收件方 | `{{skill}}` | stdout 是 JSON 数组，元素含 `id` / `title` / `created` / `url` / `body` |
| `comment` | 收件方 | `{{id}}`、`{{body_file}}` | 不解析，只看退出码 |
| `label` | 收件方 | `{{id}}` | 不解析，只看退出码 |

`list` 返回的 `id` 必须和 `create` 输出里 `#` 之后的部分处在同一个标识空间，否则 `{{id}}` 传不回去。

**`create` 和 `list` 必须带 `{{skill}}`**——命令共享之后它是区分 skill 的唯一手段。`create` 里少了它，所有 skill 的反馈挤进同一个标签，收件方分不出哪一份是自己的；`list` 里少了它，维护者会把别的 skill 的包取回来，按自己 skill 的判据归因，`Recurrence-Count` 加到错的台账上。

某条命令缺失时，依赖它的那一侧按投递失败处理（投递方降级为只落本地，收件方报"该 sink 不可读"）。用别的命令代偿会在平台上多出一条看起来像新反馈的记录，把计数搞脏。

配置骨架如下：`sink` 短标识、白名单、四条命令各占一节，标题固定，命令在小节的代码块里一条一行。agent 按标题定位，不必理解平台。

````markdown
# 反馈投递配置

sink: <短标识，进 front matter 的 `sink` 字段>

## skills
- <skill-name>

## create
```bash
<一行命令，skill 以 {{skill}} 传入，正文以 {{body_file}} 传入>
```

## list
## comment
## label
````

### 四条硬要求

**一、命令完全具体。** 仓库名、label 名、认证参数、过滤条件全部由配置写死；agent 只做 `{{skill}}` / `{{body_file}}` / `{{id}}` 的字面替换，命令的其余部分原样执行，不现编平台语法。

**二、正文一律走文件路径。** 每条要传正文的命令都以 `{{body_file}}` 接一个路径（`--body-file <路径>` 这类形式）。证据包正文含反引号、换行和代码块，拼成 `--body "<正文>"` 会被转义或截断。

**三、stdout 契约。** `create` 成功时**最后一行**给出 `<sink>#<id>`——平台 CLI 常先打进度或告警，所以取最后一行而不是整段。`list` 的过滤条件里已写死"排除 `consumed` label"，agent 不加参数。

**四、失败判据与降级。** 退出码非 0 算失败；退出码为 0 但输出解析不出预期形状（`create` 拿不到标识、`list` 不是 JSON 数组）**也算失败**——凭据过期时 CLI 返回 0 并打一段登录提示是真实存在的行为，只看退出码会把"没投出去"记成 `forwarded`。失败后只留本地文件、`status` 保持 `pending`、在报告里说明；同一轮内不重试、不换命令、不改参数。

## 批准与去重

落盘与投递都走 `SKILL.md` 第 7 节的批准门，不享第 5 节台账的免批准豁免。投递是只移交清单里"外部系统"的窄口例外，三个条件见 `SKILL.md` 第 6 节，缺任一条就回到只落本地文件、报告里给人工转交说明。

**投递侧不查重。** 每次移交都新建，不查已有的 issue，也不合并已有的本地文件——同一个 `Pattern-Key` 的两个包来自两个会话，那正是判据三要的第 2 个数据点，在投递侧吞掉它，维护者手里永远只有 n=1。去重只发生在收件侧、按 `<sink>#<id>` 逐包判断（规则见 [skill-ledger.md](../../refine-skill/references/skill-ledger.md)）。

## 脱敏分级

投递改变了读者范围，所以在 [handoff-prompt.md](handoff-prompt.md) 那份脱敏清单之上分级：

| 路径 | 尺度 |
| --- | --- |
| 当前仓 | 可含本仓文件路径与代码摘录，读者与代码同权限。凭据、令牌、个人信息照旧不写 |
| 用户级 | 按外部 issue 同一标准——这个目录存在的目的就是等着被转交出去 |
| 外部 issue | 最严，且是提交前的硬门禁 |

外部 issue 那条是硬门禁，不是"拿不准就删"的建议：逐条过那份清单，任一项存疑就删掉并在「脱敏说明」里记明删了什么，检查结果在批准门上给用户看——投出去的内容可能进搜索索引，过了那个门就撤不回来。

## 失效可见

降级有两种情形，报告里的说法必须分开：配置文件不存在，写**未检测到投递配置，本次只落本地文件**；配置在而目标 skill 不在白名单，写**该 skill 未纳入投递，本次只落本地文件**。两种都只落用户级目录，都要接一句：这个目录只在使用者自己机器上、不同人之间拿不到，仍需人工转交。

分开写是因为两边要做的事不同：前者是配置被同步覆盖或解包误删，属故障，补回配置就恢复；后者是部署方的选择，属预期，要投就先把该 skill 加进名单。混成一句，使用者会去修一个没坏的东西，或者把故障当成"本来就不投"放过去。而这两句也就是唯一的安全网，且够了：两种情形都会在下一次使用时暴露，期间的反馈都还在本地 `pending`；少了它，使用者以为投出去了，维护者那边一直没有新 issue，两边都不会主动去查。

## 超期

`refine-skill` 收口时报一句：三条路径下还剩几个未消费，其中几个**超期**。

超期指未消费的收件项，其 `created` 距今超过 **30 天**。本地文件取 front matter 的 `created`，issue 取 `list` 输出的 `created`；一律不取文件 mtime——同步、复制、格式化都会刷新 mtime。
