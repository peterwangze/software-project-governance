# 审查报告 — FEAT-040-CODE-R0

- **任务**: FEAT-040 — 多平台回归 + 灰度开关 + 回滚（切片 A 集成收尾）
- **Round**: 0（首轮审查——无前轮 findings 可引用；无 `prev_report`）
- **审查者**: Code Reviewer Agent（只读审查；唯一写操作 = 本报告）
- **审查对象**: 工作树未提交变更集（27 项）+ 活体投影面
  1. `skills/software-project-governance/infra/behavior_profile.py`（**新增**，389 行 / 16,178B）
  2. `skills/software-project-governance/infra/tests/test_behavior_profile.py`（**新增**，432 行 / 19,863B / 34 用例 / 33 子测试）
  3. `skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py`（**新增**，244 行 / 11,734B / 15 用例）
  4. `infra/bootstrap_aggregate.py` — `behavior` 面（`_behavior()` L88-101 / L613 / L674-675 / L727-729 / L884-885）
  5. `infra/governance_cost.py` — `--ttfa-acceptance`（L730-843 / L1008-1013 / L1053-1062）
  6. 协议文本 6 面（`commands/governance-init.md` / `commands/governance.md` / `commands/governance/bootstrap.md` / `SKILL.md` / `adapters/dsh/AGENTS.md.template` / `agent-presets/governance/agent.cordis.yml.template`）
  7. 投影 registry（`core/version-projections.json` declared_legacy_snapshots 10 条 / `core/manifest.json`）/ `release/projection.py::check_legacy_snapshots`
  8. 收尾面：`adapters/dsh/launch.py` / `infra/sync_entry_projection.py` / `commands/governance/snapshot-schema.md` / `release/projection.py`
- **验收口径（triage acceptance）**: 灰度开关可用 + 守护测试 / 安全边界明确 / 收尾清单处置 / 复验框架（RISK-055）/ 多平台投影同步 PASS
- **方法与限制（事实依据红线声明）**: 审查者工具面 = Read/Grep/Glob（+ 只读文件尺寸/行数度量）。**未执行任何测试、未运行任何 CLI、未做 git 操作**——凡涉运行时（pytest 计数、`git status` 的 dirty 归属、实际 token 计价）的结论一律标注「静态核验/未实测」，不作为通过依据。所有阻塞/通过结论均指向文件:行号或 Grep 逐字命中。

---

## 一、五维度审查

### 维度 1：正确性

- **解析链（优先级 + 落臂）逐行正确**：`resolve_behavior_profile`（behavior_profile.py:215-261）——`env_status=="set"` → env 臂；否则 `plan_status=="set"` → plan-tracker 臂；否则 `DEFAULT_PROFILE="modern"`（L240-245）。`classify_token`（L173-189）对 `None`/空串/纯空白 → `(None,"unset")`（L180-184），词表命中 → `"set"`，词表外非空 → `(None,"invalid")`（L189）。**非法值既不静默 legacy 也不静默 modern**：`profile=None` 落到下一臂，同时 `invalid` 列表显式记录（L233-238）——与 SKILL.md:84「非法值不猜——既不按 legacy 也不静默按 modern 执行，而是在 `behavior.invalid` 显式报告后落到下一臂」逐字一致。
- **节内读取正确**：`plan_tracker_value`（L192-212）以 `## ` 前缀截断 section（L203-204），只匹配 `- **key**: value` 形（`_CONFIG_LINE_RE` L167），key 精确等于 `behavior_profile`（L210）。负例测试 `test_plan_tracker_read_is_section_bounded`（test_behavior_profile.py:118-126）用「`## 项目总览` 内含同键」证明不越界 ✓。
- **回退表类目封闭**：`LEGACY_REVERTS` 4 条（L86-115）全部 `class=performance`；`ALLOWED_REVERT_CLASSES={performance}`（L82）。**FEAT-035 不在 `LEGACY_REVERTS`**——逐条读出 feats = {FEAT-034, FEAT-034, FEAT-036, FEAT-038}（L88/96/102/109）；FEAT-035 仅出现在 `SAFETY_INVARIANTS`（L123）。守护测试 `test_feat035_is_not_revertible`（:145-152）双向断言 ✓。
- **契约机检 4 条规则实现完整**：`revert_contract_issues()`（L342-389）——① 类目越界（L361-366）② surface 重复（L367-369）③ invariant marker 空（L375-377）④ invariant id 重复（L378-380）+ FEAT 交集判 FAIL（L383-388）。**注**：规则④的「重复 id」分支无直接负例用例（见 P3-1）。
- **边界条件/资源管理**：模块纯函数、无 I/O、无文件句柄（`plan_tracker_text` 由调用方读入）；`behavior_face` 重复调用 `_behavior()`（L613/L674/L727/L884）依赖 `sys.modules` 缓存，幂等且无副作用。
- **`_next_actions` 排序正确**：`actions.insert(0, rollback)`（bootstrap_aggregate.py:727-729）在 `[:5]` 截断**之前**——legacy 时回退提示必居首位，与「5 项上限可能吞掉它」的注释（L724-726）一致 ✓。

