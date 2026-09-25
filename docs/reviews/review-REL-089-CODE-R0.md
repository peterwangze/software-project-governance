# Code Review 报告 — REL-089（M-3 前置补强 · arch 抽检三放行条件）· R0

> **Task**: REL-089（P1）· **Round**: R0（首轮）· **Reviewer**: Code Reviewer Agent（独立子代理）
> **日期**: 2026-09-25 · **审查对象**: 工作树未 commit 3 文件（零产品代码修改——纯测试+文档）
> **结论**: **APPROVED_WITH_NOTES** · **unresolved_blockers = 0**（P0=0 / P1=0 / P2=1 / P3=6，全部非阻塞）

---

## 0. 审查范围与方法（实测优先）

被审文件（`git status --porcelain` 实测仅此 3 项，无其他修改/未跟踪残留）：

| # | 文件 | 变更 |
|---|------|------|
| 1 | `skills/software-project-governance/infra/tests/test_rel089_release_compat.py` | 新增 537 行 / 11 用例 |
| 2 | `docs/release/rel-089-m3-precondition-report.md` | 新增 187 行 |
| 3 | `docs/release/rollback-plan-0.88.0.md` | +34/-1（§8 新节 + 旧 §8→§9 + 候选池 2 行） |

实测手段（全部本审独立复跑，非采信申报）：
- **测试复跑**：单文件 `pytest test_rel089_release_compat.py -v` → **11 passed (11.79s)**；全量 `pytest skills/software-project-governance/infra/tests -q` → **4119 passed, 1 skipped, 0 failed (1164.56s, exit 0)** = 4108 基线 + 11 新增，与申报 4119P/1S/0F 逐字一致；
- **0.87 方法论复核**：`git rev-parse v0.87.0^{}` = `602f8f3`（2026-09-21，真实 tag）；`git show v0.87.0:<path>` 提取源码逐段实读（`_load_write_guard_state` / `CLOSURE_EVENT_TYPES` / 读取器报文）；六工件 `git grep -l -F <artifact> v0.87.0`（**全树，无 pathspec 限定**）→ 全零命中；
- **条件② 活体复现**：`verify_workflow.py check-governance` → Check 18/18b 恰 2 记录 × 2 检查 = 4 FAIL，与报告 §② 引文及 M-2 记录逐字一致；EVD-1140/1164 行（evidence-log L2606/L2694）、ops 收据（`governance-store-ops.json` L835/L3205：command/task_id/status/execution/new_revision 1665096/1728797/input_fingerprint 0f67a840…/4d70113a…/recorded_at 2026-09-24T09:50:09 全字段吻合）、hot tracker FIX-375 ✅ 完成行、REVIEW-FIX-375-R1 APPROVED（L2605）、REVIEW-REL-087-R0 APPROVED_WITH_NOTES+unresolved_blockers=0（L2693）逐一实证；
- **读位分叉实证**：`verify_workflow.py` L12633/L14448/L22489 三处 `description = parts[4]` + L12918 `FACT_BASIS_RE` + L12949 `_extract_structured_fact_json(description)`——basis 列（parts[5]）不在严检搜索面，假 FAIL 机理成立；L12261 `_COMPLETED_STATUS_PREFIX = "✅"` + L12280-12287 F-3 刻意分叉注释与报告引述一致；
- **工件矩阵闭合性**：`git diff --diff-filter=A v0.87.0..HEAD -- infra/`（非测试）= 恰 4 新文件（write_guard_state / decision_repository / decision_migration / decision_migration_verify），其工件字面量穷举（`.write-guard-violations.json`/`.write-guard-posture.json`/`.decision-store-state.json`/`.decision-migration`）全部落于矩阵六工件内——**无遗漏的 0.88 新持久工件**；
- **DEC-240 原文对照**（decision-log L182/L183）：三放行条件逐条比对；RISK-059（risk-log L55，触发条件=真实权威切换，未触发——与报告 (d) 行前提披露一致）；
- **cross-refs / manifest 复跑**：`check-cross-references` PASS（exit 0）；`check-manifest-consistency` 输出唯一 `[UNTRACKED] changelog.md`（advisory，exit 0）——与报告「验证汇总」行吻合。

---

## 1. 五维度审查结论

