# FIX-442 Code Review R0 — DSH preset 冒烟并发写入容忍度（28u 假阳性修复）

- **Task ID**: FIX-442（P1，user-named；plan-tracker L81）
- **审查轮次**: R0（首轮）
- **审查对象**: 工作区未 commit 变更（HEAD `42ddbca` 之上）
- **Reviewer**: Code Reviewer Agent（独立审查；只读 + 报告落盘，未修改任何代码/测试/治理记录）
- **日期**: 2026-10-10
- **审查规范**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`

---

## 1. 结论

**APPROVED_WITH_NOTES**

- `unresolved_blockers=0`（P0=0，P1=0；仅 P2×1 + P3×5，均不阻塞）
- 安全语义核心结论（本票最高优先审查面）：**归因判定不构成隔离语义放宽**。governance 自有面（`<preset_id>/` 与 `<preset_id>.staging-*`）在条目语义因子上被严密排除——`adapter_write_face_entry` 对 relpath 不可解析条目返回 True（计为自有面，fail-closed 方向），对自有面前缀命中返回 True，归因函数随即返回 False（保持 FAIL）。双因子为真正 AND：`window is None or preset_id is None` 短路 False；出现型条目 mtime 缺失/不可解析/窗口外均 False；「both/neither」防御分支 False。三级红测（自有面单元级 FAIL / 自有面 gate 级 FAIL / 引擎拒收 PASS+writes≥1）全部复现通过。
- 引擎职责边界正确：引擎不重判归因，只解析 `attributed concurrent writes : N` 并披露；PASS 拒收逻辑（`real-home writes not in (0, None)` → 拒收）与 FEAT-040 不变量逐字保持，且有引擎侧红测。

---

## 2. 发现列表

### P2-1（闭环台账面）：quality_budget performance 维度的墙钟对照证据未见载体
- **位置**: `.governance/execution-packets.json` packets.FIX-442 quality_budget.performance（"28u 冒烟墙钟不劣化……dev 完成时墙钟对照落 EVD 行"）
- **事实**: 本 diff 无墙钟守护用例；incident log（`.governance/incidents/FIX-442-r4-command-log.log`）第 14 项仅 UX 面单次 CLI 实跑，无 before/after 墙钟对照。归因计算本身为 O(Δ 条目) 级（Reviewer 实测 dsh 族 86.1s vs Developer 日志 93.8s，噪声级），无实际性能疑虑。
- **建议**: Coordinator 收口时在 EVD 行补墙钟对照（或按 packet exception 语义显式豁免），不阻塞代码合并。

### P3-1（加固建议）：`preset_id` 空串理论洞
- **位置**: `adapters/dsh/smoke_attribution.py:175`（`if window is None or preset_id is None: return False`）与 `:138`（`top == preset_id or top.startswith(preset_id + ".staging-")`）
- **事实**: 若 host-contract.json 将 `own.preset.id` 声明为空串，`_fact` 正常返回 `""`（它只对路径缺失抛异常、不校验空值），此时 `adapter_write_face_entry(entry, "")` 对一切真实条目返回 False → 自有面可被归因排除。当前不可达（契约自检/dsh 渲染对空 preset id 会先崩溃），但一行 `or not preset_id` 即可闭合。
- **建议**: 后续票顺手加固，非本票义务。

### P3-2（残余风险披露，契约已接受）：foreign 面隔离逃逸可被归因掩盖
- **位置**: `adapters/dsh/smoke_attribution.py:141-189`（`attribute_concurrent_write`）
- **事实**: 双因子无法区分「并发会话写自己的 novel-writing 面」与「被测隔离会话逃逸后写 foreign 面路径」——两者都落在窗口内 + 自有面之外，区分完全依赖「本 adapter 代码不存在写 foreign preset id 的路径」这一前提（今日成立：所有写路径经 `preset_dir()/_fact("PRESET_ID")`）。这正是 execution-packet assumption_record 预登记并经红绿测试验证的取舍（宁可保守误报不放走越界——注意此残余方向是「放走」的理论面，但仅限 `.agent-presets/<foreign>/…`；top-level 名单变化与自有面变化仍 FAIL）。
- **处置**: 无需动作；记录在案供 FEAT-094（审查可信链）演进时参考。

### P3-3（测试缺口，非阻塞）：三处同路径未直测
- **位置**: `skills/software-project-governance/infra/tests/test_dsh_adapter.py` FIX-442 块
- **事实**: ①纯消失（并发会话删除 foreign 条目、无出现对应物）未直测——`elif before_held and not after_held` 分支已被 `test_fix442_inplace_sibling_rewrite_is_fully_attributed` 的旧串半边覆盖；②foreign staging 目录名（`novel-writing.staging-*`）归因未直测；③窗口边界 inclusive（mtime == start/end_ns）未直测。三者均为已测代码路径的变体。

### P3-4（声称与实际核对，无实质不一致）
- **事实**: ①任务声称测试路径为 `tests/test_dsh_adapter.py`——实际 `skills/software-project-governance/infra/tests/test_dsh_adapter.py`（简写，同文件）；②声称 A `.governance/incidents/FIX-442-r4-command-log.log`——该路径被 `.gitignore:10`（`.governance/`）忽略故不出现在 git status，盘上存在（6230B，2026-10-10 14:45）；③声称 launch.py 拆分后 1884 行——实测 1884 行 ✓；④manifest glob 计数 1062→1063 未独立复算，由 check-governance 内 check-manifest-consistency [PASS] 间接证实；⑤STATIC_PIN_EXEMPTIONS「4 行重锚」实测 4 tuple、全部 +97（20573→20670 / 20576→20673 / 21071→21168 / 21103→21200），新行号逐一落在版本 token 上（21168/21200 = `check_release_readiness(version="0.93.0")`；20670/20673 = FEAT-081/082 fixture 行含 0.94.0），旧行号已无 token——重锚如实。

### P3-5（可复现性观察）：并行负载下 dsh 族首跑 1 失败、未复现
- **事实**: Reviewer 首次运行 dsh 族（与全套件后台并行，2×CPU 竞争）：`Ran 411 tests ... FAILED (failures=1)`，失败用例名因输出截断未捕获；隔离复跑（-v 全量落盘 `%TEMP%\fix442-dsh-family.log`）：`Ran 411 tests in 86.101s OK`。结论：存在并行负载下的时序敏感用例（未能定位是否属本票新增面——本票 12 用例在两次运行中均绿）。Developer 可靠性预算仅对 fix442 子集做了 3 连跑。建议后续把「与全套件并行跑 dsh 族」纳入 flake 排查习惯。

---

## 3. 验收①~④对照（plan-tracker L81 / execution-packet done_definition）

| # | 验收项 | 判定 | 一手证据 |
|---|--------|------|---------|
| ① | 并发写入场景测试（模拟活跃会话写真实 home→冒烟不误报） | ✅ | `test_fix442_smoke_tolerates_concurrent_session_write`：mid-smoke 注入 novel-writing 写入 fake real home → exit 0 / `Result: PASS` / `real-home writes : 0` / `attributed concurrent writes : 2` + ADVISORY。单元级另有两例（出现型/原地改写型）。Reviewer 复跑 8/8 OK |
| ② | 真实越界写入仍 FAIL（安全语义不变） | ✅ | 三级红测：单元级 `test_fix442_adapter_own_face_delta_is_never_attributable`（窗口满足仍 FAIL）+ gate 级 `test_fix442_smoke_still_fails_when_concurrent_write_hits_adapter_face`（同注入改打 governance 面 → FAIL / writes: 1 / attributed: 0）+ 引擎级 `test_pass_with_non_attributed_real_home_writes_is_refused`。均复现通过 |
| ③ | dsh 族测试全绿 | ✅ | test_dsh_adapter + test_dsh_doctor + test_dsh_compat + test_dsh_contract：`Ran 411 tests in 86.101s OK`（含 K-2 契约扫描；见 P3-5 并行负载注记） |
| ④ | 全套件回归零退化 | ✅ | 全量 test_verify_workflow.py EXIT=0；loader 独立计数 `collected: 1088` = 1084+4 ✓ |

---

## 4. 硬门槛复现（Reviewer 独立执行）

| 声称 | 复现结果 |
|------|---------|
| ① 全套件 1088=1084+4 EXIT 0 | ✅ EXIT=0（后台全量实跑）；计数经 `loadTestsFromModule.countTestCases()` 独立复算 = 1088 |
| ② check-governance exit 0（Coordinator 已闭环 Check 34 先在项，当前 [PASS]） | ✅ `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only` → `Governance: [PASS]`，EXIT=0（与 Developer 日志时点「1 issues（先在 Check 34）」+ Coordinator 后续闭环的叙事链一致） |
| ③ dsh 族 411 tests OK | ✅ `Ran 411 tests in 86.101s OK`（P3-5：并行首跑 1 失败未复现） |
| ④ 隔离不回退三级红测 | ✅ 三级（单元/gate/引擎）逐一复跑通过（见 §3②） |

附加复现：定向 `-k fix442` 8/8 OK、`-k Fix442` 4/4 OK；git status/diff 逐文件实读（8 文件声称 vs 7 个 git 可见 + 1 个 gitignored 治理例外路径，全量 diff 416+/116- 逐行读毕）。

---

## 5. 审查重点专答（本票特有面）

1. **归因不构成隔离放宽（最高优先）**：见 §1。补充论证——`write_surface` 基准为 `<home>/.agent-presets` 递归指纹（launch.py:952-988），故 `entry_relpath` 首段恰为 preset 目录名，`top == preset_id or top.startswith(preset_id + ".staging-")` 与安装路径 `preset_dir()/PRESET_ID` 及 staging 原子替换名逐一对应（launch.py:403/764）；`_fact` 对契约缺失/畸形抛 `ContractMalformed`（launch.py:248-273，绝不静默回退），故 preset_id 注入面 fail-closed。top_level 名单变化不经归因、维持 D-54 复现即 FAIL——修复面严格限于写面 diff（scope_guard 遵守）。
2. **时间窗因子正确性**：`window_start_ns` 取于 before 采样前、`window_end_ns` 取于 after 采样后（launch.py:1512-1574），窗口严格包夹双采样与被测隔离会话。TOCTOU 分析：窗口前写入若被 before 遍历捕获→非 delta；若因遍历顺序漏采→mtime < start_ns → 保守 FAIL（正确的 fail-closed 方向）。after 采样后写入不可见于 delta（窗口外，本就不属判定范围）。消失型「构造性区间包含」论证成立：条目字符串在 before 样本中实测在场、after 样本中实测缺场，删除/改写时刻被两次采样直接界定，无需 mtime 佐证（原地改写产生的新旧两串分别走出现/消失路径，`test_fix442_inplace_sibling_rewrite_is_fully_attributed` 验证两半均归因）。mtime 与 time_ns 同机同钟（NTFS 100ns 粒度），显式回拨 mtime 只会把条目推出窗口→保守 FAIL。
3. **引擎与 adapter 职责边界**：引擎新增面仅解析正则 `DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE`（verify_workflow.py:7144-7145）+ isolation 字段 + reason 如实化 + box/CLI 披露；PASS 拒收分支逐字未动（`real-home writes not in (0, None)` → "refusing to accept"）。adapter 谎报 PASS 且 writes≥1 时引擎拒收有红测；adapter 谎报 writes=0 本身引擎无法独立察觉——该信任边界为 FEAT-015 既有模型、非本票引入亦未恶化（FEAT-094 审查可信链为其演进方向）。reason 如实化无隐瞒：attributed N>0 时在 PASS reason、Check 28u box、CLI 摘要三处披露，措辞由「real ~/.dsh untouched」收窄为「untouched **by the smoke**」+ 归因说明——信息增量单调不减。
4. **拆分纯粹性**：`smoke_attribution.py` 286 行纯判定机——全文仅 `os`/`pathlib` 导入，零契约读取（preset_id 参数注入，K-2 单源纪律；dsh 族含契约外字面量扫描实测通过）。`home_fingerprint` 逐字迁移（diff 比对确认）；launch 侧保留薄包装（`witness_verdict` 注入 `_fact("PRESET_ID")`，`window=None` 默认保遗留语义）。旧 `witness_deltas` 在 launch.py/测试中零残留引用；全部遗留调用方（dsh_fixtures.py:284、test_dsh_compat.py:2377/2390、旧 adapter 用例）不带 window → 归因禁用 → 行为等价（dsh 族 411 全绿佐证）。`_smoke_attribution()` 的 sys.path 懒插入镜像既有 `_fact` 模式，带重复插入守卫。STATIC_PIN_EXEMPTIONS 重锚与 manifest glob 同步核实如实（见 P3-4④⑤）。
5. **测试质量**：12 用例真验证行为——断言面为 verdict/failures/输出行（输出行即引擎正则契约，非实现细节）；gate 级用例走真实 `smoke_preset()` 全流程（patch 仅限 env/home 指向/注入钩子三个接缝）。缺口见 P3-3。
6. **D4 纯粹性**：见 §6。

---

## 6. D4 纯粹性（修改面穷举核对）

git diff 全量 = 8 文件，逐一归类：

| 文件 | 归类 |
|------|------|
| `adapters/dsh/launch.py`（157 行变更） | 本票判定面接线 + 28n 预算驱动的内聚拆分（incident log 第 8 项：拆分前 2092 行超 warn_lines 2000，FIX-435 先例路径；除归因面外零漂移，遗留调用方行为等价） |
| `adapters/dsh/smoke_attribution.py`（新增 286 行） | 判定面本体 |
| `skills/.../infra/verify_workflow.py`（59 行变更） | 引擎面：全部 hunk 限于 check_dsh_preset_smoke/28u box/CLI——无其他 Check 逻辑被触碰 |
| `skills/.../infra/checks/version.py`（12 行变更） | 机械连带：4 行重锚 + 注释（FIX-421 纪律） |
| `skills/.../core/manifest.json`（+1 行） | 机械连带：新模块 glob（check-manifest-consistency [PASS]） |
| `skills/.../infra/tests/test_dsh_adapter.py`（+206 行） | +8 用例 |
| `skills/.../infra/tests/test_verify_workflow.py`（+97 行） | +4 用例（同时是 +97 行锚漂移的直接原因，与 version.py 重锚互为因果闭环） |
| `.governance/incidents/FIX-442-r4-command-log.log`（gitignored） | 任务许可例外路径（R4 命令日志） |

`test_dsh_doctor.py` 零改动理由成立：doctor 为只读展示面，不消费 `witness_verdict`/`_home_fingerprint`/`smoke_attribution`（git grep 零命中、diff 空）。无无关重构、无版本 bump、无 fixture 漂移。

---

## 7. 五维度结论 + AI 专项 + 硬门槛自查

| 维度 | 结论 |
|------|------|
| 正确性 | 通过——双因子 AND 逻辑/窗口时序/消失型构造性论证/防御分支逐行核验（§5.1/5.2）；边界（不可解析 relpath/mtime、both/neither、window=None、preset_id=None）全部保守方向 |
| 安全性 | 通过——隔离语义不回退（三级红测）；指纹仅 lstat 元数据、零内容读取保持；无注入面（纯内部判定）；fail-closed 全路径成立 |
| 可维护性 | 通过——归因判定内聚单函数（quality_budget maintainability 达标）；命名自释；文档锚充分（模块 docstring + 包裹层委托说明）；launch.py 1884 < 2000 |
| 性能 | 通过（附注）——O(Δ) 增量，实测噪声级；墙钟对照证据载体待 EVD 闭环（P2-1） |
| 测试覆盖 | 通过（附注）——12 用例覆盖三类红绿 + gate 级端到端 + 引擎四面向；缺口 P3-3 非阻塞 |

AI 专项 5 项：mock 残留 无（patch 全部上下文管理器内闭合；fake_launcher 写于 `_governance_temp_dir` 清理域）；硬编码返回值 无；幻觉 API 无（全部标准库真实接口）；未实现 TODO 无；过度实现 无（拆分由 28n 预算强制触发且为最小内聚切分）。

硬门槛自查：P0=0 ✓；5 维度 100% 覆盖 ✓；每条发现带级别 ✓；设计一致性（execution-packet assumption_record + plan-tracker L81 修复面）比对完成 ✓；AI 专项 5/5 ✓。

---

## 8. 复审提示（如Coordinator后续转R1）

本报告为零阻塞终态建议（AWN/0），无需返工。P2-1 属收口台账项，P3×5 属记录性发现。若 Coordinator 选择补 P3-1 加固或 P3-3 用例，属独立小改，不必重开本票审查链。
