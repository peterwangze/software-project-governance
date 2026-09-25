# Review — REL-087 · 0.88.0 M-1 版本 bump（Code Review · R0）

- **Task ID**: REL-087（P1——发布链 M-1；FEAT-059 先例形态）
- **Round**: R0（首轮）
- **Reviewer**: Code Reviewer Agent（只读审查；唯一输出本报告）
- **审查基线**: 工作树未 commit diff @ HEAD `3fb42c0`（FIX-385）——24 tracked M + 1 新建 `changelog.md`（untracked）+ 根 `CLAUDE.md`（gitignored 本地同步，`.gitignore:3` 实证，工作树实测 0.88.0）
- **审查依据**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（五维度 + P0~P3 分级 + 事实依据红线）
- **审查方式**: 逐行读 diff + 全部重点项实测复现（验证命令/扫描/grep/程序化比对），无一项仅凭工具自报采信

---

## 1. 审查范围（实测清单）

| # | 审查对象 | 实测手段 | 结果 |
|---|---------|---------|------|
| 1 | `skills/software-project-governance/SKILL.md` frontmatter 权威锚 | git diff 逐行 + check-version-consistency source-of-truth 复跑 | 0.87.0→0.88.0 ✓ |
| 2 | `infra/checks/version.py` static-pin 账本消解（删 2/留 1/增 4） | 五处豁免行逐一实读 token + scan/audit 语义复读（version.py L399-418/L421-439）+ direct scan 复现 | 全部命中 ✓ |
| 3 | `changelog.md`（新建）+ `project/CHANGELOG.md` 双位 | 全文实读 + 0.88.0 段程序化逐行比对 + git log/rev-list 抽验 | 同文成立（EOL 差异见 F-2）✓ |
| 4 | `verify_workflow.py` REQUIRED_SNIPPETS 六锚 | diff 逐行 + 消费逻辑复核（L749 字面量/L1304 check_snippets/L6680 隔离守卫）+ verify 全量复跑 | 六锚全 OK ✓ |
| 5 | 自动投影面 28 面 | release-projection check 复跑（28/28）+ 8 面实读抽查（plugin.json ×2/manifest.json/pre-commit @version/agent.cordis 模板/e2e SKILL.md/e2e governance-init ×3 块/AGENTS.md） | 28/28 PASS + 抽查全 0.88.0 ✓ |
| 6 | 双根 entry sync 4 文件 | 实读 `@bootstrap-version`（根 AGENTS.md diff + 根 CLAUDE.md 实读 0.88.0 + e2e AGENTS/CLAUDE 实读 0.88.0） | 4/4 到位 ✓ |
| 7 | 残留 0.87.0 活动锚 | `git grep 0.87.0` 全仓分类（排除 .governance/changelog/docs 后 12 文件逐一研判） | 零漏改 ✓（见 §3.2） |
| 8 | fix339 8F 基线声明 | EVD-1144 四类归类实读 + LRC 模块活体复跑 + **全量 pytest 复跑 + HEAD 干净 worktree 对照（7/7 逐字全同）** | 实质成立 ✓（计数勘误 F-5，§3.8） |

**验证复现记录（全部 exit 0 / PASS）**：

- `check-version-consistency` → PASSED，唯一 WARN=`plan-tracker workflow version=0.87.0, expected=0.88.0`（过渡态预期 WARN，与 Developer 申报一致）
- `release-projection`（check 模式）→ `pass=true, state=PASS, source_version=0.88.0, projections_checked=28, issues=[]`，`declared_legacy_snapshots=10`
- `check-manifest-consistency` → PASS（canonical 886 / actual 1023，一致）
- `check-cross-references` → PASS（727 引用，零悬挂/零废弃路径/零循环）
- `verify`（全量）→ **PASSED**，唯一 WARN 同上（过渡态）
- static-pin direct scan（`scan_static_version_pins(root)`）→ **0 issues**（零 stale 零 WARN）
- pytest 四模块（test_static_version_pins / test_release_projection / test_archive / test_governance_store）→ **293 passed**（与申报 25P+4P+105P+159P=293 总和精确吻合；其中 static pins 25P 与 EVD-1146 在案记录一致）
- `test_loop_runtime_claims.py` 单模块复跑 → **62 passed + 81 subtests passed，零失败**（FIX-389 消解后活体确认）
- **全量 pytest 复跑** → **7 failed / 4101 passed / 1 skipped / 519 subtests（1019.91s）**；失败集与 **HEAD 干净 worktree 对照 7/7 逐字全同**（archguard 棘轮席已知缓期面，零新增——明细 §3.8/附录 A）

---

