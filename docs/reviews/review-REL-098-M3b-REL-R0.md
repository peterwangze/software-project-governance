# Review Record: REL-098 — M-3b 发布门禁审查（REL，R0）

- **Task**: REL-098（M-3b——发布链双审第二面；第一面 M-3a 版本面 CODE R0 已 APPROVED_WITH_NOTES/unresolved_blockers=0，报告 docs/reviews/review-REL-098-M3a-CODE-R0.md）
- **Reviewer**: Release Reviewer Agent（角色定义 agents/release-reviewer.md + skills/release-review/SKILL.md 已加载并遵循；只读——零文件修改、零 .governance 写入、零用户交互）
- **对象**: 0.94.0 发布就绪状态（发布四件套 + CHANGELOG + plan-tracker 治理面 + M-2 执行门实测事实 + git 载荷窗口独立机验）
- **日期**: 2026-10-03 · **Round**: R0
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers = 0）** · P0=0 / P1=0 / P2=1 / P3=4

## 硬门槛自检

回滚方案存在且可执行 ✅（枚举 git 实测吻合+四场景覆盖+依赖警告在场）· 检查清单逐项有结论 ✅（十票+版本面+八层矩阵逐层）· 每条发现标注 P0~P3 ✅ · 事实红线遵守 ✅（未实跑项如实标注「Coordinator 提供/待验证」，未采信任何自报为实测）

## 一、审查输入实读清单

四件套：release-checklist-0.94.0.md（60 行）/ rollback-plan-0.94.0.md（45 行）/ feature-flags-0.94.0.md（28 行）/ docs/reconciliation-0.94.0.md（80 行）。治理面：CHANGELOG 0.94.0 段 / plan-tracker（L11 工作流版本、L44 总览、L80-89 任务表十票、L97 REL-097 先例、L203 0.94.0 路线图行）/ evidence-log EVD-1293~1305 抽验 13 条全实存。M-2 实测：三轮 check-release——18 静态面全 PASS（含热源三 FAIL 修复清零）；执行门 verify/e2e/unit 全 PASS exit 0；唯 governance health FAIL（--fail-on-issues exit 1，5 未豁免 WARN 类）；全量回归 4666P/0F/1S/563 subtests。

## 二、发布范围冻结清单逐项结论

十票+版本面 11/11 全 PASS（FEAT-081 2aa2377 / FEAT-082 5de8548 / FEAT-083 c00d70c / FEAT-084 0377b78+memo 9a527cb / FIX-421 8568b1b / FIX-422 768021b / FIX-423 9018006 / FIX-424 3883407 / FIX-425 b0075d8 / FIX-426 af7cfbd——git 实测全在场；EVD 1293~1305 实存；R0 全 AWN/0；REL-098 M-1 工作树待提交态与 checklist 一致）。载荷窗口 `84f8819..af7cfbd` 实测恰 11 commits 与清单/CHANGELOG/rollback 三处枚举一致。

## 三、arch D7 终态验证矩阵逐层判定

测试 ✅（4666P/0F 基线+双跑先例）/ 治理 ✅（strict 0 FAIL/6 WARN 全预存；governance health 子门为 WARN 处置题→§五）/ 归档 ✅（M-8 dry-run 后置）/ 行为安全 ⏳（B-23~B-27 全披露+回滚+零失败佐证；随收口）/ 受管数据 ✅（write-guard PASS）/ 发布 ⏳（唯 governance health 待裁决）/ 可追溯 ⏳（M-5a/M-6/M-7 后段）/ 回退 ✅（本审查硬门槛）。八层无缺失，待达项全有里程碑归属。

## 四、回滚方案审查（硬门槛）

**判定：存在 ✅ 且可执行 ✅**

