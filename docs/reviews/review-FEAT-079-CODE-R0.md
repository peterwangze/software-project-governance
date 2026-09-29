# FEAT-079 代码审查报告 — R0

- **任务**: FEAT-079（M1-B1b 锚点注册表+预算验证——DEC-290(4)(6)/DEC-291）
- **Reviewer**: Code Reviewer（独立审查，R0 首轮）
- **日期**: 2026-09-29
- **基线核实**: HEAD = `3544d09`（FEAT-078 已落）✅；工作树恰 3 个待审文件（未提交 diff），规模 663+/6−（声明 +650/−2，吻合）
- **审查对象**: verify_workflow.py（staged 注册表 9 锚 + staged 面语义 + Check 33 渲染扩展）/ checks/injection_budget.py（DEC-291 常量 + measure_clause_anchor_lines + check_contract_tier_budgets + 集成与渲染）/ tests/test_verify_workflow.py（时态无关 fixture + 10 新测试 + ENTRY_TEMPLATE_CANONICAL_BYTES 四值补登）

---

## 1. 结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`；findings：P0×0 / P1×0 / P2×1 / P3×4）

七项验收全部核验通过：staged 三态语义（inactive 披露/active 全守/部分注入 FAIL）代码与运行时双重证实；防夹带原语按「锚点行逐行计价」正确实现；分档断言与 Coordinator 已裁定的 per-surface 口径逐点一致；fixture 时态无关性由显式状态构造保证；四字面量与 B1a 定稿文件实际字节精确一致（双路机证）；R4 print 1318==1318 零增殖；预存在红×3 归因核实成立（R1 与 metadata_contract 两项获 Reviewer 独立结构性确认）。

## 2. 七项验收核验结果

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| ① | staged 面语义正确 | **通过** | 代码：`active = any(any(hits.values()))`；active 时逐面逐锚收集 missing 并 `issues.extend`（verify_workflow.py staged 段）。三态运行时证实：合成 inactive fixture（`test_staged_inactive_before_b1a_text_disclosed_not_failing`）零 issue+披露字段；合成部分注入（`test_staged_partial_injection_fails_closed`）FAIL 且 missing 带 stage id；当前实态 check-injection-contract 输出 `staged ADR-021-B1a: active, 9 anchors guarded` + PASSED（exit 0）——B1a 已落=active 9 锚全守。文件缺席时该面锚全记 absent，active 下计 missing（fail-closed 方向正确） |
| ② | measure_clause_anchor_lines 原语正确 | **通过** | 实现：空文本→0；否则 `sum(estimate_surface_tokens(line) for line in splitlines() if anchor in line)`——锚点行**整行**计价、多行累加（跨行/跨面拆分不可逃逸）。`test_measure_prices_every_anchor_carrying_line` 断言：非锚行免费、双锚行求和精确、他锚 0、空文本 0——4 边界全覆盖。夹带文字落在锚行内即使测量超档→FAIL（负向测试 `test_over_limit_m1_clause_fails` 证实：M1_LINE×4 注入 agents 面→per_surface 91→超 180→verdict FAIL） |
| ③ | per-surface 断言与 DEC-291 裁定一致 | **通过** | `check_contract_tier_budgets` 逐条：own-line 断言 `clause["per_surface"][name] > budget` 逐面判超；combined 断言 `combined_per_surface[name] > 370` 逐面判超；四面合计仅在 issue 文本与渲染中 "reported, not gated"；`"scope": "per-surface"` 结构化自述。与裁定「逐面测量；合计口径无防夹带意义」逐点一致。实测 worst：M1 entry 171≤180 / combined entry 342≤370（三 profile 同值） |
| ④ | 剥离 fixture 时态无关性 | **通过** | `_strip_staged_clause_anchors` 双模式匹配 B1a 实际形态：整行删除（persona/governance-init——B1a 新增行，词剥离残渣 ~300 tok 会推爆 resident 硬门——Developer 声明的 6083>6000 真实红对应修复）+ 词剥离（AGENTS/SKILL/behavior-protocol——关键词嵌于既有行，整行删除会破坏基础注册表锚）。两时态等价：B1a 前剥离为 no-op（无锚可剥）；B1a 后显式构造 pre-B1a 基线。`test_live_repo_staged_face_is_coherent` / `test_live_repo_contract_tier_face_is_coherent` 按 active/inactive 双分支断言——当前（B1a 已落时态）43 测试全绿即两测试的 active 分支实证，inactive 分支由合成 fixture 测试实证 |
| ⑤ | ENTRY_TEMPLATE_CANONICAL_BYTES 更新合法性 | **通过（双路机证）** | 值变更 4555→5089 / 9553→10087 / 10441→10975 / 2766→2840（entry 三 profile 各 +534=契约 5/6 行；thin +74=指针行）。路1：Feat039 定向测试（含 `test_entry_template_surfaces_price_the_canonical_blocks`）pass——字面量==实际计算字节；路2：check-injection-budget 三 profile 的 bytes 列独立显示 5089/10087/10975/2840——与字面量精确一致。注释块按 guard discipline 显式记载 deliberate re-price（rides-the-ticket 补登合规，价格未静默移动） |
| ⑥ | R4 print 零增殖 | **通过** | 机核：HEAD `print(` 计数 1318 == 工作树 1318（Select-String -AllMatches）。Check 33 两处渲染均为**修改既有 print 语句**（拼接 staged_summary），零新增 print 语句 |
| ⑦ | 预存在红×3 归因核实 | **通过（2/3 独立确认，1/3 采信）** | R1：独立确认——committed baseline `anchor_loc: 26478` < HEAD 引擎实际 26508 行（26582−76+2 复算吻合）——FEAT-078 结构增量未随 regen，红在 HEAD 无本 diff 即存在；本 diff 不触 baseline.json。metadata_contract：独立确认——test_archguard_ratchet.py:496 钉 26385，而 FEAT-075 regen 已将 committed baseline 升至 26478（字面量自 REL-094 后未同步）——与本 diff 零耦合（diff 不触 baseline/该测试）。registry substring：未在协议复跑范围内独立复现（无测试 ID 可定向）；采信 Developer git-stash 证据 + 结构分析（diff 仅触 3 文件，registry 测试钉定面均不在其中）——残留风险低 |

