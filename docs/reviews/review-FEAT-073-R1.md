# 设计审查报告 — FEAT-073 R1（A+B 实施面复审）

- **Round**: R1（实施产物后置审查；前轮引用：`docs/reviews/review-FEAT-073-R0.md`——R0 APPROVED_WITH_NOTES / unresolved_blockers=0，F-1~F-7 已处置）
- **审查对象**: Governance Developer 按 ADR-020（R0 修订版）§3.1+§3.2 实施的 7 个 tracked 修改（工作树现行态）
- **日期**: 2026-09-28
- **审查人**: Design Reviewer Agent（独立于实施 Developer；本报告同时承担 tech-review Bar Raiser 单 agent 最低标准）
- **审查类型**: 设计/架构审查（实施面规格一致性 + 契约无弱化验证）

## 一、六维度逐项结论

| # | 维度 | 结论 | 依据摘要 |
|---|------|------|---------|
| 1 | 方案完整性（实施规格落实） | **PASS** | ADR §3.1 保留/删除/新增三面与 §3.2 B-a/B-b/B-c/B-d 四子项全部按规格落实（逐面见二.1/二.3）；实施期两处口径偏离均经约束源测试核实为**必要且语义等价**（见二.2）；R0 三条实施相关 findings（F-2/F-3/F-7）已落实到位（见二.1） |
| 2 | 蓝军挑战 | **PASS** | 本轮独立视角切换产出 4 条挑战（见五），其中 BTR-4（压缩估算不扣保留文本）升级为 F-1（P2）——挑战有效且已有实测兜底 |
| 3 | 模块结构 | **PASS（不适用成立）** | 纯注入文本变更，无模块/依赖变更；单一事实源纪律增强——bootstrap 操作面收敛至 `adapters/dsh/AGENTS.md.template` 单点（L7-37），persona 只留身份+契约+指针，符合 ADR §9 可维护性声明 |
| 4 | 接口契约（注入契约） | **PASS** | 30/30 锚逐一对照在位：persona 15（`agent.cordis.yml.template` L49/L51/L55/L57-62 对照 verify_workflow.py L6758-6771 注册表：关键行为契约/复审必达/NEEDS_CHANGE/完成必推荐/task-priority-analysis/选项必带依据/审查结论必机录/review-record/真实环境必防护/三选一/逐条上报/隔离环境安装冒烟/三要素/推荐卡 + @version-line→L51「治理工作流（v0.91.0）」）+ SKILL.md 11 + behavior-protocol.md 3 + AGENTS.md.template 1（「关键行为契约」L23）——与 Coordinator 上报「4 files/30 anchors PASSED」完全吻合；PERSONA_PREFIX_FIRST_LINE 提取锚在位（persona L49 首行 = injection_budget.py L98 字面「You are a coding agent powered by」）；thin 11 锚全在位（L356/L357/L363/L364/L368/L369/L373/L374） |
| 5 | 非功能需求 | **PASS** | 预算验收达成：三档 PASS 且 strict 余量 391 ≥ 100（DEC-268(2)）；五安全不变量零弱化——persona L55 压缩行保留「行为灰度开关」marker + 五 marker（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达）+ 两开关 token；thin L358 三 token 钉在位；可逆性保持（模板与投影同 commit revert、投影幂等） |
| 6 | Bar Raiser 评审 | **PASS（单 agent 最低标准）** | 本 Reviewer 非实施者；结论在「实施为什么对 → 实施最可能哪里失败」框架切换后得出；4 条挑战含 1 条实质新发现（F-1——R0 亦未察觉的估算方法论缺口）；无否决 |

## 二、审查重点逐项结论（任务书 7 项）

