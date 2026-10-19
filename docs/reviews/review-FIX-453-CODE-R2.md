# FIX-453 CODE R2 — clean checkout phase2 九路径完整审查

- 日期：2026-10-19（Asia/Shanghai）；运行审计使用实际 UTC。
- 结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- HEAD：`3622889ba35c909c07951045761257b97c9b662c`
- 范围：`.governance/ci-phase2.json` 的九个 write_paths，作为 phase2 完整新范围审查，不是仅重读 R1 finding delta。只批准以下绑定的修复，不代表全 CI、FEAT-098、FIX-456、真实 DSH 或版本发布通过。
- 已读 CODE 角色、code-review/tech-review 规范、phase2 诊断、原31条 trace、九路径实际 diff 和相关既有 helper。Reviewer 未生产本票实现，未修改产品/index/治理，未创建提交或安装依赖；只新增本报告及授权仓内 scratch。

## 前轮与本轮边界

R0 仅审 marker 单行；`review-FIX-453-MARKER-R0.md` SHA256 `261eb45d5ba71cedd6dad435b336863d56395f53e8d4a62a64a3b2de772d7791`。R1 审另一18路径子集；`review-FIX-453-CODE-R1.md` SHA256 `83394bf95bc8be6347d80da54faa3a3b30081875c08ba9ec0309ee1f737f378c`。两报告本轮未改，均无待修 BLOCKING finding。

| 前轮备注 | 本轮裁决 |
| --- | --- |
| R1-N1 / Python 3.11 实跑义务 | 后续真实 run 39127309888 已发生且留下4942 tests / 18F / 13E / 38S，不能继续把它当未运行；该运行也不是全绿。本轮新修复提交后的 Ubuntu 3.11 全量仍待跑。 |
| R1-N2 / 外票失败 | FIX-450、FIX-449 的独立审查不由本报告替代；phase2 只处理本次明确映射的测试自足性问题。 |
| R1-N3 / synthetic legacy 不等于 shipped 历史资产 | 保留。本轮继续显式合成临时镜像，不以单元通过证明 ignored 私有历史代码已发行。 |

原 `.governance/ci-39127309888-failures.json` 有31条 trace（包含 subTest 条目，并非31个不同测试方法）。其中30条映射到本票 M0、registry、summary、ignored mirror、identity、release/SD fixture；坏 DSH exports 被 NOT_RUN 遮蔽的1条属于 FIX-456，未混入九路径或本轮测试结论。

## 九路径与差异绑定

下列当前 SHA256 在审查前后稳定，并与 Producer audit 的 source_files 一致。

| 路径 | SHA256 |
| --- | --- |
| `skills/software-project-governance/infra/fixtures/m0/manifest.json` | d822fed13b8e18a1310075f2235f98b1b49c1a0e07096f477c806743fffb97e4 |
| `skills/software-project-governance/infra/tests/test_contracts.py` | 80ca602e22acc77f3dfcd7a3e374f57e635c17450ce237d4125d9851cc46b2f3 |
| `skills/software-project-governance/infra/tests/test_dsh_adapter.py` | 05d8e42685a3b42d3e5fc957c0dacf99cec5d61e29ab9d85350acb3d06ce9e1d |
| `skills/software-project-governance/infra/tests/test_registry.py` | da8e578cf40fc53f3a0eb96cac10da9832056f6c14c3096df5d4e32b1b00cbe9 |
| `skills/software-project-governance/infra/tests/test_summary_only.py` | 9c987bf0258b24583b33184c3be494860d55924172276718f4dd2133896d8d5e |
| `skills/software-project-governance/infra/tests/test_verify_workflow.py` | a521789a2c7786c02352145e0425af8f6acd2a54434343940191ac96de55ba82 |
| `skills/software-project-governance/infra/tests/test_release_ledger.py` | 5026ce9e8f461b7b9dff159e085db7b181732390d231deeee92c895b15dc6635 |
| `docs/diagnostics/ci-clean-checkout-phase2.md` | c85df32de0f93e4f5bf351b121d176cd48072bf9874e35de34dee38cbad28d90 |
| `skills/software-project-governance/infra/checks/version.py` | dad3ba6bf47e10d8bfe55431a3edec1e7593850b3ae8553375536017ebc36666 |

