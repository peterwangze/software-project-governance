# Release Checklist — 0.97.0

- **版本**: 0.97.0 · **日期**: 2026-10-09（准备态——tag 未打） · **状态**: **组装进行中（M-0 GO + M-1 ✅ + M-2 全量定谳 + M-3 双审 AWN/0×2 + 三件套本批落地；M-4 组装 commit 待收口）**
- **主题**: 次版本线：治理开销优化承载版（Governance Overhead Optimization）——FEAT-089/090/091/092 四票 / 发布链 REL-101
- **版本定义**: 次版本线（0.96.0→0.97.0）：Coordinator 开销削减三契约（M7.8）+ 审查链成本收敛（delta 复审/批量审查/摘要注入）+ 子代理预算护栏 + Check 30c WARN→FAIL 执法激活（**本版最重要行为变更**——单向棘轮，bump 后即执法）；无破坏性变更、无 schema 变更、无旗标面；载荷冻结四票。
- **M-0 组装核算**: 见 `docs/release/m-0-assembly-0.97.0.md`（GO 无硬阻断/门禁全数字/strict 28tok 版本面评估/预存失败面核销双通过）。

## 发布范围（冻结清单——TRIAGE-REL-101 + M-0）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-089 (P1) | DEC-146 升级批：30c FAIL 执法激活+V6d 收紧+豁免清单载体（`c9dc84f`+`a4c73b8` rider+`af8fba0` 治理面；REVIEW-FEAT-089-R0 AWN/0；EVD-1348/1349） |
| 载荷 | FEAT-090 (P1) | Coordinator 开销削减——M7.8 三契约+SKILL 契约 7~9+模板同步（`aca1fe4`+`602dc79`；REVIEW-R0 AWN/0；EVD-1350/1351/1352） |
| 载荷 | FEAT-091 (P2) | delta 复审+批量审查+review-record --scope/--delta-base（同 `aca1fe4`；REVIEW-R0 AWN/0） |
| 载荷 | FEAT-092 (P2) | execution-packet --budget 预算护栏+检查点拆分 advisory（同 `aca1fe4`；REVIEW-R0 AWN/0） |
| 版本面 | REL-101 M-1 | 13 处 bump+义务面全套+CHANGELOG 0.97.0 段（23 文件 65+/31-；check-version-consistency PASSED） |

**不发布什么（scope creep 防护）**：观察池 P3×6（R0 findings：--delta-base 锚点 WARN/API scope 归一/裸 --budget 说明/bool 用例/M7.8 引言 legacy 映射/狗粮手工同步流序）；Check 2/8 解析盲区卫生票（RISK-052~059 行布局）；28s 三文件过阈归档（M-8 面非载荷）；strict 注入面扩容（DEC-325 式重定标候选）——均另行批次不占本版。

## 运行前提（G-5 纪律延续）

**全程 TEMP 用仓库外路径**；check-release 含全量单测（本版实测 24 分钟级）——前台超时属预期，用后台运行或延长超时。

## 检查项（逐项——发布门 G9）

### A. 范围一致性（载荷四票 vs 路线图 vs 任务状态）

- **结论**: ✅ **PASS（M-0 实读核算 + M-3a 全量复核）**——四票 plan-tracker 全 committed（窗口 `325289f..602dc79` 六 commits 实测）；0.97.0 路线图行在位（规划态→M-8 回填已发布）；审查链全 AWN/0 终态（FEAT-089 单轮+090/091/092 批量审查轮+REL-101 双半面 M-3a/M-3b）。

### B. 版本声明 13 处（M-1 已执行 ✅）

- check-version-consistency **PASSED exit=0** @0.97.0（13 faces + bootstrap markers；M-3a 独立复跑一致）。
- 义务面全套：REQUIRED_SNIPPETS 六锚/governance-init 三标记×2/AGENTS.md.template/persona/双根 entry sync ×4/e2e fixture 投影（written=17）/`.git/hooks` ×4（28q 漂移归零）——**全部实测核到**（M-3a）。

