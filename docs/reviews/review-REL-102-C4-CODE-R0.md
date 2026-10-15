# C4 修复独立代码审查报告（REL-102 / CODE R0）

- **审查对象**：未提交工作树修改 `skills/software-project-governance/infra/tests/test_verify_workflow.py`（FEAT075ExceptionAnnotationTests.test_archguard_render_carries_suffix_and_underlying_counts 时钟敏感修复）
- **审查日期**：2026-10-15 16:24（真实时钟已过 2026-10-12——修复正当其时）
- **Reviewer**：独立 Code Reviewer 子代理（零文件写入/零 commit/零改码；实验探针仅用内存+%TEMP% 临时目录；与 Developer 不同会话）
- **Verdict**：**APPROVED_WITH_NOTES，unresolved_blockers = 0**
- **派发方**：REL-102 Coordinator（C4 条件项——unit tests 3F+1E 处置，M-0 报告 §7 C4）

## ① Verdict

修复正确、外科手术式、根因定性成立、独立复跑全绿。1 项 P2 为 commit 纪律提示（不指向被审代码本身，不阻塞）。

## ② 逐项核验结果

### 1. diff 面核验 — ✅ 限定单测试，外科手术式

- 实测 numstat：`17 insertions / 2 deletions`（仅 test_verify_workflow.py；Developer 报「+19/-5」系 `--stat` 组合显示口径——19=17+2，5=三文件删除合计 1+2+2——非实质偏差，如实记录）。
- diff 全文仅 2 个 hunk，全部落在同一测试方法内（修复后 L24349-24383）：hunk1 = 14 行依据注释 + `expires = (date.today() + timedelta(days=14)).isoformat()` + `self._registry(expires_on=expires)`（L24364-24365，经 fixture 既有 `**overrides` 机制注入，`test_verify_workflow.py:24178-24190`）；hunk2 = 断言字符串动态化（L24379-24380）。零顺带重构，D4 纯粹。
- ⚠️ 工作树非净：另含 `infra/hooks/commit-msg`（+742/-1）与 `infra/tests/test_hooks.py`（+855/-2）未提交修改 + 未跟踪 `rowdump.txt`。其头部自证归属 FIX-445（commit-msg diff 首段 `# --- Step 12 support: source-verified fabrication scan (FIX-445) ---`，DEC-334 有界重设计链）——REL-102 工作树上的另一并行票据流（plan-tracker L80：C4 子步与 FIX-445 域分离）。「C4 执行期间是否触碰过 sibling 文件」无法从 git 工作树证实或证伪（无 hunk 级归属证据）→ 标注「未证实」；但被审文件内的修改面确凿限定单测试。见 F-1。

### 2. 根因判定复核 — ✅「断言过时，非产品回归」成立（独立实验证明）

- 时钟链实读：渲染走 `verify_workflow.py:23747-23748`（`_archguard_print_findings` 调 `_exception_note`，无时钟参数）→ `verify_workflow.py:1142-1151`（`_exception_note` 仅转发 check_id/artifact/severity/root/bytes_value，不传 today）→ `exception_registry.py:314-325`（`exception_note(today=None)`）→ `exception_registry.py:271`（`today or date.today()`）→ `exception_registry.py:225-229`（`evaluate_exception`：`today > expires` → `expired`，fail-closed）。
- 独立实验（内存探针，当前时钟 2026-10-15）：旧 fixture `expires_on="2026-10-12"` → 渲染含 `[ERROR] governance_data_size:` 行、counts (1,0) 不变，但 `exception accepted` 后缀消失（原 `assertIn` 必红）；新 fixture `today+14d` → 后缀以完整形态 `exception accepted (EXC-001, ref=DEC-280, expires=…)` 复现。产品 fail-closed 过期行为与 `test_expired_exception_not_effective`（`test_verify_workflow.py:24233-24241`）语义一致 → 定性「断言过时」成立，非产品回归。
- fixture 来源：`git log -S '2026-10-12'` 实证 commit `16a5157`（2026-09-28，FEAT-075/DEC-278 单元二）引入硬编码——与 Developer 声明一致。
- 注入点核验：渲染路径确无 today 注入点（API 层 `exception_note/annotate_findings` 虽收 today=，但 vw 包装层不透传）；测试唯一 seam 是 `HOST_PROJECT_ROOT`（已被使用）。「有注入点而未用→P2」条款不触发。

