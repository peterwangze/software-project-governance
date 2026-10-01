# REL-089 — 0.88.0 M-3 前置补强报告（arch 抽检三放行条件）

> **任务**: REL-089（P1——M-3 前置）· **裁决输入**: DEC-240（op-c16d9b24，arch 抽检「有条件 GO」三放行条件）
> **执行**: GovernanceDeveloper（sub-agent）· **日期**: 2026-09-25 · **工作目录**: 治理插件仓库根
> **角色边界**: 本报告不写 `.governance/`、不做最终决策；proposed entries 由 Coordinator 审核写回。

---

## ① 未激活默认的运行时验证（条件一）— **PASS**

**看护测试**: `skills/software-project-governance/infra/tests/test_rel089_release_compat.py` ::
`ReleaseBootstrapDefaultPostureTests`（6 用例，两路径全覆盖）。

| # | 路径 | 用例 | 断言（全绿） |
|---|------|------|--------------|
| 1 | 干净安装 | `test_clean_install_check_only_zero_write_and_defaults` | `check_release_bootstrap_world` converged；check-only **零写入**（连 `.governance/` 目录都不创建）；`load_authority` → `MD_ACTIVE`/`md`/epoch 0/`present=False`；`load_family_postures` → `({}, None)`（全 WARN 缺省） |
| 2 | 干净安装 | `test_clean_install_show_posture_reports_all_warn` | `run_guard_management_cli("show_posture")` exit 0；5 族输出 `现值=warn`、零 `BLOCK 已激活`；姿态配置文件零创建 |
| 3 | 干净安装 | `test_clean_install_converge_does_not_activate` | converge（守卫唯一写路径）后 `.write-guard-posture.json` 与 `.decision-store-state.json` **零创建**；权威源仍 `MD_ACTIVE` |
| 4 | 0.87→0.88 升级 | `test_upgrade_layout_check_only_zero_write_no_activation` | 0.87 布局行族 + 0.88 四类工件共存世界：check-only 零写入（逐字节快照比对）；converged；权威源 `MD_ACTIVE`（marker 在场）；姿态全 WARN |
| 5 | 0.87→0.88 升级 | `test_upgrade_layout_guard_faces_never_block_class` | 共存世界 guard 全面 status ≠ FAIL、零 `posture=="block"` issue（WARN 类披露不升级为 BLOCK） |
| 6 | 0.87→0.88 升级 | `test_upgrade_layout_converge_writes_only_guard_artifacts` | converge 新增文件 ⊆ {`.write-guard-state.json`, `.write-guard-violations.json`}；姿态配置零创建；`MD_ACTIVE`/epoch 0 不变 |

**结论**：发版自举（check-only 与 converge 两模式）在干净安装与升级两路径下均**不隐式激活**——BLOCK 姿态只能经 `--activate-block` 显式管理通道写入 `.write-guard-posture.json`（本版该文件缺省不存在 = 全 WARN 字节恒等语义），decision 权威源保持 `MD_ACTIVE` 缺省世界。运行时可查面（`load_authority` + `--show-posture`）在新装/升级两路径下如实反映未激活默认。**文档说明不代替默认行为验证的义务已由机器断言兑现。**

---

## ② Check 18/18b 分叉面 2 FAIL 正式例外（条件二）

### 活体复现（本票实测，2026-09-25）

`python skills/software-project-governance/infra/verify_workflow.py check-governance`（advisory 模式 exit 0）：

```
┌─ Check 18: Fact Grounding (FIX-080) ─────────────────┐
│  [FAIL] FIX-375 (EVD-1140): 缺少 事实依据: 字段
│  [FAIL] REL-087 (EVD-1164): 缺少 事实依据: 字段
┌─ Check 18b: Structured Evidence (FIX-083) ───────────┐
│  [FAIL] FIX-375 (EVD-1140): 缺少 结构化事实: JSON
│  [FAIL] REL-087 (EVD-1164): 缺少 结构化事实: JSON
```

与 M-2 门禁实测记录（release-checklist-0.88.0.md L130）逐字一致：恰 2 条记录 × 2 检查项 = 4 FAIL，其余 0.88 窗口同构机录行经 ✅ 豁免谓词或历史豁免跳过严检。

### 复核记录 1 — EVD-1140（FIX-375）

