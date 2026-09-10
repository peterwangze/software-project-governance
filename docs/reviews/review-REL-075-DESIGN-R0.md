# Design Review — REL-075-M3-DESIGN（0.79.0 candidate 判定面/守卫面批次）

- **Reviewer**: Design Reviewer Agent（dispatch: REL-075-M3-DESIGN）
- **Round**: R0（本候选设计侧首审；无前轮——各任务开发期双审已闭环，本审查为发布聚合面复核，与 `review-REL-075-RELEASE-R0.md`（流程/清单面）互补，非同一分析框架）
- **审查对象**: staged candidate（`git diff --cached`：M-1 打包面 27 文件 +302/−33——版本投影 0.78.1→0.79.0〔15 投影 + @bootstrap-version 标记面 + REQUIRED_SNIPPETS 6 版本钉〕+ release 三件套 + CHANGELOG）**∪ 判定面实体现状**（`v0.78.1 (6b5e7bf)..HEAD` 34 任务 commit——聚合面审查对象是「本窗多个判定变更共存后」的候选整体状态）
- **方法**: 只读审查。规范加载 `agents/design-reviewer.md` + `skills/design-review/SKILL.md` + `skills/tech-review/SKILL.md` 全文；事实依据 = staged diff 全文、引擎/基线/快照实体读取、decision-log/plan-tracker 对账、4 项只读机器实测（见附录 A）。零 .governance/产品文件写入（唯一产出 = 本报告）。
- **日期**: 2026-09-10

---

## 结论（终态四选一）

> **APPROVED_WITH_NOTES**
> unresolved_blockers = 0
> BLOCKING findings = 0；WARNING = 2（W-1/W-2）；OBSERVATION = 3（O-1~O-3）

发布聚合面（判定面/守卫面）设计复核通过：本窗 6 组判定面变更的共存语义一致、依赖序无冲突、fail-safe 方向论证成立、守卫分层清晰无重复无缺口；EVD-983 归档迁移不阻断发布。两条 WARNING 均为非阻塞的文档准确性/回滚路径健壮性事项，建议 M-4 授权前低成本处置（见 §6）。

---

## 1. 判定面聚合一致性（焦点 ①）——PASS（含 W-1）

### 1.1 四变更共存语义核验（逐对依赖序）

| 变更 | 实体证据（本次复核实测） | 与其他判定变更的关系 |
|---|---|---|
| FIX-291 Check 30 形状/终态 | `checks/review_domain.py`：`source_format` 四分类（machine/historical/machine_format/unknown，L1946/L2578-2606）+ rank 合并（L1926-1998）+ pre-FIX-174 历史形状 WARN（L2149-2361）；`verify_workflow.py` L10401-10535 W-7/BC-7 终态 marker 集（✅ 字形 + 词表严格断言，trailing-terminal 规则） | **被 FIX-292 消费**：`_status_is_completed_cell`（L10503）为唯一权威，292 只委托不改写——revert 依赖序 292→291 在 rollback-plan S2 显式登记 ✓ |
| FIX-292 谓词对齐 | `_is_incomplete_task_status`（L12252-12279）docstring 明示「Delegates to the W-7/BC-7 authoritative terminal-chain predicate (FIX-291)」，`return not _status_is_completed_cell(text)`——单点委托，无第二权威；测试 L18087/L18144（「权威词表边界〔DEC-181 消费不改写〕」） | 消费 FIX-291 权威（同数据 124→88，plan-tracker 行实测留痕）；与 FEAT-020 冻结面无冲突——18c~18i 谓词变化先于冻结落定 |
| FEAT-020 契约冻结 | `infra/contract_matrix/snapshots.json`：四契约面 live 计数 **cli_dispatch.key_count=82（keys=82）/ check_segments=70 / result_shapes=5 / guard_output_pin**；`freeze_point.residual_waves` 自记 0.79.0 尾波〔FEAT-012/FEAT-013/FX-195〕；`version_status="0.79.0 未 released"`；generator `--self-check` 实测**两次连续提取恒等（7,773 bytes，零差异）** | 冻结时点在 FIX-299/300+FEAT-017 三件套之后（FEAT-020 任务行 depends_on 显式编码「FIX-299+FIX-300+FEAT-017」）——冻结形状已包含判定面修复后的终态 ✓ |
| FEAT-019 棘轮 fatal | `core/architecture-baseline.json`：R1 `anchor_loc=24329`（零豁免配额自举豁免条目 DEC-183/184 显式登记）；`archguard_ratchet.py` 模块头自declare「advisory Check 28 族的 FATAL 对位」；候选时点实测 **R1~R7 全 PASS（0 violations，fatal gate green）** | R5 消费 FEAT-020 快照；**R5 实测输出 `cli keys 82/82 frozen, segments 70/70 frozen`**——live 派发表 = 冻结快照，机器级闭环 ✓ |

