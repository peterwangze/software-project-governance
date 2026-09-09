# Review: FIX-296 — EVD-959 CLI footgun：execution-packet --task X --write 过滤仅影响 stdout（CODE, Round R0）

- **Task**: FIX-296 — EVD-959 CLI footgun 修复：`execution-packet --task X --write` 静默清除未选包 → 过滤仅影响 stdout 预览，write 面保持全量（P2，0.79.0）
- **Reviewer**: code-reviewer（独立 R0；未参与实现）
- **日期**: 2026-09-09
- **审查对象**: 未提交工作树相对 HEAD（`fc1b739`，实测一致）的两文件变更（`git diff --stat`：+105/−4）：
  - `skills/software-project-governance/infra/verify_workflow.py`（`cmd_execution_packet` L13854-13885：+14/−4）
  - `skills/software-project-governance/infra/tests/test_verify_workflow.py`（`ExecutionPacketTests` +91：L11255-11343 三个新测试）
- **规格来源（已读）**: `.governance/change-triage/FIX-296.json`；`.governance/evidence-log.md` EVD-959（活体事故：`--task FIX-292 --write` 后 14 包被清）
- **工具边界**: 只读审查。复跑命令均为只读验证（测试、check-*、进程内探针、隔离 temp 宿主项目的 CLI A/B）；A/B 基线经 `git archive HEAD` 导出到系统 temp（未用 `git stash`/`git worktree`，未触碰现有工作树与 `.git`）；本报告为 Reviewer 唯一写入物（任务书指定路径）。真实 `.governance/execution-packets.json` 全程零写入。

---

## 1. 事实依据（全部为本审查独立复跑，2026-09-09）

