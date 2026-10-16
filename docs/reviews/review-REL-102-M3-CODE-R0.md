# REVIEW-REL-102-M3-CODE-R0 — 0.98.0 发布链 M-3 双审 CODE 半面

- **审查对象**: v0.97.0..HEAD@3b1a847（0.98.0 发布窗口代码面/版本面） · **审查日期**: 2026-10-15 · **Reviewer**: 独立 Code Reviewer 子代理（只读零写入）
- **Verdict**: **APPROVED_WITH_NOTES（AWN）｜ unresolved_blockers = 0** ｜ P0=0 / P1=0 / P2=0 / P3×3

## ① Verdict 与范围

载荷七票逐票审查已在各票 R 轮终态（AWN/0×9）；本半面聚焦 M-1 版本面 commit（3b1a847）与窗口整体一致性。结论：版本面与窗口一致性达标。

## ② 逐项核验（证据锚点）

### 1. M-1 版本面核验（git show 3b1a847 = 22 files +65/−30）— 七项全过

| # | 项 | 结果 | 锚点 |
|---|---|---|---|
| ① | SKILL.md frontmatter version | ✅ 0.97.0→0.98.0 | git show diff L4 |
| ② | verify_workflow.py 六针 + L17672 | ✅ 六 REQUIRED_SNIPPETS 全 0.98.0，diff 仅 12 行全在 L1094~ 区域；L17670-79 DEC-146 历史注释完好（全文 DEC-146×6 处未触碰） | diff 实证 + 读 L17665-17680 |
| ③ | 三 hooks @version | ✅ pre-commit/post-commit/prepare-commit-msg 均 0.98.0 | 三 hooks diff 头部 |
| ④ | 四 plugin.json+marketplace+manifest | ✅ 全 version=0.98.0，各文件 grep 无 0.97.0 残留 | 各 diff + git grep exit 1 |
| ⑤ | release-projection 再生 | ✅ adapters template/persona/commands/package.json/e2e 五件全 0.98.0 | diff 实证 |
| ⑥ | 双根 entry sync ×4 | ✅ committed 四面 @bootstrap-version 0.98.0；根 CLAUDE.md gitignored（.gitignore:3）工作树已 0.98.0（FIX-256 先例口径，不入 commit 正常） | diff + git check-ignore |
| ⑦ | CHANGELOG 0.98.0 段 | ✅ 落位与 FIX-349 占位格式正确 | project/CHANGELOG.md L5 |

### 2. 一致性实测 — 双 PASS

- `check-version-consistency`：**PASSED@0.98.0**（13 files + bootstrap markers），7 WARN 静态针与预期完全一致（6 处 test_verify_workflow.py 0.98.0 针〔DEC-213③〕+1 处 stale exemption test_archive.py:5862）。
- `release-projection`：**PASS** source 0.98.0，28 projections，legacy_snapshot_check PASS（10 declared）。

### 3. CHANGELOG 事实核对 — 无失实陈述

- 五 commit 哈希+九载荷票哈希全与 git log 一致 ✅；审查链 verdict 九文件逐抽核属实（FEAT-093-R1/094-R0/095-R1/096-R1/097-R6{"unresolved_blockers": 0}/FIX-442-R0/443-R0/446-R17/REL-102-R0）✅。
- regen 数字：R1 28160→28204 ✅（git 净 diff 28120→28204，28160 为 daac2b8 commit 内中间态——FEAT-097 接线 +40 至 28160〔review-FEAT-097-CODE-R0.md L115 佐证〕，rider regen 至 28204；CHANGELOG「+44=FEAT-095 接线」语义正确）；R5 99→107 ✅（snapshots.json 实测：added=authority-ledger/enforcement-check/goal-bridge/isolation×5，removed=[]）。
- 全量 1135 OK（EVD-1707）✅；注入预算 resident 4441（review-FEAT-097-R0 L73-75）/skill 17484（EVD-1708）两数字有据且时点自洽——见 P3-N1。
- DEC 链 330/333/334/342/350/351/352/353/354/357/358 全在 decision-log 有据 ✅；check-release 静态 16 面 PASS 与 EVD-1708 定谳口径一致 ✅。

### 4. 窗口漂移扫描 — 无未审产品变更混入

`git diff v0.97.0..HEAD --stat`：117 files +19720/−314 全部可归属（版本面 22/载荷 infra 大件+tests 9/docs/CHANGELOG 回填）；工作树余留=hooks/commit-msg+test_hooks.py（暂停链，与描述一致）；**M-1 未带入暂停链 body**（git show 3b1a847 -- hooks/commit-msg 输出为空 ✅）。

### 5. committed-state 一致性评估（如实披露，不要求修复）

- committed commit-msg @HEAD=`# @version: 0.97.0` vs worktree=0.98.0——漂移事实成立（纯标记零执行语义；check-version-consistency 读工作树故本地 PASS；check-release 不拦截——EVD-1708 实测 4 issues 无此面）。
- DEC-342/358① 暂停链保全=有意状态（M-1 message/CHANGELOG/M-0 三处披露）；⚠ **0.99.0 M-1 时须显式处理该文件**（FIX-445 恢复提交则同步 bump，否则继续保全），防止 committed hooks 版本不一致固化。

## ③ 发现 P0~P3

- **P0/P1/P2：无**
- **P3-N1（披露缺口）**：CHANGELOG 0.98.0 段未载注入预算数字（resident 4441≤6200 PASS + skill 17484>16000 report-only 超 1484/+9.3%——用户可感知披露点）——非失实，须补记（M-8 终账或随 M-4）。
- **P3-N2（措辞）**：M-1 commit message「双 marketplace」与实际不符（仅 .claude-plugin/marketplace.json 带 version；.agents/plugins 无该字段——FIX-120 后未动）；17 针总数经 package.json 补位吻合，无功能影响。
- **P3-N3（枚举不全+有意漂移）**：CHANGELOG 窗口枚举列 6/12（漏载荷四票哈希——段内 Added/Changed 有载+M-8 回填承诺；docs 两 commit c783cff/9950076）+ committed commit-msg 漂移（§5）。

## ④ 实测命令输出摘要

1. `git log v0.97.0..HEAD --oneline` = 12 commits（HEAD=3b1a8474）；`git status --short` = 2 M（commit-msg/test_hooks.py）
2. `check-version-consistency` → PASSED@0.98.0（Warnings 7）
3. `release-projection` → PASS source 0.98.0（28 projections）
4. `git show 3b1a847 -- …/hooks/commit-msg` → 空（exit 0）
5. `git show HEAD:…/hooks/commit-msg | Select-String '@version'` → `# @version: 0.97.0`
6. snapshots.json keys：v0.97.0=99 → HEAD=107（+8 键清单如上，removed=[]）

「未证实」项：无。审查只读零写入。
