# REVIEW-FIX-432-CODE-R0 — M0-M9→M10 sweep + quote_sync 引文同步守卫 + F-A2 note 监控面 + F-A5/F-5 注记

**Round: R0（首轮）** | Reviewer: Code Reviewer（独立实读审查，唯一写入=本报告文件）| 日期：2026-10-05
审查对象：commit `9a28e4d`（15 files，+138/−21，未 push）的落地产物——Reviewer 无命令通道（角色契约：Bash 禁止），以仓库当前文件态实读 + EVD-1316/1317（evidence-log L2009-2010）记录的机检事实为审查面。行数基线：behavior-protocol.md 905 行（FEAT-086 R0 基线 901，+4：M0 F-5 注记 L9 / M10.2 F-A5 段 L855 / M10.4 守卫句并入 L872）。

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**（无 BLOCKING finding；sweep 完整、守卫逻辑正确且 fail-closed、重定价合法、边界纪律与设计一致性成立）
findings 计数：P0=0 · P1=1 · P2=1 · P3=6。P1 为新守卫的测试看护缺口（强烈建议随票或遗留计划闭合）；P2 为 F-A5 注记措辞与既有样本 S2 的解读歧义；P3 全部为精度/健壮性演进备注，不阻塞本票收口。

## 逐项实读核验（审查面 1~8）

### 1. quote_sync 守卫正确性（verify_workflow.py +112 行）— 通过

实读 L12002-12075（常量+helper）、L12349-12356（结果装配）、三消费点 L7500-7513 / L16230-16274 / L22112-22162：

- **(a) M10.4 引文正则健壮性**：锚定形态 `任务级触发入口位于 SKILL\.md「Agent 分发路由」表后一行：「(.*?)」`（L12040）与 behavior-protocol.md L872 实文逐字对合（含全角标点/空格，实读比对通过）；非贪婪捕获止于引文闭合 `」`，当前引文 span（`新任务/事务分解后 → 探索适用性判断（EXP-01，详见 \`references/behavior-protocol.md\` M10）`）内部无 `」`，捕获完整。三态 fail-closed 逐一成立：①bp 锚行改写/缺失 → 正则失配 → issue（L12043-12047）；②引文与 SKILL.md 实文单侧漂移 → `m.group(1) not in skill_text` → issue（L12048-12052）；③文件不可读（OSError）→ 直接返回 fail-closed issue（L12029-12036）。未加 re.DOTALL——引文跨行会失配 → issue（fail-closed 方向正确）。
- **(b) `生成≠咨询` 双向校验**：规范源丢标记 → issue（L12055-12060）；六 note 任一丢标记/不可读/非法 JSON → issue（L12062-12074）。双向均 FAIL 而非静默跳过，与 docstring 声明（L12022-12025）一致。标记当前在规范源仅存于 M10.3（L865/L868，全仓 grep 实测），常量 `CONSULT_DRAW_MARKER`（L12018）为唯一 join key。
- **(c) 三消费点 `.get()` 兼容声明**：三处均 `cross_ref_result.get("quote_sync", [])`（L7507/L16264/L22151），且 `check_cross_references()` 在本仓的调用方恰为这三处（全文件 grep 实测：L7500/L16230/L22118 + 测试 9 处）——无第四个绕过消费点；独立 CLI 面 `cmd_check_cross_references` FAIL → `sys.exit(1)`（L22152-22162），面板面计入 `all_issues`（L16266-16267），release 面并入 issues（L7507/L7513）。「兼容 pre-FIX-432 result shapes」的注释理由本身站不住（同模块活调用不可能出现旧形态——见 P3-6），但 `.get` 防御式写法无害且不改变 fail-closed 语义。
- **(d) 常量 join-key 设计**：`QUOTE_SYNC_ADAPTER_MANIFESTS` 六元组（L12010-12017）+ 标记常量仅作匹配键；规则语义唯一存活于 M10.3（注释 L12006-12009 明示并援引 FIX-272 动态锚先例）；六 manifest `exploration_channels.source_of_truth` 回指 M10.3（dsh 实读 L72）——A10「不建平行事实源」成立。
- **(e) AI 专项 5 项**：①mock 残留=无（实读全块，零 unittest.mock/patch 依赖，读真实文件）；②硬编码返回值=无（issues 列表全部由实测检查构造，空列表仅在全通过时；OSError 分支返回 fail-closed 字符串而非静默 `[]`）；③幻觉 API=无（仅 `Path.read_text`/`json.loads`/`re.search`，模块级 import 实证：pathlib L1/re L18/json L21）；④未实现 TODO=无（L12002-12075 无 TODO/FIXME/XXX）；⑤过度实现=无（约 55 行承载两检查+两常量，无投机配置面；六元组硬编码的取舍见 P3-4）。

