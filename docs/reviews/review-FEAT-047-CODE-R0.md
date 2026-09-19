# Review FEAT-047 — CODE R0（独立代码审查 · BaselineMetadata provenance 机制）

> Round: R0 · Reviewer: Code Reviewer（独立 spawn）· 日期: 2026-09-19
> 审查对象（工作树未提交，`git status --porcelain` 两文件均 `??` 未跟踪）:
> - `skills/software-project-governance/infra/baseline_metadata.py`（实际 1003 行）
> - `skills/software-project-governance/infra/tests/test_baseline_metadata.py`（实际 620 行，53 测试方法）
> 语义基准: contracts.py（EVALUATION_RESULTS/CONTINUATION_POLICIES/ContractViolation，m0-r1 只读消费）· arch round-2 §4（七要素+分轴+豁免四要件）· round3 P1-2（量测口径）· EVD-1099/1100/1104 · version-plan-0.86.0 §2/§3
> 审查方式: 逐行读两文件全文 + 语义基准原文比对 + 4 项独立复验实跑。只读审查——本报告是唯一写产物。

---

## 总结论

# NEEDS_CHANGE

**unresolved_blockers = 1**（P0-1 ×1）

P0=1 / P1=1 / P2=3 / P3=5。按 code-review SKILL 关闭规则（P0>0 不得合并）→ Coordinator 收到后退回 Developer 修复 P0-1（修复量：一行级包装），修复后按 M7.4 发起 R1 复审（本 Reviewer，逐条比对全部 findings）。

---

## 一、独立复验（4 项实跑，非采信申报）

| # | 复验项 | 命令/场景 | 结果 | 与 Developer 申报对照 |
|---|---|---|---|---|
| 1 | 53 测试套件实跑 | `python -m unittest discover -s .../tests -p "test_baseline_metadata.py"` | **53/53 OK, exit 0**（0.263s） | ✅ 一致 |
| 2 | config_error 场景复现 | `baseline-evaluate --threshold 2 --floor-value 720 ...`（EVD-1100 形态） | exit **2** + `gate_configuration_error`（"mathematically unreachable (EVD-1100 shape)... not a user failure"） | ✅ 申报属实 |
| 3 | CLI crash 路径 exit code | `baseline-evaluate --now "not-a-date" ...`（只读：registry 指向不存在临时路径，零写副作用，事后确认未创建） | **exit 1 + 未捕获 ValueError traceback**（应 exit 3） | ❌ **申报未覆盖此路径——P0-1 实锤** |
| 4 | verify 全量 + archguard ratchet | `verify_workflow.py`（全量）/ `verify_workflow.py archguard-ratchet` | 全量 **PASSED** exit 0；archguard **PASS**（R1/R2/R3/R4/R5/R7 全 PASS，R6 INFO advisory，0 violations） | ✅ 一致（申报口径 R3/R4/R5/R7 实为全绿） |

补充状态核验：`.governance/baselines.json` 不存在 ✅（申报「真实登记留 Coordinator」属实）；`registry.py`/`verify_workflow.py` 零改动 ✅（并行票文件面不相交裁定可维持）。

---

## 二、七审查重点逐项结论

### ① 七要素→14 字段覆盖完备性与 arch 原文忠实度 — ✅ 通过（1 项 P3 留白）

arch round-2 §4 原文（L66）七要素逐项映射核验：

| §4 要素 | 字段 | 判定 |
|---|---|---|
| 测量时间 | `measured_at` | ✅ ISO-8601 校验 |
| 测量器版本 | `instrument_version` | ✅ 非空文本 |
| 来源命令 | `measurement_command` | ✅ |
| 测量对象 commit/摘要 | `target_commit_digest` | ✅ 7..64 lowercase hex 正则 |
| 范围/分子/分母/排除规则 | `scope`+`numerator`+`denominator`+`exclusions`（1 要素 4 字段） | ✅ 且四字段全部进入口径指纹 |
| 阈值依据 | `threshold_basis` | ✅ |
| 有效期失效条件 | `expiry_condition`（+可选 `max_age_days` 机器面） | ✅ |

