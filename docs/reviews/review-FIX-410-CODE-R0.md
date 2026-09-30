# Review: FIX-410 + FIX-411 — CODE R0（G-1 攻坚双票合并审查，FIX-411 并入标注）

- **Task**: FIX-410（Check 17 读端 latest-wins + 冷链轮次日期）+ FIX-411（A quickscan 虚构段 ID 撞真实段 / B archive 结构门 / C 版本面钉重基线 / D packet B3 断言 sandbox 化）
- **Reviewer**: Code Reviewer Agent（独立 R0；本窗延续：FIX-405 R0/R1/R1b）
- **基线**: HEAD=2993f08（工作集 13 文件，`git diff HEAD --numstat` 实测 **+440/−114**；任务声明 +653/−114——删除数精确、插入数差 213，见 P3-4）
- **Round**: R0
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；**P1×1**——建议 commit 前随批一行修 + P3×5 + 环境披露×2）

## 1. 五点核验

### ① B 组结构门语义（重心）（✅ + P3 注记）

- **门实现**（archive.py L1626）：`if reason == "decision_row_too_short" and len(parts) == 7:`——结构判断先于 narrative 判断；恰 5 数据格（`|` split 7 parts）才进 `_decision_narrative_verdict`，参差形态保持 FIX-342 `decision_row_too_short`（保留热表 fail-closed）
- **经验探针**（本审查独立跑，TEMP 仓库外）：5 格带日期（窗外）→`narrative_date_out_of_window` 保留 ✓；4 格/6 格→`decision_row_too_short` 保持 ✓；**7 格无 ISO 日期→`narrative_undatable` 保留**（「7 格但非 DEC 形」边界：无 DEC-\d+ 锚的行在 L1611-1617 前置过滤不可达，无日期可析则 fail-closed 保留，永不迁移）✓
- **双契约调和判定成立**：FIX-342（结构不可信=保留）对参差行完整保留；FIX-407（narrative 识别）收窄到规范 5 格形态——修复的是 FIX-407 的过宽开口（此前任意 too-short 行〔如 4 格带锚+日期+已证 refs〕可经 narrative 迁移）。**这是产品码语义修复而非测试放水**
- **陈旧测试翻转的 git 实证**：`test_archive_decision_attribution.py` 最后提交=f73bef7（FIX-342 时代，早于 narrative 机制）；FIX-407（4f52c6b）改 archive.py +117 **未触碰该测试**→旧期望（unknown_structure=1）自 4f52c6b 起陈旧红；新期望（`narrative_*` 前缀 + unknown_structure=0）与已提交机制及 FIX-411 裁定逐项一致 ✓
- **P3-1**：新注释「ragged headerless forms (4/6/10/12 cells) keep too_short」的枚举仅对 **headerless 模式**精确——with-header 模式下 10/12 格行走机器路径（related_idx=9 落在行内，`_decision_archive_version` 不查总长），本批未改亦未误述为已改，但注释易被读成两模式通用；建议注明模式限定
- **P3-2（范围外披露）**：with-header 参差 10/12 格（≠11 规范列数）仍经 related_idx 命中机器路径——FIX-342 的长度信任只护 headerless 臂。既有语义、本批零变化；登记为后续加固候选

### ② FIX-410 latest-wins 双向 fail-closed + 冷链注入（✅ + P1）

- **latest-wins 机制**（verify_workflow.py check_user_impact L13437-13462）：逐任务取最新「用户影响：」承载行判定 + `latest_wins_superseded` 计数披露 + 无 field 行任务保持原逐行逻辑。**field 行双向性验证**：最新坏行→FAIL（`test_latest_malformed_row_fails_despite_older_compliant`）✓；最新合规行盖旧坏行→PASS+superseded=1 ✓；live 实证：check-user-impact 全 PASS exit 0——`FEAT-078 (EVD-1267)` 判定 PASS、**EVD-1252 两条 FAIL 消失**（R0 时的存量红在此闭口）
- **⚠ P1-1（fail-open 边，建议随批一行修）**：**晚出的无 field 行会被 supersede 计数吞掉**——任务已有更早 field 承载行时，`_latest_field_index` 指向早行 index，晚出的 fieldless 行 `_index != _latest` → 计 superseded 并**移出判定**→该行缺失 field 的 rule-1 FAIL 消失。写入侧镜像不拦无 passage 行（presence-triggered 设计）→组合成 rule-1 执法缝：旧合规 impact 行在前的任务，其新增无 passage impact 行静默逃检（仅计入不区分形态的 superseded 计数）。与派单验收语义「最新行坏→FAIL 保持」的一般读法冲突。修法一行：supersede 仅作用于 field 承载行，fieldless 行恒入判定（+一测：field 行后接 fieldless 行→FAIL）
- **冷链注入**（review_domain L2977-2989）：冷行 extend 在 `if EVIDENCE_PATH.is_file():` 块内——**fixture 隔离成立**（EVIDENCE_PATH 缺失即整体跳过；`_cold_review_evidence_lines` 以当前模块全局构造 DataSource，补丁传播到 fixture 归档路径，不触宿主归档）✓；**fail-safe 降空表**成立（try/except→热面仍报告）✓；三测覆盖对称面：冷行历史日期（2026-07-17<FIX174 线 2026-07-18）→V1 WARN 降级 / 无日期→violation 保持 / 规范化后日期→violation 保持 ✓——REL-058 V1 误报根因（链唯一贡献=无日期历史报告文件）与修复语义吻合，`row_date` 谓词（L3007-3011 ISO 日期格）消费冷行 verbatim 日期列成立