## 3. Findings

| 级别 | 位置 | 问题 | 建议 |
|------|------|------|------|
| **P2-1** | verify_workflow.py（本批 +74 净行：26508→26582） | 本批使 R1 基线超差由 30 行（FEAT-078 遗留）加深至 104 行。非代码缺陷——DEC-260 纪律即「结构增量先落、再锚定走分离 regen 提交」（FEAT-075: 26413→26478 / FIX-400: 26385→26413 先例）；但 pending regen 义务因本批扩大 | 后续 R1 regen 提交须一并覆盖 FEAT-078（+30）与 FEAT-079（+74）并双票引用；该 regen 须在任何将 R1 视为 fatal 的发布门前落账（与 acceptance ⑦ 同一收口动作） |
| **P3-1** | checks/injection_budget.py 常量注释 | 「measured floor across the four resident surfaces is ~349 tok combined」混淆两个口径：349≈FEAT-078 四面文件增量合计（实测 348），而 per-surface 最重面 floor 是 entry 342——后文括号数字（171/342）才是准的 | 措辞澄清（如 "total added across surfaces ≈348 (FEAT-078 measured); heaviest per-surface floor 342 on entry-template"）——仅注释，无行为影响 |
| **P3-2** | checks/injection_budget.py format_budget_report combined 行 | `worst surface N tok <= 370 (hard; ...)` 在 FAIL 态仍渲染 "<="（紧随 [FAIL] 行，不构成误导性通过，但读感别扭） | FAIL 态可改为 `vs 370` 或条件化措辞——纯渲染 |
| **P3-3** | checks/injection_budget.py check_contract_tier_budgets | 函数体 ~60 行（含 20 行 docstring），略超 50 行建议线；内部顺序清晰（构造→合计→断言→notes） | 若后续增长可拆 issues/notes 构造器；当前不强制 |
| **P3-4** | 审查过程（非代码） | registry substring 预存在红未获独立复现（协议复跑面外、无测试 ID）；归因依据=Developer git-stash 证据 + diff 范围结构性分析 | 后续任一会话跑到该红时补一条 HEAD worktree 复现记录即可闭环归因链 |

