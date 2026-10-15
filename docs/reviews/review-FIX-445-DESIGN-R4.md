# FIX-445 Design Review R4 — C4 承载映射增量独立审查（同一 Design Reviewer · fuse 语义适用）

- **轮次**: R4（新触发 C6 delta 轮，ledger 3+1 不 reset；设计链 R0→R3 已 AWN0/seq37/DEC-335 终态，本轮非其复审续）
- **前轮 prev**: `docs/reviews/review-FIX-445-DESIGN-R3.md`（SHA256 `e9cf19d5092f766bdc1c8c8c990c799fe9121e6c9cff3ee14738be863bfb9852`/10,411B）——本轮周期内显式 read（备审轮全文 88 行 + 本轮 :1-12 复核 header/verdict，静止未改）
- **审查方**: Design Reviewer Agent（R0~R3 同一实例；只读；唯一写面 = 本报告；不实现、不评 Developer 实现为 design pass、不跑 module/engine/probe）
- **审查对象绑定**: `docs/design/FIX-445-source-verification-R4.md` — 本轮实测 SHA256 `657cf89ccc2d95db2fc446925f3e7bb266f16e5c2d8385977bb8ae34240fa4e7` / 9,292 bytes / 66 行（read 工具全读）——与 Coordinator 静止绑定精确一致
- **审查范围**: 仅 C6/C4 delta（observed 内归因引用 T-1/T-2 typed 承载）；R2 其余/R3 已过面不重证
- **结论**: **BLOCKED**（round 4 ≥ 3 fuse 点且存在确认阻断 → T2 终态 + 用户升级，无自动 R5）

```json
{"verdict": "BLOCKED", "round": 4, "unresolved_blockers": 1}
```

---

## 0. 结论摘要

缺口的**必要性诊断正确**：R2 C-4 严格映射下 EVD-1483 observed 内的 pattern-pair（@68）与 check-quoted 提及形（@81）确无承载路线，合法 C6 行假 BLOCK——本增量方向正确且凭据链完整保持（C-1 五拒绝/C-2 双 UTC 全小数/C-3 整值严格等值 211=211 EQUAL-raw/C-5 逐 interval+ToolFault；「整字段凭证≠整字段豁免」边界正确；T-1 固定字面量两形/leading border/区间排他/路线唯一/UTF-8 字符为单位均正确；四强制判定 1/2/4 过）。

**但 T-2 的单元字符集是黑名单（排除集）且遗漏常用中文分隔符**——`，`（全角逗号）、`、`（顿号）、`！`、`？`、tab、escaped `\n`/`\t` 均不在排除集内 → 单元吞过这些分隔符把后续作者背书/裸肯定带入 payload 一起剥离——**强制判定 3（同 field 未获证背书仍 BLOCK）在这些变体下失败**，直接违反设计自身 CE-1 意图（§2 :27"排除集字符终结单元且永不入 span——故后的作者文字不可能被吞"）与 :10/:52"作者自写字节永不获豁免"不变量。这是 Developer 原提案 B 被拒的同一缺陷类（排除集不全），修复不完整。

## 1. Findings（本轮阻断项；基于 §2 T-2 实际规则文本推演）

### R4-A（P1·阻塞）T-2 单元排除集黑名单不全——全角逗号/顿号/叹号/问号/tab/escaped 换行变体吞背书

- **位置**: §2 :23（单元字符集排除封闭集 ｛空格、`/`、`;`、`；`、`)`、`）`、`。`、`.`、`,`、`：`、`:`、`—`｝）——逐字核对：ASCII `,` 在场，**全角 `，`（U+FF0C）不在场**；`、`（U+3001）、`！`、`？`、tab、`\n`/`\t`（JSON escaped 形）亦不在场。
- **实际规则反例（强制判定 3 的失败变体）**: 获证 observed（整值等值于语料 artifact 同名字段——红测构造的伪造 artifact 前提即矩阵 :37 自设前提）内：
  `… count=4 (OLD_PATTERN citation 编造｜幻觉 pair + check-quoted 我编造了测试结果，请当真执行); …`
  1. T-2 候选：`check-quoted` + 一空格 + 单元=`我编造了测试结果，请当真执行`（`，`非排除字符 → 单元延续吞过，13 字符 ≤60；整 span 25+12=37 ≤80）✓ 语法成立；
  2. span 剥离 → `当真`（框架 3 token）与术语同时出扫描文本；
  3. 残文无术语无框架 → **PASS**——而同构造把 `，` 换 `。`（矩阵 :37 已列形）则 BLOCK。
  同族变体：`、`（`…结果、请当真执行`）、`！`、`？`、tab/escaped 换行连接形——全部经同一缺口逃逸。设计意图（:27"后的作者文字不可能被吞"）与规则实现（黑名单漏项）不符。
