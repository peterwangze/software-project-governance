# FEAT-100-CODE-R2 — 增量轮+修复轮 delta 独立代码审查报告

- **Round**: R2（复审链第 2 轮；前轮 R0/R1 = `docs/reviews/review-FEAT-100-CODE-R0.md`，AWN/0 已终态）
- **Reviewer**: Code Reviewer Agent（角色 `agents/code-reviewer.md` + `skills/code-review/SKILL.md`）
- **被审面**: `git diff --cached`（cc40646 之后 staged）——实测 **12 文件**（+319/−127），任务申报「13 文件」系增量轮 7 + 修复轮 6 中 `test_verify_workflow.py` 跨两轮重复计数（7+6−1=12，勘误级偏差，见 F-R2-3）
- **日期**: 2026-10-16
- **结论行**: **APPROVED_WITH_NOTES**
- **unresolved_blockers**: 0

## 结论摘要

| 项 | 值 |
|---|---|
| 结论 | APPROVED_WITH_NOTES（保留备注的通过终态，无未解决 BLOCKING finding） |
| unresolved_blockers | **0** |
| P0 / P1 | 0 / 0 |
| P2 / P3 | 1 / 3 |
| 硬门槛（P0=0、5 维度全覆盖、逐条分级、设计一致性、AI 专项 5 项） | 全部通过 |

两个逻辑变更（①DEC-359 能力升级落面 ②修复轮 A/B 根修）实现与证据锚点高保真对齐；修复轮的 FAIL-on-buggy 价值经 HEAD 旧实现对照机证成立；被审面引入的唯一告警面扩大是 4 条 STATIC_PIN_EXEMPTIONS stale WARN（F-R2-1，P2），建议本轮顺手 re-anchor 但不阻塞。

---

## 发现列表（分级）

### F-R2-1｜P2｜STATIC_PIN_EXEMPTIONS 行号漂移未 re-anchor——4 条 stale WARN 由本 delta 引入

- **位置**: `skills/software-project-governance/infra/checks/version.py`（exemption 登记面）← 漂移源 `skills/software-project-governance/infra/tests/test_verify_workflow.py`（本 delta 净增 37 行）
- **事实**: HEAD（cc40646）时 token 行号与登记完全一致：`0.93.0`@21207/21239、`0.94.0`@20709/20712；本 delta 插入测试行后 token 实际漂至 21244/21276/20746/20749（实测 `git show HEAD:` 对照工作树），`check-governance --level strict` 报 4 条 `stale exemption ... line no longer carries the token` WARN。
- **影响**: WARN 级不阻断（exit 0 不变），rot-guard 按设计提示 re-audit；但 cc40646 rider 先例（「STATIC_PIN_EXEMPTIONS re-anchor——测试插入行号漂移，无语义豁免扩大」）在完全相同场景做过同步 re-anchor，本 delta 插入 47 行测试未承接该模式，属被审面引入的告警面扩大（33 issues 中与本 staged delta 直接相关的仅此 4 条）。
- **建议**: 本轮提交前将 version.py 中 4 个 `(line, token)` 登记更新为 21244/21276（0.93.0）、20746/20749（0.94.0）；`test_archive.py:5862`（0.95.0）stale 为既有存量（该文件自 HEAD 未改），可一并断代后处置。

### F-R2-2｜P3｜pytest 抽验 1 failed——环境归因工作树 commit-msg CRLF（非本 delta）