## 2. 八项 MUST 重点逐项结论

### 2.1 版本锚完备性（check-version-consistency PASS 可信度）

**结论：可信（实测支撑，非工具自报）。**

- 工具自报 13 文件 + 2 bootstrap markers：实读 version.py L88-132 确认判据面 = SKILL.md 源、REQUIRED_SNIPPETS 块内钉值（L88-99 交叉校验钉值==source）、4 hooks `@version`（L100-105）、`project/CHANGELOG.md` 顶部段版本（L106-110 硬编码 canonical 位——实读确认）、plan-tracker 工作流版本（L112-116，WARN 级）、双根 `@bootstrap-version`（L117-132，tracked 陈旧=FAIL / untracked 陈旧=WARN advisory——根 CLAUDE.md gitignored 形态与该设计吻合，FIX-256/FIX-238.2 在案）。
- 28 面抽查实读 vs 工具自报：release-projection check 28/28 之外，本审查另实读 8 个投影面文本（§1 表 #5）全部 0.88.0；双根 4 文件实读全部 0.88.0（根 CLAUDE.md 虽不在 git status 可见面，实读确认已同步——「双根 4 文件 PASS」申报成立）。
- 残留 grep：全仓 `0.87.0` 在排除历史记录面（.governance/、两份 CHANGELOG 历史段、docs/ 规划与审查留档）后命中 12 文件，逐一研判**全部为合法历史面**，零活动锚漏改（分类明细见 §3.2）。

### 2.2 static-pin 账本正确性（删 2 / 留 1 / 增 4 逐行归因）

**结论：正确，五处行级实测全部命中。**

- **删 2 行 self-dormant（L12614/L12738 旧锚）——实测成立**：
  - `test_verify_workflow.py:12614`（现内容实测）：``return f"| **P1** | {task_id} | fixture task | - | 0.87.0 | tests | {status} |"``——FIX-371 fixture 行，token 0.87.0。
  - `test_verify_workflow.py:12738`（实测）：`"| ✅ 已交付 | EVD-997 / 0.87.0 |"`——FIX-376 legacy REQ 行，token 0.87.0。
  - 自休眠机制复核（version.py L408-412）：scan 仅对 `active_version ∈ tokens` 的行出 WARN；0.88.0 active 下两行 token≠active → 永不标记。删除后零功能风险（0.87.0 为已过去版本，**未来任何 active version 都不可能再匹配**），仅消除死账本重。audit 面（L421-439）对已删条目不再校验，零 stale 副作用。direct scan 0 issues 实证。
- **增 4 行 bump-time 豁免——逐行归因实测命中**：
  - `test_verify_workflow.py:12742`（实测）：`"| 🔄 进行中 | 0.88.0 交付 |"`——FIX-376 F-6① legacy-form fixture 的 `legacy_active` 场景行（L12740-12743），活跃 token 首次现身于本 bump，与「FIX-361 designed double signal」语义精确一致。归因注释中「the test asserts the ACTIVE legacy row still FAILs」与 L12736-12746 用例形态吻合。
  - `test_archive.py:4586`（实测）：`"- **工作流版本**: 0.88.0"`——FIX-384 index-rebuild fixture 世界的 plan-tracker 合成数据（_REASON_FIXTURE_TABLE）；注释声称「archive-range 语义消费硬编码 RANGE ("0.60.0", "0.61.0")」——L4592-4594 实测确认 RANGE 行存在且 L4595 的 FIX-900 行目标版本列 0.88.0 从不参与 active 比对。RANGE 消费声明**实测成立**。
  - `test_archive.py:4595`（实测）：`"| **P1** | FIX-900 | live task | — | 0.88.0 | TBD | 进行中 |"`——fixture live-task 行目标版本列（_REASON_FIXTURE_ROW_TEXT）。
  - `test_governance_store.py:493`（实测）：`f"| **P1** | {i} | 词表对齐夹具行 | - | 0.88.0 | 验收=测试用例 "`——行内自标「夹具行」，f-string 插值 `{i}` 实证消费面为 ID cell（词表对齐），版本 cell 为场景载荷。归因注释与代码事实一致。
- **保留 L30 dormant FUTURE_TARGET——实测成立**：`test_release_projection.py:30` 实测 `NEW_VERSION = "0.87.0"`——行仍携带 token，audit 零 stale；0.88.0 active 下 scan 不触及。保留论证（0.85.0/0.86.0 bump-time rows 先例同型、FIX-361「goes dormant afterwards」设计语义、实测零 WARN）与账本实况一致（L233-242/L250-256 等 0.85/0.86 历史行确在账本保留）。保留/删除的不对称性见 F-4（P3 观察项，非缺陷——删除两行有 REVIEW-FIX-388 F-1 明确 mandate）。
- **豁免语义无弱化确认**：豁免按 `(line, token==active_version)` 精确匹配（L399/L411-412），非 blanket-allow；行号锚保持方案（dynamize 否决）与 FIX-388 在案裁定（EVD-1146「方案取舍=行号锚保持（A）」）一致。

