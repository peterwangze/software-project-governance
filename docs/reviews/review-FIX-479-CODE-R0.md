# Review — FIX-479 独立代码审查（CODE R0）

- **Task**: FIX-479 — Check 9 截止日误报：emoji 前缀终态归一（D1 第二轮）
- **Round**: R0（首轮）
- **Reviewer**: Code Reviewer（独立，未参与开发）
- **Date**: 2026-11-04
- **审查对象**: 工作树未提交 diff（`git diff`，HEAD=b3adf46）——2 文件 +208/−4：`skills/software-project-governance/infra/verify_workflow.py`（共享谓词块 + 两调用点）+ `skills/software-project-governance/infra/tests/test_verify_workflow.py`（Fix479Check9TerminalStatusNormalizationTests 6 用例）
- **Verdict**: **APPROVED_WITH_NOTES**
- **unresolved_blockers**: 0
- **分级计数**: P0=0 / P1=0 / P2=0 / P3=4

## 1. 变更摘要（Developer 声明 vs 实读 diff）

两处裸词形终态筛选 `status in ("已完成", "已终止")`（check_task_deadline Check 9 @L10935 前；check_protocol_compliance DRI 面 @L10511 前）收敛为单一共享谓词 `_status_is_terminal_cell`（L11238，常量 `_TERMINAL_CELL_DECORATIONS = ("⏳","🔄","📋","🆕","⏸")` @L11235）：终态 ⟺ 权威完成谓词 `_status_is_completed_cell`（L11170，完成语义唯一源——FIX-291 W-7 / FIX-393）对原格或剥前导装饰 emoji 后判真。实测 diff 与声明完全一致，无夹带（D-units：verify_workflow.py 恰 3 个 hunk=谓词块+两调用点；测试恰 1 个新类）。

## 2. 独立复跑证据（不采信自报，全部独立执行）

| # | 验证项 | 命令（cwd=仓库根） | 实测结果 |
|---|--------|--------------------|----------|
| 1 | Fix479 测试类 | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k Fix479Check9 -v` | **Ran 6 tests in 0.043s — OK**（6/6） |
| 2 | **红相真实性**（HEAD 引擎+新测试，隔离 worktree @%TEMP%，验后已移除） | `git worktree add <tmp> HEAD` → 复制新测试文件 → 同上 -k 运行 | **FAILED (failures=4, errors=1)**——与 Developer 自报红相 4F+1E 逐字吻合；traceback 实证宿主形状复现：`DEV-101（✅ 已完成）` 落入 overdue 集 |
| 3 | 全套件回归 | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py`（输出落盘后提取） | **Ran 1175 tests in 327.275s — OK（EXIT=0）**——与自报 1175 一致，零退化 |
| 4 | 本仓 quick 面 | `verify_workflow.py check-governance --summary-only --scope quick` | **5 issues**（FAILED 段=2,21,22,28s,30,30c,32,35,36）——与本会话修复前基线完全一致，Check 9 段 PASS，**零新增** |
| 5 | 旧词形残留 | grep `已终止`（6 处）+ grep `== "已完成"` 等变体（5 处） | 旧元组形状 **0 残留**；其余出现逐一定性见 §4（全部为不同消费面既有形态，非 overdue/DRI 同型） |

## 3. 谓词语义链独立分析（逐分支读码验证）

`_status_is_terminal_cell(cell)` = `_status_is_completed_cell(原格)` ∨ `_status_is_completed_cell(剥前导装饰后)`。关键分支实测定性：

| 状态格 | 判定路径 | 结果 | 依据 |
|--------|----------|------|------|
| `已完成`（裸） | "已完成" containment（L11197） | terminal ✓ | 旧词形兼容 |
| `已终止`（裸） | W-7 断言分支（L11165 词表含 已终止；cell 端点=断言；无 active 标记 → max>−1） | terminal ✓ | **旧词形兼容成立**（关键疑点已排除） |
| `✅ 已完成` / `✅ committed` / `✅ 完成` | ✅ 分支（L11208，无 veto 标记） | terminal ✓ | 宿主活体形状（假 overdue 根因消除） |
| `⏳ ✅ committed`（复合前缀） | 原格被 ✅ 分支 veto（含 ⏳）→ 剥前导 ⏳ 后 ✅ 分支判真 | terminal ✓ | 装饰≠状态断言，与 task_priority 既有完成语义对齐（FIX-462 型狗粮行） |
| `✅ 已终止` / `⏳ 已终止` | ✅ 分支 / 剥装饰+W-7 | terminal ✓ | 终止族全覆盖 |
| `🔄 进行中` / `📋 规划中` / `⏳ 待实施` / `未开始` / `进行中`（剥后） | 全分支不命中（veto 词表与完成词表均不命中） | **active ✓** | 真活跃仍 WARN——范围红线保持 |
| `⏳ 未完成` / `未完成` / `待完成` | 未完成/待完成 veto（L11195，先于一切） | **active ✓** | 假阴性防护就位 |
| `""` / None | `_status_clean_cell` 归空 → False | active ✓ | 空格不崩溃 |

剥装饰 while 循环每轮至少消费 1 字符——终止性证明成立；纯函数无共享状态，并发安全。overdue 语义本身（有 deadline 且非终态 → WARN）未被触碰，`test_genuine_active_rows_still_overdue`（含 future-date 不入 overdue、total_active 计数）+ 红相对照双向钉死。

**单源合规（P5）**：两调用点均 `if _status_is_terminal_cell(status):`（grep 恰 2 处，测试断言钉护）；完成语义未复制（委托 L11170 唯一源）；新词表仅装饰 emoji 集（状态断言词零新增）。测试夹具列映射（status=parts[10]、priority=parts[11]、计划完成=parts[13]、owner=parts[7]）与两检查的解析注释及 FIX-480 列契约严格一致。