| # | 验证项 | 命令/方法 | 结果 |
|---|--------|-----------|------|
| F1 | 类级测试 | `python -m unittest ...test_verify_workflow.ExecutionPacketTests -v`（仓库根） | **Ran 9 tests, OK**（既有 6 + 新增 3） |
| F2 | TDD 红独立复现 | temp 导出 HEAD（`git archive HEAD skills`）+ 覆盖新测试文件，运行同类 | **FAILED (failures=1)**——恰为新核心测试 `test_execution_packet_task_filter_with_write_keeps_full_set`，L11285 `AssertionError: Items in the second set but not the first: 'FIX-086'`（EVD-959 数据丢失形态在 HEAD 代码上复现）；另两个钉子测试在 HEAD 上 ok（钉的是既有行为，符合其定位） |
| F3 | 全量回归（工作树） | `python -m unittest ...test_verify_workflow`（仓库根） | **Ran 798 tests, failures=1**——`LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`（`AssertionError: 0 != 1`） |
| F4 | 全量回归（HEAD 基线 A/B） | temp HEAD 导出（仅 skills/ 子树）旧测试 vs 新测试并行全量 | 基线 **795 ran, 18F+36E**；HEAD+新测试 **798 ran, 19F+36E**——**增量失败恰为 1 = 新核心红测试，其余逐项一致**；`test_claim_command_emits_complete_pass_report` 在全部三个环境（工作树/temp HEAD+新/temp HEAD 基线）均同一失败 → 环境敏感例定性成立、与本改动无关。**诚实披露**：temp 两轮的大批 F/E 为我只导出 `skills/` 子树的方法学伪影（缺 docs/README/commands/package.json 等，失败信息均指向 missing files），非 HEAD 属性 |
| F5 | 三 gate | `check-manifest-consistency` / `check-cross-references` / `check-locks` | **PASS（667 文件一致）/ PASS（无环）/ PASS**（Active tasks: 2, File locks: 2 = 本审查会话持有的 FIX-296 锁） |
| F6 | check-governance（工作树代码） | `check-governance --level strict` | **共 38 issues**（全清单留存：18 系 6 条全为 FIX-281 占位态〔EVD-959 恢复后既有〕；Check 17 WARN EVD-463 历史项；Check 29 M5.4b×1；Check 30×7；30c×2；31×2；**Check 34 S1×4（FEAT-011/FIX-297/FIX-294/FIX-295）**；36×19；39×3——无一条提及本改动两文件或 execution-packet 写行为） |
| F7 | +1 漂移归因（代码无关性） | temp 完整 HEAD 树 + `--project-root` 指向真实 `.governance`：不带/带 `--product-gates` 两轮 | 无产品门 36（Check 31 等 2 条 FAIL 被 FIX-270 root-divergence SKIP——temp 伪影）；**带产品门 = 38，与工作树总数一致**；逐行 diff 仅剩无 `.git` 环境伪影（identity `ROOT_SOURCE_UNAVAILABLE`、hooks_drift×3、advisory 扫描路径域差异）→ **代码改动零 issue 漂移** |
| F8 | +1 漂移归因（数据态定性） | ① 纯函数判别：`check_m5_runtime_triggers` 注入全语料 vs 剔除 EVD-966 行语料；② 逐 issue 族核对；③ 跨会话算术链 | ① M5.4b WARN **两侧均存在**（1 warning each）→ 该 WARN 早于 EVD-966 写入，排除候选；② 其余各族（17/18x/30/30c/31/36/39）全为历史稳定项；③ 链条自洽：38（FIX-294 收尾，EVD-965）→ 39（FIX-295 会话初 = +S1 FIX-294）→ 37（FIX-295 修复 −2）→ **38（现在 = +S1 FIX-295/EVD-966）**。**裁定：+1 = Check 34 `[S1] FIX-295 (evidence EVD-966, 2026-09-09) has no recommendation-snapshot row`**——与 FEAT-011/FIX-297/FIX-294 完全同模（同日完成、未补 RECO 快照行的产品代码任务在下一会话被 Check 34 计数），纯治理运行时数据态漂移，无一指向本改动 |
| F9 | 写入点唯一性（验收 1） | 全仓 grep `EXECUTION_PACKET_PATH`（16 处）+ 写调用模式 grep `execution-packets.json.*(write_text\|write(\|open()`（全仓） | 生产代码唯一写入点 = **verify_workflow.py L13873 `write_text`**（L13872 mkdir 为其父目录保障）；其余引用为定义/重指派（L137/203/218）、读取（L12690）、打印（L13882）、测试 patch；字符串级唯一命中 = `tests/test_triage_write_guard.py:599`（temp fixture 写入，非生产）；`release/verify_rel063_evidence.py:1907` 为注释；FEAT-011 `governance-write-guard` 只读校验不写 → **过滤面落盘路径在代码层不再存在** ✓ |
| F10 | existing-merge 契约（验收 1） | 通读 `generate_execution_packets`（L13800-13815）+ 新测试断言 | `base.update(packet)` 既有字段覆盖占位、`task_id/priority/status` 回钉 plan-tracker——**函数零改动**；HEAD 的中毒步骤正是 `payload["packets"] = selected`（过滤面突变 payload 后落盘），新代码 selection 与 payload 解耦；测试断言 FIX-086 填充 goal 在 `--task FIX-084 --write` 后存活（我复跑绿，F1/F2 佐证） ✓ |
| F11 | CLI 级字节 A/B（验收 2） | 隔离 temp 宿主项目（2 活跃任务 FIX-084/FIX-086）× 4 调用形态 × HEAD/工作树两套代码；stdout 与落盘文件按 path+`generated_at` 归一化比对 | ① 无参 preview：stdout **归一化后逐字节一致**（15005B 全量 JSON），双侧零落盘 ✓；② 全量 `--write`：**落盘文件归一化后逐字节一致**（15005B），stdout 仅 temp 目录名两字符之差（消息本体一致 `wrote 2 execution packet(s)`）✓；③ `--task FIX-084` 预览：stdout 归一化后一致（7518B = 仅 FIX-084），双侧零落盘 ✓；④ `--task FIX-084 --write`：**工作树**落盘 {FIX-084, FIX-086} 全量 + OK 行附注 `(--task affects stdout preview only; file written in full: FIX-084)`；**HEAD** 落盘仅 {FIX-084}、`wrote 1`——EVD-959 在 CLI 层复现且修复被实证 ✓ |
| F12 | OK 行附注措辞 | F11 stdout 实录 | ` (--task affects stdout preview only; file written in full: FIX-084)` 与任务书规格一致；全量 write 路径 note=""（不打印）✓ |
| F13 | argparse 语义 | 通读 L23345-23348 | `--task` `action="append"`（None 或非空列表，可重复）；`--write` store_true——`set(args.task)` 去重过滤、`', '.join(args.task)` 原序拼接附注，与实现假设一致 |

