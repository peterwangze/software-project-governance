# Review FIX-391 — CODE R0（后置代码审查）

- **Task**: FIX-391 — closure journal 版本感知读取器（REL-089 条件③ 消解票；DEC-241 附带裁定机器门禁落地）
- **Round**: R0（首轮）
- **审查对象**: staged diff `git diff --cached`（+684/0，2 文件——`closure_chain.py` +170 / `test_closure_chain.py` +514；工作树与 index 一致，全部实跑均针对 staged 内容）
- **审查者**: Code Reviewer Agent（只读审查；本报告为唯一写入面）
- **依据**: agents/code-reviewer.md + skills/code-review/SKILL.md；事实依据红线——每条结论指向文件行号/命令输出/测试结果
- **日期**: 2026-09-26

---

## 结论

## **APPROVED_WITH_NOTES**（unresolved_blockers=0）

P0=0 · P1=0 · P2=0 · P3=5（全部为申报口径/边界记录项，不阻塞合并）。
硬门槛全过：亲跑四组测试全绿、census 恒等实质成立（零涉及本 diff）、五维度全覆盖、AI 五项全完成、设计一致性与 REL-089③/DEC-241 契约相符、FEAT-065 串行红线无半成品接口。

---

## 1. 逐行 diff 审查（正确性）

### 1.1 预检时序真实性 —— ✅ 核验通过（审查重点 1）

`_journal_version_conflict`（closure_chain.py:665-733）在四入口的落位逐一经读：

| 入口 | 预检位置 | 锁 | 预检后的首个副作用 |
|------|---------|-----|------------------|
| `_run_locked` | :1784（函数体第一条语句） | run_chain:1769-1772 `_RunLock` 锁内 | :1787 `_load_closure_events`（读）→ :1811-1814 fenced-audit → :1818 fresh-start `closure_started` |
| `finalize_closure` | :2139（锁内第一条语句） | :2135 `_RunLock(lock_path, 10.0)` | :2142 load → :2175 fenced-audit → :2191 `closure_finalized` |
| `_cancel_locked` | :2618（函数体第一条语句） | cancel_closure:2775 锁内 | :2621 load → 后续 terminal 追加（:2681）+ locks-release |
| `_reopen_locked` | :3161（函数体第一条语句） | reopen_closure:3287 锁内 | :3164 load → :3211 `closure_reopened` |

- **fenced-audit 路径**（`_run_locked`:1811-1814）：预检在 :1784，先于 :1814 的 `_record_fenced_event`（其 journal 追加在 :2926）——「fenced resume×版本冲突叠加=拒绝且零 closure_fenced 事件」由测试 `test_preflight_precedes_the_fenced_audit_write` 钉住，静态时序与测试双向成立。
- **fresh-start 路径**：预检在 :1784，先于 :1818 的 `closure_started` 追加——新开链同样被门禁覆盖（journal 已带冲突时禁止开链写第一笔）。
- **journal 写入口完备性**：`_append_closure_event` 全部 12 个调用点（:1468/:1524/:1818/:1864/:1898/:1948/:1971/:2191/:2681/:2926/:3211，其中 :2926 属 `_record_fenced_event`，其调用方 :1814/:1848/:2175 均在已门禁入口内）皆落于四入口锁内。**`takeover_execution`（:2936-3106）经核读只写 execution-generations record（:3090），不写 closure journal**——接管路径无门禁缺口。
- 四入口锁路径同一：`_closure_lock_dir(root)/(closure_id + ".lock")`（:1769/:2134/:2773/:3285）——同 closure 的 journal 写者全串行。

### 1.2 门禁谓词完备性 —— ✅ 核验通过（审查重点 2）

`_journal_version_conflict`（:665-733）边界逐一构造推演：

