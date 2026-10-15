# FEAT-097 Code Review R0 — goal 与预算桥接（状态映射+四维权危险区+checkpoint 工件+续跑授权）

- **轮次**: R0（初审）
- **审查方**: Code Reviewer Agent（只读审查；唯一写面 = 本报告；未修改产品代码、未触碰 `.governance/`、未 commit）
- **审查对象**: 工作区未 commit 变更 14 文件（HEAD `bf6942d`；`git status --porcelain` = 12 M + 2 ??；`git diff --stat` = 254 insertions / 23 deletions）——与任务申报 **一致**（14/14 对上；另有 1 个未申报残留 `_tmp_suite097.log`，见 P3-1）
- **任务契约**: `.governance/execution-packets.json` packets.'FEAT-097'（实读全键：allowed_change_scope / non_goals×3 / quality_budget 六维 / scope_guard / rollback_plan）
- **结论**: **NEEDS_CHANGE**（P0=0；P1×1 本轮必须修复——核心资产上的丢失更新竞态；P2×4 / P3×6）

---

## 0. 结论与理由

**NEEDS_CHANGE ｜ P0=0 ｜ P1×1（本轮必须修复） ｜ P2×4 ｜ P3×6**

桥接的核心语义全部成立并经独立复现：状态机为纯数据表（7 边与申报逐一吻合）、四维权危险区任一触发收口（四维独立故障注入全绿）、warning 单独不触发、checkpoint 五面 schema 齐备且幂等（revision 稳定+单历史行）、blocked 后 3 种故障注入全拒全留痕、CHECKPOINTED 无裁决执行拒、回退开关零状态写、阈值/映射 grep 面、模板三 profile 注入预算 PASS（strict **6197≤6200 实测精确复现，headroom 恰 3 tok**）、全套件 **Ran 1115 tests OK 独立复现**（375.9s，与基线 1110+5 精确吻合）、28n 零新增（goal_bridge 916 行零告警面）、伴生面 regen 干净（anchor +40 恰为本票接线增量、R6 207→208、快照零漂移 rider——优于 FEAT-096 期形态）。

**但 P1-1 是本票核心资产（用户裁决+审计痕迹）上的未同步读-改-写竞态**：record/checkpoint/ruling 三面 load→mutate→save 无任何锁（本仓 FEAT-096 R1 刚刚以 P1-1→修复确立了治理工件写者必须持 `_TargetLock` 的协议先例，本票未跟进）。我以确定性内存探针（零落盘）实证了最坏交错：**用户的 abort 裁决落盘后（BLOCKED+scope_ruling+3 行历史），一个基于旧快照的 racing refuse 审计写回把状态复活为 CHECKPOINTED、scope_ruling=None、历史掉回 2 行——裁决与审计双双被抹**。这正是「禁静默续跑/意图断层修复」要消灭的事故形态的镜像（用户说了终止，系统忘了）。修复一行量级（三函数持 `_TargetLock(path)`，per-goal 锁零争用、无嵌套无死锁），按「发现即闭环」应本轮闭环。故 NEEDS_CHANGE。

---

## 1. 发现清单

### P1-1（关键·本轮必须修复）goal-bridge 工件读-改-写无锁——并发下用户裁决与审计行可被整体抹除

- **位置**: `infra/goal_bridge.py:441-539`（record_execution：`:469-473` load → mutate → `:484/507/513/526/533` save）、`:545-590`（write_checkpoint）、`:596-703`（record_ruling）——全文无 `_TargetLock`/任何锁原语（grep 证实）。
- **事实**（一手）: ①三变更函数均为无锁 RMW；②对照协议先例：FEAT-096 R1（同仓、上一票）刚把 execution_isolation 的同类 RMW 纳入 `governance_store._TargetLock` 协议并复审通过——本票同型面未跟进；③**确定性实证**（内存探针 `%TEMP%\feat097-r0-lostupdate-probe.py`，monkeypatch `_load_artifact` 一次旧快照返回，模拟「Coordinator 裁决 vs 流氓 agent 持续 record」交错）：abort 裁决保存后 state=BLOCKED/scope_ruling=abort/history=3 行 → racing refuse-save 落盘后 state=CHECKPOINTED/**scope_ruling=None**/history=2 行——**用户裁决连同审计痕迹被抹**；④较轻同向损害：两个并发 refuse 的 unauthorized_attempts 互相覆盖（审计少计）——验收④「故障注入全留痕」在并发相位不成立。
- **影响评估**: 需要同 goal 并发调用（裁决 vs 持续 record）——恰是 RPG 实证威胁模型（流氓并行 actor）；单 Coordinator 顺序调用不触发。损害面=用户意图记录+审计（本票核心交付），状态门本身仍拒绝执行（复活的是 CHECKPOINTED 非 RUNNING）——据此 P1 而非 P0。
- **修复建议**: 三变更函数内 `from governance_store import _TargetLock`（函数内导入保 R6 冷面 208 不变——FEAT-097 已验证的同型手法）+ `with _TargetLock(artifact_path, timeout)` 包住 load→mutate→save；StoreError→CODE_LOCK_CONTENTION 可重试。补并发回归用例（两真子进程或 monkeypatch 旧快照注入——探针可直接转正为用例）。

