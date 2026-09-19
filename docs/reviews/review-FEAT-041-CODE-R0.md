# FEAT-041 Code Review — R0（独立代码审查：入口模板契约 v2 全量推开 13 文件）

- **任务**: FEAT-041 批 2.1 入口模板契约变更瘦身（DEC-218 条件 go；REL-081）
- **Round**: R0（前轮引用：无——首审）
- **审查对象**: 工作树未提交 diff，13 文件（`git status --porcelain` 实测与 Developer §8 清单精确一致；其余未跟踪 `docs/planning/*`、`review-REL-082-DESIGN-R0.md` 属 REL-082，出范围）
- **审查者**: Code Reviewer Agent（独立实例；只读 + 本报告；未修改任何产品代码/`.governance`）
- **总结论**: **NEEDS_CHANGE**
- **unresolved_blockers**: **1**（P0-1）
- **findings 计数**: P0=1 / P1=0 / P2=2 / P3=4

---

## 1. 独立复验表（Reviewer 独立重跑，非转述 Developer 申报）

| # | 复验项 | Developer 申报 | Reviewer 独立实测 | 判定 |
|---|--------|---------------|-------------------|------|
| V1 | check-injection-budget 三 profile | standard 5,694 / strict 5,966 / lightweight 4,216 全 PASSED；strict 余量 34 tok | `verify_workflow.py check-injection-budget --profile {lw/std/strict}` 复跑：**4,216 / 5,694 / 5,966 全 PASSED**，resident ≤6,000；字节实测 standard 9,553B / strict 10,441B / thin 2,859B / lw 4,555B 与 `ENTRY_TEMPLATE_CANONICAL_BYTES` 四钉逐一相符 | ✅ 一致 |
| V2 | 五测试文件 197 passed | 197 passed | 精确「五文件/197」子集口径不可重构；等价面独立复验：`test_entry_projection.py` **34 passed**；全量 infra 套件 **3471 passed / 33 failed / 2 skipped**（33 失败全部为 HEAD 基线先在，见 V6） | ✅（口径差如实披露） |
| V3 | projection zero drift | zero drift | `check-projection-sync` 复跑：**FAILED — 1 issue：`projection drift: project/e2e-test-project/skills/software-project-governance/SKILL.md`**（详见 P0-1）；`check-entry-bootstrap-sync`（root + e2e fixture）PASS（9,552B full / 2,834B thin）；dsh dialect PASS | ❌ **申报不成立** |
| V4 | 明细零丢失（触发器↔§B 锚一一对应） | 零明细丢失 | 抽 3 锚全文对照 HEAD 模板：①SELF-CHECK 六条+补执行尾句（§B0）**逐字保留**；②FEAT-035 升级门 A~E 全套含深检前置/零写操作/归档四触发器（§B1.5）**语义完整**；③提问规则三清单+判断标准（§B3）**逐字保留**。附加：Step 3 阶段跳跃防护（MANDATORY）**全文保留在共享基座行内**；基座尾部 6 个 H2 骨架（干活前/提问规则/收工/详细规则/故障排除/快速入口）全部保留（压缩形态）；`§B0~§B5` 六小节全部存在于 SKILL.md，模板 13 处 `§Bx` 引用全部可解析；「你的铁律」「Agent 分发路由」「关键行为契约」「行为灰度开关」四个 SKILL.md 锚全部实存 | ✅ 成立 |
| V5 | 升级路径兼容（边界集旧集合超集） | 「详细规则」H2 恢复=拼接边界集超集，存量残留消除 | **实证**：以工作树 `extract_canonical_templates` 与 HEAD 复刻提取器分别计算 `_h2_titles` 边界集——**OLD-MINUS-NEW = NONE**（新集为旧集超集）；对旧安装 strict/standard 模板全文做 `bootstrap_section_span` 模拟，新边界下 span 与旧边界完全一致（strict (0,13770) / standard (0,13514) 整段覆盖）→ 旧安装整段替换、零残留 | ✅ 成立 |
| V6 | 3 失败测试先在定性（stash 净树） | stash 净树复现定性先在 | 以 **HEAD worktree（+`.governance`/fixture 未跟踪副本）替代 stash 法**（不动开发树，等效净树）：HEAD 等价态全量 **40 failed / 3464 passed** vs 当前树 **33 failed / 3471 passed**；**当前树失败集 ⊂ HEAD 失败集（新增失败 = 0）**。HEAD 侧多出 7 项中 2 项为 Reviewer 注入的红相证据（见 V7）、5 项为 worktree 环境伪影（legacy-snapshot 声明面，当前树全绿）。注：run1 34 vs run2 33 的 ±1 为时序敏感 flaky（loop-runtime performance median，FIX-320/346 已知面），非本 diff 引入 | ✅ 方向成立（全失败集均先在） |
| V7 | 双新测试红相存在性 | 组合语义守护 | 将新版 `test_entry_projection.py` 注入 HEAD worktree 对抗**旧提取器**：`test_strict_block_composes_over_standard_base` + `test_strict_delta_block_is_not_a_full_template` **双双 FAIL**（"strict delta block lost its heading" / 前缀断言失败）；当前树同文件 **34 passed** → 红→绿闭环实证 | ✅ 成立 |
| V8 | 断言随动后测试语义 | 消费者测试绿 | 见 §3 等价性论证表（7 项逐一核验） | ✅ 语义保留 |

