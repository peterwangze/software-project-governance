无（复审链关闭）

结论：APPROVED_WITH_NOTES ｜ round=1 ｜ unresolved_blockers=0 ｜ 前轮 = `docs/reviews/review-REL-078-RELEASE-R0.md`（NEEDS_CHANGE/unresolved_blockers=1：F-01 P1 + F-02/F-03 P2 + F-04~F-07 P3）

# Review — REVIEW-REL-078-RELEASE-R1（0.82.0 发布候选 · M-3 发布半面 R1 复审）

## 0. 结论、round 声明与审查边界

- **结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**——R0 全部 1×P1 + 2×P2 已实证修复，4×P3 中 2 项修复、2 项留非阻塞残留/注记（§1/§4）。复审链按 Check 30 语义以通过终态关闭。
- **round=R1**：同一 Release Reviewer（R0 同一审查方）按 M7.4 step 4.6 复审；基线逻辑 = R0 时的树 + 未暂存增量。HEAD 实测仍为 `845c050`（`git rev-parse` = 845c0501b948…）未动；增量全集 = 未暂存 diff **7 文件、+17/−17**（`git diff --stat`），逐文件归属见 §4——无声明面之外的产品逻辑改动。
- **审查边界（事实依据红线）**：全程只读；唯一写入 = 本报告。可执行复现全部在隔离 `DSH_HOME`（`$tmpHome` = `%TEMP%\rel078-r1-65d5d94e`，用后即删，已复核删除）下进行。**本通过 = M-3 审查面复审链关闭，不是发布 go 授权**——M-2 门禁实测与 M-4 用户停点（DEC-197）义务全部维持。

---

## 1. R0 findings 逐条裁决（已修复 / 未修复 / 新引入）

### F-01（P1 blocking）— **已修复（工作树面实证 + 测试转绿）**；附 M-1 打包条件

| 验收项 | R0 判据 | R1 实测 |
|---|---|---|
| 三处标记现状 | 3×`@bootstrap-version: 0.81.0`→0.82.0 | **工作树 L197/L262/L533 = 3×`0.82.0`** ✓（`git grep` 工作树）；**staged 树仍 3×`0.81.0`**（修复增量未暂存，见 §5 条件 1） |
| 定向测试 | EntryBootstrapTemplateTests 应转绿 | **6/6 OK、exit 0**（隔离 DSH_HOME；含动态断言 `test_bootstrap_version_marker_injected_into_all_profiles`——读 SKILL frontmatter 0.82.0 后断言 3×标记行，`Ran 6 tests ... OK`） |
| 同面配套 | —（R0 未列） | `verify_workflow.py` REQUIRED_SNIPPETS 版本钉 6 处 0.81.0→0.82.0（§4.1 定性：**必要且合规**——`check_snippets()`（`:1276-1290`，全 snippet 命中判据，消费点 `:10240`）对候选态 0.82.0 声明文件在旧钉下必 FAIL） |
| 残留扫描 | 0 命中（历史报告引文除外） | 剩余 `0.81.0` 标记仅在：`docs/reviews/` 历史报告引文 ✓、`project/e2e-test-project/`（e2e 夹具，未改动面，`test_e2e_fixture_mirrors_bootstrap_script_and_markers` 只断言 marker 存在——R0 同判，非新引入） |
| 判定 | **F-01 实质修复成立** | 附条件：M-1 冻结打包 MUST 将未暂存增量全部入暂存（§5 条件 1），否则 P1 在候选提交中复活 |

### F-02（P2）— **已修复**；例外口径裁决见 §2（附 1 条 P3 引注精度注记）

