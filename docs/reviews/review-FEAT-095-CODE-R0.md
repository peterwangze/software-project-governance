```json
{"verdict":"APPROVED_WITH_NOTES","round":0,"unresolved_blockers":0,"review_scope":"feat095_enforcement_protocol_cli_face","parent_full_product_complete":false}
```

# FEAT-095 动作级执法——独立代码审查报告 R0（Code Reviewer）

审查人：Code Reviewer Agent（角色：agents/code-reviewer.md；规范：skills/code-review/SKILL.md）。只读审查：全程仅 Read/Grep/Glob，未 Write/Edit、未执行命令、未起子 agent、未 AskUserQuestion。

## 1. 绑定与独立性声明

- **内容级绑定完成**：六 file 全部完整读取——enforcement.py（724 行全文）、verify_workflow.py 四接线簇全文、test_verify_workflow.py 追加类全文（26867-27261）、SKILL.md 协议段全文（232-262）+ 首尾比对、调研报告 §5-§10 全文、投影 SKILL.md 锚点/行号/尾部比对。
- **SHA256/git blob 未独立重算**：本 Reviewer 被禁止执行命令，无法跑哈希——绑定核验降级为内容级 + 交叉证据：①投影与源在 6 个执法锚点（行 239/241/243/258/260/262）逐字一致且同行号；②两文件同为 523 行、尾部 514-523 逐字一致；③validation log 第 8 行 release-projection --write PASS（28b drift 闭合）。**哈希绑定标记为「未独立验证（工具约束），内容级一致成立」**。
- **继承 dirty 基线下的「四处纯增量」核验**：git diff 不可行（前序票未提交修改混在工作树）。替代三角核验：①全文件 grep "enforcement" 22 处命中，除四接线簇（import 137-138 / 薄入口 25693-25696 / 注册 28038-28046 / dispatch 28177）外，其余命中（L126 FEAT-097 注释、L16531 deadline、L17793 intake、L24570 archguard 注释、L27686 DEC-286 注释、L28015 FEAT-096 help）均为前序票既有内容且语义无关；②全套件 1135 测试仅 3F+1E（全部前序测试类），既有面被改写大概率破坏其他测试——未发生；③开发者声明 + validation log 一致。结论：薄接线声明成立（RISK-039 纪律符合：入口仅注入 governance_dir/repo_root 后纯转发，零逻辑复制）。**残留不确定性如实声明：无法排除与前序票同文件内语义无关的微改**。
- **独立性**：本审查与开发不同会话、无共享上下文；所有结论仅基于上表文件 + 执行包 + validation log + sandbox 工件 + decision-log（DEC-330/353/354/355/356 已读原文）。

## 2. 验收①-⑤逐项裁决

**验收① 六边界×三层 + 表/执行器分离 —— 通过**。BOUNDARIES 六项与任务行逐一对应（enforcement.py:86-93）；四类硬阻断表序求值首命中即断（294-306）；审查债 Σ clamp(sev,1,5)×clamp(age,0,30) 阈 100，仅 dispatch-execute/goal-resume 两个 admission 面（174/190/308-324）——比声明的 min(sev,5)×min(age,30) 更严（下限钳制抗负值），良性；冷面 7 天仅提示（191/326-338/429-445）。四谓词闭环核验：修订错配=action.revision(int) vs state.expected_revision[task_id]（350-371）；未授权写入=action.write_paths vs authorized_writers[actor] 的 fnmatch 模式集，actor 缺席即全拒（373-395）；重复身份=actor ∈ active_identities（397-408）；阻塞复审未闭合=unresolved_reviews 中 blocking=True 且 closed≠True 且 task_id 匹配（410-424）。表/执行器分离由 test_enforcement_new_boundary_via_table_only_executor_untouched（27214-27232）真证：deepcopy 加边界 → decide 生效；默认表拒未知边界 fail-closed——加边界确是表数据操作，非静默接受。

