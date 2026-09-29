# FEAT-078 代码审查报告 — R0

- **任务**: FEAT-078（M1-B1a 契约注入文本面——DEC-290(4)/DEC-291）
- **Reviewer**: Code Reviewer（独立复审，R0 首轮）
- **日期**: 2026-09-29
- **审查对象**: 6 内容文件 + 5 投影镜像 + 1 测试扩展（git footprint 实查：`git status` 14 M + 1 gitignored 重生成）
- **锚定依据**: ADR-021 §2.1（L60/L62/L64/L68/L75）/§3.1（L292/L296/L300）、DEC-290(4)、DEC-291（预算实测口径：M1≤180 / M1+M2≤370，冻结文本为权威基线）
- **范围排除**（遵守）: FEAT-079 在途文件（verify_workflow.py / test_verify_workflow.py / injection_budget.py 的 B1b 变更本体）未评审未触碰——仅只读锚点注册表区域并复跑四个限定检查；untracked ADR/DESIGN-021 报告只读参考。

---

## 1. 结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`；findings：P0×0 / P1×0 / P2×1 / P3×2）

六面注入逐字零漂移独立复验成立；两项偏差裁定均复核为正确；预算分账真实且口径一致；投影纯机械；既有内容零破坏；测试质量合格。无阻塞项。

## 2. 零漂移核验结果（Reviewer 独立比对）

**方法**：① 逐文件读 diff 与 ADR L64/L68/L296/L300 人工比对；② 独立复跑 `.governance/tmp/feat078-zerodrift.py`（脚本从 ADR 运行时提取冻结文本——非内置常量，比对对象即 ADR 原文本身）。

**结果**：`ZERO-DRIFT: PASSED — 17/17`（Reviewer 会话内独立复跑，exit 0）：

| 面 | 检查 | 形态 | 结果 |
|----|------|------|------|
| behavior-protocol.md | M1/M2 canonical 全文 | 逐字（含 5./6. 序数+加粗） | OK |
| SKILL.md | M1/M2 压缩第 5/6 项 | 逐字（含序数+加粗） | OK |
| persona 契约块 | M1/M2 压缩体 | bullet 变换体（见 §3.0 裁定） | OK |
| persona 附加锚 | 「用户点名」（B1b 注册表 persona 专属锚） | 关键词 | OK |
| governance-init 三 profile | lightweight/standard/strict × M1/M2 | 逐字压缩行（经 `extract_canonical_templates` 提取断言） | OK×6 |
| secondary-thin + AGENTS.md.template | 双关键词指针 | 关键词 | OK×4 |

**persona 变换合法性裁定（验收①重点）**：**合法**。依据：ADR L60 明文「以锚点关键词为锚，**不用序数**——persona 契约块现为五行…双面序数天然漂移」+ L292「序数仅描述」——序数在 ADR 冻结行中是**描述位置的文字**而非契约正文；persona 块既有五行格式实证为 `- 关键词：正文` bullet（无序数无加粗，L58-62），新两行与该格式一致，冒号后正文逐字保留。且期望体由脚本**程序化从 ADR 串派生**（`re.sub` 去 `N. ` + 去两处 `**`），非手抄——转写错误向量被消除。测试侧（test_dsh_adapter.py）同形态断言 `- ` 前缀整行，双重钉住。

## 3. 两项偏差裁定复核（验收⑥）

### 3.1 ADR L62 vs L75 矛盾 → Developer 按 L75 表格执行（SKILL.md=压缩）

