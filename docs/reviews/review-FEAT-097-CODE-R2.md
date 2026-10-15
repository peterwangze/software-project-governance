# FEAT-097 Code Review R2 — F1~F6 测试返工 delta 复审

- **轮次**: R2（delta 复审）
- **前轮引用**: `docs/reviews/review-FEAT-097-CODE-R1.md`（R1 结论 NEEDS_CHANGE：P1×1 新引入 + P2×5）；机器记录 `.governance/review-FEAT-097-R0.md`（next_round 链经 R1 review-record txn-f3aa29bcf17341ecb8cbd35fc51b98f6 延续至 R2）
- **审查方**: Code Reviewer Agent（与 R1 同一实例——审查连续性经报告链传递；只读审查；唯一写面 = 本报告；未修改产品/测试代码、未触碰 `.governance/`、未 commit）
- **delta 范围**: 仅 `skills/software-project-governance/infra/tests/test_goal_bridge.py`（mtime 2026-10-11 09:39:48 local，446→722 行）；`goal_bridge.py` mtime 2026-10-10 23:56 local——早于 R1 复审读取时刻，R1 全文读取仍权威，**生产代码零新增改动，不重审**
- **结论**: **APPROVED_WITH_NOTES**

```json
{"unresolved_blockers": 0}
```

---

## 0. 结论与理由

R1 全部六项 findings（P1-R1 + P2-R1-A~E，对应修复清单 F1~F6）**逐条已修复**，零未修复、零新引入。独立实跑：**33/33 模块测 OK（4.635s，exit 0）+ 5/5 接线测 OK（0.076s，exit 0）+ 并发类连跑 3 次全 OK（3.380/3.362/3.396s，exit 0，时长稳定无 flake 迹象）**——全部在隔离环境下执行（TEMP/TMP/HOME/USERPROFILE/DSH_HOME 显式重定向至专用临时目录，§6 逐命令时间戳）。

新用例为**真断言非镜像实现**：并发回归以真子进程持锁+工件字节不变断言咬合；racing-refuse 用例在锁移除时会以错误错误码（SCOPE_RULING_REQUIRED≠BLOCKED）失败——回归有真实杀伤力。既有 26 用例无删除无弱化（26→33 精确对账：F6×2 + F4×1 + F3×2 + 并发×2；唯一既有测试修改 = F1 指定的一行 authorized_by）。遗留项全部为 P3 级非阻塞备注（§5），无未解决阻塞项——故 APPROVED_WITH_NOTES，`unresolved_blockers=0` 为独立结构字段。

**措辞边界**：本结论指模块协议/CLI 级门（goal-bridge 桥接面）的测试看护达成；不宣称宿主级拦截执法，不宣称 0.98 发布完成。

---

## 1. R1 findings（F1~F6）逐条判定

