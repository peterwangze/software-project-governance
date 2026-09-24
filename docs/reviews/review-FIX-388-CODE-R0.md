# review-FIX-388-CODE-R0 — static-pin 账本重审计 + env_failure_classification 刷新（代码审查 · R0）

> **Round 声明**：R0 首轮审查。审查对象 = 工作树未 commit diff（`git diff --stat` 实测：**2 文件 +21/−8**，`skills/software-project-governance/infra/checks/version.py` +14/−1 与 `skills/software-project-governance/infra/tests/env_failure_classification.json` +7/−7，HEAD=9df2381〔FIX-389 已 commit，时序前置满足〕）。审查方法：diff 逐行通读 + version.py 扫描器/stale-exemption 审计逐行对照 + git 考古三位点（a6d3bfb / 3c3218d / 3d31c49）+ 方案 A/B 取舍原文核验 + 九项实测复现。只读被审代码与 `.governance/`；唯一输出 = 本报告。

---

## 0. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | 0 |
| P1 关键 | 0 |
| P2 建议 | 0 |
| P3 讨论/精度注记 | 5（F-1~F-5，全部非阻塞） |

---

## 1. 验证复现矩阵（全部本席独立实测，非采信申报）

| # | 申报 | 复现命令/方法 | 实测结果 | 裁决 |
|---|------|--------------|---------|------|
| V1 | scan 3 findings → 0 | ①pre-fix 复演：`scan_static_version_pins(root, exemptions={旧账本 12375 单条})`；②post-fix：同函数真树默认账本 | ①**恰 3 findings** = 2×pin（`test_verify_workflow.py:12550`、`:12674`）+ 1×stale exemption（`:12375` token 漂移）②**0 findings** | ✓ 双向成立 |
| V2 | test_static_version_pins.py 25 OK（RealTreeContractTests 2 红→绿） | `python -m pytest test_static_version_pins.py -q` | **25 passed**（3.05s，exit 0）；RealTreeContractTests 3 用例（`test_check_version_consistency_appends_static_pin_face` / `test_ledger_rows_are_live_on_current_tree` / `test_real_tree_scan_is_warn_only_and_clean`）全绿 | ✓ |
| V3 | test_verify_workflow.py 929 OK 零回归 | `python -m pytest test_verify_workflow.py -q`（后台全量） | **929 passed + 126 subtests**（302.75s，exit 0） | ✓ |
| V4 | LRC PASS/0（FIX-389 落库后） | `verify_workflow.py check-loop-runtime-claims` | **verdict PASS / `findings: []` / exit 0**；semantic_units 308,248 ≤ 361,923；`exemptions_applied` 实录 **LRC-EXEMPT-FIX300R0-71-1 / 71-4 / 72-1** 三条生效 | ✓ |
| V5 | cross-refs / manifest / version-consistency PASS | `check-cross-references` / `check-manifest-consistency` / `check-version-consistency` | 三者 **exit 0 全 PASS**（cross-refs 78 文件/725 引用零 dangling；manifest 864 canonical 一致；version 13 面一致） | ✓ |
| V6 | 五条 review_doc_claim 条目 re-ran green | 全量套件（V3）承载 3 条 test_verify_workflow 用例；另测 2 条 loop_runtime 用例 | `test_real_repository_inventory_complete_and_within_budget` + `test_three_run_performance_identity_and_median` **2 passed**（109.04s，exit 0）——后者即 FIX-389 前唯一残红，现随落库转绿 | ✓ |
| V7 | JSON schema / families=9 / tests=20 | `json.loads` + 结构探针 | 解析无错；top-level 10 键齐（schema_version=env-failure-classification/v1）；**families=9 / tests=20** 精确吻合申报 | ✓ |
| V8 | 与 FIX-386 扩充零冲突 | `git diff` hunk 面 + `Compare-Object`（HEAD vs 工作树逐行） | 14 变更行**全部**限定 review_doc_claim 5 条 evidence + family 描述 + maintenance；`clock_window_sensitive` 家族描述与 FIX-364 resolved 条目**逐字节零触碰** | ✓ |
| V9 | FIX-389 时序前置 | `git log`/`git show 9df2381` | 9df2381 已 commit（HEAD）；diff 恰 2 文档 = review-REL-086-RELEASE-R2.md（5+/5− ragged row 修复）+ review-FIX-376-CODE-R0.md（1+/1− L42 改引用式）——与本票刷新注记记录的触发源/修复面逐位吻合 | ✓ |

