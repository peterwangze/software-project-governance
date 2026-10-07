# Code Review R0 — FEAT-089（Check 30c WARN→FAIL 升级批：豁免清单+V6d 收紧+DEC-146 ④ 侧记录）

- **轮次**: R0（首次审查）
- **日期**: 2026-10-07
- **审查人**: Code Reviewer Agent（独立审查者——未参与开发；只读审查+本报告；零产品代码/测试/治理数据修改）
- **审查对象**: 未 commit 的 working tree 改动（7 修改 + 1 新增 untracked，+882/−134）
- **审查结论**: **APPROVED_WITH_NOTES**
- **unresolved_blockers=0**（独立结构字段——无未解决 BLOCKING finding；非阻塞 findings 见 §4，共 4 条：P2×1 / P3×3，随收口流程跟踪）

---

## 1. 审查范围（git diff 实测核对）

| # | 文件 | 改动 | 声称一致 |
|---|---|---|---|
| 1 | `infra/exception_registry.py` | +167（REVIEW_PROVENANCE_EXEMPTIONS L402-435 / 结构校验 L444-483 / canonical sha256 L486-497 / 四键匹配 L499-528） | ✅ |
| 2 | `infra/checks/review_domain.py` | 390 行改（30c 本体 L3188-3196 常量、L3246 ledger 计数、L3309 侧记录断言、L3360 起主函数） | ✅ |
| 3 | `infra/checks/review_exemptions_30c.json` | 新文件（untracked，70 行——DEC-146 ④ 侧记录） | ✅ |
| 4 | `infra/verify_workflow.py` | +49/−27（30c 消费块 L17578-17640：violations→all_issues L17615、V6d WARN 显示不计入、escalation 判定面打印） | ✅ |
| 5 | `references/behavior-protocol.md` | 2 处（L558 C8 段 / L568 违反检测段——FAIL 语义同步） | ✅ |
| 6 | `infra/registry.py` | ADVISORY_SEGMENTS 移除 "30c"（L153-160 区）+docstring 8→7 sections | ✅ |
| 7 | `infra/tests/test_verify_workflow.py` | 3 处断言翻转（L22653-22740 区，FIX-344 族 V7/V8 warnings→violations） | ✅ |
| 8 | `infra/tests/test_review_machine_provenance.py` | +316/−40（10 处断言语义翻转 + 新增 Check30cFailEscalationTests 13 用例 L612-876 区） | ✅ |

`git status --porcelain` 实测恰为上述 8 文件，**无 `.governance/` 面改动、无锁外未申报改动**（范围纯粹性 ✅）。numstat 合计 882/134 与申报一致。

---

## 2. 义务符合性逐条对照（审查基准：DEC-146 ②③④ / DEC-321 / 验收⑤）

