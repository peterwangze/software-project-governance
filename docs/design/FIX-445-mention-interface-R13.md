# FIX-445 — R13 限定修订设计：B4 登记数据闭合与三警告规范关闭（DEC-346/347；R12 delta）

```json
{"role":"Architect (producer, not reviewer)","round":13,"scope":"r12_delta_revision_per_dec346",
 "supersedes":"R12 §3.1 max_occurrences/K 字段与 §3.3 ordinal 登记语句、§3.4 C4 计数句、§5.2/5.3 MREG 与目录语义、§8 M2/M4/M9 行、BT-R12-1 checklist 表述、§3.2 两样例值（1536-右、1588-左）",
 "product_implemented":false,"product_authorized":false,"migration_authorized":false,
 "self_approved":false,"implementation_ready":"pending independent R13 review; archival-gate scope expansion unapproved",
 "fix445_status":"blocked (unchanged)"}
```

- **日期**: 2026-10-13（Coordinator 供应）。**唯一写面**：本文件；R12（SHA `d9ecd153…`/238 行）、R11（`5eaf97d0…`/448 行）与两 canonical 产品（`c7d5a01f…`/`60fe5db5…`）经 closeout-check 七件 SHA 全 match 冻结不改。
- **授权（DEC-346 + DEC-347）**：仅本新设计关闭 R12 B4+三 W，冷源机械核对先于同 Reviewer 一次独立 R13；16 总轮保持、墙钟 36h（129600s）；零 R14、零产品/registry 生效/迁移/风险接受。

## 0. 基线与 supersedes 总表

R12 为基线；本文件替换其 supersedes 所列节句，其余（含 R12 §2/§4/§6/§7 与 R11 全部沿用面）原样有效。**不变项重申**：原三行零编辑；完整四任务源非零/hashbytes/latest/zero skipped/RC0；12 攻击与 R8/R9 反例逐例拒绝；GuardG/T2/M5/R3 零改动——**M5 isterm 闭集含 ASCII `.`（hook :726-728）不改**（不为样例迁就）；B3 五 env；CPU27.8/CLI36/434339/32MiB/1500 不重测不放宽；两产品文件边界；原源资格 NOT_ESTABLISHED、迁移权威未授权、产品 64tests/1FAIL 与 CodeR6 BLOCKED/3、健康 18 issues/exit1 全部不改绿。

| R12 finding | R13 响应 | 替换 |
|---|---|---|
| **B4**（两样例值跨 ASCII `.` 违边界函数；schema 无 context 合法性校验；机检仅码点数） | §2：六值机械重切修正（三源互证）+ schema 硬校验（非空 context 禁含 isterm∪pipe 任一字符）+ 登记机检扩为三元组与实际邻接逐字相等 | §2 替换 R12 §3.2 样例与 §5.2 schema 行 |
| **W-R12-1**（MREG「必发」与零 spawn 矛盾；目录语义两写；M9 纯 prose 臂不可达） | §3：诊断所有权分层（bash/engine 两发射层）+ 目录前检升级（exists∧¬regular→bash 层硬断）+ **逐场景矩阵**（异常×路径×层×令牌×判定）+ 竞态收敛性 | 替换 R12 §5.2/5.3 相应句与 M9 |
| **W-R12-2**（归档失活仅 checklist） | §4：**双层机器守卫**——运行时相等守卫（in-scanner，两文件范围内）+ 归档侧机门 SPEC（infra 面扩围**未授权提案**，输入/输出/欠缺-未知-超预算保守拒）+ 残余如实 | 替换 R12 BT-R12-1 |
| **W-R12-3**（`c≤K`=前 K 次非指定出现；ordinal 充 K 连带豁免；预留槽偷位） | §5：**位点语义**取代 K——`live_site_count`（登记时机测真值）+ 运行时 `c(T)==N` 精确相等 + `site_evidence[]` 逐出现裁决（一证不盖多例）+ 实 ordinal>1 含未裁前例**拒登记** | 替换 R12 §3.1 K 字段、§3.3、§3.4 C4 句、M4 推导 |

## 1. 本轮实际输入与事实

**本轮实读 8 件**（零 shell/零执行/零实验/零治理写/零子 agent/零用户交互；未读热面）：

