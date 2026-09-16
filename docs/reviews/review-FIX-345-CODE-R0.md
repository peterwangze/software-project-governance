<!-- machine-record: FIX-345 | reviewer: code-reviewer | round-suggestion: REVIEW-FIX-345-R1 | verdict: APPROVED_WITH_NOTES | unresolved_blockers=0 -->

# Code Review R0 — FIX-345 authority source records 归档感知重锚

- 审查对象：git index 暂存 4 文件（+82/−14），基线 HEAD `0462f3b`
- 审查者：Code Reviewer Agent（只读审查；反相全部在 `%TEMP%\fix345-r0\` 临时副本内，真实 `.governance/` 零写入）
- 结论：**APPROVED_WITH_NOTES**（unresolved_blockers=0，零 P0/P1；4 条 P2/P3 建议与遗留裁决见 §6/§7）

## 1. 范围与基线核实

| 项 | 结果 | 证据 |
|---|---|---|
| 恰 4 文件 | ✅ | `git status --porcelain` = 4×`M `（已暂存、无未暂存改动），无 untracked |
| 工作树==index | ✅ | `git diff --stat`（未暂存）为空 |
| 基线 HEAD | ✅ | `git rev-parse HEAD` = `0462f3bb8b27787ca231b3a1334cbe59521d6b70` |
| 增量 | ✅ | `git diff --cached --stat` = 82 insertions / 14 deletions，与任务描述一致 |

## 2. 锚正确性（审查重点 1）——全部独立验证通过

方法：不 import 被审模块，按文档语义独立重实现 `_canonical_text`（utf-8-sig 解码 + CRLF/CR→LF + NFC）与 `_sha_text`（sha256(NFC(text).encode("utf-8"))），对真实文件逐行 `startswith(prefix)` 计数并重算摘要。脚本与输出存 `%TEMP%\fix345-r0\verify_anchors.py`。

| 记录 | 文件 | 唯一性 | digest 独立重算 |
|---|---|---|---|
| DEC-104 | `.governance/archive/decisions/decisions-v0.1.0-0.78.0.md`（123,221 B） | `> | DEC-104 |` 前缀命中 = **1**（文件内另 2 处 DEC-104 提及均非该前缀：`> | DEC-133 |` 行内引用与 `## DEC-104:` 标题） | `ed1cadba…b61` **匹配** |
| EVD-707 | `.governance/evidence-log.md` | `\| EVD-707 \|` 命中 = **1** | `8aa48e27…e69` **匹配**（未漂移） |
| AUDIT-133 | `docs/requirements/loop-engineering-post-implementation-audit-0.66.0.md`（13,897 B） | `**Task**: AUDIT-133` 命中 = **1**（另 4 处提及均非行首前缀） | `90bc4ef9…0e9` **匹配** |

EVD-707 未动核实：authority JSON 的 EVD-707 记录（path/prefix/sha256 三元组）HEAD↔index 逐字节一致。

## 3. 双锚 lockstep 与 policy 面未动（审查重点 3）

- **代码↔JSON 逐字段一致**：`REQUIRED_SOURCE_RECORDS`（.py L139-143）与 `source_records`（JSON L19-38）解析后三元组 `code_face == json_face == True`（3 记录 × 3 字段），记录键集恰为 `{record_id, path, line_prefix, sha256}`。
- **AUTHORITY_SOURCE_RECORD_DRIFT 自洽**：`_validate_authority`（L1267-1275）以代码常量对比 JSON 面，两面同步重锚后守卫不再触发——CLI product_release 0 findings 实证（§5）。
- **policy 面未动**：`REQUIRED_POLICY_SHA256`（.py L109）HEAD↔index 相同 = `3e22d0bd…2122`；JSON `policy_sha256` HEAD↔index 相同；两者互相相等。「本任务只动 source_records 面」声明**实证成立**。
- **旧 digest 零残留**：`7666ace7…` / `c3fbd2e4…` 全仓 grep 0 命中——不存在任何仍钉旧值的沉默面。

## 4. 重锚必要性与断锚 fail-closed 语义（审查重点 2、选型验证）

