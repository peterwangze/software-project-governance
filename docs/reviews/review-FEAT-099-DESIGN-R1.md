# REVIEW-FEAT-099-DESIGN-R1 — FEAT-099 设计文档 R1 delta 复审（round 1）

- **被审对象**: `docs/architecture/feat-099-dsh-host-enforcement-poc-design.md`（R1，275 行）
- **快照**: SNAP-FEAT-099-R1-20261027T103640 — sha256 `4cffb298cea8d38c069dc3ab42002823404c0516b9a0ac91486709ff89b96531`（40199B，复审前重算逐位一致）
- **delta 基线**: `docs/reviews/review-FEAT-099-DESIGN-R0.md`（R0 = NEEDS_CHANGE，blockers D1/D2/D3 + P2 D4/D5 + P3 D6/D7/D8）
- **复审人**: Design Reviewer（R0 同实例；delta 口径——修订文本 ↔ R0 条款对照 + 新引入问题扫描）
- **日期**: 2026-10-27 | **round**: R1（DESIGN 面，复审必达 T1）
- **结论**: **APPROVED_WITH_NOTES**（unresolved blockers = 0；3 P1 全部闭环，新引入 3 条 P3 备注）

---

## 1. 快照核验

sha256 复算 = `4cffb298…531`，size 40199B——与派单快照逐位一致。修订后无二次改动。

## 2. D1-D8 逐条对照（不轻信声明，逐处实读）

### D1（P1 blocker）锚协议参数前提 — **闭环** ✅

| R0 修复要求 | R1 落位 | 核验 |
|---|---|---|
| ① §1.4 未证实清单补「guard 可读 arguments」 | §1.4 L63 未证实①：「guard 回调能否读取被调工具的 arguments（prompt）——锚协议的载体前提（README 全文无一处直接陈述 guard 回调签名与参数面；L233 仅证实 pre-execute 事件面持有 exec.arguments…架构推断而非文档证实）」 | ✅ 与 R0 D1 源证据判定逐字对应；§2.1 L90 尾增前提句「不成立则锚协议整体证伪（F1b）」 |
| ② §5.1 增 F1b 证伪分支 | L203：F1 拆 F1a（注册面）/F1b（可达但参数不可读 ⇒ **锚协议证伪**，与 F1a 不同结论），F1b 含三分支降级处置序（①拒绝反馈流重裁→②工具名级判定降级**须重新审查**→③证伪留锚） | ✅ 分支②明确「须重新审查」不自我放行——处置序语义正确 |
| ③ V 步前探明动作 | L165 V0（先于一切 V 步）：探①参数面②治理根定位序③注册原语可达性，「探明结果落盘后才进入 V1-V8」；S4 同步「V0 探明先行，F1b 触发时按 §5.1 分支裁定中止或降级重审」；§5.1「—」行判据同步为「V0-V8 全过」 | ✅ 三处联动一致 |

### D2（P1 blocker）投影单源缺文案模板 — **闭环** ✅

- §3b L128 裁定 **(b) 扩投影**（R0 建议项）：`_strategy_public()` 增列 `hard_block_rules[].{reason, remedy}`（Python 面数据投影小改、判定语义零改动）；明确否决 (a)（第二源无守护）——与 R0 修复要求一致。
- 三处文案同步改「扩展后投影」：§2.1 L90 / §3b L128 / §3c deny 呈现 L151——引用链自洽。
- S1① 落位（L236）+ 三重判据（node 单测 + JS×Python 判定 parity + 投影字节断言 + **enforcement.py 既有测试族零退化**）——末项正确覆盖「投影形状变更可能撞既有形状断言」的风险（若 FEAT-095 测试族有 --print-strategy 形状断言，S1① 判据会红并驱动处理，无静默漂移路径）。

### D3（P1 blocker）C6 带锚语义不自洽 — **闭环** ✅

- C6a（L147）：无锚 + 不可定位 ⇒ allow + 一次性 warn（「能力缺失分级仅在此面成立」）；C6b（L148）：**带锚 + 不可定位 ⇒ deny**（`enforcement-fail-closed`，reason 指名 + remedy=设 `GOVERNANCE_REPO_ROOT` 或修复 workspace 上下文）——与 R0 D3 修复要求（按锚分流）逐字对应，论证援引 C3 同一论证链，「与 C1 仅故障形态差异，处置必须同向」正是 R0 指出的自洽方向。
- V3 第四构造（L168）：带锚派发 + 清空 env 与 workspace 上下文 ⇒ deny（C6b）✅。
- §3b 治理根定位段（L132）同步「按锚状态分流（C6a/C6b）」；§8-5 张力条目标记消解、残留审查点=分流本身——**本复审裁定：分流成立**。

### D4（P2）guard 注册窗口期 — **闭环** ✅

- C0（L141）：已知执法空窗非故障、不经 guard 不判定不记录、如实披露、时长经 V8 观测、「不以概率论证替代判据」（R0 原话吸收）。
- V8（L173）：注册时间戳 + 全部 subagent 调用时间戳持续记录；窗口期内注入带锚错配**如实记录为未被拦截（不粉饰为通过）**；窗口关闭后复跑=拒绝。观测+如实记录而非时序论证——符合 R0 要求。
- §3a-7（DEC 第七要点）+ §5.3 披露行（L225，「窗口期披露与结论正交，两种结论下均须披露」）+ S3 增注册完成时间戳锚——四处联动完整。

