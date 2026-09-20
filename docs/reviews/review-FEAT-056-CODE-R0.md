# Review FEAT-056 · CODE · R0 —— closure-chain 纵切 + 混沌发布门（0.86.0 批 2 核心）

> 审查人: Code Reviewer Agent（独立，只读）· 轮次: R0 · 日期: 2026-09-20
> 审查对象（工作树未提交）: `skills/software-project-governance/infra/closure_chain.py`（1715 行）+ `infra/tests/test_closure_chain.py`（1176 行 / 30 测试）+ `benchmarks/closure/cases/{standard-success,conflict,recovery}.json` + `.gitignore`（+1 条规则 `benchmarks/closure/runs/`，含 2 行注释与 1 空行——与申报"一行[规则]"一致）
> 语义基准: arch round2 §2（前向恢复/恢复规则表/自指陷阱/双轨粒度/人工-编排器互斥）+ round3（M3 纵切 / BT-9 kill 语义）+ version-plan §2/§5.5 + evolution §2/§4 DoD + contracts.py（m0-r1 冻结面）+ 既有三写入器（task_row_update / governance_store evidence+locks / loop_event_log 机器）

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（P0=0 · P1=0 · P2=1 · P3=8 · **unresolved_blockers=0**）

硬门槛全过：5 维度逐项有结论（§3）· AI 专项 5 项全过（§5）· 设计一致性 9 个审查焦点逐项核对（§2）。按 code-review skill 关闭规则（P0=0 且 P1=0 → 可合并），P2×1 为建议级遗留项，不阻塞合并。独立复验 3/3 通过（§4）。

---

## 2. 设计一致性（九焦点逐项裁定）

| # | 焦点 | 裁定 | 事实依据 |
|---|------|------|---------|
| ① | 纯序排器边界（链引擎零业务逻辑） | **符合** | imports 仅 stdlib+contracts+loop_event_log（closure_chain.py:103-124），零 plan-tracker/evidence 解析；步骤=argv 声明（STANDARD_TICKET_CLOSURE:491-574）；summary 为唯一引擎计算步（声明内）；BT-7 kill-switch 等价性由 KillSwitchTests 实证——声明 argv 逐步直跑达到同终态 + 依赖方向扫描（engine 不 import verify_workflow；writers 不 import closure_chain） |
| ② | 事件日志分域 | **符合** | 持久化机器真复用：`loop_event_log.build_event/append_event/read_events/check_cas_monotonicity` 原样调用（:313-347）——append/read 不带 PARO 枚举校验（loop_event_log.py:231-296/404-446），closure 类型可安全过机；分域文件 `.governance/closure-events.jsonl`（:157）；closure 自有 8 类型枚举 + `_validate_closure_event` 镜像校验（:181-305）——属 round-2「类型/schema 版本/closure_id/顺序号 分域」授权面，非持久化第二实现（镜像漂移风险见 P3-8） |
| ③ | effect-based resume | **符合** | 6 型只读探针闭集（:170-177）；探针先于一切执行（:1262-1266）；reconciled 复用原锚不重执行（:1274-1288）；UNKNOWN 世界核验门控 `--world-check` 默认关、建议非自动（:1289-1299，round2 §2「先查远端再决定」忠实）；resume 输入绑定 digest 不可变（:1211-1216） |
| ④ | 自指约束 | **符合**（一处清单缺口 P3-1） | git 不在链内；`--finalize` 只读核验 commit 后记账且记录必然晚于其描述的 commit（:1477-1530）；`do_not_stage` 报告 closure-events.jsonl + closure-locks/（:1103-1106）；漏 `.lock` 伴生文件见 P3-1 |
| ⑤ | operation_id 确定性派生 | **符合** | `op-` + sha256(closure_id\|step_id)[:32]（:229-247），形状过 `contracts.require_operation_id`（测试#8 断言）；跨 resume 稳定 → 写入器 replay 兜底链路真实闭合：task_row_update ledger（:888）+ evidence-append ledger/marker 双保险（governance_store.py:1119-1143）+ locks `_locks_execute` 世界判定（:1481-1518）均被独立核实存在 |
| ⑥ | 混沌测试质量（BT-9） | **符合** | 命名故障点 `post-step-effect:<step_id>` 协议边界（效果后、记账前）；父控制器 Popen.kill 跨平台；硬终止（4 测试）与抛异常等价（结构化退出码 2 测试）分测试类；kill≠掉电声明入模块 docstring 且有测试锚（#30）；注入接口仅 `CLOSURE_CHAIN_TEST_FAULT_POINTS` 环境变量，`--help` 零旗标断言（#28）独立复验通过 |
| ⑦ | locks-release 缺口处置 | **符合** | TTL 收缩承载 = locks-amend 绝对置位 owner 全部锁（governance_store.py:1742-1752）；探针 lock_ttl_le 按 `locked_by==task` 全量核验（:721-755）；零锁世界探针 satisfied 短路避免 writer cross_record_violation 误停；缺口三处披露（docstring:93-98 / case JSON gap_disclosure / summary commit message）——登记不静默 ✓ |
| ⑧ | dry-run 复演 | **符合** | 零写路径结构成立（无 journal append、无锁、probes 只读、writer dry-run/help）；真表独立复演见 §4-3 |
| ⑨ | AI 专项 | **符合** | 见 §5 |

