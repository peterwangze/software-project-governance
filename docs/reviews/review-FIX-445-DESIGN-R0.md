# FIX-445 Design Review R0 — 有界来源修复设计独立审查

- **轮次**: R0（首次设计审查；无前轮）
- **审查方**: Design Reviewer Agent（只读；唯一写面 = 本报告；不实现、不跑 module/engine、不先于代码）
- **审查对象绑定**: `docs/design/FIX-445-source-verification.md` — 本轮实测 SHA256 `59f318d4575ca6cc2e3d487d90824b8fc74847a2d9bb92e68436c4d19d22e3f2` / 33,525 bytes / 304 行（read 工具全读）——与 Coordinator 静止绑定精确一致
- **产品窗口静止**: `hooks/commit-msg` blob `8efea9430658b73c3baf481676e455666bd914f7`、`tests/test_hooks.py`（实际路径 `skills/software-project-governance/infra/tests/test_hooks.py`）blob `8efd64da0f28a632179e890a27f4cb4a0494295b`、HEAD `bf6942dd…`——备审轮已实测（EVD-1537~1539 机录），本轮未再跑
- **结论**: **NEEDS_CHANGE**

```json
{"verdict": "NEEDS_CHANGE", "round": 0, "unresolved_blockers": 5}
```

---

## 0. 结论摘要

设计方向正确且大部分规则面成立：签名门降级为路由必要条件（R1）、闭语法 span+长度上界+未知形保守进扫描（R2）、逐腿 rc 区分（R6，B3 正确闭合）、保守拒绝+双因诊断（R7）、备选方案与蓝军挑战完备（§9/§10）、两文件可实现（§6）、回滚可逆（§11）。

**但 5 项 BLOCKING 发现使设计不能按现文通过**：①span 级包含+anchor 共现允许「真 span+真 anchor 跨字段/跨角色重组」——CH-2 残余被显式推迟到"未来"而用户未接受该风险，且本设计自己的七类映射证明 value 整体+同字段名包含对全部合法类零成本成立（收紧无理由推迟）；②R5 背书框架作用域被 `。；;` 截断，分号/句号变体的引用后背书按方案实际规则仍逃逸；③live 窗口三任务硬编码，产品落地实际需四任务（含 FIX-445 自身行）；④C7「哈希今日不可复验」为事实错误——referent 实测可解析且精确匹配；⑤语料路径缺 symlink/junction 真实解析包含检查，「不读仓库外任何路径」边界可被仓内 symlink 击穿。

## 1. Findings（全部基于设计实际规则的自含反例推演，非假设堆叠）

### D-1（P1·阻塞）豁免凭据弱于所需：span 级共现允许真元素重组，字段角色无划界，CH-2 残余无理由推迟

- **位置**: §5 R3（span+anchor 同对象共现）、§5 R4（豁免作用域）、§7 边界行、§10 CH-2（"可选收紧（未来）：要求 span 所在值整体包含"）
- **缺陷**: 豁免凭据 = span 字节包含 + 同对象 anchor 共现，不含 (i) span 所在字符串值的整体包含、(ii) 字段名/字段角色一致性。设计自认残余（§7 边界行"豁免该 span"）并推迟收紧——但用户**未接受**该已知风险，且 B1 已证根因（"复用真实 artifact 声明伪造"）要求关闭。
- **反例 α（F3 强化形——按 R2/R3/R4 实际规则推演）**: `事实依据：{"id":"#1 old-pattern bash replay (defect proof)","output_as_captured":"check \"我编造了测试结果\"","result":"复测通过"}`
  - span `check \"我编造了测试结果\"` 属 R2 类型 2 闭语法（check 转义形，≤120）→ 候选 ✓
  - R3 原文直探：该串字节在 `.governance/incidents/FIX-444-command-records.json` :15 在场（设计 C4 自证）✓；anchor id 43 字符 ≥16、同对象共现 ✓ → **span 获豁免**
  - `result` 值"复测通过"无术语 → M4 过 → **整行 PASS**
  - 攻击者将真实攻击夹具串（其原语义是 R0 探针的攻击输入）充当自己的"捕获输出"并伪造复测结论。设计 §7 F3 行的 BLOCK 判定依赖"该伪造对象无 ≥16 anchor"——那是特定测试输入的偶然，不是规则属性；补一个真实长 anchor 即反转为 PASS。
