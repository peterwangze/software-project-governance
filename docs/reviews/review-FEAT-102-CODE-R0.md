# REVIEW-FEAT-102-CODE-R0 — dsh 预设原生派生 + 兼容探针双平面独立代码审查

- 日期：2026-10-20（Asia/Shanghai；本报告所有时刻均为 **UTC 2026-10-20**）
- **结论：NEEDS_CHANGE**
- **unresolved_blockers=2**
- P0=0，P1=2，P2=4，P3=4
- 审查范围：`dcf5009..98d99c2` 的 4 个产品 commit（`e6e2ca5`、`f08e0a2`、`22b6820`、`98d99c2`）
- 审查对象：本地 HEAD `98d99c2889e292d6665e7a9f1f53309f0d008b38`（本地工作树字节；远端 CI 不能证明工作区字节）
- Reviewer 身份：独立 Code Reviewer；未参与这 4 个 commit 的写作。本报告每条结论均来自本轮实际读码、测试与命令输出，不采信实现者叙述。
- 写入边界：仅写本报告、Reviewer scratch `.codex-sandbox/FEAT-102/code-r0/`，以及为宿主复跑在 `.governance/sandboxes/` 下新建的 2 个隔离 `DSH_HOME`。未修改/stage/commit/push 任何产品代码、测试、治理记录、前轮报告；暂停 WIP 两文件（`skills/software-project-governance/infra/hooks/commit-msg`、`skills/software-project-governance/infra/tests/test_hooks.py`）字节未动。

> 本结论与 P1/P2/P3 分级只判定这 4 个 commit 的产品代码与测试。EVD-2113（真实 HOME 事故披露）与 EVD-2114（真人重启确认）不在代码审查面，未复验，标 **NOT_RUN**。

## 1. 对象绑定

### 1.1 commits

| commit | 摘要 | 文件 | 行数 |
| --- | --- | ---: | --- |
| `e6e2ca5` | derive the dsh preset from the host declaration | 18 | +1909/−57 |
| `f08e0a2` | resolve compat rows through the host's second plane | 4 | +109/−16 |
| `22b6820` | report which delivery face the compat probe validates | 2 | +33/−1 |
| `98d99c2` | print the delivery protocol in both compat renderers | 1 | +12 |

### 1.2 被审字节 SHA256

| 文件 | SHA256 |
| --- | --- |
| `lib/dsh-native/bridge.js` | `1E1C9C8BF1D558AE27F9BD3EC45C2EE308B900FBDFF6CFC470C9A58D8B1D1D39` |
| `lib/dsh-native/source.js` | `8178F27B5557B10D20D6BC237A13B9CFAE31172EECAF37404A0A093F9503C6C4` |
| `lib/dsh-native/overlay.js` | `9E8B112608E146AA8A942F971CE957AB29785620ACBEA3A29EB1744F132E5C5B` |
| `lib/dsh-native/lifecycle.js` | `CC1A22106C62E1E48060C651B32565E3437E820168AE5033DEBD83F2D2C54C26` |
| `lib/dsh-native/spec.js` | `68EC552FB64D225A9DBFDA59B62EF86763E828761CEE97F23ACD648629A33E80` |
| `lib/dsh-native/persona.js` | `5F45CAC3958C9E7762492EF3610FC989E015B979C82F2D2449D6CA884CB2336C` |
| `lib/index.js` | `D791C0C3DA53A99CC0F0F6C11BE8D05AE7DDFB68B5692345BB89849B94285A74` |
| `skills/software-project-governance/infra/dsh_compat.py` | `54DC4B5BF4FF86F31D3D9E0E6D508D2DBA8FC034613DACC3754535B3AC394829` |
| `adapters/dsh/host-contract.json` | `8511AA9499CAD5B982C9F2AE5566A4A3F84C04ECBF612441F378FE3A39E84D23` |
| `skills/software-project-governance/infra/tests/test_dsh_native_bridge.py` | `CA73ED11CD754DFEE0725CB4239F58E2519977F9651290C59431B92530F4A1A3` |

`git diff --check dcf5009..98d99c2` → **exit 2**：仅 `docs/architecture/dsh-adapter-version-decoupling.md:298-307` 的 Markdown 硬换行尾随空格（非产品代码），产品 JS/PY 无 whitespace 错误。

## 2. 结论先行

