# Release Checklist — 0.79.0 (REL-075)

**Version**: 0.79.0 (MINOR — DEC-177 ⑧ 确认；范围核增 DEC-181〔FIX-292〕+ DEC-184②〔FIX-299/300 核增 0.79.0∥〕)
**Window**: `v0.78.1 (6b5e7bf) .. <final pre-transition commit>` — **34 commits 已合入**（M-1 核定 2026-09-10，`git log v0.78.1..HEAD`——version-plan §0 待验证项①闭环）+ 本候选 commit（M-1 打包：版本投影〔子任务 A〕+ CHANGELOG/三件套〔子任务 B〕）
**Status**: candidate（`release_authorized=false`；transition/tag/push 待 M-4 用户授权——DEC-143，唯一人工门）

## Release Scope (per version-plan-0.79.0.md §5 + DEC-177/181/184)

| 分组 | 任务 | 版本归属 |
|---|---|---|
| 基线范围（DEC-172② / DEC-177①） | FIX-291（W-7/BC-7 + FIX-281 判定面①⑧）、FEAT-011（G3 扩展——governance-write-guard）、FEAT-012（G5+G6）、FEAT-013（RISK-046 根因修复）、FEAT-014/015/016（RISK-049 关闭标准①②③） | 0.79.0 |
| M-0 核增（DEC-177②③④） | FX-195（quick-scan 前移评估——RISK-044 缓解承载）、AUDIT-149（健康 117 前置诊断——规划期） | 0.79.0 |
| 范围核增（DEC-181） | FIX-292（18c~18i 执行包谓词对齐——AUDIT-149 N1）+ FIX-293（P2-1(b) 数据面承接——治理记录快速通道） | 0.79.0 |
| 降噪/缺陷批（AUDIT-149 诊断产出承接） | FIX-294（Check 36 R3 归档 ID 解析）、FIX-295（Check 10 M5 扫描面收窄）、FIX-296（execution-packet data-loss footgun——EVD-959）、FIX-297（FEAT-011 F-1 处置：M1.2 MUST + 分级口径） | 0.79.0 |
| DEC-184② Q4 核增 | FIX-299（cmd_check_release 恒 exit 1）、FIX-300（Check 31 口径差） | **0.79.0∥**（缺陷显式修复先行——契约冻结前置） |
| 0.80.0 重构线 P0（DEC-183/184①——任务行定位 0.80.0，物理合入本窗随 0.79.0 工件交付） | AUDIT-150/151/152、DOC-003、FEAT-017（hook 接线）、FEAT-018（性能协议）、FEAT-019（ArchGuard 棘轮 R1~R7）、FIX-301（归档识别修复）、FEAT-020（契约矩阵冻结）、FIX-302（canonical 措辞同步） | 0.80.0（随窗交付注记） |
| 治理记录面（gitignored 无产品 commit） | FIX-293（EVD-963）、EVD-983 真数据归档迁移（88 task + 58 DEC + 5 risk + 12 EVD，R1(b) 备份 + integrity PASS）、REL-074 规划产物、REL-075 本候选打包 | 0.79.0 周期 |
| 风险挂载（DEC-169② MUST） | RISK-044 正式复评——已执行（M-0 ④ DEC-177②：已接受 → **缓解中**；4 样本 3/4 超 60s 修订验收线） | 0.79.0 §6 |

**不在本版**（出槽登记见下）：FIX-298（⏳ blocked_by REL-002）、quick-scan 实现 Slice-1/2/3、REQ-109/111/113/114、RISK-049 残余候选（live/headless 会话面、非 dsh 适配器等级映射）、FEAT-013 遗留 F-1/F-2/F-4、各任务 P2/P3 遗留。

## Change Inventory（34 commits — `git log v0.78.1..HEAD`，2026-09-10 核定）