| # | 文件 | 规模 | 要点 |
|---|---|---|---|
| 1 | `docs/reviews/review-FIX-445-DESIGN-R12.md`（SHA `9f739cde…`） | 68 行 | BLOCKED/1（B4）+3W；C-B4 三件与 C-W1/2/3 解除条件 |
| 2 | `docs/reviews/supplement-FIX-445-DESIGN-R12-evidence.md` | 9 行 | context-check 逐格互证；C4 first-K 语义确认；归档≠风险接受 |
| 3 | `.governance/reports/FIX-445-R12-escalation.md` | 45 行 | 四项关闭表；DEC-346 范围依据 |
| 4 | `.governance/incidents/FIX-445-R12-context-check.json` | 62 行 | 六 computed 邻接值（机测）：1536-右=`原门CPU27` mismatch、1588-左=`9FFF与ASCIIalnum/符号集合空` mismatch、余四值 match |
| 5 | `.governance/incidents/FIX-445-R12-closeout-check.json` | 101 行 | 七件 SHA 全 match；review trust CLEAN；locks 0/0 |
| 6 | `.governance/incidents/FIX-445-R13-authorization.json` | 47 行 | DEC-346 范围、`guard_design_boundary`（扩围须呈报未批准）、禁白名单清单、零 R14 |
| 7 | `.governance/reports/FIX-445-R13-budget-checkpoint.md` | 44 行 | DEC-347 墙钟 36h；pwsh25=18 issues/exit1；R12:197 M5 新命中与 Check28u 隔离 witness FAIL（写者 unknown）事实 |
| 8 | `.governance/incidents/FIX-445-R10-source-extract.md`（**重读**） | 27 行 | 三冷原行逐字——本轮 §2.1 机械重切的直接输入 |

**沿用会话上下文 22 源**（R10 三件套、R0 七类、R3 prefix、R5 GuardG、DEC336 helper、R4 escalation、CODE-R6、canonical hook 1284 行/test 1480 行、角色与 SKILL 等；五件经 frozen/closeout 机证未变）。Coordinator 单源事实：goal rev6 active/armed、bridge RUNNING rev4、wall 74912/129600 safe、round 9of16、preflight 18 issues/exit1（EVD1677/1678）、隔离 witness FAIL 写者 unknown 不接受不假恢复。R12 两报告文本与 Reviewer 返件逐字一致零差异（本轮无需转录校准）。**环境事实边界**：R12 设计 ：197 的 M5 扫描命中与 source-verification:234 为冻结历史扫描事实，本设计不改旧件、不据此称健康清零；Check28u 隔离冒烟 witness 为 **FAIL**（写者/完整样本 unknown），本设计不声称该环境问题已修复或通过。

## 2. D-B4 — 六上下文机械重切与登记数据契约

### 2.1 机械重切（canonical isterm 含 ASCII `.`；∪pipe；对重读冷原行逐字符切分）

边界函数（R11 §6.2 沿用，未改 M5）：terminators = `。；;，：,:.！？!?` ∪ `|`。关键事实：ASCII `.` ∈ isterm（`27.8` 小数点、`U4E00..9FFF` 双点均切断 clause）；**`/` ∉ isterm**（斜杠分段不切）。逐行 walk：

- **EVD-1536**：X=`无预算或PASS编造`（char[1148,1158)）。左：上一终结符=交付后 `，` → 左邻=`目标含先设计后twofile修及最终交付`（20cp，无 terminator）。右：X 后 `。` 起，扫至 `CPU27` 后的 ASCII `.`（`27.8` 内）即切 → 右邻=**`原门CPU27`**（7cp）。R12 样例曾写至 `…保持`——跨 `.`，非法。
- **EVD-1587**：X=`已知no-separator当真不能默当获准安全残余`（char[428,454)）。左邻=`onlyR4A封闭允许字符集和对应五变体/控制字符回归`（27cp；三段 `/` 不切 ✓）。右邻=`要具体closedguard`（14cp）。R12 两值本已合法。
- **EVD-1588**：X=`载荷含把将当作当成视为作为当真任token整span拒免`（char[572,600)）。左：`。closed单元whitelist U4E00` 在 `U4E00..` 首个 `.` 处切断 →（空 clause，介于双点）→ 下一 clause 至 X 前 `，` 止 → 左邻=**`9FFF与ASCIIalnum/符号集合空`**（21cp）。R12 样例曾含 `U4E00..`——跨双点，非法。右邻=`sourceC6合法载荷无token`（18cp）。