**验收② exit 3 + 白名单三通道不冻 + 无关任务不冻 —— 部分通过（见 P1-1）**。exit 3 review-debt-budget-exceeded 代码+测试双证（314-324；27035-27055，含 goal-resume 面）。白名单结构不可滥用：allowlist_exempt 是规则级数据位，仅 unresolved-blocking-review 为 True（166）；fix/re-review/forensics 通道不豁免修订错配/未授权写入/重复身份（137/147/156 均 False）——「修订错配的 re-review 派发仍被拒」在 26960-26974 双变体实测，结构上白名单无法降级其余三类硬阻断 ✓。但「无关任务不冻」仅在弱口径成立：债务是全账本聚合计（review_obligations 无 task 归属字段），他票债务超阈时**无关任务的 dispatch-execute/goal-resume 会被限流**——测试只验证了 accept-completion 无限流面（27057-27063）。详见 P1-1。

**验收③ exit 4 STALE_NOTICE 非阻断 —— 通过**。exit 4 语义在代码（111-114/326-338）、测试（27081-27088：gate=9>7 → 仅提示、动作放行）、SKILL（258「动作仍放行」/262「重建展示面后继续」）三面一致。措辞瑕疵见 P3-3。

**验收④ 协议级+CLI 级降级披露 —— 通过（预授权降级且披露如实，未发现宿主级伪装）**。调研 §5 矩阵宿主级全列「未证实/原生原语未接线」、§7 U1-U7 逐项给验证方法、§229 降级声明按执行包 L1513 原文；§10 明确记录：own.host_row 未改、无 guard 注册、manifest 未新增 enforcement 能力键、U1 PoC 未做、「不调用即绕过」绕过面维持披露。enforcement.py docstring 35-39、CLI help（28040-28044）、SKILL 243 三处均明示「不做宿主级拦截能力声明」。六 file 内未发现任何宿主级能力断言——**降级披露不实即阻断的红线未触发**。

**验收⑤ 故障注入 —— 通过**。损坏 facts（子进程、HOME/USERPROFILE/DSH_HOME/TEMP/TMP 全重定向至 in-repo sandbox——符合真实环境防护三选一(a)）→ exit 2 + 记录（27107-27138）；类型故障（expected_revision 值为 mapping）→ fail-closed（27092-27100）；未知边界 → fail-closed（27001-27105）；记录写失败（record-dir 是普通文件）→ 判定照常返回 + record_error 披露不炸（27140-27151 + _emit 589-592）；4×6 零漏放矩阵 24 组合逐组断言 decision+reason_code（27006-27027，library 直调，merge 行 wip=False 不触豁免）；白名单不豁免修订错配（26967-26974 对抗变体）。

## 3. 铁边界核验

1. **scoped 非全局**：通道维 ✓（数据位豁免仅一条规则 + 限流跳白名单，代码结构保证）；任务维 ✗（债预算全局聚合）——见 P1-1。
2. **WIP carve-out 真在 merge 边界前放行**：✓ 且不只是豁免 commit 字面——carve-out 在硬阻断层之前求值（279-288 先于 294），测试堆叠修订错配+重复身份+未闭合阻塞复审四违规仍 ALLOW + reason_code=wip-checkpoint-carve-out（27067-27077）；且仅 boundary==wip_carve_out_boundary（表数据 "merge"）生效，其他边界 wip_checkpoint=True 不触发豁免（矩阵测试间接覆盖）。注意 wip_checkpoint 是调用方自证字段——属已披露的自组装 facts 降级形态，SKILL:262 已立「禁止 --facts 造假」协议补位。
3. **不改 Check 判定语义**：✓ enforcement.py 零调用任何治理检查函数，只消费 facts 投影（docstring 28-29 + 代码事实一致）。
4. **GOVERNANCE_ENFORCEMENT=off 零漂移**：✓ CLI 面 off 分支不读 facts、不判定、不落记录、exit 0（639-659）；测试断言 record dir 为空（27155-27167）——是「决策路径旁路」而非空转。非法值不猜 → 保守阻断 + 披露（616-636；27169-27177）。注：开关仅在 CLI 面生效，decide() 库路径不查开关（模块即执法本体，设计自洽，P3 级备注）。

**fail-closed 真实性**：decide() 以 except Exception 包裹 _decide 全部路径（238-256），无静默 except——异常转为保守 HARD_BLOCK + 类型名披露；_safe_* 的宽 except 仅用于决定已作出后的 payload 提取，不在判定路径；无 bare except/pass。策略表损坏（KeyError/TypeError 于 table 访问）落入同一包装——结构覆盖成立（直接测试缺，P3-4）。

## 4. 测试有效性 + AI 专项 5 项

