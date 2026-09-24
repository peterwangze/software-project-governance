# REVIEW-FEAT-061-CODE-R1 — decision-log 存储分离首表·阶段性交付（代码复审 · 同席 R1）

> **Round**: R1（前轮 = REVIEW-FEAT-061-CODE-R0，NEEDS_CHANGE / unresolved_blockers=2〔P0-F1 append epoch fencing 竞窗 / P0-F2 duplicate_acceptances 丢弃砖化〕；前轮引用：`docs/reviews/review-FEAT-061-CODE-R0.md`）
> **复审输入**: 前轮报告 12 findings + Developer 修复说明 `docs/reviews/review-FEAT-061-CODE-R0-fix.md`（机录 REVIEW-FEAT-061-R0）
> **复审性质**: M7.4 T1（round<3）同席复审——本质是验证修复：逐条比对前轮 findings（已修复/未修复/新引入）+ 修复形态闭合论证复核 + 修复后全量复跑 + R0 两个 P0 复现脚本反演
> **唯一输出**: 本报告

---

## 0. 复审结论

## **APPROVED_WITH_NOTES** — unresolved_blockers = **0**

| 项 | 数量 | 明细 |
|---|---|---|
| P0 阻塞 | **0**（前轮 2 → 双双修复并反演通过） | — |
| P1 关键 | 0（前轮 2 → 修复且有验收钉） | — |
| P2 建议 | 0（前轮 3 → 全部修复） | — |
| P3 备注/遗留 | 5 | N-1 修复声明 per-file 分配数字再次不实（23+22+7 ≠ 申报 24+21+7）；N-2 R0-F11 两处 docstring 未修（修复声明映射错位——修的是另两处真实失准）；N-3 revalidate frozen 分支语义措辞过声称（epoch CAS 先触发）；N-4 checkpoint 写入自身失败的二阶穿透（可辩护 fail-loud）；N-5 rollback-export 工件无自校验钉（新观察）+ R0-F12 未修（未声称，遗留） |

**裁决理由**：前轮两个 P0 的修复形态正确、闭合论证经代码证据复核成立、R0 活体复现脚本在修复后代码上反演通过（F-1 → 结构化拒绝+零副作用；F-2 → append ok+键集存活）；P1×2 均有判别力核验过的验收钉；P2×3 全部落地。全部实测独立复跑通过（157 + verify/cross-refs/manifest exit 0×3 + 附加回归 88 + fixture 19 步零 U+FFFD）。剩余 5 项全部 P3 非阻塞（其中 2 项为 R0 即已定 P3 备查级的未修项，本批未声称修复）。**不构成未解决 BLOCKING finding——APPROVED_WITH_NOTES 合规使用**（无未解决 blocker）。

---

## 1. 前轮 12 findings 逐条比对（R1 复审规程第 1 义务）