按 dispatch 顺序拼接 `path + NUL + hex_sha256 + LF` 的集合 SHA256 为 `956c9cb972a7f1e956320413c2657504a2ff93b90eee54cbaadb3b266b3ec28a`。`git diff -- <九路径>` 输出 SHA256 `f397fe8d39a076e55eb1f02c6ec3acc42942bc3617b711cb71a560d4d32ae092`；新诊断 untracked，不进入 Git diff，以上完整文件 SHA 单独绑定。目标 `git diff --check` exit 0。

## 逐项审查裁决

### M0 pin 与冻结历史

新增 `test_contracts.py:1601` 从真实 SKILL 行区间检查完整节标题、1至11连续条款、细则不可读停止语义和下一节边界；旧 span hash 断言仍执行，不是以条款数量替代内容身份。独立读取 Git 原始 blob，复算两个 source_revision 的 file hash 和 LF-normalized span hash，均与 manifest 相符：

| 源 | 固定 revision | span | 实际 file SHA256 |
| --- | --- | --- | --- |
| behavior-protocol.md | 3622889ba35c909c07951045761257b97c9b662c | 522–568 | 95ef735c04e8e60610d5cc847ab16afb2eedde2e8843d8bada8d2e3748070b6c |
| SKILL.md | 同上 | 220–234 | 12620ab678e4dbfff7b8331b76e4f85f0fc9d573cfb924d8506551202e4fe556 |

SKILL span 包含 C1–C11 与动作前 MUST 读完整细则、不可读停止的指针；没有遗漏 C10/C11 或条5/6。file hash 的对象明确为该 revision 原始 blob，未把 FEAT-098 工作树四行当 shipped source。`frozen_revision`、五个 fixtures map、consumers、change_rule 与 HEAD JSON 逐字段完全相等；原 `rebaseline.last` 完整进入 history，新 prior 与原 sources 完全相等，既有更早 prior 没有丢失。五个冻结 fixture 的实际 hash 回归通过。没有修改 contracts.py 或消费者语义。

Reviewer 仅在隔离读返回值中移除 C11，新的节完整性守卫实际抛 AssertionError；冻结样本和生产文件没有被改写。

### Registry 与摘要文档链

`test_registry.py:1047` 将跨 OS/Python 不稳定的 exact population 改为固定 R6 **209 ceiling**，没有提高预算。真实 count 必须等于 modules 去重数、包含 verify_workflow；registry 不引入 engine/domain、domain check 不反向引 engine、registry/quickscan 不进入 engine face、冷启动和 importtime 等既有守卫保持。独立运行四项真实冷启动/依赖隔离测试通过；另注入一致的210模块 face，真实预算断言拒收。该结论是冻结 ceiling 语义，不能解释为证明每个标准库模块集合跨平台恒等。

`test_summary_only.py:452` 沿正文实际文档链接及 `§bootstrap-health` 指针读取目标 anchor 的所属节，保留 unavailable、timed out、parse degraded 三种状态断言。源码 `SKILL.md:63` 确有「每会话触发 MUST 先读」与该细则链接，未删去安全规则。独立移除全部细则链接、独立破坏 health anchor，测试分别拒收；游离细则文件不能单独满足该测试。正文与细则的真实链路通过，未把迁移后的词断言简单删除。

### 自足 projection 与 identity fixture

