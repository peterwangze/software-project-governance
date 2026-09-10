# FIX-302 设计审查报告 — DESIGN R0

| 项 | 值 |
|---|---|
| Task | FIX-302 — FEAT-017 CODE R0 P1 F-1 承接：write-guard 接线措辞同步（canonical 两文件 + e2e 投影） |
| Round | R0（首轮独立设计审查；FIX-297 先例同域——规则/宣示面微改由 Design Reviewer 审） |
| Reviewer | Design Reviewer Agent（`agents/design-reviewer.md` + `skills/design-review/SKILL.md` + `skills/tech-review/SKILL.md`） |
| 日期 | 2026-09-10 |
| 审查对象 | 未提交工作树相对 HEAD `c6026ce`（= FEAT-017 交付 commit）的改动：`skills/software-project-governance/SKILL.md` L126 / `skills/software-project-governance/references/behavior-protocol.md` L75 / `project/e2e-test-project/skills/software-project-governance/SKILL.md` L126——**+3/−3，恰 3 文件各 1 行** |
| 结论 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0** |

---

## 1. 审查对象与事实基线

只读审查（仅 git 读 + 文件读；唯一产物 = 本报告）。全部规格与事实源均已读取：

| 事实源 | 位置 | 关键内容 |
|---|---|---|
| 工作树 diff | `git diff HEAD`（stat + 全文） | 3 文件 +3/−3；每文件恰 1 行改写；无其他 hunk、无 untracked 文件 |
| FEAT-017 交付物 | `skills/software-project-governance/infra/hooks/post-commit` L195-303 | Step 4b 段实存；L213-215「This step NEVER blocks and never aborts the hook: post-commit is advisory by design」；L217-222 ROLLBACK=「delete this whole Step 4b block … restores the FIX-297 scheme-2 posture — the pure protocol rule (behavior-protocol.md M1.2 …)」；全部命令 `|| SPG_WG_RC=$?` 防 `set -e` 中止 |
| FEAT-017 交付证据 | `.governance/plan-tracker.md` L297（✅ 完成，commit `c6026ce`）；`.governance/evidence-log.md` EVD-977、REVIEW-FEAT-017-R0（APPROVED_WITH_NOTES/unresolved_blockers=0） | 「post-commit 面板接线已交付（FEAT-017）」为已交付事实，非宣示 |
| F-1 原文 | `docs/reviews/review-FEAT-017-CODE-R0.md` L81/L106 | 指认恰为 SKILL.md L126 + behavior-protocol.md L75 两处「无 hook/commit 时点接线」字面过时；建议措辞「commit 时点已有 advisory 可见面板接线（FEAT-017）；强制复跑时点仍由 M1.2 协议 MUST 约束」 |
| 分级框架 | `core/protocol/plugin-contract.md` L52-114 | A 级 L54-69 / B 级 L71-86（含「pre-commit hook 或 CI 触发验证」）/ C 级 L88-104（L102「未实现」）/ L114 显式分级禁令；SKILL.md L120 节标题「自动化能力分级声明（plugin-contract.md L114）」实存 |
| M1.2 权威原文 | `references/behavior-protocol.md` L46-76（L75 = 该节末条） | MUST 复跑主体（直写四类产物 → MUST 复跑 → FAIL 修复 → fail-closed）在本 diff 中逐字未动；改动仅起于尾句「该守卫当前为…」 |
| 投影契约 | `core/version-projections.json` L12 | `{"id": "fixture-skill", "kind": "byte_copy", "source": "skills/.../SKILL.md", "target": "project/e2e-test-project/skills/.../SKILL.md"}`；写入路径 = `verify_workflow.py release-projection`（L21255/L23536/L24213） |
| 任务入账 | `.governance/change-triage/FIX-302.json`（files: 两 canonical 文件）+ plan-tracker L298（diff ≤6 行约束） | 改动范围与入账一致 |

投影 byte_copy 双重机器级证据：`git diff --no-index` 判定 e2e 文件与 canonical **逐字节一致**；且两文件在 `git diff HEAD` 中呈现**相同的 blob 哈希转换**（均 `7fa1cac..619f16d`）——改动前后双双同内容，非手改可构造的巧合级一致。

---

## 2. 四个审查重点逐一结论

### 焦点 ① — 分级口径准确性：**通过**

新措辞的每一项可宣示事实均有交付物锚点，无过度宣示、无弱化：