### P2-1（建议·原则上本轮修）CHECKPOINTED 恢复面与 BLOCKED 授权标准不对称——continue/extend-budget 无需任何 authorized_by 即可恢复 RUNNING

- **位置**: `infra/goal_bridge.py:621-654`（CHECKPOINTED 分支：四种 decision 均无 authorized_by 检查）对照 `:656-669`（BLOCKED 分支：decision∈AUTHORIZED **且** authorized_by 非空，否则拒+留痕）。
- **事实**: 从 CHECKPOINTED，`--decision continue`（或 extend-budget/reduce-scope）以空 authorized_by 即转回 RUNNING——选项描述自证需用户确认（continue="已确认风险"）；SKILL 第 10 条声明「CHECKPOINTED MUST AskUserQuestion 带范围裁决选项——禁静默续跑」为协议级约束，模块门未对齐。测试自身以 `ruling(decision="continue")` 无授权为合法载具（`test_goal_bridge.py:262-263`）。一个忽略 ask 的行为者可用一个旗标自清 CHECKPOINTED，仅留 authorized_by="" 的事后审计痕。
- **建议**: 恢复方向裁决（continue/extend-budget/reduce-scope）要求 authorized_by 非空（与 BLOCKED 面及选项描述对齐）；abort 可豁免（安全方向——终止后恢复本就需授权）。补对称性红测。

### P2-2（建议·原则上本轮修）record_execution 不比对 rules_version——docstring「a mixed version can never pass silently」声明宽于实现

- **位置**: `infra/goal_bridge.py:23-27`（docstring 声明）对照 `:617-619`（仅 record_ruling 比对 rules_changed）+ `:441-539`（record_execution 全程无比对）。
- **事实**: 跨会话 RUNNING 续跑（不经 ruling——goal 从未 checkpoint 的常路径）在插件版本变化后零披露继续；混合版本静默通过面存在。唯一测试（`test_resume_with_different_rules_version_is_loud`）只覆盖 ruling 路径。
- **建议**: record_execution 在 load 后比对 `_default_rules_version()` 与 `artifact["rules_version"]`，mismatch 追加 `rules_version_changed` history 行（披露不阻断——DEC-330 语义）；SKILL.md 读取为毫秒级，judge ≤10ms 预算面不受影响（judge 无 I/O）。补一条跨版本 record 用例。

### P2-3（建议·原则上本轮修）checkpoint 账本面 `events_total` 为幻觉键——恒 null，验收③账本导入缺计量

- **位置**: `infra/goal_bridge.py:283-290`（`_ledger_summary` 读 `summary.get("events_total")`）对照 `infra/authority_ledger.py:1480-1523`（`status()` 实际返回 schema/integrity/**counts**/open_recheck_obligations(_keys)/snapshot——**无 events_total 键**）。
- **事实**: 函数真实、键名虚构——`.get` 容错使其恒 null 不崩溃；`test_schema_carries_all_five_faces`（`test_goal_bridge.py:224-226`）只断言 `available ∈ (True, False)` 未断言该键，绿灯放行。checkpoint 工件的账本面（验收③）携带恒空字段；义务面（open_recheck_obligations/keys）为真键、完好。
- **建议**: 改读真实键（`integrity.last_seq`/`integrity.lines` 或 counts facets 的合计），或删该字段；测试补断言非 null（修复后）。

