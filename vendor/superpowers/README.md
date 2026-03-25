# Vendored Superpowers Skills

这里保存为了 workflow 安装链路兜底而 vendoring 进仓库的 `superpowers` 基础 skill。

当前包含：

- `brainstorming/`
- `systematic-debugging/`
- `writing-plans/`
- `subagent-driven-development/`
- `executing-plans/`
- `test-driven-development/`
- `verification-before-completion/`
- `using-git-worktrees/`
- `requesting-code-review/`
- `finishing-a-development-branch/`

默认安装优先级是：

1. 复用目标宿主或本机标准 skills 根里已存在的官方 superpowers skill
2. 尝试通过官方渠道安装 `obra/superpowers`
3. 只有官方安装不可用或失败时，才回退到这里的 vendored skill

这些目录通过仓库根的 `./setup --bundle workflow` 作为 fallback materialize 到目标宿主的 skills 根目录中，保持原始目录名不变，以避免 sibling 文档和脚本引用失效。
