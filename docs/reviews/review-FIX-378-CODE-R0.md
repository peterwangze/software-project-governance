# FIX-378 代码审查报告（CODE · R0）

> **Round**: R0（初审，无前轮引用）
> **Task**: FIX-378 — R0 代码审查（e2e legacy 快照副本切分器守卫同步 + 处置路径判定）
> **Reviewer**: Code Reviewer Agent（独立审查席，只读）
> **审查对象**（git-ignored fixture——工作树 diff 不可见，以文件现状 + Developer 行级前后对照 + FIX-373 R0 报告在案前态交叉比对为准）:
> - `project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py` 两处编辑（docstring L6855-6863 + 守卫 L6887；修改后 sha256 = 2401a0eaba5ac0ce88143b6738e4ebf81900edbb7edb305ccb155befd0348fa3——Coordinator 已独立复核在场）
> - 对照读取：`skills/software-project-governance/infra/verify_workflow.py`、`skills/software-project-governance/core/version-projections.json`、`skills/software-project-governance/infra/release/projection.py`、`skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py`、`docs/reviews/review-FIX-373-CODE-R0.md`
> **优先级**: P2（REVIEW-FIX-373-CODE-R0 F-1 [P2] 承接票）

---

## 0. 审查方法与证据边界（以读代跑声明）

- 角色铁律：Bash 禁止。本次审查**未重跑任何命令**——Developer 声称的冒烟红绿、py_compile、check_legacy_snapshots PASS、check-manifest-consistency PASS 均记为 **Developer-claimed**，其真实性以代码证据做机理/算术一致性评估（§8）。
- sha256 = 2401a0…fa3 记为 **Coordinator-attested**（本席无命令工具不复算；文件现状读取与该在案值不矛盾）。
- 事实依据全部来自：副本 L6820-6939 / L7330-7429 与主仓 L12280-12399 / L12860-12959 逐行读取；`version-projections.json` 全文（280 行）；`projection.py` `check_legacy_snapshots` L252-344；`test_projection_legacy_snapshots.py` L130-204；`review-FIX-373-CODE-R0.md` 全文（F-1 出处）；`.governance/evidence-log.md` L836（EVD-248 原行）+ L2550（EVD-1134）；`.governance/plan-tracker.md` L95（FIX-378 任务行）；两侧 `if ch ==` 引号入口全量枚举（12 = 12 对称）；fixture tests 目录 splitter 引用 grep（0 处）；`check-manifest-consistency` 命令面（主仓 L2645/L24452/L25375）。
- 整文件穷尽性边界：副本为 git-ignored fixture，无法以 git diff 复核「全文件仅两处编辑」；本席以（a）`FIX-378`/`in_code_span` 在副本内仅出现于目标函数（grep 5 处，与主仓同构）、（b）函数体逐行比对零漂移、（c）`if ch ==` 12=12 对称枚举、（d）FIX-373 R0 在案前态行号算术（§1.3）作为修改面证据。超出该证据链的整文件断言不在本席可证范围，不计为发现。

## 1. 修改内容核实

**1.1 行为变更（唯一 1 行）**：副本 L6887

```python
if ch == '"' and not in_code_span:   # 修复前: if ch == '"':（FIX-373 R0 F-1 在案旧态 L6879）
    in_string = True
    current.append(ch)
```

与主仓 L12346 **逐字同型**。函数体其余部分（副本 L6864-6904 ↔ 主仓 L12323-12363）逐行比对**零漂移**：初始化五变量、反引号分支（`not in_string` 门）、字符串内迁移、花括号 depth、管道分支（`depth == 0 and not in_code_span`）全部一致。

**1.2 docstring 机理同步**：副本 L6855-6863。正文五句与主仓 L12315-12322 **逐字一致**（code-span 内引号是字面文本不得开启 JSON 字符串态 → 未守卫引号翻转 in_string → 反引号分支被 `not in_string` 抑制 → 状态钉到行尾吞并后续管道 → live 实证 EVD-248 folded 10 data cells -> 5）；唯一差异是首行标注替换为 `FIX-378 (backport of the FIX-373 fix into this declared legacy snapshot):`——**有意的溯源披露**，非漂移。

**1.3 行级前后对照算术自洽**：FIX-373 R0 报告 F-1 在案副本旧态「L6879 无守卫 / L6855 旧 docstring」；新 docstring 9 行（旧单行，净 +8）→ 6879 + 8 = **6887** ✔ 与新守卫行号吻合。