**再生成链无语义漂移**：80 键（FEAT-020 `c92bf5d` 冻结）→ 81（FEAT-019 `c443757` 显式再生成，耦合面双审共同裁决，任务行留痕）→ 82（FEAT-013 `3a108c2` sanctioned，commit message + 快照 residual_wives 双留痕）。每次再生成均有披露；R7 `committed==fresh True` 保证当前工件 = 冻结工件。R1 锚链 24,302 →（FEAT-012 实战收紧）24,269 →（FEAT-013 sanctioned 薄入口 +60，审计补账候选 F-3 登记）24,329——只降不升语义经豁免条目零配额设计保护（超锚仍 FAIL）。

**对照 plan-tracker 任务表**：FEAT-020/019/013 任务行与快照/基线实体一致（FEAT-020 行 80 键 = 交付时点描述；FEAT-019 行含 80→81；FEAT-013 行含 R1 24,269→24,329）。「82 键/70 段」终态由机器工件（snapshots.json + R5 输出）承载——**但发布三件套未同步该终态数字，见 W-1**。

### 1.2 W-1（WARNING）：三件套终态数字漂移（低估侧，非 overclaim）

- `docs/release/feature-flags-0.79.0.md` Behavior 表：「契约矩阵 harness…快照四契约面（**CLI 80 键** / Check 70 段…）」——本候选实际发布工件为 **82 键**（FEAT-019/013 sanctioned 再生成后）。
- `docs/release/rollback-plan-0.79.0.md` S2：「FEAT-020 快照显式再生成（**80→81** 键耦合同步）」——缺 FEAT-013 的 81→82 一跳；同表 R1 引「24,302→24,329」（已含 FEAT-013），同段两数字代际不一致。
- 次级同型（仅注记）：CHANGELOG/FEAT-019 行「R4 print 1,315」为交付时点值，live 基线经 FEAT-012 后续 sanctioned regen 已单调收紧至 1,310（R4 实测 PASS `1310 ≤ 1310`）——叙述历史值 vs live 锚值非同代，但措辞属交付时点描述，不构成当前值声明。
- **影响评估**：零行为影响（R5 机器门 82/82 全绿；漂移方向为低估，无 overclaim；plan-tracker/commit 链完整）。但三件套是 0.79.0 对外发布文档面，读者据其预期 80 键将与 shipped 工件（82）不符——与本项目「机器可核验宣示」纪律相悖。
- **建议**：M-4 授权前在 staged 文档面修正两处数字（80→82 / 80→81→82），或在 feature-flags 该行补「终态 82 键（FEAT-019/013 sanctioned 再生成，见 residual_waves）」注记。非阻塞。

---

## 2. 守卫体系分层（焦点 ②）——PASS

三层守卫各锚定一个工件面，职责正交、无重复、无缺口：

