# REVIEW-FEAT-102-CODE-R2 — 文档口径收口 + 回归网补强复审

- 日期：2026-10-21（Asia/Shanghai；本报告所有时刻均为 **UTC 2026-10-21**）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=1，P3=2
- 审查对象：HEAD `98d99c2889e292d6665e7a9f1f53309f0d008b38` + **未提交返工工作树**（R3 增量）。相对 `dcf5009`：批准集 **18 文件**（16 modified + `lifecycle.js`/`test_dsh_doctor.py` 未改指纹）+ 冻结设计文档 + 既有暂停 WIP 2。
- 设计合同：`docs/architecture/dsh-adapter-version-decoupling.md` SHA-256 `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE`（806 行，冻结，不计返工面）。
- 前轮：R1 报告 SHA-256 `6AEC202973F25A9784F5115527D2DCEAEF4B4ED7CEC444AD086CEC3EAF92F7A3`（结论 NEEDS_CHANGE / 1 blocker）。Reviewer 为同一实例（M7.4 T1）。
- 写入边界：仅写本报告 + Reviewer scratch `.codex-sandbox/FEAT-102/code-r2/` + 隔离 `DSH_HOME`；未修改/stage/commit 产品代码、测试、治理记录；暂停 WIP 两文件字节未动。

## 1. 对象绑定

### 1.1 基准

| 项 | 值 |
| --- | --- |
| 基线 commit | `dcf5009` |
| HEAD | `98d99c2889e292d6665e7a9f1f53309f0d008b38`（R3 返工未提交） |
| 设计合同 SHA-256 | `122CFB22EDC997AEA2BAF2816AC1C727106101BC9DB4BB625DFA238A633754DE` |
| R1 报告 SHA-256 | `6AEC202973F25A9784F5115527D2DCEAEF4B4ED7CEC444AD086CEC3EAF92F7A3` |
| 工作树 | `git status --porcelain -uno` = 19 行（16 个 modified 批准文件 + 设计文档 + 2 暂停 WIP；`lifecycle.js`/`test_dsh_doctor.py` 未改）；`git diff --cached` 空 |
| 权威快照 | `.codex-sandbox/FEAT-102/rework-code-r1/snapshot-r3-{before,after}-{status,sha}.txt`；本轮逐项复算 **20/20 SHA 与 before 快照一致** |

### 1.2 18 个批准文件（含未改的 test_dsh_doctor / lifecycle）+ 暂停 WIP

| 文件 | SHA-256 |
| --- | --- |
| `lib/dsh-native/source.js` | `74D8BF3378F7619249DF28B7994248C8C02497E9795F43367AEF3ABCA5CDFFCD` |
| `lib/dsh-native/bridge.js` | `2FCAB50284CC4CBEBEA6BB7221A62664F66B79DCF39E4E3A4C0AE96E698B4A70` |
| `lib/dsh-native/lifecycle.js`（未改） | `CC1A22106C62E1E48060C651B32565E3437E820168AE5033DEBD83F2D2C54C26` |
| `lib/dsh-native/overlay.js` | `E262F6B0D5F6F5CAEC2A01E63CCE081C2FB4BAE3ECA83537656390E80677F0E3` |
| `lib/index.js` | `8357F8BBC143427040E5AEFEA5DAFA089829226AC6688BF0040D099FD8C36557` |
| `…/infra/dsh_compat.py` | `46771452EABD9FF50B0C1B52419B7B102025E8AF03DF60B90D8CD7D3DA8F420D` |
| `…/tests/test_dsh_compat.py` | `B4FFBE7A60E4F0935A814D19F34F0BC44C371AD0AD91494547C250996E2766ED` |
| `…/tests/test_dsh_contract.py` | `F9F6910162BA2664153C1E7BEAEA30A7AB1ED792131900C57A27137F5B849F7E` |
| `…/tests/test_dsh_native_bridge.py` | `475C9B17A03FB090E0D7CEA68826678B35F7526DC771D3C8FE39871C95614EE0` |
| `…/tests/test_dsh_adapter.py` | `35639BB5647AFF1F1556033B8A41A9534C0DB0E28428F1FB05A35EC9D871746D` |
| `…/tests/test_dsh_doctor.py`（未改） | `E44DD224283CC092B3F8BF918B3A776C49941B466EE70C9ED9D932A8278800D4` |
| `adapters/dsh/host-contract.json` | `5DFF95497EBBF52788405F1ED6A360BBFB284500BCE3F25E969D835B95E9DD9A` |
| `adapters/dsh/adapter-manifest.json` | `A58E199B03E60081500D04F7C1F33B0549AFE38E619B1DD5545781E1954BDEDA` |
| `adapters/dsh/launch.py`（仅 docstring） | `D9D27362FE2A92D1947D95BE7EAFAAF09564C82286EAD20F0C2979B93BCE006A` |
| `README.md` | `29BCDE87AD8122EE5B60303D99790F54E4D55549AC7A177BD35CD52B26775C77` |
| `adapters/dsh/README.md` | `CD06087371A562F166DABA2CD436B0BC60400B5F934D4752F1F2529A2A9D5ED4` |
| `…/core/version-projections.json` | `66E17AAD9529656327B4E7DD6670D1E18A0378A9F60D4D6D82E1B5F50EFCAD32` |
| `…/core/manifest.json` | `880C6BD327E2B59F6B32B7050F5A949C4B8F622A89D4D5FF584E3F6891905CA9` |
| 暂停 WIP `infra/hooks/commit-msg` | `97806C18C2CFB5E0FB68E909F295FCC236E40B9E50F682FF8F177AED90CD46AC` |
| 暂停 WIP `infra/tests/test_hooks.py` | `60FE5DB5514A378CCA1A325288A31CAC9984FFB555470EC7B799CBFE5669D0DB` |

