# REL-094 M-1 版本面独立审查报告（R0）

- **审查对象**：0.91.0 M-1 工作区未提交 diff（23 文件 +66/−32，版本面）+ 双 untracked 审查报告（不在 M-1 diff 内，已确认仅 `docs/reviews/review-FEAT-072-DESIGN-R0.md`、`review-FIX-399-CODE-R0.md`）
- **审查基准**：DEC-267 M-0 载荷冻结（FEAT-072 `196894a` + FIX-399 `9bafdf6`=HEAD；冻结后允许差异面=版本/投影/CHANGELOG/治理记录；额外源码修复=停止条件①）
- **审查人**：Release Reviewer Agent（独立，R0）
- **审查日期**：2026-09-28（+0800）
- **角色约束履行**：未修改任何产品文件与 `.governance/**`（唯一写操作=`release-projection --write` 幂等验证，实测 written=0 零变更；本报告为唯一产出）

---

## 结论速览

| 项 | 结论 |
|---|---|
| **Verdict** | **APPROVED_WITH_NOTES** |
| **unresolved_blockers** | **0** |
| BLOCKING（P0/P1） | 0 项 |
| P2 | 0 项 |
| P3 非阻塞备注 | 5 项（见分级清单） |
| 停止条件①（冻结边界外功能语义改动） | **未触发** |
| 停止条件②（verify_workflow.py 非六锚改动） | **未触发** |

六项审查清单全部 PASS（逐项亲跑证据见下）。M-1 diff 具备提交条件；P3 备注均为发布链后续里程碑（M-2+/M-3/M-5）的补记义务或定性说明，不阻断 M-1 落库。

---

## 审查清单逐项结论

### 1. 冻结边界 — PASS

**方法**：全量 `git diff` 逐文件比对（非抽样）；23 文件全部归类入版本面白名单。

| # | 文件 | diff 内容 | 白名单归类 |
|---|---|---|---|
| 1-5 | `.chrys-plugin/plugin.json` / `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json` / `.codex-plugin/plugin.json` / `.zcode-plugin/plugin.json` | 各仅 `version: 0.90.0→0.91.0` 1 行 | 版本投影 |
| 6 | `package.json` | 仅 `version` 1 行 | 版本投影（npm 载体身份） |
| 7 | `skills/software-project-governance/SKILL.md` | 仅 frontmatter `version: 0.90.0→0.91.0` 1 行 | 权威源 |
| 8 | `skills/software-project-governance/core/manifest.json` | 仅 `version` 1 行 | 版本投影 |
| 9-12 | `infra/hooks/{commit-msg,post-commit,pre-commit,prepare-commit-msg}` | 各仅 `# @version:` 1 行 | 版本投影 |
| 13 | `infra/verify_workflow.py` | **恰 6 处 hunk，均为 REQUIRED_SNIPPETS 版本字面量 `0.90.0→0.91.0`**（.claude-plugin/plugin.json / marketplace.json / .codex-plugin / .zcode-plugin / package.json / core/manifest.json 六锚；REL-091 先例形态） | 六锚手钉（任务白名单明确允许） |
| 14 | `AGENTS.md` | 仅 `@bootstrap-version: 0.90.0→0.91.0` 1 行 | entry 双根（根/次入口） |
| 15 | `commands/governance-init.md` | 恰 3 处 `@bootstrap-version` 字面量（模板三处注入形态） | bootstrap 模板 canonical |
| 16 | `adapters/dsh/AGENTS.md.template` | 仅 `@bootstrap-version` 1 行 | entry 模板投影（DSH dialect） |
| 17 | `agent-presets/governance/agent.cordis.yml.template` | 仅 persona 前缀 `（v0.90.0）→（v0.91.0）` 1 行 | persona 模板投影 |
| 18 | `project/CHANGELOG.md` | +34 行（0.91.0 准备态段） | CHANGELOG 面 |
| 19 | `project/e2e-test-project/.governance/plan-tracker.md` | 仅 `工作流版本: 0.90.0→0.91.0` 1 行 | 版本消费者（治理记录面） |
| 20-21 | `project/e2e-test-project/{AGENTS.md,CLAUDE.md}` | 各仅 `@bootstrap-version` 1 行 | entry 双根（e2e 根） |
| 22 | `project/e2e-test-project/commands/governance-init.md` | 恰 3 处 `@bootstrap-version`（与 15 同 blob 对：`c94d86d..12b2257`） | bootstrap 模板投影 |
| 23 | `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 2 hunks：frontmatter 版本 + M7.4「完成必推荐」行为行 | 投影再生（见下专项定性） |

**专项定性 A — verify_workflow.py 六锚纪律**：diff 中该文件 12 行变更（6+/6−）全部为版本字面量，无任何逻辑/判据/锚文本改动。**停止条件②未触发。**

**专项定性 B — e2e SKILL.md 第二 hunk（重点核查项）**：该 hunk 将 M7.4 关键行为第 2 条（完成必推荐）从 FEAT-072 前旧措辞更新为三要素推荐卡措辞。定性为**投影再生收敛，非新增功能语义改动**：
- FEAT-072 载荷（`196894a`，M-0 冻结内、REVIEW-FEAT-072-R0 AWN/0）修改了权威源 SKILL.md 该行，但 e2e 投影在 HEAD 时点滞后（未随载荷再生）——这正是 DEC-267(3) 披露的「28b 失败待 M-1 消解」项；
- 本 diff 再生后，e2e SKILL.md 与权威源 SKILL.md **blob 哈希逐字节一致（`6c47668`，git index 双证）**；
- 属冻结允许差异面「投影」，且为 28b 转绿的直接机制。

**专项定性 C — root `CLAUDE.md` 不在 diff 中（申报「双根 entry sync」核对）**：`git show HEAD:CLAUDE.md` → `path exists on disk, but not in HEAD`——AUDIT-082（`bea6f24`）已将其移出 git 跟踪（宿主本地文件，与 `.governance/` 同类）。磁盘实测该文件 `@bootstrap-version: 0.91.0` 已就位；`check-entry-bootstrap-sync` 亲跑 PASSED（repo-root 与 e2e-fixture 双根 CLAUDE.md full 9552B / AGENTS.md thin 2834B + dsh 模板互认）。**非投影缺口。**

**残留版本面路径级 grep**（`git grep "0\.90\.0"` 排除 CHANGELOG 历史段/docs/治理记录）：仅两类命中，均已定性为**正确保留**：
- `core/releases/0.90.0.json`：版本化 release ledger（历史版本账目，全序列 0.62.0~0.90.0 各一份）；0.91.0.json 缺席符合 DEC-267(4)「manifest/releases 若为 M-5 产物不提前伪造完成态」；
- `infra/checks/evidence_domain.py` `_RB2_DEMO_SENSITIVE_ACTION = "release 0.90.0 (发布)"`：FEAT-069（0.90.0 载荷本体）引入的 RB-2 演示场景主语字符串（`git log -S` 证实仅 FEAT-069 一次引入），非当前版本钉；**在本 diff 中改动它反而构成冻结违规**，保留正确。

### 2. 版本一致性 — PASS（亲跑）

```
python .../verify_workflow.py check-version-consistency
→ Result: PASSED — all version declarations consistent
  Warnings (1): [WARN] plan-tracker 工作流版本=0.90.0, expected=0.91.0
