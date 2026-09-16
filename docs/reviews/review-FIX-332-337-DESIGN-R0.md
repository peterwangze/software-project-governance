结论：APPROVED_WITH_NOTES ｜ round=0 ｜ unresolved_blockers=0 ｜ 机录 round 建议 = REVIEW-FIX-332-337-DESIGN-R0（通过终态；P2 备注 F-H 建议随未提交批内修复 + 单 hunk 微核，无需新复审轮——处置权在 Coordinator）

# Design Review — FIX-332 + FIX-337 R0（设计/规则面，独立审查）

| 项 | 值 |
|---|---|
| Task ID | FIX-332（数据资产收口）+ FIX-337（派发纪律） |
| 审查类型 | Design Reviewer（设计/规则面 R0，round 0） |
| 基线 | HEAD `0a13b21`（工作树未提交变更） |
| 审查范围 | 恰 4 文件：`skills/software-project-governance/infra/tests/env_failure_classification.json`、`docs/requirements/test-baseline-0.80.0.md`、`docs/requirements/env-failure-classification-0.80.0.md`、`skills/software-project-governance/references/agent-dispatch-template.md` |
| 明确排除 | 批 E 并行面（`lib/index.js`、`test_dsh_adapter.py`、`test_loop_runtime_claims.py`、`test_verify_workflow.py`、`verify_workflow.py`）；FIX-333 面（`test_triage_write_guard.py` 的 +87 行——仅作运行证据，不作代码审查） |
| 结论 | **APPROVED_WITH_NOTES**（P0=0，P1=0；P2×1、P3×5，均不阻塞） |
| 事实依据红线声明 | 本报告全部结论基于下方实测命令输出与文件/治理记录逐条核对；唯一不可见输入（Developer 的 DEC-194 proposed 文本原文）已显式标注为待验证，未作为任何结论依据 |

---

## 一、独立核验实测记录（2026-09-17，审查方自跑）

| # | 核验项 | 命令/方法 | 实测结果 | 判定 |
|---|--------|----------|---------|------|
| V1 | 变更范围 | `git status --porcelain` + `git diff --stat HEAD` | 工作树 10 文件 = 本批恰 4 + 批 E 5 + FIX-333 面 1；本批 4 文件 diff hunk 与声明一一对应 | ✅ |
| V2 | 金丝雀单跑 | `python -B -m unittest discover -s skills/software-project-governance/infra/tests -p "test_triage_write_guard.py" -k test_live_plan_tracker_flags_only_known_m1_rows -v` | `Ran 1 test ... OK`（0.020s） | ✅ |
| V3 | 模块套件 | 同上去掉 `-k` | `Ran 35 tests ... OK`（无 skipped 标记 = skipped=0）——与 resolved_by/test-baseline 注记声明「现 35 用例含 FIX-333 GBK 反相」逐项吻合 | ✅ |
| V4 | JSON 解析 + resolved 字段 | `python -B -c "json.load(...)"` 逐字段断言 | parse=OK；`resolved=true`；`resolved_by` 718 字符；历史字段 class=`known_defect`/family=`test_assertion_stale`/count=1/since 完整保留；ticket 含 `was:` 历史回指 | ✅ |
| V5 | 历史正文零改动 | git diff 逐字符比对 | env-failure §F2：原 bullet 文本逐字符保留、注记同行尾部追加（diff 呈现为 1 行替换）；test-baseline §4-F2：纯新增 1 行 bullet，零历史行触碰 | ✅ |
| V6 | 红线捆绑包 verbatim 边界 | git diff + 模板 L120-128 通读 | 捆绑包三段（红线原文/R1 摘要/R4 摘要）零改动——防漂移规则未触发 | ✅ |
| V7 | `$home =` 字面串出现计数 | `Select-String -Pattern 'home\s*='`（大小写不敏感）+ 逐条人工核对 `$` 前缀与空格 | 精确字面串 `$home =` 在模板中共 **4 处**：L146（❌ 负相代码示例）、L149×2（违规机制行文 + 机检提示行文）、L200（❌ 清单行）——详见 F-H | ⚠️ P2 |
| V8 | 消费契约现实 | json L196-199 通读 + 全仓 grep `env_failure_classification` | 零 `.py`/配置消费（与 AUDIT-152-CODE-R0 L40 复核一致）；契约 L197 为 prose | ✅（张力点见 F-C） |
| V9 | 交叉引用可达 | 逐一打开 | DEC-194（decision-log L132）✅、`docs/reviews/review-FIX-330-CODE-R0.md` ✅（APPROVED_WITH_NOTES / unresolved_blockers=0，L280）、incident-20260914-fix335 ✅、EVD-1035 事实一致 ✅——无悬空引用 | ✅ |
| V10 | 金丝雀改前状态外推 | `git diff HEAD -- test_triage_write_guard.py` hunk 定位 | 三个 hunk 均为 L591+ 纯新增用例块；金丝雀测试函数不在任何 hunk 内 ⇒ 工作树实测（V2/V3）可外推至 HEAD 状态；HEAD json 改前形态已在 diff 中固化（未 resolved + 过期 evidence）——即「registered id that passes => classification stale」的待收口态，与 FIX-332 动机自洽 | ✅ |