**结论支撑**：除 V3 外全部申报复验成立；V3 为机械失守（内容零差异，仅行尾分歧），修复成本低但属验收链硬门禁红。

---

## 2. Findings

### P0-1（BLOCKER）fixture SKILL.md `byte_copy` 投影漂移——check-projection-sync FAIL，申报③「projection zero drift」不成立

- **位置**: `project/e2e-test-project/skills/software-project-governance/SKILL.md`（工作树态）；投影规则 `core/version-projections.json` L20-24（`"id": "fixture-skill", "kind": "byte_copy"`）
- **事实**:
  - canonical `SKILL.md` = 49,081 B、**CRLF×487**、SHA256 `8B634355…79F1606A`
  - fixture `SKILL.md` = 48,594 B、**纯 LF（CRLF×0）**、SHA256 `EFE413E4…BE3895FC6`
  - 两文件**逐行内容零差异**（difflib 0 hunks）——分歧纯为行尾；`_projection_matches` 对 `byte_copy` 走**原始字节相等**（`release/projection.py` L31-34），不豁免 EOL
  - HEAD 基线（worktree 实测）：两侧均 32,132 B、字节相等 → **漂移为本次工作树引入**（Developer 工具以 LF 写出 fixture 侧，而 canonical gi+fixture gi 为 CRLF+BOM 字节相等——同一批次两种工具行为，恰被 byte_copy 契约捕获）
- **影响**: 验收条款③失实；发布链 M-1/M-2 投影门禁红；`check-projection-sync` FAIL 即 FEAT-041 无法以当前树进入候选打包。附带：injection budget 的 `entry-skill` surface 当前按 LF fixture 计价（48,594B/SHA `efe413e4…`），修复后字节面变化仅落 report-only skill tier，无门禁影响
- **修复建议（机械）**: 重写 fixture 为 canonical 精确字节——`python <plugin_home>/infra/verify_workflow.py release-projection --write` 后复跑 `check-projection-sync`（预期 28 mirrored / PASS）；复验口径 = 两文件 SHA256 相等
- **复审要求**: 修复后 Coordinator 可以此 mechanical 复验（PASS + SHA 相等）单独关闭本 blocker，无需重触发全链复审

### P2-1 strict resident 余量 34 tok（0.57%）——2.3 翻 hard 前置风险

