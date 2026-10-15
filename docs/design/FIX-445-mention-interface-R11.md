# FIX-445 — R11 限定来源绑定提及接口设计（DEC-344 授权范围 · 待独立 R11 审查）

```json
{"role":"Architect (producer, not reviewer)","round":11,"scope":"prose_mention_source_binding_interface_design",
 "authorization":"DEC-344 (design + independent R11 review only)","product_implemented":false,
 "product_authorized":false,"self_approved":false,"fix445_status":"blocked (unchanged)",
 "registry_migration_authorized":false,"implementation_ready":"pending independent R11 review"}
```

- **日期**: 2026-10-13（Coordinator 供应，非本角色时钟）
- **唯一写面**: 本文件。产品两文件、全部历史设计/审查/报告、`.governance/` 记录零写入。
- **审查状态**: 本设计**未经独立审查**。按 DEC-344，随后必须由独立 Design Reviewer 以原 R10 报告/补核/校准三件套 + 本文件为强制输入执行 R11 审查（账本 max10+1，不重置）。本文件任何内容不得自授 APPROVED。

---

## 0. 授权边界与不变项（先于一切设计论证）

授权包含（DEC-344，`.governance/reports/FIX-445-health-resume-20261013.md:50-57`）：同 FIX-445 的 prose/mention 来源绑定**接口设计文档** + 独立 R11 审查；设计必须明确来源资格、完整载荷与 occurrence 边界、raw-slice 映射、strict JSON 故障语义、与 M5/Guard G 的显式交互；W1 语料分配规范并入设计。

授权不包含：产品写入/实施；减源/skip；改历史 EVD/审查报告/冻结分析；新签名权威、hash/ID 白名单、sidecar/报告自授；验收放宽；自动 R12。以下原门**全部保持**且本设计不得削减：

| 不变项 | 锚点 |
|---|---|
| 完整 EVD-1587（及 EVD-1536/1588）零编辑；四任务源非零/hashbytes/latest/zero skipped/RC0 | `reports/FIX-445-R10-contract-decision.md:74`；`session-snapshot` 冻结事实（Coordinator 供应） |
| 全部已证攻击逐例拒绝（12 攻击 + R8/R9 命名反例） | 同上；`review-FIX-445-CODE-R6.md:18` |
| B3 保护（五 env/禁绝对 tmp/禁 fallback/准入前置）与性能资源门 CPU27.8s/CLI36s/434339 semantic/32MiB/1500 | 同上 |
| 现 T2 / Guard G / M5 规则**不得默扩豁免** | DEC-344；`reports/FIX-445-health-resume-20261013.md:53` |
| 两产品文件边界（`hooks/commit-msg` + `tests/test_hooks.py`） | `review-FIX-445-CODE-R6.md:6` blob 绑定 |
| inherited 64 tests/92.738s/1FAIL、Code R6 BLOCKED/3、W1 未裁决——全部保持失败/未解 | `reports/FIX-445-R10-contract-decision.md:12` |

**本设计的核心诚实声明**：本设计交付的是可独立审查的接口契约；它**不**因成文而使 FIX-445 任何验收项通过。第 13 节给出精确的现实兼容结论：在当前授权状态（registry 空/缺席）下，本接口部署后与现接口**判定等价**——原三行仍 BLOCK、全部攻击仍拒绝；使原三行 clean 需要一项**另行裁决的 origin 迁移**（第 6.4/13 节给出具体 schema 与安全代价，未授权、未实施、本文件不催促实施）。

---

## 1. 目标与预定义评价标准

**服务目标**：在保留完整原始证据行（零编辑）、全部已证攻击拒绝、现有 T2/Guard G/M5/来源授权/性能资源门不削弱的前提下，定义一个**可独立审查**的普通正文（prose）来源绑定提及接口，使"来源资格"从不可判定变为：机器可验证的必要条件 + 明确披露的裁决权威面。

**预定义评价标准**（先于第 9 节替代方案比较，沿 R10 §5 并按 DEC-344 扩充）：

1. 原 3 行逐字保留（零编辑、零过滤、零 skip）；
2. R8/R9 全部已证攻击反例与 12 攻击面逐例拒绝；
3. 豁免范围可审计（闭语法、闭表、闭前缀、诊断可观测）；
4. 不引入新签名权威、外部依赖或密码学真实性声明；
5. 全部新腿 fail-closed；语料保护（resolved-outside-before-open）与性能原门不削减；
6. 两文件可实现边界（引擎改动限 hook 内嵌 python + 测试）；
7. 可逆性（部署/回滚不产生数据迁移）；
8. **无自授**：本设计及任何派生报告不得使原正文获得资格；资格只能来自第 6.3 节的裁决式迁移；
9. **部署空态等价**：不裁决迁移时，接口行为与现状判定等价（不偷放行、不偷新增通过）；
10. W1 按第 6.8 节规范并入（per-line 8 / 独立 glob 24 / 总池 32 / 诊断分列）。

---

## 2. 实际读取输入与过程约束

本会话 Architect 实际 read 以下 20 个文件全文（零 shell、零执行、零实验、除本文件外零写入、零子 agent、零用户交互；未读热 plan-tracker/evidence-log/execution-packets——热事实为 Coordinator 单源供应）：

| # | 文件 | 规模 |
|---|---|---|
| 1 | `agents/architect.md` | 90 行 |
| 2 | `skills/stage-architecture/SKILL.md` | 139 行 |
| 3 | `.governance/reports/FIX-445-R10-contract-decision.md` | 81 行 |
| 4 | `.governance/reports/FIX-445-health-resume-20261013.md` | 84 行 |
| 5 | `docs/requirements/FIX-445-health-resume-clarification-20261013.md` | 295 行 |
| 6 | `.governance/incidents/FIX-445-R10-source-extract.md` | 27 行（含完整 3 原行） |
| 7 | `docs/design/FIX-445-mention-contract-R10.md` | 135 行 |
| 8 | `docs/reviews/review-FIX-445-DESIGN-R10.md` | 132 行 |
| 9 | `docs/reviews/supplement-FIX-445-DESIGN-R10-evidence.md` | 105 行 |
| 10 | `docs/reviews/supplement-FIX-445-DESIGN-R10-calibration.md` | 44 行 |
| 11 | `docs/reviews/review-FIX-445-CODE-R6.md` | 100 行 |
| 12 | `docs/design/FIX-445-source-verification.md` | 304 行（七类映射） |
| 13 | `docs/design/FIX-445-source-verification-R3.md` | 61 行（prefix 规范） |
| 14 | `docs/design/FIX-445-source-verification-R5.md` | 49 行（Guard G） |
| 15 | `docs/reviews/review-FIX-445-DESIGN-R9.md` | 50 行 |
| 16 | `docs/reviews/supplement-FIX-445-DESIGN-R9-protocol.md` | 75 行 |
| 17 | `.governance/incidents/FIX-445-DEC336-contract.py` | 24 行 |
| 18 | `.governance/reports/FIX-445-R4-escalation.md` | 22 行 |
| 19 | `skills/software-project-governance/infra/hooks/commit-msg` | 1284 行（canonical 全文） |
| 20 | `skills/software-project-governance/infra/tests/test_hooks.py` | 1480 行（canonical 全文） |

