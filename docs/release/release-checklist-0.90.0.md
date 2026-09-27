# Release Checklist — 0.90.0

- **版本**: 0.90.0 · **日期**: 2026-09-27 · **状态**: M-3 双半面审查中
- **主题**: 结构切换第一批——迁移验证与已知缺陷收口（DEC-252 / DEC-263）
- **版本定义**: 完成 DEC-252 范围内迁移验证、已知缺陷阶段性收口及切片前置；**未完成纵向切片、权威翻转和行为级终态验收**。

## 发布范围（冻结清单——DEC-263）

| 类型 | 项 | 说明 |
|---|---|---|
| 新能力 | FEAT-069 RB-2 前置批 | 敏感动作阻断接线（**出厂 WARN-only 不拦截**）+宿主激活前置判据+C-10 八分支看护 |
| 新能力 | FEAT-070 E-1-B | unit 权威清单人工确认链路+版本化 manifest（28 unit：2 confirmed/26 blocked） |
| 修复 | FIX-398 | SIGKILL 提交窗自愈+孤儿清扫+勘误+WARN 分流（RISK-060 关闭） |
| 新能力 | FEAT-071 E-1-A | 结构派生**影子**流水线（28 行零分歧；**切换判据 4 绿 3 红=不可切换**） |
| 搭车 | FIX-397 | 风险计数口径（DEC-256）+治理表行修复（非载荷治理修正） |

无破坏性变更；无机制激活（B-12/B-13 出厂姿态不变）。

## 候选态门禁（M-1 实测）

- 全量 pytest：4351P / 1F / 1S / 540 subtests（25:54）——唯一 F=`test_pin_revision_hashes_still_resolve`（M0 pin 既有漂移，DEC-249 先例族披露发布；**非本版载荷引入，不宣称全绿**）
- archguard ratchet：38/38 PASS（两次 sanctioned regen：DEC-260/DEC-262②）
- check-version-consistency：PASS（SKILL 0.90.0 权威+17 投影面+宿主标记+六字面量）
- check-release candidate：changelog/loop 门 PASS；execution gates 三组残留显式对账（M-3 双半面裁决）：①release-docs 三件套本提交入库（P3-5→消解）②governance health 24=REL-093 在途包契约标记，任务闭环自然消解（RELEASE 半面裁定不阻断）③内部 unittest 180s 预算超时=DEC-262 同族预算失真非测试失败（裁定不阻断，校准票 0.91 池；M-1 独立实测 4351P/1F 已承载测试事实）

## 已知问题与边界（逐项归因——DEC-263④）

1. RB-2 阻断面 WARN-only——翻转条件=B-12/B-13 独立授权票（RISK-059 关闭为前置；本版不翻转）
2. 影子判据三红（CJ-1 0/2、CJ-4 30/32 悬置、CJ-5 外部宿主未验）——结构派生**不可切换**权威清单
3. M0 pin 漂移 1F（既有族）
4. 官方审批边界不变：无 official approval / marketplace approval / universal runtime support 声明；RISK-036 维持打开（外部验证/官方提交/1.0.0 review 未满足）
5. 卫生批残留转 0.91 池（FEAT-071-R0 P3×4 等）

## 发布后验证计划

- check-release `--lineage-mode released --release-commit <sha>` PASS（tag peel 本地=remote+ledger 单父 transition+非 UNKNOWN/BLOCKED）
- 归档 integrity PASS（M-7）
- 核心功能冒烟：`/governance` bootstrap（0.90.0）+ governance-bootstrap 风险计数 18 面（DEC-256）
- 观察期：发布后 48h 无新增 P0/P1 报告（内部工具替代标准）
- **回滚触发绑定（P2-1——M-3 RELEASE 条件项）**：观察期内出现任一情形 → 立即进入 hotfix 0.90.1 或 tag 回退决策（按 rollback-plan §发布后回滚路径，历史 tag 变更需独立 DEC）：①新增 P0/P1 缺陷报告 ②`/governance` bootstrap 或 governance-bootstrap 冒烟失败 ③check-release released 复跑 FAIL

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
