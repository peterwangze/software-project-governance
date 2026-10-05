# M-0 版本面组装报告 — 0.95.0（REL-099）

- **版本**: 0.95.0 · **组装时点**: 2026-10-05（+0800） · **状态**: **M-0 组装完成（准备态——M-1 版本面 bump 待 Governance Developer 派发执行）**
- **主题**: 次版本线：「做薄·开放·主动探索」演进第一批（Minor Line: Thin, Open & Proactive Exploration — First Batch）——Phase 0 基线与止增 + 有界 Phase 1 最小行为修复
- **版本定义**: 0.94.0→0.95.0 MINOR bump（DEC-312(5) 用户裁定正式预留；载荷五票经 DEC-312(7) M-0 冻结）；无破坏性变更、无机制激活翻转、无 `.governance` schema 变更（exploration 区块复用既有 evidence 载体四字段——FEAT-085/DEC-312(2) 设计即不建子系统）。
- **依据边界**: 本报告 Bash 禁止（Release Agent 角色契约）——机器事实全部取自 EVD 行、REVIEW 行、RECO 行与文件实读；commit 哈希等未取得项以「回填位」标注，列入需 Coordinator 复跑/回填清单（§7）。

---

## 1. 载荷一致性核对（五票 vs 版本行 vs 路线图）

### 1.1 五票状态实读（plan-tracker L80~L84）

| 票 | 标题（摘要） | 证据锚 | 审查锚 | 状态（实读） |
|---|---|---|---|---|
| AUDIT-157 | 「做薄·开放·主动探索」演进立项（现状盘点+arch 两轮共同决策+总纲 A1~A14+用户三项裁定+入账） | EVD-1312（op-96b9813351fa46d7a591938bf6c8fead） | —（治理立项票，Coordinator 直写） | 🆕 ✅ 完成 (2026-10-04 入表) |
| AUDIT-158 | Phase 0 基线与止增（R5 回溯基线/checks 四分层/W1~W7 责任清单/注入与架构基线快照） | EVD-1313（op-b56a4e71cd134825ba004e23aae30831） | arch 顾问第三轮裁定通过（DEC-313） | 🆕 ✅ 完成 (2026-10-04 入表) |
| FEAT-085 | Phase 1 最小行为修复（EXP-01~05 入 behavior-protocol.md M10 节+SKILL.md 薄入口+exploration 区块+四通道语义+adapter 映射降级） | EVD-1314（op-2e016bf46e91403e919f2c3dfaf6b2a3） | REVIEW-FEAT-085-R0 = APPROVED_WITH_NOTES / unresolved_blockers=0（Design Reviewer） | 🆕 ✅ 完成 (2026-10-04 入表) |
| FEAT-086 | Phase 1 收尾批（前瞻样本三类 5 例验收+F-2 映射+F-6 validate 细化+F-3 六平台 exploration_channels） | EVD-1315（op-a1b2716149b34be3aea2aec18abf821e） | REVIEW-FEAT-086-R0 = APPROVED_WITH_NOTES / unresolved_blockers=0（Design Reviewer） | 🆕 ✅ 完成 (2026-10-04 入表) |
| FIX-432 | M0-M9→M10 sweep + F-4 quote_sync 守卫 + F-A2 note 监控面 + F-A5 四态定夺（DEC-315 扩承载） | EVD-1316（op-f591b412d0ad410396bc8cc6316a6e3a）+ EVD-1317（op-0ce8061302ad4bb78b455b0574d38169） | REVIEW-FIX-432-R0 / R1 均 = APPROVED_WITH_NOTES / unresolved_blockers=0（Code Reviewer） | 🆕 ✅ 完成 (2026-10-04 入表) |

**结论：五票全 completed，审查链全终态（AWN/0），与调度载荷一致。**

### 1.2 路线图核对（plan-tracker L207 版本行）