`test_verify_workflow.py:76`、`test_release_ledger.py:725` 和 SD live-plan 用例复用已审 `isolated_projection_root`：从 Git tracked canonical 文件构造临时树，通过真实 registry/planner 建立标明 SYNTHETIC 的 byte-copy/legacy 镜像；不再读取或回写开发者 ignored e2e 安装。独立 archive 刻意没有 `.governance` 与 ignored bootstrap mirror，所选文档/pack/projection 用例仍通过。文档原文相等、版本、mtime/bytes no-op 断言保留。

helper 生成镜像不是生产 planner/scanner 的成功 stub。独立缺 required projection ID、路径穿越、缺 legacy 文件、缺 backport marker、replace failure 真实 rollback 负例继续拒收/回滚。真实历史镜像是否发行仍由生产检查验收，不能从 synthetic 结果推出。

FIX300 presence 正例现在写显式 synthetic regular files 并使用 installed_host；这只证明 identity presence 差分一致，不再冒充 product_release 历史 authority。`test_verify_workflow.py:380` 另建完整合成 policy、source_records、真实字节/sha 与临时 product Git inventory，真实 scanner/attestor 经 engine 和 CLI 得到一致 PASS；没有 mock scanner verdict。四项 FIX300、既有 forged/missing/duplicate/edited source 拒收及空 controls/source_records 拒收均独立通过。合成 authority 的 fixture-only/release_authorized 边界仍由原协议持有，未伪造生产 DEC/EVD 历史。

### Release wiring、SD 真实拒收及 hook 环境

`test_verify_workflow.py:85` 的两个 patches 仅给原已隔离 sibling gates 的 release aggregator 用例提供可读 projection/hook 路径；**没有 mock SD scanner**，没有改生产 release/SD guard。新增 `:8694` 在这些 clean patches 之上改为缺失 projection，真实 readiness/CLI 仍报 structured unreadable、精确1 issue 与 exit 1。独立还运行原 projection-plan-error 和 SD-damage write 负例，均保持拒收；claim issue count 和 clean CLI green 对照均通过。

`test_dsh_adapter.py:58` 只调整测试临时路径：根据后代预留量选择仓内有界 fallback，copy fixture 缩为 `t/d`；不改系统 LongPaths 或用户配置。`_init_target_repo` 明确创建 `.git/hooks`，不再依赖 Git template 的 samples。`:866` 长 TEMP 与 `:875` empty template 用例实际调用原 self-upgrade 测试，仍执行真实 Bash hook、要求 self-upgraded 输出及升级后完整字节相等；没有 catch/skip OS 错误。本轮两项在 empty template 和仓内长父目录下均通过，**无 skip**。原 Bash 不可用时的 optional skip policy 没有扩张为系统错误豁免。

### 四条版本 exemption 重锚

Reviewer 对 HEAD旧行与新行逐字相等，并将 version.py 的四个行号反向替换、移除新增两注释后，结果与 HEAD 全文件相等。没有新增 exemption、token、reason 或扫描判据。

| 旧行→新行 | 原文 SHA256（不含换行） |
| --- | --- |
| 21224→21304；21256→21336 | 144695eb0d0a19b351793062ca7f3162e389f5f3a66e82f2e08e9f6c727ab682 |
| 20726→20803 | dbfa682196475c10aa6cb0733315b10df6e418ad0c1bd0cc6708201bba4dec4e |
| 20729→20806 | 4662235c744adcdbcf9c7c3ea5a9c50550b810a978ea5ada60c225c538a6dd4d |

## 独立运行与 Producer 证据区分

Reviewer 使用 HEAD `git archive` 建立全新仓内树，只 overlay 本票九路径；没有复制工作树 FEAT-098、FIX-456 或暂停 WIP。归档确认没有根治理目录及 ignored bootstrap。临时 Git 只以 archive 的精确 tracked pathspec 建 index（包括 HEAD 中被 ignore pattern 命中的 tracked 文件），无主仓 stage/commit/ref 修改。不是复用 Producer 已修复过的活动临时树。

