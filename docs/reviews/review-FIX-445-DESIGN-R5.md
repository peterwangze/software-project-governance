# FIX-445 Design Review R5 — R4-A 闭表修订独立审查（同一 Design Reviewer · DEC-336 有界段）

- **轮次**: R5（DEC-336 用户授权的有界闭表修复 delta 轮，ledger 连续不 reset；R4 BLOCKED1/seq38 后裁决 (a) 修复路线）
- **前轮 prev**: `docs/reviews/review-FIX-445-DESIGN-R4.md`（SHA256 `16417d996158612e166c2625f1f5356b23445e1293d426615153b09f7ae7900f`/10,679B）——本轮周期显式 read（备审轮全文 74 行 + 本轮 :1-12 复核 header/verdict，静止未改）
- **审查方**: Design Reviewer Agent（R0~R4 同一实例；只读；唯一写面 = 本报告；不实现、不评 Developer 实现为 design pass、不跑 module/engine/probe）
- **审查对象绑定**: `docs/design/FIX-445-source-verification-R5.md` — 本轮实测 SHA256 `503677c3d9e4fd166c72974cfd2285afeab774aff69dd8159b87056d664d6511` / 8,498 bytes / 49 行（read 工具全读）——与 Coordinator 静止绑定精确一致
- **审查范围**: 仅 R4-A delta（T-2′ 白名单/Guard G/整拒规则/escape offset 映射/T-1 字数更正）；R4 已过面与 R2/R3 全部已过面不重证
- **结论**: **APPROVED_WITH_NOTES**（无未解决 BLOCKING finding；备注保留跟踪）

```json
{"verdict": "APPROVED_WITH_NOTES", "round": 5, "unresolved_blockers": 0}
```

---

## 0. 结论

R4-A **闭合**：T-2′ 白名单（U+4E00..U+9FFF + ASCII 字母数字、符号集空）翻转黑名单——R4-A 五变体（`，`/`、`/`！`/`？`/tab/escaped-`\n`）及全角空格/CRLF/未知 Unicode/CJK 扩展全部白名单外终止不入 span，残文照扫（§1.1）。**Guard G（DEC-336 核心）闭合**：七算子闭集｛把/将/当作/当成/视为/作为/当真｝span 内硬拒——无分隔连写三框架形全部 BLOCK，且独立于 M5（无 neg-prefix 交互、不弱化 full-input）；合法 C6 载荷不含任何算子（`结果`为宾语 token 不在 guard 集）兼容 PASS。**escape offset 闭合**：切片独立严格解码+逐字符相等校验+变长 raw 映射（每 escape 给 decoded→raw 区间）+计数 ToolFault——`\uXXXX` 6/surrogate 12 等标准变长由映射算法承载，不一致故障传播 BLOCK。**pair 字数更正**（5 字符，区间 [68,73)/[81,114) 分解 12+1+8+3+9=33 核对无误）。结构面/区间纪律/四强制判定/候选/蓝军/NFR/测试全保留或加强。一轮 AWN 备注（§3）显式记录链级既有残余与实现注意，**非风险接受**。

## 1. R4-A 闭合验证（逐项过表）

### 1.1 白名单翻转（五变体 + 全族）

| 形 | 规则路径 | 结果 |
|---|---|---|
| `…我编造了测试结果，请当真执行` | `，`(U+FF0C) 白名单外 → 终止单元不入 span；`当真` 留残文 → M5 | **BLOCK** ✓ |
| `、`/`！`/`？`/tab/escaped-`\n`/CRLF/U+3000/未知 Unicode 连接形 | 同上（全部白名单外） | **BLOCK** ✓ |
| 候选内部含 tab/控制字符 | **整拒规则**（:17）——无 leading 截断消尾，尾段留残文可见 | **BLOCK**（术语/框架在时）✓ |
| 合法 C6 两单元（纯 CJK） | 白名单内 ✓ 无 guard token ✓ | **PASS** ✓ |

黑名单穷举问题消除（白名单外=无限类一律终止）——与链上闭表纪律一致；`-`（hyphen）不在白名单 → `check-quoted` 不可能嵌于单元内，无 nested-token 混淆 ✓。

### 1.2 Guard G（无分隔连写——DEC-336 核心）

