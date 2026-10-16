# Review: FEAT-101-CODE-R0 — chrys 平台适配移除

- **Task ID**: FEAT-101（移除 chrys 平台适配 + ask 裁决 live 面全清；历史档案豁免）
- **审查轮次**: R0（初审）
- **Reviewer**: Code Reviewer Agent（software-project-governance-code-reviewer）
- **审查对象**: staged 27 文件 delta（4 删除 + 23 修改，`git diff --cached --stat`: 77 insertions / 443 deletions）
- **核对清单**: `docs/research/pi-adapter-integration-research-0.98.0.md` §9.3
- **审查时间**: 2026-10-16 21:32 +08:00
- **审查环境**: 工作树含 FIX-445 未 staged 修改（commit-msg + test_hooks.py）与 Coordinator 本地面（根 AGENTS.md 标题、docs/research 研究文档）——非审查范围，见 F-3 披露

## 审查结论

**APPROVED_WITH_NOTES**

unresolved_blockers=0

分级计数：**P0=0 · P1=0 · P2=1 · P3=2**

---

## 一、审查清单逐项证据（9 项）

### 1. 移除完备性（重点）— PASS

- **live 产品面零残留（工作树 + staged 双验证）**：
  - `git grep -in chrys -- .`（工作树，大小写不敏感）：命中文件全部属于豁免面（docs/release 历史档案、docs/architecture、docs/marketplace、docs/requirements 历史设计文档、docs/research、docs/reviews 旧审查、docs/verification、project/CHANGELOG.md 旧条目、`infra/loop_migration.py` 注释、`infra/release/verify_rel063_evidence.py`、`infra/tests/test_loop_{structural_derivation,unit_manifest}.py` 合成夹具）。**verify_workflow.py、README.md、SKILL.md×2、core/manifest.json/md、version-projections.json、checks/{projection,triage_domain,version}.py、cleanup.py、quickscan_registry.py、golden_samples.txt、test_verify_workflow.py、test_dsh_*.py、adapters/dsh/*、两份活跃矩阵文档全部零命中。**
  - `git grep --cached -il chrys`（staged index，71 文件）：上述豁免面 + `AGENTS.md`（staged=HEAD 未变更版本仍含 Chrys 标题；工作树已改标题但故意不 stage——Coordinator 本地面，任务上下文明示）。staged 变更 27 文件 ∩ chrys 命中集 = 仅 test_loop_*×2（夹具豁免 + NOTE 注记）。
- **两类大小写盲区确认已清**（调研 §9.3-1）：
  - `MAINSTREAM_AGENT_LOADING_TIER1` 的 `"Chrys"` 纯大写行——diff 确认删除（verify_workflow.py 原 L2384 面）；
  - `MAINSTREAM_AGENT_LOADING_ADAPTERS["chrys"]["display"] = "Chrys"`——整个 chrys dict 删除（原 L2455-2469 面）。删除后 `grep -i` 双向复核零残留。
- **verify_workflow.py 9 处常量/检查面全清**（对照调研 §9.2 清单）：PLUGIN_SCOPE_DIRS（L352）、OPTIONAL_PROJECTION_FILES Chrys 4 行（L546）、PROJECTION_SNIPPETS chrys 三块 + `.chrys-plugin/plugin.json` 块（L654-677/678-692 面）、MAINSTREAM_AGENT_ADAPTERS 七→六元组（L1594）、RUNTIME_MATRIX_AGENT_IDS（L2351）、REQUIRED_DOCS（L2360）、TIER1（L2369）、LOADING_ADAPTERS dict（L2440）、ADAPTER_RUNTIME_CAPABILITY_POLICY chrys 六键行（L5439）——逐 hunk 实读确认。
- **计数串硬编码同步无漏**：`grep -inE "4 plugin|13 file|seven"` 扫 live 面（README/skills/**/adapters/**/两矩阵/e2e fixture）：**零 `4 plugin`/`13 file` 残留**；`seven` 命中全部属其他语义域（provenance 七要素〔baseline_metadata.py〕、seven review SKILLs〔verify L1381/1437/27078/27963——review skill 契约，与平台无关〕、TASK_STATES、injected faults、FEAT-100 pi registration faces〔test_archguard_ratchet〕）。已同步面：`Files checked: 13 (…4 plugin.json…)` → `12 (…3 plugin.json…)`（check_version_consistency 打印串，复跑实测输出 12/3）；`七平台→六平台` + `seven notes→six notes`×3（QUOTE_SYNC 注释与报错文案）；`seven adapters→six adapters`（exploration-channels PASS 输出实测）；dsh/README「与 Chrys 并列最强」→「当前最强」；dsh manifest evidence「together with Chrys」→删除；AGENT_RUNTIME_E2E 注释「Chrys-style」→删除。

