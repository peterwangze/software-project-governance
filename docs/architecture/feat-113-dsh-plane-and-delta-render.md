# FEAT-113 DSH 双平面探测与 Δ 派生渲染设计

> 状态：Accepted（2026-11-07 评审通过；裁决见 DEC-386，`.governance/decision-log.md` 末尾）
> 日期：2026-11-07
> 作者：Architect
> 任务：FEAT-113（`.governance/plan-tracker.md:74`，5 项范围；FIX-483 明确排除，`plan-tracker.md:75`）
> 决策依据：DEC-385①（目录面 = Δ 合并渲染）与 DEC-385②（plane = 增加 asar/桌面面探测），`.governance/decision-log.md:180`；DEC-366②（native 面是唯一交付面），`.governance/decision-log.md` 对应条目；RISK-072（高，owner Coordinator），`.governance/risk-log.md:61`
> 事实输入：本机 0.2.2-rc.1 桌面 asar 面 + 0.2.1-rc.2 npm CLI 面 + 用户根 29 行残留，全部只读；实验写入 `$env:TEMP\feat113-*`
> 写作约束：本文只做设计，不修改任何产品代码、测试、契约或 `.governance/` 记录；文中每个"现状行为"断言都带 `path:line`；未验证项显式标 **未验证**

---

## 0. 决策摘要（先读这一段）

| 编号 | 决策 | 一行结论 | 主要落点 | 硬失败语义 |
| --- | --- | --- | --- | --- |
| D1 | 平面身份 | 用 **asar 头部索引**（零解包）+ 三层显式来源（`DSH_INSTALL_DIR` / 新增 `DSH_DESKTOP_APP_DIR` / 有界祖先进程探测）识别桌面面，平面身份对象进全部证据 | `dsh_asar.py`(新)、`dsh_plane.py`(新)、`dsh_compat.py:1239`、`dsh_doctor.py:609` | 显式指定但不可用 → `PLANE_UNUSABLE`，裁决 NOT_RUN（绝不静默回退） |
| D2 | 行级覆盖 | 行级结果成为一等公民：每条 composition / 每个行各自记 PASS / FAIL / UNVERIFIED(原因码) / SKIPPED；`!!js` 求值使用**契约声明的 loader ctx 桩面** | `dsh_compat.py:606-1083, 1802-1975` | 未声明 ctx 成员 → 行 FAIL（漂移必须响亮）；oracle 缺失 → 只降级依赖它的行 |
| D3 | 有界发现 | `os.scandir` 前剪枝遍历（跳过 reparse point、`(dev,ino)` 去重、深度/条目/时间上限）+ 默认根收窄到包载荷目录；越界只记 UNVERIFIED 不 FAIL | `dsh_walk.py`(新)、`dsh_compat.py:1426-1445` | 崩溃/不可读 → 该根 `UNREADABLE`，裁决按剩余证据分级 |
| D4 | Δ 合并渲染 | 模板退场，治理面收缩为 **两行 overlay 片段**；安装期从**本机 plane 的 base preset** 文本级派生宿主行，与 overlay 合并；派生不到拒装 | `agent-presets/governance/overlay.cordis.yml`(新)、`composition_merge.py`(新)、`launch.py:452-740` | 任何形状漂移 → exit 2（拒绝安装，绝不猜） |
| D5 | 残留检测 | 安装期写 `render-provenance.json`（含平面身份、base 行集、输出行集）；doctor S1 离线比对实际行集，残留/缺失/版本不符 → FAIL；文案全面对齐 DEC-366② | `provenance.py`(新)、`dsh_doctor.py:406-500` | provenance 缺失 → `UNVERIFIED(PROVENANCE_ABSENT)`，一个版本宽限 |
| D6 | 契约收口 | 契约升 v2：废弃 `own.preset.template` / `host.rows`(29 行)，新增 `own.overlay`、`own.native.base_preset`、`host.planes`、`host.home.discovery`、`host.apis.loader_ctx`、`own.preset.render_provenance`；28w K-3 改为"模板不得携带宿主行"的静态守卫 | `host-contract.json`、`dsh_contract.py:126-186`、`dsh_boundary.py:706-765` | 缺键/未知键 → `ContractMalformed` / `ContractSchemaUnknown`（不许降级） |
| D7 | 可注入接缝 | 全部宿主交互经端口注入：`env`、`fs`、`process`、`runner`、`base-provider`；纯函数承担合并/裁剪/比对，fake-host 单测覆盖六类失败 | 新模块 + `tests/test_dsh_*.py` | 接缝不得读取环境/磁盘（构造参数唯一来源） |

目标版本分两批（用户裁决，DEC-386③）：**0.99.1 = FIX-484 + S0 + S1 + S2**（门与 `test_dsh_*` 套件收敛、报告平面身份、行级覆盖不再整体塌陷），**0.100.0 = S3…S9**（Δ 渲染退场模板、残留可判、28w 收口）。产品代码合计约 **2,170 LOC**（新模块 ~900，改造 ~1,270），测试约 **1,600 LOC**；切片 **10 个（S0–S9，§10）**。

---

## 1. 背景与事实基线

### 1.1 为什么有这件事

`software-project-governance` 的 dsh 交付有两个面：

- **native 面**（唯一受支持的交付面，DEC-366②）：`lib/index.js` 的 `apply()` 通过 `ctx.agentPresets.register` 注册结构化 definition，`lib/dsh-native/overlay.js:74` 的 `deriveDefinition()` 从宿主 base preset 的行派生（`structuredClone` + 追加 persona 正文 + 追加两个 skill 根）。
- **旧路目录面**：把包内 `agent-presets/governance/agent.cordis.yml.template`（258 行、14,830 B，`agent-presets/governance/agent.cordis.yml.template:1-258`）渲染成 `${DSH_HOME}/.agent-presets/governance/agent.cordis.yml`。今天该模板**冻结了 29 行宿主组合**（`dsh_boundary.py:120-122` 的 `EXPECTED_ROWS_TOP_LEVEL=16 / NESTED=13`），0.2.2 上已经漂移：一条死行（`tool-subagent-list-agents` 引用的 `@deepseek-ai/dsh-tool-subagent-control/list-agents` 在 0.2.2 已不存在）、与 base preset 行集相比缺 6 条宿主行、多出 **13 条本仓自加行**（恰为模板全部嵌套行；其中 12 行引用的包仍在，属"治理面额外启用的能力面"而非死行，清单见 §6.2.1.1；§1.3 F5）。

同时 28v（Check 28 变体）的平面探测 `locate_dsh_install()`（`skills/software-project-governance/infra/dsh_compat.py:1239-1421`）只看**磁盘目录 + profile 提升树 + PATH**，**完全看不到 asar 桌面面**。本机运行的是 `D:\app\dsh\resources\app.asar` 内的 0.2.2-rc.1，而探测报告的是 0.2.1-rc.2 的 npm CLI 面（F8）。结果是：28v 校验了错误的平面，doctor S1 对含死行的 29 行残留报 PASS（F10）。RISK-072 的闭包条件"0.2.2 真实平面行级全绿 + 用户根残留漂移可检出"正是指这两件事。

DEC-385① 已把目录面定为 **Δ 合并渲染**：模板只保留治理自有内容（persona 正文 + 2 个 skill 根 + 元数据），宿主行安装期从**本机 base preset** 派生后合并；派生不到 → 拒装，exit 2，禁止猜。DEC-385② 已把 plane 定为 **asar/桌面面探测**（已知安装路径 + 显式环境变量；读 asar 头索引，不解包），28v 必须报告平面身份与宿主版本。

### 1.2 四个平面的事实（只读）

| 平面 | 锚点 | 版本 | 当前探测状态 | 证据 |
| --- | --- | --- | --- | --- |
| asar-desktop | `D:\app\dsh\resources\app.asar`（内 `dsh/node_modules/@deepseek-ai/dsh/package.json`） | 0.2.2-rc.1 | **不可见**：`locate_dsh_install()` 无 asar 分支 | 实测（§1.3 F1/F2/F8） |
| npm-cli | `%APPDATA%\npm\node_modules\@deepseek-ai\dsh` | 0.2.1-rc.2 | 被选中（PATH `dsh` 分支，`dsh_compat.py:1378-1384`） | 实测 |
| profile | `${DSH_HOME}/profiles`（`_profile_planes()`，`dsh_compat.py:1200-1238`） | 0.2.1-rc.2 | 选中；**缺** `dsh-agent-preset-registry`，oracle 从提升树解析 | 实测 |
| user-preset | `${DSH_HOME}/.agent-presets/governance/agent.cordis.yml` | 0.99.0 渲染产物 | doctor S1 PASS（含死行） | 实测（F10/F11） |

### 1.3 已验证事实（本机实测；命令见 §1.5）

| 编号 | 事实 | 证据/数值 |
| --- | --- | --- |
| F1 | asar 头部布局可只读索引：`[4:8]`=payload size、`[12:16]`=JSON 字节数、JSON 从 16 起（截到最后一个 `}`）、内容基址 `8+payload`、`offset` 为字符串需 `int()` | 成功从 `app.asar` 读出 `dsh/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml`，6,858 B / 22 个顶层行（`.tmp-compat-evidence/rowdiff.py` 与临时脚本） |
| F2 | 只有 `Electron-as-node` 能读 asar 内模块：`D:\app\dsh\DeepSeek Harness.exe` + `ELECTRON_RUN_AS_NODE=1`；plain node `existsSync` 为 false | `derive022.mjs` 在 asar 面派生成功（`derive022.json`: `ok:true, baseRows:22, derivedRows:22, failures:[]`） |
| F3 | 冻结 29 行模板在 0.2.2 真实平面 **FAIL**：1 条 issue，死行 `tool-subagent-list-agents` 的模块 `@deepseek-ai/dsh-tool-subagent-control/list-agents` 解析不到；coverage `rows_enabled 23 / verified 19 / unverified 3 (NO_SCHEMA)` | `.tmp-compat-evidence/compat022.json`（FAIL） |
| F4 | native 派生（0.2.2 base）零失败，`personaPrefixBytes 2808`、`skillRoots` 2 条、`rowsWithoutIds 0`、`disabledRows [tool-plugin-market]` | `.tmp-compat-evidence/derive022.json` |
| F5 | 行差（协调者 2026-11-07 复核并更正本稿首版口径）：以 asar 0.2.2 的 **base preset 行集（22 行）**为基准，模板 29 行中 **13 行为本仓独有**（恰为模板全部嵌套行：`plan-mode`、`compaction-basic`、`command-compact`、`tool-result-pruner`、`tool-subagent-control`、`tool-subagent-list-agents`、`tool-subagent`、`tool-subagent-fork`、`tool-subagent-codex`、`tool-subagent-claude-code`、`workflow-ptc`、`tool-workflow`、`tool-ralph`），**6 行为 base 独有**（`command-goal`、`present`、`time-context`、`tool-plugin-manager`、`tool-plugin-market`、`tool-schedule`），其余 16 行共有。对 asar 内 331 个 `@deepseek-ai/*` 包名做集合判定：13 行中**仅** `tool-subagent-list-agents` 的子路径 `@deepseek-ai/dsh-tool-subagent-control/list-agents` 已被 exports 删除（真死行），其余 12 行引用的包**全部仍在** → 它们是**治理面自加的启用面**（标准 preset 从未启用），不是死行；"包还在"≠"功能等价"，逐行能力面见 §6.2.1.1 | 协调者实测（2026-11-07）；模板行 `agent.cordis.yml.template:133-240`；本稿首版"7 宿主独有 / 3 治理独有"系只比对部分行所致，更正记录见 §15 |
| F6 | Δ 原型（22 行 base 原文 + persona 前缀替换 + `customSkillDirs` 注入）在 0.2.2 面 **PASS**（删掉 ctx 依赖行后 `issues: []`，coverage `25/20/5`，`unreadable 0`） | 临时目录 `%TEMP%\feat113-merge\agent.cordis.yml`（145 行 / 8,490 B）+ 真实 asar probe |
| F7 | 同一 Δ 产物不删行时 **唯一失败** 是 `row "tool-plugin-manager" ... disabled !!js expression threw: TypeError: ctx.get is not a function` —— 探测桩的 loader ctx 缺 `ctx.get`（`dsh_compat.py:1071` 的 `{baseUrl, process, console}`），不是产物缺陷 | 同上两次 probe 对比 |
| F8 | `locate_dsh_install({DSH_HOME})` 报告 profile 面 0.2.1-rc.2，`other_planes` 列 desktop/web；asar 面不在候选里；`registry_package` 来自 CLI 回退 | `.tmp-compat-evidence/doctor-default.json`（未逐字段复核版本字符串，标 **待复核**） |
| F9 | `discover_compositions()` 无界：Windows junction `.governance/sandboxes/*/profiles/web/node_modules/...` → 仓库根形成自环；有界扫描实测 10.36 s、8 条 composition（7 条 sandbox 副本 + 1 条产品模板）、`skipped_reparse=336` | `.tmp-compat-evidence/rowdiff.py` 附带测量 + `dsh_compat.py:1426-1445` |
| F14 | 自指环**不只卡 28v**：以仓库根为 root 的单元测试同样纯 Python 自旋 —— `python -m unittest discover -s skills/software-project-governance/infra/tests -p 'test_dsh_*.py'` 跑 813 s CPU、无任何 child 进程，人工终止；`.gitignore` 忽略 `.governance/`，junction 由历次派发生成且评审不可见 → **门与测试套件同时自中毒** | 协调者 2026-11-07 实测（本会话复现口径） |
| F10 | doctor S1 对 29 行残留（含死行）判 PASS：只校验目录/标记/版本，不校验行集 | `dsh_doctor.py:406-500`（S1 无行集逻辑） |
| F11 | 用户根残留 `C:\Users\peter\.dsh\.agent-presets\governance\agent.cordis.yml` 为 29 行、含死行（真实环境，只读证据） | 只读 |
| F12 | 模板 persona 正文与 `persona.md.template` **逐行相同**；唯一差异是部署句：模板硬编码 `You are a coding agent powered by the {{model}} model, running on the DeepSeek Harness. Your working directory is {{cwd}}.`（`agent.cordis.yml.template:49`），而 0.2.2 base preset 的前缀是短句 `You are a coding agent powered by the {{model}} model.`（asar 内 `standard.patch.yml:14`） | 两文件逐行对比 + asar 读取 |
| F13 | Δ 原型的 persona prefix **字节数 2808 == native `personaPrefixBytes` 2808**（同 base、同 body，base 前缀 + `\n\n` + body + `\n`），双面无损可字节一致 | F4 的 2808 与合并产物重新提取值相同 |