**1. 候选 A 规格一致性 — PASS（含 R0 修复验证）**
- 保留面：L49 英文身份行（提取锚在位）✓；L51 Coordinator 身份+`__GOVERNANCE_REPO_ROOT__`+infra 绝对路径规则+版本行（v0.91.0 动态锚载体）✓；L57-62 关键行为契约块全文（5 条契约行逐字完整，14 契约锚全部载体于此）✓；L55 压缩单行含「行为灰度开关（FEAT-040）」marker + 五安全不变量 marker +「**安全语义不回退**」+ `GOVERNANCE_LEGACY_BEHAVIOR=1` 与 `behavior_profile: legacy` 两 token ✓——**R0 F-2 修复已落实**。
- 删除面：4 步操作面/SELF-CHECK 细则/模式确认细则/Agent Team 细则/hooks 升级命令行——persona 中确认全部不存在 ✓（操作性内容已由 `adapters/dsh/AGENTS.md.template` L7-37 完整承载）。
- 新增面：L53 第一动作硬触发器命令句（「每会话第一动作（bootstrap，fail-closed）：按工作区 AGENTS.md 注入面执行 resolve_entry → 热数据 → 首次交互」）——**R0 F-3 修复已落实**（命令句形态与 §8 BT-01 承诺一致）；L64 指针行含兜底句「注入面缺失或平台不支持工作区 AGENTS.md 注入时，加载 software-project-governance skill 获取同等规则；fail-closed 与安全语义不受本指针影响（DEC-080/RISK-038）」——**R0 F-7 机制边界缓解已落实**。新增合计 2 行，在 ADR「约 3 行内」预算内。

**2. 实施期两处口径裁定 — 均成立（约束驱动、语义等价、零契约弱化）**
- (a)「工作区 AGENTS.md 注入面」替代「agent-instructions 注入面」：**必要**——`test_verify_workflow.py` L21272 `assertNotIn("agent-instructions", persona)` 禁止 persona 文本含该字面量（守护 persona 提取面不回退为整文件读取）；ADR 示意原文若逐字实施必红测。**语义等价**——ADR §9（L227）机制边界明载「agent-instructions 注入 = 工作区 AGENTS.md 宿主自动注入」，实施措辞恰是 F-7 后的机制精确表述；指针目标、skill 兜底、fail-closed 声明三要素无损。
- (b) 指针行含字面「Git hooks 与升级」且置于契约块之后：**必要**——`test_review_machine_provenance.py` L239-241（`test_persona_contract_block_stays_within_budget`）：`start = text.index("关键行为契约")`、`end = text.index("Git hooks", start)`——契约块与后续「Git hooks」字面构成 2.5KB 预算块的边界分隔符；若删除该字面量，`.index` 抛 ValueError 即测试 ERROR。「置于契约块之后」是该测试语义的固有要求而非可选排布。**零弱化**——hooks/升级操作性指令完整保留于 AGENTS.md.template L35-37，persona 经 L64 指针+兜底句可达；契约块字节预算实测余量充足（粗估 ≈1.5KB ≤ 2560B）。

**3. 候选 B 规格一致性 — PASS**
- secondary-thin 压缩后（`commands/governance-init.md` L348-374，27 行）：ADR §3.2 锚清单 11/11 在位——SELF-CHECK（L361/L363）、AskUserQuestion（L364）、plan-tracker（L357/L363/L373）、§B0 指针（L364）、always-on（L368）、silent-track（L369）、evidence-log（L373）、verify_workflow.py（L373）、/governance（L374）、FIX-278 UTF-8 实质（L374）、主入口指针（L352/L359/L374）✓。B-a（SELF-CHECK 2 行/三检全保留）✓、B-b（模式确认 2 行，on-demand+silent-track 合一）✓、B-c（快速入口 2 行）✓。
- **L358 FEAT-034/040 行逐字未动** ✓：canonical 双副本（root L358 = e2e L358）与两投影（root AGENTS.md L13 = e2e AGENTS.md L13）四处文本一致；`GOVERNANCE_LEGACY_BEHAVIOR`/`behavior_profile`/「安全语义不回退」三 token 全在 L358——test_behavior_profile.py L282-292 四模板 token 钉满足；「行为灰度开关」marker 行未触碰。
- B-d（AGENTS.md.template L27-28 合一）：`always-on`/`silent-track` token 在位；模板结构完整（第一动作 5 步/灰度开关 L15-17/SELF-CHECK L19-23/模式确认 L25-28/Agent Team L30-33/hooks 升级 L35-37），「关键行为契约」锚 L23 在位；`validate_dsh_thin_pointer` 守护面机器确认（test L294-302 通过，Coordinator 上报）。

