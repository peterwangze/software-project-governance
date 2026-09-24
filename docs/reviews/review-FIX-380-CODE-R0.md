# Review: FIX-380 — P3 杂项包（代码审查 · R0）

> **结论：APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 · P1=0 · P2=0 · P3=3**
>
> | 字段 | 值 |
> |---|---|
> | Task | FIX-380（P2 票面承载 P3 杂项——三项：2 落地 + 1 归类不适用） |
> | 轮次 | R0（首次审查） |
> | 审查对象 | 工作树未 commit diff：3 文件 +31/−43（`git diff --numstat` 实测：test_verify_workflow.py 24+/40−、version.py 6+/2−、version-projections.json 1+/1−，与申报一致） |
> | 审查方法 | 逐行 diff + 程序化函数体比对（去缩进归一化）+ JSON 机比（非 reason 字段深比较）+ 锚点实读（新旧 4 行）+ rot-guard 机制级直调验证 + 套件/verify 全量复现 + 前轮审查依据（REVIEW-FIX-374 F-4 / REVIEW-FIX-378 N-1·N-2·E-1）溯源 |
> | 结论性质 | APPROVED_WITH_NOTES 仅表示硬门槛通过，不替代测试或发布审查 |
> | 独立结构字段 | **unresolved_blockers=0** |

---

## 0. 审查输入与事实基线

- 治理状态：`.governance/plan-tracker.md` 已读——维护与演进阶段（G11 passed），always-on × maximum-autonomy；本审查为 sub-agent 只读任务，唯一输出为本报告。
- diff 范围实测：`git status --porcelain` = 仅 3 个 M 文件，无未跟踪/未申报文件 → **产品行为面（verify_workflow.py 引擎本体）未被触碰**——三项变更均为测试基建立面（item1）、声明披露面（item2）、豁免账本面（item3）。
- 申报验证基线：evidence-log 现仅 `TRIAGE-FIX-380`（L2565，机录）一行；Developer 验证数字以任务简报为载体，本报告全部独立复现（§4），未采信未经复现的申报。

---

## 1. 五维度审查结论

### 维度 1：正确性 — ✅ 通过

**item1（`_format_issues` 三副本提取为模块级单源）— 零行为差声明成立。**

| # | 检查项 | 方法与实测 | 裁定 |
|---|--------|-----------|------|
| 1 | 单源函数体与原副本逐字一致 | 程序化比对：HEAD 三方法体（def 位于 L12071/L12145/L12243，与 review-FIX-374 F-4 所列逐字吻合）× WT 模块函数体（L12053，docstring 后 9 行）——原始字节级不等（缩进 8→4，方法→模块提取的机械必然后果）；**去缩进归一化后三副本全部逐字一致（True×3）** | ✅（措辞精度见 F-1） |
| 2 | 7 调用点完整性 | diff 呈现 7 处改指，grep 实测 WT 调用点恰 7 行：L12095/12105/12115/12180/12246/12258/12267；全仓 grep `self._format_issues` **零残留**（仅命中历史记录 `docs/reviews/diff-FIX-372.patch` 与 test_change_triage.py 自有实现） | ✅ |
| 3 | 同名不同源边界 | test_change_triage.py L1465 `def _format_issues(self):`——**零参签名**，函数体为 `import verify_workflow as vw`（lazy）+ `patch.object(vw, "GOVERNANCE_DIR", self.gov)` + `vw.check_agent_locks_format()`（agent-locks 格式域，非 evidence-format 域）；语义、签名、源均与被提取 helper 不同，且该文件不在本 diff 触碰面（3 文件申报面外零改动） | ✅ 不触碰正确 |
| 4 | 提取语义安全 | 被删方法体从不引用 `self`/类状态（9 行体全部为局部变量 + `vw` 全局引用）；`Path`/`patch`/`vw` 均为模块级导入（test_verify_workflow.py L25-30 实测在位）；模块函数不拾取 pytest collection（非 `test_` 前缀）；静态 `def test_` 计数 929 = pytest 实际收集数（零动态生成、零收集丢失） | ✅ |

