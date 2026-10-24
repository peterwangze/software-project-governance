# FEAT-102 — 原生派生设计增量复审 R6

- 日期：2026-10-20（Asia/Shanghai）；独立 Design Reviewer（未参与本设计或实现）。
- 规范：`design-reviewer`、`design-review`、`tech-review`；真实环境红线保持。
- 前轮：`docs/reviews/review-FEAT-102-DESIGN-R4.md`，SHA-256 `327CA0ED36FCFE923BAAF9D9AB308E5AAD6676AFBB2EA8F37D4BCFE6B14EB314`（本机 `Get-FileHash` 复算一致）；R4 审阅时的架构快照为 git blob `292bfec7adacfaa35d97f137a7ac097799485c82`，SHA-256 `AD417E66F45C45E3B492442ADDAEA3223F3683EBAC011018527F4EA6D21E4429`（本机 `git cat-file` 复算一致）。R3 快照 blob `53d2a1549a600e0ef5b3a5e4452afb760921667a`，SHA-256 `B92C7CA5491DD316A4AC3434C5C7F8A97AE0AE0C244418782C84C188CDE526BE`。
- 输入：当前 `docs/architecture/dsh-adapter-version-decoupling.md`，SHA-256 `23E3B02DBF45E8A00ABD48E89162B6C43D537BEF219B93BF6B7733F7EBCD2B50`；`lib/dsh-native/{spec,source,overlay,lifecycle,bridge,persona}.js`、`lib/index.js`、`adapters/dsh/host-contract.json`、两份预设模板、`skills/software-project-governance/core/version-projections.json`、相关测试与 README。
- 范围：只审 R4 之后的设计增量（DEC-364 原生派生方案）及其落地证据；只写本报告。R5 是 Coordinator 的 V3 fuse 升级结论文档，不是审查报告，本轮按新 engagement 以 R4 为 delta base。
- 边界：未修改产品代码、治理记录、plan-tracker/evidence-log/decision-log、agent-locks；两个暂停 WIP 文件（`skills/software-project-governance/infra/hooks/commit-msg`、`infra/tests/test_hooks.py`，DEC-342）未修改、未 stage、未 renormalize。宿主验收一律使用仓库内隔离 `DSH_HOME`（见 §5.3），未写 `C:\Users\peter\.dsh` 或用户真实 profile。
- **对象绑定**：本报告的被审对象 = **HEAD `98d99c2`（四个被审 commit `e6e2ca5`/`f08e0a2`/`22b6820`/`98d99c2`）＋设计文档 SHA-256 `23E3B02D...`**。审查期间（约 20:42 本地）工作树出现了与 **CODE R0 返工**对应的未提交改动（`README.md`、`adapters/dsh/README.md`、`adapters/dsh/host-contract.json`、`lib/dsh-native/{bridge,overlay,source}.js`、`lib/index.js`、`skills/software-project-governance/infra/dsh_compat.py`）；这些改动**未纳入本报告判定，也不被当作任何 finding 的修复**。设计文档在本轮字节未变（SHA-256 仍为 `23E3B02D...`），本报告所有设计 finding 站在该有效字节上；§16.1/§16.2 的“自动 legacy 写入”行为决策不因实现面返工而改变。
- 方法：先用 git blob 还原 R4 实际审阅的文档快照并复算 hash；再用 `git diff --no-index` 把 R4 快照与当前设计对比（实际增量只有 §16 的 34 行，见 §5.1）；随后只读安装态 SDK 0.2.1-rc.2 源码核对 API 语义，运行六组官方测试，并用 Reviewer 自写 verifier 在全新隔离 profile 上启动真实 dsh 验证核心交付。所有命令见 §5.4。

## 1. 结构化结论

```text
conclusion=NEEDS_CHANGE
unresolved_blockers=2
review_object=HEAD_98d99c2 + design_sha256_23E3B02D
concurrent_uncommitted_CODE_R0_rework=NOT_REVIEWED
carried_blocker=R3-B1_OPEN_NOT_CLOSED (R4)
new_blocker=legacy_automatic_HOME_writer_contradicts_R0_UNSUPPORTED_NO_AUTOWRITER
native_core_runtime=REPRODUCED_IN_ISOLATION (reviewer-run, dsh 0.2.1-rc.2)
full_runtime_matrix=NOT_RUN
native_tests=570_PASS_AT_HEAD (six suites)
real_profile_diagnostic=NOT_RUN
hot_refresh=NOT_IMPLEMENTED_DISCLOSED
cancellation_protocol=NOT_IMPLEMENTED_DISCLOSED
publication_fence=NOT_IMPLEMENTED_DISCLOSED
legacy_static_composition=CURRENT_SHELF_ONLY (0.1.x retired)
support_matrix=STALE_0.2.0-rc.2
design_side_changes=REQUIRED (see §9)
implementation_side_changes=CODE_R1 (see §9)
release_authorized=false
```

R4 之后的 native 派生核心不是“只写了提案”：本轮独立隔离运行确实得到 `governance` 预设、`resolve` 无 broken、治理会话 `composedPreset=governance`、治理 skill 目录含 `software-project-governance` 与 9 个命令 shim、standard 会话无治理 skill 泄漏、`${DSH_HOME}/.agent-presets` 不存在；六组测试在当前 HEAD 合计 570 项通过。**但 R4 的 carried blocker `R3-B1` 没有被真实闭合**，且新增的 legacy 自动渲染路径与 R0 的 `UNSUPPORTED_NO_AUTOWRITER` 裁定直接冲突。因此不能给 `APPROVED_WITH_NOTES`（该终态要求 `unresolved_blockers=0`），结论只能是 `NEEDS_CHANGE`。

## 2. R4 要求逐项判定

R4 原文的 finding 标签保持原样；本节不把“已披露”改写成“已闭合”。

