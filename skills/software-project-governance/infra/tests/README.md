# infra/tests

verify_workflow.py 的测试套件。零外部依赖，仅使用 Python 标准库（unittest, tempfile, pathlib, json, os）。

## 目录结构

```
infra/tests/
  __init__.py                  # package marker
  test_verify_workflow.py      # 单元测试（SYSGAP-016）
  e2e/
    __init__.py                # package marker
    test_governance_init.py    # 端到端测试（SYSGAP-017）
  README.md                    # 本文件
```

## 运行方法

```bash
# 运行所有测试（推荐——使用 pytest）
python -m pytest skills/software-project-governance/infra/tests/ -v

# 运行所有测试（stdlib only, 无需 pytest）
python -m unittest discover -s skills/software-project-governance/infra/tests -v

# 运行单个测试文件
python -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -v

# 运行端到端测试
python -m pytest skills/software-project-governance/infra/tests/e2e/test_governance_init.py -v
```

## 测试覆盖

### test_verify_workflow.py

| 测试类 | 覆盖内容 | 用例数 |
|--------|---------|--------|
| ManifestLoadingTests | manifest.json 加载（正常/不存在/JSON 错误/空文件） | 4 |
| CanonicalSetTests | canonical 集合展开（entries + glob_patterns + 去重） | 4 |
| FileExistenceTests | _check_file_exists 逻辑（存在/不存在） | 2 |
| DecisionLogParsingTests | decision-log.md 解析（正常/空文件/无 DEC 条目） | 3 |
| PlanTrackerParsingTests | plan-tracker.md 解析（task ID/Gate 状态/空文件/无任务） | 4 |
| GovernanceIntegrationTests | check-governance 集成测试（证据完整性/风险过期/Gate 一致性） | 6 |

### test_governance_init.py

| 测试类 | 覆盖内容 | 用例数 |
|--------|---------|--------|
| PlanTrackerStateTests | plan-tracker 状态模拟（全通过/部分 pending/空计划） | 3 |
| EvidenceLogStateTests | evidence-log 状态模拟（全覆盖/部分覆盖/空） | 3 |
| GateConsistencyTests | Gate 一致性场景（有证据/无证据/passed-on-entry/孤证） | 4 |
| RiskStalenessE2ETests | 风险过期检查（全部关闭/混合新鲜和过期） | 2 |
| FullGovernanceE2ETests | 完整 governance skeleton 全量检查 | 1 |

## 设计原则

- **零外部依赖**：只使用 Python 标准库，确保在任何 Python 3.8+ 环境可运行
- **隔离测试**：使用 `tempfile.TemporaryDirectory` 创建临时文件系统，`unittest.mock.patch` 模拟模块常量
- **自包含**：每个测试创建自己的 fixture，不依赖实际项目文件状态
- **可以独立运行**：不依赖 pytest 或任何第三方 runner，`unittest` 发现机制即可
