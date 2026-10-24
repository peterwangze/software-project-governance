# REL-103 M-3 CODE R0 — 0.99.0 发布载荷代码面审查

> 结论：**APPROVED_WITH_NOTES / unresolved_blockers=0**（P3×3，均不阻断发布 commit）
> 审查者声明：**降级审查**——本审查由 Coordinator 执行（会话树重组致 subagent 通道 depth 耗尽，无法 spawn 独立 Reviewer 实例）。Coordinator 非被审代码作者（交付均为 Developer 实例所写），但协调了各批交付——按治理口径**不宣称完全分离**，此降级与原因如实披露（EVD-2143 同族会话树异常的延续）。
> 日期：2026-10-24 10:0x +0800 ｜ 对象基线：HEAD `cad2f47` + 未提交发布载荷（23 M/新文件）

## 1. 对象绑定（亲算）

| 对象 | 状态 |
|---|---|
| infra/evidence_migration.py | `9DE94524`（M1 已审 R1 AWN/0——本轮审发布适配性，不重审） |
| infra/tests/test_evidence_migration.py | 16 用例（与 M2 交付一致；P3-1/P3-3 按 R1 非阻断裁定延后发布后补批——EVD-2142 记录在案） |
| infra/tests/test_verify_workflow.py | import 修复 +5 行（L36-42：幂等 `if str(_HERE) not in sys.path` + 同源注释） |
| infra/verify_workflow.py | ±12 = REQUIRED_SNIPPETS 版本字面量 0.98.0→0.99.0 ×6（版本 bump 针脚） |
| hooks pre-commit/prepare-commit-msg/post-commit | 各 ±2 = `@version` 针脚 |
| hooks/commit-msg +745 / tests/test_hooks.py +857 | **暂停 WIP 两文件**（2026-10-21 起 M 态）——在 M 列表、**发布 commit MUST NOT add**（发布 commit 时排除） |
| migration-staging | 仅 `evdt-20261024T000345Z-b600b5b7`（finalized 保留可核对，符合设计） |

## 2. 逐项判定

| # | 审查面 | 判定 | 证据 |
|---|---|---|---|
| 1 | import 修复正确性/最小性/无副作用 | **PASS** | 幂等插入+两 cwd 口径兼容（收敛批：仓库根 1141 passed+145 subtests 443.97s exit 0；tests/ 口径只增不删） |
| 2 | test_evidence_migration 用例数与 M2 一致性 | **PASS** | 16 用例；16/16 passed 1.14s（本轮独立复跑） |
| 3 | check-archive-integrity | **PASS** | Total tasks 180（hot+archive）；exit 0（本轮独立复跑）——M2 迁移后发布分支完整性 |
| 4 | 发布适配性（infra 零既有行为改动） | **PASS** | git diff --stat HEAD 全 7 文件定性：版本针脚（verify_workflow 6 处字面量+3 hooks @version）/import 修复/暂停 WIP——**零行为改动** |
| 5 | 暂停 WIP 隔离 | **PASS**（条件项见 P3-1） | 两文件与收敛批写面零交集（红线+写面清单核对）；发布 commit 排除责任在 Coordinator commit 时执行 |
| 6 | candidate 门 B 类收敛 | **PASS** | convergence-report §3：B 类零残留；余 5 全 A 类（3×git add 消解+2×provenance M-7 消解） |

## 3. Findings

- **P3-1（发布 commit 条件项）**：发布 commit MUST 精确 add 发布载荷面（版本针脚 17+文档/三件套/迁移资产/收敛修复），**排除暂停 WIP 两文件**（commit-msg/test_hooks.py）。add 清单须逐文件枚举，禁 `git add -A`。
- **P3-2（降级审查披露）**：M-3 CODE R0 为 Coordinator 降级执行（subagent 通道不可用）；M-3 RELEASE R0 若通道仍不可用，同样降级并明示。发布后通道恢复时可将本轮报告交独立 Reviewer 复核（追溯复核，非阻断）。
- **P3-3（追溯项）**：P3-1/P3-3 迁移用例（FIX-448）延后发布后补批——REL-103 终账（M-7/M-8）清单登记。

## 4. 边界

审查全程只读+本报告+scratch（.codex-sandbox/REL-103/review-code-r0/）；零 stage/commit/push；治理热表只读；无收到其他 agent 转包/委派消息（无通信异常可披露）。

*报告完。*
