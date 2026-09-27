# REVIEW-FIX-399-CODE-R0 — Check 28c 解析器装饰日期单元格健壮性修复 · 独立代码审查

- **Task**: FIX-399（P1，target 0.91.0）· triage: `.governance/change-triage/FIX-399.json`（2 文件申报，与实际 diff 一致）
- **审查对象**: 工作区未提交 diff（`196894a` HEAD 之后，2 files，+95/−4）——`verify_workflow.py`（正则 + `_latest_published_release_fact`）+ `test_verify_workflow.py`（+76 行测试）
- **审查轮次**: CODE-R0（首轮）· 审查方式：先审后提交 · 逐行 diff + 亲跑验证命令
- **结论**: **APPROVED_WITH_NOTES** · **unresolved_blockers=0** · P0=0 · P1=0 · P2=1 · P3=3
- **审查人**: Code Reviewer Agent（独立，未参与实现）· 2026-09-28

---

## 0. 亲跑命令结果摘要（全部由本审查者在本会话实跑）

| # | 命令 | 结果 |
|---|------|------|
| V1 | `git diff HEAD --stat` / `git status --porcelain` | 恰 2 文件 +95/−4；工作树另有一个**无关**未跟踪文件 `docs/reviews/review-FEAT-072-DESIGN-R0.md`（见 F-4） |
| V2 | python 进程内对真实 `.governance/plan-tracker.md` L278-282 逐行跑新正则 | L278 0.87.0 纯格式→命中 `2026-09-21`；L279 0.88.0 纯格式→命中 `2026-09-25`；L280 0.91.0 规划行→**不命中**；L281 0.90.0 装饰单日期→命中；L282 0.89.0 多日期→命中。真实行集合 `latest fact = 0.90.0 @ 2026-09-27`；全计划文件同值。**纯格式行 old==new 匹配完全一致** |
| V3 | 进程内 A/B（同进程同数据，仅将解析器回退为 HEAD 逻辑） | OLD fact=`0.88.0/2026-09-25`、NEW fact=`0.90.0/2026-09-27`；OLD 28c face = **恰 1 issue**（`session snapshot missing latest published release 0.88.0`）、NEW face = **0 issues** → 本修复代码净效果 = −1 误报、0 新增 |
| V4 | `python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_verify_workflow.py" -k fix399 -k fix339 -k snapshot -k hot_fact_source` | **Ran 36 tests — OK**（含新 6 用例 + FIX-339 族 + 0.42.0 既有用例 `test_hot_fact_source_rejects_stale_session_snapshot` / `test_hot_fact_source_accepts_current_session_snapshot` + snapshot 命名族） |
| V5 | 整类 `HotFactSourceConsistencyTests` 加载运行（unittest loader） | **Ran 28 tests — OK**（0 failures / 0 errors；运行中 `[FAIL]` 行为负例用例的引擎预期输出） |
| V6 | `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only --level strict` | 全量清单中 **28c 零条目**（0.88.0 missing-release FAIL 消失）；24 静态钉 17 条 WARN 全部指向 `test_evidence_binding_drift.py`/`test_task_priority.py` 既有文件，**`test_verify_workflow.py` 零新增静态钉**。总量 37 vs EVD-1205 记录基线 33 的 +4 漂移归因见 §6 |
| V7 | 边界探针（合成畸形输入，进程内） | 装饰文本含内嵌 `*` → 整行不匹配（fail-closed 跳过，同修复前行为）；未闭合粗体行 → 捕获组跨行（见 F-1） |

注：任务书建议的包路径形式 `python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow` 因 `software-project-governance` 含连字符（非法模块标识符）不可用；本审查改用 discover 形式（V4/V5），效果等价且已验证。

---

## 1. 审查清单逐项结论

### 清单 1 正确性 — **PASS**
- 新正则日期捕获组 `((?:\d{4}-\d{2}-\d{2})[^*]*)` 对三类真实行格式行为经 V2 亲验：0.88.0 纯格式行为不变（old==new 逐字节一致）、0.90.0 装饰单日期命中、0.89.0 多日期命中且取末日期=发布日 `2026-09-26`。
- 规划行（0.91.0 `**规划（M-0 立项 …）**`）不命中——状态 cell 严格匹配 `**已发布**` 的前置结构未被放宽。
- 匹配集单调性：`[^*]*` 可空且前缀模式不变 → L(new) ⊇ L(old)。两个消费点均召回向单调：L2039（本修复目标）与 L2185（`any(version != active_version …)` 只可能 FAIL→PASS，不可能反向）。
- 事实依据：V2 输出、verify_workflow.py:1924/2039/2185 逐行读。

