# 0.99.0 CI 候选集成验证（FIX-453）

**状态：TRUNCATED_EXIT_UNKNOWN。** 本轮完整 suite 的日志被截断，执行句柄与实际父/子进程均已消失，未取得最终 tests/F/E/S、退出码或完整失败 traceback。三基础门通过；完整单测验收未完成。未重跑 suite，也没有把进程消失判成执行成功。

## 范围与隔离

- 基准为 tracked commit `f0910607beaf5480b2f1d80718c8b639c4c34eda`，临时候选 fixture commit 为 `7dbbf9d9a23d6b87ffe48f69fc0a3fe948ce744b`。候选覆盖 FIX-453 已审 18 文件、FIX-450 候选 SKILL/新细则、FIX-449 测试共 21 路径，逐一 hash 见下。FIX-450/449 属 prospective integration，不因本 QA 获得代码审查批准。
- 保护的 `hooks/commit-msg` 与 `test_hooks.py` 来自指定 HEAD，未复制暂停 WIP；未复制 ignored 根 `.governance`、`project/e2e-test-project` 或 `.codex-sandbox`。fixture commit 仅在 sandbox clone，用隔离 hooks/template/身份/GPG 配置，不修改主仓 index、commit 或 refs，不推送。
- 实际 Windows CPython 3.14.3，解释器 `C:/Python314/python.exe`；不能替代 GitHub Linux Python 3.11。
- 测试子进程 HOME、USERPROFILE、APPDATA、LOCALAPPDATA、DSH_HOME、TEMP、TMP 重定向 sandbox；去掉 npm shim PATH、DSH 选择变量、NODE_PATH/PYTHONPATH，Git 用户配置重定向且禁用 system 配置。未重装插件、未读取真实 DSH profile、未启动 DSH/模型/网络服务。

## 实际命令与终态证据

| 命令 | UTC 开始 → 结束/最后写入 | exit | 实际耗时 |
| --- | --- | --- | --- |
| `C:\Python314\python.exe skills/software-project-governance/infra/verify_workflow.py` | 2026-10-18T12:00:55.235592+00:00 → 2026-10-18T12:00:57.597604+00:00 | 0 | 2.362s |
| `C:\Python314\python.exe skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues` | 2026-10-18T12:00:55.235814+00:00 → 2026-10-18T12:00:56.266761+00:00 | 0 | 1.031s |
| `C:\Python314\python.exe skills/software-project-governance/infra/verify_workflow.py check-cross-references` | 2026-10-18T12:00:55.236074+00:00 → 2026-10-18T12:00:56.314577+00:00 | 0 | 1.079s |
| `C:/Python314/python.exe -m unittest discover -s skills/software-project-governance/infra/tests -v` | 日志创建 2026-10-18T12:00:55.236057+00:00（命令起始未持久化）→ 日志最后写入 2026-10-18T12:11:27.318179Z | **未知** | **未取得完整耗时** |

- 原工具 session `20015`，driver PID `35132`、unittest PID `27200`。首次 checkpoint 时二者都存在。恢复时在本 QA Agent 与 Coordinator 两侧调用同 session 均返回 `Unknown process id 20015`，不是仅跨 Agent 句柄不可共享。
- 本 QA 2026-10-18T12:14:32.1481723Z 的 `Get-CimInstance Win32_Process -Filter "ProcessId = 35132 OR ProcessId = 27200"` 成功返回空集合（命令 exit 0），两个精确 PID 均不存在。原始输出见 `process-resume.json`，恢复操作记录见 `resume-audit.json`。
- `suite.log` 缺 `Ran N tests in ...`、`OK/FAILED(...)` 与尾部 traceback，`suite.json`、`all-commands.json` 均不存在。driver 只有 `subprocess.run` 返回后才写该命令 JSON，并在全部 future 返回后写 all-commands，因此没有正常采集完整 suite 终态的证据。
- 原始日志 **457525 bytes**，SHA-256 `1f4e1f4afbabf0629467307f156b8b9d72d0cdbe917d37bbc4ad5473148a627f`；逐字备份 `suite.truncated-preserved.log` 与原 hash 相等。原日志未删改。

## 部分状态与未完成分类

