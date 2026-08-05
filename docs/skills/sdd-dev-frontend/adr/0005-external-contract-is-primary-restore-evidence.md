---
status: accepted
---

# 外部设计契约成为还原失败的主要证据，截图退为选择性观察手段

[ADR-0001](0001-restore-uses-diff-list-as-red-evidence.md) 决定还原类工作不用橡皮图章式 DOM 测试，而以外部原型差异作为 RED。它解决了“判据从哪里来”，但当时默认每轮以双方截图逐项指认：机器可精确判断的结构、文案、计算样式和几何值仍依赖主观观察，页面起不来时又容易把源码级对照误写成视觉 GREEN。

我们保留 ADR-0001 的外部基线原则、R1–R6、QA 基线确认门和六步 RED/GREEN 语义，同时把主要失败证据升级为 **Story 级冻结 `restore-contract.json` 的机器报告**：

- `design-facts.json` 保存 Requirement 级原型事实和覆盖资源内容/缺失状态的原型指纹；
- `restore-contract.json` 是已冻结 `dev-baseline.md` 中 R1–R6 的机器镜像，并保存后者的内容哈希；
- `restore-report-red.json` / `restore-report-green.json` 由同一契约执行生成，单条状态只有 `red`、`yellow`、`green`；
- 静态预检、结构化渲染能判定的规则不截图；只有阴影观感、字体栅格、图片裁切、复杂叠层等机器盲区进入视觉补证。

## Considered Options

- **保留每轮双方截图**：改动最小，但机器可判项继续依赖主观观察，无法稳定复跑。
- **做像素级自动 diff**：统一但误报高，字体栅格、浏览器版本和资源缺失会把环境差异放大成产品偏差，首版成本也超出本 skill 的依赖边界。
- **只加 JSON 文档，不实现执行器**：格式看似完整，实际仍由 Agent 人肉解释，无法形成可执行闭环。

## Consequences

- 还原轮 Step ① 与 Step ④ 必须运行同一份冻结契约；`dev-baseline.md` 哈希不一致时硬失败。
- 有 RED 即整体 RED；无 RED 但有 YELLOW 即整体 YELLOW；全部规则已验证或命中冻结豁免才 GREEN。YELLOW 不得冒充 GREEN。
- 页面不可用时只允许静态支持项得出结果；render-required 规则保持 YELLOW。页面可用但结构化采集已经尝试并失败，则是执行失败，判 RED。
- 视觉缓存只有存在 YELLOW 视觉项时才生成；缓存键覆盖原型指纹、区块、视口、DPR、浏览器引擎/版本和字体指纹，命中只读复用，失配创建新目录而不覆盖旧版本。
- `alpha-tests.md` 继续是唯一证据账本，只登记报告指纹、路径、摘要、视觉缓存引用及可选截图；不复制完整机器报告。
- Phase C 布局检视暂不复用结构化采集能力。本决策只改变 Phase B 还原轮。
- 已有 Story 没有 `restore-contract.json` 时继续识别 ADR-0001 的旧截图证据格式，不要求迁移历史证据。
