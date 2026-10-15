# FIX-445 — Independent Design Review R12（DEC-345 限定修订设计复审）

```json
{"verdict":"BLOCKED","round":12,"unresolved_blockers":1,"review_scope":"r11_delta_revision_per_dec345_static","implementation_authorized":false}
```

## 0. 绑定、独立性与输入

- **审查对象**：`docs/design/FIX-445-mention-interface-R12.md`（238 行全文实读）。SHA256 `d9ecd153e4c1d9ba49bdf7dc191adb3ed35ecd14b571cb919be5a4704820fae4` / git blob `3482a6fb…` 系派发供应，本 Reviewer 未独立重测（只读约束，如实）。
- **审查方**：DesignReviewerR12 = R11 独立 Reviewer 同一 continuable agent（boundary.json:29 指定 `a254fb5a…`），非 R12 设计作者（producer `243d70ac…`），未参与其编写。human external membership / DRI 资格未知，不发明人类评审。
- **本轮新读 11 件**：R12 设计 238 行；`FIX-445-R12-review-challenges.md` 26 行；`FIX-445-R12-frozen-bindings.json` 39 行（五件 SHA 全 match，`tests_executed:false`）；`FIX-445-DesignR12-boundary.json` 83 行；`FIX-445-R11-escalation.md` 62 行（DEC-345 于 §56-58）；`FIX-445-DesignR11-transfer-audit.json` 43 行（6 行转录级差异核毕——空格/补词级，两版 findings 实质一致，Coordinator 补词不作本 Reviewer 原话）；机录版 `review-FIX-445-DESIGN-R11.md` 145 行；`FIX-445-DesignR11-returned-v2.md` 145 行；冷原行 `FIX-445-R10-source-extract.md` 27 行（重读，用于 POC 邻接上下文核对）；基线 R11 设计 448 行（重读）；`skills/tech-review/SKILL.md` 196 行（重读）。
- **沿同 agent 会话上下文沿用 22 件**（R11 轮实际全文读取，其中 hook/tests/R11design/机录review/返v2 五件经 frozen-bindings 机证未变）：角色定义、design-review SKILL、canonical `commit-msg` 1284 行、`test_hooks.py` 1480 行、R10 三件套、R10 契约设计、契约裁决报告、health-resume 报告+澄清、CODE-R6、source-verification R0/R3/R5、R9 审查+协议补核、DEC336 helper（只读未执行）、R4-escalation、R11-artifact-check。
- **工具面**：本轮 read×11，零 shell/零执行/零探针/零写/零子 agent/零用户交互；未读热面（热事实 Coordinator 单源供应）。日期 2026-10-13 沿供应。

## 1. R11 六项发现逐项裁决（已修/未修/新引入）

| R11 finding | R12 响应核验 | 裁决 |
|---|---|---|
| **B1** W1 去重锚定例 | §7 独立重算：glob_sel=F01..F24、F09 占位、glob 贡献 23（F01..F08∪F10..F24）、pool=32refs+23=55、files=pool[:32]=32 refs、GLOBCAP=8/POOLCAP=23/PATHDROP=0、F09 经 refs 恰一次、F25 任何情形不可入选、三条 focused 断言明确——全部正确，F09 为 incidents 路径系 `_REF` 合法形 ✓ | **已修** |
| **B2** 合法 clause 断言复用逃逸 | POC 机制独立重推（§2-BR1/BR2）：M3 组合行 C3 拒（实际左邻 `我确认以下断言且并非引用` ≠ 登记值）→ X 留守 → M5 `已知no-separator` 14cp 窗残留 → **BLOCK** ✓；M4 逐字复制 C4 拒（原行=#1、复本=#2>K=1）→ 留守 → M5 拒 ✓；C4 计数与载体验证解耦（载体失败不释放槽位）✓；§8 头部全称声明已撤回并限定 ✓；无 EVD id/行号/hash/task 白名单或单例分支（凭据维度=内容+时序+任务域+载体链，结构通用）✓。**但修订引入新阻断 B4（见 §2）**——B2 的机制成立，其登记样例数据自坏 | **机制已修；新引入 B4** |
| **B3** 字节/码点混淆 | §4 码点契约：全部索引/界/包含在解码 str 上，与 regions(:445)/dmap(:239-332)/dels(:637-655) 同轴；字节仅限相等性表述；artifact-check 双区间作正/负锚（实现票必测）✓ | **已修** |
| **W1** 缺席/故障欠规格 | §5.2 闭分类表（absent/notfile/read/oversize/malformed/schema）+ MREG 诊断 + 引擎分类权威 + 部署自检 ✓；但残留三处自洽性缺口 → **W-R12-1（新 WARNING，见 §2）** | **实质已修+新残留** |
| **W2** registry 自身路径矛盾 | §5.1 固定 authority path 常量、`registry-path` 故障码、三前缀闭集仅作用条目 carrier_path、registry 不能自任载体（自动被前缀检查拒）✓ | **已修** |
| **W3** 资源无界 | §6 界值表（entries≤64/registry≤256KiB/载体≤2MiB/ΣIO≤8MiB/逐条读-检-释）算术核毕（64×~2.6KiB≈166KiB≤256KiB ✓；8MiB=4×2MiB ✓）；P1/P2 双读面解耦消除载体来源歧义；交叠单读缓存；超界二分（authority 硬 fault / carrier 条目不可用）；实测与 32MiB/1500 复测诚实列为实现票待办 ✓ | **已修** |
| （W1b）在场空 entries spawn | §5.3 三态 + M7 钉死 + R11「空→零 spawn」字句作废 ✓ | **已修** |

