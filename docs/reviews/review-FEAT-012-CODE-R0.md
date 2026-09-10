# Code Review 报告 — FEAT-012-CODE-R0（Round 0）

| 项 | 值 |
|---|---|
| 任务 | FEAT-012 — G5+G6 批：tpa 同会话重复调用抑制 + summary 两态尾行 |
| 审查对象 | commit `24c6f61c2ac3c9d0b057b66c3eef74435588aaac`（父提交 `8f13c85`，6 文件 +664/−113） |
| 审查类型 | 后置代码审查（Code Reviewer，只读） |
| 轮次 | R0（首轮；无前轮 findings 比对义务） |
| 审查日期 | 2026-09-10（会话日） |
| 方法 | git 只读（show/log/stat）+ 全文读取 6 个变更文件的当前版本与 diff；测试结果采信 Developer 声明并逐条交叉印证（见 §8 采信清单）；未运行任何测试/写操作 |
| 终态 | **APPROVED_WITH_NOTES**（unresolved_blockers=0） |

---

## 1. 目标锚定（scope 对齐）

- plan-tracker L197：FEAT-012 = "G5+G6 批——task-priority-analysis 同会话重复调用抑制 + summary 尾部追查预算提示行"，⏳ 待执行（审查先行流程，状态与本审查时点一致）。
- version-plan-0.79.0.md L136/L137：G5 = "tpa 同会话重复抑制（--no-cache 语义或「已分析，推荐未变」提示）"；G6 = "追查预算提示行……G1 已覆盖主体，剩余收尾面"。实现以「复用缓存 + `--force` 旁路」承载 --no-cache 等价语义、以两态尾行收口 G1 残余追查邀请——**范围内对齐，无范围逃逸**。
- 文件面：task_priority.py（G5 宿主）+ verify_workflow.py（G6 尾行所在 + G5 纯委托）均在任务声明的 tpa/summary 输出域内；plan-tracker 行"task_priority.py 域"措辞未覆盖 verify_workflow 的 G6 改动，但任务描述明含"summary 尾行"，且该渲染只存在于引擎 `_print_check_summary`——判定位内（非偏离）。

## 2. 逐重点裁决（任务书 ①~⑧）

### ① G5 缓存判定正确性 + 首次义务穿透 — 通过（1 项 P2 边界备注）

**实证**（task_priority.py）：
- 复用谓词 `should_reuse_cached_analysis`（L1703-1736）：非 dict / 跨天 / mtime 变化 / report_text 空或非 str 四路独立失效——纯函数，测试 6 断言逐一对应（test_task_priority.py `test_reuse_misses_on_every_invalidation_signal`）。
- 损坏 fail-open：`read_last_run_state`（L1846-1857）`json.loads` 异常（OSError/ValueError）→ None → 全量重跑；非 dict → None。✓
- 跨天：date 精确比较 ISO 串（L1731），午夜滚动后首跑必重跑。✓
- mtime 序列化保真：st_mtime 经 `json.dumps`（repr 往返）写读无精度损失，不会产生假未命中。✓
- 并发写：建议性缓存 last-write-wins，最坏损坏 → 下次 fail-open；无锁可接受（单写者 Coordinator 工作流）。见 F-5（P3）。
- mtime 粒度：粗粒度文件系统（HFS+ 1s / FAT 2s）上同 tick 内编辑可能假复用（L1733 仅等值比较）。NTFS/APFS/ext4（含本仓宿主）ns 级，实际不可触发；缓存当日自愈 + `--force` 旁路。→ **F-1（P2）**：建议 state 增加 size 或 content hash 双保险。

**首次义务穿透**（核实无伤害 FIX-262 的假抑制路径）：
- `needs_live_report = (bool(evidence_task) and not duplicate_reco) or strict`（L1939）→ 首次 `--evidence-task` 必 `state=None` → `reuse=False` → 全量分析 + 落行（L1969）。专测 `test_first_evidence_task_appends_despite_cached_analysis`（先暖缓存再新任务，断言 RECO-FIX-993 恰 1 行 + `[OK]` 输出）。✓
- 反向核查：所有能到达 `write_recommendation_snapshot` 的路径上 `report` 必非 None（reuse 仅在 needs_live_report=False 时发生，而该分支下 evidence_task 要么无、要么 duplicate_reco=True 走不追加分支）——无 None 透传。✓
- strict 与 reuse 互斥（L1939）→ L1981 的 `report is not None` 守卫确为纵深防御而非缺陷。✓