本轮独立复算：20 个指纹文件逐位匹配 `snapshot-r3-before-sha.txt`；`git diff --exit-code HEAD -- test_dsh_doctor.py` = 0（未改）；`launch.py` 只在 docstring；`git diff --cached` 空。设计文档 `M` 是 Architect R7（冻结哈希一致，不计返工面）。

## 2. R1 findings 处置

| R1 finding | 级别 | 本轮状态 | 独立事实 |
| --- | --- | --- | --- |
| F1 两份 README / 全部旧叙述 | P1 | **live 文档已关闭；guard 残留 P2（R2-F1）** | 四面的旧句逐处替换；独立全量扫描无旧措辞命中；正反 guard 均存在（见 §3.1）。残留：guard 负向清单未覆盖 README:433 的旧句与 adapters README:12 的旧归属。 |
| F2 显式面幂等无永久网 | P2 | **已关闭** | `test_lib_ensure_preset_is_idempotent_per_package_version`（test_dsh_adapter.py:2131-2169）：首跑 `synced=true` + 4 文件；二次 `synced=false` + 目录 `st_mtime_ns` 不变。 |
| F3 批准集外 manifest/launch 旧叙述 | P2 | **已关闭** | manifest 32/36/63 三处改写；L63 在 HEAD 确为旧句（`bundle host row's ensurePreset() re-renders…`），R1 漏列、本轮补上；launch.py 仅 docstring（`git diff -U0` 两个 hunk：17、31 段），无代码。 |
| F4 run_cli 未覆盖 | P3 | **已关闭** | `test_the_cli_renderer_prints_the_same_protocol_line`（test_dsh_compat.py:3813-3822）对 native/legacy/unknown 三态断言 `run_cli` 输出。 |
| F5 四态「恰好一条 warn」 | P3 | **部分关闭（R2-F2）** | unreadable/absent/declaration 三负例已 `len==1`（:447/:465/:487）；**disabled 态与 native happy path 的 warn 数量仍未钉住**。 |
| F6 coverage.entries guard 语义 | P3 | **部分关闭（R2-F3）** | gap_note 已引用 `test_dsh_doctor.py::test_the_environment_gated_faces_come_from_the_contract`；该测试存在（:531-534）且断言 S6 `unverified_due_to_env`；但仍是 prose，guard 列表未加。 |
| F7 F10 POSIX 无测试 | P3 | **已关闭** | `test_path_identity_folds_case_per_platform`（:491-506）+ `_PATH_IDENTITY_PROBE`；子进程内、导入前重定义 `process.platform='linux'`，断言 `/a/skills` 被追加（2 dirs）；native 分支按平台断言。 |
| F8 §4.2 字面 nuance | P3 | **未改（设计面）** | REWORK-R3 §1.5 明确交设计面；本轮不要求；未新增错误合并/写目录。 |
| F9 locate 字段/无契约零写 | P3 | **已关闭** | `locate_dsh_install` Returns 段新增 4 字段语义；`test_render_composition_without_a_contract_reports_every_token` 新第 4 条断言 `DSH_HOME/.agent-presets` 不存在（test_dsh_contract.py:2302-2307）。 |

