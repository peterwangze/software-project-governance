# Review FEAT-057 · CODE · R0 —— write-guard 行族执法上线路由（0.86.0 批 2.3）+ FEAT-056 P2-1/P3 承接

> 审查人: Code Reviewer Agent（独立，只读）· 轮次: R0 · 日期: 2026-09-20
> 审查对象（工作树未提交 9 文件，+1094/−57）: `infra/verify_workflow.py`（write-guard 面 5——24852→25291 行）+ `infra/closure_chain.py`（P2-1/P3①④⑥ 承接）+ `infra/TOOLS.md`（TOOL-057）+ `infra/tests/test_triage_write_guard.py`（+248，7 新测试）+ `infra/tests/test_closure_chain.py`（+97，2 新测试）+ `infra/tests/test_archguard_ratchet.py`（R4 钉 1304→1306）+ `core/architecture-baseline.json`（R1 锚 24852→25291 / R4 1304→1306）+ `infra/contract_matrix/{snapshots.json,golden_samples.txt}`（契约面 + 机械 regen）
> 语义基准: version-plan-0.86.0 §2 批 2.3（「write-guard 行族全覆盖 + 接管范围零手写硬门禁上线路由（WARN 姿态——BLOCK 升级留 0.87）」）+ review-FEAT-056-CODE-R0 P2-1/P3①④⑥ + governance_store/task_row_update 标记契约（凭证判据）+ DEC-168 列契约 / Check 30c V7「counted, not judged」分类先例 + BT-4（JSON 账本邻域留后切片）+ DEC-201⑤ regen 程序

---

## 1. 总结论

## **NEEDS_CHANGE**（P0=0 · P1=1 · P2=1 · P3=6 · **unresolved_blockers=1**）

5 维度逐项有结论（§3）· AI 专项 5 项全过（§5）· 设计一致性 9 焦点 8 符合 1 部分符合（§2 焦点⑤）。独立复验 6/6 通过（§4），真实 `.governance` 全程零写入（state 文件 mtime 保持 Developer 首跑 12:09:45，`git status -- .governance` 干净）。

**阻塞项（P1-1）**：P2-1 修复把 CLI 步超时翻为 `step_unknown`/`awaiting-world-check` 分类学正确、效果已落地腿（探针 reconcile）正确且有测试；但**「效果未落地」恢复腿在标准链下是死路**——STANDARD_TICKET_CLOSURE 三个 CLI 步均未声明 `world_check`，该腿被活体实证为：不带 `--world-check` 恢复 → 永久 halt 且补救建议为字面 `n/a`；按建议带 `--world-check` 恢复 → 空 argv 探针 `ValueError("command_exit probe needs argv")` → `schema_violation` exit 2 崩溃。超时 UNKNOWN 正是批 2.2 混沌发布门的三边界之一，M-2 复演前必须修复（修复面小，三选一见 P1-1 建议）。

---

## 2. 设计一致性（九焦点逐项裁定）

