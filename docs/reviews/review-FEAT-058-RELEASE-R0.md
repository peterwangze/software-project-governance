# review-FEAT-058-RELEASE-R0 — 0.86.0 M-1 版本 bump + 候选打包 独立审查（兼 REL-082 M-1 发布半面）

- **Round**: R0（round 0，无前轮引用）
- **审查角色**: Release Reviewer（独立；绑定 skill：release-review + code-review；角色定义 agents/release-reviewer.md）
- **日期**: 2026-09-20
- **审查对象**: 工作树未提交 24 tracked 文件（git status/diff 实测 118+/31−）——手工语义面 5（SKILL.md frontmatter 权威源 / CHANGELOG 0.86.0 段 / checks/version.py 豁免账本 / verify_workflow.py REQUIRED_SNIPPETS 六锚 / commands/governance-init.md canonical 三标记）+ 再生投影面 19（与 FEAT-053 先例 24=5+19 同构）
- **语义基准**: DEC-221（预授权链）/ DEC-222（CHANGELOG 归属）/ DEC-223 / DEC-224 / EVD-1102~1118 / CHANGELOG 0.85.0 段先例 / version-plan-0.86.0 §0 / Bootstrap 变更纪律（canonical→投影）/ review-FEAT-053-CODE-R0（绕开手法先例与义务）
- **边界**: 只读审查 + 本报告；未修改任何代码/.governance；无 tag/push；无用户交互

---

## 1. 总结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **1**（F-1：CHANGELOG 批 0 段数字自相矛盾——一行勘正，tag 前必须关闭） |
| P2 建议 | **1**（F-2：引擎修复票未落票——M-8 前登记） |
| P3 讨论 | **3**（F-3/F-4/F-5） |

**REL-082 M-1 半面裁定：GO —— 0.86.0 候选可进入 M-2 门禁实测**，附两项 pre-tag 义务（F-1 于 M-3/tag 前勘正+机械复验；F-2 于 M-8 收口前落票）。裁定依据：候选树完整性机验全绿（28 投影面零漂移 + 版本面一致性 PASS + 三 profile 预算逐位等于 EVD-1104 基线 + FIX-361 scan 空 + 全量 verify PASSED 唯一预期 WARN）；P1 为发布说明文案级事实失真，不影响候选树字节正确性与 M-2 进入资格，但 **M-5 transition/tag 前必须完成勘正**（有明确遗留计划+机械复验路径——code-review 关闭表「P0=0 且 P1>0 有遗留计划 = 有条件合并」口径；本报告已机钉权威值，修复无需重启全面复审，Coordinator 做 diff 级核对即可）。

---

## 2. 八项审查重点逐项结论

### ① CHANGELOG 0.86.0 段事实核对（抽样超过要求的 6 条）

| # | CHANGELOG 声明 | 对照事实源 | 判定 |
|---|---------------|-----------|------|
| 1 | 批 0 = FEAT-049 commit `27eeea0`，revision m0-r1 | git log 27eeea0 = "FEAT-049: M0 契约冻结（0.86.0 批 0——revision m0-r1）"；EVD-1105 | ✅ |
| 2 | 批 1 三票 hash：FEAT-051=`b2152ea`、FEAT-046=`1cd224e`、FEAT-047=`bff298d` | 八 hash 逐一 `git log -1 <hash>` 全部存在且主题吻合；与 DEC-222 引用一致 | ✅ |
| 3 | 批 2 hash：FEAT-055=`a5dec3d`、FEAT-056=`7709987`、FEAT-057=`ffcb787`、FIX-365=`a7474e4` | 同上逐一验证 | ✅ |
| 4 | FEAT-047 R0 事故叙述「P0 CLI 崩溃语义混淆 + P1 观察参数静默跳过」→R1 APPROVED_WITH_NOTES/0 | EVD-1108 逐字吻合（含 R1 必需观测分层修复） | ✅ |
| 5 | FEAT-051 R0「状态 cell 空白静默剥离——Reviewer 真表事故实证」+ R1 `_cell_parts` 修复 | EVD-1110 逐字吻合（红相双证/真表 dry-run 零写入） | ✅ |
| 6 | FEAT-046 R0「P0 locks 族 conflict 腿缺 observed_revision→结构化拒绝复演」 | EVD-1111 逐字吻合（76 测试/三套回归 157/11/77） | ✅ |
| 7 | FEAT-057「960 EVD/115 任务/102 DEC 行入基线零 WARN，Reviewer 逐 digest 零差异」 | EVD-1117 逐字吻合 | ✅ |
| 8 | FIX-365「存量 5 项失败转绿 + LRC PASS + 独立扫描 1→0，APPROVED/0」 | EVD-1115 逐字吻合（四层归因链 6F→5F→0F→5F→0F） | ✅ |
| 9 | ⑥ 治理面「7 决策」=DEC-218~224 | decision-log L159~166 七行全在；一行摘要语与原文吻合（218 条件 go / 219 外扩削减面 / 222 归属 / 224 三条款） | ✅ |
| 10 | ⑥「17 EVD（EVD-1102~1118）」 | evidence-log 精确 17 行，子分组引用（八票链 1105/1108/1110/1111/1114/1115/1116/1117、发布收口 1112/1113、重测 1104）逐一命中 | ✅ |
| 11 | 「NEEDS_CHANGE→R1 转化四票」 | FEAT-047/051/046/057 四票 R0 均 NEEDS_CHANGE→R1（EVD 逐一）；不含 0.85.0 的 FEAT-054 链，口径正确 | ✅ |
| 12 | 投影段「28 个 registry 投影面」枚举 | core/version-projections.json 实数 28 entries（5 plugin/marketplace + package + manifest + 4 hook + persona + AGENTS.template + canonical 三模板 count:3 + fixture-skill/plan 2 + fixture 命令面 12）；release-projection 实测 projections_checked=28 | ✅ |
| 13 | 批 0「**87 存量契约测试零回归**」 | ❌ 见 **F-1（P1）**：与同段「99 存量零回归 + 58 新增」自相矛盾；权威值=99 | ❌ |

