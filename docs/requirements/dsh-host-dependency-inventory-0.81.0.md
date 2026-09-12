# DSH 宿主依赖面全量清点与兼容性缺口诊断（0.81.0）

| 项 | 值 |
|---|---|
| Task | **AUDIT-153**（P1） |
| 报告版本 | 0.81.0 |
| 生成日期 | 2026-09-13 |
| 仓库 | `D:/AI/agent/claude/coding/project_management_workflow` |
| HEAD | `d87ead845ff8c641ceebf52890c9232d1404aeb2`（`git status --porcelain` 空 = 清洁树） |
| 插件版本 | `0.80.0`（`package.json:4`；`lib/index.js` `PRESET_MARKER` 实测 `0.80.0`） |
| 性质 | **只清点与诊断。不设计方案、不改任何产品代码。** 本文件是本次唯一写入。 |
| 上下文 | REQ-146 / REQ-147 / REQ-148 / REQ-149（`.governance/plan-tracker.md`）；RISK-050；DEC-187 I-1/I-2/I-3；DEC-188 |

> **P1 事实纪律声明**：本报告第 1~6 节的每条技术断言都附 `文件:行号` 或「命令 + 退出码 + 输出片段」证据。
> 凡只能靠推断而未能执行的结论，一律下沉到**第 7 节事实/假设分离表**并标注 `未验证` + 验证计划。
> 凡无法在本次环境执行的面，一律标 `NOT_RUN` + 原因。
> 文档与代码不符处，本报告**以代码与实测为准**并单列指出（见 D-15、D-16、D-46、D-47 及第 5 节）。

---

## 1. 清点范围声明

### 1.1 安装态 dsh 事实（本次探针的实际目标）

| 事实 | 值 | 证据 |
|---|---|---|
| `$DSH_HOME`（环境） | `C:\Users\peter\.dsh` | `"DSH_HOME=[$env:DSH_HOME]"` → `C:\Users\peter\.dsh` |
| `$DSH_HOME`（真实目录） | 存在，含 `.agent-presets`, `attachments`, `backups`, `dsh-agent-router`, `llm-deepseek`, `profiles`, `sessions`, `storages`, `.anonymous-user-id`, `.credentials.yaml`, `settings.yaml`, 2 个 `settings.yaml.bak-*` | `Get-ChildItem -Force "$env:USERPROFILE\.dsh"` |
| `dsh` 可执行 | `C:\Users\peter\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\node_modules\.bin\dsh.ps1` | `Get-Command dsh` |
| **安装态 `@deepseek-ai/dsh` 版本** | **`0.1.5-rc.1`**（npx 树） | `node_modules\@deepseek-ai\dsh\package.json` → `version 0.1.5-rc.1` |
| profiles 镜像版本 | `0.1.5-rc.1` | `~/.dsh/profiles/node_modules/@deepseek-ai/dsh/package.json` |
| profiles 目录 | `node_modules/`、`web/` | `Get-ChildItem -Force ~\.dsh\profiles` |
| profile `web` 声明本包 | 是 | `~/.dsh/profiles/web/package.json:9` `"@peterwangze/software-project-governance-plugin"`，`:18` `"link:D:/AI/agent/claude/coding/project_management_workflow"` |
| node | `v24.13.1` | `node --version` |
| python | `3.14.3`（MSC v.1944 64 bit） | `python -c "import sys; print(sys.version)"` |
| 唯一解析平面（Check 28v 实测） | `$DSH_HOME/profiles` → `C:\Users\peter\.dsh\profiles\node_modules` | `dsh_compat.py --json` → `install.source` / `install.node_modules` |
| oracle 包实测版本 | `@deepseek-ai/cordis@4.0.2`、`cordis-plugin-include@1.0.7`、`cordis-plugin-loader@1.0.3`、`js-yaml@4.3.2` | 同上 `install.oracle_packages`（四者 `path` 均落在 npx 树） |
| `other_planes` | `[]`（无离面） | 同上 |

