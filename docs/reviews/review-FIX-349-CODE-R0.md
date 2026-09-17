# Review Report — FIX-349 Code Review R0

- **Task ID**: FIX-349（0.83.0 链）— Check 16 假阳修复 + Unicode 分隔符扫描制度化
- **Round**: R0（初审）
- **Reviewer**: Code Reviewer Agent（只读审查；本报告为唯一写入文件）
- **审查方法**: 静态逐行审查（Read/Grep/Glob）。审查协议禁止执行命令——所有需运行才能确认的 Developer 申报项均按下文「申报核实表」标注**未验证**，不写成已通过。
- **审查对象**: 工作区未提交变更集
  - `skills/software-project-governance/infra/verify_workflow.py`
  - `skills/software-project-governance/infra/tests/test_verify_workflow.py`
- **Diff 依据**: `fix349-vw.diff`（7 hunks）/ `fix349-test.diff`（1 hunk），已与工作区现状逐 hunk 比对吻合

---

## 0. Diff 统计核对（申报 vs 实测）

| 申报 | 实测 | 裁决 |
|------|------|------|
| 主文件 +77/−9 | 7 hunks：53+2+3+2+0+0+8 = net +68；增 77 / 删 9（77−9=68 自洽） | ✅ 吻合 |
| 测试 +153 纯新增 | 1 hunk @@ 6→159 = +153/−0 | ✅ 吻合 |

---

## 1. 五维度审查结论

### 维度 1：正确性 — PASS（附 P2×2、P3 若干）

**③ Check 16 duplicate 豁免（已逐项核实）**：
- `goal_map` 值改为 `[(evd_id, task_id)]`（verify_workflow.py:12408, 12431, 12433）；配对守卫 `evd_tasks[i][0] != evd_tasks[j][0]`（:12455）✅
- **fan-out 豁免确属结构必然**：`parse_impact_analysis_entries`（:12319-12373）中一条 evidence 行只产出一个 `description`（parts[5]，:12344），fan-out 循环（:12365-12372）对每个 covered task 生成 entry 时共享同一 description——同 EVD 行内多 task 同文本不可能来自模板复用，豁免逻辑与解析结构一致 ✅
- **entries 面未收缩**：fan-out 条目各自仍进入 `entries`（:12365-12372 逐 task append；消费映射 :12435-12442 逐条 append）；测试 ③c 明确断言 `entries==2` 且两个 task_id 都在（test_verify_workflow.py:11791-11793）✅
- **输出元组形状不变**：`(evd_tasks[i][1], evd_tasks[j][1])` = (task_id1, task_id2)（:12456-12457）；两个消费面 `for t1, t2 in ...duplicates`（:15282, :21135）解包兼容 ✅
- **跨 EVD 检测能力保持**：不同 evd_id 配对仍报（测试 ③b :11743-11760 钉住 `[("TASK-100","TASK-200")]`）✅
- **live 假阳场景属实**：`.governance/evidence-log.md:507` 存在 EVD-507 行，task_id 列含 `FIX-129, REQ-094, REQ-095, RISK-036` 多 ID，fan-out 机制成立 ✅（申报「live 19→0」具体计数需运行，见申报核实表）

**⑥ Unicode 分隔符扫描（已逐项核实）**：
- 7 字符族 U+000B/001C/001D/001E/0085/2028/2029（:11776-11784）与申报一致 ✅
- **行号/列号计算正确**：`line = content.count("\n",0,pos)+1` 对首行（count=0→line 1）、连续命中、任意位置均正确；`col = pos - rfind("\n",0,pos)` 在无前导换行时 rfind=-1 → col=pos+1（首行 1-based），有前导换行时 col=1-based ✅。`find(char, pos+1)` 步进对单码点字符无重叠遗漏；str.find 按码点操作，多字节字符（U+2028/2029/85）正确 ✅
- **WARN 真非阻塞（Check 14 聚合路径）**：`structural_issue_is_blocking`（:393-396）对 severity ∈ {INFO, WARN, WARNING} 返回 False；Check 14 聚合仅把 `blocking_structural_issues` 计入 `all_issues`（:15208-15210），WARN 只打印 ✅
- **「存在才扫」边界正确**：`is_file()` 为否即跳过（:11788-11789），session-snapshot 等可选文件缺失不报错（测试 :11859-11867 钉住）✅
- **挂载点**：Check 14 `check_structural_validity` 子检查 6（docstring :11819-11820，挂载 :11984-11985）✅
- **无新 CLI/无新段**：diff 无 argparse 变更；repo 级 grep 确认 issue type 在 md/json 中无 registry/manifest 登记面（`evidence_col_mismatch` 同样无——先例一致），manifest-consistency 无新增登记义务 ✅

