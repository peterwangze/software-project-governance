# FEAT-069 Code Review — Round 0

- **审查对象**: FEAT-069 分族授权票前置批（RB-2 两面接线 + C-10 八分支 pytest 看护 + F-2 收紧；E-6 经 DEC-257 移出）
- **审查主体**: Code Reviewer Agent（只读：Read/Grep/Glob；未执行命令/未复跑 pytest/未写文件）
- **轮次**: round 0（首次审查，无前轮报告）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**
- **日期**: 2026-09-27

通过依据：P0=0；硬门槛 5/5 全过；AI 专项 5/5；发现 N-1~N-6 全部 P3（非 BLOCKING，无遗留关闭压力，建议下次触碰对应文件时顺手处理）。实跑类声称（28/28×3 连跑、4251P/2F、check-governance 38≤47、archguard R1~R7）未复跑——以静态逐行核对+特征扫描+签名实读为限，与执行包 last_run 记录相容，git 级零修改证明留 Coordinator commit 前补齐（FEAT-068 R0 F-5 先例）。

## 一、5 维度结论表

| 维度 | 结论 | 要点 |
|---|---|---|
| 正确性 | PASS | 28 测试与实现分支一一映射成立（见四）；fail-closed 主导（runtime 不可读/顶层非对象/凭据缺失/悬空依赖/证据绑定缺失→FAIL；drift/读取失败→WARN 不混级）；branch6 None-guard 带对照臂证明非死分支；branch7 先 flatten 再 rename 规避自致悬空，测试设计正确。附 N-1/N-2（P3 文案与 docstring 边界） |
| 安全性 | PASS | F-2 动态正则经 re.escape 收敛（注入防护）；无敏感数据；异常全显式 FAIL/WARN 不隐藏；RB2_SENSITIVE_ACTION_RE 误匹配方向保守（多判敏感→更严判据，factory 下零实际拦截）；RB2_SENSITIVE_BLOCK_ENFORCED=False 出厂实证（evidence_domain.py:819），翻转属授权票域 |
| 可维护性 | PASS | RB-2 逻辑全下沉域模块（:796-1006），God Module 仅 3 处纯 compound 接线（verify_workflow.py:1142 import / :15887 Check 18d 段尾 / :24574 CLI 尾，逐处实读零逻辑下沉）；零第二验证器——契约半面经 _SHARED_NAMES 增 3 名 identity 复用 _validate_product_success_contract(:13395)，行锚中性打包（:77-82 注释自述 R7 约束）；docstring 逐条引用 ADR-019 §2.2/§2.5/§4/§6 与 B-12/B-13 先例 |
| 性能 | PASS | judge/readiness 每 CLI 单次；正则纯 alternation 无嵌套量词（无 ReDoS 面）；_resolve_shared 非缓存重取为既有披露模式（:85-96）；C-10 lazy import 仅武装态偿付（既有）。计时类声称未复跑（Read-Only），结构面无性能红旗 |
| 测试覆盖 | PASS | 28 测试全部落位：八分支×8+渲染器×2+F-2×4+E-6×3+RB-2 激活×4+judge×5+RB-2 渲染×2；正负例双向+对照臂；断言全内容判据零墙钟（RISK-048 合规，grep 无 sleep/datetime.now 断言）。fixture 真走 planner 链：build_migration_plan→confirm_decomposition→plan_to_payload（loop_migration_plan.py:372/:737/:631 签名实读匹配）；mock.patch.object 仅重定向 vw 路径常量（GOVERNANCE_DIR:167/SAMPLE_PATH:7579/EXECUTION_PACKET_PATH:168 实证存在）与翻转开关，判据函数零 mock |

## 二、发现列表（全部 P3）

