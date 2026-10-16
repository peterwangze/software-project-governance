# Release Checklist — 0.98.0

- **版本**: 0.98.0 · **日期**: 2026-10-15（准备态——tag 未打） · **状态**: **组装进行中（M-0 GO 有条件 + C1~C5 兑现 + M-1 ✅ 3b1a847 + M-2 定谳 ✅ EVD-1708 + **M-3 双审 AWN/0×2 ✅**〔REVIEW-REL-102-R1 CODE/R2 RELEASE，ledger seq59/60〕+ 三件套+双审报告本批落地；M-4 组装 commit 本批收口）**
- **主题**: 次版本线：可信有界执行内核（Trusted Bounded Execution Kernel）——FEAT-093/094/095/096/097 + FIX-442/443/446 七票载荷 / 发布链 REL-102
- **版本定义**: 次版本线（0.97.0→0.98.0）：权威账本与身份契约 + 审查可信链（快照绑定/CONFLICT/R2 自动）+ 动作级执法（六边界×三层，默认 GOVERNANCE_ENFORCEMENT=off）+ 执行隔离保守面 + goal 桥接（多维权危险区收口）；载荷重定 DEC-354（FEAT-098→0.99.0）；FIX-444/445 顺延 0.99.0（DEC-358①，DEC-342 暂停维持）；无破坏性变更；新增 CLI 面=enforcement-check/goal-bridge（追加）。
- **M-0 组装核算**: 见 `docs/release/m-0-assembly-0.98.0.md`（GO 建议·有条件 C1~C8；FEAT-095 harness 执法能力调研前置判定=协议级+CLI 级+降级披露）。

## 发布范围（冻结清单——TRIAGE-REL-102 + DEC-354/358）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FEAT-093 (P1) | 权威账本与身份契约——task-row-update CAS+ops 台账（`42ddbca`；R0 NEE→R1 AWN/0；EVD-1363） |
| 载荷 | FEAT-094 (P1) | 审查可信链——快照绑定/报告哈希/R2 自动/CONFLICT/ABORTED（`099acbf`；R0 AWN/0；EVD-1366） |
| 载荷 | FEAT-095 (P1) | 动作级执法六边界×三层+审查债预算（`daac2b8`；R0→P1-1〔DEC-357〕→R1 AWN/0；EVD-1698~1701/1704） |
| 载荷 | FEAT-096 (P1) | 执行隔离保守面四件套（`bf6942d`；R0 NEE→R1 AWN/0；EVD-1367） |
| 载荷 | FEAT-097 (P1) | goal 桥接——状态映射/危险区/checkpoint（`daac2b8`；R0~R6，R6 delta 复审 AWN/0；EVD-1432~1471/1705） |
| 载荷 | FIX-442 (P1) | DSH preset 冒烟并发写入容忍度（`75cc7e5`；R0 AWN/0；EVD-1365） |
| 载荷 | FIX-443 (P1) | 运行时声明扫描性能修复（`291b4f9`；R0 AWN/0；DEC-358① 随版承载） |
| 载荷 | FIX-446 (P1) | legacy evidence 归档不覆写保护（`d0bac6e`；R17 AWN/0；EVD-1695/1696/1703） |
| 版本面 | REL-102 M-1 | 17 针脚 bump+release-projection written=7+双根 entry×4+CHANGELOG 0.98.0 段（`3b1a847` 22 文件；consistency PASSED@0.98.0） |
| 修复面 | REL-102 C4 | 单测时钟敏感断言修复（`c46ad2a`；REVIEW-REL-102-R0 AWN/0；EVD-1707） |

**不发布什么（scope creep 防护）**：FEAT-098（P2→0.99.0，DEC-354）；FIX-444/445（顺延 0.99.0，DEC-358①——DEC-342 暂停维持，hooks/commit-msg+test_hooks.py 工作树保全不提交）；6 处 test_verify_workflow.py 静态版本针 WARN（DEC-213③ 口径披露）；LRC 并发窗口间歇性（既有账本面，0.99 候选池）。

## 运行前提（G-5 纪律延续）

**全程 TEMP 用仓库外路径**；check-release 含全量单测（实测 ~10-24 分钟级）——前台超时属预期；pwsh 全程 PYTHONUTF8=1。

## 检查项（逐项——发布门 G9）

### A. 范围一致性（载荷七票 vs 路线图 vs 任务状态）

- **结论**: ✅ **PASS**——七票全 committed（窗口 `dd5c2a2..3b1a847` 实测：42ddbca/099acbf/75cc7e5/bf6942d/291b4f9/d0bac6e/daac2b8/c46ad2a/3b1a847+治理 504ee89/c783cff/9950076）；0.98.0 路线图行在位（组装态，含任务列热事实同步）；审查链全 AWN/0 终态（逐票见上表）。

### B. 版本声明（M-1 已执行 ✅）

- check-version-consistency **PASSED** @0.98.0（13 faces + bootstrap markers；7 WARN 静态针披露）。
- 义务面全套：SKILL frontmatter 权威源/REQUIRED_SNIPPETS 六引擎针/四 plugin.json/双 marketplace/manifest/三 hooks @version（commit-msg 版本注释随暂停链保全未提交——28q hooks_drift 披露维持）/release-projection written=7（write_then_probe PASS，sd_integrity 28/0）/双根 entry sync ×4（@bootstrap-version 0.98.0）。

### C. 验证命令（M-2 已定谳 ✅ EVD-1708）

