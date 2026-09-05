# FIX-286 Code Review R0 — dsh.skills 路径穿越回归测试 3 例 + 穿越/畸形诊断消息拆分

- **Date**: 2026-08-28（Reviewer 无时钟访问，Coordinator 补记）
- **Task**: FIX-286（P2，0.78.1 入槽，DEC-173②）——review-FIX-272-CODE-R0 F1（路径穿越回归测试 3 例）+ F2（穿越/畸形诊断消息拆分）
- **Review round**: **R0**（首次审查，无前轮 findings）
- **Reviewer**: Code Reviewer Agent（独立于 Developer；只读审查，零文件修改、零命令执行）
- **审查对象**: 工作树未提交改动——`skills/software-project-governance/infra/verify_workflow.py`（本任务 hunk：L6780-6792 常量 + L6795-6828 分类器 + L6830-6839 wrapper + L6881-6895 消息拆分）与 `skills/software-project-governance/infra/tests/test_verify_workflow.py`（本任务 hunk：DshSkillsManifestTests 类内 L16643-16763，注释块 + 3 探针 + 互斥测试）
- **范围红线确认**: 两文件中 FIX-283（verify_workflow.py :15728 区域，实读 L15720-15737 确认为 `_extract_summary_count` 解析器区域）与 FIX-287/288/289（test_verify_workflow.py L8904 `Fix287ParserBoundaryTests` 等）已审改动不在本次范围；实读确认与本任务 hunk 区零交叠
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**（P0=0，P1=0，P2=0，P3=4；硬门槛 5/5 通过，无未解决 BLOCKING finding）

---

## 审查范围与方法

| 项 | 方式 |
|---|---|
| 被审代码 | verify_workflow.py L6740-6939 + test_verify_workflow.py L16540-16767 全量逐行通读（hunk 区逐行、非 hunk 区边界确认） |
| 来源报告 | `.governance/review-FIX-272-CODE-R0.md`（任务描述中 docs/reviews/ 路径不存在，实际位于 .governance/；F1=L55/L138、F2=L45/L98/L139 原文比对） |
| 等价性对照物 | 原 `_normalize_declared_skill_path` 逐字历史形态不可得（无 git 执行权限）；以 R0 报告 L30 分支清单（14/14 探针独立验证记录）为对照基准推演 |
| 消费方排查 | 全仓 grep "invalid declaration entry"（7 处）/"path traversal or absolute entry rejected"（6 处）/`dsh.skills`（24 处 .py）——逐处定性 |
| 调用点排查 | grep 两函数全部调用点——产品侧唯一调用 = check_dsh_skills_manifest L6879；wrapper 仅测试消费 |
| 背景一致性 | `.governance/change-triage/FIX-286.json`（EVD-917 files_correction 留痕）+ plan-tracker L268（🔄 代码完成待 R0）/L265（FIX-283 已审） |
| 运行验证 | **未执行**——Reviewer 只读协议；最终态绿灯采信 Developer 自报 + Coordinator 独立抽测（-k 5 passed），静态一致性经逐行核验 |

---

## 五维度逐项结论

### 维度 1：正确性 — PASS（P0/P1/P2 = 0）

**已独立验证 ✓**：
- **分类器逐行正确**（L6811-6827）：non-string → `(None, "non-string")`；strip + 反斜杠归一 + `./` 剥离；空值 → format；`/` 前缀 → absolute；`":" in parts[0]` → absolute；`".." in parts`（按段精确匹配，`...`/`a..b` 不误伤）→ traversal；空段/`.` 段 → format；唯一接受路径 L6827 返回归一化 POSIX 相对路径。七分支无一死代码、无一不可达。
- **wrapper 转发正确**（L6839）：`return _classify_declared_skill_path(raw)[0]`——签名 `(raw) -> Optional[str]` 与 None 契约不变；docstring（L6831-6837）声明与实现一致。
- **消息分支互斥**（L6882-6895）：`if reject_reason in _REJECT_SECURITY_DETAIL`（仅 traversal/absolute）→ security 消息；else（format/non-string）→ legacy 消息——if/else 结构保证每条目恰落一桶。
- **label 契约**（L6881）：`entry if isinstance(entry, str) else repr(entry)`——字符串原样、非字符串 repr 转义；三探针 `probe in issue` 断言依赖的原样输出成立（含 Windows 反斜杠探针）。
- **declared_count==0 断言链**：探针条目被拒 → declared 空 → `declared_count==0` ✓；若分类器放行，条目进 declared → is_file 检查 → "declared but missing on disk"（非 security issue）→ 探针 (c) 失败 + count 断言失败——双重捕获。

### 维度 2：安全性 — PASS（P0/P1/P2 = 0）

