# FEAT-049 独立代码审查报告 — R0（M0 契约冻结 · 0.86.0 批 0）

> 审查类型: Code Review（独立） · 轮次: R0 · 日期: 2026-09-19
> 审查者: Code Reviewer Agent（只读审查 + 本报告；未修改代码/.governance）
> git 基线: b717835d88f4471660d00cc78e4e2ce126b084ec（工作树未提交变更）
> 语义基准: arch-consult-round2-external §1/§3/§4/§5+规划缺失③④ · arch-consult-round3-external P1-1/P1-2 · version-plan-0.86.0 §2 批 0/§3/R-F4/F5/F10
> 出范围确认: injection_budget.py（FEAT-050 在途）未出现在本票工作树，未纳入审查

---

## 总结论

**APPROVED_WITH_NOTES · unresolved_blockers=0**

- P0 = 0 · P1 = 0 · P2 = 1 · P3 = 6（全部 findings 见下文，无一阻塞合并）
- 五面契约与顾问裁决语义忠实（round-2/round-3 逐条对照通过）；FEAT-021 frozen 形状零破坏（0 删除 + 头部 hunk 纯增逐一核验）；99 存量基线勘正属实且零回归（独立复算）；fixtures pin revision 全量可复算（独立重算命中）。
- 依据: code-review SKILL——`APPROVED_WITH_NOTES` 仅用于无未解决 BLOCKING finding 的审查；本票无 P0/P1，P2 为论证记录修正建议、P3 为讨论/记录项。

---

## 1. 审查范围（Developer 清单五处 vs 实际变更面）

git status/diffstat 实测：M 态文件恰为本票三处，无越界修改——

| # | 对象 | 变更 | 实测 |
|---|---|---|---|
| 1 | `skills/software-project-governance/infra/contracts.py` | 修改 | 573→1140 行（+567 / 0 删除）※任务描述"~1050"实为 1140（git 计数） |
| 2 | `skills/software-project-governance/infra/tests/test_contracts.py` | 修改 | 1050→1603 行（+553 / 0 删除）；99 存量+58 新增=157 ✓ |
| 3 | `skills/software-project-governance/infra/fixtures/m0/`（新） | 未追踪 | 五面 fixtures + manifest.json（6 文件） |
| 4 | `benchmarks/closure/protocol.md`（新） | 未追踪 | 91 行量测协议 |
| 5 | `skills/software-project-governance/core/manifest.json` | 修改 | +5 行（repo_only dir `benchmarks/closure/` + glob `benchmarks/closure/**/*.md`） |