**未验证项（红线标注）**：
- Developer 红相消息原文 `'FIX-086' missing`：历史时点声明；我复现的规范消息为 `Items in the second set but not the first:\n'FIX-086'`（同一断言 L11285、同一语义）——判定为转述差异，非事实冲突。
- 「基线 37」测量时点本身：历史数据态已不可重放（EVD-966 已写入）；归因经 F8 三重旁证（消除法 + 判别实验 + 算术链）建立，非直接重放。
- temp 部分导出环境（F4）的 36 errors 与部分 failures：我的方法学伪影，已在 F4 披露，不作为 HEAD 属性证据使用。

---

## 2. 五维度逐项结论

### 维度 1：正确性 — 通过

逐行实读 diff（+14/−4）与调用链对照：

- **过滤面落盘路径消除（验收 1）✓**：HEAD 的缺陷根 = `payload["packets"] = selected` 在 `if args.write:` 之前突变 payload（EVD-959 根因"过滤发生在 write 之前，无保护"）。新代码 `selected` 仅作为独立 dict 构建（L13861-13867），payload 全程不突变；write 分支落盘完整 payload（L13873-13876）。写入点唯一性经 F9 全仓双路 grep 独立证实。
- **stdout 预览语义（验收 2）✓**：无 `--task` → `preview = payload`（全量，与 HEAD 打印面一致，F11① 字节实证）；有 `--task` → `{**payload, "packets": selected}` 浅拷贝替换 packets 键——JSON 输出与 HEAD 的突变式打印**语义等价、字节等价**（F11③），且不再污染 payload（正确性改善）。
- **全量 write 字节级零变化（验收 2）✓**：`note = ""`（`selected is None` 时）→ OK 行与 HEAD 逐字节一致（F11② stdout 实证）；落盘 `json.dumps(payload, ensure_ascii=False, indent=2) + "\n"` 未动，文件归一化（仅 `generated_at` 时间戳）后逐字节一致；第三个钉子测试用**精确串等值** `assertEqual(out.getvalue(), f"[OK] wrote 2 execution packet(s) to {packet_path}\n")` 锁定。
- **边界条件 ✓**：`args.task=None`（`append` 未给）→ `if args.task:` 假 → selected=None → 全量行为；未知 task id → `selected` 为空/缺项 dict → 预览打印过滤后集合（HEAD 同行为，未回归）；重复 `--task` 值 → set 去重过滤面、附注按原始列表拼接（仅展示层重复，见 P3-1）。空列表不可达（argparse append 语义）。
- **并发/资源 ✓**：单进程 CLI；相较 HEAD 反而消除了 payload 突变（函数内字典副作用归零）；write_text + mkdir parents 与 HEAD 相同，无新资源面。
- **existing-merge 保留（验收 1）✓**：F10——`generate_execution_packets(existing=packets)` 零改动，merge 先于 selection 发生，核心测试断言未选中包的填充字段存活。

### 维度 2：安全性 — 通过

- 输入校验：无新输入面；`--task` 值仅用于 dict 键成员判断与 print 拼接。
- 注入防护：无 shell/eval/SQL 面；JSON 序列化输出。附注拼接用户自供 CLI 参数至 stdout——自伤面，无越权向量。
- 敏感数据：无密钥/token。
- 权限/路径：写目标仍为 `EXECUTION_PACKET_PATH`（GOVERNANCE_DIR 派生，FIX-245 root 校验链未动）；本改动把"过滤面静默清库"这一数据破坏向量整体关闭（安全属性净提升，EVD-959 实证 14 包丢失形态不再可达）。