### 维度 2：安全性

- **层 1（数据层）成立**：回退类目集合 `{performance}` 封闭 + FEAT 交集判 FAIL——「legacy 永不削减安全语义」是**本模块的属性**而非注释承诺（模块 docstring §2 L23-28 自陈）。三层中最强面 ✓。
- **层 2（文本层）成立**：5 条不变量 marker 逐字在位——SKILL.md:93-97（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达）与 `commands/governance/bootstrap.md:61-64` 均含全部 5 个 marker；`PROTOCOL_SURFACES` 6 面全部携带 `行为灰度开关`（Grep 逐字命中：governance-init.md:219/299/581、governance.md:99、governance/bootstrap.md:33、SKILL.md:74、AGENTS.md.template、agent.cordis.yml.template:59）；守护 `test_safety_invariant_markers_are_published`（:184-203）同时钉住「两个最富面必须携带全部 5 条」——单文件重写无法静默收窄 ✓。
- **层 3（非干扰层）成立（**但仅覆盖 env 臂——见 P1-1 / P2-2）**：`test_legacy_changes_only_the_declared_faces`（:307-322）双跑 modern/legacy，断言除 `behavior` + `next_actions` 外 10 个面（resolve/health/project/gates/tasks/risks/migration/candidates/recent）逐面相等，且 `health.state` 两态均 `deferred`——**不借绿**。`resolve` 面（fail-closed 权威）在比较集内 ✓。
- **开关不可达 fail-closed 通道**：AST 守护（:378-404）钉住 import 集合 ⊆ {os, re, __future__}，并以一个变更型调用名**封闭集合**（写文件 / 删除 / 执行 / 权限 / 目录类，见 :398-400 字面集合）断言零命中；`test_resolver_does_not_swallow_a_broken_env_mapping`（:415-421）证明 resolver 不吞宿主异常。**结构上无法旁路 `resolved_root_ok`** ✓。
- **输入校验/注入/敏感数据**：词表封闭（不做前缀/包含匹配）；无 SQL/shell/HTML 面；无密钥。全部输入来自 os.environ 与 plan-tracker 文本。**P3-2**：env 原值回显进 `behavior.env_value` 与 `invalid[].value`（L253-255、L235-238）→ 若用户误把 token 设进该变量会随聚合面进入 agent 上下文（字段语义上仅为开关 token，风险低）。
- **真实环境防护（M7.7）自查**：本次审查未触碰 `$HOME`/`$DSH_HOME`/仓库外路径；只读文件尺寸度量在仓库内。Reviewer 无写操作（本报告除外）✓。

### 维度 3：可维护性

- **单一事实源纪律**：`LEGACY_REVERTS`/`SAFETY_INVARIANTS` 是 canonical 表，协议文本与投影由 marker 守护与表对齐（docstring §3 L30-36 自陈「declared ≠ enforced，enforced 是两臂都不实现安全回退」——诚实且准确）。
- **命名/结构**：函数短小（最长 `resolve_behavior_profile` ≈47 行、`revert_contract_issues` ≈47 行，均 <50 行阈值）；模块 389 行、单一职责（解析 + 渲染 + 契约机检），无上帝模块迹象。
- **注释质量**：docstring 与实现一致——逐条核对无 overclaim：§1 双臂/优先级（对应 L240-245）✓；§2「安全边界是数据不是散文」（对应 L82/L120）✓；§4「fail-closed on garbage, never a guess」（对应 L189/L240-245）✓；R6/R2 边界声明（对应函数内 import 与 AST 守护）✓。
- **P3-3（重复散文）**：`next_action_line`（L299-301）硬编码 5 条不变量名称的散文，与 `SAFETY_INVARIANTS`（L120-151）构成双源——表变更时散文不会自动跟随（当前一致，逐字核对 ✓）。
- **收尾面可维护性**：`_section_content`（sync_entry_projection.py:406-418）把 sticky 臂与 drift 报告收敛到**单一口径**，docstring 明确记录原缺陷（sticky 比 RAW span、报告比 rstripped，L409-416）；`launch.py:1735-1744` 的 `newline=""` 带根因注释（Windows 文本层把整文件 LF→CRLF）。两处均为「修根因 + 留痕」而非补丁式修补 ✓。

### 维度 4：性能

