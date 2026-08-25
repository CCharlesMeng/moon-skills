# moon-skills

面向 **Cursor / AI 辅助开发** 的一套 **前端 SDD（规格驱动开发）skill**：把一个前端需求从「仓库初始化 → 实现计划 → Story 执行 → 检视」串成一条带证据的链路，另附两个会话级复盘工具。

---

## 安装

### 用 Cursor（推荐）

一键安装会把本仓库注册为 **Cursor 本地插件**。需要本机已安装 **Git**。

```bash
curl -fsSL https://raw.githubusercontent.com/CCharlesMeng/moon-skills/main/scripts/install-cursor-plugin.sh | bash
```

装完后在 Cursor 里 **`⌘⇧P` → `Developer: Reload Window`**，再到 **Settings → Rules** 里确认插件已出现。

### 用 `npx skills`（不走 Cursor 插件时）

```bash
npx skills add CCharlesMeng/moon-skills
```

查看可安装的 skill：`npx skills add CCharlesMeng/moon-skills --list`

---

## 技能是干什么的

### 前端 SDD 链路

| Skill | 作用 | 产出 |
| --- | --- | --- |
| `sdd-init-frontend` | 扫描前端仓，定出栈与仓库形态，把机器准备到能装、能起、能跑质量命令 | 按消费者问句分类的九份仓库级 baseline |
| `sdd-task` | 按 `requirement-design.md` 逐仓创建 Story 级实现计划 | `tasks.md`、`alpha-tests.md` |
| `sdd-task-frontend` | 前端仓的实现计划：实现位置、每个文件的职责、验收声明与风险事实 | `tasks.md`、`alpha-tests.md` |
| `sdd-dev-frontend` | 执行单个 Story：冻结验收基线、实现 tasks、按声明与风险编译最小充分验证 | 代码 + 可追溯证据 |
| `sdd-review-frontend` | 按 restore / layout / convention / quality / test 五格独立 lens 检视前端改动 | 分格 Finding 与定级 |

典型顺序：**`sdd-init-frontend` →（`sdd-task` →）`sdd-task-frontend` → `sdd-dev-frontend` → `sdd-review-frontend`**。`sdd-init-frontend` 只在首次接入或仓库 baseline 缺失时跑；`sdd-review-frontend` 是被调用的检视包，由 `sdd-dev-frontend` 的检视阶段派发，也可单独用于 PR 检视。

### 会话工具

| Skill | 作用 |
| --- | --- |
| `session-optimize` | 复盘本次会话的真实失败，沿失败层地图定位最早的可控边界，产出待批准的改进提案与跨边界移交 |
| `refine-skill` | 会话末尾复盘某个 skill 本次执行出的错，改写它避免重犯 |

---

## 想深入了解

设计与治理文档在 `docs/skills/` 下；**agent 运行期要读的规则一律在 `skills/` 内**，这样 skill 被单独安装时也拿得到：

- **[执行契约](skills/sdd-dev-frontend/references/execution-contract.md)** — `sdd-task-frontend` 与 `sdd-dev-frontend` 的唯一共享事实源（所有权、分层边界、声明状态、TaskPacket）；随 `sdd-dev-frontend` 分发，计划侧按兄弟 skill 路径引用同一份
- **[接缝契约](docs/skills/frontend-sdd/接缝契约.md)** — 跨文件接缝的注册表：ID 命名空间、门禁编号、产物路径
- **[模块与评测](docs/skills/frontend-sdd/模块与评测.md)**、**[基线分数](docs/skills/frontend-sdd/基线分数.md)** — 脚本与 evals 的覆盖情况和实测基线
- **[sdd-dev-frontend 使用说明](docs/skills/sdd-dev-frontend/README.md)** — 使用者视角的完整流程说明
- **[PRINCIPLES.md](PRINCIPLES.md)** — 和 AI 对话时的输出规范（确认门、表格优先等）
- **[Cursor 插件文档](https://cursor.com/cn/docs/plugins)** — 市场、团队分发等

改动前端链路的任何文件后，跑一次接缝一致性检查：

```bash
node tests/check-consistency.mjs
```
