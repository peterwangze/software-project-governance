# REVIEW-FEAT-102-CODE-R1 — 四态 fail-closed / 零写语义与测试看护独立复审

- 日期：2026-10-21（Asia/Shanghai；本报告所有时刻均为 **UTC 2026-10-21**）
- **结论：NEEDS_CHANGE**
- **unresolved_blockers=1**
- P0=0，P1=1，P2=2，P3=6
- 审查对象：HEAD `98d99c2889e292d6665e7a9f1f53309f0d008b38` + **未提交返工工作树**；相对 `dcf5009` 的批准集 15 文件 + 冻结设计文档（Architect R7）+ 既有暂停 WIP。工作树在权威测试窗口内逐字稳定（本轮独立复验 `STABILITY_STATUS_SAME=True / STABILITY_HASH_SAME=True`）。
- 设计合同：`docs/architecture/dsh-adapter-version-decoupling.md` SHA-256 `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE`（806 行，冻结）；本报告以它为合同基准。
- Reviewer 身份：**同一 Code Reviewer 实例**承接 CODE R0（M7.4 T1）；仅写本报告 + Reviewer scratch（`.codex-sandbox/FEAT-102/code-r1/`）+ 隔离 `DSH_HOME` sandbox；未修改/stage/commit 任何产品代码、测试、治理记录、前轮报告；暂停 WIP 两文件字节未动。

## 1. 对象绑定

### 1.1 基准

| 项 | 值 |
| --- | --- |
| 基线 commit | `dcf5009` |
| HEAD | `98d99c2889e292d6665e7a9f1f53309f0d008b38`（4 个产品 commit 已提交；本轮返工未提交） |
| 设计合同 SHA-256 | `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE`（806 行） |
| CODE R0 报告 SHA-256 | `F71AD9EC8BD6EA14F40E2475F2CEED8126027C3DF5CA782742848AB1F96DB324` |
| `git diff --cached` | 空（staged 0） |

### 1.2 15 个批准文件（含未改动的 lifecycle 指纹）+ 暂停 WIP

| 文件 | SHA-256 |
| --- | --- |
| `lib/dsh-native/source.js` | `74D8BF3378F7619249DF28B7994248C8C02497E9795F43367AEF3ABCA5CDFFCD` |
| `lib/dsh-native/bridge.js` | `2FCAB50284CC4CBEBEA6BB7221A62664F66B79DCF39E4E3A4C0AE96E698B4A70` |
| `lib/dsh-native/lifecycle.js`（未改） | `CC1A22106C62E1E48060C651B32565E3437E820168AE5033DEBD83F2D2C54C26` |
| `lib/dsh-native/overlay.js` | `E262F6B0D5F6F5CAEC2A01E63CCE081C2FB4BAE3ECA83537656390E80677F0E3` |
| `lib/index.js` | `8357F8BBC143427040E5AEFEA5DAFA089829226AC6688BF0040D099FD8C36557` |
| `skills/software-project-governance/infra/dsh_compat.py` | `B3186D4FEEFDFDCF64D164CFA7F6FF587A7F15130BEE9A87D2E5A09A2CA6E682` |
| `…/infra/tests/test_dsh_compat.py` | `D770F556068831E9B7D99FAD566DDA8407241ECB0AA90E509E476CA7426D37C2` |
| `…/infra/tests/test_dsh_contract.py` | `6F818BF868A753F4CE2C7376705CD7F0C14E0A63402DD78283DDB0E04F178FBD` |
| `…/infra/tests/test_dsh_native_bridge.py` | `70CC74B29837B9B9D1AA750F2A8487C75C6440210BD8E798B5E22DDFC409B570` |
| `…/infra/tests/test_dsh_adapter.py` | `9AC09CD421DB0A43FC799BB74E4E49B0453F38872D517C905BB306A08B1E62E4` |
| `adapters/dsh/host-contract.json` | `AD94666F53FB290F9820A8905F7162FA557E6CB648EB6C63A14A7861767ED315` |
| `README.md` | `DBCB6F86BFD88D79144056798AB7B8C022E3389BD52CC9DB4ABFAFC7CB8AD170` |
| `adapters/dsh/README.md` | `063B335E6DD5CC842C7CE7E2CAE1BBD31E142EC357E6CC017093352F42B71810` |
| `…/core/version-projections.json` | `66E17AAD9529656327B4E7DD6670D1E18A0378A9F60D4D6D82E1B5F50EFCAD32` |
| `…/core/manifest.json` | `880C6BD327E2B59F6B32B7050F5A949C4B8F622A89D4D5FF584E3F6891905CA9` |
| 暂停 WIP `infra/hooks/commit-msg` | `97806C18C2CFB5E0FB68E909F295FCC236E40B9E50F682FF8F177AED90CD46AC` |
| 暂停 WIP `infra/tests/test_hooks.py` | `60FE5DB5514A378CCA1A325288A31CAC9984FFB555470EC7B799CBFE5669D0DB` |

