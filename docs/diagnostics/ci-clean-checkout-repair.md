# 干净 checkout CI 修复检查点（FIX-453）

更新：2026-10-17；初始提交：`a001057`；需求源：用户点名修复 Git 流水线。原始失败日志和 clean-clone 复现见 `ci-failure-0.99.0.md`。本报告为实施检查点，尚不是 CI 全绿或版本发布完成结论。

## 检查点 1：只修提交态 hook 版本标记

原始远端失败：Governance CI run `38835185972` / job `116762612087` 的 integrity 门报告 `hooks/commit-msg: @version=0.97.0, expected=0.98.0`，exit 1；前次 run `38833780678` 同型。受保护工作树已写 0.98.0，但包含暂停 FIX-445 的未提交实现，不能通过 `git add` 整体带入。

本检查点从 `git show HEAD:skills/software-project-governance/infra/hooks/commit-msg` 读取原始 blob，正则替换唯一的 `# @version: 0.97.0` 为 `# @version: 0.98.0`，在临时文件逐字节验证除该行外与 HEAD 相同；保留 index mode `100644`，用 `git hash-object -w` / `git update-index --cacheinfo` 将单行修复送入 index。

- 修改前 blob：`4ddad50…`；修改后 index blob：`fea62ef30b41576d99f4c620581952258130b4b2`。
- 正则实际替换数：1；反向替换还原原 blob 的字节断言通过；`git show :<path>` 与临时修复字节完全相同。
- `git diff --cached -- <hook>` 实际只有一行删除、一行新增：0.97.0→0.98.0，没有 FIX-445 实现混入。
- Agent 未写 hook 工作文件，未 stage 其他文件，未 commit/push；最终提交和远端验证由 Coordinator 负责。

两处暂停 WIP 在 index 写入前后均通过 `.governance/paused-wip-hashes.json` SHA256 比对：

| 文件 | 原始与检查点后 SHA256 |
|---|---|
| `infra/hooks/commit-msg` | `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac` |
| `infra/tests/test_hooks.py` | `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db` |

本阶段审查范围仅上述 staged marker 单行。其他工作树修复尚在实施，不能并称已审查或已通过。

## 检查点 2：完整远端日志后的共性修复