### 2. 豁免面完整性反向核查 — PASS

- `git diff --cached` 27 文件 ∩ 豁免面 = **仅 `test_loop_structural_derivation.py` 与 `test_loop_unit_manifest.py`**，且各自 diff 仅 +2 行头部注记：`NOTE (FEAT-101): chrys 字样为合成夹具数据，非平台适配面——FEAT-101 决策保留。`——唯一允许例外，注记本身合规（与调研 §9.3-3「显式决策保留为合成数据」建议一致，防后续误清理）。
- **docs/release、旧 reviews、docs/verification、CHANGELOG（整体未 staged）、verify_rel063_evidence.py、loop_migration.py（未 staged）、.governance/**（gitignored）零出现在 staged**。

### 3. 四处同步合约 — PASS

- `verify_workflow.py` PLUGIN_SCOPE_DIRS（L344-356）= `cleanup.py` PLUGIN_SCOPE_DIRS（L48-62）= `core/manifest.json` cleanup_scope.directories（实测 count=10，成员 `.agents/.claude-plugin/.codex-plugin/.zcode-plugin/adapters/agent-presets/agents/commands/lib/skills`）——三处成员逐一比对一致，各删且仅删 `.chrys-plugin` 一行。
- **`check-manifest-consistency` 复跑：PASS**（Canonical files: 1133 / Actual files: 1341——canonical -2 与 manifest 删 2 条 `.chrys-plugin` canonical 条目自洽）。

### 4. 测试改动质量 — PASS

- **FIX-182 测试重构保住原测试价值**：`test_fix182_version_files_covers_zcode_and_chrys_plugin` → `test_fix182_version_files_covers_zcode_plugin`；PASS-after-fix 路径保留（构造 `.zcode-plugin` version 漂移断言真实 `check_version_consistency` FAIL 检出——**zcode 侧盲区回归仍在**）；FAIL-on-buggy 回放保留；**新增 FEAT-101 覆盖断言**：`VERSION_PATHS` 必须恰好含三个 plugin.json（claude/codex/zcode）——把「平台集缩减不得静默丢 per-plugin 覆盖面」固化为不变量，测试质量净提升。
- **七元→六元循环夹具**：`_write_all_adapters`（L2731）+ `_write_adapter` 删 chrys 24 行能力分支。
- **matrix 夹具**：两处 chrys 行删除（runtime 结果表 + 就绪表）。
- **dsh 族 cleanup_scope 计数 11→10**：test_dsh_boundary.py L1057-1062 与 test_dsh_contract.py L2472-2482 同步改断言并加 FEAT-101 注释；与 manifest 实测 count=10 一致（only-in-mine 主张复核成立——断言对象是 manifest 实际声明，非测试自造值）。

### 5. 金样再生成合法性 — PASS（附 P2 时机发现，见 F-1）

- `golden_samples.txt` 头部时间戳 `2026-10-16T04:16:16Z → 2026-10-16T12:24:17Z`（再生成机录特征）。
- chrys 行全部消失：REQUIRED_FILES 计数 1243→1241（manifest canonical -2）、plugin.json/README/adapter-manifest/launch.py 存在性行、STATIC adapter 行——**无手改痕迹**。
- 再生成时间差产物自然出现：FEAT-100 R0/R2 审查报告条目新增（上次金样生成时该报告未落盘）——反证机录而非手改。
- pin WARN 行号更新（25451→25468 等六条）与当前实跑输出逐字一致——金样生成时 test_verify_workflow.py 已是 FEAT-101 版。

### 6. 版本纪律 — PASS

- staged 27 文件**零版本号字面量改动**：version.py diff 仅 VERSION_PATHS 删 chrys 行 + STATIC_PIN_EXEMPTIONS 行号重锚（21244→21224、21276→21256、20746→20726、20749→20729，注释说明 FEAT-101 re-anchor -20，**复跑实测 4 条 stale exemption WARN 全部消失=重锚命中实际 token 行**）；version-projections.json 仅删 chrys-plugin 条目（6 行）；SKILL.md frontmatter 0.98.0 未动。
- **`check-version-consistency` 复跑：PASSED**（12 files / 3 plugin.json / 0.98.0 全一致）。

### 7. e2e 镜像手动同步 — PASS

- 主 `skills/software-project-governance/SKILL.md` 与镜像 `project/e2e-test-project/skills/software-project-governance/SKILL.md` 的 staged diff **blob index 完全相同（`d126bad..7ac9948`）**——两文件字节级一致的强证据（比 `fc` 抽验更强：git blob hash 相同 = 全文相同）。各删且仅删 Chrys 平台表行 1 行。

### 8. 验证复核（抽验）— PASS（1 项环境性失败，见 F-3）

| 命令 | 结果 |
|---|---|
| `check-agent-adapters` | **PASS 6/6**（claude/codex/gemini/opencode/dsh/pi，无 chrys） |
| `check-runtime-readiness-matrix` | PASS |
| `check-mainstream-agent-loading` | PASS |
| `check-exploration-channels` | PASS（输出实测「six adapters」） |
| `check-version-consistency` | PASSED（12 files，零 chrys 相关 FAIL） |
| `check-manifest-consistency` | PASS（canonical 1133） |
| `pytest -k "adapter or matrix or version or projection or chrys or plugin"` | **1 failed, 110 passed**——失败项 `SdIntegrityGateTests::test_projection_face_resolves_from_the_live_plan`，根因为 FIX-445 未 staged 工作树状态，非 staged delta（F-3 详证） |
| `git status --short` | staged=27 保持不变（审查全程零状态改变）；FIX-445 两文件（commit-msg、test_hooks.py）未 staged ✓；根 AGENTS.md 未 staged（Coordinator 本地面）✓ |

### 9. 越权检查 — PASS

staged 27 文件中**无** `.governance/`、`AGENTS.md`、`CLAUDE.md`、FIX-445 保全文件（commit-msg/test_hooks.py）、版本号面（零版本字面量改动，见清单 6）。

---

## 二、五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✓ 通过 | 删除面与调研 §9.3 清单逐项精确对应；三处 scope 同步 + manifest-consistency PASS；version.py 重锚实跑验证生效；投影链在 commit-msg（非 staged 面）之外的所有 staged 投影面全部通过 build 校验（build_projection_plan 顺序执行至 commit-msg 才抛错=前置面全过） |
| 安全性 | ✓ 通过 | 纯删除变更，只减不增攻击面；无新增外部输入/权限/敏感数据面；projection.py `_safe_repo_path` 路径守卫未触碰 |
| 可维护性 | ✓ 通过 | test_loop_* NOTE 注记防误清理；FIX-182 测试新增覆盖断言固化不变量；注释（七→六、Chrys-style 措辞、11→10 说明）与代码同步更新；无孤儿引用 |
| 性能 | ✓ 通过 | 集合/检查面/夹具规模缩小（七→六、13→12、11→10），无算法结构变化 |
| 测试覆盖 | ✓ 通过（附 F-3 披露） | 110/111 通过；唯一失败归因于审查范围外的 FIX-445 工作树状态（证据链见 F-3）；关键回归（zcode 盲区、六元循环、matrix、cleanup 计数）全部在位 |

## 三、AI 代码专项 5 项检查

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无——本次为 mock/夹具**删除**（chrys 分支 24 行、夹具行），无新增 mock |
| 2 | 硬编码返回值 | 无新增——计数串 12/3/10/6 全部实测与实际一致（version 12、plugin.json 3、scope 10、adapters 6） |
| 3 | 幻觉 API 调用 | 无——零新增 API 面；全部变更是常量/条目/断言删除 |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 轻度范围外夹带 1 处（F-2：manifest.md supported_agents 补 Pi——FEAT-100 遗漏面的必要补齐，语义正确） |

## 四、发现列表

### F-1〔P2〕金样再生成时机滞后于 version.py 重锚

- **位置**: `skills/software-project-governance/infra/contract_matrix/golden_samples.txt`（Warnings 段）× `infra/checks/version.py`（STATIC_PIN_EXEMPTIONS）
- **事实**: 金样（12:24:17Z 生成）Warnings 段含 4 条 `stale exemption test_verify_workflow.py:21244/21276/20746/20749` WARN——这是 version.py 重锚**前**的旧行号快照；staged version.py 已重锚为 21224/21256/20726/20729 且当前复跑这 4 条 WARN 全部消失。金样生成顺序为「test 文件修改 → 金样生成 → version.py 重锚」，金样未在最终 staged 状态下再生成。
- **影响**: 无门禁/测试影响（金样自声明「Tests do NOT byte-assert this file」；generator 输出非 FAIL 面）；但金样快照与 staged 终态存在 4 行 WARN 差异，违背「adapter 集变更后再生成」纪律的时机完整性。
- **建议**: version.py 重锚落定后重跑一次 `generator.py --golden`（可随 FEAT-101 commit 前收尾或 FIX-445 解阻后的下一次金样再生成顺带收口）。

### F-2〔P3〕manifest.md supported_agents 夹带 FEAT-100 遗漏面补齐

- **位置**: `skills/software-project-governance/core/manifest.md` L10
- **事实**: HEAD（FEAT-100 已 commit，cc40646/b7be5a5）的 supported_agents 为 `Claude, Codex, Gemini, opencode, Chrys, DeepSeek Harness`——**FEAT-100 漏加 Pi**；本次 diff 一次性 `Chrys` 删除 + `Pi` 补加。结果与 MAINSTREAM_AGENT_ADAPTERS 六平台集一致（语义正确、必要——若只删不加反而制造新漂移），但属跨任务修复夹带（D4 变更纯粹性小偏差）。
- **建议**: commit message 注明「manifest.md supported_agents 补 Pi 为 FEAT-100 遗漏面顺手闭合」；无代码改动要求。

### F-3〔P3·披露〕pytest 1 failed 归因于 FIX-445 未 staged 工作树状态（非 staged delta）

- **事实链**: ① 失败测试 `test_projection_face_resolves_from_the_live_plan` 断言 `sd_integrity.projection_face_paths` 非空；② `projection_face_paths` fail-closed：`build_projection_plan` 抛 `ValueError: projection pattern count mismatch for skills/software-project-governance/infra/hooks/commit-msg` → 返回空 paths；③ commit-msg 是 **FIX-445 未 staged 修改**（工作树 diff：`@version: 0.97.0→0.98.0` + 新增 744 行源验证代码，任务上下文明示「FIX-445 两文件未 staged」且 CRLF 阻断）；④ `projection.py` L229 特意 `read_bytes().decode()` 保留原生换行（FIX-366 byte_copy 字节一致性）——CRLF 污染的 `(?m)^# @version:…$` 计 0 匹配 ≠ 期望 1；⑤ **index（staged）版本 commit-msg 实测 LF 且恰 1 匹配=自洽**；⑥ staged version-projections.json 对 commit-msg 投影零改动（FEAT-101 diff 仅删 chrys-plugin 条目）；⑦ build 在 commit-msg 之前的全部 staged 投影面校验通过。
- **结论**: 失败由审查范围外的 FIX-445 工作树状态引起，pre-exists FEAT-101 staged delta；干净检出 staged 27 文件时该测试预期通过（依 ⑤⑦ 推理链；未实际干净检出复跑——见「未验证项」）。FEAT-101 自身不担责、不阻塞；提示 FIX-445 落地时需解决 commit-msg 行尾与 pattern 匹配数（其新增 744 行中不得再出现 `^# @version:` 形式行）。

## 五、硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞问题数 = 0 | ✓（P0=0） |
| 5 维度全覆盖 = 100% | ✓（五维度逐一有结论） |
| 每条发现标注级别 = 100% | ✓（F-1=P2，F-2/F-3=P3） |
| 设计一致性检查已完成 | ✓（对照调研 §9.3 核对清单逐项；与 ask 裁决「live 面全清+历史档案豁免」边界一致） |
| AI 代码专项 5 项全部完成 | ✓（见第三节） |

## 六、未验证项（诚实披露）

1. **干净检出复跑**: 未在纯净 checkout（仅 staged 27 文件、无 FIX-445 工作树修改）上复跑 pytest 全量——F-3 的「干净环境预期通过」基于 index 版本 pattern 自洽 + build 顺序推理链，非直接实测。Coordinator 若需闭环可在 commit 前于干净检出跑一次。
2. **金样 generator 逐字节再生成比对**: 未实际重跑 `generator.py --golden` 做 byte-diff（避免写操作）——机录合法性依 diff 内容特征判定（时间戳/FEAT-100 条目自然出现/计数自洽/无手改痕迹）。
3. **`release-projection --write` 全量写入**: 未执行（写操作禁令）；投影链完整性以 `build_projection_plan` 在 staged 面全过 + check-projection-sync 相关测试通过为间接证据。

## 七、给 Coordinator 的关键事实

- staged 27 文件 delta 与调研 §9.3 核对清单**逐项精确对应，无遗漏面、无越权面**；live 面零 chrys 残留（大小写双向、工作树+staged 双验证）。
- 全部 6 个抽查检查命令 PASS（agent-adapters 6/6、matrix、loading、exploration〔six〕、version〔12/3/0.98.0〕、manifest〔1133〕）。
- pytest 111 中 110 过；1 失败已闭环归因于 FIX-445 未 staged 工作树 CRLF/内容状态（F-3），FEAT-101 staged delta 无责。
- 两处非阻塞收口建议：金样在 version.py 重锚后重生成（F-1）；commit message 注明 manifest.md 补 Pi 的 FEAT-100 归属（F-2）。

**REVIEW: FEAT-101-CODE-R0 | APPROVED_WITH_NOTES | P0=0 P1=0 P2=1 P3=2 | unresolved_blockers=0**