### ② DEC-222 归属兑现 — ✅ 兑现
CHANGELOG 批 1 段标题显式登记「DEC-222 归属裁定兑现：三票为纯 0.86.0 轨道工作，0.85.0 CHANGELOG 窗口不承载」；批 0+批 1 全部承载 ✓（DEC-222 正文义务「0.86.0 M-1 时其 CHANGELOG 段承载批 0+批 1 全部」）；三票 commit 引用与 DEC-222 一致 ✓。边缘瑕疵见 F-3（DEC-222 自身的「时间归属」论据对票 3 失真——裁定结果不受影响）。

### ③ 版本锚完备性 — ✅（含白名单抽验）
- check-version-consistency **PASSED**（13 文件 + bootstrap 标记；唯一 WARN=plan-tracker 过渡态，与申报一致）。
- 全仓 `git grep -l "0\.85\.0"` = **48 文件**（与申报「74→48」一致）；48 文件逐一类目核验：docs/planning 历史 5 + docs/release 历史四件套/checklist 6 + docs/reviews 历史审查报告 25 + CHANGELOG 0.85.0 历史段 1 + e2e fixture SKILL（byte_copy）1 + canonical SKILL.md 1（L76「自 0.85.0 起」为契约 v2 起点历史陈述，非版本钉）+ core/releases/0.85.0.json（该版本发布清单，设计使然）1 + version.py（豁免账本行）1 + golden_samples.txt（Non-asserted 先例）1 + 豁免测试文件 5。**全部落历史/账本/fixture 白名 class，无活跃面残留**。

### ④ 豁免账本 11 行（FIX-361 程序 + 新 reason 先例符合性）— ✅
- 新增 0.86.0 行 = **11**：test_baseline_metadata:383（instrument ×1）+ test_task_row_update 7 行（59/68/203/421/441/586/594，fixture）+ test_closure_chain:83（fixture）+ test_triage_write_guard:992（fixture）+ :1138（新 `_REASON_GUARD_OUTPUT_ASSERT`）——与「fixture×9 + instrument×1 + 新 reason×1」申报逐行吻合。
- 程序符合性：账本总 33 行（0.84.0×12 / 0.85.0×10 / 0.86.0×11）；**33 行逐行「该行文本含其 token」机验全部通过（0 异常）**；0.85.0 期 10 行 dormant 且零 stale ✓。bump 时点双重信号（FIX-361 设计）如期触发的叙述与账本结构吻合。
- 新 reason 常量先例符合：与既有三常量同构（(line,token,reason) 注册表 + 语义排除声明），且自带 stale 审计回钩（披露措辞变更→token 漂移自动告警→强制重审）——是对 DEC-224 措辞未来变更（0.87 BLOCK 升级）的正确防御形态。
- scan_static_version_pins(active=0.86.0) = **0 hits**；test_static_version_pins **25 passed**（实测）。

