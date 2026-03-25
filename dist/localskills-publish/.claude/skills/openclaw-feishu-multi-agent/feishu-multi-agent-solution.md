# OpenClaw + Feishu 多 Agent 协作方案

## 目标

在一个飞书群里，让四个独立 agent 协同工作：

- `Steve Jobs`：总调度
- `Jonathan Ive`：设计
- `Brendan Eich`：开发
- `Seth Godin`：运营 / COO

希望达到的效果：

1. `Steve Jobs` 能读取群内上下文，判断该由谁处理
2. `Steve Jobs` 能在群里显式 `@` 对应 agent
3. 被 `@` 的 agent 能主动回群
4. agent 之间可以继续自动串联讨论
5. 绕过飞书 “bot 不能互相接收 bot 消息” 的限制

---

## 核心结论

**可行，但不能靠飞书 bot 之间直接互相 @。**

真正可行的方案是：

- 飞书里的 `<at>` 只负责“让人看见谁被点名了”
- OpenClaw 里的 `sessions_send` 负责“真正唤醒另一个 agent”
- 目标 agent 再用自己的 `message` 工具把消息主动发回飞书群

换句话说：

**视觉上的 @ 用飞书做，真实的 bot-to-bot 协作用 OpenClaw 内部会话做。**

---

## 最终架构

### 1. 外部表现层：Feishu

飞书群里看到的是：

- `Steve` 发言
- `Steve` 显式 `<at>` 设计 / 开发 / 运营
- 各 agent 以自己的 bot 身份回群

### 2. 内部调度层：OpenClaw

真正的链路是：

1. 飞书消息进入 `Steve` 对应 session
2. `Steve` 判断需要谁参与
3. `Steve` 在群里发一条带 `<at>` 的消息
4. `Steve` 对每个目标发一次 `sessions_send`
5. 目标 agent 被唤醒后，直接用 `message` 回到飞书群
6. 如果目标 agent 还想拉别人参与，重复第 3-5 步

---

## 标准工作流

### A. Steve 收到新问题

Steve 先判断三件事：

1. 这件事值不值得做
2. 谁主答
3. 是否需要多人讨论

### B. Steve 需要拉人时

必须同时做两步：

1. 在飞书群发显式 `<at>`
2. 对目标 agent 发 `sessions_send`

示意：

```text
飞书群消息：
<at user_id="{jonathan_open_id}">Jonathan Ive</at>
<at user_id="{brendan_open_id}">Brendan Eich</at>
<at user_id="{seth_open_id}">Seth Godin</at>
请分别从设计、技术、运营角度给出判断。
```

```text
sessionKey: agent:designer:feishu:group:oc_xxx

message:
Steve 在群 oc_xxx 中需要你的意见。

请直接用 message 工具回复到飞书群：
  target: chat:oc_xxx
  accountId: designer

请从设计角度回答：
- ...

不需要回我，直接回群。
```

开发和运营同理。

### C. 其他 agent 收到内部投递后

目标 agent 应该：

1. 直接读任务
2. 必要时读相关文档
3. 用 `message` 直接回群
4. 如果需要继续拉别人：
   - 先在群里 `<at>` 对方
   - 再发 `sessions_send`

---

## 关键约束

### 飞书限制

飞书不会把一个 bot 发出的消息，再投递给另一个 bot。

所以以下做法都不够：

- 只发 `@设计`
- 只发 `@开发`
- 只发 `<at user_id="...">Jonathan Ive</at>`

这些都只是“看起来像叫了人”，不代表目标 agent 真收到。

### 正确原则

**每一次 agent 委派，都必须是：**

- 一次可视化 `@`
- 一次内部 `sessions_send`

少一步都不算成功。

---

## 角色分工

### Steve Jobs

- 默认总调度
- 负责判断值不值得做
- 负责判断谁来做
- 负责拉起多 agent 讨论
- 负责在讨论中做最后收束

### Jonathan Ive

- 负责设计、体验、视觉、交互
- 可以继续拉 `Brendan` 或 `Seth`

