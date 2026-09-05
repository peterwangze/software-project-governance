# FIX-283 Code Review R0 — FIX-278 N-P2 卫生批（死代码删除 + 惰性注入对齐 + docstring + change-triage 五步双投影）

- **Task ID**: FIX-283（P2，0.78.1；DEC-172 #2/#3/#4/#8 + DEC-173）
- **审查者**: Code Reviewer Agent（Role: `agents/code-reviewer.md`；SKILL: `skills/code-review/SKILL.md`）
- **轮次**: **R0**（首审；前轮引用：`.governance/review-FIX-278-CODE-R1.md` N-P2-1/N-P2-2/N-P3-1 三遗留为本任务输入）
- **审查日期**: 2026-08-28（Reviewer 无时钟访问，Coordinator 补记）
- **被审查变更**: 工作树未提交改动中本任务净变更 5 文件：
  1. `skills/software-project-governance/infra/checks/review_domain.py`（N-P2-1：删除旧 `_legacy_blocker_keys`，委托版保留 :1663-1670）
  2. `skills/software-project-governance/infra/tests/test_verify_workflow.py`（N-P2-2：fix233 :15461-15466 / fix30 :15619-15623 注入对齐）
  3. `commands/change-triage.md`（四步→五步：L3/L27/L33/L46）
  4. `adapters/dsh/skill-shims/change-triage.md`（frontmatter L3 同步）
  5. `skills/software-project-governance/infra/verify_workflow.py`（N-P3-1：:15728 docstring ≤160→≤130）
- **诚实披露**: 本审查者按角色约束未运行 Bash/git（read/grep/glob 只读）。git 级工作树 diff 未检查——范围纪律以 triage 机器留痕 + 终态 grep 锚点静态核实；Developer 自报测试结果（干净全量 26F/2015P 前后逐位一致、test_verify_workflow 728/728、review_domain 消费者 36/36、verify 五子命令 exit 0）未由本审查者复跑，标为自述。

---

## 0. 审查结论

> **Review 结论：APPROVED_WITH_NOTES**
> **结构字段：`unresolved_blockers=0`**（无未解决 BLOCKING finding；P0=0、P1=0、P2=0，P3×2 观察级，见 §4）

**总评**：R1 三遗留全部修复且方向与 R1 建议一致——N-P2-1 为净删除（语义等价经本审独立逐行比对证实，非仅依赖 R1 转述）；N-P2-2 两处注入点与 F-1 行源对齐（与既有 :15081 参照用例同构，SimpleNamespace 六字段与真实 `TaskDep` 形状一致）；N-P3-1 注释与实现常量同步；change-triage 五步措辞与 `change_triage.py` a-e 模块契约逐点一致、双投影对称。无阻塞问题，本轮通过。

---

## 1. 5 维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | 删除后 `_legacy_blocker_keys` 单一定义且与被删版语义等价（§3-1）；注入 mock 在 live 执行路径上真实生效（:2379→:2349-2350 函数内 from-import，`mock.patch` 模块属性语义下取到 mock）；:15728 docstring 与 `_summary_detail_char_limit()`=130（:15717-15724）一致；L33 五步枚举与 a-e 契约零漂移 |
| 安全性 | ✅ 通过 | 净删除无行为面；测试 mock 全部上下文管理器包裹（:15458-15467 / :15616-15624），无泄漏；文档措辞变化不引入副作用语义；无注入面/敏感数据 |
| 可维护性 | ✅ 通过（2 项 P3 观察） | 死代码遮蔽消除、注入点与生产依赖面对齐、注释-实现同步。⚠️ P3×2：委托版无调用者（N-P3-A）、两用例断言不消费 completed（N-P3-B） |
| 性能 | ✅ 通过 | 删除无性能面；mock 注入无 I/O 开销变化；文档无运行时 |
| 测试覆盖 | ✅ 通过 | 注入恢复执行路径真实性；completed 语义的行为守卫由 `test_fix193_live_review_state_parsing_and_closure`（:15091-15101 直接消费 `completed`）承载——fix233/fix30 不承载该职责（N-P3-B 限定） |

---

