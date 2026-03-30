# moon-skills

面向前端仓库的 AI workflow skills 集合，重点解决上下文建立、需求分析、切片规划、交付对账与事故调试。

## Included Skills

- `initialize`
- `sync-context`
- `immune-debug`
- `audit`
- `analysis-spec`
- `slice-plan`
- `spec-check`

## Installation

安装整个仓库：

```bash
npx skills add ccharlesmeng/moon-skills
```

只安装单个 skill：

```bash
npx skills add ccharlesmeng/moon-skills --skill analysis-spec
```

先查看仓库内可安装的 skills：

```bash
npx skills add ccharlesmeng/moon-skills --list
```

## Superpowers Dependency

这个仓库现在只发布以上 7 个 first-party workflow skills。

`npx skills add` 只会发现标准 skills 目录，不会把其他 vendored 目录一起安装，所以如果你要使用依赖 `superpowers` 的流程，建议额外安装官方仓库：

```bash
npx skills add obra/superpowers
```

如果你只需要 `immune-debug` 依赖的基础调试流，最小安装即可：

```bash
npx skills add obra/superpowers --skill systematic-debugging
```

## Quick Use

```markdown
请用 initialize 为 <模块> 的 <功能> 建立第一版可开发上下文。
请用 sync-context 为 <模块> 的 <功能> 做开发前预热。
请完成 analysis-spec：准备 → 摸底 → 自学习 → 澄清 → 规格，产出 analysis-spec.md。
请基于 analysis-spec 产出 slice-plan，每个 slice 写清验证方式和回滚边界。
请做 spec-check，逐条对账 analysis-spec 和最终交付。
请用 immune-debug 处理这个 <问题>，并给出免疫决策。
请用 audit 审查当前 `.project-context` 资产，重点看 <范围> 是否失真。
```

## Repository Layout

- `skills/`: first-party workflow skills
- `analysis-driven-sdd.md`: 方法论文档

## Notes

- `reflect` 不单独建立 skill 目录，而是通过 `audit`、`sync-context`、`immune-debug` 的路由协作实现。
- 独立的集成类或正交能力 skill 已迁移到其他仓库维护，这里只保留 workflow 主链。