| # | 焦点 | 裁定 | 事实依据 |
|---|------|------|---------|
| ① | 行族对账正确性 | **符合** | 5 面范围与 TOOL-057 声明一致（evidence/decision/plan-tracker 文本面 + `*.ops.jsonl`；`governance-store-ops.json` 显式排除——verify_workflow.py:22734 声明，LEDGER_FILE_NAME 实存 governance_store.py:181）。凭证权威四处逐一核实：`_GOVERNANCE_STORE_MARKER_PREFIX`＝governance_store.py:981/1190 实建标记前缀；`REVIEW_MACHINE_ROW_MARKER`（review_domain.py:2887）经 verify_workflow.py:1256 既有 import 消费（同常量对象，结构性零漂移）；`STATUS_CELL_OP_SUFFIX_PATTERN`（task_row_update.py:192，`〔op-32hex〕$` 端锚）与写入器 :486 拼接形一致（anchor+padding，`trail` 为空白垫片）；receipt 行 `operation_id` 键（task_row_update.py:299/306）。多重集语义正确：`_rows_snapshot` 按 key 聚合 digest 排序列，`_judge_row_delta` pool.remove 消耗单实例——重复行键/重复实例不误报（真实库 evidence 989 实例/960 键全部对账通过）。行解析复用 face 1 既有 `_governance_table_cells`+`_TASK_ID_CELL_RE`（:12298-12307），零第二形状源 |
| ② | 状态基线设计 | **符合** | probe/CLI 路径分离实现正确：`persist_state` 仅 `cmd_governance_write_guard`（:23398）传 True；probe 调用（contract-matrix representative/聚合读/测试）零写入且不消费窗口（`next_state=None`）。确定性：golden fixture A（空宿主）SKIPPED、B（malformed）face 5 独立 PASS——契约矩阵零漂移（snapshots.json face 列表/result 形状已同步 regen，本审查 verify PASSED + 契约测试在全量套件内绿）。损坏→`row_family_state_unreadable` WARN + 首跑重建不静默（测试钉住）；不可写→`row_family_state_unwritable` 披露「下一轮重复披露同一窗口」（代码在案；无测试——P3-4） |
| ③ | WARN 语义忠实度 | **符合（带一处 hook 面披露缺口，P2-1）** | 响亮：独立 issue 逐行披露 + `Result: PASS — 0 FAIL issue(s), N WARN(s)` 行；可指引：detail 携写入器指引（use governance_store/task_row_update/receipt operation_id）+ 0.87 升级声明内联；exit 0 不阻断：CLI 实测三连（WARN 时 face [PASS] 且 exit 0）；BLOCK 留 0.87：docstring/块注释/TOOLS.md/version-plan 批 2.3 行四处一致。缺口：post-commit hook Step 4b 捕获 guard 输出后仅 grep 判定行，PASS 路径 WARN 行被整体丢弃且该次运行消费对账窗口（见 P2-1） |
| ④ | 凭证防漂移 | **符合** | FIX-292 教训闭环真实：`test_marker_authorities_bound_to_real_writer_output` 直接 import `_build_evidence_row`/`_build_decision_row` 实建行断言守卫前缀在场——写入器标记措辞漂移先红；STATUS 锚绑定含「锚后手改后缀不再匹配」负例。REVIEW 判据经共享常量 import，构造性零漂移 |
| ⑤ | P2-1 修复 | **部分符合——P1-1** | 分类学 ✓：超时→`step_unknown`/`execution:"unknown"`/halt `awaiting-world-check`（closure_chain.py:1006-1021），与 external 步 :1067-1069 同型；`_step_world_state` 对两 kind 统一 `step_unknown→unknown`（:1178-1179）；`step_unknown` 在事件枚举闭集内（:194，先例既有）。效果已落地腿 ✓：探针先行 reconcile、不重执行（`started` 计数断言=1，测试实证）。**效果未落地腿 ✗：死路 + 建议补救命令崩溃（P1-1，活体实证见 §4-6）**。测试只覆盖 landed 腿（夹具 world_check=`python -c pass` 恒 satisfied） |
| ⑥ | regen 纪律 | **符合** | R1 锚 24852→25291（= 当前 verify_workflow.py 实际行数，逐字节核实）、R4 1304→1306（+2 = face-5 BASELINE 披露行 + WARN-aware PASS 行，test_archguard_ratchet.py 注释链更新）、`archguard_ratchet.py` exit 0 实测；snapshots.json `generated.git_head=7709987`（FEAT-056 commit）+ timestamp 同步；golden_samples 头部再生时间戳 2026-09-20T04:01:52Z；DEC-201⑤ 同变更再生程序符合（baseline 与钉测试同 commit 更新，注释保留演化链） |
| ⑦ | --json 移除微破坏面 | **符合（边缘③接纳）** | 移除的是 closure_chain 自身 vestigial 恒真旗标（:1656-1661 注释在案）；仓内零调用方受损——grep 全 infra/core/benchmarks/docs：STANDARD 链 flip 步 :519 与探针 :687 的 `--json` 均指向 task_row_update 自有旗标（task_row_update.py:1397 仍在）；benchmarks/closure/cases 命令模板无 --json。负例测试钉住新契约（传 --json → 非零退出 + stderr 含 --json）。argparse unrecognized-argument 报错 fail-visible 非静默 |
| ⑧ | 对账窗口语义 | **符合（披露充分，附 0.87 设计警示）** | 「自上轮以来的行级差分、判后即翻新基线」在 docstring（:23380-23384）/TOOLS.md/WARN 文案（「复跑本命令即基线翻新」）三处如实披露；快照差分固有的「两次 guard 运行之间的中间态不可见」由 ops 台账 append-only receipt 作为写入器侧权威对账承载。CLI 实测三连证实 WARN-once-then-absorb 语义与披露一致。警示：0.87 BLOCK 升级**不得**沿用「一次披露后吸收」语义（否则 BLOCK 只阻一次），须在 0.87 设计期显式处置（见 §7 边缘 4） |
| ⑨ | AI 专项 | **符合** | 见 §5 |