### 清单 2 发布日语义 — **PASS**
- `re.findall(r"\d{4}-\d{2}-\d{2}", date_cell)` 后取 `dates[-1]`，真取 cell 内**最后一个**日期（V2 实测 0.89.0 cell 三个日期取末=09-26 发布日；单测 `test_fix399_release_fact_multi_date_cell_takes_release_date` 同断言）。
- 「日期按时序叙述、发布日收尾」的假定局限**已注释在案**（verify_workflow.py:2045-2047，含 labelled 发布：提取需先做 roadmap 规范化的展望）。
- `date_text` 回归保护成立：`dates[-1]` 恒为 findall 纯 ISO 产物，装饰尾巴不可能进入输出（V2 实测 `date_text='2026-09-27'`；正例×3 均断言 date_text）。唯一消费点 L2085 仅作错误消息展示。

### 清单 3 回归面 — **PASS**
- 既有判据代码零改动：diff 仅触及 L1917-1925（正则）与 L2032-2057（`_latest_published_release_fact` 函数体）；`_snapshot_fact_source_issues` 的版本不匹配（L2075-2078）、日期过期（L2082-2088）、缺最新发布键（L2090-2091）三判据逻辑未动，仅输入（latest fact）修正。
- 定向回归 V4（36 OK）+ V5（整类 28 OK）双证既有 0.42.0/0.81.0 断言全绿；其余触达该 face 的测试为 mock 注入（L6337/7828/8210）或 external-validation skip 路径（L10856+），不受解析器影响。
- 既有全量套件单文件超 300s 超时未在本轮跑完（文件体量原因，非本修复相关）；以 face 全覆盖（V4+V5）替代回归证据，覆盖了正则改变的全部直接/间接消费点。

### 清单 4 测试质量 — **PASS**
- 负例真实：规划/预留行**带真日期**（2026-10-01/2026-12-31）被排除 `assertIsNone`；已发布无日期行（`**—**`）不误配。两负例均验证"状态门在前"的真实路径而非恒真断言。
- 集成用例红→绿可证：断言 `_snapshot_fact_source_issues(decorated_plan, …)==[]`；旧解析器下 decorated 行不命中 → latest fact=0.88.0 ∉ snapshot 正文 → 必产生 `missing latest published release 0.88.0` issue——该 issue 文本已在真实数据上被 V3 实测复现（红态证据），绿态 V1/V4 实测 0 issues。
- fixture 版本派生 `_fix399_next_minor_version()`：`read_active_version` 实存（resolve_entry.py:82）、测试文件 sys.path 已注入 infra（L32-35）、in-minor bump 满足引擎 `0\.\d+` 版本正则、随活跃版本前进 evergreen。静态字面量仅历史版本（0.86.0-0.89.0），非活跃版本钉 → V6 实证 check 24 零新增 WARN（DEC-213③ 规避成立）。

### 清单 5 范围纯粹 — **PASS**
- V1：diff 恰 2 文件 +95/−4，与 triage `files` 申报一致；测试文件为**纯插入**（单 hunk `@@ -1996,6 +1996,82 @@`，零删除行，未触碰任何既有用例）。
- verify_workflow.py 仅两个 hunk（L1917-1925 / L2032-2057）；FEAT-072 锚区（L6734-6800）之后零 hunk → 锚区内容与 HEAD 逐字节一致。
- `project/e2e-test-project/**` 零触碰。

### 清单 6 check-governance 净效果 — **PASS**（漂移归因见 §6）
- V6 全量清单：`missing latest published release 0.88.0` 消失，28c 零条目。
- V3 提供了比 stash 对照更强的同数据隔离证据：同一进程同一份数据，仅回退解析器 → OLD face 恰 1 issue、NEW face 0 issues → **代码净效果 = −1 / +0**。

---

## 2. 五维度覆盖（硬门槛）

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | PASS | §1 清单 1；V2/V3 亲验 |
| 安全性 | PASS | 输入为内部治理数据；正则 `[^*]*` 线性、无回溯爆炸；放宽为召回向不产生绕过面（状态门 `**已发布**` 未放宽）；无注入/敏感数据面 |
| 可维护性 | PASS | FIX-399 注释齐备（正则侧+语义侧），局限声明在案；P2-1 加固建议见下 |
| 性能 | PASS | findall 线性扫描；`_latest_published_release_fact` O(行数×cell 长度)，无 N+1 |
| 测试覆盖 | PASS | 6 新用例（正例×3/负例×2/集成×1）+ 集成缺陷链 + 既有 36+28 回归绿 |

