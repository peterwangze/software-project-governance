# REVIEW-FEAT-088-CODE-R0 — 代码审查 R0：exploration_channels 通道探活守卫

**Round: R0（首轮）** | Reviewer: Code Reviewer（只读实读审查，唯一写入=本报告文件；Bash 禁止——命令输出一律以 EVD-1320/1321 机录为据并标注，未自行复跑）| 日期：2026-10-05

审查对象：commit `638509e`（5 files，+893/−6——diff 统计为机录口径，本审查以仓库当前文件态实读替代；工作树==commit 态为披露假设，见「未验证项」）。五文件：

1. `skills/software-project-governance/infra/verify_workflow.py` — `check_exploration_channels()`（L12142-12309）+ `check-exploration-channels` 子命令（L22450-22484 / argparse L26627-26634）+ Check 12 接线（L16517-16539）+ `check_cross_references()` 挂载（L12586-12598）
2. `skills/software-project-governance/infra/dsh_doctor.py` — `_channel_projection()`（L1180-1221）+ verdict FAIL 耦合（L1376-1383）+ render（L1896-1907）
3. `adapters/dsh/adapter-manifest.json` — 四 native 通道 dated 锚（L74-104）
4. `skills/software-project-governance/infra/tests/test_dsh_doctor.py` — `ExplorationChannelProjectionTests` ×6（L1196-1296）
5. `skills/software-project-governance/infra/tests/test_exploration_channels.py` — 新 372 行 ×18（全文实读）

## 总结论：APPROVED_WITH_NOTES

unresolved_blockers = 0

（独立结构字段：无未解决 BLOCKING finding。）

findings 计数：**P0=0 · P1=0 · P2=2 · P3=6**。两条 P2 均为强化/披露形态建议（佐证节定位边界、F-B3 裁定入账形态），不阻塞合并；六条 P3 为演进备注。

票面验收（plan-tracker L87）逐条映射：

- **①dsh-doctor 或 manifest 机检面含通道探活/证据形态校验** ✓ — 双面落地：引擎守卫（Check 12 计数 + 独立子命令）+ doctor 顶层投影。「探活」按物理边界如实分层为 layer(a) 静态形态 FAIL-able / layer(b) 只读探锚 / NOT-probeable 显式拒称（见审查面 2），与票面「探活/证据形态校验」的斜杠表述相容，非范围短缺。
- **②native 声明附 dated 证据** ✓ — dsh 四通道 `verified_on=2026-10-04` + `evidence_ref`，enrolled 集合 FAIL-able 强制（L12236-12245）。
- **③探活失败→降级建议不误报** ✓ — FAIL 仅触发于确定性事实（缺失/畸变/悬空/自相矛盾锚）；陈旧 >180 天仅 [ADVISORY] WARN 不计数（L12278-12287、L16518-16521 注释言明反误报理由）；降级建议内嵌 EXP-03 措辞；测试 `test_stale_anchor_is_an_advisory_never_an_issue` 钉死。
- **④回归零退化** — 机录口径达成（EVD-1320/1321：unittest 1052 OK、新面 18+92 OK、check-manifest/cross-refs/quote_sync/injection-budget 全 PASS 基线零退化）；本 Reviewer 未复跑，见「未验证项」。

---

## 逐项核验（审查面 1~7）

### 1. 守卫代码实读（verify_workflow.py 新块）— 通过