- **冷启动面 Δ0**：`behavior_profile` **只**在 `bootstrap_aggregate._behavior()` 内被函数局部 import（bootstrap_aggregate.py:100），全仓 Python 面 Grep 无其他导入点 → 不进入引擎 R6 冻结启动面。守护在册：`test_registry.py:958` `assertEqual(budget["import_count"], FROZEN_ENGINE_IMPORT_COUNT)`（=199，L111）+ `test_engine_baseline_is_the_frozen_196_module_caliber`（:942-963）的**可执行口径** `_engine_startup_face()["count"]`。申报「R6=199 不重锚」**结构成立**（静态核验；未实测计数）✓。
- **热路径零 I/O**：resolver 是纯内存 O(n) 单遍（n = plan-tracker 行数，文本已由调用方读入）；`revert_contract_issues()` 仅测试调用 → 运行期零成本。
- **输出预算**：`behavior` 面为紧凑 id 列表（`behavior_face` L264-280 只投影 profile/source/env_var/plan_tracker_key/reverted/invariants/invalid），不携带全表（`render_boundary_table` 仅供文档面）。守护 `test_face_fits_the_aggregate_output_budget`（:334-336）钉住 ≤`MAX_JSON_BYTES`（8192）✓。
- **P3-4（预算 clamp 语义）**：`_enforce_projection_budget`（bootstrap_aggregate.py:769-829）的 4 级裁剪不含 `behavior` 专属档；极端溢出时落到 ④ 逐串裁剪（`_EMERGENCY_CLIP=120`），回退提示行（≈110 字符）会被截断。缓解：结构化 `behavior` 面（`invariants` 5 条 id）不受字符串裁剪影响，权威面仍在。
- **索引口径**：`--ttfa-acceptance` 复用 `scan_sessions` 已产出的聚合（governance_cost.py:762-768 docstring 明示「no second pass over the traces」），无 N+1 ✓。

### 维度 5：测试覆盖

- **规模实证（静态计数）**：`test_behavior_profile.py` 34 个 `def test_`（与申报 34 一致）+ **33 个子测试**（`subTest` 站点 6 处，逐站参数化计数：:89 词表 legacy 7 + :93 词表 modern 5 = 12 / :112 空白 3 / :234 四模板 4 / :318 十面 9 / :409 五形 5 → 12+3+4+9+5=**33**，与申报 33 一致）✓；`test_projection_legacy_snapshots.py` 15 个用例（与申报 15 一致）✓。**用例与子测试计数静态核对通过；"1,080 passed / 31F/3,439P" 未实测（无 pytest）**。
- **核心路径**：解析链 4 臂 + 词表大小写/空白 + 节界 + 非法值三态（:68-136）；聚合面 8 用例含双跑非干扰、next_actions 首位、文本行、invalid 披露、预算（:280-336）；CLI 子进程 2 用例（:355-366）。
- **边界/错误路径**：`resolve_entry` 不可解析面未直接测（switch 不参与该路径——由非干扰测试的 `resolve` 面相等间接覆盖）；`check_legacy_snapshots` 的**三条 FAIL 路径逐条有负例**（缺失 :181-191 / 收敛 :193-202 / 无理由 :204-213）+ 两条 fail-closed（非 list :222-231 / registry 不可读 :233-239）+ 空块合法（:215-220）✓。
- **反面/注入负例（本批最强项）**：`test_checker_catches_a_smuggled_safety_revert`（:160-171）注入 `class="safety"` + FEAT-035 条目 → 断言同时触发「outside」「BOTH」两类 issue；`test_checker_catches_duplicate_surface_and_markerless_invariant`（:173-182）注入重复 surface 与空 marker。**「真实表干净」与「checker 有效」被分开证明**——不是自证循环 ✓。
- **缺口**：plan-tracker 臂无端到端/CLI 证据（P1-1/P2-1）；census 数字无钉子（P2-2）；`invalid` 无 next_action（P2-3 相关）；duplicate-invariant-id 无负例（P3-1）。

---

## 二、Developer 申报逐项核实

