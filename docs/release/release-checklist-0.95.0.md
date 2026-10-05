# Release Checklist — 0.95.0

- **版本**: 0.95.0 · **日期**: 2026-10-05（准备态——tag 未打） · **状态**: **组装进行中（M-0 完成 + 发布产物四件套本批落地；M-1 版本面 bump 待 Governance Developer 派发，门禁全量复跑 M-2）**
- **主题**: 次版本线：「做薄·开放·主动探索」演进第一批（Minor Line: Thin, Open & Proactive Exploration — First Batch）——AUDIT-157/158 + FEAT-085/086 + FIX-432 五票 / DEC-312 用户裁定预留 0.95.0 / 发布链 REL-099
- **版本定义**: 次版本线（0.94.0→0.95.0）：Phase 0 基线与止增（R5 回溯基线/checks 四分层/W1~W7 责任清单/注入与架构基线快照）+ 有界 Phase 1 最小行为修复（M10 探索协议+exploration 区块+四通道六平台映射+前瞻样本验收）+ 称谓统一与引文守卫；无破坏性变更、无机制激活翻转、无 `.governance` schema 变更（exploration 区块复用既有 evidence 载体）；载荷经 DEC-312(7) M-0 冻结（FEAT-087/088/Slice-3 走 0.96.0 候选池）。
- **M-0 组装核算**: 见 `docs/release/m-0-assembly-0.95.0.md`（B16 债务两栏核算/FEAT-084 Slice-3 结论/载荷一致性核对/版本号决策记录）。

## 发布范围（冻结清单——DEC-312(7)）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | AUDIT-157 | 「做薄·开放·主动探索」演进立项（现状盘点+arch 两轮共同决策+总纲 A1~A14+用户三项裁定+四账本入账；EVD-1312；DEC-312；零产品行为变更） |
| 载荷 | AUDIT-158 | Phase 0 基线与止增（基线四件套；EVD-1313；DEC-313 arch 第三轮裁定通过；零产品行为变更——分析票） |
| 载荷 | FEAT-085 | Phase 1 最小行为修复（M10 协议唯一规范源+SKILL.md 薄入口+exploration 区块+四通道语义+adapter 映射降级；EVD-1314；REVIEW-FEAT-085-R0 AWN/0；DEC-314 拆票口径） |
| 载荷 | FEAT-086 | Phase 1 收尾批（三类前瞻样本 5 例验收+F-2 映射+F-6 validate 细化+六平台 exploration_channels——consult 不含 draw；EVD-1315；REVIEW-FEAT-086-R0 AWN/0；DEC-314(1)/DEC-315） |
| 载荷 | FIX-432 | M0-M9→M10 sweep 19 处+quote_sync 引文同步守卫+F-A2 note 监控面+F-A5 四态定夺（EVD-1316/1317；REVIEW-FIX-432-R0/R1 双轮 AWN/0；DEC-315 扩承载+DEC-316 姿态定夺；commits `9a28e4d`/`c68cbbd`——DEC-316） |
| 版本面 | REL-099 M-1 | 权威源 bump+`release-projection --write`+双根 entry sync（sync_entry_projection.py --write ×2 root）+引擎锚（REQUIRED_SNIPPETS 六针脚）+CHANGELOG 准备态（本批已落）+发布四件套（本批）——**待 Governance Developer 执行** |

**不发布什么（Amazon 口径——scope creep 防护）**：FEAT-087（前瞻样本第二批）、FEAT-088（通道探活守卫）、FEAT-084 Slice-3 缓存子集（DEC-303(4) 留池）——均在 0.96.0 候选池不占本版；archive.py 拆分（C2）与 checks L3/L4 退役实施不在本版（Phase 2/3 节奏）；REQ-147 仅交付 Phase 0 基座不主张全量交付。

## 运行前提（G-5——F-13 纪律固化）

**全程 TEMP 用仓库外路径**（pwsh：`$env:TEMP=<仓库外可写目录>; $env:TMP=$env:TEMP`）——仓库内 TEMP 重定向会使 identity attestation 的 snapshot 落入扫描根 → ROOT_SOURCE_AMBIGUOUS 假 FAIL（REL-096 门复跑实测根因；0.94.0 checklist 同款纪律延续）。

## 检查项（逐项——发布门 G9）

### A. 范围一致性（载荷五票 vs 路线图 vs 任务状态）