> F12/F13 是 D4 的关键依据：**正文已经同源**，治理面迁移只需把"部署句"从模板里删掉，改由 base 前缀提供；native 与旧路面因此在同一 base 上产出一致 prefix。
>
> F5 口径说明：22 行基准是 base preset 的 `config.plugins` 行集；用户根冻结组合的 33 行另含 1 行 `preset-standard`（挂载 base preset 的包装行，不属于 base 行集），故"模板 vs 33 行组合"会得到 7 条宿主独有。两个数字不矛盾，本文后续一律用 **13 / 6 / 16** 这组以 base 行集为基准的口径。

### 1.4 开放问题（O4/O5/O7 已闭合或已裁决；O1/O2/O3/O6 仍**未验证**，实现前必须闭合）

| 编号 | 问题 | 影响 | 闭合方式 |
| --- | --- | --- | --- |
| O1 | 祖先进程 exe 目录探测（ctypes Toolhelp32）在本机未实现、未测；杀软/权限行为未知 | D1 第三层探测 | 先实现为可注入端口 + 开关 `DSH_PLANE_PROBE_PROCESS=0/1`，本机实测后定默认 |
| O2 | macOS/Linux 桌面布局（`.app/Contents/Resources/app.asar` 等）未测 | D1 声明面 | 契约只声明 Windows 实测；其余标 `UNVERIFIED(PLATFORM)` |
| O3 | 宿主 presets 目录对未知文件（`render-provenance.json`）的宽容度未在 0.2.2 上直接验证 | D5 落点 | 先例：同目录已有 `preset.yml` / `.dsh-bundle-version` / `skill-root.txt` 被接受（`own.preset` 声明），据此判低风险；S5 用真实平面冒烟确认 |
| O4 | ~~治理独有行去留（首版误记为 3 条）~~ → **已裁决（DEC-386②）**：13 条本仓独有行**全部**随模板退场退休；退场后旧路面 = 纯 Δ（base 行 + 治理两行），与 native 面同构；需要者另立任务在 native 面实现，不回填旧路面 | D4 能力面 | 已入账 `.governance/decision-log.md`（DEC-386）；逐行清单 §6.2.1.1 |
| O5 | ~~0.2.1 CLI 磁盘面是否也有 base patch~~ → **已闭合（2026-11-07 实测）**：0.2.1 npm CLI 面 `C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-web-app\presets\standard.patch.yml` = 6,799 B / 22 行，id 序列与 0.2.2 asar 的 6,858 B / 22 行**逐项相同**；同目录另有 `minimal.patch.yml`(4 行)、`ptc.patch.yml`(23 行)、`cordis.patch.yml`(23 行) | D4 派生面覆盖 | 已闭合；派生在**双平面（asar 桌面面 + 磁盘 node_modules 面）**成立，路径形状一致，见 §6.2.2 |
| O6 | `DSH_PROFILE_DIR` 是否作为 identification-only 事实进契约 | D1 证据稳定性 | S1 实现时按"只读识别、不写"入契约 `host.install.profile_env` |
| O7 | ~~删除 `host.rows`（29 行清单）需 schema v2 与协调者批准~~ → **已裁决（DEC-386②）**：删 `host.rows` + `own.preset.template`，`SUPPORTED_SCHEMA_VERSIONS` 1→2（S0 只加 `deprecated_in: 2` 标注，物理删除并入 S7 退场原子切片），模板快照归档 `docs/` 作历史 | D6 | 已入账 `.governance/decision-log.md`（DEC-386）；删除时序见 §10 S0/S7 |

### 1.5 复现命令（临时环境；禁止写真实 `C:\Users\peter\.dsh`）

```powershell
# 1) asar 身份与 base preset（纯 Python 头索引，零解包）
$py = @'
import json
from pathlib import Path
ASAR = Path(r"D:\app\dsh\resources\app.asar")
with open(ASAR, "rb") as f:
    head = f.read(16)
    payload = int.from_bytes(head[4:8], "little")
    n = int.from_bytes(head[12:16], "little")
    raw = f.read(n).decode("utf-8")
    idx = json.loads(raw[:raw.rindex("}") + 1])
    node = idx
    for part in "dsh/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml".split("/"):
        node = node["files"][part]
    f.seek(8 + payload + int(node["offset"]))
    print(f.read(int(node["size"])).decode("utf-8")[:2000])
'@
$py | python -

# 2) 真实平面 probe（Electron-as-node + DSH_HOME 重定向）
$env:DSH_HOME = "$env:TEMP\feat113-home"; $env:ELECTRON_RUN_AS_NODE = "1"
# request.json 见 dsh_compat._probe_request() 的字段；sc 见 _render_probe_script()
& "D:\app\dsh\DeepSeek Harness.exe" --input-type=module --eval $script < request.json
```

---

## 2. 依赖点清单（宿主面依赖矩阵）

列含义：**读者** = 今天读取该事实的代码位置；**今天的失败模式** = 不满足时会发生什么；**契约键** = 该事实在 `adapters/dsh/host-contract.json` 的声明位置（`——` 表示今天根本没有声明，属新增）；**校验点** = 哪个治理检查消费它。

| # | 依赖点 | 读者（path:line） | 今天的失败模式 | 契约键 | 校验点 |
| --- | --- | --- | --- | --- | --- |
| 1 | asar 容器布局（头偏移/内容基址） | **无读者**（盲区） | 桌面面当不存在；28v 校验错的平面（F8） | `host.planes.asar.*`（新） | K-14（新）/doctor S3 |
| 2 | Electron-as-node runner（`process.execPath` + `ELECTRON_RUN_AS_NODE`） | `_run_probe()` 依赖**环境里已有的**变量，`dsh_compat.py:1624-1637` | 若无该环境变量，plain node 读不到 asar → 永远 NOT_RUN | `host.planes.asar.runner`（新） | K-14/证据 |
| 3 | `<plane>/@deepseek-ai/dsh/package.json`（版本锚） | `locate_dsh_install()`，`dsh_compat.py:1239-1421`（`anchor_rel` 来自 `host.install.anchor_rel`） | 只在磁盘目录找 → asar 面不可见；版本证据取到 CLI 的 0.2.1 | `host.install.anchor_rel` | K-7 |
| 4 | `dsh-agent-preset-registry` 是否可解析 | `locate_dsh_install()` 的 registry 判定，`dsh_compat.py:1395-1408` | profile 面缺包 → `registry_package` 回退 CLI 值，证据张冠李戴 | `own.native.registry_row_name` | K-7 |
| 5 | `web-app/presets/<base_preset_id>.patch.yml` | **无读者**（旧路面冻结模板；native 由宿主内部读） | 旧路面没有 base 来源 → 只能冻结 29 行 → 必然漂移（F3/F5） | `own.native.base_preset`（新） | K-3′/D4 拒装 |
| 6 | base 行选择（`name == base_row_name ∧ config.id == base_preset_id`） | `lib/dsh-native/source.js:95`（`locateBase`）；Python 侧无对应 | 旧路面无法定位 base 行 → 无法合并 | `own.native.base_row_name`、`base_preset_id_default`（`host-contract.json:812`） | K-3′/parity |
| 7 | persona 行存在/唯一/未禁用、前缀形状 | `lib/dsh-native/overlay.js:91-120` | 旧路面缺校验；形状变化（引号/块标量）会被手工模板掩盖 | `own.native.persona_row_name`、`own.render.persona_prefix`（新） | 拒装码/parity |
| 8 | skill 行存在/唯一/未禁用、`customSkillDirs` 形状 | `lib/dsh-native/overlay.js:125-155`；Python `launch.py:1008-1050, 1159` | 形状不支持时旧路面静默产出错行 | `own.native.skill_row_name`、`own.render.custom_skill_dirs_shape`（`:835`） | K-4/拒装 |
| 9 | `ctx.agentPresets.register` 契约 | `lib/dsh-native/lifecycle.js:43-50` | 宿主无该服务 → `HOST_NO_AGENT_PRESETS`（warn-only） | `own.native.registration` | K-1/K-2 |
| 10 | `resolveConfig`（行配置 schema 校验） | `PROBE_SCRIPT`，`dsh_compat.py:771` | 缺包时 `fail()` 让整份报告塌成 NOT_RUN | `host.apis.cordis` | K-8/D2 |
| 11 | `entryListSchema`（`!!js` tag） | `PROBE_SCRIPT`，`dsh_compat.py:1058` | 缺包 → YAML 解析失败 → 整份 NOT_RUN | `host.apis.cordis-plugin-include` | K-8 |
| 12 | `isJsExpr` / `evaluate(ctx, expr)` | `PROBE_SCRIPT` 的 `walk()`，`dsh_compat.py:784-960` | **`ctx.get` 不在桩面 → TypeError → 行 FAIL**（F7） | `host.apis.cordis-plugin-loader` + `host.apis.loader_ctx`（新） | K-8/D2 |
| 13 | `js-yaml.load`（`schema: entryListSchema`） | `PROBE_SCRIPT`，`dsh_compat.py:1058` | 缺包 → NOT_RUN | `host.apis.js-yaml` | K-8 |
| 14 | `${DSH_HOME}` 与写侧回退 `<home>/.dsh` | `launch.py:379`（`dsh_home()`）、`:837`（`real_dsh_home()`）；`dsh_doctor.py:193` | 写错真实 home 即生产事故；probe 侧又会回退 | `host.env`（`env.home_var`、`write_side`） | K-10/S1/smoke |
| 15 | `DSH_INSTALL_DIR` / `DSH_HARNESS_NODE_MODULES` | `dsh_compat.py:1304-1318` | 只支持磁盘 node_modules；无法指向 app 目录/asar | `host.install.env_overrides`（`:51`） | K-7 |
| 16 | 新增 `DSH_DESKTOP_APP_DIR`（桌面 app 目录） | **无** | 桌面面无法被显式指定（只能靠猜测） | `host.planes.env.desktop_app_dir`（新） | K-14 |
| 17 | 新增 `DSH_PROFILE_DIR` | **无**（仅有 profiles 目录扫描，`dsh_compat.py:1200`） | 多 profile 时选中不确定 | `host.install.profile_env`（新，见 O6） | S3 证据 |
| 18 | PATH 中的 `dsh` shim | `dsh_compat.py:1378-1384` | 选中 npm CLI 0.2.1（F8），与真实宿主不一致 | `host.install.env_overrides` | K-7 |
| 19 | `profiles/*` 提升 `node_modules` | `_profile_planes()`，`dsh_compat.py:1200-1238` | 可执行但无 registry 行；版本 0.2.1 | `host.install.profiles_dir_name`（`:55`） | S3 证据 |
| 20 | `resources/runtime/versions.json`（node 版本） | **无** | 平面运行时版本不进证据，无法解释 probe 差异 | `host.planes.asar.runtime`（新） | K-14 |
| 21 | `.agent-presets/<id>/agent.cordis.yml` 路径与内容 | `launch.py:289, 403`；`dsh_doctor.py:419-421` | 目录/标记/版本对，但行集陈旧（F10/F11） | `host.home.user_preset_dir`、`own.preset.payload_dir` | S1（D5） |
| 22 | composition 发现 glob | `discover_compositions()`，`dsh_compat.py:1426-1445`；键 `host-contract.json:91` | 无界 + 事后过滤 → junction 自环（F9/F14）：28v 卡死、`test_dsh_*` 套件 813 s 自旋 | `host.home.composition_globs` → 新增 `discovery` | K-8/D3 |
| 23 | 模板路径 `own.preset.template` | `launch.py:281`；`lib/index.js:250-265`；键 `host-contract.json:803` | 退场后 `agent.cordis.yml.template` 的 224 处文本命中（含文档/测试/历史评审）全部失效 | `own.preset.template` → `own.overlay` | K-3′/K-4 |
| 24 | token 集合（3 个 `__GOVERNANCE_*__`） | `launch.py:297-304`；`dsh_boundary.py:820`（K-4） | 新增 persona body token 需同步（4 个） | `own.render.tokens` | K-4 |
| 25 | 换行策略 `lf` | `launch.py:507-525` | CRLF 混入 → 宿主按字面吃进 prefix | `own.render.newline_policy` | K-4/测试 |
| 26 | 残留 token 扫描 | `launch.py:319-336`（`leftovers()`） | 未替换 token 被写进真实预设 | `own.render.leftover_scan`（`:834`） | K-4 |
| 27 | `customSkillDirs` 渲染形状 | `launch.py:1008-1050, 1055-1157` | 形状不合契约时拒装；旧模板手工排版掩盖 | `own.render.custom_skill_dirs_shape`（`:835`） | K-4 |
| 28 | `preset.yml` 元数据 | `launch.py:285`；`dsh_doctor.py:453-462` | 名称/版本不符 → S1 FAIL | `own.preset.metadata` | S1 |
| 29 | 版本标记 `.dsh-bundle-version` | `launch.py:434-450`；`dsh_doctor.py:463-471` | 幂等判据；陈旧标记 → S1 FAIL | `own.preset.version_marker` | S1 |
| 30 | 写策略 `staging+rename, no-lock` | `launch.py:556-626`；`lib/index.js:568-601` | 崩溃半写；锁缺失下的并发覆盖 | `own.preset.write_policy` | 测试/dry-run |
| 31 | 行契约 13 字段（insert 必带 id 等） | `dsh_boundary.py:1393-1505`（K-10） | 合并产物若破坏不变式 → 静态检查失效 | `host.row_contract` | K-10 |
| 32 | `--smoke` 加载面（catalog + `/governance`） | `launch.py:1467` | 平面无关；但 Δ 后需验证 fragment 渲染仍可加载 | `own.render` | smoke |
| 33 | doctor S1/S2 的修复文案 | `dsh_doctor.py:430, 443-445, 458-460, 468-470` | **文案要求"重启 dsh 让 bundle host row 渲染预设"，与 DEC-366② 矛盾** | `own.native.legacy_policy` | 文案测试 |
| 34 | coverage 原因码（`NO_SCHEMA` 等） | `dsh_compat.py:136, 190`（`FINDING_KINDS`/`UNVERIFIED_KINDS`） | `NO_SCHEMA` 未被 doctor 声明 → 全绿口径含糊 | `coverage.entries`（`dsh_contract.py:179`） | K-8 |
| 35 | `host.rows`（29 行清单） | `dsh_boundary.py:706-765`（`template_row_mismatches`） | 模板退场后该清单无对象可比，成为第二个漂移源 | `host.rows`（`dsh_contract.py:126`）→ 降级 `evidence` | K-3′ |