### 2. sweep 完整性与豁免有效性 — 通过

- **更新 11 处逐处实读**：behavior-protocol.md L1（`M0-M10 强制性规则`）✓；SKILL.md L409（`M0-M10 强制性规则`）/ L441（`M0-M10 强制性行为协议`）✓；commands/governance-init.md L321（`M0~M10`）✓；core/VERSIONING.md L51（`M0~M10 规则的增/删/改`）✓；verify_workflow.py L488（键名 `Behavior Protocol (M0-M10)`）✓；L969 内容锚（`M0-M10 强制性规则`）+ L980 M10 标题锚（`## M10. 主动生态探索协议`）补强 ✓；e2e 面 4 处——e2e SKILL.md L409·L441、e2e commands/governance-init.md L321、e2e CLAUDE.md L57 均 `M0~M10/M0-M10` 新形态 ✓。
- **豁免 10 处逐条评估**（全仓任意分隔符 grep `M0[-–—~～]M9` 复核）：冻结 fixture 4 处（e2e core/VERSIONING.md L51、e2e behavior-protocol.md L1、e2e verify_workflow.py L206·L656——全部位于 `.gitignore` L31 排除的 `project/e2e-test-project/skills/` 下，仍为旧形态=未被触碰，冻结纪元自洽：fixture 内 verify_workflow L656 锚与 fixture behavior-protocol L1 同为旧形态，内部一致）✓；历史记录 6 处（project/references/architecture.md L419·L420、ADR-001 L615、research 快照 L44、review-FEAT-085-DESIGN-R0 L50、review-FEAT-086-DESIGN-R0 L52——均为历史时点事实记述，改写即篡改记录）✓。残留集与 EVD-1316「冻结 fixture 4 + 历史记录 6」披露逐一对号，产品面零残留。test_verify_workflow.py L23115 的 `M0~M9` 为 sweep 自述注释，非滞后引用。
- **锚补强形态**：L969 内容锚随 L1 sweep 联动 + L980 标题锚为新增防护（M10 节被删即 FAIL）——形态合理，非单点。

### 3. F-A5 注记（behavior-protocol.md M10.2 L855）— 通过（附 P2 措辞歧义）

实读 L855：判定=「可跳过」（或「受限」且未发起动作）→ 结果记「无发现」、由「判定」字段消歧、MUST NOT 解释为「探测后无发现」；不增态理由=探测与否已由判定轴表达、增态会制造矛盾组合（判定=需要+结果=未探测）。与既有样本相容性：S3/S4/S5（feat-086-prospective-samples L79-119）三块均为 `判定: 可跳过` + `结果: 无发现` + `# 未发起探测` 注释——注记将其合法化，**主句与 S3~S5 完全相容**✓。但括号短语「（或「受限」且未发起动作）」的严格读法与 S2（判定=受限、动作=无外部调用+本地降级、**结果=被阻止**，样本 L62-68）存在解读张力——见 P2-1。四态枚举（L850）与判定轴无硬矛盾矩阵，注记主张的「消歧」在其限定范围内成立。

### 4. F-5 注记（behavior-protocol.md M0 L9）— 通过

实读 L9：标题后缀（MANDATORY）定位为 M2~M8 历史视觉锚、无规范效力；规范性强弱由 RFC 2119 关键字唯一表达（与 M0 自身 L7 的关键字定义自洽）；显式豁免论证=统一补齐会与条件性条款（M1.2 MAY、EXP-01「可跳过」）冲突且无语义增益。论证成立：给含 MAY/可选语义的节挂 MANDATORY 后缀会制造标题级强度误示，而 RFC 2119 唯一表达性正是 M0 的立节基础；豁免形态（注记声明而非机械统一）与「后缀=视觉锚」的定位一致。落款（FIX-432 / FEAT-086 R0 F-5）可追溯。

### 5. 六 manifest note 标记 — 通过

六平台 note 逐平台实读（claude L70 / codex L74 / gemini L73 / opencode L73 / chrys L72 / dsh L73）：文本逐字节一致，均含 `生成≠咨询` 规范标记 + 出处（canonical rule marker synced from behavior-protocol.md M10.3 + origin review-FEAT-085-DESIGN-R0 F-3）+ 守卫披露（drift-guarded by check-cross-references）。dsh 全文实读：JSON 结构合法（配对/转义/字符串完整），`exploration_channels` 块内 status/mapping/channels 声明与 M10.3 一致（consult 明确排除 draw，L87-88），note 为标注性追加、不改能力声明面 ✓（diff 级「仅 note 变更」依 EVD-1316 机检记录）。其余五平台 JSON 合法性由守卫 `json.loads`（L12065）+ EVD-1316 manifest 1021 一致性机检背书。