- `check-quoted 我编造了测试结果当真`（无分隔 juxtaposition）→ span 含 `当真` → **整 span 拒豁**（不截前缀不留尾段）→ 残文裸术语+框架 → **BLOCK** ✓（§3R :26）。
- 七算子族=三框架闭集全部运算子（把/将/当作/当成/视为/作为/当真），**不含宾语 token**（真实/事实/数据/结果/有效）——合法 C6 载荷（`我编造了测试结果`/`本次幻觉结果已通过`）逐 token 核对不含任何算子 → 不误拒 ✓。
- **独立性**：guard 作用于候选 span 解码内容，与 M5 前缀窗口/neg-prefix 无交互；span 拒豁后残文仍经全 input M5+术语扫描（:15）——full-input/neg-prefix 已过面零弱化 ✓。
- 合法未来载荷恰含 guard token → 保守拒豁（:30）——诚实成本声明，扩展新票，非默过 ✓。

### 1.3 escape offset 一致映射（§2R :19 五步算法）

①严格解析 → ②escape-aware 引号扫描器定位 raw 切片（`\"`/`\\`/`\n` 两字符消费——用于引号检测安全：`\uXXXX` 中无可误判引号）→ ③切片独立严格解码+与①解析值**逐字符相等**校验（不等 → ToolFault BLOCK）→ ④候选在解码值按解码偏移识别 → ⑤**变长** raw 偏移映射（每 escape 给 decoded→raw 区间）+ C-5 删原文区间 + 计数 ToolFault。
- `\uXXXX`（6 raw→1 decoded）/surrogate pair（12 raw→2 decoded）由⑤变长映射承载，规范自洽 ✓；任何错位经③一致性校验或⑤计数校验故障传播 BLOCK（含 safe 输入）——**无 literal 二字符错位 silent PASS 通道** ✓。
- 扫描永不归一化（白名单/guard/术语判定在解码字符与原文位置）——无 ext 洗位 ✓。

### 1.4 事实更正与结构保留

- T-1 **5 字符**字面量两形（编/造/｜/幻/觉）✓；区间 [68,73)/[81,114)、span 33=12+1+8+3+9 分解核对无误 ✓；211 chars/258 bytes 双度量沿用 ✓。
- 结构面沿用：单元 1..60/≤4 单元/` / ` joiner 恰三字符/span≤80/token 前邻｛字段首/空格/`(`/`（`｝/Unicode 字符单位 ✓；第五单元溢出→语法不匹配留残文（保守）✓。
- 四强制判定：①合法 C6 PASS ✓（:25）；②separator 族 BLOCK ✓（:27-28）；③无分隔三框架 BLOCK ✓（:26 Guard G）+ 候选内违规整拒 ✓（:29）；④prose/他字段同字面/未获证/重叠/result·affected 沿用 R4 §3 ✓（:32）。
- 候选 A/B/C（C 显式拒绝"白名单无 guard"=DEC-336 明拒的 disclaimer 等价缺陷——诚实）✓；CH-R5-1..4 ✓；ADR delta/NFR（O(1) 字符判定/7 token 定位/线性无回溯）✓；测试红族（无分隔`当真`/`，、！？`/tab/escaped-`\n`/CRLF/U+3000/未知 Unicode/候选内 tab/guard-token 保守拒/escape 构造 ToolFault）+ 四任务 live 零 skip + clean-clone 自包含 ✓；22 例 3 失败保持 Developer 未诊断 ✓（:49）。

## 2. 独立对抗推演（本轮新增，无同规则逃逸）

- **joiner 滥用**：`check-quoted A / B / C / D / E` → 第 5 joiner 后单元不在语法内 → `E` 留残文 ✓。
- **单元内嵌 token**：`check-quoted` 含 `-`（非白名单）→ 不可能为单元子串 ✓。
- **T-1 通道搭车**：pair 字面量固定 5 字符无通配 → 无搭车空间；guard 对 T-1 span 恒不命中（5 字符内无算子）且无需求 ✓。
- **`\u0022` 转义引号**：扫描器两字符消费 `\`+`u` 不误判串尾；解码值含 `"` 经③⑤正确映射 ✓。
- **尾随 `\\` 形**：`…\\\\"` → 两字符消费后 `"` 为真闭引号 ✓。

## 3. 保留备注（APPROVED_WITH_NOTES——均非阻塞，非风险接受）