| # | R1 finding | 判定 | 证据（一手） |
|---|-----------|------|------|
| **F1 / P1-R1** | 守护套件 RED（`test_resume_with_different_rules_version_is_loud` 与 P2-1 修复矛盾） | **已修复** | `test_goal_bridge.py:322-324` 补 `authorized_by="user"`（R1 §8-F1 指定的一行修法）；原断言全保留（无错误/rules_version_changed/mixed==1，:325-331）；33/33 实跑复现 |
| **F2 / P2-R1-A** | P1-1 修复缺并发回归用例 | **已修复** | 新增 `ConcurrentSerializationTests`（:508-642）两条：① `test_cross_process_lock_contention_refused_retryable`（:529-581）——真子进程持 `_TargetLock`（ready/release 旗标握手协议，非 sleep 竞猜），三入口 timeout=1.0 全拒 `lock_contention`+`retryable`（:566-570），**拒后工件字节不变**（:573 `read_bytes()==before`——「拒即零写入」强断言），释放后 record 恢复 RUNNING 无楔死（:579-581），holder 经 `with` 正常释放 returncode=0；② `test_racing_refuse_cannot_erase_user_abort_ruling`（:583-642）——R0 P1-1 丢失更新形态的确定性重放：gated `_save` 使 abort 裁决停在save窗口（Event 握手），rogue record 在窗口期发起→锁排队→加载**裁决后**状态→按 BLOCKED 面拒绝（:633 `assertRefused(rogue, CODE_BLOCKED)`）+裁决与 rogue 审计行双双存活（:637-642）。**咬合性核验**：若锁被移除，rogue 将加载窗口期盘上 CHECKPOINTED 态→返回错误错误码→测试即红——真回归网，非镜像 |
| **F3 / P2-R1-B** | P2-1 修复缺对称红测 | **已修复** | `test_checkpointed_unauthorized_resume_refused_and_audited`（:398-421）：continue/extend-budget/reduce-scope 三方向各用**独立 fresh goal**（subTest 内重建，:406-411——避开 subTest 不重建夹具的坑）→ 全拒 `unauthorized_resume` + 恰 1 条 kind=resume 审计行（decision/state 字段逐一断言）+ 状态不动；`test_checkpointed_abort_without_authorization_is_safe_direction`（:423-433）：无授权 abort 放行落 BLOCKED 且 scope_ruling 记录在案——豁免方向与 R1 F3 规格逐字吻合 |
| **F4 / P2-R1-C** | P2-2 修复缺跨版本 record 用例 | **已修复** | `test_record_path_discloses_rules_version_change`（:333-365）：mock `_default_rules_version`（R1 §8-F4 指定手法）→ record 不阻断（allowed）+ re-pin 至新版本（:349）+ 恰 1 条 `rules_version_changed` 披露行（trigger/note 断言，:351-355）+ 状态不扰（:356）+ **同版本二次 record 零新增行**（:359-365，披露幂等） |
| **F5 / P2-R1-D** | P2-3 修复缺真键非 null 断言 | **已修复** | `test_schema_carries_all_five_faces`（:254-299）升级：真实 `LedgerWriter` 播种（:261-267，`record_task` 返回 status=registered 先行断言）后**无条件**断言：`available is True`、`events_lines` int≥1、`last_seq` int≥1、`integrity_ok is True`（:277-284）+ **幻觉键缺席断言** `assertNotIn("events_total")`（:286）——R1 §8-F5 规格全项。`LedgerWriter`/`record_task` 经实读确认为真实 API（authority_ledger.py:520/:788，返回面 :851）——测试侧无幻觉调用 |
| **F6 / P2-R1-E**（=R0 P2-4） | 边界等号与多维交叉用例缺 | **已修复** | `test_rounds_at_exact_danger_boundary_collects`（:143-153）：rounds=42 → share==0.7 精确断言 + zone=danger + any_danger + 推荐 DRAINING（`share >= danger_ratio` 等号位收口）；`test_two_dimensions_danger_simultaneously`（:155-171）：rounds+tokens 双危险 → judge 面 `danger==["rounds","tokens"]` **且 record 面 `danger_dimensions` 同对**（:166-171，超越 R1 规格的额外咬合） |

**R1 遗留 P3 项**：P3-R1-1（票面验收命令不含模块套件）→ F7 归 Coordinator 落实（两条验收命令+EVD），非 Developer 产品修改，本轮保持开放归 Coordinator；P3-R1-2（pwsh mojibake）→ 流程注记，本轮以 `[Console]::OutputEncoding=UTF8` 前置缓解（§6 命令可查）。

---

## 2. delta 质量分析（咬合性 / flake / 弱化检查）

- **非镜像实现**：全部断言针对可观测行为（返回码/disposition/工件字节/状态/history/审计行），无内部调用计数断言（gated `_save` 是交错仪器本身，正当）；F2② 在锁移除时以错误错误码失败（§1 F2 行）——回归网有真实杀伤力。
- **时序确定性**：跨进程用例用旗标文件握手（ready/release + 15s/20s/25s/30s 宽裕 deadline），非 sleep 竞猜；进程内用例用 `threading.Event` 握手（10s 等待）+ 首个 `_save` 调用即裁决窗口（调用序确定：裁决线程先启、rogue 在 window_open 后才启动）。**3 次连跑时长 3.380/3.362/3.396s 稳定**——无 flake 迹象。
- **既有用例对账（26→33）**：BudgetDangerZone 5→7（+F6×2）、StateMapping 6→6、CheckpointArtifact 4→5（+F4）、ResumeAuthorization 7→9（+F3×2，新增 `_drive_to_checkpointed` 助手）、ConcurrentSerialization 0→2（+F2）、Rollback/Perf 4→4、CliFace 1→1。**无删除、无断言弱化**；唯一既有修改 = F1 的 :323 一行（R1 指定）。
- **微噪（不构成 finding）**：`from datetime import datetime`（:46）沿袭 R1 期未使用导入——非本轮 delta 引入、两轮前已存在，不值得为此返工。

