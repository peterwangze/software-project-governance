# FIX-397 Code Review — Round 0（④ 子项：风险计数口径对齐）

- **审查对象**: FIX-397④ bootstrap risk face 口径对齐（bootstrap_aggregate.py +98/−8 + test_bootstrap_risk_face.py 新建）
- **审查主体**: Code Reviewer Agent（只读：Read/Grep/Glob；未执行命令、未复跑 pytest——诚实声明见声称核验节）
- **轮次**: round 0（无前轮引用）
- **结论**: **APPROVED_WITH_NOTES ｜ unresolved_blockers=0**
- **日期**: 2026-09-27

## 审查结论

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ round 0（R0，无前轮引用）**

无 P0/P1 BLOCKING 发现；6 条发现全部为 P2/P3 非阻塞备注。按 code-review SKILL：APPROVED_WITH_NOTES 为通过终态，仅表示硬门槛通过，不替代测试/发布审查。

## 声称核验（事实红线声明）

- 「pytest -k bootstrap 125P 零失败」：**未复跑**（Reviewer 角色禁 Bash）。结构证据：两个 bootstrap 测试文件在位且可收集，新文件实读 **18 个 test 方法**（非声称的 17，见 F1）。数值 125 离线不可证实 → 标「未验证（非阻断，留 Coordinator/CI 复核）」。
- 「活体 risks.open=18==risk-log 机械非关闭 18」：运行未复跑；**口径已由审查者从 `.governance/risk-log.md` 逐行手工机械重导吻合**——非关闭 ID 全等清单（18）：RISK-024/026/027/036/039/044/047/048/050/052/053/054/055/056/057/058/059/060。修复前 exact-「打开」位置读恰为 4（036/039/050/060），与 docstring「4 vs 18」叙事自洽。
- 「manifest PASS」：未复跑；结构证据：新测试文件位于 manifest 目录级登记之下，与既有 test_bootstrap_aggregate.py 同为不需逐文件登记的测试资产——一致性方向成立。
- 「JSON 面纯加性（新 2 键、既有 4 键不变）」：**磁盘核实通过**——summary 面恰为既有 open/escalation_overdue/escalation_soon/overdue_ids + 新增 unknown_count/unknown_statuses；open 语义 4→18 为 DEC-256 charter 目的且模块 docstring（:25-28）与函数 docstring（:383-398）双处声明；既有消费方（_next_actions :787、format_text :968-970）无破坏性依赖。

## 5 维度结论表

| 维度 | 结论 | 依据摘要 |
|------|------|---------|
| 正确性 | PASS | `_resolve_risk_status`（:356-379）逐行审：positional-first、词表外才回退、恰一命中锚定、0/≥2→unknown、positional 已命中绝不覆写——与契约逐条吻合；活体漂移形态抽查 4/8 行全部正确锚定；边界发现 F2/F3/F4（均非阻塞） |
| 安全性 | PASS | 纯解析无注入面；无密钥硬编码；regex 无灾难回溯；只读零写、UTF-8 errors=replace 容错；未知行不静默吸收（fail-closed 达成） |
| 可维护性 | PASS | 词表常量成文（:336-343）与 DEC-256 一致；divergence 声明准确；模块纪律红线守住：无 engine import/subprocess/文件写，新增零 import |
| 性能 | PASS | 单遍 O(行×格)；锚定仅对 positional unknown 行触发；披露有界（cap 5、clip 40、overdue_ids cap 3）；8KB 硬钳在位 |
| 测试覆盖 | PASS（带备注） | 18 测试与实现分支映射完整；fixture 全临时目录自包含、today 注入断言内容化；缺口=短行跳过与空编号分支无钉（F2/F3 备注） |

## 发现列表

- **F1 [P2]**: 交付声称「17 测试」，磁盘实读 18 个 test 方法——方向为多非少（覆盖≥声称）；建议交付/证据记录修正为 18。
- **F2 [P2] bootstrap_aggregate.py:410-414**: 短行静默跳过向量（len(cells) <= width 即跳过，缺格短行不进 open 也不进 unknown 披露——等式 fail-open 残留）；活体无此形态；建议计数门降为 max(id_pos, status_pos) 或 skipped_count 披露。
- **F3 [P2] :337,:346-353**: closed 前缀 reopen 词序边界未钉（假想「关闭后重开」token 落 closed 静默消失）；现无此形态；建议补 closed 侧边界 pin 测试。
- **F4 [P3] :374-378**: 锚定扫描 prose 恰一误锚固有边界（机械规则不接受语义）；活体 8 漂移行核对无冲突；DEC-256⑤ 数据归位后自然消失——已接受边界。
- **F5 [P3] :436-442**: soon 含 overdue 重叠为 engine 既有口径忠实镜像（verify_workflow.py:10854-10901 + 既有断言对照确认），非本变更引入；建议注释固化。
- **F6 [P3] test :341-366 + :737**: E2E 走真实墙钟（_build_payload 未注入 today）；当前断言时钟无关设计成立；建议 fixture 处补 clock-free 注释。

## 硬门槛逐项

1. P0 阻塞=0：**PASS**（0 条）
2. 5 维度逐一结论：**PASS**（5/5）
3. 每条发现 P0~P3 标注：**PASS**（6/6：P2×3、P3×3）
4. 口径契约一致性（DEC-256 对照）：**PASS**（五点逐项——词表/降级计入 open+披露/divergence 双处声明/18 权威/锚定覆盖+不越权改数据面）
5. AI 代码专项 5 项：**全部完成**（mock 零命中/硬编码无（词表=领域契约成文）/幻觉 API 无（stdlib only）/TODO 零/过度实现无）

## 抽查记录（risk-log.md 行号实据；漂移 ≥3 行要求，实检 4+4）

漂移行（全宽 13 格、影响格缺失、状态左移至 index 7）：RISK-052（:44）/RISK-053（:45）/RISK-056（:48）/RISK-059（:51）——positional(8)=缓解文本→unknown→全行扫描恰一命中 cells[7]=「打开」→锚定 open ✓ ×4

对齐行对照组：RISK-024（:31 缓解中直读 open）/RISK-026（:33 降级→unknown→open+披露，DEC-256②）/RISK-051（:43 关闭〔原：打开〕前缀语义正确忽略后注）/RISK-060（:52 打开+截止「—」无虚构升级信号）✓ ×4

## 裁决

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ round 0** — F1~F3 三条 P2 建议随交付记录修正或留后续票（不阻塞终态）。

---

**Coordinator 注记（2026-09-27，非 Reviewer 文本）**：
1. F1 处置：EVD-1196 结构化事实中 `new_file: 17T` 勘正为 **18**（磁盘事实，覆盖≥声称方向）；随 FIX-397 终态 EVD 入账。
2. F2/F3/F5/F6 处置：登记为 FIX-397 收口备注（卫生批候选——与 DEC-256⑤ 数据归位同批）；F4 为已接受边界随 DEC-256⑤ 消解。
3. 「pytest 125P / manifest PASS」未复跑两项：Coordinator 于 commit 前复跑 `-k bootstrap` 定向验证补齐（Reviewer 边界外事项）。
