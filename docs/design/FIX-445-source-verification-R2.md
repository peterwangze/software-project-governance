# FIX-445 设计 R2 — 来源验证合并规范（R1-A~R1-D 精确修复版）

- **性质**: `docs/design/FIX-445-source-verification-R1.md`（SHA256 `9c772fe3…67f810`/21,727B）的修订版本，经 `docs/reviews/review-FIX-445-DESIGN-R1.md`（NEEDS_CHANGE/unresolved_blockers=4，97 行，本轮 read 全文）§7 通道产生。R0/R1 两版 design 与全部 review 报告静止零改；本文件为 R2 轮唯一写面；产品两 blob 零写。
- **范围声明**: 本文件是**合并后的唯一 canonical 规范**——R0/R1 中与本文件冲突的表述一律以本文件为准（尤其 R1 §1 C-3 的 `⊆` 分支与 §7「连续真子串」注，按 R1-A 全文废弃）。已确认修复面（R1 review §3：R6/B3、D-2 作用域、D-3 四任务、D-4 正例、D-5 主体、C-4/C-5 结构改进）不重证、不重述，全部沿用。
- **本轮零新命令**（Coordinator 指示：无需再跑值核/hash 实验；V4 已证三合法行全 EQUAL）。收据更正见 §6。

## 0. Finding → 修复映射

| R1 Finding | 修复落点 | 状态 |
|---|---|---|
| R1-A C-3 保留 `ext(V) ⊆ A[F]` 子串通道（same-field 截取引用复活） | §1 C-3（仅严格整值等值）+ §4 矩阵 | 已修（删除一切 ⊆/contains/真子串） |
| R1-B 否定前缀豁免无叠否定防护（`不是不把…` 被洗） | §3（单层否定 + longest-match 计数） | 已修 |
| R1-C §3:70/:73 realpath 失败语义矛盾 | §2（单一确定性两分规则） | 已修 |
| R1-D 严格解析缺 duplicate-keys/NaN/类型拒绝/嵌套拯救 | §1 C-1（三拒绝 + 整区 fail-closed + 统一 malformed 规则） | 已修 |
| （Coordinator）V4「逐字一致」声明不成立 | §6 收据更正 | 已修（指向真 returned literal，不重执行） |

## 1. 豁免凭据 canonical 规则（合并版；取代 R1 §1 全部同号条款）

豁免的必要且充分条件 = C-1~C-5 全部成立；任一不成立 → 该 span 无豁免、按裸词/框架进入 risk 扫描。

**C-1 严格解析路由（R1-D 修复后全文）**
- M1a（awk，quote-aware）检测行内 `{…}` 候选区：引号内的 `{` 不开区（既有语义）；候选区 = 花括号配平且引号感知的原文区间。无候选 → 纯 prose 路径（不依赖 python；普通 prose 里孤立花括号/JSON 样注释**不机械 BLOCK**——安全例不误杀）。
- 有候选 → 内嵌 python（标准库 json）对**每个候选区整区**严格解码，五拒绝：
  1. **整区消费**：`raw_decode` 必须消费到区间末尾（`end == 区长`）；部分消费/尾部残料 → 该区 malformed；
  2. **重复键**：`object_pairs_hook` 检出同层重复键 → malformed；
  3. **非标准常量**：`parse_constant` 拒绝 `NaN/Infinity/-Infinity`；
  4. **非 object 顶层**（数组/字符串/数值）→ 非记录；
  5. **嵌套拯救禁止**：malformed 区内**不得**再抽取嵌套合法子 object 进记录路径（首对象 malformed → 整区按 prose，无任何豁免）。