| # | 任务 | commit(s) | 终态要点（✅ + 审查终态 + EVD） |
|---|---|---|---|
| 1 | REL-074 | `ff4bd43` | ✅ 规划段 + M-0（DEC-177）；规划期双审 APPROVED_WITH_NOTES/0；EVD-948 |
| 2 | FIX-291 | `5c630d7` | ✅ 判定面批（Check 30 历史格式迁移 + 30c 机器行分类 + 终态 marker 集）；Code R2 + Design R2 双审 APPROVED_WITH_NOTES/0；EVD-949 |
| 3 | FEAT-014 | `f473ace` | ✅ RISK-049①（Check 28t + README 等级标注）；R0→R1 APPROVED_WITH_NOTES/0；EVD-955 |
| 4 | FEAT-015 | `0996d6d` | ✅ RISK-049②（launch.py --smoke + Check 28u，隔离环境三选一取 (a)）；R0 APPROVED_WITH_NOTES/0；EVD-956/957 |
| 5 | AUDIT-149 | `8b9c835` | ✅ 健康 117 构成诊断（18c~18i 根因 + 降噪域 N1~N7）；EVD-958 |
| 6 | FIX-292 | `c91d705`+`1d3d973`+`58f8e9f` | ✅ 范围核增入账 + 18c~18i 谓词对齐（同数据 124→88）+ 表格修复；双审 APPROVED_WITH_NOTES/0 ×2；EVD-960 |
| 7 | FIX-293 | —（治理记录） | ✅ M1 存量行形状修复（write-guard FAIL 7→PASS/exit 0）；EVD-963 |
| 8 | FEAT-011 | `e90ed17` | ✅ governance-write-guard 四面守卫（G3 扩展）；Design R0 + Code R1/R2 三审 APPROVED_WITH_NOTES/0；EVD-962 |
| 9 | FIX-297 | `b8f6ca3`+`fe2faca` | ✅ M1.2 MUST + SKILL 分级口径 + e2e 投影同步；Design R0 APPROVED_WITH_NOTES/0；EVD-964 |
| 10 | FIX-294 | `76f67bd` | ✅ Check 36 R3 归档 ID 解析（33 WARN→19 + 46 EXEMPT）；Code R0 APPROVED_WITH_NOTES/0；EVD-965 |
| 11 | FIX-295 | `fc1b739` | ✅ Check 10 M5 扫描面收窄（FAIL→PASS，39→37）；Code R0 APPROVED_WITH_NOTES/0；EVD-966 |
| 12 | FIX-296 | `3cbdc92` | ✅ execution-packet --task 过滤仅 stdout（write 恒全量）；Code R0 APPROVED_WITH_NOTES/0；EVD-967 |
| 13 | FEAT-016 | `213fbba`+`ce7fa79` | ✅ RISK-049③（dsh_upgrade_regression release gate 组件）+ 闭环回写；R0 APPROVED_WITH_NOTES/0；EVD-970 |
| 14 | AUDIT-150 | `2be00ec` | ✅ 系统性架构检视 + 0.80.0 重构演进规划（DEC-183）；Design R0 APPROVED_WITH_NOTES/0；EVD-971/972 |
| 15 | AUDIT-151 | `61ef056` | ✅ 测试收集关系调查与全量基线（2,194 三方恒等；26 failed 逐例归属）；EVD-974 |
| 16 | FIX-299 | `1cda292`+`90140cc` | ✅ cmd_check_release 恒 exit 1 修复（0.79.0∥）；R0 APPROVED_WITH_NOTES/0；EVD-975 |
| 17 | FIX-300 | `e994c7a` | ✅ Check 31 身份子相位口径差（RCA 三机制，判定规则零改动）；R0 APPROVED_WITH_NOTES/0；EVD-976 |
| 18 | FEAT-017 | `c6026ce` | ✅ post-commit Step 4b 接线 write-guard（advisory）；Code R0 APPROVED_WITH_NOTES/0；EVD-977 |
| 19 | FIX-302 | `72ccc89` | ✅ canonical 措辞同步（SKILL L126 + M1.2 尾句 + e2e 投影 +3/−3）；Design R0 APPROVED_WITH_NOTES/0；EVD-978 |
| 20 | FEAT-020 | `c92bf5d` | ✅ 契约矩阵冻结与特征测试（快照四契约面 + 27 特征测试）；Code R0 APPROVED_WITH_NOTES/0；EVD-979 |
| 21 | FEAT-019 | `c443757` | ✅ ArchGuard 棘轮 R1~R7（fatal 位，R1 锚 24,302）；双审 APPROVED_WITH_NOTES/0 ×2；EVD-980 |
| 22 | FEAT-018 | `1bb4268` | ✅ 性能测量协议脚本与容差校准（零引擎改动）；Code R0 APPROVED_WITH_NOTES/0；EVD-981 |
| 23 | FIX-301 | `a599843` | ✅ 归档识别修复（四根因 + explain；真实 dry-run 88+58+5+12 可归档）；Code R0 APPROVED_WITH_NOTES/0；EVD-982 |
| 24 | —（迁移执行） | —（治理记录） | ✅ EVD-983 真数据归档迁移（Coordinator R1(b) 备份 + integrity PASS；plan-tracker −17%） |
| 25 | AUDIT-152 | `9a8040d` | ✅ 环境敏感失败定性标记（31F+1E 100% 分类 + 机器可读清单）；微审 APPROVED_WITH_NOTES/0；EVD-984 |
| 26 | DOC-003 | `8f13c85` | ✅ 数据块归宿清单（202 站点/2,441 行 100% 覆盖 + facts 勘误）；EVD-985 |
| 27 | FEAT-012 | `24c6f61`+`385b83b` | ✅ G5 tpa 重复抑制 + G6 尾行两态化（棘轮首次实战收紧 24,302→24,269）；Code R0 APPROVED_WITH_NOTES/0；EVD-986/987 |
| 28 | FEAT-013 | `3a108c2`+`c96da1b` | ✅ RISK-046 根因修复（acquire_dispatch_locks 两面机制 + 模板机器化）；Code R0 APPROVED_WITH_NOTES/0；EVD-988/989 |
| 29 | FX-195 | `97168f8` | ✅ quick-scan 前移评估（Phase-1/1.5/2 + Slice 拆分 + 关闭条件 C-1~C-5）；Design R0 APPROVED_WITH_NOTES/0 |

