# review-FIX-480-CODE-R0 — 独立代码审查报告（Round 0）

**结论：NEEDS_CHANGE**（P1 × 1，unresolved_blockers = 1）——修复后请发起 R1 复审（复审必达 T1）。

**审查人**: Code Reviewer（subagent 5445171f-55ed-4fda-820c-faf0b94316ea）| **日期**: 2026-11-03 | **对象**: FIX-480 工作树未提交改动 12 文件（+597/−79）

## 审查对象与复证基线（全部亲跑，非转述）

- 12 文件（+597/−79）：锁面 7 + 配套 5；fixture 表头与 `git show v0.54.1:core/templates/plan-tracker.md` **逐字比对一致**（HEADER_MATCH_VERBATIM 实证）
- 亲跑复证全绿：test_task_priority **191/191**、Fix480UpgradePathTaskTableTests **9/9**（含真 bash 驱动真 hook 源 4 用例）、test_hooks **70/70**（新 pattern 对旧用例零回归）、test_registry **77/77**（R6 211→212 为现测真值——「bookkeeping catch-up」声称成立）、test_archguard_ratchet **38/38**（R4 1384 / anchor 28418 锚过）
- 性能复测：60 行 20 列表 **0.79ms**（声称 0.83ms 成立）；畸形输入（短行/500 字长 cell/空文档）不崩不吞错；本仓紧凑基线 rows=69/**completed=54**（与 bootstrap 热数据 54 一致——见 P3-2）

## 发现列表

### P1-1（正确性——NEEDS_CHANGE 依据）：任务ID（FIX-287②）变体 dispatch 缺口——声称支持但实际错位解析

- **位置**：`infra/task_priority.py` — 表头检测分支（`clean_cells[0] in ("ID", "任务ID")`）与 `_build_column_index`（L1283 只认 `clean == "ID"`）不一致；dispatch `col_index.get("id") == 0`（L1426）对任务ID 表永不触发
- **实证**（亲跑）：任务ID 首列 20 列表 → `status='里程碑备注'`（备注列被读作状态——Check 36 症状在该变体复发）、`target_version='某目标'`（目标列被读作版本）、`_build_column_index(['任务ID','状态','优先级'])` 返回 `keys=['priority','status']` **无 id 键**
- **依据**：docstring 明文声称「plus the 任务ID-led legacy variant」、表头检测明文收它进 shape 2——实现与自身声明矛盾；零测试覆盖（test_task_priority/test_verify_workflow 新增均无任务ID 用例）；FIX-287② 是在案历史真实形态，升级路径宿主可能遇到
- **修复建议**（一行 + 一测）：`_build_column_index` 增 `clean == "任务ID"` → `idx["id"] = i` 分支；补任务ID 变体红绿测试（断言 status/按 header 语义而非备注列）

### P3-1（披露）：commit-msg shape (b) 测试落位在 test_verify_workflow.Fix480UpgradePathTaskTableTests 而非 test_hooks.py 既有 hook 族——真源提取+真 bash 驱动已满足 FIX-282 绑定要求，纯组织性注记，不要求移动

### P3-2（披露）：本仓 Check 1 完成计数行为变化 69→54——双完成词形收敛后，15 个活跃行（行内含 ✅ 引用文本）不再被「最后非空 cell」策略误判完成；54 与 TPA/bootstrap 权威口径一致（正确方向），但属 Check 1 输出可见变化，建议 commit message / evidence 披露一句

### P3-3（披露）：`_parse_id_first_task_row` 的 status 严格读 header 列、无裸词扫描 fallback——行宽截断时 status=""（fail-closed 合理），与紧凑路径「最后非空 cell」策略形态不同；语义差异已在 docstring 说明，知悉即可

## 硬门槛逐项裁决（派发 7 项）

1. **红绿真实性 ✓**——fixture 表头 git tag 逐字实证；三症状（0 行/状态读备注/P9）均有 pre-fix 红面断言锁定
2. **单一语义源 ✓**——热面私有解析（-35 行 profile 列索引通道）删除，收敛 `parse_task_dependencies`；demand_source 共享 helper 单词汇表；Check 36 原生经单源（risk_domain:356）自动获益；commit-msg 正则为 bash 结构护栏（无 import 能力的机制约束），双形态等价性由测试锁定——非语义漂移
3. **fail-closed ✓**——未识别形状 WARN NOT_RUN 三测 + 空表/Gate 表/REQ 矩阵/归档指针不误警亲证；解析异常 surface 不隐藏
4. **回归与 regen 合规 ✓**——全套绿；台账锚（1384/28418/212）与 regen 一致；FROZEN 211→212 经 test_registry 绿复证为真值
5. **超锁面 5 文件 ✓**——change_triage.py=验收⑥实际定义面（parse_version_chain）；regen×2+台账测试×2=archguard 纪律指定动作（Coordinator 已裁决接受）
6. **性能与质量预算 ✓**——0.79ms 复证；quality_budget NOT_RUN_YET 合法（规划中口径，交付后由 evidence 链更新）
7. **安全畸形输入 ✓**——缺列/超长行/空表不崩不吞错

## 五维度结论

正确性：P1-1 外全部通过｜安全性：通过（纯文本解析，无注入/敏感面）｜可维护性：优秀（单源收敛净 -35 私有解析，注释含错位对照）｜性能：通过（0.79ms/60 行线性）｜测试覆盖：核心/边界/错误路径全（缺口即 P1-1 变体）｜AI 专项五项：mock 残留无/硬编码无/幻觉 API 无/TODO 无/过度实现无 ✓

## 裁决

P0=0；**P1=1（任务ID 变体 dispatch 缺口）**→ **NEEDS_CHANGE**。修复面极小（一行映射 + 一测），退回 Developer 修复后请重派 R1 复审（注入本报告路径）。P3 × 3 不阻塞、知悉级。
