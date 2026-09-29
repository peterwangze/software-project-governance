# FEAT-076 Code Review R0 — 证据分层迁移+稳态治理（Wave2 主载体）

- **Task**: FEAT-076（DEC-278 后继 / DEC-287 清偿轮 / DEC-292 Wave2 解锁 / DEC-293 全量执行）
- **Reviewer**: Code Reviewer Agent（独立复审，R0 首轮）
- **日期**: 2026-09-29 · **优先级**: P1
- **审查范围**: ①archive.py（族泛化引擎）②verify_workflow.py 的 GovernanceDataSource 族面 + Check 28s 三轨信息面（FIX-405/406 hunks 不在本审范围）③checks/review_domain.py（Check 19 冷层适配）④tests（test_archive FEAT076 类 + test_evidence_layer）⑤docs/architecture/feat076-consumer-matrix.md ⑥数据面（C-3 回填+迁移留痕+journal）
- **复跑**: TEMP 重定向 `.governance/tmp/check-run-20260929`；限定面（test_evidence_layer 6/6 OK；test_archive -k FEAT076 7/7 OK + FEAT075 类 12/12 OK；check-archive-integrity PASS；check-governance-data-size layers 面实测）——禁全量遵守，重试 0

## 1. 结论

# **APPROVED_WITH_NOTES**（unresolved_blockers=0 · P0=0 · P1=0 · P2=2 · P3=6）

九项验收全部核验通过；破坏性红线（dry-run 留痕+完整性时序）实质成立（一处留痕声明精度问题见 P2-1）。无阻塞问题，可合并。

## 2. 九项验收核验