### 2.1 归纳：今天坏在哪（五个失效模式）

1. **平面盲区**（#1/#2/#16）：asar 面无法被识别，28v/doctor 的证据指向错误的宿主版本。
2. **冻结组合**（#5/#6/#35）：旧路面把宿主行固化进模板，宿主演进即漂移，且漂移只能靠人看。
3. **证据塌陷**（#10-#13）：probe 里任一 API 缺失就 `fail()` 整份报告 → 全或无，无法区分"宿主漂移"与"探测环境不全"。
4. **无界发现**（#22）：junction 自环 + sandbox 副本，扫描时间与结果都不可控。
5. **残留不可见**（#21/#33）：S1 只看目录/标记/版本，29 行残留（含死行）报 PASS；修复文案还指向已废弃的自动渲染路径。

### 2.2 契约缺口（D6 一次性补齐）

`own.overlay`（新）、`own.native.base_preset`（新）、`own.preset.render_provenance`（新）、`host.planes`（新）、`host.home.discovery`（新）、`host.apis.loader_ctx`（新）、`own.render.persona_prefix`（新，声明"保留 base 前缀 + 空行 + body + 单换行"）；废弃 `own.preset.template`、`host.rows`、`own.render.tokens` 中不再使用的项。

---

## 3. D1 平面身份：asar/桌面面探测

### 3.1 现状（读取点）

- 候选来源只有四个：显式 env（`DSH_INSTALL_DIR` / `DSH_HARNESS_NODE_MODULES`，`dsh_compat.py:1304-1318`）、profile 提升树（`:1200`）、PATH `dsh`（`:1378-1384`）、`fallback_anchor`（`:1390-1394`）；`other_planes` 只是披露（`:1410-1421`）。
- 判据是"目录里有 `@deepseek-ai/dsh/package.json`"，**没有 asar 分支**；因此 0.2.2 桌面面永远不在候选里。

### 3.2 决策

**D1：新增 asar/桌面面为第一类平面，按显式优先、逐层可注入的顺序解析，身份对象进全部证据。**

解析顺序（写入契约 `host.planes.precedence`，顺序即契约）：

1. `DSH_INSTALL_DIR`：接受 ①app 目录（含 `resources/app.asar`）②`.asar` 文件路径 ③asar 内前缀目录（`<asar>\\dsh\\node_modules`）④磁盘 `node_modules` 目录。**显式给出但不可用 → 不静默回退**，`PLANE_EXPLICIT_UNUSABLE`。
2. `DSH_DESKTOP_APP_DIR`（新）：桌面安装目录（含 `resources\app.asar`）。
3. 祖先进程探测（可注入端口 `ProcessPort`；默认 `DSH_PLANE_PROBE_PROCESS=1` 仅用于 doctor/28v 证据，`--install` 默认关闭以保持显式/离线）：枚举当前进程祖先（最多 4 层），读 `ExecutablePath`，其目录下 `resources\app.asar` 存在即候选；不写、不 spawn。
4. `DSH_HARNESS_NODE_MODULES`：磁盘 node_modules（含 `@deepseek-ai/dsh/package.json`）。
5. `DSH_PROFILE_DIR`（显式）否则 `${DSH_HOME}/profiles/*`（按 mtime）：profile 提升树。
6. PATH `dsh` shim：**最后**，且身份里标 `informational: true`（今天它反而被优先选中，F8）。

#### 身份对象（进 report / evidence / doctor / provenance）

```json
{
  "schema": "dsh-plane/1",
  "kind": "asar-desktop | disk-node-modules | profile | path-shim",
  "source": "env:DSH_INSTALL_DIR | env:DSH_DESKTOP_APP_DIR | process-ancestor | env:DSH_HARNESS_NODE_MODULES | home-profile | path",
  "anchor": "D:/app/dsh/resources/app.asar",
  "resolution_anchor": "D:/app/dsh/resources/app.asar/dsh/node_modules/@deepseek-ai/dsh/package.json",
  "node_modules": "D:/app/dsh/resources/app.asar/dsh/node_modules",
  "runner": {
    "program": "D:/app/dsh/DeepSeek Harness.exe",
    "electron_run_as_node": true,
    "module_flag": "--input-type=module",
    "source": "asar-sibling-executable"
  },
  "dsh_version": "0.2.2-rc.1",
  "runtime": {"version": "24.21.0", "source": "resources/runtime/versions.json"},
  "asar": {
    "path": "D:/app/dsh/resources/app.asar",
    "size": 0,
    "header_sha256": "…",
    "entry_count": 0,
    "content_base": 0,
    "unpacked_present": false
  },
  "profile": {"dir": "C:/Users/<user>/.dsh/profiles/desktop", "bundles": ["…"]}
}
```

`runner` 是**执行面**事实：asar 平面必须 `runner.electron_run_as_node=true` 且由探测显式设置 `ELECTRON_RUN_AS_NODE=1`（今天靠环境里恰好存在，`dsh_compat.py:1624`）；磁盘平面用 PATH node；两者都不采用"环境里碰巧有"的隐式来源。

### 3.3 asar 读取（`dsh_asar.py`，纯 stdlib，零解包）

- `AsarReader(path, fs)`：读 16 字节头；校验 `[0:4]==4`；`payload=int.from_bytes([4:8])`；`json_len=int.from_bytes([12:16])`；JSON = 从 16 起 `json_len` 字节，trim 到最后一个 `}`（尾随对齐填充）；内容基址 `8+payload`。
- `entry(rel) -> {offset:int(字符串), size:int, link?, unpacked?}`；路径按 `/` 分段，`.`/`..` 拒绝，逐段命中索引，`link` 解析最多 8 跳并记 `link_chain`（环 → `ASAR_LINK_CYCLE`）。
- `read_bytes(rel)`：`offset/size` 必须落在 `[content_base, file_size]` 内，否则 `ASAR_ENTRY_OUT_OF_RANGE`；`unpacked: true` 的条目从 `<asar>.unpacked/<rel>` 读 —— `app.asar.unpacked` **不能**当作平面（缺索引），但可以作为单条目读取来源。
- 错误码：`ASAR_HEADER_TRUNCATED`、`ASAR_MAGIC_INVALID`、`ASAR_JSON_INVALID`、`ASAR_ENTRY_MISSING`、`ASAR_ENTRY_OUT_OF_RANGE`、`ASAR_LINK_CYCLE`、`ASAR_ENTRY_CORRUPT`（S1 R1 新增：`size>0` 且无 `offset`/`link` 的畸形 file 节点——bounds 计算前拒绝，不落 TypeError；`size=0` 无 offset 合法读空）。
- `identity()`：`{path,size,header_sha256(JSON 字节),entry_count(有界计数,上限 200k),content_base,unpacked_present}`，**不含 mtime**（避免证据抖动）。

### 3.4 语义与降级

- 平面身份不可读：显式来源 → 裁决 `NOT_RUN` + `PLANE_UNUSABLE`（附原因码）；隐式来源（profile/PATH）→ 跳过该候选，继续下一个，并在 `other_planes` 披露原因。
- 版本与 profile bundle 版本不一致：**不 FAIL**，作为身份证据披露（doctor S3 显示"宿主 0.2.2 / profile bundle 0.2.1"一类差异）；只有"行级校验失败"才 FAIL。
- 多个平面同时可读：全部进 `other_planes`，主平面按 precedence 取第一个"行级校验可执行"的；28v 报告必须同时列出每个平面的 `kind + dsh_version + anchor`。

### 3.5 备选与否证

| 备选 | 否证理由 |
| --- | --- |
| 全量解包 asar 再查 | 体积/写盘/完整性风险；违反"零解包"目标；每次校验都产生临时目录 |
| 只信 PATH `dsh` | 今天的事实即反例（F8）：CLI 0.2.1 与桌面 0.2.2 并存 |
| 从 profile 反推桌面面 | `profiles/desktop/package.json` 无 asar 指针（`dsh.profile.bundles` 只有 bundle 名） |
| 用 `app.asar.unpacked` 当平面 | 只有被解包的文件，无完整索引，模块解析会随机失败 |

---

## 4. D2 行级覆盖与部分证据

### 4.1 现状

- 判定是整份报告的：`verdict` 由 `report` 级聚合得出（`dsh_compat.py:1956-1975` 的 NOT_RUN 规则、`check_dsh_preset_compat()` `:1976`）。
- probe 脚本里 oracle 构建任一失败即 `fail("installed harness API unavailable: …")`（`dsh_compat.py:731`），整份报告 `ok:false` → 上层 NOT_RUN（`:2117-2122`）；oracle 未构建 → NOT_RUN（`:2127-2132`）。
- coverage 是事后聚合的四个计数（`:1811-1873`），没有"每个行为什么没被验证"的结构化原因（`unverified_reasons` 只有粗分类 `NO_SCHEMA`）。
- `!!js` 的 disabled 表达式在**固定 ctx** 上求值（`:1071`），ctx 缺成员时抛 TypeError，被归为行级 FAIL（F7 的 `DISABLED_EXPR_ERROR` 路径，`:956`）。

### 4.2 决策

**D2：行级结果是唯一判定单位；API 缺失按角色降级；ctx 桩面进契约；报告分片写。**

1. **报告结构 v2**（`schema: dsh-compat-report/2`）：`compositions[]` 每条含 `plane`、`status`、`rows[]`（每行 `{id,name,kind,outcome,reason,detail}`，`outcome ∈ verified|unverified|failed|skipped|disabled|inherited`）、`unreadable[]`、`bounded_out`；顶层 `totals` 按 `outcome` 与原因码计数；`verdict` 只由 `failed` 决定，`NOT_RUN` 只在"没有任何 composition 可读"或"显式平面不可用"时出现。
2. **oracle 角色化**：`yaml`（解析必需）、`cordis`（schema 校验）、`loader`（`!!js` 求值）。`yaml` 缺失 → 该文件 `UNREADABLE(ORACLE_YAML)`；`cordis` 缺失 → 行 outcome `unverified(NO_ORACLE)`；`loader` 缺失 → 含 `!!js` 的行 `unverified(NO_LOADER)`，其余行照常。**任何单一 API 缺失不再让整份报告塌成 NOT_RUN。**
3. **ctx 桩面进契约**：`host.apis.loader_ctx.members`（如 `baseUrl`、`process`、`console`、`get`、`has`）与 `member_semantics`（未声明的成员一律抛错；已声明成员返回值固定为 `undefined`/`false`，以"未注入"语义表达）。probe 用 `Proxy` 实现：`ctx.<name>` 命中声明 → 返回桩值；未命中 → 抛 `Error("loader ctx member '<name>' is not declared in host.apis.loader_ctx")`，该错误**必须是行级 FAIL**（漂移要响亮，不是"未知行跳过"）。同时记录 `ctx_members_used`，28v 证据断言 `used ⊆ declared`（这就是 K-8 的机器化）。
4. **部分证据落盘**：probe 每完成一个 composition 就把该条的 `status/rows/coverage` 以 JSONL 追加到 `report.partial`（`<scratch>/report.partial.jsonl`），进程崩溃/超时后上层读取部分结果，未完成部分记 `UNVERIFIED(INTERRUPTED)`，`verdict=NOT_RUN` 且**保留已得行结果**；`_run_probe()` 的超时路径不得丢报告（今天 timeout 直接走异常，`:1627-1637`）。
5. **`rows_checked == 0` 语义**：保留"0 行被 schema 校验不能 PASS"的既有硬规则（`:1956-1961`），但原因码细化：`ALL_DISABLED` / `ALL_INHERITED` / `NO_ORACLE` / `NO_COMPOSITIONS`，禁止笼统一句。

### 4.3 备选与否证

| 备选 | 否证理由 |
| --- | --- |
| 保持全或无 + 重试 | 无法区分"宿主 API 演进"与"探测环境不全"，RISK-072 的"行级全绿"无法证明 |
| 把 API 缺失一律降为 unverified | 会掩盖真正的宿主漂移（契约已声明 API 必须可用 → 缺就是漂移） |
| 允许未声明 ctx 成员返回 undefined | 行被静默禁用，形成"看起来绿"的假象（R3 反例） |

---

## 5. D3 有界发现

### 5.1 现状

`discover_compositions()`（`dsh_compat.py:1426-1445`）用 `root.glob(pattern)` 无界遍历，`_is_skipped_relative()` **在遍历之后**过滤（`:1440`），且 `_SKIP_DIRS`（`:520`）不含 sandbox/junction 处理；Windows junction 可形成目录环（F9）。

### 5.2 决策

**D3：遍历前剪枝 + 硬预算 + 默认根收窄；越界只披露不 FAIL。**

- 新模块 `dsh_walk.py`：`walk(root, *, fs, clock, bounds)`，`bounds = {max_depth, max_entries, max_seconds, skip_reparse, suffix_allowlist}`；`os.scandir` 递归，进入目录前判 `st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT`（以及 `ST_REPARSE_TAG_MOUNT_POINT`）→ 跳过并计数；`(st_dev, st_ino)` 已访问集合防硬链/环；条目数/时间超限 → 抛出 `BoundedOut`（携带已发现结果）。**预算四项与 `clock` 全部可注入**（`clock` 默认 `time.monotonic`）：测试用假时钟断言"预算触发即停"，不依赖真实计时（否则只能写 flaky 的 `assertElapsed < N`）。
- 默认根（契约 `host.home.discovery.roots`）：包载荷目录（`agent-presets/`、`adapters/dsh/`），**不再默认扫仓库根**；`--root` 显式传入时才扫任意根（仍受预算约束）。沙箱副本因此在默认路径下不再进入结果（F9 的 7 条噪音消失）。
- 结果对象：`{found: [...], skipped_reparse_points: n, bounded_out: bool, budget_used: {...}}`；`bounded_out` 在 report 中为 `UNVERIFIED(DISCOVERY_BOUNDED)`，**不得**据此 FAIL。
- 后缀白名单（契约声明）：`*.cordis.yml`、`*.cordis.yml.template`、`overlay.cordis.yml` 不匹配前三者（片段不是 composition，必须在发现层显式排除并留一行披露，防止将来把片段当 composition 校验）。

### 5.3 备选与否证

