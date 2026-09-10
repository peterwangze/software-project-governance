# REVIEW-FEAT-018-CODE-R0 — 性能测量协议脚本（工作树 diff，commit 前置）

- **Round**: R0（首轮）
- **Reviewer**: Code Reviewer Agent（`agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行）
- **对象**: 未提交工作树改动（`git status --porcelain` 实测 = 恰 4 个未跟踪新文件，零已跟踪文件修改）
- **方法**: 只读审查——git 只读 + 逐行读全文 + 独立复算（统计面 10 项数值全部独立重算）+ 外部锚点交叉印证（§9.5 原文 / architecture-baseline R6 面 / archguard_ratchet R6 孪生 / facts §7.3 / 执行包 / FEAT-019 commit 自述口径）；测试与采样结果采信 Developer 声称并标注边界（§8）
- **日期**: 2026-09-10

## 终态裁决

> **APPROVED_WITH_NOTES（unresolved_blockers=0）**
>
> - P0 = 0；P1 = 0；P2 = 4（F-1~F-4，登记遗留候选，不阻塞合并）；P3 = 7（F-5~F-11）
> - 硬门槛 5/5 达成（§5）；AI 专项 5/5 完成（§6）；执行包 done_definition「审查确认测量不改引擎行为」**确认**（§3-⑹ 双通道核实）

## 0. 变更面清单（git status 实测）

| 文件 | 状态 | 面积 |
|---|---|---|
| `skills/software-project-governance/infra/perf_protocol.py` | 新增 | 857 行 |
| `skills/software-project-governance/infra/tests/test_perf_protocol.py` | 新增 | 281 行 |
| `skills/software-project-governance/core/perf-tolerance.json` | 新增 | 52 行 |
| `docs/requirements/perf-baseline-0.80.0.json` | 新增 | 269 行（repo-only，非产品面） |

与执行包 FEAT-018 `scope_guard`（perf_protocol.py）+「容差表文件入库」+「双命令基线报告产出」一致（execution-packets.json:513-639 实读）；测试文件属产品代码任务标准面。无越权文件。

## 1. 统计实现正确性（焦点①）— 核实通过，10/10 数值独立复算全中

**percentile 线性插值**（perf_protocol.py:115-132）：rank=(n-1)·p/100、`floor/ceil` 夹取、`data[lo]·(1−frac)+data[hi]·frac`——与 numpy `linear` 口径逐式一致；n=1 退化返回自身（docstring 显式声明 + 测试 test:69 钉死）；空样本 raise。**median**（:110-112）= `statistics.median` 再导出。**summarize**（:135-144）/ **split_cold_warm**（:147-152）边界（单样本→cold + 空 warm）有测试。

**独立复算（对照 perf-baseline-0.80.0.json，全部精确吻合）**：

| 面 | 报告值 | 复算 | 判定 |
|---|---|---|---|
| status median | 0.5215 | sorted[2]=0.5215 | ✓ |
| status p95 | 0.53114 | 0.5249·0.2+0.5327·0.8=0.53114 | ✓ |
| status warm_median | 0.5232 | (0.5215+0.5249)/2 | ✓ |
| status warm_p95 | 0.53153 | rank 2.85：0.5249·0.15+0.5327·0.85 | ✓ |
| summary median | 41.796 | sorted[2] | ✓ |
| summary p95 | 44.6627 | 42.8115·0.2+45.1255·0.8 | ✓ |
| summary warm_median | 41.31145 | (40.8269+41.796)/2 | ✓ |
| summary warm_p95 | 44.626075 | 41.796·0.15+45.1255·0.85 | ✓ |
| status decomposition 残差 | 0.419575 | 0.5215−0.101925 | ✓ |
| summary decomposition 残差 | 41.69279 | 41.796−0.10321 | ✓ |

冷暖边界（焦点①子项）：cold=该命令本会话首跑、warm=后续——§9.5 item 3「冷=新进程首跑；暖=同进程重复**或系统缓存后**」在逐进程采样口径下取「系统缓存后」分支，caliber note 1（:92-94）如实披露此口径选择。实现/披露一致。

## 2. importtime 解析健壮性（焦点②）— 主路径核实通过；探测失败静默退化为 F-1（P2）

- 解析器（:158-195）：`|` 三段拆分、头行 `import time:` 前缀剥离、int 解析 ValueError 捕获、缩进深度 `indent//2`——对照真实 CPython stderr 形状（fixture test:45-52 与引擎实测 top 面 `checks.loop_runtime_claims` 等真实模块名互证）正确。坏行不静默丢弃：`return_skipped=True` 披露计数（test:108-113 断言 header+pipe-less 共 2 条被披露）——「测量协议永不静默丢弃未理解数据」的自我约束成立。
- `import_totals` 取 self_us 求和（cumulative 会双计嵌套）——注释（:198-203）与事实相符；`top_imports` 按 self 排序（真实单导入成本）。
- **F-1（P2）**：`probe_importtime`（:552-562）不检查 `returncode`——探测子进程失败（如引擎异常退出）时 stderr 为空/错误文本 → `parse_importtime` 返回 `[]` → 报告 `import_events=0 / self_total_ms=0 / decomposition 残差=全墙钟`，**无任何失败标记**（对照：`probe_sys_modules` 失败显式返回 `None`，报告面留 null）。零值与「真的零导入」不可区分。影响面：分段报告/decomposition 是观测面非门禁面，故 P2 非 P1；建议 returncode≠0 时置显式 degraded 标记或抛错（exit 1）。
- 空输出同上并入 F-1（`parse_importtime("")` → `[]`，静默）。

