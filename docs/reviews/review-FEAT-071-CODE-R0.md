# FEAT-071 Code Review — Round 0（结构锚定派生影子流水线，0.90.0 批 2）

- **审查对象**: loop_migration.py（公开 API+NFC banner+P2-2+影子管线节+CLI --shadow-derive+P2-1 互斥）/ checks/loop_runtime_claims.py（DEC-261 预算）/ tests/test_loop_structural_derivation.py（33）/ tests/test_migration_commit_window.py（16→23）/ tests/test_verify_workflow.py（DEC-262 timeout）/ docs/verification/loop-shadow-derivation-0.90.0.md
- **审查主体**: Code Reviewer Agent（只读 Read/Grep/Glob；未复跑测试/命令——如实披露节）
- **轮次**: round 0（无前轮引用）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**
- **日期**: 2026-09-27
- **发现计数**: 0×P0 / 0×P1 / 0×P2 / 4×P3 + 1×观察（全部可遗留）

设计基准全量实读：execution-packets FEAT-071 包、DEC-254/255/258/261/262、ADR-019 §2.2/§2.6、flow-unit-approval-manifest.json 全量 212 行、REVIEW-FEAT-070-CODE-R0 + REVIEW-FIX-398-CODE-R0 原文逐条比对。

## 5 维度结论表

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | 影子管线逐分支审读：三源采集→结构宇宙→候选唯一性三态→join 归一（NFC+casefold）→对照归因矩阵（4 consistent 臂+2 DIVERGENCE 兜底臂）与报告 §3 自洽（28=2+26 互证）。P2-1 互斥、P2-2 indeterminate/None 落地正确。幂等确定性成立（grep 证实 _shadow_* 无墙钟调用） |
| 安全性 | PASS | 影子零副作用代码级核实成立：_shadow_* 全只读原语；build_migration_plan 纯函数（grep 零写原语）；模块全部写入口均不在影子调用链；无 shell/subprocess 注入面；CLI 互斥先于文件触碰 |
| 可维护性 | PASS | NFC DIGEST BOUNDARY NOTE 与 _sha_text_nfc 实现一致；_shadow_* 职责单一、docstring 锚定 ADR/DEC；公开 API 契约 docstring 完整（4 条 P3 见发现列表） |
| 性能 | PASS（记录证据） | shadow 343–400ms vs dry-run 500–612ms 同量级；basename_index 单次 O(tree)+O(1) 查找。未独立复跑——如实披露采信留痕 |
| 测试覆盖 | PASS | 33 新测试与实现分支一一映射核实（采集 4/唯一性+散文降级 4/宇宙 2/对照 6/零副作用+幂等 4/公开 API 2/P2-2 1/CLI 2+互斥 8=33 实数吻合）；复演族 16+7=23 吻合；fixture 全 tempfile 自包含 |

## 发现列表

- **P3-A**｜loop_migration.py:2377-2378（+报告 CJ-3）——`rows_without_agreement_attribution` 取 "not_comparable"，但两分支兜底均为 "DIVERGENCE"——判定面结构性恒 0（永真）。实质分歧检测效力由 DIVERGENCE 计数承载（真实存在且测试钉护）。建议补 not_comparable 归因臂或收窄 CJ-3 判定面。
- **P3-B**｜test:26 docstring——称 corrupt manifest 产生「not_comparable rows」，实际为零行（L629-631 断言正确）。建议措辞改「zero rows, never partial consumption」。
- **P3-C**｜loop_migration.py:1607 vs 1242-1245——公开 API docstring「any future reader must do the same」与模块内 dry-run reader 仍用私有名并存（P3-5 验收面满足——影子管线零私有名 import；家族内部私有名属实现细节）。建议卫生票统一或收窄表述为「外部消费方」。
- **P3-D**｜影子报告 §1.2——未明示 ①S3 裸文件名扩展名白名单（_SHADOW_BARE_FILENAME_RE：py/md/json/txt/toml/yml/yaml/cfg/ini/sh/ps1/bat/cmd）②ambiguous 命中仅记前 5。建议补精度。
- **观察（非缺陷）**——多候选 blocked 行归因 consistent_absence=「决策一致」而非「理由逐字一致」；报告 §3.2 已如实区分，§2.6 纪律两头成立。

## 硬门槛逐项