**1.4 守卫语义复核**（独立推演，对照 FIX-373 R0 §2）：`in_code_span=True` 期间 `"` 落入 else 字面追加，不再开启 in_string；反引号分支（`not in_string` 门）不再被抑制，code-span 正常闭合，其内管道受 L6897 保护。互斥不变量 `not (in_string and in_code_span)` 恢复成立。守卫是**收紧**而非放宽（引号从「开启状态」改为「字面文本」）。

## 2. E-2 同型性判定独立核实 — **判定：成立（非同型缺陷 / 两侧设计一致）**

- **两侧函数逐行比对**：`_extract_structured_fact_json` 副本 L7340-7383 ↔ 主仓 L12868-12911 **字节级同型**——均无 `in_code_span` 状态；`if ch == '"':`（副本 L7375 / 主仓 L12903）两侧**均未守卫**，零漂移。
- **机理不对应**：该函数状态机服务于 `结构化事实:` 标记后 JSON 对象抽取——quote 仅跟踪 JSON 字符串（配对开闭 + 反斜杠转义），反引号仅在 marker 后被跳过一次（L7350-7353 / L12878-12881），**无状态翻转**。FIX-373 缺陷机理（code-span 内引号开启 in_string + 反引号分支被 `not in_string` 抑制 + 状态钉到行尾吞并管道）在该状态机中**无对应面**——它不解析 Markdown 表格行，无管道折叠症状面。
- **完备性枚举**：两侧 `if ch ==` 各 12 处、逐一同型对应——早段 splitter（副本 L106/L109 ↔ 主仓 L378/L381，`in_code` 态无引号分支）、治理表切分器（已守卫）、JSON 抽取器（两侧均未守卫）。本 diff 未引入也未遗留任何主源/副本漂移。
- **精确表述**：本判定是「该点不携带 FIX-373 同型机理且两侧行为一致」，非「该函数在一切输入下无任何边界情形」的证明；若未来出现实证误报，属独立缺陷票范畴。F-1 选项 (b) 共享模块化落地时该点自然被单一事实源覆盖。

## 3. 处置路径判定（E-1：最小同步 vs FEAT-040 政策张力）— **裁决：处置成立**

**3.1 声明条目核实（Developer 主张 #1 ✔）**：`version-projections.json` L209-215 `fixture-engine` 条目在位且完整（path/canonical/scope/reason 四要素齐全；0.82-era 副本、≈579KB vs ≈1.08MB、~34.7k 差异行表述在案）。该副本**不是投影目标**——`projections[]` 中无任何 target 指向副本路径（全文核对）。

**3.2 守卫机理核实（Developer 主张 #2 ✔「收敛即红」）**：`projection.py` L252-344 实现仅有三种红：声明路径缺失（L319-324）、与 canonical **字节级收敛**（L325-331，`path.read_bytes() == canon.read_bytes()` → issue → pass=False）、声明不完整（L306-312）。**分歧本身不红**——局部 backport 后副本仍与主仓大规模分歧，守卫保持绿。`checked = len(entries)` = 10 与声明条目数（10 条）及 Developer 声称 `checked=10` 一致；`test_projection_legacy_snapshots.py` L142-152 另以测试钉住「分歧必须持续披露、不得静默吸收」。

**3.3 FEAT-040 语境张力裁决**：条目 reason 在案记载两个被否决选项——(a) 手工同步 4 个 **attribution** 点（否决理由：在 34.7k 行分歧上打 4 行补丁会**制造副本跟踪 canonical 的假象**）；(b) byte_copy 晋升（否决理由：~530KB 重写的爆炸半径远超投影注册表任务）。本票与两者**性质不同**：

| 维度 | FEAT-040 否决的 (a)/(b) | FIX-378 实际处置 |
|---|---|---|
| 驱动 | 投影注册表任务内的 cosmetic 对齐 | F-1 [P2] 承接票——live 缺陷 backport（plan-tracker L95 任务行明列「最小同步 diff」为 sanctioned 处置选项，DEC 裁决仅针对模块化替代方案） |
| 披露 | 无标注 → 制造跟踪假象 | docstring 显式 `FIX-378 (backport …into this declared legacy snapshot)` 溯源标注 |
| 声明条目 | — | 未触碰（L209-215 原文核对） |
| 守卫面 | — | converged=[]（不收敛、不缺失、声明完整——机理上不可能翻红） |

**张力承认存在**（副本现于 1 个行为点 + docstring 跟踪 canonical，守卫对该局部收敛不可见——字节级全等比较设计如此），但语境差异成立、披露充分、声明可证伪性未受损 → **E-1 裁决：Developer 的「最小同步」处置成立**。残余观察项见 N-1/N-3（P3，非阻塞）。