- **日期解析健壮性** ✓：结构化锚 `CHANNEL_ANCHOR_DATE_STRICT_RE = ^\d{4}-\d{2}-\d{2}$`（L12115）+ `datetime.strptime` 日历校验（L12136-12139）——`2026-02-31`/`2026-13-01` 均判 None→FAIL（测试 L145/L165 分别钉两种形态）；非字符串 verified_on 也落入同一路径（`isinstance` 前置，L12131）。prose 回退用宽松正则 `\b\d{4}-\d{2}-\d{2}\b`（L12114）仅作 inline 日期集合提取，二者职责分离正确。
- **enrolled 集合前向兼容语义** ✓：`CHANNEL_DATE_ANCHOR_ADAPTERS = ("dsh",)`（L12122）+ 注释言明「自愿携带锚者仍校验、未 enrolled 五平台零追溯 FAIL」（L12116-12121）。代码行为与注释一致：锚面整体位于 `status == "native"` 分支内（L12218-12219），`dated_anchor_required` 仅收紧「无任何锚」形态（L12236-12237）；畸形结构化锚对任何 adapter 都 FAIL（L12225-12228），悬空/无佐证 evidence_ref 同理（L12251-12270）——测试 L215-237 双向钉死（claude 未 enrolled 静默 + 自愿携带 "yesterday" 仍 FAIL）。
- **FAIL/WARN 阈值边界** ✓：`age > CHANNEL_EVIDENCE_STALE_DAYS`（180，对齐 host-contract `verified_on_ttl_days`，L12123-12126）严格大于——第 180 天不告警；负年龄（时钟滞后于锚）不告警也不 FAIL，与 L12102-12105「不以钟面单边证伪结构化日期」的设计声明一致。
- **结构规则** ✓：四通道键 `EXPLORATION_CHANNEL_KEYS`（L12112）缺一/多一均 FAIL（L12187-12196）；status 词表 `native/degraded/unsupported`（L12113）外 FAIL（L12207-12211）；mapping/evidence 非非空字符串 FAIL（L12212-12217）；`exploration_channels`/`channels` 非对象 FAIL（L12173-12186）。
- **不可读 JSON fail-closed** ✓：`OSError/json.JSONDecodeError/UnicodeDecodeError` → issue + face.error + continue（L12165-12172），测试 L295-301 钉死。
- **接线** ✓：`check_cross_references()` 以 quote_sync 同款「承载纪律」挂载（L12586-12591 注释言明不加新编号 check 的理由）；Check 12 内 issues 计入 `all_issues`（L16525-16526）、advisories 打 [ADVISORY] 不计数（L16538-16539）；`cmd_check_cross_references` 对 channel issues 置 fail→exit 1（L22426-22429）；独立子命令需显式 `--fail-on-issues` 才 exit 1（L22483-22484）——与 `check-manifest-consistency` 同款旗标约定（见 P3-1）。

### 2. 诚实分层验证（probe_layering ↔ 代码行为）— 通过

`probe_layering` 三段（L12293-12307）与代码逐条对得上：

- `static_evidence_form`「FAIL-able」= 上述结构+锚规则，真实可 FAIL；
- `feasible_probe`「evidence_ref existence + anchor-date corroboration…read-only」= L12254（is_file 悬空判定）+ L12259-12270（读取 + `verified_on in ref_text` 佐证），确无其它探测；**无任何 live probe 虚构**——代码不发起子进程、不探 web_search/route_agent；
- `not_probeable`「host-session tool liveness…NOT probed and NOT claimed」与 L12098-12105 顶注一致，且 CLI help 重复披露（L26630-26632「host-tool liveness is NOT probed」）、Check 12 PASS 行再披露（L16534-16537）。三层披露形态完备。

manifest 侧证据 prose 自带边界句「records existence at that date, not continuous liveness; availability drift degrades per EXP-03」（adapters/dsh/adapter-manifest.json L78/85/92/99），与守卫的声明口径一致——同一事实两个表面零漂移。

### 3. dsh-doctor 投影 — 通过

- **lazy import** ✓：`sys.path` 插入引擎目录后 `from verify_workflow import check_exploration_channels`（L1197-1200，noqa PLC0415），重复插入有守卫；传入 `ctx.root` 而非全局。
- **单裁决纪律（BT-R-02，ADR-018 L85/L192 语义）** ✓：投影不重判——block 内 `check: "check-exploration-channels"` 可联结引擎面（测试 L1267-1273 钉死）；verdict 仅由 `result["issues"]` 派生（L1215）。
- **K-12 域排除正确** ✓：K-12 比较域=「八 stage 记录 vs 28w boundary verdict」（L1341-1344 只扫 `records`）；channel FAIL 不入 records 故不制造伪 disagreement（测试 L1246-1249 断言无 K-12 记录且 stage 数恰为 8）；`k12_domain: "excluded — stage projections of 28w criteria only"` 字段披露理由（L1220）。把 manifest 判定塞进 28w 域才是 BT-R-02 违规——本实现的排除是正确执行而非规避。
- **崩溃降级** ✓：`except Exception` → `projected:false, verdict:None, note`（指向直接运行引擎命令，L1202-1212）；`BaseException`（KeyboardInterrupt/SystemExit）不吞——正确的窄捕获。测试 L1251-1265 钉死「崩溃→披露块 + exit 0 + 不因崩溃变 FAIL」，与 BT-2 stage 崩溃语义（NOT_RUN 披露而非杀 doctor，L1244-1252）同构。
- **S0-S7 契约不动** ✓：`STAGES`/`_stage_runners`（L1229-1241）零改动痕迹；投影是 report 顶层 additive 键（L1376）；`--offline` 下照跑（文件级判定，L1371-1375 注释 + `--offline` help L1922-1924 口径一致，测试 L1217-1230 钉死）。
- **verdict 耦合** ✓：`channel_failed or any(stage FAIL)` → FAIL（L1377-1382）；channel 单独 PASS 不制造顶层 PASS（PASS 需有 stage PASS）——保守方向正确。
- **render** ✓：verdict/projected/issues 数/k12_domain 一行 + issues 前 4 + advisories 前 2 + note（L1896-1907）；崩溃块无 issues 键时 `.get() or []` 安全。

