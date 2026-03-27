# Standalone Skills

这里存放不属于前端开发流程主链、但可以独立分发和维护的单个 skill。

推荐安装方式不是手动拷目录，而是从仓库根执行 `./setup`，按 bundle 安装。

这里的 standalone bundle 不依赖 `superpowers` 官方安装渠道；是否启用 official-first 只影响 workflow 里那些 process skills 的来源选择。

例如，只安装当前唯一的 standalone skill：

```bash
./setup --host auto --bundle openclaw-feishu-multi-agent --write
```

如果你已经把仓库 clone 到另一个项目的 `.agents/skills/moon-skills`，更新时可在宿主仓库根执行 `bash .agents/skills/moon-skills/install.sh ...`（会先 `git pull`），或见主 README 的 `curl ... install.sh` 用法。

```bash
cd .agents/skills/moon-skills && ./setup --host auto --bundle openclaw-feishu-multi-agent --write
```

当前包含：

- `openclaw-feishu-multi-agent/`：OpenClaw + 飞书多 agent 协作 skill bundle

主链开发流程 skill 仍保留在 `skills/`。