| R0 ID | R0 定级 | R1 处置 | 复审证据 |
|---|---|---|---|
| **F-1** append 路径 epoch fencing 仅 entry 时点 | **P0** | **已修复（形态+反演双确认）** | ① md 腿 `_TargetLock(target)` 临界区**首语句** `authority = _revalidate_authority_in_lock(...)`（governance_store.py L1359-1360）；json 腿同构（L1566-1567）；② 共享助手三重检查序：`load_authority(expected_epoch=entry_epoch)`（epoch 变动→revision_conflict 带 observed_epoch）→ frozen 重检 → backend 重检（L1430-1477）；③ 修复后 ledger 记录的 authority 快照改用**重校验后的世界**（L1418-1421/L1662-1665）——审计面比 R0 更准；④ 反演：R0 复现脚本在修复后代码上 `[1] code=revision_conflict, observed_epoch=2`、`[2] ledger 零写入`、`[5] md 字节与 seed 一致`、`[6] freshness=fresh`、`[7] 后续 append ok+投影 fresh`（R0 同脚本原样运行时在 ledger 读取处 FileNotFoundError 崩溃——恰为「拒绝+零写入」行为证据）；⑤ 验收钉 case11/12 判别力核验（§2.2） |
| **F-2** `_decision_append_json` 丢弃 `duplicate_acceptances` | **P0** | **已修复（形态+反演双确认）** | `new_store = dict(store)` 后仅覆盖 records/items（L1637-1640）——顶层可选键存活；浅拷贝足够性：`list(store["records"])` 浅拷贝列表、既有 record dict 为共享引用但 append 不修改它们、新 record 为新建 dict、json.dumps 纯序列化——引用共享无害；反演：`[2] append ok`、`[3][4] store 可载入/read_snapshot OK`、`[5] 重试 replay=ok`、`[6] duplicate_acceptances 存活 True`；验收钉 test_append_preserves_store_top_level_keys（带 DEC-194 勘正对走全 cutover→append→`set(after)==set(before)`+acceptance 值不变+fresh+DEC-238 落位，test_decision_migration.py L864-896） |
| **F-3** rollback_activate 缺摘要复检 | P1 | **已修复（镜像完整性核验）** | rollback_begin 在 json 锁内钉 `frozen_store_digest` 并载入 frozen 载荷（decision_migration.py L692-693/L702）——转换同在 json 锁内（锁序 json→state ✓）；rollback_activate 在 json 锁内对称复检 vs `authority.frozen.frozen_store_digest`（L810-829）：不一致→manual_intervention 世界保持冻结；**缺失字段→拒绝并提示重跑 rollback-begin**（前 F3 时代冻结记录兼容处理 ✓）。锚点选择比 R0 建议更严格（对 begin 时点而非 export 时点）——export 与 begin 之间的 store 篡改同样被拒 |
| **F-4** 交错覆盖缺口 | P1 | **已修复（判别力核验）** | case11（L621-665）：seam 在 `_TargetLock.__enter__` 内、`super().__enter__()` **之前**触发——写者未持任何锁=真实去调度时序；guard 防递归；dmig/drepo 持未打补丁锁引用→嵌套 cutover 干净穿透；断言 revision_conflict+observed_epoch=2+**md 字节不变**+终态 JSON_ACTIVE+postconditions。修复前该测试必红（append 会 ok 且 md 多一行）——判别力成立。case12(a) 正常路径回归（calls>=1 活跃性）+12(b) json 腿对称交错（entry JSON_ACTIVE→锁前完整 rollback→锁内拒绝+md 原样+终态 MD_ACTIVE）。**Developer 披露的初版死锁已改**：持锁后触发会与 freeze 的 md 锁同线程自锁——现版在锁获取前触发，披露真实且时序语义正确 |
| **F-5** 投影失败类别不完整 | P2 | **已修复（附一项 P3 残余）** | L1672-1673 `except (StoreError, OSError, ValueError, UnicodeDecodeError)`——last_error 按类型分支（L1684-1687）；@_returns_payload 交互：四类在投影调用点本地捕获，不再穿透。穿透路径穷举：project 内 read_bytes→OSError✓、load_json_store→StoreError✓、render 配对断裂→StoreError✓、json.loads→ValueError✓、UnicodeDecodeError✓。**残余（N-4，P3）**：`write_projection_checkpoint` 自身写失败（磁盘满/权限）的 OSError 仍从 except 块抛出——二阶场景（债务持久化也失败），fail-loud 可辩护，但「exit 0 对所有失败类别成立」措辞过强 |
| **F-6** marker 无未知键白名单 | P2 | **已修复** | `_AUTHORITY_TOP_KEYS` 12 键白名单（decision_repository.py L256-260）+ 未知键 manual_intervention 拒绝（L273-281）——与 store 侧 `_STORE_TOP_KEYS` 精度对齐 |
| **F-7** rollback_begin 不取 json 锁 | P2 | **已修复** | store 摘要读取 + 转换均在 `_TargetLock(json_target)` 内（L692-705）——与 append/activate 同一互斥 |
| **F-8** 用例计数申报 | P3 | **部分处置 → N-1** | 总数勘正到位：collect 实证 **52** ✓；但 per-file 分配数字再次不实：申报「24 repository + 21 migration + 7」→ 实测 **23 + 22 + 7**（repository 23 未变——本批未加 repository 测试；migration 19+3=22）。与 R0 的 24/19/7 偏差同型（机械 collect 可避免） |
| **F-9** 演练规模口径 | P3 | **处置确认** | fixture 重生成后为权威锚：19 步、116 记录、179 分类行口径（fix.md L47）；「116 = 118 管道行 − 表头 − 分隔」的推导口径与记录数一致；记录数 116 与 R0 fixture 一致 ✓ |
| **F-10** fixture mojibake | P3 | **已修复（实测确认）** | 重生成 fixture：**U+FFFD 计数 = 0**（字节级实测）、freeze detail 中文+em-dash 正常、脚本直写显式 UTF-8 + 三处 `-X utf8`（dmig L218 / tests L76 / 演练脚本）+ `decision_migration.main` stdio reconfigure（L1073-1074） |
| **F-11** docstring 失准 ×2（project_store_to_markdown stale-checkpoint 归属 + freshness corrupt 承诺/裸 decode） | P3 | **未修复 → N-2** | 修复声明 P3-4 所修两处（decision_append「追加为权威工件末项」L1270-1272 ✓、模块头双后端口径 L34 ✓）**真实存在但不是 F-11 指出的两处**——映射错位。F-11 本体原样：project_store_to_markdown 注释仍称 stale 路径「the checkpoint records the pending debt」而实际 raise 由调用方写（L1019-1028）；projection_freshness docstring 仍承诺 corrupt 结构化而 L1091-1092 仍裸 `md_raw.decode("utf-8")`。P3 遗留备查（fail-loud 不静默，非阻塞） |
| **F-12** id 不校验数字尾 | P3 | **未修复（本批未声称）** | L774 仍 `startswith(DEC_PREFIX)`——本批未声称修复，维持 R0 备查级 |