本轮独立复算：17 个状态行逐字相同；17 个指纹文件 SHA 与 Coordinator 快照一致；`source.js/bridge.js/overlay.js/index.js/compat.py` 等与 `snapshot-before-sha.txt` 逐位相同。设计文档 `M` 是 Architect R7（冻结哈希一致，**不计入产品返工面**）。`adapters/dsh/launch.py` 零改动。

## 2. R0 findings 处置

| R0 finding | 级别 | 本轮状态 | 独立事实 |
| --- | --- | --- | --- |
| F1 组合树不可读时静默写 `$DSH_HOME` | P1 | **已关闭** | `probeNativeHost` 四态化；`bridge.js:140-149` 对 `unreadable` 拒收；`apply()` 不再调用 `ensurePreset`（全库 grep 仅定义/注释）。Reviewer 探针：`entries()` 抛错 → exactly 1 warn `HOST_TREE_UNREADABLE`、registered 0、`wrote=false`。 |
| F2 兼容/协议新逻辑零测试 | P1 | **已关闭** | 六文件 **586 passed / 119 subtests / 0 failed / 0 skipped**（+16：native +4、compat +12）；新增断言见 §3.2；无新增 skip（仅既有 node 可用性守卫）。 |
| F3 fallback anchor 只从 profile 平面推导 | P2 | **已关闭** | `dsh_compat.py` 在 profile 选中但缺 CLI 包时回退 `which('dsh')` 安装 anchor，披露 `fallback_anchor_source`；合成「有行包、无 CLI manifest」剖面由 FAIL/legacy 变为 PASS/native/fallback=1；`protocol` 无 CLI 时为 `unknown`。 |
| F4 契约/README 与代码不符 | P2 | **未完全关闭 → R1-F1（P1）** | 契约、两份 README 的**顶部**段落已改；但两份 README 的升级/使用段落仍写「宿主行 ensurePreset() 重渲染 / 旧宿主才渲染用户根」，见 §4.1。 |
| F5 零写测试未断言 `$DSH_HOME` | P2 | **已关闭** | `test_apply_writes_nothing_on_a_native_host` 现用临时 `DSH_HOME` 并断言无 `.agent-presets`；native/absent/unreadable 三处均显式 HOME。 |
| F6 EVD-2115/2116 fallback=1 不可复现 | P2 | **证据已披露，运行面仍 NOT_RUN** | 设计合同 §16.4.1 已记「fallback=1 在 `dsh021-baseline` 实测为 0，合成剖面才为 1，CODE R0 改判 NOT_RUN 并机录 EVD-2119」；本轮未重跑 compat 基线（R0 证据仍成立），不冒称通过。 |
| F7 unknown protocol 文案矛盾 | P3 | **已关闭** | `dsh_compat.py` 三态分支；`details` unknown 不再借用 legacy 文案；新增三分支/两渲染器测试。 |
| F8 lifecycle disposal 无测试 | P3 | **已关闭** | `_LIFECYCLE_PROBE` E1-E4（激活后 dispose/飞行中卸载 late disposer/同步拒收/异步 rejection）全部断言。 |
| F9 通用 `sandboxes` 跳过 | P3 | **已关闭** | `_SKIP_PATH_PAIRS={(".governance","sandboxes")}` + `CompositionSkipTests`（产品 `product/sandboxes/...` 不再被隐藏）。 |
| F10 `samePath` 全平台小写化 | P3 | **代码已修，测试缺 POSIX 分支** | `overlay.js:27-43` 按平台折叠；无 mock `process.platform` 的测试（R1-F7）。 |

