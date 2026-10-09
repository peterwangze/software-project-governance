# REVIEW-REL-101-M3b-RELEASE-R0 — 0.97.0 发布就绪态 RELEASE 审查（Release Reviewer，2026-10-09）

- **Reviewer**: Release Reviewer（M-3b 半面，只读审查+独立复跑门禁）
- **Verdict**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**——条件：全量 pytest 联动失效条款（已满足：EVD-1353 = 4758P/1S/563st 0F exit 0）

## A. 独立复跑事实
1. `check-release --version 0.97.0 --require-changelog --lineage-mode candidate`：**FAILED - 3 issue(s)**，全部=release-docs 三件套缺失（M-4 待落盘）；**其余 22 面全 PASS**（含四执行门 exit=0：verify/governance health/e2e/unit tests；loop runtime claim gate 1192/1192；dsh 隔离升级冒烟）。与 M-0 §7 C3 预期态精确一致。
   - 措辞精确化：「candidate PASSED 全绿」不可字面复现——真实输出 FAILED-3（全为 M-4 面）
2. `check-injection-budget`：strict 6172≤6200 PASS + [FROZEN] 28tok ACTIVE；lightweight 4416 PASS；standard 5899（M-0/EVD-1351 台账）
3. governance health exit=0（风险改形后 risk-log 与门禁自洽 ✓）

## B. 七重点结论
1. **C1~C6 兑现**：C1 ✓（五契约齐）/C2 ✓（23 文件版本面+一致性机证）/C3 快面 ✓（全量联动见 E）/C4 未落盘=非阻断预期态/C5 进行中→**双 AWN/0 已齐**（M-3a+M-3b）/C6 ✓（30c×42 维持接受基线）
2. **CHANGELOG 发布质量**：准备态注记 ✓（FIX-349 零预填）；升级路径 ✓（/plugin update+FEAT-035 确认门）；30c 执法激活披露 ✓（行为变更段+双回退通道）；决策/证据链 ✓（DEC-326/327/328 L193~195 实读）；再生纪律段 ✓
3. **回滚方案**：CHANGELOG↔M-0 C4↔执行包三方一致（git revert 主轨+/plugin update 回退）；「M-4 落盘后生效」诚实注记；无 schema 变更=无数据迁移负担
4. **风险面**：三行改形≠关闭、10-31 复评窗不变、监管连续性保持（均带 REL-101 M-2 提前巡检记录）
5. **strict 28tok 宿主侧**：注入面=封闭枚举六面全为插件包内文件——宿主自定义注入增长不构成 FAIL 路径；冻结线=插件仓 CI 纪律；CHANGELOG 已披露，无需新增宿主提示
6. **双根入口/狗粮一致**：canonical 三模板块=0.97.0；root AGENTS.md（tracked）+CLAUDE.md（本地实例）均 0.97.0；三面机器 PASS 闭环
7. **0.96.0 先例对照**：M-0/M-1/M-2 ✓（时序变体非违规；无新 FAIL 面无需 GO 终审）

## C. Findings
- **P0/P1：无**
- **P2-1（M-4 前闭环）**：M-0/M-1/M-2 三行 EVD 未落——→ **已闭环**（EVD-1353/1354/1355 本会话补齐，含 P3-1 精确口径）
- P3-1：M-2 EVD 措辞按实测记——→ **已采纳**（EVD-1353 按「FAILED-3+22 面全 PASS」口径）
- P3-2：30c 精确语义（V7/V8 有日期手写→FAIL；V6d 无日期→WARN 永不 FAIL）——CHANGELOG 措辞已正确
- P3-3：冻结线可选澄清（插件仓纪律非宿主门）——非必须
- P3-4：任务前提小勘正（AGENTS.md tracked；REL-100 在 L204）

## D. M-4~M-8 移交单
**M-4 前置**：①M-3a CODE R0 AWN/0（✓ 已齐）②M-0/M-1/M-2 EVD（✓ 已补）③全量 pytest 收账（✓ EVD-1353）
**M-4 组装**：④三件套落盘（release-checklist A~G 结构/feature-flags N/A 声明件/rollback-plan 十节，区间锚 325289f..M-4 commit）⑤check-release 第三拍复跑（预期 exit 0）⑥两段式组装 commit（m-0 报告一并入库）
**M-5~M-8**：⑦candidate commit（防尾 LF 拦截）⑧ledger candidate→transition→released ⑨annotated tag v0.97.0+统一推送+remote 双 PASS ⑩收口（CHANGELOG taggerdate 回填/L11·L44·L205 终态/REL-101 ✅/归档 dry-run 先行/quality-tools NOT_RUN 诚实记/RECO 完成必推荐）

## E. 全量 pytest 联动失效条款
基于自跑 unit-tests 门 exit 0+EVD-1351 台账；父会话全量=终账——披露集外新失败即失效须 R1 复审。**已满足：EVD-1353 全量 4758P/1S/563st 0F exit 0（2026-10-09 24m13s）**。

> 边界声明（REL-021 保守口径）：不主张 official/marketplace approval、universal runtime support；非 Windows 未验证；dsh upgrade regression=隔离环境安装冒烟（DSH_HOME 重定向临时目录），非 live marketplace 升级证明。