**已独立验证 ✓**：
- **拒绝集合不放宽（核心安全声明，成立）**：逐输入类比对——非字符串/空值/POSIX 绝对/Windows 盘符（首段含 `:`）/`..` 段/空段或 `.` 段六类，每类在当前分类器中均有对应 None 分支（L6811-6826），与 R0 L30 记录的原 None 分支清单一一对应，无遗漏、无新增接受分支。等价性推演依据 = R0 的 14/14 探针分支记录（原实现逐字形态未验证——见未验证声明 3）。
- **诊断不构成绕过面**：reason 只影响 issue 文本（stdout/返回列表），不影响控制流——`normalized is None` 是唯一拒绝判据（L6880）。
- **无注入面**：label/detail 均为纯文本拼进 issue 字符串；无 shell/eval/HTML/文件写上下文；repr 转义非字符串 label。
- **零写路径**：check 链路仅 read_text/json.loads/glob/is_file/relative_to；本次 diff 未引入任何写 API。

### 维度 3：可维护性 — PASS（P3×2：F1/F4）

- 单点分类 + 薄 wrapper 结构清晰：分类逻辑唯一载体（L6795），wrapper 保 legacy 契约（3 处测试消费），无逻辑复制。
- 注释质量高：每个 hunk 均带 FIX-286 / review-FIX-272-CODE-R0 F1/F2 出处；L6780-6785 注释准确预告了 format/non-string 留 legacy 桶的兼容策略。
- reason 常量轻微不对称（F4 附带）：traversal/absolute 有常量（L6786-6787），format/non-string 为字面量——当前无代码引用后者 token，可接受。
- 函数规模：分类器 33 行、check 拆分分支 +14 行——均远低于 50 行阈值。

### 维度 4：性能 — PASS

- 分类器 O(len) 字符串操作；check 主循环每条目一次分类调用（原为一次 normalize 调用）——调用数不变，无退化。
- `_REJECT_SECURITY_DETAIL` 字典 O(1) 查找；无新 I/O、无新循环嵌套。

### 维度 5：测试覆盖 — PASS（P3×2：F2/F3）

- **R0 F1 三探针落地**：`../skills/x/SKILL.md`（L16655）/`/skills/x/SKILL.md`（L16682）/`C:\skills\x\SKILL.md`（L16707）——探针字符串与 R0 L55 建议逐字一致；每例五重防线（unit None + reason 精确元组 + security issue + declared_count==0 + rglob 零新增）。
- **reason 精确类断言为强契约**：`assertEqual(_classify(...), (None, "traversal"/"absolute"))` 全元组比较——锁定 reason token 不漂移、不退化到 legacy 桶。
- **互斥测试**（L16732-16763）：traversal 条目 `len==1` + `assertNotIn` legacy substring；format 条目含 `(format invalid)` 标记 + label——两类互斥可区分性被锁定（absolute 类锁定缺口见 F3）。
- JSON 转义正确：Windows 探针经 json.dumps/loads 往返后还原为 `C:\skills\x\SKILL.md`，分类器 replace 归一后 `parts[0]=="C:"` → absolute ✓。

---

## AI 专项 5 项检查（100% 完成）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✓ 无 | 新增测试零 mock/patch；tempfile 真实文件构造 |
| 2 | 硬编码返回值 | ✓ 无 | 分类器为真实分支逻辑；探针字符串是测试输入非硬编码输出 |
| 3 | 幻觉 API | ✓ 无 | isinstance/strip/replace/split/startswith、Path.rglob/relative_to、unittest 断言族——全部真实存在且用法正确 |
| 4 | 未实现 TODO | ✓ 无 | 两处 hunk 区通读零 TODO/FIXME/占位符 |
| 5 | 过度实现 | ✓ 无 | 单点分类器 = F2 最小实现；常量表 2+2 项适度；reason 仅塑形诊断（未引入新配置面/新抽象层/新公开 API） |

---

## 发现列表汇总

| ID | 级别 | 位置 | 摘要 | 状态 |
|---|---|------|------|------|
| F1 | P3 | test L16652-16680（三探针同构） | rglob 零副作用断言捕获范围 = root 内新增；探针 escape 目标（root 外）的创建不可检测——注释意图声明超出断言捕获范围。安全性不受损：check 零写路径 + 四重冗余捕获 | 非阻塞讨论 |
| F2 | P3 | Developer 红相实录 | 「中性化分类器→3 FAIL」与该方案推演（预期 4 FAIL 含 distinguishable）不完全自洽；若中性化对象为 wrapper 则恰 3 FAIL——措辞与数字取一，历史动作不可复核。**方向性成立**：任一方案均证明回归套件对拒绝缺陷敏感（exit 1） | 非阻塞，标注未验证 |
| F3 | P3 | test L16732-16763 | 互斥测试仅对 traversal 条目锁定；absolute 条目无双发 issue 类缺陷的断言——if/else 结构当前保证互斥，触发需未来 refactor 破坏分支结构，风险极低 | 非阻塞讨论 |
| F4 | P3 | verify_workflow.py L6821-6824 | `..:x` 病态输入归 absolute 桶（`:` 先于 `..` 判定）——Developer「cosmetic、拒绝集合不变」属实（原实现同拒，R0 L30 证实）；detail 文本语义略糙 + absolute 类 detail 无测试锁定 | 非阻塞讨论 |