截断日志观察到 **2465 条 ok 结尾状态行、12 条 FAIL、7 条 ERROR、65 条 skipped 状态行**。这些是部分输出计数，不是最终 tests/F/E/S，也不能计算完整通过率。多行 docstring 的 FAIL/ERROR 已回溯到此前准确 test ID，期望负例打印的 `ERROR:` 文本没有计为失败状态。

| 部分 test ID | 已输出状态 | 当前归类证据 |
| --- | --- | --- |
| `test_archive.TestBigTableResumableMigration.test_finalize_crash_resume_completes` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_archive.TestBigTableResumableMigration.test_stage_crash_resume_skips_completed_batches` | ERROR | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_contracts.M0FixtureManifestTests.test_pin_revision_hashes_still_resolve` | FAIL | M0 source hash pin 线索：实际 pinned span 校验未通过；需恢复 traceback/具体 hash 才能确定对象 |
| `test_dsh_adapter.DshAdapterTests.test_hook_discovers_dsh_copy_mode_snapshot` | ERROR | hook fixture 调用 ERROR；缺 traceback，不能用 host absent 自动豁免 |
| `test_dsh_adapter.DshAdapterTests.test_hook_discovers_dsh_link_mode_marker` | ERROR | hook fixture 调用 ERROR；缺 traceback，不能用 host absent 自动豁免 |
| `test_dsh_adapter.DshAdapterTests.test_uninstall_dry_run_deletes_nothing` | ERROR | hook fixture 调用 ERROR；缺 traceback，不能用 host absent 自动豁免 |
| `test_dsh_contract.TestGuardContractFailureVerdicts.test_missing_apis_exports_is_a_fail_not_an_environment_gap` | FAIL | fake-oracle 负例 FAIL；不是 installed-schema SKIP，仍需定位 |
| `test_fix394_progress_suffix_refresh.TestComposerClosureCheck1.test_closure_probe_face_reads_refreshed_row_as_committed` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_governance_cost.Feat039ZstandardDependencyAssertionTests.test_zstandard_dependency_is_present` | FAIL | 环境依赖线索：同模块明确输出 zstandard not installed；不得据此认定 Actions 已安装 zstandard 后也失败 |
| `test_governance_cost.Feat040TtfaAcceptanceTests.test_cli_flag_absent_keeps_the_report_shape` | ERROR | 环境依赖线索：同模块明确输出 zstandard not installed；不得据此认定 Actions 已安装 zstandard 后也失败 |
| `test_governance_cost.Feat040TtfaAcceptanceTests.test_cli_flag_reaches_the_report` | ERROR | 环境依赖线索：同模块明确输出 zstandard not installed；不得据此认定 Actions 已安装 zstandard 后也失败 |
| `test_governance_cost.TestZstandardFailClosed.test_cmd_exits_nonzero_without_zstandard` | ERROR | 环境依赖线索：同模块明确输出 zstandard not installed；不得据此认定 Actions 已安装 zstandard 后也失败 |
| `test_hooks.BashParityTests.test_bash_hits_bold_and_plain_rows` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.BashParityTests.test_bash_hits_bold_and_plain_rows` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.PostCommitWriteGuardPanelTests.test_crash_rc1_without_verdict_is_unavailable_not_fail` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.PostCommitWriteGuardPanelTests.test_fail_state_renders_panel_and_continues` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.PostCommitWriteGuardPanelTests.test_pass_state_renders_pass_line` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.PostCommitWriteGuardPanelTests.test_skip_when_no_verify_workflow` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |
| `test_hooks.PostCommitWriteGuardPanelTests.test_warn_state_renders_warn_count_line` | FAIL | 缺尾部 traceback：候选引入/原有缺陷/平台环境尚不能区分 |

- 已明确输出的跳过中，DSH oracle 不可发现 22 条，zstandard 不可用 40 条。DSH 宿主被主动隔离，因此前者只代表 NOT_RUN；后者属于本地测试环境依赖缺口，不能声称与 Actions 安装依赖后的环境等同。
- 静态查读仍有 `test_verify_workflow.py` 依赖 ignored `project/e2e-test-project`（例如 L10021、L16915、L23878）；完整 suite 尚未走到该文件，不能把它提前计成本轮已观察失败。