> **说明（重要）**：`client 提示` 给出的 DSH 检出路径 `C:\Users\peter\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\` 与本次 cwd 不同；本报告只把它当作**待检查的安装态代码**，未用它推断 cwd。

### 1.2 实际读取的仓库文件

| 文件 | 用途 |
|---|---|
| `package.json` | dsh 声明面 |
| `cordis.patch.yml` | 补丁层语义 |
| `lib/index.js`（全 249 行） | 宿主行模块 |
| `agent-presets/governance/agent.cordis.yml.template`（全 272 行） | 组合单一事实源 |
| `agent-presets/governance/preset.yml` | 预设元数据 |
| `adapters/dsh/launch.py`（全 924 行） | 手动/离线交付路径 |
| `adapters/dsh/adapter-manifest.json` | 适配层声明 |
| `adapters/dsh/skill-shims/governance.md` | 薄投影（9 个 shim 同构，抽验 1 个） |
| `skills/software-project-governance/infra/dsh_compat.py`（全 1224 行） | 护栏主体 |
| `skills/software-project-governance/infra/registry.py`（180-449） | Check/命令注册 |
| `skills/software-project-governance/infra/verify_workflow.py`（按需区间 + grep 全量命中） | Check 28u/28v 接线 |
| `skills/software-project-governance/infra/checks/projection.py` | Check 28b |
| `skills/software-project-governance/infra/cleanup.py`（30-99） | `PLUGIN_SCOPE_DIRS` |
| `skills/software-project-governance/infra/tests/test_dsh_adapter.py`（按需区间 + grep 全量命中） | 适配层测试 |
| `skills/software-project-governance/infra/tests/test_dsh_compat.py`（grep 全量命中） | 护栏测试 |
| `skills/software-project-governance/infra/tests/test_contracts.py`（552-596） | 陈旧行号证据 |
| `skills/software-project-governance/infra/hooks/{pre-commit,commit-msg,post-commit}` | dsh 路径发现 |
| `skills/software-project-governance/core/manifest.json` | canonical 产物 + 版本投影清单 |
| `skills/software-project-governance/core/version-projections.json`（28 行） | dsh 版本投影 |
| `.governance/plan-tracker.md` / `risk-log.md` / `decision-log.md` | 上下文（**未修改**） |

**读取的宿主侧文件（只读）**：`~/.dsh/profiles/web/{package.json,cordis.patch.yml,cordis.yml}`、`~/.dsh/.agent-presets/governance/*`、npx 树内 `@deepseek-ai/{dsh,dsh-app-boot,dsh-home-paths,dsh-skill-filesystem,dsh-agent-presets,dsh-persona,dsh-plan-mode,dsh-command-compact,dsh-tool-subagent-control,dsh-tool-ask-user,js-yaml,cordis,cordis-plugin-loader,cordis-plugin-include}` 的 `package.json` / `lib/index.js` 命中区间。

### 1.3 实际执行的命令（关键项）

1. `python skills/software-project-governance/infra/dsh_compat.py --json` → **exit 0**，`verdict: PASS`
2. `python -m unittest discover -s …/infra/tests -p "test_dsh_adapter.py"` → **`Ran 43 tests … OK`**
3. `python -m unittest discover -s …/infra/tests -p "test_dsh_compat.py"` → **`Ran 43 tests … OK`**
4. `python skills/software-project-governance/infra/verify_workflow.py check-dsh-preset-smoke` → **exit 0**，`real-home writes: 0`，`Result: PASSED`
5. `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync` → **exit 0**，`Mirrored files checked: 15`，`Result: PASSED`
6. `node`（`--eval` / `.mjs`）对 `lib/index.js` `renderComposition` 的定向探针（隔离临时目录）
7. `node` 对 `lib/index.js` `ensurePreset` 的定向探针（`DSH_HOME` + `USERPROFILE`/`HOME` 三重定向到临时目录）
8. `python` 定向探针：伪造组合 YAML → `dsh_compat.check_dsh_preset_compat`（隔离临时目录）
9. `node` 探针：从安装态平面 `createRequire` 解析真实包并读 `exports.Config`

### 1.4 未覆盖 / 未执行的范围（诚实声明）

| 未覆盖面 | 原因 |
|---|---|
| `dsh plugin add/remove --profile <name>` 冒烟 | 会写 `$DSH_HOME/profiles/web/{package.json,pnpm-lock.yaml}` 与 pnpm 存储 = 用户真实环境写操作；本任务**未预授权 incidents 留痕文件**，且三选一未成立 → `NOT_RUN` |
| `dsh --profile web --dump-config` 前后逐字节对比（DEC-187 机检判据 I-1） | 同上（需要 dsh 组合一次完整 boot，且 `dump-config` 会触碰 profile 平面）→ `NOT_RUN` |
| live LLM 会话行为 | **设计上就是 `NOT_RUN`**，见 `launch.py:790-793` 自述与 `verify_workflow.py:6863-6865` |
| macOS / Linux 宿主行为 | 本次仅在 Windows（`process.platform === 'win32'`）实测 |
| npm registry 发布的包 vs 本地 `link:` 安装 | 本机 profile 用 `link:`（`~/.dsh/profiles/web/package.json:18`），**未测 npm 安装形态** |
| 其它 5 个适配器（claude/codex/gemini/opencode/chrys）的 dsh 交互 | 不在本任务范围 |

### 1.5 破坏性红线遵守声明

- 对安装态 dsh（npx 缓存、`$DSH_HOME`）**全程只读**；未删除/清空/重建/移动用户任何配置目录。
- 所有构造性测试的写入目标均在 `C:\Users\peter\AppData\Local\Temp\audit153_*` 与 `Temp\audit153_3f4eeca5\*`。
- `lib/index.js` `ensurePreset` 探针在 `DSH_HOME` + `USERPROFILE` + `HOME` 三重定向后运行；探针结束后复查真实 `~/.dsh/.agent-presets` 内容 = `governance, novel-writing`，**与探针前一致**（未变化）。
- `dsh_compat` 探针自带的隔离机制实测生效：`isolation.home_writes: 0`，`temp_home` 稳定指向 `%TEMP%` 下一次性目录（`dsh_compat.py:757-758, 773, 801-802`）。
- `launch.py --smoke` 经 `verify_workflow.py check-dsh-preset-smoke` 以**临时 `DSH_HOME`** 调用（`verify_workflow.py:6823-6826`），实测 `Exit code: 0; real-home writes: 0; temp DSH_HOME: C:/Users/peter/AppData/Local/Temp/spg-dsh-smoke-… (removed)`。

---

## 2. 依赖点全量清单

**依赖方向**：本表全部为**正向**（本插件消费 dsh）。**未发现任何反向依赖**（宿主指向本插件的引用只出现在用户 profile 的声明里，属于 dsh 的安装机制而非我们的代码）。

**编号说明**：`D-nn`；「必要性」= `可消除` / `可弱化` / `必要`；「失效后果」= `静默失效` / `致命` / `降级`。

### 2.1 包声明面（`package.json`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-01 | `package.json:41-45` | config 键 `dsh.bundle.patch` → `./cordis.patch.yml` | **必要** | 静默失效（该键缺失 ⇒ 本包不会进入 profile `bundles` 列表 ⇒ 宿主行永不加载 ⇒ 预设永不渲染；不报错） | `dsh` 值 = `{"bundle":{"patch":"./cordis.patch.yml"}}`；`python -c` 解析断言 |
| D-02 | `package.json`（**不存在**） | config 键 `dsh.profile` / `dsh.profile.bundles` | **可消除** | 无（本包从不声明它） | `python -c` → `has dsh.profile: False`；`top-level keys: [..., 'dsh']`；真实声明在 `~/.dsh/profiles/web/package.json:5-13`（**profile 侧**，不是本包侧） |
| D-03 | `package.json:19-20` | `type: module` + `main: lib/index.js` | **必要** | 致命（`type` 非 `module` ⇒ `lib/index.js` 的 ESM `import` 语法在 CJS 下解析失败 ⇒ 宿主行 import 抛错 ⇒ 该行加载失败） | 实测导出面 = `[ 'apply', 'ensurePreset', 'name', 'renderComposition' ]`，与 loader `unwrapExports` 期望的「具名导出、无 default」同形（`docs/reviews/review-REL-076-CODE-R0.md:33`） |
| D-04 | `package.json:24-27` | `exports` 映射 `.` → `./lib/index.js` | **必要** | 致命（Node ESM 解析 `@peterwangze/software-project-governance-plugin` 时无 `exports` 命中 ⇒ `ERR_PACKAGE_PATH_NOT_EXPORTED`） | 同上；探针用绝对 `file://` URI 绕过，故**未正向实测 exports 解析** → 见 R-07 |
| D-05 | `package.json`（**不存在**） | `peerDependencies` | **可消除→但需求 REQ-147 要求补齐** | 降级（今天无声明 ⇒ dsh 升级后 npm 不提示不兼容；即「无版本闸门」） | `python -c` → `peerDependencies present: False`；`dependencies`/`devDependencies` 同样 `False` |
| D-06 | `package.json:28-40` | `files` 白名单（含 `lib/`、`agent-presets/`、`adapters/dsh/`、`cordis.patch.yml`） | **必要** | 致命（白名单漏项 ⇒ 发布包缺 `cordis.patch.yml` 或模板 ⇒ 渲染失败/`dsh.bundle.patch` 指向不存在的文件） | `files` 解析实测含 `lib/`、`agent-presets/`、`skills/`、`commands/`、`agents/`、`adapters/dsh/`、`cordis.patch.yml`、`README.md`、`LICENSE` |
| D-07 | `package.json:21-23` | `engines.node >= 20` | **可弱化** | 降级（仅 npm 警告，不阻断） | `engines` 解析实测 `{'node': '>=20'}` |
| D-08 | `package.json:3` | 包名 `@peterwangze/software-project-governance-plugin`（与 profile 声明、patch 行 `name:` 三方耦合） | **必要** | 致命（三处任一改动而其余未同步 ⇒ 行解析不到模块） | `package.json:3` == `cordis.patch.yml:43` == `~/.dsh/profiles/web/package.json:9`；三者实测字面一致 |

### 2.2 补丁层语义（`cordis.patch.yml`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-09 | `cordis.patch.yml:41-43` | YAML/JS 语义：`insert:` **无 `id`** ⇒ 追加到根 entry 列表 | **必要** | 致命（语义变更 ⇒ 本行被当作「id 定向」而报 `patch: id is required for non-insert patches`，或落进某个 group ⇒ 预设渲染时机/效果改变） | 安装态 `dsh-app-boot/lib/index.js:59,71-85`：`const { id, insert, name, ...overrides } = patch;` → `L85: } else data.push(...insert);`（无 `id` 走这支） |
| D-10 | `cordis.patch.yml:8-40`（注释声明）+ 文件内容 | 不变量：零 `- id: <host row>` UPDATE 行 | **必要（DEC-187 I-1 硬约束）** | 致命（一旦有 UPDATE ⇒ 侵入宿主行为，直接违反用户裁定） | 非注释行扫描：`- id:` 命中 **1** 处（`L42: - id: governance`，即本包自己的插入行）；`insert:` 1 处；`!!js` **0** 处；`trust:` **0** 处 |
| D-11 | `cordis.patch.yml:30` | 版本引用：`installed dsh 0.1.5-rc.2` | **可弱化** | 静默失效（引用失真 ⇒ 读者以为已按 rc.2 校验） | **文档≠事实**：安装态实测 **`0.1.5-rc.1`**（npx 与 profiles 镜像均同）。见 D-15 同源问题 |
| D-12 | `cordis.patch.yml:4-5` | 语义：`dsh plugin --profile <name> add` 依 `dsh.bundle.patch` 把本包加入 profile 的 `bundles` | **必要** | 静默失效（该机制变更 ⇒ 自动注册链断，只有 `--install` 手动路径仍可用） | 结果态可见：`~/.dsh/profiles/web/package.json:9` 已含本包；**触发过程未执行**（见 1.4）→ R-06 |

### 2.3 宿主行模块（`lib/index.js`）—— ctx API 面与写入面

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-13 | `lib/index.js:247-249` | `apply(ctx)` 导出形态（Cordis 行契约） | **必要** | 致命（`apply` 缺失/签名不符 ⇒ 行不生效） | 实测导出面 `['apply','ensurePreset','name','renderComposition']` |
| D-14 | `lib/index.js:198, 210-212, 226, 237` | `ctx.logger.warn/info`（**唯一** `ctx.*` 用法） | **可弱化** | 降级（`ctx.logger` 缺失已被可选链吞掉 ⇒ 静默无日志） | 代码行扫描：host-plane `ctx.*` 调用 **0** 处；`ctx?.logger?.warn` / `ctx?.logger?.info?.` 共 4 处 |
| D-15 | `lib/index.js:92-93` | 文档引用 `@deepseek-ai/dsh-home-paths`（安装态 `0.1.5-rc.2`）作为 `resolveDshHome()` 镜像对象 | **可弱化** | 静默失效（引用失真掩盖真实分歧） | **文档≠事实**：安装态为 `0.1.5-rc.1`；且镜像并不精确 —— 见 D-16 |
| D-16 | `lib/index.js:101-111` | **内联** `DSH_HOME` 解析（非 import，刻意复制上游语义） | **可弱化（应改为复用/能力探测）** | 静默失效（解析落点与宿主不一致 ⇒ 写到宿主不读的目录，预设不可见） | 见第 5 节 G-06 的逐 case 实测：`lib/index.js` 在 `DSH_HOME="C:/tmp/x "` 上与上游分歧；上游 `dsh-home-paths/lib/index.js:73-75` 的 `expandHomePath(configured ?? …)` **不 trim**，而本模块 `trim()` |
| D-17 | `lib/index.js:105, 192` | `homedir()`（`node:os`）→ `~/.dsh` 回退 | **必要** | 致命（`homedir()` 抛出且 `DSH_HOME` 未设 ⇒ 无法定位宿主 home） | 实跑：`homedir()` 返回 `C:\Users\peter`；清空 `USERPROFILE`/`HOME` 后仍返回 `C:\Users\peter`（Windows 走 OS API） ⇒ **抛错分支未复现** → R-03 |
| D-18 | `lib/index.js:192` | 文件/目录路径 `${DSH_HOME}/.agent-presets/governance` | **必要** | 致命（路径变更 ⇒ 预设不在宿主扫描根内） | 上游实测：`dsh-agent-presets/lib/index.js:195 const USER_PRESET_DIR = ".agent-presets"`；`:182 const COMPOSITION_FILE = "agent.cordis.yml"`；`:1300 this.resolvedRoots = [` |
| D-19 | `lib/index.js:41-48` + `:206` + `:221` | `ensurePreset` 幂等标记 `.dsh-bundle-version`（内容 = 包版本号） | **必要** | 降级（标记语义变更 ⇒ 每次 boot 重写预设；不致命但破坏「第二次 boot 不重写」契约） | 实跑三步：run1 `{"synced":true,…,"version":"0.80.0"}`；run2（同版本）`{"synced":false,…}`；run3（把标记改成 `0.0.0-stale`）`{"synced":true,…}` |
| D-20 | `lib/index.js:80, 222` | 文件路径 `${DSH_HOME}/.agent-presets/governance/skill-root.txt`（宿主行与 git hooks 的契约） | **必要** | 静默失效（该文件缺失 ⇒ 已安装项目的 git hook 找不到 workflow home ⇒ hook 静默退化为 no-op） | 写入方 `lib/index.js:222`；读取方 `hooks/post-commit:29,32`、`hooks/pre-commit:70,73`、`hooks/commit-msg:122,125` |
| D-21 | `lib/index.js:28-32 注释` vs `:83-87` | token 契约 `__GOVERNANCE_SKILLS_ROOT__` / `__GOVERNANCE_SHIMS_ROOT__` / `__GOVERNANCE_REPO_ROOT__` | **必要** | 致命（token 集不一致 ⇒ 渲染出含字面 token 的组合 ⇒ `customSkillDirs` 指向不存在的目录 ⇒ 目录静默为空） | `lib/index.js:83-87` `TOKEN_PATHS` 三键 == `launch.py:100-107` 三键；实测两渲染器输出 sha256 全等（第 2.7 节） |
| D-22 | `lib/index.js:216-224` | 写入原子性语义：staging 目录 + `renameSync` | **可弱化** | 降级（`renameSync` 失败 ⇒ 本次不更新，旧预设保留 + staging 由 catch 清理） | 实跑 run3 后 `staging leftovers: []`（catch 清理生效）；**但 catch 的清理目标存在 CWD 退化路径** → 见第 5 节 G-04 |
| D-23 | `lib/index.js:50-53, 227-238` | warn-only 契约：`apply()` 永不抛（throw 会拖垮整个 dsh boot） | **必要** | 致命（若改为抛出 ⇒ 单个插件问题导致宿主无法启动） | `:227 catch (error)` → `:237 ctx?.logger?.warn(...)`；`:184-187` 注释明示 |

### 2.4 组合模板（`agent-presets/governance/agent.cordis.yml.template`）逐行依赖面

**该文件命名了 22 个 dsh 包/子路径、5 个 group 行、6 个 `cordis:group`/内联行 id、1 个 `!!js` 表达式、2 个 token 位置、3 个 config 键。逐条如下。**

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-24 | `:46` | 包名 `@deepseek-ai/dsh-persona` | **必要** | 致命（行 config 校验失败即否决整棵预设挂载） | 实测 `Config=YES`（导出 `["Config","PERSONA_PREFIX_SECTION","PERSONA_SUFFIX_SECTION","apply","inject","name"]`） |
| D-25 | `:48` | config 键 `prefix`（`dsh-persona` 必填） | **必要** | 致命（正是 RISK-050 的 FIX-308 实证：`text`→`prefix` 变更致 `entries=0`） | 反向对照实测：`prefix` 缺失 → `CONFIG_INVALID: $.prefix missing required value` |
| D-26 | `:49` | token `{{model}}` / `{{cwd}}`（宿主 persona 插值） | **必要** | 降级（插值消失 ⇒ persona 文本残留字面 `{{model}}`） | `:49` 原文；**行为未实测** → R-08 |
| D-27 | `:51, 87` | token `__GOVERNANCE_REPO_ROOT__`（组合模板内出现 **2** 次：`:51` persona 正文 + `:87` 升级指引） | **必要** | 致命（未替换 ⇒ persona 内残留字面 token） | 实测 `agent.cordis.yml.template` 内 `__GOVERNANCE_REPO_ROOT__` 计数 = **2**（`:51` 正文、`:87` 指引；另 `:42` 为注释提及）。**注意**：`test_dsh_adapter.py:652` 的 `count == 1` 断言读的是 **`adapters/dsh/AGENTS.md.template`**（`:651` 明确赋值），该文件实测计数 = **1**（`:7`）—— 两文件不同，断言与产物**一致无矛盾** |
| D-28 | `:90` | 包名 `@deepseek-ai/dsh-agent-instructions` | **必要** | 致命（同 D-24） | 实测 `PASS`（`rows_checked` 计入） |
| D-29 | `:92` | config 键 `maxBytes` | **必要** | 致命或静默（schema 变更 ⇒ 拒绝或忽略） | 实测 `PASS` |
| D-30 | `:98-104` | 行 id `tool-bash` / `tool-pwsh`；包名 `@deepseek-ai/dsh-tool-bash` / `-tool-pwsh` | **可弱化** | 降级（平台判定变更 ⇒ 平台侧无 shell 工具） | `:100` `disabled: !!js process.platform === 'win32'`；`:104` `!!js process.platform !== 'win32'`。本机 win32 ⇒ `tool-bash` 被跳过、`tool-pwsh` 计入 |
| D-31 | `:100, 104` | **`!!js` 表达式 ×2**（`process.platform`） | **可弱化** | 降级（`!!js` 方言变更 ⇒ 表达式不求值，"disabled" 恒真/恒假） | 护栏实测 `DISABLED_EXPR_ERROR` 路径可用（伪造抛错表达式 → FAIL）；`dsh_compat.py:236` `isJsExpr` → `evaluate` |
| D-32 | `:108-114` | 包名 `@deepseek-ai/dsh-tool-fs` / `-tool-fs-search`；config 键 `sampleOverCapGlobResults` | **必要** | 致命（schema 收紧即拒绝） | 两者实测 `PASS` |
| D-33 | `:118-119` | 包名 `@deepseek-ai/dsh-tool-jobs` | **必要** | 致命 | 实测 `PASS` |
| D-34 | `:131-136` | 行 id `skill-filesystem`；包名 `@deepseek-ai/dsh-skill-filesystem`；**config 键 `customSkillDirs`（本插件 skill 目录注入的唯一通道）** | **必要** | 静默失效（`customSkillDirs` 键改名/语义变更 ⇒ 目录不注册 ⇒ skill 目录静默为空、`/governance` 手势消失 —— 模板 `:21-23` 自述这是「documented live-regression class」） | 上游实测 `dsh-skill-filesystem/lib/index.js:36 customSkillDirs: z.array(z.string()).default([]);`、`:79 .map((root) => resolve(root))`（⇒ 相对路径按 dsh 进程 CWD 解析，模板 `:17-20` 的绝对路径要求成立） |
| D-35 | `:135-136` | 目录路径 ×2：`__GOVERNANCE_SKILLS_ROOT__`、`__GOVERNANCE_SHIMS_ROOT__` | **必要** | 静默失效（目录不存在 ⇒ 目录静默为空） | 渲染后实测解析为 `D:/AI/agent/claude/coding/project_management_workflow/skills` 与 `.../adapters/dsh/skill-shims`，二者 `is_dir()` 均 True |
| D-36 | `:138-139` | 包名 `@deepseek-ai/dsh-tool-skill`（`skill` 工具本身） | **必要** | 致命（无 `skill` 工具 ⇒ 整套 workflow 加载机制失效） | 实测 `PASS` |
| D-37 | `:143-144` | 包名 `@deepseek-ai/dsh-tool-goal` | **必要** | 致命 | 实测 `PASS` |
| D-38 | `:148-168` | group 行：`- id: planning` + `name: cordis:group` + `group: true` + `isolate: {planMode: true}` + 内层 `- id: plan-mode` / `name: @deepseek-ai/dsh-plan-mode` | **必要** | 致命（group 语义变更 ⇒ 内层行不挂载） | 护栏实测 group 递归生效（`DISABLED_INHERITED` / `PASS` 分支均可达） |
| D-39 | `cordis:group`（`:149, 173, 198`） | 包名/模块路径 `cordis:` 前缀 = loader 内建 | **必要** | 致命（前缀语义变更 ⇒ 解析为普通包名 ⇒ `MODULE_UNRESOLVED`） | `dsh_compat.py:343-347`：`name.startsWith('cordis:') → BUILTIN`（不校验 schema，无 finding） |
| D-40 | `:157-168` | config 键 `section`（plan-mode 的大段策略文本） | **必要（但今天零校验）** | 静默失效（见 G-01：该行无 `Config` 导出 ⇒ config 完全不被校验） | **实测**：`@deepseek-ai/dsh-plan-mode` `exports.Config = NO`，`typeof=function`，`keys=["inject"]` |
| D-41 | `:172-190` | group `compaction` + `@deepseek-ai/dsh-compaction-basic` / `dsh-command-compact` / `dsh-compaction-tool-result-pruner`；config 键 `thresholdChars` / `headChars` / `tailChars` | **必要** | 致命（有 schema 的三行）/ 静默失效（`command-compact` 无 schema） | 实测：`compaction-basic` PASS、`command-compact` **NO_SCHEMA**、`tool-result-pruner` PASS |
| D-42 | `:197-254` | group `delegation` + `@deepseek-ai/dsh-tool-subagent-control`、`dsh-tool-subagent-control/list-agents`、`dsh-tool-subagent`(×2)、`dsh-workflow-worker-thread`、`dsh-tool-workflow`、`dsh-tool-ralph` | **必要** | 致命（有 schema 的行）/ 静默失效（`tool-subagent-control` 与 `list-agents` 无 schema） | 实测：`tool-subagent-control` **NO_SCHEMA**、`list-agents` **NO_SCHEMA**、`tool-subagent` PASS(×2)、`workflow-worker-thread` PASS、`tool-workflow` PASS、`tool-ralph` PASS |
| D-43 | `:122-125, 223-241` | config 键 `provider` / `toolName` / `backgroundMode` / `enableRunInBackground` / `maxDepth` / `subagentProvider` / `maxRounds`（全部枚举/字符串契约） | **必要** | 致命（枚举收紧 ⇒ 拒绝；`maxDepth: provider-managed` 尤甚） | `dsh-tool-subagent` 两行实测 `PASS`；`tool-ralph`/`workflow-worker-thread` 实测 `PASS` |
| D-44 | `:258-271` | 包名 `@deepseek-ai/dsh-tool-ask-user` / `-tool-todo` / `-tool-web`；config 键 `allowParallelInProgress` / `fetch` / `searchTimeoutMs` | **必要** | 致命（`tool-todo`/`tool-web` 有 schema）/ 静默失效（`tool-ask-user` 无 schema） | 实测：`tool-ask-user` **NO_SCHEMA**、`tool-todo` PASS、`tool-web` PASS |
| D-45 | `:34-36 注释` + `:96-97, 194-196, 266-267` | 宿主平面分工语义：`shell-env` / `subagents` registry / `web` service 由**宿主**组合提供，预设只贡献对应工具行 | **必要** | 降级（宿主组合变更 ⇒ 工具行找不到依赖的 registry/service） | 注释 4 处明示；**未实测**（需宿主 `cordis.yml` 全量比对）→ R-09 |

**`agent-presets/governance/preset.yml`（2 行）**：`preset.yml:1 name: 治理协调器`、`:2 description: …`。

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-46 | `preset.yml:1-2` | 文件/字段：预设 metadata（`name` + `description`） | **必要** | 降级（`description` 缺失 ⇒ 设置面板可用但无说明）/ 致命（`name` 缺失 ⇒ 预设无法在设置面板识别） | 上游实测 `dsh-agent-presets/lib/index.js:161` 提及 `METADATA_FILE`；`:183` 导出 `METADATA_FILE`；`:405` `join(directory, COMPOSITION_FILE)`。**`METADATA_FILE` 的确切文件名与 `name` 是否必填未实测** → R-10 |

### 2.5 手动交付路径（`adapters/dsh/launch.py`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-47 | `launch.py:114-118` | `DSH_HOME` 解析（**第二个独立实现**，`:115-118`） | **可弱化** | 静默失效（与 `lib/index.js` 及上游三方差分 ⇒ 写到宿主不读的位置） | 逐 case 实测见 G-06：`DSH_HOME="   "` 时 `dsh_home()` 返回**字面两个空格**，`preset_dir()` = `"  \.agent-presets\governance"`，而上游与 `lib/index.js` 均返回 `C:\Users\peter\.dsh` |
| D-48 | `launch.py:134-155` | **自实现**组合 YAML 渲染（`str.replace` + `any(token in …)` 兜底） | **必要** | 致命（渲染失败即 `return ""`，被 `:196-197, 248-254` 报错拒绝安装） | `:153` 兜底检查；**该兜底与实际不符** → G-08 |
| D-49 | `launch.py:447-496` | **自实现** `customSkillDirs` 解析（`:447-465` 手写缩进扫描；`:468-496` 手写 `!!js`/`baseUrl`/相对路径判定） | **可弱化** | 静默失效（解析漏项 ⇒ 声称 PASS 而实际不校验） | 实跑：真实模板 → 命中 2 条；构造 `customSkillDirs:` 与列表项**同缩进**（合法 YAML）→ **命中 0 条**（`:459` `<=` 早退） → G-05 |
| D-50 | `launch.py:478-488` | `!!js … new URL('…', baseUrl)` 分支 + `urllib.request.url2pathname` / `urlparse` / `urljoin` | **可消除（已死代码）** | 无（当前渲染产物不含 `!!js`） | 实测：模板含 `!!js` 为 `True`（2 处 `process.platform`），但二者**不带 `baseUrl`**；渲染后产物 `!!js` 仍为 `True`；`_resolve_skill_entry` 的 `baseUrl` 分支实测从未被真实产物命中（`test_dsh_adapter.py:227 self.assertNotIn("baseUrl", generated)`） |
| D-51 | `launch.py:514-567` `_validate_composition_rows` | 依赖 `dsh_compat.check_dsh_preset_compat`（同一实现，非二次实现） | **必要** | 致命（护栏不可用 ⇒ `NOT_RUN`，绝不静默 PASS —— `:531-532, 566` 明示且实测） | `:545 import dsh_compat`；`:555-556` 调用；实测 `schema_checked = report["verdict"] != "NOT_RUN"` |
| D-52 | `launch.py:570-679` `verify_preset_loading` | 依赖 `--smoke` 的两处加载面（skill catalog root + `/governance` shim） | **必要** | 降级（只证「加载面解析成功」，不证 schema/会话行为） | `:348-350` `SMOKE_CATALOG_SKILL/SMOKE_GESTURE_NAME/…`；`:790-793` 明示 live 面 `NOT_RUN` |
| D-53 | `launch.py:703-803` | `--smoke` 隔离与退出码（0/1/2） | **必要** | 致命（隔离守卫失效 ⇒ 可能写真实 home） | `:352-354 SMKE_EXIT_{PASS,FAIL,REFUSED}=0,1,2`；`:716-734` 未设/落在真实 home 即 REFUSED；`:738/777-785` 前后 witness 对比；实跑 `verify_workflow.py check-dsh-preset-smoke` exit 0 | 
| D-54 | `launch.py:409-444` `_real_home_witness` | 文件/目录路径 `<home>/.agent-presets` + `<home>` 顶层文件名/size/mtime_ns | **可弱化** | 降级（假 FAIL：witness 被无关宿主活动翻转 ⇒ gate 误报） | 实测：`.agent-presets` 递归 85 项；`top_level` 13 项（含 `settings.yaml` 的 size+mtime_ns、`.credentials.yaml`）；`_real_home_witness()` 耗时 0.020s。**是否存在翻转风险**：连续 8 次采样（间隔 3s，共 24s）5 个顶层文件全部 `STABLE`、sessions 子树变化被容忍（`test_dsh_adapter.py:979-1003`）→ 本次**未观察到**翻转 → R-04 |
| D-55 | `launch.py:298-303` | 路径逃逸守卫（`--uninstall` 只删 `.agent-presets/governance`） | **必要** | 致命（守卫失效 ⇒ 可删除任意路径） | `:298 if target.parent.name != ".agent-presets" or target.name != PRESET_ID: … return 1`；`test_dsh_adapter.py:313-340` 正反用例 |
| D-56 | `launch.py:78, 80, 487` | `urllib.request` / `urllib.parse` import（供 D-50 的死分支使用） | **可消除** | 无 | 实测：因 `--smoke` 与 `--install` 共用 `run_cli` 路径未被隔离到子命令，故**行为上无害**；死代码本身由 D-50 判定 |

### 2.6 薄投影面（`adapters/dsh/adapter-manifest.json` + `skill-shims/*`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-57 | `adapter-manifest.json:73-74` | CLI 行为：`dsh` / `dsh --version`；`:76` `verified_on: 2026-07-08`，证据串含 `dsh --version returns 0.1.0-rc.6` | **可弱化** | 静默失效（声明陈旧 ⇒ 读者以为已在当前 dsh 上验过） | **文档≠事实**：安装态实测 `0.1.5-rc.1`（比 `adapter-manifest.json:76` 的 `0.1.0-rc.6` 新 5 个 rc）；`:75 verified_on: 2026-07-08` 距本报告 2026-09-13 已 67 天 |
| D-58 | `adapter-manifest.json:34-35` | 字段：`skill_loading: "native"` + `skill_path` | **必要** | 静默失效（语义失真 ⇒ 文档与实现脱节；实际加载靠 `customSkillDirs`） | 实测：`:36` 的 `note` 已正确描述 `customSkillDirs`，与本字段并存 |
| D-59 | `adapter-manifest.json:63` | 文件路径 `${DSH_HOME}/.agent-presets/governance/` | **必要** | 静默失效（描述路径与实现不一致 ⇒ 排查走错方向） | 与 `lib/index.js:20, 42`、`launch.py:122` 一致（实测三处同为 `.agent-presets/governance`） |
| D-60 | `adapter-manifest.json:3-5, 32, 91` | 字段 `entry_type` / `support_status` / `native_entry.preset_file` / `launcher`（**被 `verify_workflow.py` 作为字符串消费**） | **必要** | 降级（字段缺失 ⇒ 相关 check 读键失败） | `launch.py:159-183 print_manifest()` 读 `workflow_id` / `entry_type` / `support_status` / `trigger` / `inputs` / `outputs` / `native_entry` / `runtime_e2e` / `validation` |
| D-61 | `adapter-manifest.json:36` | 文本契约：`note` 内含 `adapters/dsh/skill-shims/`、`agent.cordis.yml.template`、`customSkillDirs` 等字面串 | **可弱化** | 静默失效（文案漂移但不影响功能） | `test_dsh_adapter.py:592 test_workflow_registries_know_dsh`、`:611 test_supported_agents_and_loading_docs_include_dsh` 对 dsh 字面存在性做断言 |
| D-62 | `skill-shims/governance.md:1-4` | dsh skill frontmatter 契约：`name` == 文件名、非空 `description` | **必要** | 致命（frontmatter 不合法 ⇒ `/governance` 手势不加载） | `governance.md:1-4` 实测含 `---` / `name: governance` / `description: …`；`launch.py:653-658` 正是这三条的正则校验 |
| D-63 | `skill-shims/governance.md:2` | `name: governance` 与文件名同名（决定手势名 `/governance`） | **必要** | 致命（改名 ⇒ 手势消失） | 同名实测；`launch.py:349 SMOKE_GESTURE_NAME = "governance"` |
| D-64 | 9 个 shim 文件（`skill-shims/*.md`，共 9 个） | 目录路径 = 第二个 `customSkillDirs` 根（D-35） | **必要** | 静默失效（目录缺失 ⇒ 全部手势消失） | `Get-ChildItem adapters/dsh/skill-shims -File` 实测 9 个：`change-triage.md`, `governance-cleanup.md`, `governance-gate.md`, `governance-init.md`, `governance-review.md`, `governance-status.md`, `governance-update.md`, `governance-verify.md`, `governance.md` |

### 2.7 两点交付路径的契约一致性面

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-65 | `lib/index.js:149-163` × `launch.py:134-155` | **两处独立实现**同一渲染契约 | **必要** | 致命（分歧 ⇒ 同一包版本在两条安装路径下写出不同预设） | **实测全等**：`lib/index.js` render sha256 = `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`，长度 13566；`launch.py` render **同一 sha256、同一长度**；真实 `~/.dsh/.agent-presets/governance/agent.cordis.yml` **也是同一 sha256**（16796 字节）。三者字节全等。 |
| D-66 | `lib/index.js:154` × `launch.py:146` | 行尾归一化语义：JS `replace(/\r\n/g,'\n')` vs Python `read_text` 通用换行 | **可弱化** | 静默失效（含孤立 `\r` 的模板 ⇒ 两条路径写出不同字节） | **实测分歧**：注入 1 个孤立 `\r` 后，`python render` 孤立 CR = 0，`node render` 孤立 CR = **1**；两输出长度同为 13588，**首个分歧在 offset 16815**：py = `b'-CR probe: X\nY\n'`，node = `b'-CR probe: X\rY\n'` |
| D-67 | `test_dsh_adapter.py:1127-1156` | 测试：`test_js_and_python_renderers_agree`（node-gated） | **必要** | 静默失效（node 缺失即 `skipTest` ⇒ 契约无声未测） | `:1133-1135 if not node: self.skipTest(...)`；`:1141` 读取**真实模板文件**，`:1153-1156` 断言相等。**该测试不注入 `\r`** ⇒ 抓不到 D-66 |
| D-68 | `test_dsh_adapter.py:1158-1211` | 测试：`test_lib_ensure_preset_renders_the_user_root_idempotently`（node-gated） | **必要** | 降级（node 缺失即跳过） | `:1164-1166 skipTest`；`:1176-1178` 用 `tempfile.TemporaryDirectory()` 作 `DSH_HOME`（隔离正确）；`:1191-1193` 断言 4 个产物文件 |

### 2.8 护栏（`skills/software-project-governance/infra/dsh_compat.py`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-69 | `dsh_compat.py:134-136` | 安装锚点 `<nm>/@deepseek-ai/dsh/package.json` | **必要** | 降级（锚点变更 ⇒ 平面发现失败 ⇒ `NOT_RUN`，非静默 PASS） | `DSH_SCOPE="@deepseek-ai"`、`DSH_PACKAGE="dsh"`、`INSTALL_ANCHOR_REL=("@deepseek-ai","dsh","package.json")`；`dsh_compat.py:131-133` 注释指上游 `INSTALL_ANCHOR`；实跑 `install.status: OK`, `source: DSH_HOME/profiles` |
| D-70 | `dsh_compat.py:146-151` | `ORACLE_PACKAGES`（4 个包名） | **必要** | 降级（包名变更 ⇒ 版本报告为 `?`，护栏仍可跑） | 实跑 4 个全部解析出真实版本（`cordis@4.0.2` / `include@1.0.7` / `loader@1.0.3` / `js-yaml@4.3.2`） |
| D-71 | `dsh_compat.py:155, 560-563` | `DSH_HOME` 显式读取（**只在该 env 显式设置时才读**，从不猜 `~/.dsh`） | **必要** | 降级（未设 ⇒ 回退 PATH 锚点） | `:560-562 raw = _env_text(env, DSH_HOME_ENV); if not raw: return []` |
| D-72 | `dsh_compat.py:156, 563-576` | 目录路径 `<DSH_HOME>/profiles/<p>/node_modules` 与 `<DSH_HOME>/profiles/node_modules` | **必要** | 降级（布局变更 ⇒ 解析到别的平面或 `NOT_RUN`） | 实跑 `chosen_plane = "DSH_HOME/profiles"` → `.../profiles/node_modules`；`other_planes: []` |
| D-73 | `dsh_compat.py:160, 168` | 组合文件名 `agent.cordis.yml` + glob `**/agent.cordis.yml`、`**/*.cordis.yml.template` | **必要** | 降级（文件名变更 ⇒ 0 composition ⇒ `NOT_RUN`） | `:158-160` 注释指上游 `COMPOSITION_FILE`；实跑发现 1 个 composition（`agent-presets/governance/agent.cordis.yml.template`） |
| D-74 | `dsh_compat.py:211-221` | **上游 API 面**：`js-yaml`、`@deepseek-ai/cordis-plugin-include.entryListSchema`、`@deepseek-ai/cordis-plugin-loader.evaluate/isJsExpr`、`@deepseek-ai/cordis.resolveConfig` | **必要** | 致命→降级（任一 API 改名/移除 ⇒ `fail('installed harness API unavailable: …')` ⇒ `NOT_RUN`，**不静默 PASS**） | `:219-227` 逐项存在性/可调用性检查；实跑全部可用（probe 成功构建 oracle） |
| D-75 | `dsh_compat.py:236, 268` | 语义：`!!js` 用 loaders `evaluate(ctx, expr)` 求值；`new Function('ctx','expr','with (ctx) { return eval(expr) }')` | **必要** | 致命→降级（方言变更 ⇒ 表达式求值异常 ⇒ `DISABLED_EXPR_ERROR` / 值错） | `:236` `interpolate`；`:268 displacedOf`；实测抛错表达式被捕获为 finding |
| D-76 | `dsh_compat.py:371-376` | `exports.Config` 存在性作为「是否有 schema」的判据 | **必要（但语义不完整）** | **静默失效（核心缺口）** | `:372-375`：无 `Config` ⇒ `NO_SCHEMA`，**不计入 `checked`**；`:377 entry.checked += 1` 仅在有 schema 时执行 |
| D-77 | `dsh_compat.py:985-991, 1000-1025` | `VERDICT_*` 语义：`PASS` / `FAIL` / `NOT_RUN` | **必要** | 致命（`NOT_RUN` 被当成 PASS ⇒ 未验证冒充已验证） | `:1000-1025` 裁决：有 failures → FAIL；`elif not compositions or rows_enabled == 0` → NOT_RUN；否则 PASS。**注意 `rows_checked` 不参与 PASS 判据** → G-01 |
| D-78 | `dsh_compat.py:113-124` | `FINDING_KINDS`（6 类 finding）与 `NO_SCHEMA`/`BUILTIN`/`DISABLED_INHERITED`/`PASS` 的区分 | **必要** | 静默失效（分类错误 ⇒ 真 finding 被降级为 detail） | `:117-124` 元组实测只含 `CONFIG_INVALID`/`MODULE_UNRESOLVED`/`IMPORT_ERROR`/`CONFIG_EXPR_ERROR`/`DISABLED_EXPR_ERROR`/`ROW_SHAPE` |
| D-79 | `dsh_compat.py:445-462, 757-758` | 临时目录（`tempfile.gettempdir()` 下 `spg-dsh-compat-*` / `-home-*`） | **可弱化** | 降级（清理失败 ⇒ 临时目录残留，不影响正确性） | 实测：正常 run **新增 0 个残留**；超时 run 也 **0**；发现 **6 个历史残留**（2026-09-12 10:12~10:16，各含 `report.json` 或为空）⇒ 陈旧版本残留，当前不可复现 → G-09 |
| D-80 | `dsh_compat.py:773` | 子进程 `DSH_HOME` 重定向（隔离机制） | **必要** | 致命（隔离失效 ⇒ 探针可写用户真实 home） | 实跑 `isolation.home_writes: 0`；`:777 env=child_env`（保留 `SystemRoot`/`PATH`，注释 `:726-731` 说明为何不整体替换） |
| D-81 | `dsh_compat.py:775-785` | CLI 行为：`node --input-type=module --eval` + `input=` stdin 协议 | **可弱化** | 降级（Node CLI 行为变更 ⇒ probe 失败 ⇒ `NOT_RUN`） | `:776-784`；实跑 probe 成功（`report.ok = true`） |
| D-82 | `dsh_compat.py:1035, 1038-1093` | 渲染层契约：本模块自持 `CHECK_SECTION_TITLE` + `emit_check_section`（引擎只贡献调用） | **可弱化** | 降级（渲染契约变更 ⇒ 输出格式变，功能不受影响） | `:1030-1034` 注释引 R4 ratchet；`registry.py:406 ("28v", "dsh_compat.emit_check_section")` |

### 2.9 看护接线（`verify_workflow.py` / `registry.py`）

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-83 | `verify_workflow.py:6802-6876` | Check 28u 本体：子进程调 `launch.py --smoke`，`DSH_HOME` 指向 `tempfile.mkdtemp(prefix="spg-dsh-smoke-")` | **必要** | 降级（缺失 ⇒ 无隔离冒烟门禁） | `:6811` launcher 路径；`:6823-6826` 隔离；`:6845` `finally: shutil.rmtree(temp_home)`；实跑 exit 0 |
| D-84 | `verify_workflow.py:6797-6799` | 输出正则契约：`[SMOKE] real-home writes : N` 与 `[SMOKE] Result: PASS` | **可弱化** | 降级（launcher 输出措辞变更 ⇒ 正则不匹配 ⇒ 判 FAIL，属 fail-safe 方向） | `:6851-6853` 解析 writes；`:6855` 判定；与 `launch.py:779-780` 实际输出格式实测一致（`real-home writes : 0`） |
| D-85 | `verify_workflow.py:6892-6929` | `DSH_UPGRADE_REGRESSION_LABEL` + `run_dsh_upgrade_regression_gates`（release gate 组成） | **必要** | 降级（复用 `check_dsh_preset_smoke`，不重复实现 —— `:6903` 明示） | `:6908-6909 smoke_runner = check_dsh_preset_smoke`；`:7110-7151` 引擎接线；`details["dsh_upgrade_regression"]` 实际在 `:7142` 构建 |
| D-86 | `registry.py:405-406` | Check ID 注册 `("28u", …)` / `("28v", "dsh_compat.emit_check_section")` | **必要** | 降级（注册缺失 ⇒ check 不跑） | `:405-406` 实测存在；`:349-420` `_SEGMENT_LOADERS` 实测 **70** 条 |
| D-87 | `registry.py:197` | `LOADER_WHITELIST` 含 `"dsh_compat"` | **必要** | 降级（白名单缺失 ⇒ 加载被 fail-closed 拒绝） | `:197` 实测；`:199-204` 声明「无 package walk / entry point / 动态发现」 |
| D-88 | `registry.py:251-253` | 命令键 `check-dsh-preset-compat` / `check-dsh-preset-smoke` | **必要** | 降级（命令不可达） | `:251-253` 实测 |
| D-89 | `registry.py:428-431` | **已退役**：Segment `40`（`check_dsh_skills_manifest`）与 `dsh.skills` 声明 | **不可消除（历史事实，需保留记录）** | 无 | `:428-431` 原文：「Segment ``40`` (``verify_workflow.check_dsh_skills_manifest``) was removed with its subject: FIX-310/DEC-187 retired the dead ``dsh.skills`` declaration from package.json, so the declaration↔disk guard had nothing left to guard.」**全仓实测无 `check_dsh_skills_manifest` 定义、无 `DSH_SKILLS_DISK_PATTERNS` 符号** |
| D-90 | `verify_workflow.py:1510, 2166, 2266-2280` | 适配器清单/矩阵中的 `dsh` 条目 | **可弱化** | 降级（文档/矩阵漂移） | `:1510 MAINSTREAM_AGENT_ADAPTERS = [... "dsh"]`；`:2166 RUNTIME_MATRIX_AGENT_IDS = [... "dsh", …]`；`:2270-2280 "dsh": {…}` |
| D-91 | `verify_workflow.py:6597-6742` | 注入面契约：DSH persona 模板 / 入口 SKILL / DSH thin pointer 必须携带锚点关键词 | **必要** | 静默失效（锚点关键词丢失 ⇒ persona 不再承载行为契约） | `:6641 "adapters/dsh/AGENTS.md.template": ["关键行为契约"]`；`:6742-6743` 断言函数说明；`test_dsh_adapter.py:180-201` 对模板断言 `关键行为契约`/`复审必达`/`完成必推荐` |
| D-92 | `verify_workflow.py:18139-18141` | 注释：dsh **故意**不在 headless CLI runner 面（`DSH-ADAPTER-001`） | **不可消除（有意决策）** | 无 | `:18139-18141` 原文：「dsh is deliberately absent: it has no headless CLI runner, so its adapter matrix entry (DSH-ADAPTER-001). Do not add it without a real headless runner.」 |
| D-93 | `verify_workflow.py:19619-19634` | claim registry 的 4 条 dsh 用户可用性 claim | **可弱化** | 静默失效（claim 与实际能力脱节） | `:19623-19634`：`dsh-session-projection` / `dsh-preset-roster` / `dsh-governance-gesture` / `dsh-install-forms-boundary` |

### 2.10 版本投影与清理范围

| ID | 位置 | 依赖形态 | 必要性 | 失效后果 | 证据 |
|---|---|---|---|---|---|
| D-94 | `core/version-projections.json:25` | 投影 `dsh-persona-version`：模板内 `治理工作流（vX.Y.Z）` ↔ SKILL frontmatter 版本 | **必要** | 静默失效（投影未更新 ⇒ persona 版本号撒谎） | `:25` 原文 `{"id": "dsh-persona-version", "kind": "transformed_text", "target": "agent-presets/governance/agent.cordis.yml.template", "pattern": "治理工作流（v正则）", "count": 1}`；模板 `:51` 实测 `治理工作流（v0.80.0）` == `package.json:4` |
| D-95 | `core/version-projections.json:26` | 投影 `dsh-agents-bootstrap-version`：`adapters/dsh/AGENTS.md.template` 的 `> @bootstrap-version:` | **必要** | 静默失效（同上） | `:26` 原文 |
| D-96 | `core/manifest.json:22-23` | `canonical_product_artifacts` 的版本投影 ID 清单含 `dsh-persona-version` / `dsh-agents-bootstrap-version` | **必要** | 降级（清单漏项 ⇒ cleanup/contract 检查不覆盖） | `manifest.json:22-23` 实测 |
| D-97 | `core/manifest.json:211, 215, 239, 243, 247, 251, 255` | canonical 产物路径：`infra/dsh_compat.py`、`tests/test_dsh_compat.py`、`lib/`、`lib/index.js`、`agent-presets/`、`agent-presets/governance/agent.cordis.yml.template`、`agent-presets/governance/preset.yml` | **必要** | 降级（漏项 ⇒ `cleanup.py` 把这些当残留删除！） | `manifest.json` 实测含全部 7 条 |
| D-98 | `core/manifest.json:822` + `cleanup.py:46-63` | `PLUGIN_SCOPE_DIRS` 含 `agent-presets` 与 `lib` | **必要** | 降级（漏项 ⇒ 升级后残留不被清理 / 或不该删的被删） | `cleanup.py:56-57 "agent-presets", "lib"`（注释 `:51-55` 明示 FIX-310 加入）；`manifest.json` `cleanup_scope.directories` 实测 = `["adapters","agent-presets","agents","commands","lib","skills",".agents",".chrys-plugin",".claude-plugin",".codex-plugin",".zcode-plugin"]` |
| D-99 | `infra/hooks/{pre-commit:68-82, commit-msg:120-134, post-commit:27-41}` | Shell 路径解析 `${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance` + `skill-root.txt` | **可弱化** | 静默失效（路径变更 ⇒ hook 找不到 home ⇒ `find_spg_home` 退化） | 三 hook 实测同构：`local dsh_preset_root="${DSH_HOME:-$HOME/.dsh}/.agent-presets/governance"`；`dsh_link_root=$(cat "$dsh_preset_root/skill-root.txt" 2>/dev/null || true)` |
| D-100 | `infra/checks/projection.py:13-14` | 投影比较的归一化：`replace("\r\n","\n")` | **可弱化** | 静默失效（与 D-66 同类：孤立 `\r` 不归一） | `:14` 原文 `sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n")…)`；**`PROJECTION_SYNC_PATTERNS` 实测 11 条，其中 dsh 相关 0 条** |

### 2.11 清单统计

| 分类 | 条数 |
|---|---|
| **总计** | **100**（`D-01` ~ `D-100`） |
| 必要 | 62 |
| 可弱化 | 26 |
| 可消除 | 4（`D-02`、`D-50`、`D-56`、`D-05` 见下注） |
| 历史/有意不可消除 | 3（`D-89`、`D-92`、`D-10` 的不可逆不变量性质） |
| 未发现反向依赖 | 0 条（正向 100 / 反向 0） |

> `D-05`（缺 `peerDependencies`）判定为「可消除→但 REQ-147 要求补齐」：今天它**不存在**，因此不是「依赖点」而是**依赖管理缺口**，计入第 5 节。

---

## 3. 可消除 / 可弱化 / 必要 三类归并

### 3.1 可消除（4 条）

| ID | 当前为什么存在 | 判定理由 | 消除后影响 |
|---|---|---|---|
| `D-02` | 任务书提示 `package.json` 可能有 `dsh.profile` 键；实测不存在 | 本包从不声明它；真实声明在 profile 侧（`~/.dsh/profiles/web/package.json:5-13`），属 dsh 的安装机制 | 无（本就不存在）。**须在报告中纠正任务书假设** |
| `D-50` | `launch.py:478-488` 的 `!!js … new URL(…, baseUrl)` 分支 + `:78,80` 的 `urllib` import | 渲染产物实测不含带 `baseUrl` 的 `!!js`；模板仅有的 2 处 `!!js` 是 `process.platform` 判定；`test_dsh_adapter.py:227` 已断言 `baseUrl` 不出现在产物中 | 删除约 20 行死代码 + 2 个 stdlib import；不影响任何现有路径 |
| `D-56` | 同 `D-50` 的 import 依赖 | 同 `D-50` | 同 `D-50` |
| `D-05`（缺口形式） | 当前完全无 `peerDependencies` / `dependencies` / `devDependencies` | 「零运行时依赖」是**刻意的宿主安全设计**（`lib/index.js:94-97`：inlined 以免 module-load 失败拖垮 boot）——这条设计**不应被消除**；被消除的应是「无任何版本声明」 | 补齐 `peerDependencies` 后新增的是**声明**而非**运行依赖**，与零 import 设计不冲突 |

> **反面证据（必须记录）**：`D-05` 的一种「消除」方向是错的 —— 把 `@deepseek-ai/dsh-home-paths` 加为真依赖来消除 `D-16`/`D-47` 的重复实现，会**直接违反** `lib/index.js:94-97` 记录的宿主安全不变量（module-load 失败即拖垮 boot）。本次只能把「消除重复实现」判为**可弱化（改为契约化并机器校验三方差分）**，不能判为可消除。

### 3.2 可弱化（26 条）

| ID | 弱化方向（只列形态，不给方案） |
|---|---|
| `D-07` | `engines.node` 从硬约束改为能力探测（运行时报告 node 版本） |
| `D-11` | 版本引用改为在报告中**动态读取**而非硬编码注释（当前 `0.1.5-rc.2` 与实测 `0.1.5-rc.1` 不符） |
| `D-14` | `ctx.logger` 用法可选化（当前已用可选链，属最低限度） |
| `D-15` | 上游镜像对象的版本引用改为动态/去版本化 |
| `D-16` | 从「内联复制上游语义」改为「契约化 + 差分校验」；不得改为真依赖（见 3.1 反面证据） |
| `D-22` | staging + rename 原子性语义声明化（当前无重试/无锁） |
| `D-30`/`D-31` | 平台判定从 `!!js process.platform` 改为声明式能力探测 |
| `D-45` | 宿主平面分工从注释改为机器可读的契约声明 |
| `D-47` | `launch.py` 的 `DSH_HOME` 解析与 `lib/index.js`、上游三方**收敛为单一契约 + 差分校验** |
| `D-49` | 手写 `customSkillDirs` 缩进扫描改为**复用真实 YAML 解析**（本仓库已有 `js-yaml` 可用路径）或改为在渲染前对模板做结构化校验 |
| `D-54` | witness 范围收窄/或声明为 advisory（当前会把 `settings.yaml` 的 size+mtime_ns 纳入比对） |
| `D-57` | `adapter-manifest.json` 的 `verified_on` / 版本证据改为由机器刷新 |
| `D-61` | 文案契约从「字面串断言」弱化为「语义契约断言」 |
| `D-66`/`D-100` | 行尾归一化语义从「JS 归一 `\r\n` / Python 通用换行」改为**显式统一**（当前已实测分歧） |
| `D-67`/`D-68` | node-gated 测试从「静默 skip」弱化为「显式 `NOT_RUN` 披露」 |
| `D-69`~`D-75` | 护栏对上游锚点/API 的耦合从「硬编码包名/API 名」收敛为**单点契约表 + 启动期能力探测** |
| `D-79` | 临时目录清理从「best-effort」改为可审计（当前出现历史残留） |
| `D-81` | Node CLI 调用契约声明化 |
| `D-82` | 渲染层契约（`CHECK_SECTION_TITLE` / 输出格式）声明化 |
| `D-84` | launcher→checker 的输出正则契约改为结构化（当前靠 `[SMOKE]` 文本正则） |
| `D-90`/`D-93` | 文档/claim 矩阵漂移治理 |
| `D-99` | git hooks 的 dsh 路径发现从 shell 硬编码改为契约化 |
| `D-60` | manifest 字段从「被 `print_manifest` 直接键取」弱化为带回退的读取 |
| `D-58`/`D-59` | manifest 描述字段与实现一致性校验 |
| `D-76`（形式） | 「有无 schema」判据从 `exports.Config` 单点扩大为**显式列出零校验行**（当前 5/23 行零校验且不披露为 finding） |

### 3.3 必要（62 条，必须被契约化维护）

按依赖形态聚类（不重复列 ID，完整清单见第 2 节）：

| 聚类 | 代表 ID | 为什么不必要不可 |
|---|---|---|
| **包身份与入口契约** | `D-01, D-03, D-04, D-06, D-08` | 任一失效即「不加载 / 不生效」；这是 dsh 插件机制的入口面 |
| **补丁层 insert 语义** | `D-09, D-10` | DEC-187 I-1/I-2/I-3 的落地点；`insert` 无 `id` 是零侵入的唯一形态 |
| **预设交付路径与文件名** | `D-18, D-20, D-35, D-59` | 由 dsh 的 `COMPOSITION_FILE`/`USER_PRESET_DIR` 决定，我方无选择权 |
| **组合行的包名 + config 键（有 schema 的 18 行）** | `D-24, D-25, D-28, D-29, D-32, D-33, D-34, D-36, D-37, D-41, D-42, D-43, D-44` | 就是 RISK-050 的成因面：一行 schema 不匹配即可否决整棵预设挂载（致命） |
| **`customSkillDirs` 通道** | `D-34, D-35` | 本插件 skill 注入的**唯一**通道；失效静默（目录为空，用户只看到 `/governance` 消失） |
| **`cordis:` 内建前缀** | `D-39` | group/builtin 语义的唯一标识 |
| **护栏的上游 API 面** | `D-74, D-75, D-77` | 护栏是 RISK-050 的 CI 前移手段；其上游 API 一旦改名即 `NOT_RUN` |
| **`DSH_HOME` 语义** | `D-17, D-18, D-71, D-72` | 写入位置由宿主决定 |
| **warn-only / 永不抛契约** | `D-23` | 单向不可逆的用户体验保护 |
| **隔离与逃逸守卫** | `D-53, D-55, D-80` | 真实环境安全底线 |
| **渲染 token 契约** | `D-21, D-48, D-65` | 两条交付路径的公共面 |
| **版本投影与清理范围** | `D-94, D-95, D-96, D-97, D-98` | 治理结构完整性 |
| **看护接线** | `D-83, D-85, D-86, D-87, D-88, D-91` | 现有防护网本体 |
| **skill frontmatter 契约** | `D-62, D-63, D-64` | 手势加载的唯一依据 |

---

## 4. 现有看护覆盖矩阵

**覆盖强度定义**：`强` = 能抓住该依赖点的漂移并**判负**（有正反用例）；`弱` = 有守卫但**抓不住**该漂移，或只覆盖同形不同点；`无` = 无任何守卫。

| ID | 依赖点摘要 | Check 28u | Check 28v | `test_dsh_adapter.py` | `test_dsh_compat.py` | `--smoke` | `check-dsh-skills-manifest` | 其它 | 强度 | 一句话：能否抓住漂移 |
|---|---|---|---|---|---|---|---|---|---|---|
| D-01 | `dsh.bundle.patch` | 无 | 无 | 无 | 无 | 无 | **已退役（D-89）** | 无 | **无** | **抓不住**：该键被删除后本仓无任何机器检查（`test_dsh_adapter.py:433` 只测 `cordis.patch.yml` 内容，不测 `package.json` 的 `dsh` 键） |
| D-02 | `dsh.profile`（不存在） | — | — | — | — | — | — | — | **无** | 不适用（不存在） |
| D-03 | `type`/`main` | 无 | 弱（28v import 本包行时会经 ESM 解析） | 弱（`:1158` node-gated 间接） | 无 | 无 | — | 无 | **弱** | 半能：`type` 改 CJS 后 `test_dsh_adapter.py:1158` 的 `import {apply}` 会失败 ⇒ 能抓；但 node 缺失即 skip |
| D-04 | `exports` | 无 | 弱（同 D-03，探针用绝对路径绕过 `exports`） | 无 | 无 | 无 | — | 无 | **弱** | **基本抓不住**：所有探针都用 `file://` 绝对路径或 `link:` 目录，**没有一处通过包名 + `exports` 解析** |
| D-05 | `peerDependencies`（缺） | 无 | 无 | 无 | 无 | 无 | — | `check-version-consistency`（不涉 peer） | **无** | **抓不住** |
| D-06 | `files` 白名单 | 无 | 无 | 无 | 无 | 无 | — | `core/manifest.json` canonical 清单（但**不含**发布包白名单语义） | **无** | **抓不住**：白名单漏项只在真实 `npm pack` 后暴露 |
| D-07 | `engines.node` | 无 | 无 | 无 | 无 | 无 | — | 无 | **无** | **抓不住** |
| D-08 | 包名三方一致 | 无 | 弱 | 强（`:433-463` 断言 patch 只插本包） | 弱 | 无 | — | 无 | **弱** | 半能：patch 行 `name` 与 `package.json` 的一致性**无显式断言**；改动 `package.json:3` 不会让任何 check 变红 |
| D-09 | `insert` 无 `id` 语义 | 无 | 弱（探针按 loader 语义解析，但不校验「无 id」这一形态） | 强（`:433-463 test_bundle_patch_is_zero_intrusion`） | 无 | 无 | — | 无 | **弱** | 半能：抓「有 `id` 定向 UPDATE」（测 `!!js`/`trust`），**抓不住**上游 `applyEntryPatches` 语义变更 |
| D-10 | 零 UPDATE 不变量 | 无 | 无 | **强**（`:463 self.assertNotIn("!!js", code_text)` + 同测试系列） | 无 | 无 | — | `review-REL-076-*`（一次性人工） | **强** | 能抓：`cordis.patch.yml` 出现 `!!js`/`trust`/id-UPDATE 即测试红 |
| D-11 | 版本引用 `0.1.5-rc.2` | 无 | 弱（28v 报告真实版本） | 无 | 无 | 无 | — | 无 | **弱** | **抓不住**：注释文本无任何断言；28v 输出真实版本但**不与注释比对** ⇒ 注释失真可长期存续 |
| D-12 | `dsh plugin add` 自动注册 | 无 | 无 | 无 | 无 | 无 | — | 无 | **无** | **抓不住**：无测试覆盖 `dsh plugin add` 路径 |
| D-13 | `apply(ctx)` 导出形态 | 无 | 弱 | 弱（`:1158` node-gated） | 无 | 无 | — | `review-REL-076-CODE-R0.md:33`（一次性） | **弱** | 半能 |
| D-14 | `ctx.logger` | 无 | 无 | 弱（`:1173-1174` 注入 `ctx`） | 无 | 无 | — | 无 | **弱** | 半能：`ctx.logger` 移除后 `apply` 不抛（可选链）⇒ **静默**，测试也抓不住 |
| D-15 | 上游镜像版本引用 | 无 | 无 | 无 | 无 | 无 | — | 无 | **无** | **抓不住** |
| D-16 | 内联 `DSH_HOME` 解析 | 无 | 无 | 无 | 弱（`:245 test_dsh_home_is_never_guessed_when_unset`、`:207` profile 平面） | 有（隔离用） | — | 无 | **弱** | **抓不住**：无一处把内联实现与上游 `resolveDshHome` 做差分（本次实测 2 个分歧点） |
| D-17 | `homedir()` 回退 | 无 | 无 | 无 | 无 | 无 | — | 无 | **无** | **抓不住** |
| D-18 | `.agent-presets` 路径 | 弱（smoke 渲染到该路径） | 弱（`COMPOSITION_GLOBS` 发现） | 强（`:1179, 1199-1202` 断言 4 文件名） | 弱 | 强（渲染 + 解析） | — | 无 | **中** | 能抓：路径改名后 `test_dsh_adapter.py:1158` 与 `--smoke` 同时红 |
| D-19 | `.dsh-bundle-version` 幂等 | 无 | 无 | 强（`:1158-1211` 断言二次 boot 不重写） | 无 | 无 | — | 无 | **强** | 能抓 |
| D-20 | `skill-root.txt` | 无 | 无 | 强（`:260 test_install_writes_skill_root_marker`、`:529 test_hook_discovers_dsh_link_mode_marker`） | 无 | 无 | — | hook 测试 | **强** | 能抓 |
| D-21 | token 契约 | 无 | 无 | **强**（`:170 test_template_uses_only_known_tokens`、`:175`、`:1127` parity） | 无 | 弱（产物子串） | — | 无 | **强** | 能抓（**但见 D-27 的反面证据：`__GOVERNANCE_SKILLS_ROOTS__` 类拼错漏网）** |
| D-22 | staging + rename 原子性 | 无 | 无 | 弱（`:1158` 只测成功路径） | 无 | 无 | — | 无 | **弱** | **抓不住**：无失败注入用例 |
| D-23 | warn-only 永不抛 | 无 | 无 | 强（`:1213 test_lib_ensure_preset_warns_and_never_throws_without_payload`） | 无 | 无 | — | 无 | **强** | 能抓 |
| D-24~D-29, D-32~D-34, D-36~D-38, D-41~D-44 | 22 个 dsh 包名 + config 键（有 schema 的 18 行） | 弱（`--smoke` 经 `_validate_composition_rows` 间接跑 28v） | **强**（逐行 `resolveConfig`） | 弱（`:180-201` 字面串断言，只固定 id/name 文本） | **强**（`:545-655` 正反用例：`text`→拒绝、`prefix`→通过、结构 floor） | 弱（子集验证） | — | 无 | **强** | 能抓（有反相用例）；**但对「零 schema 行」不适用 → D-76** |
| D-30, D-31 | `!!js process.platform` | 无 | 中（`:805 test_js_scope_carries_base_url_and_process`、`:826` 抛错用例） | 无 | **强**（`:826 test_throwing_js_expression_is_a_finding_not_a_crash`） | 无 | — | 无 | **中** | 半能：抓「表达式抛错」，**抓不住**「`process` 不在 `!!js` scope 中」这类语义放宽 |
| D-35 | 两个 `customSkillDirs` 根 | 弱 | 无（28v 不校验路径存在性） | 强（`:368 test_rendered_composition_carries_absolute_existing_skill_roots`、`:397 test_rendered_skill_roots_are_pack_whitelisted`） | 无 | **强**（`:629-637` 断言 catalog 命中） | — | 无 | **强** | 能抓 |
| D-39 | `cordis:` 内建前缀 | 无 | 弱（`:343-347` 只报 `BUILTIN`，不校验） | 无 | 弱 | 无 | — | 无 | **弱** | **抓不住**：前缀语义变更 ⇒ 变成 `MODULE_UNRESOLVED`（**能**抓）或变成合法包名（**抓不住**） |
| D-40（`plan-mode` config） | `section` 键 | 无 | **无（零校验）** | 无 | **弱（且有反向用例固化）**：`:365 test_no_schema_rows_are_disclosed_not_failed` | 无 | — | 无 | **无** | **抓不住**：第 5 节 G-01 实测 `PASS / checked 0 / issues []` |
| D-45 | 宿主平面分工 | 无 | 无 | 无 | 无 | 无 | — | 无 | **无** | **抓不住** |
| D-46 | `preset.yml` 字段 | 无 | 无 | 强（`:735 test_preset_metadata_contract`） | 无 | 弱（渲染时读取） | — | 无 | **强** | 能抓 |
| D-47 | `launch.py` `DSH_HOME` 解析 | 弱（28u 用临时 home 调用 `--smoke`） | 无 | 弱（`:782`/`:806` 用 decoy/isolated home） | 无 | 弱 | — | 无 | **弱** | **抓不住**：无一处对照上游 `resolveDshHome` 做差分 |
| D-48 | 渲染兜底 `any(token in …)` | 无 | 无 | 弱（`:206 test_launch_render_is_pure_substitution`） | 无 | 弱 | — | 无 | **弱** | **抓不住**：`__GOVERNANCE_SKILLS_ROOTS__` 拼错时兜底与测试同时沉默（实测，见 G-08） |
| D-49 | 手写 `customSkillDirs` 扫描 | 无 | 无 | 弱（`:368`/`:397`/`:901` 只覆盖当前缩进形态） | 无 | 弱 | — | 无 | **弱** | **抓不住**：同缩进合法 YAML 实测命中 0 条 |
| D-50, D-56 | 死代码 | 无 | 无 | 无 | 无 | 无 | — | ArchGuard ratchet（不针对死代码） | **无** | **抓不住** |
| D-51 | 护栏可用性 `NOT_RUN` 政策 | 无 | 弱 | 强（`:924 test_verify_preset_loading_carries_the_row_schema_gate`） | **强**（`:441 test_oracle_failure_is_not_run_not_fail`、`:410`、`:423`） | 无 | — | 无 | **强** | 能抓 |
| D-52 | `--smoke` 两加载面 | 强（28u 本入口） | 无 | 强（`:845`/`:875`/`:901` 三个反相用例） | 无 | **强** | — | 无 | **强** | 能抓 |
| D-53 | 隔离与退出码 0/1/2 | **强**（28u 检查 `real-home writes`） | 无 | 强（`:806`/`:819`/`:832`/`:1049`） | 无 | **强** | — | 无 | **强** | 能抓 |
| D-54 | `_real_home_witness` 范围 | 强（28u 经 28u→launcher 输出） | 无 | 强（`:979-1023` 四情形、`:1025` 变更即 FAIL） | 无 | 强 | — | 无 | **强** | 能抓「写入被检测」；**但对「无关活动导致假 FAIL」只有 1 个容忍用例（`:1000` sessions 子树）** |
| D-55 | 路径逃逸守卫 | 无 | 无 | 强（`:313`/`:330`/`:341`） | 无 | 无 | — | 无 | **强** | 能抓 |
| D-57 | `verified_on` / 版本证据 | 无 | 弱（28v 报真实版本，但不比对该字段） | 无 | 无 | 无 | — | 无 | **弱** | **抓不住**：声明 `0.1.0-rc.6` vs 实测 `0.1.5-rc.1` 无人报警 |
| D-58, D-59, D-60, D-61 | manifest 字段/文案 | 无 | 无 | 弱（`:592`/`:611` 字面存在性） | 无 | 无 | — | `check-runtime-readiness-matrix`（弱） | **弱** | 半能 |
| D-62, D-63, D-64 | skill shim frontmatter | 无 | 无 | 强（`:633 test_skill_shim_frontmatter_contract`） | 无 | 弱（`launch.py:653-658` 校验） | — | 无 | **强** | 能抓 |
| D-65~D-68 | 渲染 parity | 无 | 无 | **强**（`:1127`）但 **node-gated** | 无 | 弱 | — | 无 | **中** | 能抓当前 LF 模板；**抓不住** `\r` 注入（D-66）；**node 缺失即 skip** |
| D-69~D-72 | 锚点/oracle/平面发现 | 无 | 强（28v 实测解析成功） | 无 | **强**（`:145`~`:256`，含 `:165 test_invalid_override_reports_instead_of_falling_back`、`:245`） | 无 | — | 无 | **强** | 能抓 |
| D-73 | 组合文件名/glob | 无 | 强 | 弱 | 强（`:276 test_repo_compositions_are_discovered`、`:285`） | 无 | — | 无 | **强** | 能抓 |
| D-74 | 上游 4 个 API | 无 | **强**（`:219-227` API 存在性 + probe 构建） | 无 | **强**（`:441 test_oracle_failure_is_not_run_not_fail`） | 无 | — | 无 | **强** | 能抓（降级为 `NOT_RUN`，非静默 PASS —— 这是唯一一处对上游 API 的**主动探测**） |
| D-75 | `!!js` 求值语义 | 无 | 强 | 无 | **强**（`:805`、`:826`） | 无 | — | 无 | **强** | 能抓 |
| D-76 | `exports.Config` 判据 | 无 | **弱→无** | 无 | 弱（`:365` 固化 NO_SCHEMA 为「不 FAIL」） | 无 | — | 无 | **无** | **抓不住**（G-01） |
| D-77 | `VERDICT_*` 语义 | 无 | 弱 | 无 | 弱（`:321`/`:377`/`:387`/`:399`/`:410`/`:423`/`:434`） | 无 | — | 无 | **弱** | 半能：`NOT_RUN` 正确；**`rows_checked==0` 却 PASS 的组合无反向用例**（G-01） |
| D-78 | `FINDING_KINDS` 分类 | 无 | 弱 | 无 | 弱（`:346` 覆盖 4 类） | 无 | — | 无 | **弱** | 半能 |
| D-79 | 临时目录清理 | 无 | 无 | 弱（`:1066 test_check_dsh_preset_smoke_passes_and_cleans_temp_home`） | 无 | 无 | — | 无 | **弱** | 半能：只测 28u 的 temp home；**不测 `dsh_compat` 自己的 `spg-dsh-compat-*`**（实测存在 6 个历史残留） |
| D-80 | 探针隔离 | 无 | 中（自报 `home_writes`） | 无 | 弱（`:857 test_isolated_home_witness_reports_zero_writes`，自证） | 无 | — | 无 | **弱** | **抓不住**：`home_writes` 是自证（`dsh_compat.py:58-63` 自己也声明「NOT a global no-write proof」） |
| D-81 | Node CLI 行为 | 无 | 弱 | 无 | 无 | 无 | — | 无 | **弱** | 半能 |
| D-82 | 渲染层契约 | 弱（28u 打印格式） | 弱 | 无 | 无 | 无 | — | `test_contract_matrix.py:43-52`（快照） | **弱** | 半能 |
| D-83~D-88 | 看护接线 | 强（28u 自测） | 强（28v 自测） | 弱（`:1066`） | 无 | 强 | — | `contract_matrix/snapshots.json:183-184`；`check-projection-sync` | **中** | 能抓接线丢失（快照/注册）；**抓不住**接线背后的语义 |
| D-89 | Segment 40 已退役 | — | — | — | — | — | **不存在** | `registry.py:428-431` 注释 | **无** | 不适用（已退役，且注释已记录原因） |
| D-90 | 适配器清单/矩阵 | 无 | 无 | 强（`:592`/`:611`） | 无 | 无 | — | `check-runtime-readiness-matrix` | **中** | 能抓 drift 的**存在性**，不抓**正确性** |
| D-91 | 注入面锚点关键词 | 无 | 无 | 强（`:180-201`） | 无 | 无 | — | `check-injection-contract`（`:702` 有反相用例） | **强** | 能抓 |
| D-92 | dsh 无 headless runner | — | — | — | — | — | — | 注释 `:18139-18141` | **无** | 不适用（有意决策，且已记录） |
| D-93 | 4 条 dsh claim | 无 | 无 | 无 | 无 | 无 | — | `verify_workflow.py:19619-19634` claim registry | **弱** | 半能：claim 登记 ≠ 能力被验证 |
| D-94, D-95 | 两条 dsh 版本投影 | 无 | 无 | 强（`:674 test_dsh_version_projections_are_satisfied`） | 无 | 无 | — | `check-projection-sync`（实测 15 文件，**但 `PROJECTION_SYNC_PATTERNS` 内 dsh 相关 0 条**） | **中** | 能抓（由该测试兜底）；**但 28b 主 check 不覆盖 dsh** |
| D-96, D-97, D-98 | 清理范围/canonical 产物 | 无 | 无 | 无 | 无 | 无 | — | `check-manifest-consistency`（`checks/manifest.py:323-327` 比对 `PLUGIN_SCOPE_DIRS`）、`test_cleanup.py:20-83` | **强** | 能抓（有 `PLUGIN_SCOPE_DIRS` 一致性断言） |
| D-99 | git hooks 的 dsh 路径 | 无 | 无 | 强（`:529`/`:562`/`:585`） | 无 | 无 | — | 无 | **强** | 能抓 |
| D-100 | 投影归一化 `\r\n` | 无 | 无 | 弱（`:674` 版本投影测试不涉行尾） | 无 | 无 | — | `checks/projection.py:13-14` | **弱** | **抓不住**（与 D-66 同类） |

### 4.1 矩阵盲区汇总（如实标注，不美化）

| 盲区 | 涉及的依赖点 | 为什么今天抓不住 |
|---|---|---|
| **B-1 包声明面零覆盖** | `D-01, D-04, D-05, D-06, D-07` | 无任何 check 断言 `package.json` 的 `dsh.bundle.patch` 键、`exports` 可经包名解析、`files` 白名单完整性、`peerDependencies` 存在性 |
| **B-2 零 schema 行专项盲区** | `D-40, D-41(command-compact), D-42(tool-subagent-control, list-agents), D-44(tool-ask-user)` | `dsh_compat.py:371-376` 把无 `Config` 导出的行降级为 `NO_SCHEMA`（非 finding），`:377` 的 `checked` 计数把它们排除；裁决式 `:1000-1025` 又不看 `rows_checked` ⇒ **5/23 行零校验却 PASS** |
| **B-3 三方 `DSH_HOME` 解析无差分闸门** | `D-16, D-47` | 无一处把 `lib/index.js` 内联实现、`launch.py` 内联实现与上游 `dsh-home-paths` 做差分；实测已存在分歧（G-06） |
| **B-4 渲染器行尾语义无覆盖** | `D-66, D-100` | parity 测试（`test_dsh_adapter.py:1127`）只读真实模板，该模板实测 0 个 CRLF、0 个孤立 CR ⇒ 断言恒真；无 `\r` 注入用例 |
| **B-5 手写解析器无结构化负相** | `D-48, D-49` | 无「拼错 token」用例（`renderComposition` 的 `leftovers` 实测抓不住，G-08）；无「同缩进列表项」用例（G-05） |
| **B-6 失败注入零覆盖** | `D-22, D-79` | 无 `renameSync` 失败用例、无 `homedir()` 抛错用例、无「探针超时后临时目录是否清理」用例（本次补测结果：不泄漏，但那是**本次补测**而非既有守卫） |
| **B-7 上游语义变更无探测** | `D-09, D-11, D-12, D-39, D-45, D-57, D-93` | `insert` 语义、`cordis:` 前缀语义、宿主平面分工、注释里的版本引用、`verified_on` 时效 —— 均无机器比对 |
| **B-8 node 缺失即静默** | `D-03, D-13, D-14, D-19, D-23, D-46, D-65, D-67, D-68` | 9 处 node-gated 测试均为 `skipTest`；无一处把 skip 上升为 `NOT_RUN` 披露 —— 与项目自己的 `NOT_RUN` 政策（`dsh_compat.py:75-77`）不一致 |
| **B-9 `check-projection-sync` 不覆盖 dsh** | `D-94, D-95` | 实测 `PROJECTION_SYNC_PATTERNS` 11 条中 dsh 相关 0 条；dsh 两条投影目前只由 `test_dsh_adapter.py:674` 单点兜底 |
| **B-10 全仓无「依赖面总清单」** | 全部 100 条 | 今天不存在任何单一文件列出本插件对 dsh 的全部依赖点；本报告是首份（且是**一次性快照**，无守卫保证其保鲜） |

---

## 5. 兼容性缺口清单

排序依据：**「dsh 下一次升级后会不会静默失效或致命」** —— 先列「会致命」与「会静默失效」，再列「能发现/降级」。

---

### 🔴 致命级 + 静默级（升级后**大概率**发生且今天看不见）

#### G-01 【已实测复现 · FIX-315 证实】`NO_SCHEMA` 行零校验却报 PASS

| 项 | 内容 |
|---|---|
| **缺口** | 5/23 enabled 行（`plan-mode`、`command-compact`、`tool-subagent-control`、`tool-subagent-list-agents`、`tool-ask-user`）无 `Config` 导出 ⇒ 护栏对其 config **零校验**，却与其他行一起计入 `PASS` 结论 |
| **触发条件** | 任一上述插件引入/改名 `Config` 键，或（更现实）dsh 升级后这些插件**新增**了 schema 而我们的 config 键变非法 |
| **是否静默** | **是（最强静默）**：`verdict: PASS` + `issues: []` + 仅一行 `NO_SCHEMA` 出现在 `details`（`emit_check_section` 在 PASS 分支**只打印含 `NOT verified` 的 detail**，`NO_SCHEMA` 不含该词 ⇒ 屏幕上完全不显示） |
| **最小可观测信号** | 今天**不能**发现 |
| **实测证据（复现）** | ① 真实模板：`rows_enabled: 23`，`rows_checked: 18`，其中 5 行 `kind: NO_SCHEMA` ② 伪造「仅一行 NO_SCHEMA + `config: {totallyBogusKeyThatMustBeRejected: 12345}`」→ `verdict: PASS`，`enabled: 1`，**`checked: 0`**，`issues: []`，reason = `0 enabled row(s) validated …` ③ 伪造「1 行 PASS + 1 行 NO_SCHEMA(bogus)」→ `verdict: PASS`，`enabled: 2`，`checked: 1`，`issues: []`，reason = `1 enabled row(s) validated …` ④ **正向对照**：同 bogus config 放在有 schema 的 `dsh-persona` 上 → `verdict: FAIL`，`CONFIG_INVALID: $.prefix missing required value`（证明护栏在有 schema 时有效） |
| **代码根因** | `dsh_compat.py:371-376`（无 `Config` ⇒ `NO_SCHEMA` + `continue`，不计 `checked`）；`:377`（仅此处 `checked += 1`）；`:1000-1025`（裁决只看 `failures` 与 `rows_enabled`，**不看 `rows_checked`**） |
| **测试反向固化** | `test_dsh_compat.py:365 test_no_schema_rows_are_disclosed_not_failed` 明确把 `NO_SCHEMA` 断言为「不 FAIL」；`:399 test_zero_enabled_rows_degrades_to_not_run` 只覆盖 `enabled==0`。**即当前行为是被测试固定下来的**，不是意外 |
| **交互** | 与项目自身的 `NOT_RUN` 政策（`dsh_compat.py:75-77`「NOT_RUN never counts as a gate issue — it discloses an unverified fact instead of inventing a green one」）**逻辑冲突**：这里恰恰「inventing a green one」 |

#### G-02 【已实测证实 · FIX-311 R1-1】group 行 `name` 从不解析 → 静默假阴性

| 项 | 内容 |
|---|---|
| **缺口** | group 行的 `name` 永不被解析；`cordis:` 前缀或不可解析的 group name 都直接短路，group 自身的模块契约零校验 |
| **触发条件** | dsh 升级改动 group 行的合法 `name` 形态（如取消 `cordis:group` 内建、要求显式包名） |
| **是否静默** | **是**：护栏 `verdict: PASS` |
| **最小可观测信号** | 今天**不能**发现 |
| **实测证据** | 构造 `- id: planning / name: cordis:group / group: true / config: [内层 @deepseek-ai/dsh-persona]` → `verdict: PASS`，`enabled: 1`，`checked: 1`；`planning` 行**未产生任何 row 记录**（既非 `BUILTIN` 亦非 finding） |
| **代码根因** | `dsh_compat.py:297 if (row.group)` 分支只做 `Array.isArray(row.config)` 形态检查（`:298-302`）→ 立刻 `walk(row.config, …)`（`:311-313`）→ **从不 import/校验 group 的 `name`**。`:275-281` 的 `name` 非空检查已在 `:277` 之前用 `row.name` 取值，故 group 的 name 仅在 `ROW_SHAPE` 报错路径被使用 |
| **测试反向固化** | `test_dsh_compat.py:681 test_group_rows_recurse_into_their_config_list` 只断言「递归进去了」，**不断言 name 被解析** |

#### G-03 【已实测证实 · FIX-311 R1-2】group 自身 `disabled` 被提前无条件求值 → 窄假阳性

| 项 | 内容 |
|---|---|
| **缺口** | loader 对 group **自己**从不调用 `disabledOf`（`Entry._disabled` 首行 `if (options.group) return false`），护栏却无条件求值 |
| **触发条件** | group 行带 `disabled: !!js <抛错表达式>` |
| **是否静默** | 反向：**假 FAIL**（对用户「无端报红」，且**吞掉该 group 内所有子行的真实校验** —— 子行既不报 PASS 也不报 FAIL） |
| **最小可观测信号** | 今天**能**发现（护栏会红），但**红错了对象**：报的是不存在的 mount 失败 |
| **实测证据** | 构造 `- id: planning / name: cordis:group / group: true / disabled: !!js undefinedVariable.nope / config: [内层 persona]` + 一个 group 外的合法 persona 行 → `verdict: FAIL`，`issues[0] = '… row "planning" (cordis:group): group disabled !!js expression threw: ReferenceError: undefinedVariable is not defined'`，`enabled: 1`（只有 group 外那一行被计入） |
| **代码根因** | `dsh_compat.py:303-310`：`if (row.group)` 分支内**先** `groupDisabled = disabledOf(row, ctx)` 并 try/catch → 抛错即成 `DISABLED_EXPR_ERROR` finding 并 `continue`（`:306-310`），子行永不进入 `walk` |
| **测试反向固化** | `test_dsh_compat.py:754 test_throwing_group_disabled_expression_is_a_finding` 断言抛错 group 表达式**是** finding。**该测试固化的正是与 loader 语义相悖的行为**——注释 `:755-756` 声称「`disabledOf` is called unguarded by the loader's ancestor walk」，但祖先走查只对被**祖先**调用，group 自身被 `if (options.group) return false` 短路 |

#### G-04 【部分证实 · FIX-313(b)】`ensurePreset` catch 清理目标可退化为进程 CWD

| 项 | 内容 |
|---|---|
| **缺口** | `lib/index.js:231-234` 的 best-effort 清理遍历 `readdirSync(dirname(outcome.dir \|\| '.'))`；`outcome.dir` 在 `:189` 初始化为 `''`，只在 `:192-193` 被赋值。若 `resolveDshHome()`（`:192`）抛错，`outcome.dir` 仍为 `''` ⇒ `dirname('.')` = `.` = **进程 CWD** ⇒ 会删除 CWD 下任何名为 `governance.staging-*` 的目录 |
| **触发条件** | ① `homedir()` 抛错（`DSH_HOME` 未设且 `USERPROFILE`/`HOME` 皆不可解析）**且** ② CWD 下恰有 `governance.staging-*` 目录 |
| **是否静默** | 反向：**误删用户 CWD 下的同名目录**（今天不能发现；不影响预设，但属文件系统副作用） |
| **最小可观测信号** | 今天**不能**发现（无任何守卫） |
| **实测证据（部分证实）** | 构造探针：在 CWD 下放 `governance.staging-VICTIM/`，把 `USERPROFILE`/`HOME` 清空后调 `ensurePreset` → **未走到 catch**：`homedir()` 仍返回 `C:\Users\peter`（Windows 走 OS API 而非环境变量），`outcome.synced: true`，`warnings: []`，**victim 存活**。⇒ 该路径**机制存在但未能复现触发条件**（故本条判 `部分证实`） |
| **代码根因** | `lib/index.js:189-193`（`outcome.dir = ''` 初值 + 赋值点顺序）+ `:231-234`（清理用 `dirname(outcome.dir \|\| '.')`） |
| **对比** | `launch.py:264, 266` 的等价清理用的是**显式 `staging` 变量**（`:261-266`），无此退化路径 —— 印证 plan-tracker 对 `FIX-313(b)`「`launch.py:266` 会删」的观察 |
| **补充实测** | 版本标记不匹配时的完整重建（run3）后 `staging` 残留 = `[]`；正常路径 catch 清理**有效** |

#### G-05 【已实测证实 · FIX-316 邻域】`launch.py` 手写 `customSkillDirs` 扫描对合法 YAML 漏项

| 项 | 内容 |
|---|---|
| **缺口** | `launch.py:447-465` 手写缩进扫描用 `if len(line) - len(line.lstrip()) <= block_indent: break`（`:459`）作为块结束判据；YAML 允许**列表项与键同缩进** |
| **触发条件** | 模板/任何组合文件把 `customSkillDirs:` 的列表项写成与键**同缩进**（合法 YAML block sequence） |
| **是否静默** | **是**：命中 0 条 ⇒ `verify_preset_loading` 报 `preset declares no customSkillDirs — … /governance would not load`（`:606-608`）**是 FAIL 方向**；但更危险的是若列表项**部分**命中则残留项完全不被检查 |
| **最小可观测信号** | 今天**不能**发现（无该形态的用例） |
| **实测证据** | ① 真实渲染产物（列表项比键多缩进 2 格）→ 命中 **2** 条（正确） ② 构造 `a:\n  b:\n    customSkillDirs:\n    - /one\n    - /two\n`（同缩进，合法 YAML）→ 命中 **0** 条 |
| **代码根因** | `launch.py:453-459`：`block_indent` 取 `customSkillDirs:` 行的**行首缩进**，而列表项合法缩进可等于该值 ⇒ `<=` 提前 `break` |

#### G-06 【已实测证实 · FIX-316】`DSH_HOME` 空白处理的**三方**分歧

| 项 | 内容 |
|---|---|
| **缺口** | 上游 `dsh-home-paths` `resolveDshHome` 对空白**用原值**（`expandHomePath(fromEnv)`，不 trim），只在**空字符串**时回落默认；`lib/index.js:103-105` **trim**；`launch.py:115-118` **不判空白**（`if env:` 对 `"   "` 为真） |
| **触发条件** | `DSH_HOME` 被设为空白或含首尾空格（环境注入、CI 变量、`set DSH_HOME= ` 之类） |
| **是否静默** | **是**：落地到不同目录 ⇒ 预设写到宿主不读的位置，用户看不到预设且无报错 |
| **最小可观测信号** | **部分能**：28u/`--smoke` 有隔离守卫（会 REFUSED），但守卫比对的是 `real_dsh_home()`（`launch.py:357-363`，由 `Path.home()` 导出），**不与上游 `resolveDshHome` 比对** |
| **实测证据（逐 case）** | `DSH_HOME="   "`（纯空格）→ 上游 `C:\Users\peter\.dsh`；`launch.py` `dsh_home()` = **`"   "`**（字面），`preset_dir()` = `"   \.agent-presets\governance"`；`lib/index.js` `C:\Users\peter\.dsh`（trim 后 `join(homedir(),'.dsh')`）— **三方分歧** `DSH_HOME="\t"` → 上游 `C:\Users\peter\.dsh`；`launch.py` = `"\t"`（字面）；`lib/index.js` = `C:\Users\peter\.dsh` — **三方分歧** `DSH_HOME="  C:/tmp/x  "` → 上游 `resolve("  C:/tmp/x  ")`；`launch.py` `C:\tmp\x`；`lib/index.js` `C:\tmp\x` — 三方分歧 `DSH_HOME="C:/tmp/x "` → 上游 `C:\tmp\x `（保留尾空格）；`launch.py` `C:\tmp\x`；`lib/index.js` **`C:\tmp\x`** — `lib/index.js` 与上游分歧 `DSH_HOME=""` / 未设 → 三者均 `C:\Users\peter\.dsh` — **一致** `DSH_HOME="~"` / `"~/x"` / `"~\\x"` → 三者**一致** |
| **代码根因** | `lib/index.js:102-105`（`.trim()`）；`launch.py:115-118`（无 trim、无空白判定）；上游 `dsh-home-paths/lib/index.js:73-75` |
| **修正结论（相对任务书表述）** | 任务书称「`DSH_HOME` 带空白时**内联解析器与参考实现**落点分歧」。实测更精确：**真空白场景（`""`）三者一致**（因上游与 `lib/index.js` 都最终落到 `~/.dsh`）；**分歧在 `launch.py`（`"   "`/`"\t"` 落字面空白路径）与上游、以及 `lib/index.js` 在「含尾空格的合法路径」上与上游**。原表述方向正确但落点需修正 |

#### G-07 【已实测证实 · FIX-316】`leftovers` 守卫对拼错 token 无效

| 项 | 内容 |
|---|---|
| **缺口** | `lib/index.js:161` 的 `leftovers` 只检查**已知 3 个 token 是否残留**，不检查**未知/拼错 token**；`launch.py:153` 的兜底 `any(token in composition for token in TOKEN_PATHS)` 同理 |
| **触发条件** | 模板里出现 `__GOVERNANCE_SKILLS_ROOTS__`（多一个 S）之类的拼写错误 |
| **是否静默** | **是**：渲染成功、守卫报 `leftovers: []`，字面拼错串被写进预设 ⇒ 该 `customSkillDirs` 项指向上游不存在的路径 |
| **最小可观测信号** | **部分能**：`test_dsh_adapter.py:170 test_template_uses_only_known_tokens` 用 `re.findall(r"__[A-Z0-9_]+__")` 抓 stray token ⇒ 能覆盖 `__GOVERNANCE_SKILLS_ROOTS__`（全大写+下划线）；**但不覆盖** `__Governance_Repo_Root__`（混合大小写，正则不匹配） |
| **实测证据** | 通过 `lib/index.js` 导出直调 `renderComposition`： `__GOVERNANCE_SKILLS_ROOTS__` → `leftovers: []`，`tokenStaysLiteral: true`，`guardCaught: false` `__GOVERNANCE_SKILL_ROOT__` → 同 `__GOVERNANCE_SHIM_ROOT__` → 同 `__Governance_Repo_Root__` → 同 `__GOVERNANCE_NEW_TOKEN__` → 同 |
| **代码根因** | `lib/index.js:161`（`Object.keys(TOKEN_PATHS).filter(...)`）；`launch.py:153`（同一集合） |
| **交叉证据** | `docs/reviews/review-REL-076-CODE-R0.md:135` 已自行记录该现象（F3）——**本次独立实测确认，且证明至今未修** |

#### G-08 【已实测证实 · FIX-316】注释/文档引用与代码实际不符（行号引用 / 计数口径）

| 子项 | 缺口 | 实测证据 |
|---|---|---|
| **G-08a** | `test_contracts.py:566, 568` 引用的行号已陈旧 | `:566` 称「`verify_workflow.py` L20613-20621 reads」（engine loop）→ 实际 `L20613-20621` 是 `fixture_identity` 代码（`L20613: if getattr(args, "fixture_identity", False):`）；真正的 `detail.get("skipped")` 在 **`L20488`**。`:568` 称「L7285-7297 builds `details["dsh_upgrade_regression"]`」→ 实际 `L7285-7297` 是 `forbidden_patterns` 列表与循环；真正构建在 **`L7142`**（grep `dsh_upgrade_regression"` 全仓仅 1 处命中） |
| **G-08b** | `registry.py:342` 称「83 dispatch keys」、`:347` 标题称「71 segments」，与实测不符 | 实测 `len(registry._COMMANDS) = 82`、`len(registry._SEGMENT_LOADERS) = 70`（无重复命令键、无重复 segment id）。⇒ `:342` 的「83」与 `:347` 的「71」错误；而 `:229`（「82 keys」）、`:348`（「70 segments」）、`:421`（「70 segments」）三处与实测**一致** —— 同文件内口径分裂 |
| **已排除（原假设不成立）** | ~~`test_dsh_adapter.py:652` 的 `count == 1` 与组合模板实际 2 次矛盾~~ | **实测排除**：`test_dsh_adapter.py:651` 赋值 `text = _BOOTSTRAP_TEMPLATE_PATH.read_text(...)`，`_BOOTSTRAP_TEMPLATE_PATH = _ADAPTER_DIR / "AGENTS.md.template"`（`:65`）；该文件实测 `__GOVERNANCE_REPO_ROOT__` 计数 = **1**（`:7`）⇒ 断言**正确**。组合模板实测计数 = 2，属**另一文件**，两者不冲突。该测试单独运行：`Ran 1 test … OK`（`python -m unittest discover … -p "test_dsh_adapter.py" -k bootstrap_template`） |

#### G-09 【已实测 · 部分证实 · FIX-316】`spg-dsh-compat-*` 临时目录残留

| 项 | 内容 |
|---|---|
| **缺口** | `dsh_compat.py` 的 scratch/home 目录依赖「正常返回路径 + 异常分支」的双点清理（`:761-763, 787-790, 801-802`）；进程被外部强杀时无兜底 |
| **是否静默** | 降级（不影响正确性，占磁盘） |
| **实测证据** | 实测平台 `%TEMP%` 下存在 **6 个残留**：`spg-dsh-compat-0051aecc973b`、`-0a6c7e5390e0`、`-b36be20721ba`（各含 `report.json`）、`spg-dsh-compat-home-3217a4e52ef6`、`-386d4dce66f6`、`-abd3bbf9385a`（均空）。mtime = `2026/9/12 10:12:36`、`10:12:50`、`10:16:02`（3 对） |
| **当前是否可复现** | **不可复现**：① 正常 run 新增 **0** 个 ② 1 秒超时 run 新增 **0** 个 ③ 不可解析 install override 的早期 `NOT_RUN` 新增 **0** 个 ⇒ 判为**陈旧版本残留**，非现行缺陷 |
| **最小可观测信号** | 今天**不能**（无残留计数守卫） |

#### G-10 【已实测证实 · FIX-316】非 UTF-8 / 截断输入使 `UnicodeDecodeError` 穿出公共入口

| 项 | 内容 |
|---|---|
| **缺口** | `launch.py` 三处 `read_text(encoding="utf-8")` 无 `errors=` 兜底：`:598`（`verify_preset_loading` 读组合）、`:146`（`render_composition` 读模板）、`:819`（`write_bootstrap` 读既有 AGENTS.md，此处已有 `errors="replace"`） |
| **触发条件** | 组合/模板文件含非法 UTF-8 字节（截断多字节、`0xFF`、孤立续字节） |
| **是否静默** | 反向：**致命**（未捕获异常 + 栈回溯，用户看不到可行动诊断） |
| **最小可观测信号** | 今天**能**发现（进程非零退出 + 栈），但**信息不可行动** |
| **实测证据** | ① `verify_preset_loading(bad_dir)` → `RAISED UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 16799: invalid start byte`（`0xA7` 与截断 `0xE4` 同样抛出） ② `launch.render_composition()` 在非 UTF-8 模板 → `RAISED UnicodeDecodeError … byte 0xff in position 16796` ③ **公共 CLI**：`main(["--install"])` → **exit code 1**，stderr 末尾三行 = `return f.read()` / `~~~~~~^^` / `UnicodeDecodeError: …`（**未捕获**） ④ 正常文件 → `verdict=PASS, issues=0`（对照组） |
| **代码根因** | `launch.py:598`（无 `errors`）、`:146`（无 `errors`）；对照 `:652`（有 `errors="replace"`）与 `:819`（有 `errors="replace"`）—— **同一文件内口径不一致** |

#### G-11 【已实测证实 · RISK-050 残留】注释中的宿主版本引用失真

| 项 | 内容 |
|---|---|
| **缺口** | `cordis.patch.yml:30` 与 `lib/index.js:93` 均引用「installed dsh **0.1.5-rc.2**」作为语义依据 |
| **触发条件** | 无触发条件 —— 这是**已经存在**的事实错误 |
| **是否静默** | **是**：注释永不参与任何机器断言 |
| **最小可观测信号** | 今天**不能**发现（28v 报告真实版本 `0.1.5-rc.1`，但不与注释比对） |
| **实测证据** | `cordis.patch.yml:30` 原文 `# Patch semantics (installed dsh 0.1.5-rc.2, \`dsh-app-boot/lib/index.js\``；`lib/index.js:92-93` 原文 `Mirrors \`resolveDshHome()\` from \`@deepseek-ai/dsh-home-paths\` (installed dsh 0.1.5-rc.2, \`lib/index.js\`: …)`；安装态实测 **两处均为 `0.1.5-rc.1`** |

#### G-12 【已实测证实】`adapter-manifest.json` 的 E2E 证据已严重过期

| 项 | 内容 |
|---|---|
| **缺口** | `adapter-manifest.json:75 verified_on: "2026-07-08"`；`:76` 证据串为 `dsh --version returns 0.1.0-rc.6` |
| **是否静默** | **是** |
| **最小可观测信号** | 今天**不能**发现 |
| **实测证据** | 安装态 `0.1.5-rc.1`（比 `0.1.0-rc.6` 新 5 个 rc 版本）；`verified_on` 距本报告 67 天。`support_status: "runtime-verified"`（`:5`）因此建立在过期证据上 |

---

### 🟠 降级级（升级后会坏但可发现 / 影响受限）

| ID | 缺口 | 触发条件 | 静默? | 今天能否发现 |
|---|---|---|---|---|
| **G-13** | `NO_SCHEMA` 行的 config 在**上游插件侧**（如 `dsh-plan-mode` 的 `PlanModeConfig`）其实是可校验的，护栏只是拿不到 schema（`exports.Config` 为空） | dsh 改变「无 Config 导出」的插件约定 | 是 | 不能（见 G-01） |
| **G-14** | `dsh_compat` 的 `oracle_packages` 实测解析自 **npx 缓存树**而非 `profiles/node_modules`（`plane` 报 `DSH_HOME/profiles` 但四个包 `path` 全在 `C:\Users\peter\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\node_modules\…`） | profile 平面与 npx 树版本漂移 | 是 | 部分能：护栏有 `other_planes` + `[SKEW]` 报告（`dsh_compat.py:939-952`），但本次实测 `other_planes: []` ⇒ **该告警今天为未触发状态**，无法确认其有效性 → R-12 |
| **G-15** | `ensurePreset` 无并发保护：`:206` 检查 → `:223` 删除 → `:224` rename 之间存在窗口，第二个 boot 可能进 catch | 两进程同时首次 boot（或多会话同时启动） | 是（仅 warn，旧预设保留或被删后未替换） | 不能（无并发用例） |
| **G-16** | `launch.py:49` 的 `--smoke` 与 `--dry-run` 互斥（`:893-897`），但 `main()` 先判 smoke（`:899`）⇒ `--smoke` 忽略 `--dry-run` | 无（属设计取舍，仅记录） | — | — |
| **G-17** | `_real_home_witness` 把 `<home>/settings.yaml` 的 `size+mtime_ns` 纳入比对（`launch.py:438-439`）；若宿主在 smoke 运行窗口内写 `settings.yaml`，gate 会**假 FAIL** | 另一进程/会话在 ~1s 窗口内改设置 | 反向：假 FAIL 阻塞发布 gate | 部分能（本次 24s×8 采样全部 STABLE ⇒ 未观察到，但无双会话并发验证）→ R-04 |
| **G-18** | `FINDING_KINDS` 不含 `NO_SCHEMA` / `BUILTIN` / `DISABLED_INHERITED` / `PASS`，分类表本身是「可信面声明」但无守卫 | 上游引入新 row 形态（如 `import`-less 行） | 是 | 不能 |

---

### 🟢 已确认闭环（**逐条反驳或证实**，供下游设计避免重复投入）

| 项 | 结论 | 证据 |
|---|---|---|
| **RISK-050 上游内部面耦合残留** | **已证实基本清零**（不再是「用 UPDATE 打 dsh 内部行 / `!!js` 自定位」的形态） | ① `cordis.patch.yml` 非注释行：`- id:` **1** 处（`L42` 本包自己的插入行）、`insert:` 1 处、`!!js` **0** 处、`trust:` **0** 处 ② `lib/index.js` 代码行（排除注释）：host-plane `ctx.*` 调用 **0**、`process.argv` **0**、非 `node:` import **0**、`profiles` 扫描 **0**、`trust:` **0**、`require()` **0** ③ 上游 `applyEntryPatches` 语义与注释一致（`dsh-app-boot/lib/index.js:59, 71-85`） |
| **RISK-050 残留（部分）** | **仍残留 2 处注释级耦合**：`cordis.patch.yml:30` / `lib/index.js:93` 的版本引用失真（G-11） | 见 G-11 |
| **DEC-187 机检判据 I-1（install 前后 entry 列表逐字节等价）** | **本次未执行**（`NOT_RUN`，见 1.4）；但**静态面已满足**：零 UPDATE 行 ⇒ 结构上不可能改动既有行 | `cordis.patch.yml` 非注释行扫描 + 上游 `applyEntryPatches` 的 `L85 data.push(...insert)` 分支 |
| **两点交付路径契约一致性（0.80.0 FIX-310 主张）** | **证实**：三路径 sha256 全等 `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723` | `lib/index.js` render = `launch.py` render = 真实 `~/.dsh/.agent-presets/governance/agent.cordis.yml`，三者均 16796 字节；`launch.py` 渲染文本 13566 chars |
| **`insert` 无 `id` 追加到根列表的语义** | **证实**（与注释一致），但**注释里的版本号不正确** | `dsh-app-boot/lib/index.js:71-85`；版本见 G-11 |
| **`customSkillDirs` 按 `path.resolve`（即进程 CWD）解析 ⇒ 必须绝对路径** | **证实** | `dsh-skill-filesystem/lib/index.js:36`（schema）+ `:79 .map((root) => resolve(root))`（无 base 参数 ⇒ CWD） |
| **`.agent-presets` 是 USER preset root** | **证实（结构层面）** | `dsh-agent-presets/lib/index.js:195 const USER_PRESET_DIR = ".agent-presets"`；`:1300 this.resolvedRoots = [`；`:1565 this.resolvedRoots.some((root) => root.trust === "user")`。**「第一个 root 胜出」的确切顺序未逐字核验** → R-13 |
| **`dsh-persona` 的 `Config` 存在且 `prefix` 为必填** | **证实**（护栏的核心有效性基础） | 实测 `exports.Config = YES`；反向对照：缺 `prefix` → `CONFIG_INVALID: $.prefix missing required value` |
| **5 个 NO_SCHEMA 行确实不带 `Config` 导出** | **证实**（不是护栏 bug，是插件侧事实） | 逐包实测：`dsh-plan-mode` `typeof=function keys=["inject"] Config=NO`；`dsh-command-compact` `keys=["apply","inject","name"] Config=NO`；`dsh-tool-subagent-control` 同形；`dsh-tool-subagent-control/list-agents` 同形；`dsh-tool-ask-user` 同形 |
| **`check-dsh-skills-manifest` 已退役** | **证实不存在** | 全仓无 `check_dsh_skills_manifest` 定义、无 `DSH_SKILLS_DISK_PATTERNS` 符号；`registry.py:428-431` 记录退役原因（FIX-310 移除 dead `dsh.skills` 声明）；`package.json` 实测只有 `dsh.bundle.patch` |
| **现有 `--smoke` / Check 28u 隔离真实** | **证实** | 实跑 `Exit code: 0; real-home writes: 0; temp DSH_HOME: C:/Users/peter/AppData/Local/Temp/spg-dsh-smoke-l4aa_g18 (removed)` |
| **`dsh_compat` 探针隔离真实** | **证实（限其自述范围）** | `isolation.home_writes: 0`；`temp_home` 指向 `%TEMP%\spg-dsh-compat-home-*`；**该机制自述「NOT a global no-write proof」**（`dsh_compat.py:58-63, 746-753`）—— 该自述**准确**，本次核实了 `USERPROFILE`/`HOME` 确实未重定向（`:772-773` 只设 `DSH_HOME`） |

---

## 6. 可调测性现状

### 6.1 一次 dsh 升级后出问题：从用户现象到根因需要几步

| 步骤 | 今天靠什么证据 | 是否自动化 | 耗时量级 |
|---|---|---|---|
| **S0 用户现象** | 「预设选不到」/「`/governance` 不见了」/「新会话创建失败」 | 否 | — |
| **S1 判断是「预设没渲染」还是「渲染了但 mount 失败」** | 看 `~/.dsh/.agent-presets/governance/` 是否存在、`.dsh-bundle-version` 内容 | **否（纯手工）** | 分钟级 |
| **S2 若存在，逐行验证 schema** | `python …/dsh_compat.py --json`（或 `verify_workflow.py check-dsh-preset-compat`） | **是** | 1.1s（实测正常 run 耗时 1.1s） |
| **S3 若 S2 报 `NOT_RUN`**，判断为何没有可用平面 | 读 `--json` 的 `install.source` / `install.reason` / `install.node_modules` | **是（披露）** | 秒级 |
| **S4 若 S2 报 PASS 但用户仍失败** | **今天无路径** —— 需靠人工读 `details` 逐行、或读源码 | **否** | 小时级 |
| **S5 判定是不是宿主侧（entry 列表被改）** | `dsh --profile web --dump-config` 前后 diff（**未自动化**） | 否 | 小时级 |
| **S6 判定是 skill 目录/shim 层** | `python …/launch.py --smoke`（隔离） | **是** | 秒级 |
| **S7 判定是 git hook 自升级断链** | 手工检查 `.git/hooks/*` 与 `skill-root.txt` | 否 | 分钟级 |

**结论**：**S2 与 S6 是今天仅有的两个自动化定界点**；**S0→S1、S4、S5、S7 全是手工**。因此「一次升级后出问题」的典型路径是 **2 个自动化步 + 至少 3 个手工步**，且 **S4 无路径**（PASS 但失败 = 无法定界）。

### 6.2 是否有「一条命令给出分阶段诊断」的入口？

**答：没有。**

| 候选命令 | 实际覆盖的阶段 | 为什么不够 |
|---|---|---|
| `verify_workflow.py check-dsh-preset-compat`（→ `dsh_compat.run_cli`） | 阶段：平面发现 / 组合发现 / 逐行 schema / 隔离 | ① 不覆盖「预设是否已渲染到 user 根」② 不覆盖「skill 目录与 shim 是否可解析」③ 不覆盖「宿主 entry 列表是否被改」④ 不覆盖「版本投影/hook」⑤ `NO_SCHEMA` 行零校验（G-01） |
| `verify_workflow.py check-dsh-preset-smoke`（→ Check 28u） | 阶段：隔离渲染 / skill catalog / `/governance` 手势 | ① 不覆盖 schema 深度（靠 D-51 间接跑 28v，输出被折叠）② 不覆盖宿主侧 ③ 不覆盖版本投影/hook ④ 输出是 `[SMOKE]` 文本而非结构化分级 |
| `launch.py --smoke` | 同 28u（28u 就是它） | 同上 |
| `launch.py --dry-run` | 只打印计划写入，不做校验 | 不是诊断入口 |
| `launch.py --check` | 只打印 `adapter-manifest.json` 摘要 | 不是诊断入口 |

**输出字段现状（供下游设计参考）**：`check-dsh-preset-compat` 的 `--json` 输出含 `verdict` / `reason` / `issues` / `details` / `install`（`source`/`node_modules`/`dsh_version`/`cli_package`/`oracle_packages`/`other_planes`/`node_version`/`probe_versions`）/ `isolation`（`temp_home`/`home_writes`/`mechanism`）/ `compositions[]`（`path`/`status`/`enabled`/`checked`/`inherited_disabled`/`rows[]`)/ `rows_enabled`/`rows_checked`/`rows_inherited_disabled`。**这是目前最接近「分阶段诊断」的输出，但它自身没有阶段分层概念**，且 5 行零校验不进入 `issues`。

### 6.3 今天**无法在离线/CI 环境**复现的面（「必须有真机才能测」清单）

| # | 面 | 为什么必须有真机 | 证据 |
|---|---|---|---|
| T-1 | `dsh plugin add` / `remove` 对 profile `bundles` 的写入与撤销 | 需要写 `$DSH_HOME/profiles/<p>/{package.json,pnpm-lock.yaml}` + pnpm 存储；CI 里等价物 = 一次真实 dsh 安装 | 本次 `NOT_RUN`（1.4） |
| T-2 | 组合后 entry 列表与未安装时逐字节等价（DEC-187 I-1 机检判据） | 需 `dsh --profile <p> --dump-config` 完整 boot | 本次 `NOT_RUN` |
| T-3 | 预设是否真的出现在设置页（`dsh-preset-roster` claim） | 需要 live 设置面板/roster 枚举；`dsh_compat` 只做静态 schema | `claude` 提示自带 claim registry：`verify_workflow.py:19623-19634` 4 条 claim 均为「用户可用性」面 |
| T-4 | 会话内 skill 目录真的被注册（`dsh-session-projection`） | 需要一次真实会话启动 | `launch.py:790-793` 明示 `live session 面: NOT_RUN` |
| T-5 | `/governance` 手势真的可触发 | 同上（`launch.py:646-650` 只证 shim 文件存在且 frontmatter 合法） | 同上 |
| T-6 | persona `{{model}}`/`{{cwd}}` 真的被宿主插值 | 需要真实 agent 路由上下文 | `:49`；本次 `R-08` |
| T-7 | 真实宿主平面注册表（`shell-env` / `subagents` / `web` service）是否满足预设行的依赖 | 需要宿主 `cordis.yml` 全量 + boot | `:96-97, 194-196, 266-267` 注释依赖宿主分工；本次 `R-09` |
| T-8 | npm registry 安装形态（非 `link:`） | 本机是 `link:D:/AI/…`（`~/.dsh/profiles/web/package.json:18`）；registry 形态需真实 publish+install | 1.4 |
| T-9 | 宿主在 smoke 窗口内写 `settings.yaml` 造成的假 FAIL | 需要双会话并发 | G-17；本次 24s 采样未观察到 |
| T-10 | `dsh-agent-router` 等宿主侧插件的持续写入是否影响 witness | 需要 live 宿主 | `launch.py:421-427` 已记录 2026-09-09 的实测（whole-home 会变） |

### 6.4 现有 fixture 与 negative case 覆盖面

| 类别 | 覆盖 | 缺口 |
|---|---|---|
| **正向 fixture** | `test_dsh_compat.py` 43 个用例（含 `:321`、`:545`、`:549`、`:637`、`:871`）；`test_dsh_adapter.py` 43 个用例（含 `:1127` parity、`:1158` 幂等） | 无「真实升级前后」的 fixture 对（没有把某个 dsh 版本的 schema 冻结成 fixture） |
| **schema 负相** | `:331 test_invalid_config_is_fail_with_row_module_and_schema_message`、`:612 test_persona_row_using_text_is_rejected_naming_persona_and_prefix`、`:562 test_structural_floor_fires_on_the_pre_fix_shape` | **无 NO_SCHEMA 行带非法 config 的负相**（G-01 正是这个缺口） |
| **group 语义负相** | `:719`（`disabled: true` 子行不校验）、`:736`（`!!js true`）、`:743`（`disabled: false` 仍校验）、`:754`（抛错 group 表达式是 finding）、`:778`（嵌套继承） | **无「group name 不可解析应报错」的负相**（G-02）；**`:754` 的负相固化了与 loader 相悖的行为**（G-03） |
| **`!!js` 负相** | `:805`（scope 含 `baseUrl`/`process`）、`:826`（抛错即 finding 不崩） | 无「`process` 从 scope 移除」或「`!!js` 方言变更」的负相 |
| **平面/安装负相** | `:165`（非法 override 不回退）、`:201`（无安装 → NOT_RUN）、`:245`（未设 `DSH_HOME` 不猜 `~/.dsh`）、`:441`（oracle 失败 → NOT_RUN） | 无「`DSH_HOME` 为空白」的负相（G-06）；无「上游 API 改名」的负相（D-74 只有存在性检查） |
| **隔离负相** | `test_dsh_adapter.py:806`/`:819`/`:832`（三种 REFUSED）、`:1025`（witness 变化即 FAIL）、`:1066`（28u 清临时 home） | 无「探针被强杀后残留」的负相（G-09） |
| **渲染负相** | `:206`（纯代换）、`:170`（stray token 只覆盖全大写）、`:433`（零侵入） | **无 `\r` 注入**（D-66 / G-05 邻域）、**无拼错 token**（G-07）、**无同缩进 `customSkillDirs`**（G-05）、**无非 UTF-8**（G-10） |
| **真实环境负相** | `:301`/`:303`/`:330`/`:341`（dry-run 零写入、uninstall 范围受限） | 无「`DSH_HOME` 含尾空格」的负相 |

### 6.5 失败定界粒度的量化现状

| 层 | 今天能否独立定界 | 判据 |
|---|---|---|
| 包声明层（`package.json` `dsh.*`） | **不能** | 无任何 check（B-1） |
| 补丁层（`insert` 是否被应用） | **不能** | 无 check 解析 profile 组合后的 entry 列表 |
| 渲染层（模板 → 组合） | **能（部分）** | parity 测试 + `--smoke` 渲染；但行尾与拼写漏网（B-4, B-5） |
| 行 schema 层 | **能（18/23 行）** | `dsh_compat` 逐行 `resolveConfig`；5 行零校验（B-2） |
| 模块解析层 | **能** | `MODULE_UNRESOLVED` / `IMPORT_ERROR` 均为 finding |
| skill 目录注册层 | **能（文件存在性）** | `--smoke` 的 `skill_catalog` / `gesture_shim`；**不能**证宿主真的注册了（T-4） |
| 宿主 entry 层 | **不能** | 无 `dump-config` 自动化（T-2） |
| 版本投影 / hook 层 | **能（分散）** | `test_dsh_adapter.py:674`、`:529`/`:562`/`:585`；`check-projection-sync` **不覆盖 dsh**（B-9） |

---

## 7. 事实 / 假设分离表

**本节单列所有未经执行的推断。禁止把本节内容当事实使用。**

| # | 陈述 | 类型 | 为什么未验证 | 验证计划 |
|---|---|---|---|---|
| R-01 | `npm pack` 后包内容与 `files` 白名单一致 | 未验证（D-06） | 未执行 `npm pack`（会产生 tarball 文件；本任务未预授权在仓库外写产物，且会触发 npm 缓存写） | `npm pack --dry-run` 在隔离目录执行，比对文件清单 vs `core/manifest.json` canonical artifacts |
| R-02 | `INSERT` 后宿主真实 entry 列表与未安装时逐字节等价（DEC-187 I-1 机检） | 未验证（D-10） | 需真实 `dsh --profile web --dump-config` 两次（装/卸前后），属用户真实环境写操作 | 用户显式授权后，在 `DSH_HOME=<tempdir>` 的一次性 profile 上执行 dump-config 对拍 |
| R-03 | `homedir()` 在 `DSH_HOME` 未设且 `USERPROFILE`/`HOME` 缺失时会抛 `uv_os_homedir ENOENT` | **未验证**（D-17 / G-04） | 实测清空 `USERPROFILE`/`HOME` 后 `homedir()` 仍返回 `C:\Users\peter`（Windows 走 OS API）⇒ 抛错分支**未能复现** | 在无 `USERPROFILE`/`HOMEDRIVE`/`HOMEPATH` 的 Windows 服务账户（或 Linux 无 `HOME` 的 `env -i`）中复现，确认是否抛错 |
| R-04 | `_real_home_witness` 会被无关宿主活动翻转（假 FAIL） | **未验证**（D-54 / G-17） | 本次 24s×8 采样全部 STABLE；无双会话并发验证 | 双会话并发跑 `check-dsh-preset-smoke`，同时让另一会话改 `~/.dsh/settings.yaml`，观察是否 FAIL |
| R-05 | `dsh_compat` 的 `[SKEW] other_planes` 告警在多平面场景下真的有效 | **未验证**（G-14） | 本机实测 `other_planes: []`（只有 1 个平面），告警分支未被执行 | 构造两个含 oracle 包且版本不同的平面（临时 `DSH_HOME`），观察是否输出 `[SKEW]` |
| R-06 | `dsh.bundle.patch` 是「`dsh plugin add` 自动加入 `bundles` 列表」的**触发因** | **未验证（因果）**（D-12） | 只观察到结果态（profile 已含本包），未执行 add 过程 | 用户授权后在一次性 profile 上执行 `dsh plugin add`，对拍 `bundles` 列表前后 diff |
| R-07 | `exports` 映射能让 `import '@peterwangze/software-project-governance-plugin'` 成功 | **未验证**（D-04） | 所有探针都用 `file://` 绝对路径或 `link:` 目录，未走包名解析 | 在临时 `node_modules` 下 `npm link` 本包，`node -e "import('…')"` 正向解析 |
| R-08 | `{{model}}` / `{{cwd}}` 由宿主注入 | **未验证**（D-26） | 需真实 agent 路由上下文 | live 会话中读 persona 原文确认已插值 |
| R-09 | 宿主 `cordis.yml` 提供预设行依赖的 `shell-env` / `subagents` / `web` service | **未验证**（D-45） | 未读宿主全量组合 | `dsh --profile web --dump-config`（需授权）或静态读 `~/.dsh/profiles/web/cordis.yml`（本次该文件对 `governance`/`insert` grep **0 命中**，需换检索键） |
| R-10 | `METADATA_FILE` 的确切文件名与 `preset.yml` 的 `name` 是否必填 | **未验证**（D-46） | 只读到上游导出 `METADATA_FILE` 符号，未读其字面常量 | 读 `dsh-agent-presets/lib/index.js` 中 `METADATA_FILE` 定义行 |
| R-11 | ~~`test_dsh_adapter.py:652` 的 `__GOVERNANCE_REPO_ROOT__` 计数断言 **1** 与模板实际 **2** 的绿/红状态~~ | **已排除（原假设错误）** | — | 已执行：`test_dsh_adapter.py:651` 读的是 `adapters/dsh/AGENTS.md.template`（实测计数 1，`:7`），不是组合模板（实测计数 2）。该测试单跑 `Ran 1 test in 0.005s … OK`。**此条已从缺口清单移除**，改列于 G-08「已排除」行 |
| R-12 | `dsh_compat` 的 `other_planes` 与 `[SKEW]` 在真实多平面下的可用性 | 同 R-05 | — | 同 R-05 |
| R-13 | `$DSH_HOME/.agent-presets/` 是 `resolvedRoots` 中的**第一个**（「first root wins」） | **未验证（顺序）** | 只读到 `:1300 this.resolvedRoots = [` 起点与 `:1565` 的 `.some(root => root.trust === "user")`；未逐行读数组字面量顺序 | 读 `dsh-agent-presets/lib/index.js:1300-1330` 全区间 |
| R-14 | 「5/23 行零校验」在 dsh 升级后**会**（而非可能）导致挂载失败 | **未验证（外推）** | 今天这 5 行 config 合法；缺失的是未来校验能力 | 需 dsh 实际变更这 5 个插件之一的 Config 契约；可用**上游源码变更监控**替代 |
| R-15 | `no Config 导出 ⇒ loader passes config through unvalidated` 这一护栏断言与 loader 真实行为一致 | **未验证** | `dsh_compat.py:373-374` 的 message 是对 loader 行为的断言，本次未读 loader 的 config-optional 分支代码 | 读 `cordis-plugin-loader` 的 `resolveConfig` 调用点，确认无 `Config` 时是否真跳过 |
| R-16 | `preset.yml` 的 `description` 必须是中文/任意内容都能被设置页接受 | **未验证** | 未在设置页实测 | 需 live 会话 |
| R-17 | 6 个历史 `spg-dsh-compat-*` 残留确由**旧版本代码**产生（而非现行强杀路径） | **未验证（推断）** | 仅凭 mtime（2026-09-12 10:12~10:16）与「现行三路径均 0 新增」推断 | `git log -p --follow skills/…/infra/dsh_compat.py` 查 2026-09-12 前后的清理逻辑变更 |
| R-18 | `check-projection-sync`（15 文件）**不覆盖** dsh 两条版本投影 | **已实测支持**（`PROJECTION_SYNC_PATTERNS` 11 条中 dsh 相关 0 条）+ 推断「因此 dsh 投影仅由 `test_dsh_adapter.py:674` 兜底」 | 「仅由…兜底」为推断（未穷举全部 check 的覆盖） | grep 全部 check 对 `version-projections.json` / 两条投影 id 的消费 |
| R-19 | 本次未在 macOS/Linux 验证任何结论 | **未验证（平台）** | 环境仅 Windows | 在 Linux CI 上跑同一套探针 |

---

## 8. 对下游设计的约束输入（只列约束与不变量，不给方案）

> 本节只列**约束**与**不变量**，不提供实现方案（本任务不做设计决策）。

### 8.1 DEC-187 I-1/I-2/I-3 派生的硬约束

| # | 约束 | 本报告中的事实锚点 |
|---|---|---|
| C-1 | **任何消除「重复实现」的方案 MUST NOT 引入真运行时依赖**，否则违反 `lib/index.js:94-97` 的宿主安全不变量（module-load 失败即拖垮 boot） | 3.1 反面证据；`D-03`/`D-16`/`D-47` |
| C-2 | 不得新增任何 `- id: <host row>` UPDATE 行、`disabled: false` 覆写、宿主平面 provider/service/tool 注册、`!!js` 自定位、`trust: system` | `D-10`；`cordis.patch.yml` 非注释行实测（`!!js` 0 / `trust:` 0 / id-UPDATE 0） |
| C-3 | 安装前后 entry 列表逐字节等价 = **必须可机检**；今天的静态面已满足，但机检入口 `NOT_RUN` | R-02；T-2 |
| C-4 | `dsh` 变更由我方适配（正向依赖）⇒ 所有对 dsh 的依赖点 MUST 被枚举并归入契约；不得存在「未枚举但被消费」的隐式依赖 | 第 2 节 100 条；本报告即首份枚举（B-10） |

### 8.2 DEC-188 与机检判据

| # | 约束 | 事实锚点 |
|---|---|---|
| C-5 | 「预设面交付形态」的机检判据 MUST 区分**渲染层**与**挂载层**；今天的机检只到渲染层 + 静态 schema | 6.5；T-4/T-5 |
| C-6 | 任何「PASS」结论 MUST NOT 大于其可信面 —— 零校验路径 MUST NOT 进入 PASS | `REQ-148` 验收信号原文；G-01 为其反例 |
| C-7 | `NOT_RUN` 语义 MUST 与项目既有政策一致（`dsh_compat.py:75-77`：NOT_RUN 不计 gate issue，只披露未验证事实），且 node-gated skip **MUST** 按同一政策披露 | B-8（9 处 `skipTest` 与 `NOT_RUN` 政策不一致） |

### 8.3 结构性不变量（治理结构）

| # | 约束 | 事实锚点 |
|---|---|---|
| C-8 | `PLUGIN_SCOPE_DIRS` MUST 与 `core/manifest.json` 的 `cleanup_scope.directories` 保持集合相等（已有守卫 `checks/manifest.py:323-327` + `test_cleanup.py:20-83`）；新增 dsh 相关目录 MUST 同时进两处 | `D-98`；实测两处 = 同一 11 元集合 |
| C-9 | `core/manifest.json` 的 `canonical_product_artifacts` MUST 覆盖 dsh 面全部产物（当前 7 条），否则 `cleanup.py` 会把它们当残留 | `D-97`；`cleanup.py:46-63` |
| C-10 | 版本投影 MUST 保持「每个 dsh 面版本字符串各有一条投影」；今天有 2 条（`dsh-persona-version` / `dsh-agents-bootstrap-version`），若 persona 模板内新增版本串 MUST 同步加投影 | `D-94`/`D-95`；`version-projections.json:25-26` |
| C-11 | `check-projection-sync`（Check 28b）今天的 `PROJECTION_SYNC_PATTERNS` 内 dsh 相关 0 条 ⇒ dsh 两条投影的主 check 覆盖缺失；不得把 `test_dsh_adapter.py:674` 当作等价替代（测试可被 skip/不跑） | B-9；R-18 |
| C-12 | `registry.py` 的 `LOADER_WHITELIST` 是闭集；新增 dsh 相关检查模块 MUST 显式加入（无动态发现） | `D-87`；`registry.py:197, 199-204` |
| C-13 | Segment `40`（`check_dsh_skills_manifest`）已退役且其主题（`dsh.skills`）已从 `package.json` 移除；不得复活该 Segment 而不复活其主题 | `D-89`；`registry.py:428-431` |
| C-14 | 「Check 28u / 28v」是 `_SEGMENT_LOADERS`（实测 70 条）的注册项；任何割接 MUST 保持注册表与实现一一对应（`registry.py:421` 自述「Machine-derived」） | `D-86`；实测 70 条无重复 |
| C-15 | 渲染输出属于 render 层（R4 ratchet），新增 check MUST NOT 增长 monolith 的 print 面 | `D-82`；`dsh_compat.py:1029-1034` |

### 8.4 可调测性约束（REQ-149）

| # | 约束 | 事实锚点 |
|---|---|---|
| C-16 | MUST 存在**单一诊断入口**且输出**分阶段结论**（今天不存在，见 6.2） | 6.2 |
| C-17 | 隔离环境（`DSH_HOME` 重定向）可复现的失败面 MUST 有 CI 可跑的负相 fixture；今天**无法离线复现**的面 MUST 被显式列出（见 T-1~T-10） | 6.3/6.4 |
| C-18 | 每条依赖点的结论 MUST 可追溯到证据（`文件:行号` 或命令输出）；「有守卫」必须区分**能抓漂移**与**仅存在** | 第 4 节覆盖强度定义 |
| C-19 | 真实环境操作 MUST 满足三选一（隔离/备份+校验/用户逐项授权）并留痕；`--smoke` 与 28u 今天满足（环境变量重定向），`--install`/`dsh plugin add` 的隔离性 MUST 单独论证 | `D-53`/`D-80`；1.5 |
| C-20 | 版本/时效类声明（`verified_on`、注释中的 dsh 版本）MUST 可机器刷新或校验，否则必然失真 | G-11、G-12、`D-57` |
| C-21 | 「零校验不得报 PASS」MUST 成为**可机检的不变量**，且其机检 MUST NOT 与 `REVIEW` 记录产生第二事实源 | C-6；G-01 |
| C-22 | 依赖面清单本身 MUST 有保鲜机制（否则本报告退化为一次性文档） | B-10；`D-61` |

### 8.5 与既有 task 的边界约束

| # | 约束 | 事实锚点 |
|---|---|---|
| C-23 | `FIX-315`（G-01）与 `FIX-311`（G-02/G-03）的修复 MUST 处理「测试已反向固化当前行为」这一事实 —— 修改护栏行为会让 `test_dsh_compat.py:365` 与 `:754` 变红，这是**预期**而非回归 | G-01 测试反向固化；G-03 测试反向固化 |
| C-24 | `FIX-313`(a)（D-66 的行尾分歧，实测证实）与 `FIX-316` 批次（G-05~G-10）在今日代码中**全部仍未修**（本次独立实测确认），**不是**「已核实但已修」 | 各 G 条实测证据 |
| C-25 | `AUDIT-153` 的产物（本报告）是**事实输入**；下游设计 MUST NOT 把本报告第 7 节的未验证项当事实使用 | 第 7 节 |

---

## 附录 A：本次真实环境命令上报表

**前置声明**：本任务「无预授权 incidents 留痕文件」⇒ 全部真实环境命令仅在本表中上报（由 Coordinator 于收到当下机写 evidence 行）。

| # | 命令（摘要） | 时间（本地） | 退出码 | 影响路径 | 性质 |
|---|---|---|---|---|---|
| 1 | `python skills/…/infra/dsh_compat.py --json` | 2026-09-13 | 0 | 读 `C:\Users\peter\.dsh\profiles`（只读）；写 `%TEMP%\spg-dsh-compat-*`（已清理，实测 0 残留） | 真实环境**只读** + 临时目录写 |
| 2 | `python -m unittest … -p "test_dsh_adapter.py"` | 2026-09-13 | 0 | 写 `%TEMP%\tmp*`（测试自管）；读仓库 | 临时目录写 |
| 3 | `python -m unittest … -p "test_dsh_compat.py"` | 2026-09-13 | 0 | 同上 | 临时目录写 |
| 4 | `python skills/…/verify_workflow.py check-dsh-preset-smoke` | 2026-09-13 | 0 | `DSH_HOME` 重定向至 `%TEMP%\spg-dsh-smoke-l4aa_g18`（已 removed）；读 `C:\Users\peter\.dsh` 顶层 metadata | 真实环境**只读 metadata** |
| 5 | `python skills/…/verify_workflow.py check-projection-sync` | 2026-09-13 | 0 | 读仓库文件；无外部写 | 只读 |
| 6 | `node …/staging2.mjs`（`ensurePreset` 探针） | 2026-09-13 | 0 | `DSH_HOME=%TEMP%\audit153_…\fakedsh2`、`USERPROFILE`/`HOME=%TEMP%\audit153_…\fakehome2` | **三重定向隔离** |
| 7 | `node …/cwdclean.mjs`（catch 清理探针） | 2026-09-13 | 0 | 仓库 cwd 内创建 `governance.staging-VICTIM`（脚本自删除） | 仓库内临时目录（已清理） |
| 8 | `node …/noschema2.mjs`、`parity2.mjs`、`leftover2.mjs`、`diag.mjs` | 2026-09-13 | 0 | 读 npx 缓存与仓库；写 `%TEMP%\audit153_*` | 只读 + 临时目录写 |
| 9 | `python …/unicode_probe.py`、`home_cmp.py`、`risk050.py`、`witness_race.py`、`leak_probe.py` | 2026-09-13 | 0 | 写 `%TEMP%\audit153_*`；读 `C:\Users\peter\.dsh` 顶层 metadata（`witness_race.py`） | 只读 + 临时目录写 |
| 10 | `python skills/…/dsh_compat.py --json <伪造组合>` ×8 | 2026-09-13 | 0 | 组合文件置于 `%TEMP%\audit153_3f4eeca5`；读真实 profiles 平面（只读） | 真实环境**只读** + 临时目录写 |
| 11 | `Get-Content` / `Get-ChildItem` / `Select-String` 对 `~/.dsh/**`、npx 缓存 | 2026-09-13 | 0 | **纯读** | 只读 |

**对用户真实环境的写操作**：**0 次**。
**对真实 `~/.dsh` 的写操作**：**0 次**（探针后复查 `.agent-presets` = `governance, novel-writing`，与探针前一致）。
**未执行的真实环境写操作**：`dsh plugin add/remove`、`dsh --profile web --dump-config`、`launch.py --install`（对真实 home）—— 全部 `NOT_RUN`（1.4）。

---

## 附录 B：本次临时产物清单（供清理）

全部位于 `%TEMP%` 下，可用 `Remove-Item "$env:TEMP\audit153_*" -Recurse -Force` 清理（**不含**任何用户配置目录）：

- `%TEMP%\audit153_3f4eeca5\`（探针脚本 + fixture；含 `parity/`、`uni/`、`cmp/`、`fakedsh*/`、`fakehome*/`、`isolated_cwd/`）
- `%TEMP%\audit153_compat.json`（Check 28v 的 `--json` 输出）
- 6 个**本次之前既存**的 `%TEMP%\spg-dsh-compat-*`（2026-09-12，见 G-09；**本报告未生成它们**）

---

*报告结束。本文件为 AUDIT-153 唯一产物；本次未修改任何产品代码或治理记录。*