| 备选 | 否证理由 |
| --- | --- |
| 继续 glob + 事后过滤 | 环上不会终止；时间不可控；沙箱噪音混入行级计数 |
| 要求用户传 `--root` | 把发现策略推给调用者；28v 默认路径不可复现 |
| Windows-only `FindFirstFile` 快路径 | 平台分裂；`scandir` 已够（实测 10 s 量级） |

### 5.4 影响面（F14：扩大的破坏范围）与强制回归

**影响面不止 28v。** 同一缺陷同时阻断两条交付路径：

1. **Check 28v**：`discover_compositions()` 以仓库根为 root 时进入 junction 自环（`dsh_compat.py:1426-1445`）。
2. **单元测试套件**：`test_dsh_*.py` 中有测试以仓库根为 root 调用 `discover_compositions()`（`_SKIP_DIRS`/`_SKIP_PATH_PAIRS` 与 `_is_skipped_relative()` 是"**事后**过滤"，遍历本身不剪枝），同一 junction 环使套件纯 Python 自旋（F14：813 s CPU、无 child 进程 → 慢在遍历而非 node）。
3. **自中毒**：`.governance/sandboxes/**/profiles/web/node_modules/@peterwangze/software-project-governance-plugin` 是历次派发生成的 junction→仓库根，且 `.gitignore` 忽略 `.governance/`，评审不可见；任何人在本机跑门/跑测试都会挂，且下次派发继续生成新的环。

因此 D3 的验收不是"28v 不卡"，而是"**门 + 测试套件**都不再受自环影响"，并且**不能靠"发现环就全盘放弃"过关**：

- **强制回归 1（显式自指环）**：测试在 `tempfile.mkdtemp()` 下构造 `root/sub/junction -> root`（Windows 用 `os.symlink(..., target_is_directory=True)`，不可用则 `subprocess.run(["cmd","/c","mklink","/J",...])`；两者都失败 → `self.skipTest("reparse-point creation unavailable: <reason>")`，**跳过必须带原因，禁止静默孤儿测试**）。断言 `discover_compositions(root)` 在 **< 5 s** 内返回，且 `skipped_reparse_points >= 1`。
- **强制回归 2（环 + 正常 composition 共存）**：同一 root 下另放一份合法 composition（fixture 或 `overlay.cordis.yml` 的副本），断言正常文件**仍被发现**、环被跳过、`bounded_out is False`（未触发预算）——证明有界 ≠ 放弃。
- **强制回归 3（预算可注入）**：用假 `clock` + 极小 `max_seconds/max_entries/max_depth` 断言 `BoundedOut` 触发且携带已发现结果；不写真实计时断言。
- **正向期望（由仓库扫描策略派生，不进契约）**：`_is_skipped_relative()` 是**仓库扫描策略**而非宿主事实，**不搬进 host-contract**；但由它派生两条正向断言写入测试：**S7 前**产品面应恰好扫到 **1 份** composition（`agent-presets/governance/agent.cordis.yml.template`），**S7 退场后**应为 **0 份**（`overlay.cordis.yml` 是片段，按 `discovery.exclude_names` 显式排除）；沙箱副本在任何阶段都不计入。

---

## 6. D4 Δ 合并渲染（旧路目录面，DEC-385①）

### 6.1 现状与问题

- 安装器 `install_preset()`（`launch.py:629-740`）渲染模板（`render_composition()` `:452-484`）→ 落 staging → rename；模板是"唯一组合源"（`launch.py:12-23` 的 docstring 明确断言）。宿主演进 → 模板必然陈旧（F3/F5）。
- native 面已经用 `deriveDefinition()` 从 base preset 派生（`overlay.js:74-163`），**旧路面没有对应逻辑**：它把派生结果手工冻结进模板 —— 这正是双面漂移的根因。

### 6.2 决策

**D4：模板退场；治理面 = 两行 overlay 片段；安装期从 plane 的 base preset 做文本级派生 + 合并；派生不到拒装（exit 2）。**

#### 6.2.1 目标产物与输入

- **新文件** `agent-presets/governance/overlay.cordis.yml`（约 20 行，唯一治理组合来源）：
  - 行 1：`persona`（`@deepseek-ai/dsh-persona`），`config.prefix` 是字面块，内容为 token `__GOVERNANCE_PERSONA_BODY__`（单一 token 占位，body 由 `persona.md.template` 渲染）；
  - 行 2：`skill-filesystem`（`@deepseek-ai/dsh-skill-filesystem`），`config.customSkillDirs` 为两个 token（`__GOVERNANCE_SKILLS_ROOT__`、`__GOVERNANCE_SHIMS_ROOT__`），块序列，缩进形状由契约 `own.render.custom_skill_dirs_shape` 声明。
- **保留** `persona.md.template`（正文唯一来源；同时承接原模板承载的注入契约关键词，见 §9.4）。
- **删除** `agent-presets/governance/agent.cordis.yml.template`（物理删除并入 S7 退场原子切片，§10；快照归档 `docs/` 作历史）。`lib/index.js` 的 `renderComposition()` 保留为"overlay 片段 token 渲染器"（JS↔Python token 一致性的 parity gate，`host-contract.json` 的 `differential_gate` 仍指向 `test_js_and_python_renderers_agree`），`ensurePreset()` 退化为 **warn + 不写** 的 deprecated shim（native 是唯一交付面，`apply()` 本来不调用它，`lib/index.js:698-707`）。

#### 6.2.1.1 随模板退场的 13 行能力损失清单（DEC-386②：全部退休）

模板 29 行的构成是 **16 顶层 + 13 嵌套**（`dsh_boundary.py:120-122`），退场的 13 行**恰为全部嵌套行**，分布在 3 个 group 下：`planning`（`isolate.planMode`，模板 `:127-131`）、`compaction`（`isolate.compaction/toolResultPruner`，`:151-156`）、`delegation`（`isolate.workflowEngine`，`:176-180`）。13 行全退后 3 个 group 无子行，随之退场；旧路面输出 = base 22 行（persona/skill 两行被 overlay 替换）+ 0 行自加 = **22 行**，与 native 派生同构。

`config` 列一律从模板对应行实读（行号见括号），不推断；"包是否仍在"来自协调者对 asar 内 331 个 `@deepseek-ai/*` 包名的集合判定（F5）。

| # | `id` | `name` | 模板行内 `config` 键（实读） | 0.2.2 asar 包/子路径 | 退场后用户可感知的变化（事实性） |
| --- | --- | --- | --- | --- | --- |
| 1 | `plan-mode` | `@deepseek-ai/dsh-plan-mode` | `config.section`：块标量（`\|`），计划模式指令正文（`:135-147`） | 包在 | 旧路面不再向模型注入计划模式指令段（该段由本仓提供，标准 preset 从未启用）；行为面未验证 |
| 2 | `compaction-basic` | `@deepseek-ai/dsh-compaction-basic` | 无（`:158-159`） | 包在 | 旧路面不再启用基础压缩插件；行为面未验证 |
| 3 | `command-compact` | `@deepseek-ai/dsh-command-compact` | 无（`:161-162`） | 包在 | 旧路面不再启用该插件（按行名推断为精简命令入口，未验证）；行为面未验证 |
| 4 | `tool-result-pruner` | `@deepseek-ai/dsh-compaction-tool-result-pruner` | `thresholdChars: 8192`、`headChars: 4096`、`tailChars: 1024`（`:166-169`） | 包在 | 旧路面不再启用工具结果裁剪（阈值/头尾保留量按键名推断，未验证）；行为面未验证 |
| 5 | `tool-subagent-control` | `@deepseek-ai/dsh-tool-subagent-control` | 无（`:182-183`） | 包在 | 旧路面不再注册子代理控制工具（与 #6 同包、不同子路径）；行为面未验证 |
| 6 | `tool-subagent-list-agents` | `@deepseek-ai/dsh-tool-subagent-control/list-agents` | 无（`:185-186`） | **子路径已删**（包在，exports 无此子路径） | 0.2.2 上**本就已死**（F3 的 1 issue）→ 退场只消除一条 FAIL，无能力损失 |
| 7 | `tool-subagent` | `@deepseek-ai/dsh-tool-subagent` | `provider: spawn`、`toolName: subagent`、`backgroundMode: continuable`（`:190-193`） | 包在 | 旧路面不再向模型暴露 `subagent` 工具；行为面未验证 |
| 8 | `tool-subagent-fork` | `@deepseek-ai/dsh-tool-subagent` | `provider: fork`、`toolName: subagent_fork`、`backgroundMode: continuable`（`:197-200`） | 包在 | 旧路面不再暴露 `subagent_fork` 工具（与 #7 同包、不同 `toolName`）；行为面未验证 |
| 9 | `tool-subagent-codex` | `@deepseek-ai/dsh-tool-subagent` | `disabled: true`、`provider: codex`、`toolName: subagent_codex`、`enableRunInBackground: false`、`maxDepth: provider-managed`（`:203-210`） | 包在 | 行自带 `disabled: true` → **今天就不生效**，无能力损失 |
| 10 | `tool-subagent-claude-code` | `@deepseek-ai/dsh-tool-subagent` | `disabled: true`、`provider: claude-code`、`toolName: subagent_claude_code`、`enableRunInBackground: false`、`maxDepth: provider-managed`（`:212-219`） | 包在 | 同上 → 无能力损失 |
| 11 | `workflow-ptc` | `@deepseek-ai/dsh-workflow-ptc` | `provider: spawn`（`:230-231`） | 包在 | 旧路面不再启用 workflow（PTC）引擎；行为面未验证 |
| 12 | `tool-workflow` | `@deepseek-ai/dsh-tool-workflow` | 无（`:233-234`） | 包在 | 旧路面不再暴露 workflow 工具；行为面未验证 |
| 13 | `tool-ralph` | `@deepseek-ai/dsh-tool-ralph` | `subagentProvider: spawn`、`maxRounds: 64`（`:238-240`） | 包在 | 旧路面不再暴露 `ralph` 工具；行为面未验证 |

合计：**实际生效的能力面 = 10 行（全部为治理面自加、标准 preset 从未启用）**；另 2 行今天已 disabled（#9/#10）、1 行已死（#6）随退场清理——死行消除反而减少一条既有 FAIL，属改善而非损失。四行 `tool-subagent*` 共用同一个包 `@deepseek-ai/dsh-tool-subagent`，靠 `toolName` 区分（`subagent` / `subagent_fork` / `subagent_codex` / `subagent_claude_code`）；`tool-subagent-control` 与 `tool-subagent-list-agents` 共用 `@deepseek-ai/dsh-tool-subagent-control`，靠子路径区分。**不得把"包还在"写成"功能等价"**：包在只说明模块可解析，启用面（工具是否暴露、引擎是否挂载）随行退场而消失。回补需求按 O4 裁决在 native 面另立任务。

#### 6.2.2 派生与合并算法（`adapters/dsh/composition_merge.py`，纯函数 + 端口）

输入：`base_patch_text`（plane 内 `<dsh>/node_modules/@deepseek-ai/dsh-web-app/presets/<base_preset_id>.patch.yml` 的原始字节解码文本）、`overlay_text`（已渲染 token 的片段）、`policy`（缩进/换行/前缀规则）。

**派生在双平面成立（O5 已闭合）**：路径形状一致——`<plane>/…/dsh-web-app/presets/<base_preset_id>.patch.yml`；asar 桌面面走 asar 条目索引（0.2.2：6,858 B / 22 行），磁盘 `node_modules` 面走文件读取（0.2.1：6,799 B / 22 行），两者 id 序列逐项相同，只差文件大小（版本差异）。派生算法、行切块与拒装码在两个平面上完全共享；同目录其他 preset（`minimal` 4 行、`ptc` 23 行、`cordis` 23 行）不在 `base_preset_id` 候选内。

1. **定位 base 行**：文本扫描顶层 `- insert:` 段，按 2 空格步进找到 `- id: <base_preset_id>` 且 `name: '@deepseek-ai/dsh-agent-preset'` 的 insert 项（契约 `own.native.base_preset.row_selector`：`name == base_row_name ∧ config.id == base_preset_id`）；其 `config.plugins:` 下的块序列即宿主行。0.2.2 实测 22 行、10 空格缩进（F1）。
2. **行切块**：以"同一缩进的 `- id:`"为行首切块，块内允许任意嵌套与块标量；记录每块 `{id, indent, start, end, id_line}`；空行/注释归属前一块。`id` 缺失、重复、行首缩进不一致 → 拒装。
3. **替换 persona 行**：读 base 行的 `prefix:` 值（0.2.2 是单行 plain scalar，F12）；若它不是"单行标量"（例如 `|-` 块、flow 序列、`!!js`）→ 拒绝（`PERSONA_PREFIX_UNSUPPORTED`，对齐 `overlay.js:112-115`）。body 的取得与拼接一律按 §6.2.2.1 的 5 步规则（与 `lib/dsh-native/persona.js:38-50`、`overlay.js:115-120` 逐字对齐）。输出为 `prefix: |` 字面块，行缩进 = 该 config 键缩进 + 2，正文每行按同缩进加空格；正文内的空行输出为空行（块标量合法）。
4. **替换 skill 行**：读 base 行的 `customSkillDirs`（若存在）并保留其既有条目；把 overlay 声明的两个绝对 posix 根**去重追加**（Windows 下 case-insensitive，复用 `samePath` 语义，`overlay.js:146-155`）；输出块序列（`- <绝对路径>`）。base 行无 `customSkillDirs` 键 → 在 `config:` 下新增；`config` 不是映射或键名形状不支持 → `SKILL_DIRS_UNSUPPORTED`。
5. **其余行 verbatim**：未触碰的行**逐字节保留**（含注释、`!!js`、`disabled` 表达式、引号风格、行尾），只做整体缩进归一（base 行缩进 → 输出顶层 0 缩进，嵌套相对偏移保持不变）。
6. **头注释**：追加 4 行生成注释（包版本、平面 `kind`/`dsh_version`、base preset id、overlay sha256、`do not edit; regenerate with adapters/dsh/launch.py --install`）。
7. **输出校验**（写盘前）：`!!js` 计数与 base 一致；顶层行数 = base 行数（不增不减）；`leftovers()` 为空；`require_lf_newline_policy()` 通过；行 id 无重复；persona/skill 行恰好各 1。

#### 6.2.2.1 persona body 派生规则（与 native `loadPersonaBody` 逐字对齐）

native 实现是**规范**：`lib/dsh-native/persona.js:38-50`。Python 侧必须逐步复刻，不得简化为"文件内容直接塞进去"：

