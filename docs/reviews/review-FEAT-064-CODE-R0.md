# Review FEAT-064 · CODE · R0 —— write-guard 分族 BLOCK 激活（0.88.0 阶段 D1 · 机制+测试交付，真实翻转未执行）

> 审查人: Code Reviewer Agent（独立，只读）· 轮次: R0 · 日期: 2026-09-25
> 审查对象（工作树未提交 10 文件，+2091/−133，`git diff --stat` 实测核对一致）: `infra/write_guard_state.py`（+896/−32，1734 行全读——裁定表/姿态配置/break-glass/逐面钳制/P2-1/P2-2/管理 CLI）+ `infra/verify_workflow.py`（+267/−64——face-5 姿态接线/钳制推进/break-glass 审计/CLI 管理分支）+ `infra/tests/test_triage_write_guard.py`（+811/−2，25 新测试，类 :2172-2920）+ `infra/registry.py`（FIX-383 收口，96→97）+ `infra/tests/test_registry.py`/`test_contract_matrix.py`（冻结计数再基线）+ `infra/contract_matrix/snapshots.json`/`golden_samples.txt`（指令化再生）+ `infra/checks/version.py`（static-pin 重锚 995→997/1141→1143）+ `infra/TOOLS.md`
> 语义基准: version-plan-0.88.0 §2 D1 行（L50——逐族裁定+break-glass 限定+七场景验收）+ §3b F-5 组合义务（L68）+ §6 出槽清单（L103）+ DEC-224（双约束）+ DEC-236①（R2 翻转面）+ DEC-236（FEAT-060 遗留三件 P2-1/P2-2/SESSION_ID）+ FEAT-061 双后端论证 + FEAT-049 写入器契约注册表
> 审查方法: 逐行读 diff 与两处全文（write_guard_state.py 1734 行全读 + verify_workflow face-5/CLI 区域全读 + 25 新测试全读）；实测优先——99P 套件复跑、邻接三套件 129P 复跑、活体 `--show-posture`（只读）、HEAD↔工作树双版本隔离探针（HEAD infra 提取至临时目录，同种子沙箱双向对比）、archguard 6F 双向归因（HEAD 副本实测 LOC/print census）；**全程零 `.governance` 写入**（探针驱动置于 %TEMP%，误写入 `.governance/review-probe-fe064/` 已即时迁出并删除；未执行任何 `--activate-block`/`--break-grant`）

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（P0=0 · P1=1 · P2=2 · P3=4 · **unresolved_blockers=0**）

5 维度逐项有结论（§4）· AI 专项 5 项全过（§6）· 设计一致性 8 焦点 8 符合（§2）· 独立复验 8/8 通过（§5，其中全量 3972P/31F 为 claimed 项如实标注）。五族裁定表与 version-plan D1 行/FEAT-049 写入器注册表逐项对得上（写入器权威 `evidence-append`/`review-record`/`decision-append` 双后端/`task_row_update` receipt 全部实存实测）；BLOCK 语义如实（写后执法——face FAIL iff block 级 issue、exit 1、**能阻断工作流 ≠ 阻止文件修改**措辞如实入码 L23173-23174/L23899）；R2 逐面钳制（前像保持+无前像扣留响亮披露+消费事务捆绑收口）七场景全数覆盖且红态经 HEAD 代码对照坐实；break-glass 五限定+use 审计不可静默+无 BLOCK 不授予+用满惰化+信任模型边界披露完整；FEAT-060 遗留三件（P2-1 覆写删除/P2-2 A-B-A 定案/`--session-id` 接线）全部兑现且对 HEAD 为真红态；FIX-383 收口正当且四处披露诚实。

