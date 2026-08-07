# fixture 现场

判定类提示词没法像脚本那样断言输出，只能给它一组**固定输入**、比对一份**已知答案**。这个目录就是那组固定输入。

```bash
python3 setup.py --case convention-01
```

跑完会在临时目录展开一个完整现场，并打印一张「路径变量取值」表——直接贴进子代理派发消息即可。加 `--with-design-spec` 会额外由两份真实原型生成 `design-spec/`。

---

## 一、为什么现场是生成的，不是存在仓里的

仓里只存**源料**四样：

| 源料 | 是什么 |
| --- | --- |
| `repo/` | 一个最小但真实的前端仓（React + TS + Vite + CSS Modules），Story 起点的代码树 |
| `baseline/` | 人工维护的 REPO-3 范式段与 onboarding 实证段 |
| `cases/<用例>/` | 一个 Story 的产物、一组带种子缺陷的改动、以及 ground truth |
| `../设计稿原型-标准版.html`、`../原型-客户风险简报.html` | 两份真实设计稿 |

其余全是派生物，`setup.py` 每次从源料重建：目标仓的 git 历史、`repo-baseline.md`（里面有绝对路径与指纹，天然机器相关）、替换过占位符的 Story 产物、`design-spec/`（`design-facts.json` 单份接近 2 MB）。

**派生物不进仓**，理由是它们要么机器相关要么体积大；能这么做的前提是重建确定性：提交时间固定为冻结日期，抽取器有 32 条回归测试钉住指标，所以任何人任何时候跑，`base-ref` 的 SHA 与 REPO-3 指纹都一样。

## 二、现场长什么样

```text
现场根目录/
├── repo/                          目标业务仓，git 已初始化
│   └── (工作区里有本 Story 的未提交改动 = 待检视的 diff)
├── frontend-baselines/risk-console/
│   ├── repo-baseline.md           REPO-1~3，readiness=READY_WITH_LIMITS
│   └── onboarding-report.md
├── story/
│   ├── tasks.md
│   └── dev-baseline.md            工程依据 + 已冻结的 QA 基线
└── design-spec/                   仅 --with-design-spec
    ├── standard/
    └── risk-brief/
```

`repo-baseline.md` 的 REPO-3 由两部分拼出来：`manage_repo_baseline.py scan` 扫出的自动发现，加上 `baseline/repo-3-patterns.md` 冻结的六条人工范式（token、请求出口、异步三态、格式化、组件写法、类型抑制各一条）。**这六条是检视类模块的全部判据来源**，它们声明的证据路径在 `repo/` 里都真实存在，可以逐条打开核对。

## 三、现场的限制，写在明处

`repo/` 没有 `node_modules`，依赖没装、页面没起、质量命令没跑、浏览器能力没探测。baseline 因此是 `READY_WITH_LIMITS` 而不是 `READY`，限制原文写在 onboarding report 里。

`story/` 下也没有 `restore-contract.json`——`dev-baseline.md` 的表头引用了它，但现场不编译还原契约（那需要一份规则草稿，而规则草稿本身是 `recon-spec` 的产物）。检视类模块的判据不读它，所以不影响用例；子代理把它记进「已知缺口」是正确行为。

**当前现场只支持判据来自静态文件的模块**：`review-convention`、`review-quality`、`recon-codebase`。需要真跑页面的 `review-layout`、`self-test` 用不了它，那要另建一个装得起依赖的现场。

## 四、用例

### `convention-01` — `review-convention` 的种子缺陷用例

一个新增「客户风险简报」面板的 Story，改动 4 个文件，里面预埋了 14 条应当被报出的缺陷、6 条不得报出的诱饵。答案在 [`cases/convention-01/ground-truth.md`](./cases/convention-01/ground-truth.md)，四项分（命中率 / 误报率 / 级别正确率 / 格式合规）的算法也在那里。

**派发子代理时不要把 ground truth 给它。** 给它的是提示词正文 + `setup.py` 打印的取值表。

诱饵是有意设计的，专挑三类容易判错的情形：仓内没有对应 token 的字面量（不得判阻断）、没有基线行覆盖的范式偏离（不得升级）、以及本 Story 未改动过的历史违规（不得报）。

## 五、加一个用例

1. 在 `cases/` 下建目录，放 `story/`（Story 产物，可用 `{{BASELINE_DIR}}` `{{STORY_DIR}}` `{{BASE_REF}}` `{{REPO3_FINGERPRINT}}` 四个占位符）、`after/`（覆盖到 `repo/` 上的改动）、`ground-truth.md`。
2. 需要新的仓内范式就加进 `baseline/repo-3-patterns.md`——但它是所有用例共享的，加之前想清楚会不会影响既有用例的 ground truth。
3. `setup.py` 会校验占位符全部替换、工作区改动数与 `after/` 文件数相符，不符直接报错退出。

改到接缝上的东西时，对照 [接缝契约](../../../../docs/skills/frontend-sdd/接缝契约.md) 看哪些 fixture 样本要跟着改。