1. **读文件**：读 `<pkg_root>/agent-presets/governance/persona.md.template` 原始字节，按 UTF-8 解码（`persona.js:39`）。
2. **CRLF 归一**：`text.replace(/\r\n/g, "\n")`（`persona.js:39`）；只做这一种归一，不碰 `\r` 单字符、不碰行尾空白。当前文件实测 16 处 CRLF（2,739 B → 2,723 B）。
3. **token 替换**：`body = text.split(body_token).join(posixPath(pkg_root))`（`persona.js:43`）。`body_token` = `__GOVERNANCE_REPO_ROOT__`（`host-contract.json:822` 的 `own.native.persona_repo_token`）；替换值是**包根 posix 化**（`posixPath(pkg_root)`，`persona.js:22-24`），**不是仓库根**、不是 asar 路径。`text` 不含该 token → `PERSONA_TOKEN_MISSING`（`persona.js:40-42`）。
4. **全 trim + 残留扫描 + 空判决**：`body = ... .trim()`（**两端**都裁，`persona.js:43`）；对 trim 后 body 跑 `own.render.leftover_scan`（`__[A-Za-z0-9_]+__`），命中 → `PERSONA_BODY_TOKEN_LEFTOVER` 并列出命中集合（`persona.js:44-47`）；随后 `body == ''` → `PERSONA_BODY_EMPTY`（`persona.js:48`）。`persona.md.template` 实测 `{{model}}`/`{{cwd}}` 各 0 处——**宿主变量必须原样保留**，渲染器不得替换。
5. **按拼接式组装**：`basePrefix = base_prefix.trimEnd()`；`basePrefix == ''` → `prefix = body + "\n"`；否则 `prefix = basePrefix + "\n\n" + body + "\n"`（`overlay.js:115-120` 逐字）。0.2.2 的 base prefix 是单行 plain scalar `You are a coding agent powered by the {{model}} model.`（54 B，F12）。

契约块 `own.render.persona_prefix`（v2 新增，S0 落）：字段表如下；**任何一项在 Python/JS 之间出现分歧都应由差分门（`own.render.differential_gate`）判 FAIL，而不是靠人工比对**。

| 字段 | 值 | 依据/说明 |
| --- | --- | --- |
| `mode` | `base-prefix-then-body` | `overlay.js:115-120` 的拼接顺序 |
| `separator` | `"\n\n"` | `overlay.js:119` |
| `trailing` | `"\n"` | `overlay.js:118-119` 两个分支都以换行结尾 |
| `empty_prefix` | `body-only` | `overlay.js:117-118`：空 base prefix 只输出 body + `\n` |
| `body_source` | `agent-presets/governance/persona.md.template` | 复用 `own.native.persona_source`（`host-contract.json:821`） |
| `body_token` | `__GOVERNANCE_REPO_ROOT__` | 复用 `own.native.persona_repo_token`（`:822`）；不另立第二 token |
| `body_token_value` | `posix_pkg_root` | 替换值 = `posixPath(pkg_root)`，不是仓库根 |
| `body_crlf` | `lf` | 先 `\r\n`→`\n` 再替换（`persona.js:39`） |
| `body_trim` | `true` | 两端全 trim（`persona.js:43`） |
| `body_empty_policy` | `refuse` | 空 body 拒绝（`persona.js:48`） |
| `leftover_scan` | 复用 `own.render.leftover_scan` | `__[A-Za-z0-9_]+__` |

> **2,808 的定位**：`2808 = 54 + 2 + body + 1` 是本机实测（0.2.2 asar base + 本机包根路径长度）的**观测值**，随包根路径长度变化，**只允许出现在测试夹具与差分断言里**（S4 的 0.2.2 fixture 断言、`test_js_and_python_renderers_agree`），**禁止**写进产品代码当魔数或常量校验。正文不写"2,739 → 2,751"式的换算断言，等式由差分测试钉住。

#### 6.2.3 拒装码（exit 2，`write_side_refusal` 同族语义，`launch.py:667-669, 863`）

| 码 | 触发 | 说明 |
| --- | --- | --- |
| `PLANE_UNUSABLE` | 无平面 / 显式平面不可读 / asar 头非法 | 不猜 base |
| `BASE_PRESET_MISSING` | plane 内无 `<id>.patch.yml` | 0.2.2 有；更早/更晚版本可能改名 |
| `BASE_PRESET_UNREADABLE` | asar 条目读失败 / 解码失败 | |
| `BASE_ROW_MISSING` | 找不到 `name==base_row_name ∧ config.id==base_preset_id` | |
| `BASE_ROW_DUPLICATE` | 同上命中多个 | |
| `BASE_ROW_DISABLED` | base 行被禁用 | 禁用行不会挂载，合并无意义 |
| `BASE_ROWS_NOT_LIST` | `config.plugins` 非块序列 | |
| `BASE_ROW_INDENT_DRIFT` | 无法稳定切块（混合缩进/行首异常） | |
| `PERSONA_ROW_MISSING`/`DUPLICATE`/`DISABLED` | 合并目标行问题 | 对齐 `overlay.js:95-101` |
| `PERSONA_PREFIX_UNSUPPORTED` | base prefix 不是单行标量 | 对齐 `overlay.js:113` |
| `SKILL_ROW_MISSING`/`DUPLICATE`/`DISABLED` | 同上 | 对齐 `overlay.js:125-132` |
| `SKILL_DIRS_UNSUPPORTED` | `customSkillDirs` 形状不支持 | 对齐 `overlay.js:142,149` |
| `OVERLAY_ROW_MISSING`/`DUPLICATE`/`DISABLED` | 片段自身非法 | 静态守卫（§9.4）也会先挡 |
| `RENDER_INTERNAL` | 上述之外（IO/编码/内部断言） | **exit 1**，不是拒装 |

`--dry-run` 同样执行派生与合并，只打印"将写出的行 id + 平面身份 + provenance"，零写盘（对齐 `launch.py:647-660` 的既有 dry-run 语义）。

#### 6.2.4 双面一致性

- 相同 base + 相同 body 下，native `deriveDefinition()` 与 Python merge 必须产出**相同的 prefix 字节**（F13 已证明可行：2808 == 2808）。
- 测试：`test_dual_face_parity` 用 fixture base（22 行样本）+ fixture body，分别跑 `overlay.js`（node）与 `composition_merge.py`，断言 prefix 字符串、`skillDirs` 列表、行 id 顺序一致；node 缺失时 skip（与现有 probe 测试口径一致）。

### 6.3 备选与否证

| 备选 | 否证理由 |
| --- | --- |
| A. 文本拼接（选定） | 保留 base 注释/`!!js`/引号/顺序；无 node、无 YAML 依赖；纯 Python 可离线；fake-host 单测只需文本 fixture |
| B. node + plane 的 `js-yaml` load→dump | 安装路径被拖上 node + asar 读取；重排全部行、丢注释、引号风格与 `!!js` tag 需重建；实测 round-trip 可行（6,586 B）但输出不再可字节审阅 |
| C. JS 里复制一份合并逻辑 | 双实现 parity 风险（正是当前漂移的形态） |
| D. 保留 29 行 + 手工补 7 行 | 下次宿主演进继续漂移；违反 DEC-385① |

---

## 7. D5 安装溯源与 S1 残留检测

### 7.1 现状

doctor S1（`dsh_doctor.py:406-500`）只校验：目录存在、`preset.yml`、`.dsh-bundle-version` 与包版本一致；**不校验行集**（F10），所以 29 行残留（含死行）判 PASS。S1 的修复文案反复要求"重启 dsh 让 bundle host row 渲染预设"（`:430, 443-445, 458-460, 468-470`），与 DEC-366②（native 是唯一交付面；目录面不自动重渲染）**直接矛盾**。

### 7.2 决策

**D5：安装期写 `render-provenance.json`；S1 离线比对"实际行集 vs 溯源行集"；文案全面改口径。**

- **落点**：`${DSH_HOME}/.agent-presets/governance/render-provenance.json`（契约 `own.preset.render_provenance = {filename, schema, fields}`）。同目录已容忍 `preset.yml`/`.dsh-bundle-version`/`skill-root.txt`，低风险（O3 仍列为待验证）。写入在 staging 内完成、随 rename 原子生效。
- **内容**（由 merge/provenance 纯函数生成，不 dump 环境）：

```json
{
  "schema": "dsh-preset-provenance/1",
  "package_version": "0.100.0",
  "rendered_at": "2026-11-07T00:00:00Z",
  "overlay": {"path": "agent-presets/governance/overlay.cordis.yml", "sha256": "…"},
  "persona": {"path": "agent-presets/governance/persona.md.template", "sha256": "…"},
  "plane": {"kind": "asar-desktop", "dsh_version": "0.2.2-rc.1", "anchor": "D:/app/dsh/resources/app.asar", "header_sha256": "…"},
  "base": {"preset": "standard", "source_sha256": "…", "row_count": 22, "row_ids": ["persona", "…"]},
  "overlay_rows": ["persona", "skill-filesystem"],
  "rows": [{"id": "persona", "origin": "overlay"}, {"id": "agent-instructions", "origin": "base"}],
  "policy": {"newline": "lf", "write_policy": "staging+rename, no-lock, best-effort"}
}
```

- **S1 判定**（新增离线行集读取，复用 merge 的行切块器，不读平面）：
  - provenance 存在：实际 `agent.cordis.yml` 行 id 序列 == `rows[].id`（顺序与集合都校验）；extra → `FAIL(RESIDUAL_ROWS)`，missing → `FAIL(MISSING_ROWS)`；`plane.dsh_version` 与当前可识别宿主版本不同 → `WARN(PLANE_VERSION_DRIFT)`（不 FAIL，因为宿主升级是合法的）；包版本不符 → `FAIL(VERSION_MISMATCH)`。
  - provenance 缺失（旧安装）：`UNVERIFIED(PROVENANCE_ABSENT)` + 一条迁移 remediation（重跑 `--install`），**一个版本宽限**；宽限期后转 FAIL（写入 RISK-072 的闭包口径）。
  - 文案：删除一切"重启渲染"叙事，改为"目录面是显式渲染产物：改治理面后重跑 `adapters/dsh/launch.py --install`（隔离环境 + `DSH_HOME` 重定向）；native 面由 `apply()` 注册，无需目录"。
- **清理面**：`uninstall_preset()` 删整个目录，天然覆盖；`cleanup.py:52-56` 的 `.agent-presets` 删除域不扩大（保持整目录语义）。

### 7.3 备选与否证

| 备选 | 否证理由 |
| --- | --- |
| S1 现场重算 base 行集 | doctor 必须离线/无平面（`dsh_doctor --offline` 契约）；重算会把 S1 变成 28v |
| 只比对行数 | 29 → 29 的替换型漂移抓不到；死行抓不到 |
| 把 provenance 放到 `DSH_HOME` 外 | 卸载/清理/迁移都失去原子性；脱离预设目录的溯源不可信 |

---

## 8. D6 契约收口与 28w 不变式改造

### 8.1 现状

- `dsh_contract.py` 的 `_REQUIRED` 硬编码必填点（`host.rows` 在 `:126`、`own.preset.*` 在 `:153-159`、`own.render.*` 在 `:160-163`、`coverage.entries` `:179`、`elimination.dispositions` `:186`）；`SUPPORTED_SCHEMA_VERSIONS=(1,)`（`:69`）。
- 28w 的 K-3（`dsh_boundary.py:742`）用 `template_row_mismatches()`（`:706-739`）把模板行与契约 `host.rows` 做**双向 29 行比对**，`EXPECTED_ROW_TOTAL=29`（`:122`）硬编码；K-4 校验 token（`:773-819`）；K-7 版本证据（`:1105`）；K-8 coverage 声明（`:1216-1300`）；K-10 行契约不变式（`:1393`）；K-12 单裁决锚（`:1792`）。
- 模板退场后：K-3 的比对对象消失，`host.rows` 成为第二漂移源（依赖矩阵 #35）。

### 8.2 决策

**D6：契约升 v2，单一事实源；28w 把"冻结 29 行"替换为"模板不得携带宿主行 + 片段形状 + 平面证据"三条新守卫。**

#### 8.2.1 契约 v2 变更（`host-contract.json`，schema_version 2）

| 键 | 动作 | 内容 |
| --- | --- | --- |
| `own.overlay` | 新增 | `{path: agent-presets/governance/overlay.cordis.yml, rows: [persona, skill-filesystem], persona_body_token: __GOVERNANCE_PERSONA_BODY__, persona_body_source: agent-presets/governance/persona.md.template, allow_js: false}` |
| `own.native.base_preset` | 新增 | `{patch_rel: dsh/node_modules/@deepseek-ai/dsh-web-app/presets/{id}.patch.yml, row_selector: {name: <base_row_name>, config_id: <base_preset_id>}, rows_path: config.plugins, insert_selector: "- insert:"}` |
| `own.preset.render_provenance` | 新增 | `{filename: render-provenance.json, schema: dsh-preset-provenance/1, fields: [...], absent_policy: warn-one-release}` |
| `own.render.persona_prefix` | 新增 | `{mode: base-prefix-then-body, separator: "\n\n", trailing: "\n", empty_prefix: body-only, body_source: agent-presets/governance/persona.md.template, body_token: __GOVERNANCE_REPO_ROOT__（复用 own.native.persona_repo_token）, body_token_value: posix_pkg_root, body_crlf: lf, body_trim: true, body_empty_policy: refuse, leftover_scan: 复用 own.render.leftover_scan}` — 规则见 §6.2.2.1 |
| `host.planes` | 新增 | `{precedence: [...], asar: {header: [...], content_base: "8+payload_size", runner: {flag: ELECTRON_RUN_AS_NODE, module_flag: "--input-type=module"}, runtime_rel: resources/runtime/versions.json, unpacked_cannot_serve: true, entry_count_cap: 200000}, env: {desktop_app_dir: DSH_DESKTOP_APP_DIR, profile_dir: DSH_PROFILE_DIR}, process_probe: {enabled_in: [doctor, boundary], max_ancestors: 4}}` |
| `host.home.discovery` | 新增 | `{roots: [agent-presets, adapters/dsh], suffixes: [".cordis.yml", ".cordis.yml.template"], exclude_names: [overlay.cordis.yml], bounds: {max_depth: 24, max_entries: 50000, max_seconds: 30}, follow_reparse: false}` |
| `host.apis.loader_ctx` | 新增 | `{members: [baseUrl, process, console, get, has], unlisted_member: throw, stub_values: {get: undefined, has: false}, evidence: ctx_members_used ⊆ members}` |
| `own.preset.template` | S0 标弃用，S7 物理删除 | S0：保留键值并加 `deprecated_in: 2`（读者不切换，`dsh_contract.py` 必填表继续要求存在——**弃用 ≠ 允许缺失**）；S7 退场原子切片删除，引用点改 `own.overlay.path` |
| `host.rows` | S0 标弃用，S7 物理删除 | S0：保留 29 行与全部读者（K-1/K-2/K-3、doctor、测试），只加 `deprecated_in: 2` 元数据；S7 删除后降级为 `evidence.rows_inventory`（历史证据，`verified_on` + TTL 由既有机制承担） |
| `SUPPORTED_SCHEMA_VERSIONS` | 1 → 2 | S0 即接受 v2；v1 读到即 `ContractSchemaUnknown`（包内契约与代码同版本发布，不存在合法的 v1 场景）。**S0 不删任何键**：v2 只是"新增键 + 旧键标弃用"，28w 与 doctor 在 S0–S6 期间保持绿，物理删除集中在 S7 |