## 2. Findings

### B4（BLOCKING·新引入）§3.2 登记样例上下文值违反设计自身边界函数——按样例登记则 M2 对 2/3 行不可达成

§3.2 声明样例值「由 source-extract 原行**按边界函数**切分」，边界函数=isterm 闭集 ∪ `|`（R11 §6.2 沿用；hook :726-728 isterm 含 ASCII `.`）。对冷原行逐字符独立重切：

- **EVD-1536 右邻**：X=`无预算或PASS编造` 后 `。` 起，下一个 isterm 是 `27.8` 中的 ASCII `.` → 真右邻 clause = **`原门CPU27`**。设计登记值 `原门CPU27.8/CLI36/semantic434339/32MiB/1500与installedhook/用户config保持` **含 `.`，不是任何边界函数下的合法 clause**。
- **EVD-1588 左邻**：X 前文本 `closed单元whitelist U4E00..9FFF与ASCIIalnum/符号集合空`——`U4E00..9FFF` 含两个 ASCII `.`，边界函数切分为 `closed单元whitelist U4E00`｜（空）｜`9FFF与ASCIIalnum/符号集合空` → 真左邻 clause = **`9FFF与ASCIIalnum/符号集合空`**。设计登记值含 `..`，**同违**。
- 1536 左（`目标含先设计后twofile修及最终交付`）、1587 左右（`onlyR4A封闭…回归`/`要具体closedguard`）、1588 右（`sourceC6合法载荷无token`）四值核验合法。

**后果链**：运行时邻接 clause 是极大 isterm-free span，永不等于含 `.` 的登记值 → 按样例登记则 C3 在**原行自身**上失败 → 零豁免 → EVD-1536/1588 迁移态仍 BLOCK（1536：sed 或形中位闭表无 `预算`→裸 `编造`；1588：`当真` 框架+前缀残留）→ **§8 M2 的「三行 PASS」按设计自带样例数据不可实现**（仅 1587 可过）。§5.2 schema 仅校验 context 长度（空或 1..256），不校验 clause 合法性——正是「手工切分」错误得以存活的缺口。方向 fail-closed（无逃逸），但与 R11-B1 同类（验收参照材料与规范自相矛盾），且打击的是 DEC-345 修订的核心交付（迁移登记参照值）。**解除**：(a) 两值修正为真邻接 clause（`原门CPU27`；`9FFF与ASCIIalnum/符号集合空`——两者仍具区分性，C4 仍为主约束，修正不弱化安全）；(b) schema 增设 context 合法性硬校验（非空则不得含任何 isterm∪`|` 字符，违者 `registry-schema` 拒）；(c) 迁移机检义务从「码点数」扩为「登记三元组与实际邻接 clause 逐字相等」。

### W-R12-1（WARNING）§5.2/§5.3/M9 spawn-诊断-目录语义三处不自洽
① §5.2 行 1「DIAG **必发** MREG=absent」与 §5.3 态 1（缺席→零 spawn）矛盾：纯 prose 无 spawn 时引擎不运行，无 DIAG 可发——「必发」仅 spawn-armed 路径（record 非空/TOCTOU）可满足；② 目录 at-path：`-f` 为假→纯 prose 臂不 spawn→`IsADirectoryError` 永不触发，行 2 的 `registry-notfile` 硬断与 M9 无条件承诺在纯 prose 臂**不可达**，而 §5.2 结尾段又称「预检 false 类（悬空链接/目录）与 absent 同收敛」——同文件内目录语义两写（硬断 vs 同 absent），行为随批内有无 record 行而变。全程零豁免（无假 PASS），定性 WARNING：须规定 MREG 输出仅定义于 spawn-armed 运行（或 bash 侧轻量诊断行）并统一目录语义、修正 M9 措辞。

### W-R12-2（WARNING）归档失活为 checklist 级，非机器可检
BT-R12-1 承认非机闭。独立评估：触发需复合治理失效（原行归档+复本在场+失活步骤被跳过），且 CH-1 攻击者可直接改 registry 故该通道不新增其能力；live 四源门与 M2/M12 期望测试提供检出。**非** DEC-345 所禁的「以披露代替修复」——M3/M4 已有机制拒绝；此为独立残余。但迁移/实现票必须含**机器可检**归档守卫（如 governance-store/archive 对命中活跃条目三元组的行在无失活回执时拒绝归档，或检查器校验活跃条目三元组仍在 live log），否则失活仅靠流程单。