### P2-4（建议）危险区边界等号与多维同时 danger 零测试

- **位置**: `infra/goal_bridge.py:320`（`share >= danger_ratio`——含等号，语义正确）与 `:311-322`（any_danger 聚合）对照 `test_goal_bridge.py:107-133`（四维**独立**注入+warning-alone，无 share==danger_ratio 恰好触发用例、无多维同时 danger 交叉用例）。
- **建议**: 补 `rounds=42`（恰 70%×60）→danger 边界用例；补 rounds+tokens 双 danger → danger_dimensions=[rounds,tokens] 用例。

### P3-1（讨论）未申报草稿残留 `_tmp_suite097.log`（仓库根、未 ignore）

- **事实**: `git status` 第 15 个未申报面；污染 untracked 检查，`git add -A` 会误入 commit。建议 Developer 收口时删除。

### P3-2（讨论）unauthorized_attempts 语义混装——DRAINING 相位拒绝计入「未授权」总数

- **位置**: `infra/goal_bridge.py:479-484`（三类拒绝同列）+ `:730-731`（goal_status 的 open_unauthorized_attempts=len 总数）。DRAINING 新工作拒绝（kind=execution）与 BLOCKED 续跑拒绝（kind=resume）混计——弱化验收④指标纯度。建议 status 按 kind 分桶。

### P3-3（讨论）`_parse_new_limits` 静默跳过畸形项——预算扩展输入 fail-open

- **位置**: `infra/goal_bridge.py:809-820`：`--new-limit rounds=abc` 静默无效（无 `=` 或非 float 的项被 continue 跳过）。预算**扩展**是安全敏感方向，建议 schema_violation 拒绝。顺带：abort/continue 决策也会应用 new_limits（无害但语义松）。

### P3-4（讨论）`_transition` 的 LookupError 无结构化捕获

- **位置**: `infra/goal_bridge.py:424-429`。守卫式分发使其当前不可达；若未来编辑破坏守卫，CLI 契约（JSON on stdout / exit 2）会以裸 traceback 破面。建议 except 转 CODE_ILLEGAL_TRANSITION 结构化错误（防御性）。

### P3-5（讨论）write_checkpoint 对 BLOCKED 目标返回 scope_ruling_options+ask_contract

- **位置**: `infra/goal_bridge.py:582-590`（返回面无状态分支）。BLOCKED 的恢复路径是授权 ruling 而非四选一范围裁决——呈现语义轻微错位。

### P3-6（讨论）申报数 4443 vs 实测 4441（lightweight resident，Δ2 tok）

- **事实**: 我的 check-injection-budget 实测 lightweight resident 4441、strict 6197（与申报精确一致）。Δ2 为子面聚合口径差异量级、无害；建议 EVD 行以当场命令输出为准记录（REL-080 F-10 精度先例）。另注：skill 档 16045>16000 report-only（+45）——非 resident 硬门、如实披露面。

---

## 2. 五维度结论（硬门槛 ②：100% 覆盖）

