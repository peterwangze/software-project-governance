# FIX-445 — R12 限定修订设计：逐次出现来源资格与契约修正（DEC-345；R11 delta）

```json
{"role":"Architect (producer, not reviewer)","round":12,"scope":"r11_delta_revision_per_dec345",
 "supersedes":"R11 §6.2 occurrence句 / §6.3 / §6.5 / §6.4资源与路径句 / §6.6部分 / §6.7(5) / §7④ / §8.2迁移态全称 / §8.4:349锚定句 / §11性能spawn句",
 "product_implemented":false,"product_authorized":false,"migration_authorized":false,
 "self_approved":false,"implementation_ready":"pending independent R12 review + separate product authorization",
 "fix445_status":"blocked (unchanged)"}
```

- **日期**: 2026-10-13（Coordinator 供应）。**唯一写面**：本文件；R11 原件（SHA `5eaf97d0…`，frozen-bindings 证未改）与全部历史冻结。
- **授权（DEC-345）**：仅本新版本设计 + 一次独立 R12 审查；harness 轮数 8→16（goal rev4 active/armed、bridge 8/16）。**不是**产品实施、registry/迁移授权或风险接受。无自动 R13。

---

## 0. 基线与替换关系

R11 为基线规范；本文件只替换 §"supersedes" 所列节/句，其余 R11 条款（含 §0 不变项、§1 评价标准 1–10、§3 现状、§4 调查、§5 包含困境、§6.1 模块、§6.8 W1 规范算法——R11 审查已确认其无歧义、§9 备选基线、§10/§12/§14/§15、附录 A 原三行）**原样沿用**。不变项重申：原三行零编辑；四任务源非零/hashbytes/latest/zero skipped/RC0；12 攻击与 R8/R9 反例逐例拒绝；B3 五 env 保护；CPU27.8s/CLI36s/434339 semantic/32MiB/1500 不重测不放宽；两产品文件边界；T2/Guard G/M5/R3 prefix 零改动；迁移（Mig-A/B）维持未授权。

## 1. 本轮实际输入与事实

**本轮实读 6 文件**（零 shell/零执行/零实验/零治理写/零子 agent/零用户交互；未读热面——热事实 Coordinator 单源供应）：

| # | 文件 | 规模 | 要点 |
|---|---|---|---|
| 1 | `docs/reviews/review-FIX-445-DESIGN-R11.md`（机录版，SHA `8e542f5c…`） | 145 行 | BLOCKED/3（B1/B2/B3）+3W（W1/W2/W3），C-B1..C-W3 解除条件 |
| 2 | `.governance/incidents/FIX-445-DesignR11-returned-v2.md`（SHA `c0b64bbe…`） | 145 行 | 同结论 BLOCKED/3+3W；findings 实质与机录版一致 |
| 3 | `.governance/incidents/FIX-445-DesignR11-transfer-audit.json` | 43 行 | 六行转录差异逐行列明（空格/补词「节」「绝」「无F25补位」「直接写」级） |
| 4 | `.governance/reports/FIX-445-R11-escalation.md` | 58 行 | DEC-345 前置升级与 B2 解除要求：「证明通用逐次出现来源资格…不能白名单特判或接受 replay 风险」 |
| 5 | `.governance/incidents/FIX-445-R11-artifact-check.json` | 73 行 | 三 clause 极大候选与双区间（字符/UTF-8 字节）机测值 |
| 6 | `.governance/incidents/FIX-445-R12-frozen-bindings.json` | 39 行 | hook/tests/R11design/机录review/返v2 五件 SHA 全 match；`tests_executed:false` |

findings 引用以机录版为准；返 v2 六处差异经 transfer-audit 一手核对均为转录级，两版 findings 实质一致；Coordinator 补词不作 Reviewer 原话（escalation §转录校准）。Coordinator 单源供应：DEC345 机录、goal rev4/armed、pwsh24 健康 16 issues/exit1（EVD1674）、暂存区空、执行包 budget32 只读投影、包内 DEC342 陈旧 assumption 已由 DEC345 替代。**沿用本 agent 会话上下文的 22 源全文**（R10 三件套、R0 七类 mapping、R3 prefix、R5 GuardG、DEC336 只读 helper、R4 escalation、三冷原行 source-extract、CODE-R6、canonical hook 1284 行 + test_hooks.py 1480 行、角色/SKILL 两件）——其中五件经 frozen-bindings 机证未变，其余为冻结历史；上下文无缺，不以摘要代读。产品 SHA 沿冻结绑定：hook `c7d5a01f…85461f` / tests `60fe5db5…9d0db`（本轮零 shell 未自测 hash，机件为源）。