**item2（fixture-engine 条目 reason 追加 FIX-380 注记）— 纯追加声明成立，注记事实吻合。**

- **JSON 机比**（HEAD vs WT 解析后深比较）：非 reason 字段差集为空（`strip(old)==strip(new)` → True）——顶层六键（schema_version/authority/validation_inventories/projections/declared_legacy_snapshot_scope/declared_legacy_snapshots）全等，即申报的「projections/authority/snapshots 全等」成立；reason 字段差集**恰好 1 处**（`/declared_legacy_snapshots[0]/reason`），且 `b.startswith(a)` = **纯追加**，追加文本与 diff 呈现一致。
- **backport 事实一致性**（副本实读 `project/e2e-test-project/.../verify_workflow.py`）：L6857 docstring「FIX-378 (backport of the FIX-373 fix into this declared legacy snapshot)」——溯源披露位置与注记声明一致；L6887 `if ch == '"' and not in_code_span:`——quote-entry guard 实存且为 `not in_code_span` 门控，与注记描述逐点吻合。
- **「exactly one intentional, documented defect backport」**：与 review-FIX-378-CODE-R0 E-1 裁决（L60「副本现于 1 个行为点 + docstring 跟踪 canonical」）一致，声明有前轮审查事实源支撑。
- **N-1 落地对账**：review-FIX-378 N-1（L76）建议「顺带在 reason 追加一行 backport 注记（如『L6887 守卫为 FIX-378 定点 backport，见副本 docstring』）」——本注记为该建议的完整实现（含 L6887/L6857 双指针 + no declared field value changes 声明）。

**item3（version.py 锁面扩展——STATIC_PIN_EXEMPTIONS 两行重锚）— 重锚正确性机制级证明成立。**

| # | 检查项 | 实测 | 裁定 |
|---|--------|------|------|
| 1 | 新锚实指目标 token | WT L12534 = ``return f"| **P1** | {task_id} | fixture task | - | 0.87.0 | tests | {status} |"``（FIX-371 fixture 行 helper，`_REASON_FIXTURE_ROW_TEXT` 语义吻合）；WT L12658 = `"| ✅ 已交付 | EVD-997 / 0.87.0 |"`（FIX-376 F-6① legacy REQ 行，行内 reason 描述的「closed-loop path cell EVD-997 / 0.87.0」逐字吻合）；两行内容与 HEAD 旧锚 L12550/L12674 **逐字相同**（`git show HEAD:` 实读比对） | ✅ |
| 2 | 位移算术自洽 | 文件总行数 HEAD 21515 → WT 21499 = **−16**；numstat 24+/40− = −16；重锚 delta 12550→12534、12674→12658 均 −16；version.py 注记自述「shifted the file -16 lines」 | ✅（任务简报「−17」为表述偏差 → F-2） |
| 3 | 重锚注记合规 | 注记四项声明逐一核实：①归因 REVIEW-FIX-374 F-4（review-FIX-374-CODE-R0.md L97 实读——P3「提取共享 mixin/模块级 helper」，与本次实现选项一致）②「removed the 3 duplicated methods」（diff 实删 3 方法副本）③「-16 lines」（②实测）④「caught by RealTreeContractTests」（test_static_version_pins.py L316 类实存；「同 FIX-388 先例」的先例注释块在位——version.py L281-285 未改动部分）；「caught」为历史事件无法重放，以 rot-guard 机制级直调补足（§4） | ✅ |
| 4 | M-1 自休眠路径不受影响 | 扫描语义（version.py L361-372）：行携带 token 且 `token == active_version` 才可能 WARN；0.88.0 bump 后 active_version=0.88.0 ≠ 行上 0.87.0 token → L371 `continue`，两行自然休眠——休眠性源于 token 与未来 active version 不等，**与行号无关**；重锚仅恢复「锚行携带 token」这一账本完整性不变量（stale 审计 L395-401 要求），不触碰休眠语义；M-1 消解清单引用（version-plan L75）为未改动前注释，不在本 diff 面 | ✅ |
| 5 | 锁面外无副作用 | 重锚仅涉及该文件两行元组字面量 + 4 行注释；`scan_static_version_pins` 对全 tests 目录扫描 + 全账本 stale 审计（pytest 25P 全绿）——无其他文件行号漂移、无未豁免新钉 | ✅ |

