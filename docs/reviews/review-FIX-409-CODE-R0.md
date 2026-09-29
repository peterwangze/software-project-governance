# Code Review — FIX-409 R0（投影 writer ACL 归一化 + write-then-probe）

- **task**: FIX-409（RISK-061 真根因根修；TRIAGE-FIX-409；P1）
- **round**: R0（首次审查，无前轮）
- **reviewer**: Code Reviewer Agent（独立；终窗票）
- **date**: 2026-09-29
- **对象**: `skills/software-project-governance/infra/release/projection.py`（+69/−2）+ `skills/software-project-governance/infra/tests/test_release_projection.py`（+121，含 WriteThenProbeTests 3 例 + ProjectionPlanOverlapTests fixture 换装）
- **复跑面**: TEMP 重定向 `.governance/tmp/check-run-20260929`；test_release_projection 全文件 + check-projection-sync + 独立活体闭环复核；禁全量（遵守）；重试 0/2（全部一次通过）

## 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）

P0=0，P1=0；F-1（P2）+ F-2~F-5（P3）为非阻塞备注。硬门槛全部通过（见 §6）。

## 七项验收核验

### ① 三层 ACL 处置语义 —— PASS

| 层 | 实现 | 事实锚 |
|---|---|---|
| L1 journal 0755 | `_journal_dir`：uuid 默认模式 `mkdir()` + `chmod 0o755` best-effort（OSError 吞） | projection.py:577-596 |
| L2 apply 0644 | `shutil.copyfile` 后、`replace` 前 `chmod 0o644` best-effort | projection.py:648-657 |
| L3 probe | write-then-probe：每个 replaced target `os.access(R_OK)`，拒读→显式 FAIL + takeown/icacls 指引 | projection.py:663-681 |

降级路径安全性核验：chmod 被敌对沙箱拒时——L1 降级后目录仍是**默认模式**（非 0700；Windows 继承父目录 DACL、Linux umask 典型 755），根源上已避开 RISK-061 的 mkdtemp-0700 损伤来源；L2 降级后 apply 文件为 copyfile 默认创建态（源 staged 文件位于默认模式 journal 内，SD 正常）；任何残余损伤由 L3 探针兜底**显式 FAIL（不静默）**。三层递进语义成立：归一化是 best-effort、探针是硬兜底。

### ② write-then-probe 的 FAIL 语义（不回滚立论）—— PASS（核验成立）

立论链逐环核验：(a) probe 之前 `check_projections` 已对全部 plan target 做 `read_bytes()+match` 验证（projection.py:660-662）——probe 触发时**字节已验证**；(b) probe 只测 R_OK——缺陷定位在**描述符**而非内容；(c) 因此回滚（恢复旧内容）既不修复描述符又丢弃已验证的新字节——不回滚 + FAIL + takeown/icacls 修复指引是正确处方。代码实现：probe FAIL `return CheckResult("FAIL", ...)` 位于 `cleanup_journal=True` 之前（projection.py:677-682）→ journal 连同 backup 有意留档供人工处置（受损环境下 cleanup 的 unlink 本身可能被拒）。`state=FAIL` 经 FIX-405 已接线的命令面（`--write` FAIL→exit 1）与发布门红灯传播——**不静默闭环成立**。

### ③ uuid journal 碰撞安全性 vs mkdtemp —— PASS（安全，附 P3 讨论）

uuid4().hex[:12] = 48-bit 随机；`mkdir()` 原子性保证碰撞时 `FileExistsError` 而非竞态覆盖/数据损坏。单 root 调用频率 = 每次 release write 一次（极低频），单次碰撞概率 2^-48，可忽略。与 mkdtemp 的差异：失去内建重试（碰撞即抛，且 `_journal_dir` 调用在 try 块外，异常直接传播）——但形态是 fail-loud 显式崩溃，无静默损坏路径。见 F-3。

### ④ 3 测试质量 + fixture 换装合规 —— PASS