| 层 | 组件 | 强制时点/级别 | 实测（候选时点） |
|---|---|---|---|
| 写时数据面 | governance-write-guard（FEAT-011/FIX-297）+ post-commit Step 4b（FEAT-017/FIX-302） | B 级 CLI 工件（exit 0/1/SKIP，只检不改）+ A 级协议触发（behavior-protocol M1.2「直写后 MUST 复跑」）；hook 面板 = advisory 显示**非阻断、不宣示时点强制/C 级** | 实测 **PASS / exit 0**（四面：M1 签名 / TRIAGE-RECO 行族 / Check 26 锁 schema / 18c 字段表，0 issues）——EVD-983 迁移后热数据仍全绿 |
| 开发时代码面 | ArchGuard 棘轮 R1~R7（FEAT-019，fatal 位） | R1-R4/R7 fatal（violation → exit 1）；R5 消费 FEAT-020 快照（缺失 → SKIP+披露，不静默 fatal）；R6 advisory（阈值随 FEAT-018 落地，v1 永不 fatal——模块头 + 基线 note 双声明） | 实测 **R1~R7 全 PASS**；R5 = 冻结一致门（82/82、70/70） |
| 发布时就绪面 | check-release（含 FEAT-016 `dsh_upgrade_regression` execution gate）+ release-ledger | execution gates 开启时实跑并阻断 FAIL；`--skip-execution-gates`/BR-4 显式 [SKIP] 披露；FIX-299 恢复「healthy → PASSED/exit 0」文档化契约 | 组件/旁路设计面核验一致（M-2 实测回填为 Coordinator 义务，本审查不越权代跑） |

- **分级口径一致性**：`SKILL.md` L116（M1.2 MUST 复跑）+ L120-129 分级声明（write-guard = B 级工件 + A 级协议触发，post-commit advisory 显示面；C 级未实现不宣示）与 feature-flags Behavior 表、FIX-302 canonical 措辞、FEAT-017 回滚文档（回滚=删 Step 4b）**逐句对齐** ✓。
- **R5 fail-open 边界**（唯一 SKIP 路径）：已披露 + 双重背书——R7 `committed==fresh` 保证快照在库即被校验；manifest dir 条目（`infra/`、`core/`）经 `_expand_section` rglob 全量入 canonical，**cleanup 残留清理不会误删冻结快照/棘轮基线**（O-1 详注）。
- 无缺口结论：write-guard（数据形状）× 棘轮（代码结构演进）× release gate（发布就绪）——未发现任一工件面无守卫覆盖，未发现同面双守卫冲突裁决规则缺失。

---

## 3. fail-safe 方向核验（焦点 ③）——PASS（breaking=无 设计侧复核成立）

| 变更 | 方向 | 边界锁定证据 |
|---|---|---|
| Check 30 历史形状（FIX-291①） | 放宽（历史形状 FAIL→WARN） | `test_review_closure_legacy.py` L639「ACTIVE（⏳ 待执行）任务的历史形状链缺轮 → 恒 FAIL」+ L665 边界用例——「ACTIVE/真实 nonzero 恒 FAIL」不放宽，八条组合路径无放宽带实测 |
| 30c 机器行白名单（FIX-291⑧） | 放宽（合法机器行 35→2 WARN） | ID 列锚定 + 溯源豁免日期序/validity 校验——白名单仅收合法 REVIEW-/RECO- 行，非泛化 |
| Check 36 R3 / Check 10 M5（FIX-294/295） | 放宽（豁免+披露） | [EXEMPT] 披露显式；不可解析保留 WARN（诚实 fail-closed 残留） |
| G5 tpa 缓存（FEAT-012） | 放宽（fail-open） | `--force` 旁路 + 完成必推荐首次义务穿透缓存（专测）+ RECO 三条件抑制 |
| 棘轮 fatal 门（FEAT-019） | 收紧（新增门） | 候选时点全绿（实测）——仅在未来回归时触发；sanctioned regen 零豁免配额 + DEC 追踪 |
| 派发锁存在性校验（FEAT-013） | 收紧（exit 2 零写入） | `--expected-new` 豁免审计化；Check 26 `expected_new` 可选向后兼容 |
| release gate 组件（FEAT-016） | 收紧（阻断 FAIL） | skip 路径显式 [SKIP] 披露——收紧不越权为不可旁路 |
| FIX-299 exit 语义 | 恢复文档化契约 | healthy→exit 0（原为无条件 FAIL 的 fail-closed 误置）；消费面 grep 实证无 quirk 依赖者（REVIEW-FIX-299-R0）；判定规则零改动 |