原生派生路径在本轮隔离真机上**成立**：EVD-2112 的核心观测全部复现（§3.1），宿主 0.2.1-rc.2 的公开 Entry/registry 语义与实现假设一致（§4.1）。但代码审查发现 **2 个 P1**：

1. **能力探测异常被误判为“旧宿主”并静默写 `$DSH_HOME`**：`probeNativeHost` 捕获 `loader.entries()` 异常后返回“无 registry”，`apply()` 随即走 legacy 渲染并实际写入 preset 目录（Reviewer 探针 B 实测 `presetWritten: true`，无 warn）。这与该文件自己声明的“读不到组合树就拒收、不猜旧宿主、不写退役目录”直接矛盾，也破坏“native 宿主不写 `$DSH_HOME`”的核心安全承诺。
2. **兼容探针/协议三个 commit（`f08e0a2`/`22b6820`/`98d99c2`）的新逻辑没有任何测试**：`dsh_compat.py` 四个 commit 合计 +127/−10；`test_dsh_compat.py` 前/后均为 136 项（`test_dsh_contract.py` 122 项也不变），全测试目录对 `fallbackAnchor/fallback_anchor/rows_resolved_via_cli_fallback/fallback_rows/registry_package/_protocol_line` **零命中**；commit message 引用的测试数不能覆盖新代码。`lifecycle.js` 的 disposal/rejection 分支同样无永久测试（本轮探针 E1-E3 证明行为正确，但没有回归防护）。

因此不能给 APPROVED/APPROVED_WITH_NOTES；P1 修复后可复审。

## 3. 证据复现（EVD-2112 / EVD-2115 / EVD-2116）

### 3.1 EVD-2112 — 复现（PASS）

环境：新建隔离 `DSH_HOME=.governance/sandboxes/feat102-code-r0-20261020T123102Z`（绝对路径前缀断言通过），profile `web` 由 `dsh021-baseline` 复制骨架 + `@peterwangze/...` junction 指向本仓库；dsh 0.2.1-rc.2；真实 `link:` bundle 语义。
命令形态：`dsh --profile web --patch <.codex-sandbox/.../verify-rerun.patch.yml> --port 0 --no-open`（verify row 写 scratch 结果后自行 exit），exit 0，UTC 12:31:22.438Z→12:31:35.945Z。

复跑结果（`.codex-sandbox/FEAT-102/code-r0/verify-rerun.json`，SHA256 `6A35C680…FF7182`）：

| 观测 | EVD-2112 声明 | 本轮复跑 |
| --- | --- | --- |
| roster 含 governance 且 `broken=null` | 是 | 是（roster 5 项：standard/ptc/minimal/cordis/governance） |
| `resolve('governance')` 无 broken | 是 | 是（`resolved.broken=null`） |
| 会话 composedPreset=governance | 是 | 是 |
| 治理 skill 可见 | 是 | 是（`software-project-governance` 在列；43 个 skill，含 9 个治理命令 shim） |
| standard 不含治理 skill（无泄漏） | 是 | 是（`leaked=false`；standard 8 个 skill） |
| standard 未被修改 | 是 | 是（`standardComposed=standard`、`broken=null`） |
| `${DSH_HOME}/.agent-presets` 不存在 | 是 | 是（新建 sandbox 只有 profiles/sessions/storages/.anonymous-user-id/.credentials.yaml） |

结论：**EVD-2112 可复现**（Windows-only、单宿主，与 EVD 范围一致）。

### 3.2 EVD-2115 / EVD-2116 — 部分复现；`fallback=1` 标 NOT_RUN（在原引用隔离环境）

| 声明 | 本轮结果 | 判定 |
| --- | --- | --- |
| `check_dsh_preset_compat` = PASS | `PASS`（12:24:25.433Z→12:24:44.110Z，exit 0） | 复现 |
| `rows_checked=19`、`rows_enabled=23` | 19/23 | 复现 |
| `NO_SCHEMA=4` 披露 | 4（plan-mode / command-compact / tool-subagent-control / tool-subagent-list-agents） | 复现 |
| `protocol=native` | `native`，details 含 `@deepseek-ai/dsh-agent-preset-registry@0.2.1-rc.2 installed` | 复现 |
| `CLI fallback=1` | 在 EVD-2112 所述隔离 `DSH_HOME=.governance/sandboxes/dsh021-baseline` 下 **0**；选中的是 CLI anchor 平面，`fallback_anchor=null` | **NOT_RUN（不可从引用环境复现）** |
| `CLI fallback=1`（合成剖面） | 构造「profile 平面含全部宿主行包 + CLI manifest，仅缺 `dsh-workflow-ptc`」后：PASS 19/23、`rows_resolved_via_cli_fallback=1`、anchor 披露 = CLI `package.json`（12:32:44.973Z→12:33:14.375Z，exit 0） | 复现（合成平面，非真实 profile） |