- **事实**: strict resident 5,966/6,000 tok；组成 persona 1,050 + composed strict entry 3,111 + thin 827 + agent-instructions 978。组合结构 = strict 完全继承共享基座增长（standard 余量 306 tok，strict 是**约束侧**）——基座每 +1 tok 在 strict 侧双计价
- **守护现状**: 翻 hard 前已有两层预警——`test_standard_and_strict_profiles_within_budget_after_feat041`（回归即红，unit 层 hard stop）+ FEAT-039 字节钉（价格移动必须有意改钉）
- **风险**: 2.3 批把 `BUDGET_TIER_POLICY["resident"].gate` advisory→hard 后，任何 >34 tok 的模板措辞微调直接 FAIL verdict + 门禁红；0.57% 缓冲低于一次小修订的典型增量
- **建议**: 2.3 前置批执行时（a）先做一次 strict 侧 trim 目标缓冲 ≥100 tok（差异段措辞或 §B 迁移面再收缩），或（b）翻 hard 的同一 DEC 内显式 re-base 预算档位并留痕。本项不阻塞本轮合并

### P2-2 「试点门 ≥85% 先行 / A@≥90%」验收子句无机检面可见——本审查未独立复验

- **事实**: FEAT-041 验收行含「试点门实测（<85% 停返）」与 DEC-218「A@≥90%」；13 文件 diff 内无对应测量工具/输出/证据路径；`docs/planning/0.85.0-2.0-injection-measurement.md` 为未跟踪 REL-082 出范围文档，未纳入审查
- **影响**: 零丢失抽检（V4）间接支撑明细面，但「A@≥90%」的量化口径在本轮**仅 Developer 声明**
- **建议**: Coordinator 在任务验收（review-record 落账）时要求补试点门实测输出（命令+数字）入 evidence-log；若无法补，则在 REL-081 发布说明如实披露该项为声明值

### P3-1 canonical `commands/governance-init.md` 新增 UTF-8 BOM（HEAD 无 BOM）

- **事实**: HEAD 首字节 `23 20 67`（"# g"）→ 工作树 `EF BB BF`；fixture 同步携带（两侧字节相等，byte_copy 不受影响）；投影 pattern `(?m)^> @bootstrap-version:` 行锚定不受影响；extract 标签正则不受影响
- **影响**: 当前零消费者破坏；但属**非预期字节变异**（仓内其余 12 个变更文件均无 BOM），未来任何字节级 diff/哈希对账（如 release integrity、byte_copy 新增面）会多出一个噪声源
- **建议**: 顺手去除（以 canonical 现行内容去 BOM 重写并同步 fixture）；或如属有意（Windows UTF-8 探测），在任务证据中留一句声明

### P3-2 composed strict 中「Strict Profile 强制规则」段落位置变化

- **事实**: 旧 strict 模板顺序 = [bootstrap] → Strict 强制规则 → ## 详细规则 → ## 故障排除 → ## 快速入口；新组合 strict = [共享基座（含三个尾部 H2）] → `### Strict Profile 强制规则`（H3）→（文件末尾）——即 strict 差异段现挂在「## 当前项目治理状态快速入口」之下作为尾置 H3
- **影响**: 五条 strict 规则（量化评分/双证据/阶段纪律/审查强制/归档完整性强制）**内容零丢失**（逐一对照）；纯版式/顺序差异。可接受；如追求版式对齐可在差异段前补一行说明其尾置语义

### P3-3 persona 复审必达触发器收窄：丢失「（含 NEEDS_CHANGES）」兼容输入提示

- **事实**: `agent-presets/governance/agent.cordis.yml.template` 新文 = "复审必达：NEEDS_CHANGE 且 round<3…"；旧文含 "（含 NEEDS_CHANGES）"。兼容输入规范仍在 `skills/code-review/SKILL.md`（"NEEDS_CHANGE（及兼容输入 NEEDS_CHANGES）"）与注入面指针（SKILL.md「关键行为契约」）中，非丢失
- **建议**: 0.85.0+ 候选——persona 触发器恢复兼容输入括注（4 字代价），避免字面匹配型 agent 漏触发

### P3-4 thin 指针 FIX-278 行删除 `[IO.File]::ReadAllText` 备选疗法

- **事实**: 根 `AGENTS.md`/secondary-thin 模板从「`Get-Content -Encoding UTF8` 或 `[IO.File]::ReadAllText…`」收窄为仅 `Get-Content -Encoding UTF8`。硬约束（必须显式 UTF-8、禁裸 Get-Content）完整保留；canonical 基座行归属「FIX-278 G4/F」正确（L815 归属纠正落地）
- **建议**: 可接受；无需动作