### ⑤ 绕开手法合规性（对照 FEAT-053 同款）— ✅ 合规
- 缺陷真实性：projection.py 单遍 plan 两阶段耦合（byte_copy 源=同批 transformed 目标必回滚，fail-closed 无静默腐坏）——review-FEAT-053-CODE-R0 P2-1 + EVD-1109 在案。
- 先例一致性：FEAT-053 R0 判定「M-1 以 canonical 先达目标值再 --write 手法绕开：终态机验一致，**合规**但未显式披露」；本版同款手法 **且补足披露义务**（CHANGELOG 披露③ 显式声明手法+fail-closed 属性）——较先例改进。
- 留痕义务兑现：「修复前每次 bump 重复该手法并留痕」✓（披露③即留痕）。
- 幂等性机验：release-projection check 模式 PASS / issues=[] / 28/28 —— 当前树=目标态（二次 apply 幂等的终态机器证明；bump 时点 written=16 过程值为 Developer 申报，本审查以终态机验为准）。
- 缺口见 **F-2（P2）**：修复票未落票。

### ⑥ 三 profile 复跑 — ✅ 逐位无回归（独立复验项 1）
check-injection-budget 实测：lightweight **4,216** / standard **5,694** / strict **5,966**，三 profile 全 PASSED ≤6,000——与 EVD-1104 批 2.2 基线**逐位一致**；披露⑥「版本 bump 不改变注入面 token 计数」独立成立。

### ⑦ MINOR 依据 — ✅ 成立
- version-plan-0.86.0 §0 在案：「bump 裁定：0.85.0 → 0.86.0 MINOR」+ 载荷论证（四类新写入器 CLI + contracts.py 契约 MUST 规则扩展 + write-guard 行族上线路由 = 新增受治理能力面；无 breaking）；「Release R1 审定」由 EVD-1102 承载（发布半面 R0 NEEDS_CHANGE（R-F1~F12）→ R1 APPROVED_WITH_NOTES/0，12/12 核销——§0 即 R-F1 补全产物）。
- VERSIONING.md 引用精确性：L11（Major=删除/重命名 MUST 规则、改变 Gate 行为语义、改变 governance 文件字段格式）与 L12（Minor=…新增 B/C 级自动化能力）原文核对吻合；write-guard WARN 姿态 exit 0 不阻断 → L11 无触发面论证成立；B-3 保持手工路径兼容 ✓。
- 版本占用：tag 序顺延（v0.85.0 已发布），无 0.86.0 roadmap 占用（Release R0 V5 代验引用 + 本审查未见冲突面）。

### ⑧ AI 专项（no-overclaim）— ✅ 通过
- 「三活体实证」措辞：三项均有独立机器凭证——①write-guard 首 WARN 捕获手写 EVD-1117 行（EVD-1117/EVD-1118 记载）②DEC-224 经 decision-append 机录（op-e86cb527dcf6411b8f14431e874c2c63，行尾机器戳在案）③EVD-1118 经 evidence-append 机录（op-7d4bc9d5403e4a83a1829ad8f5f74629）。「实证」有据，非宣传语；版本主题「写入器时代」承载于事实叙述，未越界为 production/成熟度主张。
- NOT_EVALUABLE：披露② 与 version-plan §3/§6 R-F10 固定措辞**逐字吻合**（「基线不可评估（无可信历史 trace）——未宣传达成」）；绝对目标（LLM 逻辑往返 ≤2）显式「待量测协议实测，本版不主张」✓。
- 披露⑧ 边界声明完整（official approval/marketplace approval/universal runtime support/external pilot 均未主张；非 Windows 未验证；RISK-036 维持打开与 plan-tracker 一致）；披露⑦「本版不发布什么」与 version-plan §2 Out-of-scope 一致。
- B-3/B-4 行为变更声明：B-3 与 DEC-224(a) 三条款（WARN 姿态/双约束/BLOCK 留 0.87）逐点吻合；B-4 与 DEC-224(c)（step_unknown 分类学 + cli 步探针即世界核验互斥双腿）吻合，且如实标注「链内部语义，不改变既有 CLI 对外退出码契约」——与 FEAT-056 P2-1→FEAT-057 P1-1 修复链一致。

---

## 3. Findings

