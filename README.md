# moon-skills

面向 **Cursor / AI 辅助开发** 的一套**分析驱动工作流**：把需求澄清、设计验收、切片交付、检视、验证和复盘串成一条线，并把可复用结论落在仓库的 `.project-context/` 里，避免「每开一个新会话从零开始」。

---

## 安装

### 用 Cursor（推荐）

一键安装会把本仓库注册为 **Cursor 本地插件**，并自动安装 **`immune-debug` 所需的** `obra/superpowers` → `systematic-debugging`。需要本机已安装 **Git** 与 **Node.js（含 npx）**。

```bash
curl -fsSL https://raw.githubusercontent.com/CCharlesMeng/moon-skills/main/scripts/install-cursor-plugin-with-deps.sh | bash
```

装完后在 Cursor 里 **`⌘⇧P` → `Developer: Reload Window`**，再到 **Settings → Rules** 里确认插件已出现。

**若 `curl` 返回 404**：远程可能尚未包含该脚本，请先 `git pull` / 确认仓库已推送；或克隆后执行：

```bash
git clone --depth 1 https://github.com/CCharlesMeng/moon-skills.git "${TMPDIR:-/tmp}/moon-skills-install" \
  && MOON_SKILLS_CHECKOUT="${TMPDIR:-/tmp}/moon-skills-install" \
     bash "${TMPDIR:-/tmp}/moon-skills-install/scripts/install-cursor-plugin-with-deps.sh"
```

已克隆本仓库时，也可在仓库根目录执行：`bash scripts/install-cursor-plugin-with-deps.sh`。

可选环境变量：

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `MOON_SKILLS_REPO_URL` | 克隆地址 | `https://github.com/CCharlesMeng/moon-skills.git` |
| `MOON_SKILLS_CHECKOUT` | 插件根目录（已有时不再克隆） | `~/.local/share/moon-skills/checkout`（或 `XDG_DATA_HOME` 下等价路径） |
| `MOON_SKILLS_PLUGIN_NAME` | `~/.cursor/plugins/local/` 下的目录名 | `moon-skills` |

### 用 `npx skills`（不走 Cursor 插件时）

```bash
npx skills add CCharlesMeng/moon-skills
```

查看可安装的 skill：`npx skills add CCharlesMeng/moon-skills --list`  
若未使用上文一键脚本，**建议**再安装排障依赖：

```bash
npx skills add obra/superpowers --skill systematic-debugging
```

---

## 怎么用（复制即用）

按需把下面整句丢给 AI（把 `<模块>`、`<问题>` 换成你的实际情况）。

```
# 首次接手仓库
请用 initialize 为这个仓库建立首版上下文。

# 每次开发前预热
请用 sync-context 为 <模块> 做开发前预热。

# 需求分析
请完成 analysis-spec。

# 设计验收（复杂需求时 AI 会按 skill 走多阶段确认）
请基于 analysis-spec 产出 design-pack。

# 交付切片
请基于 analysis-spec 产出 slice-plan。

# 实现后的代码检视
请用 code-review 检视当前 slice 的代码。

# 行为验证（有测试与证据再收口）
请用 verify 验证当前 slice。

# 和规格对账
请做 spec-check，逐条对账 analysis-spec 和最终交付。

# 本轮复盘
请用 audit 做本轮交付的 post-ship reflect。

# Bug / 回归
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
```

---

## 技能是干什么的

| 你对 AI 说的方向 | Skill | 典型作用 |
| --- | --- | --- |
| 建首版仓库记忆 | `initialize` | 生成 `.project-context/` |
| 开发前对齐上下文 | `sync-context` | 预热、增量同步 |
| 把需求变成可验收行为 | `analysis-spec` | 产出 TB 等规格输入 |
| 验收标准、测试思路、工作量 | `design-pack` | AC / TC / ADR 等（多阶段确认） |
| 拆成可交付切片 | `slice-plan` | 切片 + 关联 TC |
| 按规则检视代码 | `code-review` | 结构化检视结论 |
| 用证据核对是否做对 | `verify` | TC 与证据（EV） |
| 和最初规格对齐吗 | `spec-check` | TB 对账 |
| 复盘与上下文治理 | `audit` | 沉淀与治理 |
| 事故与防护 | `immune-debug` | 根因 + 免疫决策 |

整体顺序大致是：**initialize → sync-context → analysis-spec →（需要时 design-pack）→ slice-plan → 实现 → code-review → verify → spec-check → audit**；出事走 **immune-debug**。

---

## 工作流一眼看懂

```
初始化 → 预热 → 需求分析 →（设计验收包）→ 切片 → 实现 → 检视 → 验证 → 规格对账 → 复盘
                                                      ↑
                                            结论写入 .project-context/ 供下次复用
```

规格里常出现 **TB**（目标行为）、**AC**（验收标准）、**TC**（怎么测）、**EV**（证据）等缩写；细节不必背，跟着 skill 输出即可。

---

## 想深入了解

- **方法、门禁、模式与完整示例**：[analysis-driven-sdd.md](analysis-driven-sdd.md)  
- **和 AI 对话时的输出规范（确认门、表格优先等）**：[PRINCIPLES.md](PRINCIPLES.md)  
- **Cursor 插件说明（市场、团队分发等）**：[Cursor 插件文档](https://cursor.com/cn/docs/plugins)