| # | 申报 | 结论 | 证据（文件:行 / Grep 命中） |
|---|------|------|------------------------------|
| 1 | 安全边界三层（数据/文本/非干扰） | ⚠️ **层 1、层 2 全成立；层 3 仅 env 臂** | 层 1：`ALLOWED_REVERT_CLASSES` L82 + L361-366 + FEAT 交集 L383-388；层 2：SKILL.md:93-97 + bootstrap.md:61-64 全 5 marker，6 面 marker Grep 全命中；层 3：:307-322（10 面相等 + health deferred）。**特别点：FEAT-035 不在 `LEGACY_REVERTS`（4 条 feat = 034/034/036/038，L88/96/102/109），仅在 `SAFETY_INVARIANTS`（L123）✅** |
| 2 | 非法值不猜语义（落下一优先级 + invalid 报告） | ✅ 成立 | L180-189（unset/set/invalid 三态）+ L233-245（invalid 双记录 + 落臂）；测试 :98-109 断言 `source=plan-tracker` 且 `invalid[0]={arm:env, value:"legacyy"}`；聚合面 :329-332 + 文本行 L311-313（`INVALID … ignored (fail-closed, never guessed)`） |
| 3 | R6 Δ0（`_behavior()` 惰性导入） | ✅ 成立（静态） | bootstrap_aggregate.py:100 函数内 import；全仓 py Grep 无第二导入点；守卫 `test_registry.py:958`（199）+ `:942-963` 可执行口径。**计数未实测** |
| 4 | legacy 快照声明化（10 条 + 3 条 FAIL 路径 + census） | ⚠️ 声明与 FAIL 路径 ✅；**census 数字未钉** | 声明：version-projections.json:196-267 逐条读出 10 条，每条含 id/path/canonical/scope/reason ✓；机检：projection.py:272-305（4 类 issue）+ 三条负例测试 :181/:193/:204 ✓；`checked==10`（:95）、`declared_legacy_snapshots==10`（:165）✓。**census 282/55/39/177 无任何测试钉子 → P2-2** |
| 5 | 收尾清单抽验 5 项 | ✅ 5/5 成立 | ① `launch.py:1741-1744` `newline=""`（含根因注释 L1735-1740）✓；② `sync_entry_projection.py:406-418` `_section_content` 统一口径（sticky :385 与报告 :505 同经 `_normalized_content`）✓；③ DSH 方言互认：`THIN_SHARED_CORE_ANCHORS` 7 条（L67-75）+ `THIN_DIALECT_DSH_ANCHORS` 3 条（L87-91）+ `DSH_THIN_REQUIRED_EXTRA`（L101）＝**7 共享锚 + 4 extras**，守卫 `validate_dsh_thin_pointer`（L272-289）✓；④ snapshot-schema 面：canonical 与 fixture 均 1,781B 逐字节（只读度量）；⑤ **fixture governance.md 11,934B == canonical 11,934B**（独立只读度量），registry `fixture-command-governance-router`（version-projections.json:133-137）+ manifest `projection_ids` 含该 id（manifest.json:25）+ `member_match:"exact"` 12 patterns（manifest.json:55-74 ≡ `PROJECTION_SYNC_PATTERNS` verify_workflow.py:6639-6657 逐条相等）✓ |
| 6 | `--ttfa-acceptance`（阈值入码 + PENDING + 成对） | ✅ 成立 | 阈值常量 L742-747（25000/45000/`MIN_TURNS=3`）+ `TTFA_ACCEPTANCE_TASK="RISK-055"`；PENDING 分支 L798-805（`len < MIN_TURNS` → PENDING，理由含「borrowed green light」措辞）；成对：per-turn row 含 `ttfa_ms`+`time_to_work_ms`+`work_endpoint`（L780-788）+ 独立 `ttw_stats`（L796）；worst-first + 上限 20（L826-840）；`percentile` 空列表返回 None（L493-499）→ 空扫描不崩（测试 :865-867）；CLI 旗标接线 L1008-1013 / L1053-1056 / L1061-1062；测试 11 用例（test_governance_cost.py:853-942）含阈值非散文（:853-857）与旗标缺席不改变形状（:931-942）✓。**与 RISK-055 口径一致（MIN_TURNS=3 双方同值）** |
| 7 | resident 4,957/6,000（+669 分解 182/194/85/208） | ⚠️ 面在场；**数字与分解不可静态复核** | 5 个计入 resident 的面均含开关文本（persona agent.cordis.yml.template:59 / governance-init.md 4 模板 / AGENTS.md.template / AGENTS.md:13）；口径定义在 `checks/injection_budget.py:33-43`（`INJECTION_BUDGET_TOKENS=6000`、tier 求和）；口径基线在 DEC-211②（lightweight resident 4,288）。**+669 与 4,957 需跑 `check-injection-budget` 方能证实——未实测**。注：resident 档 `gate="advisory"`（DEC-210 / verify_workflow.py:20367），故本轮不构成硬阻断 |
| 8 | 路由层 11,934B/12,288B（余量 354B） | ✅ **逐字节证实** | 只读度量：`commands/governance.md` = **11,934B / 70 行**（与申报完全一致）；fixture 镜像同 11,934B；守卫 `test_router_layer_stays_within_budget_with_the_switch`（:251-254）`<= 12288` + 既有 `test_router_layer_within_injection_budget`（test_verify_workflow.py:20600-20606）；12288−11934 = **354B** ✓ |
| 9 | 测试规模 1,080 passed；全量 31F/3,439P（基线 31F/3,378P → +61） | ⚠️ 用例文件与计数静态在场；**通过/失败数未实测** | `test_behavior_profile.py` 34 用例 ✓ + `test_projection_legacy_snapshots.py` 15 ✓ + `test_governance_cost.py::Feat040TtfaAcceptanceTests` 11 ✓ = 60，与「+61 用例」同量级（未逐文件穷举，未实测） |
| 10 | AI 专项（无 mock/硬编码/幻觉/TODO/过度实现） | ✅ 5/5 过 | 见第五节 |

