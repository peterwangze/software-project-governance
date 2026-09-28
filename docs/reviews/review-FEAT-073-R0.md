# 设计审查报告 — FEAT-073 R0（ADR-020：strict 注入预算去重瘦身方案）

- **Round**: R0（首轮审查）
- **审查对象**: docs/architecture/ADR-020-injection-budget-dedup-slimming.md（266 行全文读入，未抽样）
- **日期**: 2026-09-28
- **审查人**: Design Reviewer Agent（独立于 Architect 作者；本报告同时承担 tech-review Bar Raiser 单 agent 最低标准——结论在「为什么对 → 最可能哪里失败」框架切换后得出）
- **审查类型**: 设计/架构审查（ADR 验证——阶段 1 研究产出，零实施）

## 一、六维度逐项结论

| # | 维度 | 结论 | 依据摘要 |
|---|------|------|---------|
| 1 | 方案完整性 | **PASS** | 候选 A/B 触及不同文件面、可独立实施（A=agent.cordis.yml.template prefix 块；B=governance-init.md secondary-thin 模板 + AGENTS.md.template L27-29），另有 5 个被排除备选（A'/B'/B2/直接抬限/宿主口径转正）；评估标准预定义（DEC-268(2) 验收指标 + §7 契约红线）；§5.3 溯源表逐项含手工原值/校正值/溯源位置。B'/B2 排除论断经本轮逐行核实为真（见二）。附 F-1（组合数字不自洽，P2） |
| 2 | 蓝军挑战 | **PASS** | ADR §8 BT-01~05 五条独立 ID 均配具体缓解；逐条可执行性核实：BT-04 兜底句确实存在于 §3.1 示意文本；BT-05 三档实测与 DEC-268(2) 一致；BT-02 的 guard 粒度差属实（verify_workflow.py L6913 对 persona 整文件 read_text 断言，而预算只计 prefix 块）。附本轮独立互补挑战 F-2/F-3/F-7 |
| 3 | 模块结构 | **PASS（不适用成立）** | 纯注入文本文档级瘦身，无模块变更；守卫依赖单向（verify_workflow → checks/injection_budget、sync_entry_projection、behavior_profile）无环；候选 A 收敛 bootstrap 操作面到 AGENTS.md.template 单一维护点，符合 P-v1 P5/D4 |
| 4 | 接口契约（注入契约） | **PASS** | persona 15 锚（14 契约锚 + @version-line 动态锚，verify_workflow.py L6758-6772）逐一核对全部位于保留行 L51/L66-71；拟删行 L53-57/L61/L62/L64/L73-74 逐行核对不含任何 persona 契约锚；thin 生成方言锚核对：AskUserQuestion（L364，B-a 范围内——B-a 保留锚清单已含）、.governance/evidence-log.md（L375，B-c 范围内——B-c 保留锚清单已含）、always-on/silent-track（L369/L371，B-b 保留承诺与锚位吻合）；AGENTS.md 方言锚中 # Governance Bootstrap(L1)/ask_user_question(L22,L34)/software-project-governance(L9)/关键行为契约(L23)/行为灰度开关(L15-17) 均不在 B-d 触及面 L27-29 内 |
| 5 | 非功能需求 | **PASS** | 性能（余量估算 + resident hard gate fail-closed 防回弹，injection_budget.py L187-192 核实 gate=hard）；安全（五不变量 §7.2 逐条零触碰声明——五 marker 现行确在 persona L59 一行承载，压缩保留承诺成立；guard 粒度差主动披露并给出加固路径）；可维护性/可扩展性/可逆性均有对应方案（单 commit revert + 投影幂等 sync_entry_projection.py L16-18 核实）。附 F-2 |
| 6 | Bar Raiser 评审 | **PASS（单 agent 最低标准）** | 本 Reviewer 非作者 agent，独立完成视角切换序列并输出 ≥3 条设计方未列的挑战（F-1~F-3/F-7 即切换框架产物）；无否决——所有挑战均有明确解除路径且不动摇方案方向 |

## 二、审查重点逐项核实结果（Coordinator 任务书 5 项）