**三源互证**：本重切（本轮对重读 source-extract 独立推导）= `FIX-445-R12-context-check.json` 六 computed 值（机测）= R12 Reviewer 冷行独立重切（review §2.B4）——逐字一致。

### 2.2 修正后登记样例值（唯一有效参照；登记本身未授权）

| 行 | clause X | left_context | right_context |
|---|---|---|---|
| EVD-1536 | `无预算或PASS编造`（10cp） | `目标含先设计后twofile修及最终交付`（20cp） | **`原门CPU27`**（7cp）✱修正 |
| EVD-1587 | `已知no-separator当真不能默当获准安全残余`（26cp） | `onlyR4A封闭允许字符集和对应五变体/控制字符回归`（27cp） | `要具体closedguard`（14cp） |
| EVD-1588 | `载荷含把将当作当成视为作为当真任token整span拒免`（28cp） | **`9FFF与ASCIIalnum/符号集合空`**（21cp）✱修正 | `sourceC6合法载荷无token`（18cp） |

两修正值仍具区分性（C3 拒断言前缀组合的推导不受影响：攻击左邻 `我确认以下断言且并非引用` 与两修正值均不等）；C4′ 相等守卫为主约束，修正不弱化安全（R12 审查 §2.B4 同判）。

### 2.3 schema context 合法性硬校验（B4 复发免疫）

`registry-schema` 检查新增：**非空 context 不得含 isterm∪pipe 任一字符**（`。；;，：,:.！？!?|`）；空串仅允许出现在「clause 位于行首（无左邻）/行尾（无右邻）」的登记形。违者 `registry-schema` ToolFault（BLOCK）。该闭集字符表与运行时候选边界函数**同一常量**（单一事实源，实现禁复制两份）。

### 2.4 登记机检义务（设计接口；不执行迁移）

登记程序（Coordinator 机器路径，未来经裁决才存在）对每条目 MUST 机检并留回执：①对登记 task 的 live 批机械切分全部候选；②定位 clause==entry.clause 的每个出现；③其 computed 左/右邻接 clause 与 entry.left_context/right_context **逐字相等**；④live 计数 c(T) 与 `live_site_count` 相等（§5）；⑤任一不符 → **拒绝登记**（非降级登记）。回执含六值、区间与计数，入 incidents 冷工件供独立复核。本节为义务规范，**本轮不执行、不创建 registry、不自称迁移就绪**。

## 3. D-W1 — spawn/诊断/目录语义统一（逐场景矩阵，非改词）

### 3.1 诊断所有权分层

- **E-bash**（编排层，`has_unnegated_fabrication_terms` 内）：零 spawn 路径的唯一观测源——发单行 stderr 标记（不入判定流）：`FIX445_MREG=absent` / `FIX445_MREG=notfile`。
- **E-engine**（引擎层）：一切 spawn-armed 运行的权威分类——完整 `FIX445_DIAG … MREG=absent|loaded MVERIFIED= MUNVERIFIED= MSITES=` 行。
- R12 §5.2「DIAG 必发 MREG=absent」的「必发」**限定于 spawn-armed 运行**；零 spawn 路径的 absent 观测由 E-bash 承担——两发射层互斥全覆盖，无静默分支。

### 3.2 目录前检升级（与引擎硬断一致）

bash 预检序列：`[ -e "$REG" ] && [ ! -f "$REG" ]` → **在场非普通文件（目录等）→ bash 层即判 `registry-notfile` 故障 → BLOCK（return 0），不 spawn**，E-bash 发 `FIX445_MREG=notfile`。普通文件在场 `[ -f ]` 真 → 按 R12 §5.3 态 2 spawn（引擎权威分类）；不存在/悬空链接（`-e` 假）→ absent（零 spawn + E-bash 标记）。**目录语义跨路径统一为硬断**（R12「预检 false 类与 absent 同收敛」中目录一项废除）。

### 3.3 逐场景矩阵（异常 × 调用路径 → 判定/发射层/令牌）

