# FIX-445 — Independent Design Review R15（DEC-349 保护设计复审）

```json
{"verdict":"APPROVED_WITH_NOTES","round":15,"unresolved_blockers":0,"review_scope":"archive_protection_per_dec349_static","implementation_authorized":false}
```

## 0. 绑定、独立性与输入

- **审查对象**：`docs/design/FIX-445-archive-protection-R15.md`（156 行全文实读，producer 已停写）。SHA `32aad8d1…`/blob `0beb19a2…` 系派发+authorization.json 双源一致；未独立重测 hash（零 shell，如实）。
- **审查方**：DesignReviewerR15 = R11–R14 同一独立 Reviewer（authorization.json:13），非作者（`243d70ac…`）。人类外部成员/DRI 未知，不发明。
- **本轮实读 4 件**：R15 设计 156 行；`FIX-445-R15-authorization.json` 53 行（DEC-349、`protection_design_boundary`、禁白名单清单、零 R16）；`FIX-445-R14-closeout-and-scope.md` 68 行（呈报补充表已按 R14 随附条件①原样纳入 W-A2/W-B1——当场履行核验 ✓）；R14 报告 64 行（沿上轮转录 readback 原文，逐字在案）。**源码补证一手**：`archive_migration_engine.py:205-334`——`_atomic_write_text`(:217-243) 委托 `governance_store._atomic_write_bytes`（temp+fsync+**os.replace**，fallback mkstemp+replace；**无 O_EXCL 排他语义**）；`_big_table_target_lock`(:245-253) 委托 `_TargetLock` 且存在 `_TargetLock is None` 时 **no-op 降级分支**；`_migration_load_journal`(:298-320) 坏件/异 schema 即拒 ✓；`_migration_state_dir`(:274-281) 仅 .json 不入索引视野 ✓——设计 §1 补证声明逐项属实。零 shell/执行/写/子 agent/用户交互；未读热面。
- **沿同 agent 上下文**：角色/双 SKILL、canonical 两产品、R10–R14 全链设计与报告、R0/R3/R5、R9 两件、DEC336 helper、R4-escalation、CODE-R6、历次 context/check/authorization 工件、R14 轮源码 6 段（engine :85-209/:981-1170、entity :330-454、indexing :200-359、governance_store :715-834、archive.py :895-1024）。

## 1. R14 三 W + 两 NOTE 逐项裁决

| 项 | 独立核验 | 裁决 |
|---|---|---|
| **W-A1** 枚举/资源闭表 | §2 闭表 v2：scandir+errno 错误传播（禁 glob 容错）✓、filecount≤512（明标设计界非实测，不据此称 CLI36/1500 已保证）✓、单文件/单行/Σbytes/Σlines/monotonic 时间界 ✓、双相 names+sizes 稳定性 ✓、pin≠hash 授格逐字分清（V10 红测断言授格路径不存在）✓。**残留一处一致性缺口 → W-R15-1（下）** | **已修（附新残留 W）** |
| **W-A2** legacy 覆写 | §3 单一策略全锚真实 helper：命名经既有 `host["_next_evidence_archive_filename"]`（:167-174→:135-165，我 R14 已读段独立印证）+ EEXIST→digest 等=幂等/异=`archive_target_conflict` 拒且**旧字节保留**（沿 :1000-1009）✓；「重试新档（非幂等，需对账）」与「并发同目标（EEXIST 判定）」两可达分支分开且正确（:135-165 生成器行为我独立核过：重试必得新名）✓；前提改述为条件化（legacy 修正实施前不作保真前提，呈报表同步）✓；rebuild 不复原行数据 ✓；最小未授权写面+四情形测试落点（test_archive.py 实存经 glob）✓ | **已修（规范级；实施+测试未授权如实）** |
| **W-B1** resume-TOCTOU | §4 apply 锁内末检：`_big_table_target_lock(elog)`（:245-253，与 apply :987 同锁——我本轮一手核证）+ 热表 digest 复核后、任何写前 + registry revision R1/R2 重读与活跃集重匹配（缺席=放行/坏件=拒/R2≠R1=现值重匹配）✓；双保险分层如实（末检主径+运行时守卫兜底，两终点 fail-loud——我独立推演：末检窗口内激活经 B-only 的 live 计数降 N-1 或 A 的联合计数均保守拒，无假授路径）✓；registry 写者协同=纪律辅径明示不依赖 ✓ | **已修（附措辞 NOTE N-R15-5）** |
| **N-A3/A4** task 口径 | §5 `task_member`：闭分隔符拆分→token 集→精确成员；前缀碰撞免疫表 ✓；坏 token+三元组行=保守计入+诊断 ✓；live 侧统一属实现票、期间不对称方向=假拒 ✓——**我独立补深一层推导**：live 多 ID 行对 hook awk 不可见 ⇒ 其出现根本不进引擎候选集 ⇒ 无论计数如何均**不可能获豁免**——假授路径在结构上不存在（比设计所述「方向保守」更强）；假拒全称性（登记 N 含多 ID live 出现时永拒）亦确认。四源提取零改动 ✓ | **已修** |
| **N-B2** rollback 推演 | §4.2/§6：rollback 不经 G1（管写不管恢复）✓；恢复世界与「从未归档」局部同构、(1,0,1)==N 机制放行 ✓；recount 回执=审计义务与机制分开 ✓；B-only 瞬态窗口仍属已披露残余（G1 旁路/回执信任）不新增 ✓ | **已修** |

