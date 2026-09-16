<!-- machine-record round suggestion: REVIEW-FIX-342-R1 / REVIEW-FIX-344-R1 -->
# review-FIX-342-344-CODE-R0 — 合并代码审查报告（一报告双 task）

- **审查对象**：工作树未提交改动·本批 6 文件（基线 HEAD `a2606374b6c3cce9e9b74e49bbc9b3a07e6298d2`）
- **审查者**：Code Reviewer Agent（独立于 Developer）
- **日期**：2026-09-17
- **结论**：**APPROVED_WITH_NOTES**（unresolved_blockers=0；P0=0，P1=0；P3 备注 5 条）
- **机录 round 建议**：本报告通过即复审链终态；若后续返工，下轮 record id 建议 `REVIEW-FIX-342-R1` / `REVIEW-FIX-344-R1`

## 0. 范围纪律确认（恰 6 文件）

| # | 文件 | task | 改动 |
|---|------|------|------|
| 1 | `infra/task_priority.py` | FIX-342 P2-1 | `_ARCHIVE_NON_COMPLETED_MARKERS` +5 复合词 + docstring |
| 2 | `infra/archive.py` | FIX-342 P2-2/P3-2 | `_DECISION_SCHEMA_COLUMNS=11` + header 区扫描 + fallback `!=11` fail-closed |
| 3 | `tests/test_task_priority.py` | FIX-342 | +2 用例（复合词单元 + index 端到端）+ P3-3 缓存升级用例 |
| 4 | `tests/test_archive_decision_attribution.py` | FIX-342 | +`Fix342DefensiveSurfaceTests` 5 用例 |
| 5 | `infra/checks/review_domain.py` | FIX-344 | `_REVIEW_FILE_NAMESPACED_RE` + `_match_review_file_name` + `_lookup_review_file` slug 参数 + 30c matched 桶 + V8 行通道 slug 绑定 |
| 6 | `tests/test_verify_workflow.py` | FIX-344 | +`ReviewFileSuffixAwarenessTests` 9 用例 + FIX-314 docstring 契约更新 |

工作树中其余改动（`checks/loop_runtime_claims.py`、`checks/dsh_boundary.py`、`test_dsh_boundary.py`、`test_dsh_contract.py`、`test_loop_runtime_claims.py`、untracked `core/loop-runtime-claim-exemptions.json`）属并行批 B（FIX-320/322），**已按任务边界排除**，其 diff 未纳入本审查。untracked `infra/_probe_at_literals_tmp.py`、`infra/_probe_findings_tmp.py` 为临时探针残留（见 F5）。

## 1. 独立复现证据（全部从仓库根 / %TEMP% 纯注入运行）

