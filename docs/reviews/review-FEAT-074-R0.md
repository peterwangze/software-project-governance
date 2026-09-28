# REVIEW-FEAT-074-R0 — 证据行实体解析与分类修复（DEC-278 单元一）

- **审查轮次**: R0（首次）
- **审查对象**: 工作树现行态 3 产物——infra/archive.py（五态分类重写）/ infra/tests/test_verify_workflow.py 新类 FEAT074EvidenceEntityClassificationTests（20 用例）/ docs/architecture/feat-074-classification-diff-20260928.md（差异留档）
- **日期**: 2026-09-28
- **基准**: DEC-278（单元一规格+MUST NOT+可证伪验收）+ docs/architecture/evidence-layering-design-admission-inventory.md
- **审查者**: Code Reviewer（只读；逐行）
- **结论**: **NEEDS_CHANGE**（P0=0 / P1=2 / P2=1 / P3=5）——代码面零 P0 零 P1；两条 P1 均落在差异档

## 1. 五维度结论表

| 维度 | 结论 | 要点 |
|---|---|---|
| 正确性 | **通过（代码面）** | 五态判定链（archive.py L1653-1713 _ref_verdict）亲读正确：REQ 登记来源优先（L1667-1679，registry∩task→ambiguous / registry→requirement 非门控 / task-side→生命周期 / 双无→missing）；FX 逐 ID 别名先于族判定、未列名→ambiguous（L1687-1693）；六条件逐条落地（可定位/生命周期关闭/周期封闭 max/非当前工作集/keep 词表=盘点§5 单源 L1171-1173/重复 ID 门 L1764-1767）；owning cycle=max 引用版本（L1795-1799，比旧「任一在窗」更保守，符合盘点 §2.1 β 判据）。转义管道三函数（L1180-1195）一致，两解析器同步采用（L579/600/614 与 L658/672） |
| 安全性 | **通过** | fail-closed 方向全部正确：missing/ambiguous/unknown_evd_id_shape/duplicate_evd_id/task_layout_anomaly/task_version_unparseable 六类默认禁迁且 detail 列阻塞 ID（L1786-1793）；unparseable 19 行保留禁迁（L1705-1712，未批量补猜归期）；无注入/敏感数据/权限面变更 |
| 可维护性 | **P2 附注** | 注释溯源质量高（单源纪律/context digest 钉扎 L2129-2148/resumable 世界判定对称）；但 FX 别名表 3 条注释与归档行事实不符（F-3） |
| 性能 | **通过** | O(n) 双遍扫描（重复 ID 预扫 L1643-1651 + 主扫）；无 N+1；keep 词表 6×子串扫描可接受 |
| 测试覆盖 | **通过（代码面）/ 不达（差异档）** | 20 用例覆盖完整（五态各≥1 正例 + 反例族：活跃/多引用 max/缺失/显式保留/重复 ID/未列名 FX/双重登记/转义管道/上下文 digest——逐一亲读）；夹具合成版本纪律（0.90.0/0.99.0）合规 FIX-352/353；test_archive.py 159 个测试方法亲数=159 且与分类内部零耦合（grep 零命中）；**但差异档 before/after 矩阵守恒性不达（F-1）** |

## 2. Findings