### Brendan Eich

- 负责技术判断、实现边界、架构
- 在需要时进入实现模式

### Seth Godin

- 负责运营、传播、定位、增长
- 在“团队一起讨论 / 其他人一起看”时应默认纳入

---

## 本次已完成的修复

### 1. 协议修复

已统一 `PROTOCOL.md`，明确：

- `<at>` 只是视觉层
- `sessions_send` 才是真实投递
- 支持链式 agent 讨论

### 2. 提示词修复

已修复 `Steve` 和团队 skill 的行为约束，避免系统退回旧的：

- 单 bot 多角色扮演
- 只发裸文本 `@PM/@设计/@开发`

### 3. 路由修复

已把广义团队召集默认解释为：

- `designer`
- `dev`
- `ops`

不再默认只叫设计和开发。

### 4. 会话修复

已修复 `Brendan Eich` 的一个群 session 被错误写成 `webchat` 的问题，恢复为标准 `feishu group` 上下文。

### 5. 运行态修复

已重启 OpenClaw gateway，使新配置生效。

---

## 曾出现过的典型问题

### 问题 1：Steve 只 @ 了设计和开发，没有 @ COO

原因：

- 旧规则里，“其他人讨论”被窄化理解成“设计 + 开发”
- 没把 `Seth Godin` 作为默认团队讨论成员纳入

处理：

- 已改为广义团队召集默认包含 `ops`

### 问题 2：Eich 好像收到了，但没回群

原因：

- `dev` 的群 session 被错误记录成 `channel=webchat`
- 导致它缺失正确的 Feishu 回投上下文

处理：

- 已改回 `channel=feishu`
- 已补齐 `target/chat/accountId` 等回投信息

### 问题 3：sessions_send 超时

这不一定表示没收到，可能表示：

- 被调 agent 正在长时间读文档 / 执行工具
- 内部 run 卡住
- 会话上下文不正确

需要结合 session 文件和 gateway log 一起判断。

---

## 当前残留风险

### 1. Hindsight 插件异常

当前日志里仍有 Hindsight memory 插件相关报错和启动超时。

它不是这次多 agent 协作的主因，但会污染运行态日志，增加诊断复杂度。

### 2. Feishu WebSocket 偶发 system busy

日志里有：

- `1000040350 system busy`
- `PingInterval` 相关报错

说明飞书连接层仍有偶发不稳定。

### 3. 安全风险

当前配置仍有：

- `groupPolicy=open`
- 凭据目录权限偏宽
- 多个 bot 与运行时能力暴露在同一实例里

如果后续要长期稳定使用，建议单独再做一轮安全收口。

---

## 推荐验证方法

在飞书群里测试以下话术：

```text
@Steve Jobs 让其他人一起讨论一下这个项目，分别从设计、技术、运营角度给我判断。
```

预期结果：

1. `Steve` 先发一条总调度消息
2. `Steve` 显式 `@ Jonathan`、`@ Brendan`、`@ Seth`
3. 三个 agent 分别独立回群
4. 如果某个 agent 继续拉另一个 agent，群里会再次出现新的显式 `@`
5. 被继续拉起的 agent 会再次主动回群

---

## 推荐后续动作

### 短期

1. 再做一轮真实飞书联调
2. 观察 `Steve -> designer/dev/ops` 是否都能稳定唤醒
3. 观察 `designer -> dev` 这类二跳委派是否稳定

### 中期

1. 收敛 Hindsight 插件问题
2. 升级 OpenClaw 到更新版本
3. 整理一份专门的“飞书多 agent 协作 SOP”

### 长期

1. 把群聊开放策略改成更严格的 allowlist
2. 收紧凭据目录权限
3. 把多 agent 协作和安全策略分开文档化

---

## 一句话总结

**这套方案能跑通的关键，不是让飞书 bot 互相 @，而是让 OpenClaw 在内部用 `sessions_send` 做真实投递，再由各自 bot 主动把消息发回飞书群。**