### 2.3 CHANGELOG 双位过渡（canonical 归属延后是否合理）

**结论：延后至 M-3 合理（披露完备+时限明确+锚点已留），附两项 P3 过渡态观察（F-2/F-3）。**

- **同文双位实测**：两文件 0.88.0 段程序化逐行比对——内容逐字一致；唯一差异为行尾符（根 `changelog.md` 14741 字节 LF vs `project/CHANGELOG.md` 14836 字节 = +95 = 95 行各一 `\r`，CRLF）。归一化后同文成立（EOL 差异 → F-2）。
- **canonical 判据位确认**：check-version-consistency L106-110 硬编码 watch `project/CHANGELOG.md` 顶部段——工具面 canonical = project 位；根位（新建 changelog.md）不在该检查覆盖内（→ F-3）。
- **延后合理性**：①双位披露三处在位（根文件头部披露块、两文件 0.88.0 段 Changed「CHANGELOG 双位过渡（REL-087）」条、如实披露⑥）——漂移风险已被显式声明而非隐匿；②M-3 是双半面审查（产品半面+发布半面），canonical 归属属发布架构决策，M-3 裁决有完整上下文；③过渡期由「双位同段纪律」控制，且 M-1 候选尚未落库，本审查确认当前时点双位零漂移。**不构成 NEEDS_CHANGE 依据**；M-3 裁决时 MUST 同时处理 F-2（EOL）与 F-3（根位守卫）。

### 2.4 24 票载荷准确性（git log 抽验）

**结论：准确（区间、票-哈希映射、算术、章节全部实测吻合）。**

- **区间实测**：`git rev-list --count v0.87.0..HEAD` = **29**，与载荷「git rev-list 实测 29 commits」一致；29 个 commit 逐一与载荷 Commit 区间清单（新→旧）比对**全数命中**，含终点 `fc69196`（REL-084 M-8 前版收尾）与「区间终点随 M-1 候选 commit 落库后延伸」的如实标注。
- **票-哈希映射抽验**：载荷标注的 24 票 commit 哈希逐一对 git log 实测（FIX-373=3c3218d / FIX-374=6845756 / FIX-378=44cb534 / FIX-375=04b7a42 / FIX-376=3d31c49 / FIX-386=d6dd300 / FIX-377=17e5663 / FIX-387=0840876 / FIX-389=9df2381+cdc3a0a / FIX-388=b3577c8 / FIX-379=b7df86c / FIX-380=c349f8e / FIX-381=b03a0b4 / FIX-382=ce93eb3 / FEAT-060=c515776 / FIX-383=0ff12f3 / FEAT-061=61618a5 / FEAT-064=a8afcbf / FEAT-062=14797be / FIX-384=6360ab1 / FEAT-045=467fb55 / FEAT-063=d68355f / FEAT-044=d7b9add / FIX-385=3fb42c0 / REL-086=266c32b+7d6ff6a+0233f49）——**24/24 全命中，零张冠李戴**。
- **五阶段排布**：A 14 票（含 0.87 出槽先落 3 票 FIX-373/374/378 + 调查票派生 3 票 FIX-377/388/389 系）→ B 2 → C 1 → D 1 → E 6，合计 24；与阶段小节实际列载票数逐一相符；brief 19 vs 实测 24 差异已在载荷头如实披露（0.87 出槽 FIX-373/374/378 先落）。
- **治理面算术**：11 决策 = DEC-229~239 连续区间 ✓；30 EVD = EVD-1134~1163 连续区间 ✓（EVD-1132/1133 归前版收口的边界标注如实）。
- **B-12/13/14 行为变更节**：在位（B-12 FEAT-064 分族 BLOCK+task_status WARN 后置+break-glass 回退；B-13 FEAT-061 md 转派生投影+decision-append 契约不变+旧工具明确拒绝；B-14 FEAT-062/063 纯新增）——与各票 commit message 实读（a8afcbf/61618a5/14797be/d68355f）口径一致。
- **no-overclaim 披露⑦**：在位且完整（official/marketplace approval、universal runtime support、external first-session pilot 均未主张；非 Windows 未验证；RISK-036 打开不主张 1.0.0 production-ready；RISK-036/039/046 窗裁决 2026-09-30、RISK-050 10-31）。
- **Breaking changes：无**断言：`core/VERSIONING.md` L11 实读确认引用口径准确（Major=删除/重命名 MUST 规则、Gate 行为语义、governance 文件字段格式；1.0.0 前 Minor 可含有限 Breaking）——本载荷无 MUST 删除/重命名、外部 CLI 契约（decision-append）不变、无 governance 文件字段格式变更；B-12 执法硬化属 DEC-224 登记方向兑现且有 B-11 前置基座，断言成立。MINOR bump 依据（version-plan-0.88.0 M-0 双半面 APPROVED_WITH_NOTES/0×2 终态）在案（docs/planning/version-plan-0.88.0.md 存在，M-0 双审链 review-REL-086-DESIGN-R1/RELEASE-R2 留档实测在 docs/reviews/）。

