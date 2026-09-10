# Review: AUDIT-152-CODE-R0 — 微审查：env_failure_classification.json（数据资产面）

> **Task**: AUDIT-152（P2）代码审查轮 R0（首次审查，无前轮）
> **Reviewer**: Code Reviewer Agent（角色 `agents/code-reviewer.md` + SKILL `code-review` 已加载）
> **日期**: 2026-09-10 | **HEAD**: `a599843`（与 JSON `suite_summary.head` 一致，实测 `git rev-parse --short HEAD`）
> **审查对象**（git status --porcelain 实测均为未跟踪新增 `??`）:
> ① `skills/software-project-governance/infra/tests/env_failure_classification.json`（199 行，数据资产）
> ② `docs/requirements/env-failure-classification-0.80.0.md`（212 行，配套报告，一致性对照面）
> **审查性质**: 微审查（commit 前置门）——仅数据资产面 3 项；只读 + 只读 `python -c` JSON 校验（任务授权范围内）

## 范围声明（不审项，任务界定）

- **不审**：分类学正确性深挖（报告质量采信 Analyst + 本审查抽查）
- **不审**：测试接线（`skipUnless`/`expectedFailure`——JSON `consumption.test_code_wiring` 与报告 §6.2 均明示未做，属后续任务）
- 工作树另有并行任务产物 `docs/requirements/data-inventory-0.80.0.md`（`??`）——非本审查对象（报告 §6.3 已披露零文件冲突，实测两产物确为独立文件）

---

## 微审查 3 项结论

### ① JSON 机器可读性与 schema 自洽 — **通过**

验证方式：只读 `python -c`（`json.load` + Counter 聚合，零写操作）。Analyst 四项声称逐一对账：

| 声称 | 实测 | 裁决 |
|---|---|---|
| 19 条目覆盖 33 单元 | `entries: 19`；`count_sum: 33`（19 key 的 count 字段求和） | ✅ |
| count-sum 校验 = 32 F/E + 1 skip | `suite_summary` failures=31 + errors=1 = 32 F/E；skip 条目恰 1 个（`test_utf8_read_guard`，family `codepage_gbk`）；33 − 1 skip = 32 闭合 | ✅ |
| 五类枚举 | `classes` 定义恰 5 类（`env_sensitive`/`known_defect`/`data_coupling`/`regression_candidate`/`unclassified`）；实际使用 3 类为定义子集（`subset_ok: True`）；未用的 2 类对应报告计数 0（回归候选/未定性） | ✅ |
| 必需键零违约 | 必需键 `class/family/count/evidence/since/ticket` 对 19 条目全量扫描 → `required_key_violations: []` | ✅ |

附加自洽项（Reviewer 主动加验，均通过）：

- `family` 引用面闭合：全部 `family` + `co_causes[]`（2 处）+ `latent_family`（2 处）引用的族名均落在 `families` 8 定义内（`subset_ok: True`），无悬空引用。
- 可选键使用：`co_causes`×2、`latent_class`×2、`latent_family`×2 —— 与报告 §5.2「JSON 以 latent_class 标记负载潜在暴露」的说法吻合（N1d/N1e 两测试）。
- 顶层元数据自洽：`suite_command` 与报告 §1.1 权威运行命令逐字一致；`baseline_report` 路径指向实际存在的报告文件；`transcript: %TEMP%/audit152_unittest_full.txt` 与报告 §1.2 注释一致。

### ② 无产品行为影响（纯数据文件） — **通过**

- **grep 引用面**（全仓库 `env_failure_classification`）：仅 2 处命中，均在配套报告 md 自身（L6 产物声明、L174 schema 描述）。**零 `.py`/代码/配置消费** —— 与「接线属后续任务」的声明互相印证。
- **文件形态**：纯 `.json` 数据文件，不在任何 Python import 面上；无脚本、无 hook、无 CI 配置引用。
- **工作树状态**（`git status --porcelain` 实测）：JSON 与报告均为 `??`（未跟踪新增），与任务描述「未提交新文件」一致；无既有文件被修改。
- 治理健康面（报告 §8 自述「复跑 30 issues、引用两产物的条目 = 0」）为 Analyst A/B 实录，本微审查未独立复跑（不在授权命令面内），采信并注明来源。

### ③ 与报告一致性 — **通过**

**分类计数对照**（JSON 机器聚合 vs 报告 §3 计数汇总表）：

| class | JSON count 合计 | 报告 §3 | 裁决 |
|---|---|---|---|
| env_sensitive | 25 | 24F（F1 bash/WSL）+ 1 skip（F0 GBK）= 25 | ✅ |
| known_defect | 2 | F2 + F3 = 2 | ✅ |
| data_coupling | 6 | N1×5（4F+1E）+ N3×1 = 6（N2 零独立例，以 `co_causes` 并入 N1b/N1c） | ✅ |
| regression_candidate | 0（无条目） | 0 | ✅ |
| unclassified | 0（无条目） | 0 | ✅ |