另加 identity/payload 面 `gate_id`/`value`/`unit`/`source_evd` = 14 必填字段，与 `BASELINE_FIELDS` 一致，逐字段缺一负例测试在位（`test_missing_each_required_field_is_refused`）。

分轴忠实度：PASS/FAIL/NOT_EVALUABLE ⊥ BLOCK/ADVISORY 正交双轴 ✅（`EvaluationOutcome` 双轴独立校验，均锁 contracts.py 冻结元组）；「过期/范围变化/测量器不兼容→NOT_EVALUABLE」三触发全实现 ✅（`baseline_expired`/`caliber_mismatch`+`target_changed`/`instrument_changed`）；「自动重测失败不默认通过」✅（评估器无任何自动通过路径）；「确定性矛盾→门禁配置错误，不自动调阈值」✅（`gate_configuration_error` 分支 + "never auto-adjusted" 文本钉死）。

**豁免四要件（范围/理由/授权/失效条件）**：未承载——waiver 仅出现在 continuation action 文本（L667-668）。裁定：**留白合规但不显式**。票面（version-plan §2 FEAT-047 行）为「provenance schema + 存量数值门登记」，不含豁免机制；未声称实现即无不忠实。但 docstring 未像 `BaselineConflict`（"retirement is a deliberate flow"）那样显式声明豁免结构归属后续流程 → **P3-1**。

### ② 分轴求值正确性 — ✅ 核心全过（发现 1 项 P1 语义缺口）

- config_error 先于基线状态防掩盖：✅ 求值链步骤 1 在 presence 检查前（L680-715），负例测试 `test_config_error_precedes_baseline_state` 在位。
- 新鲜但口径不匹配 → not_evaluable 非 pass：✅ 步骤 4 先于阈值比较（L759-773），unit/scope_digest 双通道均有测试。
- continuation 纯由 policy_class 派生：✅ `continuation_for` 仅吃 policy_class（L644），与 evaluation 结果零耦合；`fail` on trend 仍 advisory、`pass` on release 仍报 block 姿态（测试双钉）。
- 未知 policy_class = ContractViolation 非门判定：✅ API 面抛 `ContractViolation`；CLI 面 argparse choices → exit 3。两层均不产出门判定。

**P1-1（省略即跳过）**：`observed_unit`/`observed_scope_digest`/`current_instrument_version`/`current_target_digest` 缺省 None 时对应检查**静默跳过**，观察直接进入阈值比较——CLI 不传 `--observed-unit/--observed-scope-digest` 即复现（`test_evaluate_exit_code_face` 自身即以此路径 pass）。与同一函数内 `now` 缺失的处理（`max_age_days` 在场时 raise，"the expiry check never silently skips"）**标准不一致**：同为「检查输入缺失」，一处 fail-closed 一处 fail-open。模块 docstring 自钉承诺「a number without a trustworthy basis is NOT_EVALUABLE, never claimed」（引 version-plan §3）——口径未声明的数字同样没有 trustworthy basis。当前无实际事故（本票未接线），但批 1 engine dispatch 接线时调用方省略参数即复现 W-3 同型的口径漂移静默通过。详见 findings。

### ③ fail-closed 链完整性 — ✅ 存储/求值侧全过

- now 缺失不静默跳过过期检查：✅ L744-748 raise `ContractViolation`。
- 损坏 registry 拒读：✅ 非 UTF-8/非 JSON/顶层非 object/baselines 非 dict/key≠row gate_id 五类全部 `BaselineMetadataError`，篡改负例测试 ×2（scope_digest 直改、口径字段改而不重算指纹——写后读自检拒绝，永不比较）。
- 未知 schema_version 拒绝：✅ `RegistrySchemaError`（`version != 1` 双向拒绝——旧读器遇新 schema 同样拒，M0 face 4）。
- 已知链完整性缺口 = P1-1（观察侧输入省略），见上。

### ④ DoD 九条适用面核验 — 见下表；DoD 7 并发覆盖 TOCTOU 裁决