**诚实边界**：EVD-2115/2116 的 “1 row via CLI fallback” 只能由“profile 平面带 CLI manifest、缺 workflow-ptc”的平面产生。EVD-2112 引用的 `dsh021-baseline` profile 里没有任何 `@deepseek-ai` 包，探针直接选 CLI anchor，因此不进入 fallback。要复现 `fallback=1` 需读取真实 `~/.dsh` profile（本审查禁止）或使用合成平面。没有把合成结果冒称真实环境复现；EVD 文本应点名产生 `fallback=1` 的具体环境/夹具。

### 3.3 渲染面（`98d99c2`）— 复现

- 独立 CLI：`verify_workflow.py check-dsh-preset-compat`（12:33:23.907Z→12:33:53.415Z，exit 0）打印
  `delivery protocol: native declarations — the preset is derived at boot; the composition template is validated for legacy hosts only`，结果 `PASSED — verified 19 of 23 … NO_SCHEMA=4`。
- Check 28v section：`dsh_compat.emit_check_section()`（12:33:56.117Z→12:34:30.613Z，exit 0）打印 `│ delivery protocol: …`，`[PASS]`，返回 0。
- 两个渲染器与 JSON `protocol` 字段一致（native 分支）；unknown 分支不一致见 F7。

## 4. 正确性/安全复验（含实现假设的宿主源码核对）

### 4.1 原生派生路径：假设成立

读取本机安装态 dsh 0.2.1-rc.2（`C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh`，**只读**）：

- `cordis-plugin-loader/lib/index.js:142` `*entries()`、`:336 get disabled()`、`:349 disabledOf(...)`：`entry.options.name`、`entry.disabled`（含 owning parent 与 `!!js` 求值）确实是公开可读事实，`source.js` 的探测假设成立。
- `dsh-agent-preset-registry/lib/index.js:451` `super(ctx, "agentPresets")`、`:470 async register(definition)`：服务名 `agentPresets` 正确；`register` 在首个 `await` 前同步写入 `definitions` map，随后 `await record.ready` 返回 disposer——`lifecycle.js` 的“同步可见 + disposer 后到”语义与宿主一致。
- `dsh-web-app/presets/standard.patch.yml:4-8`（`preset-standard` / `@deepseek-ai/dsh-agent-preset` / `config.id: standard`）与 `dsh-web-app/cordis.patch.yml:587`（registry row）说明 `locateBase`/`probeNativeHost` 的定位键正确；`dsh-base/cordis.patch.yml:400-403` 的 `workflow-ptc` 改名与模板对齐。
- `overlay.js` 只有两个内容差量：persona prefix 追加、`skill-filesystem.customSkillDirs` 追加；`structuredClone` 保留 group/isolate/`!!js`（`{__jsExpr}`）/顺序/disabled；派生后 base 输入未被修改（测试 `test_derived_definition_is_base_plus_two_deltas` + §5 探针）。
- 生命周期：探针 E1（激活后 dispose → disposer 恰好 1 次）、E2（卸载飞行中，late disposer 到达后立即调用 1 次）、E3（同步 duplicate 拒收 → `REGISTER_REFUSED`）全部通过；`lifecycle.js` 行为正确，但无永久测试（F8）。

### 4.2 安全/回归