## 3. AI 代码专项 5 项（硬门槛）

| 项 | 结论 |
|----|------|
| mock 残留 | 无——测试用 tempfile 真实文件 IO，无 mock 短路核心断言 |
| 硬编码返回值 | 无——实现为真实解析逻辑 |
| 幻觉 API 调用 | 无——`read_active_version`（resolve_entry.py:82）、`_parse_iso_date`（L2030）实存且签名匹配 |
| 未实现 TODO | 无 |
| 过度实现 | 无——改动最小面（正则单组 + 取末日期 + 注释），未夹带 |

---

## 4. Findings

### P2（建议，不阻塞合并）
- **F-1 P2 | verify_workflow.py:1924 | `[^*]*` 可跨行，畸形输入下可跨行吞噬下一行行首**
  事实：V7 实测——未闭合粗体的日期行（`**2026-09-28` 无闭合）+ 下一行为已发布行时，捕获组跨行匹配为 `('0.93.0', '2026-09-28\n| ')`，并消费掉下一行行首 `**` 致其失配 → latest 误键为 0.93.0@09-28（正确应 0.94.0@09-29；旧解析器该场景反而正确键 0.94.0）。
  影响：仅畸形 markdown（未闭合粗体）触发；真实数据已验证（V2 五行全闭合）无此形态；误键后仍 fail-visible（错误 latest 键会在 snapshot 比对面产生 FAIL，非静默通过）。
  建议：`[^*]*` → `[^*\n]*`（单字符加固，装饰尾巴均为单行，真实行已验证不受影响）。
  处置：可遗留至下一轮/本批收尾小修，不阻塞本票。

### P3（备查）
- **F-2 P3 | verify_workflow.py:2049 | `if not dates: continue` 为防御性死分支**——捕获组以日期开头，`findall` 恒非空。无害（防御未来正则改动），知悉即可。
- **F-3 P3 | 装饰文本含内嵌 `*` 的行整体跳过**——如 `**2026-09-28（见 *注*）**` 不匹配（V7 实测），与修复前装饰行行为相同（fail-closed 向）。若未来 roadmap 出现该形态需先做格式规范化（与 L2046 注释的局限声明同族）。
- **F-4 P3 | 工作树无关未跟踪文件**——`docs/reviews/review-FEAT-072-DESIGN-R0.md` 不属于本票；提交 FIX-399 时建议 targeted staging 恰 2 文件，避免 `git add -A` 误裹挟。

## 5. 数据侧观察（非本 diff 缺陷 · Coordinator 待办）
- FIX-399 / FEAT-072 任务行的 goal-layer 契约占位（check 18d/18d-RB2/18f/18i FAIL 族）与 EVD-1205 缺 `用户影响` 字段（check 17 FAIL）、EVD-1207 `获得=` 值超出合法范围（check 17 WARN）为**已提交治理数据行的完备性债**，契约检查代码未被本 diff 触碰，与本代码变更无因果。不阻塞本审查，建议 Coordinator 按契约门修复流程另票/顺带清偿。
- check 21/22 的「1 product-code task review debt」即本审查（R0）进行中的正常挂账状态。

## 6. check-governance 计数漂移归因（37 vs EVD-1205 基线 33）
- +4 全部为数据侧：上述 §5 的 FIX-399/FEAT-072 行完备性 FAIL/WARN 族（EVD-1205 机器写入后补录行 EVD-1206/1207 与任务行契约检查的交互）。
- 代码侧净效果经 V3 同数据 A/B 隔离：**−1（0.88.0 误报消解）/ +0（零新增）**——与 EVD-1205 申报的 stash 对照结论（34→33、28c 消解、0 新增）方向一致。
- 方法说明：本审查曾尝试 TEMP 副本整引擎 A/B，出现 `KeyError: source_version`；控制实验证实工作树版本同位置同崩——系脚本位置探针伪影而非版本差异，该方法已弃用，以进程内 A/B（V3）替代。
- 本审查未对仓库做任何写操作（V3/V7 均为进程内探针；V6 为只读检查命令）。

## 7. 硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅（§2 逐项有结论） |
| 每条发现标注级别 | ✅（F-1~F-4 均有 P2/P3 标签） |
| 设计一致性 | ✅ 与 triage reason、EVD-1205/1206/1207 申报一致；无偏离 |
| AI 代码专项 5 项 | ✅ 全部完成（§3） |

**最终结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**——修复正确、测试看护真实、范围纯粹、净效果机证为 −1 误报/0 新增；P2-1 建议随批或遗留小修，P3 备查。可提交（注意 F-4 targeted staging）。