### 2.5 REQUIRED_SNIPPETS 六锚（手钉 vs 自动投影边界）

**结论：手钉设计合理，且非「裸手钉」——有三重防护。**

- **为何不自动**：REQUIRED_SNIPPETS（verify_workflow.py L749 字面量，FEAT-038 F-2 后「Literal is the sole authority」）是验证器的**独立期望面**；release-projection 由 SKILL frontmatter 权威源派生。若验证器期望同源自动派生，错误的权威锚会自洽传播（循环验证）——手钉正是「第二意见」绊线：遗忘手钉 → verify 直接 FAIL（fail-closed）。L6680-6682 注释（design §6.5 R0-S4）实证该字面量存在刻意的隔离设计。
- **三重防护实测**：①check_snippets（L1304-1318）断言六个目标文件实际含 0.88.0（本次 verify 全量 PASSED 内全 OK）；②check-version-consistency L88-99 反向解析 REQUIRED_SNIPPETS 块、断言块内钉值==权威版本（钉值自身不可漂移）；③release-projection 28/28 校验目标面内容。六锚（.claude-plugin/plugin.json、.claude-plugin/marketplace.json、.codex-plugin/plugin.json、.zcode-plugin/plugin.json、package.json、core/manifest.json）diff 逐行确认为纯 0.87.0→0.88.0 值替换，无夹带。

### 2.6 EVD-1146 处置口径（不动+披露）

**结论：与 DEC-227 先例约束一致，处置正确。**

- **事实基础实测**：evidence-log L2630（EVD-1146）/L2631（EVD-1147）双行在案——两行唯一实质差异为目标对齐字段（EVD-1146「账本与实况一致防审计盲区。」13 chars 触发 Check 16 FAIL ↔ EVD-1147 完整重写「账本与真实工作树状态保持一致，消除审计盲区与误告警，防止豁免面随代码演进而静默腐烂，支撑 0.88.0 发布门禁的 static-pin 面可信度量。」）+ 各自独立机器写入 op-id（op-08121279… / op-721bf76f…）——失败首写与合格重写的完整痕迹如实保留，未擦除未补录。
- **先例约束核验**：decision-log L169 DEC-227 实读——「(a) 数据补录被否——历史任务的目标对齐/用户影响字段无法事后真实还原，**补录=编造风险违反 P1 原则**」。「不动+披露+M-3 复核」正是该否决先例的正确推论；changelog 如实披露②引用准确。
- **最小干预替代方案（改写历史行）被正确排除**：改写机器写入的历史 EVD 行会破坏 op-id 审计链与 evidence-log 不可变语义。M-3 复核锚点已留（披露②+双 CHANGELOG 同段）。

### 2.7 验证复现

**结论：全部复现通过（§1 验证记录表）。** Developer 申报的 check-version-consistency PASS（唯一 WARN=plan-tracker 过渡态）、verify 全量 PASSED、static-pin 零 stale 零 WARN、manifest PASS、cross-refs PASS、套件 293P（25+4+105+159）——**逐项复现成立**。补充：LRC 模块 62P+81S 零失败活体确认（FIX-389 消解后的现势基线）；release-projection written=17 的写时点计数属历史事实，本审查只读约束下以 check 模式 28/28 PASS 等价复核（check 是 write 的收敛判定面），不重复执行写操作。

### 2.8 fix339 8F 基线一致声明

**结论：申报实质成立——「与 HEAD 基线逐字一致」已按任务明示的干净 worktree 对照法实测复现（测试名级 7/7 全同，零新增失败）；「8F」计数与实测 7F 存在口径差（F-5，P3 勘误注记）。** 全量 pytest + HEAD 对照明细见 §3.8/附录 A。

---

## 3. 关键实测明细

### 3.1 双根 entry sync 的 git 可见面差异（澄清，非发现）