---

## 三、特别审查点

1. **dirty 4 项归属（其「内容 = 当前工具正确输出」声明）**：**静态对照成立，但 HEAD 态归属不可核验**。可核验部分：`fixture-command-governance-router` 的 `byte_copy` 内容与磁盘 fixture **逐字节一致（11,934B）**，且该 id 已同时登记在 `version-projections.json:133` 与 `manifest.json:25`，构不成「registry 有、manifest 无」或「manifest 有、registry 无」的任一半边 → 若这些改动即 HEAD 的全部缺失面，则 HEAD 上 release-projection 必 FAIL、工作树修复后 PASS 的因果链自洽（测试 `test_projection_plan_is_current_on_disk` :57-61 亦断言 `check_projections` 当前 PASS）。**不可核验部分**：具体哪 4 个文件处于 dirty、以及 HEAD 内容为何——Reviewer 无 git 工具面，不采信也不否定，标「未验证（结构自洽）」。**建议 Coordinator 在闭环前补一条 git 面证据（`git status --porcelain` + `git diff --stat`）**。
2. **开关描述的注入成本权衡（+669 tok 换回退通道）**：**值**。理由三条（均有事实锚）：(a) 成本面：resident 6,000 预算本轮为 **advisory**（DEC-210 / BUDGET_TIER_POLICY，verify_workflow.py:20367），4,957 不阻断任何门禁；(b) 收益面：回退通道覆盖 4 个已落地热路径协议变更（FEAT-034/036/038 三面 + 首次交互时序），而这 4 个变更在 AUDIT-154 里正是「一次落地四个协议变更」——无通道则回归只能手改治理文件；且同一开关被复用为 RISK-055 的复验路径（阈值入码 + 一键重跑），一份文本买两个用途；(c) 风险面：17.4% 余量（6,000−4,957）仍在，且回弹被 RISK-057 的四条缓解（分项表必打印 / 翻 hard 被测试钉住 / 0.85.0 瘦身候选池 / sha256_16 指纹）看住。**保留意见**：余量已从 DEC-211② 的 28.5% 降到 17.4%，再叠加两次同量级文本改动即触线——建议把「resident 余量」作为 0.85.0 入口模板瘦身的显式输入（非本任务阻塞项）。
3. **非干扰测试的双跑机制——**只测了一臂**（本审查的重点判定）**：`_payload(env)`（test_behavior_profile.py:273-278）只驱动 **env 臂**（`patch.dict`+pop `GOVERNANCE_LEGACY_BEHAVIOR`）；`test_legacy_changes_only_the_declared_faces`（:307-322）与 CLI 两用例（:355-366）同样只走 env。**plan-tracker 臂的端到端/聚合/CLI 三面证据 = 0**——单测只覆盖了解析器（:82-86）、`AggregateFaceTests` 唯一传入 `plan_tracker_text` 的一处是 `behavior_face(plan_tracker_text=None)`（:406-421）。代码路径静态读通（bootstrap_aggregate.py:674-675 把 `plan_text` 传入 `behavior_face`），但「项目级回退通道可用」这一验收点在其最强证据面（非干扰测试）上**无覆盖** → **P1-1**。
4. **FEAT-038 P2-3 委托（packet 9→11 由 Coordinator 机写）**：本任务面内可核验的部分已完成且自洽——router 进 registry（`fixture-command-governance-router`）+ manifest `projection_ids` 对齐 + `member_match:"exact"` 12 项与 `PROJECTION_SYNC_PATTERNS` 逐条相等；packet 计数（9→11）属 `.governance/execution-packets.json` 的机写面，**不在本次代码审查面**，未核验（按任务界定转 Coordinator）。
5. **dsh 方言「7 锚」口径核对**：申报「DSH 方言互认 7 锚」= `THIN_SHARED_CORE_ANCHORS` 恰 7 条（sync_entry_projection.py:67-75：bootstrap header / version line / resolve_entry / plan-tracker / SELF-CHECK / always-on / silent-track）✓；DSH 侧额外 3 条（H1 形 / `ask_user_question` DSH 拼写 / 包名，:87-91）+ 1 条 FEAT-040 必需 marker（:101）→ 校验器实际查 **11 锚**（`validate_dsh_thin_pointer` :281-288 拼接两个元组 + extras）。**口径区分清楚：7 = 共享存活核（口径独立），11 = 该方言校验总数；申报未把 11 说成 7，也无夸大**。

---

## 四、发现列表（P0~P3）

### P1-1（关键，blocking）— plan-tracker 臂（项目级回退通道）无聚合面/CLI 面证据