WriteThenProbeTests 3 例覆盖三种形态：
- `test_journal_dir_is_created_readable_and_writable`：单元——journal 前缀 + RWX 可达（journal 随 root 的 addCleanup 清理，无漏清）。
- `test_write_output_is_readable_and_leaves_no_journal_litter`：端到端正常路径——PASS/written=2/两 target 可读且含新字节/零 litter。
- `test_unreadable_target_fails_loudly_without_rollback`：错误路径——`patch.object(rp, "_probe_readable")` 故障注入（模块属性隔离，不污染全局 `os.access`——设计正确）→ FAIL/write_then_probe=FAIL/2 issues 前缀+takeown+icacls/不回滚（新字节保留断言）。

红→绿核对：绿态独立复跑 7/7（见 §5）；红态（红三重含活体 PermissionError 复现）**采信 Developer 声明与 RCA 留痕**——Reviewer 不改码无法回退复现红态，RCA docstring 详实且与 RISK-061 实证面（20 处损伤/undeletable litter）吻合。

fixture 换装（同窗顺手件，在 FIX-409 锁面内）：ProjectionPlanOverlapTests 3 处 `tempfile.TemporaryDirectory()` → `_sandbox_tmp_dir()`（test_release_projection.py:38-52）——与 FIX-404 `test_verify_workflow._governance_temp_dir` 同模式（gettempdir+uuid+默认模式 mkdir+`rmtree(ignore_errors=True)`），docstring 标注纪律来源，断言未变。**合规**。换装后 4 例全绿。

### ⑤ 本沙箱实测复核 —— PASS（独立重做）

- `python -m pytest tests/test_release_projection.py -v` → **7 passed in 0.16s**（一次通过，重试 0/2）；留痕 `.governance/tmp/check-run-20260929/fix409-r0-tests.txt`。
- `python verify_workflow.py check-projection-sync` → **PASSED（28 mirrors）+ Entry Bootstrap PASSED，exit 0**；留痕 `fix409-r0-cps.txt`。
- 独立活体闭环（TEMP 重定向下自建 root，未触仓库工作区）：R1 write → `PASS/written:2/probe:PASS`；扰动 report.txt 回旧版 → R2 write → `PASS/written:1/probe:PASS`（**与 Developer 证据 written:1 精确吻合**）；journal litter=[]；清理后 leftover=[]；留痕 `fix409-r0-live.txt`。

### ⑥ 零范围外 —— PASS（声明核实属实）

- `git diff HEAD --stat -- verify_workflow.py` 输出为空 → **verify_workflow.py 零改动声明属实**。
- `tests/test_verify_workflow.py` 变更核对为 FIX-408（SD 用例 hermetic 化：虚构路径断言 + patch `check_projection_sync`）——非 FIX-409 混入。
- `archive.py`/`test_archive.py` = FIX-407（已审毕，未动）；e2e 3 文件 = 恢复态（不在范围）。
- 同文件 fixture 换装 = 任务预告的同窗顺手件（轻审通过，见 ④）。
- projection.py +69/−2 与 diff stat 逐行吻合；+121 测试增量 = WriteThenProbeTests + 换装 helper/imports。

### ⑦ 与 FIX-405 检测门的双保险关系 —— PASS（互补不冲突）

FIX-409 = 根修（writer 内联：去 0700 来源 + SD 归一化 + write-then-probe）；FIX-405 = 检测门（外层：`--write` 命令面 + 发布门 `check_release_readiness` 的 sd_integrity 扫描，覆盖 hooks/自升级等 writer 外的面）。定位链：TRIAGE-FIX-409.json `related=[FIX-405]`、reason 明示「根修+检测双保险」；RISK-061 行终局处置=FIX-405 检测门，FIX-409 是真根因定论（mkdtemp-0700 journal + `os.replace` 携带 SD）后的深化，与收窄终态一致非矛盾。两处 remediation 文案同风格（takeown/icacls）；probe 语义精确限定本笔 `replaced` 面（区别于检测门的全 plan 面）。根修降低检测门触发频率，检测门兜住 writer 外损伤面。

## 5 维度结论

