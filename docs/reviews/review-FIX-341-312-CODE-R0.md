结论：**APPROVED_WITH_NOTES** ｜ round=0 ｜ unresolved_blockers=0 ｜ 机录 round 建议 = `REVIEW-FIX-341-R1` / `REVIEW-FIX-312-R1`

# Review — REVIEW-FIX-341-CODE-R0 + REVIEW-FIX-312-CODE-R0（一报告双 task，FIX-334/335 先例）

- **基线**：HEAD `8bd6a8a`，工作树未提交改动 6 文件（5 M + 1 untracked 新测试文件）
- **审查者**：Code Reviewer（独立复核，不转抄 Developer 声明）
- **方法**：逐行 diff 审查 + 定向三套件独立复现 + 全量基线对照（temp worktree @8bd6a8a + 治理数据物理拷贝）+ 活体验收三命令 + 反相实验（纯文本注入 / %TEMP% 副本；全程未触碰真实 `.governance/` 写面）

---

## 一、硬门槛执行记录（独立复现证据）

| 门槛项 | 结果 | 证据 |
|---|---|---|
| 定向三套件 | **245 passed + 1 failed（既有）** | `test_task_priority.py`+`test_change_triage.py`+`test_archive_decision_attribution.py`；唯一失败 `AgentLocksAcquireCliTests::test_cli_success_expected_new_and_warn_disclosure` 在基线 worktree 同样失败（agent-locks 域，与本 diff 无交集）→ 非本次引入 |
| RED 可复现 | ✓ | 基线 `import task_priority` 无 `parse_archive_index_completed_ids`（hasattr=False）；`compute_unblocked_tasks` 签名单参数 `(tasks: 'list')`——新测试在基线必然 ImportError+失败，声明 RED 机制自洽 |
| 活体：tpa | ✓ | `Total: 30 tasks — 15 completed, 10 unblocked, 5 blocked`（与声明一致；缓存复用提示出现，`--force` 语义正常） |
| 活体：archive dry-run | ✓ | tasks 30/30/0/30/0；**decisions 72/68/0/68/4（未知结构 DEC-060/193/194/195）**；risks 35/35/0/35/0；evidence 440/431/0/431/9 |
| 活体：check-governance --summary-only | ✓ | **70 issues**；基线（拷贝治理数据）同为 **70 issues**，FAIL 条目逐字一致 → 声明「基线零 diff」证实（注：temp worktree 用 junction 挂载时会触发 4 条 `REQUIRED_PATH_MISSING … junction/reparse path segment is forbidden` fail-closed 伪影，改物理拷贝后消除——75 vs 70 的表象差异全部来自该方法伪影） |
| 全量基线对照 | ✓ 方向零新增 | 当前 **61 failed / 3106 passed** vs 基线 **62 failed / 3078 passed**：当前**少 1 个失败**、**多 28 个测试（FIX-341/312 新增，全部通过）**；两侧尾部可见失败清单身份逐一重合（quickscan / LoopRuntimeClaimAdapter / FIX300×2 / HotFactSource×15 / ExternalProjectValidation 均为既有红身份）。注：比对基于总数 + 尾部可见清单（两份输出头部截断） |
| archguard-ratchet | ✓ PASS | R1 主文件 24453 ≤ anchor 24453（未动）；R7 regen deterministic=True；0 violations。task_priority/change_triage/archive 3 模块不在管理棘轮面（R3 managed=2 modules） |
| 反相实验 | ✓ | 见下文分节（纯 %TEMP%/文本注入，只读） |

## 二、Developer 声明逐项独立复核

