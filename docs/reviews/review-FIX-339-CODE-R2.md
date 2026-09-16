结论：APPROVED_WITH_NOTES ｜ round=2 ｜ unresolved_blockers=0 ｜ 机录 round 建议 = REVIEW-FIX-339-R3

# FIX-339 代码审查 R2 —— 复审（REVIEW-FIX-339-CODE-R1 退回修复核验）

- **round=2 声明**：本审查为 R2 复审（第 3 轮审查）；前轮报告全文重读并逐条比对——`docs/reviews/review-FIX-339-CODE-R1.md`（结论 NEEDS_CHANGE / unresolved_blockers=1；F-R1-01 P1 blocking / F-R1-02~05 P3；§R2 复审重点四项）。背景链 `docs/reviews/review-FIX-339-CODE-R0.md` 一并重读。本报告即该前轮同一审查方的修复验证轮。
- 审查对象：工作树未提交改动（基线 HEAD `dfafa9591a62f55ad784e72079c623b2c05079cb`，`git rev-parse` 实证）——R1 已审状态之上的第二轮修复增量。
- 审查方式：逐行 diff（4 hunk + 测试文件 4 hunk 全读）+ F-R1-01/F-R1-05 逐项独立复核 + **自建反相副本三路复现**（四形态矩阵在 %TEMP% 真实 plan 副本；RED→GREEN 用回退补丁引擎副本 revA/revB + 未打补丁对照 revC）+ 双判据边界探针 12 项 + 定向/全量/archguard 实跑。未触碰真实 `.governance/`。
- 环境事实（对后续轮次重要，新增两条 harness 陷阱）：
  ① （沿承 R1）unittest MUST 从仓库根运行；反相实验限 %TEMP% 副本。
  ② **%TEMP% 副本必须复刻 `skills/software-project-governance/infra` 布局并以副本根为 cwd 运行**——`_hot_fact_source_plugin_scope()`（verify_workflow.py L2012-2023）比较 HOST_PROJECT_ROOT（cwd 经 resolve_entry 派生）与 PLUGIN_ROOT（resolve_entry.py L11 `PLUGIN_HOME=__file__.parent.parent` → parents[2]）；布局/工作目录不一致 → 插件域断言静默休眠 → `check_hot_fact_source_consistency` 对虚报 fixture 返回 `issues=[]`（本审查首次 RED 实验即踩中，见 §5.4 披露）。flat 布局 + 仓库根 cwd = 断言全休眠的假通过/假失败混合面。
  ③ robocopy 同步副本时 size-differs 规则会覆盖已打补丁的目标文件——补丁必须在 robocopy **之后**写入（本审查实操教训）。

---

## 1. 改动清单核验 + 范围纪律

| 文件 | numstat（vs HEAD，R0+R1+R2 累计） | R2 增量核验 |
|---|---|---|
| `infra/verify_workflow.py` | +143/−102（物理行 24453，两种计数法实证；R1 为 +127/−102、24437） | 净 +16，全部落在 2 个已审区域内：helper `_hot_task_ids_for_version`（25→35 行，+10）与 F-R1-05 注释（+6）。**零越界改动 ✅**（4 hunk 头与 R1 完全同域：常量区 / helper / 主检查体） |
| `infra/tests/test_verify_workflow.py` | +358/−1（R1 为 +269/−1） | R2 增量 = **纯尾部追加 +89/−0**（L2034 节注释 + 2 个新测试，L2034-2120）；唯一被删行 `-        plan_version=None,` 为 R0 已记录的 fixture 签名变更，不在 R2 区域。16 既有 + 4 R1 用例零触碰 ✅ |
| `core/architecture-baseline.json` | 2/2（`git_head` 5e6d8c7→dfafa95、`anchor_loc` 24412→24453） | `--regen` 机械产物；R7 `committed==fresh True` 实证非手编 ✅ |

范围纪律：无顺带改动 ✅（`git status` 仅 3 文件 + 2 份审查报告 untracked；引擎 4 hunk 逐行复核无一越出 hot-fact 函数族）。

## 2. 前轮 findings 逐条比对表（复审必达）

