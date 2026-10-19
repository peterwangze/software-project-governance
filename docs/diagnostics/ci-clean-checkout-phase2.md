# FIX-453 phase2：干净 checkout 的测试自足性修复

2026-10-19。状态：Producer 修复及相关本地验证完成，等待独立审查；未提交、未推送。**不构成 GitHub CI 全绿或 0.99.0 发布通过。**

## 原始证据与范围

真实远端 run `39127309888`，head `3622889ba35c909c07951045761257b97c9b662c`，Linux Python 3.11.17：4942 tests / 18 FAIL / 13 ERROR / 38 SKIP。完整日志 `.governance/ci-39127309888.log`，31 条结构化 trace `.governance/ci-39127309888-failures.json`。前批 Python 3.11 语法错误已不再出现在本次失败中。本报告承接 `ci-clean-checkout-repair.md`，不覆盖或改写该报告。

本票处理其中 30 条 trace 对应的测试/fixture 根因；另 1 条 `test_dsh_contract.TestGuardContractFailureVerdicts.test_missing_apis_exports_is_a_fail_not_an_environment_gap` 是 FIX-456 生产问题：宿主不存在时 NOT_RUN 遮蔽坏 contract，应单独修复。本票没有改该 guard 或测试，也没有宣称它已通过。

此外，QA 的 `ci-integration-0.99.0.md` 已记录 Windows empty Git template 与长 TEMP 故障；被截断的原 suite 没有终态，不能用作成功证据。

## 修改与 RED → GREEN

| 类别 | 原错误/RED | 修复与保留的拒收边界 |
| --- | --- | --- |
| M0 pin | SKILL 旧 `[225,232]` span 的 hash 已与基线不符；本地 `red-assets` 复现 | 从已审 HEAD 源重钉完整「关键行为契约」节 `[220,234]`，包含 C1–C11 与细则不可读即停止指针；新增节边界与十一条完整性守卫。保留原 hash 断言、冻结样本与全部 rebaseline 历史。 |
| Git template | link/copy 在 `.git/hooks/pre-commit` copyfile 报 FileNotFoundError；`red-assets` 2 ERROR | `_init_target_repo` 明确创建 hooks 目录；新增空 template 下实际 hook self-upgrade 用例，没有依赖 Git 默认模板。 |
| 长路径 | QA 原始 Win206；本票 170 字符 TEMP 父目录重放旧 HEAD 时在同一 source-home mkdir 失败，当前机器返回 WinError 3 | copy fixture 使用最薄 `t/d` 目录和短随机前缀；按后代所需长度预留 100 字符，必要时落到 checkout 内测试目录。相同 170 字符父目录下新实现跑完真实 hook 升级，exit 0。没有改系统 LongPaths、用户配置或 skip。 |
| registry | Linux 198 != 209；本地隔离 Python 3.14 实测 207 != 209 | 总 import 数是冻结 R6 ceiling，不能要求 OS/解释器标准库人口完全相等；仍保留预算 209、不导入 engine/domain 的模块集合断言、懒加载/冷启动与 importtime 守卫。还校验真实计数与 modules 集合一致。 |
| summary | `Governance: unavailable` 等在迁移后的 SKILL 正文中找不到 | 先要求 SKILL 中实际可达的 MUST-read 链接与 `§bootstrap-health` 指针，再验证目标 anchor 所属节的 unavailable / timed out / parse degraded。游离细则文件不能满足断言。 |
| ignored mirrors | FEAT038 九条 ERROR、bootstrap/status ERROR、pack FAIL、release projection ERROR、SD projection face FAIL | 复用 `test_projection_legacy_snapshots.isolated_projection_root`，只读 Git tracked canonical 资产，以真实 registry/production planner 生成明确标注的合成临时 mirror；原文、版本、幂等/mtime、路径/库存/rollback 拒收断言继续运行。没有把个人 ignored 安装副本加入 Git。 |
| 私有 host | FIX300 正例从根 `.governance` 复制私有文件而 ERROR | presence 正例改为合成 regular files + `installed_host`，明确不证明历史 authority。新增完整合成 policy/source_records 的 `product_release` 正例，真实 scanner 与 attestor 经 engine/CLI 两条路径一致；缺源差分负例、forged authority 拒收与空 control 拒收独立复跑。没有伪造 DEC/EVD 生产历史内容。 |
| release wiring | 六条 FEAT016、四条 readiness、两条 FIX299 因漏列 SD fixture 多出 issues | 原本隔离所有 sibling gate 的 wiring fixture 现在也明确提供可读 canonical projection/hook face；SD scanner 继续真实执行。新增 absent projection 的真实 unreadable 拒收，要求 structured issues/unreadable、CLI exit 1 和精确 1 issue。既有 SD plan-error/损坏拒收继续通过。 |