**Breaking changes：无**（判定面扩展均走放宽/fail-safe 方向；新增守卫/门禁组件不破坏既有行为——advisory/skip 路径显式；G5 带 --force 旁路；无接口删除/重命名/默认行为破坏——以 M-2 门禁实测 + M-3 双审复核为准）。

## Candidate Gate Results（M-2 — Coordinator 回填实测）

> 本节由 M-2 打包期实测回填（本文件创建时为 candidate 文档面，**不预填 PASS**——基线数字漂移惯例：打包期以实测为准，不引用旧值作新声明）。候选 commit hash：待回填。

| # | Gate（`python skills/software-project-governance/infra/verify_workflow.py <cmd>`） | 0.79.0 预期（version-plan §4） | Result（M-2 回填） |
|---|---|---|---|
| 1 | check-version-consistency | PASS（13 文件 0.79.0；advisory WARN ×2 同型惯例：host plan-tracker 记录版本打包后 bump + 根 CLAUDE.md gitignored 已同步） | **PASS**（M-1A 实测：13 文件+bootstrap markers 全绿；WARN=host plan-tracker 版本〔M-8 回写惯例〕） |
| 2 | check-projection-sync --fail-on-issues | PASS（15 projections；漂移时 release-projection --write + 回滚测试证据 + 再次 check） | **PASS**（15 镜像，source 0.79.0，written=15——M-1A） |
| 3 | check-manifest-consistency | PASS（判定面/棘轮/契约矩阵新增文件 MUST 已登记 manifest） | **PASS**（636 canonical/702 actual 一致——M-1A） |
| 4 | check-cross-references --fail-on-issues | PASS（零悬空/零废弃/零循环） | **PASS**（69 文件/660 引用——M-1A） |
| 5 | verify（无参） | PASSED（既有基线失败按先例如实披露） | **PASSED**（M-1A 全量：files/snippets/architecture/agent_adapter/version/loop_role） |
| 6 | pytest 全量 | 零新增失败（对照存量基线逐类归属——AUDIT-151/152 口径：环境敏感 24+1/已知缺陷 2/数据耦合 6） | **FAIL exit=1 = 32F 全存量分类零新增**（AUDIT-152 机读清单在案：24 bash/WSL 环境族+1 skip/6 数据耦合〔审查文档 claim 族〕/2 已知缺陷〔F2/F3〕——真回归 **0**；**W-3 披露：CI ubuntu 权威面未跑〔push 凭据阻塞〕——发布后补跑义务登记**） |
| 7 | check-governance --summary-only | 零新增（对照 EVD-983 迁移后基线 31——以打包期实测为准） | **33 issues 零内容缺陷新增**（W-2 构成 A/B：31〔FEAT-013 后〕→33，+2=FIX-300 审查文档数据耦合族〔AUDIT-152 N1〕——全部 advisory/已分类，无新增缺陷类） |
| 8 | check-injection-contract | PASS（28 anchors 含 @version-line 动态锚解析 0.79.0） | **PASS**（28 anchors，@version-line 动态锚 0.79.0——M-1A） |
| 9 | check-dsh-skills-manifest | PASS（35/35） | **PASS**（verify 全量内含 agent_adapter 面——M-1A；check-release agent adapters 门 PASS） |
| 10 | check-release --version 0.79.0 --require-changelog --lineage-mode candidate | 核心静态门禁 PASS + 既有基线 FAIL 分类披露（三件套 MUST 含 No-overclaim needles——0.78.1 R0 F-1 先例，本批三件套已含） | **静态 14 门全 PASS + dsh_upgrade_regression PASS（新门实战，temp DSH_HOME 零真实写入）+ loop fuse/changelog PASS**；execution gates 3 FAIL 全既有分类：①governance health 33（advisory 姿态——0.78.1 先例 127/EVD-894，严格更优）②unit tests 32F 分类零回归（见 #6）③loop claim gate semantic BLOCKED=数据耦合（N1 审查文档 affirmative/N2 归档致 authority 离热——AUDIT-152 登记，identity_verdict=PASS；W-4 披露）；整体 FAILED - 6 issue(s) fail-closed〔0.78.1 先例姿态：基线 FAIL 分类披露发布〕 |
| 11 | release-ledger --version 0.79.0 --no-remote | NATIVE_CANDIDATE（candidate commit 后；UNKNOWN/BLOCKED 不得包装为 PASS） | **NATIVE_CANDIDATE PASS**（LEDGER_EXIT=0；candidate_commit=`8d9110c`；CANONICAL_BYTES 规范化一次后过；M-5 授权后 transition 事件+integrity 追加） |
| 12 | quality-tools | NOT_RUN 如实记录（Ruff/mypy 未安装——ADR-010 不虚构 PASS） | **NOT_RUN**（本机未安装——如实；不虚构 PASS） |
| 13 | check-release --version 0.79.0 --require-changelog --lineage-mode released --release-commit \<commit\> | （M-6 释放态）核心门禁 PASS + 基线 FAIL 披露 | 待 M-6 回填 |
| 14 | release-ledger --version 0.79.0 --remote github-https | （M-6）NATIVE_RELEASED PASS（--no-remote 与 --remote 双证） | 待 M-6 回填 |

