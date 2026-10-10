# Code Review FEAT-093 — R1 复审（返工验证轮）

- **Task**: FEAT-093（P1，0.98.0「可信有界执行内核」首票，DEC-330）
- **Reviewer**: 同一 Code Reviewer Agent（R0 即本审查者，口径一致）
- **Round**: R1（前轮 R0 = NEEDS_CHANGE；机录 `.governance/review-FEAT-093-R0.md`，prev_report=docs/reviews/review-FEAT-093-CODE-R0.md）
- **日期**: 2026-10-10
- **复审对象**: R0 返工变更（声称修改面：authority_ledger.py 1400→1555 / references 62→63 / test_verify_workflow.py 25522→25841〔+9 测试新类〕/ .governance/incidents/FEAT-093-r4-commands.log）
- **复审依据**: 前轮报告全文重读 + 机录 + 返工后 authority_ledger.py 全量重读（1555 行）+ 新测试 9 条全量实读 + 独立行为探针（%TEMP%，含 R0 探针原样复现与修正后的原子性探针）+ 三硬门槛本机复现

---

## 一、结论

**APPROVED_WITH_NOTES**（unresolved_blockers = 0；P0=0 / P1=0 / P2=0；新备注 P3×2）

R0 全部 12 项发现（P1-1 / P2-1 / P2-2 / P3-1~9）**逐条验证为已修复**，修复质量高：批内身份契约以模拟折叠闭合且经本审查者独立探针验证（整批拒绝+恰 1 审计+合法伴随事件零落盘+重载完好+旧 ID 批内冻结）；拒绝路径公开面与 raw `transact` 面同口径闭合、无绕过面；9 条新测试与 R0 探针逐一同构且断言真实（拒绝+审计+零落盘+持久重载），RED 实证诚实披露（7F+1E/9，P3-4 预存分支即绿=补测非修洞，与本审查者 R0 判断一致）。三硬门槛全部本机复现通过。两处 P3 级新备注（非阻断）：模拟折叠与真实折叠的双实现漂移看护、批内冲突审计事件的 `existing_anchor` 语义注记。

---

## 二、R0 发现逐条处置标注表