| # | 声明 | 裁决 | 独立证据 |
|---|---|---|---|
| 1 | FIX-341 TDD RED→GREEN；负例四类 | **证实** | RED 机制基线复现（上表）；GREEN 定向 245 passed。负例四类对应测试齐全：index 未命中仍 blocked（`test_index_miss_still_blocks_fail_closed`）、热表 ⏳ 权威压过归档集（`test_hot_pending_dep_wins_over_archive_completed`）、归档非完成态不解除（fixture 9 个非完成 ID 全部 assertNotIn）、CLI 未知 ID fail-closed（`blocked_by=[FIX-971]` 断言） |
| 2 | 活体归因=数据缺口（行从未入档） | **证实（含补充）** | 解析真实 index.md → **292 个 completed ID（与声明精确一致）**；REL-076/FIX-162/FIX-319/FEAT-031/FIX-171 在整个 index.md 中**零出现**；进一步核实：5 个 ID 在归档 tasks 23 文件中均**无任务行**（FIX-162/FIX-171 仅 prose 提及），热表精确匹配也无以自身为 ID 的行——「任务行从未入档」归因成立，解析器判据无缺口 |
| 3 | FIX-312 TDD RED 5→GREEN 9；test_archive 126 零回归；DEC-187 晨间态探针 | **证实** | 9 个新测试全过；`test_new_decision_referencing_archived_task_is_retained` 即晨间态探针（FEAT-010@0.77.0 已归档 + FIX-310/307/308/309 热 → retained_active_task_ref）；全量失败清单中无 test_archive 任何条目 |
| 4 | dry-run 68 解析 + 4 短行 unknown；would_archive 0→0；risks/evidence 逐字一致 | **证实** | 基线 worktree 对照：旧判据 `decisions 72/72/0/72/0（no_archived_task_ref=72）` → 新判据 `72/68/0/68/4（too_short=4, no_task_family_ref=16, retained_active_task_ref=52）`；would_archive 0→0 零翻转；diff 仅 decisions 3 行，tasks/risks/evidence 逐字一致。4 个短行实证为真实结构残缺行（DEC-060=3 cells、DEC-193/195=5、DEC-194=6，canonical 11 列）→ 短行 fail-closed 是正确保守而非误伤 |
| 5 | 全量基线 ≥方向零新增；check-governance 70 零 diff；archguard PASS | **证实** | 见硬门槛表（62→61 方向改善 + 70/70 一致 + archguard PASS） |
| 6 | DEC-187 现居 `archive/decisions/decisions-v0.1.0-0.79.0.md` | **证实（含补充）** | 热 decision-log 无 DEC-187 行；归档文件含 `## DEC-187`。**补充事实**：归档内标注仍是 `归档版本: v0.77.0（关联 task 已归档）`——旧判据误判版本的遗留标注；且其 governing refs 中 **FIX-310/FIX-307 当前仍无归档任务行**（FEAT-010@0.77.0、FIX-308/309 已归档）→ 按新判据 DEC-187 现行归档属 premature archive |

## 三、FIX-341 分节结论（task_priority.py + change_triage.py + 两测试文件）

**正确性** ✓
- 段边界 load-bearing 正确：`## Task 索引` 精确 heading 匹配，任何 `#` 行重置节状态；Decision/Risk/Evidence 索引行共享 `| PREFIX-NNN |` 形状但被节边界隔离（fixture 有跨节泄漏负例，实证 DEC-187/RISK-039/EVD-641 不泄漏）。
- 判定序实现与文档一致：`status_map.get(dep)`（热表权威）→ `dep not in status_map and dep in archive_done`（归档层仅热 miss 触达）→ blocking（fail-closed）。热 ⏳ 行即使归档集含其 ID 仍阻塞——分支顺序保证。
- 复用的解析基建（`_ID_CELL_RE`/`_SEPARATOR_RE`/`_split_row`/`_strip_markdown`/`_COMPLETION_WORD`）全部验证存在且语义匹配。
- 缓存守卫正确：旧缓存无 `archive_index_mtime` 键 + index 存在 → None≠mtime 强制重跑（「one extra full run, never a stale report」属实）；index 不存在 → None==None 复用安全（报告确为 tracker 纯函数）。`should_reuse_cached_analysis(None,…)=False` 已验证。
- change_triage 接线正确：`governance_dir` 为 run_triage 参数；I/O 在 triage 流 I/O 层、`run_dependency_analysis` 保持纯注入；新键 `archive_resolved_deps` 经查 verify_workflow.py 无 strict-key 校验消费方，无破坏面。

**保守性/fail-closed 不倒退** ✓（一处 P2 防御缺口，非现行缺陷）
- 解析失败全路径保守：None/空/非索引文本 → 空集 → 全部回退热表 fail-closed；I/O 异常（OSError/ValueError）→ 空集不抛。
- **P2-1（FIX-341）完成词表假阳面**：负向 marker 表不含否定-完成复合词，正向 substring「完成」命中 `未完成`/`待完成`/`完成条件未满足`/`任务完成度50%`（探针实证全部 →True）。真实 index 当前 292 个解析行状态词分布全部为完成语义（已完成×194/完成×76/已发布×16/发布完成×6/…，零假阳），且 ✅ escape 对「待执行/暂停→✅ 完成」的处理语义正确——故为防御面缺口而非现行缺陷。影响面=tpa/triage 的 blocked 判定偏乐观，无写破坏。建议：负向表补「未完成/待完成/尚未完成」，或正向改完成词边界（如 `(?<![未待尚])完成`）。