1. 枚举正确性：序③ 11 commit 逆序序列 = git 实测窗口精确 LIFO，11/11 吻合（含 memo 9a527cb）
2. 区间锚定：下界 0e277af = `v0.93.1^{}` peel 实测吻合；上界回填位纪律在场
3. 依赖警告三组在场且语义正确（依赖者先回退：083→082→081；426→425→424）
4. 三序结构完整（数据面/版本面 regen 幂等实测 PASS@0.94.0/载荷面按需）+四场景全覆盖（fail-closed/发布后三步/tag 误推独立 DEC/hotfix 不重写 tag）
5. 零新增数据面三声明三方互证一致

## 五、M-2 唯一阻断项（governance health 5 WARN 类）逐类裁决建议

先例基线：REL-097 用户 M-7 GO 双轮裁定「13/RB2/28n 披露态——用户 GO 终审」（plan-tracker L97/L205）。本次 5 类逐一对应：

| # | WARN | 裁决建议 | 理由 |
|---|---|---|---|
| 1 | 13 DEC-ID gaps [3,24,141,142,178] | **披露态放行**（不可修） | 前纪元历史编号缺口，补造违反 arch D3 事实纪律；reconciliation §三 #1 对账在案；REL-097 同族 |
| 2 | 18d-RB2「无活跃 P0/P1 unit」 | **披露态放行**（结构性自然态） | 任务表 33/33 清零的必然结果——治理健康态非缺陷 |
| 3 | 18d-RB2 demo actions 契约缺失（×2） | **披露态放行**（设计语义） | RB2_SENSITIVE_BLOCK_ENFORCED=False 出厂（FEAT-069 授权票翻转前 enforcement off；flags L10 零改动）；REL-097「RB2 接受披露」同族 |
| 4 | 28n archive.py 4241 | **披露态放行**（可修不本窗修） | FIX-417 拆分残留阈值披露+0.94 拆分候选已登记（reconciliation §三 #7）；发布范围冻结，中途加票违反纪律；REL-097 同族 |

**独立结论**：无一「可修应修而未修」；REL-097 先例逐族覆盖。建议按先例提交用户 M-7 GO/NO-GO 终审。最终裁决权在用户。

## 六、发现列表

- **F-1（P2）** rollback-plan §回滚区间「窗口计数」列 4bfa1f5——git 实测为 0e277af 祖先（区间外），真实窗口 0e277af..af7cfbd = 13 commits 非 14 项。计数事实错误；序②/③执行序列不受影响（4bfa1f5 从非 revert 对象）。随 M-5b/M-8 勘正。非阻塞。
- **F-2（P3）** rollback 序③「docstring 票先于 pin 测试票回收」与序列字面歧义——序列依赖语义正确。措辞勘正建议。
- **F-3（P3）** 载荷 revert 全链无演练记录——regen 幂等实测+git 机验+三代同构先例；如实披露不阻断。
- **F-4（P3）** 5 WARN 类处置待用户终审（§五）——与 REL-097 双轮裁定同构。
- **F-5（P3·信息性）** checklist 矩阵状态列 @M-1 快照滞后于 M-2 事实——随 M-8 回填既定口径。

## 七、其余审查维度

CHANGELOG 用户视角完整（Added×3/Changed×1/Fixed×6 全场分类正确；FIX-349 日期零预填纪律在场；决策链/证据链抽验 13 条实存）· 版本号 minor bump 正确（新特性四件；无跳号无破坏性变更三方互证）· Feature Flags 完整（零新增+沿用表+B-23~B-27 逐项回滚+出厂姿态一致）· 边界声明四件套全在场（保守边界 REL-021 token 全量）。

## 八、结论

**APPROVED_WITH_NOTES（unresolved_blockers = 0）**——0.94.0 发布就绪。唯一残项（governance health 5 WARN 类）逐类裁决建议全部披露态放行，提交用户 M-7 GO/NO-GO 终审。P2×1 与 P3×4 均非阻塞，随发布链后段收口。发布 GO/NO-GO 最终裁决权在用户。