| R4 项（原文） | R4 要求 | R6 事实 | 判定 |
|---|---|---|---|
| `R3-B1`（BLOCKING/P1） | 找到实际公开、可定位到确切 SDK/版本的 generation 取消/撤回协议；在 payload 仍 pending 时记录能独立终结为拒收；不能以“已知边界”或提案文档关闭 | 原生路径没有使用 G 的 permit/guard，确实消除了“own cleanup 等待自己启动任务”的自锁；但 `agentPresets.register(definition)` 仍是同步建 record、`await record.ready` 后才返回 disposer（安装态 registry `lib/index.js:470-493`、`:485`）。本包 cleanup 只标记 disposed、迟到 disposer 立即撤回，**不取消 registry record**；设计 §16.2（L719）自己写明“卸载瞬间已进入 registry 的 pending record 会等到 mount 完成”“不声明 U 协议已实现”，§16.4.3（L735）写明取消协议与 publication fence 未实现。设计 §15.2 记录官方 0.2.1-rc.2 包仍无早期关闭能力；本机安装态 0.2.1-rc.2 源码同形。R4 之后没有新的取消 API、没有同一反例的修复证据、没有用户接受该窗口的记录 | **未闭合**；carried blocker 仍成立 |
| `D1` 精确 generation 提交 token 与真正原子点 | 冻结哪个公开返回值携带 generation fence、谁交给 AgentSetup、何处同步验证；create/resume/fork/subagent 真实调用点；持久化后失败的回滚/释放 | native 路径不创建 Agent setup/commit；U 路线未实现。设计没有把 `D1` 显式标成“已退出”，但它不属于本轮 native 路径的交付合同 | **不适用于 native；U 路线未实现**；不作为独立新 blocker，但设计应显式 disposition |
| `D2` close 与既有 Agent revision 的状态分支 | 区分 ACTIVATING 迟到初始化与 READY 且仍有既有用户的 standing scope；不误 dispose 已提交 Agent | 无 close，无 generation/standing scope 分支；原生路径不提供取消窗口实现 | **不适用/未实现** |
| `D3` 完整终态/兼容表 | 冻结 close-before-start、已 abort、inactive/cross-root、READY 后 close、FAILED、重复 close、tombstone 复用等结果；旧 register 行为不暗改 | 无 close/terminal 表；U 未实现；老 `register` 形状未改 | **不适用/未实现** |
| `R4-BR1` 愤怒用户：own 卸载后物理 scope 等待 | 逻辑 owner 与物理 collection 分离；close 不等待 payload；所有旧 waiter 先得到终态 | 本包 cleanup 不等待 in-flight activation（方向正确），但 pending record 仍等 mount；旧 waiter/roster 仍可能被该 record 拖住（design §16.2 已承认） | **部分缓解，未闭合**；与 `R3-B1` 同一根因 |
| `R4-BR2` 攻击者：commit 检查后 await 存储再 close | 最后 await 后的真正 publication fence、精确 token、回滚 | 无 AgentSetup/commit/publication fence；§16.4.3 明说未实现 | **未实现/未闭合**；native 路径当前不声称具备 |
| `R4-BR3` 维护者：旧 generation drain 晚到删新 id | identity 原子替换、late cleanup 只处理旧 scope、交错测试 | 热刷新未实现；相同 preset id 重复注册同步拒收；无 generation/drain 路径 | **不适用/未实现**；不能据此声称关闭 |
| `R4-BR4` 愤怒用户：READY 旧 Agent 被 close 全量失效 | 区分新 admission 与既有 committed revision；回归已有会话/子 Agent | 无 close 路径；不适用 | **不适用/未实现** |
| R4 §6 的“降低支持标准/接受 flight pending 风险须用户决策” | 明确变更 + 用户决策，不能由 Coordinator 代决 | `DEC-364` 的决策主体写的是“Coordinator（承载用户 2026-10-20 指令与实机验收）”，没有 AskUserQuestion id；`DEC-365` 记录的用户答复只是“先闭环 FEAT-102 审查缺口”；`EVD-2114` 的用户“已重启安装且生效”是安装确认，不是取消窗口风险接受 | **未满足**；并入 `R3-B1` 的 blocking 判定 |
| R4 §5 验证矩阵（旧 waiter、close/signal 交错、publication/storage gap、坏注册、普通 preset 等） | 在真实事件顺序上重跑同一反例；不得 fake registry/sleep/提前 release | 新 acceptance 只覆盖“正常 boot → roster/resolve/compose/skills/无目录”核心切片；首 lookup、取消窗口、热刷新、override/表达式、坏 base、跨 profile 等均未重跑 | **NOT_RUN**；不能称为全链通过 |

## 3. 新增 blocking findings

### P1-1（carried）R3-B1 仍开放：native 路径避免了自等待，但没有提供 registry record 的独立取消/终态

**事实链**（全部来自本机只读安装态 0.2.1-rc.2 与仓库代码）：

1. 安装态 `dsh-agent-preset-registry/lib/index.js:470-493`：`register` 先 `this.definitions.set(...)`（同步 record），再 `record.ready = this.activate(record)`，`await record.ready`，最后 `return unregister`；`unregister` 在 `:485` 仍 `await record.ready`。这就是 R3-B1 的“先登记、后激活、disposer 晚到”形状；设计 §15.2 记录官方 0.2.1-rc.2 包仍无早期关闭能力，本机安装态 0.2.1-rc.2 源码同形（R4 报告 §2 也明确没有重新联网抓取 next 包，故这里不把“R4 已确认”当作事实）。
2. `lib/dsh-native/lifecycle.js:56-83`：本包只保存 `state.disposed`，disposer 到达后立即调用；不会让 `register` 的 pending record 提前终结。`lib/dsh-native/bridge.js:90` 把 `register` 结果交给 lifecycle，`apply()` 随后返回；这正是设计 §16.2（L719）承认的窗口。
3. 设计 §16.2（L719）：“R3-B1 取消语义未消除……它不再阻塞运行时交付，作为已知边界登记，不声明 U 协议已实现。” 这是诚实披露，但不是 R4 要求的“实际新 API 及同一反例修复证据”。
4. 设计 §15.6（L626）明确要求：若降低支持标准/接受 flight pending 风险，必须另列明确变更和用户决策，不能当成原门通过；R4 报告 §6（`docs/reviews/review-FEAT-102-DESIGN-R4.md:92-94`）也声明不替用户移除目标或接受该风险。仓库中没有这样的用户决策记录：`DEC-364` 是 Coordinator 作者，`DEC-365` 的用户选择是“先闭环审查缺口”，`EVD-2114` 是安装生效确认，均不构成对 pending record 窗口的风险接受。

**为什么仍算 blocking**：R3-B1 的原始影响不是“native 路径不能用”，而是“own 卸载完成后，registry record 仍不能独立于 payload 及时终结；新 consumer/roster 仍可能等它”。native 路径把“own 卸载等待”这一半修掉了，但没有修“record 终态”这一半；设计把它降级为 known boundary 并继续宣称运行时切片可用，属于 R4 明确禁止的“用提案/边界文档把未关闭 RECHECK 改成零阻塞”。如果用户要接受该边界，必须另行机录用户决策并把它体现在支持声明中；否则 R3-B1 仍应保持 open。

**最小返工**：要么实现 U/publication fence 并用同一 permit/payload barrier 反例回归；要么由 Coordinator 以明确问题取得用户对“pending record 窗口”的接受，并把 FEAT-102 支持声明降为“native 核心切片 + 已知窗口”，不得表述为“取消问题已解决”。本轮不替用户选择。

### P1-2（new）legacy 自动渲染重新打开 R0 的 `UNSUPPORTED_NO_AUTOWRITER` 安全门，且实现会在无人读目录的宿主上写/删用户预设

**事实链**：