| 维度 | 结论 | 依据（一手） |
|------|------|------|
| **正确性** | **PASS（带 P1-1/P2-2/P2-4）** | 状态机 7 边纯数据表逐一核对（`:103-111`）；`_transition` 未知边 LookupError fail-closed；危险区判定 `share>=danger_ratio` 含等号、any_danger 聚合、round(share,4) 仅显示不影响判定（`:319-329`）；RUNNING 触发轮完成+下轮收口、DRAINING in-flight 区分、持续危险→CHECKPOINTED、显式 checkpoint 链（RUNNING→danger_zone→DRAINING→drained→CHECKPOINTED）语义与 docstring/SKILL 一致；工件加载 fail-closed（不可读/错 goal/未知 state 三拒）；幂等面（already-CHECKPOINTED 无新行无 revision bump）有测试。缺陷=P1-1 并发、P2-2 版本缝隙、P2-4 边界测试缺 |
| **安全性** | **PASS（带 P2-1/P3-2/P3-3）** | goal_id 闭式正则拒路径穿越（`../escape` 拒绝有测试——FEAT-096 P2-2 教训已吸收）；错误码闭式词表+disposition；授权语义按 non_goal ③ 边界内实现（authorized_by=调用方断言+审计痕，identity 验证归 095——边界一致）；薄弱面=P2-1 不对称、P3-3 fail-open 输入缝 |
| **可维护性** | **PASS** | 阈值/映射为配置面数据（custom 注入测试证明调整不动状态机——quality_budget 原文达成）；thin entry+add_arguments 单源+option-fact-source drift 守卫测试；模板单源（SKILL canonical 全文+触发线投影+三镜像同步由 check-projection-sync 强制）；函数内导入 authority_ledger（peer-leaf 模式）；28n 零新增（arch-health 4E/33W 与 FEAT-096 期恒等、goal_bridge 零出现）；916 行四子系统结构清晰无冗余 |
| **性能** | **PASS** | judge ≤10ms median-of-9 守护用例（纯函数无 I/O）；record 路径=工件读写+（修复 P1-1 后）一次 per-goal 无争用锁——轮间毫秒级；≤10ms 预算语义归属 judge 面（SKILL/质量预算原文「预算信号采集与状态判定」）合规 |
| **测试覆盖** | **PASS（带 P2-4）** | 26 单测+5 接线测全绿：四维独立故障注入/warning 不充分/配置数据/grep 面/状态机六面/schema 五面/幂等/跨版本响亮/故障注入 3 拒留痕+state 不离 BLOCKED/授权恢复+new_limits 生效/CHECKPOINTED 双面/abort 终态/回退开关零状态写/≤10ms/CLI roundtrip exit 2。缺口=并发零用例（P1-1）、边界等号、多维交叉 |

---

## 3. AI 代码专项 5 项（硬门槛 ⑤）

| 项 | 结论 | 依据 |
|----|------|------|
| mock 残留 | **无** | 生产模块 grep `mock/Mock/pdb/breakpoint/TODO/FIXME` 零命中；print 仅 CLI 输出面；测试侧 mock_env/`unittest.mock` 为正当工具 |
| 硬编码返回值 | **无** | DEFAULT_BUDGET_CONFIG=assumption_record 钦定首轮保守值（配置面数据、custom 可注入）；SCOPE_RULING_OPTIONS/ASK_CONTRACT 为契约常量；无业务逻辑硬编码 |
| 幻觉 API 调用 | **有 1 处（P2-3）** | `_ledger_summary` 调真实函数 `authority_ledger.status` 但读虚构键 `events_total`（status 返回 counts/integrity/open_recheck_obligations(_keys)/snapshot，无此键）——`.get` 容错致恒 null 静默；义务两键为真键完好 |
| 未实现 TODO | **无** | grep 零命中 |
| 过度实现 | **无** | 916 行（申报 ~750，docstring ~130 行）四子系统+CLI 各有验收归属；7 个 action 均可追溯（record/checkpoint/ruling=验收①③④、judge/thresholds/mapping=质量预算 accessibility、status=查世界）；与仓内 caliber 相称 |

---

## 4. 设计一致性（硬门槛 ④）

**non_goals×3 逐条**:

| non_goal | 裁定 | 依据 |
|----------|------|------|
| 不替代 harness goal 机制 | **符合** | goal 状态为输入、治理状态为本模块自身投影（docstring `:8-11` + judge/recommended_transition 形态）；无 goal 生命周期重造 |
| 不做 mid-session 热升级（DEC-330） | **符合（实现缝隙见 P2-2）** | 规则版本变化=checkpoint+新会话生效语义保留；record_ruling 路径响亮披露+history 行有测试；缝隙=record 路径无比对（P2-2，披露面缺口非执法违反） |
| 不动 FEAT-095 六边界执法面 | **符合** | 续跑授权=协议+CLI 门（authorized_by 调用方断言+审计痕）；identity 级验证未越界；模块 docstring `:34-38` 显式声明供信号不执法 |

**quality_budget 六维**: performance ✓（§2）；reliability ✓（1115 零退化+幂等用例；并发相位=P1-1 缺口）；security ✓（故障注入 0+规则版本——P2-1/P2-2 为强度缝隙）；accessibility ✓（thresholds/mapping/status 三 grep 面+阈值/映射 CLI 实测渲染；schema 即工件自描述+docstring）；ux ✓（ask_contract must_ask+四选项带描述+MUST 断言；收口阈值 thresholds 面明示）；maintainability ✓（维度可扩展不动状态机【custom 注入测试】+模板单源+28n 零新增+injection strict 6197≤6200）。