**P1-1（不阻塞，建议本轮顺手修复——纯口径/注释修正，约 10 行）**：「默认姿态 WARN 输出字节不变/byte-identical」的注释与申报口径已与实际改写的 WARN 披露文本相矛盾（F-1）。**字节恒等在「基线字节 + 零差异窗口输出」意义上成立（探针实测），但 WARN 披露 detail 正文与 CLI 摘要尾句相对 FEAT-060 时代已变更**（HEAD「BLOCK 升级留 0.87」→ 工作树「分族 BLOCK 机制已交付未激活——FEAT-064…」）；同一工作树内 version.py re-audit 注释、snapshots.json、golden_samples.txt 三处均已如实记载 "deliberate guard-output wording change"——矛盾只在代码注释（verify_workflow.py:22950、:23398-23399）与开发申报措辞。修复 = 收敛口径为「基线字节/零窗口输出恒等 + WARN 披露文本 deliberate 改写（再生面已记载）」，或按 re-audit 注释同口径改写两处注释；修复后无需重审（不触及本报告其余结论）。

---

## 2. 设计一致性（八焦点逐项裁定——对应任务 MUST 重点 1~8）

| # | 焦点 | 裁定 | 事实依据 |
|---|------|------|---------|
| ① | 五族裁定合理性 | **符合** | 裁定表 `FAMILY_RULING_DECLARATION`（write_guard_state.py:323-368）逐族携 writer+rationale。**evidence BLOCK**：writer=governance_store evidence-append——`registry._COMMANDS` 实存 `("evidence-append", …)`（python 实测 True），DEC-224 机录转轨路径成立；**review BLOCK**：writer=review-record CLI（REVIEW_MACHINE_ROW_MARKER=「review-record CLI 机器写入」，checks/review_domain 实测在库；M7.4 审查结论必机录=禁手写 REVIEW 行——写入器覆盖完备）；**decision BLOCK（FEAT-061 双后端论证）**：MD 权威行携 `机器写入：governance-store decision-append` 标记（组合测试 JSON 腿 assertIn :2895-2896 实证）+ JSON 权威 md 投影逐字重放（`test_projection_render_replay_is_digest_identical` :2900-2920 用守卫同源 `_write_guard_row_digest` 断言行摘要集恒等→整表重写零 diff）——「行摘要恒等 → 对账零 diff」声称由测试以守卫自身的 digest 函数钉住，非散文断言；**ops_ledger BLOCK 纳入**：append-only 论证成立——`*.ops.jsonl` receipt 仅由 task_row_update 尾部追加（operation_id 凭证锚，`_row_family_credential_ok` fallthrough 分支 verify_workflow.py:24819），合法追加恒在尾部→行索引身份不漂移（中部插入位移身份为 FEAT-057 既有披露边界，模块 docstring :150-152 继承不改写——如实）；**task_status WARN 后置**：version-plan D1 行（docs/planning/version-plan-0.88.0.md:50）原文「任务状态列后置（📋/⏳ 停放格不可映射的建行/激活面已实证存在手工路径——先补机录激活路径或入豁免台账再 BLOCK）」+ §6 出槽清单（:103）双实证，裁定表 rationale（:356-358）逐字对齐——**证据链完整，后置正当** |
| ② | BLOCK 语义正确性 | **符合** | face FAIL iff block 级 issue（verify_workflow.py:23334-23335，全 WARN → PASS 字节同源）；exit 1（:23971）与 exit 2（管理拒绝）语义清晰；「write-AFTER，能阻断工作流≠阻止文件修改」三处如实（模块 docstring :117-118、face-5 注释 :23173-23174、CLI docstring :23899）。**R2 逐面钳制**：`blocked_surfaces`（:1211-1233，open 非 eligible BLOCK 族违规 ∪ 本轮 fresh BLOCK 族检测→阻塞面）+ `clamp_baseline_target`（:1236-1255，前像回填/无前像扣留）+ 消费事务捆绑钳制后基线（reconcile_violation_state :1556-1594 effective_target 进 txn）——被阻塞面基线保持前像不吸收不前移（test_block_window_not_absorbed_across_repeats :2224-2245 前像字节相等断言 + test_block_surface_held_while_warn_surface_absorbs :2251-2273 混合面隔离断言）；基线重建边缘扣留+逐轮响亮披露（`block_window_baseline_hold` :1571-1577 + test :2308-2330）。恢复路径=写入器补凭证→自动消费→事务捆绑收口（test_writer_remediation_consumes_and_unblocks :2275-2306，消费后面回 PASS+基线 sha256=当前文件）。eligible 面**不**阻塞（其现快照随消费事务入基线）——docstring :1215-1217 与实现一致 |
| ③ | break-glass 安全性 | **符合** | 五限定=对象 `--families`（闭集校验 :1011-1018）+操作者 `--authorized-by`+理由 `--reason`（空即拒 :996-1005）+有效期 `--ttl-hours`（>0 校验 :1019-1024，过期惰化 `_break_glass_validity` :968-976）+次数 `--max-uses`（≥1 校验，用满惰化 :966-967）；**use 审计不可静默**：每次 persist 路径运行记一条 use 事件（verify_workflow.py:23722-23725 + record_break_glass_use :1113-1145，锁忙→响亮 issue「审计不完整」）；**无 BLOCK 不授予**（:1038-1042 `no_block_active` 拒绝，test :2569-2572）；一窗原则（:1063-1068）；`--break-clear` 入 `break_glass_history` 审计保留（:1148-1190，cleared_by/reason 必填）；**信任模型边界如实**——「本地 CLI 无密码学强制，仅记录 WHO/WHY（与全仓写入器同一信任模型）」模块 docstring :143-146 明示。范围化降级只软化 face（window 是披露通道非豁免：违规照记 open、基线保持钳制——docstring :162-165 + test_scope_limited_downgrade :2595-2611 范围外 decision 照 FAIL）。测试红绿：无窗口授予拒/双窗拒/范围外不软化/用满惰化/过期惰化/清理入史全测（:2566-2719） |
| ④ | 全 WARN 字节恒等 | **部分成立（F-1，P1）** | 成立部分（探针实测，HEAD infra 提取隔离双跑）：amnesty/零差异窗口输出 issue 集恒等 + 基线字节（归一化时间戳后）恒等；bare 场景**基线字节仍恒等**、face 状态恒 PASS、issue 结构字段（type/file/line/task_id/expected）恒等。不成立部分：**WARN 披露 detail 正文与 CLI 摘要尾句文本已改写**（HEAD「BLOCK 升级留 0.87」vs 工作树 L23460-23463「分族 BLOCK 机制已交付未激活——FEAT-064，姿态经 governance-write-guard --show-posture 查看」；L23974-23978 同改），探针 `bare_issues_equal=false` 实锤。矛盾面：verify_workflow.py:22950「the WARN output bytes are unchanged (DEC-224-pinned)」与 :23398-23399「byte-identical WARN-class disclosure of the FEAT-057/060 era」两条注释对**本函数自身发射的新文本**失实；而 version.py re-audit 注释（:267-276）、snapshots.json `guard_output_pin`、golden_samples.txt 三处均已如实记载 deliberate wording change。判定：**行为恒等成立、披露正文恒等不成立且已在再生面入账——缺陷性质=注释/申报口径失实（P1），非行为回归**。74 基线零回归实测成立（99 全绿含 74 旧测试，旧测试零改动——git diff 该文件仅追加） |
| ⑤ | 七场景+组合测试判别力 | **符合** | 场景①重复=:2224-2245（逐轮重燃+单 open 纯去重+前像保持）；②并发=:2404-2433（双线程 persist 串行、双双 FAIL、零 diverged——补丁主线程统一施加的 FIX-387 canary 教训注释在场）；③消费后崩溃=:2435-2466（phase-2 注入 OSError→仅 journal 残留→复跑 world 判定收敛 consumed+PASS）；④基线写崩=:2468-2486（plain 推进 OSError→响亮披露+窗口重燃）；⑤会话重启=:2488-2499（无身份新轮窗口保持、记录不重记）；⑥⑦伪造/无权=:2501-2536（两腿拒绝红相+BLOCK 持续 FAIL 无旁路）。**红态真实性经 HEAD 代码对照坐实**：HEAD face 硬编码 PASS（HEAD :23291「face["status"] = "PASS"」）、无钳制/无姿态层/break-glass 函数整体不存在→上述测试对 HEAD 全数为红。组合 F-5②三腿（:2831-2920）走真写入器（gstore.decision_append/drepo 权威转移 API 实存实测）零 unattributed，与 version-plan L68 ②义务对齐 |
| ⑥ | FEAT-060 遗留三件兑现质量 | **符合** | **P2-1**：HEAD `_finalize_txn` 实存 `record["hook_identity"] = txn["consumer"]`（HEAD 副本 L437 实读）→工作树删除并留注释（:1298-1304「检测侧身份不得覆写，消费方身份只活在 consumption_event」）；红态测试 `test_hook_identity_preserved_through_consumption`（:2727-2759，INVOKER_ENV 覆写形态→消费后 hook_identity 保持 test-hook+consumption_event.consumer=CLI）对 HEAD 为真红。**P2-2 定案(a)**：`session_triggers` 逐会话计数（:661-689 新记录 {sid:1}、re-trigger 沿 supersede 链继承+1、≥2 升级）——A-B-A x→y→x 在 x 的第二次触发升级（HEAD 判据=「紧邻同会话」`session_id == existing.last_session_id`（HEAD :466-467 实读）→x→y→x 不升，红态坐实）；保守半边 x→y 各首次不升（test :2786-2800，宁可漏升不可误升）。**SESSION_ID 接线**：`--session-id` argparse（:25924-25929）→check_governance_write_shapes(session_id=…)（:23926-23928）→显式优先 env（:23707-23710）；test :2802-2828 双轮显式身份升级实证 |
| ⑦ | registry/contract-matrix 再生 | **符合（正当收口）** | FIX-383 遗漏=引擎 dispatch+白名单已登陆而 `_COMMANDS` 行漏发（R5 预存漂移）——FEAT-064 因守卫输出措辞 deliberate 变更触发快照再生而暴露，同票收口正当且四处披露诚实（registry.py 注释、两测试文件计数注释 96→97、snapshots `handler_count 93→94/key_count 97`+keys 追加+git_head=61618a5 再生戳、golden 再生戳）；指令化再生路径合规（generator 元数据在案，test_contract_matrix/test_registry/test_static_version_pins 129P 实测全绿） |
| ⑧ | 验证复现 | **8/8 通过（§5）** | 99P/邻接 129P/verify PASSED/活体 posture 只读/双版本探针——全部本机复跑；全量 3972P/31F 与 host-mode 组为 claimed（§5 标注） |

