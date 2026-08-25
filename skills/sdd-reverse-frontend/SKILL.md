\---

name: frontend-reverse

description: |

  Performs reverse engineering of frontend projects (Angular/React/Vue) to extract component inventory,

  infrastructure conventions, and coding patterns. Use when scanning frontend components, extracting

  component lists, performing frontend reverse engineering, analyzing frontend architecture, or generating

  coding paradigm templates. Triggers on: "前端逆向", "前端组件提取", "前端架构梳理", "组件清单",

  "扫描前端组件", "前端组件分析", "前端编码范式", "frontend reverse", "frontend components",

  "frontend conventions".

  Auto-detects framework from package.json and file patterns. Outputs to \<repo-root>/codespec/init/.

compatibility: Angular, React, Vue frontend projects

metadata:

  author: codespec

  version: "1.0"

\---

**# 前置条件**

**## 通用前置条件**

\- **\*\*⚠️ 技能启动时必须执行打点上报\*\***：\`codespec telemetry track --event-value "frontend-reverse"\`

**# 前端工程逆向提取**

跨 skill 共用的前端工程逆向扫描规则集，覆盖组件提取、基础设施扫描、样式/UI库识别、编码范式生成等能力。输入一个前端工程路径，自动识别框架、扫描组件与基础设施、生成编码范式模板，产出面向 AI Coding Agent 的精简导航文档。

**## 设计原则**

**\*\*框架自适应\*\***：从 \`package.json\` 依赖和文件后缀推断框架，不硬编码任何框架假设。识别优先级：依赖特征 > 文件特征 > 目录模式。若多个框架特征同时存在，以 \`package.json\` 的 \`dependencies\` 中直接声明者为准。

**\*\*渐进披露\*\***：输出是导航索引而非参考手册。优先级：组件路径锚点 > 公开接口签名 > 公共依赖 > 基础设施事实 > 编码范式占位。代码示例仅在非显而易见时提供。

**\*\*AI Agent First\*\***：每个信息单元必须回答"AI Agent 增量开发时何时需要此信息"。省略显而易见的框架默认行为、文件统计、标准注解。

**\*\*事实优先\*\***：只记录从代码中实际探测到的事实。无法自动推断的字段标注"需人工补充"，宁可留空也不填入不确定的内容。

\---

**## Phase 0: 框架识别与结构探测（必须首先执行）**

**### 0.1 框架识别**

从 \`package.json\` 依赖和文件后缀推断框架：

\| 框架 | 依赖特征 | 文件特征 | 组件目录模式 |

\|------|---------|---------|-------------|

\| Angular | \`@angular/core\` | \`\*.component.ts\` | \`src/app/\` |

\| React | \`react\` | \`\*.tsx\`, \`\*.jsx\` | \`src/components/\` |

\| Vue | \`vue\` | \`\*.vue\` | \`src/components/\` |

\`\`\`bash

Read: \<repo-root>/package.json -> dependencies / devDependencies

Glob: "\<repo-root>/src/\*\*/\*.component.ts"   # Angular

Glob: "\<repo-root>/src/\*\*/\*.tsx"            # React

Glob: "\<repo-root>/src/\*\*/\*.vue"            # Vue

\`\`\`

记录：\`{framework}\` = 识别结果，\`{componentPattern}\` = 组件文件匹配模式，\`{appRoot}\` = 应用根目录。

**### 0.2 应用根目录探测**

\`\`\`bash

\# Angular

Glob: "\<repo-root>/src/app/app.module.ts"

\# React

Glob: "\<repo-root>/src/App.tsx" 或 "\<repo-root>/src/App.jsx"

\# Vue

Glob: "\<repo-root>/src/App.vue"

\`\`\`

记录 \`{appRoot}\` = 应用根目录路径（如 Angular 为 \`src/app/\`，React/Vue 为 \`src/\`）。

**### 0.3 业务域/模块发现**

\`\`\`bash

\# Angular: 列出 app/ 下的业务模块目录（排除 shared/core/layout 等基础设施目录）

Glob: "\<repo-root>/{appRoot}/\*" -> 顶级目录

\# React/Vue: 列出 components/ 或 pages/ 下的业务目录

Glob: "\<repo-root>/{appRoot}/components/\*" 或 "\<repo-root>/{appRoot}/pages/\*"

\`\`\`

区分业务域目录与基础设施目录（shared、core、common、layout、auth、guard 等）。

**### 0.4 输出探测结果**

\| 维度 | 结果 |

\|------|------|

\| 框架 | {实际识别结果} |

\| 应用根目录 | {appRoot} |

\| 业务域数量 | {N} |

\| 基础设施目录 | {列出 shared/core/common 等} |

\---

**## Phase 1: 组件提取**

按框架执行组件扫描，提取每个组件的公开接口。

**### 1.1 组件发现**

\`\`\`bash

\# Angular

Glob: "\<repo-root>/{appRoot}/\*\*/\*.component.ts"

\# React

Glob: "\<repo-root>/{appRoot}/\*\*/\*.tsx"

\# Vue

Glob: "\<repo-root>/{appRoot}/\*\*/\*.vue"

\`\`\`

**### 1.2 公开接口提取**

按框架提取组件接口：

\| 框架 | 提取方式 |

\|------|---------|

\| Angular | \`@Input()\` / \`@Output()\` 装饰器 |

\| React | Props 类型定义（interface/type） |

\| Vue 3 | \`defineProps()\` / \`defineEmits()\` |

提取时需记录：属性名、类型、是否必填、默认值（如有）。对未标注类型的属性，标记为 \`any\` 并注明"需人工补充"。

**### 1.3 组件归属分类**

将组件分为：

\- **\*\*业务组件\*\***：位于业务域目录下，与特定功能关联

\- **\*\*公共组件\*\***：位于 shared/common/components 目录下，被多个业务域引用

\- **\*\*布局组件\*\***：位于 layout 目录下，负责页面框架

**### 1.4 输出组件清单**

按业务域分组输出，格式见 \`references/output-templates.md\` 的 frontend-components 部分。

\---

**## Phase 2: 公共依赖提取**

识别被两个及以上组件引用的公共模块。单组件私有的工具函数不纳入公共依赖表。

**### 2.1 按框架识别公共模块类型**

\| 类型 | Angular | React | Vue |

\|------|---------|-------|-----|

\| 工具函数 | util/service | util | util/composable |

\| 服务 | \`@Injectable\` | service | composable |

\| 指令 | \`@Directive\` | — | directive |

\| 管道 | \`@Pipe\` | — | — |

\| 守卫 | \`@Injectable\` + CanActivate | HOC/wrapper | router guard |

\| 组合函数 | — | hook | composable |

**### 2.2 公共依赖发现**

\`\`\`bash

\# Angular: 搜索 @Injectable, @Directive, @Pipe

Grep: "@Injectable|@Directive|@Pipe" (include: "\*.ts", path: \<repo-root>/{appRoot}/shared|core|common)

\# React: 搜索 hooks 和 util

Glob: "\<repo-root>/{appRoot}/\*\*/hooks/\*.ts" 或 "\<repo-root>/{appRoot}/\*\*/util/\*.ts"

\# Vue: 搜索 composables

Glob: "\<repo-root>/{appRoot}/\*\*/composables/\*.ts"

\`\`\`

**### 2.3 引用计数**

对每个发现的公共模块，统计被引用次数。仅保留被 2 个及以上组件引用的模块。

**### 2.4 输出公共依赖表**

格式见 \`references/output-templates.md\` 的公共依赖部分。类型列区分：util / service / directive / pipe / composable / guard。

\---

**## Phase 3: 基础设施扫描**

**### 3.1 路由配置**

\`\`\`bash

\# Angular

Grep: "RouterModule.forRoot|RouterModule.forChild|loadChildren" (include: "\*.ts")

\# React

Grep: "\<Routes|\<Route|createBrowserRouter" (include: "\*.tsx","\*.jsx")

\# Vue

Grep: "createRouter|useRouter" (include: "\*.ts","\*.vue")

\`\`\`

记录：路由定义位置、路由守卫、懒加载策略。

**### 3.2 HTTP 封装**

\`\`\`bash

Grep: "HttpClient|axios.create|fetch\\(" (include: "\*.ts","\*.js")

\`\`\`

记录：封装位置、拦截器、错误处理模式。

**### 3.3 全局状态**

\`\`\`bash

\# Angular

Grep: "Store|@ngrx|NgRx" (include: "\*.ts")

\# React

Grep: "createStore|useContext|useReducer|Provider" (include: "\*.tsx","\*.jsx")

\# Vue

Grep: "createStore|useStore|Pinia|Vuex" (include: "\*.ts","\*.vue")

\`\`\`

记录：Store 定义位置、管理模式。

**### 3.4 权限机制**

\`\`\`bash

Grep: "guard|CanActivate|directive|HOC|middleware|permission" (include: "\*.ts","\*.tsx","\*.vue")

\`\`\`

记录：实现方式、粒度。

**### 3.5 样式与 UI 库**

\| 扫描项 | 识别方式 |

\|--------|---------|

\| CSS 预处理器 | 依赖特征：\`sass\`/\`less\`/\`stylus\`；文件特征：\`\*.scss\`/\`\*.less\`/\`\*.styl\` |

\| CSS-in-JS | 依赖特征：\`styled-components\`/\`emotion\`/\`@linaria\` |

\| 设计 token / 主题变量 | 搜索 \`theme\`/\`tokens\`/\`variables\` 目录或文件；CSS 自定义属性 \`var(--\` |

\| 第三方 UI 库 | 从 \`package.json\` 依赖识别：\`element-ui\`/\`ant-design\`/\`@angular/material\`/\`vant\` 等 |

\| 全局样式入口 | 搜索 \`styles.css\`/\`global.css\`/\`App.vue \<style>\` / \`index.less\` 等 |

扫描产出填入 \`frontend-conventions.md\` 的样式体系章节。若项目未使用任何预处理器或 UI 库，对应行标注"无"而非留空。

**### 3.6 工程化配置**

\| 扫描项 | 识别方式 |

\|--------|---------|

\| 构建工具 | 依赖特征：\`vite\`/\`webpack\`/\`@angular/cli\`/\`next\`；配置文件：\`vite.config.\*\`/\`webpack.config.\*\` |

\| 国际化方案 | 依赖特征：\`vue-i18n\`/\`react-i18next\`/\`@angular/localize\`；语言包目录：\`locales\`/\`i18n\`/\`lang\` |

\| 测试框架 | 依赖特征：\`jest\`/\`vitest\`/\`cypress\`/\`@testing-library\`；配置文件：\`jest.config.\*\`/\`vitest.config.\*\` |

\| 环境变量 | 搜索 \`.env\*\` 文件、\`import.meta.env\`/\`process.env\` 引用 |

扫描产出填入 \`frontend-conventions.md\` 的工程化配置章节。仅记录存在的事实，不推断未使用的工具。

\---

**## Phase 4: 输出**

写入 \`\<repo-root>/codespec/init/\` 目录（目录不存在则创建）。产出两个文件：

1\. **\*\*\`frontend-components.md\`\*\*** — 组件清单与公共依赖

2\. **\*\*\`frontend-conventions.md\`\*\*** — 基础设施与编码范式

**### 输出格式**

详见 \`references/output-templates.md\`。

**### 编码范式模板生成规则**

\| # | 规则 |

\|---|------|

\| G-1 | 生成带占位符的模板，占位符格式：\`<需人工补充>\` |

\| G-2 | 基础设施部分由自动扫描填入，编码范式部分全部标注占位符 |

\| G-3 | 模板中的项目名使用 \`<项目名>\` 占位，运行时替换为实际项目名 |

\| G-4 | 不臆测编码范式，宁可留空也不填入不确定的内容 |

**### 输出约束**

\- \`frontend-components.md\` 不超过 300 行

\- \`frontend-conventions.md\` 不超过 200 行

\- 编码范式部分全部标注 \`<需人工补充>\` 占位符，不臆测

\- 项目名使用实际项目名，不使用占位符

\---

**## EvidencePacket 降级**

前端组件提取本质是纯代码扫描，不依赖业务文档。EvidencePacket 中业务知识源（需求文档、设计稿等）为可选，代码仓库为必需。

\| # | 条件 | 处理方式 |

\|---|------|---------|

\| E-1 | 业务知识源不可用 | 允许跳过业务知识源检索，直接进入 Codebase 阶段 |

\| E-2 | \`code-repository-index.yaml\` 存在 | 读取工程入口，正常流程 |

\| E-3 | \`code-repository-index.yaml\` 不存在 | 宽松模式：从用户输入获取工程入口路径 |

\| E-4 | 用户未提供工程入口 | 提示用户输入项目根目录路径，不可跳过 |

\---

**## 增量更新规则**

\| # | 规则 |

\|---|------|

\| H-1 | 触发时机：当 \`codespec/init/frontend-components.md\` 已存在时，对比现有清单与实际代码，识别新增/删除/变更的组件 |

\| H-2 | 回写触发：代码变更完成后，按"回写预期"逐条确认 |

\| H-3 | 回写方式：追加条目到对应表格，不重扫全量 |

\| H-4 | 通用组件（位于 shared/common 目录下）→ 必须回写 |

\| H-5 | 业务组件 → 可选回写 |

\---

**## 停止条件**

\- \`package.json\` 不存在或无法识别框架：提示用户确认项目类型

\- 项目根目录无法确定：提示用户输入项目根目录路径

\- 代码仓库为空或无前端代码：输出原因并停止

\---

**## 扩展说明**

本规则集为基础版，覆盖 Angular / React / Vue 三大框架。项目若使用其他框架（如 Svelte、Solid），可在 \`architecture/codebase/\<project>/\` 下补充框架识别规则和接口提取规则，格式与本 guideline 表格一致。

\---

**## 禁止事项**

1\. **\*\*禁止伪造\*\*** — 必须从实际代码提取，探测不到的不编造

2\. **\*\*禁止硬编码路径\*\*** — 所有目录和模块名从实际结构动态发现

3\. **\*\*禁止输出显而易见信息\*\*** — 标准框架注解、默认行为不属于逆向产出

4\. **\*\*禁止跳过 Phase 0\*\*** — 必须先探测再提取

5\. **\*\*禁止臆测编码范式\*\*** — 编码范式部分全部标注"需人工补充"