1. 设计 §16.1（L712）：“有 → native；没有 → legacy 目录渲染；有但被禁用 → 明确拒收、不写目录。” `lib/index.js` 的 `apply()` 在 `mode==='legacy'` 时直接调用 `ensurePreset(ctx)`（L677-681）；`ensurePreset` 在 L586 执行 `if (existsSync(userDir)) rmSync(userDir, { recursive: true, force: true })`，随后 rename staging。也就是说：无 registry row 的宿主启动时会自动渲染并**替换/删除** `${DSH_HOME}/.agent-presets/governance/`。
2. 设计 §6（L196）原文：“legacy renderer 仍有旧自动 `rmSync(target)` 的安全债；Design R0 已裁定新交付的自动运行入口明确 UNSUPPORTED，**绝不调用旧 writer**，不再待定……恢复 legacy 自动运行需另作安全设计、隔离验证及独立审查，不得借回归测试执行真实 HOME 删除。” R0 报告（`docs/reviews/review-FEAT-102-DESIGN-R0.md:30`）也明确：“本次新交付的运行入口对无 native 能力的宿主明确 UNSUPPORTED，不自动调用旧 HOME writer……必须从普通 apply、install/repair/update 自动路径隔离。”
3. `adapters/dsh/host-contract.json:809` 的 `native.legacy_policy` 写的是“automatic HOME renderer runs only when the host has no agentPresets service **AND** the row config opts in (`legacyAutoRender: true`); otherwise warn-only and writes nothing”。但全仓检索 `legacyAutoRender` 只有这一处契约文本，`lib/index.js`/`lib/dsh-native/` 没有读取它；`test_dsh_native_bridge.py::test_apply_preserves_the_legacy_host_path` 反而断言无 registry row 时必须写出 legacy 目录（L200-212）。契约、设计 §16.1、实现、测试、README 五处不一致。**（对象绑定：审查期间工作树已出现未提交的 contract/README 措辞返工；按 Coordinator 裁定的 pre-20:42 快照，本 finding 仍按上述字节成立，返工未纳入判定。）**
4. `README.md:76` 还写着“If the host declares no registry row ... the row is warn-only and does not fall back to writing a preset directory”，与同一段下一句“The paragraphs below describe the legacy directory path that remains for hosts without the registry row”以及 `adapters/dsh/README.md:12` 的“legacy；宿主未声明 registry row 时渲染”直接矛盾。**（同上：工作树已有未提交返工；本报告不把它结案为已修。）**
5. 设计 §16.2（L722）说“0.1.x 的静态组合支持明确退役——legacy 模板只对齐当前 shelf”，而 legacy 模板当前只含 `dsh-workflow-ptc`（`agent.cordis.yml.template:228-229`）。0.1.x 目录模型需要的是 `workflow-worker-thread`（`adapters/dsh/fixtures/host-facts-0.1.5-rc.1.json:267-268`）；0.2.x registry 不扫描目录（`docs/research/dsh-0.2-upgrade-decoupling.md:45`：“0.2 的 registry 明确不扫描目录”）。也就是说：**自动旧路径写的组合没有已声明支持的目标宿主**，却仍保留删除/替换用户目录的写面。

**判定**：这不是“文档小瑕疵”，而是新的设计级安全/一致性 blocker。它不依赖 native 路径是否工作，而是在无 registry 的宿主上自动触发了 R0 已经关闭的旧 writer。R0 是 `APPROVED_WITH_NOTES/unresolved_blockers=0` 的设计裁定，R4 没有解除它；§16 未经新的安全设计/用户决策就把它重新打开。

**最小返工**：二选一并写清：
- 默认不自动渲染：`apply()` 在 legacy 分支只 warn（或明确 `UNSUPPORTED_NO_AUTOWRITER`），把写目录留给用户显式 `launch.py --install`；同时更新 §16.1、README、`legacy_policy` 的措辞与测试。
- 若确实要自动渲染：实现契约已有的 `legacyAutoRender` opt-in（默认 false），补隔离验证与用户决策，并明确哪个受支持宿主会读这个目录；仍要证明不会误删用户数据。

## 4. P2/P3 findings

### P2-1 raw/accepted 与 `BASE_BROKEN` 只披露了一半

设计 §4.1（L86-88）仍要求“不能仅读 raw `entry.options.config`；`fiber.config` 是公开已校验值；`registry.resolve(basePresetId)` 无 broken 与 base Fiber 完成启动是两件事，不能互代；无法证明则候选失败，不能删去 `BASE_BROKEN` 拒收要求”。实现 `source.js:78` 用 `entry.options.config` 定位/派生，`bridge.js:79` 把它直接交给 overlay；全仓 `lib/dsh-native/` 没有 `registry.resolve`、`BASE_BROKEN`、`fingerprint` 或 `BaseSnapshot` 的实现（仅 `overlay.js:70` 有 `structuredClone`）。§16.2（L720）诚实披露了 raw vs accepted 的分叉，但没有披露“base broken 未审计”，也没有把 §4.1 标成已替换/降级。SOURCE 推导：base raw 配置陈旧或 broken 时，governance 派生仍可能登记出一个 broken/pending preset，而不是在 register 前明确拒收；`resolve` 最终可报 broken，但 roster/首会话可用性可能先被 pending record 拖住（本轮未构造该运行，故为源码推导而非实测）。建议在设计中显式二选一：恢复 base audit/`BASE_BROKEN`，或把 §4.1 的这项硬门正式降级为 known boundary 并补负例测试。

### P2-2 persona 正文仍有两份副本，且新文件未纳入版本投影

设计 §8 S-B（L228）要求“提取唯一治理正文到 `agent-presets/governance/persona.md.template`，旧 composition 以专用 token 引用它；禁止旧模板和新模块各留一份 bootstrap；同步版本投影到该唯一正文”。实际：
- `agent-presets/governance/agent.cordis.yml.template:48-66` 仍内联完整治理正文；`persona.md.template` 是第二份；
- `lib/index.js:29-31` 明确承认“legacy composition template keeps its own rendered copy ... a test keeps the two in sync”；
- `test_dsh_native_bridge.py:216-251` 做的是 whitespace-normalized 内容比对（能防漂移，但不是单一事实源）；
- `skills/software-project-governance/core/version-projections.json:102-109` 只投影 `agent.cordis.yml.template`，没有 `persona.md.template`。下一次版本 bump 只会更新 legacy 模板的 `v0.98.0`，native persona 仍停旧版本，测试会失败或需要人工双改。
这是设计明确禁止、实现却保留的偏差；测试同步只是补偿，不满足“唯一正文/版本投影”的合同。建议：让 legacy 模板引用同一正文（如 token/include），或把 `persona.md.template` 纳入版本投影并修改设计措辞，不要同时声称“单一事实源”和“测试同步的两份副本”。

### P2-3 设计文档的模块/接口合同与实现不一致

设计 §3.1（L54-56）仍把新模块命名为 `lib/dsh-preset-source.js`、`lib/dsh-preset-overlay.js`、`lib/dsh-preset-lifecycle.js`；实际实现是 `lib/dsh-native/{spec,source,overlay,lifecycle,bridge,persona}.js` 六个模块。设计 §4.1 的 `BaseSnapshot`（含 `resolutionBase`、`config`、`fingerprint`）、§4.3 的 `RuntimeOutcome`（phase/validation/错误码全集）在实现中没有对应结构；§16 只描述了 `source/overlay/lifecycle/bridge` 的部分行为，没有把 §3/§4 标为“已由 §16 取代”或逐项 disposition。设计审查要求“接口契约是否明确、设计是否被忠实实现”，当前文档无法让实现者/审查者从 §3/§4 复现实际模块边界。建议更新 §3.1/§4 或在 §16 明确 supersede 列表与保留项。