- **反例 β（结论字段洗白）**: `{"id":"R3-adversarial-9-cases","result":"BLOCK｜韩国编造了数据"}` —— 真实 verdict span（R2 类型 1）复制进结论性 `result` 字段获剥离，result 字段被"洗净"。verdict span 的合法承载是 `observed`（C5 实测），check/pattern span 的合法承载是 `literal`（C3/C4 实测）——设计未做任何 span 类型↔承载字段的角色划界，"结果/结论与 literal 字段角色"仅靠共现，未真正划界。
- **必改（两文件内可实现，零新增依赖）**:
  1. **value 整体包含**：span 所在字符串值（归一后）整体须包含于同一 artifact 对象——合法七类实测全部已满足（C3/C4 literal 整体、C5 observed 整段、C6 observed 全角原文，均为设计自证），收紧对合法行零成本；
  2. **字段名一致**：豁免值须出现在 artifact 对象的**同名字段**内（citing record 的 `literal` ↔ artifact 的 `literal`）；
  3. **span 类型↔承载字段闭映射**（从七类归纳）：verdict 行 → `observed`；check/pattern 对 → `literal`/`output_as_captured`；结论性字段（`result`/`affected` 类）不承载 check/pattern 豁免；
  4. 收紧后残余收敛为「同对象同名字段整值+anchor 全部逐字引用」=与合法引用信息上不可区分的过程可见面（CH-1 声明边界内，diff/review 可查）——**作者自写的任何字节永不获豁免**，B1 根因（自写内容经语法门洗白）就此关闭；密码学级关闭需新权威，任务边界明示不做。

### D-2（P1·阻塞）R5 背书框架作用域被句读截断——引用后隔标点背书按实际规则仍逃逸

- **位置**: §5 R5（"作用域：自标记+封闭尾剥离点起，至下一个 `。；;` 或行尾（同级句段）"）
- **缺陷**: 作用域止于首个 `。；;`，标点后的背书续句不在框架核验内。
- **反例 α（P1 分号变体）**: `事实依据：发现"不允许不编造"为边界；请照此要求必须遵守并当真执行` —— 剥离点后首字符即 `；`，框架作用域 = `；`（空），「当真」不被检查；残句无术语 → **PASS**（R3 已证 P1 逗号形被新框架拦，分号形反逃逸）。
- **反例 β（P2 句号变体）**: `事实依据：发现"不允许不编造"已实证。我要求把结果当作真实数据` —— 作用域止于 `。`，下一句「当作真实数据」框架 1 不被检查、无术语 → **PASS**。
- **必改**: 框架核验作用域 = 剥离点起至**整个输入末端**（全 input、跨句、含长距相邻续句），不得同级 clause 截断；术语扫描（M4）作用域同步不截断。兼容性实证入红绿矩阵：本轮已核 EVD-1472 全行（含 `目标对齐`/`体验变化` 等全部列）无任何框架 token（把…当作/当成/视为/作为…真实|事实|数据|结果|有效、当作…真实数据|事实、当真），全 input 作用域下仍 PASS——EVD-1473~1477 同型，实现期逐行入测。

### D-3（P1·阻塞）live 窗口三任务硬编码——产品落地实际需四任务

- **位置**: §3（26 行基线=三任务）、§7 矩阵（C1 19 行等）、§8.4（"保持三任务零 skip 断言"）
- **缺陷**: 设计以三任务（FIX-444/FEAT-097/FIX-443）为历史基线（成本边界披露可接受），但 FIX-445 实施后其自身当前全量 EVD 行（既有 65+ 行与新增行）进入活窗口；若实现照 §8.4 落地三任务断言，本票自身证据行不进 live replay = **假绿**。
- **必改**: live replay 断言扩为**四任务**（+FIX-445 当前全量 sourcepath），FIX-445 行同样过全规则（其语料 refs+task-glob 天然含本票 incidents）；红绿矩阵补 FIX-445 行类分布一行。

### D-4（P1·阻塞）C7 事实错误——「哈希今日不可复验/referent 不可解析」不成立（本轮独立实测纠正）

