# profile.yaml Schema 指南

`profile.yaml` 是仓库级上下文的机器可读主索引。

它应该稳定、浅层、可再生，并且只承担“导航”和“定位”的职责。

## 设计原则

- 优先记录仓库事实，而不是主观解释
- 优先稳定标识与路径，而不是长篇 prose
- 优先模块边界和关键 flow，而不是内部实现细节
- 显式记录 freshness、provenance、confidence、uncertainty
- 允许未知项存在，不要为了完整而猜

## 建议结构

```yaml
version: 1
generated_at: 2026-03-17T00:00:00Z
source_commit: abc1234
generator: initialize

repo:
  name: example-repo
  type: monorepo
  summary: 面向用户的前端仓库

context:
  domains:
    - commerce
    - account
  stacks:
    - react
    - vite
    - node

modules:
  - id: web-app
    path: apps/web
    kind: app
    domain:
      - commerce
    stack:
      - react
      - vite
    summary: 面向消费者的 Web 主应用
    entry_points:
      - apps/web/src/main.tsx
    critical_flows:
      - checkout
      - login
    confidence: medium
    signals:
      - hotspot

  - id: shared-ui
    path: packages/shared-ui
    kind: package
    domain: []
    stack:
      - react
    summary: 共享组件库
    entry_points: []
    critical_flows: []
    confidence: high
    signals: []

uncertainty:
  - 历史价格计算逻辑分散在多个 util 中，暂未完全归类
```

## 最低要求

至少应支持：

- `version`
- `generated_at`
- `source_commit`
- `generator`
- `repo.name`
- `repo.type`
- `modules[].id`
- `modules[].path`
- `modules[].kind`
- `modules[].summary`
- `modules[].confidence`
- `uncertainty`

如果仓库足够复杂，建议再补：

- `context.domains`
- `context.stacks`
- `modules[].entry_points`
- `modules[].critical_flows`
- `modules[].signals`

## 适合放什么

适合放进 `profile.yaml` 的内容：

- 仓库身份
- 仓库类型
- 主要模块与路径
- domain / stack 提示
- 入口点
- 关键 flow
- confidence / uncertainty
- freshness / provenance

## 不要放什么

不要把 `profile.yaml` 变成：

- 完整架构文档
- feature tree
- 依赖清单垃圾桶
- 组件 catalog
- 教程型 onboarding 文档
- 源码替代品

这些内容应分别进入：

- `references.yaml`：共享参考模式
- `features/index.yaml`：关键特性索引
- `PROFILE.md`：人类可读摘要

## 写法建议

- `summary` 保持一到两句话，不写长段说明
- `signals` 只写高价值信号，例如 `hotspot`、`legacy`、`needs-sync`
- `critical_flows` 只写后续任务经常会碰到的 flow
- `uncertainty` 明确写出不知道什么，而不是模糊地说“有点复杂”
