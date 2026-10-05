# Code Review 报告 — REL-099-M3a（0.95.0 版本面 bump diff）

- **Round**: R0（Code Reviewer，首次审查）
- **发布链步**: REL-099 M-3a（0.94.0 先例 REL-098-M3a 同构）
- **审查对象**: `docs/reviews/REL-099-M1-R0.diff`（416 行，`diff --git` 头计数 = 恰 24 tracked 文件）+ 工作树当前态（版本面已 bump 未 commit）
- **审查人工具面**: Read/Grep/Glob only（Bash/Agent/AskUserQuestion 禁用；唯一可写文件 = 本报告）
- **日期**: 2026-10-05

---

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**

- findings 计数：**P0=0 / P1=0 / P2=0 / P3=4**
- 24/24 文件逐文件实读核验通过；版本值逐处 0.95.0、无意外夹带（非版本面变更零混入）；等长替换声明成立；STATIC_PIN_EXEMPTIONS 登记块最小且理由链成立；CHANGELOG 再生纪律段与引用工件全部对账一致；e2e fixture 镜像与真台账边界验证通过；AI 专项 5 项零命中。
- 机检事实（check-version-consistency 13 处 PASS@0.95.0 / unittest 1052 OK / injection-budget 4244/342 零变化 / projection·entry·cross-refs·manifest 全 PASS / check-governance 16 issues 零新增）**以 M-2 任务上下文记载为据**（Reviewer 无命令通道，未独立复跑；其中「13 处」获本审查代码拓扑独立对账支持，见蓝军①）。

---

## 一、逐文件核验表（24/24 实读）

| # | 文件 | diff 声明 | 工作树实读 | 判定 |
|---|------|----------|-----------|------|
| 1 | `.chrys-plugin/plugin.json` | L20 version→0.95.0 | L3 `"version": "0.95.0"` | ✅ |
| 2 | `.claude-plugin/marketplace.json` | L33 →0.95.0 | L12 `/plugins/0/version` 0.95.0 | ✅ |
| 3 | `.claude-plugin/plugin.json` | L45 →0.95.0 | L3 0.95.0 | ✅ |
| 4 | `.codex-plugin/plugin.json` | L57 →0.95.0 | L3 0.95.0 | ✅ |
| 5 | `.zcode-plugin/plugin.json` | L69 →0.95.0 | L3 0.95.0 | ✅ |
| 6 | `AGENTS.md`（root） | L82 @bootstrap-version→0.95.0 | L5 `@bootstrap-version: 0.95.0`（薄指针版） | ✅ |
| 7 | `adapters/dsh/AGENTS.md.template` | L94 →0.95.0 | L3 `@bootstrap-version: 0.95.0` | ✅ |
| 8 | `agent-presets/governance/agent.cordis.yml.template` | L107 v0.94.0→v0.95.0 | L51 `（v0.95.0）的 Coordinator` | ✅ |
| 9 | `commands/governance-init.md`（canonical） | 三标记 →0.95.0 | L198 / L269 / L354 三处 `@bootstrap-version: 0.95.0`（lightweight/standard/secondary-thin 三模板） | ✅ |
| 10 | `package.json` | L151 →0.95.0 | L4 0.95.0 | ✅ |
| 11 | `project/CHANGELOG.md` | +38 行 0.95.0 节（L5-41） | L5 `## [0.95.0] - 未发布（准备态）`；L37 版本面再生纪律段实证回填；0.94.0 节为 diff 上下文行未动 | ✅ |
| 12 | `project/e2e-test-project/.governance/plan-tracker.md` | L213 工作流版本→0.95.0 | L9 `**工作流版本: 0.95.0`（fixture 镜像） | ✅ |
| 13 | `project/e2e-test-project/AGENTS.md` | L226 →0.95.0 | L5 0.95.0 | ✅ |
| 14 | `project/e2e-test-project/CLAUDE.md` | L239 →0.95.0 | L5 0.95.0 | ✅ |
| 15 | `project/e2e-test-project/commands/governance-init.md` | 三标记 →0.95.0 | L198 / L269 / L354 三处 0.95.0；diff `index 409f33a..5ca1580` 与 root 副本同 blob hash（投影一致旁证） | ✅ |
| 16 | `project/e2e-test-project/skills/software-project-governance/SKILL.md` | L282 frontmatter→0.95.0 | L3 `version: 0.95.0`；diff `index 4d01c50..37ac32a` 与 root SKILL.md 同 blob hash | ✅ |
| 17 | `skills/software-project-governance/SKILL.md` | L294 frontmatter→0.95.0 | L3 `version: 0.95.0` | ✅ |
| 18 | `skills/software-project-governance/core/manifest.json` | L307 →0.95.0 | L4 0.95.0 | ✅ |
| 19 | `skills/software-project-governance/infra/checks/version.py` | +8 行 STATIC_PIN_EXEMPTIONS 0.95.0 登记块 | L364-373 新块实读（详见 §三） | ✅ |
| 20 | `skills/software-project-governance/infra/hooks/commit-msg` | L341 @version→0.95.0 | L5 `# @version: 0.95.0` | ✅ |
| 21 | `skills/software-project-governance/infra/hooks/post-commit` | L354 →0.95.0 | L4 0.95.0 | ✅ |
| 22 | `skills/software-project-governance/infra/hooks/pre-commit` | L367 →0.95.0 | L6 0.95.0 | ✅ |
| 23 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | L380 →0.95.0 | L6 0.95.0 | ✅ |
| 24 | `skills/software-project-governance/infra/verify_workflow.py` | REQUIRED_SNIPPETS 六针脚→0.95.0 | L1057-1074：claude-plugin / marketplace / codex / zcode / package / manifest 六面均 `"0.95.0"` | ✅ |

