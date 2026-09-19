# 代码审查报告 — FEAT-053（0.85.0 M-1 版本 bump + 候选打包）CODE 半面 R0

- **Round**: R0（前轮引用：无——首轮审查）
- **审查人**: Code Reviewer Agent（独立审查，只读；不修改代码/.governance）
- **审查对象**: 工作树未提交 **24 modified**（`git status --porcelain` 逐面核对一致）；并行在途面（`task_row_update.py`/`governance_store.py`/`test_task_row_update.py`/`test_governance_store.py` 4 个 untracked）**出范围**——但其作为豁免账本登记对象被间接核验（见 §4）。
- **语义基准**: REL-081（M-1 承载）/ DEC-216（两批制）/ EVD-1088~1108（交付链事实源，evidence-log L2299~2396 逐行核对）/ Bootstrap 变更纪律（canonical→投影再生）/ FIX-361（豁免账本设计，EVD-1098）。
- ** Developer 申报独立复验**: 见 §7 复验表——申报的每一项 PASS 均经本审查独立复跑证实，WARN 如实。

## 总结论

# **APPROVED_WITH_NOTES / unresolved_blockers=0**

（P0=0，P1=0，P2=2〔非阻塞：1 项范围外引擎缺陷修复票建议 + 1 项治理收口义务〕，P3=4 记录级。机录义务：Coordinator 以 `review-record` 持久化本结论；Reviewer 不写治理状态。）

---

## 1. 变更面构成核对

24 modified 与申报手工 5 + 再生 19 完全吻合（`git diff --stat HEAD`：131 insertions / 31 deletions）：

| 类别 | 文件 | 核验 |
|---|---|---|
| 手工-1 | `skills/software-project-governance/SKILL.md` L3 frontmatter 0.84.0→0.85.0 | ✓ diff 2± |
| 手工-2 | `infra/verify_workflow.py` REQUIRED_SNIPPETS 6 钉 0.84.0→0.85.0 | ✓ diff 12±=6 行替换 |
| 手工-3 | `infra/checks/version.py` 豁免账本 +10 行 + 3 个 `_REASON_*` 常量 | ✓ 实测 1+6+2+1=10 |
| 手工-4 | `project/CHANGELOG.md` 0.85.0 段（+63 行） | ✓ §2 事实核对 |
| 手工-5 | `commands/governance-init.md` canonical 3 标记 0.84.0→0.85.0 | ✓ 实测恰 3 处 |
| 再生 | 5 plugin/marketplace JSON + `package.json` + `core/manifest.json`（7）+ 4 hooks + persona + `adapters/dsh/AGENTS.md.template`（6）+ 双根入口 `AGENTS.md`/fixture `AGENTS.md`/fixture `CLAUDE.md`（3）+ fixture skill/plan/init（3）= 19 | ✓ §7 全量清点 |

**registry 未改动**（`version-projections.json` 不在 24 modified 中）——`canonical-bootstrap-version` 的 `count` 由 4→3 的变化已在 FEAT-041（b717835）落库，M-1 沿用；本次 `release-projection check` exit 0 机验 count=3 与文件实际 3 标记匹配（count 不匹配会 ValueError→BLOCKED）。

## 2. ①CHANGELOG 0.85.0 段事实核对（抽查 8 条 > 要求的 5 条）