| 异常 | P-A：纯 prose+触发（预检分类） | P-B：record 非空（恒 spawn） | P-C：registry 在场+触发（spawn） | 收敛 |
|---|---|---|---|---|
| 不存在/悬空链接 | 零 spawn，惰性零豁免；E-bash `MREG=absent` | 引擎 ENOENT→absent，惰性；E-engine DIAG | 同 P-B | ✓ 同分类 |
| TOCTOU（预检后被删） | —（本路径已零 spawn） | 引擎 ENOENT→absent 惰性；DIAG 可见 | 同 P-B | ✓ |
| **目录（在场非普通文件）** | **bash 层 notfile→BLOCK**（零 spawn）；E-bash 标记 | 引擎 IsADirectoryError→`registry-notfile`→BLOCK | 同 P-B | ✓ **两路同硬断** |
| 权限不可读（普通文件） | 预检 `-f` 真→转 P-C spawn | 引擎 PermissionError→`registry-read`→BLOCK | 同 | ✓ |
| 编码错误 | 同上 spawn | `registry-read`→BLOCK | 同 | ✓ |
| >256KiB | 同上 spawn | `registry-oversize`→BLOCK | 同 | ✓ |
| strict-parse 失败 | 同上 spawn | `registry-malformed`→BLOCK | 同 | ✓ |
| schema 违规（含 §2.3 新校验） | 同上 spawn | `registry-schema`→BLOCK | 同 | ✓ |
| 加载正常 | spawn，按 §4/§5 判定 | DIAG `MREG=loaded entries=N` | 同 | ✓ |

**竞态收敛性**：预检与引擎 open 之间的任何竞态由「最后触达层」给出唯一分类（预检 notfile→被换为普通文件→引擎 loaded；预检 file→被删→引擎 absent；预检 file→被换目录→引擎 notfile）——闭分类终点唯一，不存在双层分歧判定。**M9 修正**：目录/权限/超界/坏件在**全部路径** BLOCK；缺席在全部路径惰性且可见——R12「M9 无条件承诺在纯 prose 臂不可达」消除。

## 4. D-W2 — 双层机器归档守卫

### 4.1 运行时相等守卫（in-scanner；两产品文件范围内）

**C4′（取代 R12 C4）**：令 c(T)=当前 live 批内条目三元组 T 的逐字出现总数（engine 与候选抽取同遍计数，零新增 IO；DIAG 增 `MSITES=<c>`）。任一出现获豁免的必要条件：**c(T) == entry.live_site_count**（精确相等）。双向 fail-closed：

- **纯 append 复本**（无归档）：c=N+1≠N → 该三元组**全部出现**零豁免——原行一并重 BLOCK（fail-loud：攻击者仅能造成显式失败性可用性攻击，无逃逸；「前 K 槽偷位」语义随 K 移除而消灭）。
- **位点流失**（原行被归档/移出 live，无复本）：c<N → 全拒 = **机器强制的失活**——归档不可能静默保留资格（超越 R12 checklist：不需要任何人记得 deactivate，运行时自动失活）。
- **证明义务收窄（对抗核查修正）**：c(T)==N 只证明「live 批内恰有 N 个三元组逐字出现」，**不证明获裁出现仍在其中**——不以数量相等冒充原出现在场证明。
- **不可区分性引理（运行时闭合不可能）**：设原获裁位点被归档移出 live、同三元组未裁复本留存且数恰为 N（偷位场景）。则 live 批在 scanner 可用的一切局部谓词（计数、clause/上下文字节、载体内容——复本逐字复制后均同）下，与「复本即原始获裁出现」的世界**同构**；且约束禁用 hash/ID/整行锚（authorization.json `prohibited_authority_shortcuts`），故**不存在**可在原两产品 scanner 内证明「原出现仍在」的机制。该引理将 M15 从「未找到机制」升级为「运行时层可证不可闭合」。该通道必须由 4.2 归档侧权威不变量切断；**4.2 未授权前为已知开放通道**，如实列为迁移 readiness 阻断项，不伪闭。

### 4.2 归档侧机门 SPEC（infra 面扩围——**未授权提案**，按 authorization.json `guard_design_boundary` 呈报）

触碰点超出原两产品文件范围（`infra/` 治理件），**需用户另裁；本轮零实施**。提案（两触点，可并行）：