1. **§3 候选完整性**：✅ 成立。A/B 两候选独立可实施；§5.3 溯源表逐项核对格式完整；抽样复算（persona L59 手工清点粗算 ≈98-105 tok vs 报 110、A 净收益 530−119=411、B 176×0.88≈154、仅 A 5991−411=5580、standard/lightweight 同减 411 与共享表面归因逻辑自洽）量级一致。附 F-1（A+B 行与分量之和差 21 tok）。
2. **§6 排除理由（测试钉真实性）**：✅ 全部属实——本轮亲读 test_verify_workflow.py 逐行核实：
   - L9887-9888：`tpl.count("呈现升级待处理")==2`（注释 # trigger + footer）+ `tpl.count("用户未响应前零写操作")==2` → B2 否决论断为真；governance-init.md L288（trigger）/L290（footer）双写实存。
   - L9890：`tpl.count("版本升级写序列属推进类动作")==1` → 为真。
   - L9915：`assertIn("DEC-207② P2-1 / M5.5 条 3", init)` → 为真。
   - L9930-9933：插件残留清理删除面三 needle 对 governance+init 双面断言 → 为真。
   - L9816-9826：归档 Step E required needles 对 governance+init 双面断言 → 为真（注：required 列表实为 7 项非「四 needle」→ F-4，P3，方向不变）。
   - 「≥4 个测试族」计数属实：test_governance_scenario_c_matches_continuous_archive_step_e(L9811) / test_init_templates_present_pending_upgrade_and_zero_write(L9872) / test_upgrade_write_sequence_deep_check_linkage(L9900) / test_upgrade_cleanup_deletion_surface_dual_entry_aligned(L9919)。
   - B'/B2 的设计意图判断（升级确认门 FEAT-035 安全不变量的操作化载体）与测试 docstring（L9834-9844/L9872-9880/L9900-9907/L9919-9926）一致。
3. **§7 锚矩阵无遗漏**：✅ 覆盖准确。persona 14+1 锚（L6758-6772 逐锚核对）；AGENTS.md 锚组 = verify L6788 [关键行为契约] + 共享核心 7（sync_entry_projection.py L67-75）+ DSH 方言 3（L87-91）+ 灰度开关（L101）；六发布面（behavior_profile.py L168-175）；五安全不变量（L121-152，marker 与 statement 逐条对照）；四模板 token 钉（test_behavior_profile.py L282-292 对 lightweight/standard/strict/secondary-thin 断言 ENV_VAR/PLAN_TRACKER_KEY/安全语义不回退）。附 F-6（SKILL.md 11 锚 / behavior-protocol.md 3 锚未显式列零触碰行，P3）。
4. **§8 蓝军缓解可执行性**：✅ 五条缓解均具体可操作；引用的 check-dsh-preset-smoke（verify_workflow.py L7006）、check-dsh-preset-compat（L25512-25514）、test_dsh_contract config_keys=["prefix"]（test_dsh_contract.py L1390）、validate_dsh_thin_pointer（sync_entry_projection.py L286）全部实存。附 F-3（BT-01 缓解承诺与 §3.1 新增示意文本不匹配，P2）、F-7（BT-04 未覆盖机制级共现差异，P3）。
5. **Coordinator 补充重点**：
   a. **persona↔agent-instructions 结构性共现**：✅ 成立（候选 A 基础牢固）。persona prefix 块（L48-74）与 agent-instructions 组件（L76-79）同在 agent.cordis.yml.template；AGENTS.md.template 经 launch.py（L84 BOOTSTRAP_TEMPLATE）渲染为工作区 AGENTS.md 由 DSH 宿主自动注入，两面由同一适配层单次装配（--install/--sync）交付。六对重复内容逐对核实为真（第一动作/灰度开关/SELF-CHECK/模式确认/Agent Team/hooks 升级）。附 F-5（「两行同在 L45-79」措辞不精确——agent-instructions 内容源不在 preset 文件内，P3，结论不变）。
   b. **估算方法论 no-overclaim**：✅ 达标。×0.88 校正系数依据已披露（persona 清点 2722 chars/716 CJK vs 实测 2381/636，系统性偏高 ≈13%）；±12% 区间声明；§11 明确「零实施、零预算恢复、全部为估算、实测取代估算」。新增项 −119 未乘校正属保守方向（净收益下界），可接受。
   c. **路线 D「不推荐」论证闭合**：✅ 成立。injection_budget.py L15-20 与 L266-278（tokenizer_calibration 「why」字段）均明载宿主口径对 CJK 低估 3-4 倍；用它转绿即「为转绿抬限」的换名——论证成立。DEC-266(3) 顺序约束（decision-log.md L208）与 arch target 4K（L76 注释）引用准确；重定标前置门槛即 DEC-268(2) 原文（decision-log.md L210 核实一致）。
   d. **回弹归因标注**：✅ 恰当。EVD-1104 基线（injection_budget.py L44-45：4,216/5,694/5,966）与 prompt 实测（4241/5719/5991）三档差额一致 +25；「共享表面推断」已显式标注待验证且 §10.5 配归因小票——推断/实证边界清晰。

## 三、Findings 清单

