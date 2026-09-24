# REVIEW-FIX-375-CODE-R1 — R0 条件兑现确认复审（writer 族三边缘收口）

- **Task**: FIX-375 ｜ **Round**: **R1（确认轮）** ｜ **前轮引用**: `docs/reviews/review-FIX-375-CODE-R0.md`（机录 REVIEW-FIX-375-R0：APPROVED_WITH_NOTES / unresolved_blockers=0 / P1=1〔F-1〕P2=2 P3=3，条件合并——F-1 本轮补齐或明示遗留+披露勘正）
- **复审对象**: R0 之后的工作树增量（累计 vs HEAD：governance_store.py +83/−6、verify_workflow.py +23/−2、test_governance_store.py +227；R1 增量 ≈ +12/−1、+10、+55）
- **结论**: **APPROVED** ｜ **unresolved_blockers = 0**
- **计数**: P0=0 ｜ P1=0（F-1 已修复闭环）｜ P2=0（F-2/F-3 已修复闭环）｜ P3=1 新增（F-7 纯装饰性观察，不要求修改，不影响终态）
- **复审依据**: 角色定义复审四律（逐条比对前轮 findings 标注已修复/未修复/新引入；头部声明轮号与前轮引用；验证修复而非重扫）；全部结论以 git diff 逐行 + 独立实测为准

---

## 1. 前轮发现逐条处置核验（F-1~F-6）

| # | R0 级别 | 处置申报 | R1 核验 | 判定 |
|---|---|---|---|---|
| F-1 | **P1** | `elif replay_source=="apply" and not owned_files and resume_released:` 分支 + reapply_leg 红绿测试 + 注释三腿如实化 + `_pending_released_files` docstring 勘正 | **逐项证实**，见 §2 | **已修复** |
| F-2 | P2 | verify_workflow 注释如实披露 check-dsh-preset-compat 0→1 面 | 注释明写「One disclosed non-writer face changes in the same direction (F-2): check-dsh-preset-compat --fail-on-issues + FAIL verdict now exits 1 (dsh_compat.run_cli returns 1 — previously the same 假绿 class; in-repo callers do not pass that flag)」——与 R0 实测事实（dsh_compat.py L2072-2075、argparse L24744、仓内调用点无旗标）逐点吻合 | **已修复** |
| F-3 | P2 | 退出码标度按族注释 +「do not branch on a single scale」警示 | 四族标度逐一比对实际 handler 返回面：governance_store 0/2/3（`_emit` L1982-1986）✓；task_row_update 0 ok/2 usage/3 validation/4 conflict/5 retryable/6 manual（ExitCode L1142-1153）✓；baseline-register 0 ok/3 command error（run_register L1009/L1017 + `_run_error` L977-980）✓；baseline-evaluate 0 pass/1 fail/2 not_evaluable/3 storage（run_evaluate L1045-1046/L1052）✓——四族全对，R0 的单一标度误导声明已移除 | **已修复** |
| F-4 | P3 | pre-read 位移进 `_TargetLock` 块内 | diff 证实：`resume_released = _pending_released_files(...)` 现位于 `with _TargetLock(...):` 内、`_locks_execute` 调用前，附 F-4 溯源注释（只读/不取 ledger 锁）。竞态窗口闭合论证：同 op-id 的任何完成路径（`_complete_pending`）都必须持有同一 `_TargetLock`，锁内 pre-read 与 pipeline 现判之间无其他进程可行点——R0 F-4 所述「登记后、写锁前」滑动窗口消除 | **已修复** |
| F-5 | P3 | 无码改动，口径知悉（8 handlers） | 可接受：新注释按族列标度、不再携带单一错误计数；本 R1 申报自述即以 8-handler 认知为前提 | **知悉闭环**（披露面已修正，无需码改） |
| F-6 | P3 | 无码改动，措辞在 F-2/F-3 同块顺带如实化 | 注释现写「this change adds NO NEW SystemExit path (the pre-existing sys.exit(2) on a malformed --project-root stays)」——恰为 R0 建议的精度形态 | **已修复**（顺带） |

