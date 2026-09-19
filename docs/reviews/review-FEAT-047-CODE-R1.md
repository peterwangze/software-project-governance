# Review FEAT-047 — CODE R1（定向复审 · BaselineMetadata provenance 机制）

> Round: **R1**（复审必达 T1 · 同 Reviewer · 前轮引用：`docs/reviews/review-FEAT-047-CODE-R0.md` = NEEDS_CHANGE/unresolved_blockers=1）
> 审查对象（工作树未提交）：`skills/software-project-governance/infra/baseline_metadata.py`（实测 1092 行）+ `infra/tests/test_baseline_metadata.py`（实测 744 行，64 测试方法）
> 复审性质：逐条比对 R0 findings（已修复/未修复/新引入）+ 修复面独立复验实跑。只读审查——本报告是唯一写产物。

---

## 总结论

# APPROVED_WITH_NOTES

**unresolved_blockers = 0**（P0=0 / P1=0 / P2=0（遗留已显式化）/ P3=3 项记录在案）

R0 唯一阻塞项 P0-1 已修复并经独立复演实证（exit 1→3）；P1-1 按 Coordinator 裁决复合方案落地且两层 fail-loud 语义经负例与 CLI 复演确认。剩余全部为非阻塞遗留，去向已显式（批 2.0 接线票/候选池）。按 code-review SKILL：无未解决 BLOCKING finding → 通过终态。

---

## 一、R0 findings 逐条比对（复审核心义务）

| R0 # | 状态 | 修复证据（文件:行） | 复验实证 |
|---|---|---|---|
| **P0-1** CLI --now crash exit 1 冒充 fail | ✅ **已修复** | L999 `_parse_timestamp("main: --now", args.now)`（ContractViolation → 既有 except）+ L1022-1027 `except OSError` → exit 3（register/storage 同族收敛）| **复演**：`--now not-a-date` → 结构化 `ERROR: main: --now: expected an ISO-8601...` + **exit 3**（R0 对照：ValueError traceback + exit 1）。负例 `test_cli_invalid_now_exits_three_not_fail` 在位 |
| **P1-1** 观察侧输入省略静默跳过 | ✅ **已修复**（复合方案） | 层①：`observed_unit/observed_scope_digest` 基线在场时必需 → `ContractViolation`（L781-788）；层②：event-based 基线缺 current 观测 → `not_evaluable` + 新 `instrument_missing`/`target_missing`（L790-807；`DIAGNOSTIC_KINDS` 扩 2 @ L185/187）；TTL（max_age_days 在场）event 观测保持可选（L822-836 不变）；docstring "Required-observation layering" 段 L660-682 | **复演**：缺 unit → exit 3、缺 digest → exit 3（消息精确指认缺哪个）；event-based 缺 current → **exit 2 + kind=instrument_missing + continuation=block**（fail-visible+分轴）；TTL 基线不传 current 观测 → pass（可选性正确）。负例：测试面 8 新增（EvaluationAxis）+ 3 新增（CLI）全在位，含分层序负例 `test_baseline_missing_still_reports_before_required_observations`（baseline_missing 先于必需观察报出）与分轴负例 `test_missing_expiry_observation_splits_by_policy_axis` |
| **P2-1** 接线形态/双重事实源 | ⏸ **留置批 2.0** | 按 R0 处置表原样留置（本票不动共享文件——已核实 registry.py/contracts.py 零改动） | 留置确认合理 |
| **P2-2** DoD7 负例缺口 | ⚠️ **部分修复**（主体到位，子项遗留显式） | 条件(2)✅：单写者约束 docstring 段 L42-47（明确 load→replace 无跨进程锁、多写者锁=FEAT-046 锁面、并发负例随批 2.0）；条件(1)✅：并发负例去向批 2.0 显式 | 子项 **(b) key≠row gate_id 负例、(c) 非 UTF-8 字节流负例、(d) 崩溃点故障注入——未补**，随批 2.0 守护测试同票补齐（遗留，非阻塞） |
| **P2-3** lower+floor 静默忽略 | ✅ **已修复** | L691-698 入口 `ContractViolation`（caller bug 分类正确，先于门判定路径）| **复演**：lower+floor → exit 3 + "refuse rather than ignore"；负例 `test_floor_with_lower_direction_is_refused` 在位 |
| **P3-1** waiver 留白未显式 | ✅ **已修复** | docstring L81-84：deliberately OUT of scope + 四要件（scope/reason/authorizer/expiry）"none optional, never an implicit pass" | — |
| **P3-2** registry 参数 isinstance | ✗ 未处置 → 候选池 | L483 `str()` 未变 | P3 级，留候选池可接受（记录） |
| **P3-3** pass+block 语义固化 | ◐ 部分承载 | `EvaluationOutcome` docstring 已有 "a release gate's pass still reports the blocking posture of its class"；contracts.py 为共享文件本票不可动——契约注释固化留接线 | 接受 |
| **P3-4** 申报行数失准 | ⚠️ **再次失准** | 申报 957/636 vs **实测 1092/744**（+14%/+17%）| 申报口径纪律问题持续（测试方法数 64 申报属实）；非缺陷，继续记录 |
| **P3-5** handler/option_map 无测试 | ⏸ 留置批 2.0 | 与 P2-1 同票 | 确认 |

**Developer 新增自修披露 2 处核验**：① f-string py39 兼容——当前全文无嵌套同引号 f-string（自修完成）；② helper 默认观测（`digest_state` L782-783）——纯消息辅助无行为风险。两处均无新引入问题。

## 二、R1 独立复验表（10 项实跑）

