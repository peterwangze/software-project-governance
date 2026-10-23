# REVIEW-FEAT-103-DESIGN-R8 — 设计 R8 最终回写批聚焦复核

- 日期：2026-10-23（Asia/Shanghai）；Design Reviewer（R13 同链新实例，round 15）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**（P0=0 P1=0 P2=0 P3=2）
- 对象：`docs/architecture/dsh-upstream-owned-registration-R1.md` SHA-256 `F0189D1388D4F6D9791A1610095E222AA7861B62C4E934D7B85ED852F372F5AD`（606 行 / 115,805 B）——独立复算一致
- 基线：`DDF7875E…`（591 行 / 109,537 B）= R7 批产物
- delta 依据：`docs/reviews/review-FEAT-103-DESIGN-R7.md`（R13）+ `.codex-sandbox/FEAT-103/design-r8/revision-log.md` + `.codex-sandbox/FEAT-103/M5-REPORT.md`（微批修复闭环版）
- controller 只读核对：`24E3C2F4…`（3429 行）独立复算一致
- 方法：SHA 复算 → 六处落点定位（grep 27 命中）→ 逐项亲读 → controller 短路块/reuseLive 对照阅读 → 零回退锚点 grep（15 命中）→ section 行数账。命令清单见 scratch `reviewer-log.md`。

## 1. 逐项判定

| 项 | 判定 | 事实 |
|---|---|---|
| **R8-1 §5.6 第 7 条 default/list 闭合** | **PASS** | L320："legacy default/list 回归已由 M5-3 闭合（list() 形状/defaultId 优先级/resolve() 落 default/isDefault 标记行为用例 PASS；reg-prefix 同 PASS=与安装态 legacy 原行为一致零回归）"——与 M5-REPORT 事实逐项一致；容量策略"未实现/未测（维持）"如实保留。 |
| **R8-2 §8 T09+ 实现面锚注** | **PASS** | L375 锚注 vs controller 实现（亲读 L464-485）：①位置=claim live 分支 composeAgent（:476）之前 ✓；②四元组条件 `agentPreset !== void 0 && reusable(live.id) && isBlank(live.session) && presetForSession(live.session) === request.agentPreset`（:472）✓；③`assertPresetApplicable → return live`（:473-474）✓；④缺省不短路（`!== void 0` 前置，缺省走 :476 原路径）✓；⑤同构性：与 reuseLive（:521-527 `reusable+isBlank+assertPresetApplicable+target===current→return live`）唯一行为差别=短路块跳过 resolve（composeAgent 内含 resolve）——锚注"完全同构、唯一差别=跳过 resolve"亲读成立，且 :467-471 注释明示设计依据（§5.3 #2 / §5.6 _forget 分类 / D2 committed retention / 缺省边界）✓。**合同句本身（复用成功 D2 保留 P=0 等）零改动=零合同变更** ✓。 |
| **R8-3 §11 回写** | **PASS** | L426 `implementation_progress=M1…M5 done` 全链事实与 M5-REPORT 一致（归因→裁定 b 方向 1→controller B9999EE6→24E3C2F4〔+9/−0〕→t-m5 3/3 同一断言 FAIL→PASS 未弱化→六族+T01 全绿→ctrl-prefix 铁证）；L425 authorized 行 M5 面授权依据表述（"T09+ 为本设计 §8 已批合同，修复=实现既定合同非扩权"）准确；L410 硬门槛 R8 注 + **CODE R6 在途不预写**（L410/L426/L595 三处一致）✓；L417 design_revision=R8 消歧注（设计版本号 ↔ 审查报告文件编号独立）延续 ✓。 |
| **R8-4 §16 清单收敛 + 文首同步** | **PASS** | L582 头注：两条（T09+ C-1 / T11+ default·list）移出+闭环去向 §17 ✓；剩余 5 条（L583-587：真实 host publish 链/物理 storage 注入/startActivation 全链/T10 census 全量/0.1.x）与 M5-REPORT §5 及执行包 next_commands 口径一致 ✓；文首 L1 标题含 R8、L3 日期含 R8 ✓。 |
| **零回退独立复验** | **PASS 8/8** | N-R4-1 错误码映射段 L286（REGISTRATION_CLOSED/agent-preset/closed 语义等价+禁无解释混用）原样；N-R4-2 `_forget` 措辞 L198 原样；N-R4-3 §9 容量行 L390 原样；N-R4-5 fallback 用例段 L284（不得静默取 G2）原样；R5 裁定段 L229-232 + 记法 L422 原样；R6 衔接半句 L300 + 修辞 L232（附 R6 措辞替换注记）原样；§3.5 证伪出口与 §12-§16 历史修订表格（L541/L548/L560-561 等）零改写。Architect 自检 8/8 与本复验一致。 |
| **在途句清除** | **PASS** | 当前状态声明面（§5.6 L320 / §11 L426）"在途"零残留（均已闭合）；"在途"仅存于历史引文（L5 文首历史描述、§15/§16 修订记录 L572/L577/L579）= audit trail 正确保留，不应清除。 |
| **section 回归** | **PASS** | 591→606 = **+15 行全部来自 §17 新节**（L591-606，含标题/空行）；行内改写落点（L1/L3/L5/L320/L375/L410/L417/L425/L426/L582）全部在 R8 声明面内；无未声明区段变更。 |

## 2. 新偏差（P3×2，不阻断）

**R8-P3-1 — 文首 L5 性质段首句枚举漏 R8**
L5 开头"**R2 修订版 + R3/R4/R5/R6/R7 增量**"——标题 L1 已含 R8、R8 描述在 L5 段中后部（"**R8**=M5 后最终回写批…"），但首句枚举未更新至 R8。文首一致性（N-R4-6 口径）小瑕疵；建议合入前终笔时顺带补 R8 入首句枚举。

**R8-P3-2 — §17 无"待复审声明"句**
R7 批 §16 有"待复审声明"（L589，对象=四项+清单表达）先例；§17 未成文对应声明（本报告即按 §17 四项+§16 收敛执行，对象可从 §17 表格推出）。轻微：建议后续终笔批补一句或在 §16 待复审声明中加 R8 接续注。

## 3. 结论

R8 批四项（§5.6 闭合 / §8 T09+ 锚注 / §11 M5 done / §16 收敛+版本号）全部落地且与 M5 实施事实逐项一致；唯一合同关联改动（R8-2）经 controller 亲读对照确认为"记录已批合同的实现面"，零合同语义变更；R4-P2/R5/R6/R7 已批面零回退（独立复验 8/8）。设计文档现如实反映 M1~M5 全部实施事实与终态 NOT_RUN 清单（5 条，随 0.99 发布链承载）。2×P3 为文本精度项，不阻断合入判定。

**APPROVED_WITH_NOTES / unresolved_blockers=0。**

## 4. 边界合规

- 只写本报告 + scratch（.codex-sandbox/FEAT-103/review-design-r8/reviewer-log.md）
- 未改设计/代码/测试/副本/治理记录；未 stage/commit/push；SDK 只读核对（Get-FileHash/Read/grep，无运行）
- 通信异常披露：无（未收到其他 agent 转包/委派消息）

## 5. 机录建议

`review-record --task FEAT-103 --round 15 --result APPROVED_WITH_NOTES --report docs/reviews/review-FEAT-103-DESIGN-R8.md --reviewer "Design Reviewer (R13-chain new instance, R8 final write-back focused)" --scope delta --delta-base docs/reviews/review-FEAT-103-DESIGN-R7.md`
