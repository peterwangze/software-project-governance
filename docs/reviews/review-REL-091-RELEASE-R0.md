# REL-091 R0 发布审查报告 — 0.89.0 M-1 版本 bump

| 项 | 值 |
|---|---|
| Task | REL-091（0.89.0 M-1 版本 bump，REL-087 先例形态） |
| 审查轮次 | R0 |
| 审查对象 | 暂存树 24 文件（vs HEAD `b950fef`；工作树与暂存零差异已实测） |
| 审查者 | Release Reviewer Agent（只读审查——除本报告外零写入） |
| 审查日期 | 2026-09-26 |
| 票面 | plan-tracker REL-091 行 + execution-packets.json REL-091 短包 + version-plan-0.89.0 §3b M-1 |
| 先例参照 | REL-087（`72ddffb`，0.88 M-1，31 文件）、FEAT-058（`44831b8`，0.86 M-1，26 文件） |
| **总结论** | **APPROVED_WITH_NOTES（unresolved_blockers=0）** |

---

## 1. 申报核验（EVD-1182 逐项对照实测）

| # | Developer 申报（EVD-1182） | 复审实测 | 裁决 |
|---|---|---|---|
| 1 | release-projection --write：written=17 / state PASS / source_version 0.89.0 | registry（core/version-projections.json）28 面 = **17 版本承载写入面 + 11 幂等 byte_copy 镜像**，与「written=17+幂等镜像；check 28/28」口径闭合；check-projection-sync 亲跑 28/28 PASSED、Source version 0.89.0 | ✅ 一致（写入结果态亲证） |
| 2 | check-version-consistency PASSED（唯一预期 WARN=plan-tracker 工作流版本 0.88.0） | 亲跑：PASSED，Warnings(1) = `plan-tracker workflow version=0.88.0, expected=0.89.0`——恰为唯一 WARN；静态钉面零 WARN（9 行豁免恰好全覆盖） | ✅ 一致 |
| 3 | check-projection-sync PASSED（28 面+entry bootstrap+declared_legacy_snapshots） | 亲跑：Mirrored files checked: 28，PASSED；entry 面由独立检查承载（#4）；declared_legacy_snapshots=10（registry 实数 10，看护套件断言 facts=10 随套件通过） | ✅ 一致 |
| 4 | check-entry-bootstrap-sync PASSED | 亲跑：PASSED——repo-root + e2e-fixture 双根（primary CLAUDE.md 9552B/full + secondary AGENTS.md 2834B/thin ×2）+ dsh-dialect 互认 | ✅ 一致 |
| 5 | check-manifest-consistency PASS（912 canonical / 1055 actual） | 亲跑：Canonical 912 / Actual 1055，PASS | ✅ 一致（逐字） |
| 6 | static-pin bump-time 消解：删 4 行 self-dormant 0.88.0 + 登记 9 行 0.89.0 实测 WARN 逐行 | 9 行逐行核对：`test_fix390:190/202/306`、`test_fix393:103/174/311/313`、`test_fix394:100/500` 行号与 staged 文件 0.89.0 字面量**精确对应**（fixture 行模板/表场景载荷面）；删 4 行（`test_verify_workflow:12742`、`test_archive:4586/4595`、`test_governance_store:493`）fixture 本体仍在、0.88.0 token 保留=自休眠成立；2 行 FUTURE_TARGET（`test_release_projection:30`「0.87.0」、`test_static_version_pins:158`「0.85.0」）dormant 保留。**无顺手扩大豁免面**（映射全貌 diff 审毕=仅删4+登9+注释史改写） | ✅ 一致 |
| 7 | 定向看护 test_static_version_pins+test_release_projection+test_entry_projection+test_projection_legacy_snapshots = 89P+6S | 亲跑：**89 passed, 6 subtests passed**（53.22s，exit 0） | ✅ 一致（精确） |
| 8 | check-governance 49=49 持平（基线实为 49 非 50——EVD-1179 R1 后收敛） | 复审实测 **51 issues（exit 0）**——+2 漂移未获逐条归因 → **P2-1**。全部 issue 族均落在在案披露/在途任务面（REQ-092×6+EVD-1146×1 在案维持披露、REL-090/091/092 在途任务合同族、review debt、Check 28s 体积 ERROR 常设、accounting ragged 行×2~3——`review-FIX-395-CODE-R1.md` 与 `risk-log.md` 均非本票触碰对象），**无一条触及 bump 24 文件面** | ⚠️ 部分一致（时点绑定漂移，非 bump 面引入） |
| 9 | git rev-list v0.88.0..HEAD = 11 commits | 亲跑：count=11；peel=`33d19b0`（与 CHANGELOG 一致）；CHANGELOG 列举 11 个 hash 与 `git log` 输出**逐一吻合**（新旧序一致） | ✅ 一致 |
| 10 | commit 尝试被 commit-msg Step 10 hook 依规拦截（evidence 行待落——本行即补） | 不可复现（Reviewer 只读约束禁 commit/暂存/重置）；staged 树原样交还 Coordinator | ➖ 不适用（申报留档，不构成审查对象） |