### 6. 测试重定价合法性（test_verify_workflow.py L23067-23146）— 通过

- **注释链在位**：FEAT-040→FEAT-041→FEAT-073→FEAT-078→FEAT-084→FIX-432（L23081-23118）逐票递进，「a deliberate edit rides the ticket, the price never moves silently」纪律句贯穿；FIX-432 行明示 +1 B standard / +1 B strict、lightweight 与 thin 不含详细规则节。
- **重定价数值与模板实长一致性**：测试为双重断言（L23136-23139）——`resolved == canonical[profile]`（与 `extract_canonical_templates` 从 commands/governance-init.md 活提取的规范块**内容等价**）且 `len(resolved.encode()) == pin`。该结构使「只改 pin 凑绿」不可行：模板不动（10237B）而 pin 改 10238 → 长度断言 FAIL；模板动而 pin 不动 → 同样 FAIL——**pin 与模板必须同票联动**，蓝军③通道被测试设计本身封死。因果链核验：governance-init.md L321 `M0~M9`→`M0~M10` 净增 1 个 ASCII 字节（+1B）；详细规则节（L319-321）位于 standard/strict 共享基块，lightweight（5221 不变）/thin（2840 不变）不含该节——与 pin 变动面完全吻合。1047 unittest OK 依 EVD-1316（Reviewer 未独立复跑，见未验证声明）。

### 7. e2e 边界纪律 — 通过（附核验形态披露）

- **当前文件态**：e2e 更新面=3 文件 4 处（SKILL.md L409/L441、commands/governance-init.md L321、CLAUDE.md L57——均为机器守卫强制面：fixture-skill byte_copy〔Check 28b〕/ entry-bootstrap-sync）；gitignored fixture 内部件（e2e behavior-protocol.md、e2e VERSIONING.md、e2e verify_workflow.py）仍为冻结旧形态=零触碰 ✓（任意分隔符 grep 实测）。
- **commit 15 文件清单**：Reviewer 无命令通道，未独立枚举 `git show --stat 9a28e4d`——以 EVD-1316 机检记录（15 files = sweep 产品面 + quote_sync 守卫 + 随票重定价 + e2e 守卫面 3 文件）为依据并如实标注；建议 Coordinator 一条命令对号闭合（见 P3-5）。
- **根 CLAUDE.md L57 同步**：已实读确认新形态；其为 `.gitignore` L3 排除的狗粮实例（锁外 1 行），同步由 entry-bootstrap-sync/projection-sync 机检强制（EVD-1316 记录 projection-sync PASS 含根 CLAUDE.md 同步）——与 FIX-011 纪律（先改 canonical 源 commands/governance-init.md → 实例跟随）一致，处置合规。

### 8. 设计一致性 — 通过

- **A10（不建平行事实源）**：引文即 SKILL 行的 spec（守卫比对两侧实文，无第三拷贝）；标记常量=join key；manifest note=出处标注 + source_of_truth 回指。✓
- **A11（轻量载体）**：守卫搭乘既有 `check_cross_references`（子命令 `check-cross-references` 注册实证 L26449/L27360；bp L872 的归属声明属实），零新命令/零新子系统。✓
- **D4（修改纯粹性）**：sweep（FEAT-085 R0 裁定 c 明确留给本票）+ F-4/F-A2 守卫与 F-A5/F-5 注记（FEAT-086 R0 定义、DEC-315 扩承载）+ 随票重定价（测试结构强制同 commit）——全部在票内申报范围，无顺手改。✓
- **向后兼容**：结果 dict 仅增键 `quote_sync`（L12356），旧键未动——既有测试 9 处调用点断言 dangling/deprecated/cycles 不受影响（L1097/L1112 实读模式佐证）；CLI 接口零变更；release/panel/CLI 三面 JSON 形状不变（details["cross_references"]={pass,issues}，L7509-7512）。新增 FAIL 面即守卫本意（fail-closed），已在 EVD-1316 披露。✓

## 蓝军挑战（3 条独立 ID，已执行）