| DoD | 判定 | 依据 |
|---|---|---|
| 0 模型输出不可信 | ✅ | bool/NaN/Inf/空串/正则全负例（构造器+evaluate 入口） |
| 1 写前完整验证 | ✅ | 构造器即全字段校验门；register 先算 row+digest |
| 2 幂等与冲突协议 | ✅ | replay（effect-based：字节+mtime 钉测）+ `BaselineConflict` 同 gate 异 payload 拒绝 |
| 3 可靠落盘 | ✅ | 显式 UTF-8/同目录临时文件/fsync/`os.replace`/平台声明（docstring） |
| 4 写后重读自检 | ✅ | 同 schema 重读（`from_storage_row` 共享构造器——禁第二 schema 达成）+digest 比对；不 auto-restore 符合 round2 §5「恢复受版本检查保护」 |
| 5 dry-run+结构化结果 | ⚠️ | dry-run/结构化输出 ✅；但 crash 路径破坏错误分类（**P0-1**：exit 1 冒充 fail） |
| 6 恢复路径 | ✅ | 崩溃点 temp 清理（`except BaseException` unlink）；原子替换无半成品 |
| 7 守护测试 | ⚠️ | 键碰撞✅(冲突形态)/中文✅/缺行✅(构造面逐字段)/重复执行✅/并发覆盖❌(P2-2)/崩溃点△(清理代码在，无故障注入测试)/特殊字符△(中文覆盖；管道符引号未单列)/legacy N/A(全新存储)；另两处负例缺口（key≠row gate_id、GBK 字节流）→ P2-2 |
| 8 渐进启用+降级契约 | N/A | 本切片未接线——集成点在批 1 接线/批 2.0 |
| 9 机器来源标记 | N/A | baselines.json 是数据存储非治理记录行；`schema_version`+`scope_digest` 自校验面替代 |

**DoD 7 并发覆盖 TOCTOU 裁决（重点④指定裁决项）**：Developer 论证**成立，附条件留痕**。事实：`register` 是无锁 read-modify-write 全文件（load→mutate→`os.replace`），两个并发 register 不同 gate 会 lost-update、同 gate 异 payload 会绕过 `BaselineConflict`——TOCTOU 窗口真实存在。但：(a) baselines.json 当前零写入者接线（self-contained CLI）；(b) 治理流程单 Coordinator 串行，真实登记为一次性留 Coordinator；(c) round2 §1 将写入锁划归共享文件锁面（批 2.0 复跑/FEAT-046 同管道族），架构时序一致。风险现实性低，不构成本轮阻塞。**条件**：(1) 批 2.0 接线时 MUST 补并发覆盖负例或先接锁面再接线；(2) 锁面落地前 baselines.json 写入保持单写者——该约束目前未写入任何 docstring，接线时 MUST 显式化（并入 P2-2）。

### ⑤ registry 接线延后处置——文件面冻结裁定引用真实性 — ✅ 三处引用全部属实

- `LOADER_WHITELIST`：`infra/registry.py` L182-214 ✅ 共享文件，当前**不含** `baseline_metadata`（接线延后属实）。
- `_COMMANDS`：`infra/registry.py` L247 ✅ 同一共享文件。
- engine dispatch：`infra/verify_workflow.py`（import 面 L76-84、`add_arguments` 调用 L24610/24624、dispatch dict L24759）✅ 第三处共享面。
- `git status`：两审查对象未跟踪、`registry.py`/`verify_workflow.py` 零改动 → 批 1「文件面不相交」裁定**可维持**。

接线形态本身有缺口（P2-1）：声明的 governance_cost pattern 是模块暴露 `add_arguments(parser)` + engine 调用 + dispatch 直连 handler；本模块只有私有 `_add_*_options`，handler 走 Namespace→argv→main→argparse **二次解析**，且 `_register_option_map`（17 键）与 `_add_register_options`（17 项）构成同一选项集的**双重手工事实源**——漂移即静默丢参数。

### ⑥ registry 行宽 / scope_digest 双侧派生一致性 — ✅ 通过

- 存储面：`indent=2 + sort_keys + ensure_ascii=False + 尾随换行`——diff 稳定、评审可读、不注入生成时间（round2 §7 评审可读性契约全满足）；中文直出 UTF-8（FIX-278 口径），round-trip 负例测试在位。
- scope_digest：单函数 `caliber_digest` 承载双侧——register 侧 `to_storage_dict()→scope_digest()`；读取侧 `from_storage_row` 同函数重推导并与存储值比对（不符即拒）；evaluate 侧比较的 `row["scope_digest"]` 已被读取时验证。无第二实现。确定性+字段敏感性测试在位。