- **结论**: ✅ **PASS（M-0 实读核算）**——五票 plan-tracker L80~L84 全 ✅ completed；0.95.0 路线图行在位（L207，DEC-312 预留）；REQ-146 ✅ 已交付（L478）；审查链全 AWN/0 终态（REVIEW-FEAT-085-R0/REVIEW-FEAT-086-R0/REVIEW-FIX-432-R0·R1）。
- 差异披露：L207「包含任务」列未回填 FEAT-086✅/FIX-432✅（拆票承载入链——DEC-314(1)(3)/DEC-315，不破冻结）；建议 M-8 收口补记（m-0 报告 §1.2/§7）。

### B. 版本声明 13 处（**待 Governance Developer bump 执行**——M-1）

当前实读全为 0.94.0（bump 前正确态）。bump 面 13 处清单（文件实读枚举——与调度口径总数 13 一致，分组以实读为准：marketplace 实为 ×1、plugin.json 实为 ×4）：

| # | 文件 | 位置（实读） |
|---|---|---|
| 1 | `skills/software-project-governance/SKILL.md` | frontmatter `version:`（L3——**权威源，bump 起点**） |
| 2 | `skills/software-project-governance/core/manifest.json` | `"version"`（L4——canonical source of truth，VERSIONING L75） |
| 3 | `.claude-plugin/marketplace.json` | `plugins[0].version`（L12） |
| 4 | `.claude-plugin/plugin.json` | `version`（L3） |
| 5 | `.codex-plugin/plugin.json` | `version`（L3） |
| 6 | `.chrys-plugin/plugin.json` | `version`（L3） |
| 7 | `.zcode-plugin/plugin.json` | `version`（L3） |
| 8 | `skills/software-project-governance/infra/hooks/pre-commit` | `# @version:`（L6） |
| 9 | `skills/software-project-governance/infra/hooks/commit-msg` | `# @version:`（L5） |
| 10 | `skills/software-project-governance/infra/hooks/post-commit` | `# @version:`（L4） |
| 11 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | `# @version:`（L6） |
| 12 | `AGENTS.md`（仓库根） | `@bootstrap-version:` 标记 |
| 13 | `CLAUDE.md`（仓库根） | `@bootstrap-version:` 标记 |

执行形态（0.93.x/0.94.0 先例同构）：权威源先 bump → `release-projection --write` 单次确定性收敛 → `sync_entry_projection.py --write`（双根 entry：repo root + e2e fixture 的 AGENTS.md/CLAUDE.md ×4 面）→ 引擎锚 REQUIRED_SNIPPETS 六针脚 → 幂等复跑 PASS@0.95.0。**非 13 处但随链跟踪**：`project/CHANGELOG.md` 0.95.0 段（本批已落）；`.governance/plan-tracker.md` 工作流版本（L11——发布收口由 Coordinator 回写）。

### C. 验证命令（**待 M-2 复跑**——含 BM-R1-3 残余闭合）

| 命令 | 预期 | 状态 |
|---|---|---|
| `python -m unittest test_verify_workflow` | **1052 tests OK**（1047+5——FIX-432 R1 QuoteSyncGuardTests 无 EVD 机录，review-FIX-432-CODE-R1 BM-R1-3 一条命令闭合） | ⏳ 待 Coordinator |
| `check-governance --summary-only`（发布门 full 面） | 基线 **1 issue（28n 预存）零新增**（EVD-1316 口径） | ⏳ 待 Coordinator |
| `check-injection-budget` | resident 4244/6000、M1+M2 342/370 **零变化**（EVD-1315/1316 同值） | ⏳ 待 Coordinator |
| `check-cross-references`（含 quote_sync）/ `check-manifest-consistency` | PASS（EVD-1316 已证，门禁复跑） | ⏳ 待 Coordinator |
| `check-version-consistency` | bump 后 13 处一致 @0.95.0 | ⏳ 待 M-1 后 |
| `check-release --version 0.95.0 --require-changelog --lineage-mode candidate` | 全 PASS（默认含 verify/check-governance --fail-on-issues/e2e-check/unittest） | ⏳ M-2 |
| `release-ledger --version 0.95.0 --no-remote` | candidate 态 PASS（UNKNOWN/BLOCKED 不包装为 PASS） | ⏳ M-5/M-6 |
| `quality-tools` | 结构化记录（未安装记 NOT_RUN，不虚构 PASS） | ⏳ M-2 |
| tag/push 后：`check-release --version 0.95.0 --require-changelog --lineage-mode released --release-commit <commit>` + `release-ledger --version 0.95.0 --remote origin` | released 双 PASS | ⏳ M-7 |
| `archive.py migrate --auto --dry-run`（如需→执行+`check-archive-integrity`） | 无待归档或归档闭环 PASS（失败阻断发布完成） | ⏳ M-8 |

