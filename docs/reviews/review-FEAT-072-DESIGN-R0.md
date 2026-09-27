# FEAT-072 DESIGN-R0 独立审查报告（规则/架构面）

- **审查对象**: commit `196894a`（单一目的 commit：6 files +102/−6）
- **任务**: FEAT-072 完成必推荐三要素推荐卡契约
- **审查基准**: DEC-266（六项裁决，设计已冻结——本审查=实现忠实度与质量验证，非重新设计）
- **审查轮次**: R0（首轮）
- **Reviewer**: Design Reviewer Agent（独立，未参与实现）
- **日期**: 2026-09-27

---

## 结论

**APPROVED_WITH_NOTES** ｜ unresolved_blockers=0 ｜ P2×1，P3×2，无 P0/P1。

实现忠实于 DEC-266 六项裁决；五项机检亲跑全 PASS；预算申报数字与实测精确一致；范围纯粹无夹带。发现均为治理登记面滞后项，不阻断本 commit。

---

## 1. 裁决忠实度（DEC-266 六项逐条）

### (1) 落点与三行卡固定标签 — PASS
- `behavior-protocol.md` L588-599：6b 重写为「推荐下一步（FEAT-072/DEC-266）」三子弹，6c 重写为「呈现并确认」七子弹+session-snapshot 投影行；**无 6d 新增**（6d「不得直接结束」保留原文）。
- L593 卡片正文固定三行标签精确为「`服务目标：`／`解决问题：`／`方案要点：`」（read 逐字核实），第三行内子标签「`依赖理由：`」——与 DEC-266(1) 逐字一致，未采纳四行卡 ✓。

### (2) 面范围 — PASS
- ask 前正文卡 MUST：L593「MUST 在调用 AskUserQuestion 前的消息正文中……呈现一张三要素推荐卡」✓。
- session-snapshot 轻量投影 SHOULD：L599 格式 `{任务标识/短名}｜目标：…；问题：…；方案：…｜依据：{RECO 引用}｜待澄清：{如有}`，含「复用已生成卡不重新研究」与「不得把旧 RECO 当作当前状态」（对应验收矩阵跨会话条款）✓。
- bootstrap next_actions 不纳入 + 边界句：L599「bootstrap next_actions 不纳入本投影；next_actions 原文进入完成推荐交互时仍须遵守本条（6c）」✓。

### (3) 注入面投影（无规则分叉） — PASS
- persona L68 / SKILL.md L230 / interaction-boundary.md L193 三处压缩投影均携带：task-priority-analysis fail-closed、正文三要素推荐卡、依赖理由、依据缺失明示不编造、DEC-143 短选项确认、空推荐结构化原因、MUST NOT 直接结束会话——与 canonical（behavior-protocol.md L588-599）语义一致，压缩无分叉。
- L558 关键词同步清单已追加「依赖理由／三要素／推荐卡」（精确读取核实），并载明「step 6c 经 FEAT-072/DEC-266 升级为三要素推荐卡呈现……DEC-143 基线不变」✓。

### (4) 机检锚 — PASS
- `verify_workflow.py` INJECTION_CONTRACT_ANCHORS：persona 与 SKILL.md 两面各增「三要素」「推荐卡」；新增 canonical 条目 `behavior-protocol.md` 检三完整标签「服务目标：/解决问题：/方案要点：」existence-only。
- `check_injection_contract()` 函数本体**零改动**（L6871-6913 对照 diff 确认）——文件缺失→issue、锚缺失→issue、VERSION_LINE_ANCHOR 动态解析 fail-closed 语义全部保持 ✓。亲跑：**4 面 / 30 锚 / PASSED**（与 EVD-1204 声明一致）。

