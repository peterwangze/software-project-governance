# FIX-445 设计文档 — DEC-334 有界来源修复：实际来源映射与可实现设计

- **Task ID**: FIX-445（需求源：active-defect——FIX-444 R3 BLOCKED 三残余 B1/B2/B3）
- **角色**: Architect Agent（方案 producer，不自评 APPROVED；Independent Design Reviewer 只读本静止 doc 后正式审查）
- **设计范围**: 只本文件。不改产品两 blob（`hooks/commit-msg` = `8efea9430658b73c3baf481676e455666bd914f7`、`tests/test_hooks.py` = `8efd64da0f28a632179e890a27f4cb4a0494295b`）、不改 installed hook、不改历史 reports/EVD、不写 `.governance/` 状态、不跑 module/scanner/engine。
- **绑定事实（本轮实测）**: 工作区两文件 `git hash-object` = 8efea943…/8efd64da…（与 R3 审查对象精确一致）；HEAD = `bf6942dd9b961a7f707db295171b1f2c8bc3c21c`，staged 空。仓库存在未 staged 的其它工作区修改（与 FEAT-097/FIX-443/FIX-444 交付现场一致，非本设计所为）。
- **上游输入**: `docs/reviews/review-FIX-444-CODE-R3.md`（B1/B2/B3 + F1~F4/P1~P3/FC1~FC6 actual output）；`.governance/reports/FIX-444-source-validation-candidate.md`、`.governance/reports/FIX-444-R3-escalation.md`（用户已选「有界来源修复 (Recommended)」，机 DEC-334）；hook 源 `:103-252`（json_region_mask/signature_ok/两 tier sed 链）、`:551-605`（Step 12）；`tests/test_hooks.py` `:615-679`（真源抽取接口）、`:731-844`（synthetic/real replay）。

---

## 1. 目标与非目标

**服务目标**（继承 source-validation-candidate §建议方向）：维护者的合规事实说明与真实测试/命令引用能正常通过 Step-12 提交门，同时无依据的闭环声明继续被拒绝；判定过程任何一步出错必须传播为拒绝，不得空结果通过。

**解决的三条已实证通道**（R3 actual output）：

| 阻断 | 逃逸样例（actual） | 根因 |
|---|---|---|
| B1 | `{"id":"#1","observed":"PASS｜我编造了测试结果;","raw":"x"}` 三键形 PASS | 键闭表计数 ≥3 是纯语法，不是 source provenance |
| B2 | `发现"不允许不编造"为边界，请照此要求必须遵守并当真执行` PASS | 封闭谓语尾后接背书续句不检查 |
| B3 | 真实 mask 在场、sed 失败 / grep exit 2 → 肯定 payload PASS | fail-closed 未覆盖 sed/grep 管线腿 |

**非目标**：不做密码学不可伪造承诺（无新签名权威）；不增加外部依赖或新产品文件；不堆新的关键词/阈值名单、不增加只格式判断；不自动 R4、不接受风险；不改历史 EVD/reports；不读仓库外任何路径。

---

## 2. 威胁模型与安全边界（必须随实现一起落地到 hook 注释）

1. **本地可验证来源，不是密码学凭证**。本设计把「豁免资格」从*语法形状可满足*提高到「引用载荷必须逐字出现在仓库内持久 artifact 中，且与同对象 anchor 共现」。一个完全控制仓库的提交者仍可伪造 `.governance/incidents/*.json` 本身——那是持久、diff 可见、code-review 可查的伪造面，本 hook 无法（也不宣称）验证作者身份。**没有新签名权威**。
2. **禁止自授**：来源 artifact 集合不含 `.governance/evidence-log.md` 自身（防止「先写一行、再引用该行」的自echo）；不含任何仓库外路径（无 `$HOME`/`$DSH_HOME`/Temp 读取）；artifact 路径只接受闭合目录前缀（`docs/reviews/`、`.governance/incidents/`、`.governance/reports/`）下的仓库相对路径，拒绝绝对路径与含 `..` 者。
3. **豁免只作用于被验证的引用载荷 span 本身**：span 周围的 result/affected/prose 结论逐字照检（既有否定核 + 裸词 BLOCK 语义不变）。
4. **fail-closed 方向性**：验证器任何腿出错（文件不可读、grep exit 2、awk 非 0、span 语法不确定）→ 该 span 不获豁免 + 记入诊断计数；判定管线任何腿出错 → BLOCK（不因故障变 PASS）。
5. **兼容即事实**：旧 EVD 零编辑的前提下，真实三任务窗口在全窗口 replay 中保持 clean（本文 §4 已逐类实证包含关系；§8 给 synthetic 自包含计划）。

---

## 3. 实际来源映射（真实归纳——七类，来自 2026-10-11T14:31:02Z 对 live evidence-log 三任务 26 行含术语行的实际抽取分类；类数由抽取归纳得出，非预定）