## 2. F-1 修复形态与红绿测试实质（R1 核验清单第 1 项）

### 2.1 分支逻辑（governance_store.py L1901-1940 区域）

三分支结构逐腿推演：

| 腿 | replay_source | owned_files | resume_released | 命中分支 | 结果 |
|---|---|---|---|---|---|
| fresh apply | "apply" | effects_of 活捕非空 | []（空台账） | 第一分支（活捕） | 章 = owned_files（与 FIX-370 既有行为一致）✓ |
| **re-apply（R0 缺口）** | "apply" | []（effects_of 未调） | pre-read 非空（pending 条目在手） | **第二分支（新增）** | 章 = resume_released ✓ |
| resume | "resume" | [] | pre-read 非空 | 第三分支 | 章 = resume_released（R0 已修）✓ |
| ledger replay / drift / refusal | "ledger"/无 | — | []（status!=pending 恒空） | 无分支 → 无 stamp 事务 | 与 R0/R1 前行为零变化 ✓ |

无误章路径论证：第二分支要求 `resume_released` 非空，而该值非空必须存在 fingerprint 匹配的 pending 条目——fresh apply 在空台账上 pre-read 恒 `[]`，故第二分支在 fresh apply 腿**结构性不可达**（R0 建议原样落地）；零文件释放（仅删 active_tasks）三分支均要求非空清单 → 不盖章，与既有 apply 腿语义一致；漂移/外来条目被三重 guard 挡在 pre-read（返回 []）→ 不盖章 fail-closed。

### 2.2 注释/docstring 如实性

- `_pending_released_files` docstring：明确「BOTH cross-crash recovery legs ... the resume leg ... and the re-apply leg (world at baseline → re-apply → complete with source="apply")」——R0 批评的「只描述一条腿」已消除 ✓。
- 三个分支注释各自溯源（B-10 登记先行 / R0 探针⑤ / 三腿 audit identical across ALL THREE completion legs）——R0 的「identical on both completion legs」过宽声明已被三腿如实化取代 ✓。

### 2.3 test_reapply_leg_completing_release_stamps_released_files（test L1225-1278）

**红态真实性：成立。**
- 场景构造真实复现 world==baseline：与 resume 测试（L1166，显式删锁模拟 world==target）相反，本测试**不改动世界**——seeded fixture 即 baseline（注释明示「the seeded fixture IS the baseline — nothing to mutate」），pending 条目登记后直接重放 → pipeline 走 `_state_matches(data, baseline)` → re-apply 腿 ✓。
- 腿钉：`assertEqual(result.get("replay_source"), "apply")`（L1266）——若误走 resume 腿此断言先红，测试不可能被 resume 腿假绿 ✓。
- effects_of 未调路径：`entry["released_files"]` 直接键访问（L1277）——修复前 re-apply 腿不盖章 → **KeyError**，与 Developer 申报的红态机制（KeyError: 'released_files'）一致 ✓。
- 绿态断言实质：world 三项删除断言（FIX-100 出 active_tasks、两文件出 file_locks，L1269-1271）证明 mutator 真实重放；`FIX-200 仍在 active_tasks`（L1272）= collateral-zero 守护；台账 status ok + `released_files == ["docs/a.md", "docs/b.md"]`（L1276-1278）= F-1 章值 = pending_effects 键集 sorted ✓。
- API 实存：`_ledger_entry`/`_ledger_transaction`/`_fingerprint`/`seed_release_fixture`/`call_release` 均为 R0 已核验签名复用，无幻觉 API。

### 2.4 独立闭环（非 Developer 测试路径）

R0 探针⑤（本审查自建 $TEMP 脚本：手造 pending 条目 + world==baseline → `locks_release`）R0 判 `released_files: MISSING`，R1 同脚本复跑 → **`released_files present: True | value: ['docs/a.md']`**。独立场景闭环，不依赖 Developer 测试自证。