| 义务 | 事实依据（独立核验，非采信散文） | 判定 |
|---|---|---|
| **DEC-146 ② 豁免两行登记，不回写不改写历史行** | `exception_registry.py` L402-435：EXEMPT-30C-001（FIX-256）/EXEMPT-30C-002（FIX-258），均 record_date=2026-08-22/rule=V7/face=row/approved_by="DEC-146(2) + DEC-321"。git diff 无 evidence-log 改动；evidence-log L859/L868 两行原文在案未动（ID cell `REVIEW-FIX-256/258-CODE-R0` verbatim，date 2026-08-22，APPROVED_WITH_NOTES/unresolved_blockers=0 尾列在） | ✅ |
| **DEC-146 ② FAIL 条件（覆盖率 100% 且持续 ≥2 发布版本）** | `review_domain.py` L3799-3831 escalation 判定面：`condition_met = judged>0 ∧ honored==judged ∧ releases>=2`；live 复跑（本审查 §5）honored 479/479=100.0% × 23 releases → condition_met=True。「持续」语义等价性成立：evidence-log 单调追加（provenance 诚实纪律禁删改），当前态 100% ∧ violations=0 ⟹ 2026-08-22 后任意发布时点 honored 覆盖率均 100%（中途手写行会存留至今并 FAIL——live 0 违规即证明不存在） | ✅ |
| **DEC-146 ② V6d 收紧（无日期即 WARN）** | `review_domain.py` L3595-3610（文件面）/L3684-3701（行面）：undated → warnings（rule=V6d），不进 violations；`verify_workflow.py` L17627-17633 WARN 显示段明示「never increments all_issues——DEC-146 ③ accepted baseline」。live 42 WARN（rows 2+files 40）全部 rule=V6d，full 引擎 2 issues 中零贡献 | ✅ |
| **DEC-146 ④ 不可伪造 JSON 侧记录（change-triage 式）** | `review_exemptions_30c.json`：schema_version/record_type=check30c-fail-escalation/exemptions_sha256=53615bc6…87ce/escalation_basis 快照（coverage_raw 477/479 + honored 479/479 + releases 23 + live_measurement 全要素）。本审查独立复算 canonical sha256（§5）与 pinned 逐字符相等 | ✅ |
| **DEC-321 两行首批入册+禁补录** | 豁免=清单登记 only（`match_review_provenance_exemption` 查表），无任何 review-record 补录路径；registry docstring L397-401 明载 DEC-321 方法勘正理由（补录伪化持久化时点+提前触发 100%） | ✅ |
| **验收⑤ 显式豁免留痕（不动 persona）** | 依据链成立：AUDIT-155/156 R1 L30（机录契约注入面=persona 第 4 行，1535B≤1536 预算满——persona 不可扩）+L17（canonical 定位 behavior-protocol L558）；本次只改 canonical 两处（L558/L568），L560 最小契约投影关键词行未动（diff 上下文行证实）；ADR-021 锚点关键词制下未动关键词即不触发注入面同步义务——check-injection-contract 30 锚 PASSED 实证（§5） | ✅ |

---

## 3. 技术正确性验证

### 3.1 豁免四键匹配的误吞面分析

- **键集**：(rule, task_id, record_date, face)，`exception_registry.py` L499-528。rule∈{V7,V8} 白名单（L466-468 校验）；face∈{row,file,any}；record_date ISO 字符串与 `date.isoformat()` 精确等值（L517——2026-08-22 登记不吸收 08-23）。
- **face 键防住跨面误吞**：清单两条目 face="row"——文件面查询 face="file" 时 `entry["face"] not in (face,"any")` 不匹配（`review_domain.py` L3612 文件面豁免查询 → 手写文件不会被 row 豁免吸收）。测试 `test_exemption_miss_wrong_date_fails`/`test_exemption_miss_wrong_task_fails` 锁定日期/任务维度。
- **task_id 规范化**：V7 行扫描器 `_REVIEW_ROW_ID_FINDITER_RE`（L3224）从 ID cell `REVIEW-FIX-256-CODE-R0` 提取 `REVIEW-FIX-256`（ROLE 段 -CODE-R0 天然不匹配 `(?:-R\d+)?`），m_id（L3714）得 task_id=FIX-256——ROLE 段不进键，record_id 字段保真原文（docstring L32-35 披露设计意图）。
- **吸收面实测**：`grep '^\| REVIEW-FIX-25[68]'` evidence-log 恰 2 行（L859/L868）——豁免吸收面与登记面 1:1，无邻行可吞。
- ⚠️ 边界（→ F-2，P3）：键集不含 round 维度——同 task 同日的另一轮手写行（如虚构的 REVIEW-FIX-256-R1@2026-08-22）会被同一豁免条目吸收。live 无此形态（每 task 恰一行）；DEC 登记粒度如此且 docstring 已披露。属设计边界非缺陷。

### 3.2 escalation 数学口径

live 复跑（§5）：machine_total = 67（rows）+410（files）=477；honored = 477+2（rows_exempted）+0 = 479；judged = 69+410 = 479。coverage_raw = 477/479 = 99.6%，coverage_exemption_honored = 479/479 = 100.0%——**raw 与 honored 之差恰 = 豁免 2**，分子分母口径自洽，与侧记录快照逐数一致。