---

## 2. 账本重锚正确性（审查点 1 + 5）

### 2.1 锚行内容与 git 考古三位点闭环

| 位点 | `_plan_line` def 行 | return（含 0.87.0 token）行 | legacy_done 赋值行 |
|------|--------------------|------------------------------|--------------------|
| a6d3bfb（FIX-371 出生）/ v0.87.0（REL-084 落库） | 12374 | **12375**（原锚正确） | —（未出生） |
| 3c3218d（FIX-373，+109 行插入） | 12483 | 12484 | — |
| 3d31c49（FIX-376）→ 0840876 → 工作树 | 12549 | **12550**（新锚精确） | **12672**（token 行 = 12674） |

- **L12550** 实锚 = `HistoricalExemptionTests._plan_line`（类 docstring L12538 自证「FIX-371/DEC-227 路线 b」）：`return f"| **P1** | {task_id} | fixture task | - | 0.87.0 | tests | {status} |"`——行自标 `fixture task`，版本列为目标版本场景载荷。✓
- **L12674** 实锚 = `legacy_done` 字符串第二物理行 `"| ✅ 已交付 | EVD-997 / 0.87.0 |"`——token 是闭环路径 cell `"EVD-997 / 0.87.0"` 的载荷成分，与豁免 reason 措辞逐字吻合；字符串首行 L12673 无 token，锚定物理行正确。✓
- 同测试内 `legacy_active`（L12678）携带 `0.88.0`（future target）**未**登记豁免——正确留作 0.88.0 bump 的设计信号。✓

### 2.2 「断言不消费版本值」核验

- 消费 `_plan_line` 的 5 个用例（L12586/L12603/L12621/L12640/L12694 起）：断言面全部落在 `task_id` / `status` / `historical_exempted` / `entries`——**无一处比较目标版本列值**。✓
- 消费 `legacy_done` 的用例（L12667-12692）：断言 `r["pass"]` / `entries==["REQ-998"]` / `historical_exempted` 的 `evd_id`/`task_id`/`status`——**版本 cell 值零消费**。✓

### 2.3 stale 行删除后 rot-guard 健康（审查点 5）

机制逐行核对（version.py）：

- 旧 12375 条目是**移除并重锚**，非原地改 token 灭声——账本无静默放宽面。
- stale-exemption 审计（L379-397）遍历**全部**登记条目、逐行验证 token 存留（与 active_version 无关）：新 12550/12674 行均实际携带 token → 0 stale 告警（V1②实测）；其余 8 个文件的历史条目同样被审计覆盖且 0 告警——账本整体健康。
- 扫描主循环 L357 `allowed_lines` 仅豁免 `entry[1] == active_version` 的行 + L366-368 仅标记携带 active token 的行 → 新行精确豁免自身两行，无外溢。
- **设计回旋证明**：本次 2 红（stale 12375 + 出生未豁免 12674）正是 rot-guard 按设计捕获漂移的活体——Developer 残余风险有界声明成立。

---

## 3. 方案 A/B 取舍核验（审查点 2）

| Developer 论点 | 核验证据 | 裁决 |
|----------------|---------|------|
| ① token 内容匹配 = blanket-allow 形态被明文拒绝 | version.py **L167-172 原文**：「The token anchors a row to its line's content: an entry whose line no longer carries the token (drift or removal) is reported as a stale-exemption warning, **so the ledger cannot rot into a blanket allow**.」——token-内容锚将恰好废除此漂移检出设计 | ✓ 成立 |
| ② 改动面违反最小修改面 | 方案 B 需动 scanner 主循环 + 审计循环 + 契约测试 + 迁移（~25 行）；方案 A = 2 行账本数据 + 注记。P-v1 D4（不做冗余修改） | ✓ 成立 |
| ③ 两行 0.88.0 bump 自休眠 ROI 不成立（指方案 B ROI） | 自休眠机制核verified（FIX-361 设计）：bump 后 active_version=0.88.0，L357 过滤使两行退出豁免集；L366-368 只标记 active token → 两行不再被标记；L391-397 只验 token 存留 → 两行不再告警。即**既不抑制任何东西也不产生噪音**，惰性直至 M-1 删除（version-plan L75 + 注记指向） | ✓ 成立 |