### P2-4 §16.3 的测试状态已陈旧（事实性错误）

设计 §16.3（L728）仍写：“`test_dsh_contract` / `test_dsh_compat` 的少量失败与本改动无关（同一失败在 HEAD 干净 worktree 复现，见 §16.4）。” 本机在 HEAD `98d99c2`、隔离环境下实测：
- `test_dsh_contract` **122 passed**（exit 0）
- `test_dsh_compat` **136 passed**（exit 0）
- 六组合计 **570 passed**（native 7 + adapter 77 + boundary 136 + doctor 92 + contract 122 + compat 136）
`e6e2ca5` 的 commit message 在其提交时刻写这两个失败是历史事实；但 `f08e0a2`/`22b6820` 已经改了 compat 面，§16.4 也更新为“真实环境由 FAIL 转 PASS”，§16.3 却未同步。当前设计文档在这一点上陈述了与 HEAD 不符的测试结果，属于事实性错误（P2，非安全 blocker）。

### P2-5 版本锚点与支持矩阵仍停在 0.2.0-rc.2，且没有新的基线批准记录

设计开头（L6）与 §6 表（L188）仍写“当前 DSH 0.2.0-rc.2 / 当前目标 0.2.0-rc.2”；§16.3（L726）却以 **0.2.1-rc.2** 做隔离验收，当前安装态也确实是 0.2.1-rc.2（本机 manifest：DSH/registry/agent-preset/app-boot/skill-filesystem 全 0.2.1-rc.2；Cordis 4.0.5；Loader 1.0.6）。R4 §15.2（L545）明确写过“选择新版须作为完整隔离宿主基线另行批准、审查和验证”；§16 没有记录这个基线切换，`adapters/dsh/host-contract.json:18` 的 `evidence.dsh_cli_version` 仍是 `null`，设计状态行/§12 ADR 仍停在 R3/R4/U 提案。建议：更新 §1/§6 支持矩阵到 0.2.1-rc.2（或明确 0.2.0-rc.2 仍是支持目标、0.2.1 只是证据），在 decision/evidence 中记录基线切换，再声明 runtime 支持。

### P2-6 能力探测的“读取失败”被当成“旧宿主”，仍可能写 legacy 目录

`lib/dsh-native/source.js:44-60` 的 `probeNativeHost` 在 `loader.entries()` 抛错时直接 `return { present:false, enabled:false }`；`bridge.js:139-153` 把 `!present` 映射为 `mode:'legacy'`；`lib/index.js:677-681` 随后 `ensurePreset`。设计 §16.1 说 native 宿主绝不回退写目录，`apply()` 的注释（L643-649）也说“refused native path deliberately does NOT fall back”；但“树读取异常”不是“没有 registry row”。另外 `apply()` 对 `CONTRACT_WITHOUT_NATIVE_BLOCK`（L664-669）和 bridge 抛错（L657-662 → outcome null）也走 `ensurePreset`；在 native 宿主上，这些路径会写/删 legacy 目录。建议把“不可读/未知形态”与“确实无 registry”分开：前者明确 `HOST_TREE_UNREADABLE`/`CONTRACT_WITHOUT_NATIVE_BLOCK` 并 warn-only，不落 legacy；后者才按 §16.1 处理（且仍受 P1-2 的 R0 约束）。**（对象绑定：工作树已有未提交 CODE R0 返工，`source.js`/`bridge.js` 加入 `unreadable` 状态；按 pre-20:42 快照，本 finding 的树读取路径仍成立；`CONTRACT_WITHOUT_NATIVE_BLOCK`/bridge-throw 路径在快照中仍走 legacy，返工未覆盖，故本 finding 不结案。）**

### P3（非 blocking）

| ID | Finding | 证据 |
|---|---|---|
| P3-1 | `overlay.deriveDefinition` 在筛选 `persona`/`skill-filesystem` 行时先按名字计数、后判 disabled；若 base 有一个 disabled 同名行 + 一个 enabled 行，会报 `*_ROW_DUPLICATE`，而设计 §4.2 要求“恰好一个启用的 row” | `lib/dsh-native/overlay.js:77-88,108-119` |
| P3-2 | `lifecycle.startRegistration` 对 `registry.register` resolve 出的非函数 disposer 静默返回（不报 `REGISTRATION_BROKEN`）；`ctx.effect` 非函数时也没有清理路径；设计 §4.3 的 `REGISTRATION_BROKEN`/`INIT_TIMEOUT` 未落地 | `lib/dsh-native/lifecycle.js:56-83`；设计 §4.3 L111 |
| P3-3 | README/状态/ADR 多处与实现冲突：`README.md:76` 说“无 registry → 不写目录”但代码/测试写；`adapters/dsh/README.md:14` 说“单一事实源”但有 legacy 副本；设计 L4/L307/L526 仍写 R3=NEEDS_CHANGE、R4 PENDING、§15 待审，§12 ADR 仍推荐 U 提案而非 native 派生 | 见各文件行号 |
| P3-4 | 原 §5.1 的“首 lookup/admitted”硬门没有被新 acceptance 单独重测；本轮 verifier 是 boot 后等待服务再取 roster，不能替代“boot 边界后的第一条真实 list/resolve”因果证明。设计 §16.1 说不再依赖 §5.1，但没有给出新路径的首 lookup raw 证据 | `verify-result-r6.json` 只证明 boot 后 roster/resolve；§16.3 无首 lookup 时序 |
| P3-5 | `dsh_compat` 的 `protocol=native` 依据是 `own.native.registry_row_name` 包是否安装（`dsh_compat.py:1354`），不是实际 native 注册成功；它是一行交付面说明，不应被读成 runtime 支持。§16.4 已披露“native 派生行本身尚未纳入探针”，但字段命名仍可能误导 | `dsh_compat.py:1264-1354,1947-2128`；设计 §16.4 L733 |

## 5. 独立证据

### 5.1 静态事实