- **G1 归档执行门**（候选文件 `skills/software-project-governance/infra/archive.py` 归档执行路径；备选 `governance_store.py` 若归档经其入口）：输入=（将归档 evidence 行集， registry）；对每行做活跃条目三元组匹配；输出=①命中且存在**同票失活/重锚回执**（registry 变更记录带 adjudication 引用且 live_site_count 已经机测更新）→ 放行；②命中无回执 → **拒绝归档**（错误列命中条目与缺失回执）；③registry 缺席但有历史登记痕迹 / 不可读 / 坏 schema（**未知**）→ 拒绝；④命中数超申报（**超预算**）→ 拒绝。全部保守方向。G1 匹配仅按内容三元组（**无 hash/ID/整行名单**——不落入 `prohibited_authority_shortcuts`）；G1/G2 自身信任假设=governance 写面完整性（能直改 evidence-log 的攻击者同样绕过它们——CH-1 级，与现行全部门同界，如实）。
- **G2 一致性检查面**（候选 `infra/verify_workflow.py` 新 Check `mention-registry-consistency`）：输入=live evidence-log + registry；校验每活跃条目 c(T)==live_site_count；不等 → FAIL（捕双向漂移：归档丢失与复本增殖）；registry 未知态 → FAIL。观测面，不阻断提交，但为迁移 readiness 必过项。

### 4.3 残余与就绪条件（具体未解，不伪闭）

由 §4.1 引理：运行时层闭合**可证不可能**；闭合唯一路径=4.2 权威侧不变量（G1 拒无回执归档 / G2 一致性检查），其写面在 infra（两产品文件之外）且**未获授权**——按 `guard_design_boundary` 呈报待裁，不自扩。故当前具体未解=「M15 偷位通道开放」，**implementation_ready 不得成立**（明确阻断项）。4.2 获裁并实现后：M15 攻击链在归档步被拒，通道在「governance 写面完整性」假设下闭合（该假设与现行全部门同界，CH-1 级残余如实保留）。运行时半边（4.1）本身在两文件范围内、可独立实现与测试。

## 5. D-W3 — 位点语义取代 K/ordinal

- **字段**：移除 `max_occurrences`（R12 §3.1）与 ordinal 登记语句（R12 §3.3「按实值登记」——废除）。新增 `live_site_count`（≥1，≤8 sanity 界——非预留语义）与 `site_evidence[]`（长度必须 == live_site_count；逐元素非空且互异——**孤证不盖多例**）。
- **登记程序纪律（机器可检）**：①机测 c(T)；②declared N≠c(T) → **拒绝登记**（N>c=预留未来位，禁；N<c=漏报，禁）；③`len(site_evidence)==N` 否则拒；④**实 ordinal>1 且任一位点无对应裁决证据（存在未裁前例）→ 拒绝整条登记**——不得以 N 自免前 N 个出现；⑤增位仅后置：新出现实际存在并逐个获裁后，经新裁决+机测复核更新 N。
- **运行时闭合**：登记时 N=c 保证相等守卫初值为真值；后继任何漂移（任一方向）被 C4′ 保守拒绝。W-R12-3 三缺陷（前 K 语义/ordinal 充 K/预留偷位）随 K 移除与上述纪律整体消灭。
- **双侧绑定（多槽孤证约束；回应对抗核查）**：「一证不盖多例」同时约束 (i) **登记资格**——纪律③④程序性拒绝；(ii) **运行时**——`registry-schema` 将 `len(site_evidence)≠live_site_count`、元素空/重复列为引擎加载即检硬拒（明文入运行时规范，**不依赖未来 checklist**）。运行时可验的是结构一致性（长度/非空/互异/1≤N≤8）；「证据与当前出现的对应关系」运行时**不可验**（登记程序与 G2 的职责）——不以结构检查冒充对应性证明。
- **移除的 R12 过时声明清单**：§3.1 K 字段与 K∈1..8 预算语义；§3.3「登记 ordinal 以迁移时机检实值为准…按实值登记」；§3.4「C4 即出现实例计数」句；§8 M4 的「复本 #2>K」推导（由 M13 相等语义取代，结论同）；BT-R12-1 的 checklist-only 表述；M9 无条件承诺（由 §3.3 矩阵限定）。「部署自检」保留为迁移票验收步骤之一（MREG 全路径可观测后仍复核 `MREG=loaded`）。

## 6. 更新验收矩阵（delta 行；R12 其余行沿用，M3/M5–M8/M10–M12 换至 C4′ 语义结论不变）