```
- 唯一 WARN 与申报及任务预期一致（plan-tracker 工作流版本=M-8 收口项），无第二 WARN。
- **抽查 3 投影面版本行**（以 diff hunk=工作区内容实证）：`.claude-plugin/plugin.json`=`0.91.0` ✓；`core/manifest.json`=`0.91.0` ✓；`agent-presets/governance/agent.cordis.yml.template`=`v0.91.0` ✓。三者均在 check-version-consistency / check-projection-sync 28 面机检覆盖内。

### 3. 投影收敛与幂等 — PASS（亲跑）

```
python .../verify_workflow.py check-projection-sync
→ Source version: 0.91.0；Mirrored files checked: 28；Result: PASSED
```
- 28/28 收敛 = 申报「28b 消解」验证成立（M-0 时点 1 面漂移即 e2e SKILL.md，见专项定性 B）。

```
python .../verify_workflow.py release-projection --write
→ {"state":"PASS","pass":true,"issues":[],"source_version":"0.91.0","written":0}
```
- **亲跑幂等第四度：written=0，未引入任何新差异**（申报三度 17→0→0 之上新增本审查 0）；
- 写后复跑 check-projection-sync 仍 28/28 PASSED；写后 `git status --short` 与写前逐行一致（23 modified + 2 untracked，零新增/零翻转）。

### 4. 预算终态 — PASS（亲跑三档）

```
check-injection-budget --profile lightweight → resident 4241/6000 PASSED
check-injection-budget --profile standard   → resident 5719/6000 PASSED
check-injection-budget --profile strict     → resident 5991/6000 PASSED（余量 9）
```
- 三档数字与执行申报（4241/5719/5991）及 DEC-267(2) 披露口径（strict 5991/6000、余量 9）**逐项一致**；
- `Over budget — gated: none`（硬门零触界）；skill 档 14606/16000（FEAT-052 report-only 线）亦在线内；
- persona 面 sha256[:16]=`8431118734f144a4` 三档同哈希，构成 M-1 后注入面不变性锚点。

### 5. CHANGELOG 质量 — PASS（3 项 P3 备注）

对照 DEC-267(2)(3) 逐项：

| 对照项 | 结论 | 证据（project/CHANGELOG.md 0.91.0 段，L5-37） |
|---|---|---|
| arch 主声明措辞/证据强度边界 | ✓ | 「完善推荐呈现的三要素推荐卡契约，并修复 Check 28c…误报」——事实性表述，无「彻底杜绝」类越界断言 |
| 载荷两票+审查链 | ✓ | FEAT-072（`196894a`，2026-09-27）+ FIX-399（`9bafdf6`，2026-09-28，HEAD 即此 commit）；均 R0 APPROVED_WITH_NOTES/0 |
| 已知限制四条 | ✓ | ① strict 余量 9 tok（5991/6000 M-1 后实测 + 「当前口径下净增超 9 tok 即越界」 + 0.92 治理票已登记含计量器版本/范围/基线）② evidence-log 1,737,424 bytes ③ 28c P2-1 延期（0.91+ 候选池）④ 版本面再生纪律 |
| DEC-267(2) strict 9 tok 处置选 (a) | ✓ | 维持 6000 上限披露 + 0.92 票登记三要素；见 P3-N1 措辞从句备注 |
| 准备态措辞 | ✓ | 「未发布（准备态）」；无日期预填；FIX-349 taggerdate 权威注记；M-2+ 补记声明 |
| 决策链与证据引用 | ✓ | DEC-265/266/267；EVD-1204/1205/1207；TRIAGE ×3 |
| 与 0.90.0 段风格一致性 | ✓ | 同构：`## [x.y.z] - 日期态` + `### x.y.z - **主题**：…` 摘要段 + 载荷票列表 + 已知限制 + Added/Changed/Fixed |
| **披露数字实测复核** | ✓ | evidence-log 尺寸审查时点实测 **1,737,424 bytes**，与段内披露**逐字节一致** |