## 2. R11→R12 差异总表

| R11 finding | R12 响应 | 替换/新增 |
|---|---|---|
| **B1**（§8.4:349 去重锚定例三重矛盾） | 锚定例修正为 23 条贡献/无 F25 补位（§7） | 替换该锚定句 |
| **B2**（合法注册 clause 被新断言上下文逐字复用即获免） | **逐次出现凭据 POC**：邻接上下文等值 + 出现序预算双棱（§3）；§8.2 全称声明撤回并限定（§8） | 替换 R11 §6.2 occurrence 句、§6.3；新增 §3 |
| **B3**（raw 偏移「字节」错误） | 码点索引契约 + 双区间钉死测试锚（§4） | 替换 R11 §6.5 |
| **W1**（缺席/悬空/目录/TOCTOU/权限欠规格） | 闭分类表 + MREG 诊断 + 部署自检（§5.2） | 替换 R11 §6.7(5) 交互语义 |
| **W2**（registry 自身路径纪律矛盾） | 固定 authority path 例外 + `registry-path` 故障码（§5.1） | 替换 R11 §6.4 路径句 |
| **W3**（entries/registry 字节/carrier/每 spawn IO 无界 + corpus 来源歧义） | 显式界值表（有据）+ 双读面 P1/P2 + 单读缓存 + 超界二分（§6） | 替换 R11 §6.4 资源面、§7④ |
| **W1b**（新增，Coordinator 指出：R11 §11「缺席/空→零 spawn」vs §6.7(5) 在场空 entries 仍 spawn） | 三态调用语义：缺席=零 spawn；**在场（含 entries=[]）+触发=一次 spawn/零豁免**（§5.3）；性能声明改写（§11） | 替换 R11 §11 性能 spawn 句 |

## 3. D-B2 — 逐次出现凭据（Per-Occurrence Credential, POC）

### 3.1 凭据元组与豁免合取

registry 条目（v1 形状，**取代** R11 草案形状；version 仍为 1——R11 草案形条目缺新必填字段将被 §5.2 schema 检查自动硬拒，防误用）：

```json
{"clause":"…4..200码点","task_id":"FIX-445",
 "left_context":"…空串或1..256码点","right_context":"…同左",
 "max_occurrences":1,              // 1..8
 "carrier_kind":"frozen_doc|command_record","carrier_path":"…三前缀内",
 "carrier_record":{"id":"…","utc_start":"…","utc_end":"…"},
 "carrier_field":"literal|output_as_captured|observed",
 "adjudication":"DEC-xxx","archive_policy":"deactivate-on-archival","registered_at":"RFC3339"}
```

一个 M 候选出现获豁免，当且仅当以下**全部**成立（任一不成立→该出现留守残文→原 M5/术语路径照判）：

- **C1** registry 已加载且合法（§5.2 分类；缺席=惰性零豁免）。
- **C2** 条目匹配：`task_id` 相等 ∧ `clause` 码点串相等。
- **C3 邻接上下文等值**：候选的左邻 clause 与右邻 clause（§3.2 定义）码点串分别 `== entry.left_context/right_context`（空串为合法登记值）。
- **C4 出现序预算**：该条目三元组 `(left_context, clause, right_context)` 在本任务行批（evidence-log 行序）中的**累计出现计数 c ≤ max_occurrences**；计数对三元组逐字匹配递增，与载体验证成败解耦（载体失败的槽位不把后继复本顶入资格）。
- **C5** 载体验证（R11 §6.3.3 沿用，全部改码点语义：载件 UTF-8 解码后做码点包含）。
- **C6** `adjudication` 非空且格式合法。