### F-1（P1 关键）CHANGELOG 批 0 段版本事实自相矛盾——陈旧数字「87」复活
- **位置**: `project/CHANGELOG.md` L11（0.86.0 段批 0 段落）
- **事实**: 同段先写「扩展既有 contracts.py（573→1,140 行纯追加，**87 存量契约测试零回归**）」，后写「契约测试（**99 存量零回归** + 58 新增）」——同段两个「存量」计数互相矛盾。权威值 = **99**：EVD-1105 机录「99 存量零回归〔87→99 基线勘正——Reviewer HEAD 独立复算证实〕+58 新增」；review-FEAT-049-CODE-R0 L82-86/L116/L140 明确记载「87 存量」系 version-plan §2 陈旧口径（FIX-303 在规划定稿后追加 12 测试致漂移），Developer 勘正为 99 正确（HEAD 计数 99、99/99 passed），并已作为 P3-3 登记。
- **影响**: 发布说明（M-1 核心交付物、DEC-222 指定的承载正确性核心审查面）携带已被上轮审查勘误的失真数字；对以事实可追溯为价值主张的治理产品构成用户可见的准确性缺陷。不改变任何行为/打包/门禁结论（157=99+58 在任一口径下「零回归」均成立）。
- **建议**: 一行勘正——「87 存量契约测试零回归」→「99 存量契约测试零回归」（或删除首括号内重复计数，仅保留「99 存量 + 58 新增」单处表述）。
- **关闭点**: M-1R/M-3 前（**M-5 transition/tag 前必须**）；修复后由 Coordinator 做单行 diff 机械核对即可，无需重启全面复审（权威值已由本报告机钉）。

### F-2（P2 建议）引擎两阶段耦合「修复票留 0.87 候选」未落票——跨版本静默丢失风险
- **位置**: CHANGELOG 披露③ vs plan-tracker / version-plan-0.86.0 §2+§5 / CHANGELOG 披露⑤
- **事实**: 披露③ 声明「修复票留 0.87 候选」，但全仓核查：plan-tracker 无对应 task 行（grep 两阶段/byte_copy/projection.py/单遍 plan 零命中 task 行）、version-plan-0.86.0 §2/§5 候选衔接未列、披露⑤ 的 0.87 候选池九项枚举亦未含——声明与登记面脱节。review-FEAT-053-CODE-R0 P2-1 义务原文为「**MUST 立修复票**（§6 三方向任一）」。手法披露与逐 bump 留痕两项义务本版已兑现，仅「落票」缺位。
- **影响**: FEAT-053 P2-1 承诺在 0.86.0 期间从「批 2 前修复票」（EVD-1109 措辞）漂移为「0.87 候选」（披露③），且无跟踪载体——0.86.0 发布后该承诺只剩 CHANGELOG 散文引用，存在跨版本静默丢失风险（正是本项目 8 次手工事故同类「叙述性承诺」的确定性区教训）。
- **建议**: M-8 收口前登记 0.87 候选 task 行（或至少将该项补入披露⑤ 枚举，使 ③↔⑤ 自洽）。

### F-3（P3 讨论）DEC-222「时间归属」论据对批 1 票 3 失真（裁定结果不受影响）
- **事实**: DEC-222 称「时间归属：三票提交晚于 FEAT-053 的 M-1 版本面冻结 a91d6b4」。git 时间戳实测：b2152ea（051）23:52:29、1cd224e（046）23:59:13 晚于 a91d6b4（23:51:00）✓，但 **bff298d（047）= 23:25:39，早于 a91d6b4 约 25 分钟** ❌。裁定结果（三票归属 0.86.0）不受影响——轨道归属（version-plan §2 批 1）独立成立且 CHANGELOG 正确引用轨道归属；0.85.0 M-1 冻结时 FEAT-047 已在树中（EVD-1108 交叉印证：其 verify 时 FEAT-053 M-1 在途）。属于决策记录中的辅助论据失真，非裁定缺陷。
- **建议**: 留痕即可（本报告即记录）；decision-log 勘正属治理数据写操作，超出本审查边界，由 Coordinator 裁量。

### F-4（P3 讨论）version-plan-0.86.0 §2 批 0 行「87 存量」陈旧未回改
- **事实**: 与 F-1 同根——FEAT-049 审查 P3-3 已登记规划文档未回改；本版 CHANGELOG 勘正（F-1）时规划文档可顺手对齐，或维持 P3-3 在案记录。不阻塞。

### F-5（P3 讨论，流程观察）FEAT-058 在 plan-tracker 无 task 行
- **事实**: plan-tracker 全文 grep 无 FEAT-058 行（REL-082 行覆盖 M 链叙述；批 0/1/2 各票均有独立行）。M 链任务行惯例上由 Coordinator 在收口时入账；本审查不改 .governance——提示 Coordinator 收口时补登 FEAT-058 行与本报告 REVIEW 关联。

