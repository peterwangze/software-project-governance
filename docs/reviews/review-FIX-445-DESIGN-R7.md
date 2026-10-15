# FIX-445 Design Review R7 — DEC-338 三原句增量独立 delta 审查（同一 Design Reviewer · fuse 语义适用）

- **轮次**: R7（DEC-338 有界三项 delta 轮；ledger max6+1，无跳过/重置；CODE-R6 BLOCKED3/seq40 后用户裁决）
- **前轮注入**: `docs/reviews/review-FIX-445-CODE-R6.md`（SHA256 `e7147436…` 前缀/12,775B/100 行——本轮显式 read 全文）；本人 R5 report（`fdb983d6…`/11,145B，本会话一手亲写）+ R5 设计规范（`503677c3…`/49 行，R5 正式轮显式 read，scope delta 未替代 R2/R3/R4 继续有效）——按派发要求注入面齐备
- **审查方**: Design Reviewer Agent（R0~R5 设计链同一实例；只读；唯一写面 = 本报告；**本轮零命令**——无 shell/hash/探针，hash 由 parent 绑定；反例=规范文本推演，不称 actual 产品 probe）
- **审查对象绑定**: `docs/design/FIX-445-source-verification-R7.md` — Coordinator 静止绑定 SHA256 `859ff46d1d4df723b3681ea037f64dfb9783bf3fbbbb17ecb77283e46beb9412` / 11,873 bytes / read 工具 76 物理行（Coordinator 已核；Architect 返 77 计口径不覆盖、hash 命令 54 非空行——三方度量差异如实记录，以 Coordinator 绑定为准）
- **审查范围**: 仅 R7 delta（F1/F2/F3 三新豁免+B2 断言契约+B3 准入协议及其安全边界）；R0~R5 未替换规范全部有效不重证
- **结论**: **BLOCKED**（round 7 ≥ 3 fuse 点且存在确认阻断 → T2/T4 终态 + 用户升级，无自动 R8）

```json
{"verdict": "BLOCKED", "round": 7, "unresolved_blockers": 1}
```

---

## 0. 结论摘要

**三原句在规则文本下确可 PASS**（本轮对照完整原句 :2271/:2334/:2335 + 现行 hook 机制 :722-846 逐项核）：1536 经 F1（`无预算或PASS编造` 唯一术语 occurrence，行内无其他术语/框架）；1587 经 F2（裸 `当真` :770 唯一触发，`不能` 强 1/总 1）；1588 经 F3（`含` 锚+7 算子段，段内 `当真` 折扣；行内无术语、对象词全在段外无 frame1/2 匹配）。**B2 契约**（逐例断言恢复+删除 :1193-1200 弱化——本轮 read 实证该 any() 断言在场）与 **B3 协议**（五env/禁绝对tmp/禁fallback/准入前置/禁未证实rm/D20 unknown 保持）方向正确、可直接沿用。F1/F3 经对抗推演未见同规则逃逸（各有 WARNING 级注意）。

**但 F2 存在同规则逃逸（R7-A）**：post-window 强否定计数与框架极性无绑定——与框架无关的后置强否定（否定其它谓词，不否定框架）会把活性背书洗为豁免。**这是 Coordinator 派发点名的独立挑战面，实际规则文本推演成立**。fuse 轮 → BLOCKED。

## 1. Findings（本轮阻断项；基于 §1 F2 实际规则文本推演，非 actual probe）

### R7-A（P1·阻塞）F2 后置强否定与框架极性无绑定——无关后置否定洗白对象承载背书 + 规范端点歧义

- **位置**: §1 F2（"post-window 内按否定闭表位置扫描（最长匹配，**非消费式**）计数：强计数==1 且窗口内否定 token 总数==1 → 该 frame 豁免"）
- **实际规则反例（逐步推演）**: `事实依据：将结论视为事实未经复核`
  1. frame2 命中（`视为`+`事实`，hook :766-768+try_tail 同型）；
  2. post-window（frame 终点起至 isterm/16）= `未经复核`；
  3. 强集扫描：`未`（longest-match，无更长 token）→ 强计数 1；否定总数 1；窗口内无框架算子 → 三条件全满足；
  4. **frame 豁免**；残文无术语（`视为事实` 不含 编造/幻觉）→ M4 过 → **整行 PASS**。
  语义上 `未经复核` 否定的是**复核**（另一谓词），`将结论视为事实` 的背书原样成立——正是"同句后出现强否定而 affirmation 仍成立"的逃逸面。同族：`把结果当作真实数据并未夸大`（`并未`…并 非表内？longest-match 于 `并未`——未 强 1/总 1，若 并 不属 token 则计 未）——窗口内单强否定即可豁免对象承载框架，构造空间宽（16 字符内任意"强否定+他谓"尾部）。