**「无接口删除/重命名/默认行为破坏」设计侧证据**：CLI 键 80→82 仅增不减（R5 冻结匹配 = 无删改）；Result 形状 5 面冻结后 self-check 零差异；FIX-300 判定规则零改动（verdict_scope 显式化 + 复核通道）。**breaking=无 论证在设计侧成立**（与三件套声明一致；M-2 门禁实测为最终裁判，本审查不预填）。

---

## 4. EVD-983 归档迁移的设计边界（焦点 ④）——不阻断发布（含 W-2）

- **守恒实测**：`check-archive-integrity` 候选时点复跑 **PASS**（85 hot + 91 archived = 176 total；index 1,028）——与 EVD-983 记录（Archived 91/Index 1028/Total 176）恒等。
- **判定面消费方适配**：①Check 36 R3 归档 ID 解析（FIX-294，DEC-151 豁免+披露口径，不可解析保留 WARN）；②Check 30 历史链按 source_format 降 WARN（FIX-291）；③治理规则「归档文件中的证据 = 有效证据」+ bootstrap 归档感知路径（AGENTS/CLAUDE.md Step 1.3）。
- **authority 离热（58 DEC 迁出）**：AUDIT-152 任务行已登记「新发现 EVD-983 归档副作用族（**N2/N3 候选**）」+ N1~N5 处置候选登记——已知、已披露、非隐藏。**设计裁决：不构成发布阻断**——理由：(a) 守恒校验 PASS 且幂等；(b) 判定面消费方已适配或诚实降级；(c) 候选任务已登记不带入隐藏敞口；(d) 完整备份存在可恢复。
- **W-2（WARNING）**：rollback-plan S2 的归档恢复路径依赖 `%TEMP%\governance-backup-20260910-prefix301`（863 文件）——**%TEMP% 为易失位置**（OS 磁盘清理可清除），且发布后回滚需求恰好发生在时间距离迁移最远的时点。缓解已在（迁移幂等 + integrity 复验 + 禁手工拼合），残余风险=备份本体丢失后只能依赖归档文件本身的幂等性重建。**建议**：M-4 授权前将备份转存持久位置（仓外归档目录或 .governance 同级备份区）并在 EVD-983 补一行新位置——零代码、纯操作。非阻塞。

---

## 5. 三件套 No-overclaim 纪律抽查（焦点 ⑤）——PASS

- 三件套均含 No-overclaim Boundaries 节 + needles（check-release #10 静态门禁消费面）✓。
- **RISK-049 关闭声明口径抽查**：feature-flags/checklist/CHANGELOG 均限定「①dsh 用户面宣示〔DEC-179〕②isolation 加载面等级〔DEC-180〕；live/headless 与非 dsh 适配器登记后续候选」——与 decision-log **DEC-185**（2026-09-09 用户裁决）+ DEC-179/180 原文逐项一致，无口径放大 ✓。
- RISK-044「缓解中/评估交付非实现」、RISK-046「根因修复已交付但维持打开至 09-30」、RISK-036/039 不关闭——三件套与 CHANGELOG Boundaries 口径统一 ✓。
- candidate-only 纪律：`release_authorized=false`（M-4 唯一人工门 DEC-143）；M-2 门禁表**未预填 PASS**（14 项全部「待 M-2/M-6 回填」，含 quality-tools「NOT_RUN 如实记录——不虚构 PASS」）✓。
- DSH preset 时滞披露（未 sync 不宣称会话级效果）✓；MINOR bump 依据（VERSIONING L12 三支 + L37 契约面）与 DEC-177⑧ 一致 ✓。
- 唯一准确性缺陷 = W-1（**低估**侧数字漂移）——不构成 overclaim。

---