- **事实**: `pytest -k "LoopRuntimeClaim or FIX300DualCaliber or projection or pi"` → **1 failed / 45 passed**；唯一失败 `SdIntegrityGateTests::test_projection_face_resolves_from_the_live_plan`（L21199-21204）。
- **根因链（本审查独立复现）**: 工作树 `infra/hooks/commit-msg` 全 CRLF（1284 CRLF/0 纯 LF；HEAD 版纯 LF 543/0，` M` 未 staged，FIX-445 面）→ `build_projection_plan` 抛 `ValueError: projection pattern count mismatch for skills/software-project-governance/infra/checks/../hooks/commit-msg`（实测）→ `projection_face_paths` fail-closed 返回 `paths=[]` → 断言 `[] is not true` 失败。
- **归因**: 未 staged 的工作树环境缺陷（RISK-068 已入账、FIX-451 承载根治、plan-tracker P1 在案），**非 staged 12 文件引入**。修复轮 A 的效果恰由对照体现：Check 28b 从 KeyError 崩溃（EVD-1717 根因链）变为如实报告该 1 条 issue（`check-projection-sync` 实测 `Source version: unknown` 正常打印）。
- **处置**: 无需本 delta 动作；随 FIX-451 根治后自消。

### F-R2-3｜P3｜任务描述两处勘误（不影响代码）

- 「staged 的 13 文件」实为 12（`test_verify_workflow.py` 跨增量轮〔pi 夹具〕与修复轮〔Check 28b 回归〕两轮被重复计数，7+6−1=12）。
- 「机检 L6122 两块均 passed」——L6122 实为 gemini 分支；两块 passed 的机检实际位于 L6108/L6113（`_validate_runtime_e2e_block` 对 `target_cwd_e2e`/`agent_runtime_e2e` 的调用）与 L6125-6131（`full_e2e_verified=true` 要求两块均 passed 的联动校验）。语义正确，行号引用偏差。

### F-R2-4｜P3｜Check 17 User Impact 4 条 FAIL——FEAT-100 治理记录面欠账（非 staged 代码面）

- `check-governance` 报 EVD-1713/1715/1716/1717 缺「用户影响:」字段（EVD-1714 已有）。这些 EVD 是 FEAT-100 过程写入 `.governance/evidence-log.md`（非 staged 12 文件），属任务收口时应补的治理记录，交 Coordinator 在 FEAT-100 终账时处置，不属代码审查阻塞面。

---

## 审查清单逐项证据（任务 7 项）

### 1. 能力升级诚实性（重点）——✅ 通过

| 检查点 | 证据 |
|---|---|
| native 声明锚定 EVD-1715/1716 | manifest `ask_user_question.evidence`：「Runtime E2E verified 2026-10-16 (EVD-1715)... DEC-359 upgrade threshold satisfied (EVD-1716)」；`sub_agent.evidence`：「dispatch_agent real-dispatch three steps machine-recorded — role read (agents/analyst.md injected via --append-system-prompt), nested run (... child process), structured return (nested Analyst read adapters/pi/README.md and returned '# Pi Adapter' verbatim, exit 0)」。EVD-1715（evidence-log L2536）/EVD-1716（L2537）/DEC-359（decision-log L226）均实读在场，两步门槛口径（矩阵 passed + 真派发三步）与 DEC-359 原文一致 |
| ask_user 交互模式 + headless 有界错误三面保留 | manifest：「available in tui and rpc modes (rpc via extension_ui_request/response subprotocol)... fails fast with the structured GOV_ASK_USER_HEADLESS error, which is bounded behavior on the no-UI boundary, not a capability gap」；README L55：同义中文披露（「tui/rpc 交互模式可用…这是无 UI 边界上的有界行为而非能力缺失」）；SKILL.md L525 与 e2e 镜像 SKILL.md L525（同 blob 8232eb5..d126bad，投影同步）：「headless…fail-fast 返回 GOV_ASK_USER_HEADLESS 结构化错误——无 UI 边界上的有界行为而非能力缺失」——三面齐 |
| 不扩称（browser/mcp/consult/closure） | manifest `browser: unsupported`、`mcp: degraded`（evidence 未变）；`consult: degraded` 仅 evidence 措辞补 EVD 引用，status 未动；`workflow_closure: degraded` 保留且 `degraded_capabilities` 收缩为 `[browser, mcp]`——与 non_native 键集（browser/mcp，L5563-5567 机检口径）精确一致，无 missing |
| runtime_e2e 落法与机检一致 | `full_e2e_verified: true` + `target_cwd_e2e: passed`（command+verified_on+evidence 齐）+ `agent_runtime_e2e: passed`（同）+ `e2e_level: real-agent-target-cwd`——满足 L6125-6131（full→两块均 passed）、L6159（runtime-verified 的 e2e_level 枚举）、L5441（passed 必带 command/verified_on）全部机检；check-agent-adapters 实测 7/7 `[STATIC] agent adapter pi: runtime-verified` EXIT=0 |

