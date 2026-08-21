# 种子缺陷用例

判定类判据没法像脚本那样断言输出，只能给它一组**固定输入**、比对一份**已知答案**。`cases/` 就是那组答案。

**用例跟着 checklist 走。** 被测对象是本包的 checklist——改了某条的判据、级别或 `skip_when`，先回来看对应用例的 ground truth 还成不成立。

## 现有用例

| 用例 | 被测 checklist | 内容 |
| --- | --- | --- |
| `convention-01` | [convention](../frontend-code-checklists/convention.md) | 新增「客户风险简报」面板，4 个文件，14 条应报缺陷 + 6 条诱饵 |
| `convention-02` | [convention](../frontend-code-checklists/convention.md) | 订单导出，另一组 PATTERN 偏离 |
| `quality-01` | [quality](../frontend-code-checklists/quality.md) | 持仓表格，非平凡状态与副作用 |

restore、layout、test 三格还没有用例。前两者需要一个装得起依赖、跑得起页面的现场。

## 怎么跑

现场由 `sdd-dev-frontend` 的生成器搭——它产出的是 `dev-baseline.md`、`tasks.md` 与仓库现场，那些属于调用方的标准约束，所以留在那边：

```bash
python3 ../../sdd-dev-frontend/evals/fixtures/setup.py --case convention-01
```

跑完会打印一张「路径变量取值」表，直接贴进派发消息。现场的组成与限制见[生成器 README](../../sdd-dev-frontend/evals/fixtures/README.md)。

**派发时不要把 ground truth 给子代理。** 给它的是提示词正文加取值表。正常回传是 [role-result.md](../references/role-result.md) 的裸 JSON。

## 准入

四项分：命中率、误报率、级别正确率、格式合规。**每项都不得低于当前基线**，跑三次取最低那次。算法与历史分数见[模块与评测](../../../docs/skills/frontend-sdd/模块与评测.md)与[基线分数](../../../docs/skills/frontend-sdd/基线分数.md)。

## 加一个用例

1. 在 `cases/` 下建目录，放 `story/`（Story 产物，可用 `{{BASELINE_DIR}}` `{{STORY_DIR}}` `{{BASE_REF}}` `{{REPO3_FINGERPRINT}}` 四个占位符）、`after/`（覆盖到现场 `repo/` 上的改动）、`ground-truth.md`。
2. 需要新的仓内范式就加进生成器那边的 `baseline/repo-3-patterns.md`——它是所有用例共享的，加之前想清楚会不会动到既有用例的答案。
3. 生成器会校验占位符全部替换、工作区改动数与 `after/` 文件数相符，不符直接报错退出。

**诱饵和缺陷一样重要。** 现有诱饵专挑三类容易判错的情形：仓内没有对应 token 的字面量、没有基线行覆盖的范式偏离、本 Story 未改动过的历史违规。只测能不能找出缺陷，会养出一个把什么都报上来的检视。
