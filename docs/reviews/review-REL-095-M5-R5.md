# REVIEW-REL-095-M5-R5 — 0.92.0 CHANGELOG 发布态 + ledger candidate 轻量审查（R5）

> **任务**: REL-095 M-5（发布态批前置审查）· **轮次**: R5（轻量——三文件未提交批）· **Reviewer**: Code Reviewer Agent · **日期**: 2026-09-29 · **绑定**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`
> **审查对象（git status 亲证）**: `M project/CHANGELOG.md`（0.92.0 段发布态改写）+ `M docs/release/release-plan-0.92.0.md`（恰 2 行顺修）+ `?? skills/software-project-governance/core/releases/0.92.0.json`（ledger candidate）
> **结论**: **APPROVED_WITH_NOTES** · **unresolved_blockers = 0** · P0=0 / P1=0 / P2=0 / P3×3（全部非阻塞，M-8 终账核对消化即可）

---

## 0. 终态字段（Check 30 消费）

```json
{"task": "REL-095", "round": 5, "result": "APPROVED_WITH_NOTES", "unresolved_blockers": 0, "blocking_findings": 0, "p0": 0, "p1": 0, "p2": 0, "p3": 3}
```

---

## 1. RL-F1 八项逐项在文核验（对照 R3 RELEASE RL-F1 P2 全文 + checklist 放行条件⑥ 权威口径）

| # | RL-F1 项 | 在文核验 | 事实依据（独立复测） |
|---|---|---|---|
| ① | M-2 整改叙事段 | **PASS** | CHANGELOG L77「M-2 整改叙事（发布链 M-2/M-2R 补记——EVD-1233/1234/1235）」全链在文：受控回退 6 归期行（tasks would_archive 8→2）/有界迁移 2 任务+18 EVD（4 随行+14 补完成）/EXC-002 限域例外/B2 单条精确豁免/M-2R 有条件收口（「非原生全绿」原文如实登记）。数字逐项 vs EVD-1233（evidence 2939→2921 行、plan-tracker 524→522 行、幂等 0 动作、journal 区分 4 vs 14、隔离副本回滚演练、验收 5/6）/EVD-1234（九键实测、六项验收 6/6）/EVD-1235（@df26f7e 有条件收口）与 DEC-283（受控回退+B2 一次性授权）/DEC-284（扩展授权 2任务+18EVD——4 随行+14 逐 ID 列出恰 14 项）/DEC-285（EXC-002 条款全要素）——**全部吻合，零编造**（.governance 两 log 亲读） |
| ② | 双例外并列（EXC-001 块+EXC-002 块六要素+B2 行+advisory 两面） | **PASS** | L21 标题「发布准入=双例外+B2 豁免——EXC-001 与 EXC-002 条款摘要并列」；EXC-001 块 L23-28（基线/上限/发布时点重测/有效期/义务/迁移前提）；EXC-002 块 L30-37 **六要素齐**（覆盖面 178=160+4+14／承载体〔机注不可达〕／增长容忍 0／期限 min(0.93 准入,2026-10-12)／基线附件 222 行+输入锚 `40eb6f7`+sha256 2365c01c／0.93 承接 FEAT-076+Owner 四角色）vs DEC-285 逐要素一致；B2 行 L39（loop-claims 第 5 条 LRC-EXEMPT-FIX401R0-79-1）+ advisory 两面 L41 |
| ③ | 决策链 269~285 全列（17 条） | **PASS** | L45：269/270/271/272/273/274/275/276/277/278/279~281（×3）/282/283~285（×3）=恰 17 条；抽查 273（FIX-400 完成入账）/277（FIX-401 完成入账）/283/284/285 全部在文且裁决主题正确 |
| ④ | EVD-1216~1236 | **PASS** | L8 段头「EVD-1216~1236」+ L45「EVD-1216~1236（含发布链 EVD-1230~1236）」——EVD-1233/1234/1235/1236 四条亲读在案（evidence-log L2922/2925/2926/2933） |
| ⑤ | 行为变更 B-1~B-7（同源抽查 3 项+回滚） | **PASS** | L64-73 B-1~B-7 全段+回滚总说明（rollback-plan §回滚三序）。同源抽查 3 项 vs `feature-flags-0.92.0.md`：B-1（revert `e65b317`、9→391 tok、3859/5337/5609）、B-5（revert `df26f7e` 单提交自洽/锚与账本同提交）、B-6（18 EVD 出热、消费者=`archive/index.md`、回滚=迁移面序①）逐字同源 |
| ⑥ | 三面重测数字（独立实测复核） | **PASS** | evidence-log **1,757,633B**（Get-Item 实测=精确吻合）；decision-log **254,420B**（实测=精确吻合）；archive.py **5,508 行**（ReadAllLines 全行计数=精确吻合；注：非空行口径 4865 不足以判阈——CR-F2 按全行 5508>5000 成立）。时点演进链终点=当前实测精确值，起点 1,753,848 与 EVD-1235 一致，@HEAD `a31b878` 时点标注在文（HEAD 亲证=`a31b878`） |
| ⑦ | 发布日期不预填（占位+FIX-349 句在） | **PASS** | L5 `## [0.92.0] - <待回填 taggerdate>` + L6 FIX-349 口径注释（「发布日期零预填；M-7 annotated tag 落地后以 taggerdate 权威回填」）+ L75 发布态注记重申；发布 tip hash「由 M-5 提交生成，不预写」（L83）——零预填纪律维持 |
| ⑧ | Added/Changed/Fixed 保持+发布终账块 | **PASS** | L47-62 三段保持（diff 未触碰）；发布终账块 L79-84（M-3 双半面/M-4 四件套/M-5 本步/Commit 区间 `bd9bfc1..HEAD`=14 @`a31b878`——**亲测复核：HEAD=`a31b878`、`git rev-list --count bd9bfc1..HEAD`=14 吻合**） |