**比对小结**：已修复 8（F-1/F-2/F-3/F-4/F-5/F-6/F-7/F-10）+ 处置确认 1（F-9）+ 部分处置 1（F-8→N-1）+ 未修复备查 2（F-11→N-2、F-12——均 R0 即 P3 备查级且后者本批未声称）。**新引入：0**（修复未引入任何新缺陷；N-3/N-4/N-5 为核验中发现的新观察，均 P3）。

---

## 2. 核验清单逐项（任务指定 7 项）

### 2.1 F-1 修复形态与闭合论证复核 ✅

**「锁与状态转移同一互斥体」的代码证据——迁移控制器全部写路径持锁清单（逐一核验）**：

| 转换 | 锁 | 位置 |
|---|---|---|
| freeze：MD_ACTIVE→CUTOVER_FROZEN | **md 目标锁** | decision_migration.py L321（`with _TargetLock(md_target)` 内调 write_authority_transition） |
| activate：CUTOVER_FROZEN→JSON_ACTIVE | **json 目标锁** | L583（`with _TargetLock(json_target)` 内转换） |
| rollback_begin：JSON_ACTIVE→ROLLBACK_FROZEN | **json 目标锁**（本批修复后） | L692-705 |
| rollback_activate：ROLLBACK_FROZEN→MD_ACTIVE | **json 锁 + md 锁** | L803/L826 |
| cancel：CUTOVER_FROZEN→MD_ACTIVE | state 锁 only | 无目标锁——但 cancel 前世界为 CUTOVER_FROZEN，entry 检查已拒一切新写入者；在途写者（entry 于 MD_ACTIVE）被 freeze 的 epoch bump 在锁内拦截 → cancel 不引入新窗口 |

每个转换均发生在**其权威后端的目标锁内**；append 写者的目标锁与对应转换的锁同路径（`_TargetLock` 按路径互斥）→ 写者临界区与转换互斥 → **锁持有期间 marker 不可能再变**（`write_authority_transition` 只持 state 锁，但其全部调用方均先持目标锁——全库调用点核验无旁路）→ 锁内一次 fenced 重读（expected_epoch=entry）闭合窗口。md 腿余下交错由 freeze/activate 的 digest 复检兜底（R0 已核）；json 腿由 rollback_activate 对称复检兜底（本批 F-3）。**闭合论证成立**。

dry_run 不入锁不重校验（L1344/L1531 锁外 return）——维持预测语义，无写副作用，可接受。

### 2.2 case11/12 判别力 ✅（含初版死锁披露的时序核义）

