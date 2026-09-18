# 审查报告 — FEAT-036-CODE-R1（round 1 复审）

- **任务**: FEAT-036 — Snapshot 双契约（完整机器 artifact + 默认交互视图 ≤8 字段）
- **Round**: 1（前轮 = `docs/reviews/review-FEAT-036-CODE-R0.md`，结论 NEEDS_CHANGE，P0=0/P1=1/P2=3/P3=2——本报告逐条响应其全部 findings，复审本质 = 验证修复）
- **审查者**: Code Reviewer Agent（只读审查；唯一写操作 = 本报告）
- **复审对象**: R1 返工净改动（未提交）
  1. `commands/governance.md` — 9 处拆分口径修改（:479/:484/:485/:492/:505/:512-519/:521-527/:529-533/:534）
  2. `commands/governance-status.md` — 6 处（:55/:60-63/:99/:125/:155，较 R0 行号 +2 漂移源于新增 Health 注脚，见 P3-1）
  3. `skills/software-project-governance/infra/tests/test_verify_workflow.py` — `test_governance_snapshot_dual_contract_default_view_guard`（docstring + 4 个拆分口径 marker + 「24 字段」反断言锁，:9554-9608）
- **验收口径**: `.governance/change-triage/FEAT-036.json`（历史原样保留——见第四节 4）
- **方法与限制（事实依据红线声明）**: 审查者工具面无 Bash/pwsh——运行时命令（pytest / cross-refs / manifest / projection-sync / pack-status / first-run-demo / status 实跑）**均未执行**，Developer 申报的「校验全 PASS + pytest 858 passed（91 subtests）」标 **未实测（静态无矛盾）**。本轮核验方法 = 引擎事实独立逐行复核 + 三文件改动面逐行比对 + 全局残留扫描（grep）。

---

## 〇、R0 findings 逐条响应表（复审纪律 1——必达项）

| R0 # | 内容 | 判定 | R1 证据 |
|------|------|------|---------|
| P1-1 | 完整机器契约「24 字段三载体可达」声明与引擎现实不符 | ✅ **已修复**（采用 R0 建议方案 a——docs 拆口径，不动引擎） | 详见第一节 1 |
| P2-1 | Question budget 固定语义行与引擎非逐字 | ✅ **已修复** | 详见第一节 2 |
| P2-2 | governance-status.md 枚举滑移（25 token，多 "Existing governance state detected"） | ✅ **已修复** | 详见第一节 3 |
| P2-3 | e2e fixture 漂移未同步 | ⏸ **按指示转跟踪（未修复，已挂载）** | FEAT-040 在案（plan-tracker:88，依赖含 FEAT-036，⏳ 待执行，验收含「四平台投影同步 PASS」）——遗留有归属、有验收，不阻塞本任务合并 |
| P3-1 | Health 字段在完整契约无对应物（缺映射注脚） | ✅ **已修复** | governance.md:523 与 governance-status.md:64 各一行注脚：数据源 = `check-governance --summary-only`、非 snapshot 字段、按 Full 指示行取 artifact 的消费者需另跑 `check-governance`——与 R0 建议逐字同构 |
| P3-2 | 字段名不一致（"Gate setup status" vs 引擎键 "Gate/setup status"） | ✅ **已修复** | 全局 grep `Gate setup status` 零匹配；两文件统一为引擎键名（governance-status.md:60/:99/:155 与引擎 L9132 一致） |

**新引入（本轮改动面）**: 未发现 P0~P2 级新问题；2 条备注级观察见第三节。

---

## 一、Developer R1 申报逐项核实

### 1. P1-1 拆分口径——✅ 成立（与引擎现实一致，20/19/4 三数字无歧义）

**引擎事实独立复核（本轮重新逐行验证，非沿用 R0）**：
- `build_delivery_trust_snapshot`（verify_workflow.py:9120-9156）返回 **恰 20 键**：Resume state、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Flow-unit lanes、Risk、Evidence、Next action、Preset guidance、Question budget、Verification signal、No-overclaim boundary。
- `status` 文本面 `┌─ Delivery Trust Snapshot ─┐` 段（:10961-10964）逐键打印该 dict 全部条目 = **20 字段**。
- `status --json` 的 `delivery_trust_snapshot`（:10926）= 同一 dict = **20 键**。
- `FIRST_RUN_DEMO_REQUIRED_FIELDS`（:9159-9179）= **恰 19 字段**（20 键减 `Flow-unit lanes`）。
- `check_governance_pack_status`（:5201-5228）校验 **docs 文件**（`GOVERNANCE_PACK_STATUS_DOC_PATHS`）的 token 在场——4 个 pack 字段确为 doc-surface 契约，不在任何 CLI snapshot 输出中。

