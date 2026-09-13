# FIX-321 代码审查报告（Code Review R0）

- **任务**：FIX-321 — `_MARKDOWN_BOLD_SPAN_RE` 不校验真 run 边界（glob 串被粗体剥离洗白）
- **Round**：R0（首次审查；无前轮 findings）
- **审查对象**：工作树内 2 个修改文件 —— `skills/software-project-governance/infra/verify_workflow.py`（实测 **+32/−2**）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（**+71/−0**）；基线 HEAD = `3c37342`
- **来源**：`docs/reviews/review-FIX-319-CODE-R0.md` **F-01**
- **Reviewer**：Code Reviewer Agent（只读；仓库零写入已实证）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0 / P1=0 / P2=2 / P3=2）

## 1. 独立复现结论（全部由 Reviewer 自行执行）

| # | 复现项 | 结果 |
|---|---|---|
| R-1 | 核心目标红→绿（AST 抽取 4 符号，OLD = `git show HEAD`、NEW = 工作树） | `**/tests/**` **OLD=PASS → NEW=FAIL**；`strippedNEW='**/tests/**'` 不再被中和 ✅ |
| R-2 | 9 条既有反证不放宽 | `*`/`all files`/`any file in the repo`/`whole repo`/`src/*`/`*.py`/`**/*.py`/`*foo*`/`**all files**` **9/9 仍 FAIL** ✅ |
| R-3 | 正例不误伤 | 粗体 scope、`a**b**c`、`**a/b**` 全 PASS ✅ |
| R-4 | 真实语料 7/7 | `.governance/execution-packets.json` 全 packet 判定与 HEAD **完全一致** ✅ |
| R-5 | **放宽面穷举（最强保证）** | 9-token 字母表 r≤3 全笛卡尔积筛 `OLD=FAIL ∧ NEW=PASS` → **命中 0 条** ⇒ 放宽面为空集 ✅ |
| R-6 | 收紧面穷举 | 92 条，全部为「`**` 紧邻 `*` 或 `/`」族，方向 = 严格侧 ✅ |
| R-7 | 变异矩阵（in-memory 补丁，仓库零写入） | **M-A/M-B/M-C/M-D/M-I/M-J 全部被 5 条新测试抓回**；M-E/F/G/H 经 r≤5 全扫描证实为**行为等价变异**（0 判定分歧），**非覆盖盲区** ✅ |
| R-8 | 子集测试 | `-k ExecutionPacket` **Ran 21 / OK** ✅ |
| R-9 | Check 18c 真实作用域 | 活跃集 6 条；**无任何 `too broad`**；`FEAT-031 → PASS` ✅ |
| R-10 | exit / 28v 语义 | `check-governance --summary-only` **87 issues / exit 0**；28v **exit 0** + `writes: 0` + 23/18/5 不变 ✅ |
| R-11 | 存量失败归因 | 对 3 条失败测试函数体做**调用面扫描** → **4/4 均不触达本片任何符号** ⇒ 零因果 ✅ |
| R-12 | 判据差集 | 仅 3 个 hunk（正则定义 + 两处 docstring）；**其余符号逐字节未动** ✅ |
| R-13 | 真实环境防护 | 仓库路径写入 **0**；`~/.dsh` 未触碰 ✅ |

## 2. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✅ |
| 5 维度全覆盖 | 100% | 逐维度有结论 | ✅ |
| 每条发现标注级别 | 100% | F-01~F-04 全带级别 | ✅ |
| 设计一致性检查 | 已完成 | 与 Check 18c 既有语义 + docstring 自述 + 生成器 scope 形态三向比对 | ✅ |
| AI 代码专项 5 项 | 全部完成 | mock/硬编码/幻觉 API/TODO/过度实现逐项 | ✅ |

## 3. 专项裁决：Developer 对任务书字面守卫的偏离 —— **接受**

- **「不放宽」以最强形式成立**：R-5 全笛卡尔积 0 条放宽；且「`sub` 删除字符 ⇒ 不可能新造原文不存在的子串」⇒ NEW 的可达 PASS 集是 HEAD 的**严格子集**（独立于任何测试的论证）。
- **「消除误报」未退化**：真实语料 7/7 与 HEAD 一致；正例 0 误伤。
- **收紧面 = 设计明文方向**（docstring `:12716-12719`「ambiguous boundary always resolves to the strict side」）；92 条收紧向量全属该族，**fail-closed 语义兑现而非范围蔓延**（正则在结构上只减少剥离）。
- **Developer 的偏离理由经独立证实**：任书字面「span 外侧不得紧邻 `/`」对 `**/tests/**` 恒真（两侧是串首/串尾）⇒ 单独无效；实测 M-J（字面实现）对 `**/tests/**` 仍 PASS。
- **残留张力（不阻塞）**：`` `**/tests/**` ``（inline code 形式）与裸形式字符层无法区分 ⇒ 同判 FAIL；Reviewer 自建候选豁免实测证实**不存在**「裸形式 FAIL 而 inline 形式 PASS」的实现，**fail-closed 是唯一自洽解**；真实语料中「`**` 与 `/` 共现」= **0**，当前影响为零。

## 4. Findings（均非阻塞）

| # | 级别 | 位置 | 事实 | 建议 |
|---|---|---|---|---|
| F-01 | P2 | `tests/test_verify_workflow.py:11895-11960` | 新增向量**未覆盖 `**/**`**（该串 OLD=PASS → NEW=FAIL）；变异 M-C 的唯一分歧输入正是它 ⇒ **不是缺陷**，但该行为无测试钉住 | 在 `test_scope_glob_family_is_judged_consistently` 家族元组补 `"**/**"` |
| F-02 | P2 | `verify_workflow.py:12715-12722` vs `:12740-12746` | 正则在 `/` 方向是**双侧守卫**，而 docstring 的「only a slash glued to a delimiter disqualifies it」未点明 `docs/**bold**` 一类（`/` 在 span 内侧）也属收紧面 | 注释改写为「a `**` run adjacent to `/` on EITHER side is ambiguous ⇒ rejected」 |
| F-03 | P3 | `verify_workflow.py:12752` | `lambda match:` 形参遮蔽 `re.match`（**零功能影响**，模块级 46 处调用不受影响） | 改名 `m` |
| F-04 | P3 | 前轮报告 `review-FIX-319-CODE-R0.md:97` | 前轮记「`**a****b**` → PASS」**与 HEAD 实测不符**（HEAD 实测 FAIL） | 前轮该格按**勘误**处理（Coordinator 侧） |

## 5. 五维度结论

- **正确性 ✅**：单一调用点、改动面 3 hunk；形式化不变量（严格子集）；边界条件（`****`/`***a***`/`**/**`/`**a****b**` 均 FAIL）无反直觉。
- **安全性 ✅**：无网络/文件/子进程面；正则为固定字面量（无注入面）；失效方向 = fail-closed（零放宽面）。
- **可维护性 ✅**：注释与机制一致；函数 8/9 行；无死代码；F-02 为注释精度。
- **性能 ✅**：单趟 `sub`，无嵌套量词/回溯风险面；活跃集 6 条，开销可忽略。
- **测试覆盖 ✅**：5 条新用例 + 10 变异实证（6 抓回 / 4 证为等价变异）。

## 6. 真实环境命令上报表（R4）

全部写操作限于 `%TEMP%\cr-321-311\**`；`DSH_HOME` 重定向至 `%TEMP%`；**仓库路径写入 0**；`~/.dsh` 写入 0（mtime `2026/9/12 20:06:00` 未变）。**未执行任何 `git add/commit/checkout/restore/stash/reset`**。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
