# FIX-445 — Independent Design Review R13（DEC-346 限定修订设计复审）

```json
{"verdict":"APPROVED_WITH_NOTES","round":13,"unresolved_blockers":0,"review_scope":"r12_delta_revision_per_dec346_static","implementation_authorized":false}
```

## 0. 绑定、独立性与输入

- **审查对象**：`docs/design/FIX-445-mention-interface-R13.md`（192 行全文实读，producer 已停写的终版）。SHA `3b31304a5e724b7ba1c6af08b8fd01fa030143f5fcc67b9bfc629790cbe60aed`/blob `0ed94349…` 系派发+R13-context-check.json:8 双源一致；未独立重测 hash（零 shell，如实）。
- **审查方**：DesignReviewerR13 = R11/R12 同一独立 Reviewer（authorization.json:40 `a254fb5a…`），非作者（producer `243d70ac…`）。人类外部成员/DRI 资格未知，不发明。
- **本轮实读 11 件**：R13 设计 192 行；`FIX-445-R13-context-check.json` 97 行（六 contexts+九 cp 数 declared==computed 全 match，`product_code_executed:false`）；`FIX-445-R13-review-challenges.md` 17 行；`FIX-445-R12-escalation.md` 45 行；`FIX-445-R12-closeout-check.json` 101 行（七件 SHA match/trust CLEAN/locks 0）；`FIX-445-R13-authorization.json` 47 行（DEC-346/347、`guard_design_boundary`、禁白名单清单）；`FIX-445-R13-budget-checkpoint.md` 44 行；R12 基线设计 238 行（重读）；`review-FIX-445-DESIGN-R12.md` 68 行（重读）；冷原行 source-extract 27 行（第 4 次重读，本轮重切直接输入）；`infra/archive.py` 头 60 行。另 glob×1（确认 archive.py/governance_store.py/verify_workflow.py 三件实存）+ grep×2（archive.py 入口 `main`/`migrate_by_version`/`migrate_evidence_resumable` 实在；governance_store.py 已有 `_scan_archive_ids`/hot+archive 搜索 :715-990 先例）。零 shell/执行/写/子 agent/用户交互；未读热面。
- **沿同 agent 上下文**（R11/R12 轮全文实读，硬门槛许可沿用）：角色定义、design-review/tech-review SKILL、canonical hook 1284 行/tests 1480 行（closeout 机证未变）、R10 三件套、R0/R3/R5、R9 两件、DEC336 helper、R4-escalation、CODE-R6、R11 设计 448 行、R11 报告/返 v2、`FIX-445-R12-context-check.json`（R12 轮实读）、`supplement-…-R12-evidence.md`（转录核对轮实读）。

## 1. R12 四项发现逐项裁决

| R12 finding | R13 响应独立核验 | 裁决 |
|---|---|---|
| **B4** 两样例值违边界函数 | §2.1/2.2：我对重读冷原行**自行逐字符重切**（第 4 次，独立于两机件）：1536 右邻=`原门CPU27`（`27.8` 的 ASCII `.` 切断，7cp）、1588 左邻=`9FFF与ASCIIalnum/符号集合空`（`U4E00..` 双点切出空 clause 后 21cp）——与 R13 设计、R12/R13 两 context-check 三方逐字一致；九组码点数我逐一手数（10/20/7、26/27/14、28/21/18）全部吻合。§2.3 schema 硬校验（非空 context 禁含 isterm∪pipe 任一字符，与运行时边界函数同一常量源）+ §2.4 登记机检五步（三元组与实际邻接逐字相等、计数相等、任一不符拒登记）——C-B4 三件齐备 | **已修** |
| **W-R12-1** spawn/诊断/目录不自洽 | §3：E-bash/E-engine 两发射层互斥全覆盖（零 spawn 臂由 bash 单行 stderr 承担 absent/notfile 观测）；目录前检 `[ -e ]∧[ ! -f ]` 升级为 bash 层硬断；§3.3 逐场景矩阵（异常×P-A/P-B/P-C×层×令牌）逐格自洽，M9′ 全路径一致；竞态「最后触达层」收敛。残留一处叙事级矛盾 → **W-R13-2** | **已修（附新残留 W）** |
| **W-R12-2** 归档失活 checklist 级 | §4：运行时 C4′ 相等守卫（c(T)==live_site_count 双向 fail-closed：复本增殖→三元组全拒 fail-loud；位点流失→机器强制失活，归档无法静默保资格）+ §4.2 G1/G2 SPEC（输入/输出/未知拒/超预算拒，无 hash/ID/整行名单）按 `guard_design_boundary` 如实呈报为**未授权扩围**+ M15 明示开放、readiness 明示阻断。在授权边界内已闭合至最大可达程度 | **已修至授权边界（附 W-R13-1）** |
| **W-R12-3** first-K/ordinal 充 K/预留偷位 | §5：K/ordinal 字段废除；live_site_count=登记时机测真值；N≠c 拒登记；ordinal>1 含未裁前例拒整条；增位仅后置；site_evidence 长度==N/非空/互异且入运行时 schema 硬检（双侧绑定，不依赖 checklist）——三缺陷随语义替换整体消灭 | **已修** |

