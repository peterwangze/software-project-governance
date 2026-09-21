# FEAT-059 — 0.87.0 M-1 发布半面审查报告（RELEASE R0）

> **Reviewer**: Release Reviewer Agent（串行单席） · **Round**: R0 · **日期**: 2026-09-21
> **依据**: `agents/release-reviewer.md` + `skills/release-review/SKILL.md`（已全文加载）
> **治理态**: Governance: always-on x maximum-autonomy | stage: 维护与演进（G11 passed）· REL-084 M-1（FEAT-059 review 中）· 4 risks
> **工具边界声明**: 本席 Read/Grep/Glob only（Bash/Agent/AskUserQuestion 禁用）。四项 check（version-consistency / projection-sync / injection-contract / manifest）与 `release-projection --write` 均未由本席独立复跑——按任务口径采信 Developer 声明 + Coordinator 终验；所有「声明依赖」项已在 §7 未验证清单逐条列明，本席不将其写成「已验证通过」。

---

## 0. 结论速览

**APPROVED_WITH_NOTES（unresolved_blockers=0）——M-1 GO**：准予进入 M-1R 四件套（release-plan / rollback-plan / release-checklist / feature-flags）+ M-2 门禁实测 + M-3 双半面审查。**预授权不免除门禁（DEC-226 沿用 DEC-197 语义）**。Findings：P0=0 / P1=0 / P2=0 / P3=5（§5，全部非阻塞留痕）。

---

## 1. 审查对象与方法

- 对象：工作树未提交修改 24 tracked 面（0.86.0→0.87.0 bump 候选态）——SKILL frontmatter 权威锚、verify_workflow.py REQUIRED_SNIPPETS、checks/version.py STATIC_PIN_EXEMPTIONS、CHANGELOG 0.87.0 段、投影再生面。
- 复验时间盒：**14 次调用恰好用满**（批 1 版本残留/治理 ID 扫描 ×4 + 批 2 权威锚/引擎锚/账本/adapters ×5 + 批 3 隐藏目录 plugin/marketplace 五面 ×5）。
- 事实源：plan-tracker 热行、evidence-log（EVD-1122~1128）、decision-log（DEC-226~228）、ops 台账（plan-tracker.md.ops.jsonl）、change-triage 机录、仓库文件逐位 grep/read。
- 方法限制：ripgrep 默认跳过隐藏目录——首轮 JSON 扫描未覆盖 `.claude-plugin` 等 dot-dir，已用显式路径补扫（这解释了为何 plugin/marketplace 面必须显式验证；已在批 3 完成）。

## 2. Developer 验证声明复验

| # | 声明 | 本席复验方式 | 结果 |
|---|------|-------------|------|
| V1 | 投影一次收敛：`--write` → state PASS / written 17 / issues [] 零回滚 + 二次 check-only 幂等 PASS 28 面 | **声明依赖**（无 Bash）+ 引擎面佐证：FIX-366 两遍 plan 已落地（EVD-1125 R1 APPROVED/0，含 CRLF 护栏双断言 4 测试）；若旧单遍 plan 缺陷仍在，本次 bump 必现回滚震荡——与「零回滚」声明不相容 | 一致，采信（Coordinator 终验命令输出） |
| V2 | version-consistency 唯一 WARN=plan-tracker 过渡态 | **直接实证**：plan-tracker L11 `工作流版本: 0.86.0`（发布收口时由 Coordinator 更新——设计内过渡态） | ✅ 与声明精确吻合 |
| V3 | projection-sync（28+双根）/ injection-contract（3/23）/ manifest（841）PASSED | 声明依赖 + 投影面逐位抽验（§3 D2，10 类面 0.87.0 在位、0 stale） | 一致，采信 |
| V4 | FIX-361 双信号：test_release_projection.py:30（FUTURE_TARGET）+ test_verify_workflow.py:12375（FIXTURE_ROW_TEXT）归因登记后 scan 空 | **账本逐位实证**：STATIC_PIN_EXEMPTIONS 0.87.0 组恰好 2 行且 reason 归因一致；test_release_projection.py L29 `OLD_VERSION="0.86.0"` 交叉印证（NEW_VERSION=L30 即 then-future target，bump 时等于 active 恰触发一次、随后 dormant）；存量 0.86.0 字面量均为非 active 版本 payload（scan 只捕 active 版本，无需账本行） | ✅ 完全吻合，scan 空可信 |

## 3. 五维度审查

### D1 版本面逐位 ✅