### 维度 2：安全性 — PASS（零发现）

- 扫描为纯只读（is_file/read_text/find/count/rfind），固定文件名元组，无用户输入参与路径拼接，无 eval/exec/subprocess——无注入面。
- 无敏感数据硬编码；测试 fixture 全部 tempfile，无真实 `.governance/` 写入路径。
- 无新增外部输入解析。

### 维度 3：可维护性 — PASS

- 命名清晰（`_scan_unicode_line_separators`、`unicode_line_separator`），docstring 完整交代 EVD-890 事故语境、severity 定级依据（对照 `evidence_col_mismatch`）与数据修复归属边界（:11756-11770）。
- ③ 的修复以 6 行注释锚定在行为变更处（:12445-12450），含 live 假阳案例引用（EVD-507→REQ-094↔REQ-095）——注释与代码一致。
- 扫描逻辑独立成 helper 而非内联进 `check_structural_validity`，职责单一；无重复代码引入。

### 维度 4：性能 — PASS

- 扫描成本：5 文件 × 7 次 C 级 `str.find` 全文扫描。以 evidence-log 1.5MB 计 ≈ 52.5MB 字符扫描量，CPython C 实现为毫秒量级；每文件仅 1 次 I/O（无 N+1）。
- duplicate 配对保持 O(k²)（k = 同文本条目数，受 entries 总量约束，量级小）；较修复前无复杂度变化。

### 维度 5：测试覆盖 — PASS（附 P3 缺口）

- **+5 测试与申报一致**：GoalAlignmentTests ×2（:11743, :11762）+ UnicodeLineSeparatorScanTests ×3（:11818, :11859, :11869）✅
- **负例真实构造字符**（非 mock 断言）：`\x0b`×2、`\u2028`、`\x85`、`\x1e`、`\u2029` 均为真实码点植入（:11826, :11829, :11831, :11833, :11881）✅
- **断言钉住 file:line+码点**：by_file 分组断言 file 键、line 精确值（[2,3]/2/1/2/1）、detail 含 U+ 标签，另钉 type 与 severity（:11842-11857, :11886-11894）✅（`col` 未断言——见 F-4）
- **③c 走真实 fan-out 路径**：`expand_task_ids("REQ-094, REQ-095")` → `{REQ-094, REQ-095}`（:9758-9771）；`_plan_task_ids_from_hot_tracker` 对 fixture 行 `| **P1** | REQ-094 |` 正则可命中（:12096-12098）——非 mock 捷径 ✅
- **fixture 无真实环境污染**：全部 `tempfile.TemporaryDirectory` + `patch.object(vw, "GOVERNANCE_DIR"/"SAMPLE_PATH"/"EVIDENCE_PATH")`；集成测试调用 `check_structural_validity()` 时仅只读真实 ROOT 的 SKILL.md/manifest ✅
- **无预存测试回归面**：全测试文件仅新增测试引用 `duplicates`（grep 实证 3 处均为新增），旧行为无测试钉住 ✅
- 未覆盖：col 字段、U+000C 场景（对应 F-1）、read 失败路径（预存类，与既有子检查一致地未测）。

---

## 2. 发现列表

### P0 阻塞（0 条）

无。

### P1 关键（0 条）

无。

### P2 建议（2 条，均不阻塞合并）