- 「post-commit 面板接线已交付（FEAT-017——advisory 显示、非阻断）」↔ hook L195-303 实存 + L213「NEVER blocks … advisory by design」+ plan-tracker L297/EVD-977 交付证据。**精确一致**。
- 「回滚=删 post-commit Step 4b 段」↔ hook L217-222 ROLLBACK 注释（「delete this whole Step 4b block」；自含性由 `SPG_WG_*` 段内局部变量保证——注释明言「no later step reads them, so removal is self-contained」）；behavior-protocol 面增补「恢复纯协议路径」↔ hook 同段「restores the FIX-297 scheme-2 posture — the pure protocol rule」。**精确一致**。
- 「复跑时点仍由 M1.2『直写后 MUST 复跑』约束并保留为权威与回退路径」↔ M1.2 L75 MUST 主体逐字未动（见焦点④）。**未弱化**。
- 「对外宣示不得写成 write-guard hook 时点强制或 C 级」↔ 事实基础成立：post-commit 在 commit 完成后运行，结构上不可能阻断；C 级 plugin-contract L102 声明「未实现」；该禁令延续 FIX-297 R0 焦点 1 确立的「L114 禁令模范执行」姿态（显式分级 + 禁令复述双保险）并按 FEAT-017 后事实**收紧**（旧文「不得写成纯 B 级时点强制」→ 新文细化禁止时点强制与 C 级两个越级方向）。**无过度宣示**。
- 括号注记「（B 级时点强制属 commit-msg/pre-commit 既有 hook 面）」**准确**：SKILL L124 B 级定义将 commit hooks 归入 B 级；其中能在时点**阻断**的只有 pre-commit/commit-msg（未完成时点、非零退出可中止）；post-commit 天然不可阻断。该括号将「commit hooks=B 级」这一粗粒度归类的执法面精确化，消除了 L124 泛称与新 L126 之间潜在的误读空间——是澄清而非新矛盾。
- 「B 级检查器工件 + A 级协议触发」组合定级未变——CLI 调用即强制（exit 1）仍是唯一强制时点；面板仅使该裁决在 commit 点可见。与 plugin-contract 三级框架（A=协议纪律 / B=脚本验证 / C=未实现）精确相容。

### 焦点 ② — canonical 一致性与历史文档不回写纪律：**通过**

- **两文件语义对齐**：SKILL L126（热注入面）与 behavior-protocol L75（权威面）新版尾句在四个关键断言上逐点对应——接线已交付（FEAT-017）/ advisory 非阻断 / 回滚=删 Step 4b 段 / 复跑时点仍以 M1.2 MUST 为权威与回退。措辞分工沿袭 FIX-297 R0 焦点 2 确立的单源纪律：宣示禁令置于 SKILL 分级声明节（对外口径位），规范约束 + 指针「分级口径见 SKILL.md『自动化能力分级声明』」置于 M1.2（指针目标 L120 实存、可解析）。**无新矛盾**。
- **历史文档不回写**：全仓 grep「无 hook/commit 时点接线 / hook 接线为后续候选」残留仅三处且全部应留——`docs/reviews/review-FEAT-017-CODE-R0.md`（历史审查报告，L79/L81/L106 为 F-1 事实记录）、`docs/reviews/review-FIX-297-DESIGN-R0.md` L76-77（历史审查快照）、`docs/requirements/architecture-audit-facts-0.80.0.md` L477（**时态性**陈述「FEAT-011 交付时 hook 接线为后续候选」——历史事实，非现行状态宣示）。plan-tracker 无该过时短语残留。**canonical 现行状态面已无过时陈述；历史文档零触碰**。

### 焦点 ③ — 投影正确性：**通过**

- e2e SKILL.md 是注册投影：`version-projections.json` L12 `fixture-skill` / `kind: byte_copy` / source=canonical SKILL.md。
- 工作树两文件逐字节一致（`git diff --no-index` 零输出）且 diff blob 哈希转换相同（`7fa1cac..619f16d`）——机器同步语义（byte_copy）在工作树态成立，投影非手改。
- `release-projection` 为 CLI 注册的唯一投影写路径（`verify_workflow.py` L21255/L23536/L24213）；projection.py L110-141 对 projection id/kind 契约做 fail-closed 校验（ID 唯一、kind 集合与 manifest 契约全等）。本 diff 的投影文件改动 = canonical 改动的 byte_copy 结果，属契约内同步，非范围蔓延。

### 焦点 ④ — 纯粹性：**通过**

- **行数/文件数**：+3/−3、恰 3 文件、每文件恰 1 行——满足 plan-tracker L298「diff ≤6 行」约束（3 ≤ 6，按 ±行合计口径 6 ≤ 6 亦满足）。
- **范围与入账一致**：FIX-302.json `files` 恰列两 canonical 文件；第三文件为其一的字节级注册投影（契约内同步义务，先例见 FEAT-017 EVD-977「projection-sync PASSED」）。无范围外文件。
- **M1.2 MUST 主体未动**：diff 逐 hunk 核实——L75 改动起点在「该守卫当前为…」尾句；MUST 复跑主体（触发主体/四类产物枚举/命令全路径/FAIL 处置/fail-closed 五要素）逐字保留。
- **无顺手改**：无其他 hunk、无格式化搭车、无 frontmatter 触碰、无 untracked 文件。