| 命令 | 结果 |
|---|---|
| `check-release --version 0.98.0 --require-changelog --lineage-mode candidate` | **FAILED-4（release-docs 三件套=M-4 本批落地 + governance health=GO 终审面）+ 其余面全 PASS**（verify/e2e/**unit tests exit=0 全量 1135 绿**/changelog/loop claim semantic+identity PASS〔Check 31 修复实证〕/one-dot-zero/dsh 隔离冒烟/gate sequence）；三件套落盘后第三拍预期收敛至 GO 面 |
| `check-governance --summary-only` | **6 issues=4 FAIL GO 终审披露集 + WARN 基线**（4 FAIL=18d-RB2 FIX-444/445×2+28s evidence-log 1228KB+Check30 V1——全部 DEC-358① 预裁定口径内） |
| `check-injection-budget` | **PASSED — resident 4441 ≤ 6200**；skill 面 17484>16000 **report-only 披露**（entry-skill 面 FEAT-095/097 契约段增文——非 resident 硬门） |
| 全量 unit tests | **Ran 1135 OK（0F/0E）exit 0**（C4 修复后 Developer/Reviewer 双实测+EVD-1707；EVD-1697 基线 3F+1E 收敛实录） |
| `archguard-ratchet` | 七轴全 PASS 0 violations（R1 anchor 28204/R5 107 keys/R7 fresh——DEC-358③ sanctioned regen；M-1 后复验维持） |

### D. 回滚在位

✅ `docs/release/rollback-plan-0.98.0.md`（本批落盘；区间锚 `dd5c2a2..<M-6b 回填位>`；回滚序列+权威账本 sidecar 数据兼容性声明+触发条件）。

### E. 审查计划与执行

✅ **双半面 AWN/0×2 齐备（2026-10-15）**：M-3 CODE（`docs/reviews/review-REL-102-M3-CODE-R0.md`；REVIEW-REL-102-R1 机录 ledger seq59——七项版本面核验全过/一致性双 PASS/CHANGELOG 事实核对无失实/窗口无未审混入；P3×3 已当场闭环〔CHANGELOG 预算数字+窗口全枚举+措辞〕）+ M-3 RELEASE（`docs/reviews/review-REL-102-M3-RELEASE-R0.md`；REVIEW-REL-102-R2 机录 ledger seq60——C1~C8 全兑现对账/GO 终审面无越界/**DEC-330 六项承载定向实跑 8/8 绿**/回滚三件套完备性核验/feature-flags 实义裁定确认；P3-1 行同步本批执行，P3-2 入 0.99 候选池，P3-3/4 链内时序态挂 M-4/M-8，P3-5 沿披露）。载荷七票逐票 R 轮全 AWN/0 + C4 修复 REVIEW-REL-102-R0 AWN/0。

### F. Feature Flags

**本版有实义旗标面**——`docs/release/feature-flags-0.98.0.md`：GOVERNANCE_ENFORCEMENT（默认 off=零漂移 advisory 基线；on=六边界×三层执法+ENFORCEMENT-ACTION 机录）+ GOVERNANCE_LEGACY_BEHAVIOR 延续既有面。

### G. M-2 定谳声明（GO 终审——DEC-358①）

✅ 4 FAIL 面全部经用户 2026-10-15 ask 裁定「以 GO 终审披露入 0.98」（DEC-358①）：①18d-RB2 FIX-444/②18d-RB2 FIX-445（均顺延 0.99.0，DEC-342 暂停维持，last_run FAIL 为真实失败实录保全）③28s evidence-log 体量（归档 dry-run 无可归档数据——802 条全保留）④Check 30 V1（FIX-444 BLOCKED 链尾）。**无越界 FAIL、无未裁定面**。新增 WARN 披露：skill 注入面 report-only 超限 1484 + 6 静态版本针——均非阻断。

### H. M-链完成态锚（起草时点）

| M 步 | 状态 | 证据 |
|---|---|---|
| M-0 | ✅ GO 有条件 | m-0-assembly-0.98.0.md + EVD-1702 |
| C1~C5 | ✅ | 四载荷 commit + 治理校准（EVD-1702/1706）+ C4（c46ad2a/EVD-1707）+ regen（DEC-358③） |
| M-1 | ✅ | 3b1a847（22 文件；consistency/projection/budget 三 PASS） |
| M-2 | ✅ 定谳 | EVD-1708（check-release FAILED-4=时序态+GO 面；全量 1135 绿） |
| M-3 | ✅ AWN/0×2 | R1 CODE（seq59）+ R2 RELEASE（seq60）+ 两报告文件 |
| M-4 | 🔄 本批 | 三件套+双审报告+CHANGELOG 披露修订=组装 commit（本 checklist 即其一） |
| M-5~M-8 | ⏳ | candidate→transition（用户授权点）→ledger→tag v0.98.0+push（含 ahead 统一推送）→收口+故障注入六项验证落盘（DEC-330 底线） |

## 边界声明（保守口径——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；非 Windows 未验证；dsh upgrade regression=隔离环境安装冒烟（非 live marketplace upgrade）；FEAT-095=协议级+CLI 级执法+降级披露（M-0 §3 调研判定——六平台无宿主级拦截，DSH 原语完备未接线）；DEC-330 故障注入六项验证结论随 M-8 落盘（机器承载：task-row-update CAS/review-record CONFLICT+R2/goal_bridge refuse/enforcement scoped——M-3 RELEASE 半面 8/8 实测）。