- **旧锚确已断**：hot `decision-log.md` 中含 `DEC-104` 子串的行 = **0**；hot `plan-tracker.md` 中 `**P0** | AUDIT-133` = **0**——FIX-343 归档迁移后 HEAD 代码锚必然 fail-closed（红态 BLOCKED 2×AUTHORITY 的成因链完整、可信）。
- **归档迁移断锚 = 设计预期（任务指定验证项）**：DEC-104 锚现在 `.governance/archive/` 内，未来归档合并/移动该文件 ⇒ 锚文件缺失 ⇒ `AUTHORITY_SOURCE_MISSING` ⇒ BLOCKED（负例 a 实证同型）；编辑 ⇒ DIGEST、复制 ⇒ OCCURRENCE（负例 b/c 实证）。移动、编辑、复制三类扰动全部 fail-closed，强制走治理重锚。✅
- **REQUIRED_ROOT_UNAVAILABLE drift 形状仍锁死**：FIX300 `test_identity_host_source_drift_reproduces_divergence_shape` 与 `test_fixture_identity_mode_agrees_with_engine_on_missing_sources` 断言首缺失串 = `.governance/archive/decisions/decisions-v0.1.0-0.78.0.md`，**3/3 通过**。

## 5. 独立复现（硬门槛，全部自仓库根执行）

| 项 | 命令 | 实测 |
|---|---|---|
| CLI product_release（绿） | `verify_workflow.py check-loop-runtime-claims --product-root . --project-root . --scan-mode product_release` | **exit=0，verdict=PASS，findings=0，exemptions=4**（id 与 `REQUIRED_EXEMPTION_IDS` 逐一相符），candidates=780 |
| FIX300 双口径 | `pytest test_verify_workflow.py::FIX300DualCaliberAgreementTests` | **3 passed**（105.5s） |
| 新负例单测 | `pytest …::test_forged_source_records_fail_closed` | **1 passed** |
| inventory 单测 | `pytest …::test_real_repository_inventory_complete_and_within_budget` + `test_clean_complete_inventory_passes` | **2 passed** |
| archguard（致命栅栏） | `verify_workflow.py archguard-ratchet` | **PASS，0 violations**（R1 mainfile 24453≤anchor only-down；R2 47 sites/37 files；R5 84/84+71/71；R7 regen deterministic） |
| manifest | `check-manifest-consistency` | **PASS**（canonical 707 / actual **791**）——「manifest 791 PASS」✅ |
| xref | `check-cross-references` | **PASS**（无 dangling/deprecated/circular） |
| CLI 级三负例（%TEMP% 临时副本，7 文件按需拷贝；基线副本先跑 **PASS exit=0** 证明副本等价） | (a) 删除归档锚文件 (b) 复制锚行 (c) 锚行尾加 `X` | **(a) exit=1 BLOCKED `[AUTHORITY_SOURCE_MISSING]`；(b) exit=1 BLOCKED `[AUTHORITY_SOURCE_OCCURRENCE]`；(c) exit=1 BLOCKED `[AUTHORITY_SOURCE_DIGEST]`**——各恰 1 条 finding，反相干净 |

## 6. 测试适配质量 + AI 专项（审查重点 4）

**递归拷贝集（parents 逻辑）**：`_drifted_host` 拷贝集 = 5 热文件 + `AUTHORITY_ANCHOR_SOURCE_NAMES`（2 锚目标）= **恰好 identity 子-phase 解析集（HOST_PATHS ∪ source_records）的并集**，不宽不窄。`target.parent.mkdir(parents=True, exist_ok=True)` 只建祖先目录、不拷目录内容——**无过宽拷入**；evidence-log 在两集合交集处只拷一次——**无冗余**。拷贝源 `_INFRA_DIR.parents[2]`：`_INFRA_DIR = tests/..` = infra 目录 ⇒ `parents[2]` = 仓库根，正确（既有模式，非本任务引入）。