- **统一 malformed 规则（唯一，无二选）**：行侧候选区 malformed（含上述 1/2/3 及解码异常）→ **整区渲染为 prose**（prose 零豁免；术语在 prose 扫描中照 BLOCK）。不采用「malformed → 直接 BLOCK」——prose 渲染已保守（零豁免 + 全扫描），且避免误杀含花括号的安全 prose 行；BLOCK 仍由扫描命中触发。与 R0/R1「未闭合包裹 → prose」语义同族，规范唯一。
- **类型拒绝（R1-D 第 3 项）**：`id`/`utc_start`/`utc_end` 非 string → **该记录无身份**（C-2 必然失败）；`literal`/`observed`/`output_as_captured` 非 string → **该字段不授予任何豁免**。
- **artifact 侧同规**：语料 JSON 严格解码用同一五拒绝——含重复键/NaN 的 artifact 记录 → 该记录不可用（无身份/无字段授予）；artifact **文件**严格解析失败 → 该文件产出零候选记录 + probe-error 诊断（见 §2 传输/内容二分）。
- python 腿不可用/崩溃/非 0 → 该行 BLOCK（fail-closed 含 safe 输入；R1 CH-7 维持——C1/C2 纯 prose 行不依赖 python）。

**C-2 记录身份绑定**（沿用 R1，未改）：citing 与 artifact 记录 `id` 逐字符相等 **且** `utc_start`/`utc_end` 瞬时相等（RFC3339 解析比较；字符串精度差如 `.537239Z` vs `.5372390Z` 判同瞬时）。非 string 身份字段 → 无身份（C-1 类型拒绝联动）。

**C-3 同名字段严格整值等值（R1-A 修复后全文——唯一凭据式）**
- 豁免 span 所在 citing 字段值 V 与身份匹配 artifact 对象**同名字段**值 A[F]，凭据当且仅当：
  - `V == A[F]`（原文逐字等值），**或**
  - `ext(V) == ext(A[F])`（闭合显示归一 `｜ → |`、`〈反引号〉 → \`` **双向作用于两侧比较值**后的等值）。
- **不存在任何子串/包含/真子串通道**：`ext(V) ⊆ A[F]`、前缀、后缀、裁剪、部分引用——一律**不是**凭据（R1 §1 C-3 的 `⊆` 分支与 R1 §7「连续真子串」机制注全文废弃）。截取真实 literal 片段 + 复制真实身份的引用（R1 review R1-A 反例）因整值不等而**无豁免**。
- 归一映射仅用于验证比较；术语/背书扫描与 C-5 位置算术永远作用于行原文（防归一洗位/洗扫描）。
- 三合法行实测（V4，Coordinator 交叉读）：1463 literal EQUAL-ext(1309=1309)、1481 literal EQUAL-ext(879=879)+observed EQUAL-normalized(176=176)、1483 observed EQUAL-raw(211=211)——**全部整值等值成立，无任何行需要子串通道**（R1 review R1-A 实测支撑，引用不重跑）。

**C-4 span↔承载字段闭映射**（沿用 R1，未改）：verdict span → 仅 `observed`；check/pattern span → 仅 `literal`|`output_as_captured`；`result`/`affected`/`unknowns`/`protection` 类结论性字段永不承载。非 string 承载字段 → 无豁免（C-1 类型拒绝联动）。

**C-5 逐实例按位置豁免执行**（沿用 R1 C-5 修订全文，未改）：python 按解析 offset/字段边界构造残文；同值多出现每 instance 各自验证（instance 豁免仅当其所在字段对该 record 通过 C-1~C-4）；删除区间数 == 验证实例数，漂移/不匹配 → BLOCK；位置算术基于行原文；删除后其余字段/prose/未获证同字面全量继续 risk 检查；缺 safe 凭证不 payload 空过。

## 2. 语料路径与故障语义（R1-C 修复——单一确定性规则）