## 3. 重点复核（逐项）

### 3.1 旧叙述与 guard 覆盖面

- **live 文档**：对 `README.md`、`adapters/dsh/README.md`、`adapter-manifest.json`、`launch.py` 扫描 `ensurePreset() re-renders`、`let ensurePreset() re-render`、`由 ensurePreset() 重渲染`、`ensurePreset()) renders`、`The render is idempotent`、`renders the identical`、`by the bundle row lib/index.js on boot`、`whose lib/index.js ensurePreset() renders`、`旧宿主才渲染`、`宿主行 ensurePreset()` 等 → **无旧句命中**；剩余 `ensurePreset` 出现处是 `launch.py` 的合法显式面说明（:632-638）与新的否定/显式面措辞。
- **guard 结构**：`_RETIRED_AUTO_RENDER_WORDING`（test_dsh_native_bridge.py:532-544，11 条）对四个面做 `assertNotIn`；正向断言（:579-?）要求两 README/manifest/launcher 出现新措辞。正反两面都在，不是只查一半。
- **覆盖缺口（R2-F1）**：逐句核对 HEAD 旧文与 11 条短语，**不是全部覆盖**：
  - `README.md:433` 旧句「或重启 dsh 由 `ensurePreset()` 重渲染」：11 条中无任何短语可命中（整行回归会漏网）。
  - `adapters/dsh/README.md:12` 旧句「（bundle 宿主行 `ensurePreset()` 或 `launch.py --install`）」：无短语命中。
  - `README.md:32` 旧行整行会被 `the inserted row then renders the packaged preset` 命中，但其中的 `The render is idempotent per package version` 与 `(\`lib/index.js\` \`ensurePreset()\`) renders` 单句没有独立短语；只回归这两句时 guard 不会红。
  - `launch.py:637` 的 `ensurePreset()` reads 是幂等键的合法显式面说明，不属于旧叙述，未纳 guard 正确。
- **L63 核实**：HEAD `adapter-manifest.json:63` 的 `git_hooks.evidence` 确实含旧句（"the bundle host row's ensurePreset() re-renders the preset by package version"）；R1 列出的 manifest 旧句只有 32/36，故 R1 漏列属实；R3 已改写，且 `ensurePreset() re-renders` 短语会覆盖 manifest 面。
- 结论：**R1-F1 的“交付面已统一”成立**（旧句已清）；**guard 不是全部旧句的完全超集**（P2，非阻断；建议补 3 条短语/2 条变体）。

### 3.2 (a) guard 正反两面

见 §3.1：负向 11 条 + 正向四面的新措辞断言都存在；`contract` 面另有 `legacyAutoRender` 不得回归与四态词。没有“只查一半”。缺口仅是负向清单的完备性（R2-F1）。

### 3.3 (b) F10 POSIX 测法

`_PATH_IDENTITY_PROBE` 在**独立 Node 子进程**（`subprocess.run`）中运行，导入 `overlay.js` **之前** `Object.defineProperty(process, 'platform', {value:'linux'})`；`FOLD_CASE` 在模块导入时计算，因此能真实进入 POSIX 分支。该重定义只影响子进程，不污染 pytest 进程或其它测试；断言 `/A/skills` 与 `/a/skills` 在 POSIX 下是两个目录（追加后 2 dirs），在 win32/darwin 下折叠为 1。**可接受**。
- 残留风险（P3 讨论，不计 finding）：若未来 Node 把 `process.platform` 变为不可配置，`defineProperty` 会抛错使测试失败（不是静默通过）；更稳的替代是把平台作为参数传给纯路径比较函数（如 `normalizePath(value, platform)`）或导出 `samePath` 供参数化测试。当前实现与证据充分。