另有第 4 节所述 4 轮只读搜索（3 grep + 1 glob）。产品两 blob 继承 R6 绑定（hook `a327f812…`/SHA256 `c7d5a01f…85461f`/59,453B；test `0e8aff2f…`/SHA256 `60fe5db5…9d0db`/71,558B；`review-FIX-445-CODE-R6.md:6`），本轮未执行 shell 故未重测 hash——如实标注，不作新测量声明。

---

## 3. 现状接口与已证冲突（基线事实，全部一手核自 canonical hook）

管线（`hooks/commit-msg`，行号锚定本轮实读）：

```text
Step 12 (:1141-1192)
 └─ speculation grep (:1177, 原样不动)
 └─ has_unnegated_fabrication_terms (:817-839)          [M0 编排]
     ├─ json_region_mask prose|record (:137-162)         [M1，不改]
     ├─ record tier: _fix445_verify (:673-695) → 内嵌 python 引擎 (:164-671)
     │    regions(:445) → strict_obj(:218,_nodup:207/_noconst:213/end==len)
     │    → top_string_fields(:239,escape-aware dmap) → field_candidates(:360)
     │    → corpus_records(:478-554) → credential(:556) → 逐实例 raw 删除(:637-655)
     ├─ sed 否定核 (:828-833)                            [M4，不改]
     ├─ endorsement_frame_check (:704-814)               [M5，不改：24否定/19填充/≤16窗/count==1]
     └─ LC_ALL=C grep 裸词 (:836)                        [不改]
```

已证冲突（R10 三重机录 + 本轮一手重推一致）：

- EVD-1587 prose `已知no-separator当真不能默当获准安全残余`：`当真` :770 无条件框架命中；最近 isterm（含 `，`:726）前缀窗 `已知no-separator`=14 字符；`已` 不在 24-否定表(:717)亦不在 19-填充表(:719) → 残留 → bad(:805) → BLOCK(:1190)。
- 跨记录授权不可用：credential(:615-617) 只作用于 strict-obj 有效区内 typed field；prose occurrence 永留 residual。GUARD_TOKENS(:339) 含 `当真`，Guard G(:427-428) 拒绝含框架词的 T2 候选。
- 三行分别的失败机制（`review-FIX-445-CODE-R6.md:42-44`）：1536=`无预算或PASS编造`（:831 或形中位闭表无 `预算` → 裸术语）；1587=上述当真窗；1588=`载荷含把将当作当成视为作为当真任token整span拒免`（裸 `当真` + 前缀全残留）。
- corpus 现状（W1 事实，`corpus_records` :478-497）：`got` 每行重置(:483)、行内 ≤8 refs(:488)、跨行 unique 累积无 cap(:490-492)、glob sorted 追加**无独立 24 cap**(:493-496)、`files[:32]` 全局截断(:497)；resolve/outside-drop 先于 open(:510/:519 先，:528 后)。
- R9 反例 `我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷`：`：` 重置窗至 `已知parser-token`（14 字符），`已` 残留即拒；`视作` 不在框架表(:758/766)。R8 两例 outer 空窗计 0 拒 + inner 前缀残留拒（`supplement-…-R10-calibration.md:17-21` 校准分列）。

以上为**静态推演**；本设计不重跑、不新增 whole-gate probe。

---

## 4. 来源资格调查（限仓库内冷历史工件；4 轮；结论 NOT_ESTABLISHED）

**调查问题**：三条原始子句（EVD-1536 `无预算或PASS编造`；EVD-1587 `已知no-separator当真不能默当获准安全残余`；EVD-1588 `载荷含把将当作当成视为作为当真任token整span拒免`）是否存在于闭环语料前缀（`docs/reviews/`、`.governance/incidents/`、`.governance/reports/`——即 hook `_REF`(:475) 认可的 refs 面 + task glob 面）内的**既有冷工件**中，可作为来源资格载体（carrier）。

**轮次与结果**（本轮实际执行，先于任何写入）：

| 轮 | 操作 | 模式 | 结果 |
|---|---|---|---|
| 1 | grep `已知no-separator\|无预算或PASS编造\|载荷含把将当作当成视为作为当真` @ `docs/` | 24 命中 | 全部为 R1/R7/R8/R9/R10 设计与审查文档、需求澄清报告——均为**对原行的派生讨论/引用** |
| 2 | 同模式 @ `.governance/incidents/` | 7 命中 | `FIX-445-R8-arch-first-response.md:42`、`FIX-445-record-CodeR6.ps1:13`（basis 文本提及）、`FIX-445-R10-source-extract.md:13/17/21`（Coordinator 对热原行的派生提取）、`FIX-445-DesignR8-write-recovery/{quarantined-originals,original-bytes}/review-FIX-45-DESIGN-R8.md:28`（隔离副本）——全部**派生** |
| 3 | 同模式 @ `.governance/reports/` | 3 命中 | `FIX-445-R10-contract-decision.md:18-20`、`FIX-445-R9-escalation.md:12`——**派生** |
| 4 | glob `.governance/incidents/*FIX-445*`（file-only） | 59 文件 | 冷工件清点（mtime 序），含 26+ JSON 命令记录族；供第 6.8/8.4 节具体路径集使用 |

**结论（ scoped NOT_ESTABLISHED）**：在已搜索的三个闭环冷前缀内，三条原始子句的**每一处**出现均为派生物（post-date 原行、且内容为对原行的讨论/提取/隔离副本）；**未发现任何先于或独立于原行的 origin 载体**。原短语的铸造点即 evidence 行本身（EVD-1587 为 Coordinator 对 DEC-336 授权约束的摘要行文；`incidents/FIX-445-R10-source-extract.md:17`）。

**边界（如实）**：`.governance/archive/`、git 历史、三前缀之外的任何路径（含 `governance-store-ops.json`——它本就不在闭环语料前缀内，即使含有短语也不构成合资格载体）**未搜索**（4 轮预算用尽）；本结论**不**声称全部历史中不存在来源。R10 报告的 exact-phrase 先期搜索结论（`reports/FIX-445-R10-contract-decision.md:28`）与本调查互证。

**附带实证（对第 5 节关键）**：R9 攻击串 `我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷` 与 R8 攻击串同样以**派生引用**形式逐字在场于 `docs/reviews/`（`review-FIX-445-DESIGN-R9.md:18`、`supplement-…-R9-protocol.md:59`、R10 三件套等）。即：合法子句与攻击子句**同时**以引用形式存在于合资格前缀——这不是假设，是本轮 grep 的直接观测。

---

## 5. 关键不可能性观察：包含困境（Containment Dilemma）

任何"纯包含/纯时序"的来源资格规则在当前语料上不可用且不安全，证明骨架：