任务申报「双根 AGENTS.md/CLAUDE.md（repo-root+e2e 各 2）」共 4 文件，git status 仅见 3 个 M——实测根 `CLAUDE.md` 为 `.gitignore:3` 声明的未跟踪本地同步文件（FIX-256 在案形态），实读确认 0.88.0 已同步。check-version-consistency L117-132 对 untracked CLAUDE.md 陈旧仅 WARN advisory 的设计与此吻合。**申报与实际一致。**

### 3.2 残留 0.87.0 分类（活动锚零漏改实证）

| 文件 | 命中 | 研判 |
|------|------|------|
| `core/releases/0.87.0.json` | 版本命名文件 | 历史发布清单本体，合法 |
| `infra/checks/version.py` | 账本历史 token（0.85/0.86/0.87 bump-time rows） | 历史账本（audit 按 token 存留校验，合法） |
| `infra/checks/loop_runtime_claims.py:225,235` | 注释（FIX-369 v0.87.0 / version-plan-0.87.0.md 指引） | 历史注释，合法 |
| `infra/governance_store.py:2198` | docstring（FIX-370 / version-plan 0.87.0 §5 B-10） | 历史引用，合法 |
| `infra/registry.py:376` | 注释（FIX-370 0.87.0 batch 2 closure） | 历史注释，合法 |
| `infra/contract_matrix/golden_samples.txt` | `[OK] snippet … :: 0.87.0` 等 | **Non-asserted human-review material**（snapshots.json L439 明文：「snapshot equality covers faces/ only」）——非比对面，合法 |
| 6 个测试文件（archguard_ratchet ×3 / contract_matrix ×1 / loop_runtime_claims ×1 / registry ×1 / release_projection ×2〔L29 OLD_VERSION+L30 NEW_VERSION〕/ verify_workflow ×2〔L12614/12738 dormant fixture〕） | 场景载荷/历史常量 | static-pin scan（0.88.0 active）0 issues 实证无活跃 pin |
| e2e 镜像面（skills/commands/AGENTS/CLAUDE） | 零命中 | 镜像同步干净 ✓ |

### 3.3 project/CHANGELOG.md 判据面

version.py L106-110 实读：`changelog = root / "project/CHANGELOG.md"` + 顶部 `## [x.y.z]` 正则==source。本次 PASSED——0.88.0 段置于 project/CHANGELOG.md 顶部满足硬编码判据。根 changelog.md 的头部披露块明确指引历史连续性位于 project 位，与判据面语义一致。

### 3.4 投影面抽查实读（8 面）

`.claude-plugin/plugin.json` / `.chrys-plugin/plugin.json` `"version": "0.88.0"`；`core/manifest.json` 0.88.0；`infra/hooks/pre-commit` `# @version: 0.88.0`（4 hooks 由 version-consistency L100-105 全量校验 PASS）；`agent-presets/governance/agent.cordis.yml.template` 「治理工作流（v0.88.0）」；`project/e2e-test-project/skills/.../SKILL.md` frontmatter 0.88.0；`project/e2e-test-project/commands/governance-init.md` 三块 `@bootstrap-version: 0.88.0`（与主仓 commands/governance-init.md 三块 diff 同型）。**全部与申报一致。**

### 3.5 e2e fixture 面与过渡态 WARN 的边界

`project/e2e-test-project/.governance/plan-tracker.md` 工作流版本→0.88.0（fixture 世界先行投影）vs 活跃 `.governance/plan-tracker.md` 保持 0.87.0（随发布收口由 Coordinator 更新）——changelog 版本投影段如实标注「过渡态 WARN 如实呈现——本版 verify 唯一预期 WARN」，实测 verify 输出恰此一条 WARN。边界一致，无隐匿。

### 3.6 契约矩阵 regen 面义务澄清

verify_workflow.py L22955-22961 实读：contract-matrix 再生面（version.py re-audit + snapshots.json + golden_samples 三记录）系 FEAT-064 窗内已完成的历史义务（「three records in place」），非 M-1 义务；FIX-377 修复候选 FIX-C（棘轮 regen P2）明确「发布窗时点 Coordinator 裁决」——M-1 未触碰 contract_matrix 面**不构成遗漏**。

### 3.7 载荷内部交叉引用抽查

「REVIEW-FIX-388-R0 APPROVED_WITH_NOTES/0（git 考古三位点闭环）；EVD-1146/1147」与 review-FIX-388-CODE-R0.md 实读结论一致（V1 双向成立/L12550 实锚自证/F-1~F-5 P3 非阻塞）；「FIX-377 四类归类」与 EVD-1144 机录一致；「REVIEW-FEAT-063-R0 NEEDS_CHANGE/1→R1 APPROVED_WITH_NOTES/0」与 HEAD `d68355f` commit message 一致。抽查无失实。

