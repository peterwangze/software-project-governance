# review-FIX-386-CODE-R1 — 0.87 未承载遗留小项包（代码审查 · R1 复审）

> **Round 声明**：R1（同席复审）。前轮 = `docs/reviews/review-FIX-386-CODE-R0.md`（REVIEW-FIX-386-R0：NEEDS_CHANGE / unresolved_blockers=1，P0=0/P1=1/P2=0/P3=4）。本轮核验范围 = R0 F-1 修复 + F-2/F-5 处置确认 + 回归无新引入。审查方法：修复后 diff 逐行通读 + 前轮 diff 形状对拍 + 三项实测（golden 定向单测复跑、test_triage_write_guard 套件复跑、ADR-011 L453/454 行位抽验）。只读被审代码与 .governance/；唯一输出 = 本报告。

---

## 0. 总结论

**APPROVED**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **0** |
| P3 讨论 | **0**（F-3/F-4 备查项维持备查；F-5 转交付机录义务，见 §3） |

机器可读行：`REVIEW-FIX-386-CODE-R1 | round=R1 | verdict=APPROVED | P0=0 | P1=0 | P2=0 | P3=0 | unresolved_blockers=0 | prev=REVIEW-FIX-386-R0 NEEDS_CHANGE/1`

---

## 1. 前轮 findings 逐条比对（R0 → R1）

| R0 编号 | 级别 | R1 判定 | 依据 |
|---------|------|---------|------|
| F-1 第 6 文件越界修改：必要性申报失实 + pin 值错误 | P1 BLOCKING | **已修复** | §2 逐点核验 |
| F-2 47P 套件映射未定位 | P3 | **已处置（实测证实）** | Developer 补注套件名 = `tests/test_triage_write_guard.py`；本轮实测 47 passed (0.36s)——四套件申报 95P/24P/47P/60P+79subtests 全部对上 |
| F-3 LRC units +1 窗口漂移 | P3 | 备查不变 | 记录性注记，无动作需求；307,337 ≤ 361,923 结论不变 |
| F-4 stash 探针佐证口径 | P3 | 备查不变 | 记录性注记，无动作需求 |
| F-5 风险登记须挂接 RISK-046 | P3 | **处置确认（转交付机录义务）** | 申报口径 = 扩展 RISK-046 缓解列（读写竞态子项：acquire 无锁 TOCTOU 窗口确认 + 串行派发缓解 + 修复候选引 FIX-375 pre-read 先例 04b7a42），不新建独立条目——与 R0 要求逐点一致；risk-log 现文件尚无该内容（grep 实测 0 命中）= 落地为 R1 通过后的交付机录步骤，口径已锁定（§3 义务清单） |
| 新引入 | — | **无** | 工作树仍为 R0 同一 5 文件修改集（git status 对拍）；diff 形状逐字节一致（5 files, +115/−2；test_loop_runtime_claims.py 仍 1+/1−）；新增未跟踪文件仅 R0/R1 两份审查报告本身 |

## 2. F-1 修复核验（P1 → 已修复）

**修复形态**（采纳 R0 方案 (a)，test_loop_runtime_claims.py L951 单行）：

- **pin 值**：`clause:453:3` ✓——与 R0 scanner 实测的段落实际位置一致（旧 446 → 新 453，位移 +7）。
- **注释如实性** ✓——注释三个事实点逐项与 R0 实测吻合：①「shifted +7 lines (6 quote lines + 1 blank)」（6 行引文 + 1 空行，与 hunk 头 −6/+13 互证）；②「Documentation-only sync」（locator 列零消费）；③「this ledger's locator column is NOT consumed by the test assertion (path/state/provenance triple counting)」（消费代码 L1028-1036 两侧均按三元组计数）——并溯源引用 REVIEW-FIX-386-CODE-R0 F-1。
- **失实叙述消除** ✓——「不修则 golden 测试必碎」与「+8」错值已从树内消除；commit message 将按如实口径由 Coordinator 机录（R1 通过后），与修复声明一致。

**回归实测**：

| 项 | 结果 |
|----|------|
| test_former_46_locator_ledger 定向复跑 | **1 passed** (1.01s) |
| ADR-011 行位抽验 | L453 = 被钉段落行、L454 = 空行——与 pin `clause:453:3` 一致 |
| diff 形状 | 与 R0 逐字节一致（+115/−2），修复仅触 L951 一行 |
| 全套件面 | R0 已实测 60P+79subtests+4F（4F 为基线两驱动）；本轮修复不触该文件其余部分，定向复跑足以覆盖回归面 |

## 3. R1 通过后的交付机录义务（非阻塞——随 commit 承载，Coordinator 执行）

1. risk-log：按锁定口径扩展 RISK-046 缓解列（不新建条目），子项内容 = acquire 无锁 TOCTOU 窗口确认（change_triage.py L857-859 裸读 / L942-945 裸写 / 零锁原语）+ 串行派发缓解 + 修复候选引 FIX-375 pre-read 先例（04b7a42）。
2. commit message / 证据记录：不得包含「不修则 golden 测试必碎」类失实理由；第 6 文件如实表述为「文档性同步（locator 列不被测试消费）」。
3. 交付记录补注：47P 对应套件名 `tests/test_triage_write_guard.py`（F-2 处置留痕）。

## 4. 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✓ |
| 5 维度全覆盖 | ✓（R0 §2 五维结论继续有效——本轮修复仅触测试文件一行文档性常量，未触及任何维度结论的事实基础） |
| 每条发现标注级别 | ✓（§1 比对表逐条有判定） |
| 设计一致性检查 | ✓（勘误/账本/测试三面结论 R0 已实测闭合，本轮无相关改动） |
| AI 专项 5 项检查 | ✓（R0 §3 结论继续有效；注释改写不引入 mock/硬编码/幻觉 API/TODO；过度实现项随 F-1 修复消除——保留的 1 行修改现属如实文档性同步且引证溯源） |

## 5. 复审声明

本复审为验证修复的定向复审：逐条比对前轮 findings（5 条全部判定，无跳过）、头部声明 round 号与前轮引用、实测复核修复与回归——未发生「不看前轮直接通过」。复审链终态：APPROVED（unresolved_blockers=0），Check 30 可消费。
