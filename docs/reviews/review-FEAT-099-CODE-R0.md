# FEAT-099 CODE R0 — 实施面独立代码审查报告

- **审查对象**：FEAT-099（U1 DSH 宿主级执法接线 PoC）实施面——变更 6 文件 + 新增 4 文件（git diff HEAD + untracked；快照 SNAP-FEAT-099-R0-20261027T130703 覆盖 11 文件）
- **Reviewer**：Code Reviewer（独立子代理；不轻信 Developer 声明，全部关键判据亲手重跑）
- **审查日期**：2026-10-27
- **设计依据**：`docs/architecture/feat-099-dsh-host-enforcement-poc-design.md`（R1+，implementation_authorized=true）；设计审查链 REVIEW-FEAT-099-DESIGN-R0/R1（AWN/0 终态）

---

## 1. 审查范围与方法

1. 全读 `lib/dsh-native/guard.js`（486 行）、`test_enforcement_guard.py`（467 行/19 tests）、`strategy-projection.json`、U7 逃逸面清单（47 行）、S4 探针驱动（239 行）。
2. 逐文件 diff 核验：`lib/index.js`（+21/-3）、`enforcement.py`（+23/-6）、`host-contract.json`（+17/-1）、`adapter-manifest.json`（+5）、`SKILL.md`（1 行）、`README.md`（+1）、`test_dsh_compat.py`（+8/-6）。
3. **亲手重跑**（非采信日志）：guard 19 tests、FEAT-095 执法族 20 tests、dsh_compat 全量 149 tests、WriteSideHomeConvergence 类、S4 探针完整复现（V0-V8 + F3）。
4. 时间线取证：s8_full.log mtime 12:58:41 vs test_dsh_compat.py 修复 mtime 13:03:42。

## 2. 偏差①-⑦裁定表