## 3. 本轮独立复验

### 3.1 四态 / 零写 / 单 warn（Reviewer 探针，非测试套件）

`four-state-probe.mjs`（`.codex-sandbox/FEAT-102/code-r1/`，每个 case 独立临时 `DSH_HOME`，跑完删除）：

| case | registered | warn code(s) | 写目录 |
| --- | ---: | --- | --- |
| native（registry + base） | 1 | 无 | false |
| absent（仅 base） | 0 | `HOST_WITHOUT_REGISTRY`（1 条） | false |
| disabled registry | 0 | `REGISTRY_ROW_DISABLED`（1 条） | false |
| unreadable（`entries()` 抛错） | 0 | `HOST_TREE_UNREADABLE`（1 条） | **false** |
| loader 缺失 + inject | 0 | `HOST_TREE_UNAVAILABLE`（1 条） | false |
| loader 缺失 + 无 inject | 0 | `HOST_NO_LOADER_TREE`（1 条） | false |
| ambiguous：两个 base | 0 | `BASE_DUPLICATE`（1 条） | false |
| ambiguous：两条 persona | 0 | `PERSONA_ROW_DUPLICATE`（1 条） | false |

`index.js` 的 `apply()` 内无任何 `ensurePreset` 调用（grep 仅注释/定义）；所有写 API 只在 `ensurePreset()` 内（`mkdirSync`/`writeFileSync`/`renameSync`/`rmSync` 行号 547-630）。

**`CONTRACT_WITHOUT_NATIVE_BLOCK` 专属 actionable warn**（包副本移除 `own.native`，临时 `DSH_HOME`）：`threw=null`、恰好 1 条 warn，含 `contract unreadable` / `--sync` / `--install`；`.agent-presets` 不存在、HOME 条目 0。

### 3.2 测试看护（真实断言复核）

- 六文件独立重跑：**586 passed / 119 subtests / 0 failed / 0 skipped，721.15s，exit 0**；窗口前后 `STABILITY_STATUS_SAME=True / STABILITY_HASH_SAME=True`。
- 聚焦：native bridge **11 passed**；compat 新四类 **12 passed**；contract 变异/无契约 **5 passed**；adapter rework **4 passed**（均 `-q`，exit 0）。
- 关键断言抽查：`test_apply_writes_nothing_on_a_native_host`（临时 DSH_HOME + 无 `.agent-presets`）、`test_apply_refuses_an_unreadable_tree_instead_of_rendering_legacy`（mode/code/registered/warnings/零写）、`test_apply_never_renders_a_legacy_host`（`HOST_WITHOUT_REGISTRY` + 零写）、`test_declaration_based_refusals_never_write`（3 子例 code/零写）、`test_registration_lifecycle_disposes_exactly_once`（E1-E4）、`DualPlaneProbeTests`（fallback 计数/越界 NODE_PATH 拒绝/无 anchor）。未发现 skip、删除或断言偷换；本轮 7 个旧测试为有意的改名/翻转（4 contract + 2 adapter + 1 native legacy，见 REWORK-R2 §1.2/§1.5），不是静默弱化。
- `test_contract_input_describes_the_behaviour_the_row_implements` 断言契约/两份 README 含四态与「绝不写目录」，但**未断言** README 中「宿主行重渲染」旧句消失 → 该 guard 对 R1-F1 失明。

### 3.3 宿主回归（隔离 `DSH_HOME`）

新建 `.governance/sandboxes/feat102-code-r1-live-20261021T003337Z`，dsh 0.2.1-rc.2，真实 `link:` bundle，`dsh --profile web --patch <scratch> --port 0 --no-open`，exit 0：