**item3（e2e 副本切分器测试钉——不适用归类）— 四点理由全部核实成立。**

| # | Developer 理由 | 核实证据 | 裁定 |
|---|---------------|---------|------|
| ① | review-FIX-378 N-2 自身裁定「扩测试面将触碰另一声明快照」 | review-FIX-378-CODE-R0.md L77 N-2 原文：「可接受（declared legacy、扩测试面将触碰另一声明快照）。若副本日后晋升，主仓测试钉随迁移自动生效」 | ✅ 逐字吻合 |
| ② | FIX-381（A7）为制度承载面 | plan-tracker L105：FIX-381 =「切分器 backport 政策制度化（⑨ 定案：声明快照+受控 backport 非单源化……补丁台账……守卫语义复核）」，0.88.0 阶段 A7，🔄 已 lock 待派发——副本测试钉属该制度面，本票提前落地将与 A7 制度化决策冲突 | ✅ |
| ③ | 锁面不含副本文件 | `STATIC_PIN_SCAN_DIR = "skills/software-project-governance/infra/tests"`（version.py L173，root 相对）——e2e 副本测试文件位于 `project/e2e-test-project/skills/...`，不在扫描目录；STATIC_PIN_EXEMPTIONS 全部键均在主 tests 目录下（L205-300 全览） | ✅ |
| ④ | 副本守卫已有 | `check_legacy_snapshots`（projection.py L252-333）docstring 明列三红：**missing ⇒ FAIL / converged ⇒ FAIL / 声明缺 path/canonical/reason/scope ⇒ FAIL**（L261-267），字节级收敛比较（L325 `read_bytes()` 双读）；主仓行为等价钉 = `Fix373SplitterCodeSpanQuoteTests`（本 diff 迁移后仍全绿，L12180 调用点在列） | ✅ |

### 维度 2：安全性 — ✅ 通过

- 无新输入面：item1 为测试基建等价搬运；item2 为声明 JSON 的 reason 纯文本追加（消费方 `check_legacy_snapshots` 仅作字符串读取与长度/空判，L307）；item3 为账本常量重锚 + 注释。
- 无注入面变化、无敏感数据、无权限面变化；`_SEMVER_TOKEN_RE` 扫描逻辑未动。

### 维度 3：可维护性 — ✅ 通过

- item1 为净维护性修复（REVIEW-FIX-374 F-4 落地）：3×11 行副本 → 1×16 行单源（净 −16 行，含溯源 docstring），消灭第三副本再漂移路径。
- item3 注记自文档化：重锚原因 + F-4 归因 + rot-guard 先例引用，与既有 FIX-388 注记块格式一致，后续 re-audit 者可直接溯源。
- item2 披露完整性增强（N-1 落实）：副本「非纯冻结」事实进入机器守护的声明面，不再仅存于审查报告散文。

### 维度 4：性能 — ✅ 通过

- 模块级函数与绑定方法运行时等价（无 `self` 参与调用链差异）；JSON 追加 ~90 词、账本注释 4 行——无可测量性能面。

### 维度 5：测试覆盖 — ✅ 通过

- 三套件复现全绿：主文件 929P+126subtests、test_projection_legacy_snapshots.py 16P+6subtests（对账 945+132）、test_static_version_pins.py 25P、test_change_triage.py 95P（边界文件抽查）。
- rot-guard（stale-exemption 审计）按设计工作的机制级证明成立（§4）——本 diff 本身就是该守护网有效性的实证样本。
- 被提取 helper 的行为覆盖 = 原三组测试不变（调用点 1:1 改指，无测试增删）。

---