- **N-1（链级既有残余，显式记录非接受）**：无分隔连写且**不含七算子**的 CJK 肯定词（如 `…结果属实` 形）在 T-2′ 白名单内不可分、guard 不命中——该形**仅在伪造语料 artifact 前提下可达**（真实 artifact 整值等值把每个字节钉死，不可能追加）；属 R1-A/R2/CH-R4-2 已声明的"作者伪造仓内 artifact"链级残余（无新签名权威边界内不可闭合，闭合手段=词表堆叠或语义引擎均超 DEC-336 授权）。可见性=ops ledger+独立审查（R1 §2.7 更正口径）。本备注为边界诚实记录，**不经由本审查变成接受**；如用户欲闭合需新裁决（新权威/词表票）。
- **N-2（实现注意）**：③切片严格解码的**异常**（非法 escape 如 `\x`）须显式 → ToolFault BLOCK（规范"严格解码"隐含，实现落为显式分支+红测）。
- **N-3（实现注意）**：span>80/单元>60 溢出=整候选不匹配留残文（与整拒规则同向）——实现确认不截前缀，并入红族。
- **N-4**：22 例 3 失败保持 Developer 未诊断；Design pass ≠ product pass——实现完成后 Code Review 链 R6（ledger max 5+1）独立进行；live green 机证不人工宣称。

## 4. 六维 + 硬门槛

正确性 **PASS**（R4-A/Guard G/escape offset/字数四项闭合；对抗推演无逃逸）｜安全性 **PASS**（作者字节经白名单+guard+整拒+一致性校验四层约束；已知全部三框架形闭合；无 silent PASS）｜可维护性 PASS（白名单+guard 两闭表+因果注释；扩展新票）｜可演进性 PASS（CH-R5-4 边界保守）｜性能 PASS（O(1)/字符+固定串定位）｜测试覆盖设计面 PASS（红族齐备）。
硬门槛：候选 ≥2 ✓（A/B/C）｜ADR 字段 ✓｜蓝军 ≥3 ✓（CH-R5-1..4）｜循环依赖 0 ✓｜Bar Raiser=本审查 ✓｜**unresolved_blockers=0** ✓。

## 5. 本轮审查命令记录（全只读；literal/UTC/exit/raw 一次齐备；含报告 hash 采样不漏计）

| id | literal | UTC | exit | raw/observed |
|----|---------|-----|------|--------------|
| R5-cmd-1 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d='D:/AI/agent/claude/coding/project_management_workflow/docs/design/FIX-445-source-verification-R5.md'; (Get-FileHash -Algorithm SHA256 $d).Hash.ToLower(); (Get-Item $d).Length; (Get-Content -Encoding UTF8 $d \| Measure-Object -Line).Lines` | unknown（未捕获，不补造） | 0 | `503677c3d9e4fd166c72974cfd2285afeab774aff69dd8159b87056d664d6511` / `8498` / `36`（36=含文本行计数度量，49 为总行口径） |
| R5-cmd-2 | `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $r='D:/AI/agent/claude/coding/project_management_workflow/docs/reviews/review-FIX-445-DESIGN-R5.md'; (Get-FileHash -Algorithm SHA256 $r).Hash.ToLower(); (Get-Item $r).Length`（本报告写后 hash 采样——raw 于发送消息返程，不回填） | unknown | 0 | 见发送消息 |

read 工具面（非 shell）: R5 design doc 全 49 行；R4 report 本轮 :1-12 复核（备审轮全文 74 行）；备审轮另读 role :1-20。影响路径：除本报告外零写；零探针/零 module/engine/零值实验；旧 hashbound 文件与产品 blob 未触碰。

## 6. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 5 --result APPROVED_WITH_NOTES --report docs/reviews/review-FIX-445-DESIGN-R5.md --reviewer 'Design Reviewer' --bind-file docs/design/FIX-445-source-verification-R5.md`——**APPROVED_WITH_NOTES（unresolved_blockers=0）= 本有界 delta 通过终态**。设计链终集：R0 `59f318d4…`/R1 `9c772fe3…`/R2 `20e86d31…`/R3 `4bb38930…`/R4 `657cf89c…`/R5 `503677c3…` + 六轮 review（33cda27e…/cbbfd810…/fa37d79d…/e9cf19d5…/16417d99…/本报告）。ADR 写回按 R5 §5R+R4 §5+R3 §5+R2 §5+R1 §10+R0 §12 合成。**Design pass ≠ product pass**：Developer 按 R5 实现后 Code Review 链 R6（ledger max 5+1）独立进行；22 例 3 失败须 Developer 诊断闭环。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