## 3. 容差判定逻辑（焦点③）— 核实通过

- **band 公式**（:241-264）：`band = max(baseline·rel, abs_floor)`——相对容差主导常规基线、绝对秒下限放宽小基线（防抖动假 FAIL），与 §9.5 item 5（median ≤10%/P95 ≤25% 初值假设）+ 任务简报「相对容差+绝对秒下限」一致；4 个 judge 单测算术独立复算全对（0.06/0.10/0.15/0.05 四条 band 路径）。
- **两态路径**：`delta > band → FAIL`（band 内含边界 PASS；变快恒 PASS——回归门语义正确）。超容差 → CLI exit 1（:842-851）= §9.5 item 5「超容差=切片验收 FAIL」✓。退出码语义与模块 docstring（:49-51）一致（breach 归入非零退出，0 仅在 `--baseline` 全 PASS 时返回）。
- **judge_face = warm median/P95，cold 只观测不判定**（容差表 :6 + `compare_against_baseline` :355-381 只取 `wall.warm_*`）——设计选择在容差表显式声明，测试 test:208-216 用双侧同形状（报告 commands 形状）验证了「单测契约=真实数据流」防漂移主张（:360-364 注释与实现相符）。
- **r6_threshold_fill 结构对齐**（焦点③子项）：`wall_ms_rel_median/wall_ms_rel_p95/abs_floor_s/import_count_max_delta` 四键在 `validate_tolerance_table`（:344-352）强制存在；`architecture-baseline.json:538-544` 实读——`r6_startup_budget.threshold` 当前确为 `null`、note 明言「FEAT-018's tolerance table fills threshold」、probe 串逐字符一致（`python -I -B -c 'import verify_workflow' (isolated)`）。「advisory until R6 wiring consumes it, never fatal in v1」与 FEAT-019 已交付的 R6 never-fatal 语义（REVIEW-FEAT-019-CODE-R0 §1-R6）一致。
- `calibration_status: initial-hypothesis` 如实标注（§9.5 item 5「作为假设标注待校准」原文级一致）——**未把假设包装成实测事实**，符合反过度宣示纪律。
- parallel-observed 档标注「observation-only caliber, never a gate」——与 RISK-048 处置（套件级结论以静默窗口复跑为准）方向一致。
- 边界备注（非发现）：`--baseline` 判定用当前运行 `--load` 选档而不校验旧基线 load_class → F-2。

## 4. 采样方法学（焦点④）— 核实通过