- **规则 P（纯包含）**：子句字节出现在合资格前缀工件内 → 豁免。由第 4 节实证：R8/R9 攻击子句已在 `docs/reviews/` 逐字在场 → 规则 P 使全部已证攻击通过 → **违反评价标准 2，不安全**。
- **规则 T（时序优先）**：载体先于 evidence 行存在才豁免。攻击者今日引用昨日审查中的攻击串（审查即"更早的载体"）→ 攻击豁免；而合法行的铸句无先在载体（第 4 节 NOT_ESTABLISHED）→ 合法行仍拒。规则 T **恰好反转安全方向**：豁免攻击、拒绝合法 → 不可用。
- **推论**：局部可验谓词（包含、时序、标点、词形）无法区分"行文引用了某来源"与"行文即是断言本身"——与 R9 B1（identifier 形非 mention 证据）、R9 协议补核"有限语法不能保证任意作者意图"（`supplement-…-R9-protocol.md:73`）、R10"不能从等值/标点/局部可伪造工件可靠推断作者意图"（`docs/design/…-R10.md:95`）同一结论的语料级实例化。

**设计后果**：来源资格必须包含一个**不可由 hook 运行时推断的裁决分量**——即一份经用户裁决产生的 origin 绑定记录（registry），hook 只做机器验证（字节包含 + 载体在场 + 身份链）。这正是 R10 B 项"explicit M5/Guard G interaction + 用户授权"缺口的闭合面；它**是**新的授权权威面（如实命名，不自辩为纯技术），其安全代价在第 6.4/10/13 节具体展开，且**未获授权、未实施**。

---

## 6. R11 接口设计 —— M-route v1（prose 来源绑定提及）

### 6.1 模块划分（每模块职责 ≤3 句；依赖单向无环）

```text
has_unnegated_fabrication_terms (M0, 改调用条件，不改语义)
 ├─ json_region_mask (M1, 不改)
 ├─ python 引擎 (record tier 不改 + 新增 M 腿):
 │   ├─ corpus_records (M2b, W1 修订: 独立 glob24/总池32/诊断分列)
 │   ├─ credential (M2c, 不改)
 │   ├─ load_registry (M6a 新增: 一次性严格加载+schema 校验, ToolFault fail-closed)
 │   ├─ m_candidates (M6b 新增: prose 区 clause 抽取, 闭语法/闭界符/长度界)
 │   ├─ verify_mention (M6c 新增: registry 匹配 + 载体在场/包含/身份链验证)
 │   └─ per-instance raw 删除 + 计数校验 (M3 扩展: mcount-mismatch)
 ├─ sed 否定核 (M4, 不改)
 ├─ endorsement_frame_check (M5, 不改)
 └─ 裸词 grep (不改)
```

依赖方向：M6a→M6b→M6c→M3，均消费 M1/M2b 产物；无环（M6 不依赖 M4/M5；M4/M5 消费 M3 输出）。M5/Guard G/T2 代码路径**零改动**。

### 6.2 M 候选语法与 occurrence 边界（完整载荷）

- **作用域**：仅 prose tier（行内非 JSON region 区段）。clause 与任何 JSON region 相交 → 该 clause 不具 M 资格（fail-closed，禁止跨 tier span；关闭"把断言搬进 prose 绕 Guard G"的通道边界——见 6.7）。
- **clause 边界（闭表）**：相邻 `isterm`（复用 M5 现闭集 ：726-728：`。；;，：,:.！？!?`）**∪ `|`**（markdown 表格列界）或行首/行尾之间的极大 span。加 `|` 是保守收紧（clause 更小、字节精确性不变），不改变 M5 自身的 clause 定义。
- **触发（闭表）**：clause 含 (a) 任一 M5 算子（`把/将`（含内层 `当作/当成/视为/作为` 搭配）、`当作/当成/视为/作为`、`当真`）或 (b) 任一术语（`编造|幻觉`）。
- **完整载荷**：payload = **整个 clause 的逐字字节**（无截断、无归一化删改；探测时仅允许既有闭式显示归一 `_ext`(:204) 作为第二探，与 R0 §R3 两探纪律一致）。长度界：4..200 字符；越界 → 不是候选 → 留守原路径（保守拒绝）。
- **occurrence 边界**：每 clause 每次出现独立判定；同批次同 clause 多次出现逐实例删除并计数（`mcount-mismatch` ToolFault）。clause 内多触发仍为一个候选（载荷即引文整体）。
- **原三行 clause 实测（字符数）**：`已知no-separator当真不能默当获准安全残余`=26；`载荷含把将当作当成视为作为当真任token整span拒免`=28；`无预算或PASS编造`=10。R9 攻击 clause `已知parser-token当真不得视作批准合规载荷`=26（对照：同为合法长度，**语法不可区分**——第 5 节的实证核心）。

### 6.3 来源资格：裁决式 origin registry + 机器验证

一个 M 候选获得豁免，当且仅当以下**全部**成立（缺一即留守 → 原 M5/术语路径照判）：

1. **registry 在场且合法**（6.6 故障语义；缺席 = M 腿惰性，判定与现状等价）。
2. **条目匹配**：registry 存在条目满足 `clause` 字节相等 ∧ `task_id` 与当前任务相等（任务域封闭：跨任务引用不豁免——收紧，非放宽）。
3. **载体验证**（按 `carrier_kind`）：
   - `frozen_doc`：`carrier_path` 通过闭环前缀检查（`docs/reviews/`、`.governance/incidents/`、`.governance/reports/` 之内；拒绝绝对路径/`..`/`evidence-log.md`——**检查先于任何 open**，沿 :508-519 纪律）；realpath 落仓内；文件可读且 clause 在其字节中包含（直探 → `_ext` 归一再探）。
   - `command_record`：载件 strict-parse（C-1 五拒绝；内容类失败=该条目不可用，不全局 fault）；存在记录 `id` 字符相等 ∧ `utc_start/utc_end` 双瞬时 `inst_eq`(:196)；该记录的 `carrier_field`（限 `literal|output_as_captured|observed` 闭集）整值包含 clause（`V==A or _ext(V)==_ext(A)` 纪律，:575）。
4. **裁决引用在场**：条目 `adjudication` 字段引用真实 DEC/审查记录（Coordinator 写入时校验；hook 侧仅作非空与格式校验，不读 decision-log——不扩运行时读面）。

**资格语义（如实）**：以上是**必要条件的机器并集**；其安全性完全来自"registry 只能经第 6.4 节迁移面产生"这一权威边界。registry 不是签名、不证明密码学真实性；攻击者若能写 `.governance/`，与既有 CH-1（伪造 incidents JSON 获 typed 凭据）同级同界——持久、diff 可见、审查可查（`docs/design/FIX-445-source-verification.md:29` 威胁模型原文边界沿用）。

### 6.4 registry schema（**待裁决迁移面——未授权、未实施、本文件不自授**）