- **native 宿主不写 `$DSH_HOME`**：探针 A（显式临时 `DSH_HOME`）`registered=1, presetWritten=false`；EVD-2112 复跑 `.agent-presets` 不存在。成立。
- **fail-closed**：loader 服务缺失且 `inject` 可用 → `HOST_TREE_UNAVAILABLE`，不写（探针 C）；契约无 `own.native` → `CONTRACT_WITHOUT_NATIVE_BLOCK`（探针 D，index 走既有 legacy 分支，属代码注释声明的行为）。但 `entries()` 抛错路径不是 fail-closed（F1）。
- **fallback 仍校验落在该 context**：`resolveWithin()`（`dsh_compat.py:642-656`）与主平面共用，fallback 仍要求 `realpath(candidate)` 落在 `contextRootsOf(fallbackAnchor)` 的 node_modules 链接内；合成平面跑通（1 行回退）。主平面的“越界拒绝”已有测试（`test_dsh_compat.py:445-452`，NODE_PATH 反例）；fallback 平面本身无负例测试（含在 F2）。
- **无宿主/坏契约 → NOT_RUN/FAIL 而非假 PASS**：既有分支未改；本轮未见新的假 PASS。`protocol=unknown` 时 details 文案错写为 legacy（F7）。

## 5. Findings

### P1（阻断，必须在下一轮关闭）

**F1 — 组合树不可读时静默写 `$DSH_HOME`（fail-open）**

- 位置：`lib/dsh-native/source.js:50-58`（`try { for (const entry of loader.entries()) … } catch { return { present:false, enabled:false } }`）；`lib/dsh-native/bridge.js:129-146`（`loader` 存在即进入 `probeNativeHost`，异常结果被当作 `mode:'legacy'`）；`lib/index.js:677-681`（legacy 分支直接 `ensurePreset(ctx)`）。
- 证据（Reviewer 探针 B，`bridge-probes.log`，SHA256 `9C5BF7B0…F151`）：
  ```json
  "throwingTree": { "presetWritten": true, "warnings": [] }
  ```
  即 `ctx.get('loader').entries()` 抛错后，`apply()` 实际把 `${DSH_HOME}/.agent-presets/governance/agent.cordis.yml` 写了出来；没有 `warn`，只有一条 info（内容还是“host declares no agent-preset registry”，把真实原因说错）。
- 与声明矛盾：`lib/index.js:643-649` 写明“refused native path 不回退 legacy”；`bridge.js:131-132` 写明“refusing beats guessing 'old host' and writing the retired directory”；`lib/index.js:35` 写明不可派生时“left completely untouched”。`probeNativeHost` 把“读不到”与“没有”合并，恰好突破了这条边界。另：`loader` 不存在且 `ctx.inject` 非函数时，`bridge.js:180-186` 的 `HOST_NO_SERVICE_INJECTION` 在 `probeNativeHost` 之后才判断，同一 fail-open 分支（同一修复覆盖）。
- 建议：`probeNativeHost` 返回三态（absent / disabled / unreadable）或抛出；`applyNative` 对 unreadable 返回 `mode:'refused', code:'HOST_TREE_UNREADABLE'`，不进入 legacy；补一条“entries() 抛错 ⇒ 不写目录且有 warn”的测试。

**F2 — 兼容探针/协议三 commit 的新逻辑零测试覆盖**

- 位置：`skills/software-project-governance/infra/dsh_compat.py:120-128`（`_protocol_line`）、`:615-676`（`contextRootsOf`/`resolveWithin`/`resolveBare` fallback）、`:963-972`（walk fallback 计数）、`:1345-1354`（fallback_anchor/registry/protocol）、`:1409`（`fallbackAnchor` 注入）、`:1743`/`:1768`（`fallback_rows` 聚合）、`:2113-2129`（details）、`:2179`/`:2242`（两个渲染器）。
- 证据：
  - 测试数量不变：`test_dsh_compat.py` `now=136 / before=136`，`test_dsh_contract.py` `122/122`，`test_dsh_adapter.py` `77/77`，`test_dsh_boundary.py` `136/136`，`test_dsh_doctor.py` `92/92`（`git show dcf5009:…` 对比）。
  - 全测试目录 grep `fallback_anchor|fallbackAnchor|rows_resolved_via_cli_fallback|fallback_rows|registry_package|_protocol_line|delivery protocol` → **NO HITS**；`startRegistration|dsh-native/lifecycle` → **NO HITS**。
  - commit message（`f08e0a2`、`98d99c2`）以 `test_dsh_compat 136` 等**未变化的旧套件**作为 “Tests:” 依据，不能证明新分支被执行。
