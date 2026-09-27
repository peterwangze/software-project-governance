# FEAT-070 Code Review — Round 0

- **审查对象**: FEAT-070 E-1-B unit 权威清单人工确认路径（loop_migration.py manifest 段+preview 接线+CLI 旗标族；tests/test_loop_unit_manifest.py 25 测试；.governance/flow-unit-approval-manifest.json revision 28）
- **审查主体**: Code Reviewer Agent（只读：Read/Grep/Glob；未复跑测试/未重算 digest——如实披露见声明节）
- **轮次**: round 0（无前轮引用）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**
- **日期**: 2026-09-27

## 审查结论

无 P0/P1；2×P2 建议 + 5×P3 讨论，均可遗留不阻塞。设计基准实读：ADR-019 §2.2/§2.6、DEC-254/DEC-258、execution-packets FEAT-070 包（done_definition 审查面：清单抽查 ≥5 ✓ + 统一存储声明核对 ✓）。

## 5 维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | fail-closed 边界全覆盖（缺/坏清单/未知 unit/冲突映射/重复/confirmed-block 互斥）；原子写 mkstemp+fsync+os.replace+失败清理（L538-553）；写后回读全量校验（L934-938）。注：并发 record 无文件锁（后写覆盖、revision 仅+1），依赖流程层锁纪律——与 flow-unit-runtime 同族先例一致，P3-7 |
| 安全性 | PASS | 损坏清单 reader 侧 data=None 永不部分消费（L879-895）+ writer 侧拒写不覆盖（L1023-1029/L1142-1148）；RISK-040 根解析 fail-closed；无 shell 解释面；无硬编码凭据 |
| 可维护性 | PASS | 命名清晰；banner 存储声明（L663-698）load-bearing 且与 docstring（L40-55）一致；_validate_approval_manifest_data ~135 行平铺校验链可接受 |
| 性能 | PASS | 单 record=一次候选派生+一次清单 I/O（声称 169-211ms 与机制吻合）；digest 重算线性；dry-run 无清单遍历热点 |
| 测试覆盖 | PASS | 25/25 与实现分支一一对应（6 approval+3 block+6 corruption+7 preview+3 CLI）；fixture 全 tempfile 自包含；断言零墙钟 |

## 发现列表

- **P2-1** loop_migration.py:L2033-2043+L1990-2004 — CLI 旗标组合互斥缺失：--record-unit-approval 与 --record-unit-block 同给时静默走 approval 分支；record 与 --apply 同给时 apply 优先、record 意图被静默忽略（与既有 flag 族 rollback>apply>preview 语义一致，非本票回归）。建议：record 族入 mutually exclusive group + 与 --apply/--rollback 互斥校验。
- **P2-2** loop_migration.py:L1241-1249 — manifest valid + plan 派生失败分支：face status="consumed" 且 ambiguity_count=0，但实际未做 per-unit 比较；消费方若只读 unit_manifest_ambiguity_count 会得到误导性 0（缓解：face.issues 有 skipped 说明 + preview.plan_derivation_error）。建议 status 改 "indeterminate" 或 ambiguity_count=None。
- **P3-3** decision-log L200（非本票文件）— DEC-258 文本「A 组 17 项/B 组 5 项」与同句枚举（A=19、B=6）不一致；清单 26 条留痕与枚举逐一对应无误，纯裁决文本计数笔误，建议勘误。〔Coordinator 处置：DEC-259 勘误已入账〕
- **P3-4** L706-731 — NFC 归一化使 NFC 等价的字节级篡改不触发 digest mismatch（跨平台同语义一致性换来的边界）；威胁模型=意外修改检出非对抗防篡改，可接受，建议 banner 注明。
- **P3-5** L871 — FEAT-071 影子消费入口现为私有名 _load_approval_manifest/_validate_approval_manifest_data；建议 FEAT-071 立项时提供公开稳定 API 或在 docstring 声明消费契约入口。
- **P3-6** L1926 — 既有代码 except (ValueError, Exception) 冗余过宽（FEAT-003 面非本票引入）；记录供后续清理票。
- **P3-7** record 链路无文件锁 — 并发 record 竞态靠流程层 agent-locks 纪律；同族数据面既有先例一致，无需本轮修改。

## 硬门槛逐项

1. P0 阻塞=0 ✓ 2. 5 维度逐一有结论 ✓ 3. 每条发现 P0~P3 标注 ✓（0P0/0P1/2P2/5P3）4. 设计一致性已完成 ✓ 5. AI 专项 5 项全部完成 ✓

## 设计一致性（ADR §2.6 + DEC-254/258）