```json
{
  "version": 1,
  "entries": [
    {
      "clause": "<逐字 clause 字节，4..200 字符>",
      "task_id": "FIX-445",
      "carrier_kind": "frozen_doc | command_record",
      "carrier_path": "docs/reviews/… | .governance/incidents/… | .governance/reports/…",
      "carrier_record": {"id": "…", "utc_start": "…", "utc_end": "…"},
      "carrier_field": "literal | output_as_captured | observed",
      "adjudication": "DEC-xxx",
      "registered_at": "RFC3339"
    }
  ]
}
```

- **位置**：`.governance/mention-registry.json`（`.governance` 数据面，**非产品文件**；不占 W1 语料名额——权威单件，独立于 refs/glob 分配；其路径检查纪律与 6.3.3 相同）。
- **写入权威（迁移面，须用户裁决）**：仅 Coordinator 经机器路径写入；每次写入必须携带 (a) 用户 DEC 引用，(b) 独立审查对**被注册 clause 集**的对抗复核结论（注册攻击串=审查必须显式否决的用例），(c) 载体在场与包含关系的实测回执。禁止 agent 自写、禁止在设计/审查报告中"顺带"注册。
- **两条候选迁移路线（供裁决，均未授权）**：
  - **Mig-A（前缀内冻结 origin 文档）**：由 Coordinator 新建一份经用户裁决的约束 origin 文档（如 `.governance/reports/FIX-445-mention-origin-<DEC>.md`，内容含三 clause 逐字及来源上下文），作为 `frozen_doc` 载体注册。**安全代价**：该文档是"铸造在后的 origin"——其资格完全依赖用户裁决本身（不是考古发现）；这使 registry 的权威面从"认证既有事实"变为"授权新事实"，与 R10 拒绝的"复制该句建白名单"形式相近、实质差异仅在显式裁决与独立审查留痕。**必须逐字披露此代价后由用户裁决，不得默认采纳**。
  - **Mig-B（扩 carrier 前缀至 decision-log）**：将 `.governance/decision-log.md` 增入闭环前缀并以 DEC-336 行为载体。**安全代价**：扩语料前缀=扩攻击面与 IO 面（W1 需相应定义其容量语义），且 decision-log 为热治理面、非冷工件——违反"冷历史工件"调查前提。**列为不推荐**，仅证明已考虑。
- **空态**：registry 缺席或 `entries=[]` → M 腿零豁免（第 12 节部署等价性）。

### 6.5 raw-slice 映射

- prose tier：clause 的 raw 偏移即行内字节偏移（M 候选在**原始行文本**上抽取；M1 的 prose mask 仅用于 tier 判定，不用于偏移——规避 mask 丢字节导致的偏移漂移；引擎内以 `regions()`(:445) 的补集直接在原文上切 clause，与 record tier 的 `top_string_fields` raw 扫描同轴）。
- 删除作用于原始行区间 `[cs,ce)`；同删除集合与 record tier 的 `dels` 合并后统一走既有排序/重叠/计数校验（:644-653；重叠 → `deletion-overlap`；实例数不符 → 新增 `mcount-mismatch`）。
- `command_record` 载体侧的 escape 偏移不进入删除路径（载体验证只做包含与身份，不删除载件内容）；row 侧 M clause 无 escape 映射需求（prose 非 JSON 字符串区）——若未来 M 载体进入 JSON 字段，必须复用 R5 五步 dmap(:239-332)，本设计显式不做该扩展。

### 6.6 strict JSON 故障语义与故障码（全表）

| 码 | 触发 | 语义 | 方向 |
|---|---|---|---|
| `registry-read` | registry OSError/UnicodeDecodeError | 权威面不可读 | ToolFault → 引擎 RC2 → BLOCK（fail-closed） |
| `registry-malformed` | strict-parse 失败（重复键/非标常量/部分消费/非对象） | C-1 五拒绝沿用于 registry | 同上 |
| `registry-schema` | 未知键/缺必填/类型错/枚举外值/`clause` 超 4..200/`carrier_path` 形非法 | 权威数据结构性损坏 | 同上 |
| `mcount-mismatch` | M 删除实例数 ≠ 验证实例数 | 删除一致性 | 同上 |
| （沿用）`read/realpath/realpath-repo/slice-mismatch/count-mismatch/deletion-overlap` | 既有语义不变（:610/:644/:651/:499-534） | — | 不变 |
| 载体内容类失败（parse-error/包含不中/身份不中） | 条目不可用 | **非** ToolFault：该候选留守 → 行级保守拒绝 | 与 R7/R2 内容-工具二分一致 |

诊断行扩展（引擎 stdout，bash 结构检查不变）：`FIX445_DIAG VERIFIED= UNVERIFIED= PATHDROP= PARSEERR= DIRSKIP= GLOBCAP= POOLCAP= MVERIFIED= MUNVERIFIED=`。

### 6.7 与 M5 / Guard G / T2 的交互（不默扩声明）

1. **Guard G / T2 零改动**：`GUARD_TOKENS`(:339)、`field_candidates` t2 分支(:381-428)、整拒/溢出规则全部保持。M 腿仅作用 prose tier；tier 由 `regions()` 判定，M clause 与 T2 span 不可能重叠（6.2 作用域规则）。含 Guard token 的 T2 候选照旧整拒。
2. **M5 零改动**：24/19 表、≤16 窗、count==1、`当真` :770 裸触发、clause 有界——全部保持。M 删除发生在 sed/M5 **之前**（引擎残余输出已删）；未豁免 clause 的框架照旧到达 M5 并按现规则 BLOCK。
3. **R3 prefix 不扩**：否定/填充闭表、窗口消费纪律、溢出整拒——零触碰。
4. **不新增豁免给 record tier**：M 腿不给 typed field 任何新资格；typed 侧仍只有既有 C-4 路由矩阵(:621-630)。
5. **引擎调用条件（bash 侧唯一改动点）**：`_fix445_verify` 调用条件从 `record 非空` 扩为 `record 非空 OR (registry 文件存在 AND prose 含 M 触发预检)`。预检 = 既有术语 grep + 算子闭表 grep 的只读前置（不产生判定）。纯 prose 且无 registry → **零 python spawn（CH-7 保持）**；有 registry 且有触发 → 单次 spawn（与 record tier 同量级，批内一次）。

### 6.8 W1 语料分配规范（并入本设计；产品重开前必须按此裁决实现）

规范性算法（替换 `corpus_records` :478-497 的分配段；**路径集合与错误方向零变化**）：