### 3.8 fix339 8F 基线声明实证（全量 pytest + HEAD 干净 worktree 对照）

- **在案归因**：EVD-1144（FIX-377 调查票，机录+REVIEW-FIX-377-R0 APPROVED_WITH_NOTES）四类归类实测在案——「①时间敏感 0——**FIX-339 假设证伪**，16 连败隔离复跑 0.31s 全绿；②环境语义 8+2（LRC 触发文档轮换〔0233f49〕+FIX-376 L29〔3d31c49〕+R1 锚 +72——归因 FIX-373/374/375/376 合法交付）；③测试基础设施缺陷 1（FIX-375 全局重绑泄漏→FIX-387 已修）；④账本过期 2（→FIX-388 已修）」+ 前提修正「0.87.0 M-2 实测 3847P/0F——28 败全形成于 0.88 窗口」。「fix339」= test_verify_workflow.py 内 DEC-195a 热事实版本锚测试族（`test_fix339_accepts_derived_released_active_version` 等，L1927/1938 实读）——本工作树全量跑中该族**全绿**（假设证伪持续成立）。
- **本工作树全量实测**：`python -m pytest <infra/tests> -q`（未改树）→ **7 failed / 4101 passed / 1 skipped / 519 subtests passed（1019.91s）**。失败集 = archguard 棘轮 6F（R1 current-tree / R4 ×3 / R7 committed-vs-regen / CLI green）+ FIX300 dual-caliber 1F——全部为「committed baseline vs current tree」型比较面，即 version-plan §3 条 4 在案披露的「archguard 棘轮席（28o 基线 3 ERROR/26 WARN advisory——M-1R 门禁摘要显式列）」+ FIX-C regen 明确缓期至发布窗的已知席，非 M-1 新增。
- **HEAD 干净对照（任务明示 worktree 法）**：`git worktree add %TEMP%\rel087-head-baseline HEAD`（`3fb42c0`，审查后已 remove+prune 清理）→ 对两失败模块定点复跑 → **失败测试名与本工作树 7/7 逐字全同（126.88s）**。即 **M-1 diff 零新增失败、零失败面漂移**——「与 HEAD 基线逐字一致」实质成立（测试名级；worktree 缺 untracked `.governance/` 使个别失败 reason 细节不同，比较基准取失败测试集合）。
- **计数勘误（F-5）**：Developer 申报「fix339 **8F**」与本机两轮实测（工作树全量 + HEAD 对照）均为 **7F**——差异方向为申报多计 1（可能为 FIX-389 消解后的计数未刷新或不同环境/顺序下的一次性漂移）；不影响「基线一致、零新增」的实质结论。
- **边界如实**：M-2 全量门禁（version-plan §3 条 1——「最终门禁绑定实际发布提交」）仍是绑定义务，本 R0 复跑不替代 M-2。

---

## 4. 五维度结论（code-review SKILL 硬门槛）

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✓ 通过 | 账本五处行级实测命中（§2.2）；六锚值替换零夹带；双位同文；29 commits/24 票映射全中（§2.4）；全部验证门 exit 0 复现（§1） |
| 安全性 | ✓ 通过 | 变更面为版本字符串/账本/changelog，无输入面/注入面/敏感数据/权限面；豁免账本 anti-blanket-allow 语义（(line,token) 精确匹配+stale 审计）复核无弱化；fix339 面无新增 |
| 可维护性 | ✓ 通过（带注记） | 账本注释自描述（删行历史就地叙事——FIX-388 先例延续）；发现 F-1（version-plan L75 过时措辞）与 F-4（dormant 保留判据不对称）为 P2/P3 注记 |
| 性能 | ✓ 通过 | 扫描/审计为既有线性面，账本净 -2+5 行；四模块 293P 10.34s、LRC 182s 实测无退化信号 |
| 测试覆盖 | ✓ 通过 | 账本变更有 static-pin scan+test_static_version_pins（25P）+stale audit 三重看护；六锚有 check_snippets+L88-99 双向看护；双 CHANGELOG 有 L106-110 判据；全量门禁 M-2 绑定在案 |