## 4. 残留与不同面消费点枚举（全部定性为非本票范围）

- L8105/L8114/L11646：`_normalize_task_status`/统计面 4 桶枚举（0.54 表统计展示）——emoji 格不入桶为既有展示缺口，非 overdue/DRI 判定；
- L10000：数据源热面 `dep.is_completed() or …=="已完成"`——`is_completed()`（task_priority，✅ 感知）已覆盖 emoji 形态，OR 为冗余保险；
- L10005：归档条目 dict 状态等值判定——归档自身规范化形态；
- L10774：tier 审计面等值计数——漏计方向=更严（保守）；
- L15615：P0 证据面等值判定——同保守方向；
- L18752 `_plan_row_is_inactive`：G10 门禁整行包含式 inactive 词表（含英文）——不同语义面；
- L10363 `parse_completed_task_ids`：整行包含式完成 ID 收集器——FIX-480 域邻面。

以上均为既有形态，本票未恶化散布（实际消除一处散布）；全模块收敛为未来候选（见 P3-2）。

## 5. AI 代码专项 5 项

1. **mock 残留**：无——测试用 `patch.object(vw, "SAMPLE_PATH", sp)` 上下文管理器 + `tempfile.TemporaryDirectory`，退出即还原；
2. **硬编码返回值**：无——谓词为纯逻辑，测试断言行为非桩值；
3. **幻觉 API**：无——`_status_clean_cell`（L11027）/`_status_is_completed_cell`（L11170）/`_status_is_terminal_cell`（L11238）/W-7 辅助（L11064-11137）/writer 链（L11150-11167，`task_row_update._STATE_MARKER_CHAIN` 实存）逐一读码确认；
4. **未实现 TODO**：diff 内零 TODO/FIXME/pass 占位；
5. **过度实现**：无——剥装饰 run + 5 emoji 常量由活体复合前缀形状（`⏳ ✅ committed`）正当化，谓词 20 行最小闭合。

## 6. 五维度结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | **PASS** | §3 逐分支验证；边界（空格/None/复合前缀/veto）全覆盖；循环终止性成立 |
| 安全性 | **PASS** | 纯文本谓词，无注入面、无凭据、无外部输入信任变化 |
| 可维护性 | **PASS** | 单源达成；docstring 语义-先例-行号完整；命名达意（P3-2 既有散布为存量） |
| 性能 | **PASS** | 每行 O(1) 纯计算零 IO；quick 墙钟与基线无差 |
| 测试覆盖 | **PASS** | 红绿双向真实（§2#2 独立复现红相）；两调用点+向后兼容+复合前缀+active 守卫+计数面；P3-4 一处可选增强 |

**设计一致性**：FIX-291 W-7（混合链保守性保持——剥装饰仅作用于前导显示缀，不触碰 trailing-state 规则）、FIX-393（writer-committed 链零改动）、FIX-292（无第二语义源）、FIX-480（列契约一致）——全部符合。

## 7. 分级发现（全部非阻塞）

- **P3-1** [verify_workflow.py:11217] 完成谓词末端回退正则 `完成\s*(?:[（(]|$)` 会把假想的裸格「部分完成」判为完成 → Check 9 将跳过其 overdue（低报方向）。活体词表中未见该形状；为既有完成语义被 Check 9 新消费的边界，非本票引入。建议：该形状若在任一宿主活体出现，再扩 L11195 veto 词表（「部分」前缀）。
- **P3-2** [模块级] verify_workflow.py 内并存多面专属完成/非活跃词表（§4 枚举 7 处）——存量散布，本票已按 P5 收敛 in-scope 两点；全模块收敛（stats 枚举/tier/P0/数据源/G10 面）为未来独立候选票。
- **P3-3** [tests/test_verify_workflow.py] 工作树副本含 CRLF（git 提交时按 .gitattributes 归一 LF，warning 仅提示）；提交后无影响，知悉即可。
- **P3-4** [tests] 粗体/反引号装饰终态形状（如 `**✅ 已完成**`）未直接测试——`_status_clean_cell` 已处理，可选补一行断言。

## 8. 硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞数 = 0 | **PASS**（0） |
| 5 维度全覆盖 | **PASS**（§6 逐项） |
| 每条发现带级别 | **PASS**（P3×4） |
| 设计一致性检查完成 | **PASS**（§6 末段） |
| AI 专项 5 项完成 | **PASS**（§5） |

## 9. 审查边界（诚实披露）

- 本审查范围=仓内 diff 与仓内复跑；**宿主 python_game 复跑 overdue 35→0 的终验收未在本审查内执行**（Coordinator 承担，Layer1 只读直跑口径）。宿主基线 35（2026-11-04 Coordinator 探针，样本 DEV-001/ARC-001/ARC-002/SYS-001/SYS-010 全 `✅ 已完成`）已由本审查以红相在 HEAD 引擎独立复现同形状（§2#2），修复方向与该基线严格对应。
- 全套件/quick 为本仓（dogfood）面；宿主面其余 FAIL（Check 18c 缺包 DEV-001/DEV-002/ARC-001 等=F5 数据债）不属本票。

## 10. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——修复真实（红相独立复现）、语义正确（三分支兼容+双向守卫）、单源合规（P5）、全套件零退化（1175 OK）、quick 零新增。4 项 P3 均为存量/可选增强，不阻塞合并。建议 Coordinator 继续：宿主 Layer1 复跑 35→0 终验收 → commit（单 commit 承载，P-v1 D4）。