| 维度 | 结论 | 依据（摘要） |
|------|------|--------------|
| 1 正确性 | **PASS** | 11 用例判别力逐条核实（见 §3）；断言强度高：字节级快照零写入比对（test L249-252）、写入键集精确边界 `⊇{schema_version,tool,files} ∧ ⊆{…,updated_at}`（L379-385）、problems 子串披露（L444-447）、seq 碰撞双向实证 `next_seq==3 ∧ 3∈raw`（L450-451）、converge 新增文件集合 containment（L295-297）。无逻辑错误、无边界缺陷 |
| 2 安全性 | **PASS** | subprocess 全部参数列表形式（无 shell 注入面），timeout 120s/300s 兜底；git show 输出仅落临时目录；夹具数据为合成行，无敏感信息；`errors="replace"` 防 decode 崩溃 |
| 3 可维护性 | **PASS**（2 项建议见 F-2/F-3） | 常量集中（L55-70）、夹具函数复用、注释锚定 DEC/FEAT/FIX 票号可追溯；模块 docstring 精确描述两条件方法论与运行方式 |
| 4 性能 | **PASS**（1 项卫生建议见 F-7） | setUpClass 一次性提取（全套 11.79s）；`_snapshot` 仅遍历治理目录小文件；无 N+1/O(n²) 面 |
| 5 测试覆盖 | **PASS** | 条件①：两路径 × {check-only 零写入, converge 只写守卫工件, 权威源 MD_ACTIVE, 族姿态全 WARN} 全断言；条件③：6 工件静态零引用 + 3 条动态行为路径（guard 读/journal 读/archive 枚举）+ seq 碰撞攻击向量实证；错误路径（schema 违例→issues 披露）经 `_upgrade_world` FAIL 断言看护 |

## 2. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 证据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | `mock` 仅用于 `vw.GOVERNANCE_DIR`/`SAMPLE_PATH` 世界重定向（合法测试 seam，非行为伪造）；0.87 视角路径（`_run_087`）零 mock——真实子进程实跑 |
| 2 | 硬编码返回值 | **无** | 全部断言消费真实执行输出；`现值=warn` 计数断言绑定真实 CLI 输出格式（L211-212） |
| 3 | 幻觉 API | **无** | 抽查全部实存：当前侧 `check_release_bootstrap_world`/`run_release_bootstrap_converge`/`check_governance_write_shapes`/`load_family_postures`/`run_guard_management_cli`/`FAMILY_VOCABULARY`/`TOOL_ID`/`load_authority`/`initial_authority`（测试实跑通过即证）；0.87 侧 `_load_write_guard_state`/`_WRITE_GUARD_STATE_SCHEMA_VERSION`/`_load_closure_events`/`_next_seq`/`CLOSURE_SCHEMA_VERSION`/`build_event`/`_get_existing_archive_files`/`_index_path`（git show 提取源码逐一实证） |
| 4 | 未实现 TODO | **无** | 537 行零 TODO/FIXME/XXX/HACK（grep 实测 0 命中） |
| 5 | 过度实现 | **无** | 纯测试增量（git status 3 文件实证零产品代码修改）；夹具仅构造种子形状，key set 经真实写入器输出交叉校验（L375-384），不构成产品逻辑重复实现 |

## 3. 六项 MUST 重点审查（逐项结论）

### 3.1 11 测试判别力 / 0.87 视角方法论真实性 — **PASS（方法论真实）**
- **提取的是真 0.87 代码**：`v0.87.0^{}` = `602f8f3`（2026-09-21 14:00:57 +0800，实测）；`ls-tree -r v0.87.0 -- <infra prefix>` 全量提取 .py，缺关键模块即 SkipTest（fail-closed，L341-350）；
- **子进程隔离实跑而非 mock**：`_run_087` 以 `cwd=提取目录` 起 `python -c`（L352-356），0.87 与 0.88 同名模块经 cwd 隔离零污染——与 FIX-387 进程内全局态教训的对向应用，docstring 如实声明；archive 用例进一步以独立 fake-infra + `sys.path.insert` 复核（L460-494）；
- **0.87 语义断言与源码相符**（本审 git show 实读）：0.87 `_load_write_guard_state` 仅校验 `dict ∧ schema_version==1 ∧ files:dict`，未知键（`updated_at`）确实容忍 → (a1) 兼容定性成立；0.87 `CLOSURE_EVENT_TYPES` = 恰 8 型（started/step_started/step_completed/step_failed/step_unknown/step_reconciled/ready/finalized），**无 cancel/reopen/fence 概念**，报文模板 `unknown closure event_type {0!r} (closed enum of {1} types)` 与测试断言子串一致 → (b1) fail-safe 读 + 封闭枚举 8 型表述属实；
- **方法论注**：journal 用例以 0.87 `build_event` 构造 0.88 型事件——是合理的「0.87 信封 + 0.88 载荷」混合世界构造（回退后 journal 即此形状），非作弊。