- L3：`M-1 冻结前 ⟦待回填⟧ 占位 MUST 全部消除——**唯一例外 = M-2 派生回填类**（候选 commit hash 与 M-0/M-1 批 hash：manifest 须先随候选提交入库、release-ledger 才能派生——EVD-1034 / REVIEW-REL-077-RELEASE-R1 F-R1-02 先例，M-2 期回填）`✓
- L142：同口径（`例外 = M-2 派生回填类…属预期前置依赖而非冻结违规`）✓
- 自洽性：与 L48（`候选 commit hash 由 M-2 期 release-ledger 派生回填`）及 EVD-1060（M-1 完成时 ⟦15⟧/⟦16⟧ 在场——现属例外类）状态自洽 ✓

### F-03（P2）— **已修复**（主指针成立；1 条 P3 polish 注记）

- L26 改为具名双载体：`逐项处置见 docs/reviews/review-FIX-324-326-CODE-R0.md 与 Release Agent M-0 结构化返回`——前者实存（10241 bytes，已入暂存）✓；与 footer L146 移交说明一致 ✓
- 残留简写：L27 `（见 FIX-324 处置专节）`未具名载体——但链路实证可解析：F-11/F-12 = `review-FIX-316-CODE-R0.md:36-37` findings → `plan-tracker.md:93` FIX-324 第④项持久归属（`F-11（shape 报文言辞误导）+ F-12（_JS_PROBE 非标准源码重写）→ 本任务批`）。**非悬空**，P3 polish 建议与 L26 载体口径对齐（§5 条件 3）

### F-04（P3）— **部分修复**（L22 ✓；L24 残留记法矛盾）

- L22 修复 ✓：`8bd6a8a 至 845c050 含首提交——git 记法 8bd6a8a..845c050 语义为不含首的 10，本计数按含首即 git rev-list --count 8bd6a8a^..845c050 = 11`——**实测 `8bd6a8a^..845c050` = 11** ✓（计数与实测相符）
- **L24 残留**：勘误注记仍写 `（8bd6a8a..845c050 共 11 commits——…）`——与 L22 新增的记法注记（该记法语义 = 10）形成**同文矛盾**。R0 F-04 定位本含 `:22、:24` 两处，本轮仅修 :22。P3 非阻塞（计数不承载 revert 命令，M-5 现场取值纪律不变）

### F-05（P3）— **已修复**

- L27 改为：`账本文件的 digest 被 REQUIRED_EXEMPTIONS_SHA256 锚定（FIX-320 交付常量；authority 链的 REQUIRED_POLICY_SHA256 + AUTHORITY_POLICY_DIGEST 为同族机制先例）`——与 R0 建议同形 ✓；常量实证 `infra/checks/loop_runtime_claims.py:114` + 校验点 `:1355` ✓

### F-06（P3）— **已修复**；**新引入 1 处交叉引用错位（P3）**

- L35 改为：`渲染产物字节在 0.82.0 窗口内除 persona 版本行外全程不变（仅该行随 M-1 bump 变化…）`——R0 指出的自相矛盾消解 ✓
- **新引入**：括号注 `§3 校验项承载双值对照`指向 §3「数据安全」节——该节**无校验项表**；双值对照实际载体 = §2.2 第 3 步（L69：0.81.0 基线 sha256 `6caf90fe…e55d` 16796 bytes + 0.82.0 差异恰 persona 版本行 1 处）与 §4 验证表 #5（L87）。P3 非阻塞（§5 条件 3）

### F-07（P3）— **已修复**

- L36：`L37 契约面` → `VERSIONING.md 契约面条款（evidence.* 写入路径 note 治理化更正——FIX-326③）`——行号引注消除 ✓
- 残留 `L37` 引用仅在 CHANGELOG 历史版本段（0.79.0 L100 / 0.78.x L154/L305——历史不可改区，范围外）✓
- 同段 `L11 口径`/`L12 三支触发`引注实测仍准确（现行 VERSIONING.md L11 = Major/Breaking 判定行、L12 = MINOR 触发行——R0 §3 同判，零漂移）✓

### 裁决汇总

