# Review Report: FIX-407 — Code Review R0

- **Task**: FIX-407（EXC-003 终局票：decision narrative 行族解析与迁移）
- **Reviewer**: Code Reviewer Agent（独立，R0 首轮）
- **Date**: 2026-09-29
- **审查对象**: `skills/software-project-governance/infra/archive.py`（3 处）、`skills/software-project-governance/infra/tests/test_archive.py`（+212 行 / 8 新例）、`.governance/exceptions.json`（EXC-003 删除 → 空数组）
- **范围声明**: 3 个 e2e fixture M（Developer 披露的附带损伤恢复产物）按任务口径不属本审范围，但其**恢复终态一致性**属验收⑦，已核验。FIX-408 测试修改尚未存在，不涉。

## 1. 结论

**APPROVED_WITH_NOTES**

- `unresolved_blockers=0`
- P0 = 0 · P1 = 0 · P2 = 0 · P3 = 5（全部非阻塞备注）
- 硬门槛：P0 计数 0 ✓ / 5 维度全覆盖 ✓ / 每条发现标注级别 ✓ / 设计一致性检查完成 ✓ / AI 代码专项 5 项完成 ✓

## 2. 八项验收核验

### ① 解析器四重 fail-closed 语义 — PASS

`_decision_narrative_verdict`（archive.py:1009-1061）仅在 canonical 列门 `decision_row_too_short` 之后触发，四重留热语义逐行验证：

| 门 | 实现 | 触发即留热 |
|---|---|---|
| anchor 撞号 | 主循环预扫 `anchor_counts` 普查**全文件** DEC 行（机写+narrative 同计，`:1584-1593`），`>1` 即留热 | `narrative_duplicate_anchor` |
| 无 ISO 日期 | `_ROW_DATE_RE`（`\b\d{4}-\d{2}-\d{2}\b`）整行搜索 | `narrative_undatable` |
| ref 不可证 | `_DECISION_ID_TOKEN_RE.finditer(line)` **整行**扫描（prose 提及计入）+ 共享 `_make_ref_verdict` 五态裁决，`verdict != "pass"`（active/missing/ambiguous/layout_anomaly/version_unparseable）即留热 | `narrative_retained_unproven_ref` |
| 窗口末端不可解析或超窗 | `_q6_date_window_fallback` 复用（窗口末端 release date 不可解析 → None → 留热；行日期 > 末端 → 留热） | `narrative_date_out_of_window` |

「整行 prose 提及只能留热、绝不 release/re-attribute」（FIX-312/DEC-187 教训）双向成立：union 纪律使 prose 提及**只能增加**留热理由；attribution 恒为 `version_end`（`:1061` 返回 `version_end`，非任何 ref 的机写版本）——测试 `test_narrative_row_with_archived_refs_migrates_via_q6_not_attribution` 显式断言 `v0.38.0（关联 task 已归档）` 不出现。机写行完全不经 narrative 路径（仅 `reason == "decision_row_too_short"` 分支进入），零回归面。

`_build_classification_context` 异常降级为空 context（`:1594-1598`）时 ref 全部落 `missing → fail`——降级方向仍是留热（fail-safe）。

### ② Q6 裁决与 evidence 族同规 — PASS

- 日期窗裁决复用**同一函数** `_q6_date_window_fallback`（FEAT-076 / DEC-278 单元三；evidence 族 `:2067/:2641` 同源调用）。
- ref 类型裁决复用 `_make_ref_verdict`（FEAT-075 单元二共享五态 typer，单一来源，无平行实现）。
- explain 词表：`would_archive_narrative_q6` 与 evidence 族 `would_archive_date_window` 同属 `would_archive*` 前缀族；`_finalize_explain`（`:3355-3357`）`startswith("would_archive")` 统一计数——一词表一口径，无第五种旁路。全文件无其他 `would_archive` 前缀的非迁移 reason（grep 全量核对）。
- narrative 留热 reason（`narrative_*`）不在 `_EXPLAIN_UNKNOWN_REASONS`，`parsed` 口径正确（可解释留热 ≠ 未解析）。

### ③ 迁移守恒（169 = 58 + 111）— PASS（独立复核）