- **BM-1 引文格式微变稳健性（标点/空格/全半角）**：锚行任一字符漂移（含全半角冒号/空格变化）→ 正则失配 → FAIL（fail-closed，报错文案自带「update citation and guard regex together」处置指引）；引文 span 内部双侧重写（同步）→ PASS（正确——同步即合法）；单侧 → FAIL。唯一残余=嵌套 `「」` 场景的非贪婪截断误捕（当前引文无嵌套，理论面）→ P3-2。
- **BM-2 消费点绕过面**：直接调用 `check_cross_references()` 不经面板——函数自身内嵌守卫（L12349-12350），返回 dict 必含 `quote_sync`；绕过只能靠「只读旧三键」的消费方，而本仓 3/3 产品调用点均已消费（全文件 grep 实证），未来消费方有文档化 FAIL 面 + 本次报告的可追溯记录。残余=未来新消费方只读旧键的纪律依赖 → 已由 P3-6 注释问题侧面覆盖（注释应引导读全键）。
- **BM-3 重定价滥用为「改测试凑绿」通道**：本票重定价合法性由双重断言结构封死（内容等价 + 字节 pin 互锁，见核验 6）；+1B 因果链（L321 单 ASCII 字节增量 × 详细规则节仅存在于 standard/strict）与 pin 变动面（10237→10238、11125→11126、5221/2840 不动）精确吻合。无凑绿迹象。
- （附加执行）**BM-4 patched-ROOT 测试下的守卫行为**：既有测试 `patch.object(vw, "ROOT", root)`（test L1094/L1109）下 bp/SKILL 不可读 → 守卫返回 unreadable issue——测试只断言 dangling 故仍绿（1047 OK 自洽）；该形态同时暴露「守卫无专属断言」事实 → 归入 P1-1 证据。

## findings 清单

| # | 级别 | 位置 | 问题 | 修复建议 |
|---|------|------|------|---------|
| F-1 | **P1** | infra/tests/test_verify_workflow.py（缺失面；守卫在 verify_workflow.py L12021-12075） | quote_sync 守卫零 committed 回归测试：grep `quote_sync/_check_quote_sync/CONSULT_DRAW_MARKER` 全测试文件零匹配；三态负向验证仅存于 EVD-1316 会话内手工记录，不可重复执行。未来正则/标记重构若弱化检测，全部机检灯仍绿（正向路径每次 gate 都跑，检测弱化不可见）——违反 P4（测试看护/防护网）与仓库自身 pin-test 纪律（ENTRY_TEMPLATE_CANONICAL_BYTES 注释哲学）。 | 增 `QuoteSyncGuardTests`：①正态（当前仓 → `quote_sync == []`）；②负向三态（patch bp 锚行改写 / patch SKILL.md 触发行漂移 / 移除规范源标记或 note 标记 → 各自 FAIL 且 issue 文案可断言）；可镜像既有 patch.object/read_text 模式（约 30-40 行）。随本票闭合或由 Coordinator 登记遗留计划（附截止）。 |
| F-2 | **P2** | references/behavior-protocol.md M10.2 L855 | F-A5 括号短语「（或「受限」且未发起动作）」严格读法（受限且未发起外部探测 ⇒ 结果记无发现）与既有样本 S2（判定=受限、未发起外部调用、结果=**被阻止**，样本报告 L62-68——被阻止承载 EXP-03 通道阻断事实）冲突：注记未划清「未发起动作」是否含本地降级动作、未保留「被阻止」给通道阻断事实的边界。 | 措辞收紧：如「判定=可跳过，或判定=受限且无阻断事实与本地降级动作时，结果记无发现；存在通道阻断事实时记被阻止（EXP-03 记录义务）」。文本级修订，可随下一张 behavior-protocol 票或本票复审前修正。 |
| F-3 | **P3** | verify_workflow.py L12055-12060 | 标记检查为 behavior-protocol.md **文件级**（`CONSULT_DRAW_MARKER not in bp_text`），报错文案却声称「no longer present in … M10.3」——标记若漂移至其他节，检查仍绿而文案失实。当前标记恰仅存于 M10.3（L865/L868），无现实误报。 | 后续可将检查收窄到 M10.3 节 span（按 `### M10.3` 到 `### M10.4` 切片），或修正文案为文件级表述。 |
| F-4 | **P3** | verify_workflow.py L12040 | 非贪婪 `「(.*?)」` 在引文含嵌套 `「」` 时捕获截断 span；截断 span 若恰为 SKILL 实文子串可假 PASS。当前引文无嵌套，纯理论面。 | 若未来引文需要嵌套引号，改用贪婪匹配到最后一个 `」` 或显式排除法（`([^「」]*)`）；现形态可注释标注该约束。 |
| F-5 | **P3** | verify_workflow.py L12048 | 守卫校验 span **存在于 SKILL.md 任意位置**，不校验「Agent 分发路由表后一行」的位置声明——触发行整行搬迁（文本不变）后 bp 位置描述失实但守卫仍绿。 | 可选强化：正则锚定 SKILL.md 路由表尾行后的行首 `> ` 形态；或接受现状（位置语义由人审+注记承载）。 |
| F-6 | **P3** | verify_workflow.py L12010-12017 | 六 manifest 路径为硬编码元组：新增第 7 平台 adapter 不会自动纳入守卫（guard 静默不覆盖），需手工记得加元组。 | 在 adapters/ README 或 DEC-315 处标注「新增平台 MUST 同步 QUOTE_SYNC_ADAPTER_MANIFESTS」；或后续改为 glob 发现 + 白名单排除。 |
| F-7 | **P3** | commit `9a28e4d`（15 files 清单） | Reviewer 无命令通道，15 文件清单与「未 push」状态未独立复核，仅依 EVD-1316 机检记录；且 15=12 产品文件（6 sweep 面 + verify + test + 六 manifest）+ e2e 守卫面 3 的分解中，e2e SKILL.md/CLAUDE.md 按现行 `.gitignore`（L31/L3）为忽略面——其入 commit 意味着先于忽略规则被 track（合理假设但未证实）。 | Coordinator 复跑 `git show --stat 9a28e4d` 对号 15 文件清单（一条命令闭合）；确认无 gitignored fixture 文件混入。 |
| F-8 | **P3** | verify_workflow.py L7505-7506/L16262-16263/L22149-22150 | 三处注释「.get for backward compatibility with pre-FIX-432 result shapes」理由不实：三消费点均为同模块活调用，pre-FIX-432 形态不可能在进程内出现；真实理由是防御式编码风格。轻微误导后来者（暗示存在版本混布场景）。 | 注释改为「defensive .get; the live call always provides the key」或直接下标访问；与 F-1 测试同票可顺手处理。 |