### 2. CAPABILITY_POLICY 与 manifest 机检一致性——✅ 通过

`ADAPTER_RUNTIME_CAPABILITY_POLICY["pi"]`（L5508-5518，含 DEC-359 升级注释）：`ask_user_question {native}`、`sub_agent {native}`、`tool_calling {native}`、`browser {unsupported}`、`mcp {degraded}`、`git_hooks {native}`——与 manifest `runtime_capabilities` 逐键对齐（staged manifest JSON 实读比对）；`_validate_runtime_capabilities` L5542-5547 policy 门、L5548-5551 evidence/degraded_mode 门（browser/mcp 均带 degraded_mode）、L5553-5581 closure 门全部满足。测试夹具同步：`test_verify_workflow.py` pi 分支夹具 ask_user/sub_agent 改 native + `workflow_closure.degraded_capabilities=[browser, mcp]`，矩阵夹具 pi 行 `PASS | DEGRADED`——与真实文档/常量同构。

### 3. 修复轮 A（projection schema）——✅ 通过

- **两返回路径恒完整**: legacy 路径 `_legacy_projection_sync`（projection.py L33-75）字面构建 `pass/state/issues/source_version/mirrors_checked/mirrors_discovered/mirrors_skipped_untracked/version_checks`；新路径 L91-94 以 `result.get(...)` 补齐同名键（`{**result, ...}` 展开序保证补齐键后置覆盖）。空 root 实测：`BLOCKED, source_version='', mirrors=0/0/0, version_checks=[]`，裸下标消费无 KeyError。
- **根修在 schema 归位层**: 注释明示「The adapter owns the stable schema shared by BOTH return paths」——修复位于适配层（`check_projection_sync`）而非调用点 `.get()` 掩盖；调用点裸下标保留（L7613〔check-governance details 面〕/L17318〔Check 28b 打印〕/L23264〔standalone 打印〕）契约成立：schema 恒在 → 裸下标即 fail-fast 消费，缺失会立刻暴露而非静默吞掉。EVD-1717 记录的三层根因链（CRLF→匹配 0 次→BLOCKED 空 facts→裸下标 KeyError）与代码事实吻合，CRLF 第一环移交 RISK-068/FIX-451（越权红线遵守——本 delta 未触碰 .gitattributes/version-projections pattern）。
- **FAIL-on-buggy 价值**: `test_projection_sync_blocked_plan_face_keeps_caller_schema`（test_verify_workflow.py L8795-8820）在空 root 上断言 BLOCKED + 五键全在场；旧适配层无 `source_version` 键时 `result["source_version"]` 必 KeyError——机证成立（本审查以空 root 实测新行为，键全在）。

### 4. 修复轮 B（cell split 双实现）——✅ 通过