### 3.4 (c) gap_note 的 S6 测试

- `test_dsh_doctor.py::test_the_environment_gated_faces_come_from_the_contract` **确实存在**（:531-534），且断言 `S6.credible_face` 含 `unverified_due_to_env`；`test_dsh_doctor.py` 本轮未改（`git diff --exit-code HEAD` = 0，SHA `E44DD2…`）。
- `host-contract.json:1204` 的 `gap_note` 已追加该测试名；K-8 仍 PASS（26 claims / 14 strong）。
- 限制（R2-F3）：K-8 只解析 `guard` 字段，不解析 `gap_note`；因此这是**文档引用**，不是机器 guard。若目标是让该 claim 的 env-gated 面被 machine-check，应把该测试加入 `guard`（无需改测试本身）。本轮不把它当 blocker。

### 3.5 P2-1 幂等测试

见 §2 F2：真实 `lib/index.js` + 真实 payload + 隔离 `DSH_HOME`；首跑断言 `synced` 为真、四个产物文件、目录 mtime 基准；二次断言 `synced=false` 且目录 `st_mtime_ns` 不变。**真实断言，不是只断言返回**。

### 3.6 launch.py 行为零改动

`git diff -U0 -- adapters/dsh/launch.py` 仅两个 hunk：
- `@@ -17,4 +17,5 @@`（模块 docstring 的 `ensurePreset()` 叙述改为 native/显式面）；
- `@@ -30,4 +31,4 @@ Modes:`（`--install/--sync` 的 post-pull 刷新说明）。
两个 hunk 均在模块 docstring；没有语句、常量、函数、输出字符串改动。`test_dsh_adapter.py`/`test_dsh_doctor.py` 全量绿（589）。显式安装语义未削弱。

### 3.7 其余 P3

- `run_cli` 三态 protocol：已测（3813-3822），三态逐一断言。
- `len(warnings)==1`：unreadable（447）、absent（465-466）、declaration 三负例（487-488）已断言；**disabled 与 native happy path 未断言**（R2-F2）。
- POSIX：已测，可接受（§3.3）。
- `locate_dsh_install` 字段：Returns 段已补 `fallback_anchor`/`fallback_anchor_source`/`registry_package`/`protocol`（dsh_compat.py:1264-1273）。
- 无契约零写：已补（test_dsh_contract.py:2302-2307）。

### 3.8 独立复跑

| 项 | 结果 |
| --- | --- |
| 六文件全量（独立） | **589 passed / 119 subtests / 0 failed / 0 skipped**，`PYTEST_EXIT=0`；窗口前后 `status`/`sha` 文件逐字相同（`STATUS_SAME/SHA_SAME=True`）。**墙钟 12261.45s 不可作性能证据**：进程在会话暂停期间被挂起约 3h19m（04:23 恢复后继续），counts/exit 才是事实；Coordinator 的干净计时为 756.84s。 |
| 聚焦 | native bridge **12 passed**；DualPlaneReporting **6 passed**；幂等 **1 passed**；无契约零写 **1 passed**（均 exit 0）。 |
| Check 28w | `check-dsh-boundary` exit 0：K-8 PASS 26 claims（14 strong），Result PASS。 |
| 适配器 | `check-agent-adapters` exit 0：dsh runtime-verified，contracts synchronized。 |
| 快照 | 20 个指纹文件与 `snapshot-r3-before-sha.txt` 逐一相同；`git diff --cached` 空。 |

## 4. Findings

### P2（非阻断，建议本轮或紧随其后修正）

**R2-F1 — guard 负向清单不是 R1 全部旧句的完全超集**

