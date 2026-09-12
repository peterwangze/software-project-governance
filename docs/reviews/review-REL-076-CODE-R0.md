# REVIEW-REL-076-CODE-R0 — 0.80.0 候选代码面审查（release 窗口新增/重写代码）

- **Task**: REL-076 · **Round**: 3（rounds 0/1/2 分别为 Release / Design 面，占用不冲突——FIX-314 已登记 `(task, round)` 键限制）
- **Reviewer**: Code Reviewer
- **审查对象**: `v0.79.0..HEAD`（HEAD = `5a259e2`）+ 暂存候选（33 staged / 0 untracked）
- **`git write-tree`** = `88915ed2606154219561c3828f23dbf390b4dbe2` ✅ 与简报一致（审查开始、审查中、审查结束三次核对；审查期间本 reviewer 未修改任何产品文件）
- **结论**: **APPROVED_WITH_NOTES**，`unresolved_blockers=0`

## 0. 审查范围与方法

| 代码面 | 提交 | 本次审查做的事 |
|---|---|---|
| `lib/index.js`（新增 231 行，5a259e2） | FIX-310 | 全文精读 + 12 组 `node --input-type=module` 探针（真实模块、重定向 `DSH_HOME`、临时包副本） |
| `adapters/dsh/launch.py`（重写 +276/−，5a259e2） | FIX-310 | 全文精读 + CLI 行为矩阵实跑（dry-run/install/sync/uninstall/smoke/错误码） |
| `skills/.../infra/dsh_compat.py`（新增 1224 行，94c0a61；5a259e2 改 15 行） | FIX-309 | 全文精读 + 真实安装面探针（`--json`、伪造 probe 报告、ghost builtin、缺 Config 的 plugin） |
| `registry.py` / `contracts.py` / `quickscan_registry.py` / `quickscan_selector.py` 本窗增量 | FEAT-021/022/025/026 + FIX-303/304/305 + 5a259e2 | 只审本窗改动面：退役扇出（`check-dsh-skills-manifest`/Check 40/`presets/`）、注释计数、死代码、导出面 |
| 测试 | `test_dsh_adapter.py`(46) / `test_dsh_compat.py`(43) / `test_registry.py`(77) / `test_contracts.py`(99) / `test_quickscan_registry.py`(82) / `test_quickscan_selector.py`(43) | 逐个模块实跑 + 读断言体 + 清点 skip 条件 |

**未做的事（按简报硬规则）**：未跑全量 unittest、未跑 `check-release` 执行门。全量冻结基线（`Ran 2675 / failures=35 / errors=1 / skipped=1`，记录于 `docs/release/release-checklist-0.80.0.md:75`）未被触碰。

**外部只读事实源**（本机安装态，用于代码级比对）：`@deepseek-ai/dsh-home-paths@…/lib/index.js`、`@deepseek-ai/dsh-agent-presets@0.1.5-rc.2`、`@deepseek-ai/cordis-plugin-loader`、`@deepseek-ai/cordis-plugin-include`、`@deepseek-ai/dsh-app-boot`、`@deepseek-ai/dsh-plan-mode`、`dsh-home-paths` 参考实现。

**审查期间的过程披露**：`resolveDshHome` 输入矩阵探针中，相对路径输入（`relative/dir`、`~nonexistent/x`）按代码语义在仓库工作区生成了两个临时目录；已立即删除并复核 `git status --porcelain --untracked-files=all` 恢复为 33 条 / 0 untracked、`git write-tree` 仍为 `88915ed…`。（如实记录，非产品变更。）

---

## 1. 逐项裁决

### 1.1 `lib/index.js`：正确性、健壮性、契约

