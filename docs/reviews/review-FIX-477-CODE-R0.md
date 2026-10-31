# Code Review — FIX-477（pre-commit BOOTSTRAP DISCIPLINE 消费方宿主误拦）

- 审查方: Code Reviewer（独立只读；未修改任何文件、未 commit、未 spawn）
- 审查对象: 未提交 diff（`skills/software-project-governance/infra/hooks/pre-commit` −1/+15；`skills/software-project-governance/infra/tests/test_verify_workflow.py` +106）
- 日期: 2026-10-31

| 维度 | 结论 | 证据（命令 + 关键输出） |
|---|---|---|
| 1 正确性 | **PASS** | 函数定义 pre-commit:133，`SPG_RESOLVED_HOME=$(find_spg_home …)` 在 L206，调用在 L276 → 调用时就绪（bash 晚绑定；注释成立，实际行号 206/276 非 192/262）。新条件 L158-162 位于 `if` 内 → `set -e` 不触发；`local skill_md=` 无副作用；脚本仅 `set -e`（无 -u），`${SPG_RESOLVED_HOME:-}` 为额外保险。RED/GREEN 实测（同夹具，HEAD 钩子 vs 打补丁钩子）：`HEAD pre-fix hook: rc=1 blocked_marker=True` / `patched hook: rc=0 allowed_marker=True` |
| 2 纪律不回归 | **PASS** | `repo0.35_install0.37_plan0.37: rc=1`（安装根 0.37 未放宽纪律）；`repo0.37_install0.99_plan0.37: rc=0`（FIX-081 路径不变）。既有 5 例 + 新增 2 例：`Ran 7 tests in 16.481s / OK` |
| 3 消费者场景边界 | **PASS（含 P2-1 披露）** | `version_mismatch(install 0.37 / plan 0.36): rc=1` + `BOOTSTRAP DISCIPLINE`；`no_spg_home_no_repo_skill: rc=1`；`spg_home_but_no_skill_md: rc=1`（均 fail-closed）。但真实 consumer 布局下 `layout=consumer returncode=0`，`## 项目信息 owner: alice→MALLORY` 被放行（见 P2-1） |
| 4 同族缺陷 | **PASS** | `Select-String -Path hooks/* '$REPO_ROOT/skills'` 仅命中候选列表 pre-commit:80 / commit-msg:944 / post-commit:39，其后均有 env→DSH preset→plugin cache 兜底；commit-msg:1025 与 post-commit:119 的版本读取用 `$SOURCE_HOOK`（=SPG_RESOLVED_HOME/infra/hooks/…），非 repo-local SKILL.md；prepare-commit-msg 无 SKILL 引用 → Developer「无第二实例」成立 |
| 5 测试质量 | **PASS（含 P3-1/2/4）** | 夹具=临时 git 仓+临时安装根；`env["SPG_HOME"]=<tmp install>`、`pop(SOFTWARE_PROJECT_GOVERNANCE_HOME)`；断言 rc + stdout 标记（`bootstrap self-upgrade detected` / `BOOTSTRAP DISCIPLINE`），非仅 rc；`SPG_HOME` 在 `find_spg_home` 候选序中先于 HOME/DSH 兜底 → 不依赖真实 HOME/缓存 |
| 6 回归 | **PASS** | 见下三条复跑 |
| 7 范围纪律 | **PASS（含 P3-3）** | `git diff --stat`：2 files, 121 insertions(+), 1 deletion(-)；无无关格式/行为改动；`git diff --check` clean；pre-commit 工作树 0 个 CR 字节（LF 正常，FIX-451 无回归）；`?? docs/research/d1-real-use-loop-2026-10-31.md` 未跟踪、不在 diff |

## 回归复跑（独立执行）

1. `cd skills/software-project-governance/infra/tests && python -m unittest test_verify_workflow.PreCommitClaudeBootstrapUpgradeHookTests -v` → `Ran 7 tests in 16.481s` / **OK**
2. `python -m unittest test_hooks` → `Ran 70 tests in 148.511s` / **OK**
3. `python -m unittest test_pre_commit_review_evidence` → `Ran 11 tests in 3.327s` / **OK**

## 发现项

**P2-1（披露，非阻断）consumer 布局的 bootstrap 段边界未定义 + 负例夹具是混合布局**
- 非 bootstrap 判定用 awk 边界 `## 当前项目治理状态快速入口`（pre-commit:188-197）——dogfood 专属 H2。真实 consumer 宿主（python_game：bootstrap 后为 `## 项目信息` / `## 治理入口`）无该标题 → `in_bootstrap` 从 bootstrap 标题起永不复位 → **标题之后所有内容被当作 bootstrap 一并放行**。
- 实测（临时夹具，未改仓库）：consumer 布局自升级 + `## 项目信息` 改动同提交 → `rc=0 allowed`。
- 测试夹具（test_verify_workflow.py:16219 / 16240 / 16249）注入了 dogfood 边界标题 → 负例 L16282 实际只覆盖「bootstrap 标题之前」的改动（改标题），未覆盖真实 consumer 布局「标题之后」区域。
- 判断：修复本身正确（pre-fix 下 consumer 布局整体不可用，只能 --no-verify）；该边界是既有逻辑，但 FIX-477 使其首次可达 → 新开「版本 bump 同提交可夹带 bootstrap 段后内容」的允许面。建议：注释/文档明确 consumer 语义（段=标题→EOF），或泛化边界为「下一个非模板 H2」+ 补 consumer-native 负例；若不改码，至少写入完成报告/风险披露。

**P3-1** 缺 consumer 布局「安装根版本 ≠ staged plan 版本」负例测试（已手工复现 rc=1 BLOCK，未钉入套件）。
**P3-2** 缺 consumer 布局「SPG 无法解析」fail-closed 测试（已手工复现 rc=1，未钉）。
**P3-3** `docs/research/d1-real-use-loop-2026-10-31.md` 为未跟踪文件、不在 FIX-477 diff，提交时勿卷入（范围纪律）。
**P3-4** 正例无法区分 `source_ver` 来源（夹具中安装根版本与 plan 版本同为 0.37.0；若未来回落到 staged plan 版本仍可能假绿）。
**P3-5** 工作树 test 文件 CRLF（git 归一后提交为 LF），无实际影响但持续产生 CRLF 警告。

**审查结论：APPROVED_WITH_NOTES**
**unresolved_blockers=0**