- **身份**：`.governance/evidence-log.md` L2606；行标识 `EVD-1140 | FIX-375 | 产品代码 | GovernanceDeveloper | 2026-09-24 | G11 | 完成`；机器写入标记 `governance-store evidence-append op-0aff7f5b21044ce094b389e23a310dc9；schema v1`。
- **状态链**（三层核验）：① ops 台账收据 `op-0aff7f5b…`：`command=evidence-append, task_id=FIX-375, status=ok, execution=succeeded, recorded_at=2026-09-24T09:50:09, new_revision=1665096, input_fingerprint=0f67a840…`；② 证据行内嵌同一 `operation_id`（行级对账键完整）；③ hot tracker 任务行 FIX-375 状态「完成」+ 审查链 REVIEW-FIX-375-R0 APPROVED_WITH_NOTES/0 → R1 APPROVED/0 终态在案。状态链无断点。
- **本应满足的规则**：Check 18 要求「事实依据:」字段、Check 18b 要求结构化事实 JSON——该行 `事实依据：test_governance_store.py 100 passed 零回归；test_verify_workflow+registry 1001 绿…；红绿四联探针` 实质完整，但按 DEC-168 机器行族列数契约落位于**独立 basis 列（parts[5]）**（`--basis` 通道的标准落点），而 Check 18/18b 严检路径只搜 description 列（parts[4]，`verify_workflow.py` L12627-12633/L14440-14448/L22489 同构读位）。**规则实质已满足，检查器读位与机录列布局分叉导致假 FAIL。**
- **复核结论**：非数据缺陷；机录行契约合规、事实充分、状态链完整。FAIL 属检查器侧保守豁免谓词（FIX-376 F-3 窄口径 `_COMPLETED_STATUS_PREFIX="✅"`，L12261/L12281 注释明示不采用 FIX-292 权威终态判定）的已知残余面。
- **责任人**：复核 = GovernanceDeveloper（本票）；例外批准 = Coordinator（M-3 席位）。

### 复核记录 2 — EVD-1164（REL-087）

- **身份**：`.governance/evidence-log.md` L2694；行标识 `EVD-1164 | REL-087 | 产品代码 | GovernanceDeveloper | 2026-09-25 | G11 | 完成——M-1 候选（工作树→本 commit 落库）`；机器写入标记 `governance-store evidence-append op-4328347bc92a4afd9d82171a7eb6ecff；schema v1`。
- **状态链**：① ops 台账收据 `op-4328347b…`：`command=evidence-append, task_id=REL-087, status=ok, execution=succeeded, recorded_at=2026-09-25T14:51:40, new_revision=1728797, input_fingerprint=4d70113a…`；② 证据行内嵌同一 `operation_id`；③ M-1 候选已落库（commit `72ddffb`）+ REVIEW-REL-087-R0 APPROVED_WITH_NOTES/0（八 MUST 全实测）。状态链无断点。
- **本应满足的规则**：同上——basis 经 `--basis` 落独立列 parts[5]（与全部 0.88 窗口机录行同构）；`check-version-consistency PASSED` / `verify 全量 PASSED exit 0` / `293P 精确` 等事实完整在案于 basis 列。严检路径搜 parts[4] 不可见 → 假 FAIL。
- **复核结论**：非数据缺陷；同 EVD-1140 归因。
- **责任人**：同上。

### 例外登记（限定范围——不做全局绕过）

| 维度 | 限定值 |
|------|--------|
| 具体记录 | **EVD-1140、EVD-1164（仅此两条）** |
| 检查项 | Check 18（Fact Grounding）+ Check 18b（Structured Evidence）严检路径 |
| 候选版本 | 0.88.0（M-3 审查窗口内有效；0.89 修复票落地即失效） |
| 豁免方式 | 登记+披露，**不改谓词、不加豁免行**（全局绕过禁止——DEC-240② 原文口径） |
| 消解条件 | FIX-390（修复票，见下）落地后自动消解 |

### 修复票票面（TRIAGE 建议——不实现，0.89 候选）