---

## 3. 蓝军挑战（对立面分析框架）

框架切换：从「措辞是否改对」→「这条措辞在最坏读者手里会导出什么错误行为」。隐含核心假设：①读者能区分 advisory 与阻断；②读者仍读 M1.2 而非只看面板；③投影同步是机器保证。

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---------|---------|---------|---------|---------|
| 1 | **过度宣示误读**：粗读者把「hook 接线已交付」理解为「直写违规会被 commit 阻断」，从而放松写入前纪律 | 中——直写后未 commit 前的窗口期无看护，误读者可能跳过即时复跑 | 措辞显式「advisory 显示、非阻断」+「不得写成 write-guard hook 时点强制」双保险（两文件均载） | 低 | 无必须动作；F-1（P3）备记录读序微瑕 |
| 2 | **权威路径弱化**：Coordinator 依赖 post-commit 面板作为唯一复跑提醒，M1.2「直写后即时复跑」义务被架空（面板只在 commit 时点曝光一次） | 中——违规发现从「直写当下」退化为「下次 commit」 | 两文件均显式「复跑时点仍以 M1.2 MUST 为权威与回退约束」——权威归属无歧义 | 低 | 无——措辞已是最强可用缓解（纪律本体在 M1.2，未被本 diff 触碰） |
| 3 | **投影双源漂移**：canonical 改动未同步投影（或投影被手改）造成 e2e fixture 失真 | 低——影响面限 e2e 测试工程 | byte_copy 注册 + 工作树逐字节一致 + blob 哈希同转换（§1）+ projection-sync/projection id 契约 fail-closed 校验（projection.py L134-144） | 低 | 无——commit 时点可跑 `release-projection` 校验收口（Coordinator 侧常规流程） |
| 4 | **历史回写滥用**：若同步「修正」历史 review/facts 文档中的过时陈述，审计链被破坏 | 高（若发生）——审查证据不可信 | 本 diff 零触碰 docs/reviews 与 docs/requirements（git status 实证） | 无 | 无 |

≥3 条挑战完成，含标准格式输出；独立评审结论在切换框架后独立得出（未复用 Developer 叙述——本报告全部结论重建自 diff/hook/plugin-contract/triage 原文）。

**ADR 类硬门槛适用性声明**：候选方案≥2 / ADR 字段完整 / 循环依赖等门槛针对 ADR 与选型报告，本任务为 3 行宣示面措辞微改（FIX-297 先例同型），不适用——按 FIX-297 R0 同等处理，以任务书 4 焦点替代为门槛。

---

## 4. 发现汇总

| ID | 级别 | 位置 | 描述 | 处置 |
|---|---|---|---|---|
| F-1 | **P3（SUGGESTION，非阻塞）** | `skills/software-project-governance/SKILL.md` L126 | 标题行「B 级检查器工件 + A 级协议触发**（post-commit advisory 显示面）**」的括号紧贴「A 级协议触发」——最严格句法解析下 advisory 面板似挂载于 A 级触发，而面板实为 hook 工件（B 级面）上的显示层。紧随其后的完整句（「post-commit 面板接线已交付…advisory 显示、非阻断…」）已消歧，语义无错误；仅为粗读序下的微小挂载歧义，属可读性观察而非口径失真。behavior-protocol L75 对应位置（「B 级检查器工件 + A 级触发（协议纪律）的组合：…；post-commit 面板接线已交付…」用分号展开）无此挂载问题 | 不要求本轮修改；若未来重写该行，可将括号移至组合定义之后（如「…A 级协议触发 + post-commit advisory 显示面（FEAT-017）」） |

- BLOCKING：**0**
- WARNING：**0**
- SUGGESTION：**1**（F-1，P3）

---

## 5. 终态

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

- 四审查重点全部通过：①分级口径与 FEAT-017 实际能力及 plugin-contract 三级框架精确一致（无过度宣示、无弱化）；②canonical 两面语义一致、历史文档不回写纪律模范遵守；③e2e 投影机器同步（byte_copy + blob 哈希同转换双重证据）；④纯粹性达标（+3/−3 恰 3 文件、M1.2 MUST 主体未动、零顺手改）。
- F-1（FEAT-017 CODE R0 P1）诉求被完整承接：两处过时陈述按其建议方向逐点修正，且分级结论（B 级工件 + A 级触发）与宣示禁令按 FEAT-017 后事实收紧细化。
- 唯一备注 F-1（P3 读序微瑕）不阻塞——供未来重写参考，无需本轮动作。
- 建议合入（commit 收口时按常规流程完成 projection 校验与治理记录）。

---

*审查方法：只读（git 读 + 文件读）；零文件修改（本报告除外）。审查结论持久化（review-record CLI）为 Coordinator 职责，本报告即其输入。*