### M0 正规 rebaseline

没有共享语义变更：`frozen_revision=m0-r1`、五个 fixture 的 sha/bytes、`contracts.py`、三个 batch1 consumers 与 `change_rule` 都保持原值。`contracts.py` blob SHA256 仍为 `42c8cb6fe8c70bb26435d7ac63153780f725333d710a47ea1f088f155e480875`。更新只涉及 pin 元数据，并将原 `rebaseline.last` 完整保存在 history 中；FEAT-042R/046/047 的契约测试随 `test_contracts` 全模块复跑。

源 revision 明确绑定 `3622889ba35c909c07951045761257b97c9b662c`。span hash 沿用 LF-normalized recipe；file hash 明确是 `git show source_revision:path` 的原始 blob bytes，而非当前 FEAT-098 未提交工作树。

| 源 | span | content SHA256 | file SHA256 |
| --- | --- | --- | --- |
| behavior-protocol.md | 522–568 | `988f3bb510eb0993e26f854942dd29131bfb62bfa53884f88fde6b9bcfe571bc` | `95ef735c04e8e60610d5cc847ab16afb2eedde2e8843d8bada8d2e3748070b6c` |
| SKILL.md | 220–234 | `89e97f58ca96ed8e408657912b4621b3b26c68581823946ab40d6ecf9ff18f7d` | `12620ab678e4dbfff7b8331b76e4f85f0fc9d573cfb924d8506551202e4fe556` |

FEAT-098 工作树四行在该节之外，不属于上述 source revision。以后若要声明整文件 hash 为新版本源，需要显式更新 revision/hash；不能把本 pin 当作未来整文件身份。正文迁移的安全语义由 FIX-450 审查承接，本票新增守卫只冻结当前完整注入节，不重新裁决规则。

### 四条静态针行锚同步

Coordinator 暂停 Producer 写入、重新获取九路径锁并更新 `.governance/ci-phase2.json` ALLOW 后，才修改 `checks/version.py`。没有新增 exemption，没有改 token/reason/schema。逐行相等比较和下列 SHA256 证明冻结 payload 未变：

| HEAD 旧行 | 新行 | token | 原文行 SHA256（不含换行） |
| --- | --- | --- | --- |
| 21224 | 21304 | 0.93.0 | `144695eb0d0a19b351793062ca7f3162e389f5f3a66e82f2e08e9f6c727ab682` |
| 21256 | 21336 | 0.93.0 | `144695eb0d0a19b351793062ca7f3162e389f5f3a66e82f2e08e9f6c727ab682` |
| 20726 | 20803 | 0.94.0 | `dbfa682196475c10aa6cb0733315b10df6e418ad0c1bd0cc6708201bba4dec4e` |
| 20729 | 20806 | 0.94.0 | `4662235c744adcdbcf9c7c3ea5a9c50550b810a978ea5ada60c225c538a6dd4d` |

静态针全模块 25 项及 version consistency 已通过；最终 verify 不再出现这四条 stale WARN。

## 验证环境与可复查命令

复用 `.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe`，Windows CPython 3.14.3、zstandard 0.25.0，无安装动作。工作目录 `.codex-sandbox/p2/t` 来自 HEAD `git archive`，没有根 `.governance`，没有本机 ignored bootstrap/scenario 镜像；仅 overlay 本票路径。冻结与回放均不读取 FEAT-098 WIP 作为 shipped source。

驱动 `.codex-sandbox/p2/run.py`；每条子进程的完整 argv、UTC 起止、exit、耗时、日志 SHA256、影响路径与 HOME/TEMP/Git 隔离变量在 `.codex-sandbox/p2/logs/<label>.json`，原始 UTF-8 输出在同名 `.log`；汇总见 `audit.json`。所有测试写入、临时 Git index/refs、模拟安装/卸载均限制于该仓库的 sandbox，真实用户 HOME 与配置零写入。测试内部 fixture subprocess 属于表中 unittest 命令的隔离范围，不代表真实宿主安装。