| # | 验收项 | 判定 | 证据 |
|---|--------|------|------|
| ① | 引擎语义（resumable/journal fail-closed/回滚） | **PASS** | 逐行核读 migrate_evidence_resumable（archive.py:2813-3199）：journal 五阶段（intent→staging→staged→commit_intent→finalized）+ 世界判定顺序（committed→input→diverged，crash-after-hot-rewrite 优先判 commit pin）+ 三崩溃窗口恢复（archive 写后/热表改写后各可恢复）+ 拒绝码齐全（migration_state_conflict/hot_table_diverged/migration_context_changed/archive_target_conflict/migration_journal_conflict/migration_cursor_ahead_of_artifacts）。族独立 journal（category `evidence-{family}`）——同范围异族不冲突，真实世界三族 finalized journal 实存（`.migration/evidence{,-review,-reco}-v0.1.0~v0.91.0/`，commit 均=incremental-20260929-2）。`_rollback_evidence_archive` 已泛化四族前缀恢复（`_ROW_FAMILY_LINE_PREFIXES`，0.92 形态只恢复 EVD 行=族文件回滚丢行的缺陷已修）。新增 mkdir(parents=True) 修族腿首写 mkstemp 崩溃窗口。测试 12 个新/改写用例全绿 |
| ② | Q6 日期窗兜底三规则与 DEC-278 一致 | **PASS** | `_q6_date_window_fallback`（archive.py:1680-1706）：实体状态优先（仅 no-gating-ref 行进入兜底——六条件分类器先行，EVD 与三族路径同构）；行日期≤窗端发布日才迁；`_window_end_release_date` 要求路线图「已发布」行才给权威日期，否则 None→兜底拒绝（fail-closed 不猜）。测试双向：`test_date_window_fallback_classifies_all_four_families`（旧迁/新留/无日期留/族行同构）+ `test_no_released_window_end_disables_fallback_fail_closed`。leg3 实迁 49 行抽验：归档行首 ISO 日期全部 ≤ 0.91.0 发布日 2026-09-28（EVD-862/855-860=2026-08-01、EVD-587/294-304=2026-05~06）✓ |
| ③ | **迁移正确性抽查（5 行与 git 历史对照——内容零损）** | **PASS（带定性披露）** | git 最后跟踪版本 e19219a^（2026-06-17，FIX-141 untrack 前）含 527 族行。跨四族+incremental 抽 12 行：11/12 字节级相等（1 例为 PowerShell Out-String 折行伪差，精确重取后 5062=5062 相等）。升级为全量对照：0.91.0 系归档中可对照 264 行，243 字节级相等；21 例差异全部定性为**迁移前热表历史演进**（7 例 `｜`全角化——热表现存 29 行全角行从未迁移佐证其为既有状态；14 例行内修订/ID 重用〔EVD-277 refs 展开 +32、EVD-308 括号补全 +15×9 例规律性、EVD-423 ID 重写 FIX-108→AUDIT-110〕——均「归档=更新版、git=旧版」方向性演进，非截断/错位/丢失）。引擎侧 verbatim 语义有 journal digest 链（input_digest/archive_digest/hot_after_digest）+ 测试逐字断言双重支撑。**结论：迁移零内容损失成立**；21 例历史修订属 FIX-141 untrack 后不可 git 追溯的既有数据演化（P3-6 披露） |
| ④ | GovernanceDataSource 读入口语义 | **PASS** | 族面统一（get_all_family_rows/get_all_family_row_ids/find_row/layer_stats，verify_workflow.py:10106-1223）：hot-first 语义（工作集胜 id 冲突）；构造器 archive_root 从传入路径推导（`_infer_governance_dir`）——fixture patch EVIDENCE_PATH 时冷层指向临时目录，隔离成立；未知族 ValueError 大声失败。layer_stats 与索引一致：实测 EVD cold_rows 967 = index Evidence 条目 967 ✓；hot_bytes=515,685 实测 |
| ⑤ | Check 28s 三轨信息面 | **PASS** | check_governance_data_size（verify_workflow.py:21181-2136）：track1 热容量 schema 驱动不变（advisory）；track2 全库完整性=独立 check-archive-integrity（实测 PASS，Index entries 2601）；track3 总量 layers 信息面（hot/cold/total bytes + family_stats）实测输出 hot=515,685/cold=2,624,918/total=3,140,603——与 DEC-278 Q5 三轨语义（热工作集容量/全库完整性/总量增长监测）一致；增长告警骑行 EXC 周义务非第二阈值（合理设计） |
| ⑥ | review_domain 冷源注入防泄漏 + ④⑤⑥测试质量 | **PASS** | `_cold_review_evidence_lines` 以**当前模块全局** SAMPLE_PATH/EVIDENCE_PATH 构造 GovernanceDataSource（防定义期绑定泄漏——patch 传播实证于 test_check_agent_team_review_sees_cold_coverage）；live-mode 注入冷行、fixture 注入 evidence_path 时 hermetic（cold_rows=None 显式传参面）。测试质量：hermetic fixtures、正负双向断言（族行迁/留、已发布/未发布窗端、字节数/digest 断言、verbatim 逐字断言、未知族 ValueError）——6+7+12 用例复跑全绿 |
| ⑦ | 热表 425 行型化理由合理性抽验 | **PASS** | final-scan 分布（missing 199/out_of_range 58/active 31/dup 70/unparseable 45/keep 9/unknown 11/ambiguous 1/no_ref 1）合计恰 425 ✓。missing 口径抽验：热表 missing 行引用 FIX-233/235/240/241 等 → C-3 回填文件中登记为「未规划版本」（41 ID 如实留）→ `_version_to_tuple` 不可解析 → 周期不可证明 → fail-closed 留热——与 DEC-278(2) 禁猜归期红线自洽，「登记 ID 永久留热」口径成立（50 显式锚 ID 已解锁 leg2 的 131 行迁移）。live 复扫 428 行（+3 为迁移后新追加行），分布增量一致 |
| ⑧ | 消费者矩阵 26 组与三轨/不变式自洽 | **PASS** | feat076-consumer-matrix.md：I1-I4 不变式公理基础（写热/本票在热/活跃引用留热/冷层可定位）→ 26 组逐组标注（已适配 2/兼容证明 18/不受影响 6）与代码实况对账一致（#3 review_domain=已适配✓代码实况；#8 archive=本票主对象✓；#22 hooks I2 推演✓——本票查证语义不依赖冷层）；五条件闭合表与 DEC-282 C-1(b) 对齐；§2 协议/文档面处置（SKILL 行族索引查询路径已有）核验属实 |
| ⑨ | 零范围外 | **PASS** | 四文件 FEAT-076 域 hunks 全部在声明范围内：archive.py（全文件 FEAT-076）；verify_workflow.py 仅 GovernanceDataSource 族面 + check_governance_data_size layers 两处（其余 hunks=sessions BLOCKED/sd_integrity/VALID_OBTAIN_VALUES/execution-packet/release-projection 均标 FIX-405/406 批标签，未审）；review_domain.py（全 FEAT-076）；test_archive.py（FEAT076/FEAT075 类）。无夹带 |

