# 测试框架探测指南

> sdd-task 在生成 tasks.md 前，对目标代码仓执行测试框架探测，将结果写入 TaskPacket 头的 `test_framework` 字段。
> 探测结果决定 tasks.md Step 1 RED 测试代码的框架选型。**不假设任何微服务使用什么框架**——以仓内代码事实为准。

## 0. 探测原则

- **以代码事实为准**：扫描构建文件依赖声明 + 测试目录结构 + 已有测试文件模式，不凭记忆猜测。
- **后端：主框架 + 辅助框架**：优先识别集成测试框架（用于 L3 API 接口级测试），辅助识别单测框架（用于 L4 UT）。
- **前端：组件通道 + 浏览器通道**：两条通道分别探测、分别记录，互不代替。组件通道跑在 jsdom 一类的模拟 DOM 里，浏览器通道驱动真实浏览器。**Cypress/Playwright 属于浏览器通道，不得被当作组件测试主框架**——一个只装了 Cypress 的仓库没有组件测试能力，反之亦然。
- **能力状态与框架身份分字段**：状态字段只写 `available` / `absent` / `unknown`，框架字段只写真实框架名。不把 `未识别`、`none-confirmed` 这类状态值塞进框架字段——那会让下游无法区分「探测过但没有」和「框架叫这个名字」。
- **探测失败即 Stop**：仓内无任何可识别测试框架信号时 Stop 回流 Design，不得默认 JUnit/Jest。

## 1. 后端测试框架探测

### 1.1 构建文件扫描信号

| 构建文件 | 扫描目标 | 识别信号 | 推断框架 |
|----------|---------|---------|---------|
| pom.xml | `<dependencies>` / `<dependencyManagement>` | `junit-jupiter`（org.junit.jupiter） | JUnit5 |
| pom.xml | `<dependencies>` | `junit`（无 jupiter，org.junit） | JUnit4 |
| pom.xml | `<dependencies>` | `mockito-core` / `mockito-junit-jupiter` | Mockito |
| pom.xml | `<dependencies>` | `spock-core` / `groovy-all` | Spock |
| pom.xml | `<dependencies>` | `testng` | TestNG |
| pom.xml | `<dependencies>` | `karate-junit5` / `karate-core`（com.intuit.karate） | Karate |
| pom.xml | `<dependencies>` | `rest-assured`（io.rest-assured） | RestAssured |
| pom.xml | `<dependencies>` | `spring-boot-starter-test` | Spring Boot Test（含 JUnit5 + Mockito） |
| pom.xml | `<dependencies>` | `archunit`（com.tngtech.archunit） | ArchUnit（架构测试） |
| build.gradle / build.gradle.kts | `dependencies` / `testImplementation` | 同上信号 | 同上 |
| go.mod | `require` | `github.com/stretchr/testify` | testify |
| go.mod | `require` | `github.com/smartystreets/goconvey` | GoConvey |
| build.gradle | `dependencies` | `org.jetbrains.kotlin:kotlin-test` | Kotlin Test |

### 1.2 测试目录结构扫描

| 目录模式 | 推断框架 | 用途 |
|----------|---------|------|
| `src/test/java/**/karate/` + `*.feature` | Karate 集成测试（主力） | L3 API 接口级 |
| `src/test/resources/karate/features/**/*.feature` | Karate feature 文件目录 | L3 API 接口级 |
| `src/test/java/**/*Test.java` | JUnit 单测 | L4 UT |
| `src/test/java/**/*Spec.groovy` | Spock 单测 | L4 UT |
| `src/test/java/**/*IT.java` | JUnit 集成测试 | L3 |
| `src/test/java/**/architecture/` | ArchUnit 架构测试 | 架构合规 |

### 1.3 后端双轨测试识别规则

