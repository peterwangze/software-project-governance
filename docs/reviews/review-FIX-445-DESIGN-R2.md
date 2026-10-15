# FIX-445 Design Review R2 — 来源验证合并规范复审（同一 Design Reviewer）

- **轮次**: R2（复审；前轮 R1 结论 NEEDS_CHANGE/unresolved_blockers=4，report `docs/reviews/review-FIX-445-DESIGN-R1.md` SHA256 `cbbfd8109d7172bb5f5cdcb7f48c98c5e8db50c2cce9f313a7b89ef2fb4e7a88`/13,185B——本轮按协议显式 read 重读，静止未改）
- **审查方**: Design Reviewer Agent（R0/R1 同一实例；只读；唯一写面 = 本报告；不实现、不跑 module/engine）
- **审查对象绑定**: `docs/design/FIX-445-source-verification-R2.md` — 本轮实测 SHA256 `20e86d3145cef96594752501a992ec983f1acd31cecc165a86bdd95715ad345b` / 14,009 bytes / 100 行（read 工具全读）——与 Coordinator 静止绑定精确一致
- **审查范围**: 仅 R1-A~R1-D 四 delta + 原验收（Coordinator 指示）；已确认修复面（R1 review §3 / R2 §0 沿用声明）不重证
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "round": 2, "unresolved_blockers": 1}
```

---

## 0. 结论摘要

四 delta 中三项**实际闭合**：R1-A（C-3 仅 `V == A[F]` 或双向 `ext(V) == ext(A[F])`，一切子串/前缀/后缀/裁剪通道规范级删除，R1 §1/§7 旧文显式废弃）✓；R1-C（§2 单一确定性二分：resolved 成功出仓→丢候选+诊断+不读目标；realpath 抛错/读失败→该行 BLOCK；内容 malformed→缩减+残文照检——三类别无交叠）✓；R1-D（C-1 五拒绝：整区消费/重复键/NaN-Infinity/顶层非 object/嵌套拯救禁止 + 统一 malformed=prose + 非 string 身份/承载无授予，artifact 侧同规）✓。

**R1-B 未完全闭合**：§3 的否定前缀判定用闭合 token 表对 16 字符窗口做 longest-match **子串切分计数**，无词边界/残留校验——常用副词与名词内嵌的单个否定字形（`非常`之`非`、`未来`之`未`、`无论`之`无`）被计为单层否定 → 背书框架被豁免 → 背书逃逸（本轮 R2-A 反例）。叠否定两形（`不是不把`/`并非不将`）本身按规则正确 BLOCK，但同表的嵌入字误判是 R1-B 同族缺口。

## 1. 前轮 Findings 复审对照（M7.4 逐条）

| R1 Finding | R2 判定 | 依据 |
|---|---|---|
| R1-A C-3 `⊆` 子串通道 | **已修复** | §1 C-3 :38-40（仅 `==`/双向 `ext==`；"不存在任何子串/包含/真子串通道"；R1 旧文显式废弃）；§4 R1-A 反例行 BLOCK；三合法行 EQUAL 沿用 V4（不重跑） |
| R1-B 叠否定无防护 | **部分修复** | §3 计数 0/1/≥2 三态 + 两形入矩阵 ✓；但 token 子串计数无词边界 → 本轮 R2-A |
| R1-C realpath 失败语义矛盾 | **已修复** | §2 :51-54 唯一二分规则（出仓→缩减+诊断不读目标；抛错/读失败→BLOCK 含 safe；内容→缩减+照检），与 C-1 :31/:32 一致，无交叠无二选 |
| R1-D 严格解析缺拒绝规范 | **已修复** | §1 C-1 :23-31 五拒绝+类型拒绝+artifact 同规+统一 malformed=prose；§4 :81-84 矩阵行齐 |

## 2. Finding（本轮阻塞项）

### R2-A（P1·阻塞）否定前缀 token 计数无词边界——嵌入字误判单层否定使背书框架被豁免

- **位置**: §3 :63（"窗口内按闭合否定 token 表 longest-match 切分后计数"，token 表含 `不|未|别|勿|莫|无|非|…`）+ :64（"计数 ==1 → 单层否定 → 框架判合规否定（豁免该框架）"）
- **缺陷**: 切分是**子串级** longest-match，不要求 token 独立成词、不校验窗口残留。常用词内嵌的单个否定字形被计入：`非常`之`非`、`未来`之`未`、`无论`之`无`、`南非`之`非` 等。计数==1 → 豁免 → 框架失效。
- **实际规则反例（规则文本逐步推演，非语义假想）**: `事实依据：发现"不允许不编造"为边界，非常应当把该结果当作真实数据`
  1. C2 剥离后残文全 input 进入 §4（R1 已修作用域）；
  2. 框架1 `(把|将)…(当作|当成|视为|作为)…(真实|事实|数据|结果|有效)` 命中（把…当作…真实数据）；
  3. 前缀窗口 = 小句起至运算子`把`起点：`非常应当`（≤16）；
  4. longest-match 切分：位置 0 `非` ∈ token 表 → 计 1；`常`/`应`/`当` 非表内 → 计数 ==1；
  5. :64 规则 → 判"单层否定" → **豁免该框架**；残文无术语 → M4 过 → **整行 PASS**。
  语义上`非常应当把…当作真实数据`是无保留的强化背书（`非常`=程度副词），无任何否定——背书经嵌入字洗白。同族变体：`未来将把该结论视为事实`（`未`嵌入`未来`）、`无论复核与否，把该结果当作真实数据`（`无`嵌入`无论`）。
- **与 R1-B 同族**: R1-B 修的是"叠否定计漏"（2 计成可豁免类）；R2-A 是"零否定计成 1"——同一计数机制的词边界缺陷两面。
- **必改（保持闭表纪律，可实现对齐术语核先例）**: 窗口改为**全窗口闭合切分**：窗口必须完整分割为「否定 token + 封闭虚词填充集（如 是|应当|应|将|把|该|此|其|的|且|而|与|或|了|把|将 等，实现期定稿封闭表）」；出现任何无法归入 token 表或填充集的残留（如 `常`、`来`、`论`）→ 保守不豁免（计数按可完整切分窗口计，残留即拒）。推演验证：`非常应当` → `非`+残留`常` → 不豁免 → BLOCK ✓；`不是不把` → `不`+`是`(填充)+`不` → 计 2 → BLOCK ✓；`不把`/`未将` → 计 1 → PASS ✓；`并非不将` → `并非`+`不` → 计 2 → BLOCK ✓。红绿矩阵补：`非常应当把…当作真实数据`、`未来将把…视为事实`、`无论…把…当作真实数据` 三形（先红后绿）。
- **不扩面声明**: 本发现不引入语义判定/新 regex 白名单——修复=既有闭表机制加残留校验，与术语核"约束中隔"哲学同类别。

## 3. 已确认闭合面（R3 复审不必重证）

1. **R1-A 闭合**: 凭据仅整值严格等值（raw `==` 或两侧闭合 ext `==`）；ext 映射逐位字形替换（`｜`→`|` 单字对单字；`〈反引号〉`→`` ` `` 为显示转义逆映射），等值下无法注入作者新字节（仅同位字形互换，无长度/内容增量）；R1-A 反例（截取片段+复制身份+假 result）整值不等 → 无豁免 → BLOCK；整字段逐字引用+复制身份=声明闭合极限（无新权威边界内），作者结论/周围全文仍 scan（C-4/C-5 沿用）。
2. **R1-C 闭合**: 三类别（出仓/传输/内容）互斥完备，唯一规则无二选；仓外目标不读取；safe 输入下传输失败仍 BLOCK。
3. **R1-D 闭合**: 五拒绝+嵌套拯救禁止+统一 malformed=prose（零豁免+全扫描，BLOCK 由命中触发——安全 prose 花括号不误杀，矩阵 :84）；artifact 侧同规；类型拒绝联动 C-2/C-4。
4. §6 收据更正属实且处置正确（V4 逐字声明撤回、指向 Coordinator 保全的真 returned literal；V1/V3 body 全量返程保全；不重执行）。

