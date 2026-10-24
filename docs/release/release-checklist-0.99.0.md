# Release Checklist — 0.99.0

- **版本**: 0.99.0 · **日期**: 2026-10-24（准备态——tag 未打） · **状态**: **组装进行中（M-1 ✅ bump 全链 / M-2 ✅ 注入预算 PASS / M-4 三件套本批落地 / candidate 首检 FAILED-8 处置中 / M-3 双审待派）**
- **主题**: 次版本线：可信隔离验证与平台收敛（Trusted Isolated Verification & Platform Convergence）——FEAT-098/100/101/102/103 五票 + FIX-449~456 八票 / 发布链 REL-103
- **版本定义**: 次版本线（0.98.0→0.99.0）：DSH 0.2.1-rc.2 升级适配主线（FEAT-102 原生派生 + FEAT-103 隔离补丁验证〔11 轮审查全 AWN/0，承载=b 仅验证结论 DEC-368①〕+ FIX-454/456）+ 平台收敛（pi 进入/chrys 退出）+ CI 防护网自包含（FIX-449~453）+ FIX-448 D1 安全子集（热表 120 行迁移落地，容量门诚实 BLOCKED）；FIX-444/445 顺延 0.100（DEC-368②）；无破坏性变更；新增 CLI 面=无（evidence_migration 为 infra 侧工具非插件面命令）。
- **范围裁定**: DEC-368 四项（2026-10-23 用户 AskUserQuestion：承载=b/暂停=顺延 0.100/P2=FIX-448 先行/§11=D1）。

## 发布范围（冻结清单——TRIAGE-REL-103 + DEC-368）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-098 (P1) | cost numeric 精确等价（`dcf5009`；R3 机录闭环） |
| 载荷 | FEAT-100 (P1) | pi adapter 双桥+DEC-359 能力升级（`cc40646`/`b7be5a5`/`41de8ed`；R0/R2 通过后收口） |
| 载荷 | FEAT-101 (P1) | chrys live 面全清（`7db915b`/`a001057`） |
| 载荷 | FEAT-102 (P1) | DSH 预设原生派生五 commit 链（`e6e2ca5`/`f08e0a2`/`22b6820`/`98d99c2`/`2ed8bb4`；DESIGN R0~R6+CODE 链审查闭合；DEC-364/366 裁定） |
| 载荷 | FEAT-103 (P1) | owned registration 隔离补丁验证（`cad2f47`——设计终稿 R8+16 份审查报告入库；11 轮独立审查全 AWN/0；EVD-2130~2139；DEC-363/367 授权链） |
| 载荷 | FIX-449~453 (P1) | CI 防护网自包含五票（fixture 权威/注入预算/CRLF 根治/zstandard/CI 合同三链） |
| 载荷 | FIX-454 (P1) | DSH 依赖解析权威（`f091060`） |
| 载荷 | FIX-456 (P1) | 坏契约前置拒收（`c82cc9f`） |
| 载荷 | FIX-448 D1 (P2) | 热表安全子集迁移（EVD-2141/2142——infra 组件+真实迁移；DEC-368④） |
| 版本面 | REL-103 M-1 | bump 全链：SKILL frontmatter 权威源→17 针脚→release-projection written=17→双根 entry sync→CHANGELOG 0.99.0 段（consistency **PASSED@0.99.0**） |
| 治理 | REL-102 M-8 | 0.98.0 终账回填（`f392a0b`） |

**不发布什么（scope creep 防护）**：FIX-444/445（顺延 0.100，DEC-368②——DEC-342 暂停维持，hooks/commit-msg+test_hooks.py 工作树保全不提交）；FIX-447/455（现状披露）；FIX-457（triaged 待派）；FEAT-099（未规划）；FEAT-103 补丁实现（承载=b 留隔离副本，DEC-368①）；FIX-448 D2/D3（容量解锁路径 0.100+）。

## 运行前提（G-5 纪律延续）

**全程 TEMP 用仓库外路径**；check-release 含全量单测（实测 ~20 分钟级）——前台超时转后台属预期；pwsh 全程 PYTHONUTF8=1。

## 检查项（逐项——发布门 G9）

### A. 范围一致性（载荷 vs 路线图 vs 任务状态）

