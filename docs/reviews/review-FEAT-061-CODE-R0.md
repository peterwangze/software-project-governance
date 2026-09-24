# REVIEW-FEAT-061-CODE-R0 — decision-log 存储分离首表·阶段性交付（代码审查）

> **Round**: R0（首轮） · **Task**: FEAT-061（P1，0.88.0 阶段 C1——本版本最高风险票） · **Reviewer**: Code Reviewer（独立子代理，只读审查）
> **审查对象**: 工作树未 commit diff——4 新模块（`decision_repository.py` 1088 行 / `decision_migration.py` 1054 行 / `decision_migration_verify.py` 851 行）+ 1 改（`governance_store.py` +257/−5）+ 3 测试（23+19+7=**49 用例，实测收集数**）+ rehearsal fixture
> **需求事实源**: DEC-237（decision-log，机录 op-b13202de——10 条 C1-ARCH 补丁条款 + 10 用例最低验收集 + 独立性三规则）；`docs/planning/version-plan-0.88.0.md` §1 假绿对冲（L15 独立性三条）+ §2 C1 七步路径（L44）
> **硬门槛**: 每项发现附文件/行号/证据；实测优先；只读被审代码与 `.governance/`；唯一输出 = 本报告
> **性质声明**: 阶段性交付——真实切换未执行（红线遵守✓）；审查不执行真实切换

---

## 0. 总结论

## **NEEDS_CHANGE** — unresolved_blockers = **2**（P0×2，均经活体复现实证）

| 项 | 数量 | 明细 |
|---|---|---|
| **P0 阻塞** | **2** | F-1 append 路径 epoch fencing 仅 entry 时点（竞窗活体复现→端到端静默数据丢失）；F-2 JSON append 丢弃 `duplicate_acceptances`（真实热文件首笔 append 必触发→store 砖化，活体复现） |
| P1 关键 | 2 | F-3 rollback_activate 缺 store-digest 双向摘要复检（与 activate 不对称）；F-4 10 用例未覆盖「已过 entry 检查的写入者跨越线性化点」交错（假绿对冲正面战场的覆盖缺口） |
| P2 建议 | 3 | F-5 投影失败类别不完整（非 StoreError 异常穿透公共 API，违背「已提交待修复+exit 0」承诺）；F-6 authority marker 校验无未知键白名单（低于 store 侧 fail-closed 精度）；F-7 rollback_begin 不取 json 锁（与 freeze 锁纪律不对称，主修复后安全但机制声明名不副实） |
| P3 讨论 | 5 | F-8 用例计数申报口径（50 vs 实收 49）；F-9 演练行数申报口径（118 行 vs fixture 实证 179 分类行/116 记录）；F-10 rehearsal fixture 注记字段 mojibake；F-11 freshness md 非 UTF-8 裸异常未归一化 + stale 路径 checkpoint 归属 docstring 失准；F-12 `load_json_store` id 不校验数字尾 |

**通过面（如实记录）**：独立性三规则实现真实有效（镜像解析器与真实 `_split_row` **逐字符等价**——本审查逐行比对实证；子进程隔离 + 禁导入门禁结构可靠）；状态机闭表 + 原子线性化点 + epoch CAS 正确；五桶分类 + 聚合前拒绝 + verbatim 保真在**迁移/投影方向**成立；MD 世界字节级零变化成立（md append 代码路径未被触碰，仅 ledger 增量字段且 `_load_ledger` 容忍未知键——L604-632 实证）；49/49 新测试 + 105/105 回归 + 负向套件 7/7 全部**本审查独立复跑通过**；演练 3 缺陷的修复真实落地。**两处 P0 均落在迁移/投影路径未覆盖的 append 运行窗口上**——不推翻已通过面，但阻断合并。

---

## 1. 五维度逐项结论

### 1.1 正确性 — ⚠️ 两处 P0（详见 §3 F-1/F-2）

