# FIX-445 — R10 同轮证据补核报告（Design Evidence Reviewer，fresh 非作者）

**Target**: `docs/design/FIX-445-mention-contract-R10.md`（parent-bound SHA 4cb201c2…，135 行，本 child 未重测 hash——只读文本逐行核对）
**前轮引用**: `docs/reviews/review-FIX-445-DESIGN-R10.md`（132 行，BLOCKED/B1：4 份源文件未注入）+ W1

```json
{"verdict":"APPROVED_WITH_NOTES","round":10,"unresolved_blockers":0,"review_scope":"static_contract_analysis_evidence_supplement","implementation_authorized":false}
```

**结论性质**：本结论仅闭合原 R10 的 **B1 证据补核缺口**，判定 R10 静态契约分析本身质量通过。它不解锁任何实现、不修复产品、不改四源验收/健康/交付门；产品侧 W1（corpus 分配歧义）、inherited 64 tests/92.738s/1FAIL、CodeR6 BLOCKED/3 全部保持未闭合。

## 1. 实际文件访问（零执行、零写、零网络）

工具仅 read/grep/glob/skill。14 源全部以 read 分块（80~120 行）读到 End：

| # | 文件 | 读法 |
|---|---|---|
| 1 | `agents/design-reviewer.md` | 102 行全读 |
| 2/3 | design-review / tech-review SKILL | skill 工具全文加载 |
| 4 | `docs/design/FIX-445-mention-contract-R10.md` | 135 行全读 |
| 5 | `docs/reviews/review-FIX-445-DESIGN-R10.md` | 132 行全读 |
| 6 | `.governance/incidents/FIX-445-R10-source-extract.md` | 27 行全读 |
| 7 | `skills/software-project-governance/infra/hooks/commit-msg` | 1284 行 11 块全读 |
| 8 | `skills/software-project-governance/infra/tests/test_hooks.py` | 1480 行 14 块全读（另 1 次 grep 定位） |
| 9 | `docs/design/FIX-445-source-verification.md` | 304 行全读 |
| 10 | `.governance/incidents/FIX-445-DEC336-contract.py` | 24 行全读 |
| 11 | `.governance/reports/FIX-445-R4-escalation.md` | 22 行全读 |
| 12/13/14 | source-verification R2/R3/R5 | 100/61/49 行全读 |

read 调用共约 41 次。无 shell/执行/写入；日期 2026-10-12 沿用 parent 供应，非本 child 时钟。

## 2. B1 补核：原缺 4 文件现已具备，核验如下

**(a) `test_hooks.py`（1480 行）**——R10 分析 §3 的 test 接口 claims 逐符号属实：`_run_scan`（:433，提取五函数管线 real bash，True=BLOCK）；`_step12_replay`（:1048，覆盖 Step-12 两分支——speculation grep :1068 + fabrication scan :1070——per-task batching）；live 测试 `test_current_real_rows_all_clean_under_real_step12`（:1214-1229）要求四任务 `["FIX-444","FEAT-097","FIX-443","FIX-445"]` 行数非零（:1222 `assertGreaterEqual(seen,1)`）且 `assertEqual([],hits)`（:1226）。分析未过度声明；synthetic replay（:1097-1200）的攻击 BLOCK 断言与 per-row attribution 归 diagnostics 的注释（:1193-1196）与「single-match ≠ whole-gate」表述一致。

**(b) `FIX-445-source-verification.md`（304 行）**——§3 七类历史映射（C1 19 行 prose 否定/C2 标记+谓语尾/C3 OLD_PATTERN/C4 check 夹具/C5 observed 判定/C6 observed 归因/C7 哈希）完整在场。R10 分析定位准确：七类**观察**仍是权威归纳，但其 §5 R3 span+anchor(≥16) **contains 豁免机制**已被 R2 C-2/C-3 整值等值凭据（R2 §0/§1，删一切子串通道）与 R5 取代——「historical observations only; containment superseded」属实。

**(c) `FIX-445-DEC336-contract.py`（24 行）**——确为改 `execution-packets.json` FIX-445 packet 状态/next_commands/interruption_policy 的 Python 脚本，`assert last['status']=='FAIL'` 保持实际 FAIL 不改写。它是 Python 文本非 JSON carrier；即使被 `.governance/incidents/*FIX-445*` glob 收进语料，`json.loads`（hook :536）也 parse-error 归零记录（内容类失败=缩减）。分析 claim「changes execution-packet authorization; not a matching JSON carrier for this phrase」完全属实。

