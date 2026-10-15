# FIX-445 Design Review R1 — 有界来源验证修订版复审（同一 Design Reviewer）

- **轮次**: R1（复审；前轮 R0 结论 NEEDS_CHANGE/unresolved_blockers=5，report `docs/reviews/review-FIX-445-DESIGN-R0.md` SHA256 `33cda27e113851511ce2b305eb2d18bbeacfe7a04a53b6a0abca57e3378e3deb`/15,462B 静止未改）
- **审查方**: Design Reviewer Agent（与 R0 同一实例；只读；唯一写面 = 本报告；不实现、不跑 module/engine）
- **审查对象绑定**: `docs/design/FIX-445-source-verification-R1.md` — 本轮实测 SHA256 `9c772fe355b295784b5d4bc3569b8d43e070e8d28650707d24c38fd46c67f810` / 21,727 bytes / 187 行（read 工具全读）——与 Coordinator 静止绑定精确一致
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "round": 1, "unresolved_blockers": 4}
```

---

## 0. 结论摘要

R1 修订显著收紧且多处实测扎实：C-1 严格解析路由（键表删除）、C-2 身份绑定（id 逐字+双 utc 瞬时）、C-4 字段角色闭映射、C-5 逐实例 offset 删除（优于 R0 全局替换）、§2.6 三行真实 EQUAL 实测、§2.7 可见性措辞更正、§4 全 input 背书作用域（D-2 核心已修）、§5 C7 正例更正（D-4 已修）、§6 四任务（D-3 已修）、§3 realpath 包含（D-5 主体已修）。

**但 4 项 BLOCKING 使其不能通过**：①C-3 规范式保留 `ext(V) ⊆ A[F]` 连续子串通道——D-1 的 same-field 完整值边界未真正收紧，:34 规范式与自文"整值，非任意子串"措辞自相矛盾，:50 残余声明显式接纳"连续真子串"，而三行合法记录实测均 EQUAL（Designer V4 自证）——子串分支零合法价值、纯攻击面；②§4 新增的背书框架否定前缀豁免无叠否定防护——双否定形背书（`不是不把…当作真实数据`）按实际规则被洗为合规否定；③§3:70 与 §3:73 对 realpath 失败语义互相矛盾（丢路径+诊断 vs 该行 BLOCK）；④C-1"严格解析"缺 duplicate-keys/NaN/类型拒绝规范——严格性缺口在 D-1 强制范围内（非扩面）。

## 1. 前轮 Findings 复审对照（M7.4 逐条：已修复/未修复/新引入）

| R0 Finding | R1 判定 | 依据 |
|---|---|---|
| D-1 豁免凭据弱（span+anchor 重组/角色无界/CH-2 推迟） | **未修复（核心）** | C-2/C-4/C-5 已修，但 C-3 保留 `⊆` 子串通道 → 本轮 R1-A；strict-decode 缺口 → R1-D |
| D-2 背书框架句读截断 | **已修（作用域）+新引入** | §4 全 input/跨句/长距 ✓、unknown 拒绝 ✓；新加否定前缀豁免无叠否定防护 → R1-B |
| D-3 live 三任务硬编码 | **已修复** | §6 四任务+零 skip+EVD-1536 实测入矩阵；live green 留待实现机证（正确不预称） |
| D-4 C7 事实错误 | **已修复** | §5 与 R0 D-4 双实测一致（:16/:17/:49 + `b52313b7…c2e773` 逐字符匹配）；哈希规则正例化+unknown 保守不变 |
| D-5 语料缺真实解析包含 | **已修（主体）+规范矛盾** | §3 realpath/junction/hardlink 语义 ✓；:70 与 :73 失败语义不一致 → R1-C |
| （Coordinator 补充）gitignored 措辞/预算自claim | **已修复** | §2.7 更正为审查面承诺；§9 撤自claim+V1~V4 缺陷如实保留（V2 SyntaxError 不删） |

## 2. Findings（本轮阻塞项；全部基于 R1 doc 实际规则文本）

### R1-A（P1·阻塞）C-3 保留连续子串通道 `ext(V) ⊆ A[F]`——D-1 same-field 完整值边界未收紧

- **位置**: §1 C-3（:34）与 §1 闭合残余（:50）；§2.6 表注
- **缺陷**: :34 规范式为 `ext(V) == A[F] 或 ext(V) ⊆ A[F]（连续包含，V 无作者自写字节）`——`⊆` 允许 V 为 artifact 同名字段值的**任意连续真子串**；同句自称"整体（整值，非任意子串）包含"，规范式与措辞自相矛盾。:50 更将"（或其连续真子串）"写入闭合声明。
- **实际规则反例（非 hypothetical，D-1 原攻击的 same-field 复活形）**: 攻击者逐字复制真实身份与真实 literal 的一个 check 片段：
  `{"id":"#1 old-pattern bash replay (defect proof)","utc_start":"2026-10-11T12:27:10.2692827Z","utc_end":"2026-10-11T12:27:10.7367672Z","literal":"check \"我编造了测试结果\"","result":"复测通过"}`
  - C-1 解析 ✓（合法 JSON object）；C-2 身份 ✓（id 逐字+双 utc 瞬时=真实记录）；C-3 `ext(V) ⊆ A[literal]` ✓（该 check 串确为真实 literal 的连续子串——R0 已证字节在场）；C-4 check span→`literal` ✓ 合法承载 → **span 获豁免**；`result:"复测通过"` 无术语 → M4 过 → **整行 PASS**。
  - 攻击者以真实记录身份背书自己的截取式引用+伪造结论——R0 D-1 反例 α 的 same-field 变体，经 `⊆` 分支原样复活。
- **EQUAL 实测支撑（子串分支零合法价值）**: §2.6/§8 V4（Designer 自证，Coordinator 交叉读）三行合法记录全部 EQUAL（1463 literal EQUAL-ext 1309=1309、1481 observed EQUAL-normalized+literal EQUAL-ext 879=879、1483 observed EQUAL-raw 211=211）——**无任何合法行需要子串分支**；保留它只增加攻击面。
- **必改**: C-3 规范式改为**仅整值严格等值**：`ext(V) == ext(A[F])`（闭合归一双向作用于两侧比较值；原文直探等值同样接受）；删除 `⊆` 分支及 :50 "连续真子串"表述；§7 矩阵"前后缀拼接"行的机制注同步（整值等值失败即拒）；残余声明改写为"整字段值逐字引用"边界。现 artifact exact 引用允许引用；归一/探测仍按具体完整值。

### R1-B（P1·阻塞·新引入）背书框架否定前缀豁免无叠否定防护——双否定形背书被洗

- **位置**: §4（:78"否定前缀豁免：框架所在小句前置于 不|未|非|禁止|拒绝|不得|不可|勿|莫|别|无|并非 → 判定为合规否定"）
- **缺陷**: 豁免只判"前缀存在"，不判否定层数。术语扫描的否定核对叠否定有既定严格类（`不允许不编造` 无标记+闭合尾时按裸词 BLOCK——其为容许义肯定）；框架豁免未对齐。
- **实际规则反例**: `事实依据：发现"不允许不编造"为边界；不是不把该结论当作真实数据` —— 全 input 作用域下框架1（把…当作…真实数据）命中，但小句前置 `不`（叠在 `不是` 之上=双否定=肯定该背书）→ 按规则判"合规否定"→ 豁免 → 残文无术语 → **PASS**。同理 `并非不将结果视为事实`（并非+不=双否定）逃逸。
- **必改**: 否定前缀豁免仅限**单层**否定：前缀窗口内叠否定 token ≥2（不/并非/非/未…组合）→ 不豁免、框架照 BLOCK——与术语核叠否定哲学同类别（未知/叠加严格类，可实现的 token 计数，非 AI 语义）；红绿矩阵补双否定变体两形。

### R1-C（P1·阻塞）§3:70 与 §3:73 对 realpath 失败语义互相矛盾

- **位置**: §3（:70"解析抛错/出仓 → 丢弃该路径 + 计 path-unresolved probe-error 诊断（保守拒绝，不崩溃）"）vs §3（:73"parser（python json）/reader（realpath/文件读）/normalizer/awk/sed/grep 任一腿失败 → 该行 BLOCK，**即使术语扫描本会 PASS**"）
- **缺陷**: realpath 解析抛错同时落两条规则的辖域，结局一个"丢路径继续"、一个"该行 BLOCK"——规范级歧义；实现者可任选，故障传播不确定（正是 B3 类缺陷的规范版）。
- **必改**: 单一确定性规则并写入矩阵。建议（方向安全+可用性均衡）：(a) realpath **解析成功但出仓**→ 丢该路径+`path-unresolved` 诊断（语料缩减=豁免面缩减，保守）；(b) realpath **解析抛错/读已解析文件失败**→ 该行 BLOCK（工具异常不放行，含 safe 输入）；两腿各一红测。或统一全 BLOCK 亦可——但必须唯一。

### R1-D（P1·阻塞）C-1"严格解析"缺 duplicate-keys/NaN/类型拒绝——严格性缺口在 D-1 强制范围

- **位置**: §1 C-1（:26"`json.JSONDecoder.raw_decode`…严格解析"）
- **缺陷（按 D-1/D-5 强制范围评估，非扩面）**:
  1. **duplicate keys**: python json 默认 last-wins——行内 `{"literal":"<完整真值>","literal":"check \"我编造了…\""}` 时解析值≠原文首个值，C-5 的"行原文 span 定位 ↔ 解析字段验证"映射歧义（首个 literal 的 span 实例可能按末值验证/豁免）；机器写入记录键唯一，重复键=非机器形=未知类应拒。
  2. **NaN/Infinity**: `raw_decode` 默认接受非标准 JSON 常量——"严格解析"须 `parse_constant` 拒绝（artifact/行侧同规）。
  3. **承载字段类型**: C-2/C-3/C-4 依赖 id/utc_start/utc_end/literal/observed 为字符串；非字符串（数值/数组/对象）→ 应显式"无身份/无豁免"（保守拒），规范未写明。
- **必改**: C-1 增补三拒绝：`object_pairs_hook` 检重复键→该区按 prose（或直接 BLOCK，择一并入矩阵）；`parse_constant` 拒 NaN/Infinity；身份/承载字段非 string → 无身份/无豁免。offset 守卫（:45 计数/漂移→BLOCK）已有 ✓ 保留。

## 3. 已确认修复面（R2 复审不必重证）

1. **D-2 作用域**: §4 全 input（跨 `。；;`/跨句/长距）+ record 残文同规 + unknown 解析不确定结构拒——R0 反例 α/β 及变体按规则闭合（R1-B 仅涉新豁免面）。
2. **D-3**: §6 四任务零 skip；EVD-1536 实测为 C1 类合规否定入矩阵；live green 不预称（实现机证）。
3. **D-4**: §5 与 R0 D-4 实测完全一致；哈希规则正例化+指称不明保守不豁免。
4. **D-5 主体**: realpath resolved containment（symlink/junction 跟进）+ hardlink 仓内语义 + blob 读取备选；Windows case/分隔符归一未写明——假丢弃方向保守（见 W-A）。
5. **结构性改进（超越 R0 要求）**: C-5 逐实例 offset 删除取代全局替换（防同字面误清）；C-4 结论字段永不承载并以 EVD-1463 result 为对照实证；§2.7 可见性措辞更正（gitignored 事实）；CH-6/CH-7 补蓝军；§9 预算自claim 撤除+V2 缺陷如实保留。
6. R0 通过面（R6/B3、R7 保守、R2 闭语法方向、威胁模型骨架、兼容骨架、过程纪律）按 §0 声明保留，本轮未见弱化。

## 4. WARNING（非阻塞）

- **W-A** Windows 路径归一（盘符大小写/`\` vs `/`/8.3 短名）未规范——假丢弃=豁免面缩减=保守方向可接受；实现期钉死一种归一并测试（不升 BLOCK）。
- **W-B** EVD-1473~1477 全行兼容（1472 已双侧核）留实现期红绿机证——设计已声明，维持。
- **W-C** §2.6/§8 V1~V4 为设计期只读验证（含 Designer 自身 driver 缺陷链如实保留）——**不称产品通过**；产品通过仍以后置代码审查链为准。
- **W-D** 多候选语料限额（≤32）假遗漏——保守拒绝方向，R0 W-2 维持。

## 5. 六维 + 硬门槛

正确性 **FAIL(R1-A~D)**（凭据等值性/背书豁免/故障语义/解析严格性四面）｜安全性 **FAIL(R1-A/B)**（子串重组+双否定背书两逃逸面）｜可维护性 **PASS**（闭表集中+因果注释；R0 P3 维持）｜可演进性 PASS（哈希正例化/四任务/blob 备选）｜性能 PASS（语料上界+python 单次进程需实现期量化——设计已列 CH-3 族）｜测试覆盖设计面 PASS（矩阵含新反例位）。
硬门槛：候选方案 ≥2 ✓（R0 §9 沿用+R1 §3 blob 备选）｜ADR delta 字段完整 ✓｜蓝军 ≥3 ✓（CH-2 更新+CH-6/CH-7 新增）｜循环依赖 0 ✓｜Bar Raiser=本审查 ✓——**存在 4 项 BLOCKING → NEEDS_CHANGE**。

## 6. 本轮审查命令记录（全只读；literal/UTC/exit/raw 一次齐备）

| id | literal | UTC | exit | raw/observed |
|----|---------|-----|------|--------------|
| R1-cmd-1 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d='D:/AI/agent/claude/coding/project_management_workflow/docs/design/FIX-445-source-verification-R1.md'; (Get-FileHash -Algorithm SHA256 $d).Hash.ToLower(); (Get-Item $d).Length; (Get-Content -Encoding UTF8 $d \| Measure-Object -Line).Lines` | unknown（未捕获，不补造） | 0 | `9c772fe355b295784b5d4bc3569b8d43e070e8d28650707d24c38fd46c67f810` / `21727` / `151`（151=含文本行计数度量，187 为总行口径） |

read/grep 工具面（非 shell）：R1 design doc 全 187 行 read；（本轮无其他 shell 命令——D-2/D-3/D-4/D-5 判定依据 = R1 doc 文本 + R0 轮双侧实测 + Designer V4 收据/Coordinator 交叉读，不重跑、不重证 R0 通过面）。影响路径：除本报告外零写。

## 7. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 1 --result NEEDS_CHANGE --report docs/reviews/review-FIX-445-DESIGN-R1.md --reviewer 'Design Reviewer' --bind-file docs/design/FIX-445-source-verification-R1.md`——round 1 < 3 不熔断：退回 Architect 出 R2 版本（修 R1-A~R1-D，经 §11 通道，本 doc 与本报告 hashbound 不改），后同 Design Reviewer 复审 R2（逐条比对+叠否定/等值性/失败语义/严格解析四焦点）。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