> 扫描事实：三任务（FIX-444/FEAT-097/FIX-443）窗口内含 `编造|幻觉` 的 EVD 行共 **26 行**。逐行归类如下；每类给出现存 artifact 路径、真实值/摘要、可验证关系、缺失 provenance 如实标注。
>
> **窗口终态（Coordinator 通知，非本设计重扫）**：evidence-log 终窗已至 EVD-1540/859,733 bytes；新增 EVD-1536~1540 为元数据索引行（无术语技术引用，Coordinator 已独立确认）。分类基线保持 2026-10-11T14:31:02Z 抽取不变——**不为计数重跑全 module/全窗扫描**（成本边界）；DesignReviewer 已 READY 并独立确认 EVD-1463/1481/1483 存在本仓 literal/script/record 可对照旧技术引用，与本设计 §3 的实测映射互证。

### C1 — prose 单否定合规行（19 行，无需引用豁免）
- **实际行**: EVD-1434（jsonkeys=2 → 按现签名门渲染 prose）、EVD-1440~1445（C1-RED~C6-GIT）、EVD-1451~1459（G1/G2/G3-R1~R5）、EVD-1450 中的否定部分。
- **语义**: 术语只出现在 `目标对齐：` 等 prose 的合规否定（「不追加扫描或编造验收」「不编造 harness 真实预算」「未编造」），JSON record 本身不含术语。
- **验证关系**: 由否定核（sed 单否定剥离）直接 PASS；R3-4 冻结窗 replay（61/72/24 行 TOTAL_HITS=0）已实际证明全 PASS。**本设计不改此路径**。
- **provenance**: 不适用（无豁免申请）。

### C2 — 标记+封闭谓语尾的双否定发现引用（6 行，prose 层）
- **实际行**: EVD-1472~1477，真实句子：`…双否定“不允许不编造”已实证escape，必须同票真实修拒；其自然语料不存在理由不能免`。
- **绑定 artifact**: `docs/reviews/review-FIX-444-CODE-R0.md` :18/:49/:54（该发现的原生审查出处）；evidence 行 refs 列列 `docs/reviews/review-FIX-444-CODE-R0.md`（resolvable）。
- **验证关系**: 当前 prose 层标记门（marker+“叠否定”+closed tail `为边界|已实证|是攻击|是逃逸`）剥离后残句无术语 → PASS。**B2 修复后**（§6 R5）：剥离后残句在同级句段内做背书框架核验，`，必须同票真实修拒` 不含背书框架（无 当作/当成/视为/作为/当真 与 真实/事实/数据 的搭配）→ 仍 PASS（§9 矩阵逐字验证）。
- **provenance**: 谓语尾语法 + 原生报告存在；不依赖 artifact 包含（prose 引用类不进 record 豁免通道）。

### C3 — record 层 OLD_PATTERN 正则模式引用（EVD-1463，literal 字段，2 处术语）
- **实际值**: 行内显示形 `OLD_PATTERN='我[[:space:]]*(假设｜猜测｜推测｜估计)｜(大概｜应该｜可能)…｜编造｜幻觉'`（管道为全角显示转义）。
- **绑定 artifact（现存）**: `.governance/incidents/FIX-444-command-records.json` :15（literal 字段含真 ASCII 管道原文 `…(已经|是|可以|完成|存在)|编造|幻觉'`）；同内容另存 `.governance/incidents/FIX-444-old-pattern-replay.sh`。**本轮实测 grep 命中**。
- **可验证关系**: 行内 span `编造｜幻觉` 经显示归一（｜→\|）= artifact 内字节 `编造|幻觉` → 包含 ✓；anchor（id 值 `#1 old-pattern bash replay (defect proof)`，43 字符 ≥16）在 **同一 JSON 对象**（:7 id 与 :15 literal 同对象，本轮实测）✓。
- **provenance 完备**（Temp 原 raw 已不在，但仓内 command-records JSON 为行内声明的权威 literal——EVD 行/R0 报告 :54 双处明示「逐字 literal 以 command-records JSON 为准」）。

### C4 — record 层 check 夹具引用（EVD-1463，literal 字段，另 2 处术语）
- **实际值**: `check \"我编造了测试结果\"`、`check \"本次幻觉结果已通过\"`（行内 `\"` 为显示转义）。
- **绑定 artifact（现存，本轮实测）**: 同 C3 的 `FIX-444-command-records.json` :15——`check \"我编造了测试结果\"\ncheck \"本次幻觉结果已通过\"` 原文在场（artifact 中为 `check "我编造了测试结果"`）；`FIX-444-old-pattern-replay.log` 亦有输出回显。
- **可验证关系**: 归一（\"→"）后包含 ✓；与 C3 同对象 anchor 共现 ✓。
- **注意**: `check "本次幻觉结果已通过"` 本身是肯定形夹具串——**只有包含验证通过才豁免该 span**，正是「载荷豁免、周围照检」原则的实例。