### ③ A/C/D 陈旧测试更新定性抽验（各一，均非放水）（✅）

- **A（quickscan）**：虚构段 ID "41"→"99" + 计数注册表派生（45→`len(selection.chosen)` 等）。契约源可证：FEAT-080 已注册 Check 41/42 为真实段（committed registry/snapshots）→旧虚构 ID 撞真实段、旧期望在 HEAD 已红；新断言结构等强度（仍精确断言 undeclared/extra/KeyError/fail-closed，仅 ID 更换+来源注释）。派生计数有 registry↔snapshot 等价测试族锚定，非自证空转。P3-3：段 ID 数值增长终将撞 "99"——非数值哨兵可一劳永逸（可选）
- **C（版本面钉）**：`resolve_entry.py`→`resolve_entry` 标记——契约源实证：persona 模板 L53「执行 resolve_entry → 热数据 → 首次交互」（无 .py 后缀，FEAT-078 措辞）✓；「以下六条」→「六条」断言——契约源=FIX-405/406 冻结线压缩（本审查链 R1b 亲审的 L226 措辞），断言语义保持（六条计数仍在）✓；m0 manifest 双 sha 重钉带 prior 台账+授权注记（REL-094 M-1R 既有授权变更登记）✓；P3-5：SKILL 钉的 section 描述词仍为压缩前标题措辞（仅描述性字段，pin 按 sha/line_span 校验——一词级过时）
- **D（packet B3）**：增量合并 no-drop 断言**仅换 sandbox 安全夹具**（`_governance_temp_dir` 家族），断言本体零变化 ✓

### ④ DEC-213③ 两轮复锚合法性（✅）

DEC-213③（archived decisions L107 实读）：「测试/夹具静态版本钉 MUST 从被测面渲染源派生，MUST NOT 钉发布字面量」。本轮 STATIC_PIN_EXEMPTIONS 重锚（158→166；20038→20125/20056→20143；20388→20475/20420→20507）：**token（0.85.0/0.93.0）与 reason（_REASON_FUTURE_TARGET）逐项未变**，仅行号追随测试文件插入位移（+82/+5 两轮均注释留痕）——派生纪律符合、零断言弱化、零新增字面量；`test_static_version_pins` 25 passed（重锚与实际扫描命中一致）✓

### ⑤ 复跑协议（✅，TEMP=仓库外 `$env:LOCALAPPDATA\Temp\fix410-411-review`，F-13）

| 命令 | 结果 |
|------|------|
| pytest test_verify_workflow -k FIX410 | **3 passed** |
| pytest test_review_closure_legacy -k FIX410b | **3 passed** |
| pytest test_archive_decision_attribution（全） | **14 passed + 4 subtests** |
| pytest test_quickscan_registry + test_quickscan_selector（全） | **124 passed, 1 failed**（见环境披露①；从仓库根 cwd 复跑该例 **1 passed**——环境归因成立） |
| pytest test_static_version_pins（全） | **25 passed** |
| pytest test_dsh_adapter 两语义测试（launcher token + clause5/6 全面） | **2 passed + 3 subtests** |
| pytest test_verify_workflow -k ExecutionPacketTests（D 组） | **18 passed** |
| `check-user-impact`（live） | **PASSED exit 0**——EVD-1267 判定 PASS / EVD-1252 superseded 消失（FIX-410 目的 live 闭环） |
| `check-version-consistency`（live） | **PASSED exit 0**（13 面 + bootstrap 标记一致） |

