# Code Review — FIX-433 R1（CODE，针对性复核）

- **复核范围**：仅 R0 [P2]（`adapters/dsh/README.md` L29 代码块形式瑕疵）的修复质量；R0 报告：`docs/reviews/review-FIX-433-CODE-R0.md`
- **审查者**：独立 Code Reviewer（R1，同一审查者）
- **终裁**：**APPROVED_WITH_NOTES**（unresolved_blockers = 0；本轮零新 finding；R0 P3×2 维持登记）

---

## 1. 复核方法与事实

- **diff 事实源**：`git status --porcelain` + `git diff --stat` + `git diff`（逐文件）+ `git hash-object`（完整 blob hash）+ `git rev-parse`。
- **基线比对**：R0 基线 = 10 modified 文件、35 insertions / 24 deletions、18 hunk。

### 核实点 ①：命令位纯可执行 — PASS

修复后 L29（工作区实读）：

```
git -C <仓库> pull    # 升级后刷新用户根预设：pull 完成后重启 dsh（宿主行 ensurePreset() 按包版本幂等重渲染；--sync 仅限隔离 DSH_HOME）
```

与 Developer 声称形态**逐字一致**。命令位 = `git -C <仓库> pull`，纯 git 命令；`<仓库>` 为该代码块既有占位符惯例（同块 L26 `<项目目录>`、根 README 同款），非本修复引入。R0 指出的自然语言混入（`; 重启 dsh`）已移除。逐字复制（替换占位符后）仅执行 git pull——安全（无用户根写入），不再产生「重启: command not found」。

### 核实点 ②：「重启 dsh」语义完整保留于注释 — PASS

注释承载完整语义三角：**重启正道**（「pull 完成后重启 dsh」）+ **幂等语义**（「宿主行 `ensurePreset()` 按包版本幂等重渲染」）+ **隔离限定**（「`--sync` 仅限隔离 DSH_HOME」）。与 R0 已核实的守卫事实（`SMOKE_EXIT_REFUSED = 2`、`write_side_refusal` L855-915）及全仓措辞基线一致，无语义稀释。

### 核实点 ③：本次仅此一处增量改动 — PASS

- `git diff --stat` = 仍 10 文件、**35+/24-**，与 R0 基线完全相同（该修复为 L29 行内 1:1 改写，不改变插入/删除计数；hunk 结构不变）。
- `adapters/dsh/README.md` 第二 hunk（L44 注意段）与 R0 记录**逐字一致**，未被触碰。
- 其余 9 文件扰动核查（双轨证据）：
  - **blob hash 相等（字节级）**：README.md=`b81933a`、AGENTS.md.template=`9e7be6d`、launch.py=`60abfbf`、lib/index.js=`fca36fa`、agent-entry-differences.md=`1465bda`、dsh_doctor.py=`437266d` —— 与 R0 记录的 diff index 工作区端逐一相同。
  - **完整 diff 内容逐字一致**：adapter-manifest.json（L63 evidence 串）、两个 SKILL.md（L478 版本升级行）——三个文件的当前 diff 与 R0 记录逐字比对相同；且 `git hash-object` 完整 hash 自证自洽（manifest=`5536ab600c38…`、SKILL=e2e SKILL=`10ce1747fa4c…`，两 SKILL 投影同步保持，与 check-projection-sync 28 镜像 PASSED 交叉印证）。
- 唯一内容变化即 `adapters/dsh/README.md` L29 一行（该文件工作区 blob `92f897e`→`3928cea`，其余文件基端 `c06e2e5` 不变）。

### 核实点 ④：R0 其余锚点与守卫零触碰未扰动 — PASS

- **守卫零触碰**：`launch.py` 工作区 blob `60abfbf` 与 R0 记录**相等**（相同 blob = 相同内容字节）——`write_side_refusal`/`_refuse_write`/argparse/渲染逻辑在 R0 之后零变化。
- dsh_doctor.py（`437266d`）、lib/index.js（`fca36fa`）hash 亦与 R0 相等——字符串面零扰动。
- 新增 untracked 仅 `docs/reviews/review-FIX-433-CODE-R0.md`（R0 审查报告自身，合法产物）；`.governance/**` 与豁免路径仍零接触。

### 审查过程观察（非 finding，事实记录）

R0 会话输出记录的三个工作区缩写 hash（manifest `55ab36b`、SKILL×2 `10e174`）与当前完整 hash 前缀（`5536ab6…`/`10ce174…`）不匹配，且无法从当前仓库状态复现该缩写。按「无法从事实验证的内容标为未验证」红线如实记录：**内容级证据优先**——三个文件的完整 diff 与 R0 记录逐字一致（diff 由基端 + 工作区内容确定性生成，内容一致即未扰动），当前 hash-object 与 diff index 自洽，六个其余文件 hash 直接相等。判定不受影响；R0 缩写记录判定为审查侧转写不确定性，不构成对 Developer 改动面的指控。

## 2. 独立复跑（R1 审查者本人执行）

| 命令 | 结果 | exit |
|---|---|---|
| `check-agent-adapters` | 6 adapter runtime-verified，contracts synchronized | **0** |
| `check-cross-references` | 77 files / 733 refs，全部 PASS | **0** |
| `check-projection-sync` | 28 mirrors，PASSED | **0** |
| `check-entry-bootstrap-sync` | repo-root + e2e + dsh-dialect(3633B/37L)，PASSED | **0** |
| `pytest test_dsh_adapter + test_dsh_compat + test_dsh_contract -q` | **301 passed, 102 subtests** in 48.07s | **0** |

与 R0 复跑结果逐项一致。

## 3. 结论

| 项 | 状态 |
|---|---|
| R0 [P2] F-1（README L29 命令位自然语言） | **已闭合**（修复质量核实通过，核实点①②③④全 PASS） |
| R0 [P3] F-2（`--install`/`--uninstall` 指引面同等 sweep 候选） | 维持登记（R0 已判未来候选，不在本轮范围） |
| R0 [P3] F-3（ADR/reviews 豁免面显式入账候选） | 维持登记（同上） |
| 本轮新 finding | **无** |

**RESULT: APPROVED_WITH_NOTES — unresolved_blockers = 0（通过终态）。**

R0 唯一 P2 已由 Developer 当场闭环且修复质量达标；改动面纯净性（仅一行增量）与守卫零触碰经字节级（blob hash）+ 内容级（diff 逐字）双重验证；四项 check 与三文件 pytest 独立复跑全绿。存续备注仅 R0 P3×2（未来候选，已登记于 R0 报告 §4）。

---

*审查依据：git status/diff/hash-object 工作区事实、adapters/dsh/README.md L29 直读、launch.py blob hash 字节级比对、审查者独立复跑输出（§2）。本报告为审查者唯一新增写入文件（R0 报告为本审查者 R0 轮产物）。*