**docs 拆分口径核验（逐落点）**：
- governance.md:479/:512 —— 「20 字段 CLI snapshot 契约 + 4 字段 pack doc-surface 契约」双契约命名两处一致；pack 部分「不在任何 CLI snapshot 输出中」限定在场。
- governance.md:514-517 —— 三个 CLI 载体各自计数独立且准确：`status` 文本面「20 字段全量」、`status --json`「20 键」、`first-run-demo --assert-snapshot`「断言其中 **19** 字段（`FIRST_RUN_DEMO_REQUIRED_FIELDS`，不含 `Flow-unit lanes`）」——三个数字各归其载体，无一混用。
- governance.md:519 —— 字段集枚举恰 20 个名字，与引擎 20 键逐字一致（含 `Gate/setup status`、`Flow-unit lanes`）。
- governance.md:521 / governance-status.md:63 —— 4 个 pack 字段单列：「载体 = 两命令文档的固定语义行（docs 面），由 `check-governance-pack-status` 专项校验守护，不在任何 CLI snapshot 输出中」——doc-surface 契约的**获取/守护方式表述明确**（复审要点 3 答：明确）。
- **Full 指示行两处**（复审要点 1 指定）：governance.md:505 与 governance-status.md:55 均改为 `Full: 20-field CLI snapshot + 4-field pack doc-surface -> status --json (delivery_trust_snapshot) / check-governance-pack-status`——两行同口径，CLI 部分指向真实 20 键 artifact、pack 部分指向真实校验命令，无 24 字段残留。
- governance.md:529-533 —— 「两端可达，缺一不可」已从「24 字段全量」改限定为「完整 **20 字段 CLI snapshot 契约**可经 `status`/`status --json` 一步取回（两端可达，缺一不可）」——该声明在限定范围内**事实成立**（两载体各输出同一 20 键）；pack 契约单句另述载体与校验。governance.md:534 同步改「断言 CLI snapshot 契约 20 字段中的 **19 个** demo 断言字段」——与引擎一致。
- governance-status.md:60-62 —— 同口径拆分：字段集 20 名单 + 「权威载体 = 既有确定性 CLI 输出（不新建平行契约）」+ 19 字段断言限定，与 governance.md 完全对齐。

### 2. P2-1 Question budget 逐字对齐——✅ 成立

- 引擎原文（verify_workflow.py:9146-9149）：`ask no more than 3 non-critical questions before snapshot; record deferred non-critical fields as assumptions`。
- governance.md:527 / governance-status.md:72 英文部分与引擎**逐字一致**（中文括注为渲染注解，不属于被声明逐字一致的常量值，无歧义）。
- 「逐字一致」声明已按**载体分组限定**（复审要点 1 指定项）：governance.md:525 =「CLI snapshot 三行与 `status` 输出逐字一致，pack doc-surface 三行为 docs 契约常量、经 token 校验」——三行 CLI 常量（Preset guidance :526 / Question budget :527 / No-overclaim :528）经与引擎 :9142-9155 逐字比对全部成立；分组限定消除了 R0「声明对该行不成立」的矛盾。

### 3. P2-2 枚举滑移——✅ 成立

- governance-status.md:155（R0 :153）：枚举恰 **20** 个 CLI 字段名（附「恰 20 个字段名」自述）+ 4 个 pack 字段分列；`Existing governance state detected` 已删除（grep 零残留）。计数与声明一致。

### 4. 守护测试新 marker 与反断言（复审要点 2）——✅ 成立