| 维度 | 结论 | 要点 |
|---|---|---|
| 正确性 | 通过 | write/probe/FAIL/cleanup 流转正确；written 计数精确（FAIL 时 len(replaced)）；空 changed 早退不受影响；边界=chmod 拒绝三层降级（①）；probe 仅测 replaced 面 |
| 安全性 | 通过 | 无硬编码密钥/无注入面（issue 文案为静态消息）；ACL 方向=归一化到与仓库一致的默认模式（0755/0644，journal 内无敏感数据）；路径经 `_safe_repo_path` 既有校验；修复指引文案正确 |
| 可维护性 | 通过 | docstring/注释承载完整 RCA 脉络（可考古）；命名表意（`_journal_dir`/`_probe_readable`）；函数长度合规。备注 F-4/F-5 |
| 性能 | 通过 | probe=每 target 一次 `os.access`（O(n) 轻系统调用）；chmod 常数次；无循环 I/O 放大 |
| 测试覆盖 | 通过 | 核心路径+错误路径+单元属性 3 例；故障注入经模块属性（隔离性良好）；复跑 7/7。备注：probe-FAIL 后 journal 留档行为无显式断言（F-1 关联，P3 级） |

## AI 代码专项 5 项

| 检查 | 结论 |
|---|---|
| mock 残留 | 无——生产代码零 mock/patch；测试 patch 均 `with` 限定作用域 |
| 硬编码返回值 | 无——生产路径无 stub/常量短路 |
| 幻觉 API | 无——`os.chmod`/`os.access`/`uuid.uuid4`/`Path.mkdir` 均真实标准库 |
| 未实现 TODO | 无 |
| 过度实现 | 无——三层处置全部在票面验收内，无多余抽象/配置项 |

## Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | projection.py:677-681 | probe-FAIL 分支 facts 缺 journal 路径：journal 被有意保留（backup 留档供人工修复），但异常分支已有 `rollback_journal` 键先例，此分支调用方无法从结果定位保留物（仅能靠 `spg-projection-*` 前缀目视发现） | facts 增 `"retained_journal": str(journal_dir)`（下轮顺手件） |
| F-2 | P3 | projection.py:599-603 | `os.access` 在 Windows 不查 DACL（仅 readonly 位）——真实 Windows SD 损伤场景 probe 可能假阴性；该场景实际由 post-write `check_projections` 的 `read_bytes` PermissionError 路径兜住（显式 FAIL/BLOCKED），「不静默」仍达成；FIX-405 sd_integrity 同一平台限制 | `_probe_readable` docstring 补一句平台限制披露 |
| F-3 | P3 | projection.py:590-591 | uuid mkdir 无碰撞重试（2^-48/次）；碰撞时 `FileExistsError` 在 try 外未捕获传播——fail-loud 形态、无数据损坏，实际概率可忽略 | 如追求 mkdtemp 级保证：`exist_ok=False` 循环或挪入 try（讨论项） |
| F-4 | P3 | test_release_projection.py:38-52/171-178 | 测试侧两个近似重复的 fixture-root helper（`_sandbox_tmp_dir` contextmanager vs `_writable_root` addCleanup） | 可合一（纯测试侧，不阻塞） |
| F-5 | P3 | projection.py:599 vs checks/sd_integrity.py | `_probe_readable` 与 `scan_sd_readability` 两处独立实现同一「可读性 oracle」——FIX-406 F-2（谓词漂移教训）的潜在重演面：若探测语义演化（如换 Windows DACL 真探测）需两处同步 | 后续统一或交叉引用注释 |

## 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| 5 维度全覆盖 | 100%（§5 维度表） |
| 每条发现标注级别 | 100%（F-1 P2，F-2~F-5 P3） |
| 设计一致性检查 | 已完成——与 TRIAGE-FIX-409 票面、FIX-405 双保险定位、RISK-061 收窄终态一致 |
| AI 专项 5 项 | 全部完成（§AI 专项表） |

## 复跑证据留痕

- `.governance/tmp/check-run-20260929/fix409-r0-tests.txt`（pytest 7/7）
- `.governance/tmp/check-run-20260929/fix409-r0-cps.txt`（check-projection-sync PASS）
- `.governance/tmp/check-run-20260929/fix409-r0-live.txt`（活体闭环 CLOSED-LOOP-OK）