**独立结果：36 tests / 0 FAIL / 0 ERROR / 0 SKIP，162.967s；另4个 mutation 拒收探针通过，均有原始日志。** 36项构成为 M0完整类6、startup4、summary2、hook2、projection/legacy/backport6、FIX300四项与真实authority负例两项共6、release CLI3、SD3、pack2、bootstrap/document mirror2。此计数只包含本轮所选不同方法，subTests 不另加。完整 IDs 在 command-audit 的 target-regressions argv 中。

Producer 的34条审计记录与对应日志 SHA 全部逐条重算相符，九文件 source binding 也相符。其最终四完整模块339 tests（337P/2 optional skips）、docs53P、release/SD84P、identity6P、static+long26P，以及重复 negative/gate 批次均为 **Producer 结果**；本 Reviewer 没有复跑或把重叠批次相加称为独立总测试数。两项 skip 为原 PyYAML/installed-schema optional capability；不是新增 skip。Producer 原 RED、中途缩进/断言/fixture index 构造错误及两次早期 refresh 元数据缺失均有明确披露；缺失 UTC 不补造、不借最终结果抹去。

## 五维度、设计与 AI 专项

| 维度 | 结论及依据 |
| --- | --- |
| 正确性 | 本范围通过。新 pin 覆盖完整规则且来源可核；fixture 在无私有资产 clean tree 运行；真实坏 authority/SD/projection 继续拒收，未用生产判据放宽换绿。 |
| 安全性 | 通过。生产唯一差异为四个冻结 exemption 行号与注释；无安装/profile/权限改动、无用户 HOME 操作。真实 scanner/rollback/hook 字节判定保留；合成数据明确 fixture-only。 |
| 可维护性 | 通过。复用统一 projection helper；显式区分 presence 与 product_release；使用路径预算而非机器路径特判。没有新增产品职责或 God module 功能，九路径承载同一 CI 自足性修复。 |
| 性能 | 未提高生产预算；209 ceiling 及依赖守卫仍执行，210反例被拒。本地测试复制 tracked 树有实际 I/O 成本，本轮162.967s如实记录；不声称完整 CI 提速或跨平台耗时恒定。 |
| 测试覆盖 | 通过本范围。36项代表性正负实测+4拒收探针，覆盖遗漏源、tamper、SD、空模板、长TEMP等关键分支；Producer扩大批次另列。未采集行覆盖率，不把计数当 strict 90% 或全仓通过。 |

对照 P1-P7/D1-D4 和 phase2 目标：修复以原 trace/RED 为依据，不读取私有 ignored 环境来换取成功；冻结语义及安全门保留，跨 Python/OS 预算和路径问题按通用规则处理。没有混入 FEAT-098 或 FIX-456 实现。

AI 五项：**mock残留**无新增生产 mock，release fixture 只替换路径选择并配真实 SD 负例；**硬编码成功**无，projection/scanner/attestor/hook 真实产生结果；**幻觉 API**无，复用现有真实 helper/入口并运行；**未实现 TODO**无新增；**过度实现**无，未扩安装、SDK、profile、发布能力。

## Findings 与范围备注

P0=0，P1=0，P2=0，P3=2；无未解决 BLOCKING finding，无需代码返工。

- **R2-N1 / P3：真实新提交 CI 待验。** 本次 Windows CPython 3.14.3 聚焦成功不能推导 Ubuntu Python 3.11 新提交全量成功，原 run 的4942/18F/13E/38S保持为真实失败基线。Coordinator 应在正常提交推送后检查新四门终态，本批准不替代该结果。
- **R2-N2 / P3：合成镜像与 wiring 证据边界。** synthetic mirror/source_records 的通过只证明测试契约和拒收泛化；不证明 ignored 历史安装副本已作为发行资产打包，也不证明真实用户宿主兼容。实际 projection/legacy、完整 release gate 与真实宿主验收各自仍需完成。