| 检查项 | 裁决 | 证据 |
|---|---|---|
| 导出面 / 宿主行形态（`name`/`apply` 具名导出，无 default） | **PASS** | 探针 `moduleExports = ["apply","ensurePreset","name","renderComposition"]`；loader 侧 `unwrapExports`（`cordis-plugin-loader/lib/index.js:746-751`）`exports.default ?? exports`，与同类插件同形（`dsh-skill-filesystem/lib/index.js:880` 同为具名导出）；`package.json` `type: module` + `main/exports` 指向 `lib/index.js` ✓；patch `insert` 无 `id` → `data.push(...insert)`（`dsh-app-boot/lib/index.js:84-85`）✓ |
| `renderComposition()` 参数/返回契约 | **PASS（附 F3）** | 返回 `{text, leftovers}`；`leftovers` 仅覆盖 3 个已知 token（见 F3） |
| `ensurePreset()` 返回值契约 `{synced, dir, version}` | **PASS** | 探针两条路径（首装 `synced:true`、版本相同 `synced:false`）均符合 docstring；`dir` 为最终用户根 |
| 幂等（版本标记） | **PASS** | 首跑写 4 文件；二跑 `synced:false`、`agent.cordis.yml` mtime 不变（`test_dsh_adapter.py:1203-1211` 亦断言）；跨路径：`launch.py --install`（写 CRLF 标记 `0.80.0\r\n`）→ JS `readFileSync(...).trim()` 判定相 ⇒ `synced=false`（实跑实证） |
| `leftovers` 未解析 token 路径 | **F3** | 全局替换 ⇒ 已知 token 不可能残留（`leftovers` 恒空）；拼错/未知 token **不被任何一侧检出**（探针：`__GOVERNANCE_SKILLS_ROOTS__` → `leftovers: []`，原样写盘） |
| `packageVersion()` 回退 `'0'` | **F5** | 探针：package.json 不可读 → 写标记 `0`；**再跑 `synced:false`（掩盖式跳过，不是无谓重建）**；package.json 恢复后 `7.7.7` ≠ `0` → 重建 ⇒ 掩盖窗口以「package.json 持续不可读」为界 |
| `rmSync`/`renameSync` 顺序与失败窗口 | **F4/F6** | 见 §2 详述 |
| `catch` 是否可能留下 `.staging-*` | **F4（实测确认）** | 见 §2 详述 |
| 是否存在能从 `apply()` 抛出的路径 | **F2（实测确认，违反自身契约）** | 见 §2 详述 |
| `resolveDshHome()` 对 `''`/`'~'`/`'~/x'`/`'~\\x'`/相对/尾分隔 的输入 | **PASS**（6/6 与参考实现逐字相同）；**例外见 F7** | 探针对照安装态 `@deepseek-ai/dsh-home-paths.resolveDshHome(undefined,{DSH_HOME:v})`：`''`、`'   '` → `$HOME/.dsh`；`'~'` → `$HOME`；`'~/x'`、`'~\\x'` → `$HOME/x`；相对 → `resolve(cwd)`；尾分隔 → 归一化；`'~nonexistent/x'` → 字面相对（与参考一致）。全部 `match:true` |

### 1.2 渲染器 parity（JS vs Python）——**代码级确认：字节一致**

| 检查项 | 裁决 | 证据 |
|---|---|---|
| token 集合恒等 | **PASS** | JS `TOKEN_PATHS` 三键 == Python `TOKEN_PATHS` 三键（探针打印 sorted keys 相同；顺序 SKILLS→SHIMS→REPO 亦相同） |
| 绝对路径拼写（POSIX 斜杠、repo 根无尾分隔符） | **PASS** | JS `packageRoot()` 显式 `replace(/[\\/]+$/,'')` + `posixPath()`；Python `str(path.resolve()).replace('\\','/')` |
| **产物字节一致（含 CLI 写盘路径）** | **PASS（决定性）** | 三条独立路径 sha256 全等 `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`：(a) JS `ensurePreset` 写出的 `agent.cordis.yml`（16651 B / 13566 chars，`crlfCount=0`）；(b) Python `render_composition()` 文本 UTF-8 编码；(c) `launch.py --install` 实际写出的文件 |
| 换行处理 | **PASS** | 模板实测纯 LF（16651 B，0 CRLF / 0 裸 CR / 272 LF）；`.gitattributes` 未锁 `*.template`，`core.autocrlf=true` 下工作树可能为 CRLF ⇒ JS 的 `\r\n→\n` 归一化与 Python universal-newlines 是**承载性**逻辑，两侧都会归一 ✓ |
| FIX-313（裸 `\r` 分歧）— 确认还是否定 | **确认（代码级），但为 latent** | JS `'a\rb\r\nc'` → `"a\rb\nc"`（裸 CR 保留）；Python 同一输入 → `"a\nb\nc …"`（裸 CR→LF）。触发条件 = 模板含**裸 CR 字节**：实测当前模板 `bare CR = 0`，故不触发。登记状态与 DESIGN-R0 一致 |
| 跨根稳定性（DESIGN-R0 U-3） | **否定（本 reviewer 实证）** | 经 Windows junction 导入 `lib/index.js`：`import.meta.url` 报**真实路径**（Node ESM 默认解析符号链接），渲染出的 `<plugin_root>` 与经同一 junction 导入的 `launch.py`（`Path.resolve()`）**相同** ⇒ U-3 的「两条路径可能写入不同绝对路径」在同一 `link:` 场景下不成立（仅 `--preserve-symlinks` 下会分歧，dsh 不传该参数） |

### 1.3 `launch.py`

