# Review FIX-394 — CODE R1（复审：R0 P1 F-1 修复核验）

- **Task**: FIX-394（0.89.0 批次一第二票）｜ **优先级**: P2
- **Round**: **R1**（复审轮——前轮引用：`docs/reviews/review-FIX-394-CODE-R0.md`，R0 结论 APPROVED_WITH_NOTES，P0=0/P1=1/P2=2/P3=5；触发器 T1：R0 NEEDS_CHANGE 级 P1 修复后同一 Reviewer 复审）
- **复审对象**: staged diff（`git diff --cached`，2 文件，**+1414/−12**，HEAD=8a94d64 未动；R0 为 +1368/−12 → R1 增量 **+46 行**）
  - `task_row_update.py`：唯一产品码增量 = execute_refresh 锚计数门块（现 L1508-1527，+20 行）
  - `test_fix394_progress_suffix_refresh.py`：新增 `test_double_anchor_row_is_refused_on_both_paths_identically`（L399-423，+26 行；28→29 用例）
- **复审方式**: 修复面逐行读 + R0 全部锚点行号位移比对（证明修复面之外零触碰）+ R1 构造探针 9 项（F-1 复现输入双面一致性 + 次序重排无新分叉 + 范围外发现行为抽查）+ 定向回归亲跑
- **复审结论**: **APPROVED**（`unresolved_blockers=0`；遗留 P2×2/P3×5 为 R0 已登记跟踪项，非本轮发现）
- **发现计数**: 新发现 P0=0 / P1=0 / P2=0 / P3=0；R0 遗留 P2=2 / P3=5（维持）

---

## 1. R0 findings 逐条比对（复审本质=验证修复）

| R0 发现 | 级别 | R1 状态 | 核验依据 |
|---------|------|---------|----------|
| F-1 execute_refresh 多锚 fail-closed 被 no-op 短路+dry-run/execute 语义分叉 | P1 | **已修复 ✅** | ①锚计数门（0→无锚拒绝/≥2→ambiguous 拒绝，均 schema_violation）前置到 stale 检测（L1528）与 no-op 短路（L1530）之前，位于 detect/cell 提取（L1487-1507）之后、replay/CAS（L1440s-1480）之后——与 `_dry_run_refresh` 检查次序对齐（锚 L1993 先于 stale L1999+），且不侵扰重放语义（重放判定仍在门之前，同 id 重试先命中 replay 返回）；②拒绝措辞/分类与 dry-run 同款（`ambiguous — {n} ops anchors on one status cell` 前缀逐字一致，分类均 schema_violation）；③门块注释显式引用 R0 报告（L1508-1513）；④新钉住测试以 R0 原始复现输入（双锚+无滞留词，用 taboo 词「已交付」构造 no-op 类输入）断言双路径一致+零写入+零 receipt |
| F-2 翻转路径 end-anchored 剥离可制造双锚行 | P2 | **未触碰（保持登记）✅** | L659 剥离语句行号未变；行为抽查：review→committed 翻转锚后括号行仍产出双 op 锚（与 R0 一致——既不恶化也不修复，符合「范围外」声明） |
| F-3 词表前瞻只认 ASCII 空格——全角紧贴形态误判 aligned | P2 | **未触碰（保持登记）✅** | L249-253 正则逐字节未变；行为抽查：全角紧贴形态 `find_stale` 仍返回空 |
| F-4 receipt 双真源 | P3 | 未触碰（保持登记） | `refresh_candidate_row` L1324 `_removed` 丢弃依旧 |
| F-5 dry-run 异常分类粗于 execute 面 | P3 | 未触碰（保持登记） | `_dry_run_refresh` 仅整体位移 +20 行，内容未变（L1993 锚计数行号位移吻合） |
| F-6 申报计数精度 | P3 | 未触碰（记录级） | — |
| F-7 测试 fixture 注释 9≠10 | P3 | 未触碰（记录级） | — |
| F-8 「进行中」词形 alignment 不可达 | P3 | 未触碰（记录级） | — |
| **新引入** | — | **无** | 增量仅锚门块+新测试（§2 行号位移全表）；锚门块本身无新问题（早退走 `_validation_result` 保持 frozen WriterResult law；`find_stale` 内部重复搜锚为零害冗余） |