---

## 3. 五维度审查结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ⚠️ | 面 5 引擎逻辑核对无误（amnesty/多重集/快路径/状态收缩/异常路径全闭合，E2E 三连实证）；closure_chain P2-1 修复在未落地腿引入 P1-1 死路 |
| 安全性 | ✅ | 零 shell、零注入面；状态文件为守卫自身工件不触治理记录；凭证校验只读；威胁模型边界与 BT-8 一致（不抗同权限伪造——标记子串可被手写行引用而假阴，属声明边界内，见 §7 边缘 9） |
| 可维护性 | ✅ | 判据消费写入器自有常量（零第二形状源）；块注释 IS/NOT 边界清单完整；TOOLS.md TOOL-057 与实现逐项对得上 |
| 性能 | ✅ | 逐行解析 + SHA 快路径，真实库（989+102+116 行）探针毫秒级；hook 30s 预算充裕 |
| 测试覆盖 | ⚠️ | 新 9 测试覆盖 amnesty/probe 零写/正例/负例五面 WARN/单行改写/状态损坏/凭证绑定/超时分类学/P3 承接；缺口：未落地腿（P1-1 即此缺口）、中部插行、非 UTF-8 面 5 分歧姿态、unwritable 路径（P3-4/5） |

---

## 4. 独立复验（6/6 通过——Reviewer 本机实跑，全程零 .governance 写入）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 45P+32P 定向套件 | `python -m pytest tests/test_triage_write_guard.py tests/test_closure_chain.py -q` | **77 passed in 34.83s**——45+32 逐文件归因成立 |
| 2 | 3811P 全量申报 | `python -m pytest tests -q`（后台 18m23s 实跑） | **3813 passed, 1 skipped, 499 subtests passed, exit 0**（+2 与申报 3811 为计数口径差，零失败） |
| 3 | verify PASSED | `python verify_workflow.py verify` | **PASSED, exit 0** |
| 4 | 真实基线幂等（只读） | state 文件 files-map vs 三面实况逐 digest 比对 + probe 复跑 | **三面 state_match=True（evidence 960 键/989 实例、tracker 115/116、decision 102/102）；probe PASS/0 issues/0 baselined**——申报「960/115/102 行零 WARN + 幂等」独立证实（口径=唯一行键） |
| 5 | WARN 样例隔离夹具 E2E | temp `.governance` + `--project-root` 重定向，CLI 三连 | **首跑 [BASELINE]+exit 0；手改行→1 WARN 响亮+「use governance_store」指引+face [PASS]+exit 0；三跑窗口消费后静默 PASS**——申报「exit 0 不阻断+可指引文案」逐项复现 |
| 6 | P2-1 恢复腿活体证明 | temp root + 超时 CLI 步（无 world_check 声明）spec 三连 | **run1 超时→exit 2 awaiting-world-check ✓；run2 裸恢复→halt，补救建议 argv=「n/a」；run3 按建议 `--world-check`→`{"error":true,"code":"schema_violation","detail":"…command_exit probe needs argv"}` exit 2**——P1-1 实锤 |

**标注为 claimed（未独立复验）**：「标记漂移测试先红」TDD 历史顺序（持久机制=绑定测试本身，已随 45P 实跑绿灯；先红过程不可事后重现）。

---

## 5. AI 代码专项（5 项全过）

| 项 | 结论 | 证据 |
|----|------|------|
| mock 残留 | ✅ 零 | 生产 diff 零 mock；测试仅 `mock.patch.object(vw, GOVERNANCE_DIR/SAMPLE_PATH)` 做夹具隔离（声明式用途，非行为伪装） |
| 硬编码返回值 | ✅ 零 | 断言全部对着真实文件内容/退出码/JSON payload；E2E 夹具走真实子进程 |
| 幻觉 API | ✅ 零 | 逐符号核实：STATUS_CELL_OP_SUFFIX_PATTERN（task_row_update.py:192）/REVIEW_MACHINE_ROW_MARKER（review_domain.py:2887，经 :1256 既有 import）/_build_evidence_row/_build_decision_row（governance_store.py:981/1190）/RECEIPT operation_id（:299）/resolve_template 空元组行为（:642-649） |
| 未实现 TODO | ✅ 零 | diff 新增行零 TODO/FIXME/XXX/HACK |
| 过度实现 | ✅ 无 | 面 5 范围=批 2.3 声明；BLOCK 姿态未提前实现；ops 面仅 receipt 对账无越界解析 |

