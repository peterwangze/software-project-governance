# FIX-445 — Independent Design Review R14（DEC-348 归档闭合比较设计复审）

```json
{"verdict":"APPROVED_WITH_NOTES","round":14,"unresolved_blockers":0,"review_scope":"archive_closure_comparison_per_dec348_static","implementation_authorized":false}
```

## 0. 绑定、独立性与输入

- **审查对象**：`docs/design/FIX-445-archive-comparison-R14.md`（134 行全文实读，producer 已停写）。SHA `a80a768f…`/blob `9b2945b6…` 系派发+authorization.json:36-37 双源一致；未独立重测 hash（零 shell，如实）。
- **审查方**：DesignReviewerR14 = R11/R12/R13 同一独立 Reviewer（authorization.json:13），非作者（`243d70ac…`）。人类外部成员/DRI 未知，不发明。
- **本轮实读 10 件**：R14 设计 134 行；`FIX-445-R14-authorization.json` 60 行；`FIX-445-R14-review-challenges.md` 20 行；`FIX-445-R13-closeout-and-scope.md` 61 行；R13 报告 52 行（沿上轮 readback 原文）。**源码一手核验 6 段 5 文件**（不沿作者 read 表冒证）：`archive_indexing.py:200-359`（`_extract_evidence_from_archive_file` :218-244：`| EVD-` 前缀+`_EVD_ID_SHAPE_RE` 双形态+`errors="replace"` 仅 ID 面；`_UNSTRUCTURED_ARCHIVE_PREFIXES` :346）；`governance_store.py:715-834`（`_scan_archive_ids` rglob+OSError 静默 continue 先例、`_next_row_id` 碰撞拒、`_validate_row_shape` 单源、`_post_write_append_check` 披露不恢复）；`archive_migration_engine.py:85-209`（`_write_archive_file` 普通 open；增量命名纪律 :135-174「never overwrites foreign content」；`BigTableMigrationError` :199-204）与 `:981-1170`（`_evidence_apply_commit` 锁内 archive→hot→finalize、双 digest、`hot_table_diverged`/`archive_target_conflict` 拒绝、journal/batches/resume 世界判定；落盘 `archive/evidence/` 扁平 :1168）；`archive_entity_migration.py:330-454`（legacy 路径、**任务列可为逗号分隔多 ID** :347、`:425-437` 直接构造 base 文件名+`"w"` 模式、`:438` 直接热重写）；`archive.py:895-1024`（`verify_archive_integrity` 三查=引用存在/无孤儿/逐类计数交叉；`rebuild_index` 纯派生；子目录扁平 glob :923-928）。**未读段如实标注**：`archive.py:608-797`（tasks 编排腿，与 B 门无关——evidence 写路径已由 engine/entity 两段独立钉死）与 `engine:667-866`（stage/compose 细节）——均不影响下述 findings。零 shell/执行/写/子 agent/用户交互；未读热面。
- **沿同 agent 上下文**：角色/双 SKILL、canonical hook/tests、R10-R13 全链设计与报告、R0/R3/R5、R9 两件、DEC336 helper、R4-escalation、CODE-R6、历次 context/check 工件（R13 closeout 九件冻 SHA match）。

## 1. R13 附带条件修订裁决（W1/W2/N1）

| 项 | 核验 | 裁决 |
|---|---|---|
| W-R13-1 引理全称 | §2.1 撤回全称、限定 P1/P2 谓词集、反例升格为方案 A、假两难撤回、并列呈报由 §6 履行 | **已修** |
| W-R13-2 预检/竞态 | §2.2：预检仅 spawn 决策臂（P-A/P-C）；P-B 引擎权威（我核对：引擎 IsADirectoryError/ENOENT 分类 :987 前的加载面成立）；不可达首支删除；可达竞态闭集三支与矩阵逐格一致 | **已修** |
| N1 格式 | §2.3：`^DEC-\d+$` typed 引用+互异入 `registry-schema`，不发明 writer；对应性仍归登记义务（R13 N2 边界保持） | **已修** |

## 2. Findings（本轮新发现，均非阻断——但 ①② 为呈报/实现票强制前置条件）