F1 十方法 count 明细（2/2/2/4/2/4/2/2/2/2）合计 24，与报告 §3-F1「10 方法 × hook subTest = 24 项」精确闭合。

**抽查 5 条目证据字段对照**（覆盖 4 class / 5 family）：

| # | JSON 条目 | 报告节 | 对照结果 |
|---|---|---|---|
| 1 | `test_a_legacy_end_column_hits`（env_sensitive/bash_wsl_hook, count=2） | §3-F1 | ✅ WSL rc=1 / `WSL_E_DEFAULT_DISTRO_NOT_FOUND` 证据、since ≤2026-08-25（FIX-278 EVD）一致；subTest hook×2 与 count=2 一致 |
| 2 | `test_utf8_read_guard`（env_sensitive/codepage_gbk, count=1, skip） | §3-F0 | ✅ skip 理由「codepage 65001, not 936 (GBK)」逐字一致，预期行为定性一致 |
| 3 | `test_live_plan_tracker_flags_only_known_m1_rows`（known_defect/test_assertion_stale） | §3-F2 | ✅ L533 `set() is not true`、FIX-293（2026-09-09，EVD-963）since、断言反转修复候选、ticket 指向报告 §7 均一致 |
| 4 | `test_real_repository_inventory_complete_and_within_budget`（data_coupling/review_doc_claim + co_causes: authority_archive_side_effect） | §3-N1c + §N2 | ✅ findings=4（1×AUTHORITY_SOURCE_OCCURRENCE + 3×UNSUPPORTED_AFFIRMATIVE）、双因并存定性、since 双锚（e994c7a + EVD-983）一致 |
| 5 | `test_replay_real_plan_tracker_hits`（data_coupling/live_plan_tracker_row） | §3-N3 | ✅ L312 REL-071 `assertTrue → False`、EVD-983 迁移根因、迁移后浮现时序证明（AUDIT-151 无此项 + FIX-301 commit 时点为真）一致 |

`suite_summary` 6 字段（ran=2304 / failures=31 / errors=1 / skipped=1 / seconds=716.848 / head=a599843）与报告 §2 表格逐项一致；报告 §1.2 六新例单跑「5F+1E」与 JSON 六个新增条目（含 N1b 条目 evidence 中的「ERROR form」注记）形态一致。

---

## 发现列表

| # | 级别 | 位置 | 描述 | 处置建议 |
|---|---|---|---|---|
| 1 | **P3** | 报告 §6.1（L174） | schema 描述列为 `{class, family, evidence, since, ticket, count?, latent_class?, notes?}`——实际可选键为 `co_causes?`/`latent_class?`/`latent_family?`；`notes?` 从未使用，`co_causes?`/`latent_family?` 未列入。文档描述与数据实态有轻微漂移，不影响机器可读性 | 后续更新 JSON 时顺带对齐 schema 描述（无阻塞） |
| 2 | **P3** | JSON `tests` key `test_utf8_read_guard`（L115） | 该 key 无模块前缀，与其余 18 条 `module.Class.method` 形态不一致；报告 §6.1 称「test_id 采用 unittest 输出原形」。因该条目是 skip 项，不进入 §6.2 对照脚本的 FAIL/ERROR 差集面，当前消费影响为零 | 后续接线任务统一 test_id 规范时一并处理（无阻塞） |

- P0：**0**。P1：**0**。P2：**0**。P3：2（均为备注，无阻塞）。

## 维度覆盖（按微审查范围适配，如实标注）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | 通过 | ①项：schema 自洽 + count-sum 算术闭合（19/33/32+1 全机器验证） |
| 安全性 | 通过（不适用面如实标注） | 纯数据文件，无输入校验/注入/敏感数据面；JSON 内容为测试分类证据，无密钥类字段（逐条目通读确认） |
| 可维护性 | 通过（附 P3×2） | schema_version + classes/families 定义域闭合；发现 1/2 为文档-数据描述漂移 |
| 性能 | 不适用 | 数据资产无运行时行为；零消费已确认（②项） |
| 测试覆盖 | 不适用（范围裁剪） | 接线明示未做、属后续任务（任务界定不审） |

AI 代码专项 5 项（数据文件适配）：mock 残留——无（无代码）；硬编码返回值——无（无代码）；幻觉 API 调用——无（无代码）；未实现 TODO——无（`ticket: null` 为显式语义「尚无专属任务」，报告 §6.3 有约定，非 TODO 残留）；过度实现——无（顶层字段均被报告引用或为自洽元数据，consumption 节为最小使用说明）。

## 终态

# APPROVED_WITH_NOTES

`unresolved_blockers=0`

- 微审查 3 项（schema 自洽 / 零消费 / 报告一致性）全部通过，每条结论有可复查事实（python -c 输出 / grep 结果 / git status / 逐条目对照）。
- 2 条 P3 备注不阻塞 commit；建议随后续 JSON 更新任务顺带关闭，不需本轮返工。
- 本 APPROVED 仅覆盖数据资产面微审查范围；不构成对分类学正确性深挖、测试接线或报告质量的完整审查结论（任务界定的不审项）。
