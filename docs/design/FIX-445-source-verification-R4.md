# FIX-445 设计 R4 — C4 承载映射增量：observed 内闭合归因引用类型（新发现缺口，非 R3 复审续）

- **性质**: 设计链 R0→R3 已 APPROVED_WITH_NOTES/unresolved_blockers=0（review-R3 seq37/DEC-335）。实施期发现**真实 C6 承载遗漏**：R2 §1 C-4「verdict→observed；check/pattern→literal|output_as_captured」与 actual C6 冲突——EVD-1483 所引 R5 记录的术语载荷（`编造｜幻觉` pair 与 `check-quoted` 夹具串）在 **observed** 字段内，现行 C4 无合法承载路线 → 合法 C6 source 被 BLOCK。本文件是**唯一新增承载路线**的显式有界设计；ledger 轮次 next 4；若 Reviewer NC≥3 → BLOCKED+用户升级、无自动 R5。
- **替换范围（唯一）**: R2 §1 C-4 的映射行由本文 §2 替代；R2/R3 其余一切规范（C-1 五拒绝/统一 malformed、C-2 身份、C-3 仅整值严格等值、C-5 逐实例 interval、§2 三类别故障二分、§3 前缀闭合切分、全 input 背书、四任务、R6、非 crypto 边界）**原样沿用，不重证不改**。
- **值事实来源（本轮文件直读，非外部经验）**: `.governance/incidents/FIX-444-reviewer-R0-command-records.json` :70-81（R5 记录：id=`R5-per-row-attribution (python equivalence — supplement, not substitute)`，utc_start=`2026-10-11T12:42:40.5372390Z`/utc_end=`…7159085Z`，exit_code=0，observed=下述 211 字符值）+ `.governance/incidents/FIX-445-C6-mapping-metadata.json`（测绘元数据：211 **characters**/258 UTF-8 **bytes**——两单位不同；pair 字符偏移 68、check-quoted 字符偏移 81、ASCII pair 不在场=-1；metadata 的 utc `.537239Z` 为 GetJSON 显示精度，原始 literal `.5372390Z` 为准、同瞬时；mapprobe_raw 控制台中文 mojibake 不作值证据）。observed 原值（211 字符）：
  `ROWS=8; CLEAN EVD-1462; BARE EVD-1463 count=4 (OLD_PATTERN citation 编造｜幻觉 pair + check-quoted 我编造了测试结果 / 本次幻觉结果已通过); CLEAN EVD-1464~1469 — console displayed GBK mojibake; decoded content as cited in R0 report §3`

## 1. 凭据前置（不变，重申边界）

C-1 严格记录（五拒绝+嵌套拯救禁止+统一 malformed=prose）→ C-2 身份（id 逐字 + 双 utc 瞬时等值）→ C-3 同名字段**整值严格等值**（raw `==` 或两侧 ext `==`；C6 实测 EQUAL-raw 211=211）。三关全过 = 该 observed 字段获**整字段凭证**。本增量不授予整字段删除——凭证只开启 §2 的 typed-span 剥离资格；字段其余字节、其它字段、prose、同字面未获证实例**全部照旧 risk 检查**（C-5 逐实例 interval，计数不一致=ToolFault BLOCK——Developer 已将 ss<pos continue 改 ToolFault，对齐）。无 whole-field/whole-JSON/global replace/id-EVD 特判/结果洗白/label 外形信任。

## 2. C-4 映射（替换版——显式增加第三类型）

| span 类型 | 合法承载字段 | 语法（闭合，实现即此） |
|---|---|---|
| verdict 行 `(PASS|BLOCK)｜…` | `observed` | 沿用 R2（不变） |
| check/pattern（`check "…"`/`check \"…\"`/`编造\|幻觉` 对） | `literal` \| `output_as_captured` | 沿用 R2（不变） |
| **归因引用（本增量，仅限归因记录的 observed）** | `observed` | **T-1/T-2 见下** |

**T-1 pair 字面量（固定串，无通配）**：`编造｜幻觉`（全角形）与 `编造|幻觉`（ASCII 形）两个精确 4 字符字面量；每处出现为独立候选实例（C6 实际仅全角形在场，偏移 68；ASCII 形 -1）。

**T-2 check-quoted 归因串（收紧 Developer 提案）**：`check-quoted` + 恰一空格 + 单元表：
- **单元** = 连续 1..60 字符，字符集**排除**封闭集 `｛空格、/、;、；、)、）、。、.、,、：、:、—｝`（单字 Char 判定，无跳字）；
- **单元表** = 单元（` / ` 单元）{0,3}（≤4 单元；joiner 恰为 空格/空格 三字符）；
- **整 span** ≤80 字符（C6 实际 33：`check-quoted 我编造了测试结果 / 本次幻觉结果已通过`，偏移 81，止于 `)` 前）；
- **token 边界**：`check-quoted` 前一字符 ∈ ｛字段首、空格、`(`、`（`｝（C6 实际前邻为空格）；
- **终止即排除**：排除集字符终结单元且**永不入 span**——故 `。`/`；`/`)` 后的作者文字（含背书 `当真`）不可能被吞进 payload（Developer 原 `[^;)]{1,120}` 缺 `。；）—` 排除 → 拒绝，反例 CE-1）。