- R4 审阅输入不是“当前整篇 738 行”：R4 记录的架构快照（blob `292bfec7...`，704 行，93,810 bytes）SHA-256 = `AD417E66...`，与 R4 报告声明一致。当前设计（738 行，99,818 bytes）SHA-256 = `23E3B02D...`；`git diff --no-index` R4 快照 vs 当前设计 = **+34 行，全部是 §16**（L706-738）。`e6e2ca5` 的 `+738` 是整文件从 untracked 状态入库的 diffstat，不是 738 行新设计；R4 已审的 §1-§15 文本未变。这个区分对判断 R4 finding 是否仍然适用很重要。
- 安装态版本：`@deepseek-ai/dsh`、`dsh-agent-preset-registry`、`dsh-agent-preset`、`dsh-app-boot`、`dsh-skill-filesystem` 均 `0.2.1-rc.2`；Cordis `4.0.5`；Loader `1.0.6`。
- 关键代码事实：安装态 registry `lib/index.js` 的 `register` 同步建 record、`await record.ready` 后返 disposer（`:470-493`）；`diagnostic` 先 `await record.ready`（`:533-544`）；`list` 对全部 record `Promise.all`（`:570-580`）。`Entry.disabled` 是有效禁用 getter，`EntryTree.entries()` 递归公开树（Loader `index.js:142-159`；`entry.d.ts`）。
- 关键代码事实：`lib/dsh-native` 只有 `overlay.js:70` 的 `structuredClone`；无 `fingerprint`、`BASE_BROKEN`、`registry.resolve`、`RuntimeOutcome`。`legacyAutoRender` 只出现在 `host-contract.json:809`，代码零引用。

### 5.2 测试（本机独立运行，当前 HEAD `98d99c2`）

| 测试 | 结果 | 耗时 | 日志 / SHA-256 |
|---|---|---|---|
| `test_dsh_native_bridge.py` | 7 passed | 0.36s | `native-bridge-test.log` / `7F6A673F...` |
| `test_dsh_adapter.py` | 77 passed | 40.8s | `test-dsh-adapter.log` / `0641D045...` |
| `test_dsh_boundary.py` | 136 passed | 5.2s | `test-dsh-boundary.log` / `0C4EE63E...` |
| `test_dsh_doctor.py`（首次，TEMP 在包内） | 92 ran / 4 errors | 211s | `test-dsh-doctor.log` / `08C0A11D...`；4 个错误均为 `TEMP` 在包内触发 `_guard_out_target` 拒绝，属测试环境选择，不是产品失败 |
| `test_dsh_doctor.py`（重试，TEMP 在包外） | 92 passed | 213s | `test-dsh-doctor-retry.log` / `AD4AAD97...` |
| `test_dsh_contract.py` | 122 passed | 13.3s | `test-dsh-contract.log` / `4F0C2401...` |
| `test_dsh_compat.py` | 136 passed | 160.9s | `test-dsh-compat.log` / `6EF873A6...` |
| **合计** | **570 passed** | — | 与 EVD-2116 的 570 口径一致 |

首次 `test_dsh_doctor` 的 4 个错误必须披露而不是隐藏：`TEMP` 被设到仓库包内的 `.governance/sandboxes/.../tmp`，`dsh_doctor._guard_out_target` 正确拒绝 `host-facts.json` 落在 package 内；把 TEMP 换到包外的 `D:/AI/agent/claude/coding/_feat102-r6-tmp` 后 92/92 通过。这不是产品缺陷，也不能拿重试结果覆盖首次失败事实；两次日志都保留。

### 5.3 隔离真实宿主核心验收（Reviewer 自跑）

- 环境：`DSH_HOME=D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-r6-verify-20261020T2035`；`USERPROFILE`/`HOME`/`TEMP` 同向重定向；用 `.governance/sandboxes/dsh021-baseline` 的 profile 配置克隆（package.json 的 `dependencies` 为 `link:D:/AI/agent/claude/coding/project_management_workflow`，bundles 含 `@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app`、本包；node_modules 中的 `@peterwangze/software-project-governance-plugin` 重建为指向仓库的 junction）；未执行 `dsh plugin add`（该项 NOT_RUN，profile 的 link 依赖沿用已知隔离基线）。
- 第一次启动用默认端口，`EADDRINUSE 127.0.0.1:3080`（当前 Web GUI 占用），exit 1；第二次用 `--port 0 --no-open`，exit 0。第一次是环境冲突，不是产品失败，日志保留。
- Reviewer 自写 verifier 输出（`verify-result-r6.json`，SHA-256 `54F48BD1...`）：
  - roster 含 `governance`，`broken=null`，`name=治理协调器`；
  - `registry.resolve('governance')` 无 broken；
  - `sessionController.create({agentPreset:'governance'})` 后 `composedPreset=governance`；
  - 治理 skill 目录含 `software-project-governance` 与 9 个命令 shim（`governance`、`governance-cleanup`、`governance-gate`、`governance-init`、`governance-review`、`governance-status`、`governance-update`、`governance-verify`、`change-triage`）；
  - standard 会话 `composedPreset=standard`，不含 `software-project-governance`；
  - `${DSH_HOME}/.agent-presets` 不存在（`legacyPresetDirExists=false`）。
- 局限：profile 是基线克隆，standard 会话的 user skills 少于生产者的基线（本轮只有 `diagnose-windows-sandbox-acl`），所以“standard 未被修改”只能证明 composition/无泄漏，不是完整 T04 用户覆盖矩阵；`plugin add`、首 lookup、取消窗口、热刷新、override/表达式、坏 base 等均未跑。

### 5.4 命令审计

完整机器可读审计：`.codex-sandbox/FEAT-102/design-r6/command-audit.json`，SHA-256 `1120FD741E4400C12D236F4C97AE293ED67BB3F789FD8DB5422FEFEE5531DA51`。所有测试/宿主命令的 `DSH_HOME` 均指向 `.governance/sandboxes/` 内并先断言前缀；宿主 run 另把 `USERPROFILE`/`HOME`/`TEMP` 重定向。`R6-TEST-DOCTOR-1` 与 `R6-DSH-VERIFY-1` 的 exit 1 已在上文说明为环境选择/端口冲突，不是产品结论。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 影响路径 / 备注 |
|---|---|---|---|---|---|
| R6-STATIC | git status/log、文件 hash、安装态版本、`git diff --no-index` R4 快照 vs 当前设计 | 12:39:15.2747599Z | 12:39:16.0184322Z | 0 | 只读；`DIFF_EXIT=1` 因文件有差异，非失败；日志 `r6-static-audit.log` / `1721126C...` |
| R6-SNAPSHOT-REPRO | `git cat-file blob 292bfec7...` 重导出 R4 快照 | 12:40:40.8234091Z | 12:40:41.0455752Z | 0 | 输出 `r4-reviewed-doc-snapshot-repro.md`；SHA-256 `AD417E66...` |
| R6-TEST-NATIVE | `test_dsh_native_bridge.py` | 12:23:18.7761271Z | 12:23:19.5202839Z | 0 | 7 passed；`native-bridge-test.log` / `7F6A673F...` |
| R6-TEST-ADAPTER | `test_dsh_adapter.py` | 12:23:22.9311221Z | 12:24:04.2578485Z | 0 | 77 passed；`test-dsh-adapter.log` / `0641D045...`；临时目录在 OS temp |
| R6-TEST-BOUNDARY | `test_dsh_boundary.py` | 12:24:15.1469963Z | 12:24:21.0218970Z | 0 | 136 passed；`test-dsh-boundary.log` / `0C4EE63E...` |
| R6-TEST-DOCTOR-1 | `test_dsh_doctor.py`，TEMP 在包内 | 12:24:24.1414809Z | 12:27:55.9372572Z | 1 | 92 ran / 4 环境错误；`test-dsh-doctor.log` / `08C0A11D...` |
| R6-TEST-DOCTOR-2 | `test_dsh_doctor.py`，TEMP 在包外 | 12:28:09.9767158Z | 12:31:43.4551445Z | 0 | 92 passed；`test-dsh-doctor-retry.log` / `AD4AAD97...` |
| R6-TEST-CONTRACT | `test_dsh_contract.py` | 12:31:49.8466943Z | 12:32:03.5931339Z | 0 | 122 passed；`test-dsh-contract.log` / `4F0C2401...` |
| R6-TEST-COMPAT | `test_dsh_compat.py` | 12:32:06.4434843Z | 12:34:47.7950149Z | 0 | 136 passed；`test-dsh-compat.log` / `6EF873A6...` |
| R6-DSH-VERSION | `dsh --version`（隔离 DSH_HOME） | 12:35:17.5699217Z | 12:35:17.7936490Z | 0 | 输出 `0.2.1-rc.2` |
| R6-DSH-VERIFY-1 | 隔离 dsh web 启动，默认端口 | 12:35:48.7873271Z | 12:35:59.7194860Z | 1 | `EADDRINUSE 127.0.0.1:3080`；`dsh-verify-run.log` / `0A30703A...` |
| R6-DSH-VERIFY-2 | 隔离 dsh web 启动，`--port 0 --no-open` | 12:36:16.0430586Z | 12:36:29.7680245Z | 0 | 核心验收通过；`verify-result-r6.json` / `54F48BD1...`；`dsh-verify-run2.log` / `73A561C0...` |