| 检查项 | 结论 | 证据 |
|---|---|---|
| 状态机闭表完备性 | ✅ | `LEGAL_TRANSITIONS` 6 条闭表（decision_repository.py L150-157）：非法/跳级/回退外转移全拒；`STATE_BACKENDS` 后端-状态绑定校验（L283-289）；epoch 单调递增无回绕；缺失 marker = 初始 md 世界（零足迹✓，测试 test_absent_marker） |
| 线性化点原子性 | ✅ | `write_authority_transition` 在状态文件自身 `_TargetLock` 内 CAS 校验 + `_atomic_write_bytes`（mkstemp+fsync+os.replace+dir fsync，governance_store.py L438-455）——原子替换即切换时刻，单点成立 |
| **旧 epoch 写入者命运** | ❌ **P0** | entry 单次 `load_authority`（governance_store.py L1303，无 expected_epoch）；md 腿锁内（L1345）与 json 腿锁内（L1496）**均无 epoch/状态重校验**。活体复现：写入者已过 entry 检查后被调度延迟跨越 cutover 线性化点 → append 返回 ok → 记录仅在投影面 → 下一笔投影抹除 → **端到端静默丢失**（§3 F-1 复现记录 [1]-[7]） |
| unknown 判定 fail-closed | ✅ | marker 未知状态/非 JSON/backend-state 失配全拒（L252-295 + 测试×3）；store 未知顶层键/未知 record 键/schema_version 窗外全拒（L708-752）；缺 gate 输入大声拒绝（decision_migration.py L116-131） |
| 五桶分类与 verbatim | ✅（迁移/投影方向） | 每行有源位置与去处；unresolved 阻断；重复 ID 聚合前拒绝；`row_raw`/`cells` 逐字保留；`render_markdown` 位置配对渲染（L639-652，勘正对回归钉 test_render_is_duplicate_safe） |
| **JSON 往返保真（读-改-写）** | ❌ **P0** | `_decision_append_json` 重建 `new_store` 仅 4 键（L1560-1566），**丢弃 `duplicate_acceptances`** → 首笔 append 落盘后 post-write reread（L1572）即拒绝，store 砖化（§3 F-2 复现记录 [1]-[6]）。真实迁移 store 必带 DEC-194/DEC-214 验收注记（fixture L167-170 + 真实 decision-log.md L132/134/155/156 本审查实证） |
| 并发安全（锁序） | ✅/⚠️ | 锁序 json→md→state→ledger 全家族一致（无死锁）；CAS/幂等/world-recovery 与 md 腿同构；4 线程并发 append 无丢记录（测试实测）。⚠️ 冻结窗互斥对「已过 entry 的写入者」不成立（F-1） |
| 资源管理 | ✅ | `_atomic_write_bytes` 异常清理临时文件（L450-455）；锁 `__exit__` 幂等释放；subprocess 超时处置（decision_migration.py L220-225） |

### 1.2 安全性 — ✅（附 F-6 精度建议）

- 输入校验：CLI `--gov-dir` 强制显式（decision_migration.py L965——无静默默认触碰宿主）；`--accept-variant/--accept-duplicate` 格式校验（L391-409）；`_decision_row_validator` 日期/mandatory cell/marker 复验（governance_store.py L1241-1254）。
- 注入面：无 shell 拼接（subprocess 列表参数）；JSON 全程 `json.dumps/loads` 结构化；正则无灾难回溯形态。
- 敏感数据：无硬编码密钥/token（owner_token 为一次性 uuid4.hex，返回给冻结调用者、不落日志明文——`status` 仅 `owner_token_present` 布尔，L867）。
- 权限：cancel/rollback 全 owner_token+epoch 门（ARCH-09✓，case ⑨ 测试）；Activate 四重 gate（verdict PASS + migration_id 绑定 + manifest_digest 绑定 + frozen digest 复检，L515-552）。
- F-6（P2）：marker 本体无未知键白名单、`owner_token/manifest_digest/migration_id/content_digest` 无类型校验——`mutate` 可注入任意键（L401-403）。fail-closed 精度低于 store 侧（`_STORE_TOP_KEYS` L180-183 有白名单）。不构成可利用面（marker 为机器写），精度补齐建议。

### 1.3 可维护性 — ✅

- 六层职责映射在模块 docstring 显式钉死（decision_repository.py L1-77），依赖方向与实际 import 一致；私有导入理由声明（单锁/单原子写/单切分器纪律，write_guard_state 先例）。
- 需求源「consumed, never re-stated」纪律落实；每命令 ARCH 条款锚注。
- 函数长度：最长 `cmd_verify`（verify 模块 L457-592，~135 行）与 `_decision_append_json`（~205 行）超 50 行建议线，但为线性 gate 流水，分支清晰——P3 级不单列。
- 注释与代码一致性：两处失准（F-11：stale 路径 checkpoint 归属；freeze closure `writes_rejected_mechanism`「write service refuses before touching any file」对 entry-已过写入者不成立——随 F-1 修复一并更正）。

### 1.4 性能 — ✅