- **结论**: ✅ PASS——窗口 `7f161a6..HEAD` 21 commits 全推送（载荷五 FEAT+八 FIX+REL-102 M-8+REL-103 版本面本批）；审查链全 AWN/0 终态（FEAT-103 11 轮/FEAT-102 双链/FIX-448 D1 R0 NC→R1 AWN/0）。

### B. 版本声明（M-1 ✅）

- check-version-consistency **PASSED** @0.99.0（12 文件+bootstrap markers；WARN 静态针=test fixture 语义面 0.98.0 迁移窗参数〔bump 后失配自消〕+test_verify_workflow 0.99.0 in-flight 语义面——DEC-213③ 口径披露）。
- 义务面全套：SKILL frontmatter/REQUIRED_SNIPPETS 六引擎针（verify_workflow L1085-1100 六面镜像同步 bump）/plugin.json×4/marketplace/manifest/package.json/release-projection written=17（write_then_probe PASS）/双根 entry sync（@bootstrap-version 0.99.0）/CHANGELOG 0.99.0。

### C. 验证命令

| 命令 | 结果 |
|---|---|
| `check-release --version 0.99.0 --require-changelog --lineage-mode candidate` | **FAILED-8 处置中**：release docs=本 checklist 本批补；unit tests=1 error 定位中（后台全量）；governance health=GO 终审披露集（18d FIX-444/445〔DEC-368② 预裁定〕+REL-103 acceptance〔本命令 PASS 后回填〕+M5×2〔FIX-295 候选〕）；provenance gate=预存在面核查中；其余面 PASS（dsh 隔离冒烟/loop fuse/changelog/loop runtime claim gate semantic+identity） |
| `check-injection-budget` | ✅ **PASS**（resident 4441 ≤ 6200——0.99 新增契约段零超限；combined M1+M2 342≤370） |
| `check-version-consistency` | ✅ **PASSED** @0.99.0 |
| `check-governance --summary-only` | 12 issues=10 FAIL（18d-RB2 FIX-444/445/REL-103×3 + M5×2 + 其余在册已知）——GO 终审披露集，DEC-368 预裁定口径内 |

### D. 回滚方案

- `docs/release/rollback-plan-0.99.0.md` ✅（含 FIX-448 迁移恢复专用面 §4：完整备份 acl-recovery-20261024-m2pre + migration-staging 恢复契约）。

## GO 终审披露面（M-6 提案）

1. FIX-444/445 顺延 0.100（DEC-368②；18d-RB2/Check 30 [V1] FAIL 面随版披露——0.98 先例口径）；
2. FIX-448 容量门 <650KB 仍 BLOCKED（D1 已交付 hot 1,950,022B；D3/D2 路径 0.100+）；P3-1/P3-3/P3-5 发布后补批；
3. FEAT-103 NOT_RUN 5 条（真实 host publish 链/物理 storage/startActivation/T10 census/0.1.x）+ 补丁实现留隔离副本（承载=b）；
4. FIX-447/455/457/FEAT-099 现状披露；M5 反模式×2=FIX-295 白名单扩展候选；
5. test fixture 0.99.0 in-flight 语义注释漂移（注释陈述"SYNTHETIC never a real release"过时——fixture 语义仍成立，注释修正随 P3 补批）；
6. **FEAT-016 升级回归门活环境 flake**：`test_FEAT_016_real_regression_run_is_temp_isolated_zero_real_home_writes` 断言零真实 home 写入——全量 8.5min 窗口内 DSH 宿主（dogfood 会话）并发写 ~/.dsh 时序性触发（单独跑 1.4s/真实冒烟复跑 real-home writes: 0 PASS——非 FEAT-102 回归，launcher 隔离正确）；0.98 发布绿=低活动窗口运气；**0.100 候选票=FEAT-016 门 attribution 机制对齐 FIX-442 28u 先例**（concurrent attributed writes 容忍）。

## 发布序列（M-5~M-8）

M-3 双审（CODE+RELEASE）→ M-5a candidate 复检（8 issues 收敛至 GO 面）→ M-6 GO 终审（用户）→ M-7 tag+ledger+push → M-8 终账回填（CHANGELOG taggerdate 权威）。

## 保守边界声明

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；非 Windows 未验证；dsh upgrade regression=隔离环境安装冒烟（非 live marketplace upgrade——boundary 注记口径延续）；回滚/旗标边界见 rollback-plan-0.99.0.md §6 与 feature-flags-0.99.0.md。