| # | 复现项 | 命令/方式 | 结果 |
|---|--------|----------|------|
| E1 | 定向四套件 | `python -m pytest test_task_priority.py test_archive.py test_archive_decision_attribution.py test_verify_workflow.py -q` | **1135 passed / 2 failed / 93 subtests**（265.94s）；2 红为 `LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report`、`FIX300DualCaliberAgreementTests::test_fixture_identity_mode_agrees_with_engine_on_present_sources` |
| E2 | 2 红基线归属 | `git worktree add --detach %TEMP%\wt-baseline HEAD` 后同命令定向跑 | **HEAD 纯基线上 2 红同样失败** → 基线既有红（loop-claims/FIX300 域），与本批 6 文件零关联（worktree 已清理） |
| E3 | 新类 9 用例 | `pytest test_verify_workflow.py::ReviewFileSuffixAwarenessTests -v` | **9 passed in 0.13s** |
| E4 | R0 30c 探针复刻（改前 vs 改后） | %TEMP% 加载 `git show HEAD:review_domain.py` 为独立模块 vs 工作树版，同一探针数据（canonical APPROVED + namespaced NEEDS_CHANGE 带字段 + 第二半面机器行） | HEAD：`verdict=WARN, 1×V8 假 WARN（"file review-FIX-410-R0.md lacks the field"——借查 canonical 实证）、files_judged=1、unmatched=1`；NEW：`verdict=PASS, 0 warnings, files_judged=2, unmatched=0` ✅ 与 Developer 声明一致 |
| E5 | live 30c 指纹（改前 vs 改后） | 同 E4 双版对 live `.governance` 无参运行 | stats **逐字节一致**：`files_judged=147, files_unmatched=186, rows_judged=159, rows_machine=157, rows_scanned=445, rows_non_review=186, files_undated=29, rows_undated=14, files_legacy_skipped=1`；warnings 两侧均 2 条且内容一致（live 既有 WARN，非本批引入）✅ |
| E6 | archguard | `python infra/verify_workflow.py archguard-ratchet` | **PASS（0 violations）**；R1 `mainfile loc 24453 ≤ anchor 24453`（verify_workflow.py 零增行）✅ |
| E7 | FIX-342 P2-1 复合词探针（改前 vs 改后） | %TEMP% HEAD `task_priority.py` vs 工作树版，`_archive_index_status_is_completed` | 5 复合词（未完成/待完成/尚未完成/完成条件未满足/任务完成度50%）HEAD=True → **NEW=False 全 FIXED**；6 正向对照（含 `待执行/暂停→✅ 完成` escape）两侧 True 零翻转 ✅ |
| E8 | FIX-342 P2-2 headerless 探针 | 双版 `_decision_archive_version(headerless 6-cell row, None, {FIX-084:0.77.0})` | HEAD=`('0.77.0','would_archive')`（R0 误读第 5 格实证）→ NEW=`(None,'decision_row_too_short')` fail-closed ✅；canonical 11 列行两侧 `would_archive` 零翻转 ✅ |
| E9 | FIX-342 P3-2 header 区扫描 | 双版 `_decision_related_column_index` | body-decoy 文件：HEAD=0（正文表劫持实证）→ NEW=None ✅；真实 header 文件两侧 =9 零翻转 ✅；**无 separator 文件两侧 =0（零回归实证）** ✅ |
| E10 | live index 300 IDs sha | 双版 `parse_archive_index_completed_ids(archive/index.md)` | 两侧 **count=300、sha 一致**（`42b341862ba6f71e…`）✅ |
| E11 | archive dry-run 逐字对照 | 双版模块 patch 至真实根后 `migrate_auto(dry_run=True)` + summary/explain 格式化 | 输出 **1379 字节逐字节一致**；explain 决策面 `would_archive=0`（HEAD 侧输出一致 → 0→0 零翻转）✅ |
| E12 | tpa 指纹 | 双版 `run_cli_analysis(force=True)` 对 live plan-tracker | stdout **4191 字节逐字节一致**（exit 0，report sha256 `5ea73fd3933c3cc2cde50c8c316708a2`）✅ |

## 2. 五维度逐项结论

### 2.1 正确性 — PASS

- **复合词表边界**（审查重点 1）：`_archive_index_status_is_completed` 的判定序为 veto→✅ escape→positive（task_priority.py L665-668）。「完成」出现在「未完成/待完成/尚未完成/完成条件未满足/完成度」中时 veto 词先命中并直接 `return False`（无 ✅ 时），positive 子串不再可达——词序正确，E7 实证。✅ escape 语义保持（`待执行/暂停→✅ 完成` 两侧 True）。
- **11 列常量一致性**：`_DECISION_SCHEMA_COLUMNS = 11` 与真实 `.governance/decision-log.md` header（`编号|日期|主题|背景|决策内容|备选方案|选择原因|影响范围|决策人|关联任务|后续动作`，L5）逐列核对 = **11 列一致**。
- **header 区终止条件**：break 于首个 separator 行（`^\|[\s\-:|\t]+\|$`）；无 separator 文件不 break、全文件扫描，与旧版行为一致（E9 零回归实证）。
- **namespaced 正则 slug 严格性**：`^review-([A-Z]+-\d+)-R(\d+)-([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)\.md$`（大小写敏感）——slug 字符类与写入端 `_reviewer_slug` 输出形态（小写 alnum run + 单连字符 + 无首尾连字符，review_record.py L91/L100-108）**逐字符吻合**，见 §3。
- **V8 行通道 slug 绑定归属**：`slug_by_cid` 以 canonical prefix（`REVIEW-{task}-R{n}`）为 key，V8 lookup 仅在 `slug_by_cid.get(cid)` 命中时改查 `review-{task}-R{n}-{slug.lower()}.md` 单一候选、无 canonical fallback（review_domain.py L2779-2782/L2983-2984）——归属自身文件，无借查。E4 实证改前借查形态消失。
- **Check 30 聚合语义**：`_collect_live_review_sequences` 中 namespaced 文件以 canonical cid（`REVIEW-{task}-R{n}`，slug 丢弃）并入同一 (task, round) 聚合，重复轮合并仍取最 terminal 结论（L2570-2609）；测试 `test_dual_half_same_round_aggregate_most_terminal_wins` 通过。

