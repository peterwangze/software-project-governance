# FIX-364 Code Review — R0

- **Task**: FIX-364 — snapshot freshness fixture 时间敏感缺陷（00:00~02:00 跨午夜误判 stale）
- **Round**: R0（首轮复审；无前轮 findings 可比对——本报告即基线）
- **审查对象**: 工作树未提交修改（纯测试面）`docs/reviews/diff-FIX-364.patch`（6.9KB 全文已读）
- **修改面**: `skills/software-project-governance/infra/tests/test_resolve_entry.py`（单文件）
- **审查者**: Code Reviewer Agent（只读审查；未修改任何代码）
- **工具声明**: 仅 Read/Grep/Glob（角色权限内）；未运行测试——Developer RED/GREEN 实证与 Coordinator 代验（单套件 24 passed / 0.14s；verify 无参 PASSED exit 0）作为**他方报告证据**引用，非本审查独立复跑。

---

## 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0 = 0 · P1 = 0 · P2 = 0 · P3 = 3（全部可遗留，不阻塞合并）

---

## 特别复核点逐项结论（6/6 已覆盖）

### 1. 引擎本体零改动 ✅ 通过

- **事实**：patch 全文（docs/reviews/diff-FIX-364.patch L1-138）仅含一个 `diff --git a/skills/software-project-governance/infra/tests/test_resolve_entry.py b/...` 段，3 个 hunk 全部落在测试文件；无任何 `resolve_entry.py` 的 diff 段。
- **判定**：triage 修改面红线（仅测试文件）满足。引擎 L39/L48/L111-135/L269-274 的现状即 HEAD 行为（本审查逐行核对的是修改后工作树中的引擎文件，与 diff 零改动事实一致）。

### 2. 时钟注入实现正确性 ✅ 通过

- **patch 目标有效性（事实链）**：
  - 引擎 `resolve_entry.py` L39：`from datetime import datetime, timedelta` —— `datetime` 以 from-import 形式绑定到 `resolve_entry` 模块命名空间 → 模块属性 `re_.datetime` 存在。
  - 测试 L107：`patch.object(re_, "datetime", _FrozenDateTime)` 替换该模块属性 → 引擎 L272 `datetime.now()`、L124/L130 `datetime.strptime` 在调用期解析到 patched 类。**patch 有效**。
- **CPython 限制绕行正确性**：内建 `datetime` 类型禁止 setattr（`TypeError: can't set attributes of built-in/extension type`）；子类化（L102 `class _FrozenDateTime(datetime)`）+ 模块属性替换是正确绕行，docstring（L98-100）如实记录了该约束。
- **类型兼容性**：`_FrozenDateTime.now()` 返回 naive `frozen_now`；`strptime` 未 override → `snapshot_dt` 为原生 naive datetime；L272 `frozen_now - snapshot_dt` 为 naive-naive 减法，无 aware/naive 混用 TypeError 风险。`timedelta` 为独立模块绑定，未被 patch，`timedelta(hours=SNAPSHOT_FRESH_HOURS)` 保持原生。
- **patch 作用域**：with 块覆盖 `_write_snapshot`（fixture 不读时钟，直接接收 `frozen_now`）与 `_env_for`→`re_.resolve`（L272 now() 冻结点）；断言在上下文退出后执行，此时 env 已物化——无恢复期读污染。

### 3. 正例修复语义 ✅ 通过（对齐口径，非弱化）

- **引擎口径（事实）**：L124 `datetime.strptime(m.group(1), "%Y-%m-%d")` → date-only 解析为**当日 00:00**；L272-274 判定 `now - snapshot_dt <= timedelta(hours=SNAPSHOT_FRESH_HOURS)`，L48 `SNAPSHOT_FRESH_HOURS = 24`。
- **修复后**：fixture `datetime.now()` → `strftime("%Y-%m-%d")` = 今天 → 引擎见今天 00:00 → age = 当日已过时长 < 24h **恒成立**（任意运行时刻，含 00:00~02:00 窗）。`snapshot_fresh=True` 无窗口。
- **原意图等价性推演**：原意「2 小时前的快照算 recent」在引擎 date-only 输入空间只有两分支——(a) 同日：即修复语义，fresh 保留；(b) 跨午夜（昨 22:00~24:00 写入）：引擎按其口径 age ≥ 24h 判 stale——这是引擎判定语义的**一致行为**，不是误判。原测试在 00:00~02:00 窗内期望 fresh，实质是 fixture 写入了引擎必然判 stale 的输入（fixture-引擎粒度错配才是缺陷本体）。修复将 fixture 对齐引擎输入空间，「today ⇒ fresh」意图等价保留且不再携带隐藏窗口。**结论：语义正确，不构成弱化。**

### 4. 负例守护强度 ✅ 通过（未弱化）

- `test_snapshot_freshness_midnight_window_stale_stays_stale`（L323-344）：frozen 00:30，fixture = `frozen_now - timedelta(days=1)` = 昨日 00:30 → strftime → 昨日 → 引擎解析昨日 00:00 → age = **24h30m > 24h** → `assertFalse(env["snapshot_fresh"])`。
- 该断言锚定引擎真实 24h 边界：若判定公式被放宽（≥ 25h/48h）此测试即失败 → 对「为使失败测试通过而放宽边界」的回归具有真实防护力。数值核算与引擎公式逐项一致，断言未被弱化。

### 5. 48h 老负例零改动 ✅ 通过