### C5 — record 层判定行序列引用（EVD-1481，observed 字段，6 处术语）
- **实际值**: 行内 `PASS｜double-neg(不允许不编造) ; BLOCK｜不允许编造 ; BLOCK｜无法编造 ; PASS｜并非编造了结果 ; BLOCK｜韩国编造了数据 ; …`（全角 ｜）。
- **绑定 artifact（现存，本轮实测）**: `.governance/incidents/FIX-444-reviewer-R0-command-records.json` :50 observed 字段原文（ASCII `|`）：`PASS|double-neg(不允许不编造) ; BLOCK|不允许编造 ; BLOCK|无法编造 ; PASS|并非编造了结果 ; BLOCK|韩国编造了数据 ; PASS|杜绝一切幻觉 ; BLOCK|multiline-mixed ; PASS|markdown-backtick ; BLOCK|mixed-sanity — all rc=0`。
- **可验证关系**: 归一（｜→|）后整段包含 ✓；anchor id `R3-adversarial-9-cases`（22 字符）在同文件 **同一 JSON 对象**（:43 id 与 :50 observed 同对象，本轮实测 :42-54）✓。
- **provenance 边界（如实）**: 该行 literal 字段是 `<python …>` 压缩占位（真实 driver 全文曾在 Temp `fix444-r0-adv-e8603693\adv_probe.py`，已不在仓库/磁盘）——**对象级全字段包含不可满足，故本设计采用 span+anchor 共现而非整对象包含**；该缺失如实披露，不补造。

### C6 — record 层归因摘要引用（EVD-1483，observed 字段，4 处术语，全角原样）
- **实际值**: `BARE count=4 (OLD_PATTERN citation 编造｜幻觉 pair + check-quoted 我编造了测试结果 / 本次幻觉结果已通过)`。
- **绑定 artifact（现存，本轮实测）**: `FIX-444-reviewer-R0-command-records.json` :77 observed 原文**全角原样包含**（artifact 本身用全角 ｜）→ 原文直探即中，无需归一 ✓；anchor id `R5-per-row-attribution (python equivalence — supplement, not substitute)` 同对象 ✓。
- **provenance 完备**（同文件 R5 记录对象）。

### C7 — 仓内脚本+哈希+数值引用（EVD-1450，无 JSON record）
- **实际值**: `python D:/…/.governance/incidents/FEAT-097-budget-metrics.py`；UTC/exit；`median0.00290000753ms、max0.26650000655ms PASS，sourceSHA256b52313b742808e53441a035952e57c56bc85c45edc305d4381fc23cecdb2e773`；结果 artifact `FEAT-097-budget-metrics-result.json`。
- **可验证关系（本轮实测）**: 脚本与 result.json 均现存于仓内 ✓；**但 `sourceSHA256 b52313b7…` 与今日 `budget-metrics.py` 实测 SHA256（`9974dbe0…`）及 `loop_runtime_claims.py` 工作区 SHA256（`5c991a40…`）均不匹配**——该哈希指称测量时点的历史源状态，今日不可复验。**如实标注：哈希 referent 不可解析**。
- **保守处理**: 本行术语均为 prose 否定（C1 路径），不申请豁免 → 不受影响；设计规则 R3 规定：**未来任何行若以哈希引用申请豁免，哈希今日不可复验 → 拒绝豁免**（不补造历史状态）。

### 机器写入 op-id（非证明；可选诊断——**非本段授权范围，实现可整体略去**）
EVD-1450/1472/1481/1483 等行尾带 `（机器写入：governance-store evidence-append op-<32hex>；schema v1）`。本轮实测 `.governance/governance-store-ops.json`（16,369 行 ledger）中 `op-2ec8f74a…`（EVD-1450）、`op-610c01e4…`（EVD-1472）、`op-523b7ce7…`（EVD-1490）均在场且含 command/task_id/recorded_at。**设计立场：op-id 单独不构成证明（record 标签不视证明——任务红线）；本段未授权新签名/账本架构——上述仅为对既有文件的只读观察记录，不进任何判定路径（§5 R1 的豁免判定不含 ledger 读取）**；如未来票授权，可作为诊断面板的正信号，缺场不判负。

---

## 4. 架构设计

### 4.1 模块划分（每模块职责 ≤3 句；依赖单向无环）