### 2.2 安全性 — PASS

- 无输入注入面变化：正则均锚定（`^…$`/`\b`）；slug 小写化后拼文件名，写入端 slug 已 fail-closed 拒绝空 slug（review_record.py L427-430）。
- 无敏感数据硬编码；无权限边界变化；无命令执行面变化。
- fail-closed 方向正确：结构不可信行（`!=11` 列）拒绝归档（E8）；缺自身文件/缺字段保持 WARN 而非静默通过（E4 + 两个不放宽边界测试）。

### 2.3 可维护性 — PASS

- 注释质量高：`_DECISION_SCHEMA_COLUMNS` 注释逐列枚举 schema；`_REVIEW_FILE_NAMESPACED_RE` 注释记录大小写敏感的设计动机（live ~150 ROLE-token 文件防翻转）；FIX-314 docstring 契约更新如实标注 superseded stance（断言修正披露合理——旧 stance「namespaced FILES 在 30c 名形之外」被本修复取代，契约文档同步而非静默改语义）。
- `_match_review_file_name` helper 消除三处正则解析重复；函数长度均 <50 行。

### 2.4 性能 — PASS

- 无算法复杂度回退：slug_by_cid 为 per-row O(1) dict 构建；`_match_review_file_name` 为两次定长正则尝试；header 区扫描较旧版提前 break（严格不减性能）。

### 2.5 测试覆盖 — PASS

- FIX-342：复合词 5 负向 + 6 正向对照、index 端到端、缓存升级（P3-3 机制隔离验证——legacy 无 key + index 在场 → 强制 full run）、headerless 4/6/10/12 列边界、canonical 零翻转、decoy 遮蔽红→绿。
- FIX-344：9 用例覆盖三盲区（a 假 WARN / b unmatched 逃逸 / c 聚合回归）+ 两个不放宽边界（无自身文件 WARN、缺字段 WARN 且归属自身文件）+ ROLE-token 零翻转守卫 + CLI 端到端闭环（真 `write_review_record` 双审查方 → Check 30c 全绿、files_judged=2）。
- 红→绿可复现性：改前红由本审查在 %TEMP% HEAD 模块上独立复现（E4/E7/E8/E9 的 HEAD 侧），改后绿由 E1/E3 独立复现。

## 3. 跨文件契约核对（审查重点 3）：review_record.py 写 ↔ review_domain.py 读