- **位置**：`skills/software-project-governance/infra/tests/test_behavior_profile.py:273-278`（`_payload` 仅 env 臂）、`:307-322`（非干扰双跑仅 env）、`:355-366`（CLI 仅 env）
- **事实依据**：Grep 全文件——`plan_tracker_text` 作为实参只出现在 :69/:78/:84/:102/:125/:131/:258/:412（解析器单测）；`AggregateFaceTests`/`CliSmokeTests` 两类的 payload 构造一律经 `patch.dict(os.environ, {ENV_VAR: ...})`（:274-276 / :344-346），无一处以 plan-tracker 文本驱动聚合。
- **影响**：CLAUDE.md / SKILL.md:81 / TOOLS.md TOOL-056 三处均把 plan-tracker 臂文档化为「项目级回退通道」（CLAUDE.md 原文：「项目级…`behavior_profile: legacy`（项目级）」；SKILL.md:81 给出「优先级 中」）。若 `_build_payload` 的 `plan_tracker_text` 传参在未来重构中丢失（bootstrap_aggregate.py:674-675 是唯一的接续点），守护网不会翻红——用户按文档设置后回退静默失效，而 CLI 仍报 modern。**这是「用户按文档操作但机制无证据」的直接风险，属验收点「灰度开关可用」的未覆盖半边**。
- **修复建议（低成本）**：在 `AggregateFaceTests` 增加一例——用 `tempfile` 构造带 `behavior_profile: legacy` 的 plan-tracker 文本（或 `patch.object(ba, "_read_text")` 返回该文本），断言 `payload["behavior"]["profile"]=="legacy"` 且 `source=="plan-tracker"`、`next_actions[0]` 含「灰度回退生效」；并补一例 plan-tracker 臂的非干扰双跑（可直接参数化 `test_legacy_changes_only_the_declared_faces`）。

### P1-2（关键，blocking）— 非法值只在 `behavior` 面披露，未进入 `next_actions`（JSON 快路径消费者无动作信号）

- **位置**：`infra/bootstrap_aggregate.py:692-730`（`_next_actions` 仅按 `profile=="legacy"` 插回退行，L727-729）
- **事实依据**：`next_action_line`（behavior_profile.py:286-301）以 `resolution.get("profile") != PROFILE_LEGACY` 为唯一判据返回 None（L293-294）；`behavior_face` 携带 `invalid`（L279）但 `_next_actions` 不读 `invalid`。文本面已披露（bootstrap_aggregate.py:884-885 → behavior_profile.py:311-313 `| INVALID … ignored (fail-closed, never guessed)`）✓，**JSON 面仅有 `behavior.invalid` 字段，无任何 next_action**。
- **影响**：用户/agent 以 `governance-bootstrap --format json` 为快路径（CLAUDE.md Step 1 明示这是默认入口）。用户敲 `GOVERNANCE_LEGACY_BEHAVIOR=legacyy` 想要立即回退 → 语义上「不猜 = 不静默」，但 **JSON 消费者看不出「你的回退没生效」**——只有主动读 `behavior.invalid` 才能发现；而 legacy 生效时那条回退提示恰恰是设计为「操作员忘了回退、必须第一时间知道」的（L724-726 注释自陈该意图）。同一意图对 invalid 不成立，语义不对称。
- **修复建议（低成本）**：`_next_actions` 读 `payload["behavior"].get("invalid")`，非空时 append 一行（如「灰度开关取值非法已被忽略：<name>=<value>（不猜，按下一优先级执行）」），可放在回退行之后、候选之前；或在 `next_actions` 首位插入并注明。守护测试补一例（`test_invalid_env_value_is_disclosed_in_the_face` :329-332 可扩展为断言 `next_actions` 含该信号）。

### P2-1（建议）— census 数字（282/55/39/177）为纯披露、无钉子，且被测试 docstring 引为事实

- **位置**：`infra/tests/test_projection_legacy_snapshots.py:142-152`（只断言 `divergent > 0`、`declared==len`、`undeclared_in_scope==[]`）；`release/projection.py:319-373`（census 计算）
- **事实依据**：全仓 Grep `282|55|39|177` 在测试面**零命中**（仅 :11/:184/:196 的 RISK-039/34.7k 字样）。census 四数在源码/测试中无断言，仅存在于 Developer 报告与 `:103-113` 的 docstring 叙述（「REPORTED by check_legacy_snapshots」）。
- **影响**：与 FEAT-039 R0 已发生的教训同型——报告数字未经复算即引为事实（DEC-211② 明确记「R0 度量夸大 29%」）。本处不是错误，是**不可证伪的披露**：树变化后这 4 个叙述数字可以静默失效。
- **修复建议（二选一）**：给 census 加**结构性**钉子（例如 `census["inventory"] == len(vw._projection_source_files(ROOT))` 与 `divergent + identical + absent == inventory - projected`），或把 4 个绝对数从报告/docstring 中撤下、只保留相对断言。**不要求钉死绝对数**（会随树漂移）。