---

## 3. 独立复验（8/8 通过——Reviewer 本机实跑，全程零 .governance 写入、零姿态翻转）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 目标套件 99P | `python -m pytest infra/tests/test_triage_write_guard.py -q` | **99 passed in 2.30s**——74 旧 + 25 新（8+5+5+4+3 与申报清点一致），全绿 |
| 2 | 邻接三套件 | `pytest test_registry.py test_contract_matrix.py test_static_version_pins.py -q` | **129 passed in 95.40s**——冻结计数 97/97、static-pin 重锚 997/1143 锚定通过、快照再生一致 |
| 3 | verify 全量 | `python infra/verify_workflow.py verify` | **PASSED, exit 0**（版本投影/manifest/adapter 契约面含）——申报核实 |
| 4 | 活体姿态（只读） | `governance-write-guard --show-posture` | **裁定 evidence/review/decision/ops_ledger=block（现值全 warn）、task_status=warn；break-glass 无活动窗口**——活体全 WARN、红线遵守（零 --activate-block/--break-grant 执行）实锤 |
| 5 | HEAD↔工作树双版本探针（amnesty） | HEAD infra `git archive` 提取至 %TEMP%，同种子沙箱双跑 persist 路径 | **issue 集恒等 + 基线字节（归一化时间戳后）恒等**——零窗口路径字节恒等成立 |
| 6 | 双版本探针（bare WARN） | 同上 + 裸行变更轮 | **`bare_issues_equal=false`（WARN detail 文本差异实锤）+ `bare_state_norm_equal=true`（基线字节仍恒等）+ ledger 差异=新增 session_triggers 等字段（预期）**——F-1 直接证据 |
| 7 | archguard 双向归因 | 工作树 6F 实跑 + HEAD 副本 `count_print_calls`/LOC 实测 | **R4×3：WT 总数=HEAD=1318 vs committed 1316——+2 全为 FIX-383 预存（申报归因精确）；R1：anchor 25462 < HEAD 25979（+517 预存红）< WT 26182（本票加深 +203）；R7/CliGate 与 R1/R4 同根**——详见 F-2 |
| 8 | 套件卫生 | `git status` + 根残留文件检查 + `infra/.governance` 存在性 | **infra/.governance 不存在**（FIX-387 canary 成立）；根目录 0 字节未跟踪残留 `test_triage_write_guard.py`（F-3） |