- 位置：`test_dsh_native_bridge.py:532-544`（11 条）与四个面的 `assertNotIn`（:609-617）。
- 缺口（逐句核对）：`README.md:433` 旧句「或重启 dsh 由 `ensurePreset()` 重渲染」；`adapters/dsh/README.md:12` 旧句「bundle 宿主行 `ensurePreset()` 或 `launch.py --install`」；`README.md:32` 旧行中的 `The render is idempotent per package version` 和 `(\`lib/index.js\` \`ensurePreset()\`) renders` 两个分句（整行有短语 7 兜底，单句没有）。
- 现状：live 四个面已无旧句（独立扫描），positive half 也在；所以不是当前文档缺陷，而是“未来只回归某一句”时 guard 可能漏网。Developer 声称「覆盖全部旧句」不成立。
- 建议：补 `由 \`ensurePreset()\` 重渲染`、`bundle 宿主行 \`ensurePreset()\` 或`、`The render is idempotent per package version`、`\`ensurePreset()\`) renders` 等变体；或改为对四个面分别断言“不含 `重渲染`/`renders the packaged preset` 等宽模式”（注意不要误伤显式面的合法措辞）。

### P3（讨论/建议）

**R2-F2 — 「恰好一条 warn」未覆盖 disabled 与 native 零 warn**

- 已覆盖：unreadable（:447）、absent（:465-466）、declaration 三负例（:487-488）。
- 未覆盖：`test_refusals_never_register` 只断言 `disabledMode/disabledCode`（:417-421），`_PROBE` 直接调用 `applyNative` 且 logger 为 no-op，**没有捕获/断言 disabled 态的 row warn 数**；`test_apply_writes_nothing_on_a_native_host` 捕获了 warnings 但未断言为空。R1 的 Reviewer 探针实测 disabled 恰好 1 条、native 0 条，行为正确；建议补两处 `len==1` / `==0`。

**R2-F3 — coverage.entries 的 S6 引用仍是 prose**

- 见 §3.4。测试存在且覆盖 S6 `unverified_due_to_env`；gap_note 已点名，但 `guard` 未加，K-8 不解析 gap_note。若目标是 machine enforcement，把该测试加入 `guard`；若只是文档化来源，现状可接受。

### 接受项（无 finding）

- **(b) F10 POSIX 测法**：可接受（子进程隔离、导入前重定义、断言真实分支）；替代纯函数写法可选。
- **launch.py**：docstring-only 两 hunk，行为零改动（§3.6）。
- **(c) gap_note 测试**：存在且覆盖（§3.4），只需决定是否升级为 guard。
- **adapter-manifest L63**：已确认 R1 漏列（HEAD :63 旧句），R3 已改并由 `ensurePreset() re-renders` 短语覆盖。

## 5. 改动面 / 越界与夹带

- 20 个指纹文件 = 18 批准（16 modified + `lifecycle.js`/`test_dsh_doctor.py` 未改）+ 2 暂停 WIP；逐个 SHA 与 `snapshot-r3-before-sha.txt` 相同。
- `git status --porcelain -uno` = 19 行（16 modified 批准 + 设计文档 + 2 WIP）；`git diff --cached` 空；无 staged/commit/push。
- 相对 R1 的变更仅：两份 README、`adapter-manifest.json`、`launch.py`（docstring）、`host-contract.json`（gap_note/既有 R2 内容）、`dsh_compat.py`（docstring）、四个测试文件；`lib/*` 与 core 投影/清单哈希未变。
- 无批准集外 tracked 产品改动；`test_dsh_doctor.py` 未改；`launch.py` 仅 docstring；无夹带。
- 未跟踪项仅既有 review/scratch/sandbox；无产品文件。
- 设计文档冻结哈希 `122CFB22…`；不计返工面。

## 6. 回归与安全

- 本轮 R3 改动只涉及文档/测试/manifest 描述，未触运行时代码（`lib/*`、`dsh_compat.py` 代码段、`launch.py` 行为均零变化）。
- R1 已复验的四态/零写/真实宿主结果保持有效；本轮未重跑宿主（见 NOT_RUN）。
- 未读写真实 `~/.dsh`；所有命令先设并断言 `DSH_HOME` 在仓库 `.governance/sandboxes/` 内（本轮 sandbox `feat102-code-r2-20261021T010337Z`），Reviewer scratch 在 `.codex-sandbox/FEAT-102/code-r2/`。
- 未发现新的假 PASS/假 FAIL；guard 的 positive/negative 双面存在（缺口见 R2-F1）。

## 7. 命令审计（运行类）