### ② RECO 抑制三条件 — 通过

`has_reco_row_today`（L1739-1781）：行 id 精确等值绑定（L1771 `parts[1] != wanted`）+ 描述格含机器标记（L1774）+ parts[5:] 存在裸 ISO 日期 == today（L1778）。逐面验证：
- legacy 行（无标记）不命中 → fail-open 追加 = FEAT-012 前行为（专测 legacy_row 断言）。✓
- 跨任务不互抑：`RECO-FIX-1` vs `RECO-FIX-12` 等值比较无前缀误伤；task A/B 各自 RECO 独立判定（专测 FIX-991/FIX-992 断言）。✓
- **真实行回测**（本审查实证）：对 evidence-log 中实际机器行 `| RECO-DOC-003 | DOC-003 | …机器写入完成必推荐调用快照（trigger DOC-003…） | … | Coordinator | 2026-09-10 | G11 | N/A |` 逐格走查——parts[1]/parts[4]/parts[8] 三条件全命中，真实 schema 下解析器工作正常。✓
- 描述格含 `|` 的病态行最坏假未命中 → 追加（fail-open），无破坏性。✓

### ③ G6 两态边界 — 通过

verify_workflow.py L16578-16594：`total_details = len(fail)+len(warn)`（L16589-16590）；`0 < total_details <= _summary_detail_cap()`（=5，L16508-16510）→「构成已全量展示（N 项）」，否则原文指引行逐字保留（L16593）。
- =cap（5）：`_ordered_detail_items` 截断至 5（L16544）→ 恰好全展示，声明字面真。专测 ✓
- cap+1（6）/大 N（11）：截断后未全展示 → 指引行逐字节原样（`共 N issues，--level strict 查看全部`），G1 大 N 契约零回归。专测 ✓
- 病理态（count>0 无明细）：`0 <` 下界使声明不可能出现 → 保留指引（"nothing is on screen"），恒字面真约束成立。专测 `test_no_parsed_details_keeps_guidance` ✓
- N 取实际明细行数而非 issues_count——两口径（`_extract_summary_count` 锚 Result 行 vs 逐 [FAIL]/[WARN] 行解析）可能 divergence 时声明仍真。设计正确。✓
- 存量 2 断言更新（test_summary_only.py L203-246 区段）与新语义一致，且反向断言 `assertNotIn("--level strict 查看全部")` 防回潮。✓

### ④ 引擎纯委托核实 — 通过（零逻辑残留）

- `cmd_task_priority_analysis`（L21987-22016 区段）：stdout reconfigure + import + 委托调用 + `sys.exit(code)`——argparse 胶水 only。旧体的 5 个 print、parse/compute/format、RECO 追加、strict 判定全部迁出，引擎内无逻辑残留（diff 逐行核对：−71/+39 中无保留逻辑）。✓
- `--force` argparse 接线（L24081-24088）为纯胶水。✓
- 别名保真：`_recommendation_snapshot_row_text`（L21794）/`_write_recommendation_snapshot`（L21803）薄委托 + 保留 rebinding 感知的 `EVIDENCE_PATH` 默认；`--project-root` 重绑定面（`_apply_project_root_override` L206-228）覆盖 `GOVERNANCE_DIR`/`SAMPLE_PATH`/`EVIDENCE_PATH` 三全局——夹具测试不污染真实 .governance（实证 global 声明 L206-209）。✓
- RISK-040 双根纪律保持：入口仍以 HOST_PROJECT_ROOT 派生路径传参。✓
- 净 −33 行与锚 24,302→24,269 算术闭合；print −5 与 R4 1,315→1,310 算术闭合（移除的 5 print 逐一清点：not-found/parse-error/report/evidence-error/[OK]；G6 尾行 print 为原位替换净 0）。✓

### ⑤ 偏离裁决：baseline regen + 棘轮常量再普查 — 合规（门禁文档化流程内，非越权）