| # | 偏差 | 裁定 | 理由 |
|---|---|---|---|
| ① | 能力缺失降级 INFO（设计原文 warn） | **接受** | FX-JS-03「每交付失败恰好一条 warn」契约由 `test_capability_miss_degrades_with_one_info` 机器守护（warns==[] 且 infos==1）；注册故障保持 warn 分层正确；能力缺失是 probe/mock/宿主重构态的已知形态（dsh 宿主恒挂 dsh-tools） |
| ② | 活体模型会话 NOT_RUN | **接受** | manifest/README/SKILL 三处如实披露「live model session untested」；in-process 真实管线 + 类型面双证据替代成立（V1 isError + F3 reason 前缀 + 后续 guard 不复活均亲手复现） |
| ③ | V8=5ms 为 in-process 值 | **接受** | 口径如实（v8_windowMs=5 复现一致）；真实宿主 boot 窗口未测已在 C0/披露面登记；C0「已知空窗非故障」定性不依赖时长值 |
| ④ | manifest 新键不在 RUNTIME_CAPABILITY_KEYS 封闭集 | **接受+P3 登记** | 宽松放行带 note+evidence 属披露式添加、不过度声明；键集统一票应登记候选（P3-F4） |
| ⑤ | V2 toolBodyRan 探针弱化 | **部分拒绝 → P2-F2** | 实况比披露更糟：marker 探针**无效**（见发现 F2）——`toolBodyRan` 字段恒 false，不能作「工具体未执行」证据；V1 主结论由 isError+管线契约+F3 支撑仍成立 |
| ⑥ | test_dsh_compat probe 通用化重写 | **接受（代码面）** | diff 仅 rewrite 正则通用化（单文件 bridge.js → dsh-native/*.js）+ libUrl 变量提取；export 断言面不变；重跑该文件 149 passed 含本类 5 tests + 23 subtests 全绿。**但其引出 P1-F1（修复后全量未复跑）** |
| ⑦ | 投影文件名钦定 `.governance/enforcement-expected-revision.json` | **接受** | 与设计 §2.1 fixture→生产切换点一致（guard 读面接口不变），EXPECTED_PROJECTION_REL 单点定义 |

## 3. 代码发现（分级）

### P1-F1（blocker）：S8「全套件全绿」声称证据失效——修复后全量未复跑

- `s8_full.log` L7933-7935 终态：**`Ran 5127 tests in 1381.970s` → `FAILED (failures=12, skipped=2)`**——与 Developer「全量 5127 逻辑终态全绿」直接矛盾。
- 12 failures 全部为 `WriteSideHomeConvergenceTests.test_writer_case_table_agrees_with_lib_index` 的 12 个 subtest，traceback = `ERR_UNSUPPORTED_RESOLVE_REQUEST: "./dsh-native/guard.js"`（偏差⑥ rewrite 修复前的失败形态）。
- **时间线证实**：log mtime 12:58:41 < `test_dsh_compat.py` 修复 mtime 13:03:42——日志是修复前快照；修复后仅单文件复跑（149 绿，本审查复现），**全量 5127 未重跑**。
- 设计 §6 S8 判据「全套件回归零退化」因此**无当次证据**。修复面收窄（12 failures 同族同修复），但审查不采信推断性全绿。
- **解除路径**：重跑全量（约 23 分钟）拿到绿终态（或如实降级 S8 声称并留票）。

### P2-F2：S4 探针 marker 判据无效（恒 false）——`toolBodyRan` 不可用作证据

- `s4_probe_driver.py` L49 `const marker = 'MARKER'`（字面量），而工具 execute 写入 `__T_MARKER__`（被替换为 temp 绝对路径 `t/body-ran.marker`，L61/L213）；`rmSync(marker)`/`existsSync(marker)` 查的是 cwd 下不存在的 `MARKER`。
- 实证：V2（匹配放行）输出 `value: "started subagent probe (subagent)"`（execute 返回值，证明工具体已执行）却报 `toolBodyRan: false`——探针输出与事实自相矛盾。
- 影响评估：V1「拒绝且工具体未执行」结论**仍成立**（isError=true + dsh-tools 管线契约「denied call 工具体不执行」+ F3 deny reason 前缀 + 后续 guard 不复活，四证独立于 marker），但报告引用 `toolBodyRan: false` 作为「工具体未执行」证据的表述失效。
- **解除路径**：L49 改 `const marker = __T_MARKER__`（模板占位符）并复跑探针——预期结论不变、证据变有效（evidence generator 非产品文件，修复零产品面）。

### P3（非阻断，3 项）

- **F3**：`test_verify_workflow.py` `TestFeat095EnforcementBoundaries` docstring（L27108-27109）「protocol+CLI face only — no host-level interception is claimed anywhere」时点措辞与 FEAT-099 后事实不同步——enforcement.py 模块 docstring 已按设计 §5.3 更新，该测试类 docstring 不在更新点清单内。建议顺手同步一句「dsh 除外（FEAT-099）」。
- **F4**：`enforcement_host_guard` 键不在 RUNTIME_CAPABILITY_KEYS 封闭集（偏差④关联）——键集统一/收紧票登记候选（生产化批）。
- **F5**：V6 声称 p95=0.187ms 为时点值（本审查重跑得 p95=0.282ms / max 1.539ms / e2e 中位 0.851ms——同数量级噪声，远低于 10ms 预算）；建议 Developer 报告措辞注明时点或带区间。

## 4. 代码质量面核验（通过项）

| 面 | 判定 | 证据 |
|---|---|---|
| JS×Python parity 真实性 | ✅ | 网格 6 场景 decision/reason_code/detail/remedy **字节级**断言（`test_js_python_parity_over_fact_grid`），亲跑 19 passed；判定器模板消费同一单源投影 |
| 字节断言真守护 | ✅ | `test_fixture_bytes_equal_print_strategy_stdout`：fixture 逐字节 ≡ `--print-strategy` stdout（1917B 单行 JSON 亲读核） |
| 缓存五失效面 | ✅ | stat 变化/TTL 30s/开关变化/根变化/off 零 stat 零状态——`GuardCacheTests` 两测逐步断言 reads/stats 计数 [1,1,2,3,4]，Windows mtime 粒度用例（size 变化）在册 |
| never-throw 承诺 | ✅ | `apply()` belt try-catch 包裹注册（lib/index.js diff）+ `registerEnforcementGuard` 内部全路径结构化返回；deny 是管线一等语义非行异常（§3a-2 落地） |
| off 零注册零副作用 | ✅ | `test_off_registers_nothing`：guardCalls==0、logs==[]；view() off 分支不 stat |
| 注入安全 | ✅ | 锚正则锚定（task=\S+ / rev=-?\d+ / channel 枚举 / actor=\S+）；畸形锚三变体 fail-closed deny（C3 测试）；arguments 非 object/prompt 非 string 防御（promptFirstLine） |
| fs 读面限定 | ✅ | GOVERNANCE_FILES 三文件 + EXPECTED_PROJECTION_REL，仅 readFileSync 只读；无越域读 |
| 接线独立性 | ✅ | guard face 在 apply() 独立 try 块，与 preset delivery 不互扰；三服务边界声明（two→three）同步 lib/index.js L69-75 |
| C0-C7 行为规格 | ✅ | C1（corrupt 投影 deny）/C3（畸形锚 deny）/C4（非法开关 deny）/C5（off 零漂移）/C6a（无锚+无根 allow+一次性披露）/C6b（带锚+无根 deny）/C7（无锚 allow+计数）逐条有测试且亲跑绿 |
| 契约面 | ✅ | host-contract `warn_only_scope` + `enforcement_guard` 12 子字段覆盖设计 §3a-2 五要素（原语/工具面/规则/规格/开关）并扩展（governance_root/registration_fault/capability_miss_code/window/anchor_protocol/status）；SKILL L238 与 manifest/README 措辞均按 §5.3「证实时」列且未测面如实披露（不过度声明） |
| 隔离纪律 | ✅ | driver DSH_HOME 双重重定向（in-script env + subprocess env belt）+ TemporaryDirectory fixture；亲跑复现无真实 home 触碰；`D:\app\dsh`/npm 面只读 |

## 5. 抽验重跑记录（Reviewer 亲手，2026-10-27）

| 项 | 命令/方法 | 结果 |
|---|---|---|
| guard 判定面 | `pytest test_enforcement_guard.py` | **19 passed**（含 parity 网格 + 字节断言 + C0-C7 + 缓存 + 接线） |
| 既有执法族 | `pytest test_verify_workflow.py::TestFeat095EnforcementBoundaries` | **20 passed**（投影扩展零判定语义退化） |
| dsh_compat 全量 | `pytest test_dsh_compat.py` | **149 passed, 101 subtests**（含偏差⑥修复后 WriteSideHomeConvergence 5+23） |
| S4 探针完整复现 | `python .codex-sandbox/FEAT-099/s4_probe_driver.py` | mount ok / **V1 拒绝（reason 文案与 Python 模板逐字一致）** / V2 放行（value 证 execute 执行）/ V3 四构造全符 / V4 fork 同拒 / V5 corrupt deny / **V0① execution 字段含 `arguments`**（8 键实证）/ V6 p95=0.282ms / V8=5ms / F3 前缀+单调性 ✓ |
| 日志时间线 | mtime 对比 | s8_full.log 12:58 < 修复 13:03 → P1-F1 定性依据 |

## 6. 结论

**NEEDS_CHANGE — unresolved_blockers = 2**

- **P1-F1**：S8 全量回归「全绿」证据失效（所引日志终态 FAILED failures=12；修复后未复跑）——重跑全量拿绿终态后解除。
- **P2-F2**：S4 探针 marker 判据恒 false（L49 字面量 vs L61/L213 绝对路径不一致）——一行修复+复跑后解除；主结论（V1 拒绝+工具体未执行）由 isError/管线契约/F3 独立支撑不受影响。

架构与代码质量面无阻断发现：切片最小性、单源投影+字节守护、C0-C7 规格、缓存设计、never-throw/off 零漂移、隔离纪律、契约与披露诚实度均达设计 R1+ 要求；七偏差中五项全接受、①③④⑦披露充分、⑤升级为 F2、⑥接受但引出 F1。

**复审建议**：两 blocker 均为证据链/探针面修复（预计 ≤1 行产品外改动 + 23 分钟全量跑），修复后走 delta 复审（round 1）聚焦：全量绿终态 log + 探针 marker 行 diff + 复跑 V1/V2 输出。

---
*Reviewer 不改被审文件、不写 REVIEW- 机录（归 Coordinator review-record 通道）。报告 sha256 将由 Coordinator 机录时钉定。*