---

## Developer 声明逐项核验（零采信，静态可验部分全验）

| # | Developer 声明 | 核验结果 |
|---|---|---|
| 1 | 红相：中性化分类器 → 3 FAIL exit 1 → SHA256 字节级还原 → 5 PASS | ⚠ 历史动作不可复核。方向性经静态推演成立；「3 FAIL」数字与自述方案推演有分歧（F2/P3）；SHA256 还原声明未验证。还原质量的功能证据：当前代码逐行自洽正确 + Coordinator 独立抽测 5 passed（采信） |
| 2 | 全量 728→732+89 subtests 零回归；verify 五项 exit 0 | ⚠ 未独立复跑——采信自报 + Coordinator 抽测。静态旁证：+4 用例数吻合 |
| 3 | 消费方零更新（L16638 substring 断言未改保持绿） | ✅ 成立：42 → non-string → legacy 桶 → substring 命中——静态推演绿 |
| 4 | reason 只塑形诊断绝不放宽接受 | ✅ 成立：唯一拒绝判据 = `normalized is None`（L6880）；七分支与 R0 记录原 None 集一一对应 |

---

## 硬门槛裁决

| 门槛项 | 阈值 | 实际 | 判定 |
|--------|------|------|------|
| P0 阻塞数 | = 0 | **0** | ✓ |
| 五维度覆盖 | 100% | 5/5 逐项有结论 | ✓ |
| 每条发现带级别 | 100% | F1-F4 全带 P3 | ✓ |
| 设计一致性 | 已完成 | R0 F1/F2 逐字承载：F1 三探针与 R0 L55 逐字一致；F2 消息措辞与 R0 L45/L139 逐字一致；legacy substring 兼容策略保 L16638 绿；无扩界（R0 F3-F8 未顺手修）；DEC-173② 与 triage JSON/plan-tracker 一致；EVD-917 files 修正留痕与实际落点吻合 | ✓ |
| AI 专项 5 项 | 全部完成 | 5/5 逐项有结论 | ✓ |

---

## 未验证声明（事实依据红线）

1. **红相过程构成与 SHA256 字节级还原**——历史动作不可事后复核，哈希值未留存证据；方向性经静态推演成立。
2. **全量测试/verify 运行结果**——Reviewer 只读未独立复跑；采信 Developer 自报与 Coordinator 独立抽测。
3. **原 `_normalize_declared_skill_path` 逐字历史形态**——git 不可用；拒绝集合等价性结论基于 R0 报告 L30 分支清单（其 14/14 边界探针为 R0 独立验证记录）推演，非逐字 diff。
4. **来源报告路径偏差**——任务描述 `docs/reviews/review-FIX-272-CODE-R0.md` 不存在；实际文件 `.governance/review-FIX-272-CODE-R0.md`（内容完整，F1/F2 已比对）。

---

## 遗留项表（全部非阻塞）

| ID | 级别 | 建议处置 | 截止建议 |
|---|------|---------|---------|
| F1 | P3 | 注释措辞收敛（「零副作用」声明限定为 root 内）或接受现状 | 0.78.1 发布前裁决即可 |
| F2 | P3 | 无需行动——红相为 TDD 过程证据，最终态已由抽测+静态验证覆盖 | 无 |
| F3 | P3 | 可选：互斥测试增补 absolute 条目锁定 len==1 | 随缘 |
| F4 | P3 | 可选：探针增补 absolute detail 文本断言；`..:x` 归类维持现状 | 随缘 |

---

## 最终裁决

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——硬门槛 5/5 通过、P0=0、P1=0、P2=0；无未解决 BLOCKING finding。R0 F1/F2 逐字承载、拒绝集合等价性成立、消息拆分向后兼容（零消费方破坏）、四重断言实质有效。四条 P3 均为讨论级备注，不阻塞合并。

**范围合规声明**：零仓库写入、零命令执行、未修改任何被审文件、未与用户交互；全部结论引用实读行号/全仓 grep 结果/R0 报告原文；四项不可核验声明已逐条标注未验证。