**I/O 纪律** ✓
- `parse_archive_index_completed_ids` 纯文本注入；`read_archive_index_completed_ids`/`_archive_index_mtime` 为文档化的参数化 I/O 例外且只在 CLI/`run_triage` 接线层调用；`compute_unblocked_tasks`/`run_dependency_analysis` 零 I/O。

**测试质量** ✓
- 断言双向非自证：CLI 测试同时断言 resolved 行出现与 blocked 行精确字符串不存在；缓存测试 utime+mtime 前移后断言无「复用上次分析」。
- `test_duplicate_rows_any_completed_wins` 覆盖索引重复行 any-completed-wins 语义。
- P3-3（建议）：未覆盖「旧缓存（无 mtime 键）+ index 存在」的升级场景单测（当前仅靠 `if reuse: reuse = …` 一行守卫）。

## 四、FIX-312 分节结论（archive.py + 新测试文件）

**正确性** ✓
- 列定位：header 精确 cell「关联任务」扫描返回 0-based data-cell index（11 列 schema → idx 9，验证）；headerless 回退 canonical 倒数第二列（test_archive 既有 fixture 实为 11 列 headerless 行，`[-2]` 恰为关联列——既有两测在新判据下语义不变：DEC-001 全 ref 已归档 → would_archive=1；DEC-050 → 保留，仅 reason 从 no_archived_task_ref 变为 retained_active_task_ref，断言不涉 reason）。
- 负向 lookbehind `(?<![-A-Z])([A-Z]+)-(\d+)\b`：REVIEW-FIX-310/EVD-FIX-247 的内嵌 ID 不被提取（与 task_priority._ID_TOKEN_RE 同纪律）；cross-entity（REVIEW-/DEC-/RISK-）再经 `_is_task_family_id` 过滤——双保险。
- max semver：`_version_to_tuple` 对垃圾版本返回 None → `(0,0,0)`，但 refs 已先经 unarchived 过滤，且垃圾版本最终被 `_version_in_range` 判 False → ref_version_out_of_range 保守保留。
- reason 单源收集（FIX-301 契约保持）：`decision_row_too_short` 正确加入 `_EXPLAIN_UNKNOWN_REASONS`（unknown_structure 桶），活体 dry-run 4 短行入桶可审计。

**保守性/fail-closed 不倒退** ✓（一处 P2 信任边界与文档声明的偏差，非回归）
- 全 refs 已归档才迁移（缺 ref=活跃/未知 → retained_active_task_ref）；结构不可信（related_idx 溢出/len<4）→ too_short 入 unknown_structure；无 task-family ref → 保留。dry-run would_archive 0→0 零翻转实证无行为面外溢。
- **P2-2（FIX-312）headerless 短行 fallback 信任边界**：`related_idx is None` 且 `4 ≤ cells < 11` 时以 `data_cells[-2]` 为关联列——该 cell 在残缺行中并非关联任务列，title/ctx 列的已归档 ref 会被误当 governing ref（探针实证：headerless 6-cell 行 `| DEC-300 | date | title | ctx | FIX-084 | scope |` → would_archive）。与 docstring「structurally short row → retained fail-closed」的信任边界声明不一致（仅 len<4 或 related_idx 溢出触发 too_short）。缓解因素：真实 decision-log 有 header（fallback 不触发）；比旧 whole-line 判据严格得多（探针中 DEC-301 旧判据会命中、新判据保留——非回归）。建议：fallback 分支要求 `len(data_cells) == 11`（canonical schema 长度）否则 too_short；或补 headerless 短行负例测试。

**测试质量** ✓
- 9 测试含机制考古测试（`test_legacy_whole_line_attribution_is_the_documented_bug` 断言旧 helper 返回 0.77.0——文档化 bug 而非自证）；结构域负例（prose-only / cross-entity-only / ragged / headerless canonical）齐全；RiskPathUnchangedTests 锁定 risk 路径未动。

## 五、共通维度裁决