**Reviewer 独立裁定：正确。** 论据：
1. **具体优先于笼统**：L62 是节标题行（「逐字文本建议（canonical，behavior-protocol.md 与 SKILL.md 携带）」——描述模糊），L70-79「涉及文件」表对 SKILL.md 行明确写「关键行为契约节第 5 条（**压缩**）」——逐文件落点清单是更具体的规定。
2. **与 ADR 自身自洽**：L60 已声明「本条在 SKILL.md 面为第 5 项」并列出承载分工；若 SKILL.md 放 canonical 全文则 L68「压缩形式（persona / **入口模板**携带）」的分工描述反而矛盾。
3. **与既有架构一致（F1 事实基线）**：SKILL.md「关键行为契约」节既有形态即压缩投影层（「本段是注入面的 canonical 投影定义处（DSH persona 携带其压缩形式）」），canonical 全文层在 behavior-protocol.md——既有四条即此分层，第 5/6 条沿用不引入架构漂移（P-v1 D2/D3）。
4. **canonical 不丢失**：全文由 behavior-protocol.md M7.4 末尾 blockquote 承载（17/17 核验面 1），SKILL.md 节首「完整规则见 references/behavior-protocol.md M7.4 / M7.7」既有指针继续有效。
5. **流程正当**：偏差已声明列入交付报告供 ADR R1 后续确认，非静默选择。

残留：L62 表头措辞与表格的矛盾是 ADR 文档缺陷本身 → F-3（P3）。

### 3.2 任务书「28 锚点基线」→ 实测 30 勘正

**Reviewer 独立裁定：正确。** Reviewer 直读 `INJECTION_CONTRACT_ANCHORS`（verify_workflow.py L6805-6845，只读）独立计数：persona 15（含 VERSION_LINE_ANCHOR）+ SKILL.md 11 + behavior-protocol.md 3 + AGENTS.md.template 1 = **30**。任务书 28 为笔误；Developer 以实测注册表为基线并在 notes 偏差 3 如实披露（不隐藏异常）——勘正成立。复跑 check-injection-contract 输出「anchors: 30」佐证。

## 4. 定向复跑证据（Reviewer 会话内，TEMP 重定向 check-run-20260929，重试 0/2）

| # | 检查 | 结果 | 关键数据 |
|---|------|------|---------|
| 1 | check-injection-contract | **PASS**（exit 0） | 4 files / 30 anchors；staged ADR-021-B1a: **active, 9 anchors guarded**（FEAT-078 文本满足 FEAT-079 staged 9 锚——30+9 兼容证实，验收②） |
| 2 | check-injection-budget（三 profile，经 feat078-budget-delta.py 复验） | **PASS**×3 | strict resident **5609→5957**（余量 **43**>0 硬门）；**实测增量 348 = persona +141 / entry +171 / thin +23 / agents +13**（加总精确一致，验收③口径一致）；348≤370（DEC-291 分档）；standard 5685 / lightweight 4207；共享面（persona/thin/agents）三 profile delta 一致（141/23/13）——投影共享设计正确 |
| 3 | check-entry-bootstrap-sync | **PASS**（exit 0） | repo-root + e2e：CLAUDE.md 10086B/full + AGENTS.md 2815B/thin 同步 |
| 4 | check-projection-sync | **PASS**（exit 0） | 同上（含 dsh-dialect 相互识别 3444B/37L） |
| 5 | feat078-zerodrift.py 复跑 | **PASSED 17/17**（exit 0） | 见 §2 |
| 6 | pytest test_dsh_adapter.py -k "InjectionContract or injection_contract" | **3 passed + 3 subtests**（exit 0） | 三 profile subTest 全绿 |

（未复跑项：89 相邻测试全套——任务禁全量，以定向 3+3 与四个检查的交叉证据为充分；TDD RED 阶段不可逆现——采信 Developer 声明 + GREEN 态已复验。）

**投影机械性独立验证（验收④）**：SHA256 比对 `e2e SKILL.md ≡ 主 SKILL.md`、`e2e governance-init.md ≡ 主 governance-init.md`（IDENTICAL）；repo-root 与 e2e AGENTS.md thin 指针行逐字相同；repo-root CLAUDE.md（`.gitignore:3` 忽略——本地生成入口设计如此，非本次引入）经 grep 确认含第 5/6 条压缩行；双 sync 检查机器确认。**无手改夹带证据。**

**既有内容零破坏（验收⑤）**：全部 diff 为纯增量 + 3 处行内原位扩展（SKILL.md「以下四条」→「以下六条」/ behavior-protocol.md 最小契约投影句追加第 5/6 条义务句 / AGENTS.md.template 契约名清单行扩展），无既有行删除（被替换行本身除外）；30 既有锚点全 PASS。