**F-1 [P2] 扫描族遗漏 U+000C（FF）——与「闭合 splitlines 边界类」的自述口径不完全一致**
- 位置：verify_workflow.py:11776-11784（separators 元组）；自述 :11762-11765
- 事实：Python `str.splitlines` 边界集为 {\n, \r, \r\n, \x0b, **\x0c**, \x1c, \x1d, \x1e, \x85, \u2028, \u2029}。扫描覆盖 7 个但缺 U+000C（form feed）。docstring 自述覆盖「all honored as line boundaries by splitlines-style consumers」的族，U+000C 同属该类却不在列。注：\r（U+000D）被排除是**正确**的——`Path.read_text` 默认 universal-newlines 翻译会把 \r/\r\n 归一为 \n，读入后不可见且无害；但 U+000C **不受翻译、会幸存**，仍是真实的 splitlines 解析危害。
- 影响：热文件中的 U+000C 仍可复现 EVD-890 同类假阳而不被本扫描发现。无已知 live 实例（EVD-890 为 VT），且 WARN 级非阻塞。
- 建议：separators 元组补 `("U+000C", "\x0c")`（+1 行 +docstring 更新 +负例可选）；或在 docstring 明示排除口径。

**F-2 [P2] 「非阻塞」语义仅在 Check 14 聚合路径成立——独立 CLI `structural-validity` 对 WARN 仍 exit 1**
- 位置：verify_workflow.py:21057-21074（`cmd_check_structural_validity`：`if issues: ... sys.exit(1)` 不区分 severity）；对照聚合路径 :15208-15210
- 事实：独立 CLI wrapper 对**任何** issue（含 WARN）打印 `[FAIL]` 并 `sys.exit(1)`。新扫描产生的 WARN 命中会使该命令失败。此为**预存语义**——既有 `evidence_col_mismatch` WARN 在同命令下行为相同；Developer 申报原文「WARN 不入 all_issues 阻塞集」在 Check 14 路径上事实准确，无申报失实。
- 影响：使用方若以「WARN 非阻塞」预期直接调用 structural-validity 命令会产生预期差。
- 建议（不阻塞）：在函数 docstring 或 TOOLS.md 注明「WARN 会使独立 structural-validity 命令 exit 1，仅在 check-governance 聚合中非阻塞」。

### P3 讨论 / 备注（5 条）

**F-3 [P3] 申报消费面行号漂移**：申报「两个消费面约 L15214/L21067」——实测 duplicates 消费面在 :15280-15285 与 :21133-21136（`check_goal_alignment()` 调用点 :15261/:21113）。偏差约 46~66 行；两个消费面本身存在且形状兼容，申报的「两个」计数正确。属行号近似标注不精确，不影响结论。

**F-4 [P3] 测试未断言 `col` 字段**：`_scan_unicode_line_separators` 的 col 计算（:11799）无回归防护（首行/行中两分支均未钉住）。列值计算逻辑已静态验证正确，建议后续补 1~2 个 col 断言。

**F-5 [P3] ③ 豁免按 evd_id 等值键控的边界**：若两行共享**重复的 evd_id** 且目标文本相同，修复前会报 duplicate、修复后豁免。重复 evd_id 本身属数据缺陷态（且当前无独立 EVD id 去重检查面），触发条件为双重缺陷叠加，风险低。备案即可。

**F-6 [P3] 裸 `read_text` 异常路径**：新扫描 :11790 无 try/except，UnicodeDecodeError/PermissionError 会传播令 Check 14 整体失败——与同函数既有子检查 1~3（:11828/:11877/:11908）**风格一致**，预存类，非本 diff 引入。备案。

**F-7 [P3] e2e fixture 副本保留修复前行为**：`project/e2e-test-project/.../verify_workflow.py:7036` 的独立副本含旧版 Check 16。按既有发布期 fixture regen 政策（FIX-348 +17 同样处于预存 lag 状态），非本任务义务；Coordinator 在 0.83.0 发布收尾 regen 时统一同步即可。

---

## 3. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 测试仅用 `patch.object` 做路径重定向（既有测试惯例）+ 真实 tempfile fixture；负例植入真实码点字符，断言真实函数输出 |
| 2 | 硬编码返回值 | ✅ 无 | `_scan_unicode_line_separators` 全部真实计算；③ 修复为纯逻辑变更，无桩/假返回 |
| 3 | 幻觉 API | ✅ 无 | 所用 API 均为真实 stdlib：`Path.is_file/read_text`、`str.find/count/rfind`、`re.search`、`unittest.mock.patch.object`、`tempfile.TemporaryDirectory`；无不存在的方法/参数 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME/pass 桩；docstring 声明的行为与实现一致 |
| 5 | 过度实现 | ✅ 无 | 无新 CLI、无新配置项、无新抽象层；扫描面严格限定 5 文件 × 7 字符；docstring 较长但为事故语境与定级依据服务，属合理文档成本 |