| R1 ID | R1 级别 | 裁决 | 独立验证事实 |
|---|---|---|---|
| **F-R1-01**（released_face 被「任意格 token OR 累积」污染，探针 D 实证 5→1 逃逸） | P1 | **已修复 ✅** | ① 代码面：REL 行对 `release_declared/release_delivered` 的贡献收窄为双判据 `version_token_re.search(normalized[4]) or release_item_re.match(normalized[2])`（L1935-1937），`release_item_re = re.compile(r"[*\s]*发布\s*" + version_token_re.pattern)`（L1925，头部锚定 + 词界 lookaround 复用）；识别侧任意格召回保持（L1931-1934 未动）；docstring 同步改写（L1916-1921，与本轮修复一一对应）。② 行为面：四形态矩阵独立复现（§5.3）——D 形态 helper `delivered=False`、两条保护断言 FAIL 全部在场，不再逃逸。③ 测试面：负例测试 `test_fix339_r2_narrative_mention_in_delivered_rel_row_never_lifts_face` 入库，红→绿经**我自建的回退引擎副本**实证（§5.4：revA 复现与 Developer 声明逐字符一致的 RED 消息 `face-side: narrative mention must not accumulate release_delivered (ids=['REL-078', 'REL-077'])`；revC 对照全绿）。④ 边界面：12 项探针审查双判据可绕过面，全部符合声明语义或落在 fail-closed 方向（§5.2、§7 F-R2 备注） |
| F-R1-02（0.82.0 锚 3 条 missing-active 过报：FIX-335 假阳 / FIX-337 斜杠缩写 / FIX-341 真缺口） | P3 | **未修复（有意保留，方向性维持）✅ 如实** | C 形态矩阵中 3 条 missing-active FAIL 逐一复现（§5.3）；属已声明的 fail-closed 过报族，REL-078 prep 期消化的处置不变。D 形态新增的第 4 条 `missing active task REL-077` 为同一过报族的已声明后果（见 §3 重点①附注），非新缺陷 |
| F-R1-03（F-04 处置为声明面，CHANGELOG 措辞未落仓） | P3 | **未变（维持声明面）** | 本轮修复面不涉及发布文档；REL-078 发布文档期承载点不变 |
| F-R1-04（建议 Developer 自带相对上轮增量 hunk 摘要） | P3 | **部分响应** | Developer 本轮自带归因表（24437→24453 分解）——采纳了建议；但表中 1 行计数偏差（见 F-R2-01）。透明度诉求实质成立 |
| **F-R1-05**（L2119/L2133 stale-range 与 overview 检查 `version=active_version` 静默空转） | P3 | **已修复 ✅** | L2134/L2149 两处 `version=None`，注释块 L2129-2133/L2148 同步（「Recall-only：不放松完成判定，只恢复召回」与实现一致）；反相副本 revB（回退两处为 `version=active_version`）复现修前空转 RED：`stale-range check idled on 或后续 target row: FAIL missing in []`（issues 全空 = 检查静默无效的直接证据）；工作树 GREEN |

新引入 findings：**无 P0/P1**；2 条 P3 备注（F-R2-01/F-R2-02，均不阻塞）。

## 3. R1 §R2 复审重点四项逐项裁决

