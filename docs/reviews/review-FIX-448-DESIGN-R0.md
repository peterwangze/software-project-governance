# FIX-448 设计独立审查报告 R0（Design Reviewer）

- 审查对象：`docs/architecture/evidence-hot-cold-compaction.md`（Architect 设计文档，PROPOSED，immutable，本次零修改）
- Task ID：FIX-448 · Round：R0（首轮独立审查，无前轮）
- Reviewer：Design Reviewer Agent（独立于 Architect；G5 设计通过门的独立裁决面）
- 审查时间窗：2026-10-20T09:05Z ~ 09:24Z（全部命令清单见 §7）
- **最终结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**（结构化字段：无未解决 BLOCKING finding；本通过保留 P3 备注，见 §4）

## 0. 结论边界（防止误读，先于一切）

1. 本结论批准的是**设计文档本身的质量**：容量阻断结论的真实性、算术正确性、方案可审性、决策路径清晰度。**不等于实施授权**——设计自身 `implementation_authorized=false`（§13），§12 五项未决项仍需 Coordinator 逐项裁决。
2. 本结论**不解除** FIX-448 容量验收 BLOCKED：热表 <650,000 B 且 28s PASS 的原验收仍为 BLOCKED。设计没有、本审查也没有找到在现有暂停/missing fail-closed/原门约束下解除它的合法路径。
3. 本结论不改变 FIX-444/445 暂停（DEC-342）、FIX-446 保护范围语义、source NOT_ESTABLISHED 历史状态。

## 1. 审查范围与方法

按 Coordinator 任务书的六个维度执行：容量算术核验（独立复算，非复述）、标签真实性抽检、方案完备性、边界协同、决策面清晰度、反作弊核验。核验手段：设计文档全文通读；S0/S1/S2 快照 hash 与字节数复测；用项目自身单源分类器（`archive.scan_row_families` + `_build_classification_context`，与实际迁移门零漂移）在 S2 快照上**重新分类并自行聚合** frozen/missing/union/active；对设计 §2.2/§4 引用的 40+ 源码锚点逐一比对实际行；容量门实现（`architecture-health.json` / `verify_workflow.py`）语义核对；取证目录（design-r0、design-recovery-20261020）与 command-audit.jsonl 逐记录核对；git 工作树状态核对。所有命令只读（Python 侧挂写拒绝审计钩子）。

## 2. 六维度逐项结论

### 2.1 容量算术核验 — PASS（全部独立复现，零偏差）

**独立复算过程**（输入：`evidence.final.snapshot.md` 1,806,406 B，sha256 `b4f3573e…` 与设计声称一致；`plan.final.snapshot.md` 230,272 B，sha256 `2937e397…` 一致）：

1. 用 S2 plan 快照重建 canonical 分类上下文：FIX-444 与 FIX-445 均在 hot_tasks 中，状态为 BLOCKED/用户裁定暂停（非 archivable）→ 引用它们的 EVD 行必然分类为 active_task_ref（或整行 keep 标记优先）。
2. 用 `archive.scan_row_families('0.1.0','0.98.0', …)` 重扫 S2 快照，自行聚合：
   - frozen（ref_types ∩ {FIX-444, FIX-445} ≠ ∅）：**223 行 / 522,598 B**（222 active_task_ref + 1 explicit_keep_marker）；
   - missing（reason == missing_task_ref）：**112 行 / 223,822 B**；
   - 按 line_idx 求并集：**335 行 / 746,420 B**，交集为 0（两组严格不相交，522,598+223,822=746,420 加法自洽）；
   - 与 650,000 B 门比较：746,420 > 650,000；严格 <650,000（即 ≤649,999）所需从该保留集合获得的合法迁移量 = 746,420 − 649,999 = **96,421 B**（与设计 §11 D3 一致，且设计正确声明其为必要非充分条件）。