| ID | 严重级 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| F-1 | P2 | ADR §5.4（L154）/§2（L52） | A+B 组合值不自洽：仅 A ≈5580 + 仅 B ≈5837 − 5991 = 5426（余量 ≈574），报告值 ≈5447（余量 ≈553）差 21 tok，无解释；违反本 ADR「数字可溯源」的自我要求。两口径均满足 ≥100，不影响结论方向 | 修正 §5.4 A+B 行为分量之和（≈5426/≈574）或注明差异来源（如保守折扣），§2「约 550」同步对齐 |
| F-2 | P2 | ADR §3.1 L68（保留规格） | persona L59 压缩改写的保留清单（marker + 五安全不变量 marker + 安全语义不回退）缺 **GOVERNANCE_LEGACY_BEHAVIOR=1** 与 **behavior_profile: legacy** 两个 token——现行 L59 承载的开关操作指引。Step7 token 钉测试（test_behavior_profile.py L282-292）不覆盖 persona，丢弃不会红测，但用户失去拨开关的具体拼写指引，与 §7.2「压缩不弱化」自我声明不一致 | §3.1 保留规格显式补入两 token；实施时 check-injection-contract 之外自查压缩行含完整开关句 |
| F-3 | P2 | ADR §3.1 L73-74 与 §8 BT-01（L206） | BT-01 缓解承诺「首动作仍以命令句形态出现于 persona」，但 §3.1 新增示意文本只有指针（「按本 preset 的 agent-instructions 注入面执行……」）无第一动作硬触发命令句——缓解承诺与改动规格不匹配，实施者按示意文本执行则 BT-01 风险敞口 | §3.1 新增文本补一行硬触发器（示意：「每会话第一动作（bootstrap，fail-closed）：按 agent-instructions 注入面执行 resolve_entry → 热数据 → 首次交互」），或修订 BT-01 措辞与规格一致 |
| F-4 | P3 | ADR §6 B' 行（L163） | 「归档 Step E 四 needle 须在 init（L9816-9826）」——required 列表实为 7 项（L9816-9824：持续归档触发检测与执行/plugin_home/migrate --dry-run/migrate/check-archive-integrity/发布收尾阻断/无可归档数据）。计数不准但方向不变（实际钉得更死） | 「四 needle」改「7 项 required needles」 |
| F-5 | P3 | ADR §1.3 L42/L46 | 「两行同在 agent.cordis.yml.template 组合内（L45-79），共现由构造保证」措辞不精确：L76-79 仅为 agent-instructions 组件声明（maxBytes: 65536），其内容源是 adapters/dsh/AGENTS.md.template（launch.py L84/L145-168 渲染为工作区 AGENTS.md 后由宿主注入）。共现在「同一适配层单次装配」层面成立，结论不变 | 措辞修正为「两面同属 governance preset 的适配层交付物（launch.py --install/--sync 单次装配同时交付 persona prefix 与 AGENTS.md 投影），共现由装配构造保证」 |
| F-6 | P3 | ADR §7.1（L174-182） | 锚矩阵未显式列出 INJECTION_CONTRACT_ANCHORS 另两面：SKILL.md（11 锚，verify L6773-6781）与 references/behavior-protocol.md（3 锚，L6785-6787）——两候选确实零触碰，但矩阵以「无遗漏」为目标宜显式声明 | 矩阵补一行「SKILL.md 11 锚 + behavior-protocol.md 3 标签锚——两候选零触碰」 |
| F-7 | P3 | ADR §8 BT-04（L209）/§9 | BT-04 只覆盖「用户本地删改」导致的指针悬空，未覆盖机制级差异：persona 注入=preset 装配（system prompt 位置），agent-instructions 注入=工作区 AGENTS.md 宿主自动注入（workspace instructions 机制）——非 DSH 宿主复用该 preset 时后者机制不存在。兜底句（加载 skill）仍兜底，残余风险低 | BT-04 缓解句补「（或平台不支持 agent-instructions 注入时）」，§9 影响范围注明该假设的机制边界 |

## 四、本轮独立蓝军挑战（与 ADR §8 互补；视角切换后输出）

| 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---------|---------|---------|---------|---------|
| 若实施者按 §3.1 示意文本逐字执行，persona 失去第一动作命令句（F-3） | 中——bootstrap 先行率下降，异常会话不 fail-closed | BT-01 抽测+回滚为二次防线 | 中（规格修复后转低） | 规格内补硬触发器行（见 F-3） |
| 若组合预估被直接引用进 DEC/验收承诺（F-1 的 553 与 574 两口径并存） | 低——均满足 ≥100，但数字打架损耗 no-overclaim 信誉 | BT-03 实测兜底 | 低 | 分量复算修正（见 F-1） |
| 若压缩行丢开关 token（F-2），legacy 回退通道对用户变为不可操作（说「有开关」不说「开关在哪」） | 低-中——仅可操作性，非安全语义 | 五 marker 测试不覆盖此 token → 无自动防线 | 中（规格修复后转低） | 保留清单补两 token（见 F-2） |