**恢复规则表忠实度**：round2 §2 四行规则逐行有着落——evidence 已写续跑（边界① 双向夹具：evidence-first 链 + 标准链顺序镜像）；commit 核验不重复提交（rev-list 计数不变断言）；凭据失效→blocked+诊断等修复；结果不明→先核远端（建议非自动）。「不许人工协议与编排器同时推进同一 closure」由 per-closure `_RunLock` 硬拒绝承载（有界获取、无 best-effort 回退——:830-897，较 loop_event_log 的 best-effort 先例更严，方向正确）。

## 3. 五维度审查结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ✅ | seq 链算术核对无误（started 消耗 seq、终态事件 +1 链续）；resume 三态机（completed/failed/unknown/started 崩溃窗）与世界探针组合闭合重复执行窗口；探针先行使 CLI 崩溃窗安全收敛 |
| 安全性 | ✅ | argv-list 全程无 shell；external 步禁 governed 占位符（:404-411）；未知占位符 fail-closed；sha/step_id/placeholder 正则边界检查；凭据零记录（链不触 push）；无 add -A、无 force-push 面 |
| 可维护性 | ✅ | 模块自述 IS/NOT 清单精确；闭集枚举 + fail-closed 惯用法与 contracts 一致；findings 中 2 处命名瑕疵（P3-6） |
| 性能 | ✅ | 无 O(n²) 热点；探针 subprocess 有界超时；journal 读取 fail-safe |
| 测试覆盖 | ✅ | 30 测试覆盖 spec 校验×8 / E2E+finalize+resume 拒绝×3 / 幂等续跑+torn 行×2 / dry-run 零写×1 / CJK+重复执行+信封负控×3 / 混沌三边界×6 / 并发×1 / kill-switch×2 / 注入面×3；夹具为真实子进程+真实 git 仓库+本地 bare 远端（零真实远端） |

## 4. 独立复验（3/3 通过——Reviewer 本机实跑）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 30 套件实跑 | `python -m pytest skills/software-project-governance/infra/tests/test_closure_chain.py -v` | **30 passed in 32.83s**（Python 3.14.3 / win32）——Developer 申报 30/30 独立复现 |
| 2 | 混沌边界①复演（含②③腿） | 同上套件内 Boundary1 两腿（握手标记→Popen.kill→零修复 resume→锚点复用/单次追加）、Boundary2（commit 计数不变）、Boundary3（凭据 blocked→修复→先核远端补推一次；超时 UNKNOWN→建议非自动→world-check 收敛零重推） | **全部 PASSED**；隔离 bare 夹具零真实远端属实 |
| 3 | dry-run 真表零写入复演 | 真库 `.governance` 2031 文件 SHA256 快照 → `closure_chain.py run --task FEAT-056 --dry-run`（真实输入）→ 快照比对 + journal/locks 存在性 + `git check-ignore` | **2031 文件前后零差异；closure-events.jsonl 与 closure-locks/ 未创建；.gitignore 规则实测命中 `benchmarks/closure/runs/`**；dry-run 诚实输出 resolved_refusal（真实行状态 `dev`，状态级 CAS 拒绝、零写入）与 zero_locks 短路、parse-level 披露——与夹具内断言同型，真表复现 Developer「2031 文件一致+journal 未创建」 |