3. 交叉验证全部命中：S2 EVD 849 行/1,631,901 B、REVIEW 192/126,805、TRIAGE 60/20,636、RECO 65/21,641、非行族 5,423；全部 active_task_ref **405 行 / 861,976 B**（本身超门）；.98 EVD-only 候选 120/207,338 → 余 1,599,068；.98 四族 151/218,494 → 1,587,912；.99 EVD-only 274/437,549 → 1,368,857；.99 四族 331/458,277 → 1,348,129（仍超门 698,129）；宽松分段上界 138/258,850 → 1,547,556；basis 外置算术模型 694 行省 584,808 → 1,221,598、组合 963,706；§11 各任务关联 bytes（FEAT-102 150,917 / FEAT-103 45,536 / FEAT-098 98,246 / FEAT-097 104,691 / FIX-443 49,901 / FIX-453 112,232）；S0（1,752,123 B，hash `11634aa3…` 复测一致）与 S1（1,787,003 B，hash `83e6d941…` 一致）表格及差分（+34,880/+19,403 等）逐项复算成立；S1 旧 floor 597 行/1,142,763 B 与 `capacity-floor.json` 一致。
4. 容量门语义核对：`architecture-health.json` evidence per-file override warn=400,000 / error=650,000（工作树现值，未被改动）；`verify_workflow.py` `_archguard_severity` 在 `count >= error` 时返回 ERROR（故 PASS 需严格 <650,000）；`check_governance_data_size` 对宿主热文件取 `path.stat().st_size`；`layer_stats()` 仅填充 `result["layers"]/["family_stats"]`，包裹于 "informational track, never fatal" 的 try/except，不参与门判定——设计 §2.2 的四点声称全部属实。

**裁决**：在暂停边界（DEC-342）与 missing fail-closed 保持的前提下，"仅靠普通归档无法达标、验收 BLOCKED"的结论由文档内 SOURCE 证据支撑且算术独立成立。即使其它所有行全部迁出，746,420 B 的必须保留集仍超门。

### 2.2 标签真实性抽检 — PASS（一处 P3 清单缺口，无事实虚标）