```text
refs_pool: 每行 ≤8 个不同 refs（出现序，:483-489 语义原样）；跨行按首次出现去重累加（:490-492 原样；此阶段无 cap）
glob_all : sorted(glob(".governance/incidents/*<TASK_ID>*"))   # 集合不变：含非 JSON（.py/.ps1/.md/.log）与目录；排序键=OS join 后路径串
glob_sel : glob_all[:24]            # 独立 cap，先于与 refs 合并（校准四：禁止合并后截断）
GLOBCAP  : max(0, len(glob_all)-24) # glob 容量截断诊断
pool     : refs_pool 后接 glob_sel 中不在 refs_pool 的条目   # refs 先占位；与 refs 重复的 glob 消耗其排序槽位且不从第 25 个之后补位
POOLCAP  : max(0, len(pool)-32)     # 总池容量截断诊断
files    : pool[:32]
# 后续不变：evidence-log.md 跳过(:508)；绝对/.. 路径 drop→PATHDROP(:510)；realpath 仓外 drop→PATHDROP(:519)；
#          目录→DIRSKIP(:522-527)；open 失败→ToolFault("read")(:531)；parse 失败→PARSEERR 记零(:536-539)
```

硬性条款：(1) GLOBCAP/POOLCAP 与 PATHDROP/DIRSKIP **分开计数、不得混用**；(2) 语料容量截断**不得**计为源 EVD 行 skip、不得计入 PATHDROP；(3) resolved-outside-before-open 顺序不变；(4) glob 非 JSON-only（保持现集合）；(5) refs 语义 per-line（不偷换 batch 口径）。

---

## 7. 数据流（目标态；设计预期——未实现未运行）

```text
TASK_EVD_LINES（按任务批，Step 12 :1158 现状不变）
 │ speculation grep（:1177 不变）
 ▼
has_unnegated_fabrication_terms(input, task_id)
 │ json_region_mask prose|record（不变）
 ▼
[record 非空 OR (registry 存在 AND 触发预检命中)] ?
 │ 是 → python 引擎：
 │      ① registry 一次加载（fail-closed）
 │      ② 每行 regions() → record tier（不变）→ typed 逐实例删除
 │      ③ prose 区 m_candidates → verify_mention（registry+载体）→ 逐实例删除
 │      ④ W1 corpus（独立 glob24/总池32/诊断分列）供 ②③ 凭据/载体验证
 │      → residual + DIAG（新增 GLOBCAP/POOLCAP/MVERIFIED/MUNVERIFIED）
 │ 否 → residual = input（现状；零 spawn）
 ▼
sed 否定核（:828-833 不变）→ M5（:704-814 不变）→ 裸词 grep（:836 不变）
```

---

## 8. 验收矩阵（**静态设计预期**——产品未实现；"迁移态"列以第 6.4 节迁移获裁决并落地为前提，当前未授权）

### 8.1 原三行（两态对照；行零编辑；附录 A 逐字）

| 输入 | 空态（现授权态）预期 | 迁移态预期（未授权） | 机制 |
|---|---|---|---|
| EVD-1536 完整行 | **BLOCK**（与现状等价：`无预算或PASS编造` 或形中位闭表缺口，CODE-R6 B1） | **PASS** | 迁移态：clause（10 字符）注册+载体验证 → M 删除 → 行内再无未豁免术语/框架（该行为 CODE-R6 :42 判定的唯一失败机制） |
| EVD-1587 完整行 | **BLOCK**（当真窗 14 字符残留，R10 三重机录） | **PASS** | 同上：clause（26 字符）M 删除 → M5 无该框架输入 |
| EVD-1588 完整行 | **BLOCK**（裸 `当真` + 前缀全残留） | **PASS** | 同上：clause（28 字符）M 删除 |

### 8.2 已证攻击（两态均拒绝；R8/R9 命名反例）

| 输入 | 空态 | 迁移态 | 机制 |
|---|---|---|---|
| `我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷`（R9） | **BLOCK** | **BLOCK** | clause `已知parser-token当真不得视作批准合规载荷` 无合法 registry 条目（裁决面必须否决攻击串注册——6.4 写入权威 (b)）→ 留守 → M5 当真窗 `已知parser-token` 残留拒 |
| `将结论视为事实不能默当获准安全残余`（R8-a） | **BLOCK** | **BLOCK** | 无条目 → outer `将` 空窗计 0 拒 + inner `视为` 前缀 `将结论` 残留拒（校准二分列） |
| `把结果当作真实数据不得视作批准合规载荷`（R8-b） | **BLOCK** | **BLOCK** | 同上（outer `把` 空窗 + inner 前缀 `把结果` 残留） |
| 12 synthetic BAD 行（`test_hooks.py:1110-1141`） | **BLOCK** | **BLOCK** | record/prose 攻击无条目；typed 路由/Guard G/身份链照判 |

### 8.3 对抗边界与故障腿

| # | 输入 | 预期 | 机制 |
|---|---|---|---|
| A1 | 已注册 clause 尾部同 clause 内追加框架（无界符）：`…安全残余且把结果当作真实数据` | **BLOCK** | 字节不等 → 条目不匹配 → 留守 → M5 拒 |
| A2 | 已注册 clause 出现在**其他任务**行 | **BLOCK** | `task_id` 域不匹配（6.3.2 收紧） |
| A3 | registry 含重复键/`NaN`/截断 JSON | **BLOCK**（整批） | `registry-malformed` ToolFault → RC2 |
| A4 | registry 条目 schema 违规（未知键/超长 clause/非法路径形） | **BLOCK**（整批） | `registry-schema` |
| A5 | 载体文件被移除/漂移（clause 不再包含） | **BLOCK**（仅含该 clause 的行） | 条目不可用 → 候选留守（保守；非全局 fault） |
| A6 | registry 缺席 + 纯 prose 干净行 | **PASS**，零 python spawn | 调用条件短路；CH-7 保持 |
| A7 | `check-quoted 我编造了测试结果当真`（record tier, Guard G） | **BLOCK** | Guard G/T2 零改动（`test_hooks.py:861-875` 现行红测族继续成立） |
| A8 | 攻击串 + 攻击者私植载件+registry 条目（越权写） | 界外威胁模型 | 与 CH-1 typed 伪造同级：持久、diff 可见、审查可查；非密码学承诺（第 6.3/10 节披露，不计为设计逃逸也不声明不可伪造） |

### 8.4 W1 三静态例（具体路径集合；前提：候选不重叠且路径合法）

固定 fixture glob 总体 F（32 个具体文件名，取自第 4 节 glob 实测清单的排序前 32，测试在 temp repo 中按名创建）：