### D. 回滚方案在位

- **结论**: ✅ **PASS**——`docs/release/rollback-plan-0.95.0.md`（回滚基线 tag v0.94.0@6da8d04；代码面/数据面分别明确；步骤/验证/预计时间/触发条件四要素齐备）。发布前实际演练按 stage-release SKILL「需测试环境执行」口径由 Coordinator 在 M-2 面评估（回滚方案为确定性再生+revert 序列，验证命令在位）。

### E. 审查计划

- **结论**: ⏳ **待执行（M-3）**——发布终审 **Release Reviewer**（review-record 机录，`docs/reviews/review-REL-099-M3b-REL-R0.md` 形态）；建议按 0.94.0 双审先例追加 M-3a Code Reviewer 定向面（M-1 版本面为确定性再生——定向审查 bump 面+CHANGELOG+四件套即可）。NEEDS_CHANGE → 同一 Reviewer 复审 round+1（触发器 T1）；round≥3 → BLOCKED+escalation。

### F. Feature Flags / Kill Switch

- **结论**: ✅ **N/A——本版无 feature flag 面**（不创建 feature-flags-0.95.0.md）：M10 为行为协议层（agent 行为约束）非运行时旗标机制；无机制激活翻转；无 B 类旗标债务。行为变更回退 = git revert（见 rollback-plan）；Kill Switch 不适用（无运行时可翻转机制）。用户可感知行为变更（新任务探索适用性判断）已在 CHANGELOG 0.95.0 段「行为变更（非旗标面）」披露。

## M-链完成态（锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 批授权+组装核算 | ✅ 本批 | DEC-312(5) 用户预留+五票全 completed+`m-0-assembly-0.95.0.md`（B16 两栏/Slice-3/载荷核对/版本号决策） |
| M-1 版本面 | ⏳ 待派发 | Governance Developer：13 处 bump+投影再生+双根 entry×4+引擎锚+CHANGELOG 回填（版本面再生纪律段） |
| M-2 门禁 | ⏳ | Coordinator 复跑 §C 全量（含 1052 闭合——BM-R1-3 残余） |
| M-3 审查 | ⏳ | Release Reviewer 终审（+按需 Code Reviewer——0.94.0 双审先例） |
| M-4 发布四件套 | ✅ 本批 | checklist（本件）/rollback-plan/m-0-assembly + CHANGELOG 段；feature-flags 件 N/A（§F） |
| M-5a/M-5b candidate | ⏳ | core/releases/0.95.0.json + transition 提交（Coordinator） |
| M-6 ledger | ⏳ | NATIVE_CANDIDATE→released 本地+remote 双 PASS（Coordinator） |
| M-7 tag+push | ⏳ | annotated tag v0.95.0（taggerdate 权威→CHANGELOG 日期单元格回填——FIX-349 口径） |
| M-8 收口 | ⏳ | 发布态回填+快照更新+持续归档触发检查（dry-run 先行）+L207/L11 回填+0.94.0 收口残留核实（m-0 报告 §7） |

## 回滚

见 `docs/release/rollback-plan-0.95.0.md`（代码面〔版本面 revert+regen 与载荷面按需 revert 序列〕与数据面〔exploration evidence 行 append-only additive；.governance 台账非 git 管理〕分别明确；无迁移面新增、无旗标面）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；非 Windows 平台未验证，验收全部在仓库内完成；M-0 未执行 L4 删除/L3 迁移（Phase 0 裁定与退役实施分开验收——DEC-313）；archive.py 拆分债未偿如实披露（FIX-430 exclusions 止增在位）；REQ-147 仅 Phase 0 基座交付。

## 签名栏

| 角色 | 签署 | 日期 | 备注 |
|---|---|---|---|
| Release Agent（起草） | ✅ REL-099 组装（机器事实=EVD 行+文件实读；Bash 禁止契约） | 2026-10-05 | 本件+三产物 |
| Coordinator（会签） | ⏳ 待签 | — | M-1 派发前确认范围与 13 处清单 |
| Release Reviewer（会签） | ⏳ 待签 | — | M-3 发布终审（review-record 机录） |