```
Step 12 (hook :551-605, 不改结构)
 └─ has_unnegated_fabrication_terms "$TASK_EVD_LINES"     [M0 编排]
     ├─ json_region_mask prose|record                      [M1 既有，保留]
     ├─ verify_citation_provenance <record> <row> <task>    [M2 新增]
     │   ├─ extract_candidate_spans (M2a 闭语法抽取)
     │   ├─ build_artifact_corpus (M2b 闭合目录+refs+task-glob)
     │   └─ probe_containment (M2c span+anchor 同对象共现)
     ├─ strip_verified_spans (M3 bash 字面替换，只删已验证 span)
     ├─ scan_residual (M4 否定核+裸词，逐腿 rc 区分)          [既有语义+R6]
     └─ endorsement_frame_check (M5 背书框架，仅 C2 剥离后残句)
```

- **M0 编排**（改造 `has_unnegated_fabrication_terms`）：按 prose→record 两 tier 顺序调用，收集每腿退出码，任一腿错误 → return 0（BLOCK）；无命中且无错误 → return 1（PASS）。
- **M1 json_region_mask**：**不改**。签名门（≥3 闭表键、真键位、字符串外）保留为 record 路由的**必要条件**——它区分机器记录形与任意包裹（n1/n8/F4 继续走 prose），但**不再是豁免的充分条件**。
- **M2 verify_citation_provenance**：输入 record 文本 + 所在 EVD 行 + TASK_ID；输出「已验证 span 列表 + 未验证计数 + 错误计数」。闭语法抽候选、建 artifact 语料、逐 span 做包含+anchor 共现探测；一切不确定 → 该 span 未验证。
- **M3 strip_verified_spans**：只对已验证 span 做字面 `${text//"$span"/}` 删除（bash 引号形=字面，无正则元字符问题）；删除次数与探测次数一致性校验（不一致 → 视为错误 → BLOCK）。
- **M4 scan_residual**：对剥离后残文执行现行否定核 sed 链 + `grep -Eq`——但每腿显式 rc 区分（R6）。
- **M5 endorsement_frame_check**：对 C2 类 prose 剥离点之后的同级残句做封闭背书框架匹配；命中 → 撤销该次剥离资格（术语重回扫描 → BLOCK）。

### 4.2 关键接口契约（bash 函数，两文件内实现）

```bash
# M2 — rc: 0=正常完成(无论验证成败)；非0=验证器自身错误(→BLOCK)。
# stdout: 每行一个已验证 span 的原文字面（供 M3 删除）。
# stderr: 诊断计数 UNVERIFIED=<n> ERRORS=<n>（进 BLOCK 面板提示）。
verify_citation_provenance <record_text> <full_row> <task_id>

# M2c — rc: 0=contained(span+anchor 同对象)；1=not contained；2=probe 错误。
probe_containment <span_literal> <anchor_literal> <artifact_file>

# M5 — rc: 0=发现背书框架(撤销豁免)；1=无框架；2=错误(→BLOCK)。
endorsement_frame_check <residual_clause>
```

**错误码语义（全管线统一）**：探测/读文件/grep 的 rc 2（真错误）与 rc 1（无匹配）必须区分；rc 2 → 该 span/该腿按失败处理（豁免拒绝或整体 BLOCK），**永不**把错误当「无术语」。

---

## 5. 判定规则（Normative）

### R1 — 签名门降级为路由必要条件
`{...}` 对象仍需 ≥3 闭表键（M1 原样）才进 record tier；未签名/未闭合包裹渲染 prose（prose 无任何 call/verdict 豁免——n1/n7/n8/F4 语义保持 BLOCK）。op-id/ledger 不进本规则（见 §3 末节——非授权范围）。**键数/键名/record 标签均不单独授予豁免**。

### R2 — 候选 span 闭语法（只此四类，封闭表）
1. 判定行：`(PASS|BLOCK)｜[^;]{1,120};?`（含全角 ｜ 形）
2. check 调用：`check "[^"]{1,120}"` / `check \\"[^\\"]{1,120}\\"` / `check-quoted [^;)]{1,120}`
3. 模式对：`编造\|幻觉` / `编造｜幻觉`
4. （C2 prose 类不进本通道——由 M5 单独治理）

超出闭语法或长度上界的携带术语片段**不是候选**——按裸词进入 M4 扫描（未知形=拒绝，fail-closed）。