### (5) 防编造三态降级 — PASS
- L594 三态精确为「未载明／来源不可用／依据冲突」，含「依据缺失：{字段}未载明（已查：{可定位来源}）」标注格式与「MUST NOT 将推测写成既定目标、问题或方案」✓。
- 澄清不豁免：L597「缺失信息会影响范围、执行路径或风险判断时，MUST 明示『执行前需澄清』……『自主执行推荐项』不得豁免该要求」✓。
- 空推荐不虚构：L598「推荐为空时 MUST NOT 提供不存在的推荐项或『自主执行推荐项』……MUST NOT 直接结束会话」✓。
- 分析失败 fail-closed 保留：6a（L588-589）未被本 commit 触碰，「工具缺失或失败时按 fail-closed 处理并升级，不得跳过分析」原文保持——卡片不构成占位绕过路径 ✓。

### (6) 批序与登记一致性 — PASS（附 P2-1/P3-1 登记滞后项）
- evidence 面：EVD-1204（机录 evidence-append）+ TRIAGE-FEAT-072（机录 change-triage）均在案，申报字段与实测一致（见 §3/§4）✓。
- plan-tracker L280 0.91.0 版本行批序仍为立项时快照「FIX-399→FEAT-072」，与 DEC-266(5)「FEAT-072→FIX-399（替代原 FIX-399 先序）」方向相反——陈旧快照未回填，DEC-266 为权威可消解矛盾，但后续会话若只读 plan-tracker 会拿到反序指令 → **P2-1**。
- plan-tracker L81 优先级一览 FEAT-072 行状态「🆕 入账」滞后于实际交付态（EVD-1204 已机录）→ **P3-1**（终态写回时同步即可）。

## 2. 机检实现质量 — PASS
- 亲跑 `check-injection-contract`：`Files checked: 4; anchors: 30` → PASSED。新增锚未破坏既有 check 语义（函数零改动，dict 纯 additive）。
- 负例测试判别力核查（`test_injection_contract_three_element_card_anchors`）：
  - 真实 FAIL 而非恒真：temp root 复制全部锚面 → baseline `issues==[]` 断言 → 逐一 `str.replace(锚, "")`（全量替换）→ 断言 issue 同时含文件路径与锚名；
  - 判别力前提亲证：persona「推荐卡」仅 L68 一行、SKILL.md「三要素/推荐卡」仅 L230 一行、canonical「方案要点：」仅 L593 一行（grep 全文各 1 match）——移除必 FAIL；
  - issue 格式亲证：实现 L6908 `f"{relative}: anchor missing: {anchor}"` 与测试断言匹配。

## 3. 测试充分性 — PASS
- 亲跑 `python -m unittest skills/software-project-governance/infra/tests/test_dsh_adapter.py -v`（repo 根）：日志 L140 `Ran 54 tests in 19.874s`、L142 `OK`、exit 0——与申报「Ran 54 OK」一致；新测试在套件中执行（verbose 清单在案）。53→54 与 +1 测试方法吻合。

## 4. 预算事实 — PASS（申报如实）
- persona 净增字节实测：`git show 196894a^` vs `196894a` 全文件 15153→15229 = **+76 B**，与申报「净增+76B（≤~150 编辑目标）」精确一致 ✓。
- 亲跑 `check-injection-budget` 三档：lightweight 4241/6000 PASS；standard **5719/6000 PASS**；strict **5991/6000 PASS**（余量 9 tok）——与 EVD-1204 记录逐字一致，strict 档余量 9 tok 的「已知边界」披露属实（M-0 披露+0.92 候选池登记路径已在案）。

## 5. 范围纯粹性 — PASS
- diff 恰好 6 文件（`git show --name-only` 计数=6），与 triage `FEAT-072.json` files 六项一一对应，无夹带。
- `project/e2e-test-project/**` 未被本 commit 触碰（name-only 过滤 e2e 零输出）；目录存在（Test-Path=True）。**desync 中间态披露确认**：该目录为 version-projections 声明面预期 desync，由 M-1 release-projection 统一再生——按审查口径不判缺陷，留 M-1 兑现核验项。