### 维度 3：可维护性 — 通过（有 P3 备注）

- 注释质量：write 分支注释锚定 `FIX-296 (EVD-959)` 根因与契约（"the write face is always the FULL active packet set; --task filters the stdout preview only"）——正是事故根因的机器可读防回潮说明，符合仓库注释锚定惯例。
- 命名：`wanted`/`selected`/`preview`/`note` 意图清晰；`selected = None` 哨兵双语义（None=未过滤 / dict=已过滤含空 dict）见 P3-2（讨论级）。
- 函数长度：`cmd_execution_packet` 净增 ~10 行，总量 ~32 行，低于 50 行 guideline。
- 重复代码：无新增重复；`wanted = set(args.task)` 相比 HEAD 的循环内重建是微小改善。

### 维度 4：性能 — 通过

- `wanted` 集合外提（HEAD 每次 dict-comprehension 迭代重建 set → 现一次构建）；
- 预览浅拷贝 `{**payload, ...}` O(1) 字典展开（11 键），packets 引用共享无深拷贝；
- 无新增循环/IO；write 路径 I/O 与 HEAD 完全相同。

### 维度 5：测试覆盖 — 通过（有 P2 建议）

- 核心路径 ✓：红→绿测试真实钉住修复（F2：HEAD 上红、工作树上绿）；断言覆盖写面全量集合、existing-merge 存活、stdout 不含未选包、OK 行计数与 `--task` 标记。
- 行为边界 ✓：预览零写入钉子做**字节级文件等值**断言（`read_text == json.dumps(seeded)`）；全量 write 钉子做 **stdout 精确串等值**断言——两个"零变化"契约的钉法强度恰当。
- 覆盖缺口（P2-1）：`--task <未知id>` 组合（write 仍全量、附注照列未知 id）与重复 `--task` 值两边缘无测试——行为由代码读定且核心不变量（写面恒全量）已被钉住，非阻塞。
- 回归事实复核 ✓：F1 9/9、F3/F4 A/B（1 环境敏感例定性维持）、F5 三 gate PASS——与 Developer 报告全部吻合。

---

## 3. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| A1 | mock 残留 | **通过** | 生产 diff 零 mock/测试桩；测试侧 `unittest.mock.patch` 为本仓标准测试手法且全部作用于 temp 隔离对象 |
| A2 | 硬编码返回值 | **通过** | 无硬编码结果——note/payload 均由运行时状态推导；字面量仅消息模板 |
| A3 | 幻觉 API 调用 | **通过** | 仅使用 `Path.write_text`/`json.dumps`/`print`/`set`/dict comprehension——全部既有 stdlib/本文件用法（L13872-13885 实读） |
| A4 | 未实现 TODO | **通过** | diff 无 TODO/FIXME/占位；新增注释为根因说明而非待办 |
| A5 | 过度实现 | **通过** | 最小改动面：未新增 `--replace-all` 等 CLI 旗标、未引入抽象层、未顺带重构——与 D4 修改纯粹性一致 |

---

## 4. 设计一致性检查（硬门槛 3）

| 比对项 | 结论 |
|--------|------|
| EVD-959 事故根因（"过滤发生在 write 之前，无保护；`--task X --write` 对未选包构成静默数据清除"） | **修复正中根因**：过滤与写面解耦（selection 独立、payload 不突变），写面恒全量；CLI 级 A/B（F11④）在 HEAD 上复现事故、在工作树上证实消除 |
| triage 修复方向（"过滤仅影响 stdout 打印、不影响 write 面"） | **逐字落实**：`--task` 仅参与 else 分支的 preview 构建与 write 分支的附注文案；文件内容与 `--task` 无关（写面 = `payload` 全量） |
| existing-merge 保留契约（FEAT-015/FIX-292 会话先例：既有填充字段覆盖占位、全量 write 是合法稳态） | **无回归**：`generate_execution_packets(existing=...)` 零改动 + 核心测试断言 FIX-086 填充 goal 存活（F10） |
| 备选 `--replace-all` 不采的三点论证 | **裁定成立**：① 保留破坏形态——opt-in 破坏仍是破坏，EVD-959 类误用只是从默认变成一次旗标之遥；② 过滤面落盘无合法稳态——运行时文件是 Check 18c 的事实源，要求**全部活跃 P0/P1 包在场**，过滤面文件对本仓任何消费方都不构成合法状态（写完即 FAIL）；③ 最小改动——不新增 CLI 面、不新增迁移/文档负担。三点均经 F9（唯一写入点）+ Check 18c 消费关系独立核验 |