### 3.2 条件① 完备性 — **PASS**（1 项对称性建议 F-4）
- DEC-240① 原文（decision-log L182）：「干净安装+0.87 升级路径的状态断言（发版自举不隐式激活+运行时可查当前权威源与各族模式——文档说明不代替默认行为验证）」；
- 两路径 × 不隐式激活：check-only 零写入（干净=连目录都不建 L189；升级=逐字节快照恒等 L252）+ converge 只写守卫工件（L295-297 集合断言）+ posture/authority 零创建（L225-226/L254/L299）✓；
- 运行时可查：`load_authority → MD_ACTIVE/md/epoch 0/present` 两路径（L191-195/L255-258）+ 族姿态 `({}, None)` 两路径（L197-198/L259-260）+ `--show-posture` CLI 全 WARN（干净路径 L200-213，5 族= `len(FAMILY_VOCABULARY)` 动态绑定）✓；
- 「文档说明不代替默认行为验证」已由机器断言兑现（报告 §① 结论行如实声明）。

### 3.3 条件② 复核记录质量 — **PASS**
- **身份面**：EVD-1140@L2606 / EVD-1164@L2694 行标识、actor、日期、G11、状态尾与报告引文逐字一致；
- **状态链面**：三层核验全部独立复现——①ops 收据字段逐一吻合（含 new_revision 1665096/1728797、input_fingerprint 前缀、recorded_at 精确到秒）；②行内嵌同一 operation_id 实读在案；③hot tracker FIX-375 ✅ 完成行（plan-tracker L96，含 R0→R1 链与 4 个 op id）+ REVIEW-FIX-375-R1 APPROVED（L2605）+ REVIEW-REL-087-R0 APPROVED_WITH_NOTES/unresolved_blockers=0（L2693）。链路无断点；
- **规则面**：「本应满足的规则」论证被代码实证——basis 落 parts[5]（DEC-168 机录契约，evidence-log 实行布局 `| id | task | type | 描述 | 事实依据… | 文件 | …`）而严检只读 parts[4]（L12633/L14448/L22489 + FACT_BASIS_RE/`_extract_structured_fact_json(description)`），豁免谓词窄口径 ✅（L12261 + F-3 注释）——**假 FAIL 机理成立，非数据缺陷归因正确**；check-governance 活体复现 4 FAIL 逐字吻合；
- **例外限定**：{EVD-1140, EVD-1164} × {Check 18, 18b} × {0.88.0 候选版} + 不改谓词不加豁免行 + FIX-390 落地自动消解——无全局绕过，与 DEC-240② 口径一致；DEC-241（decision-log L183）已按此批准，机录在案；
- **FIX-390 票面可执行性**：acceptance 四条（三态回归/两行红→绿活体/豁免面差分 S_new⊇S_old 逐行归因/9-cell 契约零触碰）均可检验、scope 精确（verify_workflow 读位 + test_verify_workflow，不触碰写入器）——可执行。

