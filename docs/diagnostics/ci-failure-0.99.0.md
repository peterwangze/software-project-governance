# Governance CI 失败诊断（FIX-452 / 0.99.0）

诊断日期：2026-10-16。初始产品快照：`a00105717935079c54ec30ed6e6c790e8bd97290`。

## 原始远端失败

最近六次 Governance CI 均为 `failure`，不能将本地工作树通过解释为远端已恢复。已直接取得最近两次运行的原始 job 日志：

| Run / head | Job | 首个失败 | 原始结果 |
| --- | --- | --- | --- |
| [38835185972](https://github.com/peterwangze/software-project-governance/actions/runs/38835185972) / `f392a0b7769f8638b26be602805d51e971c4e69d` | `116762612087` | Verify workflow integrity | `hooks/commit-msg: @version=0.97.0, expected=0.98.0`；exit 1 |
| [38833780678](https://github.com/peterwangze/software-project-governance/actions/runs/38833780678) / `7f161a60f87d3f2859daf129dba5be7036c5c177` | `116758199788` | Verify workflow integrity | 同一版本标记不一致；exit 1 |

取证命令：

```powershell
gh run list --repo peterwangze/software-project-governance --workflow ci.yml --limit 6 --json databaseId,conclusion,headSha,createdAt
gh api repos/peterwangze/software-project-governance/actions/jobs/116762612087/logs --allow-escape-sequences
gh api repos/peterwangze/software-project-governance/actions/jobs/116758199788/logs --allow-escape-sequences
git show HEAD:skills/software-project-governance/infra/hooks/commit-msg
```

首次 `gh run view --log-failed` 的下载超时不是 CI 失败原因。直接 job 日志接口成功返回，最新日志第 1514 行明确给出上述版本错误。其余四次运行只核实失败结论，未据此推断相同根因。

当前受保护的 FIX-445 工作树 hook 已包含 `@version: 0.98.0`，但提交态仍为 `0.97.0`。因此当前工作树 `verify_workflow.py` exit 0 不能代表提交态或干净 checkout；该 WIP 不应整体提交到修复中。

## 干净提交态复现与后续门禁

Windows `git archive HEAD` 导出快照复现 integrity 的同一失败；将命令输出保存到导出目录之外后，manifest 与 cross-references 均通过。最初诊断日志曾位于导出根，导致文件系统 fallback 扫描将 `verify.log` 计为未登记文件；移出后 manifest exit 0，此诊断产物不计为项目缺陷。

随后在本机 WSL `AI-Dev-Ubuntu` 中以 `git clone --no-hardlinks` 创建独立、包含 Git 元数据的干净 checkout，执行 CI 相同全量 unittest 命令。环境为 Python 3.12.3 / Git 2.43.0，GitHub workflow 指定 Python 3.11；远端结果仍是最终验收依据。

```text
python skills/software-project-governance/infra/verify_workflow.py
  exit 1: hooks/commit-msg @version 0.97.0 != 0.98.0
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
  exit 0
python skills/software-project-governance/infra/verify_workflow.py check-cross-references
  exit 0
python3 -m unittest discover -s skills/software-project-governance/infra/tests -v
  原始诊断环境全量执行结束，exit 1；含下述真实失败及诊断环境差异，不能用作 GitHub Python 3.11 的最终失败总数
```

### ArchGuard 提交态基线陈旧

干净 Ubuntu checkout 的 `test_cli_green_on_current_tree` 与 `test_r7_committed_baseline_matches_fresh_regen` 失败。调用真实 `archguard_ratchet.build_baseline()`，经 `_strip_volatile()` 排除已声明的 commit/解释器差异面后，仅以下数据漂移：

| 面 | 已提交基线 | 当前代码真实提取 |
| --- | --- | --- |
| `r1_mainfile_budget.anchor_loc` | 28270 | 28214 |
| `checks/triage_domain.py` 的四条反向依赖位置 | 261, 267, 480, 486 | 260, 266, 479, 485 |

需由产品开发者通过正式 `archguard-ratchet --regen` 更新机器基线，并同步 `test_archguard_ratchet.py` 中元数据断言的当前 anchor。不得手编提取面、跳过 R7 或放宽阈值。

### behavior profile 测试依赖本地治理运行态

在同一干净 Ubuntu checkout 单独执行：

```text
python3 -m unittest discover -s skills/software-project-governance/infra/tests -p test_behavior_profile.py -v
Ran 47 tests
FAILED (failures=9, errors=1)
```

`AggregateFaceTests` 只替换 `_read_text`，但其真实 resolve envelope 在干净 clone 中为 `governance_initialized=false`；聚合器因此正确进入未初始化分支，尚未读取被替换的 plan 内容。`CliSmokeTests` 同样依赖未入库的 `.governance/plan-tracker.md`。报错包含 `next_actions=['运行 /governance 初始化或接入项目治理（当前 .governance/ 缺失）']`、期望 legacy 却实际 modern、及对 `None` 执行 `assertIn`。

修复应为测试构造完整临时 host/plan 夹具，覆盖真实存在面及 CLI 路径；不能在 CI 中伪造项目治理记录，也不能改变产品未初始化分支的安全语义。

### CI 缺少已要求的测试依赖（本任务已修）

`test_governance_cost.py::Feat039ZstandardDependencyAssertionTests` 明确要求 zstandard 在开发和 CI 环境存在。原 workflow 只安装 Python，没有安装该依赖。干净 Ubuntu 诊断环境单跑本模块得到 59 tests / 1 failure / 3 errors / 40 skipped；报错直接指向缺少 zstandard，不能通过跳过测试解决。

在临时依赖目录解压真实 `zstandard==0.25.0` Linux wheel，用 `PYTHONPATH` 隔离补入后，同模块 **59 tests 全部通过，exit 0**。该版本也是原 Windows 成功环境已安装的版本；`pip download --only-binary=:all: --platform manylinux2014_x86_64 --python-version 311 --implementation cp --abi cp311 --no-deps zstandard==0.25.0` 成功，验证目标 CPython 3.11 Linux wheel 存在。

本任务因此在 `.github/workflows/ci.yml` 的 Python setup 后加入 `python -m pip install zstandard==0.25.0`。四个原检查完整保留，未添加 `continue-on-error` 或条件跳过。

### 待产品开发者处理的其他已复现族

以下来自干净 HEAD；其中测试夹具、过期登记/快照与既有预算问题需各自按实际根因处理，不能统一调低门槛。

| 失败族 / 主要位置 | 直接证据 | 处理边界 |
| --- | --- | --- |
| CLI registry：`infra/registry.py`、`tests/test_registry.py`、`tests/test_contract_matrix.py` | registry 106，engine/snapshot 107；差项明确为 `enforcement-check` | 补真实声明并同步合法冻结面；不能删命令或弱化完整性检查 |
| Result shape：`infra/contract_matrix/generator.py` / `snapshots.json` | `check_governance_write_shapes.row_families.deferred_observation.skip_kind` clean 为 `NoneType`，snapshot 为 `str` | 提取器需稳定夹具，避免当地治理运行态污染静态契约 |
| 根治理文件隔离：`tests/test_feat014_check28t_product_gate.py`、`test_fix270_product_gates.py`、`test_gate_sequence_for_release.py` | 分别有 2、2、3 个 ERROR；堆栈读根 `.governance/plan-tracker.md` 抛 `FileNotFoundError` | 对应单元测试用完整临时 host 或适当 stub；不向 CI 伪造当前项目状态 |
| E2E 投影副本：`test_dsh_adapter.py`、`test_projection_legacy_snapshots.py`、`test_release_ledger.py`、`test_verify_workflow.py` | `project/e2e-test-project/commands/governance/scenario-a.md` 等 ignored 副本在 clean clone 不存在 | 为测试准备隔离的受管投影夹具；避免修改用户工作树的本地安装 |
| 审查可信链旧夹具：`test_review_record.py`、`test_review_machine_provenance.py` | 单跑前者 26 tests / 9F / 10E；错误为 FEAT-094 `report not readable ... no report, no record (fail-closed)` | 测试需创建真实报告和修订事实，保留产品可信链拒收 |
| 条款/预算：`test_dsh_adapter.py`、`test_review_machine_provenance.py`、`test_injection_budget_gate.py` | 旧断言九条而 SKILL 为“十条与铁律同级”；关键行为契约 9648 bytes > 4096；skill tier 超 16000 tokens | 文案断言与第 10 条同步；容量问题关联当前已规划 FIX-450，不能直接扩阈值 |
| M0 固定来源：`infra/fixtures/m0/manifest.json`、`tests/test_contracts.py` | SKILL span `[225,232]` 当前 SHA `5105f0ef...` 与记录 `65d5fcb1...` 不符 | 查明授权演进和重新锚定方式；不能手工掩盖来源漂移 |

WSL 诊断环境只有 Python 3.12，没有 `python` 命令和 Node；其中 interpreter family 不在正式 pin `{3.11,3.14}`、Bash `python` 调用族、Node oracle 不可达属于环境差异。FIX-442 的真实文件 mtime 窗口测试在该环境也出现间歇不归因，尚不能断言 GitHub 同样失败。其余 live scan、静态版本针等族需在正式支持环境再次归因。本任务没有删除、隔离或豁免这些测试。

## 修改边界与门禁

本任务修改 `.github/workflows/ci.yml`（仅补必需依赖）和本诊断文档。产品根因、登记/快照及测试隔离问题已交 Coordinator；暂停 FIX-445 的两份 WIP 文件保全，不在 DevOps 提交范围。`git diff --check` 对两目标路径通过。

原始诊断环境全量测试已结束 exit 1；Linux `/tmp` 临时日志与 checkout 随后已不再存在，逐族关键错误已在本报告及工具输出中保留，不能补造丢失的完整统计。正式支持环境完整结果、产品修复提交及 GitHub Actions 绿色运行尚待 Coordinator 回填，当前不能声明 FIX-452 验收完成或 0.99.0 已发布。现有六次失败历史也不满足最近五次成功率至少 80% 的稳定性标准。

## 回滚与失败诊断

修复提交形成后，可通过 `git revert <FIX-452修复提交>` 回滚该独立修复；不得恢复或提交暂停的 FIX-445 WIP。对 CI 配置的回滚只移除新依赖安装步骤，四门不会改变。诊断文档可随该提交一并回滚。DevOps 未提交或推送远端分支、tag，也未变更发布状态；尚无真实部署回滚操作可验证。

重新失败时，先取得对应 run 的 job id，再用上述 job logs 接口获取原始日志；按 integrity → manifest → unit tests → cross-references 分别核实，不以 skipped 门禁视为通过。