- R1 锚 24,302→24,269：方向=收紧（只降不升）；当前实测 24,269 == 锚（`check_r1` L210-221 为 ≤ 语义，等值通过；负对照 +1 行 FAIL 证明）。regen 与代码收缩**同变更承载**，`check_r1` 自身消息即文档化授权（"shrink the engine or regen after a sanctioned shrink"）。基线 `generated.git_head` = 父提交 `8f13c85`（与 `git log --format='%P'` 实测一致）——commit 前 regen 的既定模式（FEAT-019 R7 幂等剔除 git_head 先例）。**判定：伴随面合规。**
- R4 1,315→1,310 + per_function 删 `cmd_task_priority_analysis: 5` 条目：`count_print_calls` 明确剔除零 print 函数（archguard_ratchet.py L504）→ 函数降为 0 print 后条目消失与基线逐函数相等测试（test L210-213）精确一致；`check_r4` 只罚增长（L512/L524），收缩合法。`FACTS_PRINT_TOTAL` 改动带再普查出处注释（保留原 1,315 出处）。**判定：文档化再普查，合规。**
- 遗留小瑕：测试模块 docstring L9 仍写 "must equal 1,315" → **F-3（P3）**；baseline `design_anchor_note` 未记本次 regen 步 → **F-7（P3）**。

### ⑥ stash 集合级证明 — 采信 + 交叉印证

- 采信：32F 全等（FAILED 7=7 + SUBFAILED 25=25）为本审查未复跑的 Developer 实录（只读约束）。
- 交叉印证（算术）：AUDIT-152（EVD-984，2026-09-10）当日全量定性 31F+1E+1S = 24 环境敏感 + 2 已知缺陷 + 6 数据耦合 = 32 项——与 FEAT-012 报告的 32 项总数闭合（分桶口径不同、总数一致）；且本 commit 爆炸半径受控（tpa 流 + 尾行均有新测试看护），"零新增零消失"与改动面自洽。合理性成立，标 **采信-交叉印证一致**。

### ⑦ AI 专项 5 项 — 全部通过

1. **mock 残留**：12 个新测试零 mock——CLI 层真实 subprocess 调用真实引擎 + TemporaryDirectory 夹具；纯谓词直测。（仓内既有 R5 负对照的 `unittest.mock.patch` 为 FEAT-019 存量，非本 commit。）
2. **硬编码返回值**：谓词均由输入推导；RECO 行文本由 report 字段动态构造（stats/unblock pick/empty reason），无桩值。
3. **幻觉 API**：仅 stdlib（json/sys/re/datetime/pathlib/subprocess/tempfile）；全部调用面在模块内核实存在。
4. **未实现 TODO**：diff 内无 TODO/FIXME/占位。
5. **过度实现**：未发现镀金——迁移由 R1 预算正当驱动，别名保留有消费方（test_completion_recommendation.py L213/226/238），`--force` 为最小旁路。微瑕：`write_last_run_state` 捕获不可达的 ValueError（L1865，write_text/json.dumps 不抛）——无害死分支，不单列发现。

### ⑧ EVD-986/987 直落边界 — 可追认（1 项 P2 内容瑕疵）

- 边界语义（实证 hooks/commit-msg L336-393）：Step 10/11 为**阻断式**机器门禁——产品代码 commit 若 evidence-log 无该 task 的 目标对齐:/用户影响: 行则 exit 1。故 Developer 落 EVD-986/987 是 hook 机器指令的**必需前置**，非禁令面（禁令针对手写 REVIEW 结论行——那是 review-record CLI 独占域，本次未被触碰）。
- 形状核验：两行均在 .governance/evidence-log.md（10 列 schema；目标对齐/用户影响/事实依据齐备；日期 2026-09-10；编号 986/987 与日志最高号 987 连续无冲突；无猜测性措辞）。EVD-987 对新状态文件"建议性缓存、可安全删除"的披露与实现一致。**形状合格 → 追认成立。**
- 内容瑕疵：EVD-986 事实依据引用 "execution-packet FEAT-012"，但 `.governance/execution-packets.json`（generated 2026-09-10T08:35:11，早于 commit）实包列表为 FIX-299/FIX-300/AUDIT-151/FEAT-017/018/019/FIX-301/FEAT-020——**无 FEAT-012 包**（P2 任务按 Check 18c P0/P1 口径豁免，本无需包）。引用不存在工件 = 证据行事实依据失准 → **F-2（P2）**：修正该行（改引 plan-tracker 行 + TRIAGE-FEAT-012 机录，或注明 P2 豁免）。

