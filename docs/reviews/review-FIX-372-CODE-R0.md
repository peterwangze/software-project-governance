# Code Review Report — FIX-372（Round 0，串行单席）

- **审查对象**：工作树未提交修改（`docs/reviews/diff-FIX-372.patch`，411 行 patch，已全文通读）
- **涉及文件**：`skills/software-project-governance/infra/verify_workflow.py`（format check ~L10029-10080 + Check 20 两处扫描 ~L14241-14345）+ `infra/tests/test_verify_workflow.py`（新增 2 测试类 6 用例 + 3 处 fixture 迁移）
- **审查席**：Code Reviewer（只读；本报告为唯一写产物）
- **结论**：**APPROVED_WITH_NOTES**（unresolved_blockers=0；P0=0，P1=0，P2=1，P3=3）
- **工具时间盒**：11 次调用（≤12 合规）。Bash 禁用——测试/验证命令未能独立复跑，涉及处如实标注。

---

## 0. 范围核实

任务提示引用 triage FIX-372.json；本席 glob（`docs/reviews/*FIX-372*`、`**/triage-FIX-372*`）未直接命中该文件。范围核实改以 `.governance/plan-tracker.md` L94 为准：TRIAGE-FIX-372 机录 2026-09-20，范围 ①②③ 与任务提示逐条一致（Check 20 列偏移+统一切分器 / format check LIVE 对齐 / author→entry_method 重命名）；同族 `.governance/change-triage/FIX-373.json` 已实证存在于该目录（机录模式佐证）。diff 触达的 3 处读取点与 triage 范围精确对齐，**无范围外修改**（D4 纯粹性 ✓）。9 处 evidence 列读取点清单：plan-tracker L94 已留档（其余 7 处安全，前轮审查完成），本席未逐一重审该 7 处（范围限定 + 依赖前轮记录），如实声明。

## 1. 特别复核点 1 — 三处修复正确性（代码事实核验）

**切分器语义根基（verify_workflow.py L12270-12328，直接读源核实）**：
- `_split_governance_table_row`：仅在 `depth==0 and not in_code_span and not in_string` 时切分 `|`，**保留首尾空串**（无剥离）→ 10 格 LIVE 行 = 12 parts：parts[0]=''、[1]=EVD、[2]=TaskID、[3]=Type、[4]=Description、[5]=Fact、[6]=Location、[7]=EntryMethod、[8]=Date、[9]=Gate、[10]=Notes、[11]=''。
- `_governance_table_cells`（L12322-12328）：包裹切分器后剥离首尾空串 → cells[0]=EVD；10 格 = 10 cells，9 格历史行 = 9 cells。

**① Check 20（L14241+ 主扫描 + L14323+ 交叉引用扫描）**：`evd_type=parts[3]`、`description=parts[4]`、`file_location=parts[6]`（未动，LIVE 布局恰为 Location——正确）、`entry_method=parts[7]`（位不动）——与切分器实测语义及 fixture `_evidence_row_live`（tests L11807-11821，`| evd | task | type | desc | fact | loc | author | date | gate | notes |`）完全一致。两处扫描均已从裸 `split("|")` 换为 `_split_governance_table_row`（管道符保护统一 ✓）。`len(parts)<9` 守卫：LIVE 12 parts / 9-cell 历史 11 parts 均可达，parts[0..8] 可达性保持 ✓。**修复正确**。

**② format check（L10029+）**：`cells = _governance_table_cells(line)`；`len(cells)<9` 短行门槛；公共检查 TaskID=cells[1]、Type=cells[2]、Description=cells[3]；`len>=10` 分支 Location=cells[5]、EntryMethod=cells[6]、Date=cells[7]；9-cell else 分支 Author=cells[5]、Date=cells[6]——两组偏移按各自形状映射均正确；`cells` 保证 ≥9 后索引安全（`cells[0] if cells else '???'` 兜底空表 ✓）。**修复正确**。

**③ entry_method 重命名**：语义重命名，索引 parts[7] 不动（详见 §3）。**正确**。

## 2. 特别复核点 2 — format check 强度评估

**「6→6 字段」声明核实：不准确。** 代码事实：前版必填 7 字段（TaskID/Stage/Type/Description/Location/Author/Date，diff 删除行逐一可数）；新版 LIVE 10-cell 必填 6 字段（TaskID/Type/Description/Location/EntryMethod/Date）、9-cell 历史行必填 5 字段。**实际 7→6**（P3-F2 记录）。实质强度评估不受影响：
- 删除的 Stage 检查在 LIVE 布局下读到的是 Type 列（错位伪检查）——Type 非空在前版被重复检查两次（伪 Stage+Type），未覆盖任何 LIVE 独有列，删除无真实强度损失。
- 事实依据（fact basis）列从"必填"降为"不检"：这正是本修复消除的误报类（空 fact 被当 Description 误报），LIVE 约定下 fact 合法可空——属修正错位强制，非放松有效约束。
- 保留的 6 字段覆盖身份（EVD/TaskID/Type/Description）、位置、录入者、日期——检测强度**实质保持**。 Developer 声明"6→6"疑为计数口径误差，建议更正记录（不阻塞）。