- 全文件原子重写（store 每笔 append 全量重序列化）在当前 116 记录/164KB 量级无问题；`_scan_archive_ids` rglob 全树扫描每笔 append 一次——与 md 腿既有口径一致，未回归。
- 无 N+1/O(n²) 热点：分类/等价比对均为 O(n)；快照 digest 单次序列化。
- 锁等待 10s + 600s stale takeover（既有已披露边界 P3-2，FEAT-046 R0）不因本票恶化。

### 1.5 测试覆盖 — ⚠️ 一处 P1 覆盖缺口（F-4）

| 面 | 结论 |
|---|---|
| 49 新用例 | **本审查独立复跑：49/49 PASS**（13.0s）。申报「24+19+7=50」与实收 23+19+7=49 不符（F-8）；同申报内「49+回归105=154」自洽——以 49 为准 |
| 回归 | test_governance_store.py **105/105 PASS**（本审查复跑）——MD 零回归钉成立 |
| 10 崩溃并发用例 | 全绿；五共同后置条件中「唯一权威/无丢失无重复/未知不放行/重试稳定」四项由 `PostconditionsMixin` 逐例断言；「发布不消费陈旧证据」在 ③⑤ 及 happy path 断言（模块 docstring「EVERY case」措辞略过——P3 级，不单列） |
| **交错覆盖缺口** | **F-1 的交错（entry 已过检查的写入者 × 线性化点）10 用例零覆盖**：case ①⑦ = entry-time 拒绝；case ④⑧ = crash-resume 世界恢复（marker 已在世界中）；freeze digest gate 测试 = rogue **直接文件编辑**而非路由写入者。假绿对冲正面战场的并发面恰好漏掉本审查实测可复现的丢失交错——**必补**（seam 技法与 case ③⑤ 同族：锁 `__enter__` 处同步触发迁移） |
| 负向注入 | 独立运行 7/7 REJECTED（本审查复跑，verdict PASS） |
| 演练 fixture | 真实热文件副本全链 sample→freeze→shadow→verify PASS→activate→rollback 全环 exit 0；`round_trip_byte_identical_vs_dispositioned_input: true`；`real_governance_untouched: true` |

---

## 2. MUST 重点审查八项逐项裁决

### ① 状态机与 fencing 严密性 — ⚠️ 闭表/原子性/unknown 判定成立；**fencing 时点不成立（F-1 P0）**

闭表完备（§1.1）；`write_authority_transition` 是唯一合法状态写入者（全库 grep 证实无旁路写 marker）；原子替换线性化点真实。**但「epoch fencing 所有追加路径」（C1-ARCH-01 原文）的实现仅覆盖 entry 时点**：`decision_append` L1303 读 authority 一次，此后 md 腿（L1345 锁内）/json 腿（L1496 锁内）再无任何 authority 感知。写入者在 L1303 与锁获取之间的调度间隙（无锁依赖、纯 OS 延迟即可）跨越 freeze/activate/rollback 线性化点后照常提交。**各状态命运实测**：MD_ACTIVE→（越过 freeze+activate）→JSON_ACTIVE 世界落笔 md = 投影面孤儿行 → 下笔投影销毁（复现 [7]）；JSON_ACTIVE→（越过 rollback 全程）→MD_ACTIVE 世界落笔 store = 死存储孤儿行（同构交错；投影失败时不可修复——`project-repair` 要求 JSON_ACTIVE 态，L879）。**修复方向（主修复，可闭合两腿）**：两腿目标锁临界区内重校验 `load_authority(governance_dir, expected_epoch=entry_epoch)`，state∈FROZEN / epoch 移动 / backend≠路由后端 任一命中即拒——锁互斥保证重校验后的写入与后续线性化互斥（freeze 持 md 锁、rollback_activate 持 json 锁、rollback_begin 虽不取 json 锁但其后继 export/activate 均需 json 锁，写入者先持锁则导出含其记录，后持锁则被拒）。

### ② 独立校验器独立性真实性 — ✅ 成立（本审查最强确认项）