**标注为 claimed（未独立复验，如实说明）**：①全量 infra 3972P/31F「全 HEAD 预存（worktree 双向归因）」——全量复跑未执行（时长考量），以直接受影响 4 套件 228P 全绿 + archguard 6F 逐项 HEAD 归因（复验 7）替代，与申报口径调和一致；②host-mode 组 8 CWD 敏感为开发者环境观察，未复现；③「七场景红绿」的绿态已全数复跑，红态以 HEAD 代码对照（焦点⑤⑥）结构坐实，未逐条对 HEAD 回放。

---

## 4. 五维度审查结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ✅ | 逐行核对：canonical_family surface↔基线 files 键↔records_index 键三处一致（surface 裸名「evidence-log.md」/「*.ops.jsonl」——`_build_violation_detection` family=surface :23475-23476，REVIEW 前缀消歧复用凭证判据权威 :786-790）；钳制与消费事务的 effective_target 接线闭环（skip_baseline/baseline_written_by_txn/钳制后 plain 推进三分支全覆盖）；消费拒绝梯在 journal 前零残留；`_validate_ledger` 12 字段 floor 不含新字段（FEAT-060 旧台账向后兼容）；「P2-2 计数继承」边界（y 触发继承 x 计数器）与 B1 字面「同会话第二次独立触发」一致。未发现 P0/P1 逻辑缺陷 |
| 安全性 | ✅ | 零注入面（无 shell/eval）；姿态翻转与 break-glass 双通道全部 fail-closed（结构化拒绝+exit 2，reason/authorized-by 强制）；损坏配置 fail-safe 全 WARN（不猜测不静默，test :2332-2350）；损坏台账不 honoring（fail-closed :1088-1091）；use 审计不可静默（锁忙→响亮）；信任模型边界（本地 CLI 无密码学强制）如实披露；写后执法边界如实。残余：管理 CLI 两处只读展示面的披露小缺口（F-4/F-5，P3） |
| 可维护性 | ✅ | 实体在 leaf 模块、引擎仅薄接线（RISK-039 纪律——管理报表渲染也下沉 leaf :1619-1665「print budget 不增长」先例注释）；裁定表=数据声明（audit face）与活体姿态（posture config）分离清晰；单序列化器/单锁单原子写继续单源；注释密度与披露口径总体优秀——唯 F-1 两处注释自相矛盾需收敛 |
| 性能 | ✅ | 行级 multiset diff + SHA 快路径沿用；台账线性扫描（量级=违规记录数）；锁超时 10s 沿用；姿态配置每次运行双读（F-7，P3——微开销自愈型）；无 N+1/O(n²) 新增 |
| 测试覆盖 | ✅ | 25 新测试全部真实沙箱（temp dir + 模块全局 patch，CLI 路径 parity persist_state=True；`_activate` 走真实 activate_family_postures 实体）；七场景+裁定隔离+钳制字节断言+组合三腿真写入器；红态真实性经 HEAD 对照坐实；崩溃注入为真实异常注入。缺口为边缘（管理 CLI 损坏台账展示、activate 二读异常路径——F-4/F-5 配套测试缺席，P3） |

