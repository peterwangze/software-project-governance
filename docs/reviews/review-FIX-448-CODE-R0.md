# FIX-448 CODE R0 独立审查报告（M1 实施批：迁移协调层+dry-run）

- Task ID：FIX-448 · Round：R0（CODE 链首轮）
- Reviewer：Code Reviewer（独立实例；承接 Coordinator 派单，指令隔离——只执行本审查）
- 时间窗：2026-10-23 12:0x~12:2x +08（UTC 04:0x~04:2x）
- 基准：设计 `docs/architecture/evidence-hot-cold-compaction.md`（SHA 头 `7E1CC4DC`）+ `docs/reviews/review-FIX-448-DESIGN-R0.md`（AWN/0 批准面）+ DEC-368④（D1 安全子集；M1=零热表触碰）

## 结论：NEEDS_CHANGE（unresolved_blockers=1；P0=0 P1=1 P2=0 P3=4）

M1 的 **dry-run 面全部核实通过**（数字逐位一致/只读性证明/回归全绿/边界合规）；阻断点在 **apply 面的 I4 验证强度**——该面是模块自述"M2 dispatch 将运行的真实实现"，带着 P1-1 进入 M2 不可接受。修复面小（cold 盘面回读验证，约 +10~15 行 + 1~2 用例）。

## 对象绑定（SHA-256 独立复算）

| 文件 | SHA-256（头 8） | 状态 |
|---|---|---|
| `skills/software-project-governance/infra/evidence_migration.py` | `2193EEB5` | 新增（665 行；与派单绑定一致） |
| `skills/software-project-governance/infra/tests/test_evidence_migration.py` | `315E5463` | 新增（403 行/14 用例） |
| `.codex-sandbox/FIX-448/m1-report.md` | `A5315658` | 审查输入 |
| `.codex-sandbox/FIX-448/m1/dry-run-report.json` | 复算一致（数字层，见 §4） | 审查输入 |
| `docs/architecture/evidence-hot-cold-compaction.md` | `7E1CC4DC` | 仅 §14 末一行注记（正文规范零改动亲读确认） |
| 真实热表 `.governance/evidence-log.md` | dry-run 前=`F3C91B9A`/2,154,971 B → 后=**逐位相同** | 只读证明 ✅ |

## Findings

### P1-1（阻断）：`cold_verified` 阶段的验证是内存恒等式，非盘面验证——I4 "cold verified BEFORE hot CAS" 声明强于实现

- **位置**：`evidence_migration.py` L472-477（`apply_evd_plan` cold verify 段）
- **事实**：`_sha256_bytes(bytes(rebuilt)) != _sha256_bytes(b"".join(raw[i["byte_offset"]:…] for i in movers))` ——左侧 `rebuilt`（L446-453）与右侧拼接**同源于内存 `raw` 切片**，除 `row_sha256` 先行失败外该不等式**恒为 False**；它不读取任何磁盘字节。原语 `_write_archive_file_never_overwrite` 首次创建路径（返回 `"created"`）**无盘面回读**；仅 EEXIST 幂等分支经 `_verify_existing_archive_target` 有逐字节盘面判定（`archive_migration_engine.py` L331-357）。因此 hot CAS（L488 `os.replace`）在 cold 段磁盘字节未经读回验证的状态下执行。
- **违反**：模块 docstring L36-37 与 m1-report §3 I4 行宣称 "cold is fully published and verified BEFORE the hot CAS"；设计 §8.1 步骤 5 的 cold verify 语义。fsync 降低损坏概率但"verified"是强声明——M2 将对真实 2.15 MB 热表执行。
- **修复方向**：cold publish 后逐 segment **盘面回读**——文件整体应等于 `header+"\n"+join(剥LF行)+"\n"`（原语 L487 拼接式）且 payload 部分（去 header 行）与 movers 原字节逐段等价；任一不符 → 结构化 refusal（`identity_changed`/`byte_conservation_failed`），hot 不动。约 +10~15 行。
- **不阻断 dry-run 面**：M1 交付的 dry-run 正确性不受影响（本 finding 仅 apply 面）。

### P3-1：`test_v2_overlaps_refused` 名不符实——planner 的 overlap/conservation refusal 路径零真实覆盖

- 测试 L254-264 内联重建 guard 逻辑断言 sabotage 可检测（`overlap=True`），从未经过 `plan_evd_compaction` 真实执行（注释自认不可行）。`byte_conservation_failed` 的两个 refusal 分支（L302-305/L308-312）无任何测试触达。修复：sabotage 后调用可重构的守恒检查入口，或注入可触发真实 refusal 的畸形输入。

### P3-2：I4 顺序性无故障注入——cold publish 失败（原语 raise）时 hot 不动的世界未测

- V4 三世界均为事后恢复模拟；`BigTableMigrationError` 抛出路径（cold 失败→hot 原样→staging 可恢复）无测试。配合 P1-1 修复时补"cold 失败→hot 逐位不变"用例。

### P3-3：无尾 LF mover 行的 cold payload 字节边界不严格

- 原语拼接 `join(body_lines)+"\n"` 对无尾 LF 的 mover 行会加一个尾 LF（剥 LF 只对 `endswith("\n")` 生效）——该行 cold payload 比原字节多 1 B。当前 evidence-log 尾行恒为 prose（非 mover），实际影响零；但"payload = verbatim original row bytes"声明在该边界不严格。注记 + M2 重 plan 时机检（movers 均有尾 LF 可断言）。

