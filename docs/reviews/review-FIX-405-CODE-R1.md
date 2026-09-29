# Review: FIX-405+FIX-406 — CODE R1（scoped：只审 R0 后增量）

- **Round**: R1（前轮引用：docs/reviews/review-FIX-405-CODE-R0.md，AWN/0，P2×3+P3×4）
- **审查范围**: 增量 only——Coordinator 五点返工（F-1/F-2①②③④/P2-3/P3-2/P3-3）；非全量复审
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；新增 P3×3，其中 2 条为 R0 已披露残留的收敛注记）
- **范围排除**: FEAT-076 在途（archive.py/test_archive.py/review_domain.py/test_evidence_layer.py/feat076-consumer-matrix.md + verify_workflow.py 内 GovernanceDataSource/check_governance_data_size 两 hunk）——未评审未触碰

## 1. 前轮 findings 处置比对（复审义务）

| R0 finding | 级别 | R1 处置 | 核验 |
|------------|------|---------|------|
| F-1 plan-error 空转 PASS | P2 | **已修复** | §2.1 |
| F-2 mirror 三处漂移+注释过度声明 | P2 | **已修复（派定范围内）**，残留 P3-R1b | §2.2 |
| F-3 --write FAIL→exit1 无测试 | P2 | **已修复** | §2.3 |
| F-4 note 无 stdout 断言 | P3 | 未派（Coordinator 裁剪）——遗留，非阻塞 | — |
| F-5 remediation is_dir 误判 | P3 | **已修复** | §2.4 |
| F-6 ADR 未收编第三形态 | P3 | **已修复** | §2.5 |
| F-7 声明计数不可归因 | P3 | 未派——遗留，非阻塞 | — |

## 2. 五点核验

### 2.1 F-1：error 键两调用点提升（✅ 关闭）

- **readiness 聚合**（verify_workflow.py `check_release_readiness`）：`_sd_face_error = _sd_face.get("error")` → `issues.append(f"sd integrity: {_sd_face_error}")`（显式 issue→聚合 FAIL）+ `details["sd_integrity"] = {**sd_scan, "face_error": ...}` ✓
- **--write 面**（`cmd_release_projection`）：`_face_error` → `state=FAIL` + issues 追加 + exit 1 映射；face_error 进 result JSON ✓
- **负例测试** `test_release_readiness_surfaces_projection_plan_error`：mock `projection_face_paths` 返回 error dict → 断言 issues 含 "projection plan unreadable" + `details.sd_integrity.face_error` 等值 ✓。函数级 import 在补丁窗口内取 patched 属性，mock 生效机制正确
- **空转 PASS 缺口判定关闭**：plan 不可建 → readiness 出 issue（FAIL）/ --write 出 FAIL+exit 1，两条路径均不再可能静默通过 ✓

### 2.2 F-2：谓词统一 + rule-5 镜像 + 句读清洗 + 注释收窄（✅，带注记）

①**常量单点 + 引擎副本退役**：`VALID_OBTAIN_VALUES`（tuple，7 值与 R0 核验一致）/`USER_IMPACT_SUBFIELD_RES` 定义于 governance_store；Check 17 本地列表删除改函数级 `from governance_store import VALID_OBTAIN_VALUES` ✓。**import 方向健康性**：verify_workflow L94-95 早已模块级 import governance_store（writer CLI 派发边）——本次零新增模块依赖边；governance_store 仅依赖 stdlib+contracts（无反向 import）→ 无环 ✓。tuple 语义兼容 contains/join/切片 ✓
②**rule-5 BLOCKING 镜像**：`体验变化=是 and 迁移指南=不需要` → pre-write refuse（破坏性变更 MUST 携带迁移指南）+ 零字节 ✓；测试 `test_breaking_change_without_migration_guide_refused` ✓
③**句读清洗**：`values[label] = match.group(1).strip().rstrip("。.，,；;、 ")`——尾句读不入比较 ✓；rule-5 测试用「迁移指南=不需要。」**带句读形态**，rstrip 缺失时 `“不需要。”==“不需要”` 不成立→该测试同时是句读清洗的行为覆盖（隐式但有效）✓
④**注释收窄**：声明改为 rules 1-4 intake-judgeable faces + rule 6 留引擎终检 + 无 passage 行维持骨架契约——语义上与实现**基本**一致（EVD-1252 类=携带畸形 passage 的写入已闭合；rule 6 依赖读时仓库状态留引擎✓；无 passage 行零行为变化✓）。**注记→P3-R1a**：编号「rules 1-4」不准——括号列举实为 rule 2/3/5 的面；rule 1（影响分析行缺 passage）按 presence-triggered 设计**未**在 intake 封堵（尾句已披露该事实，声明与实现无矛盾，但数字范围建议修为「rules 2/3/5 的 intake 可判面」一词级修正）