### W-A1（WARNING）方案 A 完整性/资源闭表缺口：枚举失败静默为空 + 无文件数/时长界
§3.2 声称「拒方向全列/不允许静默截断」，但漏两类：**(a) 目录在场但不可枚举**（权限）——glob 静默返回 `[]`，与「目录缺席=absent 合法态」不可区分→a(T)=0。诚实态多为保守拒（总数≠N），但**偷位前提**（active 原行已归档+live 复本）下枚举失败使总数回落 N→复本获免——fail-open 组合（需 CH-1 级 chmod+复本写入，被既有直改残余主导，但闭表全称声明为假）。**(b) 16MiB 字节界不约束文件数**——海量小文件的 glob/open 调用开销无界，且不触发任何故障码（静默慢，非 fail-closed）。修正（实现票前置）：错误传播式枚举（scandir/stat 判别在场-不可枚举→`archive-plane-enum` ToolFault）+ filecount 界（如 ≤512）+ 对应故障码。与 `governance_store:722-726` 的 OSError-continue 先例明确分界（该先例为 ID 扫描容错，A 为字节精确面——设计 :67 已对 `errors="replace"` 分界，同一纪律应延伸到枚举面）。

### W-A2（WARNING）方案 A/B 共用的「归档保真」前提对 legacy 腿不成立：base 文件名+`"w"` 覆写
§3.2「增量文件只装新行」与 §3.3「迁移保真」仅对 resumable 路径为真（:1000-1009 digest 冲突拒+ :135-174 never-overwrite 命名）。**legacy `_migrate_evidence_impl` 直接构造 `evidence-vX-Y.md` base 名且 `_write_archive_file` 为 `"w"` 截断写**（entity :425-437），绕过了专为防覆写设计的 `_next_evidence_archive_filename_impl`——同范围二次调用（legacy 中断后重跑=其唯一恢复方式）以新行集覆写旧档→先前归档行**非对抗性静默丢失**→a(T) 下计→偷位窗口在普通运维下即可打开；B 的 G1 实体插入点（:411→:437）不修复覆写。这把 A 的残余界从「CH-1 直改」扩大到「legacy 重跑」，比较表 §6 两案安全行均建立在该不完备前提上。修正（实现票前置，A/B 通用）：legacy EVD 腿改走 never-overwrite 命名或存在即拒/append，并把保真前提改述为「resumable+legacy 已修正」。

### W-B1（WARNING）方案 B 的 G1 门位留 resume-TOCTOU：registry 不在 pinned 世界内
插入点①在 plan（journal 写前）；可续迁 apply/resume 只按 pinned digest 判世界（:988-999 热表 digest、:1096-1098 分类上下文 digest）——**registry 状态不在 pinned 集内**：plan 过门后新增 active 条目→resume 照常 apply→active 位点被归档。落地为运行时计数守卫保守拒（fail-loud、重锚后自愈）——非逃逸，但这是门自身引入的 race，不能仅以 CH-1 泛免责。修正：G1 在 `_evidence_apply_commit` 锁内复检 registry 现值（或 §4.2 明示该 TOCTOU 与保守落地路径）。

### N-A3/N-A4（NOTE）P3 task 列匹配口径未定义
「task 列**含**当前 task」未定义包含语义：任务列可为逗号分隔多 ID（entity :347 实证）——纯子串包含=保守超集（多计→拒，且未来 FIX-445x 前缀碰撞）；等值匹配=多 ID 行漏计→a(T) 下计→偷位窗口。且 live c(T) 用 hook awk **等值**——同一行 live 计 0、归档后计 1 的口径不对称（合法归档多 ID 行→总数 N+1 假拒，保守）。修正：P3 口径=按分隔符拆分后**精确成员匹配**（无漏计、无前缀碰撞），写入 §3.2 计入行并与 live 口径对称化。当前三原行任务列为单 ID 等值（`| EVD-1536 | FIX-445 |`），不影响本次登记样例。

### N-B2（NOTE）B 的 rollback 恢复推演缺失
rollback(:1074) unlink 档+热恢复：恢复后 live 计数漂移→运行时保守拒，无静默资格回归；瞬态偷位窗口仅存在于 G1 旁路（已披露残余）之下——设计 §4.1 提及 rollback 未走此推演，比较表 B 行应补一句。

## 3. 方案核验结论（源码一手）