- **语料构造**（沿用）：行内 refs ≤8 + `.governance/incidents/*${TASK_ID}*` glob ≤24，总 ≤32；排除 evidence-log 自身；目录闭前缀；拒绝绝对路径/`..`。
- **唯一规则（取代 R1 §3:70/:73 的并存表述）**，按故障类别二分，无交叠：
  - **(a) realpath 解析成功但出仓**（symlink/junction 跟进后 resolved 路径不在 `realpath($REPO_ROOT)` 下）→ **丢弃该候选路径** + `path-unresolved` 诊断；语料缩减 = 豁免面缩减（保守）；**仓外 resolved 目标不读取**。
  - **(b) 传输/IO 类失败**——realpath **抛错**、或对**已解析仓内路径的读取失败**（open/read IO 错误，含不可读权限）→ **该行 BLOCK**（工具异常不放行，含 safe 输入）。
  - **内容类失败不属本条**：artifact 文件可读但严格解析失败（C-1 五拒绝）→ 零候选记录 + probe-error 诊断，豁免面缩减，行是否 BLOCK 由扫描命中决定（malformed 内容永不授予、永不静默放行——与 §1 统一 malformed 规则同一原则：**内容 malformed → 缩减；传输失败 → BLOCK**）。
- hardlink：仓内 hardlink = 同文件仓内路径，realpath 不变其解析结果，读取即仓内内容（路径解析边界，不新增 inode 假想向量）。`git cat-file` blob 读取维持实现期等效备选。
- R6（sed 非 0→BLOCK；grep 0/1/≥2 三态；M1 既有守卫）原样保留；本条 (b) 与之同族闭合。
- W-A（Windows 盘符大小写/分隔符/8.3 归一）维持实现期钉死一种归一 + 测试，不升 BLOCK（R1 review 非阻塞项沿用）。

## 3. 背书框架单层否定豁免（R1-B 修复）

- 框架闭集与全 input 作用域沿用 R1 §4（已确认修复面，不重述）；**唯一变更 = 否定前缀豁免的层数判定**：
  - 前缀窗口 = 框架起点所在小句内、自小句起到框架运算子（把/将/当作/当成/视为/作为/当真）起点止，长度上界 16 字符。
  - 窗口内按**闭合否定 token 表 longest-match 切分**后**计数**：`并非|不允许|禁止|拒绝|杜绝|避免|防止|绝不|决不|从不|从未|毫无|没有|不会|不能|不得|不可|不|未|别|勿|莫|无|非`（longest-match：`并非` 计 1 个 token，不拆为「并+非」；`不允许` 计 1 个，不算两层；`不是` 中 `不` 计 1 个）。
  - **计数 ==1 → 单层否定 → 框架判合规否定（豁免该框架）**；**计数 ≥2 → 叠否定（语义=肯定该背书）→ 不豁免，框架照 BLOCK**；**计数 ==0 → 无前缀 → 背书，BLOCK**。
  - 窗口内出现无法归入 token 表的第二个框架/不成对引号等解析不确定结构 → 保守拒（不豁免）。
  - **无语义扩张、无新 regex 白名单**：判定 = 闭合表 longest-match + 整数计数，与术语核叠否定哲学同类别（`不允许不编造` 家族的既有严格类）。
- 红绿矩阵新增（§4）：`不是不把该结论当作真实数据`（不×2 → BLOCK）、`并非不将结果视为事实`（并非+不 → BLOCK）、`不把估计批戳当成真实戳`（不×1 → PASS）、`未将该结果当作真实数据`（未×1 → PASS）。

## 4. 修正后预期矩阵（**设计预期——产品未实现，不称实现通过**；仅列 R2 变更/新增行，其余沿用 R1 §7 全部行）