核验小计：8 项精确一致 + 1 项时点绑定漂移（P2-1）+ 1 项按约束不可复现。

---

## 2. 审查范围执行记录（24 文件逐文件，投影工件清单全列）

### 2.1 手改面（4 文件）
| 文件 | 审查结论 |
|---|---|
| `skills/software-project-governance/SKILL.md` | frontmatter 权威锚 `version: 0.88.0→0.89.0`，单 token 变更 ✓ |
| `skills/software-project-governance/infra/checks/version.py` | STATIC_PIN_EXEMPTIONS：删 4 行 self-dormant 0.88.0 + 登记 9 行 0.89.0（三文件键）+ 注释审计史改写；豁免登记与实测 WARN 对应逐行核实；无扩大豁免面 ✓ |
| `skills/software-project-governance/infra/verify_workflow.py` | REQUIRED_SNIPPETS **六锚**（.claude-plugin/plugin.json、.claude-plugin/marketplace.json、.codex-plugin/plugin.json、.zcode-plugin/plugin.json、package.json、core/manifest.json）0.88.0→0.89.0 手钉，防循环验证独立期望面 ✓ |
| `project/CHANGELOG.md` | +68 行 0.89.0 段（事实链见 §3）✓ |

### 2.2 投影工件（17 文件——CLI 再生，registry 逐面圈定）
`.chrys-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json`、`.zcode-plugin/plugin.json`、`package.json`、`skills/software-project-governance/core/manifest.json`、`infra/hooks/pre-commit`、`infra/hooks/commit-msg`、`infra/hooks/post-commit`、`infra/hooks/prepare-commit-msg`、`agent-presets/governance/agent.cordis.yml.template`（v0.88.0→v0.89.0 Coordinator 行）、`adapters/dsh/AGENTS.md.template`（@bootstrap-version）、`commands/governance-init.md`（3 锚）、`project/e2e-test-project/commands/governance-init.md`（byte_copy 镜像）、`project/e2e-test-project/skills/software-project-governance/SKILL.md`（byte_copy 镜像）、`project/e2e-test-project/.governance/plan-tracker.md`（工作流版本 transform）。

**抽查面（7 面 ≥ 5 要求）**：manifest.json `/version` ✓、plugin.json×4 `/version` ✓、package.json `/version` ✓、hooks `@version`×4 ✓、e2e fixture（SKILL.md/plan-tracker/governance-init.md）✓、marketplace `/plugins/0/version` ✓、dsh 模板双面 ✓——全部 0.88.0→0.89.0 单面变更、与 registry 定义一致、check-projection-sync 28/28 收敛。账面闭合：17 投影 + 4 手改 + 3 entry（暂存）= 24 ✓（+1 根 CLAUDE.md 磁盘态，见 P3-1）。

### 2.3 双根 entry sync（4 文件）
根 `AGENTS.md`（暂存 0.89.0）✓、根 `CLAUDE.md`（gitignore 本地文件，磁盘态 0.89.0 实测）✓、e2e `AGENTS.md`（暂存 0.89.0）✓、e2e `CLAUDE.md`（暂存 0.89.0）✓——entry-bootstrap-sync 亲跑 PASSED ✓。