## 2. Findings（本轮新发现，均非阻断）

### W-R13-1（WARNING）§4.1 不可区分性引理越界全称——「运行时层可证不可闭合」仅对已设计谓词集与读面成立，且 §7 备选漏列界内替代
引理列举的局部谓词（live 计数、clause/上下文字节、载体内容）+ 禁 hash/ID/整行锚约束下论证成立；但它**未覆盖**「扩展读面」类机制：反例设计——引擎增加 `.governance/archive/**/*.md` 读面，对三元组做 **live+archive 联合计数**：偷位世界（原出现已归档+复本 live）总计数 N+1≠N 可区分，合法世界=N 通过。该机制 (a) 在原两产品文件边界内（引擎扩展，非 infra 扩围）；(b) 不落入 `prohibited_authority_shortcuts`（纯计数，无标识符名单）；(c) 有现实可行性基础——我已实读确认 archive.py 为 evidence 归档执行引擎（md 行保存+index+integrity verify），governance_store.py 已有 hot+archive 搜索先例（:715-990）。其代价真实存在（archive IO 面需 W1 类容量语义、格式耦合、性能面），但「代价高」≠「可证不可能」。**影响**：该引理是待裁 G1/G2 扩围的论证基础——按现文本，用户被呈现「闭合唯一路径=授权 infra 扩围」的假两难。**要求**（随附条件，不改本 verdict）：(i) 任何后续修订须将引理限定为「在现设计谓词集与 P1/P2 读面内不闭合」；(ii) §7 须补列 archive-aware 运行时替代及其排除理由（或采纳）；(iii) **G1/G2 裁决材料呈报用户时必须并列该界内替代**——这是呈报完整性条件，违反则该裁决材料不完整。
### W-R13-2（WARNING）§3.2 预检作用域与 §3.3 竞态叙事首支不可达
§3.2 无条件「预检 notfile→BLOCK 不 spawn」使矩阵 P-B 目录格（引擎 IsADirectoryError）不可达（若预检在所有路径先跑）或使 §3.2 措辞过宽（若预检仅在 registry 臂跑）；且竞态叙事首支「预检 notfile→被换为普通文件→引擎 loaded」在两种读法下均不可达（notfile 预检即阻断、无后继引擎）。任一读法均 fail-closed、无假 PASS、矩阵各格自身一致——一句作用域声明可修（预检仅在 spawn 决策臂运行；P-B 引擎权威；删改竞态首支）。非阻断。
### N1（NOTE）site_evidence 元素格式未规定
运行时仅验长度/非空/互异；元素为何种裁决引用（DEC/EVD/回执）无格式约束——登记权威纪律覆盖，但建议与 `adjudication` 字段同格式要求（未来修订项）。
### N2（NOTE）逐 site 对应性=登记时义务+计数不变量，非空 TODO
§2.4 机检（定位每出现、邻接逐字相等、计数相等、回执入冷工件）+G2 漂移检构成可审计闭环；运行时不可验部分恰为 M15 面、已如实披露——回应「是否只是未知 future TODO」：不是，是指定了输入/输出/回执的义务规范。但 G2 对**已完成偷位**（count==N）确实盲——设计未过度声明（M15 归 G1 拒归档，非 G2）✓；G1 有回执重锚放行=权威信任（CH-1 级，与 registry 写面同界，如实）✓。