## 3. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | 通过（F-1 边界备注） | §2①②③④ 全路径走查：缺失 tracker→2 / 损坏缓存 fail-open / 首次穿透 / 重复抑制 / force / strict 互斥 / exit code 契约保持（2/1/0 与旧实现等价）；RECO 解析器对真实行回测通过 |
| 安全性 | 通过 | task_id 正则白名单（L1833，`^[A-Z]+-\d+$` 与旧 `_RECO_TASK_ID_RE` 同源等价）→ 无单元格注入；JSON 解析 fail-closed；无硬编码密钥；路径全部来自 HOST_PROJECT_ROOT 常量链（双根纪律） |
| 可维护性 | 通过（F-3/F-4 备注） | 计算纯度契约更新并如实登记 I/O 例外；单一职责迁移（writer+探测器+编排同宿主）；docstring 完备；两处字面量双份为已声明模式 |
| 性能 | 通过 | 复用路径免重复 parse/compute/format（AUDIT-149 目标达成）；`has_reco_row_today` O(行数) 一次性扫描可接受；缓存写为单文件小 JSON |
| 测试覆盖 | 通过（2 项 P3 缺口备注） | 12 新测试覆盖：谓词命中/×5 失效信号/RECO ×7 面 + CLI 连续两次抑制/force/mtime 失效/重复不追加/首次穿透 + G6 =cap/cap+1/大N/无明细；存量 2 断言同步更新。缺口见 F-9 |

## 4. 发现列表

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | `skills/software-project-governance/infra/task_priority.py:1733`（及 L1921） | 缓存身份仅凭 st_mtime 等值：粗粒度 mtime 文件系统（HFS+ 1s/FAT 2s）上同 tick 编辑 → 假复用展示陈旧报告。当日自愈 + --force 旁路 + 本仓宿主 NTFS ns 级，实际风险低但机制上可加强 | state 增加文件 size（或 content hash）字段，谓词加一路比较；测试补一失效信号 |
| F-2 | **P2** | `.governance/evidence-log.md` EVD-986 行 | 事实依据引用 "execution-packet FEAT-012"——execution-packets.json 无此包（P2 豁免），引用不存在工件，违反证据事实依据红线（行内其余引用可验证） | 修正该行引用（plan-tracker L197 + TRIAGE-FEAT-012 机录），或补注"P2 无包豁免" |
| F-3 | P3 | `skills/software-project-governance/infra/tests/test_archguard_ratchet.py:9` | 模块 docstring 仍写 "must equal 1,315"，与 L45 `FACTS_PRINT_TOTAL=1310` 及再普查注释自相矛盾，误导后续维护者"改回" | docstring 同步为 1,310（保留 1,315 出处语） |
| F-4 | P3 | `task_priority.py:1694` + `verify_workflow.py:21787` | RECO_ROW_MARKER 双字面量（canonical+镜像）——已声明的既定模式，但漂移将使写入面与 Check 34 消费面静默分叉 | 补一行断言两字面量相等（或引擎 import canonical 常量） |
| F-5 | P3 | `task_priority.py:1860-1866` | 并发 tpa：双跑双全量（缓存 last-write-wins）+ 同任务并发 --evidence-task 理论上可双追加（读-判-写竞态）——均为 FEAT-012 前行为，无损坏 | 单写者工作流下可接受；如需收紧可在 append 前二次探测或文档声明单写者前提 |
| F-6 | P3 | `task_priority.py:1931-1939` | 设计注记（非缺陷）：①重复抑制不感知 mtime——当日已有机器行即抑制，tracker 变更后统计不刷新（义务已闭点即快照，可辩护）；②不同任务的首次 --evidence-task 恒触发全量重分析（needs_live_report），AUDIT-149 的多任务连续调用只省 RECO 面不省分析面 | 未来增强：state 序列化 stats 供首次落行复用；在 ADR/注释中固化该取舍 |
| F-7 | P3 | `skills/software-project-governance/core/architecture-baseline.json`（r1_mainfile_budget.design_anchor_note） | note 仍止于 FEAT-019 时点叙事（24,252→24,302），未记 FEAT-012 regen 步（24,302→24,269 / R4 1,315→1,310），出处仅存于 commit message | 下次 regen 时在 note 追加一行本步出处 |
| F-8 | P3 | `.governance/tpa-last-run.json`（当前缺失） | 活体实录声称的缓存文件审查时点不存在（冷缓存；疑被 stash/clean 收走）——非缺陷（建议性、自愈），仅防 Coordinator 误读为"活体未发生"；活体输出本身未独立复现（采信 EVD-986/987 + commit 叙述） | 无需行动；如需留痕可在下次活体后另存输出快照 |
| F-9 | P3 | `tests/test_task_priority.py`（新增 CLI 5 测试） | 覆盖缺口：`--force --evidence-task` 组合（force 重追加路径，argparse help 已承诺）与 strict×reuse 互斥无直测 | 补 2 用例（force 后行数 2；strict 下无复用提示） |