**mention/assertion 范围语义**：mention 资格只授予「在冻结出现位点（由邻接上下文 + 出现序联合刻画）逐字复现的已裁决出现」；任何新出现——新上下文（C3 拒）或新时序位置（C4 拒）——一律按 assertion 处理（留守全扫）。本机制**不含任何负向短语黑名单**（断言前缀从不被枚举/禁止；绑定全为正向等值）。

### 3.2 邻接上下文定义与三原行登记样例值

左/右邻 clause = 与 M 候选同一边界函数（isterm 闭集 ∪ `|`，R11 §6.2 沿用）切出的**相邻** clause；界：空串或 1..256 码点，超界不可登记（schema 拒）→ 出现不可豁免（保守）。三原行的登记样例值（供 R12 审查与未来迁移票核对；**登记本身未授权**；码点数迁移时 机检）：

| 行 | clause X | left_context | right_context |
|---|---|---|---|
| EVD-1536 | `无预算或PASS编造`（10cp） | `目标含先设计后twofile修及最终交付` | `原门CPU27.8/CLI36/semantic434339/32MiB/1500与installedhook/用户config保持` |
| EVD-1587 | `已知no-separator当真不能默当获准安全残余`（26cp） | `onlyR4A封闭允许字符集和对应五变体/控制字符回归` | `要具体closedguard` |
| EVD-1588 | `载荷含把将当作当成视为作为当真任token整span拒免`（28cp） | `closed单元whitelist U4E00..9FFF与ASCIIalnum/符号集合空` | `sourceC6合法载荷无token` |

（样例值由 source-extract 原行按边界函数手工切分；artifact-check 已证各 X 即 R11 §6.2 极大候选且 appendix 出现次数=1。）

### 3.3 出现序预算语义

- 批 = 该任务全部 evidence 行，按 evidence-log 文件行序（append-only 时序）；同行多处按位置序。
- 每条目独立计数器；仅三元组逐字匹配递增；豁免要求 c ≤ K（K=max_occurrences）。
- **先占位**：注册出现（原行）在批内先于任何后继复本——由日志 append-only 纪律保证。若存在更早的同三元组出现，登记 ordinal 以迁移时**机检实值**为准（本轮未对热 evidence-log 复核——禁读热面；沿 R11 §4 scoping：三 clause 在证据行内仅原行出现；此为**待机检假设**，非已证事实，见 §12）。

### 3.4 与 canonical per-instance 纪律的同构

POC 是 prose tier 的 per-instance 纪律：`test_hooks.py:800-806`（`test_same_literal_second_instance_unverified_blocks`——「已验证 literal span 不清除同字节 prose 二次出现」）在 M 腿的对应物。C4 即出现实例计数，与 record tier C-5 的逐实例删除计数、`mcount-mismatch` 同族同哲学。

### 3.5 非退化论证（对「不可退化白名单/特判」约束）

凭据维度 = 内容（clause + 邻接上下文）+ 时序（出现序）+ 任务域 + 载体链。**不含** EVD id、行号、行哈希、任务名白名单、单例分支；任意出现均可被权威登记，机制对任意 (行, 出现) 通用。对照被禁形态：≠ task/EVD/整行/hash/ID 白名单（不引用任何标识符）；≠ 单例特判（无「若为某行则通过」分支）。R11 审查 BR-1 建议的「EVD 行/冻结位点锚定」其**字面形态**（条目携带 EVD id/行号）即退化为本约束所禁——本设计吸收其「钩验出现位置而非仅字节」的精神，以**时序 + 结构位点**实现位置验证而不引入标识符（详见 §9 Alt-2 排除理由）。

### 3.6 组合反例逐行推演（迁移态；R11-B2 闭合证明）

**M3 断言前缀组合**：`我确认以下断言且并非引用：已知no-separator当真不能默当获准安全残余`（同 task 新增纯 prose 行）
① `：` ∈ isterm → 候选 clause = X（26cp，触发 `当真`）；② C2 过（clause/task 相等）；③ **C3 拒**：实际左邻 = `我确认以下断言且并非引用` ≠ 登记值 `onlyR4A封闭允许字符集和对应五变体/控制字符回归`；④ 无豁免 → X 留守 → sed 无术语可剥 → M5：`当真` 命中，最近 isterm 前缀窗 = `已知no-separator`（14cp），`已` 不在 24-否定/19-填充表 → 残留 → bad → **BLOCK**。残文中的断言前缀自身无术语/框架（speculation grep `我确认` 不匹配）——但单独无害即足够：X 不再被清除，整行被 X 阻断。