---

## 3. 五维度结论（硬门槛 ②；delta 面）

| 维度 | 结论 | 依据 |
|------|------|------|
| **正确性** | **PASS** | F1~F6 断言与生产语义逐一咬合（§1/§2）；33+5 实跑绿；并发×3 稳定 |
| **安全性** | **PASS** | F3 三方向对称授权红测+abort 豁免方向留档；F2 保护用户裁决+审计不被抹除（RPG 威胁模型回归网闭合） |
| **可维护性** | **PASS** | holder 脚本为类常量、注释逐一锚定 review ID（P2-4/P2-R1-E 等）可追溯；测试类职责分区清晰 |
| **性能** | **PASS** | 套件 4.635s（并发对 ~3.4s 为握手协议成本，回归价值正当）；judge ≤10ms 守护用例原样保留 |
| **测试覆盖** | **PASS** | R1 六项缺口全闭；覆盖面=竞态/争用/对称授权/版本披露幂等/真键/边界等号/多维交叉 |

---

## 4. AI 代码专项 5 项（硬门槛 ⑤；delta 面）

| 项 | 结论 | 依据 |
|----|------|------|
| mock 残留 | **无** | `mock.patch(_default_rules_version)` 为 R1 §8-F4 指定的正当仪器；`mock_env` 沿袭既有；生产模块零 mock |
| 硬编码返回值 | **无** | 42/48/1_600_000 等为边界语义常量（注释锚定 0.70×60 推导） |
| 幻觉 API 调用 | **无** | `LedgerWriter`/`record_task`（authority_ledger.py:520/:788/:851）与 `_TargetLock`（governance_store.py:511）均实读确认为真实 API |
| 未实现 TODO | **无** | 全文读零命中 |
| 过度实现 | **无** | delta 恰为 F1~F6 指定面，无越面功能 |

---

## 5. 保留的非阻塞备注（R0/R1 承接）

| 备注 | 来源 | 状态 |
|------|------|------|
| unauthorized_attempts 语义混装（DRAINING/BLOCKED 分桶） | R0 P3-2 | 遗留（非阻塞） |
| `_parse_new_limits` 静默跳过畸形项 | R0 P3-3 | 遗留（非阻塞） |
| `_transition` LookupError 无结构化捕获（守卫式分发下不可达） | R0 P3-4 | 遗留（非阻塞） |
| write_checkpoint 对 BLOCKED 返回 scope_ruling_options 呈现错位 | R0 P3-5 | 遗留（非阻塞） |
| 申报 Δ2 tok 口径 / skill 档 report-only | R0 P3-6 | 遗留（非阻塞） |
| 票面验收命令不含模块套件 | R1 P3-R1-1 | **归 Coordinator**（F7：两条验收命令+EVD 落实，非 Developer 面） |
| pwsh 捕获管道 mojibake | R1 P3-R1-2 | 流程注记（本轮 UTF8 前置缓解） |

---

## 6. 验证命令与输出（隔离环境，逐命令 UTC 时间戳）

**隔离声明（每条命令同构前置）**：`[Console]::OutputEncoding=UTF8`；`TEMP/TMP/HOME/USERPROFILE/DSH_HOME` 显式重定向至 `C:\Users\peter\AppData\Local\Temp\feat097-r2-isolated\{tmp,home,home,dsh}`（专用临时目录，三选一之 (a) 隔离环境）；未赋值 PS 自动变量 `$HOME`；真实 HOME/DSH_HOME/仓库 `.governance` 零写入（unittest 夹具 TemporaryDirectory 落于重定向后 TEMP；仓库内仅 `__pycache__` 字节码缓存这一标准副产物）。

