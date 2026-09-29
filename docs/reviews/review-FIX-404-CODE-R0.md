# Code Review R0 — FIX-404（TemporaryDirectory 清理崩溃缺陷族扫尾）

- **Task ID**: FIX-404
- **Reviewer**: Code Reviewer Agent（独立，R0 首轮）
- **审查对象**: `git diff` 限定两文件：
  - `skills/software-project-governance/infra/verify_workflow.py`（+27/-13 中的一部分）
  - `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+103）
- **范围纪律**: 工作区另有 FEAT-077 在途变更（change_triage.py / task_priority.py / test_change_triage.py / test_task_priority.py / test_provenance_domain.py / provenance_domain.py）——已确认不触碰、不评审。
- **日期**: 2026-09-29
- **结论**: *（审查进行中，分段落盘）*

---

## 维度 1：正确性（已核）

### 1.1 `run_external_project_validation`（verify_workflow.py ~21033-21075）

逐行核验结论：

- **早退安全**：两处提前 return（21008 target 无效 / 21022 workspace parent 越界）均在 `mkdtemp` 之前，无临时目录泄漏窗口。
- **keep_workspace 分支不动**：`tempfile.mkdtemp(prefix="spg-external-validation-", dir=...)` + `release_temp=False` 语义与改动前一致（仅变量名 `temp_ctx`→`temp_value` 联动），try 内 21061-21062 的 `release_temp=False` 冗余为**改动前已存在**代码，非本次引入。
- **finally 收口语义**：try 内唯一 return（21063）+ 全部异常路径均经 21073 `finally: shutil.rmtree(temp_value, ignore_errors=True)`：
  - 正常 return 路径：清理失败 → no-op（泄漏目录交由 OS TEMP 生命周期），result dict 正常返回 ✓
  - raise 路径：`ignore_errors=True` 使 rmtree 不可抛 → 原异常不被清理失败掩盖 ✓
  - 本函数无 SystemExit；`ignore_errors=True` 在 CPython 中将 onerror 置为 no-op（scandir/删除失败的 OSError 全部静默），不存在 tempfile `onexc` 恢复链的 chmod 二次抛出通道 ✓
- **与前实现的语义差异**：丢失 TemporaryDirectory.cleanup 的 Windows chmod-重试恢复——但该恢复链正是本缺陷族的崩溃源（chmod 本身抛 WinError 5），删除该通道属于修复目的本身，非回归。

### 1.2 `_cmd_check_loop_runtime_claims_identity`（verify_workflow.py ~21610-21706）

- **with→try/finally 等价性**：`mkdtemp`（21613）与 `try:`（21614）之间零语句，无泄漏窗口；try 体缩进与原 with 体一致（diff 未触体行，已抽查 21615-21704 缩进完整）。
- **raise/exit 契约**：体内全部 `raise IdentityAttestationError`（21629/21632/21637 等）与 `sys.exit(1)`（21704，verdict≠PASS）均在 try 内；SystemExit 经 finally 执行 rmtree 后继续传播——**exit code 语义不丢**；清理失败不掩盖 raise/exit（ignore_errors 不可抛）✓
- **对比 with 形态**：原 `TemporaryDirectory.__exit__` 同样在 SystemExit 时触发 cleanup 且 cleanup 异常会掩盖 SystemExit——新形态严格更安全。

### 1.3 docstring 补充（`_run_identity_attestation_fixture_only` ~21246-21248）

新增段声称「cleanup 失败降级 no-op（rmtree ignore_errors=True），不升级为崩溃、不掩盖 verdict」——与该函数实存实现（21286 `mkdtemp` + 21287 `try` + 21316 `finally` rmtree）逐句一致。FIX-403 R0 P2-1 已闭环。

**维度 1 结论：通过（无阻塞发现）**

---

## 维度 5：测试覆盖（已核，含 3 FAIL 归因验证）

### 5.1 族计数与结果口径交叉核对

Developer 报告「定向族 13 跑：0 ERROR、10 ok、3 FAIL」。源码逐类清点（grep `^class |^    def test_`）：

| 类 | 测试数 | 环境依赖 | 预期 |
|---|---|---|---|
| LoopRuntimeClaimAdapterTests | 4 | 无（semantic-only 真实 CLI 子进程 / 纯断言 / patch 注入 identity helper / patch 注入 scanner） | ok |
| FIX300DualCaliberAgreementTests | 3 | **依赖生产 identity 真实 verdict**（未 patch `attest_explicit_sources`） | 沙箱 3 FAIL |
| FIX403IdentityFixtureCleanupContractTests | 1 | 无（全 patch，环境无关契约） | ok |
| FIX404ExternalValidationCleanupContractTests | 1 | 无（全 patch，环境无关契约） | ok |
| FIX200ScopedAttestationRehearsalTests | 4 | 无（patch `materialize/attest/scan/write_attestation`，写仅入 `_governance_temp_dir`） | ok |

4+3+1+1+4 = **13** ✓，10 ok + 3 FAIL 与报告一致 ✓。

### 5.2 3 FAIL 归因可信性（源码推演，按协议不复跑）

归因链逐环核实：

1. FIX300 三测试调用**真实** `vw._run_identity_attestation_fixture_only()`（未 patch attestation）；
2. 该 helper 的 `snapshot_dir` 位于 `tempfile.mkdtemp(prefix="fix200-identity-")`（verify_workflow.py 21286-21298）之下——**生产 0o700 目录**；
3. Developer 实证（与本审查会话同沙箱）：0o700 mkdtemp 目录对本进程拒写 → 快照物化必抛 OSError；
4. helper 的 `except Exception` 降级分支（21310-21312）→ 返回 `PENDING` verdict；
5. 三测试分别断言 `FAIL+REQUIRED_ROOT_UNAVAILABLE`（×2）与 `PASS`（×1）→ PENDING 均失配 → **FAIL（非 ERROR）** ✓ 与「0 ERROR」自洽。

推论核对：若无降级契约或降级为 crash，会是 ERROR；若沙箱可写 0o700，三测试应全绿（CI/沙箱外即如此）。「不为测试放宽生产 0o700」的取舍正确——mkdtemp 0o700 是安全属性，且本沙箱对 0o700 目录 chmod 亦被拒，无降级通道可用。**归因可信。**

注：改动前这 3 个测试因 fixture 本身 `TemporaryDirectory()` 0o700 拒写会更早 ERROR（`_drifted_host` 的 mkdir/copyfile 即失败）；本次 fixture 换装使其在沙箱内推进到断言层（ERROR→FAIL 的可诊断性改善），沙箱外行为不变。

### 5.3 新契约测试质量（FIX404ExternalValidationCleanupContractTests）

- **红绿判别力**：未修复代码上 `TemporaryDirectory.cleanup` → tempfile `onexc` 链内 scandir 拒绝 + chmod 恢复拒绝 → PermissionError 逃出 finally → `self.fail` 红相；修复后 rmtree(ignore_errors) no-op → result dict 返回 → 绿相。**测试真实走清理链**（未整体替换 rmtree，os.scandir/os.chmod 拒绝 + 真实 shutil.rmtree 机器）✓
- **补丁面最小**：仅 patch 生产函数四件套 + 模块级 os.scandir/os.chmod（非目标路径委托真实实现，其余行为不变）；断言 result 三键（pass/workspace/issues）与生产 return 形状（21063-21072）逐键吻合 ✓
- **FIX-403 契约测试同构**：同一 denying_scandir/denying_chmod 手法、同一 try/except+self.fail 红相注释、同一 result-shape 断言风格——缺陷族扫尾的模式一致性成立 ✓

### 5.4 fixture 换装覆盖

- 恰好 7 处（FIX300×3 + FIX200×4），其余 ~249 处 `tempfile.TemporaryDirectory` 未动（grep 计数 250 减注释 1）；抽检未触碰站点（677/693/699/724、4634+ 段）保持原样 ✓
- `_governance_temp_dir` yield `str(path)` 与 `TemporaryDirectory.__enter__` 返回类型一致，换装零适配 ✓

**维度 5 结论：通过（无阻塞发现）**

---

## 维度 2：安全性（已核）

- **生产 0o700 未放宽**：两处生产修复（`spg-external-validation-` / `fix216-scanner-`）均保留 `tempfile.mkdtemp`（0o700）——修复手段是**收口清理异常通道**而非降低目录权限；「修复=安全属性取舍」中 Developer 选择了不动安全属性，正确 ✓
- **测试侧放宽有界**：`_governance_temp_dir` 默认模式 mkdir 是**测试 fixture 专用**，不外溢生产；fixture 内容为合成 JSON / 仓库内治理文件副本（无密钥、无敏感数据）——详见维度 3 下的跨环境评审与 P2-1
- **注入/输入校验**：prefix 均为内部常量；无外部输入新面；deny-patch 仅 with 域内生效、非目标路径委托真实实现，无权限面变化 ✓
- **资源管理**：见维度 1（finally 收口）；测试 helper 同契约（rmtree ignore_errors → 泄漏不崩溃）✓

**维度 2 结论：通过（无阻塞发现；测试 fixture 安全权衡见 P2-1）**

## 维度 3：可维护性（已核，含验收④ `_governance_temp_dir` 跨环境安全评审）

### 3.1 注释/命名/重复

- 生产三处注释均交叉引用缺陷族（FIX-403 注释位 + 「same defect family」），第一读者可追溯 RCA ✓
- `temp_ctx`→`temp_value` 重命名与姊妹位点（`_cmd_check_loop_runtime_claims_identity` 原有 `with ... as temp_value`）命名统一 ✓
- mkdtemp+finally+rmtree 模式现于生产 3 处（21286 / 21044 / 21613）——见 P3-4（共性 helper 抽取机会，非阻塞）

### 3.2 `_governance_temp_dir` 跨环境安全评审（验收④）

| 环境 | 行为 | 评估 |
|---|---|---|
| 本沙箱（UAC 过滤令牌） | 默认模式可写（Developer 实证 0o600/0o755/0o777 可写、0o700 拒写且 chmod 亦拒） | helper 存在的理由 ✓ |
| Linux/macOS 常规 umask 022 | dir 0o755：他人可读/可穿越、**不可写** | 比 mkdtemp 0o700 多暴露「可读」面——fixture 内容为仓库内文件副本+合成数据，无敏感信息，暴露面≈0（P2-1 建议在注释中明示该权衡） |
| umask 000 环境（罕见/CI） | dir 0o777：他人可写 | 理论注入面，但目录名含 uuid4 12 hex（48 bit 熵，与 mkdtemp 的 ~47.6 bit 等价），不可预测；CI runner 单租户短生命周期，实际风险可忽略 |
| Windows 常规 | mkdir mode 基本被忽略，ACL 由继承决定 | 与 mkdtemp 行为差异缩小，无新面 |
| 并发 | uuid4 命名，多进程/pytest-xdist 无碰撞；mkdir 冲突无重试（mkdtemp 有）——48 bit 碰撞概率可忽略，失败形态为干净 FileExistsError 测试错误 | 可接受 |
| 清理 | finally + rmtree(ignore_errors=True)——与生产降级契约同构；异常路径（测试体 raise）仍清理 ✓ | ✓ |
| TEMP 尊重 | `tempfile.gettempdir()` 遵守 TMPDIR/TEMP/TMP 重定向 | ✓ |

**结论：跨环境安全评审通过**——默认模式的熵（uuid 48bit）与清理契约达标；唯一实质权衡（失去 0o700 的防读硬ening）因内容非敏感而可接受，建议补注释明示（P2-1）。沙箱内无法探测「0o700 是否可写」而不实际写入，故无条件默认模式是该约束下的合理形态。

## 维度 4：性能（已核）

- mkdtemp 与 TemporaryDirectory 构造等价（一次 mkdir）；`rmtree(ignore_errors=True)` 单次树遍历，且比 tempfile cleanup 的 onexc 包装链**更少** syscalls（无主动 chmod 恢复尝试）——无回归，微优 ✓
- 测试 helper 同理；uuid4 生成开销可忽略；无循环/算法变化 ✓

**维度 4 结论：通过（无阻塞发现）**

---

## AI 代码专项 5 项检查

| # | 检查 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | 全部 patch 在 with 域内自动还原；real_scandir/real_chmod 局部委托，无模块级污染 |
| 2 | 硬编码返回值 | ✅ 无 | `_run_external_validation_command` 的 return_value 是命令边界 fixture（契约对象是清理而非命令）；断言为结构断言（三键存在），不伪造 verdict |
| 3 | 幻觉 API | ✅ 无 | mkdtemp/rmtree/ignore_errors/uuid4.hex/PermissionError(errno, strerror, filename) 三参构造均真实；`patch.object(os, "scandir")` 拦截 shutil.rmtree→os.walk→scandir 链经 FIX-403 R0 源码逐帧核验 + 本轮绿相一手复跑证实 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME/占位 |
| 5 | 过度实现 | ✅ 无 | 5 个生产 hunk + 1 helper + 1 契约测试 + 7 处换装 + 1 import，恰好覆盖任务面 |

## 设计一致性（验收⑦：与 FIX-403 模式一致）

- **修复形态逐点同构**：`mkdtemp + try/finally + shutil.rmtree(ignore_errors=True)`，与 FIX-403 已批准位点（21286）一致；两处新注释显式引用 FIX-403/缺陷族 ✓
- **FIX-403 R0 P2-1 闭环**：docstring 补清理降级契约（21246-21248），与实现（21286/21316）逐句一致 ✓
- **FIX-403 R0 P2-2 闭环**：两处自报未防护位点（21038 `spg-external-validation-`、21601 `fix216-scanner-`）均已按同模式收口；keep_workspace 分支语义未动 ✓
- **`ignore_cleanup_errors=True` 不能封堵的论断**：沿 FIX-403 R0 对本机 CPython 3.14.3 tempfile/shutil 源码逐帧核验结论，FIX-404 注释（21040-21042）表述一致 ✓

## 范围纪律（验收⑥）

- diff hunk 清单逐一核对：无第七类改动；抽检 2 处未触碰位点（test_verify_workflow.py 677/693 段、4634+ 段仍为原 `tempfile.TemporaryDirectory()`）✓
- FEAT-077 在途文件（change_triage.py / task_priority.py / test_change_triage.py / test_task_priority.py / provenance_domain.py / test_provenance_domain.py）未触碰、未评审 ✓

## 一手复跑证据（执行协议合规）

- TEMP 重定向至 `.governance/tmp/check-run-20260929` 后：`python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow -k FIX403 -k FIX404 -v` → **Ran 2 tests in 0.143s, OK**（FIX403 契约 + FIX404 契约均绿）
- 红相未复跑（需回滚工作区，协议禁止）：经源码推演成立——未修复代码 finally 走 `TemporaryDirectory.cleanup`→`_rmtree(onexc)`→os.walk→scandir 拒绝→onexc→`_resetperms`→chmod 拒绝→PermissionError 逃出 finally→测试 except 捕获→`self.fail` 红相；与 FIX-403 R0 已核验的同一逃逸链一致。Developer 红绿实证披露与此推演相容。
- 全族 13 未复跑（协议限定两契约测试）：10 ok + 3 FAIL 口径经 5.1/5.2 源码级推演自洽采信。

---

## Findings

### P2（建议修改，可遗留）

- **P2-1【fixture 安全权衡文档化】** `test_verify_workflow.py:76-105` — `_governance_temp_dir` 注释完整记载了沙箱约束，但未明示「默认模式在非沙箱多用户环境失去 mkdtemp 0o700 防读硬ening（umask 022 → 0o755 可读）」这一主动权衡及「fixture 内容非敏感」的豁免理由。建议下一轮在注释块补两句，让安全属性差异对第一读者可见。非阻塞：uuid4 48bit 熵 + 内容非敏感 + 清理契约同构，实际风险≈0。

### P3（讨论，不要求修改）

- **P3-1【测试】** `test_verify_workflow.py:428/434` — deny 子串匹配 `"spg-external-validation-" in str(path)`（承 FIX-403 R0 P3-1 同形）；prefix 受控、作用域限测试进程，实际风险为零。
- **P3-2【测试】** `test_verify_workflow.py:456-465` — 红相包装 `except Exception` 不捕 BaseException；若未来以 SystemExit 崩溃将以 error 形态红（行为等价红）。承 FIX-403 R0 P3-2 同形。
- **P3-3【测试】** `test_verify_workflow.py:443-446` — `return_value=command_result` 使 `EXTERNAL_PROJECT_VALIDATION_COMMANDS` 循环各次迭代 append 同一 dict 引用，`result["label"] = label` 互相覆盖（当前断言不检查 commands 内容，无影响）；未来若断言 labels 建议改 `side_effect=lambda *a, **k: dict(...)` 每次新副本。
- **P3-4【生产】** `verify_workflow.py:21044/21286/21613` — mkdtemp+finally+rmtree 模式已 3 处；若出现第 4 处建议抽公共 contextmanager（keep_workspace/dir 参数化）。当前 3 处各有分支差异且注释互引，复制可接受。

---

## 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0  | 0  | 1  | 4  |

验收标准七项全部满足：①两处生产防护收口语义完整（finally 保覆盖 return/raise/SystemExit 且 ignore_errors 不吞语义、不掩盖原异常）②docstring 与实现一致（FIX-403 P2-1 闭环）③契约测试真实走清理链且红绿判别力成立 ④`_governance_temp_dir` 跨环境安全评审通过（权衡见 P2-1）⑤3 FAIL 归因经源码推演逐环闭合可信 ⑥范围纪律零越界（含 FEAT-077 隔离）⑦与 FIX-403 模式逐点一致（P2-2 两位点闭环）。

**放行。无需 R1。** P2-1 建议随下一触碰该测试文件的任务顺带完成。