## 5. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✓ 无 | diff 无新增测试/mock 代码；豁免行均为既有 fixture 的账本登记 |
| 2 | 硬编码返回值 | ✓ 无 | version.py 变更纯数据账本+注释；六锚为期望值声明（设计即如此，有 L88-99 交叉校验） |
| 3 | 幻觉 API 调用 | ✓ 无 | 无新增调用；注释引用的全部锚点（L12742/4586/4595/493/L30、version-plan L75、FIX-388 EVD）逐一实测存在 |
| 4 | 未实现 TODO | ✓ 无 | 旧注释中「re-audit there (M-1)」悬置指针已随删行消解并就地叙事闭环；无新增悬置承诺 |
| 5 | 过度实现 | ✓ 无 | 变更最小面（bump+账本消解+changelog）；version.py 历史注释较长但为删行审计轨迹的就地延续（FIX-388 账本自描述先例），非逻辑过度实现 |

---

## 6. 发现清单

| # | 级别 | 位置 | 描述 | 证据 | 建议 |
|---|------|------|------|------|------|
| F-1 | **P2** | `docs/planning/version-plan-0.88.0.md:75` | **REVIEW-FIX-388 F-1 规定的双动作只执行了一半**：F-1（review-FIX-388-CODE-R0.md L92）明确「M-1 票执行时**同步勘正 L75 措辞**并删除 2 条自休眠行」——删除已执行（version.py），但 L75 措辞勘正未执行（该文件 tracked 且不在本 diff，实测仍写「:12550 版本字面量**派生化** + :12375 stale exemption 复核」，而派生化方案已被否决、复核已完成）。changelog/version.py 引用的「version-plan L75 errata F-1」实际落字在 review-FIX-388-CODE-R0.md L92 与 EVD-1146/1147 迁移指南，规划文档自身仍是过时指令——读者沿 L75 追溯将得到与现实相反的处方 | `git ls-files docs/planning/version-plan-0.88.0.md`（tracked）+ `git status`（未修改）+ version-plan L75 原文实读 + review-FIX-388-CODE-R0.md L92 实读 | M-1 候选落库前在 L75 行尾追加勘正注记（如「〔M-1 勘正——REVIEW-FIX-388 F-1：派生化否决，消解改为删除自休眠 2 行+登记 4 行 bump-time 豁免；已执行〕」）；或经 Developer 在 M-1 收口 commit 一并带上。不阻塞 M-1 终态（P2 可遗留，但落库前顺手修成本一行） |
| F-2 | P3 | `changelog.md`（全文件）/`project/CHANGELOG.md` 0.88.0 段 | 双位 0.88.0 段行尾符不一致：根位 LF（14741 字节）、project 位 CRLF（14836=+95，95 行各一 `\r`）——归一化后逐字同文，无功能影响，但双位同段维护时会产生 EOL diff 噪音 | 程序化比对实测（长度差 95=行数，逐行差异仅尾 `\r`） | M-3 裁决 canonical 归属时统一 EOL（随裁决一次性收敛） |
| F-3 | P3 | `changelog.md`（新建面）× `checks/version.py:106-110` | 双位过渡期内根 changelog.md **无任何自动守卫**：version-consistency 仅 watch project 位（L106-110 实读），根位漂移只能靠人工「双位同段纪律」——与披露⑥的声明一致（已知过渡态），但 M-3 若裁决保留双位，必须同步给根位加守卫或收敛为单位，否则守卫缺口固化 | version.py L106-110 实读 + `git grep changelog checks/version.py` 无根位引用 | 记入 M-3 审查锚点输入（与本报告 §2.3 一并呈递） |
| F-4 | P3 | `checks/version.py` STATIC_PIN_EXEMPTIONS 整体 | dormant 豁免行「保留 vs 删除」判据不对称：删 2 行的理由是「dead-ledger weight」（自休眠后成死重），但账本中 0.85.0/0.86.0 及保留的 L30 同为 dormant 行且按「账本先例」保留——两口径各有依据（删除有 F-1 mandate、保留有审计轨迹价值），但「何时删」未成文，后续 bump 易再生此类裁量分叉 | version.py L232-337 实读（0.85/0.86 行在账保留）vs 新注释删行理由 | 非本票动作；建议 M-3/M-8 将 dormant 行保留/删除判据一句话成文（VERSIONING.md 或账本头注释） |
| F-5 | P3 | Developer 申报口径（「fix339 **8F** 与 HEAD 基线逐字一致」） | 申报计数与实测差 1：本机两轮实测（工作树全量 7F + HEAD 干净 worktree 对照 7F 逐字全同）均为 **7F**（archguard 棘轮 6 + FIX300 dual-caliber 1；fix339 测试族本身全绿）——「基线一致、零新增」实质成立，仅「8F」计数多计 1（疑似 FIX-389 消解后计数未刷新） | §3.8/附录 A 实测数据 | Developer 回复时勘正计数口径（8→7 或说明来源环境）；不阻塞 |