### 3. 修复质量 — ✅ 消除时钟敏感、语义保真、无 overfitting

- 时钟稳定性：`date`（纯日期粒度，无时区/DST 面）+ 14 天前瞻余量——今天跑/下周跑/跨年/跨午夜均稳定。
- 语义保真：断言仍完整校验 `exception accepted (EXC-001, ref=DEC-280, expires=<registry 值>)` 形态 + 底层 `[ERROR]` 行/`bytes=300000`/counts (1,0)/severity（L24377-24383）——「标注不改判原始结果」类不变量（docstring L24156-24158）全保。
- 无 overfitting：改的是 fixture 输入（override expires_on）而非削弱断言/绕过检查；断言变量与 fixture 变量同源，验证的正是「渲染回显 registry 到期日」被测语义。
- 注释引用核验：EVD-1697 ✅（evidence-log L2508）；FIX-364 ✅（clock_window_sensitive 族）；commit 16a5157/2026-09-28 ✅；DEC-280 ✅ 存在，但「two-week registration horizon」措辞未在决策文本找到（14d 实为 FEAT-075 fixture 原跨度镜像）→ F-2（P3）。
- 「类内唯一真实时钟裁决测试」声明核验 ✅：其余 11 测试逐一实读——9 个直调 `er.*` 均显式注入 `today=_today()`=2026-10-01；render/release 面或与日期无关或两分支断言均成立。全类今日（过期后第 3 天）通过 = 活体反证。

### 4. 独立复跑 — ✅（见 ④）

### 5. 回归风险 — ✅ 影响面收敛于该单测试

- fixture 默认值未动（L24186 仍 `"2026-10-12"`）→ 类内其它测试静态时钟假设零影响；新代码仅用模块级既有导入（L28），零新增依赖/零共享状态；全模块 1135 OK。

## ③ 发现分级（P0=0，P1=0，P2=1，P3=2）

| # | 级别 | 位置 | 发现 | 处置建议 |
|---|------|------|------|----------|
| F-1 | P2 | 工作树全局 | 同一未提交工作树混载 C4（+17/-2）与 FIX-445 流（commit-msg +742/-1、test_hooks +855/-2）及 rowdump.txt；C4 是否曾触碰 sibling「未证实」。一把 `git add -A` 将违反 D4 | C4 与 FIX-445 流分开提交（Coordinator 收口纪律）；FIX-445 面走自己的审查链 |
| F-2 | P3 | test_verify_workflow.py:24360-24361 | 注释「DEC-280 two-week registration horizon」措辞无决策文本依据（14d 实为原 fixture 跨度镜像） | 未来该测试再动时顺带改注「mirroring the fixture's original two-week span」；本轮 D4 纯粹性优先不改 |
| F-3 | P3 | 仓库根 rowdump.txt（未跟踪，56 行） | FIX-445 域（EVD-1536+）治理行导出调试残留 | 提交前删除或移入 `.governance/incidents/`，避免误收 |

## ④ 独立复跑输出摘要

| 命令（均 PYTHONUTF8，repo 根） | 结果 | exit code |
|---|---|---|
| `python -m unittest ...test_verify_workflow.FEAT075ExceptionAnnotationTests -v` | Ran 12 tests in 40.537s / OK | 0 |
| `python -m unittest ...test_verify_workflow`（全模块） | **Ran 1135 tests in 488.425s / OK** | **0** |
| 内存探针（旧/新 fixture 对照渲染） | 旧 expires=2026-10-12：accepted_suffix=False；新 expires=2026-10-29：accepted_suffix=True/suffix_full=True | 0 |

两项复跑与 Developer 声明逐字吻合；根因经独立实验证实。

## 审查边界声明

未证实项仅 F-1 的 hunk 级归属（git 工作树原理性不可证）；commit-msg/test_hooks.py（FIX-445 流）与 rowdump.txt 内容质量不在本次审查范围。Reviewer 未写任何仓库文件、未 commit、未改任何代码。