> **提议 ID**: FIX-390（编号以 TRIAGE 实际分配为准）· **优先级建议**: P2 · **owner**: GovernanceDeveloper
>
> **title**: Check 18/18b 严检路径改读结构化状态而非显示前缀/单一列——机录行 basis 列纳入事实判定
>
> **problem**: Check 18（Fact Grounding）/18b（Structured Evidence）对 evidence-log 行的事实判定只搜 description 列（parts[4]），且行豁免谓词为窄口径 ✅ 前缀读（FIX-376 F-3 保守分叉）。DEC-168 机器行族契约把 basis 落独立列（parts[5]），导致契约合规的机录行在任务行状态无 ✅ 前缀时必然假 FAIL（活体：EVD-1140/EVD-1164，2×2 FAIL，M-2/REL-089 两度实测）。
>
> **fix direction**: 事实判定改读**结构化状态**——basis 列（parts[5]）与机器写入凭证 marker（`机器写入：governance-store … op-…`）纳入 Check 18/18b 判定输入；豁免面扩展口径经 DEC 裁定（是否采用 FIX-292 权威终态判定替代 ✅ 前缀读——FIX-376 F-3 登记的后续票面）。
>
> **acceptance**: ① 覆盖 committed/✅/未知三态的回归测试（DEC-240② 要求的三态面）；② EVD-1140/EVD-1164 两行在修复后 check-governance 中转 PASS（红→绿活体验证）；③ 豁免面变化经穷举差分实证（FIX-382 静默集不变量同型义务 S_new ⊇ S_old 的扩张面逐行归因）；④ 既有 9-cell/列数契约零触碰（FIX-374/376/382 分叉面不回归）。
>
> **scope**: `verify_workflow.py`（Check 18/18b 读位）+ `tests/test_verify_workflow.py`；**不触碰**机录行族写入器与列数契约。

### 附票（条件三产物衍生的 0.89 候选——TRIAGE 建议，不实现）

> **提议 ID**: FIX-391 · **优先级建议**: P3 · **owner**: GovernanceDeveloper
>
> **title**: closure journal 版本感知读取器——0.87 语义视角的取消/重开/接管事件防护
>
> **problem**: 0.88 向 `closure-events.jsonl` 追加三类新事件（closure_cancelled/closure_reopened/closure_fenced）。v0.87.0 读取器（封闭枚举 8 型）跳过未知类型并响亮披露 problems（fail-safe 读，不崩溃），但**语义面误读**：已取消闭包在 0.87 视角仍为活跃，resume 可继续执行并以已被占用的 seq 追加（REL-089 实测碰撞向量：kept=[started(1),ready(2)] → next_seq=3 与 raw cancelled seq 3 相撞）→ 日志对双版本均损坏。
>
> **fix direction**: ① 写入器为新类型事件 payload 增加机器可读的 `writer_version`/`min_reader_version` 溯源字段（0.87 envelope 校验容忍未知 payload 字段——兼容）；② 读取器/回退工具提供「0.87 视角预检」命令（枚举含 0.88 事件的 closure 清单，供回退运行手册消费）；③ 终态防线的 runbook 门禁固化为 check 项（回退前 closure 清单登记）。
>
> **acceptance**: 新类型事件在 0.87 语义模拟（封闭枚举 8 型）下的行为有测试看护（REL-089 test_rel089_release_compat.py 已建基座）；碰撞向量被写入器侧防占用检查消除。

---

## ③ 持久状态回退兼容证明（条件三）

**方法**：v0.87.0 代码经 `git show v0.87.0:<path>` 提取至临时目录，子进程隔离运行（cwd=提取根；0.87 模块与 0.88 同名模块零污染）——「0.87 视角」行为测试 + 全树静态 grep（机器化的代码 diff 论证）。看护测试：`BackwardCompat087ViewTests`（5 用例）。

### 逐工件定性（四类六工件）

