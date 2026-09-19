# Code Review 报告 — FIX-356（round 0）

- **Task**: FIX-356 — governance_cost.py workspace 过滤失效修复（session 事件无 cwd 时自会话目录路径编码名回退推导）
- **优先级**: P1 · **审查类型**: 代码审查（独立，round 0）· **日期**: 2026-09-19
- **审查者**: Code Reviewer Agent（独立复验，未采信 Developer 输出充当自身验证）
- **审查对象**: 工作树未提交 diff（无 commit）——
  `skills/software-project-governance/infra/governance_cost.py`（+37/−1）、
  `skills/software-project-governance/infra/tests/test_governance_cost.py`（+107）
- **审查基准**: `.governance/execution-packets.json` `packets["FIX-356"]`（done_definition / quality_budget / allowed_change_scope / vertical_slice.scope_guard）
- **诊断事实链**: RISK-055 验收 0/344 命中死循环；EVD-1088（session 事件 `data={}`，344/344）；RISK-050 dsh 上游耦合族首例实证

---

## 总结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**

P0=0，P1=0，P2=1（非阻塞建议），P3=3（含 1 条 Coordinator 侧观察项）。硬门槛全部通过：5 维度逐一有结论、每条发现带级别、AI 专项 5 项逐一有结论、设计一致性已核对（纯增量回退分支，CLI/schema/阈值/子串匹配语义零改动，与 packet non_goals 及 scope_guard 逐项吻合）。

---

## 一、5 维度审查结论

### 1. 正确性 — PASS

- **回退推导算法**（governance_cost.py L625-651）：`Path(rel_path).parents` 自近及远遍历 → 最近编码祖先优先（test L625 区域 `test_fallback_prefers_the_nearest_encoded_ancestor` 实证）；`len(name) > 4` 正确排除 `----`（空内芯）退化形态；`name[2:-2]` 精确剥壳；无编码祖先/bare 文件返回 `""`（`Path("f").parents` 为 `[Path('.')]`，`name==""` 不命中）。
- **event-cwd-wins 守卫**（L680-685）：`parse_session` L380/L396 保证 `cwd` 恒为 `str`（`data.get("cwd") or ""`），`if not cwd` 守卫无 None 风险、判空完备；事件 cwd 在场时回退永不触发（`test_legacy_cwd_shape_still_wins_and_matches` 双向断言：按 cwd 过滤命中 + 按目录 token 过滤不命中）。
- **rel_path 提升复用**（L678/L697）：`rel_path = path.relative_to(root)` 提前计算，`"file": rel_path.as_posix()` 与原 `path.relative_to(root).as_posix()` 等值替换，无行为差异。
- **过滤语义**：`if workspace is not None and workspace not in cwd`（L686）逐字符未变——`--workspace` 子串语义保持。
- **红相实证**（见第三节）：HEAD 旧模块 `hasattr(_cwd_fallback_from_session_path)==False`，同一 `data={}` fixture 旧代码 0 命中、新代码 1 命中——缺陷真实存在且被修复击杀。

### 2. 安全性 — PASS