## 2. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 产品代码零 mock；测试 mock 均 `with patch(...)` 上下文包裹，退出即还原 |
| 2 | 硬编码返回值 | ✅ 无问题 | mock `status="✅ 完成"` 为 fixture 语义数据（与 `_status_is_completed_cell` 规则 3 对应，verify_workflow.py:10142-10149）；130 为具名函数常量非魔法数 |
| 3 | 幻觉 API | ✅ 无 | `task_priority.parse_task_dependencies` 真实存在（task_priority.py:601）；`TaskDep` 六字段核实（:463-468）；`SimpleNamespace`/`patch` 已导入（test :29-30）；`_legacy_blocker_facts` 真实存在（review_domain.py:1629） |
| 4 | 未实现 TODO | ✅ 无 | 五文件改动区域逐行读，零 TODO/FIXME |
| 5 | 过度实现 | ✅ 无 | 净删除 + 一行注释 + 注入对齐 + 文档措辞；无多余抽象 |

---

## 3. 重点审查项 1-8 逐项核实

**1. 死代码删除安全性 — ✅ 核实通过**
- 遮蔽机制（历史）：`.governance/incidents/diff-FIX-278-R1.patch` :222-236（旧实现）与 :289-296（委托版）在同一 patch 中先后新增于同一模块——Python 模块加载顺序绑定，后者覆盖前者，R1 报告 N-P2-1 同结论。
- 删除后全仓引用：grep `_legacy_blocker_keys` 全仓仅 `review_domain.py:1663` 一处 `def`（无调用点、无动态字符串引用；docs/release/*.md 4 处均为审查/规划历史引用，非代码消费）。
- 语义等价（独立逐行比对）：被删版（patch :222-236：`_LEGACY_BLOCKERS_KEY_RE.finditer` + `token not in keys` 去重保序）与委托版经 `_legacy_blocker_facts` 的 keys 分支（现行 :1641-1660，同 RE :1525-1528、同 `str(raw_field or "")` 边界、同去重保序）产出完全一致；委托版额外计算 values/invalid 为纯增量，不影响 keys。docstring 两版逐字相同。
- `_LEGACY_BLOCKERS_KEY_RE` 消费：删除后仍被 `_legacy_blocker_facts`（:1646）消费，未成死代码。

**2. 注入对齐正确性 — ✅ 核实通过（含 N-P3-B 限定）**
- 字段形状：SimpleNamespace 六字段 `task_id/status/priority/dependencies=()/cross_entity_refs=()/target_version=""` 与真实 `TaskDep`（task_priority.py:463-468：str/str/str/tuple/tuple/str；构造点 :959-966）名称、类型、缺省形态一致；关键字构造顺序无关。消费侧 `_live_completed_task_ids` 仅 `getattr(dep, "task_id"/"status")`（review_domain.py:2354-2357），不触 `.is_completed()` 方法——SimpleNamespace 无方法不构成缺口。
- 旧注入死因：F-1 后 live completed 走 `_collect_live_review_sequences`（:2377-2381）→ `_live_completed_task_ids`（:2349-2350 函数内 `from task_priority import parse_task_dependencies` + 调用）；`vw.parse_completed_task_ids` 在 live 路径零调用 → `patch.object(vw, "parse_completed_task_ids", ...)` 为 no-op。该形态全仓归零（grep 无命中；test :8855-8900 为该函数直接单测，非注入，合法保留）。
- mock 生效机制：`mock.patch("task_priority.parse_task_dependencies")` 替换模块属性；函数内 from-import 在调用时从 `sys.modules` 取属性 → 取到 mock。两用例中 mock 真实进入执行路径，completed = {FIX-197, FIX-199, REL-058} / {FIX-232} 注入 :1998。
- 与既有参照同构：与 F-1 首处对齐用例 `test_fix193_live_review_state_parsing_and_closure`（:15081-15085）形态完全一致。

**3. 五步枚举忠实性 — ✅ 核实通过（零杜撰/漂移）**
L33 第 5 步逐点对照 `change_triage.py` 契约 e（:20-28）与实现接线：
| L33 措辞 | 契约/实现 | 判定 |
|---|---|---|
| 任务输入（`--files`/`--reason`/验收描述）隐含的仓库外副作用 | "implied by the task's `files` / rationale / acceptance"（:21-22） | ✅ |
| 安装器执行/真实 profile 写入/网络发布 | "installer execution, real profile writes, network publishing"（:22-23） | ✅ |
| 触及用户真实环境自动附加 R1 审查条件 | "auto-attaches the R1 (one-of-three) review condition"（:24-25）；`requires_r1` 字段见 triage 记录 schema | ✅ |
| 检测到信号而未声明（`--side-effects`）→ WARN（advisory，不阻塞） | "undeclared detectable side effect records a WARN issue (advisory — never silent, never blocking)"（:26-27）+ "Step-e WARN issues are advisory (exit 0)"（:36-37）；旗标真实存在：verify_workflow.py:22780 `ctri_p.add_argument("--side-effects", default="")` + :21270 `declared_side_effects` 接线 | ✅ |
| 记录落入纯增量字段 `analysis.side_effect` | "purely additive `analysis.side_effect` field"（:27-28）；FIX-283 triage 记录实含 `analysis.side_effect` 块 | ✅ |
第 1-4 步（L29-L32）与契约 a-d（:8-19，含 FIX-288 两层版本语义、既有环 WARN/新任务成环拦截、已完成任务不构成冲突）方向与措辞一致。

**4. 双投影对称性 — ✅ 核实通过**
- commands/change-triage.md：「五步」3 处（L3「五步 triage」、L27「## 五步分析（MUST 全量执行）」、L46「含五步分析」）+ L33 第 5 步新增枚举。
- shim（adapters/dsh/skill-shims/change-triage.md）：frontmatter L3 description「五步 triage + 机器记录…」同步；正文按薄投影设计不复制（L8「thin pointer，自身不含 workflow 规则」）——对称变更成立。
- 实时生效佐证：本会话 available_skills catalog 中 change-triage 描述已呈现「五步 triage」措辞（目测级，未重建 bundle）。
- 「四步」残留：commands/ 与 adapters/ 下 grep 零命中；skills/ 下 8 处命中均为无关语义（「第四步」步骤标题、复盘四步法），非 change-triage 残留。

**5. docstring 一行修正 — ✅ 核实通过**
- verify_workflow.py:15728 现为 `"""Bound one summary detail line (G1: header + ≤130 chars, ellipsis)."""`，与 `_summary_detail_char_limit()`=130（:15717-15724）一致；实现 :15729-15732（`label[: max(1, limit - 1)] + "…"` = 129+省略号）与「≤130」自洽。
- 全仓 `≤160|160 chars` 零残留于代码与产品文档；`.governance/` 下 11 处命中均为不可改写历史档案（incidents patch / 历史 review 报告 / evidence-log 描述行），保留正确。

**6. 测试守卫恢复声明 — △ 部分成立（如实限定，不阻塞）**
- 旧形态失效机制（核实）：patch 点 `vw.parse_completed_task_ids` 在 F-1 后 live 路径零调用 → mock 为 no-op；用例通过纯靠断言不依赖 completed——fix233 靠日期豁免（V1 BLOCKED 降级 :2158-2168、V5 missing 降级 :2207-2216 均仅判 `pre_normalization`）+ REL-065 invalid-token violation（尾列 `unresolved_blockers=0，P0=0` 全角逗号致 :1700 fullmatch 失败 → status="invalid"（:1709-1718）→ :2249 violation）；fix30 靠 routing 类型豁免（:2176 + `_task_routing_exempt` :2294-2322）。
- 新形态（核实）：mock 真实进入执行路径（§3-2），注入点与生产依赖面一致——「死注入」状态消除。
- 限定：两用例断言集合对 completed 值**无敏感性**（移除 mock、completed=∅，逐断言推演仍全绿）。故「恢复守卫」在「注入点-生产依赖面一致」意义上成立；在「断言检测注入失效」意义上不成立。completed 语义的断言级守卫由 :15091-15101 参照用例承载。详见 N-P3-B。

**7. 范围纪律 — ✅ 核实通过（静态 + 机器留痕；git 级未验证）**
- triage 记录 `.governance/change-triage/FIX-283.json` `files` = 恰好 5 文件，与本任务声明一致；`files_correction` 留痕完整（verify_workflow.py 为 N-P3-1 唯一落点、Coordinator 扩锁补齐、reason + evidence 字段在案）。
- 三遗留落点全部位于 5 文件内；终态 grep 锚点（`patch.object(vw, "parse_completed_task_ids"` 归零 / `_legacy_blocker_keys` 单定义 / ≤160 归零 / 四步 0）与 Developer 自报一致。
- verify_workflow.py 目标区域（:15712-15748）逐行读，本任务承载面仅 :15728 一行注释；R1 时代 :15665→现 :15728 的行号漂移与 FIX-287/288/289 已审查解析器 hunk 并入一致（工作树为多任务叠加态，范围外 hunk 未审）。
- **未验证（静态）**：git 级 diff 未跑（角色禁 Bash），「5 文件外零改动 / 文件 -17 行 / verify_workflow.py 仅一行」的最终精确性依赖上述留痕 + 锚点佐证，不由本审独立复证。-17 行与被删函数块（patch :222-236 共 15 行 + 2 空行分隔）静态推算吻合。

**8. R1 遗留覆盖完整性 — ✅ 核实通过（无遗漏无扩界）**
- N-P2-1 → review_domain.py 旧定义删除（§3-1）；N-P2-2 → test 两处注入对齐（§3-2）；N-P3-1 → verify_workflow.py :15728（§3-5）。三项全部承载。
- R1 §7 其余登记项未触碰：N-P3-2（Check 19 :525 谓词不同源——`parse_completed_task_ids` 仍被 Check 19 消费，符合 R1「维持登记/后续对齐候选」定位）、P3-2（released_history_version）、P3-4（guard written_cols 边角）——无扩界。
- change-triage 四步→五步双投影非 R1 遗留，属 DEC-172 入槽范围（#4/#8 + FIX-271 第五步事实；triage 记录 reason 字段在案）——正当地，非扩界。

---

## 4. 发现列表（P0=0 / P1=0 / P2=0 / P3×2，均观察级非阻塞）

### N-P3-A — 委托版 `_legacy_blocker_keys` 现为无调用者单定义（观察）
- **位置**: `checks/review_domain.py:1663-1670`
- **事实**: 删除旧定义后，全仓代码对该函数零调用（grep 仅 def 行；不在共享名称表，无动态引用）。它已不是「遮蔽」形态，而是干净但未接线的单定义。R1 建议原文即「删除旧定义（保留委托版）」，本任务忠实执行——无行为影响，不属本任务扩界对象。
- **建议**: 后续清理候选（随下次触碰 review_domain 同域批次裁决保留或删除）；不要求本轮处理。

### N-P3-B — fix233/fix30 断言不消费 completed，注入失效不被断言捕获（观察）
- **位置**: `tests/test_verify_workflow.py:15433-15491`（fix233）、`:15599-15628`（fix30）
- **事实**: 逐断言推演——fix233 的 V1/V5 降级仅依赖 `pre_normalization`（review_domain.py:2158-2168/:2207-2216），REL-065 violation 仅依赖 invalid token（:1709-1718→:2249）；fix30 的 V1 豁免仅依赖 routing exempt（:2176+:2294-2322）。移除 mock（completed=∅）断言仍全绿。新注入的价值 = 注入点与生产依赖面对齐（R1 建议选项 a 忠实执行），非 completed 语义断言守卫；后者由 :15091-15101 承载。
- **建议**: 后续增强候选——两用例可追加直接断言 `_live_completed_task_ids()` 返回值（如 `self.assertEqual(vw._live_completed_task_ids(), {...})`），使注入失效可被捕获；不阻塞本任务。

---

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 结果 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 0 |
| 5 维度全覆盖 | 100% | ✅ |
| 每条发现标注级别 | 100% | ✅ |
| 设计一致性检查 | 完成 | ✅（DEC-172 #2/#3/#4/#8 入槽范围 + R1 三遗留 + FIX-271 五步事实逐一比对，§3-8） |
| AI 专项 5 项 | 全部完成 | ✅ |

**裁决：通过 → APPROVED_WITH_NOTES / `unresolved_blockers=0`**（零 BLOCKING 问题；P3×2 观察级登记，不阻塞合并）。

## 6. 遗留项清单（非阻塞）

| 项 | 级别 | 关闭建议 | 截止 |
|----|------|---------|------|
| N-P3-A 委托版 `_legacy_blocker_keys` 无调用者 | P3 | 后续 review_domain 同域批次裁决保留/删除 | 观察 |
| N-P3-B fix233/fix30 断言不消费 completed | P3 | 追加 `_live_completed_task_ids()` 直接断言 | 后续触碰 |
| R1 N-P3-2 Check 19 谓词不同源（承接） | P3 | 维持登记/后续对齐候选 | 观察 |

## 7. 未验证项披露

1. Developer 自报全部测试结果（26F/2015P 前后逐位一致 + flake 证伪、728/728、36/36、verify 五子命令 exit 0）未由本审查者复跑（角色禁 Bash）——建议 Coordinator 以 pytest/verify 机器输出复核。
2. git 级工作树 diff 未检查：5 文件范围/-17 行/verify_workflow.py 仅一行的精确性为 triage 留痕 + 终态 grep 锚点静态佐证，非 git 独立复证。
3. shim catalog 实时生效以本会话 available_skills 描述目测为证，未重建 bundle 验证。
4. 本报告不替代测试审查/发布审查。