PASS——§2.6「错误锚定比缺失更危险」机器化：unknown unit 拒确认（L1013-1020）、confirmed 不可经 block 静默翻转（L1154-1159）、冲突映射须显式裁决（L1037-1044）、消费面 missing/blocked 全上报不猜测。DEC-254：四元信息/版本化/阻塞不赶进度/B 先手形态 ✓。DEC-258：26 阻塞逐条留痕、gitignored .governance/（.gitignore L10 实证）、清单回滚=链路级（apply/rollback 零清单触碰与之互证）、确认 2 项证据可解释 ✓。

## 清单抽查记录（7 项抽查 + 全量计数核对）

全量实读 manifest（212 行）：revision=28 ✓；entries=2 + blocked=26 = 28 ✓；顶层字段 9/9 齐；blocked 26 条每条 reason+repo_version+recorded_by+recorded_at 全非空 ✓。抽查：

1. entry adapter.Chrys（L11-17）四元齐；证据断言「6 adapter 目录中唯一匹配 Chrys + 含 adapter-manifest/launch.py/README」→ glob 实证 adapters/ 恰 6 目录（chrys/claude/codex/dsh/gemini/opencode）且 chrys/ 含三文件 ✓
2. entry adapter.opencode（L19-25）四元齐；adapters/opencode/adapter-manifest.json 实存 ✓
3. blocked skill.review（L113-118）「7 个 review skill」→ glob skills/*-review 恰 7 个 ✓
4. blocked manifest.adapter（L204-209）「6 个 adapter-manifest.json」→ glob 恰 6 个 ✓
5. blocked manifest.canonical（L155-160）三候选面 core/manifest.json + .claude-plugin/plugin.json + marketplace.json 全部实存 ✓
6. blocked skill.Same-Package（L92-97）与 DEC-258(3) 永不确认裁决一致 ✓
7. blocked adapter.loading（L29-34）A 组散文伪影代表，候选面枚举+§2.6 no-guess ✓

digest 结构 64-hex 合法；数值一致性以机制链承载（写后回读校验 + 隔离副本 dry-run consumed——若 digest 失配加载即 corrupt），Reviewer 未独立重算 SHA-256（Bash 禁，如实披露）。

## 直写检出与单源结论

PASS——单源写入器：_write_approval_manifest 全文件仅 record_unit_approval(L1065)/record_unit_block(L1175) 两处调用 ✓。直写检出真实非纸面：test_out_of_chain_edit_detected_via_digest + digest-maintained 手写违例三连测 + test_corrupt_manifest_blocks_further_writes ✓。

## apply/rollback 零改动核实

PASS（特征扫描+行锚）——FEAT-070 特征行仅 docstring(L40-55)/常量(L121-148)/manifest 段(L663-1309)/preview 接线(L1929-1937)/CLI(L1983-2081)；apply 段(L1317-1658) 与 rollback 段(L1665-1856) 行域零清单引用；plan_hash 计算域（loop_migration_plan.py L336-339）不含清单，该文件无 approval 特征 ✓；legacy 兼容由 test_preview_legacy_shape_preserved 断言；退出码语义未变 ✓。

## 统一存储声明结论

PASS——banner+docstring 成文：清单=确认侧权威、runtime=派生面、FEAT-071 MUST 消费同一结构；结构自描述性充分（schema_version+manifest_id+条目自含+可独立重算 digest；未知 schema fail-closed）——足以支撑影子侧消费（P3-5 入口私有名遗留）。

## AI 代码专项 5 项

零 mock 残留（测试无 mock/patch，subprocess 真跑 CLI、fixture 真盘）/ 零硬编码返回值 / 零幻觉 API（跨模块符号 grep 行锚实存）/ 零 TODO / 无过度实现。

## 声明（如实披露）

测试执行结果（25/25、族回归 56/56、相邻 92/92、链路 28 CLI exit 0、副本三面绿）未由 Reviewer 独立复跑（只读约束禁 Bash），以 EVD-1199 结构化事实+执行包 last_run PASS+代码级一致性核对承载；digest 数值一致性以写后回读+副本 dry-run consumed 机制链承载，未独立重算 SHA-256。

---

**Coordinator 注记（2026-09-27，非 Reviewer 文本）**：
1. P3-3 处置：DEC-259 勘误（A 组实为 19 项/B 组 6 项+Same-Package 1 项=26；分组语义与清单留痕不变）。
2. P2-1/P2-2 处置：登记 FEAT-071 立项前置小修面（旗标互斥组 + indeterminate 语义——影子票首步顺手项）；P3-4/P3-5 一并随 FEAT-071（banner 注明+公开消费 API）；P3-6/P3-7 入卫生批池。
3. Coordinator commit 前亲验：定向 25 测试 + -k loop_migration 族回归。