### 6. 验证白名单复跑 — PASS（三项各亲跑一次）

```
check-injection-contract → Files checked: 4; anchors: 30；Result: PASSED
check-cross-references   → Files scanned: 77; References extracted: 728；[PASS] 无 dangling / 无 deprecated / 无 circular
check-manifest-consistency → Canonical: 945; Actual: 1093；[PASS] Manifest and filesystem are consistent
```

---

## 发现分级（P0-P3）

**P0（BLOCKING）**：无。
**P1（BLOCKING）**：无。
**P2（应在发布链内解决，不阻断 M-1）**：无。

**P3（非阻塞备注，随发布链承载）**：

- **N-1（P3）** `project/CHANGELOG.md` L18 — DEC-267(2) 措辞修正的第二从句「**计量或生成内容变化也可能越界**」未逐字落入 strict 预算披露行（现保留「当前口径下」限定语，语义主干完整）。修复建议：M-3+/发布态改写该段时补入该从句。
- **N-2（P3）** `project/CHANGELOG.md` 0.91.0 段 — 尚无「行为变更」声明（0.90.0 段有对应段）。与 DEC-267(3)「无 breaking 为预期分类——M-3 确认」一致，准备态不预断是正确姿态；**发布链改写时 MUST 落「行为变更」段**（含无 breaking 确认与 stdlib-only 依赖声明对齐——0.90.0 段两声明齐备，本段建议同构）。
- **N-3（P3，定性说明，禁止行动）** `infra/checks/evidence_domain.py:856` `_RB2_DEMO_SENSITIVE_ACTION = "release 0.90.0 (发布)"` — RB-2 演示场景历史主语（FEAT-069 引入），非版本钉，**正确保留勿动**；未来若演进 RB-2 演示数据应走独立变更票。
- **N-4（P3，预期缺口留账）** `core/releases/0.91.0.json` 不存在 — 符合 DEC-267(4)「M-5 产物不提前伪造完成态」；**M-5 MUST 创建**并与 release-ledger 校验。
- **N-5（P3，既有形态沿用）** `project/e2e-test-project/.governance/plan-tracker.md` 工作流版本行粗体标记形态与主干文件略有差异（`**工作流版本: x.y.z` 冒号入粗体）——HEAD 既有形态原样携带，非 M-1 引入；e2e fixture 装饰性差异，无需行动。

---

## 证据强度边界（未复跑项，如实声明）

以下为 M-0/前序证据承载、本审查**未复跑**的事实，引用时保持归属：
- 合并态联合回归 54+20 OK / contract+budget PASS@HEAD（DEC-267(1) 冻结依据，M-0 已锚）——本审查复跑了 contract/budget 三档与六项白名单验证，未重跑联合回归套件；
- `release-projection --write` 首写 written=17 为 Developer 申报（本审查实测其后态 written=0 + 28/28 收敛 + diff 面数吻合，历史时点不可复现）；
- 全量 pytest 未跑（M-2 承载，DEC-267(3) 披露分层既定）；check-release / release-ledger 属 M-3+/M-5 面，不在本审查白名单。

## 复审指引（若 Coordinator 判定返工）

R1 复审 MUST：(1) 逐条核对本报告 N-1~N-5 处置状态；(2) 重新亲跑六项验证与幂等 written=0；(3) 若 diff 面集扩大，停止条件①重新全文核对（e2e SKILL.md 第二 hunk 的投影定性依据 blob 同一性 `6c47668`，若该行再变须重新定性）。

---

**审查终态**：APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ 6/6 清单 PASS ｜ P3×5（零阻断）
