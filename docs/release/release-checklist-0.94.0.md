# Release Checklist — 0.94.0

- **版本**: 0.94.0 · **日期**: 2026-10-03（准备态——tag 未打） · **状态**: **组装进行中（M-1 版本面本批落地——定向验收已跑，门禁全量复跑 M-2）**
- **主题**: 次版本线：治理信号可信与元机制闭环批（Minor Line: Signal Trustworthiness & Meta-Mechanism Closure）——FEAT-081/082/083/084 + FIX-421~426 十票 / 用户 ask 授权 2026-10-03 启动发布链 REL-098
- **版本定义**: 次版本线（0.93.1→0.94.0）：新特性四件（M2 词集检测三件套 / behavior 面闭环率指标 / closure 采集单源化 / quick-scan 接线）+ 根因修复六件；无破坏性变更、无机制激活翻转（M2 词集检测 WARN 姿态起步）、无 `.governance` schema 变更（写侧台账三键格式为 0.88.0 FEAT-060 既有面，face-5 观测族按既有格式追加）；发布门 strict 0 FAIL 已达成（载荷十票全 committed）。

## 发布范围（冻结清单）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-081 | ADR-021 B4 M2 词集检测三件套（loop_gate_processor 新建+face-5 接线+19 用例；commit `2aa2377`；EVD-1293；R0 AWN/0；DEC-301） |
| 载荷 | FEAT-082 | ADR-021 B4′ behavior 面闭环率指标（session_closure 嵌套子面 10 叶键+单源导入+7-fixture 差分守护；commit `5de8548`；EVD-1294；R0 AWN/0；DEC-302） |
| 载荷 | FEAT-083 | closure 采集纯函数提取双端单源（引擎 155→18 行薄委托+bootstrap ~200 行镜像回收+接口等价测试；commit `c00d70c`；EVD-1302；R0 AWN/0；RISK-063 收敛路径） |
| 载荷 | FEAT-084 | quick-scan 接线会话健康摘要（--scope quick｜full 显式契约+缺省 full 字节等价+legacy performance 回退；commit `0377b78`；EVD-1297；R0 AWN/0；DEC-303；立项 memo `9a527cb`/EVD-1295） |
| 载荷 | FIX-421 | Check 28c 版本表状态列格式漂移解析修复（commit `8568b1b`；EVD-1296；R0 AWN/0） |
| 载荷 | FIX-422 | bootstrap 风险面 fabricated overdue 根因修复（commit `768021b`；EVD-1298~1300；R0 AWN/0；DEC-304） |
| 载荷 | FIX-423 | 预存 6 pytest 失败逐项归因处置（commit `9018006`；EVD-1301；R0 AWN/0；DEC-305） |
| 载荷 | FIX-424 | doc-sync 微票——docstring 计数与 purity 契约口径修正（commit `3883407`；EVD-1303；R0 AWN/0） |
| 载荷 | FIX-425 | 裁决①微票——纯谓词总括改写+ADR §3.2.3 锚（commit `b0075d8`；EVD-1304；R0 AWN/0） |
| 载荷 | FIX-426 | 裁决②探索票——docstring 口径 source-pinning 测试（commit `af7cfbd`；EVD-1305；R0 AWN/0） |
| 版本面 | REL-098 M-1 | 权威源 bump+`release-projection --write`（written=17 / write_then_probe=PASS / sd_integrity 28 scanned 0 unreadable / 幂等复跑 PASS@0.94.0）+双根 entry sync（sync_entry_projection.py --write ×2 root）+引擎锚（REQUIRED_SNIPPETS 六针脚）+CHANGELOG 准备态+发布三件套+对账台账（本批） |

## 运行前提（G-5——F-13 纪律固化）

**全程 TEMP 用仓库外路径**（pwsh：`$env:TEMP=<仓库外可写目录>; $env:TMP=$env:TEMP`）——仓库内 TEMP 重定向会使 identity attestation 的 snapshot 落入扫描根 → ROOT_SOURCE_AMBIGUOUS 假 FAIL（REL-096 门复跑实测根因）。

## 终态验证矩阵（arch D7——`docs/reconciliation-0.94.0.md` §七）

| 层面 | 放行条件 | 状态 @M-1 |
|---|---|---|
| 测试 | 双 cwd 独立新进程全席 0F+收集集一致+无未批准 skip | ✅ 已达（FIX-423：全量 4659P/0F 双跑一致+FIX-426 后 4666P/0F；M-2 复跑确认） |
| 治理 | strict 0 FAIL；可修 WARN 全修；历史对账/开放风险另行可见 | ✅ strict 0 FAIL 已达（FIX-422/423 后治理面 0 FAIL/6 WARN 全预存；M-2 复跑） |
| 归档 | integrity PASS+迁移/恢复/幂等回归 | ✅（持续复验；M-8 持续归档触发检查 dry-run 先行） |
| 行为安全 | CLI/路径/权限/敏感动作拦截契约零退化 | ⏳ 随 M-2/M-3 审查（B-23~B-27 非旗标面见 feature-flags-0.94.0） |
| 受管数据 | schema/锚/引用/生成物一致 | ✅ write-guard PASS |
| 发布 | check-release 0.94.0 全 PASS；M-0~M-8 完整 | ⏳ M-1 定向验收已跑；全量门 M-2 |
| 可追溯 | 被测 SHA=tag=ledger | ⏳ M-5a/M-6/M-7 |
| 回退 | 代码回退与数据恢复分别明确 | ✅ 本批 rollback-plan-0.94.0（11 commit 单独 revert 序列+数据面说明） |

## M-链完成态（锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 批授权 | ✅ | 用户 ask 授权 2026-10-03（发布链 REL-098 启动）+ 载荷十票全 committed（strict 0 FAIL 已达成） |
| M-1 版本面 | ✅（待提交） | 本批组装：投影 17 面+双根 entry×4+引擎锚+CHANGELOG+三件套+对账台账随批 |
| M-2 门禁 | ⏳ | check-release 全量复跑+strict 0 FAIL 复验（Coordinator） |
| M-3 审查 | ⏳ | 发布终审（R0→按需 R1） |
| M-4 发布四件套 | ✅（本批三件+checklist 本件） | rollback/feature-flags/checklist |
| M-5a/M-5b candidate | ⏳ | core/releases/0.94.0.json + transition 提交（Coordinator） |
| M-6 ledger | ⏳ | NATIVE_CANDIDATE→released 本地+remote 双 PASS（Coordinator） |
| M-7 tag+push | ⏳ | annotated tag v0.94.0（taggerdate 权威→CHANGELOG 回填位） |
| M-8 收口 | ⏳ | 发布态回填+快照更新+持续归档触发检查（dry-run 先行） |

## 回滚

见 `docs/release/rollback-plan-0.94.0.md`（代码面〔11 commit 单独 revert 序列+版本面 revert+regen〕与数据面〔零新增数据面；既有台账新观测族行说明；.governance 台账非 git 管理说明〕分别明确；无 B2 面、无迁移面新增）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 裁定关闭〔前提移除式〕+1.0.0 前置族暂缓——用户 2026-09-30 范围裁定延续）；对账台账口径为本版治理面事实，不构成上述任何声明。