- **禁导入断言**：`FORBIDDEN_MODULES` 四模块在 `environment_report()` 运行时检查 `sys.modules`（verify L179-180）。子进程调用时（controller `_run_verifier` L215 用 `sys.executable` 独立进程）新实现结构上不可能在环境中；**进程内调用同样被门禁拦截**（本进程若已 import governance_store，gate 必_fire）——负向用例 ⑦ 实证门禁机制本身。无可绕过路径（判定门在环境报告采集点一次性评估，verdict 由纯函数产出）。
- **镜像保真**：`_split_row_legacy`（verify L74-98）与真实 `governance_store._split_row`（L458-485）**逐字符等价**（strip/前导管道判定/code-span 翻转/`end` 计算/剥离规则/末 cell——本审查逐行比对）；`_DEC_ANCHOR_RE` 两侧同一正则（L212/L105），与引擎 `^\s*\|?\s*DEC-(\d+)\b` 行锚语义等价（首 cell 锚定 vs 行锚，对管道行等价）。镜像漂移方向检视：仅 header 签名一处新分类器更宽（接受英文 `id` 头，legacy 归 unresolved）——**fail-closed 方向**（分歧行阻断迁移），无假通过方向漂移。
- **三类证明输入独立性**：Class A 独立重采样（不消费 controller 状态）；Class B 用 legacy 解析器产物对 store 数据裁决；Class C 对账在世界文本中找 marker。共同盲区由「镜像=语义同一 + 全输入覆盖（每行必有去处）」组合缓解——declaration 如实披露「the duplication IS the independence」及残余风险（staged delivery / 引擎发布面未接线 / archive 消费方未路由）。
- 残余（如实记录）：Class B 不校验 `duplicate_acceptances`/provenance 注记本身的保真（元数据级，Class C 覆盖 marker 面）——P3 级。

### ③ JSON store v1 往返保真 — ⚠️ 迁移/投影方向成立；**append 读-改-写方向被 F-2 击穿（P0）**

`load_json_store` 白名单 + 窗外拒识 + verbatim 要求完备（L661-786）；`build_store_from_document`/`render_markdown` 双向 verbatim（含勘正对位置配对）。**但 ARCH 条款「保留未知字段必须覆盖读—改—写」在 append 路径失守**：合法可选键 `duplicate_acceptances` 被重建丢弃（L1560-1566）。后果不是静默丢失而是**砖化**（fail-closed 拒绝一切后续读/写——数据行仍完整，可手工修复，但自动化面全灭且失败发生在「写入已落盘」之后，错误语义误导）。修复：`new_store = dict(store)` 后覆盖四键；并补「append 前后顶层键集不变」回归钉 + 一条 duplicate-carrying store 的 append 用例（现测试套件 0 覆盖——test_render_is_duplicate_safe 只钉 codec，不钉 append）。

### ④ 投影协议 — ✅（附 F-5 边界）

checkpoint 持久化（权威提交结果与投影结果分开表达，ARCH-06✓）；stale 围栏真实（case ⑤ 实测：md 锁内重读 store digest 不匹配即拒，晚到投影无法覆盖）；`json_lock_held` 委托形态保锁序。**不可行使论证成立**：`projection_freshness` 语义就绪（fresh/stale/missing/corrupt/no_store 五态完备），发布面消费是切换票义务——已在 verify 的 `independence_declaration.residual_risks` 与任务卡明确申报为留票项（确认非隐瞒）。F-5：失败类别只捕 StoreError（L1598）/内部只捕 atomic-write OSError（repository L1015-1017）——md 缺失/非 UTF-8 时 FileNotFoundError/UnicodeDecodeError 穿透 `@_returns_payload`（仅捕 StoreError，L383）裸抛，commit 已落、checkpoint 未写、exit≠0 与「已提交待修复+退出码 0」承诺不符（P2）。

### ⑤ MD 世界零变化 — ✅ 成立

diff 逐行核验：md append 管线（`_append_context`→build→CAS→`_append_row_bytes`→`_post_write_append_check`，L1330-1412）**零触碰**；仅两处增量——entry authority 读（无文件副作用）与 ledger entry 可选 `authority` 字段（L687-692；`_load_ledger` L604-632 只查固定键、容忍未知键——additive 声明属实）。`decision-log.md` 字节路径无新代码。测试钉：test_md_world_behavior_byte_identical（无 json/state 文件产生、无 projection_status 键）+ 回归 105/105。

### ⑥ 10 用例后置条件断言强度 — ✅ 四项强断言 / ⚠️ 交错面缺失（F-4 P1）

`assert_postconditions` 每例收尾：唯一权威（state/backend 精确断言）+ 无丢失无重复（ID 集合全等 + set 去重断言）+ 重试稳定（双读 snapshot_digest 全等）+ 未知不放行（refusal payload code 逐例断言）。强度合格。缺「发布不消费陈旧证据」逐例化（docstring 过声称，P3 级）。**实质缺口是 F-1 交错零覆盖**（§1.5）。

### ⑦ 演练 3 缺陷修复质量 — ✅ 三项修复全部真实落地