## 中断原因调查边界

- 最后开始但未输出结果的 test ID：`test_loop_runtime_claims.LoopRuntimeClaimTests.test_real_repository_inventory_complete_and_within_budget`。
- 候选 `test_loop_runtime_claims.py:930–942` 此测试执行两次真实扫描，其中一次用 tracemalloc 采样；源码没有主动结束 driver/父进程的语句。最后一行只说明中断发生时正在该用例，不能据此判该用例 FAIL、超时或内存超限。
- driver 代码没有人为 suite timeout、terminate 或 cancel；QA 没有发终止命令。**退出原因 UNKNOWN**：没有进程终止事件或工具退出结果，不能确认 scope/生命周期清理、进程崩溃、系统终止或其他因果。
- 没有可继续运行的原 OS 进程；反复收取失效句柄不能恢复 traceback。本轮保留为截断/exit 未知。遵照本任务红线，不启动第二次完整 suite；后续复验须由 Coordinator 另行安排持久化执行与完整尾部采集。

## 质量判定与复查入口

- 三基础门 PASS；完整单测验收 INCOMPLETE，既有已输出 FAIL/ERROR 仍未关闭。没有 CI 全绿、发布或 DSH 原生适配完成结论。
- tests 总数、完整通过率、最终 F/E/S、退出码、完整耗时：UNKNOWN；覆盖率未做 instrumentation；没有单独性能基线或 HIGH/CRITICAL 扫描结果。
- 可复查：`snapshot-manifest.json`、`review-binding-check.json`、`suite.truncated-preserved.log`、`truncated-resume.json`、`partial-status-records.json`、`process-resume.json`、`resume-audit.json`。`parse_suite.py` 可只读解析日志，但截断输入不会产生不存在的尾部 traceback。
- 原 `running-checkpoint.json` 保留作为历史时点记录；当前终态以 `truncated-resume.json` 与本报告为准。

## 后续最小重放（独立 venv，原截断结论保留）

Coordinator 后续授权七组最小重放后，本 QA 仅在既有 sandbox 创建 `replay-venv`，一次安装 `zstandard==0.25.0`，未安装到系统 Python。执行 `--no-cache-dir --index-url https://pypi.org/simple`，PIP_CONFIG_FILE 指向 `nul`，HOME/TEMP/cache 全部隔离；未读取用户 pip/DSH 配置。venv-create、venv-pip、venv-verify 均正常 exit 0。实际下载 wheel 为 `zstandard-0.25.0-cp314-cp314-win_amd64.whl`，验证版本 0.25.0、包文件位于 venv/Lib/site-packages；本轮只对齐工作流的该依赖版本，操作系统与 Python 版本仍不等同 Linux 3.11。

七组各用独立 HOME、USERPROFILE、APPDATA、LOCALAPPDATA、DSH_HOME、TEMP/TMP、cache，venv/Scripts 位于子进程 PATH 首位，移除 DSH shim；测试仅加载原 frozen candidate，不改主项目产品、index、refs 或暂停 WIP。各组独立 log/JSON 在返回当下写入，正常 `ERROR:` 负例输出没有被计作 unittest ERROR。未运行第二次完整 discover，也未重试失败以取得绿灯。

**结果：18 tests / 14 PASS / 2 FAIL / 2 ERROR / 0 SKIP。** 这是 18 个最小目标的结果，完整 suite 仍为 TRUNCATED_EXIT_UNKNOWN。

