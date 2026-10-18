# FIX-449：ledger 测试活动版本针派生化

- 日期：2026-10-16
- 任务范围：`test_verify_workflow.py` 的六处活动版本字面量；不变更项目版本。
- 权威版本来源：`resolve_entry.read_active_version()` → workflow `SKILL.md` frontmatter。

## 根因

1. 为什么版本一致性检查出现六条 WARN？测试的可执行 fixture 行直接包含当前活动版本。
2. 为什么这些行绑定活动版本？FEAT-093 新增 ledger 测试时把当时的目标版本复制进数据。
3. 为什么以后发布仍需要修改测试？fixture 构造没有调用版本权威读取函数。
4. 为什么不能把全文件版本字符串统一替换？其他测试包含历史版本、版本对和故意错误的数据，替换会改变其验证语义。
5. 为什么只修六行还不够？同一 PLAN 的冲突行包含下一版本字面量，下一次 bump 会产生新的同族 WARN；该版本需要保持与活动三行不同，并一起派生。

修复前实测活动版本为 `0.98.0`；六处定位为 L25468、L25470、L25472、L25677、L25959、L25961（记录的是修改前行号）。扫描结果：目标文件 6 WARN，整棵测试树 7 WARN。

## 修改与语义保护

| 数据位置 | 修改 | 保留的验证契约 |
| --- | --- | --- |
| `FEAT093AuthorityLedgerProjectionTests.PLAN` 三个活动行 | 改为 `@@ACTIVE_VERSION@@`，由 `_gov()` 构造时读取并替换 | 4 个原始任务行、3 个 distinct ID；历史同 ID 换义冲突仍有 1 个 |
| 同 PLAN 的冲突行 | 改为 `@@CONFLICT_VERSION@@`，派生为同 major 的下一 minor | 原冲突标题、状态和不同版本关系保留；不把冲突数据改成正常行 |
| 31-task 性能数据 | 版本改为相同活动 token，和 PLAN 一起构造 | 原 31 行、2 秒 rebuild 门和 50ms 单事务门不变 |
| 缺锚负向 fixture 的两个行 | 测试运行时读取活动版本，用 f-string 注入 | 空事项单元格仍为空；dry/live 都拒绝并返回 `schema_violation_row`，部分迁移完整性和重跑幂等检查不变 |

新增 `test_fix449_versions_follow_authority_across_bumps`：以当前版本、下一 minor 和下一 major 为输入，检查活动三行均跟随权威值、冲突版本不同、无残留 token、实际 migration PASS 且 `flagged_conflicts == 1`。历史及其他负向 fixture 字面量未批量替换；未新增豁免。

## 验证

在项目根目录运行：

```powershell
python -X utf8 -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -k 'FEAT093AuthorityLedgerProjectionTests or FEAT093AuthorityLedgerReworkR0Tests' -q
```

结果：`18 passed, 1120 deselected, 3 subtests passed in 2.31s`。

未来版本验证同时运行上述两个完整 class，未修改工作树版本文件：

```python
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path('skills/software-project-governance/infra/tests').resolve()))
import test_verify_workflow as suite_module
from resolve_entry import read_active_version

current = read_active_version()
major, minor, _patch = map(int, current.split('.'))
for version in (current, f'{major}.{minor + 1}.0', f'{major + 1}.0.0'):
    with mock.patch('resolve_entry.read_active_version', return_value=version):
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(case)
            for case in (
                suite_module.FEAT093AuthorityLedgerProjectionTests,
                suite_module.FEAT093AuthorityLedgerReworkR0Tests,
            )
        )
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        assert result.wasSuccessful()
```

通过 `python -X utf8 -` 执行上述代码。结果：权威值 `0.98.0` / `0.99.0` / `1.0.0` 每轮均 `Ran 18 tests ... OK`，合计 54 次 test 运行，0 failures/errors；三轮耗时分别 1.445s、1.456s、1.321s。

其他验证：

```powershell
python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-cross-references
python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency
python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python -X utf8 -m pytest skills/software-project-governance/infra/tests/test_static_version_pins.py -q
```

- Cross references：PASS，无 dangling/deprecated/circular references。
- Manifest：PASS；新增诊断文档由现有文档规则覆盖，无需修改 manifest。
- Version consistency：PASSED，12 个版本投影一致；保留 1 条既有 WARN（见下）。
- `checks.version.scan_static_version_pins(Path.cwd())`：目标文件 WARN **6 → 0**，整树 **7 → 1**。
- Static-pin scanner 测试：**24 passed / 1 failed**。唯一失败为 `RealTreeContractTests.test_ledger_rows_are_live_on_current_tree`：`test_archive.py:5862` 的 `0.95.0` exemption 已漂移。修复前扫描即存在该 WARN；本票未修改该文件或 exemption registry，已通知 Coordinator 另行承接，不将此结果描述为全绿。
- 全套件由并行 DevOps 负责；本票未重复运行全量，以上为本票范围内实测。