| # | 重点 | 裁决 |
|---|---|---|
| ① | D 形态必 FAIL/不抬 face，负例测试红→绿入库 | **成立 ✅**：四形态矩阵 D 行——`claimFAIL=True / overstateFAIL=True / helper(delivered)=(False)`，修复前该形态 issues 5→1 的逃逸形态不再出现（本轮回退副本 revA 实证修复前行为仍在）；负例测试红→绿经 revA/revC 对照实证。**附注（过报裁决）**：D 形态下识别召回使 REL-077 入 0.82.0 的 ids → 新增恰 1 条 `0.82.0 roadmap row missing active task REL-077`（total 7 vs C 的 6，与 Developer 声明逐位一致）——裁决为 **fail-closed 方向的已声明预期后果**：任意格召回是 F-01/F-05 修复的既定设计（识别宽度），其过报不产生虚报通路，且已被负例测试的 `assertIn("REL-077", ids)` 显式钉住为有意行为 |
| ② | C/A/B/主路径四形态不回归 | **成立 ✅**：C-intact（6 FAIL，claim+overstate 在场）/ A-rel-date（双判据经事项头形态 `发布 0.82.0` 救回，claim FAIL 保持，R0 E3 逃逸形态仍闭合）/ B-rel-absent（显式 `claims 已发布 but no delivered release task row corroborates it`）/ D-narrative（见①）；真实数据主路径 `check-hot-fact-source` = PASSED / EXIT=0，helper 直调 `0.81.0: declared=True delivered=True`（REL-077 经事项头形态识别——目标列为 `G9/G11`，双判据第 2 支生效）、`0.82.0: declared=True delivered=False`、`0.99.9: 0/False/False` |
| ③ | 红基线身份不变 | **成立 ✅（模块口径逐位一致）**：`Ran 825 tests in 239.132s FAILED (failures=1, errors=2)`——823+2 ✓；3 红身份与 R0/R1/声明逐一一致：FIX300DualCaliber ERROR `test_fixture_identity_mode_agrees_with_engine_on_present_sources` + FIX300 FAIL `test_identity_host_source_drift_reproduces_divergence_shape` + LoopRuntimeClaimAdapter ERROR `test_claim_command_emits_complete_pass_report`。**LoopRuntimeClaimAdapter 的 ERROR/FAIL 计时面归因核实**：本轮 ERROR traceback 为 `subprocess.TimeoutExpired ... check-loop-runtime-claims ... timed out after 15 seconds`——该测试对完整 CLI 启动设 15s 超时（test L45-50 `timeout=15`），负载下超时即 ERROR、按时完成但报告失配即 FAIL；同一方法在 R0(ERROR)/R1(FAIL)/R2(ERROR) 间翻转 = 环境计时面，非产品回归 |
| ④ | R1-R7 全绿 + 行数变化重锚归因 | **成立 ✅**：`[R1] PASS mainfile loc 24453 ≤ anchor 24453 (only-down)`、R2 47≤47、R3 PASS、R4 1299≤1299、R5 84/84+71/71、R6 INFO cold import 196 (Δ0)、R7 `regen deterministic=True; committed==fresh True`；Result: PASS (0 violations) EXIT=0。归因核验见 §5.5：净 +16 算术精确成立，附 F-R2-01 归因表 1 行计数偏差备注 |

## 4. 逐维度裁决（5 维全覆盖）

| 维度 | 裁决 | 依据 |
|---|---|---|
| 正确性 | **PASS** | 双判据语义与实现逐字符一致；`release_item_re` 头部锚定（`[*\s]*发布\s*` + 复用词界 lookaround）经 12 项边界探针验证：抬 face 仅两条通路（目标列锚 token 精确/或后续；事项格 `发布 <anchor>` 头形态），叙事格/依赖格/状态格/多版本串/前缀渗透一律不抬（§5.2）；`version=None` 语义正确（召回-only，完成判定不放松——revB 反相实证）；fail-closed 显式 FAIL 分支未动 |
| 安全性 | PASS | 无新输入面：版本锚仍源自 `[0-9]+(?:\.[0-9]+){2}` 捕获，`re.escape` 转义保持；`release_item_re` 的 token 部分继承同一转义正则；只读本地治理文件；正则无灾难回溯形态（`[^。\n|]*` 边界未动，新正则为线性匹配） |
| 回归风险 | PASS | 定向 22/22 OK；全量（模块口径）825/3 红身份逐位一致；真实数据 PASSED；16+4 既有用例纯追加保护（§5.6）；R1-R7 全绿 |
| 测试质量 | PASS | 2 个新测试均 tempfile + 真函数调用、无 mock/自证；断言同时钉住「召回保持」（`assertIn REL-077 in ids`）与「face 不抬升」（`assertFalse(delivered)`）+ 两条保护 FAIL 在场——把 F-R1-01 的修复语义与其设计意图（识别/面分离）一起锁死；stale-range 测试以「或后续」行 + 依赖链待闭环行构成最小复现；两测试均经反相副本验证红→绿 |
| 可维护性 | PASS | helper docstring 与实现一致（含 R1 报告指针与「bare mention never lifts」语义声明）；F-R1-05 注释解释「同 F-02 口径」可追溯；双正则登记注释（R1 F-03）未被破坏；行数 +16 全部为修复必需面 |

## 5. 独立复现原始输出（关键行）

### 5.1 定向套件（仓库根运行）
```
Ran 22 tests in 0.077s  OK   EXIT=0     （16 既有 + 4 R1 + 2 R2）
class HotFactSourceConsistencyTests test 方法计数 = 22（脚本实证）
```