**M4 上下文逐字复制**：新行逐字复制 `…。onlyR4A封闭允许字符集和对应五变体/控制字符回归，X，要具体closedguard；…`
① 候选 X；② C2 过；③ **C3 过**（左右邻逐字相等）；④ **C4 拒**：三元组批内出现计数 = 2（原行 EVD-1587 在日志更早处 = #1，本复本 = #2）> K=1 → 无豁免 → X 留守 → M5 同上拒 → **BLOCK**。攻击者无法把复本置于原行之前：那需要对 append-only evidence-log 的直接改写/重排 = CH-1 界（与现行**全部**门同一完整性假设——今日攻击者直接改 evidence-log 同样可绕过一切现有扫描）。

**边界如实**：① 归档时序通道——若原行被归档移出 live log 而攻击复本留存，复本可能成为计数 #1 → 见 BT-R12-1（契约缓解 + 残余披露，不冒充机闭）；② registry 写权威 = CH-1 级（BT-R12-2）；③ 登记出现自身的语义审查（注册的 X 是否实为断言）= 迁移裁决责任，非运行时可判。

## 4. D-B3 — 码点索引契约（替换 R11 §6.5）

1. M 腿全部索引、长度、界与包含判定在**解码后 python str（码点）**上进行，与 canonical `regions()`(:445)、`top_string_fields`/dmap(:239-332)、`dels`(:637-655) 同轴；R11「字节偏移」字句**作废**。删除 = 行 str 的码点切片 `[cs,ce)`，与 record tier `dels` 合并后走既有排序/重叠/计数校验（`deletion-overlap`/`mcount-mismatch`）。
2. 「字节」仅用于相等性表述：str 相等 ⇔ 规范 UTF-8 字节相等（registry clause 存解码串；载件 UTF-8 解码后码点包含；两探 `_ext` 归一纪律沿 R11）。
3. 界均码点：clause 4..200；left/right_context 空或 1..256；max_occurrences 1..8。
4. **钉死测试锚**（artifact-check 机测值，实现票必测）：EVD-1536 X=char[1148,1158)（10cp）/bytes[1866,1888)（22B）；EVD-1587 X=char[428,454)（26cp）/bytes[828,882)（54B）；EVD-1588 X=char[572,600)（28cp）/bytes[954,1020)（66B）。断言：引擎产出**字符区间**；删除后行结构完好；字节区间作**负锚**（断言引擎不按其切片）。

## 5. D-W1/W1b/W2 — registry 调用语义、缺席/故障闭分类与固定 authority path

### 5.1 固定 authority path 例外（W2）

registry 自身 = **常量** repo 相对路径 `.governance/mention-registry.json`：非数据驱动、无 glob、无前缀展开。对其只施加：常量构造（绝对形/`..` 天然不存在）+ realpath 落仓内（新故障码 **`registry-path`**：解析出仓 → ToolFault）。**三前缀闭集（docs/reviews/、.governance/incidents/、.governance/reports/）只作用于条目 `carrier_path`**（R11 §6.3.3 沿用：前缀内、拒绝对/`..`/evidence-log.md、检查先于 open、realpath 仓内）。registry 路径不在三前缀内 ⇒ 条目以 registry 自身为载体被前缀检查自动拒绝，无需特判。

### 5.2 缺席/故障闭分类（W1）+ MREG 诊断