## 4. 定向复跑证据（Reviewer 会话内，TEMP 重定向 check-run-20260929，重试 0/2）

| # | 检查 | 结果 | 关键数据 |
|---|------|------|---------|
| 1 | check-injection-contract | **PASS**（exit 0） | `Files checked: 4; anchors: 30; staged ADR-021-B1a: active, 9 anchors guarded`——30 基础锚零回归 + staged active 9 全守 |
| 2 | check-injection-budget ×3（lightweight/standard/strict，--fail-on-issues） | **PASS**×3（exit 0） | strict resident **5957 ≤ 6000**（余量 43）；standard 5685 / lightweight 4207。分档（三 profile 同值）：M1 worst surface **171 ≤ 180**；combined worst surface **342 ≤ 370**；合计 361/350/711 均 "reported only"。锚行分布：M1 = agents 91 / entry 171 / persona 76 / thin 23；M2 = agents 91 / entry 171 / persona 65 / thin 23 |
| 3 | pytest 定向（-k InjectionContractStaged or ContractTierBudget or Feat039 or PresetVersionLine） | **43 passed**（exit 0，1.13s；2 subtests passed） | 与 Developer 声明「43 tests OK」精确一致；含 10 新测试（staged 5 + tier 5）全绿 |
| 4 | R4 print 计数（HEAD vs 工作树） | **1318 == 1318** | 零增殖机核 |
| 5 | R1 基线结构核 | 确认预存在 | baseline anchor_loc 26478 / HEAD 引擎 26508 行 / 工作树 26582 行（+74 净行复算吻合） |

**与 Developer 声明的红绿史交叉印证**：FEAT-078 R0 已实测 strict 5609→5957 增量 348（persona +141 = 本批 M1 76+M2 65 逐面精确对应；entry +171 = M1 行价）；本批 agents 面 91 tok 为关键词所嵌**既有行**整行计价（词剥离模式佐证）——两套口径（文件增量 vs 锚行计价）数字互洽，计价基线一致。

## 5. AI 代码专项 5 项检查

| 项 | 结论 |
|----|------|
| mock 残留 | 无——全部真实函数/真实文件（fixture 为 copyfile 真面 + 显式合成态） |
| 硬编码返回值 | 无——预算线读模块常量（测试亦读常量不钉字面量，B1a re-tune 不 reddens——设计明示）；剥离 helper 的文件清单/关键词为 fixture 数据，可溯源 B1a 形态 |
| 幻觉 API 调用 | 无——estimate_surface_tokens / load_injection_surface / set_injection_budget_surface_profiles / _governance_temp_dir / vw.ROOT 均实证存在（43 测试导入运行通过） |
| 未实现 TODO | 无 |
| 过度实现 | 无——registry + 原语 + 断言 + 渲染 + 测试，无投机面；partial 披露 note 为激活门语义必需 |

## 6. 五维度结论

| 维度 | 结论 |
|------|------|
| 正确性 | 通过——三态语义/计价原语/逐面断言/集成次序（issues.extend 先于 verdict 判定）逐行核读 + 运行时证实；None/空文本/文件缺席边界均 fail-closed 方向 |
| 安全性 | 通过——纯内部文本测量，无外部输入面、无密钥、无注入向量（OWASP 面不适用） |
| 可维护性 | 通过——DEC 引用注释完备、命名表意；P3-2/P3-3 两处小瑕 |
| 性能 | 通过——O(行数×锚数) 线性扫描 ×4 面 ×3 profile，量级微小 |
| 测试覆盖 | 通过——10 新测试覆盖 inactive/active/partial/越档 M1/越档 combined/合规稳态/原语边界/live 双分支；负向路径完整；覆盖率数值未测（定向面外），分支覆盖由用例枚举证 |

## 7. 设计一致性

DEC-290(4) staged 注册表激活门（commit-order 披露、anti-silent-partial）✅；DEC-290(6)/DEC-291 分档冻结线 180/370 + per-surface 口径（Coordinator 裁定口径逐点一致）✅；ADR-021 §2.1 关键词锚定（序数漂移规避）+ persona 专属「用户点名」✅；DEC-260 regen 分离提交纪律（P2-1 提示后续义务）✅。

---

**报告路径**: `docs/reviews/review-FEAT-079-CODE-R0.md`