**allowed_change_scope**: 14 文件全部在票面（模块/单测/接线/接线测/SKILL/init/registry 族/基线/快照/三投影）；`_tmp_suite097.log` 为越面残留（P3-1）。registry 106 重普查（17 outside/89 monolith）与快照/基线同 change 落地=documented contract-change path ✓；anchor 28120→28160=+40 恰为本票接线增量（**零外来吸收**——FEAT-096 期 P3-3 形态未再现）；R6 207→208（goal_bridge 导入期 stdlib-only，实测冷面零 authority_ledger）。

**验收①~⑤核验**: ①✓（数据表+门；P2-1 强度）②✓（四维注入+warning 不充分；P2-4 边界测试缺）③✓ 五面在场（P2-3 events_total 恒 null）④✓ 3 拒全留痕实测复现（并发相位=P1-1 关联）⑤✓ 三 profile PASS（strict 6197 余量 3 精确复现；轻量 Δ2=P3-6；三投影同步）。

---

## 5. 验证命令与输出（审查者独立实跑）

| # | 命令/动作 | 结果 |
|---|-----------|------|
| 1 | `git status/diff --stat` | 12M+2?? +254/−23 与申报一致（另见 P3-1 残留） |
| 2 | `python -m unittest …test_goal_bridge` | **Ran 26 tests in 0.595s — OK** |
| 3 | `…Feat097GoalBridgeWiringTests` | **Ran 5 tests in 0.060s — OK** |
| 4 | `…test_registry …test_contract_matrix` | **Ran 104 tests in 94.075s — OK**（冻结 106/208/73） |
| 5 | `…test_verify_workflow`（全模块） | **Ran 1115 tests in 375.921s — OK**（exit 0；与 Developer 声明「1115（基线 1110+5）」精确一致） |
| 6 | `check-injection-budget`（默认+`--profile strict`） | **PASSED**——lightweight resident 4441≤6200、**strict 6197≤6200（headroom 3 tok）**；skill 档 16045>16000 为 report-only 披露面 |
| 7 | `check-governance --summary-only` | **0 FAIL / 3 WARN**（untracked 含 P3-1 残留 + 既有 28n advisory） |
| 8 | `check-architecture-health` | 4E/33W 与 FEAT-096 期恒等；**goal_bridge 零出现**（28n 零新增） |
| 9 | `goal-bridge --action thresholds/mapping --text` | 配置数据 grep 面正确渲染（四维 limit/warn/danger + 7 边映射） |
| 10 | 内存探针（P1-1 实证，零落盘） | abort 裁决被 racing refuse-save 抹除：BLOCKED→CHECKPOINTED 复活、scope_ruling None、历史 3→2 行 |

---

## 6. 硬门槛自检（输出前）

| 门槛 | 判定 |
|------|------|
| P0 阻塞问题数 = 0 | ✓（P0=0；P1×1 显式声明「本轮必须修复」——NEEDS_CHANGE 依据） |
| 5 维度 100% 覆盖 | ✓（§2 逐项有结论） |
| 每条发现 P0~P3 + 文件:行号 + 事实 + 建议 | ✓（§1 四要素齐备） |
| 设计一致性（non_goals + quality_budget 六维） | ✓（§4） |
| AI 专项 5 项逐一结论 | ✓（§3——幻觉 API 项有 1 处实锤 P2-3） |
| 事实依据红线 | ✓（每条结论指向行号/命令输出/探针输出；Δ2 tok 等测量差如实披露） |

## 7. 给 Coordinator 的返工提示（R1 注入用）

R1 复审 MUST 逐条比对：①P1-1=三变更函数持 `_TargetLock(artifact_path)`（函数内导入）+ 并发回归用例（本报告探针可直接转正）；②P2-3=events_total 改真键或删+非 null 断言；③P2-1=CHECKPOINTED 恢复方向裁决要求 authorized_by+对称红测；④P2-2=record 路径 rules_version 比对+披露行+用例；⑤P2-4 两条边界/交叉用例。P3 可遗留（P3-1 建议收口时顺手删除）。修复后预期结论路径：APPROVED 或 APPROVED_WITH_NOTES（unresolved_blockers=0）。