| ID | 级别 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| **F-1** | **P1** | feat-074-classification-diff-20260928.md §2.1/§2.3/§4.2/§4.4 | 差异档数字内部不自恰（4 处硬矛盾）：① §2.1 表 17 行分项行数加总=**484** vs 表头与 after 汇总行声称 **482**；② §2.1 分项字节加总=**1,167,378** vs 汇总行 **1,164,905**（后者恰为盘点早时点 EVD 面值 1,164,873+32B，疑似沿用早时点数字未随晚时点快照〔sha256 84323ebf…，1,778,219B/2,918 行〕更新）；③ §4.4 (ii) 对账公式按字面计算 163+12+103+12+9+4+3−2=**304**≠**290**（结论 290 恰可由 live 317−(i)23−(iv)4=290 成立——公式写错而非结论错）；④ §4.2 枚举 REQ-007/029/059~081(23)/082~085(4)/087/089~100(12)=**42 个 ID** vs 声称 **40 唯一**；附带 §2.3「EVD-1205~1215 中 12 行」（该区间恰 11 个 ID）。DEC-278(4) 验收要件「修复前后逐行差异留档」+DEC-278(6) M-0 前置「数字与判据勘正」——本票验收标准明示「档内数字内部自洽」，不达 | 本轮勘正差异档：重跑对账脚本或修正汇总行/公式/枚举，使全档算术可复算；在途 EVD-1216~1224（9 行）在矩阵中的承载行显式化（当前 before 加总与 §5 反例族表述无法对齐） |
| **F-2** | **P1** | 差异档 §2.1 行「live→active 4」+§5「活跃 5 行」；archive.py L509-510（既有）；plan-tracker L96/L103/L105 | 差异档事实失实+暴露既有潜伏缺陷：§2.1/§5 称 FIX-343/FIX-349×3/FEAT-059 为「热表活跃/进行中」，但 plan-tracker 亲读三行状态列均以「✅ 完成」开头（终态）——FEAT-059（L96）状态格含「P3×5 **非阻塞**」、FIX-343（L103）含「tpa **假阻塞**池清零」，均命中既有 `_task_status_is_archivable` open_markers 朴素子串扫描（「阻塞」∈「非阻塞」）→ 终态任务被误判 active_task_ref。保留方向 fail-closed（安全，行仍留热），但：reason 归因系统性错误污染单元三修复台账输入；§5 作为「安全语义回归证明」表的事实陈述失实。既有函数本票未改动（非回归；旧行为=no_task_family_ref 留热，新行为=active_task_ref 留热，保留不变仅 reason 变），但单元一「可解释 reason」验收面首次暴露它 | 本轮：差异档勘正 5 行的真实归因（终态+否定语境假阳性）；登记后续票修复 open_markers 否定语境匹配（非阻塞/假阻塞/伪阻塞排除或词边界），或至少在单元三台账标注「active reason 对终态行不可信」。FIX-349 状态格完整内容本次 read 截断，其具体命中 marker 未亲证（FEAT-059/FIX-343 两例已亲证模式） |
| **F-3** | P2 | archive.py L1159/1161/1164 注释；差异档 §4.3；test L22116 注释 | FX 别名表 3 条溯源注释与归档行事实不符：FX-189 注释「design ADR batch」（归档行 v0.1.0~v0.65.1.md L29 实为 Slice 2 loop_engine core）；FX-191 注释「slice 2」（L31 实为 Slice 4 loop_migration）；FX-194 注释「quality audit batch」（L34 实为 Slice 7 Gate re-labeling）——差异档 §4.3 表同源错位。**映射功能正确：14/14 恒等映射的存在性+归档版本经归档行全部亲证**（FX-130/131@v0.64.0、FX-175@0.63.0、FX-177@0.63.1、FX-179@0.63.2、FX-181@0.63.3、FX-183@0.63.4、FX-188~194@0.65.0；999f69d 在 FX-188 归档行字面出现）。另 test L2216 注释「REQ-082-style」用于「NOT in registry」例——实际 REQ-082 在登记表（plan-tracker L430），措辞误导 | 随勘正票更正 3 条注释与 §4.3 描述、测试注释改为合成 ID 或准确例 |
| **F-4** | P3 | archive.py L1695-1696/1799 | _ref_verdict pass payload 未显式 semver 校验；L1799 `max(…, key=_version_to_tuple)` 在混合 None key 时会 TypeError。当前不可达（task_versions 值域恒 semver：_parse_completed_task_versions L683 已滤+归档提取 regex 保证），但依赖隐式不变量 | pass 分支加 `_version_to_tuple(payload)` 防御或断言（后续票顺手） |
| **F-5** | P3 | archive.py L1695 vs L1701 | one-shot 路径 task_versions 先于 context 构建非原子：mapping 建后 plan-tracker 并发改写（重开）时 stale mapping pass 可绕过 active 检测。resumable 路径有 context_digest 拒绝防护（L2290-2299）；one-shot 无锁（既有状态，本票未恶化，窗口=单次调用内） | 记录；如需收紧可在 one-shot 也复用 context 比对 |
| **F-6** | P3 | archive.py L1648/L1730/L3044 | 分类器与归档索引提取仍用 raw `line.split("|")`——EVD 行内转义管道会列错位。当前数据面关联 Task 列无转义管道（风险为零）；单元一转义修复范围=plan-tracker 行（规格内），EVD 行面未承诺 | 后续票观察项（若未来 EVD 摘要列出现 `\|`） |
| **F-7** | P3 | archive.py L1253 | `_requirement_registry_ids` header 判定 `startswith("需求ID")` 宽松（无分隔行校验、扫至 heading）——叙述表撞词会误收。当前数据面唯一（plan-tracker L370 仅一处） | 记录 |
| **F-8** | P3 | 架构提示（非缺陷） | 单元一落地即扩大实际迁移面（全窗 would_archive 11→201）：DEC-278 授权范围内（REQ/FEAT 解锁正是单元一目的；存量清偿归单元三按既有获批政策）。操作面提示：单元三执行前任何全窗 migrate 调用的迁移量将大幅高于 before 基线——Coordinator 调度须防「顺手迁移」绕过单元三复验（差异档 §0 注已自我声明红线遵守） | 调度约束记录 |