> **时序（对应 §10 S0 / S7）**：S0 只做加性变更——新增全部 v2 键 + `SUPPORTED_SCHEMA_VERSIONS` 1→2，`host.rows` 与 `own.preset.template` 保留并标 `deprecated_in: 2`，`dsh_contract.py` 用"必填但已弃用"这一态表达弃用（**不允许**用"允许缺失"表达，否则读者无法区分"新契约"与"契约破损"）。物理删除两个键、删除模板文件、K-3→K-3′、全部读者切换、锚点迁移合并为 **S7 一个原子 commit**（§10），因此 S0–S6 期间 28w（K-1/K-2/K-3）与 doctor 不会因删键删文件而变红。

#### 8.2.2 28w 变更（`dsh_boundary.py`）

- **K-1/K-2**（契约结构/allowlist）：随 v2 字段表更新；`K2_ALLOWLIST`（`:1483`）删去 `own.preset.template` 语义，新增 `own.overlay`。
- **K-3 → K-3′（静态守卫）**：`template_row_mismatches` 删除；新判据：
  1. `agent-presets/governance/agent.cordis.yml.template` **不得存在**（存在即 FAIL：任何冻结宿主行的文件都不得进包）；
  2. overlay 片段的行 id 集合 == `own.overlay.rows`（顺序敏感）；行 `name` 只允许两个声明值；
  3. 片段内**禁止 `!!js`**（治理片段必须与平面无关），禁止 `- insert:`；
  4. 片段内 token ⊆ `own.render.tokens` 且包含 `__GOVERNANCE_PERSONA_BODY__`；
  5. 片段不得含 `disabled:`（治理行不自我禁用）。
  - `EXPECTED_ROWS_TOP_LEVEL/EXPECTED_ROWS_NESTED/EXPECTED_ROW_TOTAL`（`:120-122`）删除。
- **K-4**（token）：token 表从 3 → 4（新增 body token）；token 的包内相对路径必须存在；残留 token 扫描仍由安装器执行（运行时），28w 只校验声明与片段的 token 一致。
- **K-7**（版本证据）：升级为"平面身份证据"——recorded evidence 必须含 `plane.kind`、`plane.dsh_version`、`plane.anchor`、`plane.header_sha256`（asar 面）；磁盘面可只有 `kind/version/anchor`。
- **K-8**（coverage 声明）：原因码枚举进契约（`coverage.entries` 扩展 `NO_ORACLE`/`NO_LOADER`/`INTERRUPTED`/`DISCOVERY_BOUNDED`/`PROVENANCE_ABSENT`），28w 校验代码里出现的 reason 码 ⊆ 契约声明（静态 grep，像 K-4 的 token 绑定那样）。
- **K-10**（行契约不变式）：不变，但输入从"29 行模板"改为"merge fixture 产物 + 片段"，仍需 `insert 必带 id` / `payload 可克隆` / `不写 .cordis` 三条（`dsh_boundary.py:129-132` 的拼写）。
- **新增 K-14（平面读取绑定）**：静态断言读取器的字段名与契约键一致（`dsh_asar.py` 引用 `host.planes.asar.*`、`dsh_plane.py` 引用 `host.planes.precedence`），防止"契约声明了但代码没读"的假声明；这是 K-4 的同类模式，不改 28w 的"纯文件级 judge"性质（`dsh_boundary.py:1-78`）。
- **K-12**（单裁决锚）：不变（医生与边界 exit code 一致性）。
- 影响面：`dsh_boundary.py:456` allowlist 路径、`dsh_doctor.py:825` 与 `:1686` 的模板引用、`verify_workflow.py:6864` 的注入锚点（§9.4）、`injection_budget.py:114`、`behavior_profile.py:182`、`quickscan_registry.py:603`、`cleanup.py:52-56`。

### 8.3 不引入的机制

不做"契约键存在性 vs 代码读取"的运行时反射（违反 28w 纯文件级设计）；不做契约 TTL 的动态刷新；不把 28w 改成需要平面/网络的检查（`dsh-doctor --offline` 必须仍可跑）。

---

## 9. D7 可注入接缝与 fake-host 测试

### 9.1 接缝清单（端口最小化，单一职责）

| 模块（新） | 端口 | 纯函数/IO 边界 | 职责 |
| --- | --- | --- | --- |
| `dsh_plane.py` | `env: Mapping`、`fs: FsPort`、`processes: ProcessPort` | `resolve(env, fs, processes) -> [Plane]` | 优先级解析 + 身份构建；不 spawn node |
| `dsh_asar.py` | `fs: FsPort`（默认实现读真实文件） | `header(index_bytes) -> Header` 纯函数 | 头解析/条目读取/链接解析 |
| `dsh_walk.py` | `fs: FsPort`、`clock: Callable[[], float]` | `walk(root, *, fs, clock, bounds)` | 有界遍历、剪枝、预算；预算与时钟可注入（禁真实计时断言） |
| `composition_merge.py` | 无（全纯） | `merge(base_text, overlay_text, policy) -> MergeResult`；`refusal` 异常 | 行切块/替换/校验 |
| `provenance.py` | 无（全纯） | `build(...)`、`verify(installed_text, provenance) -> Verdict` | 溯源生成与残留比对 |
| `dsh_compat._run_probe` | `runner: Runner`（可注入的 `subprocess.run` 包装） | 现有 `_render_probe_script` 保留 | 执行 probe；budget/超时 |

禁止：接缝内部读 `os.environ`/磁盘（构造参数是唯一事实来源）；纯函数模块 import `os`/`subprocess`（用静态检查或 review 约束）。

### 9.2 fake-host 六类失败（验收要求）

| 类 | 场景 | 断言 |
| --- | --- | --- |
| C1 平面 | asar 头截断/魔数错；显式平面不可用；无任何平面 | `PLANE_UNUSABLE` 原因码；NOT_RUN；绝不静默回退 |
| C2 base preset | `standard.patch.yml` 缺失；条目越界；JSON 头损坏 | 对应拒装码；exit 2；`--dry-run` 也不写 |
| C3 base 行形状 | base 行缺失/重复/禁用；`plugins` 非序列；缩进漂移 | 拒绝码精确；错误信息含行号/id |
| C4 前缀/技能形状 | base prefix 为块标量/引号变体/`!!js`；`customSkillDirs` 为 flow 序列 | `PERSONA_PREFIX_UNSUPPORTED` / `SKILL_DIRS_UNSUPPORTED` |
| C5 发现 | junction 自指环（`root/sub/junction -> root`）；环 + 正常 composition 共存；深度/条目/时间超限；不可读目录 | `< 5 s` 返回且 `skipped_reparse_points >= 1`；正常 composition 仍被发现；预算用假时钟触发；`bounded_out` 只披露不 FAIL |
| C6 probe/ctx | `ctx.get` 未声明；oracle 缺 yaml/cordis/loader；probe 超时/崩溃 | 行级 UNVERIFIED 原因精确；部分证据保留；`ctx_members_used ⊆ declared` |

### 9.3 测试文件规划

- 新增：`tests/test_dsh_asar.py`、`test_dsh_plane.py`、`test_dsh_walk.py`、`test_composition_merge.py`、`test_dsh_provenance.py`。
- 扩展：`test_dsh_adapter.py`（Δ 安装、拒装码、dry-run 零写、provenance）、`test_dsh_contract.py`（v2 必填/未知键）、`test_dsh_compat.py`（行级报告 v2、部分证据、ctx 桩）、`test_dsh_doctor.py`（S1 残留/文案）、`test_dsh_boundary.py`（K-3′/K-14）、`test_dsh_native_bridge.py`（双面 parity）。
- 全部用 fixture（合成 asar 头 + fixture patch + fixture body），**不依赖本机 DSH**（R4）。

### 9.4 注入契约锚点迁移

`verify_workflow.py:6864-6878` 目前把 persona 契约关键词 + `VERSION_LINE_ANCHOR`（`:6853`）锚在 `agent.cordis.yml.template` 上；模板退场后锚点迁到 `agent-presets/governance/persona.md.template`。实测该文件已含全部关键词（`persona.md.template:8-14`：复审必达/NEEDS_CHANGE、完成必推荐/三要素、选项必带依据、审查结论必机录/review-record、真实环境必防护/三选一/逐条上报/隔离环境安装冒烟）与版本行（`:1` 的 `治理工作流（v0.99.0）`），**无需改正文**，只改注册表路径 + staged 表（`:6912-6914`）。同时 `test_review_machine_provenance.py:223`、`test_verify_workflow.py:20867, 20953` 的断言路径同步。

---

## 10. 切片计划

> 约定：每片独立可合并、可回滚；产品代码不新增第三方依赖；`verify_workflow.py` 只允许 dispatch/常量/锚点表改动（archguard R1 anchor 28,418 LOC，当前 28,543 行，新增逻辑一律进新模块；S7 合并前重测该行数并记入切片说明）；先契约后实现。**硬纪律：任何切片结束时，28w 与 `test_dsh_*` 套件必须为绿——不允许"某片期间门是红的"**（§13.4 纪律 4）。

| 切片 | 批次 | 目标 | 原子性 | 文件 | 测试 | 验收（片末绿判据） | 预估 LOC | 依赖/进入条件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | 0.99.1 | **契约 v2 加性变更**：新增全部 v2 键 + `SUPPORTED_SCHEMA_VERSIONS` 1→2；`host.rows` / `own.preset.template` **保留**并标 `deprecated_in: 2`（必填表接受"已弃用但存在"态）；**零删除、零读者切换** | 加性单 commit；回退 = revert（无数据迁移） | `host-contract.json`、`dsh_contract.py`（REQUIRED_PATHS + 弃用元数据）、`dsh_compat.py`（`_DECLARED_BINDING` 新键）、`lib/index.js`（`:277` `OWN_SCHEMA_VERSION` 1→2 一行——实施时发现的清单遗漏：该常量按其自注（`:269-275`）镜像 `SUPPORTED_SCHEMA_VERSIONS`，不升则 JS 渲染面在 schema 2 下 fail-closed；5 个 JS mutation 测试钉住） | `test_dsh_contract.py`、`test_dsh_compat.py` | 新键可读；schema 2 接受；旧键仍必填；**对外行为与今天等价**（只多能力）；`dsh_boundary.py` + `test_dsh_boundary`/`test_dsh_contract` 绿 | 180 | — |
| S1 | 0.99.1 | asar 读取 + 平面身份 | 新模块，独立 revert | `dsh_asar.py`(新)、`dsh_plane.py`(新)、`dsh_compat.locate_dsh_install` | `test_dsh_asar.py`、`test_dsh_plane.py` | 本机 asar 读出 `kind/dsh_version/header_sha256`；四平面并列；显式不可用 → NOT_RUN；片末绿 | 420 | S0 |
| S2 | 0.99.1 | **提取并泛化 FIX-484 的有限发现**（不是重新实现） | 旧实现保留至接线后；与 FIX-484 同批，`dsh_walk.py` 可单独 revert | `dsh_walk.py`(新，从 `dsh_compat.py` 抽出遍历)、`discover_compositions` 改薄适配 | `test_dsh_walk.py`(新)、`test_dsh_compat.py`（FIX-484 用例全部保留） | §10.2 的 FIX-484 回归 ①–⑤ 全绿；自指环 `< 5 s`；默认根不扫沙箱；片末绿 | 200 | S0；与 FIX-484 同批发布，禁止先删旧实现 |
| S3 | 0.100.0 | 行级覆盖 + ctx 桩 | 独立 revert（probe/聚合逻辑） | `dsh_compat.py`（probe 脚本、聚合、部分证据） | `test_dsh_compat.py` | `ctx.get` 不再炸；缺一个 oracle 只降级相关行；部分证据保留；片末绿 | 240 | S1 |
| S4 | 0.100.0 | overlay 片段 + 合并（**不删模板**） | 不删模板；回退 = 撤销 overlay/merge 与其接线 | `overlay.cordis.yml`(新)、`composition_merge.py`(新)、`persona.md.template`、`lib/index.js`（`ensurePreset` warn-only） | `test_composition_merge.py`、`test_dsh_adapter.py`、`test_dsh_native_bridge.py` | 0.2.2 base 上 merge = 22 行、prefix 与 native 字节相等（2808 仅作夹具观测）；片段静态合法；模板仍在、K-3 仍绿；片末绿 | 320 | S0、S1 |
| S5 | 0.100.0 | 安装接线 + 拒装码 + provenance | 独立；回退 = 安装路径回到旧渲染（模板仍在） | `launch.py`（`install_preset`/`render_composition`）、`provenance.py`(新) | `test_dsh_adapter.py`、`test_dsh_provenance.py` | 派生失败 exit 2 且零写；dry-run 零写；provenance 落盘且字段齐全；安装路径不再读模板但模板文件仍存在（K-3 绿）；片末绿 | 220 | S4 |
| S6 | 0.100.0 | doctor S1 残留 + 文案 + 平面身份 | 独立 revert | `dsh_doctor.py`（S1、S3 平面身份、removal 文案） | `test_dsh_doctor.py` | 29 行残留 FAIL(RESIDUAL_ROWS)；无 provenance → UNVERIFIED 宽限；文案不再提自动渲染；片末绿 | 170 | S5 |
| S7 | 0.100.0 | **退场原子切片**（一个 commit）：物理删 `host.rows` + `own.preset.template` + 模板文件；K-3→K-3′ + K-4/K-7/K-8/K-14；全部读者切换；锚点迁移；**同 commit 放宽/退役 `deprecations.entries` 非空校验**（S0 R0 nit：两键删除后空 sidecar 不得自身成为 ContractMalformed——sidecar 随键一并退场） | **唯一原子退场**：删两键 + 删模板 + K-3′ + 读者切换 + 锚点迁移同一 commit，禁止拆分 | `dsh_boundary.py`、`verify_workflow.py`、`dsh_doctor.py`、`dsh_contract.py`、`injection_budget.py`、`behavior_profile.py`、`quickscan_registry.py`、`cleanup.py`、`core/manifest.json`、`core/version-projections.json`、`contract_matrix/golden_samples.txt`、`cordis.patch.yml`、`lib/index.js`（docstring）、`adapter-manifest.json`、`adapters/dsh/README.md`、`README.md`、`infra/TOOLS.md` | `test_dsh_boundary.py`、`test_dsh_contract.py`、`test_dsh_doctor.py`、`test_dsh_adapter.py`、`test_dsh_native_bridge.py`、`test_verify_workflow.py`、`test_review_machine_provenance.py`、`test_injection_zerodrift.py` | 模板不存在 = PASS；模板重现 = FAIL；overlay 行集 == 声明；锚点在 `persona.md.template` 生效；29 常量清零；`dsh_boundary.py` + 上列套件绿 | 300 | S4、S5、S6 全绿；双平面 merge fixture 绿；doctor S1 残留用例已就位；进入前完成 §10.3 读者清单逐项核对 |
| S8 | 0.100.0 | fake-host 六类 + 旧测试收尾 | 测试与产品代码解耦，可单独 revert | `tests/*` | 全部 | 六类各 ≥1；无真实 DSH；29 常量清零 | 650（测试） | S7 |
| S9 | 0.100.0 | 证据/冒烟/版本 0.100.0 | 收尾，不改代码语义 | `preset.yml`、`.governance/`、smoke | `--smoke`、双平面 probe | 0.2.2 真实平面行级全绿 + 平面身份入证据 + 双平面 Δ parity | 120 | S8 |