- roster 5 项含 `governance`，`name=治理协调器`，`broken=null`；`resolve` 无 broken；会话 `composed=governance`；治理 skill 43 个，standard 8 个；`governanceSkillVisible=true`、`leaked=false`、`standardUnaffected=true`；
- `${DSH_HOME}/.agent-presets` **不存在**；新 sandbox 仅 sessions/storages/identity。
- 设计 §16.1 的 native 行语义在真实宿主上未被本轮返工破坏。

### 3.4 取舍复核

**(a) 保留 `ensurePreset` 导出、标注 Explicit install face only：可接受（附 P2 条件）。**
- row 路径已无 `ensurePreset`（grep）；`host-contract.json:767` 的 `export_surface` 仍钉住它；显式面仍有 cleanup/collision/payload/成功同步测试；
- Reviewer 探针：显式调用两次 → `synced true → false`、四文件、mtime 不变（幂等语义正确）；
- **条件**：R0 的幂等测试被替换后，`existsSync(userDir) && current === version → return` 分支无永久测试（R1-F2，P2），建议随 R2 补一条显式面幂等用例。
- 若后续决定彻底移除，需同步契约 `export_surface` + `test_row_exports...`；本轮不要求。

**(b) 四态/零写语义与设计 §16.1/§16.2：一致。**
- absent/disabled/unreadable/ambiguous 全部「一条 warn + 零写」，只有 native 产生登记（§16.1 736-741）；`CONTRACT_WITHOUT_NATIVE_BLOCK` 专属 warn 仍零写；`HOST_WITHOUT_REGISTRY` 不再渲染（§16.2/§16.4.5 的 2026-10-21 修订）。
- 残留契约文字 nuance：§4.2 第 115 行写「恰好一个**启用**的 persona/skill row」，实现按同名行计数（disabled+enabled 并存会以 `*_ROW_DUPLICATE` 拒收）；§4.2 第 116 行的 `POLICY_CONFLICT` 在实现中没有对应 code。两者都是 fail-closed、不产生错误合并，且 §16.1 第 743 行也允许「明确拒收（不猜）」；作为 R1-F8（P3）建议契约措辞/测试对齐，不阻断。

**(c) `coverage.entries` guard 改指 `test_dsh_doctor.py::test_s2_reports_the_projected_coverage_in_its_credible_face`：机械成立，语义只部分成立。**
- 独立运行 `check-dsh-boundary`：**K-8 PASS，26 claims backed，14 strong each negative; Result PASS**（exit 0，UTC 00:31:18.705Z→00:31:19.303Z）。
- K-8 只验证 guard 引用可解析；该 S2 测试确实验证了 coverage 投影（`unreadable_compositions`、18 of 23），比旧的渲染幂等 guard 更贴题。但 claim 的 `gap_note` 明确指向 node-gated skip 披露（doctor S6 的 `unverified_due_to_env`），直接覆盖者是 `test_dsh_doctor.py::test_the_environment_gated_faces_come_from_the_contract`（:531-534），不在 guard 列表中。建议补列（R1-F5，P3）。

## 4. Findings

### P1（阻断，本轮必须修改）

**R1-F1 — DEC-366② 的「两份 README 统一」未完成；guard 测试给出虚假保证**

- 设计合同 §16.4.5（frozen，806 行）明确要求「代码/契约/两份 README/测试需统一到『默认 warn-only、不自动写目录，写目录仅限显式 `launch.py --install`』……由 CODE R1 关闭」。当前工作树仍存在以下用户可见陈述：
  - `README.md:111`：`# upgrade: git pull, then restart dsh — ensurePreset() re-renders the preset by package version …`
  - `README.md:113`：`… or restart dsh and let ensurePreset() re-render (overwrites in place)`
  - `README.md:432`：`升级 | … git pull 后重启 dsh——宿主行 ensurePreset() 按包版本重渲染 …`
  - `README.md:433`：`降级 | … 或重启 dsh 由 ensurePreset() 重渲染`
  - `adapters/dsh/README.md:31`：`升级后刷新用户根预设：…宿主行 ensurePreset() 按包版本幂等重渲染`
  - `adapters/dsh/README.md:34`：`只有未声明 registry row 的旧宿主才渲染用户根目录`（与本文件 :12「row 在任何情况下都不调用 ensurePreset()」直接矛盾）
  - `adapters/dsh/README.md:48`：`用户根预设的刷新正道同样是重启 dsh——bundle 宿主行 ensurePreset() 按包版本幂等重渲染`