## 5. 五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | **通过** | 零漂移 17/17；注入位置正确（canonical 在 M7.4 末/M7.5 前，SKILL 第 4 项后，persona 第 5 行后，init 三处）；投影 hash 等价 |
| 安全性 | **通过** | 纯文本面变更，无代码执行面/敏感数据；fail-closed 锚点守护语义未被削弱（staged 9 锚激活全断言）；FEAT-079 文件零触碰 |
| 可维护性 | **通过** | 压缩/canonical 分层与既有四条一致；thin 指针两条款合并一行（比 ADR 双行估算更省）；测试 docstring 含 ADR 锚与 BC-1 语义 |
| 性能 | **通过** | resident 增量 348 tok 实测受控（DEC-291 370 上界）；余量 43 偏紧但 DEC-291(4) 已裁定「B3 后新增注入面前 MUST 重跑 budget」防护 |
| 测试覆盖 | **通过** | 新测试覆盖 6 面全部 + 三 profile + 逐字钉 + 引言计数钉（「以下六条」）；关键词制与逐字钉分层正确（指针面用关键词、文本面用逐字） |

**AI 专项 5 项**：mock 残留=无 ✓；硬编码返回值=无（测试内冻结文本常量是「逐字钉」有意设计，pin 语义非伪造）✓；幻觉 API=无（复用既有 `extract_canonical_templates`）✓；未实现 TODO=无 ✓；过度实现=无（AGENTS.template 行内扩展较 ADR「短指针行」更省，方向正确且已声明）✓。

## 6. Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-1 | **P2** | `.governance/tmp/feat078-zerodrift.py` | ADR↔面「运行时提取比对」核验目前只存在于 `.governance/tmp/`（临时区，不入版本库、可被清理）；test_dsh_adapter.py 的逐字钉覆盖「文本 vs 冻结基线」，但「冻结基线 vs ADR 原文」的活链接仅此脚本提供——ADR 措辞若变，测试与 ADR 可能同时漂移而不被发现 | 后续批（建议 FEAT-079 收尾或独立小票）将 zerodrift 逻辑收编为 `infra/tests/` 持久测试（ADR 存在时运行、缺失时 SKIP+披露） |
| F-2 | P3 | ADR-021 L62 | 表头「canonical，behavior-protocol.md 与 SKILL.md 携带」与 L75 表格「SKILL.md（压缩）」矛盾——ADR 文档缺陷（Developer 已按表格正确执行，见 §3.1） | ADR 下次编辑机会（如 R1 后修订）将 L62 改为「behavior-protocol.md 携带（SKILL.md 携带压缩形式）」消歧 |
| F-3 | P3 | repo-root `CLAUDE.md`（.gitignore:3） | 主入口投影不被 git 追踪——克隆环境需 governance-init 重生成才获得第 5/6 条（既有 FEAT-037 设计取舍，非本次引入；当前实例已同步经 sync 检查机器确认） | 无需行动；维持现状（记录认知即可） |

## 7. 硬门槛裁决

| 门槛 | 阈值 | 实测 | 判定 |
|------|------|------|------|
| P0 阻塞数 | =0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5（§5） | ✅ |
| 每条发现标注级别 | 100% | 3/3（P2×1/P3×2） | ✅ |
| 设计一致性（vs ADR/DEC） | 已完成 | §3 两项偏差独立复核 + DEC-291 口径复验 | ✅ |
| AI 专项 5 项 | 全部完成 | §5 末段 | ✅ |

**终态**：APPROVED_WITH_NOTES（unresolved_blockers=0）——F-1（P2）建议后续收编不阻塞本批；Developer 六项声明全部经独立复验证实（声明①=§2/17-17 复跑、②=§4#1、③=§4#2、④=§4#3-4、⑤=采信+GREEN 复验、⑥=§4#6 定向）。

---
*Reviewer: Code Reviewer Agent（R0）· 复跑环境：TEMP 重定向 `.governance/tmp/check-run-20260929` · 重试 0/2 · 报告路径：docs/reviews/review-FEAT-078-CODE-R0.md*