### P2-2（建议）— `test_legacy_changes_only_the_declared_faces` 对未生效臂无反向守卫

- **位置**：`test_behavior_profile.py:307-322`
- **事实依据**：该用例 env-only；若 plan-tracker 文本（活体 `.governance/plan-tracker.md`）哪天被设为 `behavior_profile: legacy`，则 `modern = self._payload({})` 亦会解析为 legacy → `assertNotEqual(modern["behavior"], legacy["behavior"])`（:312）直接翻红，**但翻红原因被误读为「非干扰被破坏」，而非「活体配置改变了测试前提」**。同时仓库当前活体 plan-tracker 无该键（Grep `.governance/plan-tracker.md` 无 `behavior_profile`）→ 现状安全。
- **影响**：这是「守护测试对活体配置敏感」的脆弱点——正是被守护通道（项目级回退）启用时反而变红。
- **修复建议**：与 P1-1 同批修——把该用例改为参数化（env 臂 / plan-tracker 臂各一跑），plan-tracker 臂用自造文本而非活体文件，彻底消除活体耦合。

### P2-3（建议）— `invalid` 值无上界，`_payload_bytes` 序列化面可被环境变量放大（窄面）

- **位置**：`behavior_profile.py:235-238`（`str(raw_env)` 原样入 `invalid`）→ `bootstrap_aggregate.py:752-754`（`json.dumps` 计数）
- **事实依据**：`invalid[].value` 未做长度裁剪；`_clamp_strings` 仅在 4 级裁剪的第 ④ 级（超 8KB 时）才生效。
- **影响**：仅当用户把超长串设进 `GOVERNANCE_LEGACY_BEHAVIOR` 时才触发，实际放大极小（单环境变量），且第 ④ 级兜底存在。**信息性偏建议**。
- **修复建议**：入表时 `_clip(value, 80)`（本模块已有 CLIP 先例在 aggregate 侧），或对 `invalid` 条数设上限。

### P3-1（讨论）— `revert_contract_issues` 规则④（重复 invariant id）无负例

- **位置**：`behavior_profile.py:378-380`；测试 `:173-182` 只覆盖 duplicate surface 与空 marker
- **说明**：四条规则中三条有注入负例，规则④仅靠「真实表干净」间接覆盖。当前 5 条 id 互异（L122-150 逐条读出）✓，无实际缺陷。建议补 1 行 subTest 与既有负例同构。

### P3-2（讨论）— 环境变量原值回显进聚合面

- **位置**：`behavior_profile.py:253-255`（`env_value`）、`:235-238`（`invalid[].value`）
- **说明**：字段语义只是开关 token，且该变量名不含 secret 语义；但聚合面会进入 agent 上下文，若用户误把 token 设进该变量则会外泄到会话。不建议阻塞，提请写进模块边界注释（「本变量只承载开关词表，禁止承载凭据」）。

### P3-3（讨论）— `next_action_line` 的 5 不变量散文与 `SAFETY_INVARIANTS` 双源

- **位置**：`behavior_profile.py:299-301` vs `:120-151`
- **说明**：两处当前逐字一致（已核对）。表变更时散文不会自动跟随——这正是 FEAT-039 P3-3「双源」同族。低风险（散文只是回显），可选修复：由 `SAFETY_INVARIANTS` 的 id 列表拼装。

### P3-4（讨论）— `canonical-bootstrap-version` 投影 count=4 命名与既有测试口径的存量张力（pre-existing）

- **位置**：`core/version-projections.json:124-131`（`count: 4`，作用于 `commands/governance-init.md`）；测试 `test_verify_workflow.py:15535-15552` 已同步为 4 并注明「三模板 + secondary-thin」
- **说明**：历史 review（review-FEAT-034-DESIGN-R0 §156 / review-FIX-285）记录过「HEAD 断言 3 vs 实际 4」的存量欠账——本批已把投影与断言都收敛到 4（静态确认 4 处 marker：:198/:267/:549/:853），**该欠账在本批已闭**。仅备注：新增的 secondary-thin 第 4 处标记面已进入投影计数，是正确方向的收敛，但 12 处文档（历史 release 文档）仍引用旧计数——文档面历史引文按惯例不改。

---