**9-cell 豁免宽度：存在可探明的残余缺口（P2-F1）。** 按格数嗅探形状无法区分「9-cell 历史行」与「被截断的 LIVE 行」：LIVE 行缺失 Date 格后恰余 9 格（|evd|task|type|desc|fact|loc|entry|gate|notes|），else 分支把 cells[5]=Location、cells[6]=EntryMethod 当 Author/Date 检查非空——全通过，**真实缺失的 Date 漏报**（前版任何 9 格行一律报短行，无此洞）。同样，缺 Notes 格的截断行静默通过（Notes 前版也不检，增量可接受）。不会放过「真缺字段的完形 LIVE 行」（10 格时 Location/EntryMethod/Date 各归其位，retention 测试 L171-180 已钉住 Location 缺失仍报），缺口仅限截断形。建议后续以内容启发式消歧（如 9-cell 分支校验 cells[6] 呈日期形态，截断 LIVE 行该位是录入方式文本即报）——P2 遗留，不阻塞。

## 3. 特别复核点 3 — entry_method 重命名（parts[7] 不动）

决策依据成立，双行形实证：
- LIVE：parts[7]=录入方式（`_evidence_row_live` 的 `author` 参数实测落位于第 7 数据格，tests L11818-11821）。
- Legacy `_evidence_row_generic`：前版引擎读 `author=parts[7]` 且前版 23P 绿（含 "Analyst" 激活用例）——parts[7]=author 在 legacy 形状下由前版测试矩阵自证。
- 两形状下 parts[7] 均承载记录者身份 → `"Analyst" in entry_method` 子串检测在 LIVE（"Analyst 机写（结构化返回）"）与 legacy（"Analyst"）下均有效；description 侧 `"Analyst:"` 标记检测随 parts[4] 修正后读真描述列。**重命名语义对齐 LIVE、零行为漂移，采纳**。

## 4. 特别复核点 4 — 测试判别性（回退旧索引必红面推演，静态逐用例追踪）

| 用例 | 旧索引下行为 | 红面 |
|---|---|---|
| test_impact_type_read_from_type_column | evd_type 读到描述文本≠「影响分析」；旧 desc 读 fact 无子串→activated=0≠1 | 🔴 |
| test_bypass_detected_when_only_coordinator_recorded | impact 整体漏检→bypassed=0、pass=True，断言反向 | 🔴 |
| test_fact_column_not_treated_as_description | 旧 desc 读 fact="Analyst: 影响分析记录"→impact 经 description 命中且「Analyst:」命中→activated=1/bypassed=0，断言反向 | 🔴（双列各自钉死的最具判别性构造） |
| test_live_row_with_empty_fact_basis_passes | 旧 parts[5]=fact=""→误报 missing Description | 🔴 |
| test_nine_cell_historical_row_not_flagged | 旧裸切 10 parts<11→「only 9 fields」误报 | 🔴 |
| test_live_row_missing_location_still_flagged | retention pin——新旧行为均报 Location（设计上双绿） | ⚪（守回归） |
| 迁移位 1/2（AgentActivationTests） | 旧引擎+新 fixture：type 停在 parts[3] 读不到、旧 desc 读空 fact→激活/绕过断言反向 | 🔴🔴 |
| 迁移位 3（P1 skip 用例） | 优先级门控用例，列位不敏感 | ⚪ |

**静态必红面 = 7**，与任务声明「回退旧索引必红面 ≥7」及 Developer 实测「红 7F/23P」一致（本席 Bash 禁用未复跑，为逐行静态推演 + Developer 声明交叉印证；运行时终验由 pytest 门禁兜底）。6 新用例均含前修复回归注释，判别性优良。

## 5. 特别复核点 5 — EVD-248 增量定性复核

直接读切分器源码（L12270-12312）确认：quote 开引号分支（L12295 `if ch == '"'`）**确无 `not in_code_span` 守卫**——code-span 内遇 `"` 置 in_string=True 后，后段所有 `|` 在 in_string 分支（L12285-12293）被吞直至闭引号/EOL → 完好行折叠、格式类误报「short row」。机制与 EVD-248 描述（10 格折叠为 5 格）吻合。**定性核实**：
- 该函数定义不在本 diff 任一 hunk 内（diff 仅改两处调用点），为共享件既有局限，**非本 diff 引入** ✓；
- 留票处理符合 D4：`.governance/change-triage/FIX-373.json` 已实证入账（P2 录、实际严重级自评 P3、出槽 0.88+ 且 0.87 M-2 披露已知噪声），plan-tracker L95 已建 FIX-372→FIX-373 链 ✓；
- 补充（P3-F4）：FIX-373 triage 记录的当前影响面是 format check 单条误报（fail-noisy 方向）；同一泄漏在 Check 20 读路径为 **fail-blind 方向**（impact 行被折叠→检测漏计）——建议 FIX-373 验收清单纳入双向影响与 Check 20 形状回归 fixture。