| 目标组 | tests / PASS / F / E / S | unittest 耗时 | 进程耗时 | exit | UTC 开始 → 结束 |
| --- | --- | --- | --- | --- | --- |
| `test_archive` | 2 / 2 / 0 / 0 / 0 | 0.447s | 0.818s | 0 | 2026-10-18T12:20:18.403372+00:00 → 2026-10-18T12:20:19.221322+00:00 |
| `test_contracts` | 1 / 0 / 1 / 0 / 0 | 0.004s | 0.256s | 1 | 2026-10-18T12:20:18.403691+00:00 → 2026-10-18T12:20:18.659190+00:00 |
| `test_dsh_adapter` | 3 / 1 / 0 / 2 / 0 | 0.318s | 0.643s | 1 | 2026-10-18T12:20:18.402933+00:00 → 2026-10-18T12:20:19.046075+00:00 |
| `test_dsh_contract` | 1 / 0 / 1 / 0 / 0 | 0.567s | 0.833s | 1 | 2026-10-18T12:20:18.667926+00:00 → 2026-10-18T12:20:19.500549+00:00 |
| `test_fix394_progress_suffix_refresh` | 1 / 1 / 0 / 0 / 0 | 0.073s | 0.567s | 0 | 2026-10-18T12:20:19.053834+00:00 → 2026-10-18T12:20:19.620901+00:00 |
| `test_governance_cost` | 4 / 4 / 0 / 0 / 0 | 0.022s | 0.397s | 0 | 2026-10-18T12:20:19.233082+00:00 → 2026-10-18T12:20:19.630289+00:00 |
| `test_hooks` | 6 / 6 / 0 / 0 / 0 | 4.642s | 15.144s | 0 | 2026-10-18T12:20:19.510818+00:00 → 2026-10-18T12:20:34.654425+00:00 |

### 已取到完整 traceback 的失败

1. **M0 source pin 陈旧（现有基准即未修）**：`test_contracts.M0FixtureManifestTests.test_pin_revision_hashes_still_resolve`，`test_contracts.py:1588`。SKILL span `[225,232]` 期望 `65d5fcb1fee6817c40b73311e0cd1d29df3375359c58be6ba811710c4de7e375`，候选实际 `c292c8bd4a1d0551de1e1f3d2624f038193c9d1d9d118b4ee1ae430cc951e279`。只读读取固定基准 f091060 的同 span 得到 `5105f0ef724a024b1e53e73177340428c3a4fff3466c9ac88102faab757b40ac`，也不等于期望；因此不能把该失败归成 FIX-450 新引入。需按 manifest change_rule 正规重定 pin（内容/行锚/文件 hash 一致），不能把冻结样本或断言改成跳过。

2. **契约缺陷被 host absent 提前返回遮蔽（原基准未修，真实 guard 逻辑问题）**：`test_dsh_contract.TestGuardContractFailureVerdicts.test_missing_apis_exports_is_a_fail_not_an_environment_gap`，`test_dsh_contract.py:2145` 实得 NOT_RUN、期望 FAIL。该测试去掉 `host.apis.js-yaml.exports`，但 `dsh_compat.py:1896–1904` 在 probe 脚本渲染/该字段访问前先判断安装可用性并返回，reason 为 no dsh plugin set discovered。此分支让坏契约在无宿主环境被归到 NOT_RUN；本例不是 installed-schema 正常跳过。只读对象对比已确认 candidate 的 dsh_compat.py 与 test_dsh_contract.py 均与 f091060 相同，非本轮 CI 18 文件改动引入；应独立补齐无宿主时仍能执行的契约字段验证/防护。

3. **DSH link fixture 缺 Git hooks 目录（本地隔离环境与夹具前置条件）**：`test_dsh_adapter.DshAdapterTests.test_hook_discovers_dsh_link_mode_marker` 在 `test_dsh_adapter.py:775` 的 shutil.copyfile 先报 FileNotFoundError，目标为临时仓 `.git/hooks/pre-commit`。`_init_target_repo` L754–758 仅 git init，未 mkdir hooks；本 QA 按安全隔离要求设置 GIT_TEMPLATE_DIR 为仓内空 template，git init 无默认 sample hook 目录，暴露该夹具对默认模板目录的依赖。该错误尚未执行 stale hook 验证，不是插件运行时失败证明，也不能直接推为 Actions 默认 Git 模板下必失败。

4. **DSH copy fixture Windows 路径过长（本地平台/隔离路径限制）**：`test_dsh_adapter.DshAdapterTests.test_hook_discovers_dsh_copy_mode_snapshot` 在 `_write_source_home` L767 的 mkdir 报 `WinError 206 文件名或扩展名太长`，发生在构造 sandbox 内的 dsh-home/.agent-presets/governance/skills/software-project-governance/infra/hooks，尚未运行 hook。异常路径为 251 个字符；本轮 per-group 隔离路径比原 suite TMP 更深，因此该 traceback 只准确归因本次最小重放，不能补造为原截断 ERROR 的原始 traceback。本 QA 没有缩短路径或重试来掩盖该 IO 限制。