- **规范歧义（同 finding 组件）**: "frame match 的 operator 终点"未定义取 首算子/末算子/整 match 终点（hook 的 me=对象尾）——两读下上述反例均成立（窗口或为 `未经复核` 或含 `事实未经复核`，计数同为 1/1）；且首算子读法下矩阵 :51（`并将视为事实` 算子禁入例）与 :44 的窗口内容不同——规范-矩阵一致性依赖未定义端点。
- **根因**: post-window 为非消费式位置计数，无 R3 前缀机的完整消费/封闭填充纪律——`框架终点→强 token` 之间的内容不受任何闭表约束，无法区分"否定框架本身"（1587 `当真不能…`、:44 `是不可取的`）与"否定邻接他谓"（`未经复核`）。
- **最小修复方向（供 Designer 定稿，不代设计）**: 豁免仅当强 token **谓词化绑定框架**——封闭机制示例：①无对象框架（`当真` 裸形）：强 token 须**紧接**算子终点（1587 形 ✓）；②对象承载框架：`框架终点→强 token` 段须完整消费为 封闭填充集 ∪ 系词｛是|系|为｝（:44 `是不可取` —— 空+是 ✓；`未经复核` 无系词不消费 → 不豁免 → BLOCK ✓）；红测两向（`视为事实未经复核`/`当作真实数据并未夸大` BLOCK；:44/1587 PASS）+ 端点定义唯一化（建议=整 match 终点 me）。
- **不扩面声明**: 修复=封闭填充+系词判定的消费纪律（与 R3 前缀机同哲学），非语义引擎/新权威。

## 2. 已核实闭合面（修订版可直接沿用，R8/用户裁决后不重证）

1. **三原句 PASS 证实**（完整行对照+hook 机制，§0）；F1 使 sed :831 旧或形成特例（取代/兼容语义等价，:831 本轮 read 在场确认）。
2. **F1 规则面**: ITEM 1..8/双排除（否定 token 最长匹配+术语字 编/造/幻/觉 字节检）/NP≤16/≤2 joiner——`无法或不能编造`（ITEM 含否定）/:43（mid 含术语字）BLOCK ✓；泛化行 :40-42 与规则一致；无 EVD 特判/整句白名单/整字段免/旧行修改。
3. **F3 规则面**: 折扣爆破半径=对象承载框架不可能全落段内（对象词 真实数据/事实 等非算子 token，operator-only 段内容不下）——实际折扣面=段内裸 `当真`；段外宾语照触发（:49 `把将当作真实数据`）；无锚/<3 不触发（:50）；`，`/分隔切段各段独立 ≥3；line/field-start 锚与封闭锚集一致使用（:49 复核）。对抗形 `…枚举，然后把结果视为事实`——次句 frame 在段外照触发 ✓。
4. **B2 契约**: 逐例断言（12 BAD 行各 spawn 断言 BLOCK）+好行（含 EVD-9007 框架否定+三新形 fixture 副本）PASS+删弱化注释与 any()（:1193-1200 本轮 read 实证存在，§4 删除正确）+live per-task seen≥1/零 skip/RC0+实窗 hash/bytes/latest 记录进断言消息（不固定历史计数）✓；模块全量+独立 Code 审查必达不解锁 ✓。
5. **B3 协议**: 五env 唯一会话隔离根/禁绝对 /tmp/禁 mktemp 失败回退（fail-closed 拒执行）/准入前置（全脚本+外层 literal+写路径先返 Coordinator）/禁未证实变量 rm-rf/零 cleanup 默认/唯一 raw 路径/D20 历史 unknown 不补造 ✓——直接关闭 Code-R6 B3 类（D20 `|| echo "$REPO_ROOT"` 模式禁止）。
6. **安全语义保持（§2 声明与机制对照）**: F/G/S/P/n/A/FC 族未触碰（record 侧/Guard G/身份链/M0/R6 均在未替换规范内）；F1~F3 仅 prose/residual 层、豁免止于匹配 occurrence、全 input M5+术语扫描保持。