- Seam 真实性：触发点在 `super().__enter__()` 之前=写者**未持锁**——正是 R0 复现脚本的去调度时序（而非初版持锁后触发——那会与 freeze 的 md 锁同线程自锁，Developer 披露如实且改法正确）。
- 判别力反证：修复前行为下 case11 的 `assertEqual(result["code"], "revision_conflict")` 与 `assertEqual(world.md_text(), input_md)` 均必红（R0 实测 append=ok、md 多一行）。
- case12(b) 的嵌套：rollback 三步全程在 guard 内走 patched 锁，`not guard["active"]` 防递归——穿透正确。

### 2.3 F-2 `dict(store)` 浅拷贝足够性 ✅

records/items 被替换为**新 list**（浅拷贝元素引用）；既有 record dict 在新旧 store 间共享但 append 全程只读它们；新 record 独立构造；`json.dumps` 纯序列化无变异。浅拷贝语义充分，无嵌套结构突变风险。键集钉以真实 cutover 世界（带 `--accept-duplicate` 的 DEC-194 对）端到端实证。

### 2.4 F-3 对称复检镜像完整性 ✅（附新观察 N-5）

activate 门（md frozen→current）↔ rollback 门（store frozen→current）镜像成立；锚点为 begin 时点（严于 export 时点）。**新观察 N-5（P3）**：`rollback-export.md` 工件本身在 export→activate 之间无自校验钉——rollback_activate 直接信任 `report.export_path` 内容（L798-799），journal 的 export_digest 记录的是 activate 时读到的 digest 而非 export 时点 digest，二者间无比对。篡改需本地写权限且 md 恢复后 freshness 可检出异常——边缘备查。

### 2.5 P2 投影失败四类捕获面 ✅（附 N-4）

捕获集合覆盖 project 路径全部可抛类别（穷举见 §1 F-5 行）；`@_returns_payload` 交互正确（四类本地捕获后不穿透）。残余 N-4：checkpoint 写入失败的二阶 OSError 仍穿透（P3，fail-loud 可辩护——此时世界无法表达 pending，抛出比静默 ok 正确）。

### 2.6 修复后全量复跑（本审查独立执行）✅

| 套件 | 结果 |
|---|---|
| collect（3 新文件） | **52 collected**（23+22+7——per-file 与申报 24+21+7 不符→N-1） |
| 四文件全量（52 新 + 105 governance_store 基线） | **157 passed**（19.6s） |
| verify_workflow verify | **PASSED，exit 0** |
| check-cross-references | **[PASS] No circular references，exit 0** |
| check-manifest-consistency | **[PASS]，exit 0** |
| 附加回归抽查（test_archive_decision_attribution + test_triage_write_guard） | **88 passed, 4 subtests**（零回归） |
| R0 P0-A 复现脚本反演 | ✅ append ok / store 可载入 / snapshot OK / 重试 replay / acceptance 存活 |
| R0 P0-B 复现脚本反演 | ✅ revision_conflict+observed_epoch=2 / ledger 零写入 / md 字节不变 / freshness fresh / 后续 append ok |
| rehearsal fixture 复读 | ✅ 19 步零 U+FFFD；exit 序列 0,0,2×10,0×7（11 处逐 ID 拒绝链+全环通过）；verify PASS+reverse PASS+round_trip True+untouched True |

fix.md 申报的「263 全绿（triage_write_guard/archive/bootstrap/archive_decision/product_code 五文件）」——本审查以其中两个最大面（88 用例）抽查替代全量（bootstrap_aggregate 等与本票修改面无交集），如实标注抽查非全量。

### 2.7 R0 12 条逐条比对 — 见 §1 表

---

## 3. R1 新发现（全部 P3，不阻塞）