原始 traceback 直接证据：

- M0 span：`minimal-replays/test_contracts.log`（L1588 断言与两侧 hash），命令/exit/UTC 见同名 `.json`。
- DSH contract：`minimal-replays/test_dsh_contract.log`（L2145，NOT_RUN != FAIL 及 host absent reason），命令记录见同名 `.json`。
- DSH link/copy 两项：`minimal-replays/test_dsh_adapter.log`（L775 缺 .git/hooks；L767 WinError206），命令记录见同名 `.json`。
- 上述均相对于 `.governance/sandboxes/ci-integration-20261018/`；`minimal-replays/parsed-results.json` 同时保存完整结构化 traceback 与七组量化结果。

### 此次通过但不能回写原完整 suite 的目标

- cost 四项目标：安装固定依赖后全部通过；其中 fail-closed 负例按预期打印 `ERROR: zstandard 未安装...` 然后该 unittest 为 ok。原缺依赖结果继续保留，不能声称原 suite 因此完整通过。
- archive 两项 crash/resume、fix394 closure 一项、committed hooks 六项及 uninstall dry-run 一项此次全部通过。它们的原截断状态缺 traceback；本次还改变了 venv/PATH、依赖和逐组上下文，不能仅凭重放通过确定原失败根因、宣称原问题修复或归因顺序污染。需要更大上下文的模块级取证，由 Coordinator 单独安排；本 QA 未扩大或循环重试。

### 重放证据与审计

- 原始逐组 `.log/.json`、`parsed-results.json`、`baseline-attribution.json` 均位于 `.governance/sandboxes/ci-integration-20261018/minimal-replays/`，记录准确 test ID、完整 traceback、UTC、exit、包版本与文件 SHA。所有新 subprocess（venv/pip/验证/7组/3次只读基准 Git）已逐条追加 `command-audit.json`。
- 执行入口 `run_minimal_replays.py` 是本次已执行脚本，现有 venv/evidence 路径保护使其不能误覆盖重跑；保留之前的 replay_targets.py 作为原计划脚本，不将其“仅建议”状态误称本次执行证据。
- 原 suite.log 与 suite.truncated-preserved.log 仍逐字一致；报告前部的截断统计和 UNKNOWN exit 不修改。

## 原始最小目标与命令建议（历史计划）

按以下模块分别执行固定的失败目标，每个模块生成独立 UTF-8 log/JSON 与完整尾部 traceback，避免等待完整 suite 结束才获得信息。脚本仍将用户目录/DSH/Git 配置隔离到原 sandbox，仅设置 candidate tests/infra 的 PYTHONPATH 供 unittest 加载；不会安装依赖或运行 discover。18 个唯一目标覆盖 19 条已观察失败状态（BashParity 两个 subtest 共用同一 test ID）。

| 模块 | 类/测试目标 | 建议命令 |
| --- | --- | --- |
| `test_archive` | `TestBigTableResumableMigration.test_finalize_crash_resume_completes`<br>`TestBigTableResumableMigration.test_stage_crash_resume_skips_completed_batches` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_archive` |
| `test_contracts` | `M0FixtureManifestTests.test_pin_revision_hashes_still_resolve` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_contracts` |
| `test_dsh_adapter` | `DshAdapterTests.test_hook_discovers_dsh_copy_mode_snapshot`<br>`DshAdapterTests.test_hook_discovers_dsh_link_mode_marker`<br>`DshAdapterTests.test_uninstall_dry_run_deletes_nothing` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_dsh_adapter` |
| `test_dsh_contract` | `TestGuardContractFailureVerdicts.test_missing_apis_exports_is_a_fail_not_an_environment_gap` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_dsh_contract` |
| `test_fix394_progress_suffix_refresh` | `TestComposerClosureCheck1.test_closure_probe_face_reads_refreshed_row_as_committed` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_fix394_progress_suffix_refresh` |
| `test_governance_cost` | `Feat039ZstandardDependencyAssertionTests.test_zstandard_dependency_is_present`<br>`Feat040TtfaAcceptanceTests.test_cli_flag_absent_keeps_the_report_shape`<br>`Feat040TtfaAcceptanceTests.test_cli_flag_reaches_the_report`<br>`TestZstandardFailClosed.test_cmd_exits_nonzero_without_zstandard` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_governance_cost` |
| `test_hooks` | `BashParityTests.test_bash_hits_bold_and_plain_rows`<br>`PostCommitWriteGuardPanelTests.test_crash_rc1_without_verdict_is_unavailable_not_fail`<br>`PostCommitWriteGuardPanelTests.test_fail_state_renders_panel_and_continues`<br>`PostCommitWriteGuardPanelTests.test_pass_state_renders_pass_line`<br>`PostCommitWriteGuardPanelTests.test_skip_when_no_verify_workflow`<br>`PostCommitWriteGuardPanelTests.test_warn_state_renders_warn_count_line` | `C:/Python314/python.exe -X utf8 .governance/sandboxes/ci-integration-20261018/replay_targets.py test_hooks` |