### 4. manifest dated 锚 + 佐证文档 — 通过

- **四锚实读** ✓：discover/inspect/consult/validate 均 `status=native` + `mapping` + 带 inline 日期的 evidence + `verified_on="2026-10-04"` + `evidence_ref=docs/reviews/review-FEAT-086-DESIGN-R0.md`（L75-102）；prose 日期与结构化锚同值（drift 检查过）；`exploration_channels.degraded_mode` 全局行携带 EXP-03 措辞（L104）；note 保留 F-A2 规范标记「生成≠咨询」（L73）；consult mapping 明示 draw 排除（L91）。
- **佐证文档一致性** ✓（本 Reviewer 实读）：`review-FEAT-086-DESIGN-R0.md` 头部日期 2026-10-04（L3）；§3(c) L31 载明一手核验实测——「本 Reviewer 即运行于 dsh 宿主，本会话工具面实测存在 web_search/read/grep/glob/pwsh/route_agent（arch/vision/draw 三目标）」——与四通道 evidence prose 的逐通道声称（web_search→discover、read/grep/glob→inspect、route_agent arch/vision+draw 排除→consult、pwsh→validate）**逐项对得上**；日期在引用文档在场（头部+L34），佐证探针通过是事实而非仅机录。
- **JSON 合法性**：文件实读结构完整；`json.loads` 通过为机录口径（check-exploration-channels 0 / quote_sync 0）。
- **能力声明无变化**：以「与 FEAT-086 R0 审查记录的一致性」替代 diff 验证——该审查 §3(c)(d) 描述的 dsh 姿态（四通道 native + 全局 degraded_mode + EXP-03）与现态完全一致；−6 行的逐字旧态不可复查（无 git 通道），见「未验证项」。
- **其余五平台结构面抽查**：claude（L68-96：四键齐全、note 标记在、native 通道无锚→依范围守卫静默）与 gemini（L71-101：`unsupported` 词形合法、非 native 不进锚面、degraded_mode+EXP-03 齐全）实读通过；codex/opencode/chrys 依机录（守卫 0 issues）+ FEAT-086 R0 §3 独立描述，未逐字实读（披露于「未验证项」）。

### 5. 测试质量（24 新用例）— 通过（含覆盖缺口备注 P3-2）

- **沙箱形态** ✓：`_materialize_surfaces` 复制六 manifest + 佐证文档入一次性 temp ROOT、`patch.object(vw, "ROOT", …)`，真实仓只读（L75-86）；temp 目录用 FIX-404 同款 0o700 形态（L55-67 注释言明 UAC 过滤令牌下的理由）。
- **断言精确性** ✓：无宽断言——正向基线 `assertEqual(result["issues"], [])` 逐字空表；负向用例多为 `len==1/==2` 精确计数 + 关键子串（`dated evidence anchor`/`EXP-03`/`dangling`/`not corroborated`/`must not drift`）；一处整句逐字断言（L168-171）；face 簿记 `age_days == (today - date(2026,10,4)).days`（L338-339）。doctor 侧 6 用例断言 `projected is True/False`、stage 列表恰为 `_STAGE_IDS`、exit code 常量、render 输出子串——均窄。
- **时钟鲁棒性设计** ✓：正向基线对陈旧性做结构性双分支（fresh→零 advisory；old→全 EXP-03 advisory，L113-119），不会随日历漂移变红；陈旧用例同步改写佐证文档追加锚日期（L313-315）使 layer(b) 安静——测试自身遵守「锚与佐证同移」的语义。
- **负向覆盖面**：缺锚/双形态畸变日期/悬空 ref/无佐证日期/prose-结构 drift/未 enrolled 静默/自愿锚仍校验/inline-only 惯例兼容/缺通道键/词表外 status/多余键/坏 JSON/陈旧 advisory——守卫主分支全覆盖。缺口见 P3-2（四条次要分支）。
- **doctor 用例的引擎打桩** ✓：monkeypatch `verify_workflow.check_exploration_channels` + addCleanup 还原（L1208-1215）——测的是投影契约而非引擎重跑，边界干净。
- **1052 基线与新文件分离运行**：机录口径（EVD-1320 分列三条 unittest 命令），事实口径自洽；未复跑。