### 2.4 先例形态对齐
REL-087（31 文件）/ FEAT-058（26 文件）同构面（版本锚+投影+双根+六锚+static-pin 消解+CHANGELOG 段）全部对齐；REL-087 特有的根 `changelog.md` 双位过渡在本票按 DEC-242①/P2-1 收口**不复刻**=票面授权形态 ✓；REL-087 附带的 docs/release 四件套与审查报告属 M-1R（REL-092）范围，本票不含=正确 ✓。

---

## 3. CHANGELOG 0.89.0 段事实链核对

| 事实 | 核对结果 |
|---|---|
| 七票载荷 commit 对应 | FIX-393=`8a94d64` ✓ / FIX-394=`3cb4048` ✓ / FIX-390=`def9508` ✓ / FIX-392=`65c8e4b` ✓ / FIX-395=`7795f59` ✓ / FIX-391=`c9b7415` ✓ / FEAT-065=`ab7a8e1`+`b950fef` ✓——与 git log 实测逐一吻合；批次排布（一：393→394；二：390+392+395；三：391→065）与 DEC-246① 主序列一致 ✓ |
| EVD 引用 | EVD-1171~1181 十一行全部存在于 evidence-log（1171 REL-090 / 1172-1174 FIX-393/394 / 1175-1176 FIX-390+勘正 / 1177 FIX-392 / 1178-1179 FIX-395+勘正 / 1180 FIX-391 / 1181 FEAT-065）✓ |
| FIX-390/395 申报勘正如实入账 | EVD-1176（census 75→75 零增量勘正+archguard 路由）与 EVD-1179（P1-1 static-pin 勘正）均在案，CHANGELOG 相应段落如实转述 ✓ |
| DEC-244~248 | 五条决策全部在案且引用语义一致：DEC-244（必选六项+五前置核验不激活+激活授权票不捆绑+挂起 0.90+ 七项）✓ / DEC-245（M-1→M-8 授权+arch 顾问协议+安全语义不削减）✓ / DEC-246（八条采纳）✓ / DEC-247（V3 链内轮次）✓ / DEC-248（验收拆分+FEAT-066 拆出）✓ |
| 09-30 风险窗注记 | risk-log：RISK-036/039/046 打开、RISK-047/048 登记观察，五条均带 09-30 同窗复评义务；截至本审查无窗内履行完成的预填事实——「本 M-1 时点尚未履行，无预填未生成事实」口径如实 ✓ |
| 「无新增功能激活」 | DEC-244 明示激活授权票不捆绑；11 commits 无激活执行；plan-tracker 三面（0.88.0 发布备注「B-12/B-13 机制未激活」+0.89 行五前置核验不激活+REL-092 feature-flags 席「全 WARN/MD_ACTIVE 未激活如实登记」）口径一致 ✓ |
| 行为修正披露三面 | ①FEAT-065 gate 闭集替换（lock_ttl_le 自定义 spec 自 0.89.0 fail-closed 拒绝+lock_ttl 死输入移除）②FIX-391 零写拒绝面（正常链路零感知+跨版本 resume digest 拒绝+路径 B backport 保留）③判据收敛不放宽——三面齐备且措辞符合 DEC-246⑥ 收紧口径 ✓ |
| 单 canonical | 根 `changelog.md` 为 tracked 文件、末节=0.88.0、本 bump 未同步——DEC-242①（0.88 M-3 裁决）+ version-plan §3b M-1 RELEASE-R0 P2-1 收口「不再同步」授权形态 ✓ |
| 发布时点口径 | 日期取 M-1 候选落库时点 2026-09-26 + FIX-349 taggerdate 权威勘误条款——未预填 tag 事实 ✓ |
| 审查报告留档 | CHANGELOG 点名 11 份报告（REL-090×2、FIX-390/391/392/393 各 R0、FIX-394 R0/R1、FIX-395 R0/R1、FEAT-065 R0）glob 实测全部存在 ✓ |
| semver 合规 | MINOR 0.88.0→0.89.0（version-plan M-0 双 GO AWN/0×2 依据；载荷含新增门禁面非纯 fix）；无跳号、无预留冲突（1.0.0 未触碰）✓ |
| 回滚可执行性 | 版本 bump 票回滚=单 commit revert 面（24 文件版本 token 变更，无数据迁移、无 schema 变更、无外部副作用）；正式 rollback-plan-0.89.0 随 REL-092（M-1R）交付且 B-12/B-13 回退预案「引用不触发」——与 0.88 先例同型 ✓ |