## R4 命令审计与保护校验

复用 QA venv：`.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe`，Python3.14.3、既有 zstandard，无安装。HOME/USERPROFILE/APPDATA/LOCALAPPDATA/DSH_HOME 全指向 `.codex-sandbox/FIX-453/review-r2/home`，TEMP/TMP 指向同范围 `tmp`，XDG_CACHE_HOME 指向 `cache`。Git global config 指向隔离空文件、NOSYSTEM=1、GIT_TEMPLATE_DIR 为空模板；DSH overrides、NODE_PATH 与相关 root 覆盖变量清除。PATH 仅 QA Python、既部署 Node/Git、System32；无真实 DSH/SDK 导入或网络操作。

完整实际 argv/cwd、UTC、exit、环境、影响路径与日志 SHA 见 `command-audit.json` 和 `boundary-audit.json`。测试内临时 Git/fixture 子进程归属其隔离 unittest 调用；未把命令声明冒充系统级全文件访问监控。

| 命令/审计label | 开始 UTC 2026-10-19 | 结束 UTC 2026-10-19 | exit | impact |
| --- | --- | --- | ---: | --- |
| archive-head：git archive --format=tar HEAD | 11:04:38.145262 | 11:04:38.635041 | 0 | 只读主仓HEAD，归档输出写Reviewer scratch |
| git-init：git init -q | 11:04:40.680839 | 11:04:40.737751 | 0 | 仅Reviewer临时树.git |
| git-index-tracked：git add -f --pathspec-from-file=tracked.nul --pathspec-file-nul | 11:04:40.739549 | 11:04:46.612688 | 0 | 仅临时树index；主仓index不动 |
| target-regressions：QA Python -B -X utf8 -m unittest（精确36项见argv）-v | 11:04:46.613936 | 11:07:31.937847 | 0 | 临时tree source/合成fixture读取，写入清理仅仓内scratch；真实Bash hook作用于临时repo |
| boundaries：QA Python -B -X utf8 boundaries.py --probe | 11:07:20.889103 | 11:07:21.562360 | 0 | 只读主仓scope/HEAD/Producer日志/保护文件hash，报告输出写scratch |
| mutation-rejections：QA Python -B -X utf8 -c（4反例） | 11:07:31.941535 | 11:07:33.707450 | 0 | 只在进程内替换隔离测试输入/face；无产品文件写入 |

保护文件只读hash核验保持：paused `infra/hooks/commit-msg` 为 `97806c18c2cfb5e0fb68e909f295fcc236e40b9e50f682ff8f177aed90cd46ac`；paused `infra/tests/test_hooks.py` 为 `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`；本轮未审其 WIP 内容。

| 证据（Reviewer scratch 为 `.codex-sandbox/FIX-453/review-r2/`） | SHA256 |
| --- | --- |
| command-audit.json | 216be54835b93c5fc512f434f8c15c7bd3c9b8538c92a9f800ddd88df928d3b4 |
| boundary-audit.json | a79186ec351799d1591d2898a7a96b90cbe937cbb4addd4485cdadc1899c4baa |
| logs/target-regressions.log | 5eacfd0b36b16be4e32c48cab08b47038d93e3305923523f12400f472497182a |
| logs/mutation-rejections.log | 5d7a8bd48456b2a96475364d4189606797137624499493df6b86bb07b5dc6f4b |
| logs/boundaries.log | 37cabbad9c64a66c2256ee90fa7ecb669f96c1403cb93471c8993cbefda29e72 |
| Producer `.codex-sandbox/p2/logs/audit.json` | 8f7b48987826ada19f362f135f77c4efbea87c6879d2256ec0ba99b3c197c4c2 |

本轮完整九路径审查、前轮逐项处理、五维度、AI五项、分级、真实运行与审计均已完成。审批仅绑定本范围；review-record、锁释放、正常提交/推送和远端CI终态由 Coordinator 处理。