1. **投影重复 ID 丢行** → `render_markdown` 位置配对 + 失配拒绝（repository L639-652）+ 回归钉测试（test_render_is_duplicate_safe：按 id 字典折叠会丢第一行的形态被显式断言）✓。
2. **DEC-194 勘正对** → `duplicate_acceptances` 持久化进 store + `--accept-duplicate` 双行 verbatim 携带 + load 侧无注记即拒（L760-769）✓（fixture 实证 DEC-194/DEC-214 双对通过全链）。**注意**：该修复在迁移方向完好，但 append 方向被 F-2 打穿——同一机制两方向一好一坏。
3. **DEC-nnn① 锚定** → `^(DEC-\d+)\b` 锚定使 `DEC-214①（勘误）` 保持 record（本审查对真实文件 L156 正则级确认）；11 处勘误行留切换票源文件处置的边界在 fixture `simulated_dispositions` 显式申报（格式转换不得代劳）✓。

### ⑧ 验证复现 — ✅ 全部独立复跑通过

| 项 | 申报 | 本审查实测 |
|---|---|---|
| 新测试 | 49+（申报口径含一处 50 自相矛盾，F-8） | **49/49 PASS**（collect 49：23+19+7） |
| 回归 | 105 | **105/105 PASS** |
| verify 负向套件 | 7 用例 | **7/7 REJECTED**（standalone 复跑） |
| 真实演练 | PASS+反向 PASS+字节回环 | fixture 权威锚定：116 记录/8 变体/2 重复对，全环 exit 0，round_trip true（179 分类行——申报「118 行」口径出入，F-9） |
| P0 复现 | （未申报——为审查新发现） | **F-1/F-2 均活体复现**（脚本 + 逐步输出见 §3） |
| 宿主既有 FAIL 归因 | check-sequential-ids/structural-validity 与本票无关 | 与本审查独立实证一致（真实热文件确有重复 ID 与变体行——归因成立；未重跑引擎全量，如实标注） |

---

## 3. 发现清单（P0~P3）

### F-1【P0·活体复现】append 路径 epoch fencing 仅 entry 时点——跨线性化点写入导致端到端静默数据丢失

- **位置**：`governance_store.py` L1303（`authority = load_authority(governance_dir)`——无 expected_epoch、无锁）；L1345（md 腿 `_TargetLock` 临界区，无重校验）；L1496（json 腿 `_TargetLock` 临界区，无重校验）；`decision_repository.py` L952-1036（`project_store_to_markdown` 全量覆盖 md）。
- **违反**：DEC-237 C1-ARCH-01「所有追加…路径 epoch fencing」；freeze closure ②`inflight_converged` 机制声明（decision_migration.py L329-331）名不副实——锁获取只证明 freeze 时点无 mid-write，不 fencing 已过 entry 的写入者。
- **活体复现**（隔离 temp 世界，md 腿，脚本 `feat061_r0_repro_p0b.py`——seam：写入者在 entry 检查后、锁获取前被同步执行的全 cutover 抢占）：
  ```
  [1] racing append: code = ok | ledger snapshot = {"state": "MD_ACTIVE", "epoch": 0, "backend": "md"}
  [2] authority now: JSON_ACTIVE epoch 2 backend json
  [3] authoritative (store) record ids: ['DEC-147', 'DEC-237']   ← 记录不在权威后端
  [4] md contains the racing row: True                            ← 仅存于投影面
  [5] freshness gate: stale                                       ← 捕获分歧但归因失真
  [6] next append: code = ok | projection = fresh
  [7] md still contains the racing row after the next projection: False  ← 记录被销毁
  ```
  调用方全程 exit 0、ledger 记 ok——**静默丢失**。json 腿同构（rollback 窗内落笔死 store；投影失败变体下 `project-repair` 因要求 JSON_ACTIVE 而不可达，L879——债务永久化）。
- **影响**：本票核心不变量（唯一权威/无丢失）在并发运行窗失效；这是「本版本最高风险票」的对冲正面。
- **修复建议**：两腿目标锁临界区内重校验 `load_authority(governance_dir, expected_epoch=entry_epoch)`，`state∈FROZEN / epoch 移动 / backend≠路由后端` 任一命中即拒（锁互斥保证重校验后与线性化互斥——论证见 §2①）；同步更正 freeze closure ②机制描述；补两条交错用例（见 F-4）。

### F-2【P0·活体复现】`_decision_append_json` 重建 store 丢弃 `duplicate_acceptances`——真实热文件首笔 append 砖化 decision log