---

## 4. 发现清单（P0-P3 分级）

### P0（阻断级）
无。

### P1（须修复后方可放行）
无。

### P2（非阻塞，须跟踪销项）
- **P2-1 check-governance 活体 census 与申报差值 +2 未逐条归因**：EVD-1182 申报「check-governance 49=49 持平」；复审同日实测 **51 issues**（exit 0；`--level` 仅影响 summary 细节，census 无独立档位，口径同构）。差值无法归因到 bump 24 文件面——全部可见 issue 族落在在案披露（REQ-092×6+EVD-1146×1）/在途任务合同（REL-090/091/092 短包 in-flight FAIL 族）/常设 ERROR（Check 28s 体积 1719.5KB，0.88 M-8 起 ERROR 维持在案）/accounting ragged 行（两载体文件本票未触碰）。时点因素：49 测量后 EVD-1182 本行才落行（申报原文自证「commit 尝试被拦截——本行即补」），其后唯一 .governance 变更即该 append。**处置建议**：M-2 门禁实测（REL-092 checklist 席）以 census 分段计数逐条对账，把 49→51 差值归因入 EVD；在此之前不构成放行阻断（exit 0、零 bump 面涉及、四项出口检查与定向看护全绿）。

### P3（观察项/改进建议）
- **P3-1 根 CLAUDE.md 腿为本地磁盘态**：根 CLAUDE.md 在 `.gitignore`（L3）为本地渲染入口，双根 entry sync 的该腿仅存在于本机磁盘（0.89.0 已实测）；新 clone 不含该文件。REL-087/FEAT-058 先例同型、非本票引入——登记为工作区形态观察项（若未来要求仓库携带根 CLAUDE.md，属独立决策）。
- **P3-2 census 申报可归因性改进建议**：后续 EVD 引用 check-governance 计数时建议附 census 分段快照（各族计数），使跨时点复审可做精确差值归因（申报纪律改进，非缺陷）。

---

## 5. 硬门槛裁决

| 门槛 | 裁决 | 依据 |
|---|---|---|
| 1. 暂存树逐文件审查（24/24，投影工件清单全列） | ✅ PASS | §2：4 手改+17 投影（清单全列、7 面抽查≥5）+4 entry；零跳读 |
| 2. 亲跑四项出口检查+定向看护套件 | ✅ PASS | version-consistency PASSED（唯一 WARN=过渡态）/projection-sync 28/28 PASSED/entry-bootstrap-sync PASSED/manifest 912/1055 PASS；定向套件 89P+6S 亲跑复现——非仅信 Developer 报告 |
| 3. P0-P3 分级 + CHANGELOG 事实链逐票核对 | ✅ PASS | §3：七票 commit 级对应、EVD/DEC/风险窗/披露三面/单 canonical/11 commits 全部实测；§4：P2×1+P3×2，无 P0/P1 |
| 4. 只读约束（零写入+运行产物清理+暂存树原样） | ✅ PASS | 除本报告外零写入；pytest/pycache 运行产物已清理（git status 零 untracked）；未 commit/未暂存/未重置——交还时 24 staged / 0 unstaged 与接收时一致 |

---

## 6. 总结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

- 版本面逐位、投影面 28/28、双根 entry、static-pin 账本消解、CHANGELOG 事实链、四项出口检查、定向看护 89P+6S 全部亲证通过；先例形态（REL-087/FEAT-058）对齐；MINOR bump 依据充分。
- 保留备注：P2-1（check-governance census 49→51 差值归因移交 M-2 门禁实测对账）+ P3-1/P3-2（工作区形态观察项、申报可归因性改进）——均无未解决 BLOCKING finding。
- 暂存树保持原样交还 Coordinator；后续动作（evidence 回填、commit、M-1R 派发）由 Coordinator 按治理流程执行。

*审查方法注：本报告全部结论基于可复查事实（git 实测/检查命令亲跑输出/治理文件读取/测试亲跑），未采信任何未运行检查的推定；申报第 10 项（hook 拦截）因 Reviewer 只读约束标注不可复现而非通过。*