| Finding | R0 级别 | R1 裁决 |
|---|---|---|
| F-01 | P1 blocking | **已修复**（工作树 + 测试 6/6 绿；M-1 打包条件 §5-1） |
| F-02 | P2 | **已修复**（例外口径成立；P3 引注注记） |
| F-03 | P2 | **已修复**（P3 polish 注记） |
| F-04 | P3 | 部分修复（L22 ✓；L24 记法残留矛盾） |
| F-05 | P3 | **已修复** |
| F-06 | P3 | **已修复**（新引入 §3 错位 P3） |
| F-07 | P3 | **已修复** |

---

## 2. F-02 例外口径专项裁决（先例一致性）

**裁决：例外口径成立——消解自相矛盾，且不放松冻结纪律。**

1. **矛盾消解**：R0 指出的不可同时满足时点要求（L142 全量消除 vs L48 M-2 派生）已收敛——冻结义务 = 消除全部 ⟦待回填⟧/⟦待落地⟧ 占位，**唯一例外**为「M-2 派生回填类」：其值（候选打包 commit、M-0/M-1 批 hash）在候选提交存在之前**原则上不可知**（自指环），只能由 `core/releases/0.82.0.json` 先随候选提交入库后经 `release-ledger --version 0.82.0 --no-remote` 派生。
2. **纪律不放松**：例外类外延封闭（仅派生依赖 hash 值），非派生类占位（如 ⟦M-1 交付⟧ 的 manifest 行 L26）仍受冻结前消除义务约束；L3 尾部「未回填项不得视为通过」原文保留；`⟦M-2 回填⟧` 门禁实测值类（Gate 表 12 处）本就不在 ⟦待回填⟧ 冻结集内且受「M-2 以当场值为准」约束——三层回填语义（冻结前消除 / M-2 派生 / M-2 实测）边界清晰。
3. **先例引用核对**：
   - **EVD-1034 ✓ 对点先例**（evidence-log L2065 实存：0.81.0 M-2 门禁实测 14 项 + R0→R1 审查链）——0.81.0 期 `candidate_commit: found 0` 同判「预期前置依赖」（本审查方 R0 §1.1 Gate 13 沿用同一先例）。
   - **F-R1-02 ⚠️ 引注精度注记（P3）**：实文（`review-REL-077-RELEASE-R1.md:86-91`）= 「三处计数口径漂移→M-4 以当场值唯一口径整体刷新」——属「写作时点不可知/会漂移的值后置回填」的**同族纪律先例**，非派生回填机制本体。建议措辞分层为「EVD-1034（gate 13 派生前置依赖同判）+ F-R1-02（当场值唯一口径纪律）」或删后者。不影响例外口径成立。

---

## 3. 快速回归（R0 已核实面抽验——零回归）

| 抽验项 | R0 基线 | R1 实测 | 判定 |
|---|---|---|---|
| 三件套保守边界 token | 5 token 逐字在场 | 三文件均含：No official approval / No marketplace approval / No universal**/full** runtime support / No external **first-session** pilot success / RISK-036 + do not claim 1.0.0 production-ready（修复 diff 未触碰 L5-15/L5-14 声明段） | ✓ 零回归 |
| B-8 Node ≥22.15 限定 | R0 §5 记「三件 + CHANGELOG 一致携带」 | checklist L15 ✓ / flags ✓ / CHANGELOG ✓；**rollback 无该字面**（B-8/engines/Node 全文 0 命中）——系 **R0 §5 该行表述过宽**（R0 基线即如此，非本轮回归），在此修正审查记录；B-8 限定语的规范性载体（checklist/flags/CHANGELOG）在场即满足 | ✓（附 R0 记录更正） |
| manifest canonical | 494 bytes/无 BOM/单尾 LF/NFC/紧凑排序/roundtrip 字节相等/8 顶层键 | **逐项复现全过**：494 B；BOM=False；single-tail-LF=True；NFC=True；roundtrip_byte_equal=True；top_keys=8 | ✓ 零回归 |
| Change Inventory | 14 commits、表 14/14 全等 | `git rev-list --count e376ddf..845c050` = **14**；表行 = **14**；#14 = `845c050` ✓（fix diff 未触碰清单段） | ✓ 零回归 |
| 豁免账本 | 4 条（3×UNSUPPORTED@review-FIX-300 + 1×AMBIGUOUS@checklist-0.81.0） | 实读 `core/loop-runtime-claim-exemptions.json`：**4 条逐条同构**（`LRC-EXEMPT-FIX300R0-71-1/-71-4/-72-1` ×UNSUPPORTED_AFFIRMATIVE@review-FIX-300-CODE-R0.md + `LRC-EXEMPT-CHECKLIST0810-241-1` ×AMBIGUOUS_SUBJECT_RELATION@release-checklist-0.81.0.md）；digest 锚 `REQUIRED_EXEMPTIONS_SHA256` 实存（checks/loop_runtime_claims.py:114/:1355） | ✓ 零回归 |