| 检查项 | 裁决 | 证据（实跑） |
|---|---|---|
| `--install` 与 `--sync` 同旗标 | **PASS** | `parser.add_argument("--install","--sync",dest="install")`（L848-854）；两命令输出与产物 sha256 相同 |
| 幂等 | **PASS** | 连跑 `--install`/`--sync`：exit 0、文件 sha 不变 |
| 路径逃逸守卫 | **PASS（守卫存在但结构上不可达）** | L298：`target.parent.name != ".agent-presets" or target.name != PRESET_ID` → 1；由于 `preset_dir()` 由两个字面量拼装，该条件在当前实现下恒假（P3 注记，非缺陷） |
| `--uninstall` 删除范围 | **PASS** | 隔离 home 实跑：`governance` 消失；`sibling-preset/preset.yml`、`settings.yaml` 均保留；二次运行（已缺失）→ exit 0 幂等 |
| `--dry-run` 真不写盘 | **PASS** | `--install --dry-run`：exit 0，写面前后目录快照**逐项相同**（`home_changed=False`） |
| `--smoke` 隔离 | **PASS** | 实跑：`real-home writes : 0 (witness unchanged)`；exit 0；`DSH_HOME` 未设 → `REFUSED (exit 2)`；`--smoke` 与 install/uninstall/bootstrap/dry-run 组合 → argparse exit 2。witness 口径（仅 `.agent-presets` 递归 + 顶层）与 docstring 自述一致，非全 home 保证 |
| 错误路径 exit code | **PASS** | `--install --uninstall` → 2；`--smoke --install` → 2；`--bootstrap-project <不存在>` → 1（清晰 ERROR）；smoke PASS=0 / FAIL=1 / REFUSED=2 |
| Check 28v 接线（`_validate_composition_rows`） | **PASS（降级正确）** | `--smoke` 实跑输出：`row schemas : PASS (23 enabled row(s) validated against the installed dsh; 18 …)`；缺模块/异常 → `NOT_RUN` + reason（L542-559） |

### 1.4 `dsh_compat.py`

| 检查项 | 裁决 | 证据 |
|---|---|---|
| 是否真的不内嵌 schema 副本（FIX-309 赖以成立的性质） | **PASS（独立确认）** | `PROBE_SCRIPT`（L182-441）从**解析出的安装面**导入 `entryListSchema`/`evaluate`/`isJsExpr`/`resolveConfig`/`js-yaml`（L209-227）；全文**无** schema 字面量、无 `prefix`/`text`/属性名表、无 fallback 表（grep 命中仅 docstring 与 import 点）。唯一邻近的 fallback（`launch.py:534-541`）直接落 `NOT_RUN`，不可能影响 PASS。安装态 persona 声明 `prefix: z.string().required()`，实跑负对照 `text:` → FAIL `$.prefix missing required value` ✓ |
| node/dsh 缺失时降级 | **PASS** | 全部早退路径（L876-880 无 composition / 882-889 install≠OK / 891-898 无 node / 907-914 probe≠OK / 916-924 `ok:false`）均 `NOT_RUN`；`rows_enabled==0` → `NOT_RUN`（L1005-1019，fail-closed）；不含 stdout 解析 ⇒ 空/非 JSON stdout 无法伪造 PASS |
| 真 mismatch 是否可能静默 PASS | **F1（否定：存在一条 PASS 路径）** | 见 §2 F1 —— `NO_SCHEMA` 行不计 finding、不计入 `rows_checked`，而 `rows_enabled>0` 时整体仍 PASS |
| 未处理异常 / 输入校验 | **F8** | `UnicodeDecodeError` 逃出公共入口并泄漏 2 个临时目录（实测）；`compositions=[<不存在>]`/`[<目录>]` → `NOT_RUN` 但 reason 归因错误（实测） |

### 1.5 测试质量（是否真断言 / skip 条件）

| 模块 | 断言真实性 | 关键 skip 条件 |
|---|---|---|
| `test_dsh_adapter.py`（46，实跑 OK/15.9s） | **真断言**：parity 测试比对 JS 与 Python 全文 + `leftovers==[]` + returncode（L1127-1156）；`ensurePreset` 断言 4 文件齐备 + 二跑 mtime 不变（L1158-1211）；warn-only 断言「无 payload → 不抛 + 不残留」 | `shutil.which("node")` 三处：L1133-1135（渲染器 parity）、L1164-1166、L1217-1219（宿主行本体）；另有 bash 门（L525/558）与 PyYAML 门（L1258） |
| `test_dsh_compat.py`（43，实跑 OK） | **真断言 + 真负对照**：负对照把 `text` 形状判 FAIL（L562-577）、真实组合判 PASS；聚合契约用注入报告覆盖 FAIL/部分未验证 PASS/NOT_RUN（L301-453） | `_HAS_YAML`（L60 → 5 例 @L515）；模块级 `_LIVE_INSTALL,_LIVE_NODE = _live_probe()`（L602）门控 **14 例**（L611/636/654/680/718/735/742/753/777/804/825/841/856/870）；`skipTest` L532/L538 |
| `test_registry.py` / `test_contracts.py` / `test_quickscan_registry.py` / `test_quickscan_selector.py` | **真断言 + 负对照**（含 live 引擎 AST 归属、冻结快照恒等、dispatch 字节等价 test_quickscan_selector.py:359-371） | 四模块**零 skip**（grep 无 `skipUnless/skipIf/skipTest`）；环境依赖以硬失败呈现 |
| **node-less 机器上的实际后果** | — | `lib/index.js` 的**全部**覆盖（3 例）被 skip；parity 机检契约被 skip；`dsh_compat` 的 14 例 live oracle（含 persona `text` 回归网）被 skip ⇒ **打包预设的宿主行路径在无 node 机器上零覆盖** |