- **A 覆盖域**：归档落盘为 `archive/evidence/` 扁平命名（engine :1168/legacy :426-432/verify :923-928 三处一致）——P3 flat glob 与**全部真实写路径**的布局相符（我独立确认，非沿作者表）；index.md 纯派生（rebuild :1018+）不计入正确；REVIEW/TRIAGE/RECO 家族行 `| EVD-` 前缀不匹配天然排除（:263-279）；非结构化前缀排除有据（:346-358）。计入对象语义成立（唯口径 N-A3）。
- **B 入口**：evidence 恰两条真实写路径（engine resumable :1022-1170 / legacy entity :330-439）——双插入点覆盖声明**成立**；tasks 腿不涉 evidence 行（结构旁证，:608-797 未逐行读、如实）；「先失活后归档」无需跨事务的论证成立（拒绝先于任何写；两步间崩溃→计数漂移→运行时保守拒）；遗留两写非原子窗为预存在属性（:437-:438）披露不隐 ✓。
- **比较公允性**：备选 4（A/B/Alt-C/Alt-D）≥2 ✓；标准先列（§5）✓；条件推荐 Alt-C 非裁决 ✓；未证项分列（A=IO 未测/B=扩围+信任）✓。缺口：W-A2/W-B1 未入 §6 表——**呈报用户裁决前必须补**（见随附条件①）。
- **R13 前例回应**：A2/A3/A4 挑战——合法搬移总数不变 ✓；同内容独立复本计多（行级不去重）✓；事务暂态双在→总数膨胀→保守拒 ✓；S1/S2——预检臂修正后矩阵自洽 ✓；未测/未授权项未被写成已证 ✓。

## 4. 独立蓝军挑战（≥3；被挑战假设：H1=闭表已全列；H2=归档保真无条件成立；H3=门位一次即够；H4=口径天然一致）

| # | 攻击向量 | 影响 | 缓解 | 残余 | 增强 |
|---|---|---|---|---|---|
| BR1（攻击者） | 偷位前提+枚举阻断（W-A1a） | 复本获免 | CH-1 复合；诚实态保守 | 中 | 错误传播枚举+`archive-plane-enum` 故障码 |
| BR2（运维） | legacy 同范围重跑覆写档件（W-A2） | 非对抗性丢失→偷位窗口 | 无（现状缺陷） | **中-高（实现票必修）** | legacy 改 never-overwrite/存在即拒 |
| BR3（治理并发） | plan 过门后 registry 激活→resume apply（W-B1） | active 位点被归档 | 运行时计数守卫保守拒（fail-loud 自愈） | 低（落地保守） | apply 锁内复检 registry |
| BR4（维护者） | task 列口径漂移（N-A3/4） | 漏计窗口/假拒 | 单 ID 现状无害 | 低 | 分词成员匹配单源 |
| BR5（用户/成本） | 每 spawn-armed 读档面+无 filecount 界（W-A1b） | CLI36/1500 侵蚀 | Σ16MiB+逐文件释放；实测票 | 未测（设计如实） | filecount 界+实测 |

## 5. 六维与硬门槛

完整性：supersedes 映射对上 R13 基线 ✓；源码锚点经我逐段核验属实（除两处未读段如实标注）。架构：P3 消费既有遍历、B 插入点界外不入图，无环 ✓。接口：A 异常闭表有漏（W-A1）、口径未定（N-A3）；B 门位 TOCTOU（W-B1）——机制方向均 fail-closed。安全：M13 沿 R13 ✓；M15 在 A 机制下闭合至「直改+legacy 覆写（W-A2 修正前）」界、在 B 下闭合至「旁路/回执信任+G2 盲」界——设计未自授闭合（§9 未解①如实）；NOT_ESTABLISHED/迁移未授权保持 ✓。NFR：界值分列、原门不放宽、实测票强制 ✓。独立评审：同一独立 agent 第四轮、非作者。硬门槛：备选 4≥2 ✓；蓝军 5≥3 ✓；ADR 字段全（§8）✓；无环 ✓——**零阻断**。

## 6. 结论与随附条件

DEC-348 范围=比较设计+修 R13 两 W+N1+一次 R14——该范围内交付有效，**APPROVED_WITH_NOTES/unresolved_blockers=0**（设计范围通过）。**随附条件**：①呈报用户 A/B/Alt-C 裁决前，§6 比较表必须补 W-A2（A 残余界扩大）与 W-B1（B 门位 TOCTOU）两行，且 Alt-C 推荐须标注「以 W-A1/W-A2 修正为前提」——未补则裁决材料不完整；②实现票（任何方案）强制项：错误传播枚举+filecount 界（W-A1）、legacy never-overwrite 修正（W-A2）、apply 锁内 registry 复检或明示 TOCTOU（W-B1）、task 列分词成员匹配（N-A3）；③本通过≠实施/迁移/registry 授权≠产品验收：A/B 均未授权未实测，M15 在实施+实测+用户裁决前仍开放；产品 64tests/92.738s/1FAIL、CodeR6 BLOCKED/3、full 18 issues/exit1、四源门、B3、CPU27.8/CLI36/434339/32MiB/1500、隔离 witness FAIL（写者 unknown）全部保持。无风险接受、无白名单、无自动 R15；外部人类 DRI 未知如实。本报告为唯一最终文本，机录后不默改。

（本轮 read×10（含源码 6 段 5 文件一手核验），约 13 步/32 建议，无发散探索。）