1. P0 阻塞=0 ✓ 2. 5 维度逐一结论 ✓ 3. 每条发现 P0~P3 ✓ 4. 设计一致性 ✓（执行包三审查面全执行；DEC-254/255/258/261/262+ADR §2.2/§2.6 逐项）5. AI 专项 5 项 ✓

## 专项结论

- **影子零副作用（指定面①）：PASS**——逐函数只读审读+全树 byte-snapshot 测试断言真实（rglob+SHA-256 前后恒等+manifest SHA+runtime/archive 不存在+两次运行）；报告 5 次 SHA 恒等与声称一致（未独立复算，采信留痕+机制链）。
- **对照表抽查（指定面②，8 行 ≥5）：PASS**——决定性独立复核：grep change-triage 189 文件对 adapters/chrys、adapters/opencode 零命中——2 confirmed「机证不可复现」归因证实；7 review skills/6 adapter-manifest/3 canonical surface/26 skills glob 实证；全量计数 28=2+26 自洽。
- **切换判据可操作性（指定面③）：PASS**——7 条判据机检面在 switch_judgment_inputs 全实存可机读；「不可切换」与 4 绿 3 红自洽（CJ-1 0/2、CJ-4 30/32、CJ-5 未执行如实）；人工复核点 6+回退路径 3 成文完整；CJ-3 判定面恒真（P3-A）不改结论。
- **三源与唯一性纪律：PASS**——三采集面与 §1.2 一致；裸文件名三态消歧实现+双钉护；§2.6 多候选/零命中永不锚定（双侧边界钉）；散文降级显示层代码级保证（prose 词元零候选——散文富集 host 3 units vs 结构候选 0）；A 组伪影机检兑现。
- **公开 API 契约（P3-5）：PASS**——四要素 docstring 与实现一致；恒等测试；三态行为测试；影子管线经公开名（零私有名 import——grep 证实）；P3-C 遗留观察。
- **互斥语义（P2-1）：PASS**——8 臂全覆盖（record×record/record×4 模式/5 伴随旗标）；exit 2 先于文件触碰（断言钉护 runtime 未产生）；rollback>apply precedence 未动+兼容钉；防过度阻断臂（companion with record → exit 1）在位。
- **校准纪律（DEC-261/262）：PASS**——预算注释溯源完整（实测 25,258,238B@1054/HEAD 余量 7.6KB/公式 ceil×1.2→32MiB 同族值/跨批归属逐项/M-2 复测义务/baseline-register 登记/silent-raises 继承）；timeout 溯源完整（payload +64% 跨批/p50 24×1.5=36/18s 半额恒红/budget bites）。baselines.json 登记实存。
- **补臂测试（FIX-398-R0 P2-1/P3-1/P3-2）：PASS**——四臂真 fixture（断言 skipped 理由+目录存活）；P3-1 真引用+去引用对照臂（sweep 实跑断言）；P3-2 三臂（seed 真 .tmp 精确匹配 GLOBS/真 fs 失败 no-mock/unlink 失败 fail-closed+P7 三产物原位）。

## AI 代码专项 5 项

mock 零残留（3 处全对称故障注入）/ 零硬编码返回 / 零幻觉 API（跨文件符号逐一实存）/ 零 TODO（CJ-5 为显式留痕非隐藏桩）/ 无过度实现（无权威翻转面/无双事实源）。

## 如实披露（Reviewer 局限）

未复跑任何测试/命令。执行面声称采信影子报告 §6/§7 留痕+执行包 last_run 机制+代码级一致性核对：33/33、23/23、-k loop 547/547、claims 66/66、SHA 五次恒等数值、计时、八场景/C-10 复跑、dry-run hash 一致、R7 stale 状态。对照 28 行深查 8 行，其余 20 行经 manifest 全量+结构宇宙 glob+归因矩阵代码级核对覆盖。

## Coordinator 移交事项

1. review-record 机写（Reviewer 零写）。
2. R7 sanctioned regen（DEC-262(2)）随票 commit 分离提交。
3. P3-A/B/C/D 入卫生批池（不阻塞）。

---

**Coordinator 注记（2026-09-27，非 Reviewer 文本）**：
1. Coordinator commit 前亲验：33 新测试+23 复演（快速面）。
2. P3-A/B/C/D + 观察项：入 0.91 卫生批池（与 FIX-397/F-4/F-5 残留同池）；CJ-3 判据面收窄建议随 B→A 切换授权票处理（判据框架属其域）。