- 影响：三个 commit 改变了真实环境 PASS/FAIL 的来源（第二平面解析、报告新字段、两处渲染），却没有任何回归网；D4/P4（测试看护）不满足。
- 建议：补第二平面单元/集成测试（含 fallback 计数、越界拒绝、anchor 缺失、profile 平面无 CLI manifest 三种环境）、`_protocol_line` 三分支、两个渲染器输出断言；为 `lifecycle.js` 补 dispose/late-disposer/rejection 测试（见 F8）。

### P2（强烈建议本轮修正，不单独阻断合并）

**F3 — fallback anchor 只从“选中的 profile 平面”推导，可能产生假 FAIL 与错误的 protocol**

- 位置：`dsh_compat.py:1336-1354`。`fallback_anchor` 仅在 `cli = _package_version(chosen, "@deepseek-ai/dsh")`（或 profile 平面循环）找到 CLI 包时设置；`which('dsh')` 的 CLI anchor 只在“没有任何 profile 平面被选中”时才使用。
- 证据（合成平面，`compat-fallback-no-cli-manifest.json`，SHA256 `A2C16CCB…8228`，12:36:53.731Z→12:37:21.079Z，exit 0）：profile 平面含 22 个宿主行包（所以被选中、oracle 可解析），但没有 `@deepseek-ai/dsh/package.json`：
  - `verdict=FAIL`、`rows_checked=18/23`、`issues=['… row "workflow-ptc" (@deepseek-ai/dsh-workflow-ptc): cannot resolve …']`；
  - `fallback_anchor=null`、`rows_resolved_via_cli_fallback=0`、`protocol=legacy`；
  - 而同一台机器的 dsh CLI 0.2.1-rc.2 就在 PATH 上且带 registry——报告却写 “legacy user-root directory”。补上 CLI manifest junction 后同一合成平面即 FAIL→PASS、fallback=1、protocol=native（`compat-fallback-synthetic.json`，`9201E04B…439A`）。
- 影响：这正是本 feature 要消除的“可挂载行被判 MODULE_UNRESOLVED 假 FAIL”，在“profile mirror 有 bundle 依赖但未镜像 CLI 包”的常见 pnpm 形态下会复发；protocol 也把宿主说成 legacy。
- 建议：profile 平面被选中但缺 CLI 包时，仍从 `which('dsh')`/安装 anchor 推导 fallback anchor（并保留“必须落在该 context”校验）；协议检测改为按组合声明（与服务端 native 决策同源）或至少同时披露“selected plane 无 registry 包，但 PATH CLI 有”。

**F4 — host-contract 的 `legacy_policy` 与 README 和代码不符（含 0.1.x 无明确拒收）**

- 位置：`adapters/dsh/host-contract.json:809` 声明 “the automatic HOME renderer runs only when the host has no agentPresets service AND the row config opts in (`legacyAutoRender: true`); otherwise the row is warn-only and writes nothing”。
- 代码事实：全仓库 grep `legacyAutoRender` **只出现在该契约字符串**（0 处代码/测试读取）；`lib/index.js:677-681` 对 `mode:'legacy'` 无条件 `ensurePreset(ctx)`，没有 config opt-in，也没有 agentPresets 服务检查。`README.md:76` 更写成 “If the host declares no registry row, … does not fall back to writing a preset directory”，与代码和 `adapters/dsh/README.md`（legacy 渲染目录）同时矛盾；`test_dsh_native_bridge.py:200-212` 正好断言 legacy 会写目录。
- 0.1.x：`docs/architecture/dsh-adapter-version-decoupling.md` §16.2/§16.4 声明 “0.1.x 的静态组合支持明确退役 / legacy 自动运行明确 UNSUPPORTED”，但代码没有宿主代际检测/拒收；`agent.cordis.yml.template:221-229` 已改为 `dsh-workflow-ptc`（0.2 shelf）。因此 0.1.x 宿主既不在测试中支持，也没有被“明确拒收”，只会拿到一个引用不存在模块的目录。T16 的 “UNSUPPORTED” 验收未实现、NOT_RUN。
- 建议：二选一并写清事实——(a) 保留 legacy 自动渲染，则删除 `legacyAutoRender` 声明并修正 README/设计；或 (b) 实现 opt-in/代际检测，在非 0.2 shelf 上拒收。另修正 `lib/index.js:85-88` 对 native 失败给出 `launch.py --install` 的错误补救（native 宿主不读该目录）。