- **权威锚**：`skills/software-project-governance/SKILL.md` frontmatter `version: 0.87.0`（L3）✅
- **引擎锚**：`verify_workflow.py` REQUIRED_SNIPPETS（L749 起）六个版本锚 L1057/1060/1063/1066/1069/1072 全部 `"0.87.0"` ✅（「手工钉」为设计内流程，非绕开）
- **plugin/marketplace 五面**（隐藏目录显式补扫）：`.claude-plugin/plugin.json` L3 / `.claude-plugin/marketplace.json` L12 / `.zcode-plugin/plugin.json` L3 / `.codex-plugin/plugin.json` L3 / `.chrys-plugin/plugin.json` L3 —— 全部 `"version": "0.87.0"`，六文件（含 `.agents/plugins/marketplace.json`）**零 0.86.0 残留** ✅（「5 plugin/marketplace」计数实证自洽：4 plugin.json + 1 marketplace.json；`.agents/` 不携带版本字面量，非版本面成员——F-5 留档）
- **JSON 声明面**：`package.json` L4 / `core/manifest.json` L4 = 0.87.0 ✅
- **静态钉豁免账本**（checks/version.py L205-283）：0.86.0 期 21 行（11+7+3 形态）dormant 在账、零删除；0.85.0 期行（fixture/instrument/FUTURE_TARGET/-guard）完整保留；**0.87.0 新增恰 2 行**且逐行归因（F-1 双信号）——账本纪律良好，无滥用豁免迹象 ✅
- **0.86.0 残留全扫**：JSON 面命中 9 处均为合法历史归属（m0 fixtures provenance 引用 version-plan-0.86.0、benchmarks 案例引用、`core/releases/0.86.0.json` 发布账本本体——必须保持 0.86.0）；.py 面命中 80 处均为 docstring/注释归属、fixture payload（非 active 版本）、账本行——**active 版本钉残留 = 0 stale** ✅

### D2 投影面 ✅（spot check 10 类 ≥ 要求的 5）

SKILL frontmatter / package.json / core/manifest.json / 5 个 plugin·marketplace 面 / adapters/dsh/AGENTS.md.template（`@bootstrap-version: 0.87.0` L3）/ REQUIRED_SNIPPETS 六锚 / repo-root 双入口 AGENTS.md+CLAUDE.md（本会话注入文本实测 0.87.0）。未在席内验证：4 hooks `@version`、DSH persona 版本行、e2e-fixture 双根——见 §7（依赖 V1/V3 声明 + projection-sync PASS 28 面）。

### D3 发布材料——CHANGELOG 0.87.0 段事实核对 ✅（逐条 vs 事实源）

| CHANGELOG 主张 | 事实源核验 | 判定 |
|---|---|---|
| 九票交付（FIX-367/368/364/369/REL-084/FIX-366/372/370/371） | plan-tracker 热行 L87-95/86 全部在案；EVD-1122~1128 七票审查链机录在案（op-371b0ab1/op-0f5b7a29/op-3be7c77e/op-192ad3b2/op-ce9612dd/op-832074b6/op-104cc2ef） | ✅ |
| EVD-1122~1128 引用 | evidence-log L2460/2463/2464/2469/2474/2479/2486 逐条内容与 CHANGELOG 叙述一致（含审查结论、测试数、机录 op） | ✅ |
| DEC-226/227/228 | decision-log L168-170 机录在案：DEC-226 预授权原文「我授权Coordinator 按照推荐进行推进，直到最新规划版本发布」逐字吻合；DEC-227 路线 a/c 被否理由（补录=编造违反 P1 / M-2 仍红）吻合；DEC-228 三消费方+Check 18 静默承认吻合 | ✅ |
| B-9（361,923） | 361,923 = ceil(301,602×1.2) = ceil(361,922.4) 算术 ✅；EVD-1123「PASS/301,849 直验」在案；「重定标非豁免」与 provenance/反豁免双测试叙述一致 | ✅（测点数值发散见 F-3） |
| B-10 / B-11 | EVD-1127（先登记后删除/三态/96 键重定基线/op-7c866828 活体）/ EVD-1128（R0 NEEDS_CHANGE F-1→R1 APPROVED/0、31→5 FAIL、26=8+18 对账）在案 | ✅ |
| 披露① REQ-092 blocked 3 FAIL 维持 | ops 台账 L14「REQ-092 🚧 blocked 保持 FAIL（零豁免红线活体实证）」；REL-084 行「Check 16 FAIL 5→3」；FIX-200/FEAT-001 勘正行 L112-113（5→3 消解路径）在案 | ✅ |
| 披露② EVD-248 切分器泄漏显形 | EVD-1126 内载「EVD-248 显形→FIX-373 出槽 0.88」 | ✅ |
| 披露③ FIX-373~376 出槽 | plan-tracker L96-97 行 + change-triage 机录文件（FIX-373/374/375/376.json）全在 | ✅ |
| 披露④ CRLF 保真（read_bytes().decode + 护栏双断言） | EVD-1125 在案 | ✅ |
| 披露⑤⑥⑦ token 面不变/不发布清单/no-overclaim 边界 | 与 0.85.0/0.86.0 同措辞纪律一致；injection-contract 3/23 为声明依赖（§7） | ✅ |
| MINOR 依据 | locks-release 新子命令（新增受治理能力面→VERSIONING L12）+ 豁免账本 + Check 31 重定标 + 七票收口；无 breaking（L11 处置段在段内显式论证，B-9 引 0.85.0 判定姿态先例同型）；版本顺延 0.86.0→0.87.0 无预留冲突（REL-084 Release R0 代验，tag 面声明依赖） | ✅ |
| Commit 区间 8 行（5e56021…a6d3bfb） | **本席无 git，未验证**——列入 §7，Coordinator 终验 `git log --oneline` | ⚠️ 声明依赖 |