**残余风险有界声明**：采纳方案 A 的代价 = 行号对插入敏感、每次漂移需人工重锚——该风险由 stale-exemption 审计自动兜底（本次 2 红即实证），有界声明成立。

---

## 4. env_failure_classification 刷新质量（审查点 3）

1. **定向刷新面精确**：+7/−7 = 5 条目 evidence 演化注记（V7 探针确认 5 条 review_doc_claim 测试条目，键面 class/family/count/evidence/since/ticket ± co_causes/latent_* 与改前一致）+ family 描述 + consumption.maintenance FIX-388 锚。原 evidence 文本**逐字保留**，以 `|` 分隔追加带日期（2026-09-24, HEAD 0840876）的演化注记，pre-fix / post-fix 测量显式分标——演化链可追溯。
2. **触发源轮换声明机制背书**（非仅经验）：旧源 review-FIX-300-CODE-R0.md 3×UNSUPPORTED_AFFIRMATIVE 的吸收 = FIX-320 code-anchored 账本（loop_runtime_claims.py L115-118 `LRC-EXEMPT-FIX300R0-71-1/71-4/72-1`）——本席 LRC 实测 `exemptions_applied` 三条实录（V4）；新源两文档的修复面 = 9df2381 diff 逐位吻合（V9）；post-fix LRC PASS/0 实测（V4）。
3. **「定向刷新无全量 re-baseline」合规**：文件自身 maintenance 契约明文「update alongside data-evolution events（new review docs, archive migrations, F2/F3 fixes）」——本刷新即 data-evolution 事件的定向承载；`generated: 2026-09-10` 基线与 suite_summary（a599843/2304 ran）保留不改 = 正确姿态（全量 re-baseline 留 M-2 发布窗，与棘轮 regen 同口径）。
4. **FIX-386 零冲突**：V8 字节级验证——`clock_window_sensitive` 家族描述 + FIX-364 resolved 条目零触碰，maintenance 注记仅文字引用（「left untouched」）。
5. **无机器校验器自洽**：全 infra 仅 test_triage_write_guard.py L610 docstring 提及该文件——与 consumption.test_code_wiring「explicitly NOT done」自洽；结构合规义务由本审查承担（V7 已尽）。

---

## 5. 发现清单（P0~P3，全部非阻塞）

| # | 级别 | 位置 | 描述与证据 | 建议 |
|---|------|------|-----------|------|
| F-1 | P3 | docs/planning/version-plan-0.88.0.md:75 | M-1 bump 输入清单文本相对本票实现已过时：仍写「:12550 版本字面量**派生化** + :12375 stale exemption 复核」——实际两者均以豁免/重锚消解（派生化被否决，§3），12375 复核已完成。Developer 已披露（边缘 #2：bump 自休眠后 M-1 应删除新增 2 行） | M-1 票执行时同步勘正 L75 措辞并删除 2 条自休眠行；本票不越界改规划文档（D4） |
| F-2 | P3 | env_failure_classification.json:30 | family 描述「review-FIX-376-CODE-R0.md accounting:29:1 (UNKNOWN_STATE_PREDICATE, **L29**)」的 L29 有歧义——29 是 scanner accounting locator 行号，文档实际触发点在 L42（9df2381 commit message 与 diff 实证）；按文件行号 grep L29 只会命中空行 | 后续维护触碰该行时可顺手将「L29」改为「doc L42」；权威 locator（accounting:29:1）在位，不阻塞 |
| F-3 | P3 | test_verify_workflow.py:954/960-962/16224-16228 | Developer 惰性声明 #4「仅 3 处引用**均在 temp root**」措辞精度：3 处引用属实（L954 docstring / L960 import→L962 temp-root 调用 / L16224 import），但第三处 `extract_skill_version(vw.ROOT/...)` 读**真树**（仅提版本号，不执行账本审计）。操作命题「账本审计不在本文件对真树执行」**正确**（全文件无 `scan_static_version_pins`/`STATIC_PIN_EXEMPTIONS` 引用） | 无需动作；记录精确口径 |
| F-4 | P3 | checks/version.py:282-284 | 豁免注释把 12375→12550 漂移单独归因 FIX-373 3c3218d；git 考古显示 FIX-376 3d31c49 贡献第二段位移（+66，12484→12550）。归因不全，处置（重锚）不受影响 | 无需动作；本报告 §2.1 已存全序列 |
| F-5 | P3（观察） | 3d31c49 / checks/version.py:291-294 | FIX-376 legacy REQ 行「出生未豁免」以 WARN 态存活至本次重审计——rot-guard 只强制**已登记**行的漂移检出，新行登记依赖 WARN-only posture（DEC-213③ 设计现状）。证实 Developer 残余风险声明的边界，非本票缺陷 | 若未来升级 FAIL posture（DEC-213③ 预留裁决）可一并考虑出生即登记的流程约束 |