## 4. WARNING（非阻塞）

- **W-1** §3 :62 前缀窗口"长度上界 16 字符"的溢出语义未定义（>16 时取末 16 还是判不可豁免）——两读均保守方向（外侧 token 不计 → 计数偏少 → 偏 BLOCK），无逃逸；实现期钉死一读+测试即可，不升 BLOCK。
- **W-2** R2-A 修复的同时须保持 `不允许把…当作真实数据`（单 token `不允许`，PASS）与 `不允许不把…当作真实数据`（计 2，BLOCK）的区分——填充集定稿时用 R1 §4 正例（EVD-1472~1477 残句）回归。
- **W-3** 收据计数措辞：R2 doc 标题"本轮零新命令"与 :96"静止 hash 回执 ×1（readonly shell）"并存——按 Coordinator 裁定计独立 EVD 纠正（实为 1 条 readonly shell），不要求改静止规范。
- **W-4** 既有三框架闭集不覆盖全部无术语背书形（R0 W-1 沿用）——边界诚实保留；R2-A 修复后已证形+嵌入字三形全覆盖，其余同现行语义非回归。
- **W-5** V1~V4/§2.6 均为设计期只读验证——**Design pass ≠ product pass**，代码未写，产品通过仍后置代码审查链。

## 5. 六维 + 硬门槛