**F5 — `test_apply_writes_nothing_on_a_native_host` 没有断言它命名的属性，且可写真实 HOME**

- 位置：`test_dsh_native_bridge.py:193-198`。断言只有 `registered==1` 与 `(_REPO_ROOT/'.agent-presets').exists() == False`；没有设置临时 `DSH_HOME`，也没有检查 `$DSH_HOME`。
- 事实：`_APPLY_PROBE` 继承 pytest 环境；若 native 路径回归，legacy 渲染会写 `~/.dsh/.agent-presets`（未设 `DSH_HOME` 时）或外部 `DSH_HOME`，而仓库 CWD 断言仍可通过——测试会“绿着写真实 HOME”。Reviewer 探针 A 用显式临时 `DSH_HOME` 实测当前产品行为正确（`presetWritten:false`），但没有永久防护。
- 建议：`subprocess.run(env={**os.environ, 'DSH_HOME': td})`，断言 `Path(td)/'.agent-presets'` 不存在且 `registered==1`；同时保留仓库 CWD 断言。

**F6 — EVD-2115/2116 的 `fallback=1` 在引用的隔离环境不可复现，证据措辞需修正**

- 见 §3.2。不是代码缺陷，但“可复现性”验收要求证据点名可重跑的环境/夹具。`fallback=1` 只在合成剖面复现；在 EVD-2112 引用的 `dsh021-baseline` 下是 0。建议 EVD 文本补环境或补一条可脚本化 fixture；不要把“真实 profile 平面”（禁止本审查读取）留作唯一来源。

### P3（讨论/低风险）

**F7 — `protocol` unknown 时 JSON details 与文本渲染器自相矛盾**

- `dsh_compat.py:2113` 取 `protocol = install_probe.get("protocol") or "unknown"`；`:2120-2124` 只分 `native` / else，else 一律打印 “legacy user-root directory”。而 `_protocol_line`（`:120-128`）有独立的 unknown 分支。经 `install=` 注入（函数公开测试缝）或未来调用方传入无 `protocol` 的 install 字典时，JSON details 说 legacy、文本说 unknown。建议 else 只处理 `legacy`，`unknown` 单独一句。

**F8 — `lifecycle.js` 的 disposal/late-disposer/rejection 分支无永久测试**

- `lifecycle.js:56-85`。测试目录对 `startRegistration`/`dsh-native/lifecycle` 零命中。本轮探针 E1/E2/E3 全部通过（见 §4.1），行为正确；缺的是回归网。建议并入 F2 的补测。

**F9 — `_SKIP_DIRS` 新增通用名 “sandboxes”**

- `dsh_compat.py:520-525`。为跳过任务沙箱是合理的，但“sandboxes”是通用目录名，会静默隐藏任何同名产品目录下的组合。建议改为显式路径/仅跳过 `.codex-sandbox` 与 `.governance/sandboxes`（或保留但披露）。

**F10 — `overlay.js` 的 `samePath` 在所有平台小写化**

- `overlay.js:27-30`。Windows 安全，但在大小写敏感文件系统上把 `/A/skills` 与 `/a/skills` 视为同一目录，可能少追加一个真实存在的 skill 根。影响只限 `customSkillDirs` 去重；建议按平台处理或注明取舍。

## 6. 五维度

| 维度 | 结论 |
| --- | --- |
| 正确性 | 原生派生的两个差量、继承保真、base 不变、宿主 API 假设均由安装态源码 + 隔离真机复跑支持；但出现 F1（异常路径 fail-open）与 F3（第二平面 fallback 触发条件不足，可致假 FAIL）。 |
| 安全性 | native 路径零 `$DSH_HOME` 写入（探针 A + EVD-2112 复跑）；不写真实 HOME；无硬编码密钥/宿主路径（产品内）；fallback 共用 `resolveWithin` 的 context 包含校验。F1 是安全承诺的例外。 |
| 可维护性 | 模块小（spec 77 / persona 83 / lifecycle 86 / source 108 / overlay 150 / bridge 201 行），纯函数 + 结构化 code；契约单源；但 F4 的契约/README 与代码不一致会侵蚀“单源”价值。 |
| 性能 | 启动一次 `loader.entries()` 扫描 + `structuredClone`；无每轮扫描；`lib/index.js` 契约读取仍是 lazy memoized（`:272-286`）；probe 运行开销不变（~18-28s 含 node 启动）。 |
| 测试覆盖 | 570 passed / 119 subtests / 0 failed / 0 skipped（407.80s，exit 0）；新增 native 测试 7/7 通过。缺口：F2（`dsh_compat.py` +127/−10 零测试）、F5（假断言）、F8（lifecycle）。 |