---

## 4. 独立复验表（Reviewer 本人实跑）

| # | 复验项 | 命令 | 实测结果 | 判定 |
|---|--------|------|---------|------|
| 1 | 三 profile 注入预算 | `verify_workflow.py check-injection-budget [--profile standard/strict]` | lightweight **4,216** / standard **5,694** / strict **5,966**，全 PASSED ≤6,000；与 EVD-1104 逐位一致 | ✅ |
| 2 | 投影面/版本面一致性 | `release-projection`（check）+ `check-projection-sync` + `check-entry-bootstrap-sync` + `check-version-consistency` | projection：state=PASS / issues=[] / **projections_checked=28** / source_version=0.86.0（幂等终态成立）；sync：**PASSED**（双根 CLAUDE=9552B/AGENTS=2834B 对称）；bootstrap-sync：**PASSED**；version-consistency：**PASSED** 唯一 WARN=tracker 过渡态（与申报一致） | ✅ |
| 3 | FIX-361 账本与扫描 | python 直调 `STATIC_PIN_EXEMPTIONS`/`scan_static_version_pins` + `pytest test_static_version_pins.py` | 账本 33 行（0.84×12/0.85×10/**0.86×11**）；33 行逐行 token 在场机验 **0 异常**；scan(active=0.86.0)=**0 hits**；测试 **25 passed** | ✅ |
| 4 | 全量 verify（伞检查） | `verify_workflow.py verify` | **PASSED**，唯一 WARN=「plan-tracker workflow version=0.85.0, expected=0.86.0」（申报的过渡态预期 WARN） | ✅ |

### Developer 申报中本审查未复跑项（如实标注——M-2 门禁实测复建）
- 「全量 pytest 3,820P 零失败」：**未复跑**（成本考量；非本半面门槛）。采信为 Developer 申报值；增长量与 EVD-1114（3769P+5F）→FIX-365（+5 转绿）→批 2.3（FEAT-056 30 测试 + FEAT-057 115P+34 subtests）链相容。EVD-1118 已将全量门禁复跑+混沌复演+closure 量测首跑列为 M-2 义务。
- 「bump 时点 written=16 / scan 命中 11 行现场」：过程值未重演（不需也不应重跑 --write）；以终态机验（复验项 2/3）替代证明。
- e2e-check / dsh 隔离冒烟：M-2 范围，未在本半面复跑。

---

## 5. M-1 半面裁定（REL-082）

**GO —— 0.86.0 候选进入 M-2 门禁实测。**

- 候选树完整性：24 文件结构与 FEAT-053 先例同构（手工 5+再生 19）；28 投影面零漂移；版本锚六钉与 JSON 声明面一致（verify PASSED）；entry 双根同步；预算三 profile 零回归。
- CHANGELOG 承载正确性（DEC-222 核心面）：批 0/1/2 八票 hash/EVD/审查结论/事故叙述机核通过；DEC-222 归属显式兑现；B-3/B-4 与 DEC-224 逐点吻合；八条披露逐条有据（除 F-1 一处数字失真）。
- Pre-tag 义务：F-1 勘正（一行）+ 机械复验；F-2 于 M-8 前落票。两项均不阻断 M-2。
- M-2 提示（非本半面义务）：门禁实测按 EVD-1118 清单执行（全量 pytest 复建 + 混沌三边界复演 + closure 量测首跑——后者将首次兑现披露② 所指「绝对目标待实测」的量测义务，结果不得回写为本版已达成的表述）。

## 6. 边缘问题（移交 Coordinator）

1. F-1 勘正由 Developer 执行还是 Coordinator 按披露勘误先例（EVD-1109 P3 口径「以本行为准」式）处理——建议前者（产品文件单行 edit 走 Developer），机械复验由 Coordinator 完成。
2. F-2 落票时点：M-8 收口 or 0.87 规划期——建议 M-8（与 DEC-222 F-2 义务同窗处理，避免再次依赖散文记忆）。
3. F-3 决策记录勘正是否入账（governance 数据写操作，Coordinator 裁量）。
4. FEAT-058 task 行与本 REVIEW 的 evidence 关联在收口时补登（F-5）。

---
*Reviewer: Release Reviewer Agent（software-project-governance）· 只读审查 · 本报告为唯一写入产物（docs/reviews/）*