| # | 命令 | start (UTC) | end (UTC) | exit | 结果 |
|---|------|-------------|-----------|------|------|
| 1 | `git status --porcelain` + 目标文件 mtime/Length 查询 | unknown（单戳） | 2026-10-11T01:42:46.68Z | 0 | 12M+4??；goal_bridge.py mtime 10-10 23:56 local / test_goal_bridge.py 10-11 09:39:48 local——delta 范围确认 |
| 2 | `python -m unittest …/test_goal_bridge.py -v`（隔离） | 2026-10-11T01:43:49.25Z | 2026-10-11T01:43:54.26Z | 0 | **Ran 33 tests in 4.635s — OK** |
| 3 | `python -m unittest …/test_verify_workflow.py -k Feat097GoalBridgeWiring -v`（隔离） | 2026-10-11T01:44:07.95Z | 2026-10-11T01:44:08.42Z | 0 | **Ran 5 tests in 0.076s — OK** |
| 4 | 同命令 #2 加 `-k ConcurrentSerialization`，连跑 3 次（隔离） | run1 01:44:08.92Z→01:44:12.56Z；run2 01:44:12.56Z→01:44:16.11Z；run3 01:44:16.11Z→01:44:19.67Z | — | 0×3 | **Ran 2 tests — OK ×3**（3.380/3.362/3.396s） |

只读面（无时间戳要求）：两 MUST 文件重载（内容与会话期一致）；`goal_bridge.py` R1 全文读取权威沿用（mtime 先于 R1）；`test_goal_bridge.py` 722 行全文读；grep `LedgerWriter/record_task`（authority_ledger.py:520/:788/:851 实证）。**未重跑**：全量 1115 引擎套件/健康检查（Coordinator engine 后台运行中，按派发约束避免重载；R0 已独立验证全量面，本轮 delta 不触及该面）。

---

## 7. 硬门槛自检（输出前）

| 门槛 | 判定 |
|------|------|
| P0 阻塞问题数 = 0 | ✓（本轮零新 finding；R1 六项全闭） |
| 5 维度 100% 覆盖 | ✓（§3） |
| 每条发现 P0~P3 + 位置 + 事实 + 建议 | ✓（§1 判定表 + §5 备注均带锚点；本轮无新增 finding） |
| R1 findings 逐条 已修复/未修复/新引入 | ✓（§1 六行全「已修复」+ P3 归属更新） |
| round 号 + 前轮引用 | ✓（报告头 R2 + R1 报告路径） |
| 既有用例无删除/弱化 + 独立实跑通过 | ✓（§2 对账 26→33；§6 #2~#4 独立绿） |
| APPROVED_WITH_NOTES 独立结构字段 | ✓（§0 代码块 `{"unresolved_blockers": 0}`——无 BLOCKING finding、字段唯一无矛盾） |
| 事实依据红线 | ✓（每判定指向测试行号/命令输出/UTC 时间戳；未重跑面与沿用面如实标注） |
| 措辞边界 | ✓（协议/CLI 级门表述；无宿主级执法/0.98 发布宣称） |

---

## 8. 给 Coordinator 的机录与后续

- **review-record**：`--task FEAT-097 --round 2 --result APPROVED_WITH_NOTES --report docs/reviews/review-FEAT-097-CODE-R2.md --reviewer 'Code Reviewer' --scope delta --delta-base docs/reviews/review-FEAT-097-CODE-R1.md`（APPROVED_WITH_NOTES 为通过终态——复审链可闭合；RECHECK-R2 结清）。
- **F7（Coordinator 面）**：票面验收命令补 `…/test_goal_bridge.py` + EVD 行以本轮 §6 #2/#3 命令输出为准（UTC 时间戳已附）。
- **锁释放**：R2 报告锁（session-a1ac9399…）随结论回收释放。
- **非阻塞备注**：§5 七项留跟踪面，不阻塞本票收口；建议随票 close 时在 plan-tracker 备注或拆微票（Coordinator 决策）。