以上为最初恢复时的计划命令；后续已按 Coordinator 新授权通过 run_minimal_replays.py 执行七组最小目标，实际结果见上节，未执行第二次完整 suite。精确 module/class/test 字段见 `replay-targets.json`。

## 可机录命令审计

- `command-audit.json` 包含全部隔离 subprocess argv/cwd、已持久化 UTC 起止、exit、影响路径及 OS 查询命令。精确时间未采集的只读 Git/早期进程查询明确为 null，并给事实时间窗，不补造秒级时间。
- `resume-audit.json` 保留工具句柄失败、精确 PID 查询和零真实 HOME 写入声明；命令审计 SHA-256：`75451d0a7e666831c301da49915f63a7d471b71f6ecb2b9a9357947710bc100d`。

## 对象与证据绑定

- Snapshot manifest SHA-256：`41a4a97510b19477e0e7aea6f2931699977560cbe9f4bb4bc97f784fe2f82581`。
- `review-binding-check.json` 核对 FIX-453 全部 18 文件均与 CODE R1 绑定 hash 相等。
- 原始命令 argv、cwd、UTC 起止、exit、耗时、日志 SHA-256 逐条见同目录 `clone.json`、`checkout.json`、`fixture-add.json`、`fixture-commit.json`、三门 JSON；本次 suite 终态 JSON 缺失，按上文截断状态披露。以上写入均在授权 sandbox 内。