| 构造 | 谓词行为 | 归属车道 | 判定 |
|------|---------|---------|------|
| 合法 11 型逐一 | `CLOSURE_EVENT_TYPES`（:421-433，实数 11 型）内 → 不 flag | 正常流转 | ✅ |
| 未知 str 型（如 `closure_voided`） | :676-680 flag → `unknown_event_types` | 零写拒绝 | ✅ |
| 缺 `event_type` 字段 | :676 `isinstance(str)` 不满足 → 不 flag | `_validate_closure_event`:572-574 required-field 检查 → `journal_problems` fail-safe 车道 | ✅（与申报的 fail-safe 车道语义一致） |
| 损坏行（不可解析 JSON/非 dict） | `loop_event_log.read_events`（loop_event_log.py:404-446，文档+实现均 never raises，损坏行跳过）→ 预检不 crash | fail-safe 车道（monotonicity gap 披露） | ✅ |
| `schema_version`=2 / 0 / 负数 | :700-703 区间比较 `[1,1]` 外 → flag → `foreign_schema_versions` | 零写拒绝 | ✅ |
| `schema_version`=True（bool 戳） | :700 `not isinstance(bool)` 排除 → 不 flag | fail-safe 车道 | ✅ |
| `schema_version` 缺失 | :700 isinstance 不满足 → 不 flag | fail-safe 车道（申报明确保留；测试 `test_preflight_absent_schema_version_stays_fail_safe` 钉住） | ✅ |
| `schema_version` 非 int（float 2.0/str） | 不 flag，envelope 校验（:557-587）亦不查 schema_version → 无披露 | fail-safe 车道 | ⚠️ 见 P3-3 |

- **`supports()` 契约规避的正确性**：`SchemaVersionWindow.supports()`（contracts.py:923-926）经 `_require_positive_int` 对 0/负数/非 int **会 raise**；预检改用纯区间比较（:700-703）保全域「拒绝而非崩溃」。contracts.py 零触碰（staged diff 仅 2 文件，已核实）。申报属实。
- **读 fail-safe 半面不变**：`closure_status`（:2202+）零改动；未知型经 `_validate_closure_event`:576-579 落 `journal_problems`，读面继续披露不设门——「读 fail-safe、写 fail-closed」双语义成立，测试 `test_status_face_stays_read_only_disclosure_on_conflict` 钉住。

### 1.3 防占用 backstop 边界 —— ✅ 核验通过（审查重点 3）

`_append_closure_event`（:605-627）：

- **占用集语义**：:615-620 仅收真 int `cas_version`（`isinstance(int) and not isinstance(bool)`）——bool `True`（Python 中 `True == 1`）不误占 seq 1；`None`/字符串数字同样不入集。边界正确。
- **kept=[1,2]→next=3 与 raw 3 相撞向量**：`_next_seq`（:656-663）从 kept 视图取尾+1；原始 journal 尾部为未知型时 kept 丢尾 → next 撞已占用 seq → :621-627 raise ValueError，零写。碰撞在写入器侧机器不可达（对「忘带门禁的路径」兜底成立）。测试 `test_append_refused_at_occupied_raw_seq`（反）+ `test_append_at_free_seq_still_lands`（正控制，正常连续追加不受阻）双向钉住。
- **读-判-写窗口与锁纪律**：occupied 计算（:615-620 读）与 `append_event`（:628 写）之间存在理论窗口；经核 _append_closure_event 全部调用点均在四入口的同一 per-closure run lock 内（见 1.1 表），同 closure 并发写者串行，**窗口经锁纪律不可达=兜底定位准确**（申报属实）。唯一锁外调用面是测试直呼（单进程，无窗口）。
- **无误伤**：干净 journal 下 seq 来自 kept 尾+1，与占用集天然不相交——正常流转零拦截。

### 1.4 其余正确性核读