### 3.4 条件③ 定性矩阵正确性 — **PASS**
- **抽验 ≥2（实际全验 6 工件）**：本审以全树 `git grep v0.87.0`（无 pathspec）复验六工件 = **全零命中**，(a2)/(a3)/(b2)/(c1)/(c2)/(d)「安全忽略」定性成立；0.87 `_load_write_guard_state` 源码实读证实 (a1) 兼容定性；journal fail-safe 读 + 语义误读（kept=[1,2]→next_seq=3 与 raw seq 3 相撞）由测试双向实证；
- **矩阵闭合性**：0.87→HEAD 新增非测试 infra 文件恰 4 个，工件字面量穷举全部在矩阵内——无第三类遗漏；
- **伪造 tombstone 否决的 P1 一致性**：0.87 八型枚举中唯一终态 `closure_finalized` 语义为「提交核验」，**不存在可诚实表达「取消」的 0.87 事件型** → 向 journal 追加伪造终态是唯一「0.88 侧防御」途径，违反项目原则 P1（P-v1：不允许编造）与 closure append-only 审计纪律 → 否决正确；「0.87 是已发布 tag（路径 A 不可修补）/路径 B 可 backport FIX-391」的可达性论证与 rollback §8 路径 B 特性行一致；DEC-241 已附同一裁定。防线落在运行手册门禁（§8）+ FIX-391（§9 行 9）——闭环；
- **前提披露如实**：(d) 行「若 0.88 期间发生过 JSON 切换则 md 可能 stale——须先走 B-13 反向转换」与 RISK-059 触发条件（risk-log L55 实读）一致，本版 MD_ACTIVE 缺省未切换。

### 3.5 rollback §8 落位质量 — **PASS**
- §8（rollback-plan L174-203）与报告 §③ 加引区块**逐字一致**（仅 §N→§8、报告引用显式化为相对路径——均为落位应有变化）；两路径区分（A=tag 部署不可修补/运行手册门禁；B=revert 重建可 backport FIX-391）不合写 ✓；
- 回退前四步（closure 清单登记/check-only 留档/authority=MD_ACTIVE 确认否则禁止回退/冻结写窗）+ 回退后四验证（启动/读写/任务恢复/一致性）与 DEC-240③「最低验证=…旧版本启动/读写/任务恢复/一致性验证」映射完整；forward 恢复段（五件原样恢复生效 + journal 0.88 全量可读）在案；
- §9 候选池行 8/9（FIX-390/FIX-391）落位（L216-217）；旧 §8→§9 重编号无悬挂内部引用（全文 grep §8/§9/第 8/9 节 = 仅标题自身）；「Commit 区间」锚存在（changelog.md L100）。

### 3.6 验证复现 — **PASS**
- 11P 单跑 ✓（11.79s）；全量 **4119P/1S/0F**（exit 0，19m24s）= 申报逐字 ✓；cross-refs PASS ✓；manifest 唯一 `[UNTRACKED] changelog.md` 与报告口径一致（REL-087 双位过渡既有披露，非本票引入——changelog.md 已于 72ddffb 入 git，manifest 侧缺口为 REL-087 登记的 canonical 归属过渡面，M-3 裁决承接口径如实）。

---

## 4. 发现清单

### P0 阻塞（合并前必须修改）
无。

### P1 关键
无。

### P2 建议（可遗留，附修复窗口建议）
- **F-1 (P2)** `docs/release/rollback-plan-0.88.0.md:174,191` — 路径 B「revert 全部 29 commits（v0.87.0..M-1 tip）」存在**双指涉**：CHANGELOG 区间表实测恰 29 commits 至 `3fb42c0`（`git rev-list --count v0.87.0..3fb42c0` = 29 ✓），但报告 §② 与 REL-087 语境的「M-1 候选/M-1 tip」= `72ddffb`（版本 bump commit），实测 `v0.87.0..72ddffb` = **30**；且执行时点窗口已延伸至 33（`v0.87.0..HEAD`）。回退属破坏性程序，计数与区间指涉应唯一。缓解项已在案：CHANGELOG L100 自带「区间终点随 M-1 候选 commit 落库后延伸」注记 + rollback footer「`<发布 tip>` 属 M-5 期义务」。**建议**：M-5 刷新时统一为「按 CHANGELOG Commit 区间全量逆序 revert（以 M-5 刷新清单为准）」或去除具体计数；本轮可遗留。

