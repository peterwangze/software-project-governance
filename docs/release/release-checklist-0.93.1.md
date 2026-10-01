# Release Checklist — 0.93.1

- **版本**: 0.93.1 · **日期**: 2026-10-01（准备态——tag 未打） · **状态**: **组装进行中（M-1 版本面本批落地——验收①-⑤ 已跑，门禁全量复跑 M-2）**
- **主题**: 补丁线：验证根因修复批与归档健康收口（Patch Line: Verification Root-Cause Fix Batch & Archive Health Closure）——FIX-414~419 六件 + 卫生批 / arch 顾问 D1-D7 裁决集 / 用户 2026-09-30 预授权令 + 0.93.1 M-0 决策
- **版本定义**: 补丁线（0.93.0→0.93.1）：无新特性、无机制激活翻转、无破坏性变更、无 `.governance` schema 变更；修复范围经 arch 顾问 D1-D7 裁决集界定（对账台账 `docs/reconciliation-0.93.1.md`——随本批 M-1 一并提交）；1.0.0 暂缓/官方提交暂缓（用户 2026-09-30 范围裁定）。

## 发布范围（冻结清单）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FIX-414 | 测试期望与 FIX-413 契约对齐（released 复跑 1F 消除；commit `65cf188`；EVD-1274；R0 AWN/0） |
| 载荷 | FIX-415 | HotFact cwd 根因修复（HOST_PROJECT_ROOT import 期绑定钉根+SD 虚构化；commit `fe0afcb`；EVD-1275；R0 AWN/0） |
| 载荷 | FIX-416 | 归档触发判定+CLI 口径对齐（migrate --auto 默认 ALL；commit `2fa1ebd`；EVD-1276；R0 AWN/0） |
| 载荷 | FIX-417 | archive.py 最小内聚拆分 6016→4241（28n ERROR 清零；commit `b12eee1`；EVD-1282；R0 AWN/0） |
| 载荷 | FIX-418 | infra-cwd 11F 分类根治（双 cwd 4591/4591；commit `693fea8`；EVD-1283；R0 AWN/0） |
| 载荷 | FIX-419 | release_docs 阈值重校准 80→100（arch D4；commit `bdc037e`；EVD-1281；R0 AWN/0） |
| 卫生批 | 对账台账 | ragged 根因闭环 / 风险面三态 / 28q·28m 消解 / docs 迁移否证回退对（`263779f`↔`7d6c4a7`）——`docs/reconciliation-0.93.1.md` |
| 版本面 | REL-097 M-1 | 权威源 bump+`release-projection --write`（written=17 / write_then_probe=PASS / sd_integrity 0 unreadable / 幂等复跑 PASS@0.93.1）+双根 entry sync+引擎锚（REQUIRED_SNIPPETS 六针脚）+CHANGELOG 准备态+发布三件套（本批） |

## 运行前提（G-5——F-13 纪律固化）

**全程 TEMP 用仓库外路径**（pwsh：`$env:TEMP=<仓库外可写目录>; $env:TMP=$env:TEMP`）——仓库内 TEMP 重定向会使 identity attestation 的 snapshot 落入扫描根 → ROOT_SOURCE_AMBIGUOUS 假 FAIL（REL-096 门复跑实测根因）。

## 终态验证矩阵（arch D7——`docs/reconciliation-0.93.1.md` §七）

| 层面 | 放行条件 | 状态 @M-1 |
|---|---|---|
| 测试 | 双 cwd 独立新进程全席 0F+收集集一致+无未批准 skip | ✅ 已达（FIX-418：4591/4591 OK exit 0；M-2 复跑确认） |
| 治理 | strict 0 FAIL；可修 WARN 全修；历史对账/开放风险另行可见 | ⏳ M-2（历史对账面见台账 §三——0-blocking 历史形态不改写） |
| 归档 | integrity PASS+迁移/恢复/幂等回归 | ✅（持续复验；0.93.1 窗口归档两轮+衍生清扫已执行） |
| 行为安全 | CLI/路径/权限/敏感动作拦截契约零退化 | ⏳ 随 M-2/M-3 审查（B-21/B-22 非旗标面见 feature-flags-0.93.1） |
| 受管数据 | schema/锚/引用/生成物一致 | ✅ write-guard PASS |
| 发布 | check-release 0.93.1 全 PASS；M-0~M-8 完整 | ⏳ M-1 验收②版本识别已验；全量门 M-2 |
| 可追溯 | 被测 SHA=tag=ledger | ⏳ M-5a/M-6/M-7 |
| 回退 | 代码回退与数据恢复分别明确 | ✅ 本批 rollback-plan-0.93.1（六 commit 单独 revert 序列+零新数据面声明） |

## M-链完成态（锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 批授权 | ✅ | 用户 2026-09-30 预授权令+0.93.1 M-0 决策+arch D1-D7 裁决集 |
| M-1 版本面 | ✅（待提交） | 本批组装：投影 17 面+双根 entry+引擎锚+CHANGELOG+三件套+对账台账随批 |
| M-2 门禁 | ⏳ | check-release 全量复跑+strict 0 FAIL |
| M-3 审查 | ⏳ | 发布终审（R0→按需 R1） |
| M-4 发布四件套 | ✅（本批三件+checklist 本件） | rollback/feature-flags/checklist |
| M-5a/M-5b candidate | ⏳ | core/releases/0.93.1.json + transition 提交（Coordinator） |
| M-6 ledger | ⏳ | NATIVE_CANDIDATE→released 本地+remote 双 PASS（Coordinator） |
| M-7 tag+push | ⏳ | annotated tag v0.93.1（taggerdate 权威→CHANGELOG 回填位） |
| M-8 收口 | ⏳ | 发布态回填+快照更新+持续归档触发检查（dry-run 先行） |

## 回滚

见 `docs/release/rollback-plan-0.93.1.md`（代码面〔六 commit 单独 revert 序列+版本面 revert+regen〕与数据面〔零新数据面；.governance 台账非 git 管理说明〕分别明确；无 B2 面、无迁移面新增）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 裁定关闭〔前提移除式〕+1.0.0 前置族暂缓——用户 2026-09-30 裁定）；对账台账三态口径（已修复/历史已对账/裁定闭环）为本版治理面事实，不构成上述任何声明。