**测试缺口（与 F1/F2 直接相关）**：
- `test_dsh_adapter.py:1213` 断言「永不抛」的用例**只覆盖 payload 缺失**一种失败模式（且 `env = os.environ.copy()` 继承环境），**不覆盖** F2 实际抛出的 `homedir()` 场景 ⇒ 该契约被断言而非被验证。
- `test_dsh_compat.py:365-375` 把「`rows_checked==0` 仍 PASS」当作正确行为固定下来（与 F1 同一根因）。

### 1.6 死代码 / 残留

| 项 | 裁决 | 证据 |
|---|---|---|
| `presets/` 退役在**产品代码**中是否干净 | **PASS** | 仅 `.governance/` 历史记录与历史版本文档含 `presets/governance`；产品代码命中全部为 `agent-presets/`（前缀排除后 0 命中）。`adapters/dsh/preset.yml`、`adapters/dsh/agent.cordis.yml.template` 已不存在且无活跃引用 |
| `--mode copy` | **PASS（已闭环）** | 仅存于历史文档 `docs/marketplace/dsh-preset-adapter-0.73.0.md:36,53`，且 L36 已有 0.80.0 更正框（DESIGN R0 F10 处置） |
| `check-dsh-skills-manifest` 扇出 | **PASS** | `DSH_SKILLS_DISK_PATTERNS` / `_REJECT_SECURITY_DETAIL` 在 `infra/*.py` 中 **0 次出现**；CLI 键已从 `registry.py` 移除；其余命中均为历史 CHANGELOG/review 文档 |
| `launch.py` 的 `!!js`/`baseUrl` 解析分支 | **F10（死代码）** | `_resolve_skill_entry` 的 `raw.startswith("!!js")` 分支（L478-488）+ `urllib.request`/`urljoin`/`urlparse` 导入（L78/80）**仅**由该分支消费（L486-487 是全文唯一使用点）；FIX-310 后本包所有 composition 的 `customSkillDirs` 均为渲染后的字面绝对路径，`test_dsh_adapter.py` 只保留 `assertNotIn("baseUrl"/"!!js")` 反向断言 ⇒ **无生产调用方、无测试调用方** |
| `test_dsh_compat.py` 重复测试 | **F11** | `_PRESET_COMPOSITION` 与 `_TEMPLATE_COMPOSITION` 在 FIX-310 后指向**同一文件**（L57-59），`test_shipped_preset_persona_row_*` 与 `test_shipped_template_persona_row_*` 因此成为同一文件的重复断言 |
| `registry.py` 计数注释与代码自相矛盾 | **F12** | 代码 `COMMAND_SPECS=82` / `CHECK_SPECS=70`（实测），注释 L7「83 dispatch keys」、L8/L44「71」、L342「83」、L345「79 ride the monolith」（实际 78），而 L421 已改为「70 segments」 |
| Check 40 退役后的文档面残留 | **F13** | `quickscan_registry.py:10-24` 声明 `docs/requirements/quickscan-evaluation-0.79.0.md` §3.1 C1 为设计事实源；实测该 doc L134 的 C1 列表**含 40、不含 28v**，而 `excluded_ids()` = 25 段**含 28v、不含 40**（`test_quickscan_registry.py:59,66` 的「26 段」/「24 段」亦与 25 不符） |
| `registry.verify_registration` 对重复观察去重 | **F14** | 实测注入重复观察（`web-console` ×2 / 段 `39` ×2）→ `missing/extra` 全空 + `ok=True`；`_diff` 走 `set()`，无同族模块 `quickscan_registry._reject_duplicate_check_ids` 的零容忍守卫（仅注入面可达，live 面为 dict keys ⇒ 唯一） |
| `dsh_compat.COMPOSITION_FILENAMES` | 观察项 | 仅 `__all__` 引用，无消费者（P3 级，未单列 finding） |

### 1.7 交叉复核（并行 subagent 报告项，**未由本 reviewer 独立复现**）

以下为并行复查线程报告、且本 reviewer **未**亲自复现的条目，供处置参考，**不计入**本报告的 finding 计数：`baseUrl` 作用域取文件 URL 而非 loader 的目录 URL（`dsh_compat.py:433` vs 安装态 `cordis-plugin-include/lib/index.js:138` `new URL(".", pathToFileURL(filename))`；我已核实两侧代码事实，**未**复现其 !!js 探针）；未知 `cordis:*` builtin 无条件 PASS（我已独立核实：`dsh_compat.py:343-347` 不查注册表，loader 侧 `builtins[name.slice(7)]`（`cordis-plugin-loader/lib/index.js:271`）、dsh 仅注册 `include`/`group`（`dsh-app-boot/lib/index.js:1323,1334`），本包 3 行 `cordis:group` 合法 ⇒ 该洞对本包为 latent）；`!!js` 在 node 内**执行**组合内容（与 `_run_probe` 的 `eval` 语义一致，属 loader 对齐的必然，docstring L51-52「read-only static analysis」措辞未提示「校验即执行」）；10KB argv 超出 cmd.exe 8191 限制（`.cmd` 形态 node shim 将恒 NOT_RUN）；`quickscan_selector` 空普查 → `quick_available=True`、`mode=="full"` 分支不可达与覆盖率缺口。