| # | CHANGELOG 声明 | 对照源 | 裁决 |
|---|---|---|---|
| 1 | FIX-356 commit `be0b844`，「真实语料命中 0→156 sessions/22 TTFA」 | `git show` hash/日期/主题逐字吻合；EVD-1089「156 sessions/485 turns/22 TTFA（修复前 0）」 | ✅ 证实 |
| 2 | FIX-359 commit `11289be`，「30 项失败清零……非族 3 项转 FIX-363」 | EVD-1094：A 族 hook 回放 6 + B 族 review evidence 24 = 恰 30；非族 3 项（L95/L296/L257）→ FIX-363 候选 | ✅ 证实 |
| 3 | FEAT-041 commit `b717835`，「resident 10,718→5,694 / 10,918→5,966（-46.9%/-45.4%）lightweight 4,957→4,216」 | 前基线 EVD-1092（4,957/10,718/10,918）+ 瘦身后 EVD-1104（4,216/5,694/5,966）+ 本审查独立复跑逐位复现（§7-2）；削减比独立验算（1-5694/10718=46.9%，1-5966/10918=45.4%）吻合 | ✅ 证实 |
| 4 | FIX-362 commit `5a4c4f4`，「14,493B 陈旧镜像 promote，投影合同 27→28」 | EVD-1096（SHA 0f235613==canonical、registry/manifest 双 28）；本次 `release-projection` 实测 `projections` 数组 len=28 | ✅ 证实 |
| 5 | FIX-361 commit `2e80c69`，「WARN-only + (line, token, reason) 豁免账本可审计防腐蚀」 | EVD-1098；账本设计四要素（豁免注册表/stale 三态审计/注释-docstring 排除/多行字符串照扫）在 version.py L268-340 逐行读码证实；bump 时点双重信号 = 设计预期（L214 注释 + EVD-1098「边缘 3 入发布清单」） | ✅ 证实 |
| 6 | FEAT-050 commit `407b230` + FEAT-052 commit `1519bf1`（skill 层 16,000 线、实测基线 14,456） | EVD-1106/1107 双 REVIEW 终态 APPROVED_WITH_NOTES/0（机录行 L2383/2388 在案）；RISK-057 缓解④转事实表述与 EVD-1106 一致 | ✅ 证实 |
| 7 | FEAT-049 commit `27eeea0`「m0-r1 随候选树入库、0.85.0 零行为消费」 | EVD-1105（157=99+58 测试、契约五面、**批 0 归属如实披露⑤**——避免 CHANGELOG 与 git log 对照缺口的动机成立） | ✅ 证实 |
| 8 | 治理面「8 决策（DEC-214~221）+ 20 EVD（EVD-1088~1107）」 | decision-log L155-162 逐行在案（DEC-214/215①②/216/217/218/219/220/221 恰 8）；EVD-1088..1107 = 恰 20 连续 ID | ✅ 证实 |

**B-1/B-2 行为变更与回退口径**: B-1（契约 v2，升级路径兼容「整段替换零残留」——EVD-1103 H2 恢复=边界集超集）✅；B-2 回退通道「无 flag 级降级，版本级回滚（与 0.84.0 D-4 同型）」与 `docs/release/feature-flags-0.84.0.md` D-4 行逐字同口径 ✅。

**no-overclaim 披露七条真实性**: ①RISK-055 首判 FAIL 如实保留（EVD-1089 FAIL 原文 + DEC-215① 分域复采样裁决在案）✓；②strict 余量 34 tok（EVD-1104 裁决原文）✓；③规划漂移 +19%（EVD-1092 实测 4,718/4,918 vs DEC-211② 3,953/4,154，验算 +19.4%/+18.4% ≈ 漂移披露）✓；④豁免 10 行登记（→ 但见 P3-1 口径矛盾）✓；⑤FEAT-049 归属 ✓；⑥「本版不发布什么」与 version-plan-0.86.0/REL-082 轨道一致 ✓；⑦四项均未主张（official/marketplace/universal/external pilot）+ RISK-036 维持打开——与 0.84.0 feature-flags 披露形态一致 ✓。

## 3. ②0.84.0 残留普查复跑

全仓 grep `0\.84\.0` = 299 命中，逐类清点：**全部落在历史/事实面白名单**——docs/reviews 历史审查报告、docs/release/{feature-flags,rollback-plan}-0.84.0.md（0.84.0 版本三件套）、CHANGELOG 0.84.0 历史段及 0.85.0 段内先例引用、core/releases/0.84.0.json（已发布 ledger）、infra docstring/注释归属标注（behavior_profile/bootstrap_aggregate/governance_cost/registry/TOOLS.md/test_archguard_ratchet）、豁免账本 0.84.0 老行（FIX-361 账本内，机验仍有效）、SKILL.md L196 及其 fixture byte_copy 镜像 L196（同句历史叙述、两侧一致）、test_bootstrap_aggregate fixture/migration 测试数据（已豁免）。**未发现任何应 bump 未 bump 的活性版本锚**。双根入口（AGENTS/CLAUDE ×2 根）与 fixture 全部 0.85.0（§7-6 机验）。`docs/planning/version-plan-0.86.0.md` L10「0.85.0 段未入（在途）」为规划时点快照、历史文档不改写纪律适用，不计 finding。

## 4. ③REQUIRED_SNIPPETS 6 钉 + 豁免账本 10 行（FIX-361 符合性）