## 二、维度 1 裁决：FIX-332 resolved 登记方案设计

**裁决：方案成立，优于删除。** 依据链：

1. **注册表自身维护语义支持保留**：json L199 `maintenance` 明文「update alongside data-evolution events (new review docs, archive migrations, F2/F3 fixes)」——数据演进事件的规范动作是**更新登记**而非删除条目。resolved 登记正是该语义的落地。
2. **删除方案的代价可枚举**：将丢失 class/family/count/since 四项审计事实（含「since 2026-09-09 (FIX-293 landing)」时间线）与 AUDIT-152 发布基线（REL-075 门禁 11 以该文件存在性为据）的可追溯性。
3. **F-5 先例一致**：FIX-330 已确立「名称保留并披露语义边界」的处置范式；resolved 登记是同一范式在数据资产面的延伸。
4. **条目内 evidence 字段改写（非纯追加）可接受**：移除的「修复候选」文本已在 `resolved_by` 中以 "adopted the recorded flip candidate" 承接，原 ticket 内容以 `was:` 语法回指保留（V4）——历史可追溯性未受损；若保留过期候选文本反而与 `resolved:true` 自相矛盾。
5. **schema 扩展（resolved/resolved_by）与先例一致性**：json 此前已有条目级扩展字段先例（`latent_class`/`latent_family`/`co_causes`），两字段扩展形态一致。但注意 F-B：配套文档 schema 行未同步登记。
6. **消费契约语义自洽性**：L197「registered id that passes => classification stale, flag for cleanup」与新字段的张力见 F-C——无代码消费（V8），人类读者有 `resolved_by` 消歧，P3。

## 三、维度 2 裁决：DEC-194 登记文本（四点结构）

**事实缺口披露（强制声明）**：Developer 报告以 subagent 结构化返回存在于父会话，**其 proposed 文本原文未随本审查任务提供、亦未落盘**（全仓检索无 FIX-332/337 报告文件）——文本级可用性标为**待验证**。以下裁决基于四点结构要求（REVIEW-FIX-330-CODE-R0 L183/收尾#1 L262）与可复核事实基座，Coordinator 落笔时按此验收：

| # | 结构点 | 事实基座（审查方已核） | DEC-194 现状（L132） | 落笔要求 |
|---|--------|----------------------|---------------------|---------|
| ① | 更正依据 | FIX-330 三版本×五场景反相矩阵（不可读场景 HEAD/(a) 均 `fail=1 skip=0`，EVD-1035 + 报告 §二） | ✅ 已载（事实更正段 + 依据列引反相矩阵） | 保持 |
| ② | 最终定性 | 「诊断失真（`{''}` 不指向不可读）」（报告 L183 建议措辞） | ✅ 已载（措辞几乎逐字） | 保持 |
| ③ | 动机层价值 | R0 收尾#1 明文要求「保留 R0 动机层面的价值认定（暴露了 status 面无断言缺口，本 diff ① 已收口）」 | ❌ **缺失**——DEC-194 无此句 | **MUST 补齐**（一句话） |
| ④ | 关联 | DEC-194 + plan-tracker FIX-332 行（L97）双向登记 | ✅ 已载（双向在案） | 保持 |