- 独立事实：`apply()` 已无 `ensurePreset` 调用；absent 只 warn 不写（探针 + 586 测试）。对目录模型/显式安装用户，`git pull + 重启` 不再刷新 `${DSH_HOME}/.agent-presets/governance`，必须显式 `launch.py --install`；当前 README 的升级/降级指令会把用户引向不会发生的重渲染。
- guard 失明：`test_dsh_native_bridge.py:467-497` 只检查四态词、`绝不写目录`、契约无 `legacyAutoRender`、root README 无一句旧文案；**没有**检查上述 7 处旧句，因此测试绿而文档仍矛盾。该测试 docstring（:472-474）却声称「the old 'row renders for old hosts' wording must not come back either」——事实不成立。
- 处置：更新两份 README 的升级/降级/使用段落（上面 7 行），并把 guard 扩为「adapter README 不含『旧宿主才渲染』/『宿主行 ensurePreset…重渲染』，root README 不含 `ensurePreset() re-renders`/`let ensurePreset() re-render`」。属 doc+test 修改，无产品行为变更。
- 严重度理由：这不是孤立措辞，而是设计合同点名的 R1 关闭条件，且同一文件自相矛盾、guard 反向保证；若以 AWN 关闭会留下错误的迁移指令。

### P2（建议本轮一并修正，不单独阻断）

**R1-F2 — 显式面 `ensurePreset` 的版本幂等分支失去永久测试**

- 位置：`lib/index.js:476` 起的 `ensurePreset()`（幂等判断在 `existsSync(userDir) && current === version → return`）；旧测试 `test_lib_ensure_preset_renders_the_user_root_idempotently` 在本轮被替换为 `test_lib_apply_never_renders_the_preset_directory`。现存的显式面测试覆盖 cleanup/collision/payload/单次成功同步，但不覆盖「第二次调用 no-op、mtime/字节不变」。
- 证据：`test_dsh_adapter.py` 中 `idempot`/`st_mtime_ns` 对本函数零命中；Reviewer 探针（临时 DSH_HOME）两次调用得到 `synced: true → false`、四文件、mtime 不变——**行为正确但无回归网**。
- 建议：新增一条小测试（显式面连续两次、断言 `synced` 第二次 false 且字节/mtime 不变），或若 Python `launch.py` 侧已有等价测试，在报告/测试名中明确它不是 JS 显式面的覆盖。

**R1-F3 — 批准集外的产品文档仍描述 row 自动渲染**

- `adapters/dsh/adapter-manifest.json:32`：`"preset_file": "… rendered from … by the bundle row lib/index.js on boot, or by adapters/dsh/launch.py --install"`；`:36` note：`… whose lib/index.js ensurePreset() renders … into ${DSH_HOME}/.agent-presets/governance/`。
- `adapters/dsh/launch.py` docstring：`:17-18` 「`lib/index.js` `ensurePreset()` renders the identical composition automatically on bundle boot」；`:31-33` 「post-`git pull` refresh … is a dsh restart, which re-renders it by package version」。
- 两者均未被本轮修改（不在批准集，`launch.py` 为禁改面），但都已被 DEC-366② 推翻。`adapter-manifest` 是 `launch.py --check`/适配器清单的事实源，用户可见。建议 Coordinator 决定是否扩锁修正（纯文档/清单文案，不改启动语义），或在 §16.4.5 的关闭记录中显式列为已知残留并给关闭截止；不要以「不在批准集」自动视为通过。

### P3（讨论/低风险）

**R1-F4 — `test_both_renderers_print_the_same_protocol_line` 只测了一个渲染器**
- `test_dsh_compat.py:3803-3811` 只调用 `emit_check_section()`；`run_cli()` 的 `delivery protocol:` 行（`dsh_compat.py:2296`）未被断言。测试名/docstring 与覆盖不符。建议补 `run_cli` 断言（同一个 mocked report 即可）。