- **N-1｜P3｜evidence_domain.py:998-999**: render_rb2_goal_contract_block 的 raw-BLOCK 分支静态文案「enforcement off（授权票翻转前不拦截）」在 RB2_SENSITIVE_BLOCK_ENFORCED=True 翻转态失真（与 :994 动态打印 enforcement=enforced 同屏矛盾）。factory 态行为正确、WARN-only 纪律不受影响。建议：翻转授权票 checklist 增「渲染分支按 enforcement 态分文案」。
- **N-2｜P3｜evidence_domain.py:858/869**: check_goal_layer_contract_readiness docstring 声称 "never raises; unreadable faces degrade to WARN"，但 plan-tracker 存在且非 UTF-8 时 _active_execution_packet_tasks→parse_current_active_tasks（verify_workflow.py:12627 read_text 无防护）会抛 UnicodeDecodeError。继承自既有 Check 18d 通路（check_product_success_contracts 同暴露），非本票新引入；建议卫生批精确化 docstring 或调用点防护。
- **N-3｜P3｜test_evidence_binding_drift.py:26**: docstring 的 `python -m unittest skills.software-project-governance.infra.tests....` 运行形态不可用（包段含连字符非合法标识符）；pytest 形态（:24，done_definition 采纳命令）不受影响。
- **N-4｜P3｜test_evidence_binding_drift.py:475-480**: E-6 回滚戳测试为源码文本断言（assertIn "ver=backup_version"），形态锚弱于行为断言（变量改名即红=fail-visible，可接受）；loop_migration.py:1130 已实证存在。后续触碰 loop_migration.py 时可升级为行为断言。
- **N-5｜P3｜evidence_domain.py:823-827**: RB2_SENSITIVE_ACTION_RE 误匹配面——英文词无前缀排除（pre-release/flip-chart 类命中）、中文词无词边界（「上线前检查」命中）。方向保守不 fail-open；授权票翻转时须同步审词表（precision 取舍属翻转票域）。无 ReDoS。
- **N-6｜P3（先例延续记录）**: R0-F-6 建议的 plan_rederive_failed 独立 WARN 类型未在本批采纳——读取失败仍归 unit_set_drift 类型、以 detail 前缀「计划面重派生失败」区分（evidence_domain.py:682-686，branch8 锚定该 detail）。F-6 为 P3 遗留建议非本票目标，不构成回归，记录其仍开放。

## 三、硬门槛逐项

1. P0 阻塞=0：PASS（发现全 P3）
2. 5 维度逐一结论：PASS（5/5）
3. 每条发现 P0~P3：PASS（N-1~N-6 全带级）
4. 设计一致性：PASS（见六）
5. AI 代码专项 5 项：PASS（见七）

## 四、八分支映射核对表（逐条实读）

| # | R0 F-1 分支 | 测试锚 | 实现路径（evidence_domain.py） | 断言核实 |
|---|---|---|---|---|
| 1 | not-applicable | test_branch1_not_applicable_when_runtime_absent（:213，注释锚 R0 F-1 #1） | :433-440 runtime 缺失→applicable=False 零 issue | assertFalse(applicable)+pass+fail/warn 空+runtime_path None ✓ |
| 2 | 有效 PASS | test_branch2_valid_runtime_passes_clean（:225） | 真实 planner 链 runtime 全 face 通过 | applicable+pass True、fail/warn 空 ✓ |
| 3 | 缺 MIGRATION 行 | test_branch3_missing_migration_row_fails（:239） | Face 3 :642-650 evidence_binding_missing | assertIn fail 类型 ✓ |
| 4 | 坏 hash | test_branch4_bad_plan_hash_fails（:252） | Face 1 :511-519 64hex fullmatch | assertIn+detail 含 migration_plan_hash ✓ |
| 5 | 悬空依赖 | test_branch5_dangling_dependency_fails（:269） | Face 2 :600-615 | assertIn runtime_unit_corrupt+detail「悬空依赖」✓ |
| 6 | None-guard 含对照臂 | test_branch6_gate_schema_none_guard_suppresses_drift_warn（:286） | :688 gate_schema is None 跳过；对照臂 stale 值→gate_schema_drift | 真实 payload assertNotIn gate_schema 键+对照臂 assertIn WARN（证明非死分支）✓ |
| 7 | unit_set_drift | test_branch7_unit_set_drift_warns_without_fail（:306） | :672-681 集合不等→WARN | pass True+assertIn WARN+assertNotIn FAIL ✓ |
| 8 | plan 读取失败 | test_branch8_plan_read_failure_warns（:321） | :682-686 except(OSError,UnicodeDecodeError,ValueError)→WARN | 坏字节 fixture+detail「计划面重派生失败」✓ |
| 渲染器×2 | F-1 检查+渲染器 | test_renderer_pass_shape_and_zero_count（:341）/ test_renderer_counts_fail_and_renders_warn_without_count（:352） | render :707-729 | PASS 零计数；FAIL 计数 1→2、WARN 渲染不计数、双行输出 ✓ |

## 五、DEC-257 附加点结论（stamp-agnostic 恒真复核）：PASS