## 硬门槛自检

- **P0 阻塞问题数 = 0** ✓（findings 表实证）
- **5 维度全覆盖 = 100%** ✓——正确性（核验 1a-1d/BM-1/BM-2/F-4/F-5）、安全性（守卫无注入/无密钥/正则无 ReDoS 面——无嵌套量词歧义、文本 bounded；EXP-04 语境下守卫读仓内文件非外部输入）、可维护性（命名/注释/职责单一/F-3/F-6/F-8）、性能（守卫 2+6 次小文件读、单次调用无循环 I/O，相对 check_cross_references 全仓扫描可忽略）、测试覆盖（核验 6 + F-1 缺口如实计级）。
- **每条发现标注级别 = 100%** ✓（F-1~F-8 均带 P 级）
- **设计一致性检查已完成** ✓（核验 8：A10/A11/D4/向后兼容逐项）
- **AI 代码专项 5 项检查全部完成** ✓（核验 1e 逐项结论）

## 事实依据与未验证项声明

**已验证（本审查实读）**：verify_workflow.py L1/L18/L21/L488/L7500-7513/L955-984/L12002-12075/L12349-12359/L16230-16278/L22112-22162/L26449/L27360；behavior-protocol.md L1-16/L820-894；SKILL.md L352-376/L409/L441；commands/governance-init.md L310-334；core/VERSIONING.md L51；六 adapter-manifest.json note 行（dsh 全文）；test_verify_workflow.py L1085-1124/L23060-23146；.gitignore L1-40；evidence-log L2009-2010（EVD-1316/1317）；feat-086-prospective-samples 全文；review-FEAT-086-DESIGN-R0（格式与基线参照）；全仓 grep（`M0[-–—~～]M9`、`生成≠咨询`、`quote_sync`、`check_cross_references()`、`check-cross-references`）。

**未验证（不作通过依据，如实标注）**：①commit `9a28e4d` 的 15 文件清单与「未 push」——Reviewer 无命令通道，依 EVD-1316 机检记录（→F-7 建议 Coordinator 一条命令闭合）；②1047 unittest OK / injection-budget 4244/6000 / manifest 1021 / check-governance 基线 1 issue / quote_sync 三维负向验证——均为 EVD-1316 会话内机检输出，本审查未复跑；③六 manifest 中 dsh 以外五家的完整 JSON 逐字节解析——由守卫 `json.loads` 逻辑 + EVD-1316 机检背书 + note 行实读；④「note 仅为追加、status/mapping 零变更」的 diff 级主张——依 EVD-1316，当前态一致性已实读佐证。