| 工件 | 0.88 写入器 | v0.87.0 引用 | 0.87 行为（REL-089 实证） | **定性** |
|------|-------------|--------------|---------------------------|----------|
| (a1) `.governance/.write-guard-state.json` | guard face-5 基线（FEAT-057/060/064；**双版共有工件**） | `verify_workflow.py` 唯一代码 reader（静态 grep 实证） | 0.87 loader 只校验 `schema_version==1` + `files` dict；0.88 写入 schema_version=1 同形 + **增量键 `updated_at`**（REL-089 实测）；0.87 loader 读 0.88 真实写入字节 → `(state, issue=None)`，四受管面基线完整可读。未知键被 0.87 容忍，无破坏无误读 | **兼容——可读可续用** |
| (a2) `.governance/.write-guard-violations.json` | write_guard_state.py（FEAT-060） | **0 命中**（全树 grep） | 未知文件，无任何 0.87 读路径 | **安全忽略**（披露：0.87 无违规状态机概念——open violations 回退后不可见） |
| (a3) `.governance/.write-guard-posture.json` | guard CLI 管理通道（FEAT-064） | **0 命中** | 未知文件。0.87 face-5 无 BLOCK 语义（全 WARN 时代） | **安全忽略**（披露：已激活 BLOCK 回退后**静默降级为全 WARN**——执法语义回归；0.88 恢复后 posture 文件原地重新生效） |
| (b1) `.governance/closure-events.jsonl`（+ 0.88 三新事件） | closure_chain.py（FEAT-062/063） | **共有工件**：0.87 封闭枚举 8 型 + schema window [1,1] | 0.87 `_load_closure_events` 读 0.88 journal：**不崩溃**——新类型行逐行跳过 + problems 响亮披露（`unknown closure event_type 'closure_cancelled' (closed enum of 8 types)` ×3 实测）；**语义面误读实证**：取消/重开/接管闭包在 0.87 视角 = 活跃（started 在场 → resumed），resume 可继续且 next_seq 与 raw 已占用 seq 相撞（kept=[1,2] → next=3；3 ∈ raw） | **部分兼容——读 fail-safe、语义有界不兼容**（处置见下） |
| (b2) `.governance/closure-generations.json` | closure_chain.py（FEAT-063 fencing sidecar） | **0 命中** | 未知文件 | **安全忽略**（披露：0.87 无执行代际 fencing——回退后陈旧代际写不被拒绝） |
| (c1) `.governance/archive/.migration/<…>/journal.json` | archive.py 大表续迁（FEAT-061/FIX-385） | **0 命中** | 0.87 archive 枚举只扫固定子目录（tasks/evidence/decisions/risks）的 `*.md` 与 releases 的 `*.json`（实测：`.migration` 目录与 journal 零枚举、零触碰、原样在场；非 .md 诱饵文件同样被忽略） | **安全忽略**（披露：续迁游标 0.87 不可见——中断迁移不自动续跑，恢复 0.88 后续迁） |
| (c2) `.governance/.decision-migration/<id>/journal.json` | decision_repository / decision_migration（FEAT-061） | **0 命中** | 未知文件，无读路径 | **安全忽略** |
| (d) `.governance/.decision-store-state.json` | decision_repository（FEAT-061 权威状态机） | **0 命中** | 未知文件。0.87 decision 面直写/直读 `decision-log.md`；本版权威源缺省 = `MD_ACTIVE`（md 完整权威）→ 0.87 读到完整 md | **安全忽略**（**前提披露**：若 0.88 期间发生过 JSON 切换则 md 可能 stale——须先走 B-13 反向转换再回退；本版 MD_ACTIVE 缺省未切换，RISK-059 三条件未触发） |

**条件三代码修改面裁定**：六工件中五件 = 安全忽略/兼容 → 按票面「最小修改面」**只加测试证明，零产品代码修改**；(b1) 为唯一语义不兼容面，其「防御性拒绝」**在 0.88 侧不可达**——0.87 是已发布 tag（路径 A 不可修补；路径 B 的重建分支可修，归入 FIX-391），0.88 侧唯一可做的伪造 tombstone（向 journal 追加 0.87 可识别的终态事件）违反 P1（编造事实）与 closure 域 append-only 审计纪律，**否决**。实际防线 = 回退运行手册门禁（下节）+ FIX-391 修复票。此裁定属最小修改面与事实纪律的正确交集，无过度工程。

### rollback-plan 补节文本（proposed——Coordinator 落位 `docs/release/rollback-plan-0.88.0.md`）