## 6. 蓝军挑战（tech-review Step 4——≥3 条，含标准格式）

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|---|
| BM-1 | 「冻结」语义被 sanctioned regen 洗白：窗口内快照再生成 ×2、R1 锚 sanctioned 上调 ×1（+60）——若 regen 无审计，棘轮/冻结均可被静默改写 | 高（若成立）——判定面权威失效 | R7 `committed==fresh` + regen 幂等三连同哈希；baseline 豁免条目**零配额**（超锚仍 FAIL，条目仅为 DEC 披露非增长许可）；每次 regen 在 commit message + 快照 residual_waves + 任务行三处留痕；耦合面双审 | 低 | FEAT-019 W1（CI regen 方向断言）已登记 0.80.0——维持 |
| BM-2 | 多重 WARN 放宽复合后信号丢失：Check 30 历史降级 × 30c 白名单 × Check 10/36 豁免 × G5 缓存抑制同窗落地，真实回归可能被压成 WARN 群 | 中——降噪与灵敏度此消彼长 | 「ACTIVE/真实 nonzero 恒 FAIL」边界锁定八路径实测；豁免全部 [EXEMPT]/披露显式（可审计计数）；降噪链各步 A/B 实测留痕（117→…→31） | 中低 | M-2 打包期以实测基线复核构成（checklist 触发器 #3 已预设「新增 FAIL 类」口径）|
| BM-3 | 归档回滚单点：authority 已离热 + 恢复依赖 %TEMP% 备份（易失）——发布后若需回滚归档面，备份可能已被 OS 清理 | 中 | 迁移幂等 + integrity 校验 + 禁手工拼合；备份 R1(b) 三选一留痕 | 中 | **W-2**：M-4 前转存持久备份 |
| BM-4 | cleanup 残留清理 × 冻结工件交互：升级场景 bootstrap 自动 cleanup 若将 snapshots.json/architecture-baseline.json 判为残留删除 → R5 SKIP、R1 基线缺失 fail-closed | 高（若成立） | **已证伪**：manifest `infra/`、`core/` dir 条目经 `_expand_section` rglob 全量入 canonical（cleanup.py L201-207）→ 冻结工件非残留；check-manifest-consistency `covered_by_dir` 同语义（checks/manifest.py L444-446） | 低 | O-1：显式 file 条目登记建议（见下） |

---

## 7. 硬门槛裁决（design-reviewer.md）

| 门槛 | 阈值 | 裁定 | 依据 |
|---|---|---|---|
| 候选方案 ≥2 | ≥2 | ✅ | 聚合面审查——底层决策均带备选：DEC-177（同窗双入槽 vs 串行）、DEC-181（入槽 0.79.0 vs 0.80.0 vs 拒绝）、DEC-184（27 项全录 vs P0 任务化）、DEC-185（立即关闭 vs 延后）各自「被否决方案」列完整 |
| ADR/DEC 关键字段 | 100% | ✅ | 抽查 DEC-177/181/184/185：日期+背景+决策+备选+排除理由+影响范围+后续动作齐备 |
| 蓝军挑战 ≥3（独立 ID） | ≥3 | ✅ | BM-1~BM-4（标准格式输出，含一条已证伪向） |
| 模块无循环依赖 | =0 | ✅ | R3 机器实测：12 edges、SCC max 1、0 violation（archguard-ratchet PASS 输出） |
| Bar Raiser（对立面框架） | 已执行 | ✅ | 本审查以判定面/架构守卫面框架独立展开，与 Release Reviewer（流程/清单面）框架正交互补；结论在切换框架后独立得出 |

---

## 8. 发现汇总

