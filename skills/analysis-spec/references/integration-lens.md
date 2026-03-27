# 集成检查清单

适用信号：需求跨两个以上边界或存在联动契约。

## 检查项

- [ ] 输入输出契约和版本边界
- [ ] 错误链路和依赖失败时的降级路径
- [ ] 回滚边界是否跨团队
- [ ] 是否需要 feature flag、灰度或 staged rollout
- [ ] 哪些验证必须跨边界一起完成

## 定制

要修改本检查清单，复制本文件到 `.project-context/lenses/integration.md` 并编辑。同名文件仓库版本优先于 skill 默认。不要直接修改本文件。

要新建检查清单，参考 [lens-template.md](lens-template.md)。