## 6. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | §1 全部偏移经切分器实测语义核验；守卫可达性保持；`cells` 索引安全。残余：P2-F1 截断行歧义 |
| 安全性 | ✅ 通过 | 无注入面（纯本地 Markdown 解析）、无敏感数据硬编码、无 eval/命令拼接；regex 无 ReDoS 形态 |
| 可维护性 | ✅ 通过 | 复用共享切分器无第二解析源（FIX-292 教训遵守）；重命名语义对齐；注释含 FIX 锚点与前修复机理，风格与文件一致 |
| 性能 | ✅ 通过 | 每行单次 O(n) 切分，无新增嵌套扫描/N+1 |
| 测试覆盖 | ✅ 通过（含 1 P3 留意） | §4：6 新用例+3 迁移全覆盖三条修复的回归面；retention pin 防过度放宽。P3-F3：交叉引用扫描分支无专属回归 pin（现由主扫描同形状间接覆盖） |

## 7. AI 代码专项 5 项

| 项 | 结论 |
|---|---|
| Mock 残留 | ✅ 无——patch.object 为合法依赖注入（SAMPLE_PATH/EVIDENCE_PATH/GOVERNANCE_DIR 重定向临时目录），无伪造返回值 |
| 硬编码返回值 | ✅ 无——引擎全部走真实文件读取 |
| 幻觉 API | ✅ 无——`_split_governance_table_row`/`_governance_table_cells`/`expand_task_ids` 等均实证存在（读源/定义行号核验） |
| 未实现 TODO | ✅ 无新增——注释均为 FIX-372/FIX-368 机理说明 |
| 过度实现 | ✅ 无——修改严格限定 triage ①②③；9-cell else 分支为必要分支非镀金 |

## 8. Findings 清单

| # | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | P2 | verify_workflow.py format check（~L10058-10076） | 9-cell 豁免按格数嗅探，缺 Date/Notes 格的截断 LIVE 行（恰 9 格）落入 else 分支用错位偏移检查全通过，真实缺失 Date 漏报（前版一律报短行无此洞） | 后续版本以内容启发式消歧（9-cell 分支校验 cells[6] 日期形态），或对 9 格行附「historical-shape assumed」提示 |
| F-2 | P3 | 交付声明 | 「Stage 必填删除——6→6 字段」与代码事实不符：前版必填 7 字段，实为 7→6（LIVE） | 更正任务记录口径；实质强度结论（§2）不受影响 |
| F-3 | P3 | check_agent_activation 交叉引用扫描（~L14323-14345） | 该分支的偏移修复无专属回归 pin，现仅由主扫描同形状间接覆盖 | 补一条仅交叉引用路径可达的用例（如主扫描未命中、覆盖集经 raw_ids 展开命中的形状） |
| F-4 | P3 | .governance/change-triage/FIX-373.json | 该泄漏在 Check 20 读路径为 fail-blind 方向，triage 现记录的是 format check fail-noisy 方向 | FIX-373 验收纳入双向影响评估 + Check 20 形状回归 fixture |

**未独立复核声明（如实）**：Developer 声明的「TDD 红 7F→绿 30P」「check-governance 172→173（唯一增量=EVD-248）」「实数据 0 个 P0 跨层任务」因 Bash 禁用未复跑，本席以静态逐行推演交叉印证（红面推演=7 一致、EVD-248 机制与 172→173 定性吻合、fail-open 恢复=检测能力恢复与 bypass 用例实证一致），运行时终验归 pytest/Check 30 门禁。format fixture 以 GOVERNANCE_DIR 解析证据文件路径（Check 20 fixture 则显式 patch EVIDENCE_PATH）——解析不对称性经 Developer 绿灯声明印证为函数内路径解析差异，运行时门禁兜底。

## 9. 硬门槛裁决

| 门槛 | 裁决 |
|---|---|
| P0 阻塞数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅（§6 逐项有结论） |
| 每条发现带 P0-P3 | ✅（F-1~F-4 全标注） |
| 设计一致性 | ✅（范围=TRIAGE-FIX-372 ①②③ 精确对齐，无范围外修改；9 处清单前轮留档引用） |
| AI 专项 5 项 | ✅（§7 逐项有结论） |

## 10. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0、P1=0；F-1（P2）与 F-2~F-4（P3）均为非阻塞遗留项，建议随 FIX-373 或下个维护窗口处置。三处修复经代码事实逐项核验正确，测试判别性达标，EVD-248 定性与留票处理合规（D4）。可合并。

---

*Reviewer: Code Reviewer Agent（software-project-governance）· R0 · 2026-09-20 · 证据：diff-FIX-372.patch 全文 / verify_workflow.py L12270-12328、L10029+、L14241+ / test_verify_workflow.py L11807-11839、L11937+ / plan-tracker.md L94-95 / change-triage/FIX-373.json / evidence-log.md L848*