### 6. 五维度评审（含 AI 专项视角）+ 向后兼容 — 通过

- **正确性**：见审查面 1/3；边界（非字符串锚、空 channels、未来日期、时钟滞后）均有确定行为。
- **安全性**：输入校验 fail-closed；无注入面（manifest 内容只进字符串拼接输出，无 eval/命令执行）；无硬编码密钥；evidence_ref 仅 is_file/read_text。遗留：无仓内包含性校验（P3-6）。
- **可维护性**：命名表意（`_anchor_date_or_none`/`native_anchored`/`inline_date_only`）；注释与代码一致且携带设计出处（F-A3/EXP-03/BT-R-02/K-12/R1 N-3 逐处可查）。函数长度超 50 行指引（P3-3，仓库同文件先例一致）。
- **性能**：六 manifest + ≤4 引用文档的一次性只读 I/O，无循环放大；doctor 侧 lazy import 避免启动载入。
- **测试覆盖**：见审查面 5。
- **AI 专项视角**：本票核心风险正是「AI 声明可信度」——实现的回答是把声明拆成可证伪层（dated 结构化字段 + 可复查引用文档 + 机检）与不可探层（显式拒称），manifest prose 不再含「used by the live sessions」式的不可证伪自述作为唯一支撑（旧句保留但让位于 dated 锚）。这是对 AI 自述漂移面的正确工程化。
- **向后兼容** ✓：子命令纯 additive（argparse 新 parser，L26627-26634）；`check_cross_references()` 返回 dict 新增键，既有消费者按旧键取值不受影响（Check 12 显示代码用 `.get(…, {})` 防御旧形态，L16506/L16522）；manifest 新字段 `verified_on/evidence_ref` 对未 enrolled 平台零约束（EVD-1321 迁移判断与此一致）；doctor report 新顶层键 additive，`--json` 消费者旧键不动。

### 7. F-B3 显式不归属裁定评估 — 裁定成立，披露形态薄（→ P2-2）

- **裁定实体**：F-B3 源于 review-FEAT-087-DESIGN-R0（L49/L55）——「SHOULD 注记无机器守卫（省略合规性与偷懒不可机检区分）……随 FEAT-088 通道探活守卫票一并评估归属」。FEAT-088 收口时裁定不归属本票机检面（EVD-1320 结论列：「F-B3 显式不归属（低判别力启发式 + A10 薄度，sweep 为更适载体）」）。
- **四点理由逐条评估**：①**判定面不同**成立——F-B3 判的是样本报告 exploration 区块的留痕存在性，本票判的是 manifest 通道声明证据形态，判决输入与规范源（M10.2 样本纪律 vs M10.3 通道表）均不同；②**机检效力边界**成立——087 审查自身即承认「如实省略（合法）与懒惰省略（违规倾向）不可机检区分」，强拧进本票只会制造低判别力启发式，恰是本票「FAIL 仅触发于确定性事实」原则（L12110-12111）所要防的误报类；③**A10 薄度**成立——为不可判定的面加检查违背薄度原则（087 L49 已预注「不宜强推」）；④**更适载体**成立——sweep/check-governance 的 advisory 形态与 F-B3 的非阻断性质匹配。
- **裁定时点** ✓：F-B3 明文约定「随 FEAT-088 一并评估」，裁定发生在 FEAT-088 收口证据内（2026-10-05），无逾期、无静默跳过。
- **披露形态** ✗ 薄：四点理由的完整展开只存在于本票调度面与 EVD-1320 结论列一句压缩；对照 DEC-315 先例（六条跨票 findings 归属逐条入 decision-log），跨票 finding 处置入账层级降了一档；且「sweep 为更适载体」的残余项在 plan-tracker/risk-log 未见登记载体——存在被静默丢落的窗口。→ P2-2。