Coordinator 已分别提交并推送 marker-only `2fa4938` 与测试依赖 `2aae6ff`。后续 [Governance CI run 38923337599](https://github.com/peterwangze/software-project-governance/actions/runs/38923337599) 真实结果为 **4870 tests / 75 failures / 81 errors / 37 skipped，379.888s**。原始日志保存在 `.governance/ci-38923337599.log`，本轮读取现有日志，未重复下载或推断失败数。

本轮只修改已锁定的 18 个目标路径；不改 CI 四门、不改生产可信审查逻辑、未 stage/commit/push，也不改暂停 hook/test_hooks 或其他票范围。

### 实施与边界

- `adapters/dsh/launch.py`：将原 1590–1591 行的跨行 f-string 条件表达式抽为局部 `witness_status`，打印内容保持等价。远端 Python 3.11 的原 SyntaxError 是失败依据。本机只有 3.14/3.12：两者的 `ast.parse(feature_version=(3,11))` **连原坏代码也接受**，因此不能宣称已真实运行 Python 3.11。新增表达式行跨度回归明确旧代码 RED、新代码 GREEN，记录在 `pep701-boundary-regression.json`；真实 3.11 import/执行仍待 Actions。
- registry：补回 FEAT-095 已存在于 engine/snapshot、遗漏于注册表的 `enforcement-check`，实际 CLI 106→107；对齐两个固定 CLI 计数与已有冷启动记录 209，未增加执行入口或放宽约束。
- contract matrix：代表 Result 构造改用真实临时 initialized host，完整执行原 check，避免 ignored 本地 `.governance` 决定 `deferred_observation.skip_kind` 的类型。通过原 generator `--regen` 更新快照；原差异/篡改负例保留。
- behavior / Check 28t / FIX-270 / gate sequence：用完整临时 plan/evidence/risk/decision 文件绑定既有 host 事实入口，不再读取仓库 ignored 治理记录。新增未初始化 CLI 反例仍验证初始化边界。
- review_record / provenance：夹具建立真实 Git commit、报告字节与 ledger；未 mock Git/生产 trust reader/writer。正例重新验证记录 trust 为 CLEAN、commit 等于夹具真实修订；原缺报告/冲突语义没有绕过，覆盖 overwrite/backup/wiring 等旧行为。
- projection：真实 registry 的 10 条声明仍检查，但 fixture tree 明确标 `SYNTHETIC`，以临时副本验证声明、缺失、收敛、census、backport ledger 拒收；不借用本机 ignored 历史代码，也不宣称这些历史副本已 shipped。**发行资产缺失边界仍存在**，生产 `check_legacy_snapshots` 不变。
- DSH 单元 smoke：渲染/并发/清理测试显式设置临时 `DSH_INSTALL_DIR=<fixture>/absent-install`，阻止 fallback 到本机已改变的 0.2 插件集合；schema 面诚实输出 NOT_RUN，独立 installed-schema 拒收测试仍保留。原本机 5F 中 4F 源于缺 `@deepseek-ai/dsh-workflow-worker-thread`，另 1F 为 Windows Node staging rename EPERM；隔离后曾得到 74/74 PASS，EPERM未复现，**未据此宣称修复该文件系统问题**。
- FIX-442 文件时间窗口：临时文件明确写入固定 `os.utime(ns=...)`，时间因子和原负向拒收均保留，不通过 sleep 或放宽窗口制造通过。
- ArchGuard：通过正式 `archguard-ratchet --regen` 更新机器基线，FEAT-101 的 56 行删除使 R1 28270→28214，R2 保持 48 sites / 37 entries，R4 保持 1376。不是手编基线或调高容量。
- version exemption：仅将历史 `test_archive.py` Q6 同一 token/同一 reason 的行锚 5862→5870，没有增加豁免。

### 必须保留的失败

`test_review_machine_provenance.py` 的关键行为契约 4KB 检查真实失败：9648 bytes > 4096，未抬阈值。SKILL 现有列表已达 11 条，而 intro 写十条；本轮将 DSH 旧定值断言改为从真实条款数量派生，使该不一致响亮失败，避免原来九→十的替换制造假绿。两项均交 FIX-450/SKILL 范围处理，本轮不改 SKILL。

### 已持久化的工作树定向统计

UTF-8 原始输出位于仓库 `.codex-sandbox/FIX-453/`；下表是实际已有日志，尚不能替代完整 Actions：

| 模块 | 实际结果 |
| --- | --- |
| test_behavior_profile | 49 PASS |
| test_contract_matrix | 27 PASS |
| test_projection_legacy_snapshots | 26 PASS |
| test_gate_sequence_for_release | 45 PASS |
| test_review_record | 26 PASS |
| test_feat014_check28t_product_gate | 3 PASS |
| test_fix270_product_gates | 7 PASS |
| test_review_machine_provenance | 41 total / 1 failure（4KB，FIX-450） |
| test_dsh_adapter-restored | 74 PASS（加入条款数量派生守护之前的中间结果；当前 intro 失败需如实保留） |

命令模式：

```text
python -m unittest discover -s skills/software-project-governance/infra/tests -p <module>.py -v
python skills/software-project-governance/infra/contract_matrix/generator.py --regen
python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet --regen
```

所有后续命令的 `TEMP`、`TMP`、`DSH_HOME` 重定向至仓库 sandbox，未安装真实 DSH，未改用户 HOME 配置。原始完整远端失败保全；原 WSL 临时文件丢失的试验统计未补造。

## 干净 tracked checkout 验收

使用本地 `git clone --no-hardlinks`、禁用 fixture checkout hooks/template，获取 HEAD `2aae6ff1f1cf49e3566e25c5d55b7fe1afdb762f`，仅 overlay 当前 FIX-453 的 18 个目标文件。复制清单与解释器记录在 `clean-context.json`。检查已确认：根 `.governance` 不存在、ignored `scenario-a.md` 与 legacy engine 不存在；E2E skill 目录保留的两个文件本来即 tracked，不能把“目录存在”误当成本机忽略数据泄漏。

11 个相关模块最终共 **413 tests / 2 failures / 0 errors / 1 skipped**。两处 failure 分别为条款 11/10 不一致与 4KB 真超限，均保留交 FIX-450；其余通过。新增 schema FAIL 传播负例另跑 1/1 PASS，合计 414 次执行、411 PASS、2 FAIL、1 SKIP，未执行完整 4870 全套件。

| clean 模块 | tests | 实际结果 |
| --- | --- | --- |
| test_behavior_profile | 49 | PASS / 0F / 0E / 0S |
| test_contract_matrix | 27 | PASS / 0F / 0E / 0S |
| test_projection_legacy_snapshots | 26 | PASS / 0F / 0E / 0S |
| test_dsh_adapter | 74 | FAIL / 1F / 0E / 1S |
| test_review_record | 26 | PASS / 0F / 0E / 0S |
| test_review_machine_provenance | 41 | FAIL / 1F / 0E / 0S |
| test_gate_sequence_for_release | 45 | PASS / 0F / 0E / 0S |
| test_feat014_check28t_product_gate | 3 | PASS / 0F / 0E / 0S |
| test_fix270_product_gates | 7 | PASS / 0F / 0E / 0S |
| test_registry | 77 | PASS / 0F / 0E / 0S |
| test_archguard_ratchet | 38 | PASS / 0F / 0E / 0S |

- clean `verify`、`check-manifest-consistency --fail-on-issues`、`check-cross-references`：**exit 0 × 3**。
- 最终只将注释更新与新增 schema 负例 overlay 到同一 clean fixture，再执行正式 ArchGuard regen，检查 **R1/R2/R3/R4/R5/R7 全 PASS，0 violations**；authored exemption 保留 1 条，无新增豁免；将此严格本票源上下文的机器基线复制回目标文件。
- `contract_matrix/generator.py --check`：4 faces / zero drift / exit 0。
- `test_smoke_verifier_preserves_schema_failure_without_live_install`：1 test / PASS；受控 oracle 拒收仍向上传播 FAIL，安装面隔离不删除负向判据。
- 源根本票路径 `git diff --check`：exit 0；暂停 WIP 2/2 unchanged。

复查入口：`.codex-sandbox/FIX-453/clean-context.json`、`clean-results.json`、`clean-final-results.json`、`final-verification.json` 及对应 UTF-8 `.log`。这些是仓库内授权 scratch，不应整体加入产品提交。生产 snapshot 检查保留；当前合成单元夹具不能替代真实历史副本发行验收。


## 回滚、残余与交付边界

Coordinator 完成独立审查并形成独立修复提交后，用 `git revert <FIX-453提交>` 回滚；禁止整体 restore/reset/stash 共享工作树，以免覆盖暂停 WIP 或其他票。CI 四门保持原检查强度。

暂停文件 SHA256 已再次核对 **2/2 unchanged**，记录 `paused-wip-validation.json`：hook `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`；test_hooks `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`。

残余：Python 3.11 实际执行、完整远端 CI、范围外 test_verify/FIX-449、SKILL/FIX-450、DSH 0.2 原生接线/真实历史副本发行均未在本轮闭环，不能声明 CI 全绿、完成独立审查或发布完成。