| R0 发现 | 级别 | 处置 | 验证依据（一手） |
|---------|------|------|------------------|
| P1-1 批内身份契约缺口 | P1 | **已修复** | 代码 `authority_ledger.py` L633-690 `_check_batch_identity`（批内模拟折叠：register 冲突→`_refuse_identity_conflict`；supersede old 未注册/new 已注册（含批内先序）→拒；state_changed 未注册→拒）+ L692-708 `_refuse_identity_conflict`（嵌套事务落审计后 raise，业务事件零落盘）。**独立探针**：A=同批双锚→拒绝+恰 1 `identity_conflict_rejected`+未注册+重载 integrity ok；B2=混合批〔合法注册+冲突+合法翻转〕→整批拒、delta 仅 1 审计、合法 FEAT-920 未注册、正身锚完好；B3=supersede+旧 ID 批内换义→拒、重载后旧锚冻结；G=重复冲突尝试每次恰 1 审计（attempt 级）、锚不变、integrity ok。新测试 3 条（L25634-25766 区）同构复现且含不过度拒绝面（同锚幂等/批内 register→flip→supersede 链合法/批内 new-id 撞车拒） |
| P2-1 未注册 id 状态事件接受后静默丢弃 | P2 | **已修复** | 代码 L776-802（公开面 `unknown_task_id` 结构化拒绝，零事件落盘）+ `_check_batch_identity` L683-690（raw 面同口径）。探针 D：公开面 refused/unknown_task_id；raw 面 raise ✓。测试 L25768-25794 双面断言+注册后放行 |
| P2-2 幻影 supersede | P2 | **已修复** | 代码 L834-840（old 必须已注册）+ 批内分支 L666-674。探针 E：公开面 refused/unknown_task_id；raw 面 raise ✓；注册 old 后同调用成功。测试 L25796-25822 |
| P3-1 开关 invalid 语义文档与代码不符 | P3 | **已修复** | docstring L894-903「REPORTED by the arm that saw it — no further arm is consulted」、references L46「由所见臂即报 invalid 返回（不咨询下一臂）」、测试注释同步改——三处一致且与代码（L917-919 立即返回）相符；测试 test_p3_6 附 invalid 节内外断言 |
| P3-2 「逐字节不变」措辞精度（stdout 加性键） | P3 | **已修复** | references L46 显式披露「CLI stdout 成功路径的 JSON 载荷仍含加性披露键 `authority_ledger: {"status":"off"}`……以此口径为准」 |
| P3-3 dry-run 再迁移保真度 | P3 | **已修复** | 代码 L1186-1196（live 事件日志副本播种 temp 演练账本）；测试 test_p3_3：再迁移 dry-run `task_registered=0 / duplicates=3 / flagged=1` 预测 live 计数、live 零触碰（events 数不变） |
| P3-4 哈希篡改分支未测试 | P3 | **已修复（补测）** | 测试 test_p3_4：改写已落盘事件内容→`hash mismatch` 报告+拒绝追加；RED 期即绿（预存分支）已诚实披露于 incidents R4-02，与本审查者 R0「已实现未测试」判断一致 |
| P3-5 migrate 空锚行 traceback 中止 | P3 | **已修复** | 代码 L1198-1201/L1217-1220（双路径捕获→`_migration_row_refused` 结构化 FAIL `schema_violation_row`，无堆栈）+ `_emit` L1489 增 code/detail 渲染；测试 test_p3_5：dry/live 双路径 FAIL+已落事件保持有效+两轮重跑恰 1 条 task_registered（幂等续跑） |
| P3-6 开关键无节作用域 | P3 | **已修复** | 代码 `_config_section_text` L873-890（与 `_gate_section_text` 同款节作用域口径）+ `switch_state` L922 仅扫节内；测试 test_p3_6：节外同形行（含 invalid 形态）不翻转、节内正常三态 |
| P3-7 锚口径假设备注 | P3 | **已修复** | references L32「口径假设：首个粗体段即声明标题（现行 plan-tracker 表格式使其成立……表格式约定属防退化看护面）」 |
| P3-8 O(n) 重折叠备注 | P3 | **已修复** | 代码 L610-614 披露性注释（量级+实测预算+增量折叠推迟至规模需要） |
| P3-9 行数声称不符（1249 vs 1400） | P3 | **已修复** | incidents R4-08 以 .Count 复核（1400→1555 / 62→63 / 25522→25841）；本审查者复核：1555 ✓ / 63 ✓ / 25841 ✓ |

**标注汇总：已修复 12 / 未修复 0 / 新引入 0（阻断级）**

## 三、新发现（本轮新增，均 P3 备注，非阻断）

- **P3-N1（看护项）**：`_check_batch_identity`（L652-690）是折叠身份语义的**第二套手写实现**（known 字典模拟），与 `fold_state` 的身份语义存在双实现漂移风险——本模块自身布道「单源反漂移」（R0 P0-1 教训）。当前语义有界（集合成员+指纹相等+顺序应用），9 测试+探针覆盖不变量，风险可控；建议后续以性质测试看护（随机合法/非法批→模拟判定与真实折叠结果一致），或提取共享的身份转移谓词。非阻断。
- **P3-N2（语义注记）**：批内冲突的审计事件中 `existing_anchor` 取批内**首个尝试锚**（该锚从未成功注册）——审计完整记录了两个尝试锚且 `attempted_source:"transact"` 可区分来源，但读审计者可能误读 existing=已注册锚。语义 nit，可在 references 或字段名上再澄清。非阻断。
- **复核确认的合法语义（非发现）**：被拒尝试**不毒化** ID——从未注册成功的 ID 以第三锚注册合法（首次成功写入建立身份），record_task 与 transact 两面语义一致；探针 B 初版预期错误系本审查者设计失误，已以 B2/B3 修正探针补足真正的原子性验证。