---

## 6. Findings

### P0（阻塞）——无

### P1（关键——本轮修复）

- **P1-1 CLI 步超时 UNKNOWN 的「效果未落地」恢复腿死路 + 建议补救命令崩溃** · `closure_chain.py:1326-1354`（unknown 分支）× STANDARD_TICKET_CLOSURE:504-574（三 CLI 步均无 `world_check` 声明）
  事实（§4-6 活体实证）：CLI 步超时→`step_unknown` 后，probe 未命中时——(a) 裸 resume 永久 halt 于 `awaiting-world-check`，note 建议 remedial 命令 argv 为字面 `n/a`；(b) 按建议带 `--world-check` resume → `wc_probe.argv=[]`（parse_chain_spec :484 把缺省压成空元组，resolve_template(:621) 空进空出）→ `_run_probe` :805-808 `raise ValueError("command_exit probe needs argv")` → main :1714-1716 捕获为 `schema_violation` exit 2。链内无任何路径可重执行该步（写器 replay 安全性使重执行本可行——修复前旧行为即直接重执行）。
  影响：无数据损坏（journal 干净、写器 replay 安全、新 closure 可绕行重启）；但 (1) 生产标准链唯一超时崩溃窗的链内恢复通道断裂；(2) 输出自带的补救建议必然崩溃且被误标 `schema_violation`（世界态问题≠校验错误，误导操作者与按码分支的自动化）；(3) 旧 closure 永久滞留 awaiting-world-check 成审计死巷；(4) 与 P2-1 修复 docstring「resume reconciles via the step's own read-only probe …」的承诺只在 landed 腿成立。
  修复建议（三选一，(c) 最小）：(a) STANDARD_TICKET_CLOSURE 三 CLI 步声明 world_check（如 flip 步用 task_row_update `--inspect` 只读命令）；(b) spec 校验期强制：`kind=cli` 步必须声明 world_check 或显式豁免；(c) unknown 分支对 `kind=cli` 且 world_check 为空时，视步探针为世界核验——probe 未命中即放行重执行（写器 replay 协议兜底，与修复前语义等价）。修复后补 not-landed 腿测试（world_check 未命中→重执行恰一次 / 无 world_check→不崩溃）。

### P2（建议，可遗留，不阻塞）

- **P2-1 hook 路径 WARN 输出被丢弃且对账窗口在 hook 处被消费——主自动化面上 WARN 实际不可见** · `infra/hooks/post-commit:260-272` × `verify_workflow.py:23398`（persist_state=True）
  事实：post-commit Step 4b 以 CLI 姿态跑 guard（`persist_state=True`）→ 捕获输出后 PASS 路径仅 grep `^Result: PASS`，WARN 行不回显、窗口已翻新。直写→commit 的现实工作流中，未手动复跑 guard 的手改行其 WARN 在 hook 处生成即消失，且无任何持久 WARN 台账。TOOLS.md 有披露（「hook 面板对 WARN 数零呈现差异」）故非隐瞒；但披露未覆盖「窗口同时被消费」的组合效应。
  建议：hook ✅ 行附 WARN 计数（`(N WARNs — rerun governance-write-guard for detail)`）且/或 hook 以 probe 姿态（不消费窗口）跑 face 5，把窗口消费权留给人工复跑。**0.87 BLOCK 升级前必须补齐该披露链**（BLOCK 走 exit 1 FAIL box 不受此影响）。

### P3（讨论/建议）