## 2. ledger 逐键 vs 0.91.0.json（git show HEAD 实读基线）

| 键 | 0.92.0.json（candidate） | 0.91.0.json（released 基线） | 判定 |
|---|---|---|---|
| 结构 | 单行 compact、键序 artifacts→effective_state→events→lifecycle_state→provenance→schema_version→trust→version（sorted canonical） | 同序 | ✓ 一致 |
| artifacts | changelog=project/CHANGELOG.md；release_docs=四件套 0.92.0 名（字母序，四文件均实测存在）；review_evidence=[.governance/evidence-log.md] | 同构（0.91.0 名） | ✓ 同构 |
| effective_state | amendments=[]/lifecycle_state=**candidate**/withdrawn=false | released | ✓ candidate 中间态正确 |
| events | **[]**（candidate 无事件——0.91.0 有 transition 事件，released 态差异） | 1 条 candidate_to_released | ✓ 预期 |
| trust | candidate_commit.derivation=**git_commit_adding_path** | 同 | ✓ 派生同源 |
| version/provenance/schema_version | 0.92.0 / native / 1 | 0.91.0 / native / 1 | ✓ |

**`release-ledger --version 0.92.0 --no-remote` 复跑**：state=FAIL，issues=**恰 1 条**——「candidate_commit: expected exactly one commit adding …, found 0」＝candidate 文件尚未提交的**预期中间态**（M-5 提交后即消）；trust_level=**NATIVE_CANDIDATE**；**无其他 issue** ✓（与任务预期完全一致）。

## 3. no-overclaim 逐字核验

- **intro 句（L10）**：「结构性解锁已完成；容量问题未技术消除。本轮不执行 EVD 物理迁移，按限期例外控制，后续迁移以读取契约闭合为前提。」——与 DEC-282(7) 原文（decision-log L224 亲读提取）**逐字一致** ✓。
- **178/18 精确口径括注**：「178 行历史证据面未迁移由 EXC-002 纸质例外治理」「18 行有界迁移〔2 任务+18 EVD〕属 DEC-284 补完成授权，非「本轮不执行」矛盾」——与 release-plan L14 精确措辞**逐字一致**（仅括号形制差异，零语义差异）✓；「补完成授权非矛盾」口径经 DEC-284（14 任务已归档、旧 FEAT 前缀解析缺陷滞留热表）事实支撑成立。

