无（复审链关闭）

结论：APPROVED_WITH_NOTES ｜ round=1 ｜ unresolved_blockers=0 ｜ 前轮 = `docs/reviews/review-REL-078-CODE-R0.md`（NEEDS_CHANGE/unresolved_blockers=1：F-01 P0 + F-02/F-03 P1 + F-04 P2 + F-05~07 P3）

# REVIEW-REL-078-CODE-R1 — 0.82.0 窗口聚合面（M-3 产品代码半面）R1 复审

- **审查对象**：与 R0 同窗（`e376ddf..HEAD` = 14 commits，`git rev-list --count` 实测 14 未变；HEAD 仍 `845c050`）+ **R0 退回修复后的暂存面 33 文件 / +1142 −33**（R0 时点 25 文件 +498 −21 → 净增 8 文件，逐文件归属见 §3）。复审焦点 = R0 findings 修复状态 + 复跑清单 + 新引入面。
- **Round**：R1（同一 Code Reviewer，R0 同一审查方，按 M7.4 step 4.6 复审）；前轮引用 = `docs/reviews/review-REL-078-CODE-R0.md`。
- **隔离纪律**：全部引擎命令从仓库根运行；每次调用以 `$tmpHome = %TEMP%\spg-rel078-code-r1-*`（guid 后缀，FIX-337 非保留变量名规范）隔离 `DSH_HOME`；测试脚本/套件 JSON 全部落 `%TEMP%`；真实环境（`$HOME/.dsh`、真实 `$DSH_HOME`）零触碰；本报告是本次审查**唯一**仓库写入文件。
- **机录**：本报告只产出审查结论；REVIEW 证据行由 Coordinator 经 `review-record` CLI 机录（本报告不手写 REVIEW 行）。

---

## 0. 独立复现声明（本次会话实测）