- **SOURCE 抽查**：§4 消费者矩阵 40+ 锚点逐一比对实际源码行，全部命中且语义相符（含 `verify_workflow.py:10044/10066/10153/18551/19505/21181/21741/23945/24624/13608`、`archive_verdicts.py:248/162`、`archive.py:519/693`、`governance_store.py:1021/1042/1157/1198/1222/1256/738`、`review_record.py:600/1015`、`archive_entity_migration.py:426/442~454/598`、`archive_migration_engine.py:1279/1298`、`tests/test_archive.py:6785`（确为 non-EVD 覆盖语义钉住测试）、hooks/pre-commit:32 与 commit-msg 全部 13 个锚点、`quickscan_registry.py:525`、checks/* 各锚点）。FIX-446 独占发布算法的描述（O_EXCL、EVD-only、fsync 先于热表改写、外来/交换/非普通文件拒绝）与 `archive_entity_migration.py:445~454` 注释与代码逐字相符。
- **NOT_RUN 诚实性**：`tests/test_evidence_compaction.py` 确认不存在（"待实现"属实）；未发生实际迁移（live 热表比 S2 更大而非更小；archive 目录自 S2 无变化）；设计文档未提交（git untracked）；门文件零 diff；§10 十二项验证明确全部 NOT_RUN；§12 蓝军挑战明确标注为 Architect 自检而非独立意见。未发现任何把未执行验证写成已完成、把设计写成事实的实例。
- **PROPOSED 分离**：§6/§7/§8/§9 的接口、不变量、恢复契约均以 PROPOSED/NOT_RUN 标注，且 §1 明确 A 段净额仅 207,338 B、"不能宣称完成容量目标"，C1 段历史收益 0 B。
- 发现的缺口见 §4 F-3（取证清单漏列 3 个 post-S2 模拟文件）。

### 2.3 方案完备性 — PASS（条件化闭合到 fixture 级，未验证部分未计作已验证）

- 两段最小方案（A：完成任务完整 EVD 分段归档；C1：新证据独立命令审计载荷）边界清晰、收益如实（207,338 B / 0 B 历史），明确不冒充容量目标达成。
- §8 应用顺序八步 + §8.2 九类中断世界 + §8.3 回滚契约：拒绝复用旧 `_rollback_evidence_archive_impl`（append 回热 + unlink，已核实存在于 `archive_entity_migration.py:598`）；`withdraw_new_segments` 的 no-replace 保全退出为显式 PROPOSED 新能力，平台原语未验证时降级为 plan-only/前向 resume——条件化闭合，未假装已有能力。
- §10 验证矩阵 V1~V12 覆盖分类同源/字节守恒/FIX446 守卫/逐点故障注入/双进程并发/读者等价/身份机录/冻结 hook/撤销重开/资源审计/实际容量/迁移成本，fixture 级断言具体（LF/CRLF/BOM/末行无换行、identity swap、磁盘满、超时等）。设计明确"设计阶段已执行的仅为…未跑下列回归"，未借旧测试存在声称新设计通过。
- §7 模块划分单一职责、依赖图（mermaid）无环，无读写组件反向依赖分类。
- 硬门槛：候选方案 ≥2（A/B1/B2/C1/C2）✓；评估标准预定义（§2.1 ①~⑦ 在候选比较前固定）✓；蓝军挑战 8 条 ≥3 且逐条有缓解/阻断条件 ✓；无循环依赖 ✓；ADR 字段完整（日期/背景/决策/备选+排除理由/影响范围/可逆性/后续动作）✓。

### 2.4 边界协同 — PASS（一处 P3 定义待明确）

- DEC-342 暂停：FIX-444/445 关联 223 行 pin 热表；hooks/engine/registry 零写入；§11 D2 明确 hook/source 读契约触碰须另获裁决，"不能由 FIX-448 设计自授权"。无回退风险路径。
- FIX-446 语义：I5 保持 EVD 独占发布算法；如实披露 resumable 引擎（exists/hash+atomic-write）与非 EVD legacy 覆写（test 6785 钉住）不享同等保护、不在本票暗改。协同正确。
- missing fail-closed：D1 要求逐项找到原任务/原归档/可信原记录才能补齐，否则继续热保留，禁止批量补"已完成"。取证目录中的 missing 模拟文件（见 F-3）本身也以 simulation_only/NOT_RUN 自标，与此纪律一致。
- 待明确点见 §4 F-4："关联"的精确边界（gating ref vs 行内 prose 提及）。

### 2.5 决策面清晰度 — PASS

§11 D1（维持暂停+安全子集，容量持续 BLOCKED）/ D2（另票授权 B2 读契约切换，明示非当前授权范围）/ D3（先业务闭环再重测，附公式 `H_window − eligible + added + manifest < 650000` 与 96,421 B 必要条件、S1 旧值 492,764 已作废声明、FEAT-102 等关注点且"不能与 207,338 B 重复相加"）；§12 五项未决项均为 Coordinator 必答；§13 proposed ADR 字段完整、状态 PROPOSED、DEC 编号待分配、implementation_authorized=false。三选一路径与后果足以支撑裁决。

### 2.6 反作弊核验 — PASS（未发现口子）

- 门未动：工作树 `architecture-health.json` / `verify_workflow.py` 零 diff（400,000/650,000 现值核对）；I6 明确双门不变。
- 不改名：§1 "本设计不把失败的容量目标改名为完成"，状态行自持 "容量验收 BLOCKED"。
- 不删日志/不改机录：I1/I7 + C2 明确拒绝历史改写；`.ops.jsonl`/`governance-store-ops.json` 被明确列为不可删账本。
- 不假终态：§2.2 禁止以"移出若干行"推导健康 PASS、full 健康 42 issues 不改写；V11 要求真实物理 bytes 与命令输出。
- 路径迁移不造成 quickscan 假新鲜：§4 已要求显式登记依赖，当前零 registry 改动。
- 28s 三轨语义（热字节/全库完整性/全量增长分别报告）防止"体积转移冒充成本消除"。
- 本审查复核未发现任何可实现"改名/删日志/改门/抬门/假终态"的遗留通道。

## 3. 审查时点事实（Coordinator 知悉用）

- 审查时 live `.governance/evidence-log.md` = **2,085,539 B**（sha256 `20f76ce5…`），比 S2 终读（1,806,406 B）再增 ~279 KB。这是 S2 之后的合法并发追加（含 FIX-453 闭环与本轮任务链机录），非损坏；设计 §3.1 已声明该增长模型。**含义**：(a) 容量问题较 S2 更严重，BLOCKED 结论 a fortiori 成立；(b) 任何实施前必须按 §8.1 quiesce+revalidate 重取快照，本文与设计中的全部数字均绑定 S2，不得直接用于未来批次。
- 审查时 HEAD = `e28e67c6fb3c3c15fda278d179bf8abc9daae8bd`，与设计 §3.4 声称一致；`source-anchors.json` 逐文件 hash 清单在案。

## 4. Findings（P0-P3 分级）

无 P0 / P1 / P2。以下 P3 共 4 项（保留备注，不阻塞通过）：

- **F-1（P3 · 锚点精度）**：§2.2 引 `core/architecture-health.json:77` 为 evidence override——line 77 实为 `governance_data_size` 节起点，per-file override 实体在 line 89-92（值 warn 400000 / error 650000 正确）；§4 `_write_archive_file_never_overwrite:442` 实为发布段起点，独占创建调用块在 445-454。语义与数值均正确，锚点行号有 2 处小幅漂移。证据：本报告 §7 命令 C-05/C-09 输出。
- **F-2（P3 · 快照作用域提示）**：设计全部"当前/最终"数字绑定 S2（08:31:48Z）；审查时 live 热表已 2,085,539 B。设计自身已声明增长模型且 §8.1 强制锁内复验，此处仅提示 Coordinator：D3 的 96,421 B 必要条件是 S2 作用域数字，未来重测必然变化（大概率变大）。证据：§3 命令 C-02 stat 输出。
- **F-3（P3 · 取证清单不完整）**：§3.4 枚举的 scratch 产物清单遗漏 5 个实际存在项：`audit.ps1`（隔离执行器，正文间接提及）、`isolated-home/`、以及 **post-S2**（08:35:50Z~08:37:31Z，audit 记录 22~26）生成的 `missing-three-refs.txt`、`missing-fix140-proof-simulation.json`、`missing-rel075-proof-simulation.json`。后三个文件自标 `simulation_only_explicit_fact_mapping` / `actual_governance_writes: []` / `verification_limit … NOT_RUN`，且未被设计正文引用为事实——无隐瞒或虚标，但"取证可复查性"一节的枚举应补全，建议 Architect 在后续轮次或 Coordinator 在 EVD 中补记。证据：§7 命令 C-03/C-04/C-12 输出。
- **F-4（P3 · 暂停边界"关联"定义待一句明确）**：设计的 frozen 下限以 gating task ref（分类器 ref_types）定义"FIX-444/445 关联"=223 行。独立复算发现另有 **15 行 / 31,468 B** 在行内（basis 等）prose 提及 FIX-444/445 但 Task 列不引用它们；其中 **4 行 / 12,300 B**（EVD-1687/1693/1694/1696）当前即为 .98 would_archive 候选——即实施 A 段时它们会被迁冷，其含 FIX-444/445 字样的全文对 hot-only 消费者（hooks/M5）不可见。这些行自身 gating 任务已闭环，迁出大概率合法且方向有利（减少热表），不影响 BLOCKED 结论（按 gating 定义 746,420 已超门；按 prose 定义下限更大，更超门）；但设计应显式给出一句规则（"暂停关联 = gating Task ref；prose 提及不冻结行"或相反），以免实施批次与后续审查产生边界争议。证据：§7 命令 C-11 输出。

## 5. 结论

设计文档在事实、算术、标签、方案闭合、边界协同、决策面、反作弊七个方面经受住独立核验：所有可复算数字零偏差复现，40+ 源码锚点命中，未发生任何越权实施或门篡改，容量 BLOCKED 结论真实成立，三选一决策路径可裁决。

**APPROVED_WITH_NOTES**（unresolved_blockers=0）：
- 批准 FIX-448 设计文档作为"阶段性设计交付"进入 Coordinator 裁决（§11 D1/D2/D3 三选一 + §12 五项未决项）。
- F-1~F-4 为 P3 备注：F-1/F-3 建议由 Architect 在获准实施前的文档更新中一并修正/补全（或 Coordinator 机录备注）；F-4 建议在批准实施范围时由 Coordinator 一并给出"关联"定义裁决；F-2 提示实施前必须重取快照。
- 重申：本批准不含实施授权、不解除容量验收 BLOCKED、不恢复 FIX-444/445、不改任何冻结语义。

## 6. 硬门槛自检（Reviewer 角色定义）

| 门槛 | 结果 |
|---|---|
| 只写本报告文件，设计文档/治理文件零修改 | PASS（唯一写面 `docs/reviews/review-FIX-448-DESIGN-R0.md`） |
| 抽查基于实际读取/命令证据，算术给出独立计算过程 | PASS（§2.1/§7） |
| 不实施设计任何部分、不预设 BLOCKED 解除路径 | PASS（全部命令只读，Python 挂写拒绝审计钩子） |
| 候选方案 ≥2 / ADR 字段完整 / 蓝军挑战 ≥3 / 无循环依赖 / Bar Raiser（本审查） | PASS（§2.3/§2.5） |
| 审查结论四态 + unresolved_blockers 结构字段 | APPROVED_WITH_NOTES / unresolved_blockers=0 |

## 7. 审查命令清单（供 Coordinator 机录 EVD；全部只读）

执行环境：Git Bash / python 3.x，工作目录 `D:\AI\agent\claude\coding\project_management_workflow`。时间窗 2026-10-20T09:05Z~09:24Z；逐命令精确 UTC 未单独留痕，以本窗与下表顺序为准（诚实声明：以下"退出码"为工具结果判定，除标注外均 0）。

| # | 命令（摘要） | 结果/退出码 | 路径 |
|---|---|---|---|
| C-01 | 加载 agents/design-reviewer.md、skills/design-review/SKILL.md（Read 工具） | 0 | 工作区 |
| C-02 | `stat -c '%s %n'` + `sha256sum` 于 `.governance/evidence-log.md` | 0；2,085,539 B；sha256 20f76ce5… | .governance/evidence-log.md |
| C-03 | `ls -la` 于 `.codex-sandbox/FIX-448/design-recovery-20261020` 与 `design-r0` | 0；发现 §3.4 未列的 3 个 missing-* 文件 | .codex-sandbox/FIX-448/* |
| C-04 | Read capacity-floor-final.json / measure_current.py / audit.ps1 | 0；223/522598/112/223822/335/746420/96421 | 同上 |
| C-05 | `sha256sum` 四快照 + 解析 metrics-final.json anchors/physical/pinned/segment | 0；S2/S1/S0 hash 全吻合；1,806,406 / EVD 849/1,631,901 / 708/1,365,844 / 138/258,850 | 同上 |
| C-06 | 解析 command-audit.jsonl 27 条记录标签/UTC/exit；提取记录 16（audit_clarification）与 18/20（floor 生成代码） | 0 | 同上 |
| C-07 | `grep/sed` 读 archive.py / archive_verdicts.py / archive_parsing.py（分类上下文、_make_ref_verdict、scan_row_families） | 0 | skills/software-project-governance/infra/ |
| C-08 | **独立复算**（python -B，写拒绝审计钩子）：重建 ctx → scan98/99 → 自聚合 frozen 223/522,598（222+1）、missing 112/223,822、union 335/746,420（交集 0）、necessary 96,421、active 405/861,976、各候选与余量表、regex 交叉 238/554,066 | 0；全部与设计一致 | S2 快照 + infra |
| C-09 | `sed -n` 核对 architecture-health.json（override :89-92 = 400000/650000）与 verify_workflow.py（_archguard_severity :21181 `count>=error`；check_governance_data_size :21741 `path.stat().st_size`；layer_stats informational） | 0 | core/ + infra/verify_workflow.py |
| C-10 | 锚点批量比对 28 处（verify_workflow/archive*/governance_store/review_record/quickscan_registry/write_guard_state/task_row_update/evidence_domain） | 0；全部命中 | infra/ |
| C-11 | 锚点比对 hooks（pre-commit:32；commit-msg 13 处）+ test_archive.py:6785；S0/S1 扫描数字复现（139/236,412+45/16,318→1,499,393；120/207,338→1,579,665；184/252,730→1,534,273）；S0 hash 复核；review/triage 剩余锚点 | 0（注：初次以 `skills/.../hooks/` 路径定位失败 exit≠0，纠正为 `infra/hooks/` 后全部命中——错误输出可见，不影响结论） | infra/hooks/ 等 |
| C-12 | prose-mention 复算：15 行/31,468 B 提及而非 gating；其中 4 行 would_archive（EVD-1687/1693/1694/1696，12,300 B）；S1 capacity-floor.json（597/1,142,763）核对 | 0 | S2 快照 + infra |
| C-13 | `git status --porcelain` + `git diff --stat`（门文件零 diff；设计文档 untracked）+ `git rev-parse HEAD`（=e28e67c6…）+ source-anchors.json 抽样 + plan-header-final.diff 头部（任务 ID→ID 表头变更可见）+ `ls tests/test_evidence_compaction.py`（不存在，证实 NOT_RUN） | 0 | 仓库根 |

*报告完。本文件为 FIX-448 设计审查唯一产出写面；未修改任何产品/治理/取证文件。*