## 4. 顺修 2 行独立复测（M4R4-F1/F2 消化）

- **F1（release-plan L27 MINOR 依据行）**：新增区间限定〔六票+发布链对账区间 `e65b317^..df26f7e`，搭窗 `4cb3081` 除外；全窗 `bd9bfc1..df26f7e`=56 文件 +5523/−239〕——独立复测：`git diff --stat e65b317^..df26f7e` = **51 文件 +5333/−216** ✓；`git diff --stat bd9bfc1..df26f7e` = **56 文件 +5523/−239** ✓——两窗数字逐位吻合，措辞与 M4R4-F1 建议句式对应。
- **F2（release-plan L111 门禁摘要第 1 行）**：新增「（面级 9 面；issue 级 7）」注——落实 M4R4-F2「面级/issue 级混排」建议（2+5+2=9 面 vs 7 issue 双口径并列）✓。
- diff 亲证：release-plan 变更**恰 2 行**（2 增 2 删），无第三处改动 ✓。

## 5. 静态检查复跑（只读）

- `check-version-consistency`：**PASSED**（13 文件+bootstrap markers 全一致）。
- `check-manifest-consistency`：**PASS**（983 canonical / 1135 actual——较 M-3 CODE 时点 976/1128 增长可归因 M-4/M-5 新增文件，含未提交的 candidate json 计入 actual 面）。

## 6. AI 专项——引用 6 处抽核（全命中）

1. EVD-1233（L2922）：18/18 精确、2939→2921、524→522、幂等 0/0、4 随行 vs 14 补完成、隔离副本回滚演练 ✓。
2. EVD-1234（L2925）：九键实测、REQUIRED_EXEMPTIONS_SHA256 **d47f5d16**、六项验收 6/6 ✓。
3. EVD-1235（L2926）：@df26f7e 双源复测、candidates **1096**、豁免 5、热表 1,753,848B、遗留面 EVD-702/1194/1198 ✓。
4. EVD-1236（L2933）：M-3 双半面+M-4 四件套、RL-F1=M-5 MUST、CR-F1/F2 数字 ✓。
5. DEC-283/284/285（decision-log L225/226/227）：受控回退+B2 授权／扩展授权 2任务+18EVD（14 项逐 ID 恰合）／EXC-002 限域条款 ✓；`df26f7e`/`12bef7c` 提交亲证存在且主题吻合 ✓；digest 双锚实测：`4f8a6cc8…`@df26f7e^ → `d47f5d16…`@HEAD（loop_runtime_claims.py L118）✓。
6. 1096@df26f7e **时点标注**：CHANGELOG L77「EVD-1235@`df26f7e`：…candidates 1096」——数字与锚定时点双标注在文 ✓。

## 7. 五维度结论（硬门槛=100% 覆盖）

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | §1 八项+§2 逐键+§4 独立复测全吻合；无逻辑/事实错误 |
| 安全性 | PASS | 纯文档+单行 JSON；无敏感数据/注入面；不伪造 released 态、不预填日期/hash（fail-closed 纪律维持） |
| 可维护性 | PASS | 结构对齐 0.91 先例；EXC-002 六要素模板化；行为变更段与 feature-flags 同源（P3 措辞项见 findings） |
| 性能 | PASS（不适用面） | 无运行时代码变更（三文件均为文档/数据面） |
| 测试覆盖 | PASS | 验证面=静态复跑三件套（version/manifest/release-ledger）+数字独立复测，全部执行 |

## 8. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| 5 维度覆盖 | **100%** |
| 每条发现标注级别 | **100%**（P3×3） |
| 设计一致性（ADR/DEC 契约） | **已完成**——DEC-282(1)(4)(7)/DEC-283~285/DEC-260/DEC-262/FIX-349 逐项对照一致 |
| AI 专项 5 项 | **全部完成，零命中**（mock 残留=无代码面；硬编码返回值=数字全可溯源且独立复测吻合；幻觉引用=6/6 实存在案；未实现 TODO=占位符均为显式回填位非债务；过度实现=顺修恰 2 行零范围外改动） |