---

## 2. Findings（P1 / P2 / P3）

### F1 — P1 — Check 28v 可对「安装态插件自己会拒绝的 config」返回 PASS（false-green）

- **文件/行**: `dsh_compat.py:371-376`（`NO_SCHEMA` 不入 `FINDING_KINDS`，见 L117-124）、`979-991`（NO_SCHEMA 只进 `details`）、`1005`（仅 `rows_enabled==0` 降级，`rows_checked==0` 不降级）、`1021`（PASS）；`launch.py:566`（`schema_checked = verdict != "NOT_RUN"`）；docstring `dsh_compat.py:71`（「PASS = every enabled row validated」）
- **命令与观测（本 reviewer 实跑）**：
  - 出厂组合：`python skills/software-project-governance/infra/dsh_compat.py --json` → `verdict PASS / enabled 23 / checked 18 / issues []`，其中 **5 行 NO_SCHEMA**：`plan-mode`、`command-compact`、`tool-subagent-control`、`tool-subagent-list-agents`、`tool-ask-user`（23−18=5 与逐行诊断一致）
  - 构造组合（`- id: plan-mode / name: '@deepseek-ai/dsh-plan-mode' / config: {bogusKey: 1}`）→ **`verdict PASS / enabled 1 / checked 0 / issues []`**
  - 同一配置交**安装态插件自己的**校验器：`node … @deepseek-ai/dsh-plan-mode/lib/index.js` → `exports Config? false`，`plugin validator: REJECTED -> PlanModeConfig needs a string \`section\``（该模块 `lib/index.js:58`，导出面 L412 确无 `Config`）
- **性质**：探针把 NO_SCHEMA 行标注为「the loader passes this config through unvalidated」——对 `dsh-plan-mode` 一类**自带校验器、不导出 `Config`** 的插件，该表述为**假**。于是护栏对 5/23 行零覆盖，同时输出 `PASS` 与 `schema_checked=True`，与 docstring L71 的「every enabled row validated」不符。
- **诚实边界**：①覆盖缺口以**数字**披露（reason 与 `docs/release/release-checklist-0.80.0.md:78` 的「enabled 23 / schema-checked 18」都已写出），故这不是「零行校验仍绿」的静默假绿；②`unknown`：本 reviewer **未**真机启动会话验证「plan-mode 坏 config 是否会否决挂载」（已证：插件校验器抛错；loader 在该行构造插件时传入 config）。据 ①B 的严重度口径（兄弟轮 F-1「假绿 I/O 机判」= P1），本条按 P1 登记。
- **建议最小修复**：`rows_checked == 0` 视同 `NOT_RUN`；NO_SCHEMA 行改判为「未验证披露」而非事实上的通过；对导出 `resolveConfig`/构造校验的插件补一条校验回退路径。

### F2 — P2 — `apply()` 存在可从宿主行抛出的路径（违反本模块明写的失败契约）

- **文件/行**: `lib/index.js:105`（`join(homedir(), '.dsh')`）经 `180-183` 在 **try 之外**（`try` 自 L184 起）被调用；`219`（catch 内再次解引用 `ctx.logger`）
- **命令与观测（实跑）**：
  - 清空 `USERPROFILE/HOMEDRIVE/HOMEPATH/HOME` 且 `DSH_HOME` 未设：`node -e "…m.apply({logger})"` → **`apply() THREW: SystemError: A system error occurred: uv_os_homedir returned ENOENT`**；同环境 `os.homedir()` 单独调用亦抛同错
  - 新鲜 home + `apply(undefined)` → **`THREW: TypeError: Cannot read properties of undefined (reading 'logger')`**（成功路径 L217 抛 → catch L219 再抛）
- **性质**：模块头 L50-53、`docs/release/release-checklist-0.80.0.md:57`、`feature-flags-0.80.0.md:23` 均把「失败只 warn、绝不抛」作为**已交付事实**陈述；DESIGN-R0（其 L159）明确以「`resolveDshHome()` 只碰 env 字符串」为由排除该风险——**本条为对该判断的代码级否证**。
- **可达性（如实）**：`dsh --version` 在同样剥离的环境下**正常退出**（实测），但 profile boot 必须解析 home 才能定位 profile/组合层，故真机上宿主多半先失败（推断，非实证 ⇒ 见未知 U-1）。`apply(undefined)` 变体经 Cordis 不可达（宿主总传 ctx），但说明「catch 自身可抛」使该保证**非结构性**。修法为两行：把 `packageVersion()`/`resolveDshHome()`/`join()` 移入 try，catch 内改用可选链 + 兜底。