**附加核验（diff 外边界）**：

| 对象 | 事实 | 判定 |
|------|------|------|
| root `CLAUDE.md`（gitignored 本地实例，`.gitignore` L3 → 不入 diff 属设计内） | L5 `@bootstrap-version: 0.95.0` | ✅ 已同步（check 面为 untracked WARN advisory，version.py L117-138） |
| 真台账 `.governance/plan-tracker.md`（`.gitignore` L10 忽略） | L11 工作流版本仍 **0.94.0** 未动 | ✅ 符合声明（M-8 Coordinator 面） |
| 0.94.0 残留扫描（adapters/ commands/ agent-presets/ e2e-test-project/ 全域 grep） | **零匹配** | ✅ 无漏 bump |
| 0.94.0 残留扫描（infra/*.py） | 仅 version.py 台账注释/旧行（L355-362、L368）+ test_verify_workflow.py L20573/20576（0.94.0 bump-time 已豁免夹具行） | ✅ 均为设计内保留 |

**夹带检查**：全部 hunk 逐行复核——除版本子串替换、CHANGELOG 新增节、version.py 登记块外零内容变更；e2e plan-tracker L9 等长替换正确保留了先在格式怪癖（缺闭合 `**`，见 P3-3）；0.94.0 节/其余文件内容均为上下文行未动。**非版本面变更零混入 ✅**。

---

## 二、等长替换声明验证（审查面 2）

| 注入面文件 | 实证 |
|------|------|
| `agent.cordis.yml.template` L106→107 | 前后行仅 `（v0.94.0）`→`（v0.95.0）` 子串差异，6 ASCII 字符→6 ASCII 字符，等长 ✅ |
| `adapters/dsh/AGENTS.md.template` / `AGENTS.md` / governance-init.md 三标记 | `@bootstrap-version: 0.94.0`→`0.95.0` 同为 6 字符等长 ✅ |
| `ENTRY_TEMPLATE_CANONICAL_BYTES` 相容性 | 钉值现值（test_verify_workflow.py L23119-23124）：lightweight 5221 / standard 10238 / strict 11126 / secondary-thin 2840。等长 bump（6B→6B）不改变任何 entry 模板字节数 → **无需重定价，本 diff 亦未触碰该钉** ✅（FIX-432 窗口的随票重定价已在其自身 commit 完成，m-0-assembly-0.95.0.md L58 记载） |
| CHANGELOG「root 10238B/full + 2816B/thin」对账 | 10238 = standard canonical 钉值精确一致；2816 = **渲染态**字节数（sync_entry_projection.py L282-283：thin 投影 = canonical 模板 `.replace('{PRIMARY_ENTRY}', 'CLAUDE.md')`，工具按渲染段报告 bytes L472-473；2840 − 2×(15−9) = 2816 算术精确吻合）。两数各自域内成立，非矛盾（域口径注记见 P3-1） |

---

## 三、STATIC_PIN_EXEMPTIONS 登记块（审查面 3）

- **实读**（version.py L364-373）：新增 dict 键 `"skills/software-project-governance/infra/tests/test_archive.py"`，唯一行 `(5862, "0.95.0", _REASON_FIXTURE_ROW_TEXT)`。
- **钉行对账**：test_archive.py L5862 实读为 `archive = self._prepare("| 0.95.0 | 规划中 | — |\n")`——位于 `test_no_released_window_end_disables_fallback_fail_closed`（FEAT-076 Q6 date-window fallback fail-closed 用例），行内容含 0.95.0 token，(line, token) 与台账行精确匹配 ✅。
- **理由链成立**：该夹具行版本格携带的是 then-future window-end 0.95.0（0.93.0 窗口写入，0.94.0 期间因 token ≠ active version 休眠，本 bump 恰一次浮现——FIX-361 设计双信号）；判定消费的是 released-status 格（`规划中`→fallback 拒发），从不比较版本格。与 `_REASON_FIXTURE_ROW_TEXT` 语义及 0.85~0.89 先例口径一致 ✅。
- **登记面最小**：仅 test_archive.py 一行；静态钉扫描（version.py L173 `STATIC_PIN_SCAN_DIR` 限 infra/tests）下 0.95.0 新浮现面恰此一处 ✅。
- **旧行保留非删除**：0.94.0 行（L361-362）、0.93.0/0.89.0 各块全部保留 ✅（token≠active 自动休眠，无需清理——见蓝军②）。

---

## 四、CHANGELOG 再生纪律段（审查面 4）

L37 实读核对：

| 声明 | 对账结果 |
|------|---------|
| `release-projection --write` written=17 / write_then_probe=PASS / sd_integrity 28 scanned/0 unreadable / 幂等复跑 PASS@0.95.0 | 以 M-2 记载为据（未复跑）；**written=17 与 REL-098 先例同值**（EVD-1311：「投影 written=17」）——同构发布面文件计数一致性旁证 ✅ |
| 双根 entry sync（root + e2e 的 AGENTS.md/CLAUDE.md） | 三 tracked 文件在 diff + root CLAUDE.md（gitignored）工作树 0.95.0 实读 ✅；字节数对账见 §二 |
| REQUIRED_SNIPPETS 六面版本针脚 0.95.0 | 六针脚实读 ✅（§一 #24） |
| STATIC_PIN_EXEMPTIONS 0.95.0 bump-time 登记（test_archive.py L5862） | 实读 ✅（§三） |
| 回填位纪律 | 发布日期零预填（L6 FIX-349 占位注释）；Commit 区间 `6da8d04（v0.94.0 tag peel）..<M-1 回填位>` 终值不预编造（L10）；准备态注记明示终账随 M-2+ 补记（L41）✅ |
| 引用工件存在性（反幻觉） | `docs/release/m-0-assembly-0.95.0.md` ✅ / `rollback-plan-0.95.0.md` ✅ / `release-checklist-0.95.0.md` ✅ / `docs/research/feat-086-prospective-samples-2026-10-04.md` ✅ / REVIEW-FEAT-085-R0（=review-FEAT-085-DESIGN-R0.md，AWN + unresolved_blockers=0 实读）✅ / REVIEW-FEAT-086-R0（同形 AWN/0）✅ / REVIEW-FIX-432-R0·R1（R1 报告头载 R0=AWN/0，R1 自身 AWN/0）✅ / EVD-1312~1317 全在 evidence-log ✅ / DEC-312~316 全在 decision-log ✅ |

---

## 五、e2e fixture 边界（审查面 5）

- diff 内 `project/e2e-test-project/.governance/plan-tracker.md` 为 **fixture 镜像**（e2e 测试工程自带治理目录）✅。
- **真台账** `.governance/plan-tracker.md`（repo root）L11 工作流版本仍 **0.94.0**——未被本 diff 触碰，且该路径整体被 `.gitignore` L10 忽略，结构上不可能混入 tracked diff（双保险）✅。真台账 0.94.0→0.95.0 写回属 Coordinator M-8 面，声明与事实一致。

---

## 六、AI 专项 5 项（审查面 6）

| 项 | 结果 | 依据 |
|----|------|------|
| mock 残留 | 0 | diff 新增面无 mock/patch；test_archive.py L5863 `patch.object` 为既有测试代码，非本 diff 变更（本 diff 未触碰 test_archive.py——L5862 是登记既有休眠夹具行） |
| 硬编码 | 0（by-design 面） | 版本针/豁免台账为机制本身的声明式字面量；无密码/token/密钥类硬编码 |
| 幻觉 API | 0 | diff 无任何 API/接口变更；CHANGELOG 全部引用工件经存在性核验（§四） |
| TODO/FIXME | 0 | 新增块（version.py L364-373 / CHANGELOG L5-41）逐行无 TODO/FIXME/XXX/HACK |
| 过度实现 | 0 | 变更面 = 4 手工处 + 机写投影，无一超出版本面 bump 所需；等长替换未顺手修格式怪癖（正确遵守修改纯粹性 D4，见 P3-3） |

---

## 七、设计一致性（审查面 7）

Bootstrap 变更纪律方向验证 ✅：canonical（`commands/governance-init.md` 三模板标记）在 diff 中先改 → 实例经 `sync_entry_projection.py --write` 机写再生（root AGENTS.md/CLAUDE.md + e2e 双根四文件，渲染态含 `{PRIMARY_ENTRY}` 替换实证）→ 未发现任何绕过 canonical 直改实例的路径（root CLAUDE.md 为 gitignored 狗粮实例，本身即投影目标非事实源）。root 与 e2e 的 governance-init.md / SKILL.md diff blob hash 两两相同（409f33a..5ca1580 / 4d01c50..37ac32a）——投影零漂移旁证 ✅。

---

## 八、Findings（P0~P3）

**P0 = 0；P1 = 0；P2 = 0；P3 = 4**

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| F-1 | P3 | `project/CHANGELOG.md` L37 | 「root 10238B/full + 2816B/thin」未注域口径：2816 是**渲染态**（`{PRIMARY_EDITOR}`→`CLAUDE.md` 替换后）段字节数，而机器钉 `ENTRY_TEMPLATE_CANONICAL_BYTES["secondary-thin"]=2840` 计价 **raw canonical** 模板；两数各自正确但跨域比对会呈现 24B 表观差（本审查即触发该对账路径） | 下版或 M-8 收口顺手加二字注记（如「2816B/thin（渲染态）」）；不阻本版 |
| F-2 | P3 | `checks/version.py` L364-373 | 新 0.95.0 登记块插入于 0.94.0 行与 0.89.0 块之间，台账注释时间线非单调（0.93→0.94 │ 0.95 │ 0.89→…）。dict 按 file-path 键组织，功能零影响，纯阅读顺序问题 | 无需动作；未来登记可按版本降序或文件序统一 |
| F-3 | P3 | `project/e2e-test-project/.governance/plan-tracker.md` L9 | `**工作流版本: 0.95.0` 缺闭合 `**`（先在格式怪癖，非本 diff 引入）；等长替换正确保留原样（符合最小 diff 纪律） | 知识记录；**不在本 bump 修**（修改纯粹性 D4——版本面提交不夹带格式修复） |
| F-4 | P3 | `.governance/evidence-log.md` | REL-099 目前仅 TRIAGE-REL-099 在账；M-1/M-2 机检事实（13 处 PASS/1052 OK/probe PASS 等）尚无 EVD 行——发布链进行中属正常时序，收口时 MUST 补齐（否则 Check 30 复审链/证据完整性面将见缺口） | Coordinator M-8 收口时按纪律补 EVD（观察项，非本 diff 缺陷） |

---

## 九、蓝军挑战（3 条）

**① 六针脚漏改一处的检出面**：`REQUIRED_SNIPPETS` 六针不含 `.chrys-plugin/plugin.json`——若 chrys 漏 bump，verify_workflow snippet 面单查不出。**但** check-version-consistency 的 `VERSION_PATHS`（version.py L10-18）含 chrys（L17，`/version` JSONPath），FAIL 面独立比对 SKILL.md 权威源；且 version.py L88-99 还会对 REQUIRED_SNIPPETS 块做整体 semver-token 一致性复核。**检出面拓扑独立清点：7（VERSION_PATHS：SKILL+6 json）+ 1（snippets 块）+ 4（hooks @version）+ 1（CHANGELOG latest）= 恰 13 处**——与 M-2 记载「13 处」精确吻合（本审查代码级对账，非复跑）。结论：双层覆盖，单点漏改必被 FAIL 面拦截；残余窗口仅在「新增平台 adapter 未登记 VERSION_PATHS」的未来漂移面（属新增面登记纪律管辖，现行 13 处封闭）。

**② bump-time 豁免登记被后续版本复用忘清的漂移面**：豁免行按 `(line, token, reason)` 三元组消费——token 仅在等于当前 active version 时进入消费判定；0.95.0→0.96.0 后本行**自动休眠**，「忘清」无检出后果、不产生 blanket-allow。真正的漂移面是**行号锚**：test_archive.py L5862 上方插入会移位钉行 → stale-exemption WARN（rot-guard，version.py L169-172「ledger cannot rot into a blanket allow」；FIX-410/411/416/418/421/422 先例多次证明该守卫实际咬合）。结论：设计自洽，漂移有守卫拦截，无需本版动作。

**③（附加）等长 bump 对字节钉的边界**：0.94.0→0.95.0 恰 6B→6B 使 `ENTRY_TEMPLATE_CANONICAL_BYTES` 免于重定价；若未来版本串不等长（如 0.100.x 三段变长），entry 模板字节数将漂移 → 字节钉 FAIL。现行 guard discipline 已有 rides-the-ticket 重定价先例（FEAT-079/FIX-432，注释块内联记载），机制可承载，仅作前瞻披露。

---

## 十、硬门槛自检（skill 质量标准）

- [x] Review 意见覆盖 5 个评审维度（正确性=§一/§二逐处值核验；安全性=§六无敏感数据/无注入面；可维护性=§三理由链/§八 F-2 注释面；性能=纯文本版本面无运行时语义变更，不适用面明示；测试覆盖=guard 面（13 处/静态钉扫描/rot-guard/字节钉）代码实读 + 1052 unittest 以 M-2 记载为据）
- [x] 每条意见有明确级别标注（F-1~F-4 均 P3）
- [x] P0 计数 = 0
- [x] P1 计数 = 0（P2 亦 = 0；P3 不阻塞）
- [x] 结论有明确理由 + 事实依据红线：每条结论指向文件路径/行号/实读内容/引用工件存在性核验；无法实验证的内容全部列入 §十一

---

## 十一、未验证项声明（事实依据红线）

1. **Bash 禁止（角色硬约束）**：以下机检结果未独立复跑，以 M-2 任务上下文记载为据并标注——check-version-consistency PASSED@0.95.0（13 处）、unittest 1052 OK、injection-budget 4244/342 零变化、release-projection write_then_probe=PASS / sd_integrity 28/0、check-governance 16 issues 零新增、cross-refs/manifest PASS。其中「13 处」获本审查 FAIL 面拓扑代码级清点独立对账支持（§九①）；written=17 获 REL-098 先例 EVD-1311 同值对账支持。
2. **git 状态面**：diff 是否为工作树未提交变更的完整集（diff 之外有无其他 tracked 改动）无法以 `git status` 复核——以 M-1 diff 生成纪律 + M-2 projection/entry/cross-refs/manifest 全 PASS 记载为据；残余面（adapters/commands/agent-presets/e2e/infra）已用 grep 全域零残留扫描补偿覆盖。
3. **REL-099 M-1/M-2 EVD 行**尚未见于 evidence-log（仅 TRIAGE-REL-099）——发布链进行中，收口补齐属 Coordinator 面（F-4）。
4. `REL-098-M1-R0.diff` 先例存在性已核验（397 行数值未复点，非审查依赖项）。

---

## 十二、结论

**APPROVED_WITH_NOTES**

**unresolved_blockers = 0**（独立结构字段；无 BLOCKING finding）

4 条 P3 均为文档口径/台账排版/知识记录/收口时序类备注，无一要求本 bump 修改。版本面 0.95.0 bump 变更集：24 tracked 文件逐一对号通过、等长替换实证、登记块最小合规、真台账/fixture 边界清晰、引用链全可解析——**建议进入 M-3a 通过终态**（先例 REL-098-M3a 同构口径）。