### 5.2 helper 直调（真实 plan-tracker）+ 双判据边界探针（中性最小 plan，B 系列）
```
anchor=0.81.0 total_ids=25 rels=['REL-077'] declared=True  delivered=True   ← 主路径（事项头形态救回 G9/G11 错位）
anchor=0.82.0 total_ids=5  rels=['REL-078'] declared=True  delivered=False
anchor=0.99.9 total_ids=0  rels=[]           declared=False delivered=False
wb-neg(0.810 行 vs 0.81.0 锚): FIX-999 in ids = False                  ← 词界守卫无前缀渗透（R1 行为保持）
B1 head-bold **发布 0.81.0**, target=date    : declared=True  ← 头形态+粗体+目标列错位 = 救回通路（REL-077 实形态）
B2 no-space 发布0.81.0                      : declared=True  ← \s* 零宽可匹配（该行文即发布声明，方向无害）
B3 fullwidth-space 发布　0.81.0              : declared=True  ← Unicode \s
B4 other-verb-first 拟发布 0.81.0, target=—  : declared=False ← 非「发布」头形态不抬 face
B5 head+multi-ver 发布 0.81.0，后承 0.82.0, target=0.81.0, a=0.82.0 : declared=False ← 多版本串归属本版本
B6 同行, a=0.81.0                           : declared=True  ← 本版本行正常抬升
B7 prefix渗透 发布 0.81.01                  : declared=False in_ids=False ← lookaround 阻断
B8 narrative-not-head 备注：发布 0.81.0       : declared=False ← 非头部锚定不抬 face
B9 head-or-later 发布 0.81.0 或后续, target=— : declared=True  ← 头形态+或后续（与 R0 F-05 既定或后续约定同族，残余薄风险见 §7 注）
B10 D-micro 自版本行叙事提及 0.82.0, a=0.82.0 : declared=False in_ids=True ← 召回保持 + face 不抬（F-R1-01 微缩复现）
B11 裸 token 仅在依赖格                      : declared=False ← 任意非目标/非头格不抬 face
B12 全角冒号 发布：0.81.0                    : declared=False ← 变体不识别 → 过报方向（fail-closed），P3 备注
（另：P7 target=或后续 + 事项格他动词「推进 0.82.0 收尾」→ declared=True delivered=True —— 目标列判据独立生效，
  验收点「事项格以其他动词开头但目标列为或后续形态的组合覆盖」成立）
```

### 5.3 四形态反相矩阵（%TEMP% 真实 plan 副本：锚 0.81.0→0.82.0 + roadmap 0.82.0 行改「已发布（模拟提前虚报）」）
```
RESULT C-intact   : total=6 claimFAIL=True  nocorrFAIL=False overstateFAIL=True rel077missing=False helper(delivered,declared)=(False,True)
RESULT A-rel-date : total=6 claimFAIL=True  nocorrFAIL=False overstateFAIL=True rel077missing=False helper=(False,True)   ← 双判据经事项头形态救回
RESULT B-rel-absent: total=6 claimFAIL=False nocorrFAIL=True  overstateFAIL=True rel077missing=False helper=(False,False)  ← 显式无佐证 FAIL
RESULT D-narrative: total=7 claimFAIL=True  nocorrFAIL=False overstateFAIL=True rel077missing=True  helper=(False,True)
    D 的第 7 条 = 0.82.0 roadmap row missing active task REL-077（识别召回的已声明过报）
C 的 6 条明细：must not claim 已发布 / project overview missing active version 0.82.0 / overstate / missing FIX-335 / FIX-337 / FIX-341
```
（如实登记：R1 期 C 形态 total=5（由 R1「5→1」反推），本轮 C=6；差额为 `project overview missing active version 0.82.0` 在场——该检查行为 R0 前既有代码（L2103-2105，不在本轮 diff），且今天的 plan-tracker 概览面相对 R1 审查时点已被修复轮数据更新（gitignored 活数据）→ 判为活数据漂移面，非引擎回归。见 F-R2-02。）