| # | 输入 | 状态 | 预期 | 机制 |
|---|---|---|---|---|
| M2′ | 原三行（零编辑） | 迁移态（六值=§2.2、N=1、机检回执齐） | **PASS** | C1–C3/C5/C6 + C4′（c=1==N；ordinal=1 为登记机检产出，非假设填写） |
| M9′ | §3.3 全场景矩阵 | — | 矩阵逐格（目录/权限/超界/坏件全路径 BLOCK；缺席全路径惰性+可见） | §3 |
| M13 | 同任务新行复本 append（无归档） | 迁移态 | **原行+复本均 BLOCK**（fail-loud） | c=2≠1 → 三元组全拒（取代 M4 推导） |
| M14 | 原行被归档移出 live（无复本） | 迁移态 | 零豁免（机器失活） | c=0≠1 |
| M15 | 已裁原出现被归档移走、同三元组未裁复本留存且数=N（偷位） | 4.2 未授权 | **开放通道**（count==N 守卫设计上盲于此；§4.1 引理=运行时可证不可闭合）——readiness 阻断项，不称已拒 | 4.2 获裁后=归档步被拒（无回执→拒归档） |
| M16 | 登记场景：实 ordinal>1 且证据不足 / N≠c / 孤证多例 | 登记 | **拒绝登记** | §5 纪律①–④（授权面机器闸） |
| M17 | registry 含非空 context 带 isterm∪pipe 字符（如 B4 旧值） | — | `registry-schema` BLOCK | §2.3（B4 复发免疫） |

## 7. 替代方案（标准先列；R11/R12 基线沿用不重复）

**新增预定义标准**：14) 登记数据与边界函数机械一致且三源互证；15) 归档守卫至少运行时半边机器可检，另一半以未授权扩围提案如实呈报；16) 位点语义无预留、无 ordinal 充当已裁数、孤证不盖多例。

| 方案 | 判定 |
|---|---|
| **Alt-1（选定）** §2–§5 组合 | 满足 1–16；开放面如实（M15/readiness） |
| Alt-2 仅修两样例值、不加 schema 校验与机检 | **排除**：B4 存活缺口恰在 schema 无校验（R12 审查 BR3：「按样例登记→M2 假承诺」） |
| Alt-3 运行时保留「豁免前 c 个」三态计数 | **排除**：即 W-R12-3 所禁前 K 槽偷位语义 |
| Alt-4 将 G1/G2 静默并入两产品文件实现 | **排除**：违 authorization.json `guard_design_boundary`（扩围必须呈报另裁，不得自扩 infra） |

## 8. 蓝军挑战（≥3）

| # | 挑战 | 响应 | 残余 |
|---|---|---|---|
| BT-R13-1 | 攻击者以复本 append 触发原行重 BLOCK（可用性攻击/fail-loud 滥用） | 设计接受：可用性向保守；四源门显式失败暴露异常行；攻击者无法借此获免 | 接受的可用性代价（非逃逸） |
| BT-R13-2 | 归档偷位（已裁原出现移走+复本复位 count==N） | §4.1 不可区分性引理（运行时可证不可闭合；不以数量相等证明原出现在场）；§4.2 SPEC（无 hash/ID/整行名单、未知即拒）+未授权呈报；readiness 阻断项 | **开放**（不伪闭；获裁前迁移不可就绪；闭合后仍余 CH-1 级 governance 写面残余） |
| BT-R13-3 | 登记程序被绕过/失当（Coordinator 失误） | §5 机器闸（N≠c、site_evidence 长度/互异、拒登记规则）+ §2.4 六值逐字机检回执（独立可复核）+ 运行时 C4′ 兜底漂移 | 权威面纪律（CH-1 级） |
| BT-R13-4 | schema 校验盲区（isterm∪pipe 之外的非法 clause 形/空串错配） | §2.3 空串仅限行首/尾形；§2.4 机检以实际邻接逐字相等兜底（登记数据必须复现于真实行） | 无已知绕过 |
| BT-R13-5 | 双层竞态产生新分歧 | §3.3 收敛性：最后触达层唯一分类，全部竞态终点入闭表 | 无已知分歧 |

## 9. NFR / 版本 delta

- registry 字节界复核：增 `site_evidence[]`（≤8×短引用串/条目）后最坏条目 ≈2.8KiB×64 ≈ 180KiB < 256KiB——**余量收窄如实标注**（原估 166KiB），超界语义不变。
- 性能：C4′ 计数与候选抽取同遍（零新增 IO）；E-bash stderr 单行轻量；其余沿 R12 §11（缺席零 spawn / 在场一次 spawn / record 现状）。原门不重测不放宽；实现票强制复测含 MSITES/DIAG 面与 §6 界值实测。
- registry schema version 仍 1；R12 形条目（含 max_occurrences、缺 live_site_count/site_evidence）→ `registry-schema` 硬拒（自执行防旧形误用）。
- 回滚不变（revert 两文件 + 删/清 registry；G1/G2 若未来获裁，其回滚独立于本设计面）。