出范围并行文件（docs/planning/*、docs/reviews/* 等）未发现被本票触碰。

---

## 2. 五维度审查结论（全覆盖）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | 新增 514 行逐行读毕：全部声明式/纯函数（零 I/O、零内部依赖）；`decide_operation_replay` 三值判定 fail-closed（畸形 fingerprint 拒判）；`WriterResult.__post_init__` 交叉不变量完备（ok⇒new_revision+execution、ok+failed 矛盾拒绝、error 禁 new_revision、conflict 必带 observed_revision、validation/conflict/retryable 禁 execution）；`SchemaVersionWindow` 拒空窗/倒窗、refuse 双侧越界；`MappingProxyType` 只读表防运行时篡改（有测试）。157/157 实测通过 |
| 安全性 | ✅ 通过 | 零 I/O 面（无 open/subprocess/urllib）；模型输出防线：JSON 往返显式 rehydrate、raw dict 注入 EvidenceRef 位被拒（fail-closed，有测试 pin）；无硬编码密钥；`check-injection-contract` PASSED（3 files/23 anchors，独立复跑） |
| 可维护性 | ✅ 通过（2 项 P3） | 五 face 分节注释携带出处锚（§/P1-x 逐条）；命名一致；单函数长度合规。P3-4/P3-5 见 findings |
| 性能 | ✅ 通过 | 纯校验逻辑，无循环 I/O、无 O(n²) 面；`_FULL_*_RE` 模块级预编译 |
| 测试覆盖 | ✅ 通过 | 58 新增测试按 face 分五类，覆盖：合法/非法构造、fixture-模块一致性双向 pin（replay_cases/window_cases/error_code_dispositions 全表比对）、JSON 往返+显式 rehydrate、manifest hash 完整性、pin span 重算、consumers 声明。存量 99 零回归 |

---

## 3. AI 代码专项 5 项检查（全部完成）

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | 新增区（contracts L627-1140 / tests L1054-1603）grep `mock|Mock|patch` = 0 命中；全部实逻辑 |
| 2 | 硬编码返回值 | ✅ 无 | `new_operation_id` 为真实 uuid4 生成器；校验函数真实判定；fixture 样本经模块重放（`test_writer_io_fixture_samples_replay_through_module`）非摆设数据 |
| 3 | 幻觉 API | ✅ 无 | 新增区 API 面 = `uuid.uuid4().hex`/`re.compile`/`types.MappingProxyType`/`dataclass`/`typing`/`object.__setattr__`——全部 stdlib 文档化 API；R3 AST 白名单测试（ALLOWED_IMPORTS stdlib-only）在 157 套件内通过 |
| 4 | 未实现 TODO | ✅ 无 | grep `TODO|FIXME|XXX|NotImplemented` = 0 命中 |
| 5 | 过度实现 | ✅ 无 | 批 1 票逻辑零预实现：无锁实现/无存储写入/无 CLI/无投影逻辑——仅词表枚举+纯校验+数据类形状，符合"M0 冻结跨票接口非全部内部细节"（round-3 P1-1）；writer_io.json `not_frozen_here` 字段显式声明内部细节不入冻结面 |

---

## 4. 审查重点逐项结论

### ① 五面契约 vs 顾问原文语义忠实度 — ✅ 忠实

| 冻结面 | 顾问原文（对照面） | 实现与判定 |
|---|---|---|
| operation_id 产生/重试复用/同 ID 异载荷 | round-3 P1-1 四要素；round-2 §1「相同 operation_id 重试返回原结果；同 ID 不同输入拒绝」 | `op-[0-9a-f]{32}` + `new_operation_id()` 单一生成源；`decide_operation_replay` 三值 execute/replay/conflict ✓。**作用域要素仅由模块 docstring L89（"global scope"）+ fixture `"scope": "global-across-governed-writers"` 承载，Face 1 正文与测试未规范断言**→P3-2 |
| 状态与合法迁移 | round-3 P1-1；behavior-protocol §4.6（L516-531 转移表、C3 熔断=3、C4 通过终态） | 7 态/12 边与 §4.6 状态机逐边吻合（review→approved=T3 / review→dev=T1 / review→blocked=T2+T4 / blocked→dev、→triaged=交付裁决 C）；`REVIEW_CIRCUIT_BREAKER_ROUNDS=3` ✓ |
| UNKNOWN / NOT_EVALUABLE 分轴 | round-2 §4「评估结果 PASS/FAIL/NOT_EVALUABLE；继续策略 BLOCK/ADVISORY」三分离 | `EXECUTION_RESULTS`(succeeded/failed/unknown) × `EVALUATION_RESULTS`(pass/fail/not_evaluable) × `CONTINUATION_POLICIES`(block/advisory) 三轴独立，无交集有测试断言（set 交集为空）✓；DELIVERY_VERDICTS/RUNTIME_POSTURES 第三层分轴（round-3 P1-3 / version-plan §4）✓ |
| 错误码 8×4 分类 | round-2 §5 DoD 条 5「区分校验失败/冲突/可重试/需介入」 | 4 处置类 verbatim（validation/conflict/retryable/manual）；8 码闭枚举逐码有出处锚，映射逐一合理（schema_version_unsupported→validation、revision_conflict→conflict、lock_contention→retryable、manual_intervention→manual）；`RESULT_OK="ok"` 置于错误枚举之外有论证 ✓ |
| SchemaVersionWindow 拒写 | round-2 规划缺失③「旧 CLI 遇新 schema 拒写」「新格式产生新数据后不能靠恢复备份回退丢数据」 | 窗口 [minimum,current] 双侧拒绝、拒绝高于 current 有专测（"never guesses or downgrades"）；bump discipline 含备份回退禁令（fixture `bump_discipline`）✓ |
| EvidenceRef 五类型 | round-2 §3 引用类型表 | repo_file/git_object/governance_id/url/human_observation 五类 verbatim + 逐类语义吻合；`REFERENCE_VALIDATION_STATES`（可解析/不可解析/暂不可验证）与 verdict 分离（"CLI 绝不从文件存在推导测试通过"）✓；URL 默认不联网验证 ✓ |
| WriterRequest/WriterResult 最小 I/O | round-2 §1 五步（task ID/期望版本/目标状态/证据引用 → 返回新版本+结果码） | 请求六字段=五步提交面+幂等身份（operation_id/fingerprint）；结果含 CAS 观测回传、`execution` 外部动作态（源已提交投影待修复=manual+succeeded；push 超时=manual/ok+unknown，查世界不信日志）✓ |

### ② frozen 形状零改动核验 — ✅ 满足约束

git diff（-U0）11 hunks 逐个核验：**0 删除 0 修改行**。
- 尾部追加 1 hunk：`-573,0 +627,514`（契约主体，EOF 追加）✓
- 头部 10 hunks 全部纯增：模块 docstring +20 行（M0 节说明）；`import uuid`/`from types import MappingProxyType` 2 行；`__all__` 扩展 8 hunks +32 行（全部为新增导出名插入，未动既有条目）
- 判定说明：「只允许追加节」若按"仅文件尾追加"字面理解，头部 import/__all__ 扩展超出字面；但 FEAT-021 frozen 形状的承载（全部既有类/函数/常量定义行）零触碰，且存量形状守护测试（`AdapterVsFrozenShapeTests`、R3 AST 零 I/O 白名单）全数通过——**不破坏既有 frozen 形状**约束成立。测试侧 ALLOWED_IMPORTS 白名单扩注（uuid/types）即该测试设计的预期变更路径（"add it here in the same reviewed change"），带注释留痕 ✓

### ③ 99 基线勘正独立复算 — ✅ 属实

- HEAD `def test_` 计数 = **99**（git show 独立计数两次）；工作树 = **157**（+58）
- HEAD 套件在临时目录独立运行：**99 passed**（首跑 2 failed 为提取伪影——`SNAPSHOT_PATH` 相对读取缺 `contract_matrix/snapshots.json`，补 HEAD 版快照后 99/99）
- version-plan §2 仍写「87 存量」——FIX-303 在规划定稿后追加 12 测试致口径漂移，Developer 勘正为 99 正确→P3-3 记录

### ④ fixtures manifest 完备性 — ✅ 完备（独立重算全命中）

- `contracts_module_sha256` 重算命中；5 个 fixture sha256+bytes 逐一命中；pin revision 两源（behavior-protocol.md [512,556] / SKILL.md [223,230]）按 manifest 内 `span_hash_recipe` 独立重算 content_sha256+file_sha256 **全部命中**；span 内容与 section 声明精确对齐（512=step 4.6 节头、556=T4/Check 行末，无越界裹挟）
- frozen_revision（id m0-r1/规则/验收命令）、consumers（三批 1 票 read-only + 消费面声明）、change_rule（契约变更流程四步）齐备 ✓
- pin 定位诚实：`test_pin_revision_hashes_still_resolve` docstring 明示"故意断"语义（维护性编辑触发重置 pin 而非静默通过）✓

### ⑤ protocol.md vs round-2 量测要素 + round-3 P1-2 — ✅ 字段级吻合

- LLM 往返四规则（逻辑计 1/流式不另计/工具结果后再响应另计/传输重试单列）1.1~1.4 verbatim ✓；起止点+排除段（wait_human/wait_external 分列）✓；三路径分类（standard/exception/excluded）+ 三维验收口径 + 门槛变更纪律（禁止测后改门槛）✓
- 固定用例组三路径（standard-success/conflict/recovery）与 P1-2 一致；用例组 C 三边界 kill+resume 零人工修复=批 2.2 混沌门口径 ✓
- runs 规格：`runs/<run-id>/{manifest.json, results.jsonl, summary.md}` 结构、manifest 必备字段表（model/prompt_template/tool_config/code_revision/use_case/path_class）、results.jsonl 逐行字段、summary.md 必备项——字段级齐备 ✓；标准库生成/敏感脱敏/测量工件 JSON≠业务存储 JSON 化前移/M2 导入保留双时间戳/R-F10 固定措辞 ✓
- 边界披露：`cases/` 物理文件与 `runs/` 递延批 2.x（头部显式声明）——本票冻结用例组定义而非可运行用例，属披露性递延（写入器尚不存在，无法先行）→P3-5 记录；round-2 规划缺失④的扩展指标（首次写入成功率等）未入 summary.md 必备集（其冻结依据 version-plan §3 亦不含）→P3-6 记录

### ⑥ manifest.json 同步面 — ⚠️ 同步正确，论证不成立（P2-1）

变更本身：repo_only dir + `benchmarks/closure/**/*.md` glob，当前树 `check-manifest-consistency` PASS（803 canonical，独立复跑）。但「benchmarks glob 不含 runs——误追踪由 check-manifest 捕获」的论证**两半均与实现事实不符**，详见 findings P2-1。

### ⑦ CAS 语义 — ✅

`decide_operation_replay` 严格三值（execute/replay/conflict），畸形输入拒判而非给值 ✓；`WriterResult` conflict 处置码强制 `observed_revision`（缺失即 ContractViolation，含中文锚引 round-2 §1），非 conflict 码携带 observed_revision 同样拒绝（channel 专属）✓；`expected_revision` 不匹配"永不自动换版执行"落实为形状约束（error 禁 new_revision）✓

---

## 5. 独立复验表

| # | 项 | Developer 申报 | 独立复验 | 判定 |
|---|---|---|---|---|
| 1 | test_contracts 全量 | 157 passed | `pytest -q` → **157 passed** (0.14s) | ✅ 一致 |
| 2 | 99 存量基线勘正 | 87→99（FIX-303 漂移），99/99 零回归 | HEAD 计数 **99**；HEAD 套件临时目录运行 **99 passed**（补 HEAD snapshot 后） | ✅ 一致 |
| 3 | pin revision 可复算 | test_pin_revision_hashes_still_resolve | 独立重算 contracts_module_sha256 + 5 fixture hash/bytes + 2 pin span content/file sha256 **全命中** | ✅ 一致 |
| 附 | check-injection-contract | PASS | 复跑 **PASSED**（3 files / 23 anchors） | ✅ |
| 附 | test_registry | 77 passed | 复跑 **77 passed** | ✅ |
| 附 | check-manifest-consistency | verify 全量申报 PASSED | 复跑 **PASS**（803 canonical） | ✅ |
| — | verify 全量 / archguard R1~R7（contracts 保持 L0 干净节点） | 申报 PASSED / 不升 | 未独立复验（复验预算 1~3 项已用于上三项） | 申报值 |

---

## 6. Findings

### P2（建议本轮修改，不阻塞）

- **P2-1 manifest 同步面守卫论证与实现事实不符**（`core/manifest.json` L892/L907 + `checks/manifest.py` L140/L195/L444-447）
  - 事实 a：glob `benchmarks/closure/**/*.md` 经 `Path.glob` 展开，`**` 跨层匹配——本审查实证 `benchmarks/closure/runs/r1/summary.md` 被命中（pathlib 语义证明已运行），「glob 不含 runs」对 runs 的 .md 工件不成立。
  - 事实 b：未被 glob 命中的 runs 工件（results.jsonl/run manifest.json）位于 canonical dir 条目 `benchmarks/closure/` 之下，`check_manifest_consistency` 的 covered_by_dir 前缀豁免（L444-447）将其排除在 untracked 报告外——**check-manifest 结构上无法捕获 runs 误追踪**。
  - 真实防线 = protocol.md §5 / version-plan R-F5「runs/ 由创建批次加入 .gitignore」+ git ignore 拦截普通 `git add`——已披露但属批 2.x 义务、无机器守卫。
  - 影响：同步今日正确（PASS 复验）；风险在批 2.x 若漏 .gitignore，原始 trace（已要求脱敏）入 git 历史，且无任何检查报警。
  - 建议：①修正该论证的留痕记录（票注/evidence），不得作为既有守卫引用；②批 2.x runs 落库票的 DoD 显式列入 .gitignore 增补硬项；或③经契约变更流程评估在本票收尾预置 `.gitignore` 行 `benchmarks/closure/runs/`（超出本票冻结文件面，须 Coordinator 裁决，本审查不改码）。

### P3（讨论/记录，不要求修改）

- **P3-1 operation_id 作用域未在代码 Face 1 规范声明**（round-3 P1-1 四要素之一）：仅模块 docstring L89 摘要（"global scope"）与 fixture `"scope": "global-across-governed-writers"` 承载；fixture scope 字段无测试断言，仅读 contracts.py 的批 1 消费者可能漏看作用域规范。建议后续在 Face 1 docstring 补一句（走契约变更流程）。
- **P3-2 WriterRequest 未承载 schema_version 载点**：face 4 冻结了字段类型/窗口/拒写规则，face 5 最小 I/O 未声明 schema_version 在请求/记录中的位置——三批 1 票各自决定存在口径分叉风险（manifest consumers 已声明 FEAT-047 消费"schema_version 字段"）。建议批 2.0 集成验收前在契约引用文档显式声明各记录族载点。
- **P3-3 version-plan §2「87 存量」数字陈旧**：HEAD 实测 99（勘正属实、99/99 已验证）；规划文档本身未回改。批 2.0 复跑文档应以 99 为准。
- **P3-4 `__all__` 排序微瑕**（contracts.py L149-151 区段）：`SchemaVersionWindow/WriterRequest/WriterResult` 置于 `TASK_STATES/TASK_TRANSITIONS` 之后，破坏既有字母序。纯外观。
- **P3-5 protocol `cases/` 物理文件递延批 2.x**：已在 protocol.md 头部披露（本票冻结 §4 用例组定义）；写入器批 1 后才存在，先行落库只能是空壳——披露性递延，记录备案。
- **P3-6 round-2 规划缺失④扩展指标未入 protocol summary.md 必备集**（首次写入成功率/投影漂移人工恢复次数等）：本票冻结依据（round-3 P1-2 要素清单、version-plan §3）均不含它们；「提前退出」事件类型亦未显式列入 results.jsonl event 枚举。建议批 2.x 首次实测前评估是否补列。

### 边缘问题（记录，不计级）

- 任务描述行数口径 "573→~1050" 实测 573→1140（git 计数）；"99+58=157" 精确。
- `expected_revision` 限定 ≥1，"新增记录族首写（无前版=0）"场景无表达——批 1 三票均为既有记录面更新/追加，不阻塞；契约冻结后此形状约束长期存在，届时按变更流程处置。
- HEAD 基线临时目录复跑首现 2 failed 为本审查提取伪影（缺 snapshots.json），非回归——已在复验中排除并留痕。

---

## 7. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞数 | =0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5 有结论（§2） | ✅ |
| 每条发现标注级别 | 100% | P2×1 + P3×6 + 边缘记录，逐条有级 | ✅ |
| 设计一致性检查 | 已完成 | §4① 五面逐条对照顾问原文 + §4② frozen 形状对照 version-plan 约束 | ✅ |
| AI 专项 5 项 | 全部完成 | §3 五项逐一有结论 | ✅ |

**结构化字段：`unresolved_blockers=0`**

复审提示（Coordinator 用）：本票若因 P2-1 建议返工，属非阻塞改进——按 M7.4，返工后 MUST 重 spawn 同一 Reviewer 复审（R1，注入本报告路径）；亦可采纳为 notes 直接进入关闭证据四项核对（谁交付/产物在哪/验收命令/哪些票被阻塞——批 1 FEAT-042R/046/047 为被阻塞票）。