**破坏性红线复核**：12 份 dry-run 留痕实存（feat076-dryrun-{leg1×4,leg2×4,leg3×4}，16:57/17:04/17:09，每真跑前有对应 dry-run）✓；完整性时序 5 时点连贯（pre-FAIL〔trigger gap 既有〕→post-migration PASS→post-c3 FAIL〔trigger gap，见 P2-1〕→post-decisions PASS→post-leg3 PASS），最终态+本次复跑 PASS ✓。三段统计独立复核：leg1 900=178+469+142+111、leg2 131=60+37+21+13、leg3 49=45+2+0+2，随批 risk1+DEC6，合计 1,087 ✓；索引计数守恒逐段恰等（1,423→2,324〔+901=900+risk1〕→2,546〔+222=131+C-3 91〕→2,552〔+6〕→2,601〔+49〕）✓。

## 3. Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-1 | **P2** | 留痕 `post-c3-integrity.txt` vs EVD-1258/notes §2.4 声明 | 「check-archive-integrity PASS×4」与留痕不符：4 份 post 时点留痕中 post-c3（17:04:47）记录 **FAIL**（issue=archive trigger gap——C-3 回填 91 任务行引入的 Check 27 触发面判定，非完整性计数失败；随后 decisions 迁移后恢复 PASS）。终态与本审复跑均 PASS，实质无缺口，但证据声明必须与留痕逐份一致 | EVD/收尾材料将「PASS×4」修正为「PASS×3 + 1 时点 FAIL（trigger gap 类，post-decisions 起 PASS）」，或在 notes 补一句 post-c3 FAIL 定性 |
| F-2 | **P2** | EXC-001 / Check 28s track1 | Developer 如实披露（notes §2.6）：热表 512,474B（现 515,685B）仍 >250KB error 线，EXC-001 **未撤销**。「199 行登记 ID 永久留热」口径下 track-1 的 250KB 阈值可能结构性不可达——这是 0.93 准入前必须裁决的开放决策项（EXC-001 条款本要求准入前失效/撤销再重评），非代码缺陷 | Coordinator/user 裁决：track-1 阈值按「登记留热豁免后口径」重定标，或例外续期——须 DEC 入账后再入 0.93 发布准入 |
| F-3 | P3 | archive.py `_q6_date_window_fallback` | 行日期=行内**第一个** ISO 日期 token：若摘要列先于日期列出现叙事性旧日期（引用某旧 EVD），兜底取叙事日期→方向为「多迁」。docstring 已披露 schema-drift-tolerant 权衡；leg3 实迁 49 行抽验未发现误迁实例（首 token 均取到行日期） | 后续若出现 Q6 误迁争议，考虑日期列优先、首 token 兜底的双级取值 |
| F-4 | P3 | review_domain `_cold_review_evidence_lines` / verify_workflow layers 面 | 两处 `except Exception: return []/None` 为 fail-open——冷层读取失败时 Check 19 退化为纯热面（方向保守：造成假 FAIL 而非假 PASS）、28s layers 置 None（信息面 never fatal 有注释）。设计可辩护但失败被静默 | 可选：失败时在 result 中携带 `cold_read_error` 披露字段（不改变判定语义） |
| F-5 | P3 | `migrate --auto ALL` 路径 | auto 的 ALL 经 migrate_by_version→`_migrate_evidence`（one-shot 无 journal），而 CLI migrate-big-table 是 resumable+journal 路径——两路径崩溃恢复能力不同（0.92 既有结构，非本票引入；生产迁移实际走了 resumable 路径 ✓） | 后续统一 auto 走 resumable 引擎（可挂 0.93+ 池外独立小票，非本票义务） |
| F-6 | P3 | 数据面历史债务（非本票引入） | ①热表 duplicate 70 行+git 对照发现的 EVD-423 ID 重写（FIX-108 旧行被 AUDIT-110 内容覆盖——0.4x 时代事件）；②21 例历史行修订/全角化属 FIX-141 untrack 后不可 git 追溯的既有演化 | 披露即可；若未来做 evidence 数据修复票可一并处理 |
| F-7 | P3 | journal fail-closed 实证留痕 | leg2 前四族 finalized journal 撞 `migration_state_conflict`（C-3 回填致世界漂移）的实证仅 notes 自述+journal 目录状态旁证（TRIAGE 缺失=重开后 0 候选不建 journal；三族存在=leg2/3 重开 finalize），无独立 stdout 留痕 | 未来拒绝类事件保留 stdout 留痕（机制本身有测试覆盖，不影响本结论） |
| F-8 | P3 | layer_stats 性能 | layer_stats 对每族各调一次 `_cold_family_lines` → 4×全量归档文件读（现 42 文件×4）。每 check 一次可接受 | 可选优化：单遍扫描按族分桶 |