回放入口（在仓库根目录）：

```text
python .codex-sandbox/p2/run.py test <label> <unittest test IDs...>
python .codex-sandbox/p2/run.py gate <label> [verify_workflow subcommand]
```

| 最终 label / 完整目标见对应 JSON argv | 结果 | 说明 |
| --- | --- | --- |
| `modules-assets-final` | 339 tests，337 PASS / 2 SKIP，exit 0 | test_contracts、test_registry、test_summary_only、test_dsh_adapter 四个完整模块 |
| `verify-docs` | 53 PASS，exit 0 | PackStatus、StatusContract、EntryBootstrap、FEAT038、Projection 完整相关类 |
| `verify-release-final` | 84 PASS，exit 0 | ReleaseReadiness、FEAT016、FIX299、SDIntegrity 完整相关类 |
| `identity-final` | 6 PASS，exit 0 | FIX300 完整类 + 真 forged 拒收 + 合成完整 inventory 正例 |
| `release-negative-final` | 4 PASS，exit 0 | FIX299 三项 + empty controls/source_records 拒收；与上表重叠，不累计为新增测试数 |
| `pins-and-long-final` | 26 PASS，exit 0 | 静态针 25 项 + 最终长 TEMP 回归（外层也预留构造长父目录的空间） |
| `green-long-bounded` | exit 0 | 与旧 HEAD 同为 170 字符 TEMP 父目录，真实 copy hook self-upgrade 通过 |
| `gate-version-final` | exit 0 | check-version-consistency |
| `gate-verify-final` | exit 0 | 基础 verify，无 stale exemption WARN |
| `gate-manifest` / `gate-crossrefs` | exit 0 / 0 | manifest、引用/循环/quote sync 等原检查 |

两项 SKIP 沿用原 optional capability：PyYAML 不存在、installed dsh schema oracle 不存在；没有新增 skip，也没有把 NOT_RUN 记为 PASS。本票没有重复全仓 suite；表中局部成功不能推导 Linux Python 3.11 全量成功。

RED 原始日志：`red-assets`（5 tests / 3F2E）、`red-mirrors`（6 tests / 3F11E，含 subTest ERROR）、`red-long-original-2`（旧 HEAD、170 字符 TEMP、WinError 3、exit 1）。Windows 长路径的具体错误码可随 API/路径长度变化，QA 原始 Win206 与本次 WinError 3 都发生在 source-home mkdir；这里如实保留两者，没有声称本机重复得到 206。

## 中途失败、限制与回滚

所有中途日志保留，不能计为通过：一次 patch 缩进错误、一个新测试误以为 CLI 必显示 SD 路径（实际路径属于 structured details），均已修正后复跑。最初 export 的 `git add .` 漏掉「HEAD 已跟踪但命中 ignore」的文件，导致临时 projection fixture 缺 plan；随后按 archive 精确 1359 tracked 路径在 **sandbox-only index** 中恢复，没有复制 ignored 私有数据。其后稳定快照的完整最终批次通过；该构造错误只影响早期本地验证，不能归因为产品 bug。

早期重叠运行时修改过 sandbox index，identity 中途结果不用于结论；`identity-final` 在稳定 index 下独立完成 6P。两次早期 index refresh 使用同名审计文件，旧起止元数据未保全，不补造；最终 refresh、全部 RED/GREEN 测试命令及原始输出均有保留记录。`audit.json` 明确此边界。

本票未验证新提交的真实 Linux 3.11 CI 全量，也未解决 FIX-456，未验收真实 dsh 宿主安装。合成 legacy snapshot 仅用于测试 registry/漂移/ledger 拒收；不能证明发行包携带历史 E2E 源码。生产 snapshot、坏 contract、SD、release 四门检查均未放宽。

暂停 WIP SHA256 保持：commit-msg `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`；test_hooks.py `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`。未改主工作树 index/refs、系统 LongPaths、Git 用户配置或 `.governance` 治理记录。

回滚：由 Coordinator 对本票九路径的独立提交执行正常 revert；M0 rebaseline 与其守卫、四条行锚必须同批进出。当前未提交时，只撤回本票明确 diff，不能 reset/stash 或覆盖暂停 WIP。下一步为独立 Code Review，随后由 Coordinator 正常提交、推送并以真实 GitHub CI 结果决定流水线是否闭合。