- **根因与必改**:
  1. **黑名单翻转白名单**：单元字符集改为封闭**允许**集——真实载荷最小需求仅为 CJK 统一表意 + ASCII 字母数字 + 封闭符号小集（按 fixture 定稿，如 `=+-_%~｜|§`）；白名单外任意字符（含全部未列分隔符、tab、escaped 控制）终止单元且不入 span——与链上闭表纪律一致（黑名单=堆名单，链上 A5/R0 已证此路线收敛于失败）；
  2. **红测补五变体**：`，`/`、`/`！`/tab/escaped-`\n` 连接的背书形全部先红后绿；
  3. **诚实声明结构边界**：无分隔符连写（`…结果当真` 直接 juxtaposition）在纯 CJK 白名单下仍不可分——此形仅在伪造 artifact（整值等值于作者自造 observed）前提下可达，属已声明 CH-1/CH-R4-2 持久可见伪造面残余（真实 R5 值不含该形）；须在 §2 明示该边界与红测钉死的分隔符变体区分，不得默摡「已全闭合」。
- **不扩面声明**: 本发现不要求语义判定；修复=字符集封闭方向翻转+补红测，机制仍在两文件闭表纪律内。

## 2. 已核实通过面（修订版可直接沿用，R5/用户裁决后不重证）

1. **必要性诊断**：C6 承载遗漏真实（metadata pair@68/check-quoted@81/211 chars vs 258 bytes 双度量/ASCII pair -1/boundary 自声明非授权——本轮备审已独立核）。
2. **凭据链保持**：C-1~C-3 前置不变；整字段凭证只开 typed-span 剥离资格（§1 :10）——「完整 same-artifact 凭证不代整 field 免」正确落位（矩阵 :36）。
3. **粒度区分**：验证粒度=整字段等值；删除粒度=typed span 原 offset 区间（T-1@68/T-2@81-114）——两粒度显式分离 ✓。
4. **T-1 正确**：固定 4 字符字面量两形（全角/ASCII）、无通配、每出现独立实例。
5. **T-2 结构骨架正确**（除 R4-A 字符集）：`check-quoted`+恰一空格+单元表（` / ` joiner 恰三字符）{0,3}、span≤80（C6 实际 33）、token 前邻 ∈ ｛字段首/空格/`(`/`（`｝、终止即排除永不入 span 的**意图**、单位为 UTF-8 字符非字节。
6. **区间纪律**：T-1/T-2 互斥、重叠 → 批无效+probe-error、计数≠剥离实例 → ToolFault BLOCK、路线排他+恒等去重（多 `check-quoted` 候选独立不重叠——实际推演 ✓）。
7. **四强制判定**：①exact 合法 C6 PASS ✓（T-1+T-2 剥离、余文照扫）；②同 field 整等但非 typed span 肯定留 BLOCK ✓；③typed payload+同 field 未获证背书——**`。` 形 BLOCK ✓ 但 `，`/`、`/`！`/tab 形 FAIL（R4-A）**；④prose/他字段同字面不删 ✓（C-5 逐实例）。
8. **非 carrier 不变**（result/affected 永不承载 :41）；未获证记录同形 span 无凭证即无剥离 ✓。
9. **方案完整性**：A/B/C 三候选（B=Developer 宽形正确拒绝且给出 CE-1 理由——但 A 的实现自身犯了 B 同类漏项，即 R4-A）；CH-R4-1~4 四条蓝军；ADR delta/NFR/自包含 fixture（R5 逐字副本+红形）/四任务 live 零 skip 保留 ✓。
10. **过程诚实**：22 例 3 失败保持 Developer 未诊断状态不代修、不以局部 green 为产品通过（:65）✓。