**流程面观察**（非 findings，呈 Coordinator）：①execution-packets.json 无 FEAT-076 包（Developer 已记偏差 D-2，派发 prompt 为边界权威——Check 18c 面由 Coordinator 处置）；②R1 mainfile anchor 26,921→26,965 regen 已在工作区（吸收 FEAT-076+FIX-405/406 共 +44 行；regen 授权面属 FIX-405/406 批审查域，本审仅交叉披露）。

## 4. 五维度结论

| 维度 | 结论 |
|------|------|
| 正确性 | 引擎/journal/回滚/Q6/读入口逻辑逐行核验正确；边界（空世界/未知族/漂移/崩溃窗口）全覆盖；真实数据对账自洽 |
| 安全性 | fail-closed 全链（禁猜归期/未发布拒迁/未知族拒绝/digest 钉住/原子写+锁）；无注入/硬编码敏感数据/mock 残留 |
| 可维护性 | 单源分类器（scan=迁移零漂移）、族泛化不破坏 EVD 既有路径、命名注释充分 |
| 性能 | 批处理+digest O(n)；F-8 轻微读放大可接受 |
| 测试覆盖 | 17 个新/改写用例（核心/边界/错误路径+verbatim/digest 断言）全绿；限定面复跑实证 |

**AI 专项 5 项**：mock 残留=无 · 硬编码返回值=无（fail-closed 结构化错误）· 幻觉 API=无（stdlib only）· 未实现 TODO=无 · 过度实现=无（26 消费者仅 3 处必要适配，克制）。

**复审链**：R0（本报告）。

## 5. 证据锚

- 复跑输出：`.governance/tmp/check-run-20260929/`（本审新增 review-r0/ 子目录）+ d8-d14/feat076-* 留痕
- 对照基线：git `e19219a^:.governance/evidence-log.md`（527 族行）
- Journal：`.governance/archive/.migration/evidence{,-review,-reco}-v0.1.0~v0.91.0/journal.json`（phase=finalized）
- C-3 回填：`.governance/archive/tasks/backfill-20260929-feat076-c3.md`（91 行=41 未规划+50 显式锚）