### D5（P2）expected 派生源指认 — **闭环** ✅（遗留 1 条 P3 措辞，见 N1）

**行号核验（复审派单明示要求，全部实读）**：

| R1 引用 | 实读结果 |
|---|---|
| task_row_update.py L1827 | ✅ `report["observed_revision"] = revision_of(text)`——行号属实。**粒度偏差见 N1**：实参 `text` = plan-tracker 全文件文本，R1 写「revision_of(task row text)」不准 |
| L1945-1946 | ✅ observed_revision 打印（inspect 输出面） |
| L2200-2201 | ✅ help 原文「Content-level CAS expectation (from --inspect observed_revision)」逐字 |
| L2215-2217 | ✅ --inspect help「observed_revision (the CAS expectation source)」逐字 |
| L2092-2097 | ✅ 不匹配即拒（code=revision_conflict，expected != observed） |

- 机制指认成立：observed_revision 确为现成 content-level CAS 期望源；fixture→生产切换点（投影文件由 fixture 手构造改为 bootstrap 聚合机写，guard 读面接口不变）明确——R0 D5 要求满足。

### D6（P3）节号勘误 — **闭环** ✅（§1.3 L54 改「§6 发现1」+ 勘误括注）

### D7（P3）DEC 窗口期定性 — **闭环** ✅（§3a-7 第七要点，随 D4）

### D8（P3）投影字节断言 — **闭环** ✅（§3b 双重守护② + S1 判据）

## 3. 新引入问题扫描（修订扩写部分）

无新增 P0/P1/P2。三条 P3 备注：

### N1（P3）D5 新文本的 observed_revision 粒度描述不准

- R1 §2.1 L93 写「`observed_revision`（`revision_of(task row text)`…）」——L1827 实读为 `revision_of(text)`，`text` 是 **plan-tracker 全文件内容**（L1820-1826 读 target 文件所得），非单任务行文本。observed_revision = 整文件内容修订号。
- 影响：PoC 验收无影响（fixture 自造 per-task int）；生产化语义需按全文件粒度理解——任何行变更 → revision 前进 → 旧锚 deny（「视图新鲜度」语义，多任务并发互斥性是特性而非缺陷，但后续批裁定时应明说）。勘误一句 + 后续批粒度语义裁定提示即可，不阻断。

### N2（P3）C0 括注措辞反向

- C0 行（L141）reason_code 列括注「—（**窗口期外**无 guard 在场）」——语义主体是窗口期**内** guard 不在场（故无判定无记录）；「窗口期外无 guard 在场」字面说反（窗口期外 guard 恰在场）。C0 行为规格本身正确，仅括注笔误。

### N3（P3）F1b 分支①依赖未证实点

- 分支①「若 deny reason 面可附参数摘要 → 锚改载于拒绝反馈流重裁（后续批）」——其机制前提「宿主在 deny 结果自动附调用参数摘要」未证实（dsh-tools L126 仅「may attach `ToolErrorInfo`」，附件内容形态未述）。分支①已标「后续批」，不构成当前实施误导；重裁时应先验证该点。

### 交叉一致性检查（修订面）

- C6b 与 C1-C3 处置同向 ✅；V0-V8 序贯自洽（V0 先行门禁 + F1b 中止路径）✅；F1a/F1b 拆分与 §5.1「—」行判据同步 ✅；§3a-7 ↔ C0 ↔ §5.3 披露行 ↔ V8 ↔ S3 五处交叉引用一致 ✅；§7 自检表与 §8 前置项更新诚实（新增第 6 项 F1b 审查点）✅；修订记录 L9 与实际落位逐条相符 ✅。

## 4. 结论

**APPROVED_WITH_NOTES — unresolved blockers = 0**

- R0 三 P1（D1/D2/D3）全部真实闭环且语义正确；P2×2 / P3×3 全部落位。
- 新引入三条 P3（N1 粒度措辞 / N2 C0 括注笔误 / N3 分支①未证实点提示）——均备注级，随 S7 披露面更新或后续批顺手处理，不需 round 2。
- 六项审查重点（R0 口径）复核：a 锚协议——前提已标注+证伪分支完备 ✅；b expected 源——派生源核实+切换点明确 ✅；c DEC 草案——七要点完备 ✅；d 单源——扩投影裁定+双重守护 ✅；e C6 分流——成立 ✅；f 通面——修订零回归 ✅。
- **implementation_authorized 可翻转**（R1 通过终态；翻转与 DEC 入账归 Coordinator）。

## 5. 后续建议（非阻断）

1. N1/N2 随 S7 披露面更新批顺手勘误（两处措辞，零结构改动）。
2. 生产化批（fixture→bootstrap 投影）裁定时明示 observed_revision 全文件粒度语义与多任务并发互斥特性。
3. F1b 若触发，分支①重裁前先验证「deny 附件参数摘要」的宿主实际形态。

— R1 delta 复审报告完 —