## 2. Findings（本轮新发现，均非阻断）

### W-R15-1（WARNING）闭表 v2 残留：ENOTDIR 并入 absent + 非常规文件条目未规定
**(a)** §2.1 步 1 把 ENOTDIR 与 ENOENT 同并 `APLANE=absent`——但 ENOTDIR 意为路径组件非目录（如 `evidence` 被置为普通文件）：这是「在场畸形」而非「缺席」，处理却比面内子目录（unexpected-dir 拒）**更温和**（静默归零）——纪律不自洽；偷位前提+CH-1 置换下为 fail-open 组合，违反 §2.1 自身「禁容错语义」的完备声明。**(b)** 步 2「仅收 *.md」未限定**常规文件**：面内 symlink 指向仓内文件（如 evidence-log.md）时 realpath 仓内不逃逸→被当档件读入→live 行被 archive 面双计→总数爆膨假拒（保守 DoS，非假授）。修正（实现票前置）：ENOTDIR→`archive-plane-unexpected-dir` 族拒（仅 ENOENT=absent）；枚举条目 `is_file(follow_symlinks=False)` 限定常规文件，symlink 条目一律拒。方向：两处均 CH-1 主导/保守向，但闭表全称声明需补齐才算闭合。
### N-R15-2（NOTE）时间界=事后检查点非抢占界
`time.monotonic` 每文件检查点只能**检测**超时（检测延迟≤单文件扫描时长），不构成硬中断界——§2.2「≤5s/spawn」应明示为「检测界」；单文件扫描受 2MiB/1MiB 行界约束，最坏 overrun 有界。设计已标「检查点」半诚实，补一句即可。
### N-R15-3（NOTE）O_EXCL 与 `_atomic_write_text` 组合张力需拆句
我本轮核证 `_atomic_write_text` 为 temp+**os.replace**（:217-243）——**无排他**；「O_EXCL 独占原子创建」与「经 _atomic_write_text durability」并列内部紧张。两分支后果我独立推演均保守：(i) 直接 O_EXCL 终名——partial-crash 留截断档，热表全量在 ⇒ 过计 ⇒ 拒；(ii) temp+replace——创建非独占，由 never-overwrite 唯一命名+EEXIST 判定补偿。fork 留实现票+V5 钉死可接受，但 §3.2 措辞应拆明两分支各自接受什么、放弃什么。
### N-R15-4（NOTE）「三处共用此一源」跨边界字面不可行
commit-msg 内嵌 python 与 infra G1 无法共享同一函数字面源——实现为**受控双副本+等价钉死测试**（FEAT-076 双 regex 漂移教训），规范应言明防「单源」误读。
### N-R15-5（NOTE）两处措辞防误读
①「registry 状态由此进入 pinned 世界」——R1/R2 pin=journal 审计记录，**非写者互斥**（末检窗口由运行时守卫保守兜底，设计已列但措辞易被读成互斥）；②`_big_table_target_lock` 在 `_TargetLock is None` 时为 **no-op 降级**（:249-253 我本轮核证）——末检的「锁内」以治理店可导入为前提，实现票应加导入失败=拒的降级语义。