## 6. 交叉引用与 manifest — PASS
- 亲跑 `check-cross-references`：No dangling / No deprecated / No circular → PASS。
- 亲跑 `check-manifest-consistency`：Canonical 943 / Actual 1093 → PASS。

---

## 蓝军挑战（3 条独立挑战与缓解）

| # | 挑战 | 缓解/现状 |
|---|------|----------|
| RB-1 | 锚为 existence-only，契约正文可被改写而锚仍在 → 机检不拦语义漂移 | 设计边界自洽（existence-only 是 FIX-272/FEAT-010 显式边界，行为面归 REQ-107/108/113）；三处注入面措辞已逐字对照无分叉；后续语义漂移依赖复审链人检——已知边界，不构成本票缺陷 |
| RB-2 | strict 档余量仅 9 tok，下一票任何 persona 触碰即撞硬门 | 已如实披露并入 0.92 候选池；DEC-266(3) 已预定超限处置序（先压缩重复表达→瘦身 diff 讨论→禁擅删强制行为/既有锚/禁提上限）——缓解路径在案 |
| RB-3 | plan-tracker 陈旧批序行（P2-1）误导后续会话按 FIX-399 先序开工 | DEC-266 行自身明示「替代原 FIX-399 先序」，权威裁决可消解；建议 Coordinator 终态写回时同步勘正 L280/L81（见下） |

## 发现清单

- **P0（阻断）**: 无
- **P1（重要）**: 无
- **P2（建议）**
  - **P2-1** plan-tracker.md L280：0.91.0 版本行批序「FIX-399→FEAT-072」与 DEC-266(5) 裁决「FEAT-072→FIX-399（替代原 FIX-399 先序）」相反。属 DEC-265 立项快照未随 DEC-266 回填的登记滞后，非产品文件缺陷。建议：Coordinator 终态写回时勘正该行批序表述（引用 DEC-266 为权威），避免后续会话按反序执行。
- **P3（备查）**
  - **P3-1** plan-tracker.md L81：FEAT-072 优先级一览行状态「🆕 入账」滞后于 EVD-1204 已机录的交付态。建议终态写回时同步任务行状态列。
  - **P3-2** persona 压缩面未携带「三态降级」词面（仅「依据缺失明示、不编造」语义主干）——投影语义一致性已核实、无规则分叉，仅备查：canonical 三态语义后续演进时，persona 短语是否需随动由该次变更评审判定。

## 亲跑命令与结果摘要

| 命令（repo 根） | 结果 |
|----------------|------|
| `verify_workflow.py check-injection-contract` | 4 files / 30 anchors → **PASSED** |
| `verify_workflow.py check-injection-budget`（lightweight/standard/strict 三档） | 4241 / 5719 / **5991** tok ≤ 6000 → **PASSED ×3** |
| `python -m unittest skills/software-project-governance/infra/tests/test_dsh_adapter.py -v` | **Ran 54 tests in 19.874s — OK**（exit 0；含新测试） |
| `verify_workflow.py check-cross-references` | dangling/deprecated/circular 全无 → **PASS** |
| `verify_workflow.py check-manifest-consistency` | Canonical 943 / Actual 1093 → **PASS** |
| `git show 196894a` / `git show 196894a^:…` 字节对比 | 6 files +102/−6 确认；persona 15153→15229 = **+76B** |

**未完成验证项**: 无（六项审查清单全部完成；单测试方法隔离重跑因 unittest 路径参数形式限制未执行——全量套件 OK 已覆盖该测试，不影响结论）。

---

## 复审须知（若 Coordinator 转 NEEDS_CHANGE 场景）

本报告为 R0。若 P2-1 处置方式被裁定为须改产品文件（当前裁定为治理登记面、不改产品文件），复审时 MUST 逐条比对 P2-1/P3-1/P3-2 修复状态并声明 round 号。