## 3. 审查重点 1-8 逐项结论（浓缩）

1. **五态分类**：✅ 判定链亲读正确；旧 reason 消费者清查亲证：全仓 11 处命中=4 处历史文档（盘点/差异档/release-checklist-0.80.0）+3 处 archive.py 注释（「replacing the old bucket」）+2 处测试（L22270 assertNotIn 负例守护）——**零功能性消费者**，Developer 声明成立。ref_types 字段=五态词汇表，测试断言值域（L22274-22285）✅
2. **六条件**：✅ 逐条对照 DEC-278 §3.1 落地；「版本已发布≠生命周期关闭」经 active 拦截面验证（test_active_hot_ref_retained：tv=0.82.0 已发布+🔄 进行中→active 留热）；fail-closed 方向全部正确（见安全性维度）
3. **FEAT/FX/REQ 三修复**：✅ FEAT 入族（L1094-1098）+task_priority 词表对齐；FEAT-073 类型 task+owning 0.92.0 超窗留热/FEAT-074 进行中留热（测试 L22229-22247 合成 0.99.0 双例+差异档 §0#6 双源）✅ 可证伪验收 #1 达成；FX 14/14 亲证（见 F-3）+未列名 fail-closed（FX-187/195 归档存在且未入映射，亲证）✅；REQ 优先判定边界正确（含双无→missing），40 唯一 ID 双重登记零例亲证（被引高频 REQ-007/029/083/092/095/096 在 archive/tasks 零命中）✅ 可证伪验收 #2 达成（计数 40 vs 枚举 42 矛盾归 F-1）
4. **转义管道**：✅ FEAT-047 根因=解析器盲区亲证（plan-tracker L98 原文 `block\|advisory` 转义管道在列内；9 原始管道=8 真分隔+1 转义）；`(?<!\\)\|` 负向后行、split/count 同源；两解析器同步；「改解析器优于改数据」论证成立（内容保全）。REL-086=真缺列分隔符（数据面），§6.1 提案与 Coordinator 落地（L97 两格拆分）亲证一致 ✅
5. **MUST NOT 红线**：✅ 全部通过——零新行族写迁移（分类器仍只扫 `| EVD-`，L1727-1729）；零 28s 阈值/语义变更（三产物不含 verify_workflow.py；archive.py 阈值常量 L103-105 原样）；零 loop_migration 契约变更（`_MIGRATION_JOURNAL_SCHEMA` L110 不变；context_digest 为新增字段，旧 schema journal 在非 finalized 世界 loud 拒绝=fail-closed 演进，差异档 §8 已披露）；零宽松正则（未列名 FX/双重登记/重复 ID 三处显式拦截，_EVD_ID_SHAPE_RE 未动）；零抬阈缩窗/补猜归期
6. **回归测试与差异档**：代码面 ✅（20 用例覆盖面完整、test_archive 159/159 静态亲证）；差异档守恒性 **不达**（F-1）
7. **越界检查**：✅ 恰 3 产物（archive.py 变更面全部亲读识别、测试 +322 行=L22039-22357 新类吻合、差异档 175 行）；test_archive.py 零改动（159 方法亲数+零耦合）；`.governance/` 零写入采信（差异档声明+REL-086 落地由 Coordinator 承担）
8. **AI 专项**：①mock 残留：无（tempfile+patch.object 合法）②硬编码返回值：无逻辑绕过（别名表为数据映射，注释错位归 F-3）③幻觉 API：无（全部调用函数实存亲读；git 首提 commit 未独立复跑——见遗留项）④未实现 TODO：无 ⑤过度实现：无（keep 门/max 语义/digest 钉扎均为六条件规格组成；无行族迁移能力）