```text
F01 FIX-445-C6-mapping-metadata.json        F02 FIX-445-C6-mapping-metadata.ps1
F03 FIX-445-CodeR6-blocked-results.py       F04 FIX-445-CodeR6-command-and-boundary-records.json
F05 FIX-445-D20-safety-incident.json        F06 FIX-445-DEC336-contract.py
F07 FIX-445-DEC338-contract.py              F08 FIX-445-DEC338-execution-protocol.md
F09 FIX-445-DesignR10-boundary.json         F10 FIX-445-DesignR7-blocked-results.py
F11 FIX-445-DesignR7-boundary.json          F12 FIX-445-DesignR8-boundary.json
F13 FIX-445-DesignR8-preserve-quarantine.ps1 F14 FIX-445-DesignR8-supplement-quarantine.ps1
F15 FIX-445-DesignR9-boundary.json          F16 FIX-445-DesignR9-command-receipts.json
F17 FIX-445-R10-source-extract.md           F18 FIX-445-R4-blocked-results.py
F19 FIX-445-R4-priority-boundary.json       F20 FIX-445-R6-checkpoint-results.py
F21 FIX-445-R6-priority-boundary.json       F22 FIX-445-R8-arch-first-response.md
F23 FIX-445-R8-archive-errant-paths.ps1     F24 FIX-445-R8-preserve-recovery.ps1
F25 FIX-445-R8-write-incident.json          F26 FIX-445-architect-R1-V1-V3-returned-literals.md
F27 FIX-445-architect-R1-V4-returned-literal.ps1 F28 FIX-445-architect-R1-command-records.json
F29 FIX-445-architect-R2-command-records.json F30 FIX-445-architect-R3-command-records.json
F31 FIX-445-architect-R4-command-records.json F32 FIX-445-architect-R5-command-records.json
```

| 例 | 输入 | expected selection（具体集合） | 容量诊断 |
|---|---|---|---|
| W1-Ex1 | 0 refs + F01..F32 | **F01..F24**（24 glob 入选；F25..F32 截断） | GLOBCAP=8，POOLCAP=0，PATHDROP=0，DIRSKIP=0 |
| W1-Ex2 | 4 行 × 8 不同 refs（=32：`docs/reviews/FIX-445-fixture-ref-01.md`…`-32.md`，均为 `_REF` 合法形、与 glob 命名空间不相交）+ F01..F32 | **refs-01..refs-32**（32 refs 全保留；F01..F24 因总池 32 全部出局） | GLOBCAP=8，POOLCAP=24，PATHDROP=0 |
| W1-Ex3 | 16 refs（refs-01..16）+ F01..F32 | **refs-01..16 + F01..F16** | GLOBCAP=8，POOLCAP=8，PATHDROP=0 |

去重/补位锚定：W1-Ex2 中若某 glob 条目与 refs 重复，其消耗自身排序槽位且**不**从 F25 之后补位（例如 refs 含 F09 时，入选 glob 集为 F01..F08,F10..F25 中前 23 个未占位者——总数仍 24，重复不回收名额）。三例与 R10 裁决表（`reports/FIX-445-R10-contract-decision.md:44-48`）逐格一致。

**live 现状快照（示意，非测试依据）**：2026-10-13 glob 实测 59 文件 + 至少 2 个已知目录（`FIX-445-DesignR8-write-recovery`、`FIX-445-R5-implementation-evidence`）→ 排序后总体 ≥61，独立 glob24 截断将丢弃 ≥37（GLOBCAP≥37）；目录条目入选时按 DIRSKIP 处理（结构跳过，非读故障）。未知是否有更多目录（glob 不列目录）——如实标注；测试必须以固定 fixture 总体验收，不得以 live 快照为准。

---

## 9. 替代方案（预定义标准=第 1 节；先定标准后比较）

| 方案 | 要点 | 判定（对照标准 1-10） |
|---|---|---|
| **A — 保守拒绝维持（现状）** | 不改任何接口 | 标准 1-8、10 全过；标准 9 平凡满足；**不解决可用性**（合法行永拒）。定位=姿态非修复（R10 同判） |
| **B — M-route v1（本设计，选定）** | 裁决式 registry + 机器验证 + W1 并入 | 标准 1-7、9、10 满足；标准 8 通过"空态等价 + 迁移须裁决"达成；**现实兼容性受限于第 4 节 NOT_ESTABLISHED**（第 13 节） |
| **C — 验收范围分离**（历史行退出当前扫描） | 改 mandatory acceptance | **排除**：DEC-344 明示不授权验收放宽（标准 1/2 面违约风险，`docs/design/…-R10.md:107`） |
| **D — 语义/LLM 判定** | 模型判 mention vs assertion | **排除**：外部依赖+不可审计+非 fail-closed（R0 A4 同判） |
| **E — 纯包含/时序资格（无 registry）** | 第 5 节规则 P/T | **排除**：包含困境证明不安全（P）或方向反转（T）——本轮 grep 实证支持，非纸面推演 |
| **F — 局部词形/闭表再扩展**（R7-R9 路线） | 加语法标记/后缀 | **排除**：R9 B1 反例未解，"不再只加一个标记"（`session-snapshot` R9 补核解除条件） |

选定 **B** 的理由：唯一同时满足"原行零编辑 + 攻击拒绝 + 无自授 + 可审计 + 两文件边界"的候选；其代价（第 13 节现实结论）如实呈现，不以设计文成隐藏。

---

## 10. 蓝军挑战与响应（≥3；含 ID 与缓解）

| # | 挑战 | 响应 | 残余 |
|---|---|---|---|
| BT-1 | **派生引用洗白**：攻击串已逐字在场于 `docs/reviews/`（第 4 节实测），纯包含资格会放行全部攻击 | 第 5 节包含困境 → 资格必须过 registry（裁决分量）；E 方案正式排除；6.4 写入权威要求独立审查对注册集做对抗复核（攻击串注册=必须显式否决的用例） | 裁决质量依赖人/流程（DRI/外部资格未知，如实） |
| BT-2 | **registry 伪造/自授**：能写 `.governance/` 的攻击者（或越权 agent）注册攻击 clause | 联锁：条目还须载体在场+包含/身份链（registry 单独不充分）；任务域封闭；写入仅 Coordinator 机器路径+DEC 引用+审查留痕；diff 可见 | 与 CH-1 typed 伪造同级同界（接受边界，非密码学声明）；空态零暴露 |
| BT-3 | **Guard G 绕道 prose**：把算子载荷搬出 JSON 进 prose 再注册 | tier 分离规则（6.2）：clause 与 JSON region 相交即不具资格；T2/Guard G 零改动；迁移裁决同样须对此对抗复核 | 依赖 BT-2 同一权威边界 |
| BT-4 | **W1 容量滥用**：refs 挤占 glob 或 glob 扩大凭据/IO 面（校准三的双向性） | 6.8 规范：独立 glob24 先于合并、无补位、GLOBCAP/POOLCAP 与 PATHDROP 分列；方向双向如实（既不称保守也不称逃逸，沿校准三措辞） | 实际 selected 构成未测（实现期必须以 focused tests 验收三例） |
| BT-5 | **registry 故障成为新停机面**：损坏的 registry 阻断一切提交 | fail-closed 是**有意方向**（权威面损坏不得静默降级）；回滚=移除/修复 registry 单文件；schema 闭集校验尽早失败 | 可用性代价如实计入 NFR |
| BT-6 | **clause 边界博弈**：注册 clause 内拼接框架、跨任务复用、边界外附加 | 8.3 A1/A2 + 字节精确 + 闭界符表（isterm∪`|`）+ 长度界；任何变形=不匹配=留守=现状拒绝 | 无已知绕过；未知形保守拒（沿 R5 哲学） |

---