补充说明：纯只读检查命令（`git log/show`、`Get-ChildItem`、`Get-Content`、`Select-String`、`dsh --help` 等）也执行过；它们未改变仓库/宿主状态，其关键结果已由 `R6-STATIC` 重采。一次探索性命令误用 PowerShell 只读自动变量 `$host`（`$host='C:/...'` 赋值失败，随后读取了错误路径），该命令没有产生任何被本报告采用的 fact，也没有写入；在此如实披露，不把它当作被测事实。

### 5.5 WIP 与真实环境边界

- `git status --porcelain` 仍只有 DEC-342 的两个暂停 WIP 为 `M`（`commit-msg`、`test_hooks.py`），未 stage；本轮未执行 renormalize、未改其字节。其 SHA-256 分别为 `97806C18C2CFB5E0FB68E909F295FCC236E40B9E50F682FF8F177AED90CD46AC`、`60FE5DB5514A378CCA1A325288A31CAC9984FFB555470EC7B799CBFE5669D0DB`。
- 本报告只新增 `docs/reviews/review-FEAT-102-DESIGN-R6.md`、`.codex-sandbox/FEAT-102/design-r6/` 下的审查原始产物，以及宿主 run 所用的隔离目录 `.governance/sandboxes/feat102-r6-20261020T2020`、`feat102-r6-verify-20261020T2035`（仅隔离环境，不是治理记录）；未写 `.governance` 的 plan-tracker/evidence-log/decision-log/agent-locks，未写产品代码、未写真实 `~/.dsh`。安装态 SDK 只读（npm 安装目录），未读 `C:\Users\peter\.dsh`；宿主 run 的 `USERPROFILE`/`HOME`/`DSH_HOME`/`TEMP` 均已重定向到仓库 sandbox。测试首次 adapter/boundary/native 使用 OS temp 的 fixture，随后 doctor/contract/compat 已把 TEMP 指向包外 D: 临时目录 `D:/AI/agent/claude/coding/_feat102-r6-tmp`；没有任何命令写用户 `.dsh` profile。

### 5.6 并发工作树漂移（未纳入本报告判定）

- 证据采集完成后（约 20:42 本地），工作树出现以下**未提交**改动，非本 Reviewer 所写：`README.md`、`adapters/dsh/README.md`、`adapters/dsh/host-contract.json`、`lib/dsh-native/{bridge,overlay,source}.js`、`lib/index.js`、`skills/software-project-governance/infra/dsh_compat.py`。其 diff 注释明确写“CODE R0 F1/F3/F7/F9/F10”，属于 CODE R0 返工面。
- 按 Coordinator 的 pre-20:42 快照裁定，本报告不把这些字节纳入判定，也不把它们当作本报告任何 finding 的修复。设计文档 SHA-256 仍为 `23E3B02D...`，未受这些改动影响。
- 本报告涉及的代码行号/hash 以 HEAD `98d99c2` + 采集时工作树为准；若后续以 dirty worktree 记录 review snapshot，需注意这些行号可能已漂移，且未审返工不能反向定义设计结论。相关实现面交 CODE R1（§9.2）。

## 6. 六维度与蓝军简裁

| 维度 | R6 判断 |
|---|---|
| 方案完整性/必要性 | native 派生确实移除了“整套工具行副本”，宿主新增/改名/禁用工具可自然继承；核心隔离验收通过。但 R3-B1 的取消边界未闭合，legacy 自动写回路径未按 R0 收口，方案的“安全终态”不完整。 |
| 模块/所有权 | `lib/dsh-native` 六模块职责基本单一（spec 读契约、source 读树、overlay 纯派生、lifecycle 登记、bridge 编排、persona 读文件）；无宿主反向依赖。设计 §3.1 的三模块命名与实际六模块不一致；`apply()` 的 legacy 分支让入口重新拥有旧 writer，所有权边界变脏。 |
| 接口契约/API 兼容 | `agentPresets.register`/`loader.entries`/`Entry.disabled` 公开事实成立；但 `BaseSnapshot`/`RuntimeOutcome`/`BASE_BROKEN` 未实现，raw vs accepted 仅部分披露；`legacy_policy` 的 opt-in 未实现。 |
| 安全/非功能 | native 正常路径零 HOME 写、只处置自己的 disposer、失败 warn-only，核心验收成立；legacy 分支仍自动 `rmSync(userDir)`，与 R0 安全裁定冲突；R3-B1 的 pending record 仍可能拖住 roster/首会话；热刷新/取消/publication fence 明确未实现。 |
| 可验证性/维护 | 570 项测试全绿、核心宿主验收可复现；但 §16.3 测试状态陈旧、persona 双副本/版本投影缺口、设计文档的 0.2.0/0.2.1 锚点与模块合同未同步；完整 T01-T20 矩阵远未跑。 |
| 独立 Bar Raiser | 本轮换了 Reviewer、独立还原 R4 快照、独立跑测试与隔离宿主；没有采信 Producer 的 verify-result 作为唯一证据；保留了 `test_dsh_doctor` 首次失败与首次 host 端口冲突。 |

