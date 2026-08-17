# 测试框架探测指南

> sdd-task 在生成 tasks.md 前，对目标代码仓执行测试框架探测，将结果写入 TaskPacket 头的 `test_framework` 字段。
> 探测结果决定 tasks.md Step 1 RED 测试代码的框架选型。**不假设任何微服务使用什么框架**——以仓内代码事实为准。

## 0. 探测原则

- **以代码事实为准**：扫描构建文件依赖声明 + 测试目录结构 + 已有测试文件模式，不凭记忆猜测。
- **主框架 + 辅助框架**：后端优先识别集成测试框架（用于 L3 API 接口级测试），辅助识别单测框架（用于 L4 UT）；前端识别组件测试框架。
- **探测失败即 Stop**：仓内无可识别测试框架信号时，标注 `test_framework=未识别` 并 Stop 回流 Design，不得默认 JUnit/Jest。

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

### 2.1 package.json 扫描信号

| 扫描目标 | 识别信号 | 推断框架 |
|----------|---------|---------|
| `devDependencies` / `dependencies` | `jest` | Jest |
| `devDependencies` | `vitest` | Vitest |
| `devDependencies` | `mocha` | Mocha |
| `devDependencies` | `jasmine` | Jasmine |
| `devDependencies` | `cypress` | Cypress |
| `devDependencies` | `@playwright/test` | Playwright |
| `devDependencies` | `@testing-library/react` | Testing Library（React） |
| `devDependencies` | `@testing-library/vue` | Testing Library（Vue） |
| `devDependencies` | `@testing-library/angular` | Testing Library（Angular） |
| `devDependencies` | `@vue/test-utils` | Vue Test Utils |
| `devDependencies` | `@angular/core`（含 `@angular-devkit/build-angular` 测试配置） | Angular TestBed |

### 2.2 配置文件扫描

| 配置文件 | 推断框架 |
|----------|---------|
| `jest.config.{js,ts,mjs,cjs}` 或 `jest` 字段在 package.json | Jest |
| `vitest.config.{js,ts}` 或 `vitest` 字段 | Vitest |
| `.mocharc.{js,json,yml}` | Mocha |
| `cypress.config.{js,ts}` | Cypress |
| `playwright.config.{js,ts}` | Playwright |

### 2.3 测试目录结构扫描

| 目录模式 | 推断框架 | 用途 |
|----------|---------|------|
| `__tests__/` / `*.test.{ts,tsx,js,jsx}` / `*.spec.{ts,tsx,js,jsx}` | Jest/Vitest | 组件/单元测试 |
| `cypress/e2e/` | Cypress | E2E |
| `e2e/` + `*.spec.ts` | Playwright | E2E |
| `src/**/*.test.tsx` | Testing Library + Jest/Vitest | 组件测试（L3 mock 集成） |

### 2.4 前端探测结果输出格式

```
test_framework=Jest+@testing-library/react
test_dir=src/__tests__/,src/components/**/*.test.tsx
component_test_pattern=Jest(*.test.tsx)+Testing Library
```

## 3. 探测降级规则

| 条件 | 处理 |
|------|------|
| 构建文件存在但无测试框架依赖 | 标注 `test_framework=未识别`，tasks.md Step 1 用伪代码（标注"框架未识别，需人工适配"），触发 Stop If |
| 构建文件不存在（无 pom.xml/build.gradle/go.mod/package.json） | Stop，回流 Design 标注"仓内无构建文件，无法探测测试框架" |
| 多框架共存 | 主框架取集成测试能力最强者（后端：Karate > RestAssured > Spring Boot Test；前端：Cypress > Playwright > Testing Library），辅助框架取单测框架 |
| 仅有单测框架无集成框架（后端） | 主框架 = 单测框架（如 JUnit5+Mockito），L3 API 接口级测试用单测框架 + Mock 外部依赖实现 |

## 4. 探测结果与 tasks.md 的衔接

探测结果写入 tasks.md TaskPacket 头：
- `test_framework=` 字段声明主 + 辅助框架（如 `JUnit5+Mockito+Karate` 或 `Jest+@testing-library/react`）
- Step 1 RED 测试代码的代码块语言标注基于探测结果（`java` / `gherkin`（Karate feature）/ `typescript` / `javascript`）
- 后端 API 接口级测试优先用集成测试框架（如 Karate feature 文件，通过 HTTP 调用 API 端点）；L4 UT 用单测框架
- 前端 mock 集成级测试用组件测试框架（Jest/Vitest + Testing Library），后端 API 全 mock
- 参照仓内已有测试文件的模式（测试运行器类、feature 文件结构、mock 配置等），保持一致

## 5. 探测执行步骤（sdd-task Step 2.6）

1. 定位仓根构建文件（pom.xml / build.gradle / go.mod / package.json）
2. 扫描依赖声明，按 §1.1 / §2.1 信号表识别框架
3. 扫描测试目录结构，按 §1.2 / §2.3 确认框架实际使用
4. 按双轨规则（§1.3）确定主框架 + 辅助框架
5. 输出 `test_framework=` 字段值，写入 tasks.md TaskPacket 头
6. 探测失败按 §3 降级规则处理
