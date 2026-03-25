# Vendored Superpowers Skills

这里保存为了“一键安装开发流程 skill 套件”而 vendoring 进仓库的 `superpowers` 基础 skill。

当前包含：

- `brainstorming/`
- `systematic-debugging/`

这些目录会被 `scripts/install_workflow_skills.py` 直接复制到目标 skill 目录中，保持原始目录名不变，以避免 sibling 文档和脚本引用失效。