- 6 钉与 6 个 JSON 声明面逐一相等（0.85.0），`check-version-consistency` PASSED（13 面 + bootstrap markers）。
- 豁免账本 **10 行逐行实测**（行号→当前文件行内容）：
  - `test_bootstrap_aggregate.py:123` = fixture 任务表行「| P2 | FEAT-104 |…| 0.85.0 |…」→ 与 `_REASON_FIXTURE_TABLE` + bump 双重信号注释吻合；
  - `test_baseline_metadata.py` 60/315/392/563/620/738 = 6 处 `instrument_version="check-injection-budget@0.85.0"` fixture 参数 → 与 `_REASON_INSTRUMENT_VERSION` 逐字吻合；
  - `test_task_row_update.py` 74/76 = 任务行文本 fixture（0.85.0 为场景 payload）→ 与 `_REASON_FIXTURE_ROW_TEXT` 吻合；
  - `test_static_version_pins.py:158` = `'ahead = "0.85.0"\n'` 合成 future-target → 与 `_REASON_FUTURE_TARGET`（「仅在 0.85.0 bump 时点等于 active，随后休眠」）精确吻合。
- **机验兜底**: 直接调用 `scan_static_version_pins(Path('.'))` → 返回 `[]` = 零未豁免命中 **且** 账本 stale 审计（L321-339）对全部 22 条豁免（12 老 + 10 新）零告警 → 全部行号当前锚定有效。FIX-361 设计符合性 **PASS**。
- 行号锚定时效（在途竞态）复核结论 → P3-2（措辞过时，行号本身有效）。

## 5. ④canonical→投影纪律

- Bootstrap 变更纪律方向正确：权威源（SKILL frontmatter 0.85.0）→ `commands/governance-init.md` canonical 模板 3 标记（FEAT-041 契约 v2 后 4→3 属实：0.84.0 为 full×3+secondary-thin×1，契约 v2 合并后 3）→ fixture byte_copy 再生（fixture init 恰 3 标记 0.85.0，与 canonical 字节面一致）。
- 「4→3，registry count 同步」申报核实：registry `canonical-bootstrap-version` 面 count 与文件匹配由 release-projection check exit 0 机验（mismatch 即 BLOCKED）；FEAT-041 b717835 已承载该变更，M-1 零 registry 改动正确。
- 终态一致性机验：`release-projection`（check 态）exit 0，28 面 zero drift；census divergent=37/undeclared_out_of_scope=27 与 EVD-1096 披露的既有未声明面持平（非本批新增）。
- 例外披露：两阶段耦合导致的执行手法 → §6/P2-1。

## 6. ⑤引擎两阶段耦合缺陷（范围外发现——定级 P2-1，附修复票评估）

**缺陷证实（读码层）**：`release/projection.py` `build_projection_plan`（L190-221）单遍构建写入计划——byte_copy 的 `content = source.read_bytes()`（L203）在 **plan 阶段**从磁盘快照，而 apply 发生在写入阶段（L471-477）。registry 同时含 `canonical-bootstrap-version`（transformed_text，target=`commands/governance-init.md`）与 `fixture-command-governance-init`（byte_copy，source=同一文件）。版本 bump 场景下单次 `--write`：byte_copy 目标计划内容=旧版本字节（apply 前源未更新）→ apply 后 post-write check（L478 重建计划）检出 fixture drift → `OSError("post-write projection validation failed")` → **全事务回滚**（journal 逆序恢复）。

**定性**：可用性缺陷而非正确性缺陷——fail-closed 方向（不会静默产出「canonical 新/fixture 旧」的腐坏终态，任何不一致都会回滚），bump 场景引擎单次执行不可用。该面组合自 0.84.0 发布期 fixture-command 面纳入投影合同（REL-080 R0 F-05 修复）后才存在，0.85.0 M-1 是首次完整 bump 暴露。

**绕开手法合规性**：终态（canonical 先达目标值使 transformed 面幂等化 → `--write` 从已更新源再生 byte_copy 面）经本次 28 面 check exit 0 机验一致；canonical 权威、投影再生的纪律实质未被破坏（手工使 canonical 达到与投影引擎本应写入的相同值，不产生 drift）。**合规但不可持续**：手法依赖执行者对引擎缺陷的理解，未在 CHANGELOG 投影段显式披露（「二次 apply 幂等」为间接表述）。