- **算法**: `_split_with(literal_backslashes)` 单遍确定性扫描 + 转义优先（span 内 `` \` `` 为方言 documented escaped-backtick 形式，记录 `span_escapes`）+ 孤悬回溯（`closed=False` 且有 `span_escapes` 时，从最后转义符逐个降级 `ordered[:take]` 重跑直到闭合）。正确性经 5 形状新旧对照机证（本审查探针，HEAD 旧实现 `git show` 加载对比）：

  | 形状 | 旧 | 新 | 判定 |
  |---|---|---|---|
  | pi-doc L97 尾反斜杠孤悬（`` `C:\Users\peter\.pi\agent\` ``） | 2（ragged 误报） | **3** | FAIL-on-buggy 成立——回归测试在旧实现下必红 |
  | 归档 review in-span escaped backtick（`` `String.raw\`...\`` ``） | 3 | 3 | 契约保留（bit 一致） |
  | span 外 `\|` | 2（`['a \| b','c']`） | 2 | 语义不变 |
  | 多个 in-span 转义且闭合 | 3 | 3 | bit 一致 |
  | 真 unclosed 无转义符 | 2 | 2 | 真 ragged 不被回溯掩盖（无 `span_escapes` 可降级，不进回溯） |
  | 全转义应力（`` `\`\`\` `` tail） | 2 | 3 | 回溯按设计闭合合法 CommonMark 尾反斜杠行 |

- **已闭合行 bit 一致**: 探针对 5 条已闭合行（含纯 code、无转义行）逐一断言 old==new（两实现分别）→ 全部 True——「escape-first pass already closed → untouched」声明可抽验成立。
- **双实现同步**: `loop_runtime_claims.py` 与 `loop_runtime_claim_attestation.py` 的 `_split_markdown_cells` 代码体逐行同构（diff 对照；注释差异是刻意的：claims 版带完整 rationale + REL-086-RELEASE-R1 L44 出处，attestation 版引用孪生实现并声明「intentionally has no dependency on the scanner」——符合叶模块无反向依赖的架构约束）；探针断言新 claims==新 attestation 全 case True；同步锁测试 `FEAT100AttestorCellSplitSyncTests`（2 方法，双实现同 fixture 双断言）质量充分——任一拷贝漂移即红。
- **4 份归档 review 契约保留**: `review-REL-086-RELEASE-R1.md` L19/L44 实存「code-span 内 `\|` 受 `_split_markdown_cells` 转义机制保护」原文（claims.py 注释引用的 L44 出处属实）；`review-FEAT-030-CODE-R0.md` L33 / R1 L24 实存 `` `String.raw\`...\`` `` 形态（测试 fixture 锚点属实）；`review-FIX-373-CODE-R0.md` 经 REL-086-RELEASE-R1 L44 引用锚定（ragged 用例依赖转义契约面）；`review-REL-086-RELEASE-R2.md` L57/L61 存 `\|` 等价转义叙述。DEC-360（decision-log L227）「①span 内转义优先 100% 保留②孤悬回溯」与实现逐条对齐；CommonMark 严格化否决有据（4 份归档明文依赖）。
- **6 项回归全绿（实测）**: claims 3（backtrack 闭合/in-span 单 span/out-of-span 字面量）+ attestation 同步锁 2 + verify_workflow Check 28b 回归 1 = `pytest -k FEAT100 + projection_sync_blocked_plan_face` → **6 passed**。

### 5. 验证复核（抽验）——✅ 完成（1 项环境性偏差已归因）

| 命令 | 结果 | 判定 |
|---|---|---|
| `check-governance --summary-only` | **exit 0**，33 issues（FAIL 26 + WARN 若干） | FAIL 全数指向 .governance 记录面（execution-packet 契约族/Check 17/Check 30 FIX-444 存量/28b 的 commit-msg CRLF）——与本 staged delta 直接相关的仅 F-R2-1 的 4 条 stale WARN（P2 已立案）；28b 不再 KeyError（根修生效面） |
| `pytest test_verify_workflow.py -k "LoopRuntimeClaim or FIX300DualCaliber or projection or pi"` | 1 failed / 45 passed / 1091 deselected | 唯一失败环境归因 F-R2-2（工作树 CRLF，非 staged）；LoopRuntimeClaim/pi/projection 语义面全绿 |
| `check-agent-adapters` | 7/7 runtime-verified（含 pi）EXIT=0 | ✅ |
| `git status --short` | staged=12（见被审面勘误 F-R2-3）；FIX-445 两文件（`infra/hooks/commit-msg`、`infra/tests/test_hooks.py`）均 ` M` 未 staged ✅；另有 `docs/research/pi-adapter-integration-research-0.98.0.md` ` M` 未 staged（不在被审面，未审其工作树改动，如实披露） | ✅ 与申报结构一致（文件数 12≠13 为计数口径勘误，非夹带） |