**回滚验证**（stage-release 硬门槛；本仓无独立测试环境——0.76.0/0.77.0/0.78.1 先例：以可逆性分析 + 门禁复跑为验证载体）：见 `docs/release/rollback-plan-0.79.0.md`（全量/部分回滚路径 + 回滚后复跑 #1/#2/#10 与 `git diff --check`）。

**FEAT-016 新增 gate 组件披露**：#10/#13 execution gates 开启时 `dsh_upgrade_regression` 实际运行（temp DSH_HOME 零真实 home 写入）并阻断 FAIL；`--skip-execution-gates` / BR-4 released-history 显式 [SKIP] 披露——M-2 实测时按此口径记录。

## Review Evidence（M-3）

- 任务链审查终态（已机录，docs/reviews/）：全链 APPROVED 或 APPROVED_WITH_NOTES/unresolved_blockers=0——判定面变更双审（FIX-291/292、FEAT-019）+ 新增守卫双审（FEAT-011 三审）+ 契约面双审（FEAT-019/020 耦合面共同裁决）。逐任务 REVIEW ID 见 Change Inventory 表。
- M-3 候选双审（Release Reviewer + Design Reviewer，对 v0.78.1..candidate 全窗）：**REVIEW-REL-075-RELEASE-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（go_no_go=GO）**——清单完备性 PASS（三件套超集/回滚两级保真/备份 863 文件实测吻合）/CHANGELOG 无 breaking 逐项核验/版本一致性全量 diff 核/ M-2 姿态=GO（3 FAIL 均命中 0.78.1 先例模式且数字与分类质量严格更优）/MINOR 成立（L12/L37 逐字核验）；W-1 回填已执行 + W-2 构成 A/B 已附 + W-3 CI 未跑披露已入 #6 + W-4 分类披露已入 #10。**REVIEW-REL-075-DESIGN-R0 APPROVED_WITH_NOTES/unresolved_blockers=0**——判定面聚合一致性 PASS（R5 机器实证 82/82+70/70 依赖序无冲突）/守卫三层正交（write-guard A+B / 棘轮 fatal / release gate）/fail-safe 方向核验 breaking=无 设计侧成立/归档边界不阻断（守恒 176 PASS，N2/N3 候选登记）/No-overclaim 抽查 PASS；W-1 数字修正已执行（82 键）+ W-2 备份已转存 .governance/backups/（863 文件持久）。
- 归档迁移执行证据：EVD-983（R1(b) 完整备份 %TEMP%\governance-backup-20260910-prefix301 + check-archive-integrity PASS + R4 逐条上报）。