| 契约面 | 写入端（review_record.py，未在本批改动） | 读取端（review_domain.py，本批） | 判定 |
|--------|------------------------------------------|----------------------------------|------|
| 文件名 slug 形态 | `_reviewer_slug`：`[^a-z0-9]+ → "-"` + `strip("-")` → 小写 alnum、单连字符、无首尾连字符（L100-108）；namespaced 名 `review-{task}-R{n}-{slug}.md` 仅在 canonical 已存在且 owner 不同时产生（L431-445） | `_REVIEW_FILE_NAMESPACED_RE` slug 组 `[a-z0-9](?:[a-z0-9-]*[a-z0-9])?`（大小写敏感） | **一致**（字符集、单连字符、首尾约束全吻合；单字符 slug 亦匹配） |
| evidence id slug 形态 | namespaced 时 `REVIEW-{task}-R{n}-{SLUG.upper()}`（L446-449）；canonical 占位者不加 slug | `_REVIEW_ROW_ID_SLUG_TAIL_RE`：`(REVIEW-[A-Z]+-\d+-R\d+)-([A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)`，group1=canonical prefix 与行扫描既有 finditer 的截取形态对齐 | **一致**（大写化 ↔ `[A-Z0-9-]` 类；key 对齐实证于 E4 探针） |
| round-less namespaced 名 | 写端**不存在**该形态（canonical_name 恒带 `R{n}`，L422） | 读端不识别（namespaced RE 强制 `-R(\d+)-`） | **一致**（遗留裁决 ③，见 §5） |
| 端到端闭环 | CLI 双审查方写入 | Check 30c 全绿 | `test_cli_two_reviewer_records_pass_check30c` 独立运行通过（E3），含 `files_unmatched=0, files_judged=2, verdict=PASS` 断言 |

## 4. 不放宽证明（审查重点 2）

1. **30c V7 对 namespaced 真覆盖**（fixture 反相）：`test_namespaced_handwritten_file_warns_v7`——namespaced 手写文件（去 marker）→ V7 WARN，`files_unmatched=0`（进 matched 桶**不是豁免**）。独立运行通过。
2. **V8 两边界不放宽**：`test_namespaced_row_without_own_file_still_warns_v8`（自身文件缺失、即使 canonical 兄弟在场 → WARN）；`test_namespaced_file_without_next_round_still_warns_v8`（缺 next_round → WARN 且 reason 指向自身 namespaced 文件、断言不指向 canonical）。独立运行通过。
3. **live 零翻转指纹独立复现**：E5（30c stats 147/186 逐字节一致 + warnings 2/2 同内容）、E10（index 300 IDs sha 一致）、E11（dry-run 1379 字节一致 + would_archive 0→0）、E12（tpa 4191 字节一致）、E6（archguard 24453 零改动）。

## 5. 遗留裁决三项评估（审查重点 5）——三处均有意设计且如实合理

| # | 裁决 | 证据 | 评估 |
|---|------|------|------|
| ① | ROLE-token 大写尾文件（~150 live）保持 files_unmatched | `_REVIEW_FILE_NAMESPACED_RE` 大小写敏感（无 IGNORECASE）；`review-FEAT-002-CODE-R0.md` 对 canonical/namespaced 两 RE 均 None；E5 live stats 两侧 186→186 一致 | **合理**。重分类将翻转 Check 30 V1-V6 与 30c files_unmatched 基线，违反零回归纪律；ROLE-token 文件的结论仍走行通道 V7 扫描（row-level 覆盖不缺失），非执法空洞 |
| ② | V8 严格不借查（无自身文件/缺字段均 WARN 且归属自身） | `_lookup_review_file` slug 分支单一候选、无 canonical fallback；两个边界测试 | **合理**。借查即掩盖复审义务不可机读的事实（E4 实证借查制造假 PASS 方向的输出）；fail-closed 是 30c 的既定判定纪律 |
| ③ | round-0 裸 slug 形态（`review-{task}-{slug}.md`）不识别 | namespaced RE 强制 `-R(\d+)-` 段；写端该形态不存在（§3 行 3） | **合理**。识别一个写端永不产生的形态只会给手写文件开豁免口子；不识别 = 零放宽且零成本 |