---

## 5. 发现清单

| # | 级别 | 位置 | 描述 | 处置建议 |
|---|------|------|------|----------|
| P2-1 | P2 建议 | tests L11255-11343 | 边缘组合缺测：`--task <未知id> --write`（应全量落盘、附注列出未知 id）与重复 `--task A --task A`（附注重复展示） | 收尾批次可补 2 用例；核心不变量已钉住，非阻塞 |
| P3-1 | P3 讨论 | verify_workflow.py L13880 | 附注 `', '.join(args.task)` 原样拼接：重复 id 会在附注中重复出现 | 可改 `', '.join(dict.fromkeys(args.task))` 保序去重；现状无正确性影响 |
| P3-2 | P3 讨论 | verify_workflow.py L13861 | `selected = None` 哨兵承载双语义（None=未过滤；dict=已过滤，含空 dict） | 独立 bool（如 `filtered`）可读性略优；现状分支逻辑正确且局部，仅讨论 |
| P3-3 | P3 讨论 | tests L11291-11293 | OK 行附注文案仅子串断言（`--task`、`wrote 2`），未精确钉注全文 | 未来附注措辞漂移不会被捕获；与全量 write 钉子的精确串等值形成对照，可接受 |
| P3-4 | P3 讨论（既有，非本改动引入） | cmd_execution_packet | `--task <未知id>` 预览静默打印空/缺失集合，无提示无退出码差异——HEAD 既有行为，本改动如实保留 | 可作为后续 UX 候选（warn 或 exit 2），超出本任务范围 |

**P0 = 0；P1 = 0；P2 = 1；P3 = 4（其中 P3-4 为既有行为披露）**

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | **✓ 0** |
| 5 维度全覆盖 | 100% | **✓** 正确性/安全性/可维护性/性能/测试覆盖逐一有结论（§2） |
| 每条发现标注级别 | 100% | **✓** 5 条发现全部 P2~P3 标注（§5） |
| 设计一致性检查 | 已完成 | **✓** 4 项比对全过，含备选方案裁定（§4） |
| AI 代码专项 5 项 | 全部完成 | **✓** A1~A5 逐一有结论（§3） |
| 事实依据红线 | 无法验证即标注 | **✓** §1 未验证项三条如实标注 |

---

## 7. 审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

- **P0=0 / P1=0 / P2×1 / P3×4**；P2-1 与 P3-1~3 为非阻塞建议（可随收尾批次处置），P3-4 为既有行为披露。
- **通过依据**：(1) 过滤面落盘路径在代码层不再存在（F9 全仓双路 grep 唯一写入点 L13873 恒全量）且 CLI 级 A/B 实证（F11④）；(2) 三个行为边界全部零变化实证（F11①②③ + 两个钉子测试）+ 预览语义正确（仅打印所选）；(3) existing-merge 契约无回归（F10 + 测试断言）；(4) TDD 红独立复现（F2）；(5) 回归事实全部复核吻合（F1/F3/F4/F5）；(6) +1 issue 漂移独立定性为 Check 34 S1(FIX-295/EVD-966) 治理运行时数据态（F7 代码无关 + F8 三重旁证），无一指向本改动。
- **建议**：合并按现状；P2-1 边缘用例与 P3-1 附注去重可登记收尾批次；Check 34 的 S1 家族（FEAT-011/FIX-297/FIX-294/FIX-295 连续四任务同模缺 RECO 行）建议 Coordinator 作为独立治理候选项处理（非本任务范围）。