**4. 投影一致性 — PASS**
- root `AGENTS.md` 薄指针段（L3-29，27 行）== e2e `project/e2e-test-project/AGENTS.md`（L3-29）== canonical thin 渲染（`{PRIMARY_ENTRY}`→CLAUDE.md），逐行对照一致 ✓（「27 行」口径核实：薄指针段 L3-29）。
- 两个 `governance-init.md`（root/e2e，均 488 行）secondary-thin 区域 L345-389 逐行一致 ✓；文件总行数一致。
- 两个 CLAUDE.md 未变：canonical 三钉 4555/9553/10441 未动（字节级 canonical 不变）+ check-entry-bootstrap-sync 通过 + 双 CLAUDE.md 全文（宿主注入获得）结构内容一致且 @0.91.0——「幂等 SKIP」声明成立；薄指针段边界守护（test_verify_workflow.py L21400-21408 strict 块不含薄指针内容）在位。
- 预授权例外留痕确认：`.governance/incidents/FEAT-073-impl.log` 存在；`.governance/incidents/FEAT-073-preset-backup-20260928-105459/` 含 5 件（before/after/preset.yml/.dsh-bundle-version/skill-root.txt）✓。

**5. 字节钉 rebase 纪律 — PASS**
- `test_verify_workflow.py` L21441-21446：lightweight 4555 / standard 9553 / strict 10441 **三钉未动** ✓；secondary-thin 2859→2766 仅此一钉改动 ✓。
- FEAT-073 注释块（L21438-21440）格式对照 FEAT-040（L21424-21428）/FEAT-041（L21430-21436）先例一致（「old→new — 说明 + Same guard discipline: deliberate edit / never silently」句式）✓。
- 全文件 grep「FEAT-073」仅 1 处（L21438）——测试文件改动确为授权的一处 ✓。

**6. 越界检查 — PASS（有边界，见遗留项 1）**
- 7 文件之外零 tracked 修改：本角色 Bash 禁止无法独立运行 git status 复核，**采信 Developer/Coordinator 上报 + 全量测试绿（948 passed）间接佐证，标注未独立核实**。
- 测试文件仅授权一处（上述 grep 证实）；`.governance/` 零直写（incidents 两处为派发预授权例外，已核实存在）。

**7. 实测数字对账 — PASS（附 F-1）**
- 内部自洽精确成立：strict 5609 = 721+3111+798+979 ✓；standard 5337 = 721+2839+798+979 ✓；lightweight 3859 = 721+1361+798+979 ✓；分量 delta 与基线闭环：persona 1075→721（−354）、secondary 827→798（−29）、agent-instructions 978→979（+1）、entry 三档基座未动（strict 3111 不变）✓。
- 组合对账精确：ADR 估算余量 ≈574 − 实测 391 = 183 =（A：411−354=57）+（B：154−28=126）✓——差额完全可分解，无隐藏变化。
- A 侧实测 −354 落在 ADR 声明区间 [350, 480] 内（对 F-3 调整后点估计 366 亦在 ±12% 带内）——估算纪律达标。
- B 侧实测 −28 对估算 ≈154（带 115-190）**严重偏离**→ F-1（P2，ADR 估算侧修正，见四）。
- no-overclaim 标注：Coordinator 基线以实测口径呈现并注明与 Developer 上报一致性；DEC-268(2) 验收（391 ≥ 100）达成且由候选 A 独立承载——措辞无过度声明。

## 四、Findings 清单