| # | label | UTC 2026-10-21（起→止） | exit | 要点 |
| --- | --- | --- | ---: | --- |
| R1 | pytest 六文件（独立复跑） | 01:03:54.145Z→04:28:04.493Z（墙钟含约 3h19m 会话挂起） | 0 | **589 passed / 119 subtests / 0 failed / 0 skipped**；前后 status/sha 相同；DSH_HOME=sandbox feat102-code-r2-… |
| R2 | 聚焦四段 pytest | 04:22:35.164Z→04:22:37.693Z | 0 | native 12 / compat reporting 6 / 幂等 1 / 无契约 1 |
| R3 | check-dsh-boundary + check-agent-adapters | 04:23:32.801Z→04:23:33.840Z | 0 | K-8 PASS 26 claims（14 strong），Result PASS；adapters OK |
| R4 | guard 覆盖面只读分析（import 测试类 + `git show HEAD:…`） | 约 04:24（只读，无精确 START 打印） | 0 | 逐句核对 11 短语 vs HEAD 旧行；发现 README:433、adapters:12 与 README:32 两个分句未被覆盖 |

只读命令（`git status/diff/show`、`Get-Content`、`Select-String`、`Get-FileHash`）保留在会话记录；未计入上表。

### Reviewer 证据 SHA-256（`.codex-sandbox/FEAT-102/code-r2/`）

| 文件 | SHA-256 |
| --- | --- |
| `pytest-six.log` | `34FE99EC69CFAF907B727CAF2171B71ED08FF0B0D0B20E026C46D6295DBE0204` |
| `pytest-native-bridge.log` | `C849D3E34F587710E2FBD48580B4A3FAD416163C8BEDC2E78E274285A125694C` |
| `pytest-compat-reporting.log` | `8958CC222A213E1EA53A30526529F402479A04FE9A1E819961A21FC6C124FDB3` |
| `pytest-idempotence.log` | `CFBDBEF0BD3FDD642DDFF7CC420647FE8469EE8A364BD12F9E9C0204A6BD8133` |
| `pytest-no-contract.log` | `9C4EF75DA17FBCAA7744CBB02990403961E153B98C18F62B3367B85C5358920D` |
| `check-dsh-boundary.log` | `540F753E765680C035CB2CADA6D3C1922B51E3F439616A93BAFA9712DA6C0423` |
| `check-agent-adapters.log` | `571C24E2E517215B6818426F0A47F66D94F1B321BFC5110197ADDEE2801EBFA0` |
| `status-before.txt` / `status-after.txt` | `1192499AC26943A421D23976B245019974A52BB3CE09C91B86E150EB62DB480C`（两者相同） |
| `sha-before.txt` / `sha-after.txt` | `3203727E743FCD058550297CD0C64AB8FF6FBE2F2AD45455FF7028C264D40657`（两者相同） |

## 8. NOT_RUN（未跑 ≠ 通过）

- 真实 dsh 0.2.1-rc.2 宿主会话：本轮未重跑（R3 只改文档/测试/manifest 描述；R1 的隔离宿主证据保持，不冒充新跑）。
- `check-projection-sync`：本轮未重跑（投影/清单哈希未变；R1 的 28 mirrors/唯一 FIX-457 漂移结论保持）。
- 0.1.x 宿主、多 profile / desktop / headless：NOT_RUN。
- `launch.py --install/--smoke` 运行：未跑（仅 docstring；显式面不在本轮测试面）。
- 完整 `check-governance` 全量引擎：未跑；只跑六文件 + Check 28w + check-agent-adapters。
- EVD-2115/2116 的 `fallback=1` 原隔离环境复现：NOT_RUN（R0/R1 结论保持；设计 §16.4.1/EVD-2119 已披露）。

## 9. 硬门槛自检

1. 未修改产品代码/测试/治理记录/前轮报告；仅写本报告 + Reviewer scratch + 隔离 sandbox。未 stage/commit/push。✓
2. 每条结论有实际运行/读取证据（文件:行号、探针、日志哈希）；未把 NOT_RUN 写成通过；墙钟异常（会话挂起）如实披露。✓
3. 全部运行在仓库内隔离 `DSH_HOME` 完成（前缀断言）；未读写真实 `~/.dsh`。✓
4. 设计合同按冻结哈希 `122CFB22…` 核对；R1 报告按 `6AEC2029…` 承接。✓