- 0.95.0 行在位：**规划中（2026-10-04 DEC-312 用户裁定预留——Phase 0+有界 Phase 1 载体；M-0 规划双审冻结范围）**。
- 行内约束列四项与本报告对位：①FIX-430 exclusions 止增与实际还债 M-0 逐项核算分别报告（A8）→ §2；②FEAT-084 Slice-3 缓存子集不自动纳入（M-0 单独核算）→ §3；③阶段按退出证据推进不与版本号绑定（A7）→ §4；④FEAT-086/FIX-432 收口后 MUST 确认版本 bump 落地（VERSIONING L51 触发条件——REVIEW-FEAT-086-R0 F-A6，DEC-315⑥）→ §5。
- **差异披露（建议 Coordinator 发布收口时回填）**：L207「包含任务」列当前为 `DEC-312, REQ-146, REQ-147, AUDIT-157✅(立项), AUDIT-158, FEAT-085, RISK-066`——**未回填 FEAT-086✅/FIX-432✅**。两票经 DEC-314(1)(3)（拆票承载：验收⑤前瞻样本→FEAT-086；19 处 sweep→FIX-432）与 DEC-315①②（F-A2/F-A5 并入 FIX-432）入链，属冻结范围内拆票承载（DEC-315 约束符合段明示「不破 0.95.0 M-0 载荷冻结」），非扩载荷；但行形态与 L206（0.94.0 行全票✅ 列举）不对齐，建议随发布收口补记。

### 1.3 需求面对照

- **REQ-146（主动生态探索行为闭环，P0）**：✅ 已交付（plan-tracker L478——FEAT-085 机制+FEAT-086 收尾，验收信号 2026-10-04 闭合；锚：behavior-protocol.md L821-865、SKILL.md L364、六平台 exploration_channels、三类前瞻样本 5 例、EVD-1315）。
- **REQ-147（治理做薄，P1）**：🚧 规划中（L479——Phase 0 分类先行已随本版交付基座；Phase 2/3 按 0.96.0+ 候选节奏执行）。**本版只主张 Phase 0+有界 Phase 1 交付，不主张 REQ-147 全量交付**（no-overclaim）。

---

## 2. B16 债务逐项核算（两栏分别报告——A8 口径）

**B16 定义**（thin-open-evolution-proposal-2026-10-04.md L71）：「0.95 债务偿还范围（FIX-430 exclusions 族）与 Slice-3 是否纳入｜建议：M-0 时逐项核算，本次只锁方向」；**分别报告义务**（phase0-baseline §4.2 L123，A5 纪律锚定同源）：「FIX-430 exclusions（archive.py）为『止增』登记——0.95.0 M-0 时与『实际还债』分别报告」。

### 2.1 止增栏——FIX-430 exclusions 机制止增面

| 项 | 事实与锚 |
|---|---|
| 机制内容 | architecture-health.json `module_size.exclusions` +4 行——archive.py 精确路径豁免（fnmatch 精确命中零误伤，R0 实证 `**/basename` 为持续误伤面；对齐 FIX-350 单文件先例）。锚：EVD-1309（op-b72a2a403e6c4189acf7d7ab58b825ce）。 |
| 审查链 | REVIEW-FIX-430-CODE-R0 AWN/0（P1 F-1 reason 引用锚失准）→ 方案 a 一行修正 → REVIEW-FIX-430-R1 AWN/0（F-1 完全修复+scope 护栏增强）——双轮闭合。锚：EVD-1309。 |
| 止增语义（本栏核心） | exclusion **不删债**：archive.py module_size 债务（历史峰值 6,016 行，FIX-417 已拆至 4,241 行——EVD-1282 残留记录）本体仍在，仅使已登记债务的重复 WARN 不再累加（架构健康输出噪音止增）；**0.95 拆分落地后移除**（看护冻结语义，EVD-1309 原文）。 |
| 纪律约束 | A5：做薄全程不改 R1 锚点（24,252）、**不扩 exclusions 放宽债务**（phase0-baseline §4.2 L123）。本版无新增 exclusions 行——纪律维持。 |
| @0.95.0 状态 | exclusions 4 行在位、**债务本体未偿**：archive.py 后续拆分（C2 票 4——analysis-FIX-427 §三 #7 登记为 0.95 候选）**未纳入 DEC-312(7) 冻结载荷**，继续冻结、移交 0.96.0+ 候选池。**如实披露：本版不主张 archive.py 体积债务已清偿。** |

### 2.2 还债栏——本版本实际偿还项（逐项证据锚）

