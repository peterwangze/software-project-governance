# review-FIX-389-CODE-R0 — LRC 文档面清账（代码审查 · R0）

> **Round 声明**：R0（首轮审查，无前轮 REVIEW 报告可比对）。审查对象 = commit **9df2381**（`git show --stat`：2 文件 6+/6−——`docs/reviews/review-REL-086-RELEASE-R2.md` 5+/5−、`docs/reviews/review-FIX-376-CODE-R0.md` 1+/1−）。
>
> **审查方法**：逐 diff 通读（git show 9df2381 全量）+ LRC 扫描器源码逐行核验（`_split_markdown_cells` / `_markdown_accounting` / `_analyze_text` state_slots / `_classify`）+ 五项独立实测（LRC CLI 复跑、双版本 ragged 全文件枚举〔源码级补丁复刻 `_markdown_accounting`，raise→收集〕、accounting:29:1 定位映射、insert-only 字符级验证、pytest 定向套件）。实测脚本存档于 `%TEMP%\fix389_review\`（scan.py / classify.py）。审查全程未修改产品代码与 `.governance/`；本报告为唯一仓库内输出文件（落盘后成为 1 个 untracked 文件，如实注记）。

---

## 0. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **0** |
| P3 讨论 | **5**（F-A / F-B / F-C / F-D / F-E） |

零 P0/P1/P2：全部六项 MUST 重点审查项经实测坐实（§1）；审查报告语义完整性红线保持（§1.1）；根因修正申报与源码机理、实测数据三方一致。P3 均为申报措辞精度/口径注记，不动摇任何结论。

---

## 1. MUST 重点审查项逐项核验

### 1.1 审查报告语义完整性（红线——不改审查结论）— ✅ 通过

- **REL-086-R2 §2 表 L42-45**：对 4 行逐一做字符级插入检测——`new == old[:k] + " | " + old[k:]` 全部命中（插入点 k = 143 / 70 / 67 / 54，token 恒为 `" | "`）。**零字符删除** ⟹ 合并 cell 的信息在结果/证据两列间零丢失；结果列收尾符（`——`/`；`）为拆分自然边界的原字符保留，非新增内容。审查结论字符面零改动（红线保持）。
- **REL-086-R2 §3 表 L61**：diff 实测为单处替换 `'`\\`' → '反引号包反斜杠再包反引号的三字符形态'`（difflib 单 opcode）。指代清晰度：替换文本与 L59 行 7d6ff6a 先例措辞逐字同构（「反引号包反斜杠再包反引号的三字符形态」），且同表 L57-60 已建立该描述的语义锚定；该行自身判定列（「等价（引述改叙述式）」）未被触碰。见 F-D（引述非逐字的固有代价）。
- **FIX-376-R0 L42**：改写后审查结论「**fallback 语义逐字保持**」加粗断言原样保留，仅证据引用形态由 inline code-span 改为引用式描述；verbatim 代码**确在上方实现块 fence 留档**——现行文件 L36-37 = `if not status and cells:` / `status = cells[-1].strip()`（fence 区 L30-39 未被本 commit 触碰，diff 上下文行可证）。改写描述忠实：「状态为空且 cells 非空」⇔ `if not status and cells`；「直取末列 cell 文本的条件赋值」⇔ `status = cells[-1].strip()`（`strip()` 语义由 fence 字面承载）。证据链完整。

### 1.2 根因修正核验①：ragged 5 处声明 — ✅ 精确复现（5/5，无第 6 处）

将 `_markdown_accounting` 的 ragged raise（loop_runtime_claims.py L672-673）源码级补丁为收集后对 pre-commit（`git show 9df2381^`）与 post-commit 全文件枚举：

| 版本 | ragged 行实测 | 判定 |
|------|--------------|------|
| pre-commit | `[L42(3v4), L43(3v4), L44(3v4), L45(3v4), L61(1v3)]` | **恰好 5 处**——与修复面逐一对应 |
| post-commit | `[]`（另无任何 ACCOUNTING 异常） | **0 处**——修复完整 |

「解析器同文件首错 abort 掩盖」机理源码坐实：ragged raise 沿 `_account_candidate`（L919-922）被捕获后**整文件 accounting 返回空 records + 单条 finding**（且该 finding 无 locator）——同文件后续 ragged 行不可见，LRC findings 只呈现首错，与申报一致。**边界完整性**：L41/L57/L58/L59/L60 亦含同形 `` `\` `` 构造但实测不触发——`_split_markdown_cells` 的 careful path 有 `protected_pipe` 门控（L523-531：仅当行内含 `\|` 或 marker 对跨管道时进入转义感知路径），这些行的 backtick 均 confined 于首 cell 内且行内无 `\|` → naive split 达标；L61 因行内含 `\|`（「\| 2 \|」）进入 careful path，`` `\` `` 的闭合反引号被 `\` 转义吞掉（L545-547 escaped 分支先于 backtick 分支）→ `code_delimiter` 卡开 → 后续管道全部吞并 → 1 cell vs 3 headers。**5 处枚举既无遗漏也无过度修复（D4 修改纯粹性成立）。**

### 1.3 根因修正核验②：「非 fence 内」声明 + 真机理 — ✅ 坐实（附 F-C 措辞精度注记）

对 pre-commit FIX-376-R0 全量 accounting→semantic unit→relation 实测：

- **映射精确**：`accounting:29:1` → source_span 起始行 = **文件 L42**，provenance = list_item，unit 文本 = 改写前 L42 bullet（含 inline code-span `status = cells[-1].strip()`）。
- **fence 零嫌疑**：fence 行 L31-38 = accounting records **20-27**（md_fence_line），全部不产生 unknown_state unit——pre-commit 全文件 unknown_state unit **仅 accounting:29:1 一个**。触发点在 prose bullet，不在 fence ✓。
- **机理链逐环坐实**：state_slots 正则（L1710-1713：`\b(status|...)\b\s*[:=]\s*["']?([\w-]+)`）命中 `status = cells` 捕获 `cells` → `reviewed_state` 白名单（L1714-1720）无 `cells` → relation `unknown_state:cells`（实测记录）→ `_classify` L3145-3146 → UNKNOWN_STATE_PREDICATE。与 Developer 申报机理逐字吻合。
- post-commit 同法实测：unknown_state unit = **0**（UNKNOWN_STATE_PREDICATE **1→0** 实测成立）。改写后 L42 仍含 hint token（「循环行」）故仍为 unit，但无 `status[:=]` 形态 → 零 relation → 良态分类（实测 STRUCTURAL_DATA）。

### 1.4 insert-only 声明核验 — ✅ 范围诚实（附 F-A 口径注记）

- §2 L42-45：**字符级 insert-only 成立**（§1.1，单 token `" | "`、零删除）。
- §3 L61 与 FIX-376 L42：**非 insert-only**（真实替换，difflib 实证）——commit message 的「insert-only 零字符删除」**仅限定于 §2 L42-45 修复**，未对后二者声称，表述范围准确。整体 commit 6+/6− = 4 行字符级插入（行级 diff 呈现 4+/4−）+ 2 行替换，如实记录。

### 1.5 LRC PASS + 套件复现 — ✅ 全部精确实测命中

| 申报 | 实测 | 判定 |
|------|------|------|
| check-loop-runtime-claims verdict PASS / exit 0 | exit **0**，verdict **PASS**，findings = **空**，exemptions_applied = **4**（账本既有 4 条，无新增） | ✅ |
| UNKNOWN_STATE_PREDICATE 1→0 | state_totals 无该键 + 双版本 per-file 实测 1→0（§1.3） | ✅ |
| semantic_units → 308,248 ≤ 361,923 | **308,248 精确命中**（余量 53,675）；STRUCTURAL_DATA 307,257 / NEGATIVE_NONCLAIM 971 / PLANNED_NOT_ACTIVE 9 / HISTORICAL_FACT 7 / UNSUPPORTED_AFFIRMATIVE 3（豁免覆盖）/ AMBIGUOUS_SUBJECT_RELATION 1（豁免覆盖） | ✅ |
| pytest 62P + 81 subtests / 0F | **62 passed, 81 subtests passed**（150.22s，exit 0） | ✅ |
| commit 门测试物化机理 | 源码坐实：`test_three_run_performance_identity_and_median`（test_loop_runtime_claims.py L1086-1133）以 `materialize_loop_runtime_git_root(product_root, ":index", ...)`（L1097）从 **git index** 物化被测树并断言 `verdict == "PASS"`（L1116）——pre-commit 时 index 未含修复必红、commit 后转绿；「工作树首跑 61P+1F」为历史申报，与该机理自洽，未独立复跑（需 revert 面），如实注记 | ✅ |

### 1.6 处置 (a) vs (b) 选型核验 — ✅ 理由链成立

核验链（四点全部成立）：①该命中为**冗余 inline 断言**——verbatim 代码已完整留档于上方 fence（§1.1），改写零信息损失，不属「改写即损毁记录」的豁免对象族；②账本 `expected_duration` 语义（4 条既有条目均为「报告改写即删除本条目」）意味着为即将改写的文本新立豁免条目属自相矛盾；③账本为代码锚定（`REQUIRED_EXEMPTIONS_SHA256` = `4f8a6cc8…`，loop_runtime_claims.py L114）——处置 (b) 需同步 digest 锚并走产品代码审查，成本失衡；④账本目标族 = 已发布产物记录性文本误判（FIX-300 记录性文本 / checklist「已发布文档不可改写」），本命中非该族。**处置 (a) 正确。**

### 1.7 commit 9df2381 边界 — ✅ 干净

`git show --stat`：仅 `review-REL-086-RELEASE-R2.md` + `review-FIX-376-CODE-R0.md`，恰等于 agent-locks 中 FIX-389 的锁面（`docs/reviews/review-REL-086-RELEASE-R2.md` / `review-FIX-376-CODE-R0.md` / `review-FIX-389-CODE-R0.md`〔本报告，expected_new〕）。FIX-388 锁面（`test_verify_workflow.py` / `env_failure_classification.json` / `review-FIX-388-CODE-R0.md`）**零混入**；工作树现存 2 个未提交修改（`checks/version.py`、`tests/env_failure_classification.json`）为 FIX-388 并行 WIP，不在本 commit 内。两票文件族独立（锁面 TTL 备注同证）。

---

## 2. 五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | 5 处 ragged 精确复现且边界完整（§1.2）；accounting:29:1→L42 映射精确、机理链逐环实测（§1.3）；insert-only 字符级验证（§1.4）；审查结论红线保持（§1.1） |
| 安全性 | ✅ 通过 | 纯仓库内文档变更；无输入面/密钥/权限变化；不触碰扫描器代码，其 fail-closed 语义不变 |
| 可维护性 | ✅ 通过（净改善） | 消除使真实树扫描 fail-closed 的文档触发源；文字化沿用 7d6ff6a 先例措辞（同构复用，语义锚定一致）；「字面见上列实现块」引用式为证据链保留的干净惯式 |
| 性能 | ✅ 通过 | 语义单元 +3（本票可归因 delta，§5）；308,248 ≤ 361,923 余量 53,675；代码零变更 |
| 测试覆盖 | ✅ 通过 | 本票防护网 = LRC 真实树门禁 + loop-runtime 套件：exit 0 / PASS / findings 空 + 62P+81sub/0F 实测；commit 门测试随物化转绿（§1.5） |

## 3. AI 专项 5 项检查

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | ✅ 不适用（零代码变更）；文档无伪造运行痕迹——所有数值经本席复跑命中 |
| 2 | 硬编码返回值 | ✅ 不适用；申报数值（308,248/62P+81sub/5 处 ragged）全部实测一致，无编造面 |
| 3 | 幻觉 API/事实调用 | ✅ 无——引用的 commit（9df2381/266c32b/7d6ff6a）、工具（check-loop-runtime-claims）、正则/白名单/行号（L1710-1720/L3145-3146/L672-673）均实存且经源码/实测核验 |
| 4 | 未实现 TODO | ✅ 无——diff 无 TODO/FIXME；无悬置声明 |
| 5 | 过度实现 | ✅ 无——恰 5 行 + 1 行，未顺手改 L41/L57-60 同形构造（parser 实测其不触发，克制正确）；未触碰审查结论字符面 |

## 4. 发现清单（全部 P3——不阻塞）

### F-A | P3 | 「全落 STRUCTURAL_DATA」口径不精确（本票可归因 delta 实测落点）

- **位置**：任务申报「semantic_units 306,085→308,248 全落 STRUCTURAL_DATA」；commit message 同族表述。
- **事实**：本票可归因 delta 实测 = REL 文件 0→3（abort 解除，3 units 全为 **NEGATIVE_NONCLAIM**）+ FIX 文件 4→4（其中 29:1 unit 由 UNKNOWN_STATE_PREDICATE 转 **STRUCTURAL_DATA**）——4 个可见落点为 NEGATIVE_NONCLAIM ×3 + STRUCTURAL_DATA ×1，**非字面「全落 STRUCTURAL_DATA」**；但全部为非 claim 良态（零 findings、零豁免面扩容），承载结论（无新 claim 类单元、预算内）成立。
- **建议**：后续申报改用「全落非 claim 良态（NEGATIVE_NONCLAIM/STRUCTURAL_DATA）」口径。

### F-B | P3 | pre-baseline 数字不可从现树复现（306,085 vs 306,504 双源不一致）

- **位置**：任务申报 306,085→308,248；commit message 306,504→308,248（306,504 与 R2 报告 L15/L43 记录值同源）。
- **事实**：以「现树 − 2 文件改动」最小差量重构 pre-total = 308,245（本票 unit delta 实测 +3：REL 0→3、FIX 4→4），两个申报 pre-baseline 均与之不符——差异（1,741~2,160 units）来自两次运行之间治理面写入等树漂移，无法事后归因。承载结论不受影响：post 值 308,248 精确命中、budget 达标、UNKNOWN 1→0。
- **建议**：pre/post 对比申报应同窗实测并注明时点，勿跨报告引用历史基线。

### F-C | P3 | 根因叙述两处措辞不精确（load-bearing 结论不受影响）

- **位置**：commit message「（fence 被扫描器跳过）」；任务上下文「（剔除了 L30-39 fence）」。
- **事实**：实测 fence 行 L31-38 **被记账**为 records 20-27（md_fence_line）且参与 29:1 序数算术（非「剔除」）；其不产 unit 的真因是该批 payload/context 无 claim-potential hint（`_has_claim_potential_hint` L1887-1893 + `_semantic_units_from_accounting` L976-987 过滤），非 fence 面整体跳过。精确表述：触发点在 prose L42（list_item），fence 行虽记账但不构成 unknown_state unit。映射声明 accounting:29:1 = 文件 L42 本身精确成立（§1.3）。
- **建议**：机理叙述以「记账但无 claim potential」替代「跳过/剔除」。

### F-D | P3 | L61 文字化后历史引述不再逐字（固有代价 + 连排歧义继承）

- **位置**：review-REL-086-RELEASE-R2.md L61（现行）。
- **事实**：原文列系 R1 落盘文本之引述，文字化后由 verbatim 引用降为构造描述——该信息无损（三字符构成由 L59 先例措辞 + 邻位 cell2「反斜杠原样追加」精确承载），且保留字面形式将复发同型触发（自指陷阱），属消除触发源的必然代价（与 7d6ff6a 先例一致）；「三字符形态 原样追加」连排的语义歧义系 R1 原文自身结构之继承，非本次改写引入。
- **建议**：无需动作；如后续再触碰该行，可考虑「……三字符形态，其反斜杠字符原样追加……」消歧。

### F-E | P3 | 「verdict PASS」为 semantic_only scope（commit message 未标注）

- **位置**：commit message「verdict PASS / exit 0」；CLI 实测 `verdict_scope: "semantic_only"`。
- **事实**：FIX-300/EVD-969 纪律下 semantic-only PASS ≠ Check 31 identity 全绿；identity 面在 R2 已 PASS（R2 报告 §2#4），非本票义务，无虚报——但裸引「verdict PASS」宜带 scope 限定。
- **建议**：后续申报写「semantic verdict PASS（scope: semantic_only）」。

## 5. Developer 申报核验对照表

| # | 申报 | 核验结果 |
|---|------|---------|
| 1 | ragged 非 1 处是 5 处；首错 abort 掩盖（findings 只报 L42） | ✅ 双版本全文件枚举精确复现 5 处〔pre: L42/43/44/45(3v4)+L61(1v3) → post: 0〕；abort 机理源码坐实（raise L672-673 → `_account_candidate` L919-922 整文件 discard） |
| 2 | 命中点不在 fence；真机理 = prose inline code-span 复述赋值 → state_slots 捕获 `cells` → 白名单外 → UNKNOWN_STATE_PREDICATE | ✅ accounting:29:1 → L42（list_item）精确映射；fence records 20-27 零 unknown unit；正则/白名单/分类三环源码+实测坐实（措辞精度见 F-C） |
| 3 | LRC verdict PASS / exit 0；UNKNOWN 1→0；→308,248 ≤ 361,923 | ✅ 全部精确实测命中（findings 空、exemptions_applied=4、余量 53,675）；pre-baseline 精度注记 F-B、落点口径注记 F-A |
| 4 | pytest 62P+81subtests/0F；commit 门测试 index 物化、pre 61P+1F → post 62P | ✅ 62 passed + 81 subtests passed（150.22s）实测；物化机理源码坐实（L1097 `:index` + L1116 assert PASS）；pre 61P+1F 为历史申报，与机理自洽，未独立复跑（如实注记） |
| 5 | 处置 (a) 不入 FIX-320 豁免账本（冗余 inline 断言 + expected_duration 要求改写后删除） | ✅ 理由链四点全部成立（§1.6）；账本实测维持 4 条、digest 锚未动 |
| 6 | commit 只含 2 任务文件、FIX-388 锁面未混入 | ✅ `--stat` = 2 文件 6+/6− = FIX-389 锁面；FIX-388 面零混入（工作树 2 修改为其未提交 WIP） |

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞数 | =0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5（§2） | ✅ |
| 每条发现标注级别 | 100% | F-A~F-E 均 P3 | ✅ |
| 设计一致性 | 已完成 | 与 7d6ff6a 文字化先例、FIX-320 处置 (a)/(b) 框架、FIX-300 semantic_only 纪律比对（§1.6/F-D/F-E） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5（§3） | ✅ |
| 只读约束 | 未修改产品代码/.governance | 审查对象零写入；实测脚本均在 %TEMP%；仓库内唯一输出 = 本报告 | ✅ |

## 7. 复审链终态声明

```
R0 (APPROVED_WITH_NOTES / unresolved_blockers=0, P0=0 P1=0 P2=0 P3=5)  ← 本报告——审查通过终态
```

本票为独立闭环审查（无前轮）；零 BLOCKING finding，不触发 M7.4 复审循环。Notes（F-A~F-E）均为申报措辞精度注记，供后续票引用口径时采纳，不构成返工义务。

---

*审查者：Code Reviewer Agent（FIX-389 派发）· 实测存档 %TEMP%\fix389_review\（scan.py / classify.py——含 LRC CLI 复跑、源码补丁式 ragged 枚举、accounting 映射、insert-only 字符级验证、pytest 定向）· 报告路径 docs/reviews/review-FIX-389-CODE-R0.md。证据基线：git show 9df2381(^) 双版本 diff/枚举 + check-loop-runtime-claims CLI（exit 0 / PASS / 308,248 / findings 空）+ pytest test_loop_runtime_claims.py（62 passed + 81 subtests passed）+ LRC 扫描器源码核验（loop_runtime_claims.py L515-576/L620-682/L1710-1720/L3145-3146）+ agent-locks.json 锁面对照。*