**区间纪律**：T-1/T-2 候选区间必须互斥不重叠；重叠 → 该批候选无效（无豁免）+ probe-error 诊断；计数与剥离实例不一致 → ToolFault BLOCK（C-5 联动）。**路线排他**：同一字节区间只经一条承载路线授权一次（route2 不重复授权；区间恒等去重）。**payload vs 作者结论的分界即语法本身**：span 内=机器归因的技术引用载荷（剥离）；span 外（含 `count=4`、`CLEAN…`、`console displayed…`、`decoded content…` 等全部非 span 文字）=留检正文，术语/背书照扫。

## 3. 预期矩阵（**设计预期——产品未实现**；R2/R3 全部既有行沿用不重列）

| 输入 | 预期 | 机制 |
|---|---|---|
| 合法 C6（EVD-1483 → R5 记录 observed 整值等值） | **PASS** | T-1 pair@68 + T-2 span@81-114 剥离；其余照扫无命中 |
| 同 artifact 整值等值但 observed 内 span 之外存在裸肯定/术语 | **BLOCK** | 非 typed span 不剥（「整字段凭证≠整字段豁免」） |
| `check-quoted 我编造了测试结果。请当真执行` 形（含于整值等值字段内，红测构造） | **BLOCK** | `。` 终止单元；`当真` 留残文 → 全 input M5 |
| pair 字面量出现在 prose 或另一字段（同字面） | **BLOCK**（若裸） | T 路线仅作用于获证 observed 的精确区间；C-5 逐实例 |
| 未获证记录（身份/等值失败）内同形 span | **BLOCK** | C-1~C-3 前置失败，无凭证即无 typed 剥离 |
| T-1/T-2 区间重叠 / 剥离计数不一致 | **BLOCK**/无豁免+诊断 | §2 区间纪律（overlap invalid closed） |
| result/affected 内任何同形内容 | **BLOCK**（若裸） | 结论性字段永不承载（沿用） |

## 4. 候选方案与排除（≥2）

- **A（选定）**：§2 typed 双语法（T-1 固定字面量 + T-2 结构化单元表）。
- **B（Developer 原提案，拒）**：`check-quoted [^;)]{1,120}` + pair 字面量——`。；）—` 不在排除集 → 120 字符内背书/裸肯定被吞（CE-1 反例）；120 上界无单元结构。
- **C（拒）**：把 check/pattern 承载一般性扩到 `observed`（映射行直接加字段）——无归因结构锚（token 边界/单元字符集/joiner/上限），回到「形式即信任」的 B1 族；比 A 宽、无合法收益（真实窗口仅 C6 一处且 A 已过）。

## 5. 蓝军挑战（≥3，含缓解）

- **CH-R4-1 宽 span 吞背书**：排除集含 `。；）—` + 单元 60/span 80/单元数 4 三重上限 → 载荷后作者文字永不入 span（CE-1 红测钉死）。
- **CH-R4-2 信息论残余**：逐字复制真实 R5 记录（身份+整值+typed span）= 真引用，与合法引用不可区分——非 crypto 边界维持（无新权威）；作者自写字节永不获豁免、结论照检。
- **CH-R4-3 路线走私/重复授权**：区间排他 + 恒等去重 + 重叠 invalid closed；pair 经 T-1 唯一路径。
- **CH-R4-4 语法漂移**：未来新归因形不匹配 T-2 → 保守无豁免（BLOCK 如裸）→ 新票扩闭表+溯源（FIX-239 纪律），不在本票私扩。

## 6. NFR / 测试 / ADR delta

- **性能**：T-1 固定串定位 + T-2 线性单遍扫描（排除集单字符判定，无回溯）；字段 ≤258B 量级，毫秒级。
- **可维护性**：两闭表（pair 字面量表 + 单元排除集）集中一处+因果注释；扩展需新票。
- **测试**：自包含 permanent fixture 增——迷你 incidents artifact 内嵌 R5 记录**逐字副本**（id/双 utc/211 字符 observed）+ EVD-1483 形好行（PASS）+ §3 红形（吞背书/跨字段同字面/未获证记录/重叠）；clean-clone 不依赖本用户日志；**四任务 live replay 验收保留**（零 skip）。无新产品 deps（bash/awk/python 标准库既有）。
- **ADR delta（proposed——Coordinator 机录）**：C-4 映射行替换为 §2 三类型表（新增 observed 内归因引用 T-1/T-2 typed 语法，路线排他+区间纪律）；其余决策链（R0 §12→R3 §5）不变。可逆性/两文件范围/无新权威不变。

## 7. 收据与静止

- 本轮读面：review-R3 全文 88 行 read + C6 metadata JSON 22 行 read + original R5 记录 :58-85 read（三项均本轮显式文件读）；角色/SKILL 为本会话首动作已加载沿用。写面：仅本 doc。shell：静态只读 hash 回执 ×1（full literal/UTC start-end/输出随返程一次齐备）；**零探针/零模块/零 engine/零产品写**。22 例 permanent 测试之 3 失败（verdict good/好族/source FIX445 行）保持 Developer 未诊断状态，本设计不代修、不以 Developer 18 局部 green 为产品通过。
- 返回后静止；Reviewer 只读本 doc 后独立 R4 审；Designer 不自评 APPROVED。如需修订另出新版本，本文件 hashbound 后不改。