**(d) `FIX-445-R4-escalation.md`（22 行）**——R4 熔断升级报告（R4-A 黑名单缺陷、checkpoint 22tests/69.724s/3failures、推荐有界闭表修复）。无任何 current whole-value/prose-binding 接口。分析 claim 属实。

**B1 闭合**：原 R10 report §1 所列 4 缺项全部补齐并核验，原分析对它们的依赖性引用无一处失实。

## 3. 原 analysis 中心 claims 独立复推（静态推演，零执行）

**EVD1587 冲突（§4）——成立**。短语 `已知no-separator当真不能默当获准安全残余` 在 source-extract :17 逐字在场。`当真` 在 hook :770 无条件成框架命中；前文最近 clause 终结符为全角逗号（isterm 含 `，` :726）；窗口=`已知no-separator`（12 chars ≤16）。逐字符过表：`已`不在 24-否定表（:717）也不在 19-填充表（:719）→ 首字符即残留 → bad=1 → rc 0 → Step 12 BLOCK（:1178）。`不能` 在运算子之后不入窗口（R3 §3.1）。prose finding-marker sed 规则（:828-832）只管引号叠否定 `编造/幻觉` 形，与本短语无关。跨 record 凭证不可授：credential 只作用于 strict-obj 有效区内的 typed field（:615-617），prose occurrence 永留 residual。

**Credential/guard 边界（§3）——成立**。`_nodup`(:207)/`_noconst`(:213)/`strict_obj`(:218, end==len 整区消费+无嵌套拯救)/`inst_eq`(:196, ljust 全分数比较，第 7 位差异拒绝——测试 :763-767 印证)/`V==A or _ext(V)==_ext(A)`(:575)/typed-route 矩阵(:621-630, verdict→observed、check→literal/output_as_captured、t2→三者)/Guard G 整拒(:427-428, `not guarded`)/GUARD_TOKENS 七 token(:339, 含当真)。C6 全凭据无 span 仍 BLOCK（测试 :742-748）——「typed attribution 非 whole-value deletion」属实。

**R9/R8 调和（§4）——成立**。R9 例 `：` 重置窗口至 `已知parser-token`（14 chars），`已`残留即拒；`视作`不在框架表（:758/766 仅 当作/当成/视为/作为）。R8 两例 mo=外层 `将/把`（:763），前缀 `将结论`/`把结果` 均不可消费。四例字节互异，无 identical-input/opposite-output 反例——分析未越界声称不可能性。R9 T（48 形/10 字符后缀）与 D3 token/4-5 码点在 hook 中无任何对应实现——「never implemented」属实。

## 4. W1 深化核验与本次具体裁决参数（可审 closure 建议）

**事实链全部核实**：R2 :50 逐字「行内 refs ≤8 + `.governance/incidents/*${TASK_ID}*` glob ≤24，总 ≤32」。hook `corpus_records()`（:478-497）：`got` 每行重置（:483）；行内 refs ≤8（:488 break）；跨行 refs unique 累积无全局 cap（:490-492）；glob sorted 追加**无独立 24 cap**（:493-496）；`files[:32]` 全局截断（:497）。resolve/outside-drop 在 open 之前（:499-527 先 drop :510/:519，open :528）——无 outside-read 破门、无性能推断，与原 W1 一致。

三个静态例核实：(1) 0 refs+32 个可解析 JSON glob 文件 → 32 glob 条目，**违反 glob ≤24 字面**（静态潜力；当前 incidents 目录 FIX-445* JSON 文件远少于 24，**现窗口不触发**，非当前活性故障，且方向保守=误拒豁免面而非逃逸）；(2) 4 行×8 distinct refs → 32 refs 挤掉全部 glob（每行 ≤8 字面合规——歧义）；(3) 16 refs → glob 至多 16（总 32 截断，分配优先级 R2 未定——歧义）。

**具体裁决参数（供 Coordinator decision packet，产品 opening 前必须解决，本 reviewer 不直接改产品/R2 冻结面）**：
1. per-line vs batch pool：维持「行内 refs ≤8」per-line 语义（与 R2 字面一致）；跨行累积 dedup 顺序维持先 refs 后 glob（现行为），须在 packet 明示。
2. separate glob 24 cap：最小产品修正在 :496 后对 glob 结果独立 `[:24]` 截断（或等效：截断优先级 refs 全留 → glob ≤24 → 总 [:32]）。
3. global 32 truncation 优先/不足处理：明确「refs 先占位、glob 后补足至 24、合计再截 32」；不足时（refs>8 行累积超 32）保守截断并记 PATHDROP 诊断。
4. 附原 W1 三静态例为验收用例 + 各自 expected selection；任何产品修正需单独授权 + focused tests（不静默改 R2，不改冻结分析）。