### 2.3 P2-3：--write FAIL→exit 1 自动化测试（✅）

`test_write_face_fails_with_exit_one_on_sd_damage`：mock `write_projections`（as_dict→PASS，零真实投影字节移动）+ mock damaged scan → `cmd_release_projection(SimpleNamespace(write=True, config=None))` → `SystemExit` code==1 + 双 mock called 断言 ✓。green-by-coverage 达成：既有契约（result JSON 携带 sd_integrity、FAIL 覆写、exit 码映射）现有守护 ✓

### 2.4 P3-2：remediation_for is_dir 探测失败→目录模板（✅）

`is_dir = True` 缺省 + `except OSError: is_dir = True`——探测失败落**递归**模板（fail-safe 宽修复面，保 /t 继承授权）✓；docstring 补 FIX-406 P3-2 说明 ✓；专项测试 patch `Path.is_dir` side_effect=OSError → 断言 /r 与 /t ✓

### 2.5 P3-3：ADR §2.2.3 第三形态收编注（✅）

ADR-021 L206 追加（+1/-1）：「第三形态（FIX-406 P3-3 收编，B4-2 落地）：M 与 U 的 P 级均已解析且 M 的 P 级严格更低（如 M=P2 排 U=P1 前）——排序键正确时同样不可能（P1 恒先于 P2），归 INV-1 FAIL（else 臂拆分：已解析乱序 FAIL / 未解析保守 WARN）」——与 provenance_domain.py 实现分支**逐句一致**；与 INV-X（M 更高=容忍 WARN）边界表述不冲突 ✓。R0 立论延伸→规范性条款的缺口正式闭合 ✓

## 3. R1 findings（新增）

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P3-R1a | P3 | governance_store.py F-2 注释 | 「rules 1-4's intake-judgeable faces」编号不准：括号列举=rule 2/3/5 面；rule 1（影响分析行缺 passage）presence-triggered 设计下未在 intake 封堵（尾句已如实披露） | 一词级修正（「rules 2/3/5」或「red-row-class rules」） |
| P3-R1b | P3（R0 F-2 残留收敛注记） | mirror vs Check 17 | 谓词统一为**枚举级**：subfield 解析器仍两套（mirror charset+rstrip vs Check 17 终止符+contains）——中段「。」分隔形态 mirror 过拒（fail-closed）；mirror rule-5 在 Check 17 自身宽松解析（“是；”≠“是”）不触发的形态上触发= intake 严于引擎（声明为有意姿态后可接受） | 下次机会：引擎改用 USER_IMPACT_SUBFIELD_RES 或抽共享 parse helper，彻底单一事实源 |
| P3-R1c | P3 | cmd_release_projection --write | plan 不可建时 write_projections 本返回 BLOCKED（exit 3），face_error 在场时被覆写为 FAIL（exit 1）——按派定规格实现（"--write→state FAIL→exit 1"），诊断信息经 issue 串保留，仅 BLOCKED/FAIL 语义区分有损 | 可忽略；如在意可 face_error 分支保留原 state 仅追加 issue |

## 4. 增量维度与 AI 专项

- **正确性**：五点返工逐行实读（error 提升两路径/rule-5 refuse/rstrip/is_dir 兜底/ADR 措辞）+ 负例测试全绿 ✓
- **安全性**：无新输入面；refuse 路径全 fail-closed ✓
- **可维护性**：常量单点化改善（且复用既有依赖边）；P3-R1a 注释一词修正 ✓/注记
- **性能**：零新增循环（error 提升为 O(1)）✓
- **测试覆盖**：+5 测试（rule-5/isdir-probe/plan-error/exit-one/fixture 句读）覆盖全部五点行为面 ✓
- **AI 专项 5 项**：mock 残留=无（patch 全部测试内）✓；硬编码返回=无（fixture 返回值属测试合法注入）✓；幻觉 API=无（VALID_OBTAIN_VALUES import 实存 L13421、SimpleNamespace 标准）✓；未实现 TODO=无 ✓；过度实现=无（增量与五点派单 1:1，零多余面）✓