---

## 4. 新引入面检视（增量全集定性）

未暂存增量 7 文件（+17/−17）逐一归属：

1. **`commands/governance-init.md`**（3 行）= F-01 修复 ✓（已声明）
2. **`docs/release/release-checklist-0.82.0.md`**（3 行）= F-02/F-03 修复 ✓（已声明）
3. **`docs/release/rollback-plan-0.82.0.md`**（2 行）= F-04/F-06 修复 ✓（已声明；F-04 L24 残留 + F-06 §3 错位见 §1）
4. **`docs/release/feature-flags-0.82.0.md`**（1 行）= F-05 修复 ✓（已声明）
5. **`project/CHANGELOG.md`**（1 行）= F-07 修复 ✓（已声明）
6. **`skills/software-project-governance/infra/verify_workflow.py`**（6 行）= **任务书未列增量**——REQUIRED_SNIPPETS 版本钉 0.81.0→0.82.0（5 个 plugin/marketplace/package/manifest 锚）。定性：**必要且合规**——(a) CHANGELOG L38 投影段已声明「REQUIRED_SNIPPETS 版本钉」属 M-1 投影面；(b) 消费方 `check_snippets()` 全命中判据下，不 bump 则候选态（声明文件已 0.82.0）必 FAIL；(c) 净行数零差（6 处原位替换），archguard 24453 行数锚不受影响（checklist Gate 6 已预置「M-2 按 bump 后现场判定 R7 committed==fresh」条款承接）；(d) 方向与候选一致。→ 记入 M-2 复跑面（Gate 6 / verify 命令），非缺陷。
7. **`AGENTS.md`**（1 行）= 工作树 bootstrap 标记 0.81.0→0.82.0——**R0 之前既已在场**（R0 Gate 1 实跑已核 AGENTS/CLAUDE 工作树标记全 0.82.0），非本轮新增量 ✓

**结论：无声明面之外的产品逻辑改动；无范围漂移。**

---

## 5. 非阻塞 Notes 与后续义务

**M-1 冻结打包前置条件（MUST——不满足则 P1 复活）**

1. `git add` 全部未暂存增量后再打候选提交（7 文件：AGENTS.md、commands/governance-init.md、docs/release ×3、project/CHANGELOG.md、infra/verify_workflow.py）——**当前 staged 树仍含 3×`@bootstrap-version: 0.81.0`**，漏 add 即 F-01 在候选载荷中复活（R0 判据「staged 树 0 命中」以 M-1 冻结后的暂存面为准复核）。

**随批顺手项（P3，可选，不阻断）**

2. rollback L24 勘误注记记法与 L22 统一（如改为「`8bd6a8a^..845c050` = 11」或「含首 11」）。
3. rollback L35「§3 校验项」改为「§2.2 第 3 步与 §4 验证表 #5」；checklist L27「FIX-324 处置专节」补具名载体（与 L26 口径对齐）。
4. F-02 引注分层化（EVD-1034 主引 / F-R1-02 同族纪律）。