### F3 — P3 — `leftovers`（未解析 token）契约是空转的：已知 token 不可能残留，未知 token 不被检出

- **文件/行**: `lib/index.js:154-162`；`launch.py:150-155`
- **证据（实跑）**：`renderComposition('A __GOVERNANCE_SKILLS_ROOT__ B __GOVERNANCE_REPO_ROOT__ C','D:/p')` → `leftovers: []`（`split/join` 全局替换，已知 token 必被替换）；`renderComposition('customSkillDirs:\n  - __GOVERNANCE_SKILLS_ROOTS__\n','D:/p')` → 原样保留且 `leftovers: []`。Python 侧同构（`str.replace` + 同一 `any(token in …)` 检查）。
- **后果与网**：拼错 token 会在**开机路径**被静默写进用户预设（`synced: true`、零告警）；下游网仍在——`verify_preset_loading` 对同一预设判 **FAIL**（实测：`customSkillDirs entry is a literal relative path … (FIX-290)`），但 Check 28v 自身对该行判 PASS（schema 只要求字符串）。故属于「护栏层级不一致」而非无网。

### F4 — P3 — JS `catch` 不清理自身 `.staging-*`（实测确认，DESIGN-R0 F9 / 登记 FIX-313）

- **文件/行**: `lib/index.js:207-215`（写入 staging）→ `218-220`（catch 只 warn，无 `rmSync(staging)`）；对照 Python `launch.py:264,266` 失败即 `rmtree`
- **证据（实跑）**：以副本包（payload 的 `preset.yml` 为目录，令 `cpSync` 在 `agent.cordis.yml` 已写入后抛错）运行 → `logs: WARN … preset sync failed`，`.agent-presets/` 下**残留** `governance.staging-1789179016920-oim6ey`。同次运行中旧预设（sentinel）因失败发生在 L214 之前而**存活**。
- **量级**：已独立核实 `@deepseek-ai/dsh-agent-presets/lib/index.js:105` `PRESET_ID = /^[a-z0-9][a-z0-9-]*$/` + L403 以该正则过滤子项 ⇒ 含 `.` 的残留目录**不会**出现在预设 roster（纯磁盘残留，非 UX 缺陷）。

### F5 — P3 — `packageVersion()` 回退 `'0'` 是「掩盖式跳过」，不是无谓重建

- **文件/行**: `lib/index.js:128-135`、`197`
- **证据（实跑）**：package.json 删除后首跑 `{synced:true, version:"0"}` 且标记写为 `0`；再跑 **`{synced:false}`**（早退）⇒ 掩盖窗口 = package.json 持续不可读期间；恢复后版本号不等 → 立即重建。`launch.py:125-131` 同值同源，两侧一致。
- **风险**：低（需 package.json 不可读或版本字段缺失），且不产生重建抖动；仅当「不可读期间载荷已变化」才会留下陈旧预设。

### F6 — P3 — `rmSync` → `renameSync` 是「有窗口的替换」而非原子交换（**未复现**，代码顺序推断）

- **文件/行**: `lib/index.js:214-215`；同构 `launch.py:270-272`
- **说明**：`rm` 成功后 `rename` 若失败（Windows 上对目录持句柄/杀软干预等），该轮**无预设**且仅 warn；下一轮启动因标记随目录一并消失而重建（自愈）。本 reviewer **未能构造** rename 失败的可复现用例 ⇒ 按代码顺序推断登记，与 DESIGN R0 F9 同向。模块自身措辞（「can never leave a half-rendered preset」）准确，仅发布文档的「原子」措辞偏强。

### F7 — P3 — `DSH_HOME` 前后带空白时，内联 `resolveDshHome()` 与参考实现/`launch.py` 三方分歧

- **文件/行**: `lib/index.js:102-110`（`fromEnv.trim()`）
- **证据（实跑对照安装态参考实现）**：输入 `'  <path>  '` → 本模块（经 `ensurePreset().dir` 观测）解析为 **`<path>/.agent-presets/governance`**（已 trim、按绝对路径处理）；`@deepseek-ai/dsh-home-paths.resolveDshHome(undefined,{DSH_HOME:'  <path>  '})` → `<cwd>/  <path>  /.agent-presets/governance`（**不 trim**，字面相对路径）；`launch.py` 用 `Path(env).expanduser()`（同样不 trim）。`match:false` 是 10 个输入中**唯一**的不一致。
- **性质**：docstring L92-97 声称「Mirrors `resolveDshHome()` from `@deepseek-ai/dsh-home-paths`」——参考实现只把「全空白」当未设（`fromEnv.trim().length > 0` 仅作判断，值原样传递），本实现额外 trim 了**值**。后果：带空白 `DSH_HOME` 时，bundle 自动路径与 `--install` 手工路径会写入**不同目录**，「两条交付路径不可能分歧」在该输入下不成立（其余输入实证一致）。严重度低（需用户设置带空白的 `DSH_HOME`，且该环境本身已令宿主解析异常）。