**未独立复验（Developer 申报，标注为 claimed）**：infra 全量 3804P 零回归、verify_workflow PASSED、archguard 冻结面 95/95（Reviewer 快检 `archguard_ratchet.py` exit 0 无违规输出，弱佐证）。此三项建议 Coordinator 在 Check 30 / 批 2.0 复跑面按既有机制机验。

## 5. AI 代码专项（5 项全过）

| 项 | 结论 | 证据 |
|----|------|------|
| mock 残留 | ✅ 零 | 测试全真实子进程/真实写入器；grep mock/patch 仅命中 "dispatch lock" 子串误报 |
| 硬编码返回值 | ✅ 零 | 断言全部对着真实文件内容/事件流/退出码 |
| 幻觉 API | ✅ 零 | 逐一面核：`--inspect`(task_row_update:1389,1441)/`--dry-run`(1365,1878)/`--operation-id`(1368,1840,1863)/locks-amend ttl 全锁置位(1742-1752)/contracts 五符号均在 __all__ |
| 未实现 TODO | ✅ 零 | closure_chain.py 零 TODO/FIXME；locks-release 缺口为登记披露非沉默欠账 |
| 过度实现 | ✅ 无 | external 步 kind 生产链为零实例（声明+夹具限用）；engine 接线显式排除在切片外（docstring :63-65） |

## 6. Findings

### P0（阻塞）——无

### P1（关键）——无

### P2（建议，可遗留，不阻塞）

- **P2-1 CLI 步超时的事件分类学偏离 round-2 UNKNOWN 纪律** · `closure_chain.py:983-992`（对照 external 步 `:1033-1047`）
  事实：CLI 步 subprocess 超时被记录为 `step_failed`（code=manual_intervention, disposition=manual），而 external 步同型超时记录为 `step_unknown`（execution=unknown）。subprocess.run 超时即杀子进程——对 governed writer 这同样是「效果可能已落地」的硬终止崩溃窗，属 round-2 持久化清单「外部动作结果不明标 UNKNOWN」的覆盖对象；BT-9「硬终止 vs 抛异常分开」在事件分类学上未对齐。
  影响：**正确性无险**——resume 探针先行 + 写入器 replay 兜底使恢复路径与 unknown 完全同构安全；但 blocked+manual 处置把「本可由世界探针自动收敛的崩溃窗」报告为需人工，且 journal 审计分类失真。
  建议：CLI 超时 → `step_unknown`（或至少事件载荷携 `execution: "unknown"` 并在 detail 声明崩溃类），状态机走 `awaiting-world-check`/探针收敛。可遗留下一轮（批 2.0 集成面或 R1 顺带）。

### P3（讨论/建议）