### 3.3 releases_since 的 ledger 过滤与可注入性

`_released_versions_since`（L3246-3307）：`core/releases/*.json`，effective_state.lifecycle_state 优先、非 withdrawn、首个可解析 events[].recorded_at ≥ 生效日；单文件 parse 失败 skip（fail-open 不虚增，L3279-3281）。本审查独立复算（§5）：23 个版本 = 0.76.0~0.96.0（含 0.78.1/0.93.1 patch），与函数返回值相等、与侧记录 releases_source 披露口径（lower bound，ledger 起步 0.62.0）一致。可注入性：`test_released_versions_since_injectable` 四形态 fixture（生效日后 released 计/日前不计/candidate 不计/withdrawn 不计）→ 断言 n==2，注入通道（releases_dir 参数）真实生效。

### 3.4 fail-closed 三面（读代码证实，非听声称）

1. **清单 malformed→inert**：`load_review_provenance_exemptions`（L444-483）逐条校验必填九字段/rule/face/ISO 日期，malformed 即 drop+errors（不参与匹配——L514 注释「an entry that cannot prove its scope never matches」）；同时 errors 经 `_verify_exemptions_side_record` L3332-3338 转为 EXEMPTION-SIDE-RECORD FAIL——双重兜底。
2. **侧记录漂移/缺失/畸形→FAIL**：`_verify_exemptions_side_record`（L3309-3357）三 miss 路径全覆盖——exception_registry 不可导入（L3316-3321）/registry malformed（L3332-3338）/侧记录文件缺失或不可解析（L3339-3347）/pinned≠live hash（L3348-3356）→ 均 verified=False → violations.append（L3791-3796）。测试 `test_side_record_hash_mismatch_fails_closed` 以 mock 追加伪造条目真实驱动 hash 比对路径 → EXEMPTION-SIDE-RECORD FAIL 断言通过。
3. **hash 断言每跑执行**：`check_review_machine_provenance` 函数体尾部（L3789-3790）**无条件**调用 `_verify_exemptions_side_record()`——fixture 与 live 双路径共用该主干，不存在跳过分支。

### 3.5 消费端（verify_workflow.py）

L17615 `all_issues += len(mp30c["violations"])`——V7/V8/EXEMPTION-SIDE-RECORD 计入 all_issues（FAIL 语义兑现）；L17627-17633 V6d WARN 仅显示且明示不计入；L17596-17612 escalation 判定面全要素打印（coverage raw/honored 分子分母+百分比 × releases × condition_met × side record verified）。与 behavior-protocol L558/L568 新文本逐句对应。

### 3.6 联动完整性与协议同步

- **ADVISORY_SEGMENTS 移除 "30c"**：测量事实镜像同步——`test_registry.py::CheckRegistryTests`（AST pass 重判）复跑全绿（§5，含 test_registry 86 passed）；`_run_full_engine_checks` 30c 段现有 all_issues AugAssign（L17615）支撑移出。severity floor 语义正确。
- **断言翻转恰为语义变化面**：`grep 'rule"\] == "V[78]"'` test_verify_workflow.py 全文件恰 3 处（L22666/L22714/L22733）且全部已翻转 violations，无遗漏未翻转的 V7/V8 warnings 断言；test_review_machine_provenance.py 10 处翻转均为 V7/V8 WARN→FAIL 语义面，绿保持测试（discharge/pass 族）未动——无过度翻转。
- **L560 投影关键词行未动**：diff 中该行为上下文行（无 ±）；check-injection-contract 30 锚 PASSED（§5）实证注入契约不受影响。

---

## 4. Findings