**文本可用性裁决**：事实基座完全支撑四点结构，文本**现在可写**；无论 Developer proposed 文本为何，落笔稿 MUST 含第③点。FIX-332 的 diff 侧（json resolved_by + 两文档注记）对 ①②④ 的引用与 DEC-194 现文一致，无矛盾。

## 四、维度 3 裁决：FIX-337 规则质量

1. **小节位置——独立新增正确**：新 `### 隔离变量名纪律` 落于「破坏性红线注入」节内、捆绑包代码块与注入纪律之后（L136-149），未改写 M7.7 注入摘要、未触碰 verbatim 捆绑包（V6）——防漂移规则（L134）正确地未被触发。改写捆绑包的替代方案会违反「单一权威副本，修改须经决策记录」，未采纳是正确的。
2. **正相 2 行/负相 1 行 + 规范名 `$tmpHome`**：与任务规范逐项一致（L142-143 正相、L146 负相、L138 规范名）✅。
3. **incident 引用与机制表述**：与 `.governance/incidents/incident-20260914-fix335-dshhome-redirect-failure.md` 逐点吻合（WriteError 不中断 ⇒ DSH_HOME 回落真实主目录 ⇒ 该次 import 链零读写）✅。注意 incident 自身标注「未经 Coordinator 独立复现」，模板以「incident 实证」引用属如实转述；`$HOME` 只读性为 PowerShell 平台已知行为，风险可接受。
4. **机检提示可执行性**：对**声明的作用域**（派发命令与隔离脚本）可执行——字面串匹配、大小写不敏感、grep 即判。但模板自身不变式表述失真见 F-H（P2）。
5. **与 M7.7 权威文本的关系——裁决 MAY（非 MUST），时机=下一规则面批次**：
   - 现状态不构成冲突：M7.7 R1(a) 本就规定「环境变量重定向到临时目录」，命名纪律是该机制的实现细节，二者兼容、纯增量；
   - 权威链先例支持模板承载执行面规则（R3 捆绑包 verbatim 即仅存于模板，M7.7 前言 L707 明示模板为配套执行面）；
   - 但「单一权威副本」原则下，一条规范 MUST 仅存于 reference 文件属权威链弱化——**建议**在下一 behavior-protocol.md 规则面批次（如 0.82.0 规则维护窗口）于 R1(a) 追加一行指针（「隔离命令变量命名纪律见调度模板『隔离变量名纪律』（FIX-337）」）；
   - **升格为 MUST 的触发条件**：若后续决策将该纪律并入 M7.7/R1 正文成为子条款，或 M7.7 被表述为真实环境防护的完备面时，同步即为 MUST。落笔建议：以决策记录固定「权威.home = 模板小节 + M7.7 指针」这一安排，避免双头维护。
6. **Coordinator 禁做清单追加完整性**：新 ❌ 行（L200）含违规形态 + 规范名 + 后果 + incident 指针 + 小节回指，与该清单既有行格式一致、对本 incident 类完备 ✅。
7. **可选 Check 不做——接受**：plan-tracker FIX-337 行明示「可选加一条 Check 扫派发模板」；验收标准（非保留变量名约束 + 一条负相示例）已满足；Check 的边际收益（模板本地 grep）低于 verify_workflow.py 增检 + 测试面成本。机检提示已把检查动作下放到实际执行面（派发命令），代价阈值判断成立。

## 五、维度 4：一致性与范围纪律