## 4. 硬门槛自检

- [x] P0 阻塞问题数 = 0（F-1/F-2 为 P1）
- [x] 5 维度 100% 覆盖
- [x] 每条发现标注级别（8/8 条有 P0~P3 标签）
- [x] 设计一致性检查已完成（DEC-278 六条件/MUST NOT/可证伪验收逐项对照）
- [x] AI 专项 5 项全部完成
- [x] 引用事实带文件+行号
- [x] Developer 测试输出采信+静态交叉印证（159 方法数亲数吻合；stash 对跑基线无法独立复现——采信并声明）
- [x] 只读审查：未调用 Write/Edit/Bash/Agent/AskUserQuestion

## 5. 终态结论

**NEEDS_CHANGE** — 依据：P0=0 但差异档（本票三产物之一、DEC-278(4) 验收要件载体）数字内部自洽性与事实准确性不达本票明示验收标准（F-1/F-2 两条 P1，「原则上本轮修改」，且勘正义务与 DEC-278(6) M-0 前置冲突不可作为常规遗留项漂移）。**代码面（archive.py + 测试）无任何必改项**——R1 复审聚焦差异档勘正（重跑对账+修正 active 5 行归因表述+3 条 FX 注释顺手更正），可附 parser 否定语境假阳性的处置决策（修复或台账标注）。复审不必重查代码主链。

## 证据清单（关键锚点）

1. archive.py：L1094-1098（FEAT 入族）/L1128-1137（五态+other-entity）/L1148-1165（FX 14 条）/L1171-1173（keep 词表）/L1180-1195（转义管道）/L1229-1261（registry）/L1264-1306（context）/L1562-1807（分类器）/L1653-1713（_ref_verdict）/L1764-1773（重复+keep 门）/L1795-1806（max 语义）/L110（journal schema 不变）/L2129-2148（digest）/L509-510（open_markers 根因）
2. test_verify_workflow.py：L22039-22357（20 用例逐行）/L39（archive_mod 导入）
3. 差异档 175 行全文；盘点文档全文；DEC-278（decision-log L220）
4. plan-tracker：L96（FEAT-059）/L97（REL-086 归一）/L98（FEAT-047 转义）/L103（FIX-343）/L105（FIX-349）/L370+L372-463（registry）
5. archive/tasks grep：FX 14/14 归档行（含版本+commit 999f69d 字面）；FX-187/195 未列名存在；被引 REQ 零归档命中
6. 全仓 grep live_or_unresolvable_task_ref=11 处（零功能消费者）；test_archive.py 159 个 def test_ 亲数

## 遗留不确定项

1. git pickaxe 首提 commit（77df046/20bdc53/7792b4e）未独立复跑（Reviewer Bash 禁止）——采信差异档双源声明+归档行交叉印证
2. FIX-349 状态格完整内容被 read 截断——具体命中 marker 未亲证（FEAT-059/FIX-343 模式已双例亲证）
3. Developer 测试输出（20/20、159/159、聚合 exit 0、stash 对跑 9 项基线）采信——159 方法数与 20 用例静态亲证吻合
4. before 快照 sha256 84323ebf 无法独立复算（evidence-log 已漂移至现行态）
5. `.governance/` 零写入（Developer 面）采信