| ID | 级别 | 位置 | 内容 |
|---|---|---|---|
| **N-1** | P3 | fix.md L46 / 本审查 collect | per-file 分配数字连续两轮不实：R0 申报 24/19/7（实 23/19/7），R1 申报 24/21/7（实 **23**/22/7）。总数正确；repository 文件本批未加测试仍报 24。建议以 `pytest --collect-only -q` 机械数替代人工申报 |
| **N-2** | P3 | decision_repository.py L997-1001（注释）/L1069+L1091-1092；governance_store.py L1270-1272（已修✓） | R0-F11 两处 docstring 未修（修复声明映射错位——声称修的与实际修的不是同一组；实际修复的两处真实有效）。遗留：project_store_to_markdown stale 路径 checkpoint 归属描述、projection_freshness corrupt 承诺 vs 裸 decode |
| **N-3** | P3 | governance_store.py L1455-1466 / fix.md L15 | `_revalidate_authority_in_lock` frozen 分支的声称语义（「entry 后才开始的冻结 → illegal_transition」）过声称：任何线性化必 bump epoch，frozen 分支实际只覆盖「epoch 未变但 state frozen」的篡改场景——行为正确（拒绝+observed_epoch 回传），仅措辞与实际触发序不符 |
| **N-4** | P3 | governance_store.py L1681-1691 | 投影债务 checkpoint 写入自身失败的 OSError 二阶穿透（append 的四类捕获不含 checkpoint 写失败）——磁盘满/权限场景 exit≠0 而承诺 exit 0；fail-loud 优于静默，可辩护设计，登记边界即可 |
| **N-5** | P3 | decision_migration.py L798-799/L833 | `rollback-export.md` 工件在 export→activate 之间无自校验钉（journal export_digest 是 activate 时点值非 export 时点值）——边缘篡改面，freshness 可事后检出 |

**R0-F12 维持备查**（L774 startswith——未声称修复）。

---

## 4. 五维度 + AI 专项复审增量

- **正确性**：两 P0 闭合 ✅；状态机/锁序/幂等面未因修复退化（157 全绿 + case11/12 正常路径回归腿）；重校验后的 authority 快照进 ledger——审计面增强。
- **安全性**：marker 白名单补齐（F-6）；拒绝路径零副作用（反演 [2] ledger 零写入实证）。
- **可维护性**：共享助手消除两腿重复（单一 fenced 重读语义源）；N-2/N-3 两处措辞遗留。
- **性能**：每笔 append 增加一次 marker 读取（锁内）——量级可忽略；其余面无变化。
- **测试覆盖**：19→22（case11/12+键集钉）；12 崩溃并发用例全绿；交错面缺口闭合。
- **AI 专项 5 项（增量复检）**：mock 残留无（case11/12 seam 注释化+guard 还原）；硬编码返回值无；幻觉 API 无（新引用 `_revalidate_authority_in_lock`/`_AUTHORITY_TOP_KEYS`/`frozen_store_digest` 全部实际存在）；未实现 TODO 无（grep 零命中）；过度实现无（修复严格限定前轮 findings 范围）。

---

## 5. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 = 0 | ✅（0） |
| 5 维度全覆盖 | ✅ |
| 每条发现标注级别 | ✅ N-1~N-5 全 P3 + 行号 |
| 设计一致性 | ✅ ARCH-01（epoch fencing 全路径）/02/06/07/09 五条款修复后重检通过；其余条款 R0 已核未受修复影响 |
| AI 专项 5 项 | ✅ |
| 事实依据红线 | ✅ 全部结论锚定行号/命令输出/反演记录；157/88/三命令/fixture U+FFFD=0/两反演均为本审查独立实测 |

**REVIEW-FEAT-061-CODE-R1 · 结论：APPROVED_WITH_NOTES · unresolved_blockers = 0**

*复审方法披露：修复说明逐行对照修复后代码（两腿锁内重校验/helper/dict(store)/四类捕获/白名单/rollback 双门/新增 3 测试）；闭合论证以迁移控制器全部状态转换的持锁清单为代码证据复核；R0 两个 P0 复现脚本在修复后代码上反演（P0-B 原脚本崩溃点本身构成「拒绝+零写入」行为证据，另建反演脚本取证）；157/附加 88/三命令/collect 计数/per-file 计数/fixture U+FFFD 字节级检查均为本审查独立实测。全程未触碰真实 `.governance/`（只读）。*

*遗留移交：N-1~N-5 + R0-F12 全部 P3 备查级——建议随切换票前的小批（或本票收尾 commit）一并清扫；其中 N-2/N-3 为纯注释措辞，N-1 为申报纪律，N-4/N-5 为边界登记。真实切换授权前置条件（R0 报告 §6.3）现已被 P0/P1 修复满足。*