| ID | 级别 | 位置 | 事实与建议 |
|---|---|---|---|
| **F-1** | **P2** | archguard-ratchet（R1/R4/R7）+ test_archguard_ratchet.py | 交付树 ratchet 4 violations（R1 mainfile 27895>27866 +29 / R4 print total 1375>1371 与 _run_full_engine_checks 625>621 各 +4 / R7 baseline-stale 连带）+ test_archguard_ratchet 6 failed——全部为本票 30c 消费块/判定面渲染的 sanctioned 增量（逐轴归因本审查复跑吻合，增量面与申报一致，无 hand-edit）。packet（execution-packets.json FEAT-089）maintainability.validation 已结构化登记收口路径：「Code Review R0 AWN/0 后执行 --regen → 复跑 0 violations + 冻结字面量用例绿」，且 18f pending + 验收命令 `check-governance --summary-only && archguard-ratchet` 的 && 链使 last_run 回填被 ratchet exit 1 硬性阻断——**收口义务不可逃逸**。按先例链（DEC-320 路径 A/DEC-324 同构）R0 先审后 regen 顺序成立，不构成本轮阻断；**收口时 MUST 完成 regen rider + 全轴 PASS + 18e/18f 回填**（DONE 定义第 3/4 条）。 |
| **F-2** | P3 | exception_registry.py L499-528（match 键集） | 豁免键无 round 维度：同 task 同日的异轮手写行会被单条目吸收。live 实测每 task 恰一行（grep 锚定 ^\| REVIEW-FIX-25[68] 仅 2 行），DEC 登记粒度如此且 docstring 已披露；若未来登记含多轮任务的建议在 note 字段显式写明轮次范围或由 DEC 裁定扩键。 |
| **F-3** | P3 | 验收措辞 / verify_workflow.py L16095-16096 | 「check-governance exit 0」为弱信号：cmd_check_governance 仅在显式 `--fail-on-issues` 且 issues>0 时 exit(1)，默认 exit code 恒 0——exit 0 与执行包 FAIL 行并存是引擎设计而非矛盾。**裁定（Coordinator 提请复核的疑点）：Developer 的 exit-0 声称在其运行时点技术上可能成立，不构成不实申报**——执行包骨架 FAIL（TO_BE_DEFINED 占位，派发前已生成）只影响输出中的 [FAIL] 行不影响 exit code；且 packet ux.evidence 已如实披露「5 issue 均为执行包骨架项，V6d 零贡献」。建议后续验收措辞以 issues 计数或 --fail-on-issues 为准（本票验收 && 链中 ratchet 的 exit 语义已提供有效硬门）。 |
| **F-4** | P3 | review_domain.py L3283-3296（_released_versions_since） | recorded_at 取 manifest **首个**可解析事件日期而非 released transition 事件日期（candidate 创建日早于发布日）——计数只会偏少不会偏多，对「≥2」阈值是 fail-closed 方向的 lower bound；docstring 与侧记录 releases_source 均已如实披露该口径。无需修改，登记观察。 |

**P0=0，P1=0，P2=1，P3=3。**

---

## 5. 复跑实录（本审查独立执行；Windows pwsh，python -X utf8）