### P3 讨论/文档精度（不要求本轮修改）
- **F-2 (P3)** `rel-089-m3-precondition-report.md:102,115` + `rollback-plan-0.88.0.md:176` — 工件计数口径不自洽：「四类六工件」「六工件中五件 = 安全忽略/兼容」vs 定性表实为 **8 行 = 7 安全忽略/兼容 + 1 部分兼容**（按 `_ARTIFACTS_UNKNOWN_TO_087` 口径则是 6 未知工件全部安全忽略 + 2 共有工件〔1 兼容 1 部分兼容〕）。建议统一为「8 项定性 = 7 安全忽略/兼容 + 1 部分兼容」，§8 同步。
- **F-3 (P3)** `test_rel089_release_compat.py:55,512,526` vs `rel-089-m3-precondition-report.md:100,107` — 静态机检 pathspec 限定 `_INFRA_PREFIX`（infra 代码树），报告口径为「全树 grep」。本审已全树独立复验 6 工件零命中（主张今日为真），但机器看护不含 docs//adapters/ 等未来新增引用面。建议测试放宽为全树 pathspec（成本≈0）或报告措辞收窄为「infra 代码树」。
- **F-4 (P3)** `test_rel089_release_compat.py:200-213 vs 259-260` — `--show-posture` CLI 端到端断言仅在干净安装路径；升级路径族姿态经 `load_family_postures` API 断言（同源数据、语义等价，DEC-240①「运行时可查」已满足）。建议补升级路径 CLI 断言达到两路径完全对称。
- **F-5 (P3)** `rel-089-m3-precondition-report.md:23`（§① 结论）— DEC-240① 内嵌的「CHANGELOG 措辞三级区分」子句未在报告显式销项。实测 `changelog.md:92` 披露⑤/⑦（「FEAT-064 BLOCK 为机制交付……本版不主张全族已 BLOCK 运行」+ no-overclaim 边界）已实质满足；建议报告补一行引用使条件①销项闭环，避免 M-3 复核口径争议。
- **F-6 (P3)** `rel-089-m3-precondition-report.md:102-113` — DEC-240③ 枚举中的「心跳并行」无对应定性行。本审实测：FEAT-044 心跳为纯上报语义（`loop_engine.py:405`「writes no files」；loop_telemetry 纯度量），`flow-unit-runtime.json` 为 0.87 已知共有工件（v0.87.0 全树已引用）→ 无兼容性问题。建议补一行「心跳面零新持久工件」显式定性，使 §③ 对 DEC-240③ 枚举逐项可追溯。
- **F-7 (P3)** `test_rel089_release_compat.py:324` — `setUpClass` 的 `tempfile.mkdtemp(prefix="rel089-v087-")` 无 `addClassCleanUp` 清理，每次测试会话残留一个提取目录。建议 `cls.addClassCleanUp(shutil.rmtree, cls._tmp087, ...)`（注意 Windows 句柄时序可用 ignore_errors）。

---

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | **0 ✓** |
| 5 维度全覆盖 | = 100% | **5/5 逐一有结论 ✓**（§1） |
| 每条发现标注级别 | = 100% | **7/7（P2×1 + P3×6）✓**（§4） |
| 设计一致性检查 | 已完成 | **完成 ✓**——与 DEC-240 三条件原文（decision-log L182）、DEC-168 机录列契约、FIX-376 F-3 分叉口径、P-v1 P1 原则、closure append-only 纪律逐项比对无偏离 |
| AI 代码专项 5 项 | 全部完成 | **5/5 ✓**（§2） |

## 6. 总结论

**APPROVED_WITH_NOTES**（unresolved_blockers = 0）

- 申报「4119P/1S/0F（4108 基线 + 11 新零回归）」「cross-refs PASS」「产品代码零修改」「0.87 视角 = git show 提取真实代码 + 子进程隔离实跑」四项申报**全部实测证实**；
- 三放行条件销项质量：①两路径运行时断言完备（F-4 为对称性增强建议）；②复核三面扎实、例外限定无全局绕过、FIX-390 票面可执行（DEC-241 已机录批准）；③六工件矩阵经独立全验无遗漏、伪造 tombstone 否决与 P1/append-only 一致；
- P2×1（F-1 计数指涉）+ P3×6 均为文档精度/测试强化建议，不阻塞合并；建议 F-1/F-2 随 M-5 rollback 刷新消解，F-3/F-4/F-7 可入 0.89 测试维护批，F-5/F-6 为报告补注（Coordinator 酌定是否要求补）；
- 按 M7.4：本报告为 R0 通过终态，复审链可终结；遗留项移交 Coordinator 入跟踪。