## 6. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | 测试用 tempfile 真实文件 + 真 `write_review_record` CLI 产物断言；无 MagicMock/monkeypatch 伪造返回值充当行为 |
| 2 | 硬编码返回值 | **无** | 产品 diff 无 stub/常量返回；探针词表与列数常量均带 schema 依据注释 |
| 3 | 幻觉 API 调用 | **无** | diff 调用的所有函数/常量（`_match_review_file_name`、`_DECISION_SCHEMA_COLUMNS`、`TPA_STATE_FILENAME`、`_archive_index_status_is_completed` 等）均在对应模块实存（逐一读源核对）；测试 import 均可解析（E1 全套件收集成功） |
| 4 | 未实现 TODO | **无** | diff 无 TODO/FIXME/占位实现；docstring 均为已实现行为的契约描述 |
| 5 | 过度实现 | **无** | 两个正则 + 一个解析 helper + 一个常量 + 词表 5 项，均为 R0 finding 的点对点修复；无投机性抽象/无未使用分支 |

## 7. 发现列表（全部非阻塞）

- **F1（P3，FIX-344·review_domain.py L2933-2935）**：`slug_by_cid` 以 canonical prefix 为 key——同一 id_cell 若同时含同 prefix 的裸 canonical id 与 slug id（手写混合行），裸 id 的 V8 lookup 会被误绑至 slug 文件。机器写入端每行单 id 不触发；此类行本就先吃 V7 无-marker WARN。建议（下轮可选项）：slug 绑定改为按 id 出现位置配对。
- **F2（P3，FIX-344·review_domain.py L2649-2650）**：小写 role-token 尾的历史文件形态（如 `review-X-R0-code.md`，若存在）会被重分类为 namespaced 机器文件进判定面。live 零翻转实证（E5：186→186）表明当前不存在此类文件；风险仅面向未来手写命名。建议：归档 README/约定中声明 namespaced 尾仅限 reviewer slug。
- **F3（P3，FIX-342·task_priority.py L641-645）**：负向词表仍是开放枚举——`预完成`/`即将完成`/`基本完成` 等含「完成」的未达成形态不在表内（substring positive 仍会误判）。本次为探针驱动最小面修复，真实数据零翻转（E7/E10/E12）；后续出现新词形时按同一红→绿路径增补即可。
- **F4（P3，FIX-342·archive.py L769-775）**：无 separator 的畸形 decision-log 在 P3-2 后仍全文件扫描（与旧版行为一致，E9 零回归实证）——正文 narrative 表带「关联任务」理论上仍可应答 headerless 场景；但该场景同时要求 11 列 canonical 行才走 fallback（E8），实际误归档面已收窄至可忽略。如实记录既有边界，不要求修改。
- **F5（P3，流程·工作树卫生，归属批 B/流程面）**：untracked 临时文件 `infra/_probe_at_literals_tmp.py`、`infra/_probe_findings_tmp.py` 残留于工作树。非本批 6 文件；提交前应清理或显式纳入批 B 范围，避免误入 commit。

## 8. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 判定 |
|--------|------|------|------|
| P0 阻塞 | = 0 | 0 | ✅ |
| P1 关键 | = 0（blocking = P0/P1） | 0 | ✅ |
| 5 维度全覆盖 | 100% | §2.1-2.5 逐项有结论 | ✅ |
| 每条发现标注级别 | 100% | F1-F5 均 P3 | ✅ |
| 设计一致性 | 已完成 | §3 契约表 + §5 裁决表；R0 findings（P2-1/P2-2/P3-2/P3-3/30c 三盲区）逐点对应修复 | ✅ |
| AI 专项 5 项 | 全部完成 | §6 逐项 | ✅ |
| 独立复现 | 四套件+新类 9+R0 探针+live 指纹+archguard | §1 E1-E12 | ✅ |
| 范围纪律 | 恰 6 文件 | §0 | ✅ |

## 9. 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）

Developer 三组声明（FIX-342 探针红→绿与真实数据零翻转、FIX-344 30c 三盲区修复与 live 基线零翻转、共通 archguard/套件口径）**逐项独立复核属实**；2 个套件红经 HEAD worktree 复跑确认为 loop-claims/FIX300 域基线既有红，与本批无关。三处遗留裁决均有意设计、依据充分、如实披露。P3 备注 5 条不阻塞合并，F1-F3 建议随下一次触及对应文件时顺带评估。