正确性 **FAIL(R2-A)**（唯一残面：前缀计数词边界）｜安全性 **FAIL(R2-A)**（背书豁免逃逸面）｜可维护性 PASS（闭表+残留校验修复方案仍在两文件闭表纪律内）｜可演进性 PASS（R2 §5 ADR delta 字段完整）｜性能 PASS（窗口 16 上界沿用）｜测试覆盖设计面 PASS（矩阵含 R1-A/叠否定/realpath/五拒绝行；R2-A 修复补三形）。
硬门槛：候选方案 ≥2 ✓（R0 §9 沿用+§2 blob 备选）｜ADR 字段完整 ✓｜蓝军 ≥3 ✓（CH 链延续）｜循环依赖 0 ✓｜Bar Raiser=本审查 ✓——**存在 1 项 BLOCKING → NEEDS_CHANGE（unresolved_blockers=1）**。

## 6. 本轮审查命令记录（全只读；literal/UTC/exit/raw 一次齐备；含报告 hash 采样不漏计）

| id | literal | UTC | exit | raw/observed |
|----|---------|-----|------|--------------|
| R2-cmd-1 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d='D:/AI/agent/claude/coding/project_management_workflow/docs/design/FIX-445-source-verification-R2.md'; (Get-FileHash -Algorithm SHA256 $d).Hash.ToLower(); (Get-Item $d).Length; (Get-Content -Encoding UTF8 $d \| Measure-Object -Line).Lines` | unknown（未捕获，不补造） | 0 | `20e86d3145cef96594752501a992ec983f1acd31cecc165a86bdd95715ad345b` / `14009` / `78`（78=含文本行计数度量，100 为总行口径） |
| R2-cmd-2 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $r='D:/AI/agent/claude/coding/project_management_workflow/docs/reviews/review-FIX-445-DESIGN-R2.md'; (Get-FileHash -Algorithm SHA256 $r).Hash.ToLower(); (Get-Item $r).Length`（本报告写后 hash 采样——raw 于发送消息返程，不在本表内回填） | unknown | 0 | 见发送消息 |

read 工具面（非 shell）: R2 design doc 全 100 行；R1 report 显式重读（:1-30 核 header/绑定/verdict，文件 97 行与本 Reviewer 亲写版一致）。影响路径：除本报告外零写；判定依据 = R2 doc 规则文本逐条推演 + R1/R0 轮已实测事实，无重跑、无 module/engine。

## 7. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 2 --result NEEDS_CHANGE --report docs/reviews/review-FIX-445-DESIGN-R2.md --reviewer 'Design Reviewer' --bind-file docs/design/FIX-445-source-verification-R2.md`——round 2 < 3 不熔断：退回 Architect 出 R3（仅修 R2-A：全窗口闭合切分+残留校验+填充集封闭表+三形红绿），后同 Design Reviewer 复审 R3。**注意 round 3 为复审 fuse 点**：R3 若仍有 BLOCKING → 按 M7.4 T2 建议转 BLOCKED+用户升级。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