- **交错序真实性**：`interleave_sample`（:606-639）round-robin（r1: cmd1,cmd2…; r2: cmd1,cmd2…），`sample_order` 逐次 append 并原样进报告——已提交基线的 `sample_order` = `[status,summary]×5` 真交错实录 ✓。单实现自采样口径（docstring :9-12「interleave is command-vs-command + round order preserved, ready to become A/B」）如实披露——当前无新旧对可 A/B，这是 §9.5 item 2 在单实现切片下的诚实降级而非冒充。
- **子进程构造**：`COMMANDS`（:86-90）argv 列表直传（无 shell）；`run_command_once` perf_counter 计时、timeout=900、returncode≠0 → RuntimeError → CLI exit 1（fail-closed）。
- **-B 变体口径**：采样 argv、importtime 探测（`[argv[0], "-X", "importtime"] + argv[1:]` 保留 -B）、sys_modules 探测（`-I -B`）三处全带 -B——caliber note 2 属实；AUDIT-151「measurement-safe variant」口径引用正确。
- **探测隔离**：importtime 探测在全部墙钟样本之后每命令跑一次（:636），仪表开销不入墙钟样本——caliber note 3 属实。
- **caliber_notes 六条逐条对照实现**：①冷暖定义=:147-152 ✓；②-B=:86-90 ✓；③探测隔离=:606-639 ✓；④P95 线性插值=:115-132 ✓；⑤分解近似=:220-235（residual 合并披露，不猜）✓；⑥负载协变量=--load/:399-415/容差表双档 ✓。**六条全部与实现一致，无一条是装饰性文案**。
- ⑥的数值归属核实：facts 文档 architecture-audit-facts-0.80.0.md:428 实读——0.49s/0.56s 为 FIX-270 串行时点实测，4.04s 为「本会话为并行治理 agent 负载环境」单次实测——「0.49~0.56s serial vs 4.04s parallel-observed」**有文档级依据**，非杜撰归因。
- 环境面（:399-415）：python 版本/平台/核数/cwd/git_head/负载类+注记/timestamp——§9.5 item 4「median+P95+环境信息」齐备；同机同树主张由 cwd+git_head 锚定（报告 git_head=c443757=当前 HEAD ✓）。

## 5.（占位）——见 §4/§6 编号连续性说明

（为保持 findings 编号与口头汇报一致，本节无独立内容；五维结论见 §7。）

## 6. 测试真实性 19 例 + stdlib-only + 零引擎改动 + 存量归属（焦点⑤⑥⑧）