## 四、硬门槛复现结果（一手命令输出）

| 门槛 | 命令 | 本机结果 | 与声称比对 |
|------|------|---------|-----------|
| ① | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py` | `Ran 1084 tests in 443.801s` `OK` exit 0 | ✅ 1084=1075+9 逐字一致 |
| ② | `python ... verify_workflow.py check-governance --summary-only` | `Governance: [PASS]` exit 0 | ✅ |
| ③ | `python ... verify_workflow.py check-architecture-health` | `4 ERROR, 33 WARN (advisory)` exit 0；authority_ledger.py（1555 行）不在告警列表 | ✅ 与 R0 基线逐字持平=零新增 |

附：incidents 日志 R4-05~07 与本复现输出一致（①三遍实跑、②③数值相符）。

## 五、纯度核验（D4·返工轮）

- **返工仅触碰锁面 3 文件 + incidents 日志**：authority_ledger.py / references/authority-ledger.md / test_verify_workflow.py / `.governance/incidents/FEAT-093-r4-commands.log`。其余 8 个 M 文件（verify_workflow +23 / registry +9 / task_row_update +76 / 四测试 / 两快照）与 R0 版本逐字节相同（git diff --stat 数值不变复核）；快照 diff hunks 与 R0 完全一致（返工未再 regen，合理——引擎/registry/契约面零触碰）。
- **声称路径歧义（如实指出，非违规）**：Developer 声称修改面写「incidents/FEAT-093-r4-commands.log」，实际位于 `.governance/incidents/`——文件存在、内容完整（R4-01~08 含 RED/GREEN 实证），仅路径表述省略了 `.governance/` 前缀。
- **R0 前既存未 commit 变更之外零触碰** ✓；无越票、无版本 bump、无 FEAT-094/095/096 边界侵入（`record_event` 泛化收口=身份契约在既有通用面的自然延伸，非新功能面）。

## 六、R1 审查重点逐面结论（任务问项）

1. **批内覆盖完备性**：模拟折叠按序应用 register/supersede/state_changed——探针覆盖交错链（register→flip→supersede→flip 于一批，4 事件全落 ✓）、supersede 后旧 ID 批内换义拒（B3）、批内 new-id 撞车拒（新测试）；审计恰 1 条/次、拒绝后零业务污染+重载持久（A/B2/G）。同锚批内重复=幂等放行（重复注册事件落日志、折叠计 1——append-only 账本的诚实形态，测试+探针确认不过度拒绝）。
2. **拒绝路径无绕过**：公开面（结构化 refused dict）与 raw `transact` 面（raise）双面同口径——探针 D/E 双面验证；`record_event` 通用面走私冲突注册被拒（探针 F）——泛化收口实证。
3. **新引入面**：双实现漂移风险→P3-N1 看护项；`record_event` 泛化未破坏既有合法用法（review/recheck/goal/gate/risk 族 14 测试+全套件 1084 通过）；switch 节作用域与 Gate 解析同款口径（`_config_section_text` ≡ `_gate_section_text` 结构，前缀常量不同）。
4. **新测试质量**：9 条断言真行为（拒绝码+审计 kind+事件计数 delta+重载持久+幂等续跑计数），非跑通即过；RED 实证有 incidents 载体且诚实标注 P3-4 预存绿。
5. **D4 纯度**：见第五节 ✓。
6. **硬门槛**：三门槛全复现 ✓（第一节表）。

## 七、结论重申

**APPROVED_WITH_NOTES** — `unresolved_blockers = 0`（P0=0 / P1=0 / P2=0；P3 备注两项〔P3-N1 漂移看护、P3-N2 审计语义注记〕+R0 12 项全部闭合）。硬门槛全部通过；返工质量与披露诚实度良好。可交 Coordinator 机录终态并进入完成链（完成必推荐等收口动作由 Coordinator 执行）。

*审查过程零仓库写操作（唯一写面=本报告）；探针仅 %TEMP%，已随脚本清理。*