**M-2 义务不变（本报告不代替任何 M-2 实测）**：Gate 1~15 复跑（含 Gate 6 R7 committed==fresh——版本钉增量入判、安静窗 850 复跑、28u/28v/28w、check-release 后台作业、渲染 parity 字节值、契约 SHA 复测、ledger 候选态 lineage）；回滚演练 ≥1 次（M-2/M-5）；RISK-050 维持打开；**M-4 用户停点前不做发布决策、文档不得声明 M-2/M-3 未实测项通过**（本轮复核：现无此类声明）。

---

## 6. 命令上报表（全部只读 + 隔离 DSH_HOME；唯一写入 = 本报告）

| # | 命令（摘要） | 退出码 | 结论 |
|---|---|---|---|
| 1 | `git rev-parse HEAD` / `git status --porcelain` | 0 | HEAD = 845c050 未动；增量 7 文件 unstaged |
| 2 | `git diff --stat` + 逐文件 `git diff` | 0 | +17/−17 全集归属（§4） |
| 3 | `git grep @bootstrap-version`（工作树 / --cached 双态） | 0/0 | 工作树 3×0.82.0 / staged 3×0.81.0（§5-1 条件依据） |
| 4 | `python -m unittest discover -k EntryBootstrapTemplateTests`（隔离 DSH_HOME=`%TEMP%\rel078-r1-65d5d94e`，用后即删） | 0 | **6/6 OK**（含 3×标记动态断言） |
| 5 | `git grep REQUIRED_EXEMPTIONS_SHA256`（infra/） | 0 | checks/loop_runtime_claims.py:114/:1355 实锚 |
| 6 | 保守 token 扫描（三件套，UTF-8 显式读取） | 0 | 5 token 三文件在场；rollback 无 Node≥22.15 字面（R0 记录更正） |
| 7 | 账本实读 + ID/finding_code/source 逐条 | 0 | 4 条与 R0 记录一致 |
| 8 | manifest canonical 五检 + roundtrip（python） | 0 | 全过（§3） |
| 9 | `git rev-list --count e376ddf..845c050` / `8bd6a8a^..845c050` | 0/0 | 14 / **11**（L22 修正计数实证） |
| 10 | 先例实存核对：EVD-1034（evidence-log:2065）/ EVD-1054（:2147）/ EVD-1060（:2169）/ F-R1-02（REL-077 R1 :86-91） | 0 | 全实存；F-R1-02 实文为计数口径纪律（§2 注记） |
| 11 | F-11/F-12 指针链：`git grep` review-FIX-316-R0/R1 + plan-tracker:93 | 0 | 链路可解析（L27 非悬空） |
| 12 | review-FIX-324-326-CODE-R0.md 实存 + 结构读取 | 0 | 10241 bytes；L26 指针成立 |
| 13 | VERSIONING.md L11/L12/L37 行引注实读 | 0 | L11/L12 准确；L37 非契约面（F-07 前提复核） |
| 14 | CHANGELOG `L37` 残留扫描 | 0 | 仅历史版本段（范围外） |
| 15 | checklist Gate 行/冻结纪律/占位扫描（UTF-8） | 0 | §1/§2 所引原文逐条核过 |

未执行任何 `git add/commit/restore/reset/checkout/stash/revert/worktree`；未运行全量测试套件（仅定向 EntryBootstrapTemplateTests）；未触碰 `$HOME/.dsh` 与仓库外持久路径（`$tmpHome` 用后即删已复核）。

---

*审查方：Release Reviewer Agent（R0 同一审查方，round=R1）｜审查对象：0.82.0（REL-078）工作树未提交面（HEAD `845c050` + 未暂存增量 7 文件）｜结论：**APPROVED_WITH_NOTES**｜unresolved_blockers=0｜复审链关闭（首行「无（复审链关闭）」）｜M-2 门禁实测与 M-4 用户停点义务全部维持——本结论不是发布 go 授权。*