蓝军攻击面（新增部分）：
- **legacy 宿主上的愤怒用户**：无 registry 时 boot 自动 `rmSync` 用户预设目录；若用户在 `${DSH_HOME}/.agent-presets/governance` 放过自定义文件，会被替换/删除。R0 正是为此关闭自动 writer；当前实现重新打开。P1-2。
- **native 宿主的攻击者**：让 loader tree 读取抛错或让 contract 缺 native block，`probeNativeHost`/`apply` 把失败折叠为 legacy，然后在 native 宿主写目录；与“native 绝不回退写目录”声明冲突。P2-6。
- **维护者**：版本 bump 只更新 legacy 模板的 v0.98.0，persona.md.template 不在投影内；测试会红但发布脚本不会更新，容易在紧急 bump 时漏改。P2-2。

## 7. 未覆盖面 / NOT_RUN 声明

以下均未在本次独立复验中执行，不得读成 PASS：

- 真实 profile 的 `check_dsh_preset_compat` 由 FAIL→PASS（设计 §16.4.1 的 19/23、1 行 CLI fallback、4 行 NO_SCHEMA）：**NOT_RUN**。本轮只跑 `test_dsh_compat` 136 项，未读/未写真实 `~/.dsh` profile。
- `dsh plugin --profile web add link:<repo>` 的安装动作：**NOT_RUN**；本轮用已知隔离基线的 profile 克隆启动，验证的是 link 依赖已存在后的 boot。
- `T01-T20` 全矩阵：本轮只复现 `T01` 的 core 子集（boot 后 roster/resolve/compose/skills）和 `T04` 的“standard composition 无泄漏”子集；`T02`（nested/flat/pnpm oracle）、`T03`、`T05`（宿主新增/替换/禁用工具）、`T06`（profile override/!!js）、`T07`（同版本换路径）、`T08`（base 缺失/重复/disabled/broken/空 plugins）、`T09`（多 persona/表达式/非法 schema）、`T10`（启动延迟/首 lookup 时序）、`T11`（首 consumer）、`T12`（热刷新）、`T13`（取消/卸载）、`T14`（duplicate id）、`T16`（0.1.x 旧版）、`T19`（工具 schema/真实模型）、`T20`（全 sandbox 快照）均 **NOT_RUN**。
- 取消窗口、publication fence、热刷新：**未实现/未验证**；设计 §16.2/§16.4.3 已披露。
- 多 profile/desktop/headless/真实用户 UI/真实模型：**NOT_RUN**；本轮只 current-web 隔离。
- `test_dsh_doctor` 首次 4 errors：环境选择导致（TEMP 在 package 内），重试 92/92 通过；不构成产品失败，但首次失败保留披露。
- `R6-DSH-VERIFY-1` 的 `EADDRINUSE 3080`：当前 Web GUI 占用，属环境；第二次 `--port 0` 通过。

## 8. 给 Coordinator 的返工建议（不替用户决策）

1. **先处理 P1-2**：把无 registry 宿主的自动 legacy 渲染改为默认 warn-only / 显式 opt-in（实现 `legacyAutoRender`），或给出“哪个受支持宿主会读该目录、为何不会误删用户数据”的新安全设计 + 隔离验证 + 用户决策；同步 §6/§16.1/README/host-contract/tests。不要在 native 路径修好的同时重新打开 R0 的旧 writer。
2. **R3-B1 二选一**：
   - 实现 U/publication fence 并用同一“permit 后 payload barrier”反例回归；或
   - 由用户明确接受“pending record 窗口”，机录该决策，并把支持声明限定为“native 核心切片 + 已知窗口”，FEAT-102 不标完成、不宣称取消安全。
3. **补设计一致性**：§4.1 的 raw/accepted + `BASE_BROKEN` 要么实现、要么显式降级；`BaseSnapshot`/`RuntimeOutcome` 要么落地、要么在设计中移除/标 deferred；§3.1 模块名更新为六模块；`persona.md.template` 纳入版本投影或改为真正单源；§16.3 测试状态、§1/§6 版本锚点、状态行/§12 ADR 更新到当前事实。
4. **补测试**：base broken/raw 分叉、legacy opt-in/默认不写、首 lookup（boot 边界后第一条真实 list/resolve）、duplicate disabled persona/skill、非函数 disposer、取消/热刷新负例。只有核心 boot 后 roster 不足以关闭 R3-B1 或 T10/T11/T13。
5. 在上述完成前，**不要**把 FEAT-102 标完成、不要发布“已适配”支持声明、不要据 §16.3 的旧测试状态或 §16 的“已验收”做超范围发布。native 核心切片可以作为“隔离证据”保留，但不是全链 PASS。

## 9. 设计面 vs 实现面结论（供 Coordinator 路由）

按 Coordinator 的 pre-20:42 快照裁定，两类返工分开列；**实现面在途返工不改变设计面判定，也不被本报告视为已修复**。

### 9.1 ① 设计面必须改（设计文档 / 契约语义 / 行为决策）

| ID | 设计位置 | 最小修订 | 是否需要用户/DEC 行为裁定 |
|---|---|---|---|
| D-R6-1 | §16.2 的 R3-B1 bullet、§16.4.3、§12 ADR | 明确写“R3-B1 仍未闭合；native 切片不提供取消；支持声明不得写‘取消已解决’”。二选一：(A) 实现 U/publication fence 后更新；(B) 保留 known boundary，但必须由用户/DEC 明确接受 pending record 窗口，并限定支持声明。**不要把 §15 提案当作已实现的关闭** | **是（选 B 接受窗口时）**；选 A 是实现依赖，不是设计豁免 |
| D-R6-2 | §16.1 第 1 条、§6 的 legacy 表/段、`host-contract` 的 `native.legacy_policy`、两份 README 的 legacy 段 | 二选一：(A，推荐) 默认不自动渲染：无 registry 宿主只 warn/`UNSUPPORTED_NO_AUTOWRITER`，写目录只留给用户显式 `launch.py --install`；同步把 §16.1、§6、契约、README、测试统一到该语义。(B) 保留自动渲染：必须明确这是对 R0 裁定的**行为变更**，另写安全设计（ownership/备份/opt-in/误删防护）并取得用户/DEC 同意，再改 §6/契约/README | **是（选 B 时）**；选 A 是恢复 R0 既有裁定，不需要新用户授权 |
| D-R6-3 | §4.1（raw/accepted、`BASE_BROKEN`、`BaseSnapshot`/fingerprint）、§16.2 | 二选一：(A) 保留 §4.1 硬门，要求实现用 `fiber.config` + `registry.resolve(basePresetId)` + `BASE_BROKEN`；(B) 正式把 §4.1 降级为“declaration-based 派生；accepted/broken 审计是 known boundary”，并在 §16.2 增加对应 bullet 与负例测试。不能保持“§4.1 仍要求、§16.2 只提 raw”的半披露状态 | 选 B 若被视为接受安全/可用性边界，需在 DEC 层披露；选 A 是设计保持 |
| D-R6-4 | §3.1 模块表、§4.1/§4.3 接口、§16 的 supersede 说明 | 把 §3.1 的三个模块名更新为实际 `lib/dsh-native/{spec,source,overlay,lifecycle,bridge,persona}.js`；将 `BaseSnapshot`/`fingerprint`/`RuntimeOutcome` 标为“已实现/延期/由 §16 取代”，不能留下与实现不符的接口合同 | 否（文档一致性） |
| D-R6-5 | §8 S-B（唯一正文/版本投影）、`version-projections.json` | 二选一：(A) legacy 模板改为专用 token 引用 `persona.md.template`，真正单源；(B) 保留两份但明确“测试同步的副本”是已接受设计，并把 `persona.md.template` 加入版本投影，确保 bump 时同步。推荐至少做 (B) 的投影；若代码无条件按设计“唯一正文”，则做 (A) | 否（维护性）；若选 B 需修改设计措辞 |
| D-R6-6 | §16.3 测试状态、§1/§6 版本锚点、状态行、§12 ADR | §16.3 改为当前 HEAD 的 570 项全绿（contract 122/compat 136）；§1/§6 支持矩阵改为 0.2.1-rc.2（或明确 0.2.0 是支持目标、0.2.1 是证据）；§12 ADR 从 U 提案改为 native 派生 + 未关闭边界；状态行从 R3/R4 更新到 R6 | 0.2.1 基线切换建议以 DEC/证据记录；文档更新本身不需要 |
| D-R6-7 | §16.1 的 fallback 语义 | 把“absent（无 registry）”“disabled（声明但禁用）”“unreadable（树不可读）”“ambiguous（base 缺失/重复/不可合并）”四态写清；明确后三者 warn-only、不落 legacy；契约 `legacy_policy` 与 README 同步。实现面已有在途返工覆盖 `unreadable`，但设计文本必须独立写清 | 否（行为语义澄清；若改变 legacy 自动渲染则并入 D-R6-2） |