---

## 5. AI 代码专项检查（5 项全过）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 通过 | 产品代码（write_guard_state.py/verify_workflow.py）零 `mock` 引用；mock 仅存于测试且均域内（patch 模块全局/环境变量/注入崩溃） |
| 2 | 硬编码返回值 | ✅ 通过 | 无绕过逻辑的固定返回；裁定表为**数据声明**（target/wave/writer/rationale），活体执法状态由 posture config 决定——声明与执行分离正确 |
| 3 | 幻觉 API | ✅ 通过 | 组合测试引用的 `governance_store.decision_append`/`decision_repository` 6 API/`vw._write_guard_row_digest` 等 12 个符号 hasattr 实测全 True；registry writer 权威（evidence-append/review-record/task-row-update/write-guard-bootstrap）实测在册 |
| 4 | 未实现 TODO | ✅ 通过 | 两产品文件零 TODO/FIXME/NotImplemented/占位（grep 实测）；deferred 语义以裁定表 `wave=deferred（0.89+ 出槽）` 字段承载并对应 version-plan §6——是有意的范围裁定非未完成实现 |
| 5 | 过度实现 | ✅ 通过 | 交付面与 D1 行义务逐项对齐（五族裁定/break-glass/七场景/遗留三件）；未实现 D1 未要求的执法动作（真实翻转未执行——红线遵守）；管理 CLI 渲染下沉 leaf 避免引擎膨胀，方向克制 |