## 五、硬门槛自检

| 门槛项 | 阈值 | 实测 | 判定 |
|--------|------|------|------|
| 候选方案数 | ≥2 | 2 个主候选（A/B）+ 5 个排除备选 | ✅ |
| ADR 关键字段完整 | 100% | 日期(L3)+背景(§1)+决策建议(§2)+备选方案(§3-4)+排除理由(§6)+影响范围(§9)+后续动作(§10) = 7/7 | ✅ |
| 蓝军挑战条数 | ≥3 独立 ID | BT-01~05（5 条，均配缓解） | ✅ |
| 模块循环依赖 | 0 | 不适用成立（无模块变更）；守卫依赖单向无环 | ✅ |
| Bar Raiser 评审完成 | 已执行 | 本 Reviewer 独立执行（非作者、框架切换、独立结论，见四） | ✅ |

## 六、终态结论与理由

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

理由：ADR-020 的全部核心论断经本轮逐行核实为真——结构性共现成立（候选 A 基础牢固）、4 个测试族钉住论断属实（B'/B2 排除理由可复现）、锚矩阵覆盖准确（15+11+7+3+1 锚逐一对照）、路线 D 不推荐论证闭合（计量器自述 3-4x 低估 + DEC-266(3) 顺序 + arch target 4K 三重支撑）、no-overclaim 声明到位（估算/实测边界、推断/实证边界、决策权边界三清）。7 条 findings 无一为设计级缺陷：F-1 是数字自洽性修订、F-2/F-3 是实施规格补全（不修复将在实施票产生真实缺口，建议随实施票必改）、F-4~F-7 为措辞/完备性 P3。方案方向、安全语义、可逆性、验收路径均无需变更。F-2/F-3 建议在用户裁决前随 ADR 一并补正（Architect 动作，非本角色）。

## 七、证据清单（本轮 Read/Grep）

| 文件 | 位置 |
|------|------|
| docs/architecture/ADR-020-injection-budget-dedup-slimming.md | L1-266 全文 |
| agents/design-reviewer.md | L1-102 全文 |
| infra/tests/test_verify_workflow.py | L9800-9959（4 测试族+双写钉+needle 断言） |
| infra/verify_workflow.py | L6720-6929（INJECTION_CONTRACT_ANCHORS/check_injection_contract）；grep check_dsh_preset（L7006/L25512/L26301） |
| infra/checks/injection_budget.py | L1-120（口径/EVD-1104/预算常数/PERSONA_PREFIX_FIRST_LINE）、L121-295（表面表/tier policy/estimate/tokenizer_calibration）、L340-419（prefix 提取） |
| agent-presets/governance/agent.cordis.yml.template | L40-164（persona prefix 块逐行 + agent-instructions 组件声明） |
| adapters/dsh/AGENTS.md.template | L1-38 全文 |
| commands/governance-init.md | L280-389（基座 Step1.5 双写 L288/L290、strict 差异段、secondary-thin L347-379、FEAT-037 保留清单 L386） |
| infra/sync_entry_projection.py | L1-175（幂等/方言锚 L67-101/strict 组合 L159-164）；grep validate_dsh_thin_pointer（L286） |
| infra/behavior_profile.py | L85-184（五不变量 L121-152/六发布面 L168-175/marker L165） |
| infra/tests/test_behavior_profile.py | L225-309（发布矩阵 L237-256/marker L275-280/token 钉 L282-292） |
| .governance/decision-log.md | L200-211（DEC-265~269：授权链/DEC-266(3)/DEC-267(2)/DEC-268(2)/DEC-269③） |
| SKILL.md | grep resolved_root_ok（L217 fail-closed 叙述实存） |
| infra/tests/test_dsh_contract.py | grep config_keys（L1390 ["prefix"] 断言实存） |

## 八、遗留不确定项（未核实项与原因）

1. **手工清点逐 token 精确值**（§5.3 各项）：Bash 禁止无法跑计量器复算，仅抽样验证量级一致（persona L59 粗算 ≈98-105 vs 报 110，±10% 内）。ADR 已声明最终以实施 PR 双档实测为准（BT-03 承接）——可接受残余。
2. **Coordinator 实测基线**（4241/5719/5991 + sha）：Bash 禁止未独立复跑；采信任务书实测并与 injection_budget.py L44-45 EVD-1104 基线原文交叉印证（差额 +25×3 一致）。
3. **validate_dsh_thin_pointer 函数体精确终点**：起点 L286 已核实、下一函数 L306，推断范围 L286-303 与 ADR 引用一致；未逐行读函数体（对结论无影响——该引用仅用于 A' 排除论证的守护面存在性）。