### P3-4：`apply_evd_plan` 未包装原语异常为结构化 Refusal

- cold 冲突路径 raise `BigTableMigrationError` 以 traceback 冒出（exit≠0、hot 不动——fail-loud 语义保持），但 §7.2 接口契约期望 Refusal dict。包装为 `{"status":"refused","code":"archive_target_conflict",…}` 更符契约。

## I1~I7 逐条核验（亲读+测试+dry-run 三源）

| 不变量 | 判定 | 依据 |
|---|---|---|
| I1 原字节不可改写 | **PASS** | 实例=(source_sha256, byte_offset, byte_length, row_sha256)；切片 hash=原字节（L446-452+测试 `test_v2_i1_…`）；before 备份 L417；行不重渲染（P3-3 边界注记除外） |
| I2 canonical 单源 | **PASS** | `scan_row_families` 复用（L214-217），零新词表；fixture reason 池 pin（L169-184）；dry-run reason 分布与 archive 语义一致（120 would_archive/112 missing/250 active/416 out_of_range） |
| I3 活动全集热可达 | **PASS** | interval removal 只删 mover 区间（L286-295）；prose/retain 原样（`test_v2_hot_after_is_exact_interval_removal`+复跑 hot_after 算术自洽） |
| I4 cold 先验证→hot CAS→finalize | **PASS（顺序）/ FAIL（验证强度）** | 阶段机次序硬编码（publish L442-477 → hot CAS L481-497 → finalize L500-504）无跳阶；但"verified"=内存恒等式（**P1-1**） |
| I5 FIX446 原语保持 | **PASS** | cold 唯一入口 `_write_archive_file_never_overwrite`（L466）；幂等 skip 测试（L315-331）；无 exists-then-replace；原语本身零改动（git 边界） |
| I6 门只报告 | **PASS** | L314-320 报告 `blocked`；测试 `test_i6_capacity_reported_not_bent`；650,000/400,000 常量 mirror |
| I7 独立 transaction_id | **PASS** | `evdt-<utc>-<rand>`（L392-394）；不冒用 op-*；测试断言前缀（L312） |

## --execute 硬门禁核验：PASS

L381-388 函数最前 `FIX448_EVD_M2_EXECUTE` 检查；缺 flag → 结构化 refusal + staging 不创建（测试 L275-280）；CLI 面无旁路参数；直接 import 后设 env 属 M2 授权语义本身（约定级门禁——设计意图即环境变量=独立批授权标记）。

## 独立复跑实数（UTC 2026-10-23T04:1xZ，仓库根）

| 命令 | 结果 |
|---|---|
| `evidence_migration.py --dry-run`（真实热表） | exit=0；moved=120/207,338 B；retained=1178；hot_after=1,947,633 B；capacity=blocked；热表前=`F3C91B9A`/2,154,971 B 后=**逐位相同** |
| dry-run 产物 vs `m1/dry-run-report.json` | moved/hot_after/retained/hot_sha/reason 分布前 5 全部逐项一致 |
| `pytest test_evidence_migration.py` | **14/14 passed**（0.90s） |
| `pytest test_summary_only.py` | **27/27 passed** |
| `pytest test_archive.py`（全量） | **206 passed + 1 skipped + 8 subtests passed**（共享归档腿零漂移证实） |
| `git status --porcelain -uno` | 仅既有暂停 WIP 两行（M）——本批零 stage/commit/push ✅ |

四族判定与设计 §3.3/§11 S2 对照：EVD 120/207,338（逐位）、missing 112/223,822（逐位）、REVIEW 18/6,700、RECO 5/1,612、TRIAGE 8/2,844、四族合计 151/218,494（一致）；hot_after=2,154,971−207,338=1,947,633 算术自洽 ✅。M1 仅 EVD 可为 mover（FIX-446 硬化腿边界）与设计口径一致。

## NOT_RUN 如实性：PASS

`withdraw_new_segments`（§8.3）/V5 并发面/V9 撤销面声明为 M2+ 范围未实现（m1-report §8.3）；`--execute` 实现但门禁禁用——披露诚实，无冒充。

## 边界合规：PASS

审查过程只读（热表 SHA 前后自证）；只写本报告+scratch `.codex-sandbox/FIX-448/review-code-r0/`（dry-run-rerun.json）；不改被审对象；不 stage/commit/push；writer/hooks/source/registry/消费者 schema/GovernanceDataSource 零改动亲读确认（git 边界+模块 import 面核对）；暂停 WIP 两文件零接触；安装态/DSH 零接触。

## 通信异常披露

无——审查期间未收到其他 agent 的转包/委派消息。

## 复审请求（NEEDS_CHANGE → 同 Reviewer round+1）

修复 P1-1（cold 盘面回读验证）+ 建议 P3-2 随附用例 + P3-4 包装后，按 M7.4 复审必达注入本报告路径复审 round 1；P3-1/P3-3 可登记为 M2 前置清单项（不阻断复审通过判定，若修复方选择一并处理则验证之）。

*报告完。本文件为 FIX-448 CODE R0 审查唯一产出写面；未修改任何产品/治理/取证文件。*