- `_run_locked` raise ValueError（:1786）vs 其余三入口 return dict——与各入口**既有错误风格一致**（_run_locked 全部 refusal 均 raise，如 :1796 cancelled-terminal、:1803 digest mismatch；CLI 面经 cmd_run:3495-3497 统一映射 `schema_violation`/`validation`/exit 2）。语义一致，见 P3-2 的清单字段面注记。
- 冲突 payload 结构（:719-733）：`error/disposition: validation/code: schema_violation/unknown_event_types/foreign_schema_versions`，与既有 closed-code 惯例（如 takeover:2970-2972）同构；`sorted()` 保证清单确定性。✅

---

## 2. 安全性 —— ✅ 通过

- 输入=不可信原始 journal 字节：预检经 never-raises 读原语 + isinstance 防御，任意字节不崩溃；区间比较全域拒绝（0/负数/出窗）。
- 注入面：无 shell/SQL/路径拼接新增；追加仍走 `loop_event_log.append_event` 单行 JSON 原语。
- 零写拒绝优先于一切恢复副作用（含幂等审计追加）——不会向不可判读 journal 写入任何字节。
- 权限/授权面零改动（cancel/reopen 的 authorized_by 字段纪律不在本 diff 触碰范围）。

## 3. 可维护性 —— ✅ 通过（一项既有债务注记）

- docstring 契约节（diff L10-54）逐条与实现核对一致（预检/结构化拒绝/读半面/backstop/伪造 tombstone/兼容矩阵/锁归属七点全对得上）。
- `_journal_version_conflict` 单一职责、零业务逻辑；四入口门禁各 3-4 行，无重复逻辑（分类逻辑单点收拢）。
- 28n WARN 注记：closure_chain.py 3617 行 / `_run_locked` 函数尺寸——既有超限模块 +170 行的**深化**而非新问题类型（God Module 拆分已挂起 0.90+，plan-tracker 有账）。见 P3-5。

## 4. 性能 —— ✅ 通过

- 每次写操作 journal 全读次数：门禁 1 次 + load 1 次 + backstop 1 次 = 3 次 O(n) 读；closure journal 规模 = 链步数级（几十行量级），可忽略。无新增 O(n²)/N+1。
- `unknown_types`/`foreign_versions` 用线性 `not in` 去重——冲突清单长度为常数量级，无热点。

## 5. 测试覆盖 —— ✅ 通过（亲跑）

- **新节 17 用例**（`-k "VersionAwareJournalReader or RunLockOwnership"` → **17 passed**，14.74s）：
  - VersionAwareJournalReaderTests **16** 用例：枚举前置 1 / 预检单元 4（干净×3 形态合 1、未知型、出窗 schema 2/0、缺失 schema）/ 四入口零写 4 / 预检时序（fenced-audit 前置）1 / 伪造 tombstone 负例 1 / backstop 正反 2 / 读半面不变 1 / 兼容矩阵 2。
  - RunLockOwnershipTests **1** 用例：stale release 不扰新持有者租约 + lock FILE 永不删除 + 租约可回收。
- 零写断言为**双重覆盖**：`_gov_snapshot`（.governance 字节快照，journal 在 `.governance/closure-events.jsonl`:537-544 内含其中）+ `_raw_unit_line_count`（原始 journal 行数，kept 视图无法提供的探针）——断言效力成立。
- 兼容矩阵五格亲跑通过（历史 8 型手装 journal 全流转+finalize/标准链锁腿幂等 resume 零追加/未知型含 tombstone 形状全入口零写拒/schema 2与0 全域拒/缺失 schema 留 fail-safe 车道）。
- 锁归属两组亲跑指认：dispatch-lock 归属面由既有 `CancellationLockOwnershipTests`（test_closure_chain.py:2483）+ `ExecutionGenerationFencingTests`（:2924）钉住，均含于 104P 全量绿内。

---