## 11. NFR 映射

| 维度 | 措施 | 残余/未测 |
|---|---|---|
| 安全 | 全腿 fail-closed（6.6）；闭环前缀+路径检查先于 open；无新签名权威/外部依赖；tier 分离护 Guard G；任务域封闭 | registry 权威面=CH-1 级接受边界；非密码学承诺 |
| 可靠性 | registry 三级 ToolFault；载体内容类失败行级保守拒绝（二分沿 R2/R7）；W1 诊断分列可观测 | 故障腿仅设计推演，实现期须红绿注入 |
| 性能 | registry 单件一次读；clause 扫描线性有界（4..200）；W1 上界保持（24/32）；纯 prose 无 registry 零 spawn（CH-7） | CPU27.8/CLI36/434339/32MiB/1500 **不重测不放宽**；实现后必须复测原门 |
| 可用性 | 空态与现状等价（合法行仍拒——如实）；迁移态方可用 | 现窗合法 prose 仍阻断（R10 CH2 残余 High 保持） |
| 可维护性 | 单一 registry schema + 单一 clause 闭语法，集中注释因果；扩展须新票 | 词法补丁债（R9 补核警示）以"不再加标记"纪律规避 |
| 可测试性 | 每故障码一红一绿；W1 三例 fixture 具体路径集；原三行两态矩阵；真源抽取接口沿 `_extract_*_fn` 模式 | B2（batch-any 弱化）为**独立产品阻断**，本设计不解决不掩盖 |

---

## 12. 版本、部署等效性与回滚

- **版本**：registry `version:1`（schema 演进须新票+迁移说明）；引擎 DIAG 增 `MRV=1` 面板标记。
- **部署空态等价**：registry 缺席/空 → 判定与现接口等价（M 腿零豁免、零 spawn、零语料变化——W1 例外：glob24/总池32 分配修正**本身**是行为变化，属 R10 已裁决的 W1 缺陷修复面，方向与诊断已由 6.8 规范固定；其实现仍属产品票，须独立授权+focused tests，本设计仅并入规范）。
- **回滚**：产品侧 = `git revert` 单 commit（两文件，D4 纯粹性；无数据迁移——registry 为增量数据面）；数据侧 = 删除/清空 registry 文件即回到空态。历史 EVD、载件、审查记录零触碰。**可逆**。

---

## 13. 现实兼容结论与待裁决项（下一裁决）

1. **当前授权态（registry 空/缺席）**：部署本设计后，EVD-1536/1587/1588 **仍 BLOCK**，全部攻击仍拒绝，四任务源仍不 clean，FIX-445 验收仍失败——与 R10 结论一致的**有意**结果（标准 8/9：无自授、空态等价）。
2. **资格现实**：第 4 节 scoped NOT_ESTABLISHED——三 clause 在闭环冷前缀内无 origin 载体；且第 5 节证明纯包含/时序规则不可用。**因此"只修接口"永远不能使原三行 clean**；使它们 clean 的唯一本设计内路径 = 第 6.4 节迁移（Mig-A/Mig-B），**未获授权**，本文件不实施、不催促、不预填 registry。
3. **待用户裁决的具体问题**（经 Coordinator 呈现）：(a) 是否授权 Mig-A 迁移（新 origin 文档 + 三 clause 注册 + 独立对抗复核）及其安全代价（6.4 逐字披露：权威面从"认证既有事实"变为"授权新事实"）；(b) 或维持阻断（方案 A 姿态）；(c) W1 产品实现票（独立于本接口，可单独授权）。
4. **即使迁移获裁决并通过独立 R11 审查**：仍须经产品实现、B2 逐例断言恢复、B3 处置、64 tests 全绿、四任务源 zero skipped/RC0、独立 Code 审查全部实际完成后，FIX-445 方可谈验收——本设计不承诺其中任何一步。

---

## 14. proposed ADR delta（Coordinator 写回 decision-log；本文件只出草案）

- **标题**: ADR-FIX-445-R11 — prose 来源绑定提及接口采用"裁决式 origin registry + 机器验证"契约（设计，未实施）
- **日期**: 2026-10-13
- **背景**: R10 三重机录证成现接口与保留 EVD-1587 prose clean 在该输入上不可兼得；R7-R9 否决局部词形；本轮第 4 节证明闭环冷前缀内无 origin 载体、第 5 节证明纯包含/时序资格不安全或不可用（包含困境，grep 实证）。DEC-344 授权限定设计 + 独立 R11。
- **决策（proposed）**: 采纳 B（M-route v1）：prose tier 新增 M 腿（闭语法人 clause、任务域、registry 必要条件并集、载体验证、逐实例 raw 删除）；T2/Guard G/M5/R3 prefix 零改动；W1 按 per-line8/独立 glob24/总池32/诊断分列规范并入；registry 迁移（Mig-A/B）为独立待裁决项，未授权未实施。
- **备选方案/排除**: 第 9 节 A/C/D/E/F。
- **影响范围**: `hooks/commit-msg`、`tests/test_hooks.py`（产品实现须另授权）；`.governance/mention-registry.json`（数据面，仅经裁决迁移产生）；无其它门弱化。
- **后续动作**: 独立 R11 审查（强制输入：R10 三件套 + 本文件）；裁决第 13.3 节三问；任何产品实现另行授权 + focused tests + 原性能资源门复测。
- **可逆性**: 可逆（第 12 节）。

---

## 15. 自检与过程披露

- 硬门槛：备选 **6≥2**（A-F）；蓝军 **6≥3**（BT-1..6 均有响应）；ADR 字段完整（§14）；模块无环（§6.1）；接口输入/输出/类型/验证/故障码（§6.2-6.6）；Design Doc 最小结构（目标 §1/方案 §6/替代 §9/风险 §10/NFR §11）齐。
- 红线：零 shell/执行/实验；零产品写；零 `.governance` 写（DEC336 helper 只读）；零子 agent；零用户交互；未读热面（热事实=Coordinator 单源）；未 stage/commit/push。
- 诚实项：本文件不是批准；空态=原三行仍 BLOCK（§13.1）；B2/B3/64tests/CodeR6 未解且不归本设计；live glob 目录数未知（§8.4）；git 历史/archive 未搜索（§4）；hash 未重测（§2）；DRI/外部评审资格未知；一切"迁移态"列以未授权迁移为前提。
- 步数预算：实际 read 20 文件 + grep×3 + glob×1 + write×1，未接近 35 步建议上限；无发散探索。

---

## 附录 A. 原三行逐字（来自 `.governance/incidents/FIX-445-R10-source-extract.md:13/17/21`，Coordinator 对热原行的完整提取；本设计以该提取为唯一原行文本依据，零编辑）