### F8 — P2 — `UnicodeDecodeError` 逃出 `dsh_compat` 公共入口，并泄漏 2 个临时目录

- **文件/行**: `dsh_compat.py:797-802`（`except OSError` 不含 `UnicodeDecodeError`；`_remove_scratch_dir` 在 raise 之后）；调用点 `verify_workflow.py:16300-16302`（`all_issues += emit_check_section()` **无 try/except**）
- **证据（本 reviewer 实跑）**：`issubclass(UnicodeDecodeError, OSError) = False`；以伪造 `subprocess.run` 写出截断 UTF-8 报告 → **`entry point RAISED: UnicodeDecodeError`**，`%TEMP%` 下 `spg-dsh-compat*` 目录 **4 → 6**（新增 `spg-dsh-compat-0051aecc973b`、`spg-dsh-compat-home-abd3bbf9385a`）。
- **可达性**：正常运行由 Node 写 UTF-8 JSON，不会触发；触发需报告文件被截断/损坏（崩溃、磁盘满、进程被杀）。一旦触发，`check-governance` 引擎整体中止（调用点无保护）＋ 临时目录泄漏。建议：`except (OSError, UnicodeDecodeError)` + 清理入 `finally`。

### F9 — P3 — 组合不可读时 `reason` 归因错误（真实原因仅存 `details`）

- **文件/行**: `dsh_compat.py:961-965`（UNREADABLE → `unverified`/details）与 `1005-1015`（`rows_enabled==0` 分支先触发）
- **证据（实跑）**：`_validate_composition_rows(<不存在路径>)` 与 `(<目录>)` 均得 `NOT_RUN` + `reason = "no enabled preset row could be validated — every row of 1 composition(s) is disabled (0 inherited from a disabled ancestor), so this preset would mount nothing"`——真实原因（文件不可读）只在 `details`。裁决仍 fail-closed（非假绿），仅诊断误导。

### F10 — P3 — FIX-310 遗留死代码：`launch.py` 的 `!!js`/`baseUrl` 分支及其唯一消费者导入

- **文件/行**: `launch.py:478-488`（分支）、`486-487`（唯一使用点）、`78/80`（`urllib.request`、`urljoin`/`urlparse`）
- **证据**：FIX-310 后本包 composition 的 `customSkillDirs` 为渲染后字面绝对路径（模板 L100/104 的 `!!js` 仅用于 `disabled`）；`verify_preset_loading` 的调用方只有 `--smoke`（两处均为新渲染产物）与手写测试；`test_dsh_adapter.py` 对该形态只剩**反向**断言（L227 `assertNotIn("baseUrl", generated)`、L463 `assertNotIn("!!js", code_text)`）⇒ 无生产调用方、无测试调用方。

### F11 — P3 — `test_dsh_compat.py` 两个测试在 FIX-310 后成为同一文件的重复断言

- **文件/行**: `test_dsh_compat.py:54-59`（`_PRESET_COMPOSITION = _TEMPLATE_COMPOSITION = agent-presets/governance/agent.cordis.yml.template`）、`545-551`（两个测试方法）

### F12 — P3 — `registry.py` 注释计数与代码/自身相互矛盾（FIX-310 退役后未同步）

- **文件/行**: `registry.py:7`（83）、`:8`（71）、`:44`（71）、`:342`（83）、`:345`（79）、`:347`（71） vs `:421`（70）；实测 `COMMAND_SPECS=82`（78 引擎内 + 4 引擎外）、`CHECK_SPECS=70`

### F13 — P3 — 被声明为权威事实源的文档仍含已退役 Check 40、缺新增 28v

- **文件/行**: `quickscan_registry.py:10-24`（声明 `docs/requirements/quickscan-evaluation-0.79.0.md` §3.1 C1 为设计事实源 + 与 `_PLUGIN_PRODUCT_CHECK_IDS` 恒等）；doc L134；`test_quickscan_registry.py:59`（26 段）、`:66`（24 段）
- **证据（实跑）**：doc C1 列表 `40 → True`、`28v → False`；`qr.excluded_ids()` = 25 段，`28v → True`、`40 → False` ⇒ 机制恒等成立但文档面滞后一轮（FIX-309 加 28v、FIX-310 退 40 均未回写）。

### F14 — P3 — `registry.verify_registration()` 静默去重重复观察（与兄弟模块零容忍口径不一致）

- **文件/行**: `registry.py:907-909`（`_diff` 过 `set()`）vs `quickscan_registry.py:711-727`（`_reject_duplicate_check_ids`）
- **证据（实跑）**：`verify_registration(observed_cli_keys=keys+['web-console'], observed_segment_ids=segs+['39'])` → `missing_keys=() extra_keys=() missing_segments=() extra_segments=()` 且 `ok=True`。live 面为 dict keys（唯一）⇒ 仅注入/冻结面可达，非活体漏检。