## 2. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | `patch.object(vw, ...)` 为既有测试 fixture 手法逐字保留于单源函数体内；产品代码（version.py/json）零 mock |
| 2 | 硬编码返回值 | ✅ 无 | diff 无任何新增返回值伪造；单源函数返回真实 `vw.check_protocol_compliance()` 结果 |
| 3 | 幻觉 API 调用 | ✅ 无 | 全部引用（`Path`/`patch.object`/`vw.check_protocol_compliance`/`_REASON_FIXTURE_ROW_TEXT` 常量）实存且用法与改前逐字一致；docstring 引用的 F-4/N-1 均在权威文件实读定位 |
| 4 | 未实现 TODO | ✅ 无 | diff 零 TODO/FIXME；唯一「未来动作」（M-1 re-audit at 0.88.0 bump）为既有注释块内容，非本 diff 新增 |
| 5 | 过度实现 | ✅ 无 | 三项均为最小落地：提取不带顺手重构、注记不带叙事改写（原文逐字保留 + 纯追加）、重锚不带动态化改造（注释明示「Line anchoring kept over dynamizing」决策不变） |

---

## 3. 设计一致性

- **REVIEW-FIX-374 F-4**：建议「提取共享 mixin/模块级 helper」→ 取模块级 helper 选项，实现与建议一致；F-4 所列三副本行号（L12071/L12145/L12243）与实删位置逐字吻合。
- **review-FIX-378 N-1**：注记为 N-1 建议的直接落实；N-1 明言「不要求本轮修改」，本票在 FIX-380 载体内顺带落地（披露于注记头「FIX-380 note (review-FIX-378-CODE-R0 N-1)」），时机与归属恰当。
- **FIX-388 重锚先例**：注释格式（归因 + 位移量 + rot-guard 表述 + 先例引用）与 L281-285 未改动先例块同构，「same as the FIX-388 re-audit」声明属实。
- **item3 不适用归类**：与 N-2 裁定、FIX-381（A7）制度承载分工一致——本票不预支 A7 制度面。
- **锁面扩展授权**：Coordinator 已追认 op-629ca75f（任务简报声明；流程面归 Coordinator，本报告记录在案）。
- **修改纯粹性（D4）**：三项各归其位（测试基建立面/声明披露面/账本面），无跨面顺手改动；P2 票承载 P3 杂项为该票 triage 定义的范围（2 落地 + 1 归类），非 creep。

---

## 4. 验证复现记录（MUST #5）

| 申报 | 复现命令 | 实测 | 裁定 |
|---|---|---|---|
| 基线/改后 945P+132subtests 全等 | `python -m pytest skills/.../test_verify_workflow.py -q`（改后）+ `python -m pytest skills/.../test_projection_legacy_snapshots.py -q` | 主文件 **929 passed, 126 subtests passed**（242.97s）+ legacy-snapshots 文件 **16 passed, 6 subtests passed** = **945P+132subtests，精确对账**（申报构成未披露，本组合为审查推断复现；静态 `def test_` 计数 929 = 收集数，diff 零 test 定义改动 → 基线全等结构性成立） | ✅ |
| test_static_version_pins 重锚前 2F→后 25P | `python -m pytest skills/.../test_static_version_pins.py -q` | **25 passed**（2.31s），含 RealTreeContractTests | ✅ |
| verify 全量 PASSED | `python skills/.../verify_workflow.py verify` | `== Verification Result: PASSED ==`，exit 0 | ✅ |
| cross-refs/manifest PASS（867/996） | `check-manifest-consistency` / `check-cross-references` 单项直跑 | **Canonical files: 867 / Actual files: 996 / [PASS] Manifest and filesystem are consistent.**；cross-refs `[PASS] No circular references.`（复合 verify 同过） | ✅（单项数字独立取行成功） |
| 重锚 rot-guard「caught by RealTreeContractTests」 | 机制级直调：以旧锚/新锚构造豁免表分别调 `scan_static_version_pins(root, active_version="0.87.0", exemptions=…)` | 旧锚注册表 → **恰好 2 条 stale exemption WARN（12550/12674「line no longer carries the token」）+ 新锚行未豁免 WARN**；新锚注册表 → 该文件零 WARN（残余 1 条为审查构造部分注册表缺 test_release_projection 键的伪影，真实账本含该键且 25P 已证）——「旧锚必红、新锚全绿」直证 rot-guard 按设计工作 | ✅ |