产品合计约 **2,170 LOC**（S4 320 + S7 300 = 原 340 + 280，总数不变）；测试约 **1,600 LOC**。合并顺序：S0→(S1,S2)→S3→S4→S5→S6→S7→S8→S9；S2 可与 S1 并行；S6 可与 S7 的**前置核对**并行，但 S7 必须在 S6 片末绿后合入。

### 10.1 批次验收与回退点

| 批次 | 组成 | 批次验收（独立发布前必须机器通过） | 回退点 |
| --- | --- | --- | --- |
| **0.99.1** | FIX-484 + S0 + S1 + S2 | ① 门与 `python -m unittest discover -s skills/software-project-governance/infra/tests -p 'test_dsh_*.py'` 整体收敛（junction 自环不再自旋，F14）；② 28v 报告 asar 平面身份（`kind=asar-desktop`、`dsh_version=0.2.2-rc.1`）；③ 行级覆盖不再整体塌陷（`rows_enabled > 0`，部分证据保留）；④ `dsh_boundary.py` 绿；⑤ 对外行为与今天等价（S0 纯加性，只多能力与报告字段） | 回到含 FIX-484 的 0.99.0：S0 只新增键、无删除，回退无需数据/契约迁移；`dsh_walk.py` 未接线前保留旧 `discover_compositions` 实现，回退即停止注入 |
| **0.100.0** | S3…S9 | ① Δ 渲染双面 parity（prefix 字节相等、22 行、skillDirs 相等）；② 残留可判（真实 29 行残留 → FAIL(RESIDUAL_ROWS)）；③ 28w K-3′ + K-4/K-7/K-8/K-14 绿且 29 常量清零；④ 0.2.2 真实平面行级全绿 + 平面身份入证据 | ① 退场 commit 可单独 revert（模板与两个键从 `docs/` 快照恢复）；② `--legacy-render` 逃生口（R2，渲染归档快照，默认关，最多保留一个版本）；③ provenance 缺失按 UNVERIFIED 宽限一个版本（D5） |

### 10.2 S2 ↔ FIX-484：提取与泛化，不是重新实现

- **定位**：FIX-484（Developer，只改 `infra/dsh_compat.py` + `tests/test_dsh_compat.py`）先落地**最小有界扫描**；S2 把它的遍历**抽到 `dsh_walk.py` 并注入接缝**，`discover_compositions()` 退化为薄适配层。**不允许**在 S2 重写一遍遍历逻辑，也不允许先删 FIX-484 再补。
- **FIX-484 的对外语义 S2 必须原样保留**：返回类型；披露计数（`skipped_reparse_points`、`bounded_out` 及既有计数键）；`ScanBudget(max_depth/max_entries/max_seconds)`；溢出抛 `CompositionScanOverflow`；28v 把溢出映射为 `NOT_RUN` + `SCAN_OVERFLOW` 原因码（**绝不静默 PASS**）。
- **S2 新增的只有接缝**：`fs`（`scandir`/`stat`/`readlink`）、`clock`（默认 `time.monotonic`）、预算对象可注入；纯函数化后单测不依赖真实目录与真实计时。
- **S2 必须保留的 FIX-484 回归用例**（缺一视为回归）：① 自指环 `< 5 s` 返回且 `skipped_reparse_points >= 1`；② 环 + 正常 composition 共存时正常 composition 仍被发现且 `bounded_out is False`；③ 沙箱根整棵剪枝（默认根结果不含 `.governance/sandboxes` 副本）；④ 预算溢出 → `CompositionScanOverflow` → 28v `NOT_RUN`/`SCAN_OVERFLOW`；⑤ 越界/不可读的披露计数不丢失。
- **语义差异（显式声明）**：本设计的"越界只披露"指**不判 FAIL**，不等于"判 PASS"；溢出时裁决是 `NOT_RUN` + `SCAN_OVERFLOW`，与 FIX-484 完全一致。若 FIX-484 最终选择 FAIL 而非 NOT_RUN，S2 **保留 FIX-484 的选择**并回写本节差异说明——不允许含糊。

### 10.3 S7 进入条件：退场读者清单（逐项核对，缺一不合入）

| 被删对象 | 今日读者（实测） | S7 切换去向 |
| --- | --- | --- |
| `host.rows` | `checks/dsh_boundary.py:399`（K-1）、`:756`（K-3）；`dsh_contract.py:126`（必填表）、`:314-345`（校验器）；`dsh_doctor.py:1811`；`tests/test_dsh_boundary.py:353`；`tests/test_dsh_contract.py:660-703,888,915,1160,1387-1392,1929,1963` | K-1 改用 `evidence.rows_inventory`/新字段；K-3′ 不再读行清单；doctor 用 provenance 行集；测试改 overlay/merge fixture 断言 |
| `own.preset.template` | `checks/dsh_boundary.py:810,816`（组合文件名）、`dsh_doctor.py:824,1685`、`verify_workflow.py:6864-6878`、`injection_budget.py:114`、`behavior_profile.py:182`、`quickscan_registry.py:603`、`core/manifest.json:290`、`core/version-projections.json:103-105`、`contract_matrix/golden_samples.txt:94` | 一律改 `own.overlay.path` / `persona.md.template`（§13.3 全表） |
| `agent.cordis.yml.template` | K-3 的 `_read(subject.template)`（`dsh_boundary.py:748-751`：模板缺失即 FAIL）；§13.3 全部命中 | K-3′ 改为"模板不得存在"；锚点迁 `persona.md.template`；快照归档 `docs/` |

> 进入 S7 前另需实测：`verify_workflow.py` 行数锚（R1 = 28,418）与当前行数，连同 `dsh_boundary.py` + `test_dsh_boundary`/`test_dsh_contract`/`test_dsh_doctor` 的基线绿，一并记入 S7 切片说明（一个 commit 内完成删除与切换，不拆成"先删后修"）。

---

## 11. 风险与回退

| 编号 | 风险 | 触发信号 | 缓解 | 回退 |
| --- | --- | --- | --- | --- |
| R1 | 平面误判/进程探测不稳（权限、杀软、多安装） | 同一次 doctor 的 `kind` 在两次运行间变化 | 显式 env 永远优先；进程探测只在 doctor/28v 且可 `DSH_PLANE_PROBE_PROCESS=0` 关闭；身份对象全量披露 | 退回"显式 env + path"两种来源；asar 面标 UNVERIFIED |
| R2 | Δ 文本合并对 base 形状脆性（0.2.3 改缩进/引号/块标量） | 拒装码集中在 `*_UNSUPPORTED`/`INDENT_DRIFT` | 逐形状校验 + 精确拒绝码 + parity 测试 + 每版 fixture | 保留 `--legacy-render` 一个版本（渲染**当前退场的冻结模板快照**，默认关）作为逃生口 |
| R3 | 模板退场波及注入契约/28w/224 处文本引用 | `verify_workflow` FAIL 或 28w K-3′ 误伤 | 锚点先迁 `persona.md.template`（正文无需改，F12）+ S7 一个原子 commit 内完成删除与切换（§10 S7/§10.3）；K-3′ 只断言"不存在/仅两行" | 恢复模板文件并临时把 K-3′ 降级为 WARN（需 decision 记录，最多一个版本） |
| R4 | **13 条**本仓独有行退休导致能力损失（10 行实际生效全部为治理自加；另 2 行已禁用、1 行已死随退场清理，§6.2.1.1） | 用户/协调者反馈 `subagent`/`subagent_fork`/`ralph`/`workflow` 全 family 或 `plan-mode` 指令段缺失 | 退休作为 DEC-385① + DEC-386② 的显式后果入账；§6.2.1.1 逐行清单 + "包还在 ≠ 功能等价"；需要者在 native 面另立任务 | 保留旧模板快照在 `docs/` 归档，不参与安装 |
| R5 | provenance 新文件被宿主 presets 扫描拒绝（O3） | 预设加载失败/宿主报错 | S5 用真实 asar 平面冒烟；文件名/位置可经契约一键改 | provenance 移到 `${DSH_HOME}/.agent-presets/.governance/`（S1 读同一路径） |
| R6 | 仓库自中毒：junction 自指环被 `.gitignore` 掩盖，门与 `test_dsh_*` 套件同时自旋（F14） | 门/套件耗时不收敛；无子进程 CPU 高 | D3 有界遍历 + 三条强制回归（§5.4）+ 默认根收窄；测试显式构造环并带原因 skip | 保留 `skipped_reparse_points` 披露；**禁止**回退到"事后过滤"（回退即复原缺陷） |

**回退总闸**：所有新行为由契约键驱动；回退 = 契约回滚 + 模块保留未接线，不删用户文件。任何回退不得写真实 `C:\Users\peter\.dsh`（测试用 `DSH_HOME` 重定向）。

---

## 12. 不做什么（out of scope）

- 不解包 asar（`app.asar.unpacked` 只作为单条目来源）。
- 不改宿主源码/插件市场/桌面 UI；不实现自动升级。
- 不做 macOS/Linux 桌面布局（只在契约声明 Windows 实测，其余 UNVERIFIED）。
- 不清理 `.governance/sandboxes`（P7；本设计只保证发现不被其污染）。
- 不把 `_is_skipped_relative()` 搬进 `host-contract`（仓库扫描策略 ≠ 宿主事实）；不为 junction 环加"路径白名单"绕过遍历（必须真剪枝；"发现异常就全盘放弃"同样不可接受，见 §5.4）。
- 不恢复 **13 条**本仓独有行（DEC-386② 已裁决全部随模板退休，清单 §6.2.1.1）；需要者另立任务在 **native 面**实现，不回填旧路面。
- 不引入 PyYAML/js-yaml/任何第三方 Python 依赖；不为安装路径引入 node 运行时依赖。
- 不改 `verify_workflow.py` 的业务逻辑（只 dispatch/常量/锚点表）。
- 不改 `dsh_compat` 的 verdict 字符串集合（PASS/FAIL/NOT_RUN 对外契约不变），只改内部结构与原因码。
- 不写真实 `C:\Users\peter\.dsh`；不把实验产物提交进仓库（`.tmp-*` 一律清理）。

---

## 13. 实施者须知（MUST READ）

### 13.1 复验清单（实现前逐条跑，输出贴进任务评论）

| # | 复验项 | 命令/期望 |
| --- | --- | --- |
| V1 | asar 头布局与 base 路径 | §1.5 命令 → `standard.patch.yml` 6,858 B / 22 行；`prefix` 在 `:14` |
| V2 | 冻结模板在 0.2.2 FAIL | 对 `agent.cordis.yml.template` 跑真实 probe → 1 issue（死行 `tool-subagent-list-agents`） |
| V3 | native 派生零失败 | `derive022.json` 的 `ok:true, rowsWithoutIds:0, failures:[]` |
| V4 | Δ 原型 PASS | 合并产物（删 ctx 依赖行）→ `issues: []`，coverage 25/20/5 |
| V5 | `ctx.get` 缺口 | 未删行时唯一 issue 是 `TypeError: ctx.get is not a function`；改动后应消失 |
| V6 | 平面误判 | `locate_dsh_install` 今日报 0.2.1-rc.2（profile/CLI）；S1 后应报 0.2.2-rc.1（asar） |
| V7 | junction 环 | 默认根扫描 30 s 内终止；`skipped_reparse > 0` 披露；**另跑 `python -m unittest discover -s skills/software-project-governance/infra/tests -p 'test_dsh_*.py'`，必须整体收敛（F14 当前 813 s 不收敛）** |
| V8 | 残留 PASS | doctor S1 对 29 行残留今日 PASS；S6 后 FAIL(RESIDUAL_ROWS) |
| V9 | 锚点正文 | `persona.md.template` 含 `INJECTION_CONTRACT_ANCHORS` 全部关键词 + 版本行 |

### 13.2 临时环境政策

- 一切实验写 `$env:TEMP\feat113-*`；`DSH_HOME` 必须重定向；**禁止**写 `C:\Users\peter\.dsh`、禁止改真实预设目录。
- asar 只读；不复制整包；不 `npm install`；不新增依赖。
- 实验脚本一律 stdin 管道执行（`$py | python -`），不落仓库；确需落盘只进 `$env:TEMP`。
- 命令输出含中文时用 `Get-Content -Encoding UTF8` 或 `read` 工具，避免 GBK mojibake。

### 13.3 模板退场后必须同步的既有引用（真实 grep 命中，按文件）