**计数：P0=0，P1=0，P2=2（F-1/F-2），P3=7（F-3~F-9）。** 无阻塞项。

## 5. Developer 声称逐条核验表

| 声称 | 核验 | 方式 |
|---|---|---|
| G5 判定=当日+mtime+report_text，fail-open | ✅ 属实 | 代码走查 L1703-1736/L1846-1857 |
| RECO 三条件/legacy 不误判/跨任务不互抑 | ✅ 属实 | 代码走查 + 真实行回测（RECO-DOC-003）+ 专测 |
| --force 旁路 | ✅ 属实 | L1931/L1940 + argparse L24081 + 专测（组合面缺口见 F-9） |
| 首次闭环义务穿透缓存（专测） | ✅ 属实 | L1939 控制流 + `test_first_evidence_task_appends_despite_cached_analysis` |
| RECO schema 逐字节保真 | ✅ 属实 | 迁移前后函数体逐行比对（含校验正则同源 `^[A-Z]+-\d+$`、错误消息同文）；既有消费方测试（test_completion_recommendation.py L213/226/238）经别名继续覆盖 |
| G6 两态（≤cap 声明/恒字面真/病理态保留） | ✅ 属实 | §2③ 四态走查 + 4 专测 |
| 12 新测试红→绿 | ✅ 结构属实（3+5+4=12）/ 红→绿时序采信 | 测试文件逐个清点 |
| 活体两次第二次抑制 + 缓存报告 51 行 + --force 全量 | ⚠️ 采信（机制经代码+测试证实；输出未独立复现，缓存文件现缺失 F-8） | — |
| stash 32F 全等 | ⚠️ 采信 + 算术交叉印证（与 AUDIT-152 定性 32 项总数闭合） | §2⑥ |
| 健康检查 30 issues 字节级一致 | ⚠️ 采信（逻辑自洽：30>cap → 尾行走原指引分支，字节不变成立） | — |
| 棘轮 R1~R7 全 PASS（首次收紧） | ✅ 机制实证（锚/常量/方向/等值语义/负对照全核）+ 运行结果采信 | §2⑤ |
| EVD-986/987 hook 直落 | ✅ 存在且形状合规可追认；内容 1 处失准（F-2） | §2⑧ |

## 6. 硬门槛自检

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 = 0 | ✅ |
| 5 维度 100% 覆盖 | ✅（§3 逐项） |
| 每条发现标注级别 | ✅（P0~P3 全标） |
| 设计一致性（ADR/契约） | ✅ 纯度契约更新、FIX-262/REQ-108 义务保真、FIX-278 G1 大 N 契约逐字保留、RISK-040 双根、R1/R4 棘轮方向合规 |
| AI 专项 5 项 | ✅（§2⑦ 逐项） |

## 7. 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

G5/G6 实现与声称一致：抑制判定从事实出发（纯函数谓词 + 建议性缓存 fail-open），首次闭环义务穿透路径经控制流与专测双重证实无 FIX-262 假抑制；引擎纯委托零残留，棘轮收紧方向正确且在文档化流程内。2 项 P2（mtime 单因子身份、EVD-986 引用失准）与 7 项 P3 均为非阻塞改进/记录修正，登记遗留即可。允许合并；后续轮次建议优先 F-2（证据行修正，零代码）与 F-9（补 2 测试）。

*本报告为只读审查产物；未修改任何产品代码。测试运行结果均按任务书以采信+交叉印证方式处理，未经本审查独立复跑。*