## 4. 五维度结论（验收标准 1）

| 维度 | 结论 | 依据 |
|---|---|---|
| **正确性** | **PASS**——守卫行与主仓逐字同型、函数体零漂移（§1.1）；守卫语义独立推演成立（§1.4）；红绿算术与真实数据行/EVD-1134 双向吻合（§8.1-8.2）；行号算术自洽（§1.3） | §1、§8 |
| **安全性** | **PASS**——纯文本表格解析器，无输入执行面；守卫收紧输入解释（code-span 内引号从状态开启改为字面文本），不扩大接受面；无敏感数据；纯仓库内只读审查对象，无真实环境操作 | L6864-6904 |
| **可维护性** | **PASS**——最小守卫 + 溯源 docstring（显式 backport 标注直接缓解 FEAT-040「假象」关切，§3.3）；docstring 正文与主仓零漂移，唯一差异即披露行本身 | §1.2、§3.3 |
| **性能** | **PASS**——单遍 O(n) 逐字符扫描不变；守卫为常量时间布尔判断；无新循环/数据结构/正则 | L6871-6903 |
| **测试覆盖** | **PASS（附注）**——fixture 侧无 splitter 测试钉（fixture tests 目录 grep 0 处引用；fixture 测试文件本身为 declared legacy snapshot `fixture-test-verify-workflow`）；回归防护 = 主仓套件 `Fix373SplitterCodeSpanQuoteTests` + 本轮冒烟（Developer-claimed）。对 declared legacy snapshot 而言可接受，不阻塞；见 N-2 | §8、N-2 |

## 5. 发现列表（P0=0 / P1=0 / P2=0 / P3=3）

| # | 级别 | 位置 | 发现 | 事实依据 | 建议 |
|---|---|---|---|---|---|
| N-1 | **P3** | `skills/software-project-governance/core/version-projections.json:209-215` | `fixture-engine` 声明 reason 的叙事现含一步时效差：其否决叙事针对 attribution 点手工同步，而副本现含一处**有意的缺陷 backport**——reason 未记录该事实（守卫可证伪性不受影响，纯披露完整性） | 条目 reason 原文 vs 副本 L6857 backport 标注比对 | 未来治理记录变更时顺带在 reason 追加一行 backport 注记（如「L6887 守卫为 FIX-378 定点 backport，见副本 docstring」）；不要求本轮修改 |
| N-2 | **P3** | `project/e2e-test-project/skills/software-project-governance/infra/tests/test_verify_workflow.py`（缺失钉） | 副本切分器行为无可重复测试钉：fixture 套件对 `_split_governance_table_row`/`_governance_table_cells` 零引用，本票回归防护依赖主仓套件 + 一次性冒烟 | fixture tests 目录 grep 0 处引用；主仓 `Fix373SplitterCodeSpanQuoteTests`（FIX-373 R0 §6）为行为等价钉 | 可接受（declared legacy、扩测试面将触碰另一声明快照）。若副本日后晋升，主仓测试钉随迁移自动生效 |
| N-3 | **P3** | 两侧 `_split_governance_table_row`（主仓 L12314 / 副本 L6854） | F-1 选项 (b) 泛化性根治（切分器抽共享模块单一事实源）仍开放——本票选 (a) 后同型缺陷「修两处」的双维护面持续存在（本票即是第二次逐点修复的实例） | F-1 原建议（review-FIX-373-CODE-R0 L69）；本票处置路径 | 保留为后续候选票；plan-tracker L95 已将「共享模块化 DEC 裁决」列为替代路径 |

## 6. AI 代码专项 5 项（验收标准 3）

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 编辑区为纯状态机守卫 + docstring，无任何 mock/monkeypatch/替身构造 |
| 2 | 硬编码返回值 | **无** | 行为变更为状态转移条件收紧，无预设返回值、无数据特判 |
| 3 | 幻觉 API | **无** | 守卫仅引用**既有**局部变量 `in_code_span`（副本 L6868 初始化 / L6873 翻转 / L6897 管道保护均为 0.82-era 既有代码，非本票发明的新状态）；无未核实符号 |
| 4 | 未实现 TODO | **无** | 编辑区无 TODO/FIXME/占位；docstring 的 FIX-378 标注是溯源说明而非未完成标记 |
| 5 | 过度实现 | **无** | 恰 1 行条件 + docstring 机理同步；无投机抽象、无超范围重构、未触碰声明条目；符合 D4 修改纯粹性 |

## 7. 设计一致性检查（已完成）