## 3. F-2/F-3/F-4 勘正如实性（R1 核验清单第 2 项）

已在 §1 表逐条给出「注释 vs 实际 handler 返回面」比对：四族标度全对（对照 task_row_update.py L1142-1153、baseline_metadata.py L977-1052、governance_store.py L1982-1986）；F-2 面描述与 dsh_compat.py L2072-2075 及仓内调用点事实吻合；F-4 位移经 diff 证实且竞态闭合论证成立。**三处勘正均如实，无新引入的失实声明。**

装饰性观察（**F-7，P3，不要求修改**）：governance_store.py 指纹计算点（L1862-1864）保留了一段「capture ... BEFORE the pipeline completes」注释，而实际捕获调用已按 F-4 位移入锁块（块内另有更完整的 F-4 注释）——两段注释内容均属实、仅位置分离略显冗余；可选清理（删前段或合并），非必改。

## 4. 回归核验（R1 核验清单第 3 项）

| 项 | 申报 | 本审查独立实测 | 判定 |
|---|---|---|---|
| test_governance_store.py 全量 | 101 passed | **101 passed in 3.44s** | ✓ 一致 |
| 三边缘 9 测试点名 | 全绿 | **9 passed, 92 deselected in 0.94s**（7 个 R0 测试 + reapply_leg + 既有 resume 守护 test_resume_completes_without_reapplying_when_target_reached） | ✓ 一致 |
| check-governance --summary-only | 无新增非 REQ-092 FAIL | **FAIL 总数 5，全部 REQ-092（EVD-476/473/423 目标对齐/用户影响缺字段），非 REQ-092 FAIL = 0**，exit 0 | ✓ 一致 |
| R0 探针⑤ | —（Developer 侧为单测） | MISSING → **PRESENT ['docs/a.md']** | ✓ F-1 独立闭环 |

diff 纯净性：R1 增量 hunk 严格限于 F-1（stamp 三分支+docstring）、F-4（位移+注释）、F-2/F-3/F-6（verify_workflow 注释块）、reapply 测试与 import 行——无顺手改、无范围爬移；AI 专项 5 项在增量上复验（mock 残留无/硬编码返回值无/幻觉 API 无/TODO 无/过度实现无）。

## 5. 硬门槛裁决

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞数 | = 0 | 0 | ✓ |
| 5 维度全覆盖 | 100% | 正确性（三腿推演+独立闭环）✓ 安全性（guard/原子写纪律未触碰）✓ 可维护性（注释如实化完成，余 F-7 装饰性）✓ 性能（锁内多一次只读台账读，无感）✓ 测试覆盖（R0 缺口已由 reapply_leg 补齐，9/9 绿）✓ | ✓ |
| 每条发现标注级别 | 100% | F-7 带位置与事实；F-1~F-6 逐条带处置判定 | ✓ |
| 设计一致性 | 已完成 | 与 R0 建议修复形态逐字吻合；B-10 登记先行时序、`_complete_pending` 清空语义、家族 stamp 约定未破坏 | ✓ |
| AI 专项 5 项 | 全部完成 | 增量复验五项逐一有结论 | ✓ |

## 6. 总结论

**APPROVED ｜ unresolved_blockers = 0**（P0=0、P1=0、P2=0；唯一 P3=F-7 纯装饰性观察，不构成遗留义务）。

R0 有条件合并的全部条件已兑现并经独立实证：F-1 分支按建议形态落地、红态机制真实（KeyError）、独立探针 MISSING→PRESENT 闭环；F-2/F-3/F-6 勘正逐点属实；F-4 竞态闭合；回归三联（101 全量 / 9 点名 / 0 非 REQ-092 FAIL）与申报一致。复审链通过终态（round 1 < 3，无熔断），可流转 review-record 机录。