### ⑦ AI 专项 — ✅ 5 项全过（1 项有条件）

| 检查项 | 结论 |
|---|---|
| mock 残留 | ✅ 无（无 `unittest.mock` 导入；测试全真实临时目录+真函数） |
| 硬编码返回值 | ✅ 无（输出全部派生自输入） |
| 幻觉 API 调用 | ✅ 无（全标准库；contracts.py 三导入实存且只读消费，冻结元组逐字一致） |
| 未实现 TODO | ✅ 无（grep TODO/FIXME/NotImplemented 零命中） |
| 过度实现 | ✅(有条件) handler+option_map 预埋为声明的批 1 集成点预留，有票面依据；无测试覆盖 → P3-5 接线时补 |
| dry-run 演示数字 EVD 锚定 | ✅ 4,216/5,694/5,966、b717835、2026-09-19、DEC-210/211、6,000 门全部与 EVD-1104/EVD-1100 逐位一致（本审查独立核对原文） |

---

## 三、Findings 全列表

### P0（阻塞，必须修复后复审）——1 项

**P0-1 · CLI `baseline-evaluate --now` 非法值 → 未捕获异常 exit 1 冒充 gate fail**
- 位置：`baseline_metadata.py` L916（`datetime.fromisoformat(args.now)`）+ L936 except 面（仅捕 `ContractViolation`/`BaselineMetadataError`，裸 `ValueError` 穿透）。
- 事实（复验 #3 实录）：`--now "not-a-date"` → `ValueError: Invalid isoformat string` traceback → 进程 **exit 1**。
- 影响：exit 1 是钉死的 `fail`（objective_missed）语义。引擎/CI 消费退出码时把 usage 错误误读为门失败 → 错误的阻断/告警决策。直接违反模块自钉契约（L80-83 "exit 3 on any usage/storage/contract error — a gate verdict must never be confusable with a command crash"）与 DoD 5 错误分类面。同族次要面：register 子命令的 storage `OSError`（`os.replace`/临时文件）同样穿透 except，违反「3 on storage error」（register 无 1 语义、误读风险低，可同修）。
- 修复建议：L916 改用 `_parse_timestamp("baseline-evaluate: --now", args.now)`（raise `ContractViolation` → 既有 except → exit 3），一行级；顺手评估 except 面是否收敛 `OSError` → 3。补 CLI `--now` 非法值负例测试（钉 exit 3）。

### P1（强烈建议本轮修改）——1 项

**P1-1 · 观察侧口径/新鲜度输入省略即静默跳过检查，与 `now` 的 fail-closed 标准不一致**
- 位置：`evaluate` 签名 L625-628（四个 Optional 参数）+ L729-736/L760-773 的 `is not None` 门。
- 事实：四参数缺省 None → 对应检查跳过 → 观察直接进阈值比较。CLI 省略 `--observed-unit/--observed-scope-digest` 即走此路径通过（现有 CLI 测试即如此）。而同函数 `now` 缺失 + `max_age_days` 在场 → raise（fail-closed）。docstring 未声明「None = skip check」语义。
- 影响：批 1 接线后调用方省略口径参数 → W-3 同型的口径漂移静默通过——正是本票要消灭的事故形态；模块自钉「无可信基础 = NOT_EVALUABLE」承诺出现静默旁路。
- 修复建议（择一）：(a) 接线前将口径参数改必需，或 (b) 省略时 diagnostic 显式标注 checks-skipped，或 (c) 至少 docstring 显式声明省略语义并由接线票定义强制面。R1 复审时核对处置。

### P2（建议修改，可遗留但须记录）——3 项