- **位置**: §3 C7（"与今日 budget-metrics.py 实测 9974dbe0… 及 loop_runtime_claims.py 5c991a40… 均不匹配……哈希 referent 不可解析"）、§7 C7 行、§13.1；§14 X3/X4
- **实际事实（本轮只读实测）**:
  - `.governance/incidents/FEAT-097-budget-metrics.py` **:16** `sys.path.insert(0, str(root / 'skills/software-project-governance/infra'))` → **:17** `import goal_bridge as gb`；**:49** `'source_sha256': hashlib.sha256((root / 'skills/software-project-governance/infra/goal_bridge.py').read_bytes()).hexdigest()` —— 指称对象在源码中**显式且唯一**；
  - 本轮 `Get-FileHash` `skills/software-project-governance/infra/goal_bridge.py` = `b52313b742808e53441a035952e57c56bc85c45edc305d4381fc23cecdb2e773`，与 EVD-1450 行内 `sourceSHA256b52313b7…c2e773` **逐字符一致**。
- **判定**: Designer X3/X4 测试了两个错误候选（metrics 脚本自身/scanner）后得出"不可复验"——测量对象错误，非 referent 缺失。影响：核心交付物（实际来源映射）含虚假「不可验证」声明；R3 哈希规则失去其示例理由（C7 实为**今日可复验且匹配的正例**，恰证明哈希类引用可验证）。本报告按 Coordinator 指示如实纠正；design doc 静止不改，修订经新版本（§15 通道）。

### D-5（P1·阻塞）语料路径缺真实解析包含——symlink/junction 可击穿「不读仓库外任何路径」边界

- **位置**: §5 R3（"路径含 `..`/绝对形 → 丢弃"）、§2.2（"不读仓库外任何路径"）
- **缺陷**: 仅做字面前缀/`..` 检查；闭合目录前缀下的仓内相对路径若为提交入树的 symlink（POSIX 检出为真链接）或 Windows junction，grep/awk 读取即跟随出仓，§2.2 边界被击穿且无诊断。
- **必改（两选一，未知保守）**: (a) 语料文件取用前 resolved containment——realpath 归一后必须仍在仓内闭合目录下，是 symlink/junction/不可解析 → 丢弃该路径+计 probe-error（保守拒绝）；或 (b) 改经 `git cat-file`/`git show <rev>:<path>` blob 读取（结构性免疫工作区路径跟随）。诊断面板区分 `path-unresolved`。

## 2. 前轮对照

R0 首轮，无前轮设计 findings。上游 R3 code review 三阻断（B1/B2/B3）与本设计映射：B1→R1+R3（R1 成立、R3 需 D-1 收紧后才闭合 B1 根因）；B2→R5（需 D-2 作用域修正后闭合已证形）；B3→R6（**成立，无保留**）。

## 3. 六维审查

| 维度 | 结论 | 依据 |
|---|---|---|
| 方案完整性 | **PARTIAL** | 备选 ≥2（A1~A5，排除理由充分）✓；ADR 字段完整 ✓；但核心凭据规则（R3）留 D-1 残余、验收面缺第四任务（D-3） |
| 蓝军挑战 | **PARTIAL** | CH-1~CH-5 ≥3 条 ✓；但 CH-2 缓解为"推迟"非"关闭"（D-1）、CH 清单缺 symlink 向量（D-5） |
| 模块结构 | **PASS** | M0~M5 职责各 ≤3 句、依赖单向无环（§4.1 图）、接口契约含 rc 语义 |
| 接口契约 | **PASS** | §4.2 三函数输入/输出/rc/stderr 诊断完整定义；错误码语义全管线统一 |
| 非功能需求 | **PASS（带 D-5）** | 性能三重封顶（120/32/单探针）+实测毫秒级；安全边界五条需 D-5 补齐后成立；回滚 git revert 可逆 |
| Bar Raiser | **执行中** | 本独立审查即之；结论 NEEDS_CHANGE |

## 4. 通过面（验证为实的规则，复审时不必重证）