## 五、AI 代码专项检查（5 项）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 唯一 mock 用法是 `unittest.mock.patch` **注入违规**（:168/:174/:180 注入 smuggled/duplicate/markerless）与 `patch.dict(os.environ)`（:274）——均为**被测对象的真实代码路径**，非替身。无 autospec 缺失、无 MagicMock 断言自证 |
| 2 | 硬编码返回值 | ✅ 无 | `expected` 侧无「为让测试过而写死」的桩值；阈值常量（25000/45000/3）是**契约参数**并有测试钉住「阈值入码非散文」（test_governance_cost.py:853-857）；`_plan_tracker_text` 是测试夹具 |
| 3 | 幻觉 API 调用 | ✅ 无 | 新代码仅用 `os/re/ast/json/tempfile/unittest/pathlib` 与仓内真实模块（`resolve_entry`/`task_priority`/`release.projection`/`sync_entry_projection`/`checks.version`）——逐一 Grep 存在；`patch.object(bp,"LEGACY_REVERTS",...)` 作用于真实模块属性（:168） |
| 4 | 未实现 TODO | ✅ 无 | 新增三文件与改动的五处调用点无 TODO/FIXME/`pass  # impl`/NotImplementedError；`# pragma: no cover - defensive`（behavior_profile.py:226）是**已实现的防御分支**（非占位） |
| 5 | 过度实现 | ✅ 无 | 开关是**单一总开关**而非逐 FEAT 矩阵（docstring §1 自陈并核对实现：无 per-FEAT 覆盖项）；`render_boundary_table` 服务文档面按需；`revert_contract_issues` 服务于测试；未引入未声明的 CLI/配置面（无独立 CLI，符合 R6 决策）。`--ttfa-acceptance` 复用既有扫描（无第二遍遍历） |

---

## 六、硬门槛裁决

| 门槛项 | 阈值 | 实测 | 判定 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | **0** | ✅ |
| 5 维度全覆盖 | = 100% | 正确性/安全性/可维护性/性能/测试覆盖 逐维度有结论（第一节） | ✅ |
| 每条发现标注级别 | = 100% | P1×2 / P2×3 / P3×4 全部带级别与位置 | ✅ |
| 设计一致性检查 | 已完成 | triage acceptance 五项逐项：开关可用（env 臂 ✅ / plan-tracker 臂 ⚠️ 无端到端证据 → P1-1）/ 守护测试（✅ 含注入负例）/ 安全边界明确（✅ 三层，FEAT-035 不参与回退）/ 收尾清单处置（✅ 抽验 5/5）/ 复验框架（✅ RISK-055 阈值入码 + PENDING 不借绿）/ 多平台投影（✅ 6 面 marker + registry-manifest 集合相等 + `member_match:"exact"` 12 项） | ✅（1 项带 P1） |
| AI 代码专项 5 项 | 全部完成 | 见第五节，5/5 | ✅ |

**P0 = 0；P1 = 2（P1-1 / P1-2，均 blocking）；P2 = 3；P3 = 4。**

---

## 七、结论

**NEEDS_CHANGE**

**unresolved_blockers=2**

理由：两条 P1 都落在本次交付的**核心语义**上——(a) 项目级回退通道（文档化并按 SKILL.md:81 给「优先级中」的臂）在聚合面与 CLI 面无任何证据，若接续点丢失则守护网静默，属「机制可用性无证据」；(b) 非法取值虽已按「不猜」语义落臂且被披露，但 JSON 快路径的消费者拿不到动作信号，而**同一条设计意图在 legacy 生效时恰被实现为最高优先级提示**（bootstrap_aggregate.py:724-729），语义不对称。两者修复成本都很低（各 1 条测试 + 数行代码），不需要重做设计。

**非阻塞但应在下一轮一并收口**：P2-1（census 数字不可证伪——FEAT-039 度量教训同型）、P2-2（守护测试对活体 plan-tracker 耦合）、P3-1~P3-4。

**已独立证实的强项（本轮不应退回重做）**：安全边界三层的数据层与文本层是全批最扎实的工程——`ALLOWED_REVERT_CLASSES={performance}` + FEAT 交集判 + 注入式负例证明 checker **会红**（不是自证干净）；FEAT-035 确认**只在 `SAFETY_INVARIANTS`、不在 `LEGACY_REVERTS`**；6 个协议面 marker 逐字在位；路由层 11,934B/12,288B **逐字节证实**（余量 354B）；fixture router 与 canonical 逐字节相等且 registry/manifest 双边登记；三条 legacy 声明 FAIL 路径各有可证伪负例；`--ttfa-acceptance` 阈值入码、PENDING 不借绿、成对 TTW 与阈值测试齐备；R6 Δ0 由惰性 import + 可执行冻结计数守护；AI 专项 5 项全过。

**复审触发**：按 M7.4 step 4.6 T1——Developer 返工后 MUST 立即 spawn 同一 Reviewer 复审（round 1），re-spawn prompt 注入本报告路径为强制读取项；复审须逐条比对 P1-1/P1-2 并标注「已修复/未修复/新引入」。

**本报告的事实边界（不做的事实声明）**：未运行任何测试或 CLI（无 pytest 实测、无 `check-injection-budget` 实测、无 `git status`）；「1,080 passed / 31F / 3,439P / resident 4,957 / +669 分解 / dirty 4 项归属」六项按未实测处理，其中路由层字节数、fixture 字节相等、registry/manifest 集合相等、10 条 legacy 声明、三个新文件用例计数已由只读度量与 Grep **独立复算通过**。