| # | 命令/方法 | 结果 | 与声称对照 |
|---|---|---|---|
| R1 | `pytest tests/test_review_machine_provenance.py -q` | **41 passed** in 0.63s | =「41 passed（绿）」✅；红态算术自洽：13 新用例+10 翻转断言=23=申报红数 ✅ |
| R2 | `pytest test_verify_workflow.py::ReviewFileSuffixAwarenessTests + test_registry.py -q` | **86 passed** | 3 处翻转断言绿 + ADVISORY_SEGMENTS 镜像重判绿 ✅ |
| R3 | 30c live 直调（check_review_machine_provenance） | 0.22s；verdict=WARN；**violations=0**；warnings=42 全 V6d（rows 2+files 40）；rows 69/67/2、files 410/410/0；cov raw 477/479=99.6%；honored 479/479=**100.0%**；releases=**23**；**condition_met=True**；side_record verified=True | 六元组全部吻合 ✅；与侧记录 escalation_basis.live_measurement 逐数一致 ✅ |
| R4 | canonical sha256 独立复算（python 直调 exception_registry） | live=**53615bc68488cf2d9d754592998dd85b41da5937dd56410407186fea19f287ce** == pinned ✅；load_errors=[]；侧记录 exemptions 数组与 registry 键字段逐条相等 | 钉扎真实 ✅ |
| R5 | release ledger 独立复算（独立脚本重放过滤逻辑） | 23 个（0.76.0~0.96.0 含 0.78.1/0.93.1）== 函数返回 ✅ | =「ledger 口径 0.76.0~0.96.0」✅ |
| R6 | `verify_workflow.py archguard-ratchet` | **FAIL（4 violations）**：R1 +29 / R4 +4 / R4 +4 / R7 stale | 逐轴与披露吻合（Coordinator 复核事实同）✅ → F-1 |
| R7 | `check-injection-contract` / `check-cross-references` / `check-injection-budget` | **30 锚 PASSED（exit 0）** / **exit 0** / **4303≤6200 PASSED** | 三项全吻合 ✅ |
| R8 | `check-governance --summary-only`（full） | **2 issues**（18d-RB2/18f——FEAT-089 packet 收口 pending 项），exit 0；30c 面零 issues 贡献（V6d 不计入实证） | 与「两项诚实 pending 待收口回填」一致 ✅ → F-3 裁定依据 |
| R9 | `pytest test_archguard_ratchet.py -q` | **6 failed / 32 passed**（逐条归因 R1/R4×2/R7/CLI exit——baseline 未重锚） | =「6=ratchet 本票增量」✅ → F-1 |
| R10 | `pytest test_contract_matrix.py / test_contracts.py -q` | **3 failed/24 passed**（matrix drift）/ **1 failed/156 passed**（M0 pin hash） | =「4 预存」✅（干净树同红引用 Coordinator 复核事实——本审查未 stash 工作树，避免破坏审查对象） |
| R11 | 全套件 4732P/11F | 未整跑（按派发指令引用 Coordinator 复核事实）；已核实构成 6（R9）+3+1（R10）=10，余 1 为申报 flaky（loop_claims 单跑绿——未复跑，无反证） | 吻合度充分 ✅ |

**R5 违禁措辞扫描**：packet 验收标准/quality_budget 全部 validation 命令为只读复算类（直调计时/summary-only/archguard-ratchet），无「真实安装/真实环境」类措辞 ✅。

---

## 6. 结论

DEC-146 ②③④ 三动作 + DEC-321 处置 + 验收⑤依据链**全部经独立验证成立**：豁免两行四键精确登记且吸收面 1:1、历史行零改写（git diff 无 .governance 面）、V6d 收紧 WARN 不计入、侧记录 sha256 钉扎独立复算相等且三面 fail-closed 读代码证实、escalation 判定面分子分母可复算（479/479 × 23）、协议两处 FAIL 语义与引擎行为一致且注入契约 30 锚无扰、断言翻转恰为语义变化面无过度翻转、fixture 保真（ID cell verbatim/FX258 修正后结论与 live L868 一致）。Developer 全部关键声称经抽查复跑吻合；唯一疑点（check-governance exit 0）裁定为技术上成立的弱信号而非不实申报（F-3）。

**APPROVED_WITH_NOTES / unresolved_blockers=0**

收口前置（非本轮阻断，流程已结构化强制）：F-1 regen rider（全轴 PASS + 6 测试转绿 + 18e/18f 回填 + last_run 落 EVD）。

## 给 Coordinator 的后续动作

- 结论为通过终态（T3）：可继续 step 5（commit）链；但**commit 前建议先完成 F-1 收口**（regen rider→复跑 0 violations→18e/18f 回填→验收命令整链 exit 0），使 DONE 定义第 3/4 条与交付态一致。
- 本结论按 (C8)/FIX-260 须经 `review-record` CLI 机器持久化（REVIEW-FEAT-089-R0）；NEEDS_CHANGE 复审义务为空。
- F-2/F-4 为观察级，随下次触碰 30c/ledger 的任务顺带考虑即可，不单独设轮。