- docstring（test:9555-9560）重写为「split-accurate: a 20-field CLI snapshot reachable via the existing status CLI carriers plus a 4-field pack doc-surface contract guarded by check-governance-pack-status (no parallel contract)」——与拆分口径一致。
- 4 个拆分口径 marker（test:9572-9575）：`20 字段 CLI snapshot 契约` / `4 字段 pack doc-surface 契约` / `不在任何 CLI snapshot 输出中` / `断言其中 19 字段`——经与两 docs 文本静态比对，四个 marker 在两文件中均真实在场（governance.md:479/512/517/521；governance-status.md:60/62/63/155），非不可满足的死 marker。
- 「24 字段」反断言锁（test:9603-9606）：`24-field` 与 `24 字段` 不得出现在 **compact 块**——作用域正确锁定在回归风险面（compact 视图）；governance.md:510 的历史基线引用（AUDIT-154「改造前 24 字段强制生成」）位于 compact 块外，不触发误报，与「有意保留」申报自洽。
- 既有结构断言保留完整：`len(compact_labels)==8` 自检（:9581）、恰 8 字段行（:9596）、full-face 泄漏反断言（:9599-9602）、`Flow-unit lanes` 在案（:9608）。

### 5. 历史申报记录未改（复审要点 4）——✅ 成立

- 审计报告 `docs/requirements/governance-bootstrap-cost-audit-0.84.0.md:182` 原样保留「artifact 保留 24 字段」acceptance——历史不改写纪律 ✓。
- triage JSON `.governance/change-triage/FEAT-036.json` 原样（:15 reason「24 字段强制输出」为历史归因，保留）✓。
- plan-tracker:85 与 execution-packets.json 的 24 字段 acceptance 原文未动 ✓（属历史/计划记录，任务收尾时由 Coordinator 做口径映射入证据，见备注 N-1）。

### 6. 运行时校验申报——⚠️ 未实测（静态无矛盾）

- Developer 申报 cross-refs / manifest(739) / projection-sync / pack-status / first-run-demo 全 PASS + pytest 858 passed（91 subtests）。审查者工具面无 Bash/pwsh，**未复跑**。静态核验无矛盾：守护测试全部断言项经逐条静态比对可满足；pack-status 校验对象（docs 文件 token）在场；first-run-demo 断言面（19 字段 + no-overclaim markers）与引擎现状一致。**该申报以「静态核验通过 + Developer 机录证据为准」，不构成本轮审查的独立运行时证明。**

---

## 二、五维度复审（本轮改动面）

### 维度 1：正确性
- 拆分口径与引擎现实逐点一致（20 键 / 文本面 20 / --json 20 键 / demo 断言 19 / pack 4 字段 doc-surface）——见第一节 1。
- 拆分后全部可达性声明可核验：「两端可达」限定于两 CLI 载体（成立）；「断言其中 19 字段」限定于 demo 断言面（成立）；pack 部分不再被声明为 CLI 可达。
- 无新逻辑面引入（docs + 测试断言，无引擎改动）。

### 维度 2：安全性（异常不隐藏红线回归检查）
- R0 已核实的红线行在 R1 改动后**全部原样在场**：governance.md:486（折叠红线）/:498（Mode hooks）/:502（Health deferred→待检查 + FAIL 内联）/:509（Risks 最高升级项）；governance-status.md:52/:59/:154。拆分口径重写未触碰任何 fail-closed 语义。
- no-overclaim 面：governance.md:528/:531 与 governance-status.md:71 的 Pack boundary 行保留全部 boundary tokens 与中文否定结构；`check_governance_pack_status` 校验对象在场——静态推演仍构成 scoped negation。**静态核验，运行时未实测。**

### 维度 3：可维护性
- 双文件同步面维持同一口径（20/19/4 数字在 15 个落点间零漂移——逐落点比对）；守护测试以结构断言 + marker 双层锁定，防回归强度较 R0 进一步提高（新增「24 字段」反断言锁堵住 P1-1 的复发路径）。
- 行号漂移（governance-status.md +2）源于 Health 注脚插入，内容对应关系已逐点确认，非漂移失同步。

### 维度 4：性能
- 无新性能面（本轮改动为措辞与测试断言）。≤700 tok 预算与 DEC-205 推演口径标注原样保留（governance.md:510）。