---

## 6. 发现清单（P0=0 · P1=1 · P2=2 · P3=4）

### P1（原则上本轮修改，可申请遗留）

- **P1-1 · 「全 WARN 字节恒等」注释/申报口径与 WARN 披露正文改写自相矛盾（F-1）**
  - 位置：`infra/verify_workflow.py:22950`（「the WARN output bytes are unchanged (DEC-224-pinned)」）、`:23398-23399`（「yields the byte-identical WARN-class disclosure of the FEAT-057/060 era」）vs `:23460-23463`（新 WARN detail 文本）、`:23974-23978`（新 CLI 摘要尾句）
  - 证据：双版本隔离探针 `bare_issues_equal=false`（HEAD「BLOCK 升级留 0.87」vs 工作树「分族 BLOCK 机制已交付未激活——FEAT-064…」）；同工作树 version.py:267-276 re-audit 注释自认「the disclosure's tail clause was also rewritten」+ test_contract_matrix.py 注释自认「FEAT-064's deliberate guard-output wording change」+ golden/snapshots 再生一致
  - 影响：交付叙事自相矛盾——后续审查者/协调者据注释断言「WARN 文本零变化」会做出失实结论；对以响亮披露为产品的治理工具属披露准确性缺陷。行为面无回归（基线字节/face/exit/issue 结构均恒等，探针实测）
  - 建议：三选一——(a) 推荐：把两处注释与申报口径收敛为「基线字节+零窗口输出恒等；WARN 披露文本 deliberate 改写（static-pin/golden/snapshots 再生面已记载）」；(b) 恢复旧文本（不推荐——旧文本「BLOCK 升级留 0.87」在 0.88.0 已失实）；(c) 保持现状并要求 Coordinator 在入账证据中显式记录该口径勘正（最低限度）。修复后无需重审

### P2（建议修改，不阻塞合并）

- **P2-1 · archguard 预存失败披露不全，R1 超额被本票加深 +203 行（F-2）**
  - 位置：`infra/verify_workflow.py`（引擎 LOC 25979→26182）；`core/architecture-baseline.json` r1 anchor 25462
  - 证据：工作树 test_archguard_ratchet 实测 **6F**（R1×1/R4×3/R7×1/CliGate×1），边缘披露仅点名 R4×3（该归因精确——WT=HEAD=1318 vs committed 1316，+2 全 FIX-383）；R1 在 HEAD 已红（HEAD 25979>25462，+517），本票净 +267 使 excess 517→720
  - 影响：协调者对 R1 加深无感知；ratchet only-down——0.88 M-2 门禁（plan-tracker L306 含棘轮席）前需处置路径（授权 regen 或 sanctioned shrink），否则发版链带红
  - 建议：补披露入交付证据；将 R1 锚处置排程进 REL-086 M-2 前置清单（与既有 3-ERROR 预注册口径合并表述）