## 出槽登记（无隐藏带入）

version-plan-0.79.0.md §5.1 裁决表 21 行全承载（DEC-172 ② 承接项 + DEC-177/181/184 核增项入槽；搁置维持项如下）——F-03（e2e 投影决策，触发式）、F-04（npm pack 守卫，0.79.x 守卫批次候选）、F-04-env（锁模型扩展）、F-05+BC-1（升 FAIL 条件结构性不可满足——DEC-160 锚定 0.77.x，累计仍 =1）、FIX-279 P2-3+P3×3（观察池）、N-P3 组、REQ-109/111/113/114（→ 0.80.0+，DEC-177⑦）、quick-scan 实现 Slice-1/2/3（→ 0.80.0，FX-195 拆分建议）、FIX-298（⏳ blocked_by REL-002——DEC-182 拆出）、RISK-047/048 后续候选（维持观察）、RISK-049 残余候选（live/headless 会话面〔DEC-180〕+ 非 dsh 适配器等级映射〔DEC-179〕）、FEAT-013 遗留 F-1/F-2/F-4 + FEAT-014 F-4~F-12/N-1~N-6 + FEAT-016 F-2/F-3 + FEAT-018 P2×4 + FEAT-019 W1~W4/P2×3 + FEAT-020 P2×3/P3×5 + FIX-301 P2×2 + 各任务 P3 遗留（0.80.0 重构线 §10 P1/P2 十七项锚定——DEC-184④）。

## No-overclaim Boundaries

This candidate does not create or prove `v0.79.0` and does not close RISK-036 or RISK-039. 0.79.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-049 已关闭（DEC-185——口径限定 DEC-179/180，残余面登记后续候选，不依赖本风险敞口）；RISK-044 缓解中（DEC-177②——FX-195 为评估交付非实现，不声明关闭）；RISK-046 根因修复已交付（FEAT-013）但维持打开至 2026-09-30 复评窗收口（不声明关闭）；RISK-047/048 维持观察。No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

- candidate-only：`release_authorized=false`——transition/tag/push 待用户授权（DEC-143，M-4 唯一人工门）。
- Breaking changes：无。
- DSH preset 时滞：升级路径 `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`；未 sync 安装不宣称会话级效果。