---

## 3. 断言随动 7 项——语义保留/等价性论证表

| # | 断言 | 旧形 → 新形 | 等价性论证 | 判定 |
|---|------|------------|-----------|------|
| 1 | FEAT-035 升级门针语计数 | file 级 `count==4/2` → composed 级 per-profile `count==2/1` | 旧=两份自包含模板各含 ×2；新=file 只载基座 ×2，strict delta 含 **0** 针（实测 delta 全文无「呈现升级待处理/零写操作/执行升级（推荐）/推进类动作/首次交互 ask」任一针语）→ composed strict = 2 ✓ 每注入面保证不变，且新增「delta 不得携带全模板标记」负向守护 | ✅ 等价 |
| 2 | 插件残留清理删除面 | file `count==2` → composed per-profile `count==1` | 同上结构；C 段 cleanup 流程（dry-run 先行/确认后执行/不确认跳过）语义完整迁于 §B1.5 + 基座行内触发器 | ✅ 等价 |
| 3 | `@bootstrap-version` marker | file `count==4` → composed 四 profile 各 `count==1` | marker 从 strict delta 移除后，file 计数 4→3（`version-projections.json` 同步 4→3），注入面逐 profile 恰一行由组合级测试守护；意外给 delta 加 marker 会被 per-profile `==1` 拦截 | ✅ 等价（投影 count 钉随文件形变，注入面不变） |
| 4 | 字节钉 `ENTRY_TEMPLATE_CANONICAL_BYTES` | 23,836/24,462/3,013 → 9,553/10,441/2,859（lw 4,555 不变） | 四钉与 V1 实测逐一相符；注释块内联记录新旧价格与组合语义（9,553 基座 / 10,441 = 基座+delta+分隔），价格移动仍须有意改钉——守护强度不变 | ✅ 保留 |
| 5 | gated/report-only 分离测试 | 真实 standard 超 6K → `budget_tokens=5000` 合成超载 | tier posture 数据不变（resident advisory / skill report-only）；原真值态（standard 超 6K）已因瘦身不复存在，合成预算是等价激励而非弱化——hard 翻转后的 fail-closed 语义仍由此测试可达（见 #7） | ✅ 等价 |
| 6 | `test_standard_profile_is_an_advisory_candidate…` → `…within_budget_after_feat041` | 「standard 必须 ADVISORY」→「standard+strict 必须 PASS」 | 验收关键翻转：瘦身交付本体断言；保留 posture 断言（advisory/report-only 不变），未来回归自动重连 ADVISORY 并翻红本测试 | ✅ 强化 |
| 7 | `test_budget_tier_is_not_a_hard_fail_while_advisory` | 真实超载 → `budget_tokens=5000` 强制超载 | fail-closed 硬门槛（gate=hard ⇒ issues+FAIL）在合成预算下完整可达；finally 恢复 posture | ✅ 等价 |

---

## 4. 五维度 + AI 专项结论

**五维度**（全 diff 逐行覆盖）：
- 正确性：✅ 组合语义单点权威（extract 内组合，entry projection/check-entry-bootstrap-sync/budget/tests 全部经同一出口）；边界集超集实证成立；红→绿闭环。唯一正确性缺陷 = P0-1（字节投影面）
- 安全性：✅ 无新增输入面/无凭据/无注入面；fail-closed 语义（upgrade 确认门/真实环境防护）全量保留于触发器行内
- 可维护性：✅ 单次维护达成（strict 侧 503 行重复消除）；锚点指针体系自洽（13 引用全解析）
- 性能：✅ resident 注入 5,694/5,966/4,216 tok ≤6,000（本次任务主目标达成）；skill tier report-only 不变
- 测试覆盖：✅ 组合正例 + 负向守护（delta 不得为全模板）+ 红/绿双相实证；33 个先在失败零新增