**AI 专项 5 项**：
1. mock 残留：无新增。既有 `patch` 用法均为引擎级 `HOST_PROJECT_ROOT` 重定向与契约常量注入（fixture 惯例，docstring 明示 "no scanner mocks"）。
2. 硬编码返回值：无。digest 常量是代码锚定机制本身（与改动前同构），非 mock。
3. 幻觉 API：无。引用的 finding 码（MISSING/OCCURRENCE/DIGEST/RECORD_DRIFT/RECORDS_EMPTY）在 L1259-1315 全部真实存在；stdlib-only。
4. 未实现 TODO：diff 无 TODO/FIXME。
5. 过度实现：无。16 行注释为任务要求的归因文档（双锚 lockstep 义务 + policy 面未动声明），内容与事实逐句相符；无夹带重构。

## 7. Findings 与遗留裁决

**P0/P1：无。**

- **P3-1（声明措辞）**「archguard 38 OK」不可按字面复现。可复现事实：致命栅栏 `archguard-ratchet` = PASS 0 violations；advisory `check-architecture-health` = **38 条 findings（8 ERROR + 30 WARN，均为改动集外文件的既有项：verify_workflow.py / e2e 投影 / archive.py 等，advisory 不阻塞）**；`check-duplicate-code` = 5 对中 3 ERROR（`__init__.py` 100%、`cleanup.py` 89.2%、`resolve_entry.py` 100%，同样不在改动集，advisory）。落地证据行建议改用精确口径（本节三句）。
- **P3-2（声明措辞）**套件计数："套件 60+1" 实为 **59+1=60**（HEAD 59 → index 60）；"850+1" 实为 **850+0**（HEAD=index=850，FIX300 仅改既有 3 测试不加方法）。实质声明（新增恰 1 测试、FIX300 3/3）为真，计数措辞虚高 1。
- **P3-3（余红归因，实证成立）**两余红均为 FIX-346 性能预算域、非本任务回归：① `test_three_run_performance_identity_and_median` FAILED 于 `assertLess(median, 8.0)`（实测 **14.78s**；开发侧 16.2s），其前置于同一测试内的 identity 一致性与 `verdict==PASS` 断言全部通过——功能面完好，红点纯在时限；② `test_claim_command_emits_complete_pass_report` FAILED 于 `subprocess.TimeoutExpired … 15 seconds`，而同一命令无超时约束下实测 PASS exit=0。新增扫描开销仅为一次性读取 123KB+14KB 两文件，数量级不可能跨越 15s 阈值。
- **P2-1（遗留①，确认成立）**AUDIT-133 历史 task 行归档缺口：hot plan-tracker 0 处、`.governance/archive/**/*.md` 全量 **0 处**、archive index 无条目——旧行被迁移删除但无归档落点（功能面由审计报告本体兜住，不影响本特性）。→ **数据批候选**，建议入账补归档。
- **P3-4（遗留③）**归档迁移断锚纪律：语义已验证（§4）。建议候选：`archive.py` 迁移在触碰 `.governance/archive/` 下文件时提醒「loop-runtime claim 源记录锚存在，迁移后 MUST 复跑 product_release 并按需治理重锚」。→ 未来任务候选，不阻塞。
- **遗留②**：P3-3 的两条实证建议记入 FIX-346 证据（median 实测值与 15s timeout 复现）。

## 8. 五维度裁决

| 维度 | 结论 |
|---|---|
| 正确性 | ✅ 重锚逻辑、lockstep、fail-closed 三分支独立复现全部正确 |
| 安全性 | ✅ 路径校验（`_safe_relative`/`_safe_join`）未弱化；反相仅落 %TEMP%；无敏感数据 |
| 可维护性 | ✅ 归因注释与事实一致；测试拷贝集有注释说明；命名清晰 |
| 性能 | ✅ 本任务无显著开销（+2 次小文件读）；既有超时红点归 FIX-346 域 |
| 测试覆盖 | ✅ 三负例（缺失/复制/篡改）单测 + CLI 双层覆盖；drift 形状锁死；恰新增 1 测试 |

## 9. 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`（无 P0/P1）。4 文件改动可合并；P2-1/P3-4 为遗留候选建议随本审查转 Coordinator 入账（数据批 / archive.py 提醒候选 / FIX-346 证据），不构成本次合并前置条件。

*取证留存：`%TEMP%\fix345-r0\`（verify_anchors.py、neg_run.py、cli_*.out）；本报告为唯一仓库内写入物。*