### R3 — 包含验证（span + anchor 同对象共现）
- **归一映射（封闭，仅用于探测比较；删除时用原文形）**：探测顺序 ①span 原文直探 → ②`｜`→`|`、`\"`→`"` 归一形再探。两次皆 rc1 → 未验证。
- **anchor 规则**：span 所属 record 对象中取**另一个**长度 ≥16 的字符串值（优先 id/kind/literal 片段）；无合格 anchor → **拒绝豁免**（保守：F1/F2/F3 的 `#1`/`x` 短值即落此）。anchor 与 span（归一后）必须在**同一 artifact 的同一顶层 JSON 对象**内共现（awk 花括号深度切分 slurp 文本后 index() 判定——M1 已有同型机制）。
- **artifact 语料（闭合构造，≤32 文件）**：①本 EVD 行内出现的 `docs/reviews/[A-Za-z0-9._-]+` 与 `.governance/(incidents|reports)/[A-Za-z0-9._-]+` 路径（≤8）；②`.governance/incidents/*${TASK_ID}*` glob（≤24）。路径含 `..`/绝对形 → 丢弃并计错误。**不含 evidence-log.md 自身、不含任何仓库外路径**。
- **哈希类（C7 形）**：行以 `sourceSHA256<64hex>` 申请豁免时须对 refs 所指仓内文件今日重算匹配；不可复验 → 拒绝豁免（EVD-1450 的历史指称如实披露，不追溯）。

### R4 — 豁免作用域
仅被验证 span 的字面从 record 文本删除（M3）；record 其余值、result/affected/prose 尾注全部进入 M4。M4 命中裸 `编造|幻觉`（否定核不覆盖）→ BLOCK，面板附诊断：未验证 span 计数 + 前三个 span 摘要（各 ≤40 字符）+ 提示「引用需可溯源至 incidents/reports/reviews artifact 原值」。

### R5 — 背书框架（B2 修复；作用于 C2 剥离后同级残句）
- **作用域**：自标记+封闭尾剥离点起，至下一个 `。；;` 或行尾（同级句段）。
- **封闭框架（运算符×宾语的搭配，非词单堆叠）**：
  - 框架1：`(把|将)[^。，；“”"]{0,32}(当作|当成|视为|作为)[^。，；“”"]{0,12}(真实|事实|数据|结果|有效)`
  - 框架2：`(当作|当成|视为|作为)[^。，；“”"]{0,12}(真实数据|真实结果|事实)`
  - 框架3：`当真`
- **语义**：残句命中任一框架 → 该次 C2 剥离资格撤销 → 叠否定词强制裸词 → BLOCK（未知残句形不默认通过：框架检查后残句仍须经 M4 术语扫描——无术语且无框架 → PASS，与现行语义一致）。
- **兼容实测**：EVD-1472 残句 `，必须同票真实修拒` / `；其自然语料不存在理由不能免` 无任一框架（无 当作/当成/视为/作为/当真）→ 保持 PASS；P1（`…当真执行` 命中框架3）、P2（`把结果当作真实数据` 命中框架1）→ BLOCK。

### R6 — 管线腿错误传播（B3 修复）
`printf | sed -E … | grep -Eq` if 语境（hook :227-236/:241-251 现状）改为显式分腿：
```bash
stripped=$(printf '%s\n' "$prose" | sed -E -e … 2>/dev/null); sed_rc=$?
# sed_rc!=0 → BLOCK（sed 对未匹配输入恒 0；非 0 即真错误）
printf '%s\n' "$stripped" | LC_ALL=C grep -Eq "编造|幻觉"; grep_rc=$?
# grep_rc: 0=命中→BLOCK; 1=干净; ≥2=错误→BLOCK
```
同型改造覆盖：prose 腿、record 残文腿、M2 全部 grep/awk 腿（含 M2c 的 rc 2 区分）、M1 既有守卫（`|| return 0` 与空 prose 守卫保留不动）。**FC5/FC6 注入位（sed return 1 / grep return 2）在 fixture 桩替换下必须 BLOCK**。

### R7 — 缺来源的保守处理
artifact 缺失/不可读/语法不确定/anchor 缺失/哈希不可复验 → 一律**只拒绝豁免**（不崩溃、不空放行）；若因此残文含裸术语 → BLOCK + 具体诊断。诊断措辞模板进 BLOCK 面板（区分 `provenance-missing` 与 `probe-error` 两因）。

---

## 6. 两文件实现可行性（无新增产品文件/外部依赖/runtime artifact 写）

**`skills/software-project-governance/infra/hooks/commit-msg`**：
- M2/M3/M5 为新增 bash+awk 函数（awk slurp+深度切分+index 共现，与既有 signature_ok 同风格；bash 字面替换用引号形参数展开）；M0/M4 改造现有函数；M1 不动。GNU grep/sed/awk/bash 既有依赖，零新增。Step-12 调用点结构不变（:590-591）。
- 预估 diff：+180~240 行（含威胁边界注释块——§2 五条必须进源码注释）。

