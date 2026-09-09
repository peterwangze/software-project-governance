# Review: FIX-294 — Check 36 R3 归档任务 ID 解析（CODE, Round R0）

- **Task**: FIX-294 — AUDIT-149 N2：Check 36 R3 归档任务 ID 解析（DEC-151 口径：可解析豁免+披露 / 不可解析保留 WARN）
- **Reviewer**: code-reviewer（独立 R0；未参与实现）
- **日期**: 2026-09-09
- **审查对象**: 未提交工作树相对 HEAD 的两文件改动
  - `skills/software-project-governance/infra/verify_workflow.py`（+206/-1：L1118-1121 导入增补；L14234-14421 新增 FIX-294 块；L16021-16051 Check 36 面板换 wrapper + [EXEMPT] 披露块）
  - `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+270：L17310 起 `Fix294Check36ArchiveResolutionTests` 13 用例）
- **范围澄清（与任务书的差异，如实记录）**: 任务书描述 HEAD=`b8f6ca3` 且工作树另含 e2e 投影同步改动。实测 HEAD=`fe2faca`（投影同步已独立成 commit，`b8f6ca3` 为其祖先）；工作树 diff 现仅含本任务两文件（`git status --porcelain` 实证）——审查范围比任务书时点更纯净，投影改动不在本轮范围且已自然剥离。
- **工具边界**: 只读审查。复跑命令均为只读验证（测试、check-*、进程内探针）；本报告为 Reviewer 唯一写入物（任务书指定路径）。A/B 对照经临时 `git worktree`（HEAD 干净基线）完成，已清理，未触碰现有工作树。

---

## 1. 事实依据（全部为本审查独立复跑，2026-09-09，仓库根执行）

| # | 验证项 | 命令/方法 | 结果 |
|---|--------|-----------|------|
| F1 | 新增测试 | `python -m unittest tests.test_verify_workflow.Fix294Check36ArchiveResolutionTests -v`（infra 目录） | **Ran 13 tests, OK**（0.058s） |
| F2 | FIX-265 基础测试 | `python -m unittest tests.test_risk_mitigation_closure -v` | **Ran 24 tests, OK** |
| F3 | 全文件回归（含改动） | `python -m unittest tests.test_verify_workflow` | Ran 788 tests, **failures=10**（9×hot_fact 系 + 1×LoopRuntimeClaimAdapterTests） |
| F4 | 全文件回归（HEAD 基线，临时 worktree） | 同上命令于 fe2faca 干净检出 | Ran 775 tests, **failures=10——失败用例名单与 F3 逐项相同** |
| F5 | 引擎 Check 36 实况 | `verify_workflow.py check-governance` | 33 R3 → **19 WARN + 46 [EXEMPT]**（面板实证，格式与任务书示例一致，如 `RISK-008: DESIGN-005 resolved via archive: .governance/archive/tasks/legacy-v0.6.0.md (family range DESIGN-001~005)`）；全仓 summary **38 issues** |
| F6 | 两遍 wrapper 进程内量化 | 直调 `check_risk_mitigation_closure_with_archive()` | pass-1 R3=33 条/71 引用（67 唯一 ID）→ pass-2 WARN=19（全 R3）、豁免=46 条/43 唯一 ID（literal 33 + range 13）；**两次连跑结果逐字节一致（确定性 ✓）** |
| F7 | 注入不变量 | 进程内探针 | 调用方 map **未被变异**（`dict(active_map)` 拷贝）；**注入 ID 与 active map 交集 = 空**（永不覆盖既有条目） |
| F8 | index-only 对照（设计决策独立验证） | 仅对 `archive/index.md` 跑同一解析器 | 可解析 **23/67**（全语料 43/67）；**11 个 ID 仅经区间族可解析**（DESIGN-005、FIX-033/035/036/037/038、MAINT-009/010/011、PLAN-003/004） |
| F9 | 残留 WARN 诚实性抽查 | `Select-String` 于 archive/index.md 与热 decision-log | OPS-001 / MAINT-001 / RESEARCH-001 / DEC-149：archive index **无**、热 decision-log **有** → 不可解析保留 WARN 属实（AUDIT-149 H7「33 条全部可归档解析」假设确被语料证伪） |
| F10 | 辅助检查 | `check-locks` / `check-manifest-consistency` / `check-cross-references` | PASS / PASS / PASS（Active tasks: 2, File locks: 2） |
| F11 | 语料规模 | 脚本统计 | 50 文件 / 1,478,579 字节（≈1.4MB，与代码注释一致）；区间族记法出现 **179 次**（注释称 110——见 P3-1） |
| F12 | 端到端墙钟 | `Measure-Command` 包 check-governance 全程 | 单次 28.5s（无同机基线可比；微基准 +0.9s 为 Developer 报告值，**未独立复测**） |
| F13 | deferred-globals 陷阱实证 | 探针脚本首调 `_default_task_status_map()`（未先 `_resolve_shared()`） | 返回 None（NameError 被宽 except 吞掉）——**反向证明 wrapper 顶部 `_resolve_shared()` 调用是必要的**（否则新进程首调会静默降级为 fail-safe WARN，归档解析整体失效） |

**未验证项（红线标注）**：
- TDD 红态（12 ERROR + 1 FAIL）：历史声明，只读审查无法重放（需临时移除实现），**未复验**；绿态已复验（F1）。
- Developer 时点「总 issues 54→41」：工作树状态已漂移（锁/投影已被 Coordinator 修复），**不可直接复现**；我时点实测 38（F5），与 Coordinator「基线会低于 54」的预告一致。
- Developer「788 tests / 1 failure」绝对数：**未复现**（我环境 10 failures，两侧 A/B 一致——见 P3-5）。
- 微基准 +0.9s / resolver 0.9~1.7s / ~48s 墙：**未独立复测**（F12 仅单次观测）。

---

## 2. 五维度逐项结论

### 维度 1：正确性 — 通过（有 P3 备注）

逐行实读 diff 与 `checks/risk_domain.py` 判定函数对照：

- **两遍 wrapper 语义零漂移（验收标准 1）✓**：pass-1/pass-2 调用的是**同一** `check_risk_mitigation_closure`（verify_workflow.py L14383/L14415），`risk_domain.py` 零改动（git status 实证仅两目标文件）。注入纯增广（`if tid not in augmented` L14406），R1/R2 触发条件（`uncompleted` = map 内非 ✅）不可能因注入改变——注入 ID 原本不在 map（R3 的 absent 定义），注入后带 ✅ 归入「已完成」，既不进 `uncompleted` 也不进 `absent`。R4（无引用）/R5（跳过类）与 map 无关，逐字不变。R2 FAIL 不被豁免吞掉：`test_r2_fail_unaffected_by_sibling_archive_exemption` 断言 `wrapped["violations"] == base["violations"]` 逐字相等，我复跑绿（F1）。
- **注入状态经同一权威规则判定 ✓**：`_ARCHIVE_RESOLVED_STATUS` 含 ✅，走 DEC-151 ② 钦定的 `_task_status_is_completed`（✅ 子串）——无平行判定谓词。
- **解析器边界（验收标准 2）✓**：literal 相位 `\b` + `re.escape(tid)`——「REQ-0012 不误命中 REQ-001」有测试锁定且复跑绿；区间族 `_ARCHIVE_FAMILY_RANGE_RE`（`\b([A-Z]+-\d+)\s*~\s*(\d+)\b`）双端闭区间、`hi<lo` 剔除、`hi-lo>500` 封顶；「PLAN-001~004 不越界解析 PLAN-005」有测试锁定。zfill 宽度取头部记法宽度——宽度不匹配记法（如假设的 `FIX-1~042`）只会**漏解析**（保留 WARN，fail-safe 方向），结构上不可能误豁免（生成族恰为 lo..hi 枚举，`pending & family` 精确串匹配）。
- **fail-safe ✓**：不可读文件（IOError/OSError/UnicodeDecodeError/ValueError）逐文件跳过；目录缺失贡献空集；解析器结构上 never-raises（全 I/O 包裹）；「archive 缺失降级回 WARN」= audit N2 明示要求，有测试锁定（`test_missing_archive_corpus_fails_safe_to_warn`）。
- **确定性 ✓**：固定语料序（index.md → tasks/decisions/evidence/risks 各 name-sorted）、first-hit 溯源，`test_index_source_wins_deterministically` 锁定 + F6 双跑逐字节一致实证。
- **真实语料实证 ✓**（F6/F8）：33→19+46（43 唯一 ID）与 Developer 报告完全一致；13 条经区间族解析——与「DESIGN-005/PLAN-003/004 仅存于区间记法」的代码注释主张吻合（我实测还多出 FIX-033~038、MAINT-009~011 共 11 个 range-only ID）。

边缘备注（P3-4）：某 R1/R2 风险的 absent 兄弟引用若经**另一条风险的 R3** 成为候选并被注入，pass-2 再生成的该 R1/R2 warning 会失去 reason 中 `(extra refs not found: X)` 后缀——规则、verdict、task_refs（恒为全引用集）均不变，仅 reason 文本随 map 事实更新。语义零漂移成立，属可接受的表现差异，无测试锁定此边缘。

### 维度 2：安全性 — 通过

- 输入校验：解析目标 ID 来自 `_TASK_ID_IN_REF_RE` 产出的治理文件引用；literal 相位 `re.escape` 防模式注入。
- 注入防护：无 SQL/XSS/命令面；无 `eval/exec/subprocess`。
- 敏感数据：无硬编码密钥/token。
- 权限/路径：只读访问 `.governance/archive/` 固定子树（pathlib glob），无穿越面、无写操作、无网络。OWASP 关键项不适用面均无风险。

### 维度 3：可维护性 — 通过

- 命名（`_archive_corpus_files` / `_resolve_archive_task_refs` / `check_risk_mitigation_closure_with_archive` / `_ARCHIVE_RANGE_SPAN_CAP`）自释；FIX-265 基函数未被触碰（ADR-016 抽取边界受尊重）。
- 注释质量高（设计选项、确定性、性能口径、DEC-151 语义全部落注）；但两处量化注释与实测不符（P3-1）。
- 函数长度：wrapper ~74 行 / 解析器 ~60 行（含 docstring），属文档密集型包装器，可接受。
- 微重复：`SAMPLE_PATH.parent.parent` 在解析器内出现两次（P3 级）。

### 维度 4：性能 — 通过

- 惰性触发为**结构性**事实（代码实读）：无 R3 候选 → 不触语料 I/O，仅多一次 map 拷贝判空；候选仅来自 pass-1 R3 warnings。
- 文件单次读取（literal 相位读入并缓存 `corpus`，range 相位复用）；复杂度 ≈ O(文件×候选) 正则搜（50×67 实测语料），量级可控。
- 端到端单次 28.5s（F12）；+0.9s 微基准为 Developer 报告值（未独立复测，P3-2）。无 R3 项目零开销主张与代码结构一致。
- map 不可用路径存在 `_default_task_status_map()` 双次构建（wrapper 一次 + base 内部一次）——仅异常路径，开销可忽略（P3-6）。

### 维度 5：测试覆盖 — 通过（有 P3 缺口备注）

13 用例覆盖：豁免+披露（literal/range）、fail-closed 三边界（不可解析/语料缺失/map 不可用）、map 不覆盖、R2 FAIL 不被吞、确定性溯源、词边界、区间不越界、live 全链路、面板接线（源码形状）。核心路径/边界/错误路径齐备。缺口（P3-3）：span>500 封顶、非 UTF-8 跳过、zfill 宽度不匹配三个防御分支无直接测试。覆盖率门槛按 profile（standard ≥70%）——本块新增逻辑 13 用例密度充足，未跑覆盖率工具（无既成覆盖率基线可比，不单独扣分）。

---

## 3. 设计一致性（硬门槛 3）

| 依据 | 比对结论 |
|------|----------|
| **DEC-151 ①**（parts[12] 主源、parts[10] 回退、并集去重） | 基函数 L437-440 未动，契约原样 ✓ |
| **DEC-151 ②**（task 状态以 task_priority ✅ 规则为权威） | 注入状态经同一 `_task_status_is_completed` 判定，无平行谓词 ✓ |
| **DEC-151 ③**（跨实体引用由 R3 WARN 披露兜底） | 语义按 audit N2 细化：可解析→豁免**且披露**（[EXEMPT] 块 + 机读 `archived_exemptions` 带来源溯源），不可解析→R3 WARN 逐字保留。与 N2 建议动作原文（audit 文档 L180「可解析为终态的引用降为 INFO/豁免，不可解析的保留 R3 WARN（保住 DEC-151 布局漂移披露语义）」）逐点吻合 ✓ |
| **FIX-265 判定契约**（R1~R5、injectable map、fail-safe never-FAIL、never-raises） | wrapper 仅增广 map 重跑同一函数；豁免不吞 FAIL（测试+复跑）；never-raises 结构成立 ✓ |
| **AUDIT-149 N2 诉求**（-33 预期、fail-safe 降级、红→绿） | 实测 33→19（-14 警告，46 引用豁免披露）；fail-safe 有测试；红→绿历史声明未复验（绿已复验）；「tv/router 项目 R3 形状回验」以合成 fixture 覆盖形状类，未在真实 tv/router 项目上回验（P3-3 附注，建议 0.79.0 发布前补做） |
| **设计决策一：语料扫描 vs index-only** | **论证成立，且被我独立量化强化**：index-only 实测仅解析 23/67（F8），全语料 43/67，11 个 ID 仅存于 legacy 族文件；范围核增正当（只读、不动 archive.py/index 数据）。但代码注释中「~9/67」的量化依据与实测不符（P3-1）——结论对、数字错 |
| **设计决策二：区间族 fallback** | **成立**：literal 词边界优先（authoritative）、range 仅兜底；实测 13/46 豁免经 range、11 个 ID **仅有** range 可达（F8）——无此 fallback 则 11 个诚实归档 ID 将残留为假 WARN。span≤500 封顶 + 双端闭区间防滥用 |

---

## 4. AI 代码专项 5 项检查（硬门槛 4）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | 产品代码零 mock；测试的 `patch.object` 均配 `addCleanup`/上下文管理器 |
| 2 | 硬编码返回值 | **无** | `_ARCHIVE_RESOLVED_STATUS` 是数据常量（注入 map 的状态文本），非伪造返回；所有结果由真实判定函数产出 |
| 3 | 幻觉 API 调用 | **无** | 逐一核验：`_display_path`（L248）、`_resolve_shared`（risk_domain L69）、`_default_task_status_map`（L295）、`SAMPLE_PATH`（L7435）、`read_text/glob/re` 均真实存在 |
| 4 | 未实现 TODO | **无** | diff 内无 TODO/FIXME/placeholder/NotImplemented |
| 5 | 过度实现 | **无** | 面积与任务书规格一一对应（解析器+wrapper+面板披露+13 测试）；语料缓存复用是性能必需而非镀金 |

---

## 5. 发现清单

> P0 = 0，P1 = 0，P2 = 0，P3 = 6。

| # | 级别 | 位置 | 事实 | 影响 | 建议 |
|---|------|------|------|------|------|
| P3-1 | P3 | verify_workflow.py L14247（「~9/67」）、L14251（「110 occurrences」） | 注释量化主张与实测不符：index-only 实测 23/67（F8）；区间记法实测 179 处（F11） | 误导后续维护者评估 option (b)；设计结论本身不受影响（43>23、range-only 11 ID 实证更强） | 后续触碰该块时修正两个数字（可并入 0.79.0 收尾批次，不单独返工） |
| P3-2 | P3 | verify_workflow.py L14260-14263 性能注释 | +0.9s / resolver 0.9~1.7s / ~48s 墙为 Developer 报告值，本审查未独立复测（F12 单次 28.5s，无可比同机基线） | 性能口径无独立复算记录 | 无需代码改动；建议 evidence 侧补记基准方法（命令+机器）供 0.79.0 复测 |
| P3-3 | P3 | tests（新增类） | 三个防御分支无直接测试：span>500 封顶、非 UTF-8 文件跳过、zfill 宽度不匹配记法 | 防御逻辑仅经代码实读确认（方向均为 fail-safe：漏解析→保留 WARN，无误豁免） | 后续补 3 个微测试；同批补 tv/router 真实项目 R3 形状回验（audit N2 原始建议） |
| P3-4 | P3 | wrapper pass-2 再生成路径 | R1/R2 风险的 absent 兄弟引用经他风险 R3 注入后，pass-2 的该 warning reason 失去 `(extra refs not found: X)` 后缀；规则/verdict/task_refs 不变 | 极边缘的表现差异，无语义漂移、无漏报（豁免经 [EXEMPT] 披露承接） | 文档化即可；如求完备可加一条锁定测试 |
| P3-5 | P3 | Developer 回归报告口径 | 「788 tests / 1 failure」未复现：本环境 10 failures（9×hot_fact + 1×LoopRuntime），HEAD 干净基线 A/B **失败集逐项相同**（F3/F4）→ FIX-294 零新增零愈合成立；绝对数差异指向 hot_fact 系环境敏感（FEAT-011 证据行自身注记 LoopRuntime 为「环境超时」定性） | 不影响本任务裁决；但回归口径的绝对数不可跨环境引用 | 建议另立维护任务排查 HotFactSourceConsistencyTests 稳定性（非 FIX-294 范围） |
| P3-6 | P3 | wrapper L14390（`or active_map is None`） | map 为 None 时 base 产出 R1-unavailable 而非 R3 → candidates 恒空，该分支实际不可达（防御性冗余）；map 不可用路径存在双次 `_default_task_status_map()` 构建 | 无行为影响 | 保留无害；后续可简化 |

**豁免不静默专项确认（验收标准 3）**：[EXEMPT] 块在面板可见（46 条计数 + 8 条带溯源明细——与该面板 violations/warnings 一贯的 `[:8]` 截断约定一致）；机读面 `archived_exemptions` 全量 46 条；`all_issues` 记账行（L16051）未变，实测 summary 38 = 含 Check 36 的 19 警告、不含 46 豁免（若误计入应为 +46）。R2 FAIL 逐字不变有测试锁定并复跑绿。**豁免不会掩盖 FAIL：verdict 聚合仍由未修改的基函数执行，violations 通道与豁免通道正交。**

---

## 6. 硬门槛裁决

| 门槛 | 裁定 | 依据 |
|------|------|------|
| P0 阻塞数 = 0 | **通过** | 发现清单最高级别 P3 |
| 5 维度全覆盖 | **通过** | §2 逐项有结论 |
| 每条发现带级别+位置+事实+影响+建议 | **通过** | §5 表格 |
| 设计一致性检查完成 | **通过** | §3：DEC-151 ①②③ / FIX-265 契约 / N2 诉求逐条比对；两项设计决策论证均裁定成立（其一的注释量化数字有误但结论独立强化证实） |
| AI 专项 5 项 | **通过** | §4 全部完成 |
| 事实依据红线 | **通过** | §1 全部可复查；不可验证项显式标「未复验/未独立复测」 |

---

## 7. 结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**理由**：注入式实现经独立验证正确（同一判定函数、纯增广注入、调用方 map 零变异、注入 ID 与 active map 零交集）；解析器边界（词边界/区间族/封顶/fail-safe/确定性）经测试与真实语料双重实证；豁免带披露且不吞 FAIL；33→19+46 量化结果与 Developer 报告完全一致；A/B 对照证明零新增零愈合回归。6 条 P3 备注均为文档精度/测试缺口/环境口径类，无一阻塞，无需返工——建议作为 0.79.0 收尾批次的顺手项（P3-1 数字修正、P3-3 补微测试与 tv/router 回验）择机处理。

---

*本报告为 Reviewer 只读审查产出；除本文件外未修改任何文件。审查过程 A/B 对照使用临时 git worktree，已清理。*