### W-R12-3（WARNING）ordinal≠1 时 K 语义欠规定
§3.3「登记 ordinal 以迁移时机检实值为准…按实值登记（机制通用支持）」可读作 K=实值 N 即豁免第 1..N 次——将**未经裁决的更早复本一并豁免**；且 schema 许 K≤8 而无「K=注册时已存在且经逐个裁决的出现数」约束——K>1 且部分裁决出现未落地时，攻击者逐字复本可落入前 K 槽**偷取豁免位**（并使后继合法出现意外被拒）。须规定：K 逐出现裁决、只登记已存在出现、增位仅后置追加。

## 3. 独立蓝军挑战（≥3，标准格式；假设被挑战：H1=登记数据天然与边界函数一致；H2=首 K 出现≡冻结出现；H3=缺席可观测性免于 spawn 结构）

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|---|
| BR1（攻击者） | 断言前缀组合（R11-M3） | 迁移态新断言求免 | C3 邻接等值拒（独立重推 BLOCK） | 低 | 已机制闭合 |
| BR2（攻击者） | 三元组逐字复制（R11-M4）/ 远距断言嵌入（上下文外再添断言） | 复用求免 | C4 首计数拒（复本恒 #2>K=1；置于原行前需改写 append-only 日志=CH-1 界，与现行全部门同一完整性假设）；远距嵌入内容留残文照扫 | 低（归档通道另计=W-R12-2） | 迁移票机器归档守卫 |
| BR3（维护者） | 按样例登记（B4） | 迁移「成功」但 2/3 行仍 BLOCK，M2 假承诺 | schema 无 context 合法性校验 | **高（本阻断）** | 修正样例+schema 硬校验+机检扩程 |
| BR4（运维） | 目录/悬空/TOCTOU 部署错误（W-R12-1） | 观测承诺（MREG=absent/notfile）部分不可达 | 零豁免方向 | 低 | 统一 spawn-armed 诊断定义 |
| BR5（治理） | K>1 前置偷位 / ordinal≠1 连带豁免（W-R12-3） | 未裁决复本获免 | 写权威+对抗复核 | 中 | K 逐出现后置登记纪律 |

## 4. 六维与硬门槛

完整性/结构：R12 delta 结构完备、替换映射（supersedes）逐条对上基线原文 ✓，但 §3.2 样例数据错误（B4）。架构/依赖：POC 并入 M6c→M3 无新环 ✓。接口契约：C1–C6 闭表+故障码+三态调用大体完备；B4（登记数据合法性）+W-R12-1（自洽性）未过。安全/授权：空态等价、M1 空态 BLOCK、攻击矩阵 M3–M6 机制性拒绝均独立复推成立；NOT_ESTABLISHED 未被自授（§12.2① ordinal 机检假设如实、§0 不变项沿用）✓。NFR：界值有据、原门不放宽、W1b 钉死 ✓。独立评审：本报告同一独立 agent 复审，非作者；人类资格未知如实。硬门槛：备选 4+6≥2 ✓；蓝军 5≥3 ✓；ADR 字段 ✓；无环 ✓；接口契约与数据一致性门 **FAIL（B4）**。

## 5. 结论与解除条件

Round 12 = DEC-345 授权的一次复审（账本 max10+1 后 +1）；存在阻断 → **BLOCKED，零自动 R13**，升级用户裁决。解除条件：**C-B4**（三件：样例两值修正；schema context 合法性硬校验；迁移机检扩为三元组逐字核对）为必要条件；**C-W1/W2/W3**（MREG 诊断 spawn-armed 定义+目录语义统一+M9 修正；机器可检归档守卫入迁移/实现票；K 逐出现后置登记纪律）为随修订必备。修订须用户新裁决授权 + 新独立审查，本 Reviewer 不代行。

**不变项**：产品两文件零改动（frozen-bindings 机证）；FIX-445 blocked；64 tests/92.738s/1FAIL、Code R6 BLOCKED/3、完整四任务源门、B3 保护、CPU27.8/CLI36/434339/32MiB/1500、full 健康 16 issues/exit1 全部保持，本审查不使其任何一项通过或减轻。本 BLOCKED 不否定 DEC-345 授权边界——POC 架构与五项修复（B1/B3/W2/W3/W1b）经独立核验成立；阻断仅在登记样例数据的自洽性。设计通过≠实施授权≠迁移授权≠产品验收；无风险接受、无自动 R13。本报告为唯一最终文本；如需校准，经 Coordinator 保全本报告后另件，不默改 hash-bound 史。

（本轮 read×11，约 12 步/32 建议，无发散探索。）