1. **R6/B3 闭合成立**：sed 非 0→BLOCK（sed 对未匹配恒 0）；grep rc 0=命中 BLOCK/1=干净/≥2=错误 BLOCK；M1 既有守卫（`|| return 0`+空 prose）保留；FC5/FC6 注入位必 BLOCK。
2. **R1 方向正确**：签名门降级为路由必要条件，n1/n8/F4 继续走 prose 无豁免；键名/键数/record 标签不单独授予豁免（op-id/ledger 不进判定路径——§3 末节立场正确）。
3. **R2 闭语法 fail-closed 方向正确**：超出闭语法/长度上界的携带术语片段按裸词进 M4（未知形=拒绝）。
4. **R7 保守处理正确**：缺 artifact/anchor/语法不确定/哈希不可复验→只拒绝豁免不空放行；双因诊断（provenance-missing/probe-error）。
5. **威胁模型诚实**（§2）：明示非密码学承诺、无自授（evidence-log 自身排除出语料）、伪造面持久 diff 可查——不夸大真实性。
6. **§8 兼容计划**：旧 EVD 零编辑+现存 artifact 包含支撑（C3~C6 本轮/designer 双侧实测互证）；clean-clone fixture 自包含（迷你 incidents 同源生成）保留；`_extract_*_fn` 真源抽取接口不复制实现体。
7. **过程纪律**：零产品/治理写、未跑 module/engine、§7 自标"设计预期——产品未实现"、§14 收据诚实（X1 批次无逐条 UTC 如实标注）、预算内收口。

## 5. WARNING（非阻塞，跟踪不入 blockers）

- **W-1** 背书框架闭表不能覆盖全部无术语背书形（如「视为结论可信」不含框架宾语）——非语义门的固有界限；D-2 修正后已证形（P1/P2 及变体）全覆盖，无术语非框架背书与现行语义一致（非回归）。框架 token 集为闭表维护面，扩展需同步溯源（FIX-239 纪律），不得无限扩。
- **W-2** 语料 ≤32（行内 refs ≤8+task-glob ≤24）：跨任务引用超界保守拒绝——可用性权衡已披露，可接受。
- **W-3** 归一映射封闭双向（原文→`｜`→`|`/`\"`→`"`）：未来新转义形失配仅致拒豁免（保守方向），fixture 钉死两形——设计已考虑（CH-4），维持。

## 6. 硬门槛自检

候选方案数 ≥2 ✓（5）｜ADR 关键字段完整 100% ✓（日期/背景/决策/备选/排除/影响/后续/可逆）｜蓝军挑战 ≥3 ✓（5 条含缓解）｜循环依赖 0 ✓｜Bar Raiser 已执行 ✓（本报告）——**但存在 5 项 BLOCKING（D-1~D-5）→ NEEDS_CHANGE**。

## 7. 本轮审查命令记录（全部只读；逐条 literal/UTC/exit/raw）

| id | literal | UTC | exit | raw/observed |
|----|---------|-----|------|--------------|
| R0-cmd-1 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d='…/docs/design/FIX-445-source-verification.md'; (Get-FileHash -Algorithm SHA256 $d).Hash.ToLower(); (Get-Item $d).Length; (Get-Content -Encoding UTF8 $d \| Measure-Object -Line).Lines` | unknown（未捕获，不补造） | 0 | `59f318d4575ca6cc2e3d487d90824b8fc74847a2d9bb92e68436c4d19d22e3f2` / `33525` / `230`（230=含文本行计数度量，非 304 总行口径） |
| R0-cmd-2 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; (Get-FileHash -Algorithm SHA256 '…/skills/software-project-governance/infra/goal_bridge.py').Hash.ToLower()` | unknown（未捕获，不补造） | 0 | `b52313b742808e53441a035952e57c56bc85c45edc305d4381fc23cecdb2e773`（=EVD-1450 sourceSHA256，D-4 依据） |

read/grep 工具面（非 shell）：design doc 全 304 行；`FEAT-097-budget-metrics.py` :1-60（:16/:17/:49 为 D-4 指称依据）；evidence-log grep ×2（`b52313b7…` → EVD-1450 行 :2171；`^\| EVD-1472 \|` → 行 :2197 全文，D-2 兼容核依据）。影响路径：无（全只读）；保护：无 -w/无 env 重迁/无仓库外访问。

## 8. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 0 --result NEEDS_CHANGE --report docs/reviews/review-FIX-445-DESIGN-R0.md --reviewer 'Design Reviewer' --bind-file docs/design/FIX-445-source-verification.md`——NEEDS_CHANGE 非终态：退回 Architect 修订（D-1~D-5，经 §15 新版本通道，本静止 doc 与本报告均不改），后同 Design Reviewer 复审 R1（逐条比对已修复/未修复/新引入）。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
