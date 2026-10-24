# CODE R0 — FIX-460 守卫导入 + 可见 skip + 台账行 re-anchor（独立审查）

- 审查人：Code Reviewer（独立，M7.4；本轮零代码修改 / 零 `.governance/` 写入 / 零 git 变更——只读命令 + 本报告文件）
- 审查对象：working tree 未提交 diff 两文件——`infra/tests/test_evidence_migration.py`（39+/2-）+ `infra/checks/version.py`（净+3/改1）
- 基线：HEAD=29e7367；背景=CI run 40076165914 唯一 error（模块级 `import pytest`）；扩展授权链=EVD-2153（61→80 re-anchor 为最后一次手编，类修复=FIX-462 / DEC-220）
- 取证：diff 全文逐行 + 行号漂移独立 grep + 引用实体存在性核查（FIX-462/DEC-220）+ 五门独立复跑（§6）

## 结论

综合裁定（证据与复跑输出见 §1-§7）：

FIX-460: APPROVED_WITH_NOTES (unresolved_blockers=0)

## 1. Shim 安全性（关键项）——无静默执行/静默通过向量

`_PytestImportShim.__getattr__` 返回 `_passthrough`：bare 形式（单可调用位置参数无 kwargs）返回原函数；factory 形式返回恒等 `lambda fn: fn`。核查：

- **静默执行**：16 个 pytest 风格测试是模块级函数，pytest 缺失时无任何 runner 调用路径；unittest discover 唯一收集对象是 `PytestSuiteCoverageMarker`（G1 实测收集恰 1 个）。
- **静默通过**：真 pytest 路径未受 shim 影响——G3 = **17 passed**（16 真实测试 + 1 marker 全执行）。shim 仅在 pytest 缺失的导入期求值装饰器（模块级唯一用法 bare `@pytest.fixture`，正确返回原函数）；`pytest.raises` 等仅存于测试体内，缺失时永不求值。

## 2. Marker 语义——极性正确

`@unittest.skipUnless(HAS_PYTEST, ...)`：G1（无 pytest 模拟）= 1 skipped 带理由（理由含 FIX-461 引用，stderr 实测可见）；G2（有 pytest）= marker ok（证导入路径健康）。无反逻辑。

## 3. `__main__` 守卫——失败信号响亮

`pytest.main([__file__, "-q"]) if HAS_PYTEST else 2`：pytest 缺失直跑退出码 2（显式失败，非静默成功）。合理。

## 4. 台账 re-anchor（61→80）——漂移实证 + 引用实体在案

- **漂移独立核实**：现文件 L61 = 空行（sys.path 块后）；**L80** = `| **P1** | FIX-903 | 活动任务丙 | — | 0.99.0 | 在途 | 🔄 进行中 |`——全文件**唯一**字面 `0.99.0`（grep 逐行复核）。re-anchor 目标行正确。
- **条目保真**：token（"0.99.0"）与理由（`_REASON_FIXTURE_ROW_TEXT`）逐字不变，纯行号变更；version.py diff 其余=3 行纪律注释，无逻辑改动。
- **引用实体存在性**：FIX-462 = TRIAGE-FIX-462 已机录（change-triage/FIX-462.json + plan-tracker P1「pin 台账机写命令」）；DEC-220 = decision-log 在案（确定性核心/LLM 边界公理）。注释链披露（"final hand re-anchor; class fix = FIX-462 …DEC-220"）事实可溯，非空头引用。
- **契约权威验证**：G5 `test_static_version_pins` 全模块 **25 tests OK**（含 RealTreeContractTests 台账活性双用例）——re-anchor 经专用契约测试复活验证。

## 5. Diff 最小性——恰两文件，无越界

`git diff --stat HEAD` 4 个修改文件中：本任务面 = 恰上述两文件；另两文件（`infra/hooks/commit-msg` 743、`infra/tests/test_hooks.py` 857 --stat 口径）= 会话前暂停链 WIP 指纹（numstat 742+/1- 与 855+/2-），未被本任务触碰。未跟踪文件未动；`.governance/` 零写入（本审查）。

## 6. 五门独立复跑（当前树实跑，非采信自报）

| 门 | 命令 | 结果 | exit |
|---|---|---|---|
| G1 | `sys.modules['pytest']=None` + discover（该文件） | **OK (skipped=1)**，skip 理由可见 | 0 |
| G2 | 同 discover（有 pytest） | **OK**（marker ok，skipped=0） | 0 |
| G3 | `python -m pytest <该文件> -q` | **17 passed in 1.02s** | 0 |
| G4 | `python verify_workflow.py` | **PASSED**（无 FAIL 行、无 static-version-pin WARN 输出） | 0 |
| G5 | `unittest discover -p test_static_version_pins.py` | **Ran 25 tests, OK** | 0 |

## 7. Notes（非阻塞，N1-N5）

- **N1** shim bare 形式启发式对本文件唯一用法正确；未来新增 factory-单可调用参数用法需复核——FIX-461 转换后 shim 整体移除，窗口有界。
- **N2** marker 在本地 pytest 环境作为第 17 个测试平凡通过（`pass` 体）——职能是 CI 可见性，非覆盖声明。
- **N3** G1 stderr 实测 skip 理由完整输出 = CI 面可见性达成（skipped=1 带理由，非静默零收集）。
- **N4** 16 测试 CI 覆盖洞以 skip 理由 + FIX-461（已 triage P2）双通道披露。
- **N5** 本 re-anchor 是台账第 4 次手编（FIX-453→459→460 链）；EVD-2153 + 注释链已将其定界为**最后一次手编**，类修复 FIX-462（机写器）+ 溯源公理 DEC-220 在案——随机性有终点，符合确定性核心设计边界。

## 审查边界声明

全程只读命令（git diff / grep / 行读取 / discover / pytest / verify_workflow / test_static_version_pins）+ 写入本报告文件；未修改代码、未碰 `.governance/`、未动 git 状态（无 add/commit/stash）。