| 情形 | 判定 | 方向 |
|---|---|---|
| FileNotFoundError / ENOTDIR / 悬空符号链接 open ENOENT / 预检后 TOCTOU 被删 | **MREG=absent**：M 腿惰性、零豁免、**非故障**（合法部署前态）；DIAG 必发 `MREG=absent`（可见，不静默） | 保守可用性向 |
| 路径为目录（IsADirectoryError） | ToolFault **`registry-notfile`**（在场非普通文件=部署错误） | BLOCK |
| PermissionError / 其它 OSError / UnicodeDecodeError | ToolFault **`registry-read`** | BLOCK |
| 文件 > 256 KiB（§6.1） | ToolFault **`registry-oversize`** | BLOCK |
| strict-parse 失败（重复键/非标常量/部分消费/非对象） | ToolFault **`registry-malformed`** | BLOCK |
| schema 违规：未知键/缺必填（含 R11 草案形条目——缺 left_context/right_context/max_occurrences）/entries>64/clause∉4..200/context∉空或1..256/K∉1..8/carrier_path 形非法/adjudication 空 | ToolFault **`registry-schema`** | BLOCK |

bash 侧存在预检（`[ -f ]`）仅为 spawn 优化；**引擎分类为权威**；预检 false 类（悬空链接/目录）与 absent 同收敛（零豁免，M5 仍看护受污染 prose——无假 PASS 通道）。BT-5 措辞相应修正：缺席类=惰性+诊断可见；故障类=硬断。**部署自检**：迁移/实现票必须含一步断言 `MREG=loaded ∧ entries=N`（票内 TODO，非运行时门）。

### 5.3 三态调用语义与 spawn 记账（W1b）

bash 侧引擎调用条件 = `record 非空` OR（registry 路径 `-f` 为真 AND prose 触发预检命中）。三态：

1. **registry 缺席**（`-f` 假）→ 纯 prose 零 spawn（CH-7 保持）；
2. **registry 在场**（任意内容，含 `entries=[]`）且触发 → **一次 spawn**：加载/判空/校验，零豁免（空 entries）或按 §3 判定；
3. record 非空 → 现状 spawn（不变）。

