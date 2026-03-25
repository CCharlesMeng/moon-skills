# Vendored Superpowers Skills

这里保存为了“一键安装开发流程 skill 套件”而 vendoring 进仓库的 `superpowers` 基础 skill。

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

这些目录现在会通过仓库根的 `./setup --bundle workflow` 一起 materialize 到目标宿主的 skills 根目录中，保持原始目录名不变，以避免 sibling 文档和脚本引用失效。
