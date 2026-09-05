# Rollback Plan — 0.78.1 (REL-073)

> 复刻 version-plan-0.78.1.md §3.1 回滚边界表（0.77.0 R0 P2-1 先例义务延续）。**注记（Design Reviewer R0 F-4）**：本文件在边界表语义保真的前提下对工作树做了适配细化（FIX-290 实体所在 commit 与各安装形态用户处置）——§3.1 的两级回滚边界与约束逐项保持。

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（仅版本投影/发布文档/manifest 面——**不含任务链实体变更**：FIX-282..290 的产品/文档实体在各任务 commit（FIX-290 = `ce17dfd`），按 §3.1 候选回退不触碰任务链） | 常规可逆操作（0.76.0 rollback-plan Reversibility 先例） |
| 已发布 v0.78.1 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据 + DEC） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（"Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

## 部分回滚路径

- 版本投影面（SKILL.md frontmatter/15 projections/版本钉/preset 版本行）：`git revert <candidate-commit>` 恢复 0.78.0 声明面；`release-projection --write` 以恢复后的权威源重写并复跑 check-version-consistency + check-projection-sync。
- FIX-290 dsh 面（实体在任务链 `ce17dfd`，候选回退不涉及）：若需单独回退该批，`git revert ce17dfd`（独立可逆）；已安装用户处置——`link:` 用户 `git checkout v0.78.0` 前滚回退；`file:`/`github:` 用户 `dsh plugin remove` 后以 0.78.0 tag 重装（`github:...#v0.78.0`）；`.agent-presets/governance`（launch.py 装入）用 `launch.py --uninstall` 移除，不受 git 回退影响。
- 治理记录（.governance，gitignored）：不受 git 回退影响；DEC/EVD 行按 append-only 纪律补记回退事件，不改写历史行。

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.78.1 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

## 回滚后验证

复跑 #1（check-version-consistency）/#2（check-projection-sync）/#10（check-release --lineage-mode candidate）+ `git diff --check`；回滚事件入 decision-log。
