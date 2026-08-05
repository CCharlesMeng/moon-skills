---
status: accepted
---

# 区块靠 class 结构定位，行号只作引用坐标

原设计贯穿全文用「原型文件 + 行号范围」定位区块，本决策推翻它。两份样本（[`evals/`](../../../../skills/sdd-dev-frontend/evals/)）实测下来，行号在其中一档上完全失效，而语义标签这条替代路线根本不存在。

## Considered Options

- **按 `<section>` 或其他语义标签分段**：两份样本里**唯一出现的语义标签就是 `section`**，`a`/`p`/`h1`-`h3`/`table`/`tr`/`td`/`ul`/`li`/`button`/`input`/`form`/`img`/`svg` 全部为 0、0 个 `id=`，整份稿子只有 div 和 span；而 `section` 标准版 1 个（`.section-87`）、导出件 4 个（`.section`、`.static-42`、`.section-88`，以及一个只有 `flex_common1 display_common1` 两个工具类、**没有任何具名 class** 的），要索引 10.4 屏内容。方案最初版本走的就是这条路，被实测否掉。
- **保留行号范围作查找手段**：`设计稿导出件.html` 269,198 字符只有 2 行，`L1–L1` 就是全文，「只精读这个范围」在它上面是空转。格式化档（`设计稿原型-标准版.html`，1316 行）行号可用，但那是运气不是机制。
- **按原型形态分档，各写一套解析器**：两份样本是同一生成器的两种输出，class 命名约定（`.text-2`、`_commonN` 工具类）与 `assets/<节点ID>.svg` 引用模式完全一致，**只差空白格式**。分档只需体现在锚点是否附带行号，解析逻辑一套够用。

因此锚点主体是承载区块的 class 名，它在两档上都成立且可复算；文件格式化时附带行号范围，**作人类可读的引用坐标，不作查找手段**。上面那个只有工具类的 `section` 划出了约束边界：**区块根元素不保证有唯一具名 class**，锚点方案必须为这种情况兜底（走结构路径，或就近的具名祖先／后代）。

## Consequences

- 全仓「行号范围」表述迁移为「锚点」并说明取值形态：`SKILL.md`、`diff-list-template.md`、`alpha-tests-restore.md`、`qa-baseline-template.md`、`sdd-task-frontend-split.md`、`方案设计.md`（后者 5 处：L119、L152、L186、L301、L319；L260 的「基线行号」指 QA 基线表格行编号，与原型定位无关，不在内）。
- 脚本的锚点方案必须为「根元素无具名 class」的区块提供兜底，不得假设具名 class 恒存在。
- [`sdd-task-frontend-split.md`](../../../../skills/sdd-dev-frontend/references/sdd-task-frontend-split.md) L99 的「行号跨度 200 行」经验值在单行档上无意义，改为按组件实例数提示；「一屏可截」仍是唯一判据。
- Phase 0 需探测原型形态，用来决定锚点是否附带行号。
- 无脚本能力时的降级分两档：格式化档还能用 `rg` 按 class 名逐个定位、勉强凑出区块边界；单行档没有退路，直接判基线源不可用并按 P7 上报。