| 文件 | 命中行（2026-11-07 实测 grep） | 处理 |
| --- | --- | --- |
| `skills/software-project-governance/core/version-projections.json` | `:103-105`（`dsh-persona-version` → 模板） | 投影目标改 `agent-presets/governance/persona.md.template`（版本行在 `:1`）；不改则版本一致性检查指向已删文件 |
| `skills/software-project-governance/core/manifest.json` | `:290`（产品文件清单含模板） | 换成 overlay + persona.md.template 两条 |
| `skills/software-project-governance/infra/contract_matrix/golden_samples.txt` | `:94`（模板作为黄金样本） | 黄金样本换 overlay 片段（产物校验见 §6.2.2） |
| `adapters/dsh/host-contract.json` | `:803`（template）、`:834-835`（leftover/形状）、`:812`（base 行名）、`:91`（globs） | S0 一次改到 v2（§8.2.1） |
| `checks/dsh_boundary.py` | `:120-122`（29 常量）、`:263`（读取）、`:456`（allowlist）、`:706-765`（K-3） | 删 29 常量；K-3 → K-3′；allowlist 路径换 overlay |
| `dsh_doctor.py` | `:824-826`、`:883`、`:942-973`（JS↔Python 差分门）、`:1685-1686` | 渲染对象换 overlay；差分门保留（它是"双渲染不可分歧"的机检锚） |
| `verify_workflow.py` | `:6864-6878`、`:6912-6914`（注入锚点）；`:359-363`、`:18353`（产品归类） | 锚点迁 `persona.md.template`；归类按新文件名 |
| `behavior_profile.py` | `:182` | 产品文件清单换 overlay |
| `checks/injection_budget.py` | `:114` | 注入预算对象换 overlay（或 persona.md.template） |
| `quickscan_registry.py` | `:299`、`:544`、`:547`、`:561`、`:603` | asset id 换 overlay |
| `cleanup.py` | `:52-56` | `.agent-presets` 删除域不变；确认无模板路径残留 |
| `cordis.patch.yml` | `:27-28`（注释描述渲染面） | 文案改"overlay 片段 + 安装期派生" |
| `lib/index.js` | `:39`、`:426`（docstring 称模板为唯一组合源） | 改述为 overlay 片段渲染器；`ensurePreset` 标 deprecated |
| `adapters/dsh/adapter-manifest.json` | `:36`（note 描述渲染路径） | 同步 Δ 口径 |
| `adapters/dsh/README.md` | `:13`、`:76` | 同步 Δ 口径 + 新环境变量 |
| `README.md` | `:32`、`:78` | 同步 Δ 口径（安装叙事） |
| `infra/TOOLS.md` | `:551`、`:586` | 命令说明同步 |
| `docs/architecture/dsh-adapter-version-decoupling.md` | `:250` | 版本投影清单改为 overlay/persona（文档变更随 S9 提交） |
| `tests/test_dsh_contract.py` | `:81`、`:94-96`、`:890-908`、`:1171`、`:1204`、`:1935-1972`；模板命中 `:356`、`:1512-1594`、`:1809`、`:1826` | 删 29 常量；`template_row_mismatches` 用例改 overlay 断言 |
| `tests/test_dsh_boundary.py` | `:363-401`、`:409-428`、`:450` | K-3′ 新用例 |
| `tests/test_dsh_adapter.py` | `:86`、`:657`、`:707`、`:998-1142`、`:1899`、`:1922-1986`、`:2057`、`:2115-2117` | 模板断言改 overlay；`ensurePreset` 断言改 warn-only；dry-run 零写 |
| `tests/test_dsh_compat.py` | `:71`、`:485`、`:2052`、`:2231`、`:2418`、`:3198`；`rows_checked` 语义 `:333-968` | 报告 v2 断言；`rows_checked==0` 规则保留 |
| `tests/test_dsh_doctor.py` | `:360-368`、`:633`、`:921-938` | S1 新增残留用例；去掉"重启渲染"预期 |
| `tests/test_dsh_native_bridge.py` | `:38`、`:533-543`、`:667-672` | 双面 parity 扩展 |
| `tests/dsh_fixtures.py` | `:45`、`:238`、`:283`、`:336`、`:454` | fixture 增加 base patch/overlay/provenance 构造器 |
| `tests/test_review_machine_provenance.py` | `:223-247` | 锚点路径 |
| `tests/test_verify_workflow.py` | `:20867-20953`、`:21939`、`:22070`、`:23704-23731` | 锚点/产品文件断言 |
| `tests/test_injection_zerodrift.py` | `:36` | 产品文件清单 |

> 实测 grep 总量 224 处命中（含 `docs/reviews/` 历史记录与归档，不入本轮改动）；上表只列"改代码就必须同步"的面。`dsh_compat.py` 本身**不直接**引用模板路径（命中全在测试里），新增的坐标一律走 `own.overlay` 契约键。

### 13.4 顺序与纪律

1. 先 S0 契约（v2 字段一次到位；**S0 是加性变更**——只新增键 + schema 升版 + 旧键标 `deprecated_in: 2`，零删除零读者切换），再实现；禁止"先写代码再补契约"。
2. 每片一个 commit，message 引用 `FEAT-113`；不混入 FIX-483 或无关格式改动。**S7 是唯一的原子退场切片**：物理删两个契约键 + 删模板文件 + K-3′ + 全部读者切换 + 锚点迁移必须在**同一个 commit** 内完成，禁止"先删后修"的中间态。
3. `verify_workflow.py` 只允许 dispatch/常量/锚点表改动；新逻辑进新模块（archguard R1 锚 28,418 LOC；S7 前重测行数并记入切片说明）。
4. **片末绿判据（硬）**：每片结束时必须同时为绿——① `python skills/software-project-governance/infra/checks/dsh_boundary.py`；② `python -m unittest` 跑本片触碰的 `test_dsh_*` 套件（S0/S1/S2 至少 `test_dsh_boundary` + `test_dsh_contract`；S7 加 `test_dsh_doctor`/`test_dsh_adapter`/`test_dsh_native_bridge`/`test_verify_workflow`）；③ 涉及安装路径时 `--smoke`。**任何"本片期间门是红的、下一片修复"的安排一律不接受**；做不到就扩大本片范围或前移依赖（这正是 S7 合并删键/删模板/换读者的原因）。
5. 0.99.1 必须能独立发布且全绿（S0 不做任何删除或读者切换，对外行为与今天等价、只多能力）。
6. 不提交 `.tmp-*`、`__pycache__`、提取的 asar 副本。
7. 任何"契约声明了但代码没读"或"代码读了但契约没声明"的差异，按 R3 处理（大声失败，不静默）。

---

## 14. 机器可检查验收（对应 FEAT-113 验收口径）

| 验收 | 机器检查 | 切片 |
| --- | --- | --- |
| 0.2.2 真实平面行级全绿 + 平面身份入证据 | 28v report v2：`plane.kind=asar-desktop`、`dsh_version=0.2.2-rc.1`、`failed==0`（死行消失后）；evidence 含平面身份 | S1/S3/S9 |
| Δ 渲染在双平面上声明 | 对 asar 面与磁盘 fixture 面各跑一次安装+probe；provenance 的 `plane.kind` 两条不同 | S4/S5 |
| 用户根残留漂移可检出 | doctor S1 对 29 行残留 → `FAIL(RESIDUAL_ROWS)`；注入一行额外行同样 FAIL | S6 |
| fake-host 覆盖六类失败 | `tests/test_dsh_*.py` 中 C1-C6 各 ≥1；不 spawn 真实宿主 | S8 |
| junction 自指环不阻断门与套件 | S2 回归三连（§5.4）：<5 s 返回、环 + 正常 composition 共存仍被发现、假时钟触发预算；默认根结果不含沙箱副本 | S2 |
| 3 条不变式机器记录 | K-10 输入 fixture 产物仍校验 `insert 必带 id`/`payload 可克隆`/`不写 .cordis` | S7 |
| 模板不再携带宿主行（静态守卫） | K-3′：模板文件不存在；overlay 行集 == 声明；无 `!!js` | S7 |
| 旧路面与 native 同一治理正文 | `test_dual_face_parity`：prefix 字节相等、skillDirs 相等 | S4 |
| 每片片末门绿（§13.4 纪律 4） | 每片末 `dsh_boundary.py` + 本片触碰的 `test_dsh_*` 套件 PASS；不存在"某片期间门是红"的中间态 | S0-S9 |
| 双批次独立可发布 | 0.99.1（FIX-484+S0+S1+S2）：门/套件收敛 + 平面身份 + 覆盖不塌陷，对外行为等价；0.100.0（S3-S9）：Δ 双面 parity + 残留可判 + 29 常量清零 | 0.99.1 / 0.100.0 |

---

## 附录 A：实测输出摘要（只读证据，非提交物）

- `derive022.json`：`ok:true`，`presetId: governance`，`baseRows:22`，`derivedRows:22`，`personaPrefixBytes:2808`，`skillRoots:[<repo>/skills, <repo>/adapters/dsh/skill-shims]`，`rowsWithoutIds:0`，`disabledRows:["tool-plugin-market"]`，`failures:[]`。
- `compat022.json`：`verdict: FAIL`，1 issue（`tool-subagent-list-agents`），`rows_enabled:23`、`rows_verified:19`、`rows_unverified:3 (NO_SCHEMA)`。
- 行差：模板 29 行 vs 0.2.2 base preset **22 行** → 本仓独有 **13**、base 独有 **6**、共有 **16**（13+22=29+6 ✓）；与用户根 33 行组合比较会多出 1 行包装行 `preset-standard`，故旧稿"7 条宿主独有"不矛盾，但口径以 base 行集为准（F5）。模块漂移 0。
- Δ 原型：145 行 / 8,490 B；`!!js` 3 处保留；persona prefix 2,808 B；真实 probe 两次对照（含 ctx 依赖行 FAIL / 删除后 PASS，coverage 25/20/5）。
- 有界发现：10.36 s、8 条 composition、`skipped_reparse=336`。
- 用户根残留：29 行，含死行（只读，未修改）。

## 附录 B：术语

- **平面（plane）**：一个可执行的宿主安装形态（asar 桌面面、磁盘 node_modules 面、profile 提升面、PATH shim 面）。
- **base preset**：宿主自带的预设声明（0.2.2 为 `web-app/presets/standard.patch.yml` 中 `insert` 行的 `config.plugins`）。
- **Δ 合并渲染**：治理 overlay 片段 + 安装期从 base 派生的宿主行 → 完整 composition；不是把宿主行冻结进包。
- **provenance**：安装期写出的渲染溯源（平面/版本/行集/哈希），供离线残留检测。

---

## 15. 评审记录

**评审时间**：2026-11-07；**评审人**：协调者（实测 + 裁决）、架构师（修订）；**结论**：Accepted（DEC-386，`.governance/decision-log.md`）。实现按 §10 两批推进（0.99.1 / 0.100.0）。

| # | 评审发现 | 处置 | 落点 |
| --- | --- | --- | --- |
| 1 | F5 行差低估：旧稿"多 3 条治理独有行 / 缺 7 条宿主新行"只覆盖部分行；实测模板独有 **13**、base 独有 **6**（以 22 行 base 行集为基准；33 行组合另含包装行 `preset-standard`） | 全部更正；补 13 行逐行清单；明确"包还在 ≠ 功能等价" | §1.1、§1.3 F5、§6.2.1.1、§11 R3/R4、§12、附录 A |
| 2 | O5 未闭合（0.2.1 磁盘面是否有 base patch） | 实测闭合：6,799 B / 22 行，id 序列与 0.2.2 asar 6,858 B / 22 行相同；派生在**双平面**成立 | §1.4 O5、§6.2.2 |
| 3 | O4/O7 待决策（13 行去留、删键批准） | DEC-386② 裁决：13 行全退、删 `host.rows` + `own.preset.template`、schema 1→2、模板快照归档 `docs/` | §1.4 O4/O7、§6.2.1.1、§8.2.1、§12 |
| 4 | 交付节奏未分段 | DEC-386③：0.99.1 = FIX-484+S0+S1+S2；0.100.0 = S3-S9；各批次独立验收 + 回退点 | §0、§10.1 |
| 5 | 切片原子性缺陷：旧表 S0 删键、S4 删模板会让 S0-S6 全红（K-1 `dsh_boundary.py:399`、K-3 `:748-751`、doctor `:1811`、契约必填表 `dsh_contract.py:126/314-345` 等读者未切换） | S0 改为**纯加性**（保留两键 + `deprecated_in: 2`，必填表接受"已弃用但存在"态）；物理删两键 + 删模板 + K-3′ + 全部读者切换 + 锚点迁移合并为 **S7 退场原子切片**（一个 commit），排在 S4/S5/S6 之后 | §8.2.1、§10 S0/S7、§10.3、§13.4 |
| 6 | S2 与 FIX-484 可能重复实现 | S2 = **提取与泛化**（抽 `dsh_walk.py` + 注入接缝），保留 FIX-484 对外语义与 **5 类回归用例**（§10.2 ①–⑤）；同批 0.99.1 发布；语义差异显式声明 | §10、§10.2 |
| 7 | persona body 派生与 native 不对齐（body 不是文件直塞；旧稿公式 `body.trimEnd()` 与契约 `body_trim: true` 矛盾） | 按 `lib/dsh-native/persona.js:38-50` + `overlay.js:115-120` 写 **5 步规则**（读→CRLF 归一→token→posix 包根替换→全 trim/空判/残留扫描→拼接）；契约 `own.render.persona_prefix` 补 11 字段；`2808` 只作测试夹具观测值 | §6.2.2、§6.2.2.1、§8.2.1 |
| 8 | 切片表缺批次列 / 片末绿判据 / S7 进入条件；`verify_workflow.py` 行数锚未前置复核 | 表加「批次」「验收（片末绿判据）」列；补 §10.1 批次验收与回退点、§10.3 S7 读者清单；§13.4 纪律硬化为"不允许某片期间门是红的"；S7 前重测 R1 行数锚（28,418） | §10、§13.4、§14 |

**本稿仍标"未验证"的项**（不阻塞 Accepted，阻塞对应切片合入，见 §1.4）：O1 进程祖先探测（未实现、未测试）、O2 macOS/Linux 布局（只声明 Windows 实测）、O3 宿主对 `render-provenance.json` 的容忍度、O6 `DSH_PROFILE_DIR` 未进契约；另 F8 `doctor-default.json` 版本串（`0.2.1-rc.2`）需在 S1 落地前复核一次。