| ID | 级别 | 内容 | 处置建议 | 阻塞 |
|---|---|---|---|---|
| W-1 | WARNING | 三件套终态数字漂移：feature-flags「CLI 80 键」/ rollback-plan「80→81」vs shipped 快照 **82 键**（R5 机器实证 82/82）；R4「1,315」为交付时点值 vs live 锚 1,310 | M-4 前修正 staged 文档两处数字或补终态注记（低估侧，零行为影响） | 否 |
| W-2 | WARNING | 归档回滚路径依赖 %TEMP% 备份（易失） | M-4 前转存持久位置 + EVD-983 补注 | 否 |
| O-1 | OBSERVATION | FEAT-019/020 新工件经 manifest **dir 条目**覆盖（checker/cleanup 语义一致、无缺口），而非显式 file 条目；checklist 门 #3 措辞「MUST 已登记 manifest」强于实际机制 | 0.80.0 REFACTOR-contract-layer 时为判定面权威工件（snapshots.json / architecture-baseline.json）补显式 file 条目 + validation_commands 绑定（architecture-health.json 先例） | 否 |
| O-2 | OBSERVATION | R5 缺快照 → SKIP+披露（fail-open）为守卫体系唯一非 fatal 边——设计自洽（披露 + R7 背书），但 0.80.0 快照消费面扩大后建议评估升 fatal | 登记 0.80.0 演进候选（FEAT-019 W 系同域） | 否 |
| O-3 | OBSERVATION | 判定面终态数字（82 键）在人类可读治理面（plan-tracker 任务行/三件套）止步于 81——仅 commit message 与机器工件承载终态；与 W-1 同根因 | 随 W-1 一并处置 | 否 |

---

## 9. 附录 A——机器实测记录（本审查执行，全部只读，零写入）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `verify_workflow.py archguard-ratchet` | R1 24,329≤24,329 / R2 46≤46 / R3 12 edges SCC 1 / R4 1,310≤1,310 / **R5 cli keys 82/82、segments 70/70 frozen** / R6 INFO advisory / R7 committed==fresh —— **PASS（fatal gate green）** |
| 2 | `contract_matrix/generator.py --self-check` | 两次连续提取恒等（7,773 bytes，零差异） |
| 3 | `verify_workflow.py check-archive-integrity` | **PASS**——85 hot + 91 archived = 176；index 1,028 |
| 4 | `verify_workflow.py governance-write-guard` | **PASS / exit 0**——四面 0 issues（迁移后热数据） |

## 附录 B——事实依据索引

- staged diff 全文（27 文件；`git diff --cached`）；`git log v0.78.1..HEAD` 34 commit 清单与 release-checklist Change Inventory 表逐行对账一致
- `infra/contract_matrix/snapshots.json`（faces/freeze_point/generated 实读）；`core/architecture-baseline.json`（R1 锚/豁免/R5 消费/R6 阈值 null）
- `verify_workflow.py` L10401-10535（W-7/BC-7）/ L12252-12279（谓词委托）；`checks/review_domain.py` L1906-2606（source_format/历史形状）；`archguard_ratchet.py` 模块头 + L916-1106（fatal/SKIP 语义）
- `SKILL.md` L116/L120-129（分级声明）；`cleanup.py` L61-107/L187-252（canonical 展开）；`checks/manifest.py` L406-446（covered_by_dir）
- `.governance/plan-tracker.md`（FIX-291 L188 / FIX-299 L204 / FIX-300 L205 / FEAT-013 L198 / FEAT-019 L212 / FEAT-020 L214 / AUDIT-152 L207）；`.governance/decision-log.md` DEC-177/181/184/185
- `docs/reviews/review-*`（48 份机录审查报告在册，含本批判定面任务全链 R0~R2 与 REL-075-RELEASE-R0）

---

**审查结论（机录消费字段）**

```
REVIEW-REL-075-DESIGN-R0
verdict: APPROVED_WITH_NOTES
unresolved_blockers: 0
blocking_findings: 0
warnings: 2 (W-1 doc-number drift; W-2 %TEMP% backup durability)
observations: 3 (O-1 manifest explicit-entry; O-2 R5 fail-open edge; O-3 terminal-number doc chain)
round: 0
reviewer: design-reviewer
scope: staged candidate + v0.78.1..HEAD 判定面/守卫面聚合
machine_evidence: archguard-ratchet PASS / contract self-check zero-diff / check-archive-integrity PASS / governance-write-guard PASS(exit 0)
```