| 维度 | 裁决 | 要点 |
|---|---|---|
| 正确性 | ✓（P2×2 防御缺口） | 见分节 |
| 安全性 | ✓ | 无注入/密钥/权限面；解析器对 bytes decode errors=replace 不抛 |
| 可维护性 | ✓ | 新函数职责单一、文档密度高、复用既有基建无复制 |
| 性能 | ✓ | 解析 O(n)；`_archive_index_mtime` 仅 2 次 stat；frozenset 查询 O(1) |
| 测试覆盖 | ✓ | 声明面负例全覆盖 + 基线对照 + 活体三命令；28 新测试全绿 |
| 范围纪律 | ✓ | diff 恰为声明的 6 文件；risk/evidence 路径未动（diff 证实）；无越界 |
| AI 专项 5 项 | ✓ 全过 | mock 残留：产品代码零 mock（测试 patch ROOT/PLUGIN_ROOT 为合法隔离惯例）；硬编码返回值：无；幻觉 API：全部引用函数逐一验证存在；未实现 TODO：三产品文件 grep 零命中；过度实现：`archive_resolved_deps` 有真实消费方（triage record JSON），非死代码 |

## 六、Findings 汇总（blocking = P0/P1；本轮 P0=0、P1=0）

| # | 级别 | task 归属 | 位置 | 描述 | 建议 |
|---|---|---|---|---|---|
| P2-1 | P2 | FIX-341 | `task_priority.py` `_archive_index_status_is_completed` + `_ARCHIVE_NON_COMPLETED_MARKERS` | 完成词表假阳面：`未完成`/`待完成`/`完成条件未满足`/`完成度NN%` 均解析为 completed（探针实证）；真实 index 当前零触发 | 负向表补否定-完成复合词或正向加边界 |
| P2-2 | P2 | FIX-312 | `archive.py` `_decision_archive_version` fallback 分支 | headerless 且 4≤cells<11 时 `[-2]` 非关联列，title/ctx 已归档 ref 误当 governing（探针实证 would_archive）；与「短行 fail-closed」docstring 信任边界不一致 | fallback 要求 canonical 11 列长度否则 too_short + 补负例 |
| P3-1 | P3 | FIX-312（数据修复） | `.governance/archive/decisions/decisions-v0.1.0-0.79.0.md` | DEC-187 归档标注仍为误判版本 v0.77.0；governing FIX-310/FIX-307 现仍未归档 → 按新判据属 premature archive，且 DEC-188「已回迁」叙述过时（Developer 已声明；本轮补充 v0.77.0 标注与 FIX-310/307 未归档两个事实） | 入账数据修复任务：回迁 DEC-187 或补齐 governing refs 归档行后按新判据重归档 |
| P3-2 | P3 | FIX-312 | `archive.py` `_decision_related_column_index` | 全文件扫描取首个含精确「关联任务」cell 的表行——正文若先出现含该 cell 的叙述表格会错位（真实数据 header 在文件头，不触发） | 限扫 header 区（如首个 separator 行前） |
| P3-3 | P3 | FIX-341 | `test_task_priority.py` | 缺「旧缓存无 archive_index_mtime 键 + index 存在」升级场景单测 | 补一条负例 |

## 七、Developer 遗留项裁决（全部同意入账，均不阻塞）

1. **归档行数据缺口（活体翻转前置）**——同意入账，P2 数据项。实证加强：REL-076/FIX-319/FEAT-031 归档 tasks 文件零行；FIX-162/FIX-171 仅 prose 提及；且活体翻转还要求这些任务补录归档任务行（先入档行、index 才可解析、tpa 才会解除）。
2. **DEC-187 叙述过时**——同意入账，并入 P3-1 数据修复（范围扩大：回迁 + 修正 v0.77.0 误判标注 + DEC-188 叙述勘误）。
3. **loop_exit_bridge/risk_domain 未扩展消费**——同意入账（消费扩展属后续任务，本 fix 无义务）。
4. **risk 路径同族判据**——同意入账为独立 task（本 fix 只动 decisions 是正确的 scope 纪律；risk 路径 `_entry_version_for_archive` whole-line 误归档面仍在，有 `_is_risk_closed` 门缓解）。

## 八、硬门槛裁决

- P0 阻塞 = **0**；P1 关键 = **0**；5 维度全覆盖 = **100%**；每条发现带级别 = **100%**；设计一致性（FIX-171 fail-closed 契约 / FIX-301 reason 单源 / FIX-012 缓存纯函数契约 / I/O 例外文档化）= **符合**；AI 专项 5 项 = **全过**。
- **结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**——两 task 均可进入机录入账；P2×2 建议下轮或遗留计划处理。
