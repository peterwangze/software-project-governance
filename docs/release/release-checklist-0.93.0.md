# Release Checklist — 0.93.0

- **版本**: 0.93.0 · **日期**: 2026-09-29（准备态——tag 未打） · **状态**: **候选链进行中（R0 终审 NEEDS_CHANGE 已快修——C1~C5 闭合，门复跑+R1 重审待办）**
- **主题**: 元机制执法双件与例外清偿终局（Meta-Mechanism Enforcement Pair & Exception Ledger Finality）——DESIGN-021/FEAT-077~080/FEAT-076/FIX-403~409 载荷 / DEC-286(7)+290~296 / EVD-1240~1264+
- **版本定义**: DEC-292 批授权 + DEC-293 用户裁定单轮；**发布准入零例外承载**（EXC-001 重校准 DEC-295 / EXC-002 关闭 DEC-294 / EXC-003 删除 DEC-296——三例外全终局）；无破坏性变更、无机制激活翻转（B-12/B-13/RB2 出厂姿态不变；M1/M2 为引擎执法面，见 feature-flags-0.93.0）。

## 发布范围（冻结清单——DEC-292/293）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | DESIGN-021 | ADR-021 元机制双件（M1 优先级执法+M2 发现即闭环）——R0 NEEDS_CHANGE→23 处返工→R1 AWN/0；DEC-290/291 |
| 载荷 | FEAT-077 | M1-B2 demand_source 字段+优先级加权+provenance_domain 模块+修订通道 |
| 载荷 | FEAT-078/079 | 契约四面注入（348 tok 实测）+ 分层锚注册反走私预算（M1≤180/M1+M2≤370） |
| 载荷 | FEAT-080 | M1-B3 接线：Check 41/42 入聚合器、CLI --demand-source 必填、发布门 provenance 子检查、freeze-line、zerodrift、packet 增量合并（+regen rider） |
| 载荷 | FEAT-076 | 证据分层迁移与稳态治理——1087 行三腿迁移（热表 −70.9%）、C-3 91 ID 清偿、GovernanceDataSource 门面、Check 28s 三轨、Q6 日期窗 |
| 载荷 | FIX-403~409 | 稳定性/SD 根修链（FIX-405/406 SD 门+重校准；FIX-407 EXC-003 终局 decision-log 259K→177K；FIX-408 hermetic+勘误；FIX-409 writer ACL 根修+write-then-probe；FIX-403/404 清理族） |
| 版本面 | REL-096 | 权威源 bump+引擎锚+release-projection 单次写入 17 面（幂等 written=0；**write_then_probe=PASS 首例**）+双根 entry sync+CHANGELOG 准备态+发布三件套（本批） |
| 整改面 | REL-096 R0 | C1（CHANGELOG 三处：Fixed 段/准备态日期字面/archive.py 实测 5,959 行/274,228B）+C2（intake 带 demand_source 补建——Coordinator）+C3/C4（发布三件套+回滚面）+C5（EVD 机录）+热事实三面（roadmap 行/总览/快照版本戳） |

## 运行前提（G-5——F-13 纪律固化）

**全程 TEMP 用仓库外路径**（pwsh：`$env:TEMP=<仓库外可写目录>; $env:TMP=$env:TEMP`）——仓库内 TEMP 重定向会使 identity attestation 的 snapshot（mkdtemp 随 $TEMP）落入扫描根 → ROOT_SOURCE_AMBIGUOUS 假 FAIL（REL-096 门复跑实测根因）。

## 门禁与审查锚（R0→R1）

| 面 | 状态 |
|---|---|
| 发布门 check-release --version 0.93.0 | R0 时 7 issues（3 热事实+3 docs 缺失+provenance）→ C1~C5+热事实闭合后**待复跑**（预期全 PASS） |
| 发布终审 R0 | NEEDS_CHANGE（三处 P1 文本级）→ 快修闭合，R1 同一 Reviewer 重审待办 |
| 载荷审查链 | 12 commits 全 R0/R1 AWN/0（终窗 `4f52c6b`） |
| 版本一致性 | PASSED（警告 9→0——DEC-213③ 豁免 7 条注册：1 重锚+6 bump-time，R0 逐行定性） |
| 注入预算 | 三档全过：strict 5957 / standard 5685 / lightweight 4207（≤6000） |

## 发布收口一次性项（本版特有——M-7 前后执行）

1. **CLAUDE.md takeown（仓库根，一次性）**：普通终端执行 `takeown /f CLAUDE.md && icacls CLAUDE.md /grant "%USERNAME%:F"`——根治历史 SD 受损（python 写拒；内容已规范但未来 python 系 sync 会再崩）。REL-096 组装期经 harness 通道字节级复原（10115B 与 sync 计算目标一致）。
2. **环境残留目录清理（普通终端，一次性）**：`Remove-Item -Recurse -Force spg-projection-bghpqx4_, spg-projection-lz5mmgx9, .pytest_cache`——历史 writer 失败趟与 pytest 缓存的拒读 ACL 残留（gitignored，新 writer 不再产出）。
3. **非沙箱终端复跑三类验证（发布后验证）**：①check-governance --summary-only --level strict（全量）②python -m unittest discover（全席——沙箱内已知环境性 ERROR 面在非沙箱应全绿）③check-release --version 0.93.0（released 态复跑）。

## M-链完成态（锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 批授权 | ✅ | DEC-292（B5 闸门）+DEC-293（用户单轮裁定） |
| M-1 版本面 | ✅（待提交） | 本批组装：17 面投影+双根 entry+CHANGELOG+锚+豁免（write_then_probe=PASS） |
| M-2 门禁 | ⏳ | R0 7 issues 闭合→门复跑待办（本 checklist §门禁） |
| M-3 双半面审查 | ⏳ | R1 重审（同一 Reviewer）待办 |
| M-4 发布四件套 | ✅（本批三件+checklist 本件） | rollback/feature-flags/checklist（release-plan 非门禁必需面，0.92 四件套含——按需补） |
| M-5a/M-5b candidate | ⏳ | core/releases/0.93.0.json + transition 提交（Coordinator） |
| M-6 ledger | ⏳ | NATIVE_CANDIDATE→released 本地+remote 双 PASS（Coordinator） |
| M-7 tag+push | ⏳ | annotated tag v0.93.0（taggerdate 权威→CHANGELOG 回填位） |
| M-8 收口 | ⏳ | 发布态回填+快照更新+fix407-backup 结账后清理排程 |

## 回滚

见 `docs/release/rollback-plan-0.93.0.md`（回滚三序：迁移面〔fix407-backup 备份随 `.governance/tmp` 迁出至仓库外临时区，sha256 70F74584… 保留至结账〕→版本面 revert+regen→载荷链按需；无 B2 面）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）；三例外终局为本版治理面事实，不构成上述任何声明。