---

## 6. 硬门槛裁决

### 6.1 五维度

| 维度 | 结论 |
|------|------|
| 正确性 | ✓ 重锚三位点 git 考古闭环（§2.1）；scan 3→0 双向实测（V1）；锚行内容/断言消费面逐行核验（§2.2）；LRC + 三一致性门全绿（V4/V5） |
| 安全性 | ✓ 数据面 diff，无输入处理/注入/敏感数据/权限面变化；stale-exemption 防 blanket-allow 机制原文核对在位（L167-172、L379-397）；无静默放宽面（§2.3） |
| 可维护性 | ✓（带注记）注记含漂移成因/方案取舍/自休眠指向——账本自描述性提升；P3 措辞精度 4 条（F-1~F-4） |
| 性能 | ✓ 无运行时路径改动（账本为扫描输入数据）；LRC 语义单元 308,248 ≤ 361,923 容量；全套件 302.75s 零回归 |
| 测试覆盖 | ✓ 25 + 929(+126 sub) + 2 全绿（V2/V3/V6）；2 红转绿即本票交付面；账本审计由 RealTreeContractTests 真树看护 |

### 6.2 AI 代码专项 5 项（diff 为纯数据面：账本条目 + JSON 注记）

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | ✓ 无——无测试代码引入 |
| 2 | 硬编码返回值 | ✓ 无逻辑改动；(line, token, reason) 为 DEC-213③ 设计内静态账本数据，非硬编码返回值 |
| 3 | 幻觉 API 调用 | ✓ 无调用面；注记引用的全部锚点（`_plan_line` L12550 / legacy_done L12674 / version-plan L75 / LRC-EXEMPT-FIX300R0-\* / FIX-320 账本 / FIX-377 finding 4〔FIX-377 commit message「账本过期 2→FIX-388」实录〕）逐一实测存在 |
| 4 | 未实现 TODO | ✓ 无 TODO 标记；M-1 re-audit 指向为已登记义务（version-plan L75 + 边缘披露 #2），非遗漏 |
| 5 | 过度实现 | ✓ 无——+21/−8 两文件，方案 B 大改面被明确否决，修改纯粹性（P-v1 D4）满足 |

### 6.3 设计一致性

✓ DEC-213③（静态版本钉扫描 WARN-only + 可审计豁免账本）/ FIX-361（bump 自休眠设计）/ FIX-320（code-anchored 豁免账本 + digest 锁）/ env_failure_classification maintenance 契约——实现与全部在案设计对齐；FIX-377 归因（账本过期 2→FIX-388）与执行事实吻合。

---

## 7. 交付机录义务（非阻塞——随 commit 承载，Coordinator 执行）

1. commit message/EVD 按本轮实测口径机录：2 文件 +21/−8；scan 3→0 双向复现；test_static_version_pins 25 passed；test_verify_workflow 929 passed + 126 subtests；LRC PASS/findings=[]/exit 0（exemptions_applied 含 3×LRC-EXEMPT-FIX300R0）；三一致性门 exit 0；loop_runtime 2 用例 2 passed（残红转绿）。
2. F-1（M-1 时勘正 version-plan L75 + 删除自休眠行）转 M-1 票输入，不阻塞本票终态。

---

*审查方法学披露：全部 pytest/CLI 运行只读仓库语义面（工作树 `git status` 复核仍恰为 2 个被审文件；`.pytest_cache`/`__pycache__` 为 gitignored 忽略面）；唯一写操作 = 本报告文件；验证中间产物落 `%TEMP%\fix388-review\`（仓库外）；未使用 git stash/checkout（pre-fix 复演以 `scan_static_version_pins(exemptions=...)` 参数注入实现，零工作树突变）；pwsh 管道退出码陷阱（Developer 边缘披露 #3）以「退出码落盘文件」姿势规避。*