### 5.4 RED→GREEN 反相实验（%TEMP% 回退补丁引擎副本，复刻仓库布局 + 副本根 cwd，revC 对照）
```
revC（未打补丁对照，fixed 引擎）  : Ran 2 tests OK, EXIT=0
revA（回退 F-R1-01 → R1 OR 累积）  : FAILED (failures=1)
    AssertionError: True is not false : face-side: narrative mention must not accumulate release_delivered (ids=['REL-078', 'REL-077'])
    ← 与 Developer 声明的 RED 消息逐字符一致
revB（回退 F-R1-05 → version=active_version）: FAILED (failures=1)
    AssertionError: False is not true : stale-range check idled on 或后续 target row: FAIL missing in []
    ← issues 全空 = 修前检查静默无效的直接证据
```
harness 披露：首次反相尝试采用 flat 布局 + 仓库根 cwd → 插件域断言休眠（`_hot_fact_source_plugin_scope()` 判 False）→ 观察到 `issues=[]` 的假失败形态；复刻布局后三副本结果如上。该陷阱已记入头部环境事实②。

### 5.5 全量套件（模块口径 = R0/R1 基线口径 `-p "test_verify_workflow.py"`，仓库根运行，单独跑）
```
Ran 825 tests in 239.132s  FAILED (failures=1, errors=2)      ← 823+2 ✓
ERROR: …FIX300DualCaliberAgreementTests.test_fixture_identity_mode_agrees_with_engine_on_present_sources
FAIL:  …FIX300DualCaliberAgreementTests.test_identity_host_source_drift_reproduces_divergence_shape
ERROR: …LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report
   → subprocess.TimeoutExpired: … check-loop-runtime-claims … timed out after 15 seconds  ← 计时面实证
```
**口径披露（重要）**：全仓 discover（默认 `test*.py`，31 个文件级模块）= `Ran 3112 tests … FAILED (failures=34, errors=2, skipped=1)`，其中模块外新增红全部位于**零 diff 参与**的模块（test_hooks replay ×6 子测试 / test_pre_commit_review_evidence ×~25 子测试 / test_change_triage / test_loop_runtime_claims ×2）——这些测试的输入 = gitignored 活数据（plan-tracker/evidence-log，修复轮内被数据更新）+ 未变更的 hooks/triage/loop 代码，反事实与 HEAD 树逐位相同 → 判活数据面/环境面，**非本次 3 文件改动所致**。R0/R1 的「全量」口径即模块口径（819/823/825 递增与本模块用例数递增精确对应），基线声明在该口径下成立；建议后续轮次统一以「模块口径」声明全量（F-R2-02）。

### 5.6 定向 22 用例无弱化专项
- R2 对测试文件的净贡献 = **纯尾部追加 +89/−0**（numstat 269/1 → 358/1 差分 + 唯一删除行归属 R0 区域实证）；16 既有 + 4 R1 用例逐意图在位（4 个 R1 测试 L1930/1965/1994/2016 原样；R1 §5.6 的断言未动结论继续有效）。
- 新测试 1 断言结构：`assertIn(REL-077, ids)`（召回保持）→ `assertFalse(release_delivered)`（face 不抬）→ `assertTrue(release_declared)` → 两条保护 FAIL 在场——比 R1 建议的「1 条负例」更强：同时钉住识别面与面分离语义。
- 新测试 2：`或后续`目标行 + 依赖链「待闭环」行最小复现 F-R1-05 空转形态，断言 FAIL 在场。

### 5.7 archguard 重锚 24453 归因核验
```
[R1] PASS mainfile loc 24453 ≤ anchor 24453 (only-down) | [R7] PASS regen deterministic=True; committed==fresh True
净 +16 算术核验（终态树逐段实测）：helper 25→35 行（docstring 9→16 = +7；release_item_re 新行 = +1；REL 条件 1→3 行 = +2）
  + F-R1-05 注释（L2129-2133 五行 + L2148 一行 = +6）+ 两处 version=None 为原位改写（0 净）＝ +16 精确 ✓
Developer 归因表：docstring +7 / release_item_re +1 / REL 条件 +3 / F-R1-05 注释 +6 = 合计 17 ≠ 净 +16 → 见 F-R2-01
```