## 9. Findings（P3×3——全部非阻塞）

| # | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | **P3** | docs/release/release-checklist-0.92.0.md L20 | 残留裸「窗口 diff 51 文件 +5333/−216」——M4R4-F1 标记双位置（release-plan L27 ✓已修 / checklist L20 未修）；checklist 自称「0.92.0 窗口=bd9bfc1..tip」口径下仍有指代歧义（事实完备无错，仅限定词缺） | M-8 终账核对时补区间限定词（同 release-plan L27 句式），或随 M-5b/M-8 批顺修；非阻塞 |
| F-2 | **P3** | R3 报告⑥措辞 vs checklist ⑥ 权威口径 | R3 放行条件⑥ 描述含「双位同步 project+root」，但 checklist ⑥（条件本体）仅要求 project/CHANGELOG.md（canonical）；根面 `changelog.md`（git 实录小写名）自 0.88.0 后 0.89~0.91 三版**零同步先例**（v0.91.0 tag 与 HEAD 亲证均仅 0.88.0 段），根面文件自载「canonical=project/CHANGELOG.md」。本批不触根面=先例一致，**非缺口**——记录以闭合 R3 措辞与实操差异，防 M-8 终账误判 | M-8 终账核对按 checklist ⑥ 权威口径执行；根面 F-10（生成式投影/sync check）维持 0.93 候选池 |
| F-3 | **P3** | project/CHANGELOG.md L39/L70 | B2「受控解冻」语义以「DEC-283 题 2 一次性授权+双锚 re-pin+正负因果测试+revert 单提交自洽」成分转述，未逐字出现「受控解冻-差异审查-重新冻结」短语（权威源=EVD-1234/DEC-283） | 实质成分在文、语义无缺失；M-8 终账核对按语义成分核对即可，无需改文 |

## 10. 证据清单

1. `git status --porcelain` / `git diff`（三文件批次与两处顺修亲证）；`git diff --stat` 双窗复测（51/+5333/−216；56/+5523/−239）。
2. `git show HEAD:skills/.../releases/0.91.0.json`（ledger 基线实读）+ 0.92.0.json 工作区实读（逐键对照）。
3. `verify_workflow.py release-ledger --version 0.92.0 --no-remote` 复跑输出（唯一预期 issue、NATIVE_CANDIDATE）。
4. `verify_workflow.py check-version-consistency`（PASSED）/ `check-manifest-consistency`（PASS 983/1135）复跑输出。
5. `.governance/evidence-log.md` L2922/2925/2926/2933（EVD-1233~1236 亲读）；`.governance/decision-log.md` L224~227（DEC-282(7)/283/284/285 亲读）。
6. 文件实测：evidence-log=1,757,633B、decision-log=254,420B、archive.py=5,508 行（全行口径）。
7. git 亲证：HEAD=`a31b878`（M-4 批=四件套+三报告 722 insertions）；`rev-list --count bd9bfc1..HEAD`=14；`df26f7e`/`12bef7c` 提交在案；digest `4f8a6cc8`@df26f7e^→`d47f5d16`@HEAD。
8. `docs/release/release-checklist-0.92.0.md` L70-75（放行条件⑤⑥ 权威口径）；`docs/reviews/review-REL-095-RELEASE-R0.md` L104（RL-F1 定义）；`docs/reviews/review-REL-095-M4-R4.md`（M4R4-F1/F2 定义与建议句式）。
9. 根面先例：`git show v0.91.0:changelog.md` / `HEAD:changelog.md` 均仅 0.88.0 段。

---

*本审查只读执行（产品代码零修改）；review-record 机录 round=5 随本报告由 infra 命令执行（task=REL-095）。REL-095 M-5 批在落实 F-1 时无需返工——三 P3 均为 M-8 终账核对位，不阻塞 M-5 提交。*