| # | 输入 | 预期 | 机制 |
|---|---|---|---|
| **R1-A 反例** | 真实 id+双 utc + `literal` = 真实 literal 的 check 片段截取 + `result:"复测通过"` | **BLOCK** | C-3 整值等值失败（无子串通道）；result 永不承载（C-4）；结论照检 |
| 前后缀拼接/任意裁剪 | 真整值±作者字节 | **BLOCK** | C-3 仅 `==`/`ext==`，任何 ≠ 即无豁免 |
| **叠否定背书 A** | `发现"不允许不编造"为边界；不是不把该结论当作真实数据` | **BLOCK** | §3 计数 2（不+不）→ 不豁免 |
| **叠否定背书 B** | `…已实证。并非不将结果视为事实` | **BLOCK** | §3 计数 2（并非+不）→ 不豁免 |
| 单层否定框架 ×2 | `不把估计批戳当成真实戳` / `未将该结果当作真实数据` | **PASS** | §3 计数 1 → 合规否定 |
| **realpath 出仓** | 仓内 symlink → 仓外 | 丢路径+诊断；若无其它来源且术语在 → **BLOCK** | §2(a) |
| **realpath 抛错/读失败** | 解析异常 / 已解析仓内文件不可读 | **BLOCK**（含 safe） | §2(b) |
| **artifact 内容 malformed** | 语料文件可读但含重复键/NaN | 零候选+诊断；术语在则 **BLOCK** | §1 统一 malformed（内容→缩减） |
| **行侧重复键** | `{"literal":"<真值>","literal":"check \"我编造了…\""}` | **BLOCK** | 整区 malformed → prose → 零豁免 → 术语命中 |
| **NaN/半 JSON/嵌套拯救** | `{"a":NaN,…}` / 部分消费 / malformed 内嵌合法子对象 | **BLOCK**（术语在时）；零豁免永远 | C-1 五拒绝 + 嵌套拯救禁止 |
| **非 string 身份/承载** | `"id":1` / `"observed":[…]` | 无身份/无豁免 → 术语在则 **BLOCK** | C-1 类型拒绝 |
| **安全 prose 花括号** | 普通注释行含 `{` 无术语 | **PASS** | 无候选/parse-fail → prose 扫描无命中（不误杀） |
| （沿用）F1~F4/α/β/n1/n7/n8/P1/P2/分号句号长距/复制载荷后背书/FC1~FC6/A1~A5/C1~C7/live 四任务 | — | 同 R1 §7 | 已修复面不重证 |

## 5. ADR delta（proposed——Coordinator 写回）

- **决策更新（R2）**：C-3 凭据收紧为仅整值严格等值（raw `==` 或双向 ext 等值），删除一切子串通道；背书否定前缀豁免限单层（闭合表 longest-match 计数，≥2 拒）；realpath 失败二分唯一规则（出仓→缩减+诊断；抛错/读失败→行 BLOCK）；严格解析五拒绝（整区消费/重复键/NaN/非 object/嵌套拯救禁止）+ 统一 malformed=prose 规则 + 非 string 身份/承载字段无授予。
- **可逆性/影响范围**：不变（原两文件、Step-12 门、其它门零弱化、git revert 可逆、无新权威）。

## 6. 收据更正与来源指向（本轮零新命令）

- **V4「逐字一致」声明更正（Coordinator 指出，属实）**：R1 doc §8 内嵌 body 与实际返回的 V4 literal **不**逐字一致——doc 版为 `from datetime import datetime` + `inst` lambda；实际 returned 版为 `from datetime import datetime, timezone` + `def inst(ts)` 函数及额外打印行。**权威 V4 record = Coordinator 已保全的真正 returned literal**（见 Coordinator correction record）；R1 doc §8 的内嵌版是撰写时的近似转录，非执行原文。本 R2 不重执行、不改 R1；后续引用一律指向真 returned script/Coordinator correction，不再使用「逐字一致」表述。
- V1~V3 body 已由本 Architect 经 returned message 全量返程、Coordinator 保全（含 V2 outer 0 + python child 1 的失败事实）。
- 本轮（R2）命令面：仅 read 工具 ×1（R1 review 全文 97 行）+ 本 doc 写 ×1 + 静止 hash 回执 ×1；零值核/hash/探针新实验（遵 Coordinator 指示与 R1 review §3 已确认面不重证）。

## 7. 静止声明

本 R2 为合并 canonical 规范的完整修订版，四处 R1 findings 的修复全部落在 §1 C-1/C-3、§2、§3，与已确认修复面无矛盾。返回 Coordinator 后静止；独立 R2 复审只对四 delta（等值性/叠否定/失败语义/严格解析）比对；是否 APPROVED 由 Reviewer 判定，本 Designer 不自评。如需再修订另出 R3 新版本，本文件 hashbound 后不改。