```text
EVD-1536（原行 2271）:
| EVD-1536 | FIX-445 | DEC334新有界来源修复入账与设计先行派发 | 用户影响：获得=不需要；感知=实际安全阻断经用户裁决进入可验证来源修复；体验变化=先核对来源再独立设计审查，旧失败不改成通过，产品暂不写；迁移指南=不需要。目标对齐：落实用户熔断裁决在原two产品边界正确关闭三实缺陷，设计与代码审查分离，不自动原R4、不放宽安全、不把机器推荐扩成发布或新功能。 | 事实依据：用户ask fix444-r3-escalation选择有界来源修复 (Recommended)已machineDEC334 op88835292e9b540eeb7dbdb4fc440b6e4；TRIAGE-FIX445完整五步exit0/newcyclefalse/version0.98当前0.97合法/deps空，文件重叠含历史FIX282/FIX359/REL079与旧FIX444可见，当前实锁empty/旧agentidle无并发write，串行原产品未来独占；只report锁与triage两产品差异advisory已披露，不隐瞒。新plan行经Coordinatorread/edittriaged入账、机器triaged->dev op3da6877cdf5b4de38eace385643d5c74、execution-packet --write --taskFIX445 --budget18增量17包其余16保持、definehelper实际exit0/contractnotrunyet。支持CLI核对时task-create --help实际invalidexit2/no写，已用合法新行入账+task-row-update锚非绕状态；参数帮助本地只读无真实home写。readlocks空后machine取FIX445仅twoexpectednewdoc联合ownership，Architect5244871b-aae2-486e-b07b-c324275dbda4用角色与stage-architecture模板只designwrite，DesignReviewer c9506ab9-13f7-4bec-baa4-cfba2ee77066用独立role/skill只reportwrite、等staticdoc。产品两blob仍8efea943.../8efd64da.../zeroedit，原threefindings实证全注入，来源绑定不能只格式键数，unknown保守拒绝，originalrows/reportszeroedit。goal用户新裁决修订至rev3/activearmed/max8，目标含先设计后twofile修及最终交付，无预算或PASS编造。原门CPU27.8/CLI36/semantic434339/32MiB/1500与installedhook/用户config保持，未stage/commit/push。 （机器写入：governance-store evidence-append op-5bdb86da5b844c15b07265a17ed79346；schema v1） | .governance/change-triage/FIX-445.json; .governance/incidents/FIX-445-define-packet.py; .governance/execution-packets.json; .governance/reports/FIX-444-R3-escalation.md; .governance/session-snapshot.md；refs[repo_file:.governance/change-triage/FIX-445.json=resolvable] | Coordinator | 2026-10-11 | G11 | 用户DEC334裁决落实、新段FIX445设计先行；旧FIX444BLOCKED保持，产品未修改或验收 |

EVD-1587（原行 2334）:
| EVD-1587 | FIX-445 | 用户DEC336闭表修订授权与独立R5派发 | 用户影响：获得=不需要；感知=熔断后按明确选择继续有界修复；体验变化=只修新增规则缺口并先独立审查，产品历史失败保持可见；迁移指南=不需要。目标对齐：落实用户有界闭表修复选择，不把来源一致性边界变成风险接受，不自动重置审查轮次、不提前产品通过或commit批准，持续完成原健康任务。 | 事实依据：用户ask fix445-r4-escalation实选有界闭表修复，DEC336/op81e3e4a979d74cb7986c5eb976c2dbc2、taskblocked→dev opac8f2b6551124dcc8f406fc4d386e0c6；reademptylocks后机取newR5design/review双doc各所有权，Architect/同DesignReviewer已填模板派发。onlyR4A封闭允许字符集和对应五变体/控制字符回归，已知no-separator当真不能默当获准安全残余，要具体closedguard；C1C2C3C5/R2fault/R3prefix/原baseline保持。productcheckpoint仍f2794b.../05b05b...static，22tests3FAIL不改/actuallastFAIL保留，合同helper只scopeprogress更新并_TargetLockpreserve其它16packets。actualPython执行原pwshliteral和helper已持久，本次receipt中UTC/exit0/五envsg663cc191，未运行code或newprobe。R5deltaactualpass才解产品续作，NC5再次升级/noautoR6；最终Code轮次账本max+1，修复方向非交付批准。 （机器写入：governance-store evidence-append op-5c8327760edc4c0f830b1622ac60bc5d；schema v1） | .governance/incidents/FIX-445-DEC336-contract.py; .governance/decision-log.md; .governance/agent-locks.json; .governance/reports/FIX-445-R4-escalation.md；refs[repo_file:.governance/incidents/FIX-445-DEC336-contract.py=resolvable] | Coordinator | 2026-10-12 | G11 | 用户新有界授权已机录，R5设计与独立备审在途，原实际FAIL保持 |

EVD-1588（原行 2335）:
| EVD-1588 | FIX-445 | DEC336闭表R5设计静止回执与同Reviewer正式复审 | 用户影响：获得=不需要；感知=熔断授权后的修订以具体规则送独立复审；体验变化=字符白名单和载荷背书guard明确，未知分隔与转义偏移保守闭合；迁移指南=不需要。目标对齐：只修R4A范围并保持已过完整身份和逐片段引用约束，拒绝已知连写背书而不默接受残余风险，实际设计通过后再继续原两个产品文件及三个失败闭环。 | 事实依据：R5newdoc49line8498bytes/SHA503677c3d9e4fd166c72974cfd2285afeab774aff69dd8159b87056d664d6511 parent全read+hash实核；Architectactualfullonlyreadonlyshell UTC2026-10-12T00:05:16.1469733Z至.1824455Z/outer0/各cmdlet未捕unknown，fullbody/raw持久FIX-445-architect-R5-command-records.json，本轮read1/write1/hashshell1/zero实验产品或仓外。closed单元whitelist U4E00..9FFF与ASCIIalnum/符号集合空，载荷含把将当作当成视为作为当真任token整span拒免，sourceC6合法载荷无token；unknownseparator/control留residualscan/候选溢出整拒/escapeaware raw映射解析值一致校验，oldR4pair4误更正5、payload33char/field211chars258bytes来源已核。sameReviewerR5正式onlydelta+prevR4report已send/reportonlylock机转，actualverdict未出；oldpassedface不重全，NC5须再升级noautoR6，Designpass不产品pass，22test3FAIL和oldR4BLOCKED记录保持。DEC336是新明确bounded授权不是绕熔断，不发布/放宽baseline/commitapproved。 （机器写入：governance-store evidence-append op-07a47bb2e19f4e4683ea3ceacb0d3e80；schema v1） | .governance/incidents/FIX-445-architect-R5-command-records.json; docs/design/FIX-445-source-verification-R5.md; docs/reviews/review-FIX-445-DESIGN-R4.md; .governance/agent-locks.json；refs[repo_file:.governance/incidents/FIX-445-architect-R5-command-records.json=resolvable] | Coordinator | 2026-10-12 | G11 | 用户授权的仅R4-A设计R5已静止交审，产品继续保持失败现场直到实际设计通过 |
```

（附录 A 为派生提取的逐字转录，本身不构成来源资格——`incidents/FIX-445-R10-source-extract.md:3` 原文约束沿用于本文件。）