### 维度 5：测试覆盖
- 反断言锁补上了 R0 P1-1 的回归路径（旧单契约措辞复活）；4 个 marker 锁住拆分口径关键短语。遗留不锁面与 R0 相同（fixture / 预算 / 字段顺序——前者已挂 FEAT-040，后两者本质不可静态锁定，R0 已裁定可接受，无变化）。

---

## 三、新引入检查（复审要点 3）与备注

**未发现 P0~P2 级新引入问题。** 逐项检查：
- doc-surface 契约获取方式：明确（载体 = docs 固定语义行 + `check-governance-pack-status` 校验，两文件各两处表述一致）✓
- 20/19/4 数字在各落点无混用 ✓；「逐字一致」声明按载体分组后无过度声明 ✓
- 反断言锁作用域（compact 块）与历史引用（:510）无冲突 ✓
- 全局残留扫描：`24 字段`/`24-field`/`断言全部字段`/`Full: 24` 在 commands/ 下仅剩 governance.md:510 一处（AUDIT-154 历史基线引用，有「改造前」限定，有意保留）✓

备注级观察（不构成 finding，不要求修改）：
- **N-1（收尾口径映射）**: plan-tracker:85 acceptance 原文「artifact 保留 24 字段」未改（历史纪律正确）。任务收尾入证据时，Coordinator 应记录口径映射——20 CLI 字段 + 4 pack doc-surface 字段 = 24 个契约 token 零删减，修正的仅是「载体可达性声明」而非契约面本身，acceptance 意图（不削减机器面）满足。
- **N-2（Full 指示行语义）**: 指示行中 pack 部分指向 `check-governance-pack-status`（校验命令而非获取命令）；契约正文（governance.md:521 / governance-status.md:63）已明确 pack 字段载体是 docs 语义行，指示行作为索引不误导。纯记录。

---

## 四、AI 生成代码专项（本轮改动面 5 项，复审要点 5）

1. **mock/占位**: 无——测试读真实仓库文件 ✓
2. **硬编码敏感信息**: 无密钥/token/密码（marker 硬编码属文档契约守护测试本职）✓
3. **幻觉 API**: 本轮无新 API 引用；docstring/marker 均为字符串字面量，`re.search/read_text/subTest/vw.ROOT` 用法 R0 已核验 ✓
4. **TODO/残桩**: 改动面无 TODO/FIXME/占位实现 ✓
5. **过度实现**: 拆口径为纯措辞修正 + 4 marker + 1 反断言，未扩引擎、未新建平行契约（「不新建平行契约」marker 本身在案）✓

---

## 五、硬门槛自检

- P0 = 0 ✅
- 5 维度全覆盖 ✅（第二节）
- 每条发现 P0~P3 分级 ✅（本轮新 finding：P0=0/P1=0/P2=0/P3=0；R0 遗留 P2-3 有跟踪归属）
- 设计一致性（triage acceptance）：默认视图 ≤700 tok ✅（推演口径，R0 裁定）；异常不隐藏 ✅；artifact 字段保留——24 个契约 token 零删减（20 CLI + 4 doc-surface），载体声明已与引擎对齐 ✅（备注 N-1 的收尾映射留予 Coordinator）
- AI 专项 5 项 ✅（第四节）
- **R0 复审锚逐条响应 ✅**（第〇节——6 条 findings 全部响应，复审纪律 1/2/3 均满足：逐条标注、头部 round=R1 + R0 引用、未跳过验证直接通过）

---

## 结论：APPROVED_WITH_NOTES（unresolved_blockers=0；P0=0/P1=0/P2=0/P3=0）

R0 全部 6 条 findings 逐条核验：P1-1/P2-1/P2-2/P3-1/P3-2 已修复且与引擎事实独立复核一致（20/19/4 三数字无歧义，Full 指示行两处同口径）；P2-3 按指示挂 FEAT-040（跟踪在案，不阻塞）。历史申报记录未改写；守护测试反断言锁与拆分口径 marker 落点真实可满足；无新引入 P0~P2 问题。运行时校验申报（pytest 858 + 各 validator PASS）因审查者工具面限制未复跑，静态核验无矛盾。备注 N-1（收尾时 plan-tracker acceptance 口径映射入证据）与 N-2（Full 指示行 pack 指向语义，纯记录）不阻塞合并。