| # | 偿还项 | 内容 | 证据锚 |
|---|---|---|---|
| 1 | Check 28b 投影漂移闭环 | 0.95 窗口组装期 Projection Sync Guard（verify_workflow.py L15814——source/fixtures/native entries）滞后：EVD-1315 时点「28b 待 commit 2」→ 载荷 commit 落地后 EVD-1316「check-governance 基线 1 issue 零新增」——28b 漂移清零、基线回落预存面。 | EVD-1315 → EVD-1316；检查名实读 L15814/L16840 |
| 2 | F-A2 manifest note 同步债务闭合 | 六平台 adapter-manifest note 规则转述漂移（REVIEW-FEAT-086-R0 F-A2 发现）→ DEC-315① 并入 FIX-432 → note 增规范标记并纳入监控面；负向验证「note 丢标记」维度触发实证。 | REVIEW-FEAT-086-R0 F-A2；DEC-315①；EVD-1316 |
| 3 | quote_sync 引文同步守卫 | check-cross-references 新增引文同步维度——规范源丢标记/转述 note 丢标记/引文行漂移三维负向验证均触发；引文与规范源漂移从「无守卫债务」转「机器拦截」（15 files 承载面之一）。 | EVD-1316（负向验证三维）；FIX-432 票行 L84 |
| 4 | M0-M9→M10 滞后描述 19 处 sweep | R0 实测 19 处（behavior-protocol.md L1/SKILL.md L409·L441/governance-init.md L321/verify_workflow.py L488·L969 存在性锚/VERSIONING.md L51/e2e 副本 8+ 处）逐处更新或显式豁免（豁免披露：冻结 fixture 4+历史记录 6）——称谓与新增 M10 节一致。 | FIX-432 票行 L84；EVD-1316（15 files：sweep 11 处产品面+守卫+ENTRY_TEMPLATE_CANONICAL_BYTES 随票重定价+e2e 守卫面 3 文件） |
| 5 | F-5/F-A5 规则姿态定夺落文 | MANDATORY 后缀统一问题定夺（规范性强弱由 RFC 2119 关键字唯一表达——后缀为历史视觉锚无规范效力，M0 节补语义注记）+ M10.2 结果四态不增「未探测」枚举（判定轴消歧，schema 注释落文；S3~S5 用法合法化）。 | DEC-316；EVD-1316 |

**两栏总结论**：止增面（FIX-430 exclusions 族）维持冻结在位、债务本体未偿（如实披露）；本版实际还债 5 项全部落在「检查器/文档与规范源同步」债务族（28b/F-A2/quote_sync/称谓 sweep/规则姿态），与「做薄以减少系统责任及重复实现为主」的 Phase 1 有界范围一致——物理拆分债（archive.py C2）与机制退役（L3/L4 段）未动，属 Phase 2/3 及 0.96.0+ 节奏（DEC-312(4)）。

---

## 3. FEAT-084 Slice-3 单独核算（缓存子集）

- **定义与出处**：Slice-3 = quick-scan/post-commit hook 性能优化的缓存子集——DEC-303(4) 范围裁定原文：「post-commit hook Step 4 维持全量（R2 缓解在位：dogfood 产品自检不延迟，发布门 full+每 commit 覆盖）；**Slice-3 缓存子集留池 0.95+**（FEAT-012 G5 先例）；窗口 0.94.0」。plan-tracker L98（FEAT-084 票行）注记同口径：「Slice-3 缓存子集显式推迟至 0.95+，裁定承载见 DEC-303(4)」。
- **M-0 输入裁定**（版本行 L207 约束列）：「FEAT-084 Slice-3 缓存子集不自动纳入（M-0 单独核算）」。
- **核算结论：不计入 0.95.0 载荷。** 依据：①DEC-312(7) M-0 载荷冻结为五票——Slice-3 不在其中，且无 TRIAGE 机录、无热表票行（未立项）；②「留池 0.95+」为可用性窗口表述而非立项承诺——0.95.0 载荷已经用户裁定冻结（DEC-312(5)），不因「0.95+」字面自动纳入；③无活性机器信号：R2 缓解在位（post-commit 全量=每 commit 覆盖，0.94.0 发布门达成——EVD-1311 M-2 末轮 exit 0；REQ-145.7 二次修订达标——DEC-303(3)，dogfood 14.1/13.4s、宿主 3.2s），Slice-3 为纯性能优化非缺陷，无必须纳入的阻塞信号。
- **处置**：入 **0.96.0 候选池**（与 DEC-315③⑤ 新票 FEAT-087/FEAT-088 同池管理）；立项须独立 change-triage（demand_source=machine-signal/user-named 如实标注），不占用已冻结版本号。