**`skills/software-project-governance/infra/tests/test_hooks.py`**：
- 真源测试接口沿用既有 `_extract_*_fn` 正则抽取模式（:655-679 先例），新增 `_extract_provenance_fn`；**fixture 自包含升级**：temp repo 内写 `evidence-log.md` + 迷你 `incidents/` artifact 文件（含被引用 span+anchor 原值）——正常 fixture 不依赖本用户私有日志。
- 新增红绿测：F1/F2/F3/P1/P2/FC5/FC6 先红后绿；span-不包含/anchor-缺失/探针错误/路径逃逸/自echo 拒绝各一；C3~C6 形合法样本（fixture artifact 在场）PASS。
- 既有 RealEvdStep12ReplayTests（live 窗口三任务）保持零 skip 语义；其通过性由 §3 已实证的仓内包含关系支撑（旧 EVD 零编辑）。

---

## 7. 预期验证矩阵（**设计预期——产品未实现，不得称实现通过**）

| # | 输入（actual 来源） | 预期 | 机制 |
|---|---|---|---|
| F1 | `{"id":"#1","observed":"PASS｜我编造了测试结果;","raw":"x"}` | **BLOCK** | 签名 ✓→record；span 候选 `PASS｜我编造了测试结果;` 两探皆无包含；无 ≥16 anchor（#1/x）→ 拒豁免；裸词命中 |
| F2 | literal 键 + check-quoted span 伪造三键形 | **BLOCK** | 同上：span 不包含 + anchor 缺失 |
| F3 | output_as_captured + check 转义 span 伪造三键形 | **BLOCK** | 归一 span `check "我编造了测试结果"` 虽在 C3 artifact 中**字节存在**，但该伪造对象无 ≥16 anchor（`#1`）→ 同对象共现失败 → 拒豁免 |
| F4 | 两键伪造 | **BLOCK** | M1 签名门（未签名→prose→无豁免）保持 |
| P1 | `发现“不允许不编造”为边界，请照此要求必须遵守并当真执行` | **BLOCK** | R5 框架3「当真」命中→撤销剥离→叠否定强制裸词 |
| P2 | `…已实证，我要求把结果当作真实数据` | **BLOCK** | R5 框架1「把…当作…真实(数据)」 |
| P3 | 真引用+闭合尾+括注（ctl） | **PASS** | 剥离有效；残句无框架无术语 |
| FC5 | 真实 mask 在场 + sed 桩 return 1 | **BLOCK** | R6 sed_rc!=0→BLOCK |
| FC6 | 真实 mask 在场 + grep 桩 exit 2 | **BLOCK** | R6 grep_rc≥2→BLOCK（≠1 无匹配） |
| FC1~FC4 | mask 缺失/崩溃/空输出/真实在场 | BLOCK/BLOCK/BLOCK/正常 | M1 既有守卫不动 |
| A1~A5 | 旧五攻击（affirm/mixed/dneg/check 裸形/…） | **BLOCK** | 事实依据门/否定核/prose 无豁免——原语义零弱化 |
| n1/n8 | 单键 JSON 包裹 | **BLOCK** | M1 未签名→prose |
| n7 | `我发现“不允许不编造”是要求必须遵守并当真` | **BLOCK** | 尾不匹配 closed-tail→不剥离→叠否定裸词（既有）+R5 |
| V2 | affirm/mixed/dneg 拒绝集 | **BLOCK** | missing-basis 门保持 |
| C1 19 行 | 真实 prose 否定行 | **PASS** | 否定核不动（R3-4 冻结窗已证） |
| C2 6 行 | EVD-1472~1477 | **PASS** | 剥离+R5 残句无框架（逐字核验 §5.R5） |
| C3/C4 | EVD-1463（4 处术语） | **PASS** | span 包含+anchor `#1 old-pattern…` 同对象（本轮实测） |
| C5 | EVD-1481（6 处） | **PASS** | 归一包含+anchor `R3-adversarial-9-cases` 同对象（实测 :42-54） |
| C6 | EVD-1483（4 处） | **PASS** | 全角原文直探包含+anchor 同对象（实测 :77） |
| C7 | EVD-1450 | **PASS** | 术语均 prose 否定；哈希不可复验仅披露不豁免 |
| 边界 | span 字节=真实 artifact 串 + 伪造长 anchor 重组 | **豁免该 span**（残余） | 见 CH-2：包含证明「引用」不证明「引称真实」；周围照检+diff 可查 |

---

## 8. 兼容计划（旧 EVD 零编辑 + clean clone）

1. **旧 EVD 不改**：C3~C6 的豁免全部由**现存仓内 artifact**（`FIX-444-command-records.json`、`FIX-444-reviewer-R0-command-records.json`）的实测包含关系支撑——旧行文字零改动即维持全窗 clean；C1/C2 走不动/微调路径（§7）。
2. **clean clone synthetic**：fixture repo 自带迷你 `incidents/*.json`（含 span+anchor 原值）；EVD-9003/9005/9006 升级为引用该迷你 artifact（fixture 行文与 artifact 同源生成，一次写入两处）——不依赖本用户日志/私有 Temp。
3. **canonical helper 真源测试接口**：全部新函数经 `_extract_*_fn` 正则从 shipped hook 抽取后 eval（既有 :655-679 模式）——测试永不复制实现体。
4. **live 窗口 replay**：保持三任务零 skip 断言；其 green 的依据是本文 §3 的实测映射（Reviewer 可独立复核 artifact 与包含关系）。
5. **降级/回滚兼容**：见 §11。