## 3. 独立蓝军挑战（≥3；被挑战假设：H1=引理全称成立；H2=矩阵+竞态叙事零矛盾；H3=登记证据自证）

| # | 攻击向量 | 影响 | 缓解 | 残余 | 增强 |
|---|---|---|---|---|---|
| BR1（攻击者） | M15 归档偷位（原出现归档+复本复位 count==N） | 未裁复本获免 | C4′ 对准备态（count=N+1）已全拒；完成需绕 G1 回执=权威信任（CH-1） | **开放**（设计如实列 readiness 阻断） | G1/G2 裁决材料并列 W-R13-1 界内替代 |
| BR2（攻击者） | 复本 append 致原行连带重 BLOCK（M13 fail-loud 滥用） | 可用性攻击 | 设计明示接受：无逃逸、四源门显式暴露 | 接受的可用性代价 | — |
| BR3（治理） | 登记失当（N≠c/孤证/前例未裁） | 坏数据入场 | §5 纪律①-④+§2.4 机检回执+运行时 schema 兜底 | 权威面纪律（CH-1） | N1 格式约束 |
| BR4（运维） | 预检/引擎双层竞态分歧 | 观测矛盾 | 最后触达层唯一分类 | W-R13-2 叙事首支 | 作用域一句修 |
| BR5（规模） | registry 余量收窄（180/256KiB）+entries 增长 | 逼近 oversize | 算术复核 ✓（2.8KiB×64≈180KiB）；超界硬断 | 实现票实测 | 复测含 MSITES 面 |

## 4. 六维与硬门槛

完整性/结构：supersedes 映射逐条对上 R12 基线原文 ✓；六值三源互证 ✓。架构/依赖：C4′ 并入候选遍历、诊断分层不改方向、G1/G2 界外不入图，无环 ✓。接口契约：C1-C6′+故障码+三态+场景矩阵闭表 ✓（W-R13-2 一处叙事）。安全/授权：空态等价与 M1-M6/M13-M17 机制性结论经我独立重推成立；M3 在修正值下仍拒（攻击左邻≠任一登记左邻）✓；NOT_ESTABLISHED 未自授、迁移/产品未授权、M15/readiness 如实阻断 ✓。NFR：界值复核、原门不放宽、复测入票 ✓。独立评审：同一独立 agent 第三轮、非作者；人类资格未知。硬门槛：备选 4≥2 ✓；蓝军 5≥3 ✓；ADR 字段 ✓；无环 ✓；**全门通过（零阻断）**。

## 5. 结论与随附条件

DEC-346 授权范围=新设计修 B4+三 W+冷源核对+一次 R13——该范围内四项发现全部有效闭合，**APPROVED_WITH_NOTES/unresolved_blockers=0**（设计范围通过）。**随附条件**（呈报/后续义务，非本 verdict 前提但违反将使后续裁决材料不完整）：①G1/G2 扩围呈报必须并列 W-R13-1 的 archive-aware 界内替代及其取舍；②任何后续修订须修 W-R13-2（预检作用域一句）并考虑 N1；③M15 开放、implementation_ready 阻断、迁移三问、G1/G2 扩围均待用户裁决——本通过**不构成**实施/迁移/registry 生效授权，不使产品 64tests/92.738s/1FAIL、CodeR6 BLOCKED/3、full 18 issues/exit1、四源门、B3、CPU27.8/CLI36/434339/32MiB/1500 任何一项通过；隔离 witness FAIL（写者 unknown）与 M5 冻结命中不因本报告变化。无风险接受、无白名单/单例、无自动 R14；外部人类 DRI 未知如实。本报告为唯一最终文本，机录后不默改。

（本轮 read×11+glob×1+grep×2，约 15 步/32 建议，无发散探索。）