| ID | 严重级 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| F-1 | P2 | ADR-020 §5.3（L144-148）/§3.2（L103）/§5.4（L157） | **候选 B 收益估算结构性高估 ≈5.5 倍**：估算 ≈154 tok（带 115-190），实测合计仅 −28（secondary −29、agent-instructions +1）。方法论根因：§5.3 候选 A 各行扣减了新增文本（−119），候选 B 各行**未扣减压缩后保留文本**——B-a「三检全保留」约束使保留行承载 ≈80% 原内容，B-d 两 bullet 合一仅省换行+短横（实测 +1 佐证）；字节钉 2859→2766（−93B）与实测 −29 tok 按 thin 面密度互证，测量自洽、估算失真。后果：「仅 B 达标（余量 ≈163）」论断被实测证伪（B 单独实施余量仅 ≈37，不满足 ≥100）；A+B 验收不受影响（391，由 A 承载） | ADR 增补实测修订注（§2/§5.3/§5.4 标注 B 实测 −28 与「仅 B 不达标」结论，实测取代估算——§5.2/§11 已有该优先级条款）；DEC/evidence 入账实测分量数字，防后续票引用 ≈154；方法论沉淀：压缩类候选一律按「净省 = 原值 − 重写值」计价 |
| F-2 | P3 | governance-init.md L382（root/e2e 双副本） | FEAT-037「完整 6 条→薄 5 条」SELF-CHECK 压缩映射枚举与现行薄指针 2 条布局不符（薄 3/薄 4/薄 5 编号悬空）——**先行漂移，非 FEAT-073 引入**（该映射与压缩前 3 条布局亦不符；本轮无法 git diff 确认引入轮次）；实质无损：完整 6 检全覆盖（1-3+6→薄 1，4+5→薄 2），carry-over 反而由「（含 carry-over）」就地承载，强于映射声明 | 后续文档 pass 顺手对齐该枚举（或并入 F-1 的 ADR 修订注一并说明）；不阻塞本票 |
| F-3 | P3 | agent.cordis.yml.template L53 | 第一动作硬触发器行无内联兜底尾（兜底句在 L64 指针行）——不支持工作区 AGENTS.md 注入的平台上，L53 字面读法悬空（与 ADR §3.1 示意形态一致，属 BT-04/BT-01 已登记残余的形态细节） | 可接受的登记残余；未来微编辑可在 L53 尾补「（缺失则按下句兜底）」，或在 DEC 记录明确两行合并解读口径 |

## 五、本轮独立蓝军挑战（视角切换后输出，与 ADR §8/R0 §四互补）

| 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---------|---------|---------|---------|---------|
| BTR-1 攻击者/预算回弹：persona 瘦身腾出的 391 余量被后续「合并类」编辑蚕食（B-d +1 即实证——合并操作可净增） | 低-中——hard gate 会拦截越界，但「贴线回归」摩擦成本高 | resident hard gate + 四钉字节级看护 | 低 | 无需新增；F-1 修订注中提示「合并≠省」 |
| BTR-2 维护者/术语别名漂移：persona 禁用「agent-instructions」字面（L21272）后，ADR/DEC 术语与 persona 表述分叉，未来维护者 grep「agent-instructions」定位 persona 指针将落空 | 低——可维护性摩擦，非正确性 | 术语对应关系目前只存在于本审查与 ADR §9 机制边界 | 低-中 | F-1 修订注中显式登记别名：「工作区 AGENTS.md 注入面 ≡ agent-instructions 表面（L21272 禁字面）」 |
| BTR-3 最愤怒用户/非 DSH 平台：L53 无内联兜底（见 F-3） | 低 | L64 兜底句 + BT-04/F-7 缓解 + 冒烟抽测承诺 | 低 | 见 F-3 |
| BTR-4 维护者/估算纪律系统性风险：§5.3 方法对一切「压缩类」候选系统性高估（本轮实测证伪）→ 未来 DEC 可能按失真估算排优先级 | 中——决策质量风险（非本票验收风险） | BT-03 实测兜底 + §5.2 实测优先条款已兜住本票 | 中（方法论不修则复发） | F-1 建议的净省计价法沉淀入 ADR 模板/审查 checklist |

## 六、硬门槛自检

| 门槛项 | 要求 | 实测 | 判定 |
|--------|------|------|------|
| 只读审查 | Write/Edit/Bash/子 agent/用户交互 全零 | 本轮仅用 Read/Grep/Glob；零写入、零命令执行、零子 agent、零用户交互 | ✅ |
| 事实锚定 | 引用带文件+行号；不可核实项标注 | 全部结论带行号；git status 复核/2741B 字节数等 4 项显式标注「未核实」（见九） | ✅ |
| 复审本质 | 逐条比对前轮 findings | R0 F-2/F-3/F-7（实施相关三条）逐条验证已落实（二.1）；F-1/F-4~F-6 为 ADR 文本侧处置，R0 修订版已核 | ✅ |
| 报告边界 | 不做最终决策 | 提交裁定权留 Coordinator | ✅ |