---

## 4. Developer 申报核实表（事实依据红线）

| # | 申报 | 裁决 | 依据 |
|---|------|------|------|
| ① | diff +77/−9 与 +153 | ✅ 已验证 | §0 逐 hunk 核对 |
| ② | ③ goal_map 值/守卫/元组形状/entries 不收缩/跨 EVD 保持 | ✅ 已验证 | :12408/12431/12433/12455/12456-12457；:12362-12372；:15282/:21135 解包兼容 |
| ③ | ③ live 19→0 | ⚠️ **未验证**（机制成立） | 审查协议禁执行命令；EVD-507 实况行（evidence-log.md:507）与 fan-out 机制已静态核实，方向性支持，具体计数需运行 |
| ④ | ⑥ 7 字符族/5 热文件存在才扫/WARN 非阻塞/挂载 Check 14-6 | ✅ 已验证 | :11776-11784/:11772-11775/:11788-11789/:393-396+:15208-15210/:11984-11985 |
| ⑤ | ⑥ 无新 CLI/无新段/registry、manifest 无登记面 | ✅ 已验证 | diff 无 argparse 变更；repo 级 grep md/json 无 issue-type 登记面（evidence_col_mismatch 先例一致） |
| ⑥ | 测试 +5（×2+×3）全 tempfile fixture | ✅ 已验证 | test 文件 :11743/:11762/:11818/:11859/:11869；patch+tempfile 全覆盖 |
| ⑦ | 裸 verify PASSED / cross-references PASS / manifest-consistency PASS（722 canonical） | ⚠️ **未验证**（无结构性冲突证据） | 禁执行命令；静态核对无新增文件/路径/登记面，manifest 面不涉及本变更 |
| ⑧ | 向后兼容 | ✅ 已验证（静态） | 公共函数签名未变；`check_goal_alignment` 返回 dict 键集与 duplicates 元组形状未变；消费面解包兼容 |
| ⑨ | 回归三组红归因（archguard +17 预存 + 本任务 +68 叠加 / WSL 无发行版 / hooks replay 漂移）；重锚移交 Coordinator | ⚠️ **未验证**（内部一致性通过） | 「本任务 +68」与本 diff 净增行数 68 **精确吻合**（§0），归因算术自洽；+17 预存量、WSL 环境红因、hooks 漂移均需运行/环境事实，超出本次可验证范围。归因逻辑框架成立，裁决权在 Coordinator（符合申报的范围划界） |
| ⑩ | 无幻觉 | ✅ 已验证（静态） | §3 AI 专项第 3 项 |

---

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | 0 | ✅ PASS |
| 5 维度逐一结论 | 100% | 5/5（§1） | ✅ PASS |
| 每条发现 P0~P3 + 位置 + 事实依据 | 100% | 7/7（§2） | ✅ PASS |
| 设计一致性 | 已完成 | 与 FIX-349 申报范围一致；docstring 与行为同步更新；无 ADR 冲突证据 | ✅ PASS |
| AI 专项 5 项 | 全部完成 | 5/5（§3） | ✅ PASS |

---

## 6. 审查结论

```yaml
verdict: APPROVED_WITH_NOTES
unresolved_blockers: 0
findings:
  P0: 0
  P1: 0
  P2: 2   # F-1 U+000C 族完整性 / F-2 CLI wrapper WARN exit-1 语义注记
  P3: 5   # F-3~F-7
blocking: false
notes: |
  两项 P2 均为非阻塞改进项：F-1 建议补 U+000C（1 行 + 测试可选），
  F-2 建议文档注记；均可在本轮顺手处理或遗留下一轮，不构成合并障碍。
  Developer 申报中所有可静态验证项全部吻合；运行类申报（live 19→0、
  三个硬门槛命令、回归三组红归因）按事实红线标注未验证，其中
  「+68 叠加」与 diff 净增行数精确吻合、归因框架自洽，重锚裁决权
  按申报划界归 Coordinator。
```

**复审提示**（若 Coordinator 选择先修 F-1 再合并）：复审时逐条核对 F-1~F-7 的修复/遗留状态，无需重开全量审查。

---

*Review method note: 本审查为静态只读审查（Read/Grep/Glob），按角色协议未执行任何命令、未修改任何被审文件；本文件为唯一写入产物。*