---

## 蓝军挑战（4 条）

1. **prose 内联日期正则的误匹配面**：宽松正则抓取 evidence 文本中一切 `\d{4}-\d{2}-\d{2}`。攻击面拆解：(a) drift 检查是「锚日期 ∈ prose 日期集合」的成员判定——prose 含多个无关日期时不误报（只要锚在其中），但也**无法识别哪个日期才是锚声称**，多日期 prose 中错锚可蒙混（若同时满足 doc 内在场）；(b) 佐证探针是**全文子串匹配**——manifest 声称「evidence_ref §3(c) saw …」而机检只验「日期出现在引用文档任何位置」，节定位声称超出机检能力（当前仓库态 §3(c) 与头部确实在场，事实无恙；这是强度边界非事实错误）。→ P2-1。
2. **enrolled 集合未来扩员的追溯 FAIL 风险**：向 `CHANNEL_DATE_ANCHOR_ADAPTERS` 加 id 而不同改 manifest（如 claude——其 native inspect/validate 现无任何锚）会立刻响亮 FAIL。这是 fail-closed 的正确失败形态（强制两步协议同 change 完成），但协议本身只活在代码注释（L12116-12121）——规范源 M10.3/manifest 文档面无登记，未来扩员者可能只改常量。→ P3-4。
3. **dated 锚「自验自引」循环面**：manifest（生态产出）→ 引用 review 文档（生态内 Reviewer agent 产出）→ 守卫（同仓）验内部一致性。佐证效力边界=仓内一致性≠外部独立验证；实际强度来自引用文档是**异会话、角色契约约束（只写报告文件）的 Reviewer 在 dsh 宿主上的一手实测记录**，且该文档自身诚实披露未验证项（其 L79）。守卫从未声称超过此边界（not_probeable 措辞精确），manifest prose 用「records existence at that date, not continuous liveness」自限。残余接受：这是 CLI 进程可诚实达到的最强形态，且比原先的裸自述严格更强。无 finding，边界记录在案。
4. **陈旧性依赖墙钟**：机器钟前跳会提前告警、后跳会压制告警——设计明示拒绝以钟面单边证伪（L12102-12105），且 advisory 永不入 gate、重约会自愈。攻击成本>收益（告警不阻断），接受。