R11 §11「缺席/**空**→零 spawn」中「空」字**作废**——在场空 entries 是一次 spawn/零豁免，不是零 spawn。性能门不放宽；新 spawn 面计入实现复测（§11）。

## 6. D-W3 — 显式资源界与双读面

### 6.1 界值表（设计界 + 依据 + 超界语义；实测=实现票待办，与设计措施分列）

| 界 | 值 | 依据 | 超界 |
|---|---|---|---|
| entries | ≤64 | 迁移需求 3 条 + 在账任务量级 34（bootstrap 单源）+ 2× 余量 | `registry-schema` BLOCK |
| registry 文件 | ≤256 KiB | 64 × 最坏条目（clause 200cp×3B + 双上下文 512cp×3B + 元数据≈0.4KiB ≈2.6KiB）≈166KiB，取幂余量 | `registry-oversize` BLOCK |
| 单载体文件 | ≤2 MiB | 既有 docs/reports 冷工件为数百行/数十 KB 量级观测 + ≥10× 余量（**非全量实测**，实现票实测） | 条目不可用（保守） |
| 每 spawn 载体 ΣIO | ≤8 MiB | 4× 单载体界；交叠路径单读缓存后实际更低 | 超预算载体不可用 + 诊断 `MBIO=`（保守跳过） |
| 内存驻留 | 载体逐条「读-检-释」，不跨条目累积；峰值 ≈ corpus 面 + max(单载体) + registry | 有界驻留策略 | —（32MiB/1500 原门：**实现票强制复测**，含新 spawn 面与界值实测） |

### 6.2 双读面（消除 §6.3.3/§7 载体来源歧义）

- **P1 = record-tier 凭据语料**：W1 分配（per-line 8 refs / 独立 glob 24 合并前 / 总池 32 / 不补位 / GLOBCAP、POOLCAP 与 PATHDROP 分列）——R11 §6.8 原样（审查已确认无歧义），仅供 `credential()`。
- **P2 = M 载体面**：registry 声明路径（三前缀 + realpath 仓内 + 逐条 2MiB + Σ8MiB），仅供 `verify_mention()`。
- **P2 不要求载体入选 P1**：W1 容量截断不削减 M 资格（消除「直接验=无界 vs corpus-only=不可验」两读法：载体资格=登记+前缀+界，与语料池成员资格解耦）；P1 成员亦不自动成为载体。交叠路径按 resolved path 单读缓存（一次读/解析，两面共用）。R11 §7 流程图④ 相应改为「P1 供 ②（credential）；P2 供 ③（verify_mention）；交叠单读缓存」。

### 6.3 超界语义二分

authority 面（registry 自身）超界/损坏 = 硬 ToolFault（权威完整性，§5.2）；carrier 面 = 条目不可用（内容类，沿 R2/R7 内容-工具二分——R11 审查已认可该分类先例）。

## 7. D-B1 — W1 去重锚定例修正（替换 R11 §8.4:349 锚定句）

**修正后锚定例**：若 refs 已含 F09（合法 `_REF` 形——refs regex 含 incidents 路径），glob_sel 仍为 **F01..F24**（F09 占其排序槽位，独立 cap 先于合并不变）；pool 的 glob 贡献 = F01..F08 ∪ F10..F24 共 **23** 条——重复槽位不回收、**无任何补位**；F25 ∈ glob_all[24:] 在任何情形下不可入选。pool = 32 refs + 23 = 55 → files = pool[:32] = **32 refs**（F09 经 refs 仍在语料中，其凭据可用性不受损）；诊断 **GLOBCAP=8、POOLCAP=23、PATHDROP=0**。focused tests 必须同时断言：① glob 贡献数=23（非 24）；② F25 ∉ files；③ F09 在 files 中恰一次（经 refs）。R11 §6.8 规范算法不变；W1-Ex1/2/3 三例经 R11 审查独立重算全部正确，沿用。

## 8. 更新验收矩阵（delta 行；R11 §8 其余行沿用，但其 §8.2「迁移态全部攻击仍拒」全称声明**撤回**，限定为：未注册串（M6）+ 已注册组合（M3/M4）+ 跨任务/变形（M5、R11-A1/A2）均机制性拒绝；残余=registry 写权威与归档时序通道，按 CH-1 级披露、不作全称声明）

| # | 输入 | 状态 | 预期 | 机制 |
|---|---|---|---|---|
| M1 | 原三行（R11 附录 A，零编辑） | 空态（现授权态） | **BLOCK**（与现状等价） | registry 缺席，M5 原路径拒（R10 三重机录） |
| M2 | 同上 | 迁移态（POC 登记三出现，K=1） | **PASS** | C1–C6 全立；X 删除后行内唯一阻断消失（CODE-R6 :42-44 判定各行唯一失败机制）；ordinal=1 为迁移时**机检**项（§3.3/§12） |
| M3 | `我确认以下断言且并非引用：已知no-separator当真不能默当获准安全残余` | 迁移态 | **BLOCK** | C3 拒（左邻≠登记值）→ X 留守 → M5 窗 `已知no-separator` 残留（§3.6 逐步推演） |
| M4 | 新行逐字复制原句 `…回归，X，要具体closedguard…`（同 task） | 迁移态 | **BLOCK** | C4 拒（三元组计数 2>K=1）→ X 留守 → M5 拒（§3.6） |
| M5 | M4 变体置于其他任务行 | 两态 | **BLOCK** | C2 任务域拒（R11-A2 沿用） |
| M6 | R9/R8 字面攻击（未注册串）、12 synthetic | 两态 | **BLOCK** | 无条目（R11 §8.2/8.3 沿用） |
| M7 | registry 在场 `entries=[]` + prose 触发行 | — | **一次 spawn、零豁免、判定=现状** | §5.3 ②（W1b 钉死） |
| M8 | registry 悬空链接 / 预检后被删（TOCTOU） | — | MREG=absent 惰性零豁免（诊断可见） | §5.2 行 1 |
| M9 | registry 为目录 / 不可读 / >256KiB / 坏 parse / 坏 schema | — | 对应 ToolFault → BLOCK | §5.2 闭表 |
| M10 | 载体漂移 / 单件>2MiB / ΣIO 预算尽 | — | 条目不可用 → 候选留守 → 行级保守（MBIO 诊断） | §6 |
| M11 | 码点钉死（artifact-check 双区间 × 三行） | 实现票 | 引擎产出=字符区间；字节区间=负锚 | §4.4 |
| M12 | W1 三例 + 去重锚定例（F09∈refs） | 实现票 | Ex1/2/3 沿 R11 + 锚定例 23 条/无 F25/F09 恰一次 | §7 |

## 9. 替代方案（预定义标准先列，后比较；R11 §9 A–F 基线沿用不重复）

**标准（R11 §1 十条 + 新增三条，先于比较）**：11) B2 组合反例（断言前缀+注册 clause、上下文逐字复制）在迁移态被**机制**拒绝；12) 不退化为 task/EVD/整行/hash/ID 白名单或单例特判；13) 单位契约与 canonical 码点体系同轴。

| 方案 | 判定 |
|---|---|
| **Alt-1 POC 逐次出现凭据（选定，§3）** | 满足 1–13（M1–M6 机制性；无标识符维度；码点契约 §4）；残余=归档通道/写权威（披露非机闭，BT-R12-1/2） |
| Alt-2 EVD 位点/行号锚定（R11 审查 BR-1 建议的字面形态） | **排除**：条目携带 EVD id/行号=标识符位点白名单，直接违标准 12；归档/重排使行号漂移（脆弱）；吸收其「验位置」精神→时序位点（§3.5） |
| Alt-3 显式 replay 风险裁决（R11 审查 C-B2 选项 b） | **排除**：DEC-345/escalation 明示「不把单纯风险披露作为修复」「不能接受 replay 风险」——纯披露不满足标准 11 |
| Alt-4 整行字节绑定（行级白名单） | **排除**：违标准 12；且整行复制仍可绕（复本即白名单行） |

## 10. 蓝军挑战（≥3；R11 BT-1..6 沿用，BT-2/BT-5 措辞按 §5 修正）

| # | 挑战 | 响应 | 残余 |
|---|---|---|---|
| BT-R12-1 | **归档时序通道**：原行被归档出 live log 而攻击复本留存 → 复本成计数 #1 → C4 不拒 | ①`archive_policy:"deactivate-on-archival"` 为**必填**字段：归档涉及含注册出现的行时必须同步 deactivate/re-anchor（治理侧强制步骤，入迁移票验收与归档流程检查单）；②live 四任务源门（seen≥1/零 skip/RC0）对原行缺席显式暴露；③原行若被归档而复本在，M2 期望失效会被 M12 类测试暴露 | **过程+契约缓解，非运行时机闭**——时序绑定固有界，与 append-only 日志完整性同级（现行全部门同依赖）；如实披露不冒充 |
| BT-R12-2 | registry 写权威滥用（ illicit 注册攻击 clause 或虚增 K） | 仅 Coordinator 机器路径 + DEC 引用 + 独立对抗复核（复核**必须显式执行 M3/M4 类反例推演**）；diff 可见；空态零暴露 | CH-1 级接受边界，非密码学声明 |
| BT-R12-3 | 上下文/预算穷举绕过（改上下文/复制上下文/跨任务/同行多次/前后置断言/字节变形） | 逐项映射 C2–C4 拒绝（§8 M3–M5、R11 A1/A2）；未知形=保守留守 | 无已知绕过 |
| BT-R12-4 | 资源界即 DoS 面 / spawn 面回归 | §6 界+二分超界+逐条释放；M7 三态钉死；原门不放宽 | 界值实测与原门复测=实现票待办 |
| BT-R12-5 | 机制在实践中只用 3 条=实质单例 | 通用性是结构属性（任意出现可登记，无特判分支）；实际用量=权威选择 | 非安全缺陷；如实标注 |

## 11. NFR / 版本 / 回滚 delta

- **性能声明（替换 R11 §11 性能行）**：缺席=零 spawn；**在场（任意内容含空）+触发=一次 spawn**（空则零豁免）；record 面=现状。新读面=registry ≤256KiB 一次 + 载体 Σ≤8MiB（逐条释放）。CPU27.8/CLI36/434339/32MiB/1500 **不重测不放宽**；实现票强制复测（含 W1b 新 spawn 面与 §6 界值实测）。
- **registry schema**：version 保持 1；本文件 §3.1 形状取代 R11 草案形状（旧形条目被 §5.2 自动硬拒）。DIAG 增 `MREG=absent|loaded`、`MBIO=`。
- **回滚**：不变（R11 §12）：revert 两文件单 commit + 删/清 registry 单件；无数据迁移；历史零触碰。

## 12. 限定可行性结论（设计静态正确性与产品/迁移资格分开）

1. 在「append-only 证据日志 + registry 只经裁决产生 + 载体在环」三前提下，**零改原三行、通用逐次出现资格、全部已证攻击拒绝三者可同时成立**（§8 M1–M6 机制性推演）——此为**静态设计结论**，非实施就绪、非产品通过。
2. 未解事实（如实，不伪造可行契约）：① ordinal=1 假设未对热 evidence-log 复核（禁读热面；沿 R11 §4 scoping + artifact-check appendix 出现次数=1）；迁移时**机检**为强制步骤，若实值≠1 则按实值登记（机制通用支持）。② 归档时序通道=过程+契约缓解非机闭（BT-R12-1）。③ registry 写权威=CH-1 级。④ 迁移（Mig-A/B）与产品实施均未授权。⑤ 界值实测、12 B2 逐例、B3 处置、64 tests、性能原门复测=实现票待办。⑥ 不宣称所有有限语法不可能——本设计只证明本契约在前提内自洽。
3. implementation_ready = **pending 独立 R12 审查 + 另行产品授权**；本设计不使 FIX-445 任何验收项通过；R11 BLOCKED 记录不覆盖；无自动 R13。

## 13. proposed ADR delta（Coordinator 写回；本文件只出草案）

- **标题**: ADR-FIX-445-R12 — M 腿来源资格升级为逐次出现凭据（POC：邻接上下文等值 + 出现序预算）；W1 锚定例/码点契约/registry 路径与故障分类/资源界双读面/spawn 三态六项契约修正
- **日期**: 2026-10-13
- **背景**: R11 审查 BLOCKED/3+3W（B1 锚定例矛盾、B2 合法 clause 断言复用逃逸、B3 字节/码点混淆、W1/W2/W3 + W1b spawn 过声明）；DEC-345 限定修订 + 独立 R12。
- **决策（proposed）**: 采纳 Alt-1 POC（§3）；§4–§7 契约修正；R11 其余条款沿用；迁移/产品维持未授权。
- **备选/排除**: §9（Alt-2/3/4；R11 A–F 基线）。
- **影响范围**: 同 R11（两产品文件 + registry 数据面）；无门弱化。
- **后续动作**: 独立 R12 审查（强制注入：R11 设计/机录审查/返 v2/transfer-audit/artifact-check/escalation + 本文件）；用户裁决迁移三问（R11 §13.3 沿用）；实现票含 §6 实测与 M7/M11/M12 钉死测试。
- **可逆性**: 可逆（§11）。

## 14. 自检与过程披露

- 硬门槛：备选 **4≥2**（新增集，标准先列）+R11 基线 6；蓝军 **5≥3**（BT-R12-1..5 均有响应与残余标注）；ADR 字段完整（§13）；模块无环（POC 消费 M6b 候选与 P2 面，产出删除区间并入 M3 既有校验，无新环）；接口输入/输出/类型/验证/故障码闭表（§3/§5/§6）；单位契约码点（§4）；预定义标准先于比较（§9）。
- 红线：零 shell/实验/临时安装/测试/治理写/其他 docs 改/子 agent/用户交互；R11 原件与历史零改（frozen-bindings 五件 SHA match 为机源，本轮只读未自测 hash）；未写 registry、未改历史源/报告、未减源 skip、未放宽验收、无新 deps、无白名单/hash/ID/EVD 单行特判、无风险接受、无自动 R13。
- 诚实项：本文件非批准、非自审；M2 迁移态 PASS 以未授权迁移为前提且含 ordinal 机检义务；归档通道未机闭（BT-R12-1）；性能界值实测待办；「迁移态攻击仍拒」已限定范围（§8 头注）；不得称人类外部资格/DRI 已确认。
- 步骤：本轮 read 6 文件 + write 1（本文件）+ read-back 1，约 8 步/32 建议；无发散探索。