当仓内同时存在集成测试框架（Karate/RestAssured）和单测框架（JUnit/Spock）时：
- **主框架** = 集成测试框架（Karate > RestAssured > Spring Boot Test），用于 L3 API 接口级测试
- **辅助框架** = 单测框架（JUnit5+Mockito / Spock），用于 L4 UT
- tasks.md Step 1 RED：L3 用例优先用主框架（如 Karate feature 文件）；L4 UT 用辅助框架（如 JUnit5+Mockito）
- 参照仓内已有测试文件的模式（如已有 `AgentDataApiKarateTest.java` + `*.feature`，新测试沿用此模式）

### 1.4 后端探测结果输出格式

```
test_framework=JUnit5+Mockito+Karate
test_dir=src/test/java/com/.../adapter/,src/test/resources/karate/features/
integration_test_pattern=Karate(*.feature)
unit_test_pattern=JUnit5(*Test.java)
```

## 2. 前端测试框架探测

### 2.0 两条通道的划分

前端探测输出两组独立结论，不合并成一个「主框架」：

| 通道 | 运行环境 | 能证明什么 | 典型框架 |
|------|---------|-----------|---------|
| **组件通道** | jsdom / happy-dom 等模拟 DOM | 组件挂载、交互、条件渲染、请求参数、三态 | Jest、Vitest、Mocha、Jasmine、Angular TestBed，配合 Testing Library / Vue Test Utils |
| **浏览器通道** | 真实浏览器 | 完整用户路径、跨页导航、真实布局与运行时 | Playwright、Cypress |

两条通道各自独立判定 `available` / `absent` / `unknown`。**一条通道存在不能推断另一条存在**：只装 Vitest 的仓库没有浏览器通道；只装 Cypress 的仓库没有组件通道。历史上把 Cypress 当成「集成能力最强的主框架」是错的，它证明不了组件级断言。

### 2.1 package.json 扫描信号

| 扫描目标 | 识别信号 | 推断框架 | 通道 |
|----------|---------|---------|------|
| `devDependencies` / `dependencies` | `jest` | Jest | 组件 |
| `devDependencies` | `vitest` | Vitest | 组件 |
| `devDependencies` | `mocha` | Mocha | 组件 |
| `devDependencies` | `jasmine` | Jasmine | 组件 |
| `devDependencies` | `cypress` | Cypress | **浏览器** |
| `devDependencies` | `@playwright/test` | Playwright | **浏览器** |
| `devDependencies` | `@testing-library/react` | Testing Library（React） | 组件（配套，不单独构成通道） |
| `devDependencies` | `@testing-library/vue` | Testing Library（Vue） | 组件（配套） |
| `devDependencies` | `@testing-library/angular` | Testing Library（Angular） | 组件（配套） |
| `devDependencies` | `@vue/test-utils` | Vue Test Utils | 组件（配套） |
| `devDependencies` | `@angular/core`（含 `@angular-devkit/build-angular` 测试配置） | Angular TestBed | 组件 |

Testing Library 系与 Vue Test Utils 是**断言/渲染库**而不是运行器：只有它们而没有 Jest/Vitest 一类运行器时，组件通道记 `unknown` 并写明缺运行器，不记 `available`。

### 2.2 配置文件扫描

| 配置文件 | 推断框架 | 通道 |
|----------|---------|------|
| `jest.config.{js,ts,mjs,cjs}` 或 `jest` 字段在 package.json | Jest | 组件 |
| `vitest.config.{js,ts}` 或 `vitest` 字段 | Vitest | 组件 |
| `.mocharc.{js,json,yml}` | Mocha | 组件 |
| `cypress.config.{js,ts}` | Cypress | 浏览器 |
| `playwright.config.{js,ts}` | Playwright | 浏览器 |

### 2.3 测试目录结构扫描

| 目录模式 | 推断框架 | 通道 |
|----------|---------|------|
| `__tests__/` / `*.test.{ts,tsx,js,jsx}` / `*.spec.{ts,tsx,js,jsx}` | Jest/Vitest | 组件 |
| `src/**/*.test.tsx` | Testing Library + Jest/Vitest | 组件 |
| `cypress/e2e/` | Cypress | 浏览器 |
| `e2e/` + `*.spec.ts` | Playwright | 浏览器 |