- **恰 4 文件** ✅（V1）；本批文件与批 E/FIX-333 面零重叠。
- **批内一致性**：json resolved_by、test-baseline 注记、env-failure 注记三处对同一事实集（FIX-330 落地参数、复跑结果、F-1 证伪、DEC-194 指引）的表述彼此一致且与 EVD-1035/plan-tracker 一致——无相互矛盾。
- **验收措辞（R5 精神）**：本报告对真实环境的表述均为「仓库内只读审查 + 标准测试套件运行」，未使用无限定语的「真实安装/真实环境」措辞。

## 六、Findings 汇总

| ID | 级别 | task | finding | 建议 |
|----|------|------|---------|------|
| **F-H** | **P2** | FIX-337 | 「本节负相示例为该字面串在本模板中的唯一豁免出现」**与实测不符**：字面串 `$home =`（大小写不敏感）在模板实存 **4 处**（L146 负相示例、L149×2 规则行文、L200 ❌ 行）——按该句写 `count==1` 机检的维护者会对本模板误报红（V7） | 一行改写即可：把「唯一豁免」限定为「唯一**代码示例赋值形态**出现（其余出现均为规则行文引用）」或删除该不变式句；机检作用域维持「派发命令与隔离脚本」不变。建议随本未提交批修复 + 单 hunk 微核；或登记为后续批（处置权在 Coordinator） |
| F-B | P3 | FIX-332 | 配套文档 schema 行（env-failure-classification-0.80.0.md L174）未登记 `resolved/resolved_by` 扩展（受「历史正文零改动」纪律约束，未就地改属正确） | 下次数据演进事件的追加注记中补一句「JSON 条目新增 resolved/resolved_by（schema 扩展，同 latent_*/co_causes 先例）」 |
| F-C | P3 | FIX-332 | json L197 消费契约「registered id that passes => classification stale, flag for cleanup」与 resolved 登记保留条目的设计存在语义张力——照章办事的后续操作者可能删除解决记录 | 下次数据演进事件在 `consumption` prose 追加豁免句：「resolved:true 条目为永久解决记录，不适用 stale-cleanup 清除」 |
| F-D | P3 | FIX-332 | ticket 字段引号内文本为 maintenance note（L199）的节选改写（原文含 "new review docs, archive migrations, F2/F3 fixes"），非逐字引用 | 下次触碰该条目时改为准确节选或去掉引号；不追加成本 |
| F-E | P3 | FIX-332 | 两文档注记追加形态不对称（env-failure §F2 为同行尾追加、test-baseline §4-F2 为独立新 bullet）——均满足零改动纪律，纯外观 | 无需行动；记录在案 |
| F-I | P3 | FIX-337 | 规范 MUST 仅存于模板、M7.7 无指针——权威链弱化（裁决见 §四.5：MAY，非现时 MUST） | 下一规则面批次于 M7.7 R1(a) 加一行指针；或以决策记录固定权威归属 |

**已验证正面项（摘要）**：resolved 登记优于删除（五点依据，§二）；金丝雀单跑 OK + 模块 35 OK skipped=0 独立复现（V2/V3）；两文档历史正文零改动（V5）；捆绑包 verbatim 零触碰（V6）；incident 机制表述一致（§四.3）；❌ 清单追加完备（§四.6）；范围恰 4 文件（V1）；全链交叉引用可达（V9）。

## 七、结论

**APPROVED_WITH_NOTES / unresolved_blockers=0**（P0=0、P1=0；P2×1、P3×5 均不阻塞）。

- FIX-332 设计裁决通过：resolved 登记方案与注册表维护语义、F-5 先例、消费现实三方自洽；两文档注记纪律达标；全部事实性声明经审查方当日独立复现。
- FIX-337 规则裁决通过：小节位置规避防漂移规则、捆绑包边界完好、机检提示在其声明作用域可执行、禁做清单追加完备、可选 Check 的代价阈值裁减成立。
- Coordinator 落笔义务（非本 diff 缺陷）：DEC-194 补第③点（动机层价值）；DEC-194 proposed 文本原文未达审查方（待验证项，见 §三）。
- 复审链：本轮为通过终态，无需 R1；若采纳 F-H 批内修复，建议由 Coordinator 将修复 hunk 送本 Reviewer 做单点微核（不构成新审查轮）。