## 3. WARNING（非阻塞）

- **W-1（F1 背书倾向 ITEM2）**: `无异议或批准编造`（矩阵 :41 PASS）依赖无标点 NP-支配读法（`无[异议或批准]编造`）；句级析取背书读法（`无异议，或批准编造`）需逗号——逗号破坏 ITEM-或-ITEM 邻接 → 不匹配 → 术语裸留 BLOCK ✓。要求红测钉死逗号形；`批准/同意/允许` 类 ITEM2 的歧义面如实记录（结构邻接已排除危险读法，非语义保证）。
- **W-2（F2 修辞问残余）**: 矩阵 :46 `当作真实数据不行吗` 保守拒——设计已诚实披露为可用性成本（非安全洞），维持（R7-A 修复时一并入红族）。
- **W-3（F3 锚集）**: ｛含,括,列,即,是｝封闭小集——`是` 兼系词/锚双角，实现注释区分语义角；扩展新票。
- **W-4**: §3 矩阵自标"设计预期非 actual" ✓；B2/B3 的实际验证在实现/Code 审查段（本设计只定义契约）——Design pass ≠ product pass。
- **W-5**: 行数三方度量差（76 物理/77 Architect 计/54 非空）已由 Coordinator 裁定以绑定 SHA 为准——如实记录不重测。

## 4. 四设计维度 + 硬门槛

方案完整性 **PARTIAL**（三形各 ≥2 备选+排除理由 ✓/ADR delta/NFR ✓；F2 缺极性绑定语义 → R7-A）｜蓝军 **PARTIAL**（CH-R7-1~4 ≥3 ✓；未覆盖后置无关否定面——Coordinator 派发点名后本轮实证）｜风险与边界 **FAIL(R7-A)**（新增豁免路径洗白活性背书）｜可实现性 PASS（三闭表线性、两文件内、无 EVD 特判）。
硬门槛：候选 ≥2 ✓（每形 A/B/C）｜蓝军 ≥3 ✓（CH-R7-1~4）｜循环依赖 0 ✓｜Bar Raiser=本审查 ✓——**1 项 BLOCKING + round 7 ≥ 3 fuse → BLOCKED（T2/T4）**。

## 5. 本轮 read 面（零命令——派发禁 shell；hash 由 parent 绑定）

role :1-15 重载；R7 design 全 76 行；CODE-R6 report 全 100 行（显式 prev）；evidence-log 定向 grep 三行完整原句（:2271/:2334/:2335）；hook `commit-msg` :722-846（isterm :725-729/try_tail/前缀机 :772-807/M0 :816-839/sed :828-833）；test_hooks.py :1152-1231（any() 弱化 :1197-1200+live 断言区 :1214-1229）。R5 report/spec 本会话一手+R5 轮显式 read。影响路径：除本报告外零写；零 shell/零产品写/零仓外访问/零 .governance 写。

## 6. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 7 --result BLOCKED --report docs/reviews/review-FIX-445-DESIGN-R7.md --reviewer 'Design Reviewer' --scope delta --delta-base docs/reviews/review-FIX-445-CODE-R6.md --bind-file docs/design/FIX-445-source-verification-R7.md`——**BLOCKED = 终态（非通过）**：T4 用户升级（无自动 R8），裁决项：(a) 授权 F2 极性绑定修订（R8 仅修 R7-A：封闭填充+系词消费纪律+端点唯一化+双向红测；F1/F3/B2/B3 按 §2 沿用）；(b) 用户逐项点名接受指定残余（本报告不代接受）；(c) 收缩 F2 范围至无对象 1587 形（:44 类对象承载否认句回落 BLOCK——可用性代价）。Design pass ≠ product pass；产品两 blob a327f812…/0e8aff2f… 未触碰。本报告发送后不追加；补充经独立 supplement 由 Coordinator 处理。