## 5. 复跑证据（TEMP=.governance/tmp/check-run-20260929；重试 0/2；混合树上执行）

| 命令 | 结果 |
|------|------|
| pytest test_governance_store.py + test_provenance_domain.py | **145 passed**（store 108→109 含 rule-5 新测试；provenance 36 不变） |
| pytest test_verify_workflow.py -k "SdIntegrity or collect_session_closure or ExecutionPacketIncremental or UserImpact" | **21 passed**, 988 deselected（SdIntegrity 9=6+3 新；UserImpactTests 引擎面选中=import 路径实证） |
| pytest test_archguard_ratchet.py -k "anchor or census" | **2 passed**（锚断言读 JSON 值 26965——本批不 regen 故不动；print 计数 **1338** 复验=R1 增量与 FEAT-076 在途均零新 print） |

**regen 预期红说明**（按派单口径，非本增量 finding）：本批不 regen（防 FEAT-076 在途 +140 污染锚归因）；live LOC（27125+）> 锚 26965 的漂移面属两批并行中间态，序=FEAT-076 commit+rider → FIX-406 rider 补差 +16（Developer 声明）。

## 6. 裁决

**APPROVED_WITH_NOTES** — unresolved_blockers=0。五点返工全部核验关闭（F-2 带范围注记）；新增 P3×3 均为收敛注记/一词修正，零阻塞。遗留（Coordinator 已裁剪，非阻塞）：R0-F-4（note stdout 断言）、R0-F-7（计数声明可归因性）。

---

# §R1b：窗口第三增量复核（DEC-295 授权链三件，2026-09-29）

- **Round**: R1b（scoped 增量——R1 后追加三件，非全量复审）
- **授权链**: DEC-295（decision-log L231 实读全文：EXC-001 终局=阈值重定标〔用户 ask 裁定〕/SKILL 预算线升格 2560→3072B/0.93.0 组装清单增补）
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；P3×2 + 披露×2）

## R1b.1 三件核验

### ① SKILL.md 冻结线瘦身 2957→2866（−91B）（✅）

- **六条冻结文本一字未动**：git diff 权威证实 SKILL.md 仅 2 行变更（L224 标题行/L226 引言行），六条款 L229-234（复审必达/完成必推荐/选项必带依据/真实环境必防护/推荐必标需求源/发现即闭环）零字节差异；条款标题与全文逐条实读在场 ✓。注：派单语境中「审查结论必机录」属 references/behavior-protocol 层（M7.4），非 SKILL 六条投影面——我方首轮探针措辞误差，已用逐条标题实读修正
- **锚全在**：`check-injection-contract` 复跑 **PASSED**（exit 0；Files checked: 4; anchors: 30; staged ADR-021-B1a: active, 9 anchors guarded）——零 issues ✓
- **−91B 精确性**：独立字节计量——标题行 Δ=51B + 引言行 Δ=40B = **91B 整**；当前段实测 **2866B**（按守护测试同边界：index("关键行为契约")→index("产品代码 vs 治理记录边界")），余量 3072−2866=**206B**——与 DEC-295(2)「2957→2866 / 余量 206B」逐数吻合 ✓
- **删的仅两处非语义面**：✓ 考据引注（「注入面最小契约集，FIX-253/REQ-112」→DEC-295 decision-log 承载）；✓ 引言重复措辞收敛——**MUST 语义零损失判定成立**：全部 MUST 承载命题（同级/违反=流程违规/canonical 投影/persona 压缩形式/锚点守护）逐项保留，仅删冗词与考据，无任何 MUST 动词或义务面消失

### ② SKILL 预算线字面量 2560→3072（✅）

- 字面量对实读：`test_review_machine_provenance.py` L262-263 断言 2560→**3072**（消息「DEC-295(2) raise」）；persona 面测试 L242 保持 **2560**（不同面，未动）✓
- **docstring 升格链注记与 DEC-295(2) 一致性**：逐项核对——DEC-144 2KB→FIX-274/DEC-162 2.5KB（四条时代，2026-08-23）→DEC-295(2) 3.0KB（六条时代——B1a 注入第 5/6 条 +448B 永久文本；瘦身后实测 2866；+206B 余量）——与 DEC-295(2) 原文（2509+448=2957；−91B=2866；余量 206B）**全算术链吻合** ✓；docstring 明示 persona 预算 2.5KB 属不同面（与 L242 未动互证）
- **InjectionAnchorExtensionTests 复跑 4/4 passed**（0.11s）✓