---

## 9. 已考虑的替代方案（≥2，含排除理由）

| 方案 | 要点 | 排除理由 |
|---|---|---|
| **A1（选定）span 包含 + anchor 共现验证** | §4/§5 全文 | ——（选定：全部三类阻断闭环、兼容实测、两文件可实现） |
| A2 行级机器签名链 | governance-store 对每条 EVD 行签名，hook 验签 | **新签名权威**——任务边界明示「没有新签名权威」；需改 governance-store+install 面，超出两文件有界段；密钥管理引入新风险面。排除（可作未来票） |
| A3 record 豁免降级为告警+人工门 | R3 报告选项 c | 合法来源（C3~C6）全部退化为人工确认——违背「合法来源要过」的服务目标；自动化回归面消失；不解决 B2/B3。排除 |
| A4 语义/LLM 判定 | 小模型或规则引擎判语义 | 外部依赖+不确定性判定违反 fail-closed 与零依赖边界；不可审计。排除 |
| A5 纯闭语法加固（无 provenance） | 只加 span 长度/结构约束 | 语法形仍可自满足——B1 根因未动；已由 R0→R3 四轮证明此路线收敛到「堆名单」。排除（其闭语法思想被吸收进 R2/R5） |

---

## 10. 蓝军挑战（≥3，含缓解）

- **CH-1「artifact 伪造」**：提交者自写 `.governance/incidents/x.json` 含目标 span+anchor。**缓解/接受边界**：威胁模型 §2.1 明示——非密码学承诺；伪造物持久、diff 可见、review 可查；hook 面板诊断让「豁免来自哪」可追溯。残余如实披露，不称不可伪造。
- **CH-2「真串重组」**：攻击者逐字复制真实 artifact span + 复制真实长 anchor 组装最小 record。**缓解**：同对象共现要求迫使两元素来自同一真实对象；重组结果≈引用了真实记录的真实两个字段——豁免仅限该 span，周围结论照检；行为上与合法引用不可区分是本设计的**声明边界**（§7 末行）。可选收紧（未来）：要求 span 所在值整体包含。
- **CH-3「性能/DoS」**：行长×span 数×artifact 数组合爆炸。**缓解**：R2 长度上界（120 字符）、语料上界（32 文件）、anchor 单探测；grep -F 固定串+awk index 均线性；实测窗口最大行 4272B（EVD-1463）/26 含术语行——量级毫秒级。上限超界 → 保守拒绝豁免（R7），不无限扫描。
- **CH-4「显示转义漂移」**：future 行用新转义形（如半角引号直接入表）导致归一映射失配。**缓解**：归一映射封闭且双向探测（原文→归一）；失配仅致「拒豁免」（保守方向）；fixture 测试钉死两种形。
- **CH-5「grep 版本差异」**：BSD/GNU grep rc 语义差异。**缓解**：GNU grep 为既有依赖（hook 已依赖 GNU sed -E/timeout 等）；测试矩阵在 Git-bash（真 bash，既有 _BASH 路径）跑；rc≥2 统一按错误→BLOCK，方向安全。

---

## 11. 非功能需求覆盖与回滚

| NFR | 措施 |
|---|---|
| 性能 | §10 CH-3 上界三重封顶；单行毫秒级；模块全量回归预算维持 ~103s 级 |
| 安全 | §2 五条边界进源码注释；路径逃逸拒绝；无仓库外读；无自授 |
| 可维护性 | 闭表（span 语法/归一映射/背书框架/目录前缀）集中一处+逐表注释因果；扩展需同步溯源（延续 FIX-239 纪律） |
| 可测试性 | 每规则至少一红一绿；真源抽取接口；故障注入只改隔离 fixture 依赖函数（不卸系统工具） |
| 可移植性 | bash/awk/grep/sed GNU 既有集；LC_ALL=C 字节模式（FIX-239）沿用 |

**回滚方案**：产品两文件单 commit 承载（D4）；回滚 = `git revert` 该 commit（旧 EVD 未动、incidents artifacts 未动、无 runtime 写、无安装面变更——revert 后 hook 回到 R3 blob 8efea943… 状态，Step-12 门恢复 R3 语义）。设计本身不产生需清理的持久面。**可逆性：可逆**（无数据模型/格式迁移）。

---

## 12. ADR（proposed——Coordinator 写回 decision-log）