- 回退函数为纯字符串操作：只读 `parent.name`，返回值仅为过滤匹配 token；全库 grep 证实 `cwd` 值仅流向 L686 子串过滤与 L1020 text 报告显示切分，**从未进入任何 Path 构造或文件系统调用**——无路径重构/遍历面。
- 无网络、无写入、无外部输入执行；`rel_path` 相对 sessions root，祖先遍历止于根，不借语料外目录名。
- 测试断言 token 非 `--` 包裹、不含 `/` `\` `:`（`test_fallback_token_is_a_match_token_not_a_path`）——non-path 契约有看护。

### 3. 可维护性 — PASS

- dsh 内部命名约定（`--<workspace-id>--` 包裹、分隔符归一为 `-`）**单点编码**于一个可独立单测的纯函数，docstring 明示 RISK-050 耦合面与 rel_path 语义（packet quality_budget.maintainability 代码注释项满足；risk-log RISK-050 族条目在案 L44）。
- 接线点单一（scan_sessions 一处 4 行），注释与代码行为一致；不与解析主循环耦合——符合 non_goals「不重构其余解析面」。
- 无重复逻辑、函数远小于 50 行。

### 4. 性能 — PASS

- 回退为每次会话文件 O(深度) 的 O(1) 字符串检查，无逐事件重扫描。
- 实测全语料（346 文件）扫描 wall time 5.3s < 10s 预算（基线 4.8s/298 文件，EVD-1073——增量与文件数增长相称）。

### 5. 测试覆盖 — PASS

- 7 新用例 = 4 单元（解包正确值 / 无编码祖先+bare 文件返回空 / 最近祖先优先 / token 非 path 形状）+ 3 集成（真实形状过滤命中并断言 cwd 字段 / 负例不过匹配（他工作区 + 无编码祖先 plain 目录）/ legacy cwd 优先不被覆盖）。
- **Fixture 形状还原真实 v3**：`_ev("session", 1000)` 产出 `data={}`（EVD-1088 真实形状）；`_write_session` 紧凑 JSON 序列化对齐 harness 字节形状（envelope 标记真实命中快速路径）；真实 zstd 压缩。
- zstandard 0.25.0 在场，pytest 输出全 dots 零 skip——58 用例全部真实执行（58 = 基线 51 + 新增 7，与申报一致）。
- 红相存在性：**实证确认**（见第三节）——6/7 用例修复前必 FAIL；`test_legacy_cwd_shape_still_wins_and_matches` 修复前即绿，属防过度实现回归护栏（非红相用例，合理设计）。
- 突变击杀力：遍历顺序反转→最近祖先用例杀；剥壳缺失→non-path 用例杀；守卫失效（回退覆盖事件 cwd）→legacy 用例双向断言杀；过匹配（任意目录/仅前缀命中）→负例用例杀；`>=4` 突变与 `>4` 行为不可区分（`----` 剥壳结果为 `""`，与不命中等价）——无存活可观测突变。

---

## 二、Findings

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-1 | **P2**（非阻塞建议） | governance_cost.py CALIBRATION（L736）vs L680-685 | `sessions[].cwd` 语义现为双源：事件 cwd（旧形状）或目录推导 token（新回退）。该 provenance 未入 `CALIBRATION` 披露面——本工具其余口径（other_residual_ms、user_wait 等）均机器可读自述语义；JSON 消费者（infra 外无消费点，grep 证实）与 RISK-052 跨时点 diff 口径（无 `--workspace` 时 totals 不受 cwd 影响，可比性保持）均不受阻，故不阻塞。 | 后续小改：CALIBRATION 增一行披露 cwd 双源语义（如 `"cwd": "event cwd when present; else directory-derived workspace token (RISK-050/FIX-356)"`）。可随下个版本顺带，不构成本轮返工项。 |
| F-2 | P3 | governance_cost.py L647-650 | `--<id>--` 包裹形态对内芯含 `--` 的工作区 id 有歧义（dsh 编码有损，路径含 `--` 目录名时不可反解歧义）。子串匹配语义下仅病态命名可能过/欠匹配。 | 无需行动——约定本身属 dsh 内部面，函数已作为单点编码并 docstring 明示；若 dsh 未来给出结构化 workspace 字段，在此单点替换即可。 |
| F-3 | P3 | governance_cost.py L649 | `len(name) > 4` 边界：恰排除 `----`；`--x--`（5 字符）为最小合法形态。行为正确，测试间接覆盖（bare/无编码祖先），无直接 `----` 用例。 | 可选：补一个 `----` 目录名用例固化边界。非必需（行为与不命中等价）。 |
| F-4 | P3（观察项，Coordinator 侧） | .governance/risk-log.md L44 | RISK-050 族条目在案（打开、Coordinator 所有）；packet maintainability 要求的「risk-log 各一行」是否需要为 FIX-356 追加实例注记，属治理记录维护职责，超出本代码审查范围。 | Coordinator 收尾时按 evidence/治理流程自行核对，不影响代码结论。 |

**P0 计数 = 0，P1 计数 = 0。**

---

## 三、红相实证（独立复验，非引用 Developer 输出）

方法：`git show HEAD:...governance_cost.py` 在内存重建修复前旧模块（零仓库写入），对同一真实形状 fixture（`data={}` session 事件 + `--D-AI-agent-claude-coding-project_management_workflow--` 目录 + zstd 紧凑 JSON）分别以旧/新代码执行 `scan_sessions(tmp, workspace="project_management_workflow")`：

```text
OLD module has _cwd_fallback_from_session_path: False   ← 4 个单元用例修复前 AttributeError
OLD scan_sessions hit: 0 sessions (pre-fix behavior)     ← 集成用例修复前 FAIL（缺陷复现）
NEW scan_sessions hit: 1 sessions, cwd = D-AI-agent-claude-coding-project_management_workflow
RED-STATE (integration tests fail pre-fix): CONFIRMED
```

## 四、AI 代码专项 5 项

| 检查项 | 结论 | 依据 |
|--------|------|------|
| mock 残留 | 无 | 新增 7 用例不使用 mock；既有 `unittest.mock` import 为存量 |
| 硬编码返回值 | 无 | 推导自输入 `rel_path`，无条件捷径 |
| 幻觉 API | 无 | `Path.parents`/`.name`/`startswith`/`endswith` 均真实 stdlib，58 用例全绿佐证 |
| 未实现 TODO | 无 | diff 无 TODO/占位 |
| 过度实现 | 无 | 单一函数 + 单点接线；CLI/schema/阈值/参数面零改动（add_arguments L1027-1048 未触碰） |

## 五、向后兼容断言核对（packet non_goals）

- CLI/schema/阈值/参数面：diff 零改动 ✓（report dict 键集合不变，REPORT_SCHEMA 不变，TTFA 阈值常量不变）
- `--workspace` 子串语义：L686 过滤表达式逐字符未变 ✓
- 事件含 cwd 旧形状：守卫保证行为不变，专项用例双向断言 ✓
- 只读扫描语义：无新增写/网络面 ✓

## 六、独立复验结果表

| # | 命令 | exit code | 输出摘要 |
|---|------|-----------|---------|
| 1 | `python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q -p no:cacheprovider` | 0 | **58 passed in 0.17s**，零 skip（zstandard 0.25.0 在场，全部真实执行）；与申报 58 passed 一致 |
| 2 | `python skills/software-project-governance/infra/verify_workflow.py`（全量） | 0 | `== Verification Result: PASSED ==`（全部子命令）；与申报一致 |
| 3 | `... verify_workflow.py check-cross-references` | 0 | PASS——78 文件 / 711 引用，无悬挂/废弃路径/循环引用 |
| 4 | `... verify_workflow.py check-manifest-consistency` | 0 | PASS——canonical 776 / actual 876 一致 |
| 5 | 红相实证（`git show HEAD:` 内存重建旧模块 + 同 fixture 新旧对照） | 0 | OLD 无函数 + 0 命中；NEW 1 命中 + 正确 token → CONFIRMED |
| 6 | `... verify_workflow.py governance-cost-report --sessions-root C:/Users/peter/.dsh/sessions --workspace project_management_workflow --ttfa-acceptance --format text`（真实语料，只读，R1(c) 授权） | 0 | 346 files parsed / failed 0；**156 sessions / 485 turns / 22 TTFA**（0 → 非零，修复生效）；wall 5.3s；RISK-055 verdict=FAIL（p50 4m39s > 25s）——真实测量结论，非本修复缺陷 |

**与 Developer 申报的差异说明**：申报 155 sessions/483 turns/344 files，复验 156/485/346——sessions 根为活体语料（复验输出 paired rows 中含本会话链自身的新 session 文件），2 文件增量为复验窗口期新会话写入，方向一致、22 TTFA 一致，非缺陷。

## 七、真实环境命令逐条上报（R4）

授权链：用户 2026-09-19 经 ask_user_question 逐项授权该验收命令（M7.7 R1(c)）；隔离方式：命令为纯只读扫描（无备份必要，满足三选一的授权项）。

| 命令 | 时间 | exit code | 影响路径 | 写入 |
|------|------|-----------|---------|------|
| `python skills/software-project-governance/infra/verify_workflow.py governance-cost-report --sessions-root C:/Users/peter/.dsh/sessions --workspace project_management_workflow --ttfa-acceptance --format text` | 2026-09-19 11:18:38–11:18:44（5.6s） | 0 | 只读扫描 `C:\Users\peter\.dsh\sessions`（346 个 `session.v3.jsonl.zstd` 读取） | 无（stdout 输出） |

其余命令（pytest / verify_workflow 检查 / git diff / git show）均限于仓库工作区与 pytest 标准临时目录夹具，不触及用户 HOME 配置目录；全程未对 `$HOME` 下任何配置目录执行删除/清空/重建/移动。

## 八、范围纪律

`git status --porcelain`：修改恰为 packet `allowed_change_scope` 内 2 文件；无顺带改。（工作树另有 1 个未跟踪文件 `docs/reviews/review-REL-080-RELEASE-R6.md`，属前序任务产物，非本 diff 一部分。）

## 九、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞数 = 0 | ✅（P0=0，P1=0） |
| 5 维度全覆盖 = 100% | ✅（第一节逐项有结论） |
| 每条发现带级别 = 100% | ✅（F-1~F-4 均带 P2/P3） |
| 设计一致性检查 | ✅（与 packet non_goals/scope_guard/rollback_plan 逐项吻合——纯增量、可单 commit revert） |
| AI 专项 5 项 | ✅（第四节逐一有结论） |
| 独立复验 1~3 项命令真实执行 | ✅（第六节，exit code + 输出摘要） |
| 报告落盘 docs/reviews/ | ✅（本文件） |

**结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**——可合并；F-1 CALIBRATION 披露行建议随下个版本顺带处理。