**P2-1 · 接线形态偏离声明的 governance_cost pattern + 选项集双重事实源**：`_register_option_map`/`_add_register_options` 手工双维护（17 键 vs 17 项），handler 二次解析 Namespace→argv→main。接线票落地时 MUST 统一为 `add_arguments` 导出面或建立单事实源，否则新增选项漂移即静默丢参数。
**P2-2 · DoD 7 负例缺口（含并发覆盖裁决的附条件）**：(a) 并发覆盖 ❌——裁决见 §二④，论证成立附两条件（批 2.0 补负例或先接锁；单写者约束显式化）；(b) `load_registry` key≠row gate_id 拒绝路径（L495-498）无负例测试；(c) 非 UTF-8 字节流拒绝路径（L468-473）无直接测试；(d) 崩溃点 temp 清理无故障注入测试。
**P2-3 · `floor_value` 在 `direction="lower"` 时静默忽略**：L704 仅 upper 分支检查 floor；lower 方向的对称矛盾（threshold 高于冻结天花板）无机制，CLI help 未声明方向语义。建议：lower+floor 组合入口 `ContractViolation`，或文档显式「floor 仅 upper」。

### P3（讨论/记录）——5 项

- **P3-1** 豁免四要件未承载且留白未显式声明——建议 docstring 补一句「waiver 结构属后续流程」（对照 `BaselineConflict` 对 retirement 的显式留白写法）。
- **P3-2** `evaluate(registry=...)` 收任意对象，`str()` 后不存在即读作空注册表——误传 dict 得到误导性 `baseline_missing` 而非类型错误。建议 isinstance 校验。
- **P3-3** `pass` + `continuation=block` 组合的消费者语义未在 contracts.py 注释/`EvaluationOutcome` docstring 固化（contracts 只举例 not_evaluable+block）——接线时建议钉死「block 是类别姿态，pass 恒不阻塞」。
- **P3-4** 申报行数与实际不符：申报 872/526 行，实际 1003/620 行（+15%/+18%）——早期快照口径，非缺陷；测试方法数 53 申报属实。
- **P3-5** `cmd_baseline_register`/`cmd_baseline_evaluate`/`_namespace_to_argv` 无直接守护测试（现测试全走 `main(argv)`）——接线时补 dispatch 面测试。

---

## 四、硬门槛裁决

| 门槛项 | 判定 |
|---|---|
| P0 阻塞问题数 = 0 | ❌ **=1（P0-1）→ 阻断合并** |
| 5 维度全覆盖 | ✅ 正确性（②③+P1-1/P2-3）/安全性（DoD0+注入面无+输入正则）/可维护性（P2-1/P3-1/P3-3）/性能（registry 全量重读 O(n) 每次评估——行数量级个位，非问题；digest SHA-256 单次）/测试覆盖（53 测试+缺口 P2-2） |
| 每条发现标注级别 | ✅ P0×1/P1×1/P2×3/P3×5 全标注 |
| 设计一致性（vs ADR/契约） | ✅ contracts.py 三导入只读、冻结元组逐字一致；arch §4 分轴/七要素/确定性矛盾三分全忠实（豁免留白见 P3-1） |
| AI 代码专项 5 项 | ✅ 全过（过度实现有条件 → P3-5） |

## 五、遗留项（若 Coordinator 接受 P1 延期处置）

| 项 | 遗留去向 | 关闭条件 |
|---|---|---|
| P1-1 | 批 1 接线票前置 | 接线前口径省略语义决策入账 + docstring 显式化 |
| P2-1/P2-2/P3-5 | 批 2.0（接线/锁面/复跑） | 形态统一 + 并发负例或锁面 + dispatch 测试 |
| P3-1/P3-2/P3-3/P3-4 | 随 R1 修复或候选池 | 择机收敛 |

## 六、申报核验汇总

Developer 申报 8 项：53/53 ✅ · verify 全量 PASSED ✅ · archguard PASS ✅ · 契约/injection/registry 回归（未逐项重跑，archguard R5 cli keys 88/88 frozen + 全量 verify PASSED 旁证）△ · dry-run exit 实录 ✅（exit 0/1/2 三态复验一致，但 crash 路径 exit 1 未申报——P0-1）· baselines.json 未创建 ✅ · 文件面冻结三处引用 ✅ · 行数申报 ✗（P3-4）。

---

*Review 方法披露：逐行读两审查对象全文（1003+620 行）+ contracts.py/round2-external/round3-external/version-plan/EVD-1099/1100/1104 原文比对 + registry.py/verify_workflow.py 接线面定位 + 4 项复验实跑（全程零产品代码修改、零 .governance 写入、零真实环境副作用）。*