设计一致性：`docs/architecture/dsh-adapter-version-decoupling.md` §16.1 的机制与代码一致；§16.4 “native 派生行尚未纳入探针、launch.py 仍 legacy”与本轮观察一致（探针仍只校验 legacy 模板，native 宿主上的 `PASS` 语义仅覆盖模板，细节行已披露）；`0.1.x` 退役只有文字、无运行时拒收（F4）。

## 7. 命令审计（本轮 Reviewer 全部运行类命令）

工具层文件读取（`git show` / `Get-Content` / `Select-String` / `Get-FileHash` / job 状态）保留在会话记录；下表是执行类命令。所有 `DSH_HOME` 均先断言绝对路径以 `<repo>\.governance\sandboxes\` 开头；未读取/写入真实 `~\.dsh`。compat 检查读取了 PATH 上的全局 CLI 安装（`C:\Users\peter\AppData\Roaming\npm\node_modules`）**只读**用于 oracle 解析。

| # | label | UTC 2026-10-20（起→止） | exit | 影响路径 / 要点 |
| --- | --- | --- | ---: | --- |
| R1 | pytest-subset | 12:23:12.750Z→12:30:01.328Z | 0 | `test_dsh_native_bridge/compat/contract/adapter/boundary/doctor`：**570 passed, 119 subtests, 0 failed, 0 skipped, 407.80s**；`DSH_HOME=.governance/sandboxes/feat102-code-r0-20261020T123102Z` |
| R2 | pytest-native-bridge | 12:36:20.474Z→12:36:21.717Z | 0 | 单独复跑 7 passed（含在上述 570 内）；收集 570 tests |
| R3 | compat-baseline（EVD-2115/2116） | 12:24:25.433Z→12:24:44.110Z | 0 | `DSH_HOME=.governance/sandboxes/dsh021-baseline`（只读）；PASS 19/23、NO_SCHEMA 4、protocol=native、fallback=0 |
| R4 | compat-synthetic-fallback | 12:32:44.973Z→12:33:14.375Z | 0 | 合成 profile + CLI manifest：PASS 19/23、fallback=1、protocol=native |
| R5 | compat-no-cli-manifest | 12:36:53.731Z→12:37:21.079Z | 0 | 合成 profile 无 CLI manifest：FAIL 18/23、workflow-ptc unresolved、protocol=legacy、fallback=0 |
| R6 | compat-cli-renderer | 12:33:23.907Z→12:33:53.415Z | 0 | `verify_workflow.py check-dsh-preset-compat`：PASSED 19/23 + protocol 行 |
| R7 | compat-check-section | 12:33:56.117Z→12:34:30.613Z | 0 | `emit_check_section()`：`[PASS]` box + protocol 行，返回 0 |
| R8 | bridge-probes-run1 | 12:34:54.147Z→12:34:54.340Z | **1** | Reviewer 探针自身缺陷（临时 base 被删后 `mkdtemp` ENOENT），无产品结果，如实保留 |
| R9 | bridge-probes-run2 | 12:35:00.618Z→12:35:00.828Z | 0 | A native 零写；B entries 抛错→写目录；C 无 loader→拒收；D 无 native 块→拒收；E1/E2/E3 生命周期 |
| R10 | dsh-host-verify-rerun | 12:31:22.438Z→12:31:35.945Z | 0 | EVD-2112 复跑；新 sandbox 仅 sessions/storages/identity，`.agent-presets` 不存在 |
| R11 | dsh-help | 12:36:21.717Z→12:36:30.222Z | 0 | `dsh --help` / `dsh web --help` 只读选项发现 |
| S1 | sandbox-scaffold（R10 内） | R10 起前 | 0 | 从 `dsh021-baseline/profiles/web` 复制 5 个骨架文件 + 4 个 node_modules 元数据；`@peterwangze/...` junction→repo；写 scratch patch/verify row |
| S2 | synthetic-plane junctions（R4/R5 内） | R4/R5 起前 | 0 | 在 2 个 sandbox 内建 25 个指向 CLI 包的 junction；只读使用目标 |
| S3 | junction remove/restore（R5） | 12:36:53 前/后 | 0 | 删除前校验绝对路径前缀 + `LinkType=Junction`；跑完恢复 |

**计数**：执行类 11 条（R1-R11，其中 R8 失败自纠）+ 准备类 3 条（S1-S3），共 **14 条命令**；连同只读读取/检索，本轮 pwsh 工具调用 60+ 次（执行类全部在上表，只读类保留于会话记录）。测试实数：**570 passed / 0 failed / 0 skipped**（另有 native 文件 7 passed 的独立复跑；subtests 119 passed）。

### Reviewer 证据 SHA256（`.codex-sandbox/FEAT-102/code-r0/`）

| 文件 | SHA256 |
| --- | --- |
| `pytest-subset.log` | `D41475E48036143A5427FFDF7DF870C57C697292B5EA26771B630D73E04B9B1A` |
| `pytest-native-bridge.log` | `460269D001961146D9E801B359CFD363FA63ED3CE7EA056072DE32D86F00F692` |
| `compat-dsh021-baseline.json` | `249AC43B26717D8E0B4EF57172FA07350C427385D722FFBD116544E126CE44B1` |
| `compat-fallback-synthetic.json` | `9201E04B89A6F5C4C47FCF6D95FF27EE623EB45698D2896E1BEA28AF65FD439A` |
| `compat-fallback-no-cli-manifest.json` | `A2C16CCBA25C209E50EF43C5945A19E3600ADC93FD3E69FEBDA34E6F3B678228` |
| `compat-cli-renderer.log` | `687F5500BB4A2AF5333AD6F284BC0A8964A14F7E85087789FDA1B555B18DC8DC` |
| `compat-check-section.log` | `CF8D1081DA9CE1C07FF4FA535AFD0AEA510F8DFEC0D69F89C17859F27839351D` |
| `verify-rerun.json` | `6A35C68084178B28F5B2B1D254548022917D59D6F05EB8477F142DD247FF7182` |
| `dsh-verify-rerun.log` | `F53ABDF31401BB1A9B827C23BDB7D5CE1F58EFA333B2FB658F29A673AB0055A3` |
| `bridge-probes.log` | `9C5BF7B04B3E3853360AE556224A08DA20E7E9118E841C34F53BDE140280F151` |
| `bridge-probes.mjs` | `270F6A6AB32752F9DA8FAE306AE6BBA145593CC917EA5C256681094A59C7B029` |
| `verify-rerun.patch.yml` | `28D9252EA8AD79C96A5ECADC50E2DD001210D222C965C196EDD3298290F94914` |
| `verify-row.mjs`（scratch 副本） | `B3CF34C76E1347F3B63E1210CC01BDF3BAA5C1715FBB4099457AE93E7645583B` |

## 8. NOT_RUN 清单（未跑 ≠ 通过）

- EVD-2115/2116 的 **`fallback=1` 在原引用隔离环境不可复现**（见 §3.2）；合成剖面结果不冒称真实环境。
- EVD-2113（真实 HOME 事故）、EVD-2114（真人重启确认）：不在代码审查面，**NOT_RUN**。
- 0.1.x 旧宿主兼容/明确拒收：无 0.1.x 安装可跑，**NOT_RUN**（代码也未见拒收实现，见 F4）。
- 多 profile / desktop / headless：未安装未启动，**NOT_RUN**。
- 完整 `check-governance` 全量引擎：未跑；仅单独跑了 Check 28v 的 section 渲染函数与独立 CLI。
- `launch.py --install/--smoke`：未跑（legacy 语义，不在 native 交付面）。

## 9. 硬门槛自检

1. 未修改任何产品代码/测试/治理记录/前轮报告；仅写本报告 + Reviewer scratch + 2 个隔离 sandbox（均为审查所需，且均在本仓库内）。未 stage/commit/push。✓
2. 每条结论均有实际运行/读取证据（文件:行号、JSON、日志哈希），无推断性通过；失败命令（R8）与 NOT_RUN 项如实保留。✓
3. 全部运行在仓库内隔离 `DSH_HOME` 完成（前缀断言），不读写真实 `~/.dsh`；兼容检查只读全局 CLI 安装。✓
4. 暂停 WIP 两文件未触碰。✓