---

## 4. 硬约束延续声明

1. **DEC-312(7) M-0 载荷冻结**：本版本未扩载荷——载荷恒为五票（§1.1）；FEAT-087（前瞻样本第二批）、FEAT-088（通道探活守卫）经 DEC-315③⑤ 入 0.96.0 候选池；FEAT-084 Slice-3 同池（§3）。0.96/0.97/0.98 仅候选不正式预留（DEC-312(4)）。
2. **A7 阶段推进纪律**：五阶段按退出证据推进不与版本号绑定——本版承载 Phase 0（退出门槛五项全 ✅，phase0-baseline §5 终判）+ 有界 Phase 1（机制落地+前瞻验收闭合）；Phase 2/3 不随本版号推进主张。
3. **F-A6 bump MUST**：FEAT-086/FIX-432 已收口（审查链 AWN/0 终态）→ 本版本 bump 为 MUST 事项（§5）——本报告即该约束的 M-0 兑现动作，执行面（13 处版本声明+投影再生）待 M-1 Developer 派发。
4. **A5 棘轮纪律**：本版零新增 exclusions、零 R1 锚点变更（§2.1）；ArchGuard 只紧不松维持。
5. **止增纪律**：新增 check 准入登记条款已随 Phase 0 基线生效（EVD-1313）；本版新增检查维度（quote_sync）为例行守卫扩展、经既有票承载与审查链闭环，未经新增准入通道扩治理责任面。

---

## 5. 版本号决策记录（semver + bump 理由）

| 项 | 决策 | 依据 |
|---|---|---|
| bump 级别 | **MINOR：0.94.0 → 0.95.0** | ①新增 M10 主动生态探索协议=新增 MUST 行为规则+新机制面（VERSIONING.md L12 Minor 触发「新增 MUST 规则、新增 B/C 级自动化能力」；L37「SKILL.md MUST 规则新增 → MINOR〔1.0.0 之前可灵活处理〕」）；②非纯 bug fix（含新功能面），PATCH 不足以承载 |
| bump 义务（MUST） | 触发条件已满足 | `core/VERSIONING.md` L49 起「以下变更 MUST 触发版本号升级」条目 **2**（references/ 文件变更——修改强制检查项：behavior-protocol.md 新增 M10 节〔EVD-1314〕+六平台 manifest note 规范标记〔EVD-1316〕）与条目 **3**（verify_workflow.py 检查扩展：check-cross-references 新增 quote_sync 维度〔EVD-1316〕）——REVIEW-FEAT-086-R0 F-A6 / DEC-315⑥ / 版本行 L207 约束④ 三处同指 |
| 版本号合法性 | 无占用冲突 | 0.95.0 由用户 2026-10-04 三项裁定**正式预留**（DEC-312(5)——「预留 0.95.0 承载 Phase 0+有界 Phase 1」）；无 0.95.x tag/预留冲突（0.94.0 已发布顺延 +1，不跳号；1.0.0 预留位未触碰——VERSIONING 版本规划纪律 L121~L124） |
| semver 合规性 | 合规 | SemVer 2.0.0 于 0.x 段：MINOR=向后兼容的新功能累积里程碑（VERSIONING L11-L12）；本版无 Breaking（见下） |
| Breaking 评估 | **无** | ①CLI 接口与 JSON schema 零变更（quote_sync 为既有子命令检查维度扩展；消费点 `.get` 兼容旧结果形——EVD-1316/1317 原文）；②无 MUST 规则删除/重命名（M10 纯新增；M0-M9→M10 为称谓统一非判定语义变更——DEC-316(1) 裁定 MANDATORY 后缀无规范效力）；③manifest `exploration_channels` 与 note 规范标记为 additive 新键（check-manifest-consistency 1021 一致 PASS——EVD-1316）；④无 Gate 行为语义改变、无 governance 文件字段格式变更（exploration 区块复用既有 evidence 载体）；⑤**1047 unittest 零回归实证**（EVD-1316 时点）——FIX-432 R1 新增 5 用例后预期 **1052**，发布门 M-2 复跑闭合（review-FIX-432-CODE-R1 BM-R1-3 明示残余移交 Coordinator） |
| 升级路径 | /plugin update | 入口 bootstrap 版本戳 0.95.0 后经 FEAT-035 升级确认门自升级（用户未响应前零写操作）；无迁移指南需求（EVD-1316/1317「迁移指南=不需要」） |