### ⑤ 测试 19 例真实性 — 核实通过
- **19 例清点**：PercentileStatsTests 4 + ImporttimeParseTests 3 + ToleranceTests 5 + ReportSchemaTests 3 + SlowPathInjectionTests 1 + CliPlanTests 3 = **19** ✓。
- **注入面无外部依赖伪装**：唯一慢路径测试 `test_sample_command_uses_injected_runner`（test:222-246）用 `patch.object(pp, ...)` 注入**自家模块函数**（run_command_once/probe_importtime/probe_sys_modules）——先例声称核实：`test_archguard_ratchet.py:261` 确以同法 patch `ar.r5_live_faces` ✓。patch 语义正确（interleave_sample 经模块全局名解析，运行时补丁生效）；断言有实质鉴别力（3 次调用、零 importtime 污染、样本/探针数据流全查）。
- **入库锚定测试真实**：`test_committed_tolerance_table_valid_and_r6_aligned`（test:148-165）读**真实提交的** core/perf-tolerance.json 过 validate + §9.5 初值上界 + 双负载档存在性——容差表与 §9.5 的一致性被测试钉死，非仅声明。
- 断言算术抽查（percentile 4.8/38.5/1.76、judge 四路径、importtime depth=2/skipped=2）全部独立复算正确。
- **F-4（P2）**：CLI `main()` 面零覆盖——exit 2（arg/schema 错）、exit 1（采样失败/**容差 breach**）、`--init-tolerance` 写盘、`--out` 写盘均无测试。纯函数面+计划面覆盖良好，但 breach→exit 1 这条验收关键路径只在函数级（compare/judge）覆盖，未到 CLI 终态。standard profile 核心路径判据大体满足，此为缺口非达标失败。

### ⑥ stdlib-only + 零引擎改动 — 双通道核实通过
- **stdlib-only**：perf_protocol.py imports = argparse/hashlib/json/math/os/platform/statistics/subprocess/sys/time/datetime/pathlib/typing（:54-68，全文无 deferred import）——全部 stdlib ✓；测试文件仅 +unittest.mock/pathlib/sys ✓。执行包 non_goal「不引入第三方依赖」达成。
- **零引擎改动双通道**：(a) `git diff --stat HEAD` 为空 + git status 仅 4 未跟踪文件——已跟踪文件零修改；(b) 引擎 grep `perf_protocol` 零引用——不存在反向接线。且 perf_protocol 自身**不 import 引擎**（只 spawn 子进程）与不 import 兄弟任务模块——R2 反向依赖面零新增（见 ⑧ ratchet 结构印证）。模块边界（evolution §10 REFACTOR-perf-protocol 行「must not be imported by the engine, and must not import sibling task modules」）双向达成。

### ⑧ 存量失败归属 — 采信 + 算术闭合 + 边界标注
- **算术双闭合**：FEAT-019 commit c443757 自述「全量 **2,278** 恒等、健康 **31** 恒等」（git log 实读）；本任务 +19 测试 → 2,278+19 = **2,297** ✓；30F+1E = 31 = 26（AUDIT-151 三族：bash/WSL×24+GBK×1+已知缺陷×1 的 26 失败口径，EVD-974「2,194 收集/26 失败/1 跳过」）+ 4（FIX-300 审查文档引发 loop-runtime BLOCKED）+ 1（RISK-048 族）✓。
- **采信边界（如实声明）**：本 Reviewer 未复跑全量套件（只读审查边界 + 全量 ~361s 成本）；「三次采样 ±5%」中提交报告仅含一会话 5 样本，另两次运行为 Developer 证据行声称，未独立复现。「manifest/ratchet 双 PASS」同样采信——但**结构性佐证独立完成**：manifest `product.entries` 含 `infra/`、`core/` 目录型条目（core/manifest.json:139-141/:87-89）自动接纳新文件；ratchet R1（引擎未动）/R2（两新 py 零引擎引用，实测读 import 面）/R4（只计引擎主文件 print，:481-505）/R6（见 §3 import_count 196+sha256 精确交叉）/R7（基线文件未动）逐规则推演均无违规路径。若后续 EVD 行附命令输出原文，可升格为完全实证。

## 7. 审查维度结论（5/5）

| 维度 | 结论 | 依据摘要 |
|---|---|---|
| 1 正确性 | **PASS** | §1 统计 10/10 独立复算；§2 解析/§3 容差逐行核实；边界缺口 F-1/F-5/F-6 均非阻塞（观测面/不可达路径/库误用路径） |
| 2 安全性 | **PASS** | 全程 argv 列表子进程（无 shell/无注入面）；`--sample` 键白名单限 COMMANDS；探测串路径经 `{path!r}` repr 转义（与 archguard 生产孪生同法）；无密钥/无敏感数据外泄（报告含 cwd+git_head 属测量元数据） |
| 3 可维护性 | **PASS** | 命名自明、函数短小、caliber 披露式 docstring 贯穿；COMMANDS 注册表即扩展点（任务简报「可参数扩展」）；F-9 死参数/F-11 main 长度为卫生项 |
| 4 性能 | **PASS** | 测量工具自身开销受控（探测带 timeout 900/120；F-7 冗余探测 ~1s×(N−1)）；排序 O(n log n) 微不足道；无 N+1/无算法问题 |
| 5 测试覆盖 | **PASS（含 F-4 缺口）** | 19/19 真实（§6⑤）；纯函数面+注入面+入库锚定面齐备；CLI 终态路径缺口登记 F-4 |

## 8. AI 代码专项 5 项检查（5/5 完成）

| # | 检查 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 生产代码零 mock/零测试分支；补丁全部位于测试 with 块内（test:236-239） |
| 2 | 硬编码返回值 | **无假成功** | 容差数值显式标 `initial-hypothesis`（非实测伪装）；`probe_sys_modules` 失败返 None（诚实降级）；关联弱点 F-1（importtime 失败零值无标记——是披露缺口，非伪造成功） |
| 3 | 幻觉 API 调用 | **无** | 引擎子命令实存：`status`（verify_workflow.py:23417）、`check-governance --summary-only`（:23472）；importtime 格式与真实 CPython stderr 互证（基线 top 面全部为仓内真实模块，`checks/review_domain.py` 等 17 个 checks 模块 glob 实存） |
| 4 | 未实现 TODO | **无** | 两文件 grep TODO/FIXME/XXX/HACK 零命中 |
| 5 | 过度实现 | **无** | `--sample` 双语义有执行包验收命令（`--sample status,summary`）+ 任务简报（`--sample N`）双锚；decomposition 合并残差是「披露而非猜测」的克制实现 |

## 9. 发现清单（P0~P3，全部带 file:line）

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | perf_protocol.py:552-562 | `probe_importtime` 不查 returncode：探测失败 → 空解析 → importtime 面静默全零（import_events=0/self_total=0/残差=全墙钟），无降级标记，与「真零」不可区分 | returncode≠0 或空 stderr 时置显式 degraded 字段或 raise（exit 1） |
| F-2 | **P2** | perf_protocol.py:805-825 | `--baseline` 判定按当前 `--load` 选容差档，不校验旧基线 `environment.load_class`——跨负载类比较（如新串行 vs 旧并行基线）会用串行 band 判并行污染基线，可能假 PASS；容差表 note 只警示未强制 | compare 前比对双侧 load_class，不一致 warn 或拒判 |
| F-3 | **P2** | perf_protocol.py:766-779 | `--init-tolerance` 无守卫覆盖默认路径（已入库 core/perf-tolerance.json）——校准后误跑即静默重置回初值假设 | 覆盖已存在文件时要求显式 `--force` 或改写非默认路径 |
| F-4 | **P2** | test_perf_protocol.py（缺失面） | CLI `main()` 终态零覆盖：exit 2（arg/schema）、exit 1（采样失败/容差 breach）、`--init-tolerance`/`--out` 写盘均无测试；breach→exit 1 验收关键路径仅函数级覆盖 | 补 main() 级测试（可复用注入手法 patch interleave_sample/build_report） |
| F-5 | P3 | perf_protocol.py:366-368 | `compare_against_baseline` 对任一侧缺失的命令静默 `continue`——判定覆盖面收窄不可见 | 报告 skipped 命令清单 |
| F-6 | P3 | perf_protocol.py:705-708, 371-379 | 退化路径：warm 为空时 `_print_summary` 对 None `:.3f` 格式化崩溃；旧基线 warm_* 为 None 时 judge TypeError 未捕获（CLI 不可达——repeat≥5 强制；库误用可达） | 打印前判 None；compare 前校验双侧 warm 非空 |
| F-7 | P3 | perf_protocol.py:636-637 | `probe_sys_modules(INFRA_DIR)` 每命令跑一次但结果恒同（~1s×(N−1) 冗余；孪生 archguard 用 lru_cache） | 模块级缓存或单次探测共享 |
| F-8 | P3 | perf_protocol.py:293-298 + judge_face | warm 面判定的 P95 样本 n=repeat−1=4（rank 2.85 被 max 主导）——统计上弱；§9.5 未规定 warm-only P95，属可辩护设计选择 | 判定轮 repeat_min 提至 6 或在容差表披露 warm n=4 的口径 |
| F-9 | P3 | perf_protocol.py:530-538 | `run_command_once(importtime=True)` 参数为死代码（全仓无 True 调用；探测走独立 probe_importtime），docstring「used only by the separate probe」与实际路由不符 | 删参数或让 probe_importtime 复用该开关 |
| F-10 | P3 | perf_protocol.py:344-352 | `validate_tolerance_table` 对 r6_threshold_fill 仅查键存在，不验数值（如 import_count_max_delta 数值性/非负） | 补数值校验 |
| F-11 | P3 | perf_protocol.py:729-853 | `main()` ~125 行超出 50 行指引（argparse 声明+dispatch，CLI 惯例可接受） | 可选拆分 `_cmd_init_tolerance`/`_cmd_sample` |

## 10. 硬门槛裁决

| 门槛 | 判定 |
|---|---|
| P0 阻塞问题数 = 0 | **✓（0）** |
| 5 维度 100% 覆盖 | **✓（§7 五行逐一有结论）** |
| 每条发现标注级别 | **✓（F-1~F-11 全带 P2/P3）** |
| 设计一致性检查 | **✓（§9.5 六条映射逐条对上；R6 面/探针孪生/容差初值三处锚点交叉印证）** |
| AI 专项 5 项全部完成 | **✓（§8 五行逐一有结论）** |

**结论：APPROVED_WITH_NOTES，unresolved_blockers=0。** F-1~F-4（P2）建议登记为遗留候选（FIX 候选位），不阻塞本次 commit；F-5~F-11（P3）记录备查。APPROVED 仅表示硬门槛通过，不替代 FEAT-020/切片验收对容差表的后续消费校准。

## 附：采信边界声明（事实依据红线）

本报告「已核实」项均基于：文件实读（行号可复查）、git 只读命令输出、独立数值复算、仓内文档锚点（§9.5/facts §7.3/R6 面/执行包/FEAT-019 commit 自述）。以下为**采信项**（未独立复现，已标注）：全量 2,297/30F+1E 运行结果、「三次采样 ±5%」中未入库的两次运行、manifest/ratchet 双 PASS 的实际命令退出码（结构推演支持但未执行）。Coordinator 入账 EVD 时建议保留此边界标注。