## 10. 限定可行性与未解事实（不伪造可行契约）

1. **静态结论**：在「append-only live 日志 + registry 只经裁决产生 + 六值机检登记 + C4′ 相等守卫」前提下，原三行零改、通用逐次出现资格、已证攻击逐例拒绝三者静态成立（M2′/M3/M13 等）。B4 修正后 M2′ 对三行均可达（R12 审查确认两修正值合法且区分性保持）。
2. **未解/开放（如实）**：①原源资格 **NOT_ESTABLISHED** 维持（R11 §4 scoping）；②迁移与产品实施**未授权**；③M15 归档偷位通道开放直至 4.2 获裁（§4.1 引理：运行时层可证不可闭合，不以数量相等证原出现在场）——**implementation_ready 阻断项**；④ordinal=1 由登记机检产出（live 侧本轮未测，禁读热面）；⑤32MiB/1500 等原门与界值实测为实现票待办；⑥R12:197 与 source-verification:234 的 M5 冻结扫描命中、Check28u 隔离 witness FAIL（写者 unknown）、健康 18/exit1 均为保全事实，本设计不改不称已修。
3. 产品侧全部不变：FIX-445 blocked、64tests/92.738s/1FAIL、CodeR6 BLOCKED/3。静态通过 ≠ implementation ready ≠ 迁移授权 ≠ 产品验收；无自动 R14。

## 11. proposed ADR delta（Coordinator 写回；只出草案）

- **标题**: ADR-FIX-445-R13 — M 腿登记数据契约闭合（六值机械重切+schema 硬校验+机检义务）、分层诊断/目录统一、双层归档守卫（运行时相等+未授权归档门提案）、位点语义取代 K
- **日期**: 2026-10-13
- **背景**: R12 审查 BLOCKED/1+3W（B4 样例跨 ASCII `.`、W-R12-1/2/3）；DEC-346/347 限定修订。
- **决策（proposed）**: 采纳 Alt-1（§2–§5）；R12 其余条款沿用；G1/G2 为未授权扩围提案待裁。
- **备选/排除**: §7；R11/R12 基线沿用。
- **影响范围**: 原两产品文件（运行时守卫/诊断/schema）+ registry 数据面；G1/G2 若获裁另涉 infra/archive.py|verify_workflow.py（未批准）。
- **后续动作**: 冷源机械核对（Coordinator 机件提取 R13 六 context 逐字对比）→ 同 Reviewer 独立 R13 → 用户裁决（迁移三问 + G1/G2 扩围 + M15 通道）。
- **可逆性**: 可逆（§9）。

## 12. 自检与过程披露

- 硬门槛：备选 **4≥2**（标准 1–16 先列）；蓝军 **5≥3**；ADR 字段全；模块无环（C4′ 计数并入既有候选遍历；诊断分层不改依赖方向；G1/G2 为界外提案不入依赖图）；接口输入/输出/故障方向闭表（§3.3/§4.2/§5）；登记数据与边界函数三源互证（§2.1）。
- 红线：零 shell/probe/test/安装/其他 docs 改/治理写/子 agent/用户交互；R12/R11/产品/历史源报告零改（closeout 七件 SHA match 为机源，本轮零 shell 未自测 hash）；未写 registry、未减源 skip、未放宽验收、无白名单/hash/ID/EVD 单行特判、无风险接受、不声称隔离冒烟通过、无自动 R14；不以机器守卫设计冒充实现或风险接受。
- 诚实项：M15 开放通道与 readiness 阻断明示（§4.1 引理=运行时不可闭合，不以数量相等证明原出现在场）；「一证不盖多例」双侧绑定（登记资格+运行时 schema）；ordinal=1 为机检产出非假设；环境 FAIL 事实（隔离 witness/M5 冻结命中）不归本设计不称已修；不得称人类外部资格/DRI 已确认。
- 步数：本轮 read 8 件 + write 1 + readback 1，约 10 步内/32 建议；无发散探索。