**AI 专项 5 项**：mock 残留=无（全 diff 无新增 mock/stub）；硬编码返回值=无（字节/计数钉均为注释声明之有意守护常量）；幻觉 API=无（`check_injection_budget(budget_tokens=…)` 参数实存且测试实证可达；`extract_canonical_templates` 组合面真实消费）；未实现 TODO=无；过度实现=无（组合逻辑 8 行，最小实现）。**附加异常字节发现 = P3-1 BOM。**

**设计一致性（DEC-218 条件 go 对照）**：触发器行内+明细按需 ✅；共享基座 standard⊂strict ✅（前缀组合 + 测试守护）；strict 约束侧 ≤6,000 ✅（5,966）；随行 FIX-278 行恢复+归属纠正 ✅（canonical「FIX-278 G4/F」）；「A@≥90% / 试点门 ≥85%」→ 见 P2-2（声明值，未独立复验）。

---

## 5. 边缘问题与处置建议（Coordinator 关注面）

1. **strict 34 tok 余量（P2-1）**：翻 hard（批 2.3 前置）落地前建议缓冲 ≥100 tok 或同 DEC re-base；当前双层预警（PASS-pin 测试 + 字节钉）使回归即响，不阻塞本轮。
2. **Check 10 规划文档触发面**：工作树新增未跟踪 `docs/planning/*.md`（REL-082 规划文档，本 diff 出范围）。`M5_RECORD_DOC_DIRS` 现含 `docs/release`/`docs/reviews`/`docs/requirements`，**不含 `docs/planning`**——若规划文档正文出现方案选项列表形态（"方案 A / 方案 B"），Check 10 可能报 `m5_option_list_no_auq` BLOCKING。建议：REL-082 triage 时二选一——按 FIX-348 先例评估扩白名单（产品代码面，走 Developer），或规划文档措辞规避选项列表形态；本报告落盘 `docs/reviews/`（已豁免面）无此风险。
3. **投影门禁的未跟踪依赖（先在，出范围）**：`check-projection-sync` 的 pass 态依赖 fixture 侧未跟踪文件（如 `project/e2e-test-project/commands/governance/scenario-a.md`，HEAD 无此文件时引擎 BLOCKED——fail-closed 行为正确）；fresh clone 会 BLOCKED 而非 PASS。建议登记治理数据卫生批候选（与 FIX-343 同族思路：要么入 manifest 跟踪、要么引擎对该面显式披露）。
4. **全量套件 ±1 flaky**：loop-runtime performance median 时序敏感（run1 34 vs run2 33），与 FIX-320 口径修正（median<8.0s 待 FIX-346 重定标）同源，先在。

## 6. 遗留项清单（建议 0.85.0+ 批）

| 级别 | 项 | 建议归属 |
|------|----|---------|
| P2-2 | 试点门/A@≥90% 实测证据补账 | Coordinator 验收集（evidence-log） |
| P3-1 | canonical gi BOM 去除（+fixture 同步） | Developer 顺手批 / 与 P0-1 同一修复 commit |
| P3-3 | persona NEEDS_CHANGES 兼容输入括注 | 0.85.0+ 候选 |
| 边缘-3 | 投影门禁未跟踪依赖披露/跟踪 | 治理数据卫生批候选 |

## 7. 复审路径（供 Coordinator 执行 M7.4）

- Developer 修复 P0-1（`release-projection --write` 或按 canonical 字节重写 fixture；建议同 commit 去 BOM/P3-1）→ 复验口径：`check-projection-sync` PASS + 两文件 SHA256 相等 + `check-entry-bootstrap-sync`/budget 三 profile 复跑不回归 → **机械复验通过即可关闭 blocker 并转 APPROVED_WITH_NOTES（unresolved_blockers=0）**，无需全链重审。
- 结论机录：本报告为 R0 记录源，请 Coordinator 按 M7.5 `review-record` 持久化（NEEDS_CHANGE → next_round=R1）。

---
*Reviewer: Code Reviewer Agent（独立实例）· 方法：只读 diff 逐行 + 命令独立复跑 + HEAD worktree 基线对账（未触碰开发树未提交变更）· 证据全部来自本会话实测命令输出*