### 9.2 ② 实现面（交 CODE 链 R1 闭环；本报告不结案）

| ID | 实现位置 | 在途状态 / 要求 |
|---|---|---|
| I-R6-1 | `lib/dsh-native/source.js`、`bridge.js` 的 tree-unreadable 状态 | 工作区已有未提交 CODE R0 返工（`unreadable` 状态）；未审查，不得当 R6 的修复。CODE R1 应按 D-R6-7 最终语义重审并补测试 |
| I-R6-2 | `lib/index.js` 的 `CONTRACT_WITHOUT_NATIVE_BLOCK` / bridge-throw → `ensurePreset` 路径 | 快照中仍存在；需按 D-R6-2/D-R6-7 决定：默认不落 legacy，或明确该 fallback 的受支持语义 |
| I-R6-3 | `lib/dsh-native/overlay.js` 的路径 identity | 工作区已有未提交 CODE R0 返工（平台感知大小写/分隔符）；未审查，CODE R1 复核 |
| I-R6-4 | `dsh_compat.py` 的 protocol/fallback/anchor/scan | 工作区已有未提交 CODE R0 返工（F3/F7/F9 等）；未审查，CODE R1 复核；设计 §16.4 的“native 派生行尚未纳入探针”仍成立 |
| I-R6-5 | `lib/dsh-native/overlay.js` 的 disabled 同名行、`lifecycle.js` 的非函数 disposer/`ctx.effect` 缺失 | 代码级 P3；CODE R1 修复或明确不支持 |
| I-R6-6 | 测试面 | 补 base broken/raw 分叉、legacy 默认不写/opt-in、首 lookup（boot 边界后第一条真实 list/resolve）、duplicate disabled persona/skill、非函数 disposer、取消/热刷新负例；跑六组测试 + 隔离宿主核心验收 |
| I-R6-7 | 设计面 D-R6-1～D-R6-7 落地后的回归 | 设计修订经 R7 复审后，CODE R1 再按新合同回归；不要用未审返工反推设计通过 |

**路由建议**：先做 D-R6-1/D-R6-2 的行为裁定（需要用户或 DEC），再做 D-R6-3～D-R6-7 的设计文本修订；D-R6 复审（R7）通过后，CODE R1 再把实现面返工纳入审查。R6 的 `NEEDS_CHANGE/2` 不因 §9.2 的在途实现返工而降级。

## 附录：原始产物路径 / SHA-256

| 文件 | SHA-256 |
|---|---|
| `.codex-sandbox/FEAT-102/design-r6/r4-reviewed-doc-snapshot.md`（= R4 输入） | `AD417E66F45C45E3B492442ADDAEA3223F3683EBAC011018527F4EA6D21E4429` |
| `.codex-sandbox/FEAT-102/design-r6/r3-reviewed-doc-snapshot.md` | `B92C7CA5491DD316A4AC3434C5C7F8A97AE0AE0C244418782C84C188CDE526BE` |
| `.codex-sandbox/FEAT-102/design-r6/r6-static-audit.log` | `1721126C02417444533A08CCC157D5807142698F1273C62CC3C04F939FC5244F` |
| `.codex-sandbox/FEAT-102/design-r6/command-audit.json` | `1120FD741E4400C12D236F4C97AE293ED67BB3F789FD8DB5422FEFEE5531DA51` |
| `.codex-sandbox/FEAT-102/design-r6/native-bridge-test.log` | `7F6A673F1B8B401D06047AC4477958CB0DF598652C46DD2234F651CC0EB0185B` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-adapter.log` | `0641D0458F1E5484F112F26E57199B5453C18F1712770E0384949CB7870A877D` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-boundary.log` | `0C4EE63EC2E020C98E76A23A3A03564D0C18D432145774634BE2524860B09991` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-doctor.log`（首次 4 errors） | `08C0A11DACDD07DE39D81E7C9DE4E6C30A7B2F6B865400AC13074A0C605C7101` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-doctor-retry.log` | `AD4AAD972044B8D72B035858BD6015CCA6538F5FE43892C0A16425DC87841242` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-contract.log` | `4F0C24016EC337E8A50DF765B1F221214D285637CFC9B484B47CA3417CE34EEE` |
| `.codex-sandbox/FEAT-102/design-r6/test-dsh-compat.log` | `6EF873A625076C8FA4D01ACFE11F322A9EBB41A29AB3B05965C980CA39622CD1` |
| `.codex-sandbox/FEAT-102/design-r6/verify-result-r6.json` | `54F48BD1E8AD5334CE5B7ACFF9D9F1B8B7936CEE9B67B774CFC4D1ECB4E24DDC` |
| `.codex-sandbox/FEAT-102/design-r6/dsh-verify-run.log`（第一次端口冲突） | `0A30703A9286D5CA42D827FF4EA81E0AE68C7266DC22970CB3883877C619372C` |
| `.codex-sandbox/FEAT-102/design-r6/dsh-verify-run2.log`（核心验收） | `73A561C0671CD804E836C12A8B4DDCAD9624654641C7E3C6D813C48C7D68EE75` |

**结论重申**：native 核心路径可运行且已独立复现，但 R4 的 `R3-B1` 未闭合，legacy 自动写回重新打开 R0 安全门；因此 `NEEDS_CHANGE` / `unresolved_blockers=2`。本报告不授权发布、重装、风险接受或产品完成声明。