## 6. AI 专项 5 项检查（R2 增量面）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无——2 个新测试 tempfile + 真函数调用，零 patch/mock |
| 2 | 硬编码返回值 | 无——断言全部数据派生；fixture 内嵌版本串均为测试语义所需 |
| 3 | 幻觉 API | 无——新增引用逐一读实现核实：`release_item_re`（L1925 新增且被 L1936 消费）；复用符号 `_markdown_table_cells`/`_normalize_markdown_cell`/`_status_cell_is_delivered` 为 R0/R1 已核实存量 |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 无——改动严格限于声明面（双判据收窄 + 2 处 version=None + 2 测试）；「识别侧召回保持」为已声明设计并经测试显式钉住，非静默超实现 |

## 7. Findings

| ID | 级别 | 位置 | 问题 | 事实依据 | 处置建议 |
|---|---|---|---|---|---|
| F-R2-01 | P3 | Developer 修复声明（归因表）；无代码影响 | 重锚归因表内部合计 +17 与已验证净 +16 差 1：`REL 条件 +3` 实测为 +2（R1 单行 `if normalized[1].startswith("REL-"):` → 现 3 行条件头，函数体 2 行未动）；净 +16 本身声明正确 | §5.7 算术核验；helper 25→35 行 | 记录更正即可，无需代码变更；下轮报告归因表按 hunk diff 生成避免手计偏差 |
| F-R2-02 | P3 | 流程/环境口径 | ① 「全量」口径在 R0/R1 声明中实为模块口径（`-p "test_verify_workflow.py"`），全仓 discover 口径（3112 用例）下存在一批与本次 diff 无关的活数据面红（hooks replay / review-evidence regex / triage CLI / loop-claims inventory）——口径不固定易造成「红基线身份」误比对；② 活数据（plan-tracker 概览面）在修复轮内被更新，使 R1 期 C 形态 total 5 → 本轮 6，数据面变更未入 diff，跨轮对比需口径感知 | §5.5 两口径原始输出；diff 文件清单（3 文件）；被红模块均零 diff 参与 | 后续任务书固定「全量 = 模块口径」措辞；全仓口径红如需收敛另立任务（活数据测试与 gitignored 数据耦合是 FIX-328 已知风险族的延续） |
| —（备注，非 finding） | P3 | `release_item_re` 头形态边界 | 两处已核实无害残余：`发布：0.81.0`（全角冒号）不识别 → 过报方向（B12）；`发布 0.81.0 或后续`头形态按或后续约定抬 face（B9）——残余虚报通路需要「发布任务实际跳版」+「自版本行自称已发布」同时成立的薄组合，与 R0 F-05 以来既定或后续约定一致 | §5.2 B9/B12 | 随下次触碰该函数族时顺带评估；不构成本轮修改义务 |

## 8. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| P1 关键数 | **0** → unresolved_blockers = **0** |
| 5 维度覆盖 | 100%（§4） |
| 每条发现标注级别 | 100%（§7 + §2 比对表） |
| 设计一致性 | 与 DEC-195 方案 (a) 及 R1 报告修复建议（面侧收窄「目标列+事项头双判据」+ 1 条负例测试）逐项一致；docstring 声明语义与实现一致（R1 F-R1-01 的「实现弱于声明」偏差已消除） |
| AI 专项 5 项 | 全部完成（§6） |
| 复审必达 | 前轮 findings 逐条比对（§2）；round=2 声明 + prev 引用（头部）；round=2 无 blocking → 不触发 BLOCKED 升级路径 |
| 破坏性红线 | 不适用已遵守——纯仓库内只读审查 + %TEMP% 副本反相实验，未触碰真实 `.governance/` |

## 9. 结论

**APPROVED_WITH_NOTES（round=2，unresolved_blockers=0）——通过终态。**

R1 唯一阻塞项 F-R1-01 的修复经三路独立验证成立（四形态全栈矩阵 / 回退引擎 RED 消息逐字符复现 / 12 项双判据边界探针），F-R1-05 同样成立（空转空 issues 的 RED 形态复现）；四项 R2 复审重点全部成立；825/3 红身份逐位一致且 LoopRuntimeClaimAdapter ERROR 的计时面归因有 traceback 实证；重锚 24453 算术精确、R7 证实为 regen 产物；范围纪律与 AI 专项全部通过。两条 P3 备注（F-R2-01 归因表计数更正、F-R2-02 全量口径固定建议）均不阻塞合并，随下版任务书或文档批次消化即可。

**（通过终态，无 R3 复审重点；如后续轮次触碰同一函数族，建议关注 §7 备注中两处头形态边界的处置。）**