- **位置**：`governance_store.py` L1560-1566（`new_store = {format, schema_version, records, items}`——四键重建）；L1569（落盘）；L1572（post-write reread）。
- **违反**：C1-ARCH-05/往返保真条款「保留未知字段必须覆盖读—改—写」；审查重点 ③。
- **触发现实性**：真实迁移 store **必带** `duplicate_acceptances`（fixture L167-170：DEC-194+DEC-214；真实 `.governance/decision-log.md` L132/L134、L155/L156 双对实证）。演练序列 activate 后**无 append 步骤**（fixture steps）——缺陷落在未演练区。
- **活体复现**（隔离 temp 世界，脚本 `feat061_r0_repro_p0a.py`）：
  ```
  [1] pre-append store loads OK; records=['DEC-001','DEC-002','DEC-003','DEC-003'];
      duplicate_acceptances={'DEC-003': '勘正对——两行保留'}
  [2] append result: code = cross_record_violation | error = True   ← 失败发生在写入已落盘后
  [3] post-append store BRICKED: cross_record_violation             ← load_json_store 拒绝
  [4] read_snapshot REFUSES: cross_record_violation                 ← 权威读路径全灭
  [5] retry append: code = cross_record_violation | error = True    ← 幂等重试不可达
  [6] store on disk now carries duplicate_acceptances key: False; record count: 5
  ```
- **影响**：真实切换后**第一笔** decision-append 即触发；数据行完整（可手工补注记恢复）但自动化读/写/验证面全灭；错误出现在提交已落盘之后，语义误导（失败≠未提交）。
- **修复建议**：`new_store = dict(store)` 后覆盖四键（保留全部合法可选键）；补「append 前后 store 顶层键集不变」断言 + duplicate-carrying store 的 append→replay→投影 用例各一。

### F-3【P1】`rollback_activate` 缺 store-digest 双向摘要复检——与 activate 的完整性 gate 不对称

- **位置**：`decision_migration.py` L768-820——直接信任 `rollback-report.json` 的 `export_path`/`store_digest`（L777-786），不比对当前 store 字节。
- **对照**：activate 有 frozen→current md digest 复检（L543-552，测试 test_freeze_digest_gate_bidirectional 钉死 rogue md edit 防护）；rollback 侧对 store 的 rogue edit/窗口内变更零防护。结合 F-1（json 腿无锁内重校验），ROLLBACK_FROZEN 窗内落盘的记录被静默排除在恢复后的 md 之外（export 已成旧物）。
- **修复建议**：rollback_activate 在 json 锁内比对 `_sha256_hex(store) == report.store_digest`，不匹配即拒（fail-closed，与 activate 对称）。

### F-4【P1】10 用例零覆盖「已过 entry 检查的写入者 × 线性化点」交错

- **位置**：`test_decision_migration.py` 全部 10 case——①⑦ entry-time 拒绝、④⑧ crash-resume（marker 已在世界中）、digest gate 用 rogue 直接编辑（L647-650）而非路由写入者。
- **影响**：F-1 的丢失交错在申报的「最低崩溃并发验收集」防空洞上漏过；「10 用例全绿」不能为本票并发面背书。
- **修复建议**：随 F-1 修复补两条 seam 用例（md 腿：锁 `__enter__` 处同步 cutover 后断言 append 被拒 + 零文件变更；json 腿：锁 `__enter__` 处同步 rollback 后断言同构），并把五共同后置条件中的 freshness 断言逐例化。

### F-5【P2】投影失败类别不完整——非 StoreError 异常穿透公共 API

- **位置**：`decision_repository.py` L1009（`current_md = md_target.read_bytes()` 无 FileNotFoundError 防护；try 仅包 L1015-1017 的 atomic write）；L1071-1072（freshness `md_raw.decode` 裸 UnicodeDecodeError）；`governance_store.py` L1598（`except StoreError`）；L383（`@_returns_payload` 仅捕 StoreError）。
- **影响**：md 缺失/编码损坏时投影尝试裸抛 traceback、exit≠0、checkpoint 未写——与「投影失败=已提交待修复 checkpoint+退出码 0」承诺不符（commit 实际已落）。retry 走 ledger replay 返回 ok 但不再触发投影（按设计），债务只能靠 repair——语义可接受，但失败报告形态违背契约措辞。
- **修复建议**：`project_store_to_markdown` 将 OSError/UnicodeDecodeError 归一化为 checkpoint pending 或结构化 StoreError。