## 回滚与边界

回滚本票的两个文件即可；没有业务数据迁移、版本 bump、hook 修改或 `.governance/` 写入。提交与独立审查由 Coordinator 承接。

## R0-F1 修订检查点（2026-10-17，待 R1 独立复审）

独立审查 `docs/reviews/review-FIX-449-CODE-R0.md` 结论为 NEEDS_CHANGE/1：`FEAT093AuthorityLedgerReworkR0Tests._migrated_gov()` 直接写共享 `fixture.PLAN`，绕过新增渲染器，三个已注册任务的版本变成字面 token。此前 18 tests × 三版本虽然真实通过，但计数断言未检查此消费者的 plan/ledger 版本值；不能据此认定共享 fixture 消费者全部正确。该遗漏与原验证局限在此明确更正，原始运行记录保留。

修订仅涉及同一测试文件和本诊断：

1. `_gov()` 改为可由两个 class 共用的 classmethod，保留同一个版本读取/渲染/写入入口。
2. `_migrated_gov()` 复用该 helper，再执行原真实 migration；删除第二份 PLAN/RISKS 写入逻辑。
3. switch-state 测试读取该 helper 已渲染的 plan，再构造开关变体，避免继续直接消费模板。
4. 新增 `test_fix449_migrated_fixture_versions_follow_authority`：实际调用遗漏消费者，在当前/下一 minor/下一 major 下检查 plan 无 token、活动三行版本相同、冲突行为同 major 下一 minor、ledger 三任务版本跟随权威值、完整性保持、registered=3 且 historical identity conflict=1。

全文件 `.PLAN` 使用点复查只剩统一渲染器 `cls.PLAN + plan_extra_rows` 一处。没有派生历史冻结资料，也没有改变原冲突标题、负向拒绝断言、任务数量或性能门。

### 红 → 绿

先新增上述回归，不改 `_migrated_gov()`，运行：

```powershell
python -X utf8 -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -k test_fix449_migrated_fixture_versions_follow_authority -q
```

RED：**exit 1**；三个版本子例 `0.98.0`、`0.99.0`、`1.0.0` 均在 `assertNotIn("@@", plan)` 失败，输出 `3 failed, 1 passed, 1138 deselected in 4.72s`（pytest 将主方法与失败 subtest 分开计数）。原 R0 报告同时提供 ledger token 失真的独立复现。

应用共用 helper 修复后，沿用本报告前述两个 class 的 pytest 命令：**exit 0，19 passed, 1120 deselected, 6 subtests passed in 3.55s**。

沿用前述三版本完整 unittest 重放命令，并追加实际 `_migrated_gov()` 的 plan/ledger 探针，实际权威版本读取为 **0.98.0**，项目版本未 bump：

| 注入权威版本 | 两 class 结果 | 消费者 plan 残留 token | ledger 的 FEAT-093 / FEAT-094 / FIX-442 版本 |
| --- | --- | --- | --- |
| 0.98.0 | 19 tests / OK，1.978s | False | 均 0.98.0 |
| 0.99.0 | 19 tests / OK，3.347s | False | 均 0.99.0 |
| 1.0.0 | 19 tests / OK，3.166s | False | 均 1.0.0 |

合计 **57 次 test 运行，0 failures/errors，exit 0**。追加探针可在前述脚本的每个 version mock 内运行：

```python
with suite_module._governance_temp_dir(prefix='fix449-r1-probe-') as td:
    al, gov = suite_module.FEAT093AuthorityLedgerReworkR0Tests()._migrated_gov(td)
    plan = (gov / 'plan-tracker.md').read_text(encoding='utf-8')
    targets = {k: task['target_version']
               for k, task in al.LedgerWriter(gov).state['tasks'].items()}
    assert '@@' not in plan and set(targets.values()) == {version}
```

### 同轮门禁

- `python -X utf8 -m pytest skills/software-project-governance/infra/tests/test_static_version_pins.py -q`：**exit 0，25 passed in 4.23s**。
- `scan_static_version_pins(Path.cwd())`：**exit 0，目标文件 WARN=0、整树 WARN=0**。原 archive exemption 残留由并行 CI 修复处理，整树改善不全部归因 FIX-449。
- `check-version-consistency`：**exit 0，PASSED**，12 个版本投影一致、无 WARN。
- `check-cross-references`：**exit 0，PASS**，79 文件、748 引用；无 dangling/deprecated/circular references。
- `check-manifest-consistency`：**exit 0，PASS**。
- `git diff --check -- skills/software-project-governance/infra/tests/test_verify_workflow.py docs/diagnostics/fix-449-version-pins.md`：**exit 0**。

未重复全套 suite，未修改其他 CI fixture、SKILL、DSH 原型、暂停 hooks/test_hooks 或治理账本，未提交。R0-F1 的实现与回归现可送原 Reviewer 做 R1；本检查点不自行批准。