## 6. AI 代码专项五项 —— ✅ 全部完成

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | 无 | 测试用真 CLI 子进程（subprocess.run）+ 手装 journal fixture——fixture 是测试数据非生产 mock；产品代码零 mock |
| 2 | 硬编码返回值 | 无 | 冲突 payload 全部源自实测 journal（read_events 实读）；无固定返回绕道 |
| 3 | 幻觉 API 调用 | 无 | 所调用 API 逐一实存（read_events/build_event/append_event/CLOSURE_EVENT_TYPES/SchemaVersionWindow 字段/测试 helper 全数定位），且 17+104+11 全绿实证 |
| 4 | 未实现 TODO | 无 | diff 全文 grep TODO/FIXME/XXX/HACK/NotImplemented 零命中 |
| 5 | 过度实现 | 无 | 预检/backstop/门禁均为最小实现；超票面的 cancel/reopen 门禁有同向量依据（边缘①，见 §8）；无投机泛化 |

## 7. 硬门槛亲跑实录

| 门槛 | 命令 | 结果 | 申报比对 |
|------|------|------|---------|
| 新节 | `pytest test_closure_chain.py -k "VersionAwareJournalReader or RunLockOwnership" -q` | **17 passed**（14.74s） | 申报总数 17 ✓；**拆分申报 15+2 ≠ 实际 16+1**（P3-1） |
| 全量 | `pytest test_closure_chain.py -q` | **104 passed**（134.01s，exit 0） | 申报 87P→104P ✓（+17 一致） |
| REL-089 兼容 | `pytest test_rel089_release_compat.py -q` | **11 passed**（9.71s，exit 0） | 申报 11P ✓ |
| census 严格档 | `verify_workflow.py check-governance --summary-only --level strict` | **exit 0，51 issues** | 申报 49 → 实测 51，+2 归因见 P3-4；**51 条逐条核读，零条涉及本 diff 产品代码** |
| write-guard | `verify_workflow.py governance-write-guard --show-posture` | exit 0（裁定表 D1 warn 姿态=既录状态，非本 diff 产物） | ✓ |
| cross-refs | `verify_workflow.py check-c­ross-references` | PASS（无 dangling/deprecated/circular） | 申报 ✓ |
| manifest | `verify_workflow.py check-manifest-consistency` | PASS（910 canonical 一致） | 申报 ✓ |
| semver 字面量 | `pytest test_static_version_pins.py -q` | **25 passed**（真实树扫描，docstring/注释面不命中——新节 3 处「0.87」为历史叙事散文） | 申报零命中 ✓ |

**census 51 条逐条归因摘要**（零涉及判定）：Goal Alignment/User Impact（REQ-092/FIX-388 等 EVD 旧证据格式）· 18d/18f/18i（REL-090/091/092 发布链三件套占位——后续 REL 票义务）· Review Debt（**FIX-391 本票自身待审态**——本审查闭环后由 Coordinator 机录消除）· 28s evidence-log 体积 · Check 31（review-FIX-395-CODE-R1.md 边界 + risk-log ragged row——兄弟票/治理文件）· Check 34×2 · 各 WARN（风险过期/结构/28n 形状等既有账）。closure_chain.py 仅现于 28n 形状 WARN（既有超限模块）。

**不可复验项（如实申报）**：TDD 红相「13F/4P exit 1」——红态已不存在，复现须回滚产品代码（违反审查红线，不执行）；按终态反推红相拆分为 11-12F/5-6P 量级，申报数字疑为开发中间态快照（与 P3-1 的 15+2 同源）。绿态与本票验收相关的全部事实已亲跑核验。

## 8. 边缘 3 项定级

| 边缘 | 内容 | 定级 |
|------|------|------|
| ① | cancel/reopen 门禁超出票面字面 MUST（同误读向量的追加入口） | **采纳，正确闭合**——「不留半成品接口」核读成立：四入口门禁全量完整落位（非 stub/非预留），测试四格零写钉住；与「每 journal 消费型写入口必门禁」的 arch① 原则自洽 |
| ② | 预检选型=完整 journal 预检（arch①）而非等效隔离（arch②） | **采纳，非等效论证成立**——`test_preflight_precedes_the_fenced_audit_write` 实证「发现未知事件于中途」不可安全化：隔离方案下 fenced-audit 追加会先落笔；预检使冲突 journal 连一条审计事件都不增益 |
| ③ | 防占用 backstop 作为碰撞向量的写入器侧消除机制 | **采纳，边界正确**——bool/None/字符串数字损坏形态不误判占用；锁纪律使读-判-写窗口不可达=纯兜底定位如实；正反两测钉住零误伤 |