| # | 实测内容 | 结果 |
|---|---|---|
| 1 | `resolve_entry.py --json`（隔离 DSH_HOME） | resolved_root_ok=true，active_version=0.82.0，hooks ×3 全装 |
| 2 | `git diff --cached --stat` / `--name-only` 计数 | **33 文件 +1142 −33**；未跟踪文件 0 |
| 3 | 未暂存增量 `git diff --stat` | **恰 1 文件 2 hunk**：`rollback-plan-0.82.0.md` L24 记法精化（`8bd6a8a..845c050` → `8bd6a8a` 至 `845c050` 含首）+ §1 表交叉引用更正（`§3 校验项` → `§2.2 第 3 步与 §4 验证表 #5`）——恰为 RELEASE-R1 §5-2/3 两项 P3 顺手项的响应（见 §4-N4） |
| 4 | checklist L81（Gate 14）现文 | `回滚区间 = 整个 0.82.0 窗口 `e376ddf..<发布 tip>`` + 起点注记「0.81.0 发布 tip〔v0.81.0^{commit} peel 实测〕，`845c050` 非 0.81.0 发布 tip〔见 rollback-plan §勘误注记〕」✅ |
| 5 | `git log -1 e376ddf --format='%h %s'` | `e376ddf REL-077: 0.81.0 transition + 门禁收口与审查退回修复` = 0.81.0 发布 tip（与 R0 #1 同判）|
| 6 | staged `verify_workflow.py` 版本钉计数 | `"0.82.0"` = **6** 处、`"0.81.0"` = **0** 处；numstat **6/6**（纯原位替换，未触碰 L717-719 dead-store 与任何逻辑行）|
| 7 | staged 标记面 | `AGENTS.md` 1/1 = 0.82.0；`commands/governance-init.md` 3/3 模板标记 = 0.82.0（L197/262/533 同位）；`project/e2e-test-project/CLAUDE.md` L5 = 0.82.0；root `CLAUDE.md`（gitignored 工作树载体）L5 = 0.82.0 |
| 8 | `check-version-consistency` 实跑（隔离） | `Result: PASSED — all version declarations consistent`，exit 0（唯一 WARN = plan-tracker 工作流版本 0.81.0，gitignored M-8 清除面，预期披露与 Gate 1 一致）|
| 9 | `check-projection-sync --fail-on-issues` 实跑 | PASSED（15 投影，Source 0.82.0），exit 0 |
| 10 | `check-dsh-boundary`（28w）实跑 | PASS — 0 failing criterion(a)；K-2 `outside-contract host literals: 0 (11 declared consumer(s) scanned)`；K-7 NOT_RUN（DEC-193 as-built 合法态，R0 同判）|
| 11 | `archguard-ratchet` 实跑 | R1 `24453 ≤ 24453`、R2 47、R3 12 edges、R4 1299、R5 `cli 84/84 + segments 71/71`、R6 196 Δ0、**R7 `committed==fresh True`** → PASS 0 violations（6 钉行替换后行数锚恒等 + committed 与 fresh 一致）|
| 12 | `check-loop-runtime-claims --scan-mode installed_host / product_release` 实跑（×3 次取字段） | **双模式 `verdict: PASS`、`verdict_scope: semantic_only`、exit 0**；`exemptions_applied` = 4 条全部生效（CHECKLIST0810-241-1 + FIX300R0-71-1/-71-4/-72-1）；`state_totals` = 3×UNSUPPORTED_AFFIRMATIVE + 1×AMBIGUOUS_SUBJECT_RELATION（恰为账本 4 条族）；**`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY` 不在场**（R0 唯一未豁免 finding 已消解）|
| 13 | staged `review-FIX-333-CODE-R0.md` diff | **恰 1 行**（L33）：`` `%TEMP%\fix333_review\` `` → `` `%TEMP%\fix333_review` ``——行内代码尾反斜杠删除 = 修复声明「删 1 字符」逐字属实 |
| 14 | 定向测试（显式 TestLoader，隔离 DSH_HOME）：`FIX300DualCaliberAgreementTests` + `LoopRuntimeClaimAdapterTests` + `EntryBootstrapTemplateTests` | **Ran 13 tests in 57.732s，OK，exit 0**——R0 四失败 ①`test_bootstrap_version_marker_injected_into_all_profiles` ②`test_fixture_identity_mode_agrees_with_engine_on_present_sources` ③`test_identity_host_source_drift_reproduces_divergence_shape` ④`test_claim_command_emits_complete_pass_report` 全部转绿 |
| 15 | 850 全量 | 修复方实跑记录 **192.8s OK**（任务书授权口径：定向绿即采信全绿结论）；checklist Gate 10 的 M-2 安静窗 850 复跑义务继续在案兜底 |
| 16 | 根因机制旁证 | 检测点 `infra/checks/loop_runtime_claims.py:655`（`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row`）；同型尾反斜杠残留 `staged review-FIX-333-CODE-R0.md:13`（HEAD 既有）经 #12 全树扫描实测**不触发**（该处合并 span 未跨单元格）|
| 17 | `core/manifest.json` 载荷检索 | 不含 `e2e-test-project` ⇒ e2e 镜像为测试夹具、非插件发布载荷（N3 裁决依据）|

---

## 1. R0 findings 逐条裁决（已修复 / 未修复 / 新引入）

### F-01（R0 P0，阻塞）— **已修复 ✅**

- checklist L81 = `e376ddf..<发布 tip>`（#4），与 `rollback-plan` §区间锚定/§勘误注记（staged L24 = `e376ddf..<发布 tip>`）一致；peel 实测注记 + 勘误指针在场（#5 锚身份复验）。R0 判据「一行文本修复、与 rollback-plan 对齐」完整兑现。

### F-02（R0 P1，M-2 前必达）— **已修复 ✅（机检/测试义务面全部兑现 + 全部入暂存）**

- (a) 6 钉：staged 6×0.82.0 / 0×0.81.0（#6）✅；`AGENTS.md` staged 1/1 ✅；Gate 1 实跑 PASSED（#8）✅。
- (b) 模板标记面：root `governance-init.md` ×3 + e2e `CLAUDE.md` L5 staged 0.82.0（#7）✅；`EntryBootstrapTemplateTests` 绿（#14，含 `test_bootstrap_version_marker_injected_into_all_profiles` 动态断言）✅。
- (a)+(b) **全部入暂存**：index 33 文件含上列全部修复面（§3）——RELEASE-R1 §5-1 条件「漏 add 即复活」已消除。
- **N1（P3 注记，不阻塞）**：`project/e2e-test-project/commands/governance-init.md` ×3（L197/262/533）仍 0.81.0——实测非插件载荷（#17，manifest 不含 e2e 夹具）、`check-version-consistency` 标记面零覆盖（其输出自证仅 root AGENTS/CLAUDE）、无测试依赖（13 定向 + 850 全绿实证）；RELEASE-R1 §1 残留扫描同判「e2e 夹具未改动面、非新引入」。与本 R0 建议的「双镜像同法（0.81.0 先例）」不同型，但机检/用户交付面影响为零。建议随下批 e2e 夹具维护/文档卫生批顺手同步，不构成本版义务。
- **N2（P3 注记）**：R0 F-02(c)「模板标记面纳入机检」候选——decision-log/session-snapshot 未见 DEC/任务登记（R0 已定性非本版义务）。建议 M-8 后补登记入 DEC 候选池。

### F-03（R0 P1，发布前必达）— **已修复 ✅（R0 二选一之 (i)「消解」路径成立）**

- **1 字符修复入暂存**（#13，恰 1 行 L33）；根因机制（行内代码尾反斜杠转义闭合反引号 → accounting ragged fail-closed）与检测点实现（#16）相容；staged 同文件 L13 同型残留经全树扫描实测不触发（HEAD 既有、非本批引入）。
- **我本人复跑**：loop-claims 双模式 `verdict: PASS` / exit 0（#12），`exemptions_applied` = 4 条账本豁免全部生效，`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY` 消失，`state_totals` 与 R0 账本 4 条族逐条一致（**无新增语义 finding**）——R0 的「semantic verdict 被单条 accounting 项压至 BLOCKED ⇒ FIX-320 族 3 测试连坐红」因果链被完整消解。
- **定向复跑**：R0 四失败全绿（#14，13/13 OK）；850 全绿 192.8s 为修复方实跑记录，按任务书授权口径采信，且 Gate 10 的 M-2 安静窗全量复跑义务不变（兜底）。
- **pristine/materialize 对照结论核对**：修复方定谳「materialize `845c050`（修复前基线）复现同 1 finding = 已入库基线缺陷在 bump 窗口暴露，非引擎/非 bump/非期望回归」——与 R0 实测时序（报告 2026-09-16 落库未变、EVD-1059 次日 850 OK）及本审查机器终态（修复后双模式 PASS + 语义集合与账本族恒等）一致，定谳接受。R0 要求「定谳前不得写真回归/既有基线」——现已定谳，Gate 10「FIX-320 族若出现即真回归」与 Gate 15「语义面双模式全绿预期」**原文无需改写且与实测一致**。
- **N3（P2，本批新引入的披露态过期——非阻塞）**：`project/CHANGELOG.md:34` 如实披露① 仍写「`REVIEW-FIX-333-CODE-R0` 报告自身携带 1 条 accounting（ragged table）项……随批披露、不阻断」。该状态已被**同一候选批**修复消解（#12/#13），句子与同批交付内容自相矛盾（过期披露；方向为过度披露，不使任何门禁失真）。**建议候选提交前一行改写**，如：「窗口内曾触发 1 条 accounting（ragged table）项，已随本批 1 字符修复消解（loop-claims 双模式 PASS 实证）」——1 行文本，随批零风险。

### F-04（R0 P2，M-1 冻结时处理）— **已修复 ✅**

- checklist L3 + L142 引入「**唯一例外 = M-2 派生回填类**」（候选打包 commit 与 M-0/M-1 批 hash：0.82.0.json 先随候选入库 → `release-ledger --no-remote` 派生）；L47/L48 与 CHANGELOG L21 占位均落该类。发布半面 RELEASE-R1 §2 已独立裁决例外口径成立（EVD-1034 对点先例 + F-R1-02 引注精度 P3 注记），本审查核对其裁决链实存在案，**口径采纳一致**。
- **N4（P3 注记）**：checklist L26 `⟦M-1 交付⟧`（`core/releases/0.82.0.json` candidate）按 RELEASE-R1 §2-2 自划边界属**非派生类**占位——M-1 已实际交付（EVD-1060 + candidate 已入暂存），该占位现为陈旧态，宜随候选冻结提交一并消除（一词改写）。

### F-05（R0 P3）— **维持裁决（讨论项）**

- CHANGELOG [0.82.0] 不列 FIX-338 ×3：checklist Change Inventory 行 1~3 + rollback-plan 构成披露兜底在案，非静默遗漏；维持不阻断。

### F-06（R0 P3，窗口外既有）— **维持**

- `verify_workflow.py` L717-719 dead-store：本批引擎文件增量 numstat = 6/6 纯版本钉行（#6），未触碰该结构；后续引擎清理批顺手消除（原建议不变）。

### F-07（R0 P3）— **闭环（随本批收敛）**

- R0 记录的并发修改（钉/标记修复、root 标记面自升级）已全部收敛入暂存（§3 的 8 个新增文件逐一归属）；唯一残留并发面 = rollback-plan **未暂存** 2 hunk（#3，恰为 RELEASE-R1 §5-2/3 P3 顺手项响应）。**N5**：建议候选打包前 `git add` 收编（RELEASE-R1 §5-1 条件精神——避免评审对象与候选载荷漂移）；不收编亦不阻塞（暂存面自身自洽，L22 计数方法注记已使 staged 文本无硬矛盾）。

---

## 2. 复跑门禁面汇总（R0 复审要求 ②，全部隔离 DSH_HOME 实跑）

| 门禁 | R0 时点 | R1 实测 | 裁决 |
|---|---|---|---|
| Gate 1 `check-version-consistency` | T1 FAIL（钉未暂存）/ T3 PASS（未暂存修复） | **PASSED exit 0**（1 条预期 WARN） | ✅ 且修复已入暂存 |
| `check-projection-sync` | PASSED ×2 | **PASSED**（15 投影） | ✅ |
| Check 28w `check-dsh-boundary` | PASS | **PASS 0 failing**（K-2 = 0/11 consumers） | ✅ |
| `archguard-ratchet` | PASS | **PASS**（24453 恒等 + **R7 committed==fresh True**——6 钉行替换后核） | ✅ |
| loop-claims 双模式 | 双模式 BLOCKED/exit 1（1 条 accounting 未豁免） | **双模式 PASS / exit 0**（4 豁免生效、0 新增语义 finding） | ✅ F-03 消解实证 |
| 850 套件 | 4 failures | 定向 13/13 OK（四失败转绿）+ 修复方 192.8s OK 记录采信 | ✅（M-2 安静窗全量复跑义务不变） |

## 3. 新引入面检视（R0 复审要求 ④：暂存增量逐文件归属）

现 index 33 = R0 已审 25 + **8 个新增文件**，逐一归属：

| # | 文件 | numstat | 归属 |
|---|---|---|---|
| 1 | `skills/.../infra/verify_workflow.py` | 6/6 | F-02(a) 6 钉原位替换（唯一引擎文件增量；逻辑零变更，archguard/R7 实证） |
| 2 | `AGENTS.md` | 1/1 | F-02(a) bootstrap 标记 |
| 3 | `commands/governance-init.md` | 3/3 | F-02(b) 模板标记 ×3 |
| 4 | `project/e2e-test-project/CLAUDE.md` | 1/1 | F-02(b) e2e 标记 |
| 5 | `docs/reviews/review-FIX-333-CODE-R0.md` | 1/1 | F-03 1 字符修复 |
| 6 | `docs/reviews/review-REL-078-CODE-R0.md` | +206 | R0 审查报告入库（审查链证据） |
| 7 | `docs/reviews/review-REL-078-RELEASE-R0.md` | +274 | 发布半面 R0 报告入库 |
| 8 | `docs/reviews/review-REL-078-RELEASE-R1.md` | +152 | 发布半面 R1 报告入库（APPROVED_WITH_NOTES/0，复审链关闭） |

其余 25 文件 = R0 已逐 diff 过目的原暂存面（三件套/CHANGELOG 随 F-01/F-04 修复有小幅文本增量，均已在上文逐点核验）。**结论：无声明面之外的产品逻辑改动、无范围漂移、无越界触碰。**

**AI 代码专项 5 项（对 8 文件增量）**：mock 残留 0（测试文件未动）；硬编码缺陷 0（6 钉 = 版本投影契约期望值面）；幻觉 API 0（纯字面量替换 + 文档）；未实现 TODO 0（⟦⟧ 占位均在 F-04 例外/回填协议允许面）；过度实现 0（8 文件全部映射审查链/发布面职责）。

## 4. 非阻塞 Notes 汇总与后续义务

- **N1（P3）**：e2e `commands/governance-init.md` ×3 仍 0.81.0（非载荷、零机检覆盖、RELEASE-R1 同判）——下批夹具维护顺手同步。
- **N2（P3）**：「模板标记面纳入机检」候选未登记 DEC/任务池——M-8 后补登记。
- **N3（P2，建议候选提交前处理）**：CHANGELOG L34 如实披露① 措辞过期（ragged 项已消解）——1 行改写（§1 F-03 内建议文案）。
- **N4（P3）**：checklist L26 `⟦M-1 交付⟧` 陈旧占位——随候选冻结提交一词消除。
- **N5（P3）**：rollback-plan 2 个未暂存 hunk 建议 `git add` 收编后再打候选提交。
- **M-2/M-4 义务不变**：本通过 = M-3 产品代码半面复审链关闭，**不是发布 go 授权**——Gate 1~15 M-2 门禁实测（含安静窗 850 全量复跑、check-release 后台作业、渲染 parity、契约 SHA 复测、ledger 候选态 lineage、回滚演练 ≥1 次）与 M-4 用户停点（DEC-197）义务全部维持。

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0**（R0 F-01 已修复；本轮无新 P0） | ✅ |
| 5 维度全覆盖 | = 100% | 正确性✅（修复面逐点实证 + 引擎 4 门禁全绿）/ 安全性✅（无输入/凭据/注入面变化；1 字符文档修复）/ 可维护性✅（N1~N4 注记在案；F-06 既有）/ 性能✅（archguard R1~R7 全 PASS、R6 Δ0）/ 测试覆盖✅（13/13 定向 + 850 采信 + M-2 复跑兜底） | ✅ 5/5 有结论 |
| 每条发现标注级别 | = 100% | N1~N5 全部带 P2/P3 标签 | ✅ |
| 设计一致性检查 | 已完成 | checklist Gate 10/14/15、rollback-plan 区间锚、CHANGELOG 披露面与实测逐点比对（§1/§2） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 有结论（§3） | ✅ |

⇒ 硬门槛全通过（P0 = 0，无未解决 BLOCKING）→ **结论 APPROVED_WITH_NOTES（unresolved_blockers=0）**。

## 6. 命令上报表（只读；工作目录 = 仓库根；DSH_HOME 逐命令 `$tmpHome` 隔离）

| # | 命令（摘要） | 退出码 | 结果 |
|---|---|---|---|
| 1 | `resolve_entry.py --json` | 0 | resolved_root_ok=true / 0.82.0 |
| 2 | `git status --short` / `diff --cached --stat` / `--name-only` | 0 | index 33 文件 +1142/−33；未跟踪 0 |
| 3 | `git diff --stat` / `git diff -- rollback-plan` | 0 | 未暂存恰 2 hunk（归属 §1 F-07/N5） |
| 4 | `git log -1 e376ddf` / `rev-list --count e376ddf..HEAD` | 0 | 0.81.0 transition tip；14 commits |
| 5 | staged blob 读取（`git show :path`）：verify_workflow 钉计数 / AGENTS / governance-init / e2e CLAUDE / FIX-333 diff | 0 | #6/#7/#13 全部兑现 |
| 6 | `check-version-consistency` / `check-projection-sync --fail-on-issues` / `check-dsh-boundary` / `archguard-ratchet`（隔离） | 0/0/0/0 | §2 四门禁全绿 |
| 7 | `check-loop-runtime-claims --scan-mode installed_host / product_release`（隔离，×3 取字段） | 0/0 | 双模式 PASS；4 豁免；accounting 边界项不在场 |
| 8 | 显式 TestLoader 定向（隔离；脚本落 %TEMP%） | 0 | 13 tests OK 57.7s |
| 9 | manifest 载荷检索（staged blob） | — | 不含 e2e-test-project |
| 10 | 尾反斜杠-反引号扫描（staged 全文件） | — | 仅 FIX-333 R0 L13（HEAD 既有、机检不触发）+ test_change_triage.py 代码字符串 |
| 11 | `checks/loop_runtime_claims.py` 检测点定位 | — | L655 ragged table row |
| 12 | evidence-log/decision-log/session-snapshot/plan-tracker 检索（EVD-1060、REL-078 执行态、DEC 候选） | 0 | 链路核对 §1 |

**未执行**：任何 `git add/commit/restore/stash/worktree`、`--regen`、`check-release`/`release-ledger`、全量 850/3200 discover 复跑（按任务书授权以定向绿 + 修复方实跑记录采信）、真实环境任何写入。

## 7. 未验证 / 待验证声明

1. 850 全量 192.8s OK 为修复方实跑记录（本审查以 13/13 定向 + 任务书授权口径采信）；M-2 安静窗复跑为最终现场判据。
2. 修复声明中「同类陷阱修复 R1 报告 L25」指针未能解析到具体文件:行（staged `review-FIX-333-CODE-R1.md:25` 为章节头、RELEASE-R1 L25 无该形态）；修复本体已由 #12/#13 机器实证，不影响裁决，登记为措辞精度观察。
3. materialize@845c050 复现为修复方执行的对照程序，本审查以机器终态 + 1 字符 diff + 检测点机制一致性接受其定谳（R0 的未定谳状态就此关闭）。

---

*审查方：Code Reviewer Agent（R0 同一审查方，round=R1）｜审查对象：0.82.0（REL-078）暂存候选面 33 文件（HEAD `845c050` 未动）｜结论：**APPROVED_WITH_NOTES**｜unresolved_blockers=0｜复审链关闭（首行「无（复审链关闭）」）｜M-2 门禁实测与 M-4 用户停点义务全部维持——本结论不是发布 go 授权。*