| 候选路径 | 来源 | 字节 SHA-256 |
| --- | --- | --- |
| `adapters/dsh/launch.py` | `adapters/dsh/launch.py` | `26b4323ba7a8f854379d60dae33b3fb8c24270ed07c6993d06414a025fd94007` |
| `skills/software-project-governance/core/architecture-baseline.json` | `skills/software-project-governance/core/architecture-baseline.json` | `e301df70d90cd20220c59a6480fcf589b8640e396d8fe9f2cbcd1cff1f0294ad` |
| `skills/software-project-governance/infra/registry.py` | `skills/software-project-governance/infra/registry.py` | `043c00fd0b84c3a1a1ae4b97b10dbcec3bdd7d2a531f8ce252ba9a4b905535b8` |
| `skills/software-project-governance/infra/checks/version.py` | `skills/software-project-governance/infra/checks/version.py` | `129a59906080442327a64d1d98f383fe292c62c1f3dfe66f4400d9256dea2f31` |
| `skills/software-project-governance/infra/contract_matrix/generator.py` | `skills/software-project-governance/infra/contract_matrix/generator.py` | `4e3284163a353e73d834c206c8f0be41f09ec4768b2f5ef49daec07656275feb` |
| `skills/software-project-governance/infra/contract_matrix/snapshots.json` | `skills/software-project-governance/infra/contract_matrix/snapshots.json` | `ab0e327fa66eae7c0ea0d66c008801454f8d4e1dac98da2c5ecedf82514f8193` |
| `skills/software-project-governance/infra/tests/test_registry.py` | `skills/software-project-governance/infra/tests/test_registry.py` | `7a78c2da1434ed0ed679b1b44a7e9849197d028fee2964277b6fe855ab92bbb2` |
| `skills/software-project-governance/infra/tests/test_archguard_ratchet.py` | `skills/software-project-governance/infra/tests/test_archguard_ratchet.py` | `afa3765150beeae20f7d3837caae6567d96f1f035e4dfc85265feac00ac40fa6` |
| `skills/software-project-governance/infra/tests/test_behavior_profile.py` | `skills/software-project-governance/infra/tests/test_behavior_profile.py` | `cebff9842207ee905395ce39429646daaeafd8228e54d3a474ca3c3973280b47` |
| `skills/software-project-governance/infra/tests/test_contract_matrix.py` | `skills/software-project-governance/infra/tests/test_contract_matrix.py` | `22d01ee1adaa9a5c8a256fe0851c30ab2a6b3a48924341ef954365d0b67a9915` |
| `skills/software-project-governance/infra/tests/test_dsh_adapter.py` | `skills/software-project-governance/infra/tests/test_dsh_adapter.py` | `3ecad49c23da4d49199988ebb09ff930aca10b5124c309c1c19b7b3632aa8225` |
| `skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py` | `skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py` | `e7106b01d4929a2b96241ae86a371fe021cd42694a40e4727257bad84115a8f2` |
| `skills/software-project-governance/infra/tests/test_fix270_product_gates.py` | `skills/software-project-governance/infra/tests/test_fix270_product_gates.py` | `1df4438efe84dd64f7f5757aca30619cda0f2b75f27f1c086718c39cc193393f` |
| `skills/software-project-governance/infra/tests/test_gate_sequence_for_release.py` | `skills/software-project-governance/infra/tests/test_gate_sequence_for_release.py` | `e28354f7d616a5d9a9168d4b1af69db47c482a178bcf22e84fed0a6e193a06c0` |
| `skills/software-project-governance/infra/tests/test_review_record.py` | `skills/software-project-governance/infra/tests/test_review_record.py` | `9c1a24b50f585871f5aa3ab5d62a8046964f912c085226cc53ee7c3e2f31a931` |
| `skills/software-project-governance/infra/tests/test_review_machine_provenance.py` | `skills/software-project-governance/infra/tests/test_review_machine_provenance.py` | `042d3168c5481977fe3d92281b71c6bead7ccd8a349655500b67e5e78fc2b86f` |
| `skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py` | `skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py` | `f4ebc6b03144755e0adba87c60f8f1b294dc5140db792aebf85d1d3f7ff66cd9` |
| `docs/diagnostics/ci-clean-checkout-repair.md` | `docs/diagnostics/ci-clean-checkout-repair.md` | `c0ca5f7ab83664129ba7ea40fb408df08da2938758a2af1259dd99c844f015c8` |
| `skills/software-project-governance/SKILL.md` | `.governance/candidate-FIX450-SKILL.md` | `6c0c5e54db1cd4839bb4d4a10544846fee326e019728ca2c42e49f5f8e88e6c3` |
| `skills/software-project-governance/references/behavior-contract-details.md` | `skills/software-project-governance/references/behavior-contract-details.md` | `e2f9899ee060dd2126a917a34bd34965edc73e1450f6a112d8b5108a6cb879ac` |
| `skills/software-project-governance/infra/tests/test_verify_workflow.py` | `skills/software-project-governance/infra/tests/test_verify_workflow.py` | `e9e33cdd8843a7d9725bd253ac8eb32961231de38ce53b941d195f8936726799` |

保护文件（仅从固定 HEAD）：

| 路径 | checkout 字节 SHA-256 | 基准 blob SHA-256 |
| --- | --- | --- |
| `skills/software-project-governance/infra/hooks/commit-msg` | `a038f41dff3879adbdab05e7f26df6420f8ecb8df0423601c8a0e1fdd72185b8` | `a038f41dff3879adbdab05e7f26df6420f8ecb8df0423601c8a0e1fdd72185b8` |
| `skills/software-project-governance/infra/tests/test_hooks.py` | `3a5a61caefe95c7a9eceb77f3c942ac821e11d08ad521fe42808c4dba82669a6` | `3a5a61caefe95c7a9eceb77f3c942ac821e11d08ad521fe42808c4dba82669a6` |