### ③ track-1 热容量线重定标 per-file 覆写（✅）

- **①file_overrides face 级取线**：`check_governance_data_size`（verify_workflow.py L21173-21190 实读）——`override = file_overrides.get(rel, {})` → `face_warn/face_error = override.get(..., 全局线)` 逐文件解析；全局 warn/error 200000/250000 原值不动 ✓。**EXC-003 语义保留的决策依据成立**：decision-log 仍走全局 error 线（live 实证 ERROR@250000 + EXC-003 注解承载）——覆写严格 per-file，非全局抬线 ✓
- **②schema 覆写值+锚**：architecture-health.json `governance_data_size.file_overrides[".governance/evidence-log.md"] = {warn 400000, error 650000}` + note 载 DEC-295(1) track-1 recalibration（用户裁定 2026-09-29；稳态依据：199 永久留热登记行 ~280-300KB + 工作集；实测 515KB + 迁移摆动余量）✓；diff 全读核实其余 +41/−9 为纯重排版，无其他语义变更
- **③EXC-001 删除后 exceptions.json 有效**：实读 `.governance/exceptions.json`——仅余 EXC-003（2→1 ✓）；live 判定面仅 EXC-003 注解出现 ✓
- **④TDD 两例真实性**：`test_dec295_evidence_log_per_file_override_lines`（合成 root：evidence@515KB→WARN + reason 含 "400000"；decision@260KB→**ERROR 走全局线**——直接证 per-file 作用域）+ `test_dec295_live_schema_and_code_comment_carry_anchor`（inspect 源码含 "DEC-295" + live schema 断言覆写值 400000/650000 + 全局 error_bytes 仍 250000）——真实函数+真实 live schema，非 mock 空转 ✓
- **⑤live 三文件判定面复现一致**：`check-governance-data-size` 实跑——evidence-log **515685B (503.6KB) WARN `exceeds warn_bytes=400000`**（覆写线）✓ / decision-log **257905B ERROR `exceeds error_bytes=250000 — exception accepted (EXC-003, ref=DEC-288…, expires=2026-10-12)`**（全局线+例外承载）✓ / plan-tracker **204831B WARN `exceeds warn_bytes=200000`**（全局线）✓；risk-log 无发现（线内）✓；test_architecture_health 全量 **25 passed**（含 2 新例）✓

## R1b.2 findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P3-R1d | P3 | core/architecture-health.json | +41/−9 中约 2/3 为 compact→pretty 纯重排版，语义变更（note+file_overrides）与格式化混于同一变更（D4 修改纯粹性注记）；工作区文件现为 CRLF（git 将归一化 LF，无实害） | 后续格式变更分离；非阻塞 |
| P3-R1e | P3（移交） | DEC-295(1) | 「基线重定标入 baseline-register」为 Coordinator 台账动作，不在本三件文件面内——本增量未核验其落账（无机器面与之矛盾；重定标生效已经 exceptions.json+live 判定双实证） | Coordinator 确认 baseline-register 落账（writer 子命令，DEC-223 面） |

**披露（非 finding）**：①TEMP 目录 `.governance/tmp/check-run-20260929` 被多并行 agent 共用（产物时间戳横跨 08:06–17:29）；其中 10:28–10:48 的陈旧失败日志（'import registry' 断言）经查当前 verify_workflow.py 无 top-level `import registry`——FIX-404 时代中间态、非现红，本增量证据不受污染（本审查全部输出自带时间戳与命令可溯）。②R1 报告时点的「review_domain.py/GovernanceDataSource hunk=范围外」判断在 R1b 语境下部分收编：`check_governance_data_size` 的 layers/three-track 面即 DEC-294 所述 FEAT-076 三轨落地——本增量仅按派单核验 track-1 取线与判定面，layers 面归 FEAT-076 审查链。

## R1b.3 裁决

**APPROVED_WITH_NOTES** — unresolved_blockers=0。三件全部核验通过：瘦身 −91B 字节级精确+六条冻结文本零动+30 锚全守；预算线升格链与 DEC-295(2) 全算术吻合+守护 4/4；track-1 覆写 per-file 语义/TDD 两例/live 三文件判定逐字复现。P3×2（重排版纯粹性/baseline-register 落账移交）零阻塞。