### F-6【P2】authority marker 校验无未知键白名单、核心字段类型校验不全

- **位置**：`decision_repository.py` L252-295——校验 state/epoch/generation/backend/history 五项；`owner_token/manifest_digest/migration_id/content_digest/schema_version` 无类型校验、顶层未知键不拒、`mutate` 可注入任意键（L401-403）。
- **对照**：store 侧有 `_STORE_TOP_KEYS` 白名单 + 逐键类型校验（L708-786）。
- **修复建议**：marker 白名单 + 全字段类型校验对齐 store 侧精度。

### F-7【P2】`rollback_begin` 不取 json 目标锁——冻结转换锁纪律不对称

- **位置**：`decision_migration.py` L671-696（仅状态转换；对比 freeze L305 持 md 锁转换、rollback_activate L790 持 json 锁）。
- **影响**：主修复（F-1 锁内重校验）落地后语义安全（写入者先持锁则 export 含其记录、后持锁则被拒），但「冻结=结构性拒写」的机制声明在 rollback 腿完全依赖写入者侧自觉，非互斥保证——纵深缺失。
- **修复建议**：文档化该不对称，或对齐锁纪律。

### F-8【P3】用例计数申报口径出入

申报「24+19+7=50」与「49+回归105=154」自相矛盾；实测 collect = **49**（repository 文件 23，非 24）。以机器收集为准勘正。

### F-9【P3】演练规模申报口径出入

申报「真实 118 行演练」；fixture 权威证据为 **179 分类行（content 61 + header 1 + separator 1 + record 116）/ 116 记录**（与真实文件 180 物理行一致——本审查实测）。以 fixture 为准勘正。

### F-10【P3】rehearsal fixture 注记字段 mojibake

`tests/fixtures/feat061-rehearsal-result.json` L30/38/158-172 等中文字段为 GBK 写入痕迹（mojibake）。结构化事实（digest/exit/verdict/ID 清单）完好。FIX-278 口径下证据工应 UTF-8——建议随修复批次重生成该 fixture。

### F-11【P3】两处注释/docstring 与代码失准

① `projection_freshness` docstring 承诺 corrupt 为结构化状态，但 md 非 UTF-8 走裸异常（decision_repository.py L1071-1072，与 F-5 同源）；② `project_store_to_markdown` docstring 暗示 stale 路径自记 checkpoint，实际由调用方（append 路径 L1598-305 / finalize 路径 L653-660）写入。随 F-1/F-5 修复一并更正（freeze closure `writes_rejected_mechanism` 文案同批）。

### F-12【P3】`load_json_store` 的 id 校验不锁数字尾

L754 仅 `startswith("DEC-")`——`"DEC-abc"` 可入 store；分类器只产 `DEC-\d+`、`next_decision_id` 跳过非数字（L903-906），口径不齐无实际危害。对齐为 `DEC-\d+` 全匹配。

---

## 4. AI 代码专项 5 项检查（全项完成）

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | 产品代码零 mock；测试 mock 全部 seam 注释化 + with/finally 还原（test_decision_migration.py L298-307/L395-409、verify 测试 L215-222） |
| 2 | 硬编码返回值 | ✅ 无 | 全部结果来自真实文件操作/计算；两处 P0 复现即反证（行为由真实 I/O 驱动） |
| 3 | 幻觉 API | ✅ 无 | 跨模块 18 个引用逐一在源中定位（`_split_row` L458、`_render_row` L488、`_TargetLock` L508、`_atomic_write_bytes` L438、`_line_ending_of` L418、`_hot_id_numbers` L728、`_scan_archive_ids` L712、`_recover_append` L1209、`_build_decision_row` L1229、`_decision_row_validator` L1241、`_replay_payload` L649、`_ledger_transaction` L636、`_append_row_bytes` L823、`_post_write_append_check` L790、`_dry_run_append` L829 等）；`ERROR_CODE_DISPOSITIONS` 来自 contracts.py（decision_migration.py L78） |
| 4 | 未实现 TODO | ✅ 无 | 三新模块 grep `TODO|FIXME|XXX|NotImplemented` 零命中；留切换票项（freshness 发布接线/archive 路由/DEC-nnn① 源处置）以 residual_risks + simulated_dispositions 显式申报，非隐形 TODO |
| 5 | 过度实现 | ✅ 无 | CLI 11 子命令全部对应任务验收面（FEAT-046 先例——不生长引擎 dispatch 面）；六层分层与实际文件边界一致；无投机抽象 |

---