## 七、终态结论与理由

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

理由：7 个修改对 ADR-020 §3.1+§3.2 的规格落实为**逐面对照成立**——保留面/删除面/新增面/明确不动面全部按规格执行，R0 三条实施相关 findings（F-2/F-3/F-7）全部落实；实施期两处口径偏离经约束源测试逐行核实为**测试必然性要求**（L21272 禁字面 / provenance L239-241 分隔符），语义等价且零契约弱化；30/30 注入契约锚在位、三档预算实测达标（strict 余量 391 ≥ 100）、字节钉 rebase 纪律与先例格式一致、e2e 镜像与投影一致、越界零迹象。唯一 P2（F-1）指向 **ADR 估算方法论**而非实施缺陷：B 份额实测 −28 远低于估算 ≈154，但测量链自洽（字节钉互证）、验收由候选 A 独立承载、ADR 自身的「实测取代估算」条款覆盖该情形——修复动作是文档修订注 + DEC 记录，不要求改动任何实施产物。方案方向、安全语义、投影一致性、可逆性均无需变更。

## 八、证据清单（本轮 Read/Grep/Glob）

| 文件 | 位置 |
|------|------|
| docs/architecture/ADR-020-injection-budget-dedup-slimming.md | L1-289 全文 |
| docs/reviews/review-FEAT-073-R0.md | L1-98 全文 |
| agents/design-reviewer.md | L1-102 全文 |
| agent-presets/governance/agent.cordis.yml.template | L1-249 全文（persona prefix L48-64 逐行） |
| commands/governance-init.md | L192-221 / L270-409（基座+strict 差异段+secondary-thin L348-374+FEAT-037 L382） |
| project/e2e-test-project/commands/governance-init.md | L345-389（与 root 逐行一致；总 488 行） |
| adapters/dsh/AGENTS.md.template | L1-37 全文 |
| AGENTS.md（root）/ project/e2e-test-project/AGENTS.md | 全文（薄指针段 L3-29 双侧一致） |
| skills/.../infra/tests/test_verify_workflow.py | L21240-21299（L21272 禁字面）、L21385-21499（钉 L21441-21446/注释块/边界 L21400-21408）；grep secondary-thin（8 处）/FEAT-073（1 处）/agent-instructions（5 处） |
| skills/.../infra/tests/test_review_machine_provenance.py | L175-294（L227-244 分隔符预算测试；L211-225 persona review-record 锚） |
| skills/.../infra/tests/test_behavior_profile.py | L266-305（token 钉 L282-292/DSH 方言 L294-302） |
| skills/.../infra/verify_workflow.py | L6728-6792（INJECTION_CONTRACT_ANCHORS 注册表 30 锚） |
| skills/.../infra/checks/injection_budget.py | grep PERSONA_PREFIX_FIRST_LINE（L98/L370） |
| .governance/incidents/ | glob：FEAT-073-impl.log + FEAT-073-preset-backup-20260928-105459/（5 件） |

## 九、遗留不确定项（未核实项与原因）

1. **「7 文件之外零 tracked 修改」**：Bash 禁止无法运行 git status 独立复核——采信 Developer/Coordinator 上报 + 948 passed 全量绿间接佐证；建议 Coordinator 提交前以 git status 终验一次。
2. **投影字节数 2741B**：无法实测字节数；「27 行」已核实（薄指针段 L3-29）；字节口径由 canonical 钉 2766 + check-projection-sync 机器看护，低风险。
3. **测试运行声明（948 passed/139 subtests、290s）**：本角色未复跑（命令禁止）；check-injection-contract PASSED（4 files/30 anchors）与我的 30 锚逐一人工对照完全吻合，交叉印证成立。
4. **F-2 的引入轮次**：L382 映射枚举漂移无法 git 归因（命令禁止）；按「与压缩前布局亦不符」判定为先行漂移，非本票引入。
5. **真实环境零写入声明**：本任务无真实环境操作面；incidents 留痕（log + 备份 5 件）存在性已核实，其内容正确性未逐一审阅（属 R4 过程证据，非本设计审查标的）。