- 绑定量=runtime 自身 migration_version（Face 1 :480 提取，Face 3 :618-638 用该值构造 re.escape 正则）——对任意戳恒可用（stamp-agnostic），但**非恒真化**：版本值仍是有效断言变量。三重反证：(a) F-2 测试证 version mismatch（"0.65" vs 行 0.65.0、0.65.0 vs 行 0.65.01）→ evidence_binding_missing FAIL；(b) branch3 缺行→FAIL；(c) migration_version 缺失/空→Face 1 FAIL（:505-510）。版本契约退化（段数变化/行格式破坏/戳漂移）仍被捕获，无掩盖面。
- E-6 移出核实：MIGRATION_VERSION="0.65.0" 保留（loop_migration.py:96），ver=backup_version 在（:1130），_EVIDENCE_ROW_PREFIX_RE 在（:116）且测试的 _first_cell 镜像与 _count_evidence_rows 消费形态（:257-266）逐行同构——镜像声称成立。E-6 兼容面 3 测试（stamp-agnostic 绑定/row-prefix regex/backup_version 源锚）落位。

## 六、RB-2 四象限/WARN-only/设计一致性

- 四象限全落位：缺失+敏感（factory）→ raw BLOCK+verdict WARN+enforcement warn-only（judge :945-966 三断言验证）；缺失+翻转臂→verdict BLOCK+enforced（翻转逻辑 :955-962 正确，mock 开关对模块全局生效路径成立）；缺失+非敏感→WARN；契约在+敏感→PASS。
- WARN-only 纪律：render_rb2_goal_contract_block 全部分支仅 [PASS]/[WARN]（:982/:986/:998/:1001/:1004），零 [FAIL] 路径；不接 all_issues 不计数——「check-governance 增量纯 WARN 零计数」与代码结构相容（C-10 渲染器 FAIL 计数是既有 C-10 语义非 RB-2 面）。factory=False 实证 :819。
- 设计一致性 PASS：ADR-019 §4 RB-2 两半齐备（contract_ready_units × plan_tracker_goal_face，非 TO_BE_DEFINED 判据复用真模板验证——test_precondition_rejects_placeholder_contract_host 经真实 build_execution_packet :14308-14324 全 TO_BE_DEFINED 模板）；§6 步骤 4「机制先行+出厂 WARN+翻转留授权票」忠实（B-12/B-13 先例引用）；DEC-256 恰一机械锚定哲学一致（F-2 单一定界符判据不猜语义）；执行包 scope_guard 零越界（无授权票翻转/registry 翻转/无关重构）；接载假设（Check 18d 判据族扩展零第二验证器）实证成立。

## 七、F-2 边界结论 + AI 专项 5 项

- F-2：正则 `^\|\s*MIGRATION-<re.escape(ver)>(?=\s*\||\s|$)` 对 strip 后逐行 match——前缀（0.65 vs 0.65.0）拒绝、超段（0.65.01）拒绝、恰配行中段/行尾/裸行尾绑定；红（f2 测试 1/3）绿（f2 测试 2/4）结构完整，R0 F-2 fail-open 方向闭合；re.escape 注入安全。
- AI 专项：①mock 残留：无（patch 仅路径常量+翻转开关，判据零 mock）PASS ②硬编码返回值：无（判据全数据驱动；_RB2_DEMO_* 为演示标签非返回值）PASS ③幻觉 API：无（9 个跨模块符号逐一实读核实存在且签名匹配）PASS ④未实现 TODO：无（两文件 grep 零命中）PASS ⑤过度实现：无（域段 189 行承载两 face+judge+renderer+常量，与包 scope_guard 一致；无越界面）PASS

## 八、零修改核实（loop_migration.py / test_loop_migration.py）

特征扫描：loop_migration.py 零 FEAT-069/RB2 特征、戳保留 0.65.0、ver=backup_version 与 _EVIDENCE_ROW_PREFIX_RE 在位（与 HEAD 语义一致）；test_loop_migration.py 零 FEAT-069/RB2/evidence_binding_drift 特征。git 级证明超 Read-Only 边界，留 Coordinator commit 前 `git diff --stat` 补齐。

---

**Coordinator 注记（2026-09-27，非 Reviewer 文本）**：
1. git 级零修改证明与定向测试复跑由 Coordinator 于 commit 前补齐（见 EVD 终态行）。
2. N-1/N-5 处置：登记入 B-12/B-13 翻转授权票 checklist 素材（渲染分文案 + 敏感词表审查——DEC-255 红线「翻转留授权票」的配套项）；N-2/N-3/N-4/N-6 留卫生批顺手项（与 FIX-397 残留同池）。