依赖声明与目录结构冲突时以**能实际跑起来的一侧**为准：有配置文件和测试文件但依赖缺失记 `unknown`，有依赖但一个测试文件都没有也记 `unknown`，两者都写清扫描到的信号。

### 2.4 前端探测结果输出格式

状态与框架分字段，四个字段一起写：

```
component_test_status=available
component_test_framework=Vitest+@testing-library/react
browser_test_status=absent
browser_test_framework=
test_dir=src/__tests__/,src/components/**/*.test.tsx
component_test_pattern=Vitest(*.test.tsx)+Testing Library
```

写法约束：

- `*_test_status` 只取 `available` / `absent` / `unknown`。
- `*_test_framework` 只在对应 status 为 `available` 时填，且只填真实框架名；其余情况留空。
- `absent` 表示扫描过且确认没有，`unknown` 表示信号矛盾或无法判定——两者对下游的含义不同，不可互换。

## 3. 探测降级规则

| 条件 | 处理 |
|------|------|
| 后端构建文件存在但无测试框架依赖 | 标注 `test_framework=未识别`，tasks.md Step 1 用伪代码（标注"框架未识别，需人工适配"），触发 Stop If |
| 前端 `package.json` 存在但两条通道都无信号 | `component_test_status=absent`、`browser_test_status=absent`，两个 framework 字段留空，触发 Stop If |
| 前端只有一条通道有信号 | 该通道记 `available` 并填框架名，另一条记 `absent` 并留空框架字段；**不拿现有通道冒充缺失的那条**，也不因此 Stop |
| 构建文件不存在（无 pom.xml/build.gradle/go.mod/package.json） | Stop，回流 Design 标注"仓内无构建文件，无法探测测试框架" |
| 后端多框架共存 | 主框架取集成测试能力最强者（Karate > RestAssured > Spring Boot Test），辅助框架取单测框架 |
| 前端多框架共存 | **不排优先级**。同通道内多个运行器时按配置文件与测试文件数量取实际在用的那个并记录另一个；跨通道各自独立记录，不比较强弱 |
| 仅有单测框架无集成框架（后端） | 主框架 = 单测框架（如 JUnit5+Mockito），L3 API 接口级测试用单测框架 + Mock 外部依赖实现 |

## 4. 探测结果与 tasks.md 的衔接

探测结果写入 tasks.md TaskPacket 头：
- 后端写 `test_framework=`，声明主 + 辅助框架（如 `JUnit5+Mockito+Karate`）
- 前端写 `component_test_status/framework` 与 `browser_test_status/framework` 四个字段；`test_framework=` 仍保留为供 v1 消费者读取的派生摘要（如 `Vitest+Testing Library`），**判据以四个新字段为准**，两者冲突时按新字段
- Step 1 RED 测试代码的代码块语言标注基于探测结果（`java` / `gherkin`（Karate feature）/ `typescript` / `javascript`）
- 后端 API 接口级测试优先用集成测试框架（如 Karate feature 文件，通过 HTTP 调用 API 端点）；L4 UT 用单测框架
- 前端组件级测试用组件通道框架（Jest/Vitest + Testing Library），后端 API 全 mock；需要真实浏览器的验证走浏览器通道，缺该通道时不用组件通道冒充
- 参照仓内已有测试文件的模式（测试运行器类、feature 文件结构、mock 配置等），保持一致

## 5. 探测执行步骤（sdd-task Step 2.6）

1. 定位仓根构建文件（pom.xml / build.gradle / go.mod / package.json）
2. 扫描依赖声明，按 §1.1 / §2.1 信号表识别框架，前端同时记下每个信号属于哪条通道
3. 扫描测试目录结构，按 §1.2 / §2.3 确认框架实际使用
4. 后端按双轨规则（§1.3）确定主框架 + 辅助框架；前端按 §2.0 分别判定两条通道的状态，不跨通道比较强弱
5. 输出字段值写入 tasks.md TaskPacket 头：后端 `test_framework=`；前端四个通道字段 + 派生摘要
6. 探测失败按 §3 降级规则处理