- **P2-2 · 根目录 0 字节残留文件 `test_triage_write_guard.py`（未跟踪）（F-3）**
  - 位置：仓库根 `test_triage_write_guard.py`（0 字节，mtime 2026-09-25 08:01）
  - 证据：`git status` `??`；`Get-Item` Length=0
  - 影响：`git add -A` 类操作会带入垃圾文件；疑似 repo 根运行 pytest/重定向残留
  - 建议：删除不入库；排查产生命令路径

### P3（讨论/低优先）

- **P3-1 · `activate_family_postures` 二次裸读无异常防护（F-4）**——write_guard_state.py:925-928：`load_family_postures` 校验通过后再次裸 `json.loads(path.read_text(...))`，两读之间文件损坏/被删 → 未捕获异常 → 管理 CLI traceback（非结构化 exit 2 拒绝）。竞窗极窄、无数据风险（原子写保证读者见旧或新）。建议包 try/except → `posture_config_unreadable` 拒绝
- **P3-2 · `--show-posture`/`--break-show` 对台账损坏静默（F-5）**——write_guard_state.py:1653-1654、:1725：`load_ledger` 返回的 issue 被丢弃，R6 损坏场景下渲染「无活动窗口/历史 0 条」不披露。执法面（guard run）仍响亮，非静默执法缺口；只读展示面披露完整性问题。建议报告行追加 `[!] issue.detail`
- **P3-3 · F-5①③ 组合测试未见兑现（版本级义务归属待确认）（F-6）**——version-plan-0.88.0.md:68 清单①（guard 台账损坏×FEAT-061 切换窗口共存）③（基线更新×decision-append 投影失败恢复）在 infra 测试内 grep 无对应实现（②=本票三腿 ✔；④ 明示 E 阶段）。plan-tracker L306 M-2 门禁含组合测试集必查——建议 Coordinator 入账归属票或确认随 M-2 前补齐；非本票验收缺口（本票义务=②）
- **P3-4 · 姿态配置 persist 路径双读（F-7）**——verify_workflow.py:23218（face judge）+ :23698（state machine）各读一次（注释已自述「second read-only load」）；并发 `--activate-block` 竞窗下两判定可短暂异姿（下一轮自愈，原子写保证无半态）。低优先：单读透传

---

## 7. 遗留项（关闭建议）

| 项 | 级别 | 处置建议 | 截止建议 |
|----|------|---------|---------|
| P1-1 口径收敛 | P1 | 本轮顺手修（注释 2 处 + 申报口径勘正入证据） | 本票收尾前 |
| P2-1 archguard R1 处置 | P2 | REL-086 M-2 前授权 regen 或 shrink（与预注册 3-ERROR 合并表述） | M-1R/M-2 前 |
| P2-2 根残留文件 | P2 | 删除 | 本票收尾前 |
| P3-1~P3-4 | P3 | 随下轮或 0.89 批次 | 不阻塞 |

---

## 8. 结论说明

- **APPROVED_WITH_NOTES / unresolved_blockers=0**：硬门槛全过（P0=0、5 维度全覆盖、发现全标注、设计一致性 8/8、AI 专项 5/5）；P1-1 为披露口径缺陷非行为缺陷，按 skill 关闭规则「P0=0 且 P1>0（有遗留计划）→ 有条件合并」以通过终态通过并登记遗留（§7）。
- 红线遵守确认：审查全程未执行 `--activate-block`/`--break-grant`；活体姿态经只读 `--show-posture` 复核为全 WARN；审查零 `.governance` 写入（探针驱动置于 %TEMP%；一次误写入 `.governance/review-probe-fe064/` 已即时迁出删除，无残留）。
- 机制+测试交付、真实翻转未执行——与任务语义基准一致；上线翻转时点由 Coordinator 裁定（届时建议按 D1 行顺序先 evidence/review 族，task_status 维持 WARN 至机录激活路径补齐）。
