# Review — FIX-457 对账回写核证（RECONCILE R0）

- **Reviewer**: independent Reviewer (delegated instance, dispatched by Coordinator session-d42d192e)
- **Date**: 2026-10-26 (Asia/Shanghai)
- **Object**: the reconciliation claim — "FIX-457（e2e 夹具 SKILL 投影漂移，Check 28b）已由 e254584（REL-103 0.99.0 发布链 M-1 bump 全链回同步，2026-10-24）顺带消解；今日 check-projection-sync PASSED；行状态滞后按对账回写闭环、无开发面" — verified against repository facts, not against the Coordinator's narrative.
- **Verdict**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**

## R1 现状复跑 — PASS

`python skills/software-project-governance/infra/verify_workflow.py check-projection-sync`（仓库根，本人亲跑）：exit 0，`Result: PASSED — entry bootstrap sections synchronized with the canonical templates`；repo-root 与 e2e-fixture 双面（primary CLAUDE.md 10685B/full，secondary AGENTS.md 2815B/thin）一致。

## R2 哈希直接比对 — PASS（强于规范哈希口径）

| 项 | 源 skills/software-project-governance/SKILL.md | 镜像 project/e2e-test-project/skills/software-project-governance/SKILL.md |
|---|---|---|
| 原始 sha256 | `67A0C2FA6A46BC1B4FB8A1C250A9FF4D14EBE1F41852C472485E4F9DF537973B` | 同左（逐位相等） |
| CRLF→LF 规范化 sha256 | `a7429bb2ac5848648549efb4489d1d9945896d1f1617b7044ed3bcc313a15ef6` | 同左 |
| 字节串 | 30485 | 30485（`IDENTICAL=True`） |

字节级相等蕴含 Check 28b 的规范化哈希一致口径，漂移不复存在。

## R3 溯源核实 — PASS

`git log --follow -- project/e2e-test-project/skills/software-project-governance/SKILL.md`（本人亲跑）：

1. `e254584` — "REL-103: bump 0.99.0 across all pins and land the release dossier (21-commit payload …)"（= 0.99.0 发布链，与 EVD-2145/EVD-2148 在案的发布 commit 一致）
2. `7db915b` — "FEAT-101: 移除 chrys 平台适配"（= triage 记录的漂移引入点，前一态吻合）
3. `b7be5a5` — FEAT-100 后续（更早基线）

主张的「最后提交=e254584、前一态=7db915b、消解载体=REL-103 bump 全链回同步」逐项与 git 事实一致。

## R4 夹具其余面 — PASS

`git show --stat e254584 -- project/e2e-test-project`：夹具目录内仅 3 文件——fixture `.governance/plan-tracker.md`（2 行版本面）、`commands/governance-init.md`（6 行模板面）、`SKILL.md` 镜像（71 行，+27/−52 属版本内容回同步量级）；均为投影/版本回同步性质，无意外夹具改动。整 commit 52 文件/+9462 与 REL-103 发布卷宗量级一致。

Check 28b 今日 full 面输出（本人一手读取本日全量检查输出 `spg-check-full.txt`，非转述）：`Source version: 0.99.0 / Mirrored files checked: 28 / [PASS] Source, target fixture, native entries, and plugin versions are synchronized.`——与 EVD-2167 引用一致。

## R5 处置合理性 — PASS

- 验收原文 =「check-projection-sync 与 Check 28b PASS（该镜像与源规范化哈希一致）」——是**终态判据**而非「必须由专项开发达成」的路径判据；终态已由发布链 e254584 达成（R1/R2/28b 三面绿），再派 Developer 做「回同步」将是零操作。无开发面闭环与事实自洽。
- EVD-2167 结论标「待独立核证」且 plan-tracker 行仍为「⏳ 🔄 进行中（待派发开发）」——顺序正确（先核证后回写），不存在「为消红而改状态」：状态变更尚未发生，且将以 EVD-2167 + 本报告为据。
- 溯源链无反证：triage 时点（2026-10-20）FAIL 与今日 PASS 之差恰好由 e254584（2026-10-24）承载，时间线闭合。

## Findings

- **F1 [P3]** 行状态收尾待办：核证通过后应将行状态由「🔄 进行中（待派发开发）」回写为「✅ 缺陷已消解（对账回写，EVD-2167 + REVIEW-FIX-457-RECONCILE-R0）」，避免候选池继续把它当待派发项（TPA 已将其列为 unblocked 候选）。
- **F2 [P3]** `check-projection-sync` 文本输出以 entry bootstrap 面为主叙，SKILL.md 镜像面的机器看护实为 Check 28b（full 面）；引用时两者并提（EVD-2167 已如此），无需改动。
- **F3 [P3]** 观察项：e254584 含夹具内 `.governance/plan-tracker.md`/`commands/governance-init.md` 的版本面小改——均为投影类，无夹具语义意外。

无 P0~P2 finding；unresolved_blockers=0。

## 复跑命令（均本人执行）

```text
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync   # exit 0, PASSED
Get-FileHash 源/镜像 SKILL.md -Algorithm SHA256                                            # 逐位相等
[CRLF→LF 规范化 + 字节串比对]                                                              # IDENTICAL=True
git log --oneline --follow -6 -- project/e2e-test-project/skills/software-project-governance/SKILL.md
git log -1 --format="%H%n%s" e254584
git show --stat --format="" e254584 -- project/e2e-test-project
Select-String spg-check-full.txt "Check 28b"（本日 full 面输出一手读取）
grep .governance/evidence-log.md EVD-2167；grep .governance/plan-tracker.md FIX-457
```