- patch 中 `test_snapshot_freshness_old_is_not_fresh` 仅以 context 行出现（patch L136-138，前缀空格），无 +/- 行 → **零改动确认**。
- 窗口敏感性独立核算：`now() - timedelta(hours=48)` 渲染 date-only；最坏情形 now = 今日 23:59:59.999 → 前日 23:59:59.999 → 引擎见前日 00:00 → age = 47h59m59s > 24h → stale **恒成立**。Developer「边界推演窗不敏感、保持原样」的判断成立。

### 6. 5 维度 + AI 专项 5 项 ✅ 见下节

---

## 5 维度逐项结论

| 维度 | 结论 | 依据 / 发现 |
|------|------|------------|
| 正确性 | ✅ 通过 | 特别复核点 1-5 全部通过；patch 作用域、类型兼容、数值核算均验证 |
| 安全性 | ✅ 通过 | 纯测试面：无外部输入校验面、无注入面、无敏感数据、无权限面。无发现 |
| 可维护性 | ✅ 通过 | docstring 完整记录 FIX-364 粒度契约、freezegun 等价决策、CPython 约束（L62-69/L89-101/L297-308/L323-331）；helper 命名达意；clock helper 复用于两窗口测试，无重复。P3-1 备注（下） |
| 性能 | ✅ 通过 | 2 个新测试 = 临时目录 IO + 内存计算；套件 24 passed / 0.14s（Coordinator 代验）。无 O(n²)/N+1 面 |
| 测试覆盖 | ✅ 通过 | 核心路径（fresh 判定）+ 窗口边界正/负两钉 + 错误路径（missing→None，原有未动）。P3-2 遗留备注（下） |

## AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | `_frozen_engine_clock` 为受控测试注入，with 退出自动恢复真实 `datetime`；无生产代码 mock 泄漏 |
| 2 | 硬编码返回值 | ✅ 无 | `now()` 返回冻结值是时钟冻结的意图本体；fixture 日期派生自同一冻结钟；00:30 有 docstring 依据，非孤立魔数 |
| 3 | 幻觉 API | ✅ 无 | `patch.object(re_, "datetime", ...)` 目标存在（引擎 L39 确认）；`datetime.now().replace(...)`、`contextmanager`、`strftime("%Y-%m-%d")` 均为真实 stdlib API，且与引擎 `_SNAPSHOT_DATE_RE`（L60-62，`\d{4}-\d{2}-\d{2}`）格式匹配 |
| 4 | 未实现 TODO | ✅ 无 | 全文无 TODO/占位 |
| 5 | 过度实现 | ✅ 无 | 单文件聚焦；零新依赖（stdlib-only）；未触碰引擎；未顺手改其他测试（48h 负例原样，符合 D4 修改纯粹性） |

---

## Findings 列表

### P0 阻塞：无

### P1 关键：无

### P2 建议：无

### P3 讨论/遗留（3 条，均可遗留，不阻塞）

- **P3-1**（可维护性/未来风险）：`patch.object(re_, "datetime", ...)` 依赖引擎「from-import 模块级绑定」这一实现细节。若未来引擎重构为 `import datetime` + `datetime.datetime.now()` 模块级访问，patch 将**静默失效**退回真实时钟——守护弱化（窗口钉退化为时段依赖），非误判。缓解现状：docstring L94-95 已显式声明该契约；可选加固：模块级自检（如断言 `re_.datetime` 可替换）或在引擎侧注释标记该耦合。不阻塞。
- **P3-2**（测试覆盖/遗留项）：精确 24h 边界值（age == 24h00m00s，引擎 `<=` 判 fresh）无直接钉。时钟冻结基建已就位，补一个 `frozen 00:00 / snapshot 昨日 00:00` 用例成本极低。建议后续票处理，非本票义务。
- **P3-3**（理论性/环境）：`datetime.now().replace(hour=0, minute=30)` 在存在午夜 DST 跳变的极端时区下「00:30」与真实世界时间语义偏差；naive datetime 下 replace 为纯数值操作不会异常，测试断言的是引擎数值判定，不受影响。本地部署环境无 DST，风险极低。仅记录。

### 证据完整性声明

- 本审查**未独立复跑测试**（Reviewer 无 Bash 权限）。「24 passed / 0.14s」「verify 无参 PASSED exit 0」「cross-refs PASS」「manifest PASS」「RED 实证（TEMP 冻结钟 00:30）」均引用 Developer 交付结论与 Coordinator 代验记录，作为他方报告证据；本报告的通过判定**不依赖**这些他方证据，仅基于静态逐行核对（diff 全文 + 修改后测试全文 + 引擎 L36-140/L258-302 事实）。若需独立运行时确认，由 Coordinator 在 M-2 低竞争窗执行全量对照（已在任务背景中排期）。
- 全量对照（并行 IO 竞争环境限制）**未覆盖**——如实标注，不作为本结论的依据或缺口。

---

## 硬门槛裁决

| 门槛 | 状态 |
|------|------|
| P0 阻塞问题数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 = 100% | ✅（逐项有结论） |
| 每条发现标注级别 = 100% | ✅（P3×3 全标注） |
| 设计一致性检查 | ✅（与 triage 修改面红线 / FIX-364 粒度契约一致；引擎零改动） |
| AI 专项 5 项 | ✅（5/5 有结论） |

## 复审协议说明

- 本轮为 **R0**（首轮），无前轮 review 报告可比对；后续若触发 R1，MUST 逐条比对本报告 P3-1~P3-3 的「已修复/未修复/新引入」状态。