## 9. FEAT-065 串行红线 —— ✅ 核读通过

- 本 diff 零触碰 locks-release/TTL 判定面（FEAT-065 的标的）；无半成品接口、无预留 hook、无 TODO 桩。
- `RunLockOwnershipTests` 钉住的「run-lock FILE 永不删除」与 FEAT-065 的「dispatch locks 条目真释放」分属两个域（锁文件 vs locks.json 条目），无冲突；测试 docstring 已显式指认 dispatch 面归既有两组测试。
- plan-tracker：FEAT-065 状态「🆕 已 triage 待排期」，FIX-391 先行落位完整闭环，无跨票依赖倒挂。

## 10. 发现清单（P0-P3）

**P0：0 条。P1：0 条。P2：0 条。**

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| P3-1 | P3 | 申报口径 | 申报「VersionAwareJournalReaderTests 15 用例+RunLockOwnershipTests 2 用例」与 staged 终态 **16+1** 不符（总数 17 一致）；TDD 红 13F/4P 亦疑为中间态快照 | 后续申报以 collect-only 实数为准；本票无需改码 |
| P3-2 | P3 | closure_chain.py:1786 | run/resume 面经 `raise ValueError(detail)`，CLI 映射后 `unknown_event_types`/`foreign_schema_versions` **机器清单字段在该面降级为 prose**（finalize/cancel/reopen 三面保留完整结构）；申报「机器清单」在 4 面中 3 面成立 | 若 runbook 消费方需在 resume 面机读清单，后续票可为此引入结构化异常类型（涉及 cmd_run 错误通道扩展，超出本票字面范围，不阻塞） |
| P3-3 | P3 | closure_chain.py:700 | 非 int schema_version（float 2.0/str 形态）既不入版本门亦不被 envelope 校验披露——与「缺失 schema_version」同行 fail-safe 车道，但申报只点名了缺失形 | docstring 车道声明可补一句「非 int/缺失 stamp 同属 fail-safe 车道」；纯文档级 |
| P3-4 | P3 | census 实测 | census 严格档实测 **51 issues**（exit 0）vs 申报 49：+2 为工作流推进产物（本票自身 review-debt + 兄弟票 FIX-395 R1 报告的 Check 31 边界项），另 1 条 untracked WARN 系**本次审查自身临时 diff 文件**（已清理）；「49 issues 逐条归因零涉及」的**实质结论（零新增涉及本 diff）经 51 条逐条核读成立** | 无需行动；后续申报附 census 快照时间戳以便对账 |
| P3-5 | P3 | closure_chain.py（模块级） | +170 行落入既有超限模块——28n module_size/_run_locked function_size WARN 深化（无新问题类型；God Module 拆分已挂起 0.90+ 有账） | 由挂起的拆分票统一清偿 |

## 11. 遗留项

无阻塞遗留。P3-1~P3-5 均为记录项，无关闭截止日要求；P3-2 若被采纳为后续票，建议随 REL-090 收尾前评估。

## 12. 审查用临时产物

审查期间于仓库根创建的 `.fix391_tmp_staged.diff`/`.fix391_tmp_census.txt` 已在报告落盘前删除（`git status` 复核仅剩两个 staged 文件）；`$env:TEMP` 下两份副本同步清除。

---

*审查者声明：本报告全部结论基于逐行 diff 核读（747 行 diff + 关联产品代码 ~600 行上下文）与上表亲跑命令输出；无假设性通过。复审锚点：若进入 R1，须逐条比对 §10 五条 P3 的处置状态。*