**修复票建议评估**：**合理且 MUST 落票**（建议 0.85.0 发布窗后、0.86.0 批 2 前登记候选）。可行方向（供修复票参考）：(a) 计划分两轮——先 apply transformed/structured 面，再重建计划并 apply byte_copy 面；(b) plan 阶段对「source ∈ 本批写入目标集」的 byte_copy 传递计算预期内容（以源的计划内容替代磁盘快照）；(c) 至少在 post-write FAIL 信息中显式提示该耦合形态。三案均保持 journal/回滚语义不变。

## 7. ⑥验证复跑（独立执行，全部只读）

| # | 复验项 | 命令/方法 | 结果 | 对照申报 |
|---|---|---|---|---|
| 1 | verify 全量 | `python …/verify_workflow.py` | **PASSED exit 0；唯一 WARN = plan-tracker workflow version 0.84.0 expected 0.85.0** | ✅ 与申报逐字一致（预期过渡态属实） |
| 2 | 注入预算三 profile | `check-injection-budget --profile {lightweight,standard,strict}` | **4,216 / 5,694 / 5,966 ≤ 6,000 全 PASSED** | ✅ 与 EVD-1104 逐位一致，零回归 |
| 3 | 版本一致性 | `check-version-consistency` | PASSED（13 面 + bootstrap markers；同唯一 WARN） | ✅ |
| 4 | 投影同步 | `release-projection`（check）+ `check-projection-sync` | 均 exit 0；28 面零 drift；双根入口 synchronized | ✅ |
| 5 | 豁免账本 10 行 | 逐行读文件 + `scan_static_version_pins` 直调 | 行内容逐行吻合 + 返回 `[]`（零未豁免命中、22 条账本零 stale） | ✅ FIX-361 设计兑现 |
| 6 | 版本面全量清点 | 逐面读值 | 4 hooks `@version: 0.85.0`、6 JSON、manifest、persona `v0.85.0`、dsh 模板、SKILL frontmatter、双根 AGENTS/CLAUDE ×2、fixture SKILL/plan、canonical+fixture init 3+3 标记 = **全部 0.85.0** | ✅ |
| 7 | 11 commit 引用 | `git show --format` 逐个 | hash/日期（均 2026-09-19）/主题逐字吻合 | ✅ §2 |
| 8 | 静态钉套件 | `pytest test_static_version_pins.py -q` | **25 passed**（申报「36+3」口径 → P3-4） | ⚠ 口径待澄清 |

## 8. ⑦AI 专项 5 项（变更面 = 文档/版本号/账本，无逻辑代码）

| 检查项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | 无 | diff 无测试逻辑改动；4 个 untracked 测试文件出范围 |
| 硬编码返回值 | 无违规 | REQUIRED_SNIPPETS 版本字符串属声明面钉（版本 bump 的本质工作），非逻辑硬编码 |
| 幻觉 API 调用 | 无 | 豁免账本仅常量+元组；3 个 `_REASON_*` 文本与被引行实测内容逐字相符（§4），无虚构引用 |
| 未实现 TODO | 无 | diff 零 TODO/FIXME；复核义务（「re-audit at landing」「批次落库时 MUST 复核」）有 stale 审计机检兜底，非空承诺 |
| 过度实现 | 无 | 账本 10 行均必要（缺任一行 → bump 时点 WARN 假信号）；无超范围改动（registry/引擎未触碰） |
| **「全绿」申报如实性** | **如实** | 申报 PASS 项复跑全过；唯一 WARN 如实呈现且与实测一致；FEAT-041 R0 NEEDS_CHANGE 同段如实记载（→ 措辞歧义见 P3-3） |

## 9. Findings 列表