## 5. 设计一致性（与 DEC-237 十条款逐条比对）

| 条款 | 裁决 | 备注 |
|---|---|---|
| ARCH-01 权威恢复协议/状态机/epoch fencing | ⚠️ | 状态机/线性化/unknown fail-closed ✅；**append 路径 fencing 仅 entry 时点——F-1 P0** |
| ARCH-02 冻结四闭合条件 | ⚠️ | 四条件显式记录 ✅（非假设锁/时间戳）；②机制声明对 entry-已过写入者不成立（随 F-1 更正） |
| ARCH-03 三类完整性证明 | ✅ | A/B/C 三类实现 + 独立采样器产 manifest + controller 只读不写（L266-293）+ 重采样=新 migration_id（case ⑥ 负向钉） |
| ARCH-04 独立执行与负向验收 | ✅ | 子进程隔离 + 禁导入门禁 + 7/7 注入全拒（独立复跑）；环境报告含 commit digest/加载模块/script sha256 |
| ARCH-05 全输入覆盖 | ✅ | 五桶全分类、unresolved 阻断、聚合前拒绝、verbatim；Class B 位置配对对勘正对 |
| ARCH-06 投影恢复协议 | ✅/F-5 | checkpoint 分离持久 + stale 围栏 + freshness 五态；发布面接线留票（已申报）；失败类别不完整（F-5 P2） |
| ARCH-07 回退兼容窗口 | ⚠️/F-3 | 从冻结全量 store 导出 + 独立反向校验 + 编号/幂等身份保留 ✅（case ⑦/rollback_variants 测试）；**activate 侧缺对称 digest 复检——F-3 P1**；存储格式回退承诺边界如实（guard_state_note） |
| ARCH-08 基线更新约束 | ✅ | 迁移全家族零 guard 基线写入（grep 实证；proof-pack 仅断言面） |
| ARCH-09 锁释放与取消 | ✅ | owner token + epoch 双验证；异主拒绝不释放（case ⑨ 全路径测试） |
| ARCH-10 证明包最低内容 | ✅ | 八节齐备 + 独立性声明含共享依赖与残余风险（非「独立：是」，测试断言钉死） |

---

## 6. 复审指引（给 Coordinator / Developer）

1. **修复范围最小集**：F-1（两腿锁内 epoch/状态重校验）+ F-2（`dict(store)` 保键）为合并前置；F-3/F-4 强烈建议同批（F-4 的两条交错用例是 F-1 修复的直接验收钉）；F-5~F-7 可批内或登记遗留。
2. **复审轮次**：R1 MUST 逐条比对本轮 findings（已修复/未修复/新引入），复跑三件套（49 用例 + 回归 105 + 负向 7）+ 本报告两个复现脚本的修复后反演（F-1 复现应变为结构化拒绝；F-2 复现应 append ok 且 `duplicate_acceptances` 保留）。
3. **真实切换票前置**：F-1/F-2 未闭合前，**不得**派发真实切换授权（本票红线未破——切换未执行；两 P0 恰在切换后才暴露杀伤面）。
4. DEC-238/RISK-059 为 Coordinator 待写回项——本审查检索 `.governance/` 无此二者（与「待写回」申报一致）；建议写回口径吸收本报告 F-1~F-4。

---

## 7. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 = 0 | ❌ **P0 = 2 → NEEDS_CHANGE** |
| 5 维度全覆盖 | ✅ §1.1-1.5 逐项有结论 |
| 每条发现标注级别 | ✅ F-1~F-12 全带 P0~P3 + 行号 + 证据 |
| 设计一致性检查 | ✅ §5 十条款逐条比对 |
| AI 专项 5 项 | ✅ §4 全项完成 |
| 事实依据红线 | ✅ 结论全部锚定文件行号/命令输出/测试结果/复现记录；两个 P0 为活体复现非推断 |

**REVIEW-FEAT-061-CODE-R0 · 结论：NEEDS_CHANGE · unresolved_blockers = 2（F-1, F-2）**

*审查方法披露：逐行读四个模块 + diff 全文 + 三测试文件 + fixture；独立复跑 49 用例/回归 105/负向套件 7；两个 P0 以隔离 temp 世界确定性复现（seam 技法，未触碰真实 `.governance/`——全程只读）；镜像解析器与真实 `_split_row` 逐行比对；真实热文件 DEC-194/214 双对与 8 变体行 grep 实证。复现脚本位于审查临时目录（`%TEMP%\feat061_r0_repro_p0a.py` / `p0b.py`），未入仓。*