## 2. 修复面之外零触碰证明（R0→R1 锚点行号位移全表）

| R0 锚点 | R0 行号 | R1 行号 | 位移 | 结论 |
|---------|---------|---------|------|------|
| `STATUS_CELL_OP_SUFFIX_PATTERN.sub`（F-2 区） | L659 | L659 | 0 | 未触碰 |
| `_STALE_PHRASE_RES`（F-3 区） | L249 | L249 | 0 | 未触碰 |
| `canonical_input_fingerprint`/`action` 参（契约区） | L341/L350 | L341/L350 | 0 | 翻转 fingerprint 契约未触碰 ✅ |
| `build_candidate_row` refresh 调用 | L639 | L639 | 0 | 未触碰 |
| `refresh_candidate_row` 多锚消息（纵深防御层） | L1301 | L1301 | 0 | 保留（与前置门构成双保险） |
| execute no-op detail | L1515 | L1535 | +20 | 仅位移 |
| `_dry_run_refresh` 锚计数 | L1973 | L1993 | +20 | 仅位移（内容未变） |
| **新锚门块** | — | L1508-1527 | 新增 | 唯一产品码增量 |

9-cell 行契约/contracts.py：diff 仅两申报文件，零涉及 ✅。

## 3. 亲跑命令与关键输出（全部本会话实跑）

1. `python -m pytest skills/.../test_fix394_progress_suffix_refresh.py -q` → **29 passed, 12 subtests passed in 0.44s**（含新钉住测试）
2. F-1 复现探针（R1 版 9 项，构造输入）→ **9/9 有效通过**：
   - 双锚+无滞留词：execute=**schema_violation**、零写入、零 receipt；dry-run=**exit 3 schema_violation**——双面一致（R0 时 execute=ok aligned，已闭合）
   - **0 锚+无滞留词**（次序重排新分叉抽查）：execute=schema_violation、dry-run=exit 3 schema_violation——双面一致（R0 同类旁路一并闭合）
   - 双锚+有滞留词：双面一致拒绝（不回归）
   - **happy path 不被误伤**：单锚+滞留词仍正常刷新（ok、滞留词清除、单锚重打）
   - **no-op 语义不变**：单锚+干净行（干净 ledger 下复验）ok+文件字节不变+ledger 不存在
   - F-3 行为抽查：全角紧贴形态仍 miss（未顺带触碰）；F-2 行为抽查：翻转仍产双锚（未顺带触碰）
3. 定向回归：`pytest test_task_row_update.py test_fix393_writer_terminal_states.py -q` → **59 passed**；与新文件 29P 合计 **88P+12subtests**——与申报逐位一致（29+42+17=88）
4. staged 统计：`git diff --cached --stat` → 2 files, **+1414/−12** ✅；HEAD=8a94d64 未动 ✅；`git status` 复核 staged 两文件+本报告外零变更

## 4. 复审结论

**APPROVED**（`unresolved_blockers=0`）

- P1 F-1 修复经独立核验成立：锚门前置、双面同分类、无新分叉、happy/no-op 路径不受扰、重放次序未侵扰；新钉住测试锁死复现输入。
- 修复面之外（F-2/F-3/P3×5/fingerprint/9-cell）经行号位移全表+行为抽查证明零触碰——修复范围最小、纯粹（D4）。
- 遗留 P2×2（F-2/F-3）+P3×5 维持 R0 登记，由 Coordinator 按原排程跟踪；均不阻塞合并。

> Reviewer 声明：本复审为只读审查，未修改任何产品代码与 staged 状态；唯一写入物为本报告文件。
