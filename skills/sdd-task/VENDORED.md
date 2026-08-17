# `sdd-task` 是 vendored 副本，只允许改路由

本目录是部门维护的上游 `sdd-task` skill 的**手工复制副本**。

| 项 | 值 |
| --- | --- |
| 上游版本 | `3.2`（取自本目录 `SKILL.md` frontmatter 的 `metadata.version`） |
| 上游归属 | 部门，`metadata.author: codespec` |
| 来源提交 | **未知——复制时没有记录**，本仓无法反查 |
| 复制日期 | **未知——复制时没有记录** |
| 本仓所有权 | 仅限路由分支（见下） |

来源提交与复制日期是一个已知缺口，不是待填的占位符：不要凭 `git log`、文件 mtime 或版本号推算一个值填进去。要闭合这个缺口，只能向上游要到确切提交号后再回填。

## 本仓授权的唯一改动：前端路由

`SKILL.md` 的 **Step 2.4 前端路由**是本仓有意加入的改动，把 `type=frontend` 的行整行交给 `skills/sdd-task-frontend/`。配套的四处一行标注（Step 2 分流注释、Step 2.5 / 2.6 / Step 4 的「已路由则跳过」、完成标准的 frontend 行）同属这一改动。

边界很窄，越界就是过度改动：

- **只改分流，不改语义。** 通用生命周期、`codespec` CLI 用法、命名与变更识别、提交规范、后端行的任何规则一律照抄上游。
- **后端零影响是回归底线。** 用一个纯后端 Story 生成 `tasks.md`，产出必须与加路由前逐字一致。
- **前端内联路径保留为兜底**，不删。`sdd-task-frontend` 不可用时仍按 Step 2.5～2.6、Step 4 执行并标降级。
- 目录内其余既有内容照抄上游保留，**包括看起来像笔误的部分**（例如 ` templates/` 目录名带前导空格）。

## 前端规则的归属已经变了

这两份文档原本是「写成说明书，由使用者带到上游照着改」的需求书。上游一直没有落地，而现在前端行不再经过上游生成计划，**它们的执行责任已转入 `skills/sdd-task-frontend/`**：

| 文档 | 主题 | 现在的定位 |
| --- | --- | --- |
| `skills/sdd-dev-frontend/references/sdd-task-amendments.md` | `tasks.md` Step ① 失败证据扩展为两种形态 | 设计依据；执行落在 `sdd-task-frontend` Step 7 |
| `skills/sdd-dev-frontend/references/sdd-task-frontend-split.md` | 前端 Story 的任务拆分口径 | 设计依据；执行落在 `sdd-task-frontend` Step 6 |

**不要再为前端规则写新的上游说明书。** 前端专有规则直接进 `sdd-task-frontend`。只有需要改动通用主干（后端行、CLI、命名、提交规范）时才走上游说明书这条路。