---

## 6. 产物清单（M-0/M-4 批）

| 产物 | 路径 | 状态 |
|---|---|---|
| M-0 组装报告（本件，含版本号决策记录） | `docs/release/m-0-assembly-0.95.0.md` | ✅ 本批 |
| CHANGELOG 0.95.0 段（准备态） | `project/CHANGELOG.md`（canonical——根 `changelog.md` 为 0.88.0 双位过渡期投影，0.89+ 版本段仅落 canonical 面） | ✅ 本批（追加） |
| 发布检查清单 | `docs/release/release-checklist-0.95.0.md` | ✅ 本批 |
| 回滚方案 | `docs/release/rollback-plan-0.95.0.md` | ✅ 本批 |
| feature-flags 件 | —（**不创建**） | N/A：本版无 feature flag 面——M10 为行为协议层非运行时旗标机制；无机制激活翻转；行为变更回退=git revert（无 flag 清理债务）——详见 checklist §F |

---

## 7. 需 Coordinator 复跑/回填清单（Bash 禁止——机器事实缺口）

**复跑（发布门 M-2 面）**：

1. `python -m unittest test_verify_workflow` —— 预期 **1052 tests OK**（EVD-1315/1316 时点 1047；FIX-432 R1 +5〔QuoteSyncGuardTests〕无 EVD 机录——review-FIX-432-CODE-R1 BM-R1-3 残余，一条命令闭合）。
2. `check-governance --summary-only`（深检/发布门固定 full 面）—— 预期基线 **1 issue（28n 预存）零新增**（EVD-1316 基线口径）。
3. `check-injection-budget` —— 预期 resident 4244/6000、M1+M2 342/370 **零变化**（EVD-1315/EVD-1316 同值复验）。
4. `check-cross-references`（含 quote_sync）+ `check-manifest-consistency` —— 预期 PASS（EVD-1316 已证，发布门复跑）。
5. `check-version-consistency` —— bump 后 13 处一致（当前实读全 0.94.0——待 M-1）。
6. `check-release --version 0.95.0 --require-changelog --lineage-mode candidate`（M-2；默认含 verify/check-governance --fail-on-issues/e2e-check/unittest）。
7. `release-ledger --version 0.95.0 --no-remote`（M-5/M-6 candidate 态；tag/push 后 `--remote origin` + released 模式 check-release）。
8. `quality-tools` —— 结构化记录（未安装记 NOT_RUN，不虚构 PASS——stage-release SKILL 退出条件）。
9. `archive.py migrate --auto --dry-run`（M-8 持续归档触发检查；如需归档→执行+`check-archive-integrity`）。
10. git log 区间锚 —— 载荷/组装 commit 哈希清单（已知锚：FIX-432 两 commit `9a28e4d`/`c68cbbd`——DEC-316；其余回填 rollback-plan 回填位与本报告 §1.1）。

**回填（发布收口 M-8 面）**：

- 版本窗口终值（`6da8d04（v0.94.0 tag peel）..M-1 tip` 终值）→ CHANGELOG 0.95.0 段与 rollback-plan 回填位。
- L207「包含任务」列补 FEAT-086✅/FIX-432✅（§1.2 差异披露）。
- plan-tracker L11「工作流版本」行更新（当前仍述「REL-098 发布链进行中」——与 L206 已发布终态不一致，建议随 0.95.0 收口一并刷新为 0.95.0 链述）。
- **0.94.0 收口残留核实**：`project/CHANGELOG.md` 0.94.0 段头仍为「未发布（准备态）」而 L206 已有权威发布事实（tag v0.94.0→6da8d04、taggerdate 2026-10-04 annotated 4d4da76）——M-8b taggerdate 回填疑似未落字，建议核实补记（REL-098 M-8 残留，非本版载荷）。

---

## 8. 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success；非 Windows 平台未验证，验收全部在仓库内完成（RISK-036 先例口径延续）。M-0 未执行 L4 删除或 L3 迁移（Phase 0 裁定与退役实施分开验收——DEC-313/phase0-baseline §5）；archive.py 拆分债未偿如实披露（§2.1）；REQ-147 未全量交付（§1.3）。