- **与声明快照契约一致**：`declared_legacy_snapshots` 的可证伪守卫设计（缺/收敛/声明不完整 → 红）允许声明文件继续演进，只要不消失、不全等收敛——本票不触发送检三条件（§3.2）。
- **与 FIX-373 R0 §7 注释契约的关系**：主仓 L12366-12370「单一事实源 / no second shape source」契约未被触碰；副本为 declared legacy，其与主仓的双实现共存本身即已机器披露的分歧（census 披露面），非本票新造。
- **与任务行验收对齐**：plan-tracker L95 验收 = 「副本守卫同步 ✔ / e2e 冒烟如适用零回归（Developer-claimed 冒烟即其直接面）/ pytest 指定套件零回归」——结构性论证：canonical 文件未触碰（主仓套件无新回归面），fixture 套件零 splitter 引用（grep 实证）。
- 无 ADR/契约偏离；无接口变更（函数签名与返回形状不变）。

## 8. Developer 验证声明核实（以读代跑口径）

| 声明 | 核实方式 | 判定 |
|---|---|---|
| 冒烟红绿 LIVE：EVD-248 行红 **6 parts/5 data_cells** → 绿 **12/10** | 独立算术推演：evidence-log L836 实际行 = leading 空 + 4 个完整数据格（EVD-248/FMT-001/维护/治理归档）+ 描述格内首个未守卫引号起 EOL 合并巨格（吞并其后 5 数据格）= 红 **6 parts/5 data_cells** ✔；绿态 10 数据格 + 两端空 = **12/10** ✔；10→5 折叠与 FIX-373 docstring「folded 10 data cells -> 5」吻合 | **算术独立证实（未复跑）** |
| 冒烟红绿 SYNTH：形状行红 **5/4** → 绿 **12/10** | EVD-1134（evidence-log L2550）在案 FIX-373 红态记录「10 格**折叠 4 格** + only 4 data fields 误报复现」→ 红 4 数据格吻合 ✔；绿 12/10 同上。SYNTH 行的具体构造无 repo 工件可复核 | **与主仓记录一致性成立；行构造 Developer-claimed** |
| py_compile exit 0 | 无法复跑；编辑区（docstring + 条件行）经逐行读取语法良构 | **合理（未复跑）** |
| check_legacy_snapshots PASS（checked=10/converged=[]/missing=[]） | 机理核实（§3.2）+ 条目计数 10 吻合 + backport 后不满足任一翻红条件（非缺失、非字节全等收敛、声明完整）；PASS 输出本体未复跑 | **机理自洽；输出 Developer-claimed** |
| check-manifest-consistency PASS（849/978） | 命令面存在（主仓 L2645/L24452/L25375）；数值含义与输出未复跑 | **命令存在证实；数值 Developer-claimed** |
| sha256 = 2401a0…fa3 | 本席无命令工具不复算；文件现状读取与在案值无矛盾 | **Coordinator-attested** |

**交叉核对裁决（任务指定项）**：红态数值与主仓 FIX-373 记录的**一致性主张成立**——LIVE 红 5 数据格 ↔ FIX-373 docstring「10→5」；SYNTH 红 4 数据格 ↔ EVD-1134「10 格折叠 4 格 / only 4 data fields」；两侧绿态 12/10 与 10 数据格形状吻合。

## 9. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | 0 | ✔ PASS |
| 5 维度全覆盖 | = 100% | 5/5（§4） | ✔ PASS |
| 每条发现标注级别 | = 100% | 3/3（N-1~N-3 均有 P 级 + 位置 + 依据 + 建议） | ✔ PASS |
| 设计一致性检查 | 已完成 | §7（含 declared_legacy_snapshots 机制与 FEAT-040 语境比对） | ✔ PASS |
| AI 代码专项 5 项 | 全部完成 | 5/5（§6） | ✔ PASS |

## 10. 审查结论

## **APPROVED_WITH_NOTES**（unresolved_blockers=0）

- 硬门槛 5/5 通过；零 P0/P1/P2；守卫与主仓逐字同型、函数体零漂移、溯源披露充分；E-1 处置路径判定成立（§3）、E-2 同型性判定成立（§2）。
- **Notes**（非阻塞遗留）：N-1（P3）声明 reason 时效性注记建议；N-2（P3）副本侧无可重复测试钉（对 declared legacy 可接受）；N-3（P3）F-1 选项 (b) 共享模块化根治保持开放。
- 本结论仅为代码审查硬门槛通过，不替代测试执行复核（Developer 声称的命令运行结果未由本席复跑）与发布审查。
- E-3/E-4 未在本票裁决面中定义，无对应裁决对象（结构化返回模板字段，非本票内容）。