> ### §N 回退路径区分：部署 v0.87.0 tag vs revert 29 commits 重建（REL-089 · DEC-240③）
>
> **共同前提**：源码回退**不撤销数据写入**——0.88 已产生的持久状态工件原地保留（`.write-guard-state.json` / `.write-guard-violations.json` / `.write-guard-posture.json` / `closure-events.jsonl` 0.88 事件 / `closure-generations.json` / `archive/.migration/` / `.decision-migration/` / `.decision-store-state.json`）。兼容性逐工件定性见 REL-089 报告：五件安全忽略/兼容，closure journal 部分兼容（读 fail-safe、语义有界不兼容）。
>
> **回退前通用步骤（0.88 仍在位时执行并留档）**：
> 1. 登记 in-flight closure 清单：检查 `.governance/closure-events.jsonl` 尾部是否含 0.88-only 事件类型（`closure_cancelled` / `closure_reopened` / `closure_fenced`）——含任一者的 closure 进入「0.88 事件闭包」清单；
> 2. `write-guard-bootstrap --check-only` 世界判定留档（converged 与否均留档）；
> 3. 确认 `.governance/.decision-store-state.json` 权威状态 = `MD_ACTIVE`（本版缺省必为 MD_ACTIVE；若非——0.88 期间发生过切换——先执行 B-13 反向转换并校验 md 完整性，否则**禁止回退**）；
> 4. 冻结写窗（停止一切治理写入）。
>
> **路径 A——部署 v0.87.0 tag**（peel `602f8f3`）：
> - 操作：以 v0.87.0 tag 安装/部署插件，`.governance/` 数据不动；
> - 特性：0.87 代码**不可修补**——closure 语义防线只有运行手册门禁：**回退后禁止 resume/finalize 任何「0.88 事件闭包」清单中的 closure**（0.87 会响亮披露 `unknown closure event_type` problems——出现该披露即停，经人工核对 journal 尾部后处置；恢复 0.88 后再对该闭包做终态操作）；
> - 0.87 下 guard face-5 首跑按 amnesty 对存量行重建基线（0.88 增量键 `updated_at` 被 0.87 容忍读取，首次 0.87 收敛写回 3 键形状——字节面随写收敛，无破坏）；
> - 违规台账/姿态配置/fencing sidecar/续迁游标被 0.87 忽略（不破坏、不可见）。
>
> **路径 B——revert 29 commits 重建**（v0.87.0..M-1 tip，清单见 CHANGELOG 0.88.0「Commit 区间」）：
> - 操作：按 commit 逆序 revert 全部 29 commits → 重建分支 → 安装重建产物，`.governance/` 数据不动；
> - 特性：重建分支**可先行落防御性修复**——按 legacy_snapshot_backport 政策（FIX-381 先例）将 FIX-391（closure 版本感知读取器）backport 进重建分支后再切换，closure 语义面由机检防护（仍建议保留路径 A 的运行手册门禁作为双保险）；
> - 其余工件行为与路径 A 完全一致（同一 0.87 语义基线）。
>
> **回退后验证（DEC-240③ 最低验证映射，两路径同集）**：
> 1. 启动：0.87 `verify_workflow.py` 全量 PASSED；
> 2. 读写：`governance-store decision-append` 直写 decision-log.md 成功（MD_ACTIVE 世界）；
> 3. 任务恢复：仅对 journal 无 0.88 事件的 closure 执行 resume；含 0.88 事件者按门禁处置；
> 4. 一致性：0.87 guard face-5 重建基线零意外 WARN（amnesty）；四类 0.88 工件在场不阻断任何 0.87 检查（REL-089 测试基座佐证）。
>
> **恢复 forward（0.88 复装）**：五件被忽略工件原样恢复生效（posture/violations/fencing/续迁游标零丢失）；closure journal 经 0.88 读取器全量可读（0.88 认识全部事件类型）。

---

## 验证汇总（硬门槛）

| 门槛项 | 结果 | 证据 |
|--------|------|------|
| 新增看护测试 | **11 passed** | `python -m pytest skills/software-project-governance/infra/tests/test_rel089_release_compat.py` → 11 passed（条件① 6 + 条件③ 5） |
| 全量套件零回归（4108P 基线） | 见会话机器记录 | `python -m pytest skills/software-project-governance/infra/tests -q`（本票执行，结果随 structured result 回传 Coordinator） |
| check-cross-references | PASS | `verify_workflow.py check-cross-references` → 无悬挂/无循环 |
| check-manifest-consistency | 新增文件无缺口 | `test_rel089_release_compat.py` 命中既有 tests glob；唯一 UNTRACKED = 根 `changelog.md`（**REL-087 M-1 双位过渡既有披露面，非本票引入**，canonical 归属留 M-3 裁决） |
| 向后兼容 | PASS | 零产品代码修改（纯测试增量）；CLI 接口零变化 |
| 无 AI 幻觉 | PASS | 全部断言基于 git show v0.87.0 提取代码实跑 + 当前代码实跑；定性表每行有测试或 grep 证据锚 |