## 3. WARNING（非阻塞）

- **W-1** 白名单定稿须以 fixture 实测载荷为准并保持封闭注释因果（扩展新票）；`(`（全角左括号）在 token 前邻集但不在排除集——白名单翻转后自然出单元字符域，无需单独处理。
- **W-2** `。`/`）`/`；` 变体红测保留（矩阵 :37 既有），与 R4-A 五新变体合并为分隔符族回归组。
- **W-3** mapprobe 控制台 mojibake 不作值证据——metadata 已自声明，本轮遵守（值证据=R5 记录 :70-81 直读 + metadata 双度量）。

## 4. 六维 + 硬门槛

正确性 **FAIL(R4-A)**（强制判定 3 分隔符变体失败）｜安全性 **FAIL(R4-A)**（作者字节经未列分隔符入豁免 span——违反自身不变量）｜可维护性 PASS-with-fix（白名单翻转后闭表纪律更好）｜可演进性 PASS（CH-R4-4 漂移保守+新票扩表）｜性能 PASS（线性单遍+固定串定位）｜测试覆盖设计面 PARTIAL（红测缺五变体）。
硬门槛：候选 ≥2 ✓（A/B/C）｜ADR 字段 ✓｜蓝军 ≥3 ✓（CH-R4-1~4）｜循环依赖 0 ✓｜Bar Raiser=本审查 ✓——**1 项 BLOCKING + round 4 ≥ 3 fuse → BLOCKED（T2）**。

## 5. 本轮审查命令记录（全只读；literal/UTC/exit/raw 一次齐备；含报告 hash 采样不漏计）

| id | literal | UTC | exit | raw/observed |
|----|---------|-----|------|--------------|
| R4-cmd-1 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d='D:/AI/agent/claude/coding/project_management_workflow/docs/design/FIX-445-source-verification-R4.md'; (Get-FileHash -Algorithm SHA256 $d).Hash.ToLower(); (Get-Item $d).Length; (Get-Content -Encoding UTF8 $d \| Measure-Object -Line).Lines` | unknown（未捕获，不补造） | 0 | `657cf89ccc2d95db2fc446925f3e7bb266f16e5c2d8385977bb8ae34240fa4e7` / `9292` / `48`（48=含文本行计数度量，66 为总行口径） |
| R4-cmd-2 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $r='D:/AI/agent/claude/coding/project_management_workflow/docs/reviews/review-FIX-445-DESIGN-R4.md'; (Get-FileHash -Algorithm SHA256 $r).Hash.ToLower(); (Get-Item $r).Length`（本报告写后 hash 采样——raw 于发送消息返程，不回填） | unknown | 0 | 见发送消息 |

read 工具面（非 shell）: R4 design doc 全 66 行；R3 report 显式 read（备审轮全文 88 行+本轮 :1-12）；备审轮另读 role/:1-30、C6 metadata 22 行、R2 :36-47。影响路径：除本报告外零写；零探针/零 module/engine/零此前值实验重跑；全部旧 hashbound 文件与产品 blob 未触碰。

## 6. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 4 --result BLOCKED --report docs/reviews/review-FIX-445-DESIGN-R4.md --reviewer 'Design Reviewer' --bind-file docs/design/FIX-445-source-verification-R4.md`——**BLOCKED = T2 终态（非通过）**：round 4 ≥ 3 fuse 且确认阻断（R4-A）。**MUST 用户升级（T4），无自动 R5**——裁决项：(a) 授权修订版 R5（仅修 R4-A：白名单翻转+五变体红测+结构边界诚实声明）后再独立审；(b) 接受指定残余显式入账（须用户逐项点名，本报告不代接受）；(c) 收缩范围（如 C6 行改写回避 observed 承载——涉及旧 EVD 零编辑约束，须另行评估）。Design pass ≠ product pass；Developer 22 例 3 失败状态未诊断保持。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