## 3. 独立蓝军挑战（≥3；被挑战假设：H1=闭表 v2 已完备；H2=原子性与排他可兼得；H3=pin 即互斥；H4=口径统一即字面单源）

| # | 攻击向量 | 影响 | 缓解 | 残余 | 增强 |
|---|---|---|---|---|---|
| BR1（攻击者） | `evidence` 置换为文件/面内 symlink（W-R15-1） | 归零偷位/双计 DoS | CH-1 主导；symlink 向保守 | 中 | ENOTDIR 拒+常规文件限定 |
| BR2（运维） | legacy 修正后中断重试 | 双在→全拒 | never-overwrite 新档+对账（未授权） | 可用性（安全向） | 对账程序随实现票裁决 |
| BR3（治理并发） | 末检后窗口 registry 激活 | active 位点被归档 | 运行时守卫保守拒（A/B 两案均有） | 低（无假授） | N-R15-5 措辞+导入失败降级 |
| BR4（维护者） | 双副本谓词漂移（N-R15-4） | 口径分叉 | 等价钉死测试（实现票） | 低 | 落点明示 |
| BR5（用户） | 界值过紧误拒正常档库 | availability | 设计界可调+实测票 | 未测（如实） | 实测校准 |

## 4. 六维与硬门槛

完整性：supersedes 映射对上 R14 基线 ✓；§1 补证经我一手核证属实。架构：P3/末检/谓词均消费既有遍历或锁，无新环 ✓。接口：闭表 v2 有 W-R15-1 残口；O_EXCL 组合 fork 两分支均保守。安全：M13/M15 推演表（§6）逐行独立复核成立；多 ID 假授结构不可能性我独立补证；pin/授格分清 ✓；NOT_ESTABLISHED/迁移未授权保持 ✓。NFR：全部界值明标设计界未实测 ✓；原门不放宽 ✓。独立评审：同一独立 agent 第五轮、非作者。硬门槛：备选 4≥2（Alt-A′/B′/C′/D，标准先列）✓；蓝军 5≥3 ✓；ADR 字段全（§9）✓；无环 ✓——**零阻断**。

## 5. 结论与随附条件

DEC-349 范围=一次修齐 R14 三 W+两 NOTE+口径/回滚推演——该范围内交付有效，**APPROVED_WITH_NOTES/unresolved_blockers=0**（保护规范级通过）。**随附条件**：①实现票（任何方案）前置必含：W-R15-1 两修正（ENOTDIR 拒+常规文件限定）、N-R15-3 两分支拆句与 V5 扩断言、N-R15-4 双副本等价测试、N-R15-5 两处措辞与锁降级语义；②全部写面（A 两产品/B·保全面 infra 三件+test_archive.py）维持未授权提案，Alt-C′ 推荐仍以修正实施为前提；③本通过≠实施/迁移/registry 授权≠产品验收——M15 仍待用户架构裁决，原源 NOT_ESTABLISHED 保持；产品 64tests/92.738s/1FAIL、CodeR6 BLOCKED/3、full 18 issues/exit1、四源门、GuardG/T2/M5/R3、12 攻击逐例、B3、CPU27.8/CLI36/434339/32MiB/1500、隔离 witness FAIL（写者 unknown）全部不改绿。无风险接受、无白名单、无自动 R16；外部人类 DRI 未知如实。本报告为唯一最终文本，机录后不默改。

（本轮 read×4（含 engine 补证 :205-334 一手），约 7 步/32 建议，无发散探索。）