### D4 回滚就绪 ✅（M-1 半面口径）

B-9 回退通道（还原预算值+基线注销，数据级双向自洽）/ B-10（误删补偿=acquire 幂等重取，不可逆面=零）/ B-11（账本可增删可回滚——DEC-226 非-T2 裁定）均已在 CHANGELOG 载明。版本级回滚主轨沿用 0.86.0 先例（rollback-plan-0.86.0 §8 → 0.87 版随 M-1R 四件套交付——**GO 的组成部分，非本席豁免项**）。

### D5 披露完整 ✅

七条如实披露全部有事实源支撑（见 D3 表）；行为变更 B-9~B-11 均含用户可感知面 + 回退通道；Breaking=无 的 L11 论证在段内完整呈现。

## 4. 绕开撤除合规专节 ✅

| 比较项 | FEAT-053/058 手法（绕开） | 本版 M-1（正道实证） |
|---|---|---|
| 顺序 | canonical 标记**先**达目标值 → transformed 幂等 → `--write` 再生 byte_copy（掩盖单遍 plan 缺陷） | canonical 先 bump → 单次 `release-projection --write` 一次收敛（V1：PASS / written 17 / issues [] / 二次幂等 28 PASS） |
| 引擎根因 | 未修（FEAT-053 P2-1 挂账 0.87） | FIX-366 两遍 plan 落地，EVD-1125 R1 APPROVED/0 + 重叠红态回归 + CRLF 护栏 |
| 豁免面 | 无账本滥用先例 | 0.87.0 账本仅 +2 行且为 FIX-361 设计内双信号，逐行归因、dormant 可审计 |
| 残留 | — | active 面 0 stale（D1 全扫）；「手工钉 REQUIRED_SNIPPETS」为披露的设计流程，非隐藏绕开 |

**结论**：「一次收敛零回滚」声明与引擎修复事实、账本纪律、残留扫描三方互证，无绕开手法残留证据。

## 5. Findings（P0=0 / P1=0 / P2=0 / P3=5）

- **F-1 (P3)** CHANGELOG 版本投影段标题「28 面」与括号枚举算术 30（5+1+1+4+1+1+3+2+12）不一致——同段措辞逐字承袭 0.85.0/0.86.0（同 28+同枚举），非本版引入；权威计数以 registry/projection-sync（28 PASS）为准。建议后续勘误票改非穷举措辞或对齐枚举。
- **F-2 (P3)** plan-tracker FIX-366 任务行 narrative「R1 复审待补测」落后于 EVD-1125（R1 APPROVED/0 + 4 测试落库）——证据链权威面一致，任务行待 M-1 收口 writeback。
- **F-3 (P3)** LRC 容量各记录测点数值不一（triage 300,913 / DEC-226 300,701 / 公式基线 301,602 / 改后直验 301,849）——不同时点实测，公式基线与 EVD-1123 一致；建议 M-2 呈现时标注测点时点。
- **F-4 (P3)** 本席无 Bash——§7 未验证清单全部依赖 Developer 声明 + Coordinator 终验（流程设计内，非缺陷）。
- **F-5 (P3)** `.agents/plugins/marketplace.json` 不携带版本字面量（非 28 面成员）——留档免后续席位重复考古。

## 6. 裁决

**APPROVED_WITH_NOTES · unresolved_blockers=0 · M-1 GO。**

下一单元（按 DEC-226 标准链）：M-1R 四件套（release-plan / rollback-plan / release-checklist / feature-flags）→ M-2 门禁实测（**含 Check 31 重定标后口径**、唯一预期 WARN=tracker 过渡态）→ M-3 双半面审查 → M-5~M-8。F-1/F-2/F-3 为非阻塞留痕，建议分别挂 M-3 材料核对与收口 writeback。

## 7. 未验证清单（诚实声明——未写成通过）

1. `release-projection --write` / check-only 幂等 / 四项 check 自跑输出（V1/V3 声明依赖）。
2. 4 hooks `@version`、DSH persona 版本行、e2e-fixture 双根的逐位在席验证（projection-sync PASS 28 面覆盖面内）。
3. 8 个 commit short-hash 与 git log 的对照；tag/预留冲突（REL-084 R0 代验声明依赖）。
4. 三 profile 注入 token 逐位复测（披露⑤，injection-contract 3/23 声明依赖）。
5. `python verify_workflow.py` 全量门禁（M-2 实测承载）。