### C. 验证命令（M-2 已定谳 ✅）

| 命令 | 结果 |
|---|---|
| `check-release --version 0.97.0 --require-changelog --lineage-mode candidate` | **FAILED-3（release-docs 三件套=M-4 本批落地）+ 其余 22 面全 PASS**（含四执行门 exit=0；loop claim gate 1192/1192）——M-3b 独立复跑一致；三件套落盘后第三拍预期 exit 0 |
| `check-governance --summary-only` | **[PASS] 零 issue**（风险过期经 DEC-329 改形消解；Check 12 已修；M-3a/M-3b 双复跑一致） |
| `check-injection-budget` 三 profile | 4416/5899/6172 全 PASS（strict 冻结线 ACTIVE 28tok；M-1 等长替换零漂移——M-0 §3.2 兑现） |
| 全量 pytest | **4758 passed + 1 skipped + 563 subtests，0 failed**（24m13s exit 0——EVD-1353；上轮负载型 flaky 未复发） |
| `archguard-ratchet` | 七轴全 PASS 0 violations（anchor 27934；M-0 实测） |
| `test_review_machine_provenance` | 41 passed（DEC-327 ≤4096B 断言+30c 棘轮激活语义活体） |

### D. 回滚在位

✅ `docs/release/rollback-plan-0.97.0.md`（本批落盘；区间锚 `325289f..<M-6b 回填位>`；四序回滚序列+验证判据+触发条件+数据兼容性声明）。

### E. 审查计划与执行

✅ **双半面 AWN/0×2 齐备**：M-3a CODE（`docs/reviews/review-REL-101-M3a-CODE-R0.md`；REVIEW-REL-101-R0 机录）+ M-3b RELEASE（`docs/reviews/review-REL-101-M3b-RELEASE-R0.md`；REVIEW-REL-101-R0-RELEASE-REVIEWER-M-3B 机录）。联动失效条款已满足（全量绿入 EVD-1353）。载荷四票各自 R0 亦全 AWN/0（含批量审查首用——FEAT-091 派发协议）。

### F. Feature Flags

N/A——`docs/release/feature-flags-0.97.0.md`（声明件：载荷均为契约文本/CLI 可选参数/单向棘轮，无旗标面；GOVERNANCE_LEGACY_BEHAVIOR 延续既有面仅 M7.8.3 fallback）。

### G. M-2 无新 FAIL 面声明

✅ 本版**无新披露面**（0.96.0 有 DEC-325 GO 终审先例因当时有 15-17 面 FAIL 定谳需求；本版 M-2 快面=22 PASS+3 时序态〔本批消解〕，全量 0F——无需 GO 终审）。既有 WARN 基线（28n closure_chain 债务/30c×42 接受基线）维持不扩界。

### H. M-链完成态锚（起草时点）

| M 步 | 状态 | 证据 |
|---|---|---|
| M-0 | ✅ GO | m-0-assembly-0.97.0.md + EVD-1353（分析行） |
| C1 | ✅ | execution-packets.json 五契约填充（18 族 FAIL 消解） |
| M-1 | ✅ | EVD-1354（23 文件；consistency PASSED） |
| M-2 | ✅ | EVD-1355（22 面+全量 4758P/0F 定谳） |
| M-3 | ✅ | 双 AWN/0×2 机录+两报告文件+EVD 待 M-4 补 |
| M-4 | 🔄 本批 | 三件套+组装 commit（本 checklist 即其一） |
| M-5~M-8 | ⏳ | candidate→ledger→tag/push→收口（回填位） |

## 边界声明（保守口径——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；非 Windows 未验证；dsh upgrade regression=隔离环境安装冒烟；治理开销收益数字为单宿主基线推算目标值（升级后首会话回测为准——执行包 success_metrics）。