1. **do_not_stage 漏列 journal 锁伴生文件** · `closure_chain.py:1103-1106`：`loop_event_log._cross_process_lock` 必然产生 `.governance/closure-events.jsonl.lock`（loop_event_log.py:310），真实运行后存在；do_not_stage 仅列 jsonl 与 closure-locks/。整目录 staging 时伴生文件可入 commit。建议补列。
2. **evidence 步指纹含当日日期 → 跨午夜 resume 的 conflict 面** · 指纹覆盖 `date_str=now.date()`（governance_store.py:1064-1065,1073-1079）+ 链侧确定性 op-id：若 append 首跑与 resume 跨午夜且探针未命中（如目标暂不可读），同 id 新指纹 → `operation_id_conflict` fail-closed（不致错，但把可 replay 收敛降级为 blocked）。建议后续：date 纳入链输入绑定，或契约变更流程下将 date 排除出指纹。
3. **dry-run parse-level `--help` 腿对未知旗标不设防** · `closure_chain.py:1417-1439`：argparse help action 先于 unrecognized-arguments 报错退出 0——旗标拼错时 parse_level 仍 resolvable。当前三项 argv 旗标已逐一核实存在（task_row_update:1368/1392、governance_store:1840/1865、locks-amend:1840），无现实缺陷；建议 parse-level 腿追加一遍无 `--help` 的静默解析。
4. **并发不同 closure 同 task 无护栏**：per-closure 锁不防双 closure 并行推进同一任务（双 evidence 行可能）。evolution §6② 已登记 0.87 开放问题——建议模块 docstring 补一句「单 closure 单飞假设」声明，防误用。
5. **未知写入器错误码 → disposition=manual 静默映射** · `closure_chain.py:966`：`.get(code, "manual")` fail-safe 方向可接受，但建议 detail 保留 unknown code 原文供对账。
6. **两处命名瑕疵** · `--json` 恒真 vestigial 旗标（:1620）；`events_appended` 实为 journal 事件总数非本次追加数（:1364）。
7. **`_maybe_fault` 在步失败（returncode≠0）时仍于 post-step-effect 触发**（:993）——"effect 已落"语义失真；仅测试入口，无生产影响。
8. **closure 信封校验为 §5.1 管道的域内镜像**（:275-305 vs loop_event_log.validate_event:465-499）——持久化机器零第二实现成立，但镜像与母本需人工同步；建议后续抽 shared non-enum 校验 helper（required-fields+int sanity），§5.1 演化时防双源漂移。

## 7. Developer 申报边缘 · 7 项裁定建议

| # | 边缘申报 | 裁定建议 |
|---|---------|---------|
| 1 | locks-release 缺口 → locks-amend TTL 收缩承载 | **接纳**。Governed 效果承载真实（全锁绝对置位+探针核验），三处披露+登记缺口候选在案；符合「缺口登记不静默」。真删除留后续切片正确 |
| 2 | locks-amend 无 --dry-run → parse-level help 披露 | **接纳**。逐层披露（dry-run note + 测试断言 mode）；P3-3 加固建议随行 |
| 3 | external 步 kind 生产链零实例（夹具限用） | **接纳**。闭集内声明 + governed 占位符禁入（:404-411）使该 kind 无法成为治理写入旁路；commit/push 留链外与 round-2 权限语义一致 |
| 4 | kill ≠ 掉电/存储故障（不推导断电持久性） | **接纳**。docstring + round3 原文 + 测试#30 三重锚定；报告/发布措辞照此限定 |
| 5 | UNKNOWN 世界核验建议非自动（--world-check 显式） | **接纳**。round2 §2「先查远端再决定」忠实落地且默认不联网查询；与「外部 URL 不自动抓取」同族纪律一致 |
| 6 | 引擎未接线 engine dispatch（standalone CLI） | **接纳**。镜像 writers pre-FEAT-055 姿态；冻结面未触（archguard 面 95/95 为 Developer 申报）；接线留后切片是正确收缩 |
| 7 | 量测目标 ≤2 留 M-2 实测（case JSON 不下结论） | **接纳**。三 JSON 显式声明「协议工件≠第二事实源」（防双主漂移）+「M-2 实测判定，非本文件结论」——符合 version-plan §3「不得测后改门槛」纪律；conflict.json 引用的写入器红相（test_state_cas_conflict_reports_observed_revision）经核实真实存在 |

## 8. 复审指引（若 Coordinator 走 R1）

R1 必须逐条比对：P2-1（CLI 超时分类学——查 `_execute_cli_step` 超时分支事件类型）＋ P3-1（do_not_stage 补列）为最可能修复项；P3-2/3 可与批 2.0 集成面合并处置；P3-4~8 可遗留给 0.87 面并入登记。复审时不得未读本报告直接 APPROVED。

---
*审查依据: skills/code-review/SKILL.md + agents/code-reviewer.md · 事实依据红线遵守：每条结论均可回溯至文件行号/命令输出/测试结果 · Reviewer 零代码修改、零 .governance 写入*