## Findings（P0~P3）

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-C1 | **P2** | verify_workflow.py L12259-12270 | 佐证探针为引用文档**全文子串匹配**，而 manifest evidence 声称节级定位（「evidence_ref §3(c) saw …」）——机检强度低于 prose 声称粒度；日期在文档无关章节在场也会通过 | 可选强化：锚日期须出现在 evidence_ref 中「§/章节标记邻域」或头部 N 行内；至少在 probe_layering.feasible_probe 措辞中明示「document-wide，非节定位」。遗留承载：下一张 infra sweep 票 |
| F-C2 | **P2** | .governance/evidence-log.md L1971（EVD-1320 结论列） | F-B3 不归属裁定实质成立但披露/追踪薄：四点理由完整展开仅存调度面，机录面一句压缩；对照 DEC-315 先例（跨票 findings 归属入 decision-log）入账层级降档；「sweep 为更适载体」残余无登记载体（plan-tracker/risk-log 均无 F-B3 行） | 补一条 DEC（引用 087 R0 F-B3 + 本票裁定四点理由）或在 sweep 候选池登记该残余；本报告 §7 可作依据 |
| F-C3 | **P3** | verify_workflow.py L22483-22484 | 独立子命令默认 exit 0（需 `--fail-on-issues`），与 `cmd_check_cross_references` 默认 FAIL 不同向；与 check-manifest-consistency 同款旗标约定、help 如实标注，CI 直接采用者可能误判 | 维持现状可；建议在 help 或 docs 统一说明「独立诊断面默认零退出、门禁面走 check/check-cross-references」 |
| F-C4 | **P3** | test_exploration_channels.py | 四条次要分支无直测：channel 值非对象（L12200-12204）、mapping/evidence 空串（L12212-12217）、evidence_ref 非字符串（L12247-12250）、ref 读取 OSError→空文本→佐证 FAIL 路径（L12261-12264） | 随下一张 infra 测试票补齐（均为低频形态，主路径已覆盖） |
| F-C5 | **P3** | verify_workflow.py L12142-12309 | 函数 ~168 行超编码规范 50 行指引（仓库同文件 check_cross_references 等先例一致，段落注释清晰）；另：非 native 通道自愿携带的畸形锚不校验（锚面仅 native，L12218）——设计选择但无注释/测试固化 | 择一：拆 `_check_channel_anchor()` 辅助函数；或在锚面入口加一行注释明示「degraded/unsupported 自愿锚不校验」+ 补一条钉死用例 |
| F-C6 | **P3** | verify_workflow.py L12116-12122 | enrolled 扩员两步协议（manifest 加锚字段 + 常量加 id 同 change）仅存于代码注释；M10.3 规范源/manifest 文档面无登记 | 在 behavior-protocol M10.3 物理化说明或本票 evidence 补一句扩员协议，供未来 enroller 检索 |
| F-C7 | **P3** | verify_workflow.py L12252-12253 | `evidence_ref` 无仓内包含性校验：`base / ref_norm` 接受 `../` 逃逸路径（只读 + 输出仅日期在场布尔，无泄露面；manifest 属版本控制内容，信任级高） | 防御深度：`ref_path.resolve().relative_to(base)` 包含性校验，随 F-C4 同票 |
| F-C8 | **P3** | .governance/change-triage/FEAT-088.json L10-13 | triage files 面仅 2 文件，实际改动 5 文件（dsh_doctor.py 与两测试文件未入 conflict 检测面——FEAT-031 等历史票含 dsh_doctor.py，若并发会漏报冲突） | triage 快照为时点产物可不强改；建议后续票把「triage files ⊇ 实际改动集」纳入收口自检或 check-governance advisory |

处置建议：F-C1/F-C2 可遗留（载体已建议）；F-C3~F-C8 记录为 sweep 候选。无 P0/P1，按 skill 关闭规则可合并。

## 硬门槛自检

- [x] Review 意见覆盖 5 个评审维度（§6 逐维度 + §1-§5 展开正确性/测试覆盖）
- [x] 每条意见有明确级别标注（P0~P3，findings 表 8 条）
- [x] 所有 P0 已关闭（P0 计数 = 0）
- [x] 所有 P1 已处理或记录遗留（P1 计数 = 0）
- [x] Review 结论有明确理由（验收①~④映射 + APPROVED_WITH_NOTES 依据：无阻塞缺陷，两条 P2 为强化/披露建议）
- [x] 每条阻塞/通过结论指向可复查事实（文件:行号 / 实读引文 / 机录 EVD 编号）
- [x] APPROVED_WITH_NOTES 含独立结构字段 `unresolved_blockers = 0`（本节上方独立行，非自然语言偶然出现）

## 未验证项声明（Bash 禁止——以下均以机录为据并标注，不作独立通过依据）

1. **全部命令输出**：unittest 1052 OK / 18 OK / 92 OK、check-manifest-consistency / check-cross-references / check-exploration-channels / dsh-doctor --selftest / check-injection-budget（resident 4244/6000、342≤370）/ check-governance 2 issues（28n 预存 + 28c 宿主态）——EVD-1320/1321 机录，本 Reviewer 无命令通道未复跑。回归零退化（验收④）的判定以此机录为据。
2. **commit `638509e` diff 统计**（+893/−6 及分文件行数）：无 git 通道；以仓库当前文件态实读替代，**工作树==commit 态为披露假设**。
3. **manifest「无能力声明变化」（−6 行旧态）**：不可逐字复查；以「现态与 FEAT-086 R0 审查记录 §3(c)(d) 描述一致」替代验证。
4. **codex/opencode/chrys 三 manifest 逐字实读**：未做；依守卫机录 0 issues + FEAT-086 R0 §3 独立描述（claude/gemini/dsh 已逐字实读）。
5. **dsh-doctor --offline 整体 exit 1 的环境归因**（预存 S1 preset 陈旧）：机录/调度面口径，未复跑。
6. **佐证文档的一手核验行为真实性**（087/086 Reviewer 会话当时确实测过工具面）：不可复查时序事实；本审查可核的仓内一致性（日期在场 + 逐通道声称对齐）已全部实读核验。