**20 用例清点**（逐一数名）：4 硬阻断单类 + 4×6 矩阵 + 债限流 + 白名单/goal-resume + scoped + WIP + 冷面 + fail-closed×2 + 记录失败 + off 零漂移 + 非法开关 + 可 grep/报错含解除路径 + print-strategy + 表驱动 + 性能守护 + SKILL 协议面锚点 = 20 ✓，与 log 第 4/6/15 行 "Ran 20 tests" 三跑一致。无恒真/同义反复：断言含 rc+decision+reason_code+payload 字段+记录行数与内容。TDD 红（log L2 exit5→L3 import error，即 ModuleNotFoundError 形态）→绿（L4-L6 三迭代）轨迹与声明一致。

**TEMP 伪影解释（边缘发现 a）——成立，有直接证据**：run1（full-suite-run.log，7F）比 run2（full-suite-run2.log，3F+1E）多的 3 个失败中：①ReviewFallbackPolicy 失败 diff 明文出现 `.governance/incidents/FEAT-095-sandbox/tmp/tmplf6wfl4w/...` 路径；②FIX300 两失败明文 `ROOT_SOURCE_AMBIGUOUS: snapshot must be outside every scanned root`——TEMP 指进仓库导致快照落入扫描根内，恰是这些测试自身不变量要求的环境形态。run2（TEMP 系统默认，HOME 等仍沙箱）= 3F+1E，四个失败全在前序类（FEAT075×1/FIX300×2/LoopRuntime×1），与 M-2 既知基线一致，enforcement 类零失败。结论：**3F+1E 是真基线，run1 超额失败是测试环境形态问题而非本票退化**；但 run1 未入 17 行 validation log（P3-5）。

**性能**：log L13 `AVG_DECIDE_SECONDS=0.00000586 avg_us=5.86 calls=1500` 与 5.86µs 声明逐字一致；probe 覆盖三条最重路径（错配/放行/债务）×500（perf_probe.py 33-43 与 L13 输出吻合；L12 内联版 NameError 后以脚本重跑，log 如实留痕）。套件内另有 ≤10ms 墙钟守护（27236-27248）。**门禁复跑（check-governance 21/arch-health/manifest）本 Reviewer 无命令权限，按 log exit code 采信，未独立重算**——manifest glob 覆盖已独立核实：core/manifest.json:68 `infra/**/*.py` 模式覆盖 enforcement.py，无需逐文件登记（与 goal_bridge 同模式），consistency PASS 语义有效。

**AI 专项**：①mock 残留——无（生产代码零 mock；测试 mock.patch.dict 为合法环境注入）✓；②硬编码返回值——无（阈值为声明的策略表数据，非伪计算）✓；③幻觉 API——无（纯 stdlib，全部真实；但 tempfile 为未用 import，P3-1）✓；④未实现 TODO——无 ✓；⑤过度实现——build_parser/main 独立面与 goal_bridge 同构，非过度；单子命令 subparser 形态略奇（P3 级）✓。

## 5. 发现清单（P0=0 / P1=1 / P2=1 / P3=6）