此为触发点当场闭环建议，非「登记以后」；执行主体是经授权的产品修正票，不是本审查。

## 5. 六维度与硬门槛（design-review + tech-review）

| 维度 | 结论 |
|---|---|
| 完整性/结构 | ADR 字段全（日期/背景/决策/备选/排除/影响/后续）；日期为 Coordinator 供应如实标注。**通过** |
| 架构/依赖 | task 抽取→编排→verifier→residual→M5/裸词，无环；tests 绑 canonical 实现无反向依赖。**通过** |
| 接口 | 现接口契约描述经 hook 逐符号核验**无失实**；B（未来 mention 契约）刻意未具体化，正确地未宣称 implementation-ready。**通过** |
| NFR/演进 | 安全/成本/可用性/可维护性有覆盖，继承数据未冒充实测。**通过** |
| 蓝军 | 作者 CH1-4 + 本轮独立 3 挑战（§7）。**≥3 通过** |
| 独立评审 | fresh 非作者 role 执行；**human external membership / DRI 排除仍未知**——沿用如实披露，不发明人类评审。**有边界通过** |

硬门槛：备选 **3≥2** ✅；ADR 字段 **100%** ✅；挑战 **≥3** ✅；无循环依赖 ✅；证据门——原 B1 缺口**本次补齐闭合** ✅。未发现 analysis 自身新需修缺陷。

## 6. 替代方案评估（≥2，溯源）

- **A 保守拒绝（维持）**：安全姿态/权威/历史全保；不能满四任务 clean——分析定位「posture 非 repair」准确。**推荐现状维持**。
- **B source-bound mention**：需独立既有 eligible provenance + 新 payload/prose-binding 契约 + M5/GuardG 交互决策——EVD1587 无此结构，未授权，不保证可实施。核验支持「先决条件未满足」。
- **C 历史分离**：改 mandatory acceptance 未授权。维持原判。

## 7. 蓝军挑战（本轮独立，标准格式）

| 攻击向量 | 影响 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|
| CH-A 补核本身被当「产品已修」信号传播 | 误解锁实现/交付 | 本报告 JSON `implementation_authorized:false` + 三处明示边界 | 低 | Coordinator 机录时保留 scope 字段原样 |
| CH-B W1 在产品重开时被静默搁置 | glob>24 场景合法凭据被误拒（保守失效）或 R2/代码漂移 | §4 裁决参数 + 三验收用例 | 中 | decision packet 逐项裁决后才准产品 opening |
| CH-C 两时点测试账目（R4:22/69.724s/3F vs R10:64/92.738s/1F）被混读为矛盾 | 审计噪音/误判历史失实 | 两者均可溯源（R4 escalation :9 / EVD 与 seq46 账） | 低 | 后续引用注明测量时点 |

## 8. NFR 映射（摘要）

安全：strict 凭据/typed offset/Guard G/residual 全检——非密码学承诺（CH1 两边可 forge，本地一致性边界如实）；可靠性：fail-closed 全腿（read :531-534 / slice-mismatch :610 / count :644）；性能：总 32 cap 保持，CPU27.8/CLI36/434339/32MiB/1500 继承未测；可用性：合法 prose（EVD1587）仍被拒——冲突未解，如实保持；可维护性：单一可审契约优于词法补丁。

## 9. 结论与边界

**APPROVED_WITH_NOTES / unresolved_blockers=0**——仅就 R10 静态契约分析的**证据补核与质量**：B1 闭合，中心论证、接口描述、credential/guard 边界、R9/R8 调和、替代方案、挑战全部经 14 源独立核验无失实。

**Notes（非阻塞）**：N1=W1 产品侧分配歧义（§4 裁决参数已给，产品 opening 前必须解决）；N2=测试账目两时点并存防混读；N3=human Bar Raiser 资格未知。

**不变项**：产品两文件未动；inherited 64/92.738s/1FAIL、CodeR6 BLOCKED/3、原 seq46/txn-c1193e…、原 R10 report 与 R10 分析冻结不动；future independent Code review、12 individual B2、protected B3 faults、全四任务源、模块/健康/交付门全部保持待办。本通过不构成 FIX-445 完成、实现就绪、风险接受或发布批准。Round 10 已超 fuse：T4 语义，无 automatic R11。

（正文约 1750 中文字。持久化建议：parent 原样 persist 至 `docs/reviews/supplement-FIX-445-DESIGN-R10-evidence.md`，随后按 M7.4 以本 JSON 机录 review-record。）