- 备份 `fix407-backup/decision-log.md`（259,053B）DEC 行数 = **169**（亲数）。
- 独立 shape census（只读脚本，镜像实现）：**62 机写 + 107 narrative**；narrative 细分 **5 撞号 + 102 可判定**——与 Developer 披露逐项一致。
- 迁出 **58**：归档文件 58 头 / 58 Q6 注记 / 58 verbatim 块（亲数）；`index.md` 指向 `decisions-v0.1.0-0.91.0.md` 的条目 = **58**；总 Decision 条目 **185 = 127 + 58**。
- 留热 **111**（亲数）= 62 机写（`retained_active_task_ref` 47 + `no_task_family_ref` 15）+ 49 narrative（**42 不可证 ref + 5 撞号 + 2 超窗**）——对当前热日志 dry-run explain 复跑亲测，分布逐项吻合且**零残留候选**（迁移终态稳定，无遗漏）。
- decision-log 259,053B → **177,202B**（亲测）。
- 备份锚：`fix407-backup/decision-log.md` sha256 = `70F7458446F82CDEF05F7123695A50A3E067729FCDD0869CD1F84365D7EBE217`（可复核）。

### ④ 原始行逐字保全（FIX-162）— PASS（程序化比对）

集合双向比对（备份 ∖ 热日志 = 迁出集）：58 迁出行**逐字**出现在归档 `> | DEC-…` verbatim 块（0 missing）；热日志 0 编造行（热 DEC 行全部源自备份）。归档头 `## DEC-n: title` + Q6 注记 + verbatim 三段式结构完整（58/58/58）。

### ⑤ EXC-003 删除后 Check 28s 语义 — PASS（亲测）

`exceptions.json` = `{"schema": "governance-exceptions/1", "exceptions": []}`（空数组，EXC-003 已删）。`check-governance-data-size` 亲测：**0 ERROR / 2 WARN**，且两条 WARN 均为既有 advisory（plan-tracker 200.9KB、evidence-log 509.0KB）——**decision-log 177,202B 不再出现在任何级别**（原 259,053B 超 250KB error 线需 EXC-003 承载）。decision 面消失 = 无例外承载的正确形态：例外删除与数据瘦身互为闭环，语义成立。

### ⑥ 8 测试质量 — PASS（亲测 8/8）

`python -m pytest tests/test_archive.py -k FIX407 -q`（TEMP 重定向 `.governance/tmp/check-run-20260929`）→ **8 passed, 178 deselected in 0.16s**。覆盖矩阵：

| # | 测试 | 验证门 |
|---|---|---|
| 1 | `test_narrative_row_migrates_via_q6_date_window` | 正例全链（归档三段式 + 机写行同期留热 + verbatim 前缀断言） |
| 2 | `test_narrative_boundary_date_equal_to_window_end_migrates` | 边界 ≤ 含等 |
| 3 | `test_narrative_row_after_window_end_retained` | 超窗留热 |
| 4 | `test_narrative_row_with_unproven_ref_retained` | 整行不可证 ref 留热 |
| 5 | `test_narrative_row_with_archived_refs_migrates_via_q6_not_attribution` | prose 已归档 ref **不重定** attribution |
| 6 | `test_narrative_row_without_iso_date_retained` | 无日期留热 |
| 7 | `test_narrative_anchor_duplicate_with_machine_row_retained` | narrative×机写交叉撞号 |
| 8 | `test_window_end_unreleased_retains_all_narrative` | 窗口末端不可解析整体拒绝 |

四重 fail-closed 各有专属测试；断言精确到 reason 字符串与文件内容（非仅计数）；mock（`patch.object` ROOT/`_window_end_release_date`）全部 with 块内自动还原，无残留；`_writable_root` 用 plain mkdir 规避 UAC 过滤 token 下 mkdtemp 0o700 不可写问题（沿 FIX-404 纪律，有注释）。

### ⑦ 抢救完备性 — PASS（终态亲测）

| 声明 | 亲测结果 |
|---|---|
| `governance-init.md` hash == HEAD blob（24538aa） | `git hash-object` 主副本与 e2e fixture 均为 `24538aa24e6d97986768bf22862a2902a2b1d428` == HEAD blob；`git status` clean ✓ |
| SKILL.md == 投影期望（49,941B） | 主 = fixture = 49,941B，**逐行 IDENTICAL**（Compare-Object 零差异）✓ |
| check-projection-sync PASS | 亲测 PASSED（28 mirrored files）+ Entry Bootstrap Sync PASSED ✓ |
| 3 fixture ACL 恢复 | `governance-status.md` / `verify-e2e.sh` 内容 == HEAD（`git diff --summary` 空、diff body 空，仅 LF/CRLF stat 噪音）；fixture SKILL.md 4 行 delta 为「投影期望落盘」合法形态（见 P3-3）✓ |