---

## 3. Skip 条件与「因此未被测试」清单

| 位置 | 条件 | 被跳过而**无替代覆盖**的行为 |
|---|---|---|
| `test_dsh_adapter.py:1133-1135` | `shutil.which("node")` 为空 | JS/Python 渲染器 parity 契约（0.80.0 的核心机检契约） |
| `test_dsh_adapter.py:1164-1166` | 同上 | 宿主行 `ensurePreset` 在用户根渲染 + 幂等（`lib/index.js` 的**唯一**覆盖） |
| `test_dsh_adapter.py:1217-1219` | 同上 | warn-only / 不抛 / 不残留（仅覆盖 payload 缺失一种模式） |
| `test_dsh_compat.py:602 → 611,636,654,680,718,735,742,753,777,804,825,841,856,870` | `locate_dsh_install().status=="OK"` 且 `which("node")`（**模块导入期求值**） | 14 例 live oracle：`PROBE_SCRIPT` 全部语义、persona `text` 回归负对照、group 继承/`disabled` 表达式/CONFIG_INVALID 提取等 |
| `test_dsh_compat.py:60 → 515` | `importlib.util.find_spec("yaml")` | 5 例纯 Python 结构地板（组合行形状负/正对照） |
| `test_dsh_adapter.py:525/558` | bash（`shutil.which("bash")` 或 Git bash 路径） | hook 侧 shell 行为（非本窗新增） |
| 四模块（registry/contracts/quickscan×2） | **无 skip** | — |

结论：**无 node 的机器上，`lib/index.js` 与「两渲染器字节一致」这条机检契约完全无覆盖**；`dsh_compat` 只剩注入式聚合测试（真实 schema 面 0 覆盖）。

---

## 4. 未知（未能证实/证伪）

- **U-1**：F2 的 `homedir()` 抛出在**真实 dsh boot** 中是否会先于宿主自身解析失败而触发——`dsh --version` 在剥离环境下正常（实测），profile boot 的解析顺序未实证。故 F2 的实机可达性未知（契约违反本身已实证）。
- **U-2**：F1 中「plan-mode 坏 config 会否决整棵预设挂载」的**用户可见后果**未真机验证（已证：插件自有校验器抛错、loader 在该行构造插件时传入 config）。
- **U-3**：`:970-978` 关于「quick-scan 读取器把 `[WARN]` 计为 issue token」的注释是否成立（并行线程找不到该读取器；本 reviewer 未裁决）。
- **U-4**：`dsh_compat.locate_dsh_install` / `_profile_planes` 在 pnpm `.pnpm` 布局下的安装面选择是否恒等于运行中 dsh 的 plane（本机 `profiles/node_modules` 为指向 npx 安装树的 junction，恰为同一 plane；换布局未验）。
- **U-5**：`.cmd`/`.bat` 形态 node shim 下 10 KB argv 是否必然超出 cmd.exe 8191 限制（并行线程以 simulant 观察，本 reviewer 未复现）。
- **U-6**：`agent-presets/governance/agent.cordis.yml.template` 在 `core.autocrlf=true` 且无 `eol` 锁定的前提下，用户新克隆的工作树是否确为 CRLF（本机工作树实测纯 LF；结论已按「两种情形两侧均归一」表述，不依赖该项）。
- **U-7**：本报告 §1.7 所列并行复查项中未由本 reviewer 复现者（`baseUrl` !!js 探针、`.cmd` argv、selector 空普查/`mode=="full"` 不可达与覆盖率数字）。

---

## 5. 结论

- **未发现 P0**：无数据损坏路径、无假定的安全边界突破、无构建/装配级破坏；0.80.0 的核心新契约**「两条渲染路径产物字节一致」经三条独立路径 sha256 全等证实**（含 `--install` 实际写盘），且 `lib/index.js` 在 junction（`link:` 安装）场景下与 `launch.py` 取到同一包根（DESIGN R0 U-3 就此否定）。
- **1×P1 + 2×P2 + 11×P3** 登记；其中 F1（护栏对 5/23 行零覆盖且可对「插件自拒的 config」报 PASS）与 F2（`apply()` 可抛，否证「绝不抛」这一被三处文档陈述的事实）为最需要处置的两条；F4/F5/F6/F7 与 DESIGN R0 的 FIX-313 邻域同向，本报告给出执行级证据。
- 既有审查结论中**需要更正**的两点：①DESIGN-R0 L159「`resolveDshHome()` 只碰 env 字符串 ⇒ 无抛出风险」——被 F2 否证；②DESIGN-R0 U-3（跨根路径稳定性）——被 junction 实测否定。
- **裁决**：**APPROVED_WITH_NOTES**（与 `REVIEW-FEAT-025-CODE-R0`「P1×1 + P2×2 + P3×n → APPROVED_WITH_NOTES」先例同口径：findings 全部登记处置，不构成发布阻塞）。

unresolved_blockers=0