重试预算：2/2（quickscan 失败详情 + 仓库根复跑）。

## 2. findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P1-1 | **P1** | verify_workflow.py check_user_impact latest-wins 块 | 任务有更早 field 承载行时，**晚出的无 field 行被计 superseded 并移出判定**→其 rule-1 缺失 FAIL 消失（写入侧镜像 presence-triggered 不拦无 passage 行→组合成执法缝）；与「最新行坏→FAIL 保持」验收语义冲突 | 一行修：supersede 仅作用 field 承载行、fieldless 行恒判 + 一测（field 后接 fieldless→FAIL）；**建议 commit 前随批修**（成本低过后续票） |
| P3-1 | P3 | archive.py L1630-1636 注释 | 「4/6/10/12 cells keep too_short」枚举仅 headerless 模式精确（with-header 10/12 格走机器路径） | 注明模式限定 |
| P3-2 | P3（范围外披露） | archive.py `_decision_archive_version` | with-header 参差 10/12 格（≠11 列）经 related_idx 命中机器路径——FIX-342 长度信任只护 headerless 臂（既有语义，本批零变化） | 后续加固候选票 |
| P3-3 | P3 | quickscan 测试虚构 ID "99" | 数值段 ID 增长终将再撞 | 可选：非数值哨兵 |
| P3-4 | P3 | 派单声明 | 工作集 +653/−114 vs 实测 **+440/−114**（删除精确、插入差 213） | 交接附可复现命令 |
| P3-5 | P3 | fixtures/m0/manifest.json SKILL 钉 section 描述词 | 仍为压缩前标题措辞（描述性字段，pin 按 sha 校验不受影响） | 下次编辑机会同步 |

## 3. 环境披露（非本批 finding）

1. **树外污染工件**：gitignored `skills/software-project-governance/infra/.governance/`（今日 18:31:39 生成，含 archive/）劫持 cwd 根发现——pytest 从 infra cwd 跑时 `test_default_invocation_keeps_the_product_gate_active` 红（HOST=infra≠PLUGIN→product gate 判 False）；**同测试从仓库根 cwd 复跑即绿**（本审查实证）。该测试不在本批改动集、输入与 HEAD 逐字节同源→非本批回归。建议 Coordinator 定位误定向写入者（疑为某并行运行 cwd=infra 未带 --project-root）并在确认无在跑任务占用后清理。本审查未触碰该目录（可能是活跃任务工件）
2. **HEAD 陈旧红模式**：本批两组「旧期望翻转」（B 组 unknown_structure、A 组 "41" 撞段）均有 git 实证其旧期望在 HEAD 已红（分别陈旧自 4f52c6b 与 FEAT-080 注册）——与 G-1 攻坚（陈旧测试清理）定性一致；Coordinator 后台权威全量套件为最终裁决面

## 4. 五维度 + AI 专项（增量）

- 正确性：✅（B 门边界经验探针四态全中；latest-wins 双向 field 行验证；P1-1 为唯一语义缺口）
- 安全性：✅（零新输入面；冷链注入 fail-safe；夹具全 sandbox 化——真实环境零暴露）
- 可维护性：✅（常量/派生计数/来源注释纪律好；P3-1/P3-5 措辞精度）
- 性能：✅（latest-wins 两遍 O(n)；冷行单次读取）
- 测试覆盖：✅（13 文件 +440 行中 ~56% 为测试；P1-1 边界缺一测）
- AI 专项：mock 残留无 ✓／硬编码返回无 ✓／幻觉 API 无（_cold_review_evidence_lines/_decision_narrative_verdict/qr.segment 均实存）✓／TODO 无 ✓／过度实现无（四组+两票与派单 1:1）✓

## 5. 裁决

**APPROVED_WITH_NOTES** — unresolved_blockers=0。五点核验全立；**P1-1 强烈建议 commit 前随批一行修**（晚出 fieldless 行逃检缝——修复成本一行+一测，低于后续票）；P3×5 与环境披露×2 不阻塞。HEAD 陈旧红模式的最终裁决归 Coordinator 后台权威全量套件。

---

# §FIX-412：R3 归档感知任务映射（快审，2026-09-29）

- **对象**: risk_domain.py `_archive_terminal_task_statuses()`（archive/index.md 任务面签名解析）并入 `_default_task_status_map` + test_risk_mitigation_closure.py 新类 3 测 + 4 处 fixture 沙箱化
- **工作集**: 2 文件 +51/0、+85/−4（与派单 1:1，零范围外 ✓）
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；P3×3）