- **标题**: ADR-FIX-445 引用豁免从语法签名改为仓内 artifact 包含+anchor 共现验证
- **日期**: 2026-10-11
- **背景**: R0→R3 四轮证明：键数/键名/引号形/check 形等语法条件均可被作者自满足（B1）；封闭谓语尾不约束尾后背书（B2）；mask 层 fail-closed 未覆盖 sed/grep 腿（B3）。用户裁决 DEC-334 选择有界来源修复。
- **决策**: 采纳 A1——签名门降级为路由必要条件；豁免必要条件=闭语法 span 在闭合目录 artifact 集内的同对象包含+共现；B2 用封闭背书框架撤销机制；B3 用逐腿 rc 区分传播。
- **备选方案/排除**: §9（A2~A5）。
- **影响范围**: `hooks/commit-msg`、`tests/test_hooks.py` 两文件；Step-12 门语义；无其它门弱化（事实依据存在性/推测模式/review 门零触碰）。
- **后续动作**: Developer 按 §5/§6 实现（先红后绿）；Independent Design Reviewer 审本 doc；通过后同 Reviewer 代码审查链重启（新轮次，非 R4）。
- **可逆性**: 可逆（§11）。

---

## 13. 诚实披露与残余（不risk-accept，逐轮报告）

1. EVD-1450 `sourceSHA256 b52313b7…` 今日不可复验（实测两候选文件均不匹配）——按历史指称披露，豁免规则对其保守。
2. EVD-1481 行内 literal 为压缩占位（原 Temp driver 已不在）——anchor 机制即为该现实设计；对象级全包含不可满足，如实说明。
3. 本设计**不是**不可伪造承诺：CH-1/CH-2 为声明边界内的残余。
4. R2 的七类为真实归纳（26 行实测）；未来新引用形出现 → 按未知=拒绝处理，扩展闭表需新票+溯源。
5. 步数预算：本设计在派发建议 18 步预算内收口（来源精读+只读验证探针+成文+补注+自检返回）；未发生无界探索，未为计数重跑 module/全窗扫描（终窗事实按 Coordinator 通知记录，未自扫），未跑模块/scanner/engine，未写任何 `.governance`/产品文件。缺源与不可复验项（C5 占位 literal、C7 哈希 referent）已标待验证/具体缺口，由 DesignReviewer 以实际规则反例评估，Designer 不反复自证全攻击。

---

## 14. 本设计过程只读命令收据（逐条：literal 要点/UTC/exit/保护）

| # | 命令要点 | start(UTC) | end(UTC) | exit | 影响/保护 |
|---|---|---|---|---|---|
| X1 | `git hash-object` 两目标 + `git rev-parse HEAD` + `git status --porcelain` + 文件 Length | 14:30:41Z 前后（会话批次） | 同批 | 0 | 纯只读；确认 8efea943…/8efd64da…/bf6942dd…/staged 空 |
| X2 | python 只读分类脚本（读 evidence-log，26 行含术语行归类）经 pwsh here-string 管道 | 2026-10-11T14:31:02.7409080Z | 14:31:02.8144583Z | 0 | 纯只读；控制台中文显示 GBK mojibake（显示边界，分类列有效——R0 EVD-1483 同已知现象） |
| X3 | `Get-FileHash SHA256` budget-metrics.py | 14:34:51.1554840Z | 14:34:51.1720121Z | 0 | 纯只读；=9974dbe0… ≠ b52313b7…（EVD-1450 指称披露） |
| X4 | `git hash-object`/`Get-FileHash` loop_runtime_claims.py（工作区+HEAD 内容） | 14:35:31.8727723Z | 14:35:32.0291083Z | 0 | 纯只读；=5c991a40…/blob d2162ac4… ≠ b52313b7… |
| X5 | grep 只读 ×6（R0 报告/两 command-records/evidence-log/governance-store-ops/evidence 行） | 批次内 | 批次内 | 0（rg exit 0） | 纯只读；包含关系与 op-id 在场实证 |
| — | read 工具只读 ×8（architect.md/SKILL/R3 报告/两 reports/hook :1-70/:95-294/:545-619/test :615-679/:700-898/incidents :40-57 等） | 批次内 | 批次内 | n/a | 纯只读 |

未执行：git commit/add/push、任何 install、任何 `.governance` 写、任何仓库外写、任何真实环境操作（无三选一需求触发）。未知项：X1 批次未逐条采集独立 UTC 戳（会话工具批处理）——按批次时间如实标注，不补造精确戳。

---

## 15. 范围变化报告

无。设计在派发边界内完成：只本 doc 新增；无产品/治理状态写；无模块/scanner/engine 执行；探针仅只读分类与哈希计算（无五 env 隔离需求——零写零执行侧产品）。若 Reviewer 要求修订：另出新 doc 版本，不改本文件（hashbound 静止后由 Coordinator 绑定）。