## 修改文件清单

| 文件 | 变更 |
|------|------|
| `skills/software-project-governance/infra/tests/test_rel089_release_compat.py` | **新增**（本票唯一交付文件；~500 行） |
| 产品代码（write_guard_state.py / closure_chain.py / archive.py） | **零修改**（定性裁定：五件安全忽略/兼容只加测试；(b1) 防御在 0.88 侧不可达——见条件三裁定） |
| `docs/release/rel-089-m3-precondition-report.md` | 新增（本报告） |

## Coordinator 写回清单（proposed entries）

1. **evidence-log entry**（REL-089）：

> | EVD-11xx | REL-089 | 产品代码 | 0.88.0 M-3 前置补强票（arch 抽检三放行条件 DEC-240）：①未激活默认运行时验证——新增 test_rel089_release_compat.py 两路径 6 断言（干净安装/0.87+0.88 共存世界 ×check-only 零写入/converge 只写守卫工件/show-posture 全 WARN/load_authority MD_ACTIVE）全绿；②Check 18/18b 分叉面 2 FAIL 正式例外——EVD-1140/EVD-1164 人工复核（身份/ops 收据状态链/basis 列 parts[5] 契约落位 vs 严检搜 parts[4] 读位——非数据缺陷）+例外限定（记录×2/检查项×2/候选 0.88.0）+修复票 FIX-390 票面（检查器读结构化状态，0.89 候选）；③持久状态回退兼容——v0.87.0 提取代码子进程实跑+全树 grep 机检：六工件逐项定性（guard 状态基线兼容可读〔增量键 updated_at 被 0.87 容忍〕/violations ledger+posture config+fencing sidecar+两个 migration 工件+authority marker 安全忽略/closure journal 部分兼容——读 fail-safe 实证+seq 碰撞向量实证）+两回退路径区分补节文本（proposed）；产品代码零修改（最小修改面裁定）；11P 新增全绿。 | 事实依据：pytest 11 passed；git show v0.87.0 提取实跑 5 用例；check-governance 活体复现 2×2 FAIL 逐字；全量套件 <结果回填>；cross-refs PASS | skills/software-project-governance/infra/tests/test_rel089_release_compat.py; docs/release/rel-089-m3-precondition-report.md | GovernanceDeveloper | 2026-09-25 | G11 | 完成 |

2. **decision-log entry**（可选——正式例外登记，DEC-240② 落地件）：

> | DEC-24x | 2026-09-25 | Coordinator | Check 18/18b 分叉面 2 FAIL 正式例外批准（DEC-240② 兑现）：EVD-1140+EVD-1164 人工复核通过（身份/状态链/本应满足规则三面核实——机录行 basis 独立列契约合规，检查器读位分叉所致假 FAIL）；例外限定 记录={EVD-1140,EVD-1164}×检查项={Check 18,18b}×候选版本=0.88.0；不做全局绕过（谓词不放宽）；消解条件=FIX-390 落地。REL-089 报告为复核证据载体 | REL-089 报告 §②（docs/release/rel-089-m3-precondition-report.md）；ops 收据 op-0aff7f5b…/op-4328347b… | — | Coordinator | 2026-09-25 | G11 | — |

3. **TRIAGE 入账**：FIX-390（P2，0.89 候选）+ FIX-391（P3，0.89 候选）票面文本见本报告 §②。

4. **rollback-plan 补节**：§N 文本（本报告 §③ 加引区块）落位 `docs/release/rollback-plan-0.88.0.md`。

## 已知披露（非阻断）

- 根 `changelog.md` manifest 缺口 = REL-087 既有披露面（双位过渡 canonical 归属留 M-3），本票未触碰；
- closure journal 语义面在 0.87 回退世界为**有界残余风险**（运行手册门禁承载 + FIX-391 承接）——放行口径内如实披露；
- 本票验证全部在仓库内/隔离临时目录完成，无真实环境操作（破坏性红线不适用）。