### ⑧ 零范围外 — PASS

`git status` 共 5 个 M：`archive.py` + `test_archive.py`（本票）+ 3 个 e2e fixture（披露的抢救恢复产物）。无其他未披露修改；隔离产物限于 `.governance/tmp/fix407-quarantine/`（见 P3-5）。

## 3. 执行协议遵循（复跑记录）

- TEMP 重定向 `.governance/tmp/check-run-20260929` ✓ · 重试 0/2（一次通过）✓ · 禁全量遵守（未跑全量测试/e2e）✓
- `test_archive -k FIX407`：8 passed / 0.16s ✓
- `archive.py verify`（--project-root 显式）：Pass True · 1650 archived tasks · 2653 index entries ✓
- `archive.py rebuild-index`：Integrity PASS · Decision 185（幂等 no-op——Developer 已重建且稳定）✓
- `check-governance-data-size`：0 ERROR / 2 WARN（既有 advisory，见⑤）✓
- `check-projection-sync`：PASSED（28 files）+ Entry Bootstrap Sync PASSED ✓

## 4. Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| P3-1 | P3 | archive.py:992-1006 | `_decision_narrative_title` docstring 称 fallback 链为「决策内容 → owner cell」，实际代码为 parts[4]（决策内容）→ parts[5]（理由）→ parts[3]（决策人）→ 默认——理由格先于 owner 被检查，docstring 未提及 | 下次触碰时补 docstring（纯展示字段，原始行完整保全，无行为风险） |
| P3-2 | P3 | test_archive.py `_make_decision_log` | separator 行由 `"| --- \|"*2 + " --- \|"*9` 拼接，产生 `\| --- \|\|` 空列形态，markdown 渲染不标准（解析功能正确——separator 检测 regex 只校验字符集） | 改为 `"| --- |" * 11` 之类标准形态 |
| P3-3 | P3 | project/e2e-test-project/.../SKILL.md | 4 行 delta（相对 HEAD）是投影期望落盘的合法恢复形态（与主 SKILL.md 逐行一致，projection-sync PASS），但**未提交**——长期悬置会让下个会话误判为未披露修改 | 随 FIX-407/FIX-408 下一次 commit 一并入账 |
| P3-4 | P3 | archive.py:1787-1800 | `_window_end_release_date` 无 per-run 缓存——narrative 裁决逐行调 `_q6_date_window_fallback` 时重读 plan-tracker（~107 次 × 205KB）。FEAT-076 既有模式（evidence 族同构），非本票引入，单次迁移实测秒级 | 后续票统一加 per-run memo（evidence + decision 两族同享） |
| P3-5 | P3 | `.governance/tmp/fix407-quarantine/` | 隔离搬移残留目录仍在 tmp 下；备份 `fix407-backup` 按纪律保留（sha256 锚可复核） | 备份窗口确认后清理 quarantine（备份保留至下个 release 结账） |

**AI 代码专项 5 项**：mock 残留无（with 块自动还原）✓ / 硬编码返回值无（窗口日期从 roadmap 解析、fail-closed None）✓ / 幻觉 API 无（全部调用 grep 确认存在的既有函数）✓ / 未实现 TODO 无 ✓ / 过度实现无（122 行全部服务于 narrative 行族）✓

## 5. 审查维度结论

| 维度 | 结论 |
|---|---|
| 正确性 | 四重 fail-closed 逐行验证 + 真实数据独立复核（守恒/残留/逐字保全全吻合）——PASS |
| 安全性 | 全部降级路径朝留热（数据保守）；TOCTOU in-lock 复检保留；备份可复核——PASS |
| 可维护性 | 与 evidence 族共享裁决器（单一来源）；docstring 引用 FIX/DEC 历史充分；2 处 P3 文档不精确——PASS |
| 性能 | O(n) census + 逐行裁决；1 项 P3（无缓存，既有模式）——PASS |
| 测试覆盖 | 8 例覆盖全部门+边界+反向归因；核心路径/边界/错误路径齐备——PASS |

## 6. 报告路径

`docs/reviews/review-FIX-407-CODE-R0.md`（本文件）

---
*Code Reviewer Agent · FIX-407 R0 · APPROVED_WITH_NOTES（unresolved_blockers=0）*