- **P1-1 scoped 承诺与全局债预算的语义差**｜enforcement.py:24-25（「无关任务不受他票审查债影响（DEC-330 发布验证底线）」）、SKILL.md:260①（同口径无限定）、test_verify_workflow.py:27057-27060（测试名/注释声称 "unrelated tasks not frozen by another task's review debt"，实际仅验证 accept-completion 无限流面）。影响：代码事实上对无关任务的 dispatch-execute/goal-resume 施加全局聚合限流（他票义务 Σ>100 即 exit 3）；文档/注释承诺强于实现，DEC-330/DEC-353 发布验证底线「无关任务不被全局冻结」在 REL-102 M-7/M-8 故障注入时按字面探针（无关任务派发执行 under 他票债）会命中 exit 3——发布链末端的可预见失败，且当前无任何落盘裁决钉住「限流≠冻结」的解释。修法（廉价、纯措辞+裁定，不动行为）：①三处措辞收窄为「硬阻断与未闭合复审按任务/通道 scoped；审查债预算是**全局新工作准入限流**，白名单通道与用户裁定额度逃生门保留」；②测试名/注释改为陈述其实际验证面（非 admission 边界无限流面）；③在 REL-102 M-7 前落一条 DEC 钉住 DEC-330 底线的解释口径（或给债预算加 task 域过滤，二选一，推荐前者+裁定）。
- **P2-1 facts 缺席字段静默跳过**｜enforcement.py:350-352（action.revision 缺席 → 修订错配检查静默不适用）、437-439（冷面缺席 → 永不 stale）。SKILL:262 要求组装「修订号」但模块不强制在场：诚实但马虎的调用方漏装修订号即无信号跳过最强硬阻断；冷面为提示层、宽松可接受。修法：expected_revision 含该 task 而 action 缺 revision 时按 fail-closed 拒绝（或至少在 SKILL facts 契约中显式声明「缺席=不适用」的前置条件）。
- **P3-1** 未用 import tempfile（enforcement.py:57）——删除。
- **P3-2** argparse 用法错误出口码=2 与 HARD_BLOCK 码碰撞（enforcement.py:706-720）——方向保守（错当阻断），建议注释声明或区分。
- **P3-3** SKILL:239 概括行「非 0 即 MUST 停下…重试」未内联 exit 4 例外（262 已澄清）——快速阅读者可能把提示态当阻断；建议行内加「（exit 4 提示态除外：重建后继续）」。
- **P3-4** 损坏策略表/未知规则 id 的 fail-closed 路径无直接测试（结构上被 catch-all 覆盖）——补一条传入损坏 strategy 的用例。
- **P3-5** run1（7F）全量跑未记入 validation log，两环境故事需靠 sandbox 工件重建——流程透明度瑕疵，无实质影响。
- **P3-6** unauthorized-write 的 fnmatch 正斜杠约定未写入 facts 契约：Windows 反斜杠路径对正斜杠模式全不匹配 → 授权写入被误拒（fail-closed 方向，非漏洞但是可用性陷阱）——在 SKILL:262 契约中约定路径分隔符。

## 6. 五维结论

| 维度 | 结论 |
|---|---|
| 正确性 | 通过——四谓词闭环、类型防线严格（bool-as-int 显式拒收）、WIP 优先级正确；P1-1/P2-1 为语义精度缺口非逻辑错误 |
| 安全性 | 通过——无注入面（facts 纯数据、无 eval/exec、路径仅比较不执行）、无硬编码密钥、fail-closed 姿态贯穿（异常/非法开关/记录失败三面） |
| 可维护性 | 通过——表/执行器分离有测试机守、命名清晰、函数短小；P3-1 死 import |
| 性能 | 通过——5.86µs/判定（实测/log 逐字一致），低于预算三个数量级；O(规则×路径) 无热路径风险 |
| 测试覆盖 | 通过——20 用例覆盖全部声称矩阵（4×6+白名单对抗+WIP 堆叠+故障注入×4+off 零漂移+表驱动+性能+协议锚点）；缺口见 P1-1/P3-4 |

## 7. 硬门槛与范围声明

- P0=0 ✓；五维 100% 覆盖 ✓；每条发现带级别+位置+影响+修法 ✓；设计一致性（对 DEC-330 四层执法/scoped/commit 不设卡裁定、DEC-354 预授权降级口径、调研 §8 建议）已完成 ✓；AI 专项 5 项全完成 ✓。
- **结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**。P1-1 建议本票内闭环（纯措辞+裁定收窄，不动行为）；若 Coordinator 判定 P1-1 需行为级修改（债预算 task 域过滤），按 NEEDS_CHANGE 返工通道处理——本审查按「措辞级可本轮修」给 AWN。
- 未验证面显式清单：SHA256/git blob 哈希（禁命令，未重算）；check-governance 21/arch-health 28n/manifest-consistency 三门禁（按 log exit code 采信，未独立复跑）；「既有面零改写」的绝对排除（继承 dirty，无 git diff，三角核验替代）；evidence-log EVD 行落盘（Coordinator 机录面，不属本审查输入）。
- 范围：仅六绑定 file；M-2 既知 3F+1E/21 issues、FEAT-094/096/097 继承 dirty 内容、REL-102 发布链均不在本票裁决面。降级面本身不阻断（预授权）；降级披露经查如实，未触发「披露不实即阻断」。

—— Code Reviewer R0 完（报告正文供逐字落盘 docs/reviews/review-FEAT-095-CODE-R0.md）