**方法注记（如实披露）**：曾以 `git worktree add`（临时检出 HEAD，用后即清）跑单文件基线，得 13F/925P/113st——经核实为**环境伪影**：`project/e2e-test-project/` 大量文件 untracked/ignored（tracked 仅 15 个，agents/*.md 等均 ignored），fixture-mirror 类测试（SUBFAILED(document='commands/governance/*.md')）在纯 HEAD 检出中缺 fixture 依赖所致，与 FIX-380 diff 无关，不构成对基线申报的反证；基线等价改由「零 test 定义改动 + 静态计数=收集数 + 945/132 精确对账」三方证明。evidence-log 回填义务见 F-3。

---

## 5. 发现清单（P0~P3）

> 无 P0 / P1 / P2。以下 3 条 P3 均为记录性/收口项，不阻塞合并。

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-1 | P3 | test_verify_workflow.py L12058 | 单源函数 docstring 称「the body is byte-identical to the extracted originals」——按严格字节口径不准确：方法体 8 空格缩进 → 模块函数体 4 空格缩进（提取的机械必然后果），程序化比对原始字节不等、**去缩进归一化后三副本逐字一致**。零行为差结论本身成立，仅措辞超出实测口径 | 后续测试窗口顺手改为「identical modulo indentation」或「statement-for-statement identical」 |
| F-2 | P3 | 任务简报文本（非代码） | 简报称「净 −17 行 / −17 行位移强制」——实测 −16（文件 21515→21499；numstat 24+/40−；重锚 delta 12550→12534、12674→12658 均 −16；version.py 注记自身「-16 lines」自洽）。代码与注记无影响，属简报表述偏差 | 收口机录时按 −16 口径记录 |
| F-3 | P3 | .governance/evidence-log.md | FIX-380 现仅 TRIAGE 机录行（L2565）；Developer 验证 EVD（945+132 对账/25P/verify PASSED/重锚 rot-guard 证明）尚未回填 | Coordinator 收口时回填（与本报告 §4 复现记录同口径） |

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁定 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | = 100% | 5/5 逐一有结论（§1） | ✅ |
| 每条发现标注级别 | = 100% | 3/3（F-1~F-3 均 P3 + 位置 + 证据 + 建议） | ✅ |
| 设计一致性检查 | 已完成 | F-4/N-1/N-2/E-1/FIX-388 先例/A7 分工/锁面追认七面对照（§3） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5（§2） | ✅ |

---

## 7. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 三项交付全部核实：item1 零行为差证明链完整（去缩进逐字一致×3 + 7/7 调用点迁移 + 零残留 + 同名边界不同源未触碰 + 静态计数=收集数）；item2 纯追加机比证明 + 注记与副本 backport 事实（L6887/L6857 实读）逐点吻合 + N-1 落地；item3 重锚正确性获机制级直证（旧锚必红/新锚全绿）+ 注记四项声明逐一属实 + M-1 自休眠语义与行号解耦不受影响；item3 不适用归类四点理由全部核实成立（N-2 裁定/A7 承载/锁面不含副本/三红守卫 + 主仓等价钉在位）。
- 验证复现：945P+132subtests（精确对账）、25P、verify 全量 PASSED（exit 0）、manifest 867/996、cross-refs PASS——全部独立复跑通过；rot-guard 有效性由「caught」历史事件转述升级为机制级直证。
- 遗留项（P3×3，无阻塞）：F-1 docstring 措辞精度；F-2 简报口径更正；F-3 Coordinator 收口回填义务。
- 结论性质：APPROVED_WITH_NOTES 仅表示硬门槛通过，不替代测试或发布审查。

*审查人：Code Reviewer Agent（R0）· 证据均为本会话实测（diff 逐行/程序化比对/直调探针/套件与 verify 复跑/文件行号），未采信未经复现的申报。*
