# Code Review 报告 — FEAT-013-CODE-R0（后置审查）

- **审查对象**: commit `3a108c2a74080f683a0dc454b67a42a06b58d821`（HEAD；8 文件 +789/−12）
- **任务**: FEAT-013 — RISK-046 根因修复：派发锁写入前路径存在性校验 + change-triage files 交叉核对
- **Reviewer**: Code Reviewer Agent（角色文件 `agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载）
- **Round**: R0（首轮；无前轮复审链）
- **模式**: 后置审查（commit 已落库，HEAD 即审查对象）；只读——git 只读 + 文件读取；测试结果按任务规范**采信 + 静态交叉印证**，未独立运行
- **日期**: 2026-09-10（会话内）；证据基线 = 工作树 @ 3a108c2

---

## 1. 审查范围与交叉印证事实

| # | 声称 | 印证结果 |
|---|------|---------|
| 1 | 8 文件 +789/−12 | ✅ `git show --stat` 精确一致 |
| 2 | change_triage.py +307（acquire_dispatch_locks + agent_locks_acquire_cli） | ✅ diff +332（含 docstring/`__all__`），两个新函数 + `cross_check_triage_files` 纯函数（change_triage.py:695-944） |
| 3 | verify_workflow.py +60 薄入口（免 print 免冷导入） | ✅ `cmd_agent_locks_acquire` 6 行胶水（verify_workflow.py:22584 附近）+ argparse 8 参数（:24202 附近）+ commands-dict 1 行；函数体内延迟 `from change_triage import agent_locks_acquire_cli`；零 print（print 全在 change_triage 层） |
| 4 | 18 测试用例 | ✅ `def test_` 计数 70→88（父 commit vs 本 commit），+18 精确吻合；分布 = CrossCheck 3 + Acquire 9 + Check26Sync 4 + CLI 2 |
| 5 | Check 26 可选 expected_new:bool 向后兼容 | ✅ verify_workflow.py:17496 附近仅类型校验（存在且非 bool → schema_violation；缺省 PASS）；legacy/true/非 bool 三态 + write-guard face3 消费均有测试锁定 |
| 6 | 棘轮 R5 81→82 键 | ✅ 三处同步一致：snapshots.json（handler 78→79 / key 81→82 / 新键 `agent-locks-acquire`）+ test_archguard_ratchet.py:241 + test_contract_matrix.py:42 |
| 7 | R1 24,269→24,329 regen；R4/R6 Δ0 | ✅ baseline diff 仅 2 行（git_head + anchor_loc）；r4/r6 区不变；+60 与引擎净增一致 |
| 8 | EVD-988/989 落账 | ✅ `.governance/evidence-log.md:1899/1901` 存在且内容详实（.governance/ 整体 gitignored——FIX-141 模式，本地落账即完整落账） |
| 9 | triage 声明面 | ✅ change-triage/FEAT-013.json files = 4 产品文件，与 agent-locks.json FEAT-013 锁完全一致 |
| 10 | 全量 2,326 passed / 32F 零新增 / 健康 30 恒等 / R1~R7 PASS / 16 红→18 绿 | ⚠️ **采信 + 静态交叉印证**：TDD 红 phase 未入库（单 commit 无法独立复核红状态）；绿 phase 18/18 与文件事实吻合，棘轮三处计数闭合。结论按采信口径接受，标注不可独立复核部分 |

## 2. 八个审查重点逐一裁决

### ① 「当日」口径语义充分性 — 裁决：设计选择成立，但跨日静默缺披露（→ F-1/P2-4）

`cross_check_triage_files`（change_triage.py:733）`created_at != today → return None`：跨日 triage（Day1 triage、Day2 取锁）完全跳过核对且**零提示**——summary.cross_check=None，CLI 无任何输出，用户无法区分「无记录」「他任务记录」「跨日记录」三态。该行为有显式测试锚定（`test_missing_or_other_day_record_returns_none`），是 documented design choice 而非疏忽。但**活体首次使用即落入跨日分支**：FEAT-013 自己的锁（created 2026-09-10 20:50）对照其 triage 记录（created_at 2026-09-08）= 跨日静默跳过。RISK-046 ② 的 drift 检测在跨日场景 100% 失效且不可见。当日核对本身正确（归一化 slash/大小写、双向差异、task_id 精确匹配）。

### ② expected_new 持久化语义 — 裁决：语义自洽（审计痕迹，无状态漂移）

Check 26（verify_workflow.py:17496 附近）对 expected_new 仅校验类型、不赋予「文件当前不存在」语义 → 锁条目保留 `expected_new: true` 在文件创建后 = 纯「获得时通道」审计痕迹，机器层面无漂移。测试锁定三态 + guard 消费。读锁者语义约定（「获得时经豁免通道」而非「文件尚不存在」）建议在 Check 26 消费面文档化（P3-2 顺带）。

### ③ 豁免滥用面 — 裁决：滥用通道存在且披露有缺口（→ F-1/P2-4）

`--expected-new typo-path` 完全绕过存在性校验（self-declaration 本质）。WARN 仅在「当日 triage 记录存在且集合有差异」时触发；**无当日记录时 expected_new 豁免零披露**（cross=None → warnings=[]）。当日内 WARN 确实会把 typo 路径列为 lock_only 披露（测试锁定）。缺口与①同根：披露依赖当日记录存在。

### ④ acquire API 正确性 — 裁决：校验/合并/损坏路径正确；竞态如实评估 = 存在但低危（→ F-2/P2-2）

校验顺序与 docstring 声明一致（形状→子集→TTL→损坏锁→去重→跨任务冲突→面1→面2→写）；六类失败全部零写入（测试逐一断言 `locks_path` 不存在/未变）。合并保全他人条目（测试锁定）。**竞态事实**：read_text→内存合并→write_text（change_triage.py:927）为读后写模式，无进程间锁、无 temp+rename 原子写——两个并发 acquire 丢失更新（后写覆盖前写者的锁条目）；write_text 中途崩溃可留半写文件（下次 fail-closed 拒绝合并——方向可接受）。现实触发条件 = 两个并发 CLI 进程；当前治理模型单 Coordinator 串行派发，风险低，但 docstring 未声明单写者假设。

### ⑤ 薄入口纯度 + R1 上锚 regen 裁决 — 纯度通过；R1 上升 sanctioned 但披露强度低于 FEAT-019 先例（→ F-3/P2-1）

纯度：✅ 6 行胶水 + 延迟导入（免冷导入，R6 不受影响）+ 零 print（R4 不受影响；baseline r4/r6 区 diff 为零佐证）。

R1 裁决：regen 路径本身合规——FEAT-019 packet mandates 实测为准 at regen time（archguard_ratchet.py:735-740 note 明载），R7 双生一致性保证 committed==fresh regen，「只降不升」是 R1 检查语义（check_r1: current>anchor→violation）而非 regen 语义；+60 全部为任务授权的 CLI 接线（argparse+cmd+dict+Check 26 扩展），与 FEAT-019 dispatch wiring 同性质，**不是**绕过棘轮。缺口在披露：FEAT-019 先例 = regen 上升 + `DEFAULT_EXEMPTIONS` allowance=0 的 DEC-tracked RECORD 条目（archguard_ratchet.py:742-756，dec=DEC-183/184，expire 0.81.0）；本次 +60 **未添加**对应 RECORD 条目，`R1_DESIGN_ANCHOR_NOTE` 常量未更新（仍只描述 FEAT-019 时期 18 行 wiring 的归属），且 commit message 复读「the wiring lines are registered as the R1 self-bootstrap exemption」——该句描述的是 FEAT-019 的 18 行，非本次 +60，措辞与仓库事实有偏差。审计强度不足（对照先例），非路径错误。

### ⑥ 模板机器化正确性 — 裁决：通过

agent-dispatch-template.md 第 4 步命令的参数名（--task/--files/--role/--session/--ttl-reason/--expected-new）与 argparse 定义逐一对齐；--ttl 缺省 14400 与 DEFAULT_LOCK_TTL_SECONDS 一致；exit 2 语义、expected_new 声明义务、禁手写措辞齐全。仓库根相对路径执行成立。

### ⑦ AI 专项 5 项 — 裁决：全过

| 项 | 结论 |
|---|------|
| mock 残留 | 无——patch.object(vw,"GOVERNANCE_DIR") 均在 with 块内自动还原；生产代码零 mock |
| 硬编码返回值 | 无——_LOCK_NOW 为测试时钟注入参数（惯例）；无硬编码结果 |
| 幻觉 API | 无——sys.stdout.reconfigure / Path / json / datetime 均为真实标准库 API |
| 未实现 TODO | 无——diff 内零 TODO/FIXME/占位 pass |
| 过度实现 | 无——+60 接线均为必要面；cross_check 独立纯函数系可测性拆分而非过度设计 |

### ⑧ 测试真实性 + 存量归属采信 — 裁决：接受

18 用例真实存在、断言具体（exit code / stdout JSON / stderr WARN / 文件系统副作用逐项断言）、CLI 测试真实 subprocess 调用 verify_workflow.py（非 mock CLI）。红 phase 不可独立复核（单 commit），按采信口径接受 EVD-988 TDD 叙述。存量（32F 基线、健康 30、全量 2,326 passed、R1~R7 PASS）采信；静态交叉印证无矛盾（三处 82 键闭合、baseline 仅 2 行变更、EVD-988 内含 stash 对照归因叙述）。REL-074 active_tasks 空目标条目为 09-08 存量，非本次引入，归属存量。

## 3. 五维度结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ✅ 通过（带 P2） | 校验顺序/失败零写入/合并保全全对；边界（空 files/形状/TTL/损坏锁）覆盖；绝对路径旁路与竞态见 F-2/F-4 |
| 安全性 | ✅ 通过（带 P2） | 无敏感数据、无注入面（纯 JSON 读写、无 shell）；路径形状校验缺口见 F-4 |
| 可维护性 | ✅ 通过 | docstring 详尽（六步校验顺序成文）、纯度契约声明同步更新、命名达意、`__all__` 导出齐 |
| 性能 | ✅ 通过 | 每次 acquire 全量 load_triage_records——当前记录量级（~20）无影响 |
| 测试覆盖 | ✅ 通过 | 核心路径/边界/错误路径 18 用例；缺口与 F-2/F-4 对应（并发与路径形状无用例——修补时补） |

## 4. 发现列表

### P2（建议修改——可作为遗留项，不阻塞合并）

**F-1 / P2 — face 2 跨日静默 + expected_new 豁免在无当日记录时零披露**（焦点①③）
- 位置：`skills/software-project-governance/infra/change_triage.py:733`（跨日 return None）、`:895`（WARN 仅在 cross 非 None 时）、`:880`（expected_new 豁免无独立披露）
- 事实：跨日 triage → cross_check=None → 零输出；无当日记录时 --expected-new 声明的不存在路径入锁无任何提示。活体首用（FEAT-013 自身锁 vs 2026-09-08 triage）即跨日静默。
- 影响：RISK-046 ② drift 检测在跨日场景失效且不可见；豁免通道滥用（typo 声明为 expected_new）在无当日记录时不可见。
- 建议：非当日记录存在或 expected_new 非空且 cross 为 None 时，输出一条 informational 行（stderr 或 summary.warnings）披露「跳过核对/豁免声明」事实；保持不阻断语义不变。

**F-2 / P2 — 读后写竞态 + 非原子写，未声明单写者假设**（焦点④如实评估）
- 位置：`skills/software-project-governance/infra/change_triage.py:927`（write_text 直写）
- 事实：read→merge→write 无进程间互斥、无 temp+rename；并发 acquire 丢失更新；中途崩溃留半写文件（下次 fail-closed，方向可接受）。
- 影响：当前单 Coordinator 串行模型下低危；API 文档未声明单写者假设，未来并发调用即触发。
- 建议：短期在 docstring 声明单写者契约 + 模板注明「串行调用」；长期改 temp 文件 + `os.replace` 原子写（Windows 兼容）。

**F-3 / P2 — R1 上锚 +60 的审计披露低于 FEAT-019 先例**（焦点⑤裁决）
- 位置：`skills/software-project-governance/core/architecture-baseline.json`（anchor_loc 24269→24329，design_anchor_note 未变）、`infra/archguard_ratchet.py:735-756`（note 常量与 DEFAULT_EXEMPTIONS 均未随本次上升更新/增补）
- 事实：regen 路径 sanctioned（实测为准）且 R7 闭环，但本次 +60 无 allowance=0 的 DEC-tracked RECORD 条目、note 归属文本仍停在 FEAT-019 语境；commit message「wiring lines are registered as the R1 self-bootstrap exemption」与豁免登记事实不符（登记的只有 FEAT-019 的 18 行）。
- 影响：sanctioned 增长的可追溯性弱于先例——读者无法从 baseline/exemptions 得知 24,269→24,329 的归属任务。
- 建议：补一条 allowance=0 RECORD 条目（reason 注明 FEAT-013 agent-locks-acquire wiring 60 行，dec 引用，expire 0.81.0）或更新 note 常量；属审计补账，无需代码返工。

**F-4 / P2 — 绝对路径与 `..` 相对路径未被拒绝，repo_root 拼接可被旁路**（安全性/输入校验）
- 位置：`skills/software-project-governance/infra/change_triage.py:695`（_normalize_lock_path 仅做斜杠归一）、`:880`（`repo_root / f`）
- 事实：Windows 上 `Path(repo_root) / "D:/abs/path"` 丢弃 repo_root 直接判绝对路径——仓库外已存在文件可通过存在性校验入锁；锁 key 与相对路径声明的同文件锁不匹配 → 跨任务冲突检测被削弱（RISK-046 目标场景的变体）；`../` 前缀同理可越界。posix 上不旁路（fail-closed 拒绝），win32（本仓运行环境）旁路成立。
- 影响：高频误用形态（从资源管理器贴绝对路径）静默通过；损害 = 锁错位 + 冲突检测面绕过，非数据损坏。
- 建议：`_normalize_lock_path` 后拒绝绝对路径（`Path(f).is_absolute()` 或盘符正则）与 `..` 段；补 2 个用例。若 Coordinator 出现实际绝对路径取锁事例，升级 P1。

### P3（讨论/观察——不要求修改）

**P3-1** `change_triage.py:927` + `agent_locks_acquire_cli`：post-write guard 失败 exit 2 但**不回滚**已写入的锁文件；docstring「NOTHING is written on any error」未覆盖 CLI 层 guard 场景（措辞边界）。建议 guard 失败时恢复原文件内容或措辞限定范围。
**P3-2** `change_triage.py:910`：active_tasks 条目同时写 `target_files` 与 `files` 双同值字段——若为 Check 26 历史兼容所需，建议注释说明；顺带在消费面文档化 expected_new「获得时通道」语义（见②裁决）。
**P3-3** `change_triage.py:964` 附近（_split）：逗号与分号双分隔宽容——含逗号/分号的文件名会被错误切分（repo 相对路径罕见）；建议文档注明或收敛为仅逗号。
**P3-4** 观察（治理操作时间线，非本 commit 缺陷）：真实 `.governance/agent-locks.json` FEAT-013 锁 locked_at=`2026-09-10T20:50:00` 与本 commit 内测试固定时钟 `_LOCK_NOW` 秒级相同，且晚于 commit 时间 19:47:27——该锁疑为 commit 后用新 CLI 获取（活体狗粮，正常），但时间戳秒级同值无法自然解释，无独立证据定论，交 Coordinator 判断是否存在时间对齐复写。
**P3-5** `change_triage.py:753` acquire_dispatch_locks 函数 ~170 行（含 60 行 docstring），超 50 行建议——分段与 docstring 结构清晰，可读性尚可，接受。
**P3-6** triage/锁声明面（4 产品文件）未涵盖 4 个棘轮伴随 regen 文件（baseline/snapshots/两个测试计数）——伴随 regen 系文档化流程（FEAT-019 先例）且 R7 闭环验证，接受；建议后续统一「伴随面是否入 triage files」口径，避免 drift 语义悬空（本任务自身的 face 2 对伴随面即静默跳过）。

## 5. 硬门槛核对

| 门槛 | 结果 |
|------|------|
| P0 阻塞数 | **0** |
| P1 关键数 | **0**（P2×4 + P3×6） |
| 5 维度覆盖 | 100%（§3 逐项有结论） |
| 每条发现标注级别 | 100%（F-1~F-4/P2；P3-1~6） |
| 设计一致性 | 已完成——与 ADR-017 §4.4 纯度契约一致（I/O 集中声明已同步扩展至新函数）；与 RISK-046 根因对位；与 FEAT-011 write-guard 共享 Check 26 schema（消费经测试验证而非假设）；与 M7.6a 锁纪律（去重/冲突/释放先行）一致 |
| AI 专项 5 项 | 全部完成（§2⑦逐项有结论） |

## 6. 审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**理由**：RISK-046 两面根因修复真实落地——面 1 写前存在性校验六路 fail-closed 零写入（逐路有测试与断言）、expected_new 豁免通道持久化且 Check 26 向后兼容（legacy PASS 测试锁定）、面 2 当日核对归一化正确且 WARN 不阻断语义与 triage-先于-锁的流程自洽；薄入口纯度达标（免 print 免冷导入，R4/R6 零变化有 baseline diff 佐证）；模板机器化参数逐一对齐可执行；18 用例真实且断言到文件系统副作用；EVD-988/989 本地落账在案。无 P0/P1。4 条 P2（跨日/豁免披露缺口、竞态、R1 审计补账、路径形状校验）均为防护面增强与审计完整性建议，不影响正确交付的核心行为，作为遗留项登记由 Coordinator 排期（自然载体：0.79.0 收尾链后续小修或 FX 批次）。R1 上升经裁决为 sanctioned regen（实测为准 + R7 闭环），仅披露待补账（F-3）。

**遗留项**：F-1/F-2/F-4 建议随 0.79.0 收尾批修补（同一 API 面小改 + 补用例）；F-3 为审计补账（exemption RECORD 或 note 更新），可随下一棘轮触碰时点执行。P3-4 时间线观察请 Coordinator 核实后在证据面留痕。

---

*审查方法依据：`agents/code-reviewer.md`（只读、不修改产品代码、不与用户交互）+ `skills/code-review/SKILL.md`（5 维度、P0-P3、事实依据红线——本报告每条结论均指向可复查事实：diff 行号 / 文件内容 / git 输出；测试运行结果按任务规范采信并已标注不可独立复核边界）。*