## 五点核验

| # | 要点 | 判定 | 事实依据 |
|---|------|------|---------|
| ① | 前提证伪处理完备 | ✅ | OPS-001/MAINT-003~006 跨实体族 + DESIGN/PLAN/DOC 早期族**零踪迹实证**（hot tracker + archive/index.md 任务面均无 grep 命中；risk-log L10/L23 仅作缓解引用出现）→前治理纪元实体按设计保持 R3 WARN（不升 FAIL、不静默吞——`test_truly_nonexistent_reference_keeps_r3` 断言 reason 串）；live 面如实分层：62 归档任务解析（59 完成+3 终止）+ 零踪迹族 R3 残余（live 抽样 RISK-001/006/008/009/011 → DESIGN-001/PLAN-004/DESIGN-005/PLAN-003/DOC-001 全为设计内 WARN）；实现零发明解析 |
| ② | 热表恒胜（双态不混） | ✅（结构保证）+ P3-1 | 热表四桶（completed/blocked/unblocked/non_executable）先全量填 map，archive 经 `setdefault` 仅补缺（L366-367）——结构性保证一个 task_id 永远单状态；**缺双态回归测**（同 id 热表进行中+归档已完成→热胜） |
| ③ | 缺档回退 fail-safe | ✅ | 三重防护（is_file 缺→{}；Path 构造 OSError/ValueError→{}；read 失败→{}）never raises；{} 合并=no-op=修复前逐字节同行为（`test_missing_index_falls_back_to_hot_only`）；另：hot parse 失败→`return None` 先于归档合并（L355-359→L366）——归档面不救援热表失败，保守正确 |
| ④ | 3 新测质量 | ✅ + P3-2 | 三态覆盖：归档完成→PASS 零警+stats.pass=1 / 真不存在→R3 WARN 保持 / 缺档→热-only 回退；fixture 沙箱化 4 处（FIX-411 家族 `_sandbox_gov_dir`）+ SAMPLE_PATH 经 `_resolve_shared()`（check 入口 L432 在 map 构建 L446 前）刷新——patch `vw.SAMPLE_PATH` 全链传播 ✓；复跑 **27/27 passed**；live 探针：62 任务解析正常、签名判别（cells[4]=archive/tasks/ 位置+无空格 id+终态词表）对 EVD/DEC 索引行零误匹配。**缺口**：已终止映射（fixture OPS-009 行在场但无断言——terminated≠completed 诚实映射无直接测试） |
| ⑤ | 零范围外 | ✅ | git status/numstat：仅 risk_domain.py + test_risk_mitigation_closure.py，与派单 1:1；CRLF 归一化提示同前批（无实害） |

## findings（P3×3，零阻塞）

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P3-F412-1 | P3 | 测试 | 双态热恒胜（同 id 热表+归档）无回归测——setdefault 结构性保证现正确，但语义靠实现细节而非断言钉护 | 补一测：同 id 双态→热状态胜 |
| P3-F412-2 | P3 | 测试 | 已终止映射无直接断言（OPS-009 fixture 行已备，仅差一个用例）——terminated≠completed 的诚实性未被钉护 | 补一测：引用已终止归档任务→非 R3 但也非 completed |
| P3-F412-3 | P3 | risk_domain L309 | `_archive_terminal_task_statuses` 依赖调用链先行 `_resolve_shared()`（现由 check 入口 L432 契约承担）；绕链直调且未刷新时 `Path(SAMPLE_PATH)` NameError（`_default_task_status_map` 的 try 只包 parse，幸而未刷新时 parse 先炸→None fail-safe，到不了 archive 调用——唯一暴露面=私有函数直调） | 可选：函数内自调 `_resolve_shared()` 一行自洽 |

## 复跑证据（TEMP=仓库外 `$env:LOCALAPPDATA\Temp\fix412-review`；重试 0/2）

pytest test_risk_mitigation_closure.py（全）→ **27 passed**（=声明 27/27 ✓）；live 探针：`_archive_terminal_task_statuses()`=62 条（59 已完成+3 已终止）；live `check_risk_mitigation_closure`：R3 残余=零踪迹族设计内 WARN、R2 violation（RISK-003/DESIGN-002/2026-04-17）=既有存量与本批无关。

## 裁决（§FIX-412）

**APPROVED_WITH_NOTES** — unresolved_blockers=0。五点全立（②为结构性保证+测试钉护建议）；P3×3（两测缺口+直调自洽注记）零阻塞，可并入随批或遗留。