**R1-F5 — 四态「恰好一条 warn」未被测试钉住**
- 契约/README 说每个不可用态「each logs exactly one warning」；`test_dsh_native_bridge.py` 的四态测试断言 `warnings > 0`/含 code，未断言 `len==1`；`test_dsh_contract.py::_assert_row_warns_and_writes_nothing` 同。Reviewer 探针实测恰好 1 条，但重复 warn 的回归不会被测试抓到。建议加 `assertEqual(len(warnings), 1)`（native happy path 可另断言 0）。

**R1-F6 — `coverage.entries` guard 的语义尚未覆盖 gap_note**
- 见 §3.4(c)。K-8 机械 PASS（26 claims）成立；建议把 `test_dsh_doctor.py::test_the_environment_gated_faces_come_from_the_contract`（:531-534，`unverified_due_to_env`）加入 guard，或把该 claim 的 gap_note 收窄到 S2 实际覆盖的 coverage 计数。

**R1-F7 — F10 平台路径折叠无测试**
- `overlay.js:27-43` 的 POSIX/macOS 分支（不折叠大小写、不把 `\` 当分隔符）没有 mock `process.platform` 的用例；当前证据仅 Windows。建议补一条 Node 子进程 `Object.defineProperty(process, 'platform', ...)` 或纯函数参数化测试。

**R1-F8 — 设计 §4.2 的「恰好一个启用 row」/`POLICY_CONFLICT` 与实现对不齐（契约内部）**
- `overlay.js:47-55` 的 `rowIndexes` 按 name 计数，不按 effective disabled 过滤；一个 disabled + 一个 enabled 的同名 persona/skill 行会被判 `*_ROW_DUPLICATE` 而不是选用 enabled 行。设计 §4.2 第 115 行写「恰好一个**启用**的 row」，§16.1 第 743 行又写「按『恰好一个启用 row』判定并明确拒收（不猜）」；实现选择拒收，属 fail-closed、无错误合并/无写目录，但与 §4.2 的字面规则不一致且无共存用例。§4.2 第 116 行的 `POLICY_CONFLICT` 在代码/测试中无对应实现或 code。建议由设计 owner 明确规则（启用过滤 vs 直接拒收），补一条共存负例；不阻断本轮代码行为。

**R1-F9 — 两处小文档/测试缺口**
- `locate_dsh_install` 的 return docstring 未列出本轮新增的 `fallback_anchor`/`fallback_anchor_source`/`registry_package`/`protocol`（只有旧字段），与实现字段面不一致。
- `CONTRACT_WITHOUT_NATIVE_BLOCK` 的零写由 Reviewer 探针验证（`agentPresetsExists=false`、HOME 条目 0），但既有 `test_render_composition_without_a_contract_reports_every_token` 只断言 warn/`--sync`，未断言 `DSH_HOME` 空；建议在 R2 顺手加一条断言。

## 5. 改动面 / 越界与夹带核查

- `git status --porcelain -uno` = **17 行**：14 个修改的批准文件 + `lifecycle.js`（未改指纹）+ `docs/architecture/dsh-adapter-version-decoupling.md`（Architect R7，冻结哈希一致）+ 2 个暂停 WIP。`git diff --cached` 空。
- 无新增/修改批准集外的 tracked 产品文件；`adapters/dsh/launch.py` 未改；`agent-presets/*` 未在本轮改动（4 个 commit 内容保持）；未发现夹带。
- 未跟踪项仅为 Reviewer 既有 review 文档、`.codex-sandbox/`、`.governance/sandboxes/` 隔离目录；无产品文件。
- 暂停 WIP 两文件 SHA 与登记值一致（`97806C18…`、`60FE5DB5…`），本轮零变化。
- 说明：`docs/architecture/...md` 相对 HEAD 有 156 行改动（R7 设计修订），属设计合同变更，不是产品代码返工；本轮按 Coordinator 指定以其为合同基准。

## 6. 回归与安全

- native 宿主零写 `$DSH_HOME`（真实隔离宿主 + 探针）；absent/disabled/unreadable/ambiguous/`CONTRACT_WITHOUT_NATIVE_BLOCK` 全部 warn-only 零写。
- `apply()` 无 `ensurePreset` 调用；写 API 仅在显式面 `ensurePreset()`；`launch.py` 未改，`test_js_and_python_renderers_agree` 通过（六文件 586 套件内）。
- 无宿主/坏契约：`HOST_TREE_*`/`HOST_NO_LOADER_TREE`/`CONTRACT_WITHOUT_NATIVE_BLOCK` 均为拒收+零写；compat 的 `NOT_RUN`/`FAIL` 逻辑未改，未见新的假 PASS。
- 真实环境防护：本轮所有命令先设并断言 `DSH_HOME` 在仓库 `.governance/sandboxes/` 或 `.codex-sandbox/` 内；宿主运行使用新建 sandbox；未读写真实 `~/.dsh`。一次探针命令误用 PowerShell 只读变量 `$home`，赋值失败后触发前缀断言、**运行前 fail-closed**（未启动 Node），改名后重跑；如实披露。

## 7. 命令审计（运行类）

| # | label | UTC 2026-10-21（起→止） | exit | 要点/影响路径 |
| --- | --- | --- | ---: | --- |
| R1 | pytest 六文件（权威） | 00:29:32.528Z→00:41:34.312Z | 0 | **586 passed / 119 subtests / 0 failed / 0 skipped，721.15s**；`DSH_HOME=.governance/sandboxes/feat102-code-r1-20261021T002907Z`；窗口前后 status/hash 同 |
| R2 | 聚焦四段 pytest | 00:41:40.166Z→00:42:00.622Z（同一窗口） | 0 | native 11（0.64s）/ compat 新类 12（0.55s）/ contract 变异+无契约 5（0.86s）/ adapter rework 4（16.61s），四段均 exit 0 |
| R3 | check-dsh-boundary | 00:31:18.705Z→00:31:19.303Z | 0 | K-8 PASS 26 claims（14 strong）；Result PASS 0 failing |
| R4 | check-projection-sync | 00:39:05.095Z→00:39:12.709Z | 0 | 28 mirrors；唯一 drift=`project/e2e-test-project/.../SKILL.md`（既有 FIX-457，非本任务）；persona 零 drift |
| R5 | dsh 宿主 verify（REVIEW 复跑） | 00:33:37.898Z→00:33:51.094Z | 0 | roster/composed/skills/leaked/standard/`.agent-presets` 见 §3.3 |
| R6 | 四态探针首次 | ≈00:32:10Z（打印 START 前断言终止，无精确 UTC） | **1** | Reviewer 命令自身误用只读 `$home`，前缀断言 fail-closed，未运行 Node；如实保留 |
| R7 | 四态探针重跑 | 00:32:13.167Z→00:32:13.304Z | 0 | 8 case + direct contract 见 §3.1 |
| R8 | CONTRACT 无 native 探针 | 00:42:07.154Z→00:42:07.281Z（console）；00:42:57.991Z 重跑留档 | 0 | 1 条 actionable warn、零写、HOME 0 条目 |
| R9 | ensurePreset 幂等探针 | 00:42:12.534Z→00:42:12.663Z（console）；00:42:58.117Z 重跑留档 | 0 | 首次 synced=true，二次 false，mtime 不变 |

只读命令（`git status`/`git diff`/`git show`/`Get-Content`/`Select-String`/`Get-FileHash`）保留于会话记录；未计入上表。测试实数：**586 passed / 0 failed / 0 skipped（119 subtests）**；聚焦另计 11/12/5/4 全绿。

### Reviewer 证据 SHA-256（`.codex-sandbox/FEAT-102/code-r1/`）

| 文件 | SHA-256 |
| --- | --- |
| `pytest-six.log` | `348A5167A4C8D5DB0B633917B9C09275385C9BBC549156F9A636FEF500F8A499` |
| `pytest-native-bridge.log` | `E347E1DAA7BA1AFD6BE613E99A28A4EF8999EF4C24C2F5325F61C79A300E6341` |
| `pytest-compat-new.log` | `F21A13727199B9BFE714ECFB8BE97948789F5BB80E2256BD1EB401591A520CF1` |
| `pytest-contract-rework.log` | `904C7ACCEA65D3119AD924D5227821A092DFA6BDA6452D9E0369ABBBCAE3E858` |
| `pytest-adapter-rework.log` | `DA2BCE11E3874C9A7937A7EF331CAD5EBA563F7DFACCD7134BF6EEF66E502F99` |
| `check-dsh-boundary.log` | `540F753E765680C035CB2CADA6D3C1922B51E3F439616A93BAFA9712DA6C0423` |
| `check-projection-sync.log` | `68F0110442F47C031BD93603E6102AED5091529E23FC221D842A70B6F4C91B36` |
| `verify-r1.json` | `5F758F75C2939DB14BA790DF9360141A63D235071E43CC8A34692FE825226C3B` |
| `dsh-verify-r1.log` | `C11BA335C531864CB62725EB9FE71197F4DC570C917A44DEB5B4BE8C6F5E5F94` |
| `four-state-probe.log` | `45A4A95AB0552BCD99E1973E32F4EADB81D937D585D2682DA03D4AE94E241EEC` |
| `four-state-probe.mjs` | `58DE8AAC7D098838907897099F1B921F272BC843DEE6E6977CE0452626295E24` |
| `contract-unreadable-probe.log` | `9BDDB33D783507398BF41DC98B403F929405F0FC37249091AC82F6DDBE797585` |
| `ensure-preset-idempotence.log` | `499EECE5277439622AF89E4B55D350A3B18B27CE43604CCE7506C7DD17F2665A` |
| `verify-r1.patch.yml` | `BAED2287304CB391E9C5345CD59E66F500926FE63E2261CB3C7F47AD7B353F98` |
| `verify-row.mjs`（scratch 副本） | `B3CF34C76E1347F3B63E1210CC01BDF3BAA5C1715FBB4099457AE93E7645583B` |
| `status-before.txt` / `sha-before.txt` | `9AC851DE43A835E72DA620AE01B513AC6051435C4E78F7679E9EB950AC3FBB2E` / `C6E678AE24EC70CD87BA020EDCCD316C9EDA63776045C04B6C481E4244AFDDEE` |

## 8. NOT_RUN（未跑 ≠ 通过）

- EVD-2115/2116 的 `fallback=1` 在 EVD-2112 所述隔离环境仍 **NOT_RUN**（R0 实测 0；设计 §16.4.1 已记，EVD-2119）；合成剖面结果只作代码路径验证，不冒称真实 profile。
- 0.1.x 旧宿主：无安装，NOT_RUN；代码现为 warn-only + 显式安装（不声明旧版运行支持）。
- 多 profile / desktop / headless：NOT_RUN。
- 完整 `check-governance` 全量引擎：未跑；只跑六文件测试 + Check 28w boundary + projection sync。
- `launch.py --install/--smoke`：未执行（未改动；显式安装语义由代码/既有测试面保持）。
- raw/accepted、base broken、`BASE_CONFIG_INVALID`/`BASE_NOT_CLONEABLE` 负例：设计 §16.4.7 明确 NOT_RUN（I-R6-6），本轮未覆盖。
- 真实 `~/.dsh` / 真实 profile：未读写，NOT_RUN。

## 9. 硬门槛自检

1. 未修改产品代码/测试/治理记录/前轮报告；仅写本报告、Reviewer scratch、隔离 sandbox。未 stage/commit/push。✓
2. 每条结论均有实际运行/读取证据（文件:行号、探针输出、JSON、日志哈希）；失败命令（R6）与 NOT_RUN 项如实保留，未把未跑写成通过。✓
3. 全部运行在仓库内隔离 `DSH_HOME` 完成（前缀断言），宿主复跑使用新建 sandbox；未读写真实 `~/.dsh`。✓
4. 设计合同按冻结哈希 `122CFB22…` 核对；R0 报告按 `F71AD9EC…` 承接。✓