| ID | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| P2-1 | **P2**（范围外引擎缺陷，非阻塞本候选） | `skills/software-project-governance/infra/release/projection.py` L190-221/L448-480（**未变更文件**） | byte_copy 两阶段耦合：plan 阶段磁盘快照源内容，bump 场景单次 `--write` 必然 post-write FAIL+全事务回滚；M-1 以「canonical 先达目标值再 --write」手法绕开（终态机验一致，合规但未显式披露） | MUST 立修复票（§6 三方向任一）；发布清单/EVD 行补一句手法披露；修复前每次 bump 重复该手法并留痕 |
| P2-2 | **P2**（治理收口义务，非代码缺陷） | `.governance/execution-packets.json`（仅 FEAT-041/FEAT-050 两包，无 FEAT-053 包）；`.governance/session-snapshot.md`（未随 M-1 刷新） | FEAT-053（活跃 P1）执行短包缺失（Check 18c 同族缺口，verify 全量未覆盖该面故 PASSED 与缺包并存）；session-snapshot 停在前一工作单元 | Coordinator 随 M-1 EVD 落账补写 packet + 刷新快照（先例：EVD-1100 FEAT-041 packet 本轮补写） |
| P3-1 | P3 | `project/CHANGELOG.md` 0.85.0 段（版本投影段 vs 如实披露④） | 同段口径矛盾：投影段「登记静态钉豁免 **8 行**」vs 披露④「豁免 **10 行** 登记（2+8 分解）」——账本实测 **10 行**（1+6+2+1） | 候选提交前勘正投影段措辞（改 10 或显式 2+8 分解） |
| P3-2 | P3 | `project/CHANGELOG.md` 披露④ + `checks/version.py` 豁免注释 | 时点过时：test_baseline_metadata.py 已随 bff298d（FEAT-047，当前 HEAD）落库为 tracked、工作树零未提交修改；「在途未跟踪批次文件 ×6」「is being edited while this bump runs」在候选打包时点失准（仅 test_task_row_update.py ×2 仍属在途未跟踪）。行号本身实测全部有效（§4/§7-5）——纯披露精度 | 候选提交前勘误措辞，或 EVD 行留时点澄清（「登记时点在途、落库后行号经复核有效」） |
| P3-3 | P3 | `project/CHANGELOG.md` ⑥ 治理面段 | 「11 票 R0 全闭环」措辞歧义：FEAT-041 R0=NEEDS_CHANGE（同段已如实记载，链在 R1 闭合），汇总句易被误读为 11 个 R0 均一次通过 | 改「11 票审查链全闭环（其中 FEAT-041 R0 NEEDS_CHANGE→R1 APPROVED_WITH_NOTES/0）」 |
| P3-4 | P3 | Developer 申报口径 | 「静态钉测试 36+3 passed」无法与在场套件精确对表（实测 test_static_version_pins.py = 25 passed）；所有可观测静态钉面实测绿，不阻塞 | EVD 落账时澄清计数口径（36+3 疑指其它套件组） |

## 10. 硬门槛裁决

| 门槛项 | 结果 |
|---|---|
| P0 阻塞数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅ 正确性（§2/§4/§6 读码+机验）/ 安全性（变更面无输入面/无注入面/无敏感数据/权限面不变；全部复跑只读）/ 可维护性（账本 reason 可审计、常量命名清晰）/ 性能（N/A——无算法变更；扫描 O(files×lines) WARN-only 可接受）/ 测试覆盖（静态钉 25/25 + verify 全量 + 账本 stale 审计机验） |
| 每条发现标注级别 | ✅（P2×2 + P3×4，逐条位置/依据/建议） |
| 设计一致性 | ✅ canonical→投影纪律、FIX-361 账本设计、DEC-216 两批制承载、Bootstrap 变更纪律全部符合（§4/§5） |
| AI 专项 5 项 | ✅ 全过（§8） |

## 11. 边缘问题（移交 Coordinator）

1. P2-1 修复票的归属版本窗（0.85.0 窗后 vs 0.86.0 批 2 前）需裁决——建议随 0.86.0 批 2（closure/混沌发布门前引擎应修复，届时 bump 频率更高）。
2. P2-2 补包与快照刷新随 M-1 EVD 落账一并完成即可，不构成 M-2 门禁前的新增阻断。
3. 「绕开手法」的披露落点：建议在 M-1 EVD 行与发布清单各补一句（CHANGELOG 投影段已含「二次 apply 幂等」，若按 P3-1 勘误可顺带补明）。

---
*审查方：Code Reviewer Agent（独立审查，只读；未修改代码与 .governance）｜审查对象：FEAT-053 工作树 24 modified（HEAD = bff298d）｜结论：**APPROVED_WITH_NOTES / unresolved_blockers=0**（P0=0 / P1=0 / P2=2 非阻塞 / P3=4）｜机录义务：Coordinator 以 `review-record` 持久化本结论（round 0）。*