| # | 项 | 结果 |
|---|---|---|
| 1 | 64 测试套件实跑 | **64/64 OK, exit 0**（逐类计数 9+4+10+30+9+2=64 与申报一致） |
| 2 | P0-1 场景复演 | `--now not-a-date` → ERROR + **exit 3**（R0：exit 1+traceback）✅ |
| 3 | P1-1 层① 复演 | 缺 observed-unit → exit 3；缺 observed-scope-digest → exit 3 ✅ |
| 4 | P1-1 层② 复演 | event-based 缺 current 观测 → **exit 2 + instrument_missing + block** ✅ |
| 5 | P2-3 复演 | lower+floor → exit 3 ✅ |
| 6 | pass 主路径回归 | exit 0 + evaluation=pass ✅ |
| 7 | 三套回归实跑 | contracts **157**/injection **11**/registry **77** 全 OK ✅（与申报逐套一致——R0 未逐套重跑的项本轮补齐） |
| 8 | archguard-ratchet | PASS，0 violations ✅ |
| 9 | verify 全量 | **FAILED——范围外**：唯一 FAIL=`AGENTS.md @bootstrap-version=0.84.0 is stale (< active_version 0.85.0)`。已查明：verify_workflow.py 工作树 12 行 diff 全部为 REQUIRED_SNIPPETS 版本 pin 0.84.0→0.85.0（六处 plugin/manifest）——属 **0.85.0 发布链 bump 中间态**，与 FEAT-047 交付面无关（R0 时同命令 PASSED）。→ Coordinator 需在 0.85.0 发布链内收口该 bump 半途态，不计入本票结论 |
| 10 | 文件面/状态核验 | 本票两文件未跟踪 ✓；`registry.py`/`contracts.py` 零改动 ✓（文件面冻结维持）；`verify_workflow.py` 的 M 状态=上述版本 pin（非本票面，归属发布链动作——建议 Coordinator 在票面归属上留痕）；`baselines.json` 未创建 ✓（真实登记留 Coordinator） |

## 三、新引入问题扫描（R1 增量）

1. **P3-N1** `current_instrument_version=""`（空串非 None）→ 走 `!=` 比较报 `instrument_changed`（fail-visible，方向安全），但诊断语义略偏——接线时建议入口 `_non_empty_text` 校验（候选池）。
2. L839/L845 的 `is not None` 守卫在 L781 必需化后恒真——防御性冗余，无害，不要求修改。
3. `test_cli_event_based_missing_expiry_observation_not_evaluable` 断言 `kind ∈ {instrument_missing, target_missing}`——参数序决定实际恒为 instrument_missing，断言弱化但钉住 fail-visible 语义，接受。
4. 行为面更新自洽：`_evaluate` helper 默认补齐 current 观测、CLI exit-code-face 测试补齐口径参数、stock-row 测试补齐两观测——64/64 全绿佐证无隐性回归。

AI 专项（增量）：新增代码无 mock/硬编码返回/幻觉 API/TODO；新 diagnostic kind 经 `Diagnostic.__post_init__` 闭集校验（拒未知 kind 负例既有）✅。

## 四、硬门槛裁决

| 门槛项 | 判定 |
|---|---|
| P0 阻塞问题数 = 0 | ✅ =0 |
| 5 维度全覆盖 | ✅ 正确性（分层序/闭集/TTL 可选性复验）/安全性（caller bug 分层+exit face 收敛）/可维护性（docstring 三段新增：单写者/layering/waiver）/性能（无新热点）/测试覆盖（64 含 11 新增，负例族齐全；残余缺口已显式留批 2.0） |
| 每条发现标注级别 | ✅ 本轮新增 P3×1（P3-N1）+ 记录 P3-2/P3-4 |
| 设计一致性 | ✅ 复合方案与 arch §4 对齐：必需口径=provenance 核心、missing 观测=NOT_EVALUABLE 族（非 pass、非 caller 报错二分正确——观测缺失是评估基础不全非调用错误）、分轴继续由 policy_class 独立派生 |
| AI 代码专项 5 项 | ✅（增量复扫） |

## 五、遗留项（全部非阻塞，去向显式）

| 项 | 去向 | 关闭条件 |
|---|---|---|
| P2-2 残余（key≠row 负例/非 UTF-8 负例/崩溃点注入/并发负例） | 批 2.0（FEAT-046 锁面票随票补齐） | 守护测试负例补齐 + 锁面接线 |
| P2-1/P3-5（接线形态统一+dispatch 测试） | 批 2.0 接线票 | add_arguments 形态统一或单事实源 |
| P3-2/P3-N1（isinstance/空串校验） | 候选池 | 择机收敛 |
| P3-3（契约注释固化） | 批 2.0（contracts 消费面） | 接线时在契约面固化 pass+block 语义 |
| P3-4（申报口径纪律） | Developer 习惯项 | 后续申报以实测为准 |
| verify FAIL（AGENTS.md bootstrap 滞后 + verify_workflow 版本 pin 中间态） | **0.85.0 发布链（范围外，Coordinator 处置）** | bump 序列收口后 verify 复绿 |

---

*R1 方法披露：重读两文件全文（1092+744 行）逐条比对 R0 五+二 findings；独立复验 10 项实跑（64 测试/六场景 CLI 复演含纯净退出码/三套回归 157+11+77/archguard/verify/行数实测/文件面 git 核验）；范围外 verify FAIL 经 diff 逐行溯源（12 行全为版本 pin）。零产品代码修改、零 .governance 写入、复验临时登记均在系统临时目录且已清理。*