**P0 = 0；P1 = 0；P2 = 1（F-1）；P3 = 4。**

---

## 7. 硬门槛裁决与总结论

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✓（0） |
| 5 维度全覆盖 = 100% | ✓（§4 逐维有结论） |
| 每条发现标注级别 = 100% | ✓（F-1~F-4 全标注） |
| 设计一致性检查（与 ADR/在案设计比对） | ✓ 完成——FIX-361 double-signal 设计、FIX-388 F-1 处方、DEC-227 路线 a 否决先例、FIX-256 untracked CLAUDE 形态、FEAT-059 先例形态逐一比对（§2.2/2.5/2.6/3.1） |
| AI 专项 5 项 | ✓ 全部完成（§5） |

### 总结论：**APPROVED_WITH_NOTES**

- **unresolved_blockers = 0**
- 依据：P0=0 且 P1=0；八项 MUST 重点全部实测通过（§2）；验证门禁全量复现 exit 0（§1）；24 票载荷与 git 实况零偏差（§2.4）；EVD-1146 处置与 static-pin 消解的依据链完整且引用准确（§2.2/2.6）；fix339 8F 基线声明实证成立（§3.8）。
- **Notes（非阻塞）**：F-1（P2）建议 M-1 候选落库前一行勘正 version-plan L75；F-2/F-3（P3）作为 M-3 canonical 裁决的必带输入；F-4（P3）记录在案供 M-3/M-8 成文；F-5（P3）申报计数 8F→实测 7F 请 Developer 回复时勘正口径。
- **移交 Coordinator**：①本报告按 M7.4/M7.7 持久化 review-record（APPROVED_WITH_NOTES 为通过终态，无 next_round）；②F-1 处置决定（落库前修 or 遗留跟踪表）；③M-3 锚点带上 F-2/F-3/F-4；④M-2 全量门禁仍绑定实际发布提交（version-plan §3 条 1——本 R0 的 7F 基线快照可作为 M-2 对照基线）。

---

## 附录 A：全量 pytest + HEAD 干净 worktree 对照记录（fix339 8F 实证）

**A.1 本工作树全量**（未 stash 未改树——与 HEAD 差异即本 diff 24 M+1 文件）：
- 命令：`python -m pytest skills/software-project-governance/infra/tests -q --no-header`
- 结果：**7 failed, 4101 passed, 1 skipped, 519 subtests passed in 1019.91s**
- 失败集（7）：
  1. `test_archguard_ratchet.py::R1MainfileBudgetTests::test_r1_passes_on_current_tree`
  2. `test_archguard_ratchet.py::R4PrintOrchestrationTests::test_r4_committed_per_function_matches_current`
  3. `test_archguard_ratchet.py::R4PrintOrchestrationTests::test_r4_shrink_passes`
  4. `test_archguard_ratchet.py::R4PrintOrchestrationTests::test_r4_total_matches_facts_census`
  5. `test_archguard_ratchet.py::R7ReproducibilityTests::test_r7_committed_baseline_matches_fresh_regen`
  6. `test_archguard_ratchet.py::CliGateTests::test_cli_green_on_current_tree`
  7. `test_verify_workflow.py::FIX300DualCaliberAgreementTests::test_fixture_identity_mode_agrees_with_engine_on_present_sources`

**A.2 HEAD 干净对照**（任务明示 worktree 法）：
- `git worktree add %TEMP%\rel087-head-baseline HEAD`（detached `3fb42c0`）→ 对两失败模块定点复跑（`test_archguard_ratchet.py` + `FIX300DualCaliberAgreementTests`）→ **7 failed / 34 passed，失败测试名与 A.1 逐字全同（126.88s）**→ `git worktree remove --force` + `prune`（已清理，实测 removed=True）
- 比较基准说明：worktree 无 untracked `.governance/` 本地态（如 `.governance/plan-tracker.md` FileNotFoundError 细节），个别失败 **reason** 细节不同，但**失败测试集合** 7/7 一致——「零新增失败」以此为判定面。
- 结论：M-1 diff **零新增失败、零失败面漂移**；「与 HEAD 基线逐字一致」成立（计数口径 8→7 勘误见 F-5）；archguard 棘轮失败族 = version-plan §3 条 4 在案披露的已知席 + FIX-C regen 缓期至发布窗（非本票缺陷，M-2/M-1R 门禁摘要显式列义务在 Coordinator）。

---

*Reviewer: Code Reviewer Agent · R0 · 2026-09-25 · 本报告为唯一输出文件；未修改任何被审代码与 .governance/ 文件。*