### 6. R1 遗留 P2/P3 处置确认——✅ 无悬空

- **F-C1**（staged 面披露缺口）: cc40646 message 实读含「披露〔CODE R0 F-C1/F-C2〕：staged 实 23 文件=申报 18+设计文档（含 F-1 出处勘误）+e2e 镜像 byte_copy 提前同步（逐字节一致）+research/两审查报告」——已落实。
- **F-C2**（research 文档 ragged）: 由修复轮 B 引擎根修承接（EVD-1717 B 项「两轮文档修复无效因缺陷在引擎」；本审查 6 项回归 + 新旧对照机证根修有效）——闭环，无悬空。

### 7. 越权检查——✅ 通过

staged 12 文件不含 `.gitattributes`、不含 version-projections 配置面；`projection.py` 改动仅限 `check_projection_sync` 适配层返回 schema（未触碰 pattern 匹配/CRLF 容忍逻辑——该面属 FIX-451，plan-tracker P1 在案）；FIX-445 两文件未 staged。移交边界干净。

---

## 5 评审维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ | cell split 回溯算法 6 形状机证（含真 ragged 不掩盖）；projection 双路径 schema 恒稳实测；能力面与 policy/矩阵/机检四面一致；manifest 与 EVD/DEC 锚点逐条对齐 |
| 安全性 | ✅ | 纯解析器+声明性配置变更，无输入注入新面、无敏感数据、无权限面变化；CRLF 判定不改写文件 |
| 可维护性 | ✅ | 根修在归位层非调用点掩盖；双实现同构+同步锁+叶模块无反向依赖声明；注释携带 rationale 与归档出处（可追溯）；P2 备注：exemption re-anchor 欠账（F-R2-1） |
| 性能 | ✅ | 回溯最坏 O(k·n)（k=in-span 转义数，表格行级 n/k 极小）；schema 补齐零运行时成本；无 N+1/批量问题 |
| 测试覆盖 | ✅ | 6 项回归全绿且 FAIL-on-buggy 经旧实现对照机证；pi 夹具/矩阵夹具与真实面同构；抽验选择器 45 passed（1 failed 环境归因非代码） |

## AI 代码专项 5 项

1. **mock 残留**: 无——测试内 patch 均为局部 fixture（`patch.object` 上下文管理器），产品代码零 mock。
2. **硬编码返回值**: 无——manifest evidence 是声明性文档且逐条锚定 EVD/DEC（实读核对）；解析器返回由算法推导。
3. **幻觉 API 调用**: 无——extension TS 代码不在本 delta（R1 已审）；本 delta 为 Python infra + 配置/文档，引用的模块/函数（`check_projections`/`build_projection_plan`）均实存。
4. **未实现 TODO**: 无——grep 无新增 TODO/FIXME 残留于 delta。
5. **过度实现**: 无——12 文件全部可归因（增量轮 7 + 修复轮 6 − 跨轮重叠 1）；无超出两逻辑变更的搭车改动。

## 硬门槛裁决

| 门槛 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5 | ✅ |
| 每条发现标注级别 | 100% | 4/4（P2×1、P3×3） | ✅ |
| 设计一致性（ADR/DEC 契约） | 已完成 | DEC-359/DEC-360/EVD-1715/1716/1717 逐条比对 | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 | ✅ |

## 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）。delta 可合并：能力升级诚实性四面（manifest/policy/矩阵/README+SKILL）一致且证据链闭环；两个根修（schema 归位、转义回溯）实现正确、契约保留经归档对照机证、6 项回归 FAIL-on-buggy 有效。备注 F-R2-1（P2，exemption re-anchor 建议本轮顺手闭合）与 F-R2-2/3/4（P3，环境归因/勘误/治理记录面交 Coordinator）不构成阻塞。

— Code Reviewer Agent，2026-10-16
