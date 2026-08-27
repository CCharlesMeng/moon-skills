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
| `baseline/` | 冻结的九份 app baseline，`setup.py` 原样拷进目标 app |
| [`sdd-review-frontend/evals/cases/<用例>/`](../../../sdd-review-frontend/evals/README.md) | 一个 Story 的产物、一组带种子缺陷的改动、以及 ground truth |
| `../设计稿原型-标准版.html`、`../原型-客户风险简报.html` | 两份真实设计稿 |

**用例不在本目录**：它们测的是 review 包里的 checklist，所以跟 checklist 一起放在包里。留在这边的是现场——`repo/`、`baseline/` 与本脚本产出的 Story 产物，那些是调用方的标准约束样本。

其余全是派生物，`setup.py` 每次从源料重建：目标仓的 git 历史、替换过占位符的 Story 产物、`design-spec/`（`design-facts.json` 单份接近 2 MB）。

**baseline 内容不再现场生成。** 它全部用仓内相对路径指路，不含绝对路径也不含哈希，所以源料本身就是最终内容；`setup.py` 只把它拷进目标 app 的 `frontend-baselines/`、校验文件齐全，再与业务代码一同提交为 Story 起点。

**Story 产物与 `design-spec/` 不进目标仓**，理由是它们属于外层 SDD 工作区且后者体积大；能这么做的前提是重建确定性：提交时间固定为冻结日期，抽取器有 32 条回归测试钉住指标，所以任何人任何时候跑，`base-ref` 的 SHA 都一样。

## 二、现场长什么样

```text
现场根目录/
├── repo/                          目标业务仓，git 已初始化
│   ├── frontend-baselines/
│   │   └── index.md + 七份关注点文件   原样拷自 baseline/
│   └── (工作区里有本 Story 的未提交改动 = 待检视的 diff)
├── story/
│   ├── tasks.md
│   ├── dev-baseline.md            工程依据 + 已冻结的 QA 基线
│   └── review-evidence.json        当前 diff 指纹；静态 fixture 的场景与质量命令为空
└── design-spec/                   仅 --with-design-spec
    ├── standard/
    └── risk-brief/
```

九份 baseline 里有六条正向 `PATTERN-*`：`PATTERN-COMP-1` 组件写法与命名、`PATTERN-COMP-2` 数值展示口径、`PATTERN-API-1` 请求统一出口、`PATTERN-DATA-1` 取数三态与取消、`PATTERN-STYLE-1` token 与样式落地、`PATTERN-STRUCT-1` 类型来源与检查抑制。**这六条是检视类模块的全部判据来源**，它们依据清单条目指的路径在 `repo/` 里都真实存在，可以逐条打开核对。`PATTERN-STRUCT-1` 对应 `sdd-init-frontend` 的类型抑制判据（`tsconfig` 严格度 + 抑制注释惯例），不是夹具自造的落点。

另有五条**「无统一做法」规范**同样是判据：`PATTERN-API-2` 无 mock 层、`PATTERN-DATA-2` 无缓存无 store、`PATTERN-DATA-3` 无表单机制、`PATTERN-STYLE-2` 阴影没有基准、`PATTERN-STYLE-3` 无主题机制、`PATTERN-TEST-1` 无既有测试与定位约定。它们决定的是**不得**判什么违规，漏读会造成编造基准。

## 三、现场的限制，写在明处

`repo/` 没有 `node_modules`，依赖没装、页面没起、质量命令没跑、浏览器能力没探测。这不影响 baseline——baseline 只装跨需求契约，机器实证本来就不落在那里。

`story/` 下也没有 `restore-contract.json`——`dev-baseline.md` 的表头引用了它，但现场不编译还原契约（那需要一份规则草稿，而规则草稿本身是 `recon-spec` 的产物）。检视类模块的判据不读它，所以不影响用例；子代理把它记进「已知缺口」是正确行为。

**当前现场只支持判据来自静态文件的模块**：`review-convention`、`review-quality`、`recon-codebase`。需要真跑页面的 `review-layout`、`self-test` 用不了它，那要另建一个装得起依赖的现场。

## 四、用例与加用例

都在 [`sdd-review-frontend/evals/`](../../../sdd-review-frontend/evals/README.md)：现有三个用例、准入分、以及加一个用例的步骤。

本目录只在两处与用例耦合：`baseline/` 的 `PATTERN-*` 是所有用例共享的判据来源，`setup.py` 校验九份文件齐全、占位符全部替换、工作区改动数与 `after/` 文件数相符。

改到接缝上的东西时，对照 [接缝契约](../../../../docs/skills/frontend-sdd/接缝契约.md) 看哪些 fixture 样本要跟着改。