1. **ops 台账中部插行语义无钉住测试** · 行号键控下插行导致后续行键位移，receipt 行凭 `operation_id` 仍命中不误报、裸插行恰 WARN（分析成立）；建议补一条中部插行测试防回归。
2. **face 5 非 UTF-8 面 WARN+skip 的分歧姿态无测试** · faces 1-4 fail-closed（FIX-333）与 face 5 WARN+skip 的契约分歧（docstring :23104-23108 已声明）建议各补一负例。
3. **凭证子串匹配可被引用性假阴** · 手写行若引用/复制真实标记串则免于 WARN——与 BT-8「不抗同权限伪造」声明一致，属边界内；建议 0.87 BLOCK 设计期改判据为「标记 + op-id 在 ops 台账可 join」（governance_store 凭证侧车 18 键 join 锚已具备）。
4. **`row_family_state_unwritable` 路径无测试** · Windows 下 chmod 模拟不可靠可谅解；建议以 monkeypatch write_text 抛 OSError 补一条。
5. **ratchet 锚钉 `assertIn("25", …)` 弱钉** · 沿用既有 "24" 弱钉模式，建议随 0.87 收紧为区间/精确值断言。
6. **申报行数口径** · 「960/115/102 行」实为唯一行键数；多重集实例数为 989/116/102（evidence 含 29 个重复键实例）。守卫行为正确，建议后续申报标注口径（keys vs instances）。

---

## 7. Developer 申报边缘 · 10 项裁定建议

| # | 边缘申报 | 裁定建议 |
|---|---------|---------|
| 1 | TRIAGE/RECO 行不标记判定 | **接纳**。写入器先于标记纪律，DEC-168 列数契约已覆盖形状；与 Check 30c V7「counted, not judged」分类先例同构（review_domain.py:3133 实证） |
| 2 | 行删除不追溯（归档迁移合法机器面） | **接纳**。snapshot 基线吸收消失键，判据只审在场行实例；与 FIX-162~171 归档引擎链语义一致 |
| 3 | `--json` 移除微破坏 | **接纳**（§2 焦点⑦）。仓内零调用方、负例测试钉住、fail-visible |
| 4 | 对账窗口「变更后至少跑一次 guard」 | **有条件接纳**。快照差分语义三处如实披露 + ops receipt 为写入器侧权威；**0.87 约束：BLOCK 升级不得沿用 WARN-once-then-absorb**（须 WARN/BLOCK 台账化或窗口保持到人工确认） |
| 5 | ops 台账行号键控（中部插行） | **接纳**（语义分析成立：位移行凭证仍命中；裸插行恰 WARN）；P3-1 钉住测试随行 |
| 6 | `governance-store-ops.json` JSON 文档账本留后切片 | **接纳**。非行可 diff 实证（LEDGER_FILE_NAME 为单 JSON 文档）；BT-4 邻域声明在案，后切片处置正确 |
| 7 | 状态基线 = 守卫自身工件（CHECK-ONLY 修订） | **接纳**。唯一落盘工件、仅 CLI 路径、probe/tests/聚合读零写入（test_probe_mode_never_persists_state 钉住）；docstring 已从「writes NOTHING」修订为「CHECK-ONLY for governance records」——措辞诚实 |
| 8 | hook 面板 WARN 零呈现 | **部分不接纳**（→P2-1）。披露在案但组合效应（输出丢弃+窗口消费）超出披露面；0.87 前须补 |
| 9 | amnesty 首跑红线（存量手写行零 WARN） | **接纳并实证**。真实基线 12:09:45 建立后 probe 零 issues；528 REVIEW 行中 289 历史手写行零打扰；标记子串假阴属 BT-8 声明边界（P3-3 留 0.87） |
| 10 | 凭证判据绑定写入器实建行（先红申报） | **接纳机制、先红标注 claimed**。绑定测试为持久防漂移机制（FIX-292 教训闭环成立）；TDD 先红过程不可事后重现，如实标注 |

---

## 8. 复审指引（R1 必读）

R1 必须逐条比对：**P1-1**（未落地腿——验证修复方案落地后 `--world-check` 与裸恢复两路径均可达终态且 not-landed 腿有测试）为唯一阻塞项；**P2-1**（hook WARN 计数/窗口消费权）可与 0.87 预备面合并处置或本轮顺带。P3-1~6 可遗留登记。复审时不得未读本报告直接 APPROVED；本报告基于工作树未提交状态，R1 须以修复后 diff 复核 §2 焦点⑤与 §4-6 复现路径是否闭合。

---
*审查依据: skills/code-review/SKILL.md + agents/code-reviewer.md · 事实依据红线遵守：每条结论可回溯至文件行号/命令输出/测试结果 · Reviewer 零代码修改、零 .governance 写入（state 文件 mtime 全程保持 2026-09-20 12:09:45，`git status -- .governance` 干净）*
