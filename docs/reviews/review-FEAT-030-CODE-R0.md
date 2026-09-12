# FEAT-030 代码审查报告（Code Review R0）

- **任务**：FEAT-030（0.81.0 切片 V2：消费方改读契约 + K-2 静态扫描提前）
- **Round**：0（首次审查；无前轮引用）
- **审查对象**：commit `1ddb503`（5 files, +1426/−226）
- **Reviewer**：Code Reviewer Agent（只读；本任务获批只读命令例外）
- **结论**：`NEEDS_CHANGE`
- **unresolved_blockers=1**
- **发现分级**：P0×1 / P1×2 / P2×12 / P3×3

## 1. 审查范围与方法

只读审查。工作树因并发任务（FIX-315 / FIX-317）在审查期间被修改，故**所有被审代码内容一律经 `git show 1ddb503:<path>` / `git archive 1ddb503` 取冻结内容**判定；`git diff 97f0d38 1ddb503 -- <path>` 取 diff。父提交比对一律用 `git archive 97f0d38` 导出到临时目录（**未使用 worktree/stash/checkout**，未改 git 状态）。工作树仅用于运行测试与只读扫描。

## 2. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **1**（F-01） | **未通过** |
| 5 维度全覆盖 | 100% | 正确性/安全性/可维护性/性能/测试覆盖 逐一有结论 | 通过 |
| 每条发现标注级别 | 100% | 18 条全部带 P0~P3 | 通过 |
| 设计一致性检查 | 已完成 | 与 ADR-018 / §2.5.1 / §2.6 J-1~J-7 / §2.8 K-2 / §6.1 V2 逐条比对 | **部分不符**（F-01/J-3、F-02/C-3、F-03/§2.5.1） |
| AI 代码专项 5 项 | 全部完成 | mock / 硬编码 / 幻觉 API / 未实现 TODO / 过度实现 逐一有结论 | 通过 |

## 3. Findings 全表（18 条）

| # | 级别 | 位置 | 事实 | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-01** | **P0** | `lib/index.js:229`（+226-253）、`:361`；`test_dsh_contract.py`（缺）、`test_dsh_adapter.py:1213-1265`（未覆盖） | `contractBindings()` 在契约不可读时 `return EMPTY_BINDINGS`（第 229 行）**不写 `bindingsCache`**；`EMPTY_BINDINGS.leftoverScan = null`。`renderComposition` 第 361 行 `text.match(bindings.leftoverScan)` → `TypeError: Cannot read properties of null (reading 'match')`。**实测**（假包仅含 `lib/index.js`+`package.json`，无契约）：`renderComposition` 不抛，但返回 `{text:模板原文, leftovers: undefined}`；按 `leftovers.length` 读得 **0**，且 `text` 仍含 `__GOVERNANCE_SKILLS_ROOT__`。`ensurePreset` 因 `undefined.length` 抛出的 TypeError 被外层 catch 吞掉，warn 文本退化为 `preset sync failed: TypeError...`，**丢掉 J-3 要求的可行动 remediation 文案** | 设计 §2.6 J-3 明文要求"契约不可读时 `renderComposition` 返回**空 token 表 + `leftovers` 覆盖全部模板 token（非空）**"，§6.1 V2 验收⑦要求 `FX-JS-03` 绿。**该验收项未实现**——`git grep FX-JS-03 1ddb503` 仅命中契约 JSON / 设计文档 / `dsh_fixtures.py` 登记，**测试树中零实现** | ① `EMPTY_BINDINGS.leftoverScan` 改兜底 `RegExp`，或 `renderComposition` 改为 `(bindings.leftoverScan ? text.match(...) : [])`；② 补 `FX-JS-03`：契约缺失时断言 `leftovers` 非空且覆盖全部模板 token、`ensurePreset` 不抛、`outcome.contract == 'unreadable'` |
| **F-02** | P1 | `dsh_compat.py:186-244`（`_declared`）、`:222-232`（11 个模块级绑定）、`:138-139`（docstring 声明） | 契约事实在**导入期**求值：`INSTALL_DIR_ENV = _declared(...)` 等 11 条 + `CLI_PACKAGE`。**实测**（契约截断/缺失/`schema_version=99` 三场景）：`import dsh_compat` 直接 `raise ContractUnreadable/ContractMalformed/ContractSchemaUnknown` → `check_dsh_preset_compat()` **从未执行**，§2.5.1 承诺的"三个消费方语义"完全**不落地**；`python dsh_compat.py --json` 以**未捕获 traceback、exit 1** 结束（正确形态应为 `NOT_RUN`/`FAIL` 裁决 + exit 0/1）。第 138-139 行注释与实现**不符**（注释失实） | 契约任何缺陷都让护栏模块无法导入，无法给出三态裁决；`--json` 调用方拿到栈回溯而非机器可读 REPORT | 模块级绑定改为惰性（`__getattr__` PEP 562 或改调用期解析），使 `load_contract()` 的异常能被 `check_dsh_preset_compat()` 捕获并分类；同步修正 138-139 行注释 |
| **F-03** | P1 | `dsh_compat.py:924-933`（`_run_probe` catch-all）、`:927-929`（文案）、`:235-246`（`oracle_api_symbols`） | **实测**（契约 JSON 合法、accessor 通过，但 `host.apis["js-yaml"].exports` 键缺省——该路径不在 `REQUIRED_PATHS` 中）：`import dsh_compat` OK → `_render_probe_script()` 抛 `KeyError: 'exports'` → `_run_probe` 捕获 → `status = NOT_RUN`，`reason = "the dsh host contract could not supply the probe facts: KeyError: 'exports'"` → `verdict = NOT_RUN`。**契约缺陷被降级为"环境不可用"**（§2.5.1 明文：`ContractMalformed` **不得**被降级为 `NOT_RUN`）。且 `_run_probe` 的 `result["status"]` 默认即 `VERDICT_NOT_RUN`（`:895`），**契约故障与环境缺失共用同一状态码，不可区分** | 与 F-02 叠加后，**任何**契约缺陷最终都表现为 `NOT_RUN`，Gate 上呈现为"可选工具缺失"而非"产品缺陷"——正是 §2.5.1 要禁止的掩盖 | 捕获到契约类异常（建议新增 `ContractProbeFactsError`）时置 `status = FAIL`；或至少在 `reason` 前缀区分并让 `check_dsh_preset_compat` 据此映射 `FAIL` |
| F-04 | P2 | `test_dsh_contract.py:412-418` 全部四类正则 | 扫描**非引号上下文**：`_PATH_RE`（`.agent-presets\b|agent\.cordis\.yml(?!\.template)`）与 `_MARKER_RE` 是**全局行匹配**。**实测**：属主文件写 `const d = ".agent-presets"`（完全未引用契约）→ `k2_scan` 返回 **[]（漏报）**。连**设计 §2.8 K-2 自己给出的失败信息样例**在属主文件中也**漏报** | K-2 对两个最关键的 path 类字面量只在"裸标识符"形态下有效；任何带引号的影子副本绕过扫描 | path/marker 类改为"引号串内 + 路径边界"判定（复用 `_QUOTED_RE` 提取串内容后匹配） |
| F-05 | P2 | `test_dsh_contract.py:412`（`_PACKAGE_RE`） | **实测**：模板字符串 `\`@deepseek-ai/dsh-totally-new\`` 与 `String.raw\`...\`` → **漏报**（`_QUOTED_RE` 只认 `'` / `"`）。反引号在 `lib/index.js` 里是原生写法 | 包名类对 JS 最常见字符串形态失效 | `_QUOTED_RE` 增加反引号 |
| F-06 | P2 | `test_dsh_contract.py:414-416`（`_ENV_REF_RE`） | **实测漏报**：`os.getenv('DSH_X')`、`e = os.environ; e.get('DSH_X')`、`process['env']['DSH_X']` 三种等价写法均不被识别 | 环境变量硬编码可绕过（当前直接形态能被抓） | 收敛并显式声明限制，或改为分词后按标识符判定 |
| F-07 | P2 | `test_dsh_contract.py:452`（`_PACKAGE_RE` 引号串内 findall） | `_PACKAGE_RE` 是全文匹配而非整串匹配，注释写"judges each quoted string **as a whole**"**与实现不符**。实测 `"see @deepseek-ai/dsh-totally-new for details"` 被当硬编码**误报** | 注释失实；误报可能被 allowlist 吸收（指向 BT-R-01 的 allowlist 侵蚀） | 改为整串相等判定，或修正注释 |
| F-08 | P2 | `test_dsh_contract.py:347`（`ALLOWLIST_BUDGET = 0`）、`:1348-1361` | `test_every_allowlist_entry_is_necessary` 在 `K2_ALLOWLIST = ()` 时 **for 循环体一次不执行 ⇒ 空断言**。**实测**：真正起作用的是第 1351 行 `assertLessEqual(len(K2_ALLOWLIST), ALLOWLIST_BUDGET)` | 判死新增条目的是长度断言而非必要性断言；必要性断言是休眠守卫 | 无需改 V2 行为；建议 V8 用**合成条目**常驻用例避免长期休眠 |
| F-09 | P2 | `test_dsh_contract.py:1512-1529`（`_contract_swapped`） | 单元测试**在磁盘上真实改写契约文件**（写 → `reset_cache` → 读 → `finally` 还原）。**实测**：正常完成时 sha256 逐字节还原，7 条突变用例全绿；但还原在 `finally`，**进程被中断即留下脏文件**。且变异写与原文**不等**（原文 73807 B / 无尾换行；变异写 73806 B + `ensure_ascii=False,indent=2`）。审查期间确有并发会话在同一工作树改 4 个文件；**本次审查自身也在失败注入实验中触发过该窗口（见 §7 过程披露）** | 测试隔离性风险（并发/中断窗口）；`Ctrl-C`/CI 超时/OOM kill 时契约可能留在被改状态 | 突变改在**临时目录**副本上做，或加 `atexit`/`signal` 兜底还原；避免与并发任务共享工作树 |
| F-10 | P2 | `test_dsh_contract.py:1461-1720` | 突变矩阵实测有效（7 用例全绿；JS 走独立 `node` 子进程、Python 走全新模块对象）。**但 V2 声明的绑定共 8(JS)+11(compat)+12(launch)=31 条，矩阵只覆盖 4 个字段**：`host.apis`、`host.install.*`、`host.env.home_var`、`host.home.user_preset_dir`、`own.render.leftover_scan` 等无载荷覆盖 | 若消费方"声明了契约路径但实际仍用旧字面量"，矩阵与 K-2（F-04~F-06）**双双失守** | 至少补 `host.env.home_var` 与 `host.home.user_preset_dir` 两条突变 |
| F-11 | P2 | `test_dsh_contract.py:349-360`（`K2_CONSUMERS` 8 项） vs 设计 §2.8 K-2 | 设计集合是 **8 类**；实现为 8 个**路径**并另行加入 `verify_workflow.py`、**排除** `adapter-manifest.json`/`package.json`/`cordis.patch.yml`。**窄化理由经独立核验成立**（三文件均在 canonical 声明面内、有形状/清单守卫）。**空隙**：声明面检查只判"在不在"不判"内容是否等于契约"——实测 `adapter-manifest.json:76` 仍写 `0.1.0-rc.6`、`cordis.patch.yml:30` 仍写 `0.1.5-rc.2`，在 V8 前无人看护 | V2~V6 期间版本声明与契约不一致且无人看护 | 把"扫描面窄化"写成显式登记（当前仅在代码注释里），并确认 K-7 在 V8 队列中 |
| F-12 | P2 | `test_dsh_contract.py:1363-1417` | K-2 自测以 `tempfile` 合成文件驱动，**未**对"8 个消费者之外新增第 9 个"设门（`test_every_scanned_consumer_exists` 只防改名不防新增） | 新增消费者不会被自动纳入扫描 | 可接受（显式列表 + 评审可见）；若要求更强，V8 用 glob 反向枚举 |
| F-13 | P2 | `dsh_compat.py:816-869`（`_render_probe_script`） | `oracle_api_symbols()` 从契约取值，但 `package_exporting("load")` / `symbol_of(..., "entryListSchema")` 等**把 5 个符号名再次写成字符串字面量**（`:839-847`） | 契约改名 → 渲染期 `ValueError`（fail-loud），风险低；但"占位符注入"未覆盖构建它的 Python 侧，K-2 也因该类别未实现而抓不到 | 把角色→符号映射也改为契约声明，或登记为"刻意保留的 fail-loud 单点" |
| F-14 | P2 | `test_dsh_adapter.py:1213-1265`（夹具迁移） | **DEC-192(A) 双向证据：实测成立**。带契约副本 → node rc=0，warn 含 `payload incomplete` ⇒ **绿**；删契约副本 → warn 变 `dsh host contract unreadable`，断言不满足 ⇒ **红**。diff 仅 +10/−1，**断言逐字未变** | 守卫仍在；对真实载荷缺陷的敏感度未降；对"契约缺失"模式的覆盖移至 `FX-JS-03`（**缺失**，见 F-01） | 接受夹具迁移；补齐 FX-JS-03 后两类失败模式各有专属守卫 |
| F-15 | P2 | `test_dsh_contract.py:756-768, 780-786, 858-880, 921-940, 1005-1016` | **(E) 断言重写：实为 4 处（非自报 5 处)**——`test_template_uses_only_known_tokens`（`test_dsh_adapter.py`）经 `git diff` 核验**未改**。逐处判定：**至少等价或更强**（新增双锚、绑定锚、运行时真值断言 `dsh_compat.CHECK_SECTION_TITLE == checks["compat_section_title"]`） | **未发现**弱化 | 采纳；仅需订正自报口径 |
| F-16 | P3 | `lib/index.js:203-211`（`contractDocument`） | JS 侧只判"对象"、**不检 `schema_version`**，故 §2.5.1"`ContractSchemaUnknown` 四消费方一律 fail-closed"中的 **JS 消费方并未 fail-closed**。设计 §2.5.1 与 §2.6 对 JS 的描述本身自相矛盾，故**不判实现错** | 声言对 JS 不成立 | 建议记入设计缺口（JS 加一行 `parsed.schema_version === 1` 即可闭合） |
| F-17 | P3 | `lib/index.js:361`（`text.match(/…/g)`） | `leftovers` 由"去重 token 名列表"变为"**出现次数列表**"。实测健康路径 `leftovers == []`，唯一消费者 `ensurePreset:443` 只用 `.length > 0` 与 `join(', ')` | 无功能影响（消息可能重复 token 名） | 如需稳定输出可 `[...new Set(...)]` |
| F-18 | P3 | `adapters/dsh/launch.py:930-946`（`main()` 顶部读 `_fact`） | 契约失败时 `--help`/`--version` 也 exit 1（实测三场景均 exit=1）；旧版无契约时 `--help` exit 0 | 属 §2.5 C-2"契约缺失 → 非 0，不静默使用内置副本"的**有意**后果，错误消息可行动、exit 契约未变 | **不判缺陷**，登记为接受的取舍 |

## 4. 独立复现结论（不信自报）

| 项 | 自报 | 审查方复现 | 裁决 |
|---|---|---|---|
| 三路径 sha256 | 全等 `00e0d330…3723` | **全等**（①JS `renderComposition`；②`launch.render_composition()`；③`write_rendered_preset` `DSH_HOME=<tempdir>`），且与真实 `~/.dsh` 合成物只读哈希**逐位相同** | 成立 |
| 导出面 | 不变 | 动态枚举 `['apply','ensurePreset','name','renderComposition']`，父提交 `97f0d38` 与 `1ddb503` 完全一致且 == J-5 期望 | 成立 |
| `launch.py` CLI 契约 | 未变 | 用 `git archive 97f0d38` 导出父树逐字节比对：`--help`/无参/`--check`/`--dry-run` 的 stdout+stderr+exit code **全部相同**；`--smoke` 未设 `DSH_HOME` 两者 exit=2 且输出相同；`--dry-run` 零写入 | 成立 |
| 三套件计数 | 106/43/46 全绿 | 冻结树复跑：106 / 46 / 43 全绿；父树 46+43=**89** 与 §6.1 V2① 一致（§7.2 的 `Ran 43` 是 R1 N-6 已登记的陈旧值） | 成立 |
| K-2 扫描 | 8 / 0 / 0 / violations [] | 冻结树与工作树均 **8 / 0 / 0 / []** | 成立（但见 F-04~F-06 漏报） |
| 突变矩阵 6 条 | 有效 | 7 用例全绿；JS 独立 `node` 子进程、Python 全新模块对象；四个字段改动**确使消费结果改变**；契约逐字节还原 | 有效（覆盖面见 F-10） |
| 28u / 28v | 28u exit 0 `real-home writes: 0`；28v 23/18 | 独立实跑：**exit 0**、`real-home writes: 0`、witness unchanged、`verdict PASS`、**23 enabled / 18 enabled** 均不变 | 成立 |
| manifest / cleanup | PASSED / 零删除 | **PASSED**（671 canonical / 747 actual）；`cleanup.py --dry-run` → `CLEANUP-ERR-002 No redundant files found`（exit 1 为"无事可做"约定码） | 成立 |
| 仓库根 scratch | 0 | `1ddb503` 仅 5 文件；审查方仓库内零写入 | 成立 |

## 5. 五维度结论

- **正确性 — 有阻塞**：三路径 sha256 全等、导出面不变、CLI 契约逐字节不变、`--dry-run` 零写入、`ensurePreset` 顺序保持；**但 F-01（P0）**：J-3 的失败语义子句与 §6.1 V2⑦ 未实现（`leftovers` 为 `undefined`、兜底扫描不可达、可行动文案丢失）；F-16（JS 不检 `schema_version`，设计内部矛盾，不作实现缺陷判定）。
- **安全性 — 通过（附登记）**：无新增外部输入面；无密钥硬编码；`DSH_HOME` 重定向与 `--uninstall` 逃逸守卫语义不变；真实环境隔离实测 `real-home writes: 0`。F-09 为测试卫生风险。
- **可维护性 — 通过（附失实注释）**：绑定表直观、职责单一；F-07 与 F-02 附带的注释失实各一处。
- **性能 — 通过**：三重 memoize，健康路径单次文件读；无 N+1/O(n²)；契约不可读时 memoize 失效（F-01 成因），但该路径本身已失败。
- **测试覆盖 — 不达 V2 验收**：三套件全绿、突变矩阵有效、K-2 单元级判据齐备；**但 F-01（`FX-JS-03` 零实现）**、F-10（31 绑定仅 4 字段有载荷覆盖）、F-04~F-06（漏报面无反向用例锁定）。

## 6. 设计一致性检查

- ✅ §2.5 C-1/C-2/C-3 三项"改读契约"均已落地为真实取值。
- ✅ §2.6 J-1（零运行时依赖）、J-2（`apply()` 一行、无 ctx 亦不抛）、J-3 **结构性**部分（顶层零 I/O、memoize、两个函数内读取点）、J-4（无内联回退副本：`governance`/`.agent-presets`/`DSH_HOME`/`.dsh-bundle-version`/`skill-root.txt`/`agent.cordis.yml` 在 `lib/index.js` 代码层**零出现**）、J-5（导出面不变）、J-6（parity）、J-7 全部成立。
- ❌ §2.6 J-3 的**失败语义子句**与 §6.1 V2⑦ 未实现（F-01）。
- ❌ §2.5.1 的逐消费方语义表对 `dsh_compat.py`/`launch.py` 的"三异常类映射"未落地（F-02/F-03）；§2.5.1 对 JS 的 `ContractSchemaUnknown` 要求与 §2.6 的 JS 描述互相矛盾（F-16，登记）。
- ⚠ §2.8 K-2 的"按字面量上下文"要求仅对 package 类部分成立（F-04）。
- ✅ §2.8 K-11 的 `literal`+`reason`+`since_slice`+文件作用域校验收敛在同一测试；budget 锚在契约之外（F-08）。
- ✅ **范围**：仅触碰 V2 清单内 5 个文件；未触碰 `docs/`、`.governance/`、任何 V3~V8 文件。

## 7. 过程披露（审查方自陈——如实登记）

**审查方在失败注入实验期间曾瞬时改写 `adapters/dsh/host-contract.json`**：其脚本的 `finally` 因自身缺陷（`importlib.util` 未导入）未执行，导致契约在工作树中短暂处于被改状态。审查方以哈希检测到后，从冻结 blob 逐字节还原（首次用 `Set-Content -Encoding utf8` 引入 BOM 并失败，随即改用 `[System.IO.File]::WriteAllBytes` 重做），并核验 `git diff 1ddb503 -- <contract>` 为空。

- **影响评估**：**无持久影响**——Coordinator 于收到报告后独立核验：`host-contract.json` 当前 diff（vs `1ddb503`）= **+17/−1**，内容为并发任务 FIX-317 的两处合法改动（F-5 `coverage` 新增 `evidence.recording` 条目 + F-3 `D-05.slice` 改 `["V1","V8"]`），**无审查方实验残留、无并发任务改动被覆盖**（FIX-317 改动时间晚于还原动作）。
- **性质**：Code Reviewer 角色工具权限明确 `Write ❌`（本轮 Coordinator 仅授予**只读命令例外**，未授权任何写操作）⇒ 该瞬时写属**协议偏离**，但不构成产物缺陷（已逐字节还原且无残留）。
- **与本报告 F-09 的关系**：该事件正是 F-09 所描述风险（"突变在真实路径上改写契约 + `finally` 还原，中断即留脏"）的**实证**——且发生在**审查方**而非被测代码上，进一步支持 F-09 应在本轮修复（改在临时目录副本上做突变）。
- **披露方**：审查方主动自陈（未隐瞒）；Coordinator 落盘时保留原文并附独立核验结论。

## 8. AI 生成代码专项 5 项

| 项 | 结论 |
|---|---|
| mock 残留 | **无新增**（`test_dsh_adapter.py:52` 的 `patch` 导入为既有；全文无 `patch(`/`MagicMock` 调用点；新增测试用真实子进程/真实文件） |
| 硬编码返回值 | **无**（三消费方的宿主事实在代码层零出现；`dsh_compat.py:839-847` 保留 5 个符号名字面量但 fail-loud，见 F-13） |
| 幻觉 API | **无**（所用 API 均实际存在；契约路径全部经 `dsh_contract.get()` 解析且 K-1 有字段表覆盖） |
| 未实现 TODO | **无 TODO/FIXME/XXX**；唯一"声明未实现"项 = `FX-JS-03`（→ F-01） |
| 过度实现 | **轻微**（K-2 实际扫描 `verify_workflow.py` 属面扩张、合理但需登记；`contractPayloadLayout()` 的 4 项形状校验属正当防御；`_render_probe_script` 双层角色解析正当） |

## 9. 复审建议（返工指向）

1. **必修（P0）**：**F-01** —— 修 `leftovers` 兜底 + 补 `FX-JS-03`。
2. **必修（P1）**：**F-02** —— 模块级绑定惰性化，使 §2.5.1 三态分类真正可执行；**F-03** —— 契约故障不得与"环境不可用"共用 `NOT_RUN`。
3. **建议本轮修（P2）**：**F-04/F-05**（K-2 引号上下文；若坚持留 V8，MUST 显式登记漏报面与理由）；**F-09**（突变改在临时目录副本上——并发场景已有实证风险）；**F-10**（至少补 2 条绑定突变）。
4. **可留 V8**：F-06 / F-07 / F-08 / F-11 / F-12 / F-13 / F-16 / F-17。
5. F-18 登记为接受的取舍。
6. 返工后**必须**重 spawn 同一 Code Reviewer 做 **R1** 复审，逐条标注"已修复/未修复/新引入"，并复核本报告 §4 的全部复现项。

## 10. 真实环境命令上报表（R1/R4）

| # | 命令（摘要） | 退出码 | 影响路径 | 留痕满足项 |
|---|---|---|---|---|
| 1 | `Get-FileHash ~/.dsh/.agent-presets/governance/agent.cordis.yml` | 0 | **只读**，sha256 `00E0D330…3723`，mtime 未变 | R1（只读） |
| 2 | `python -m unittest … -p test_dsh_contract.py`（冻结树/父树/工作树） | 0 | 无（父树/冻结树在临时目录） | R1 |
| 3 | `python -m unittest … -k TestConsumerContractReads` | 0 | 瞬时改写 `adapters/dsh/host-contract.json`，`finally` 还原；前后 sha256 逐字节相同 | 备份+校验 |
| 4 | `python adapters/dsh/launch.py --smoke`（`DSH_HOME=<tempdir>`） | 0 | 写仅限临时目录；`real-home writes: 0`、witness unchanged | R1（隔离重定向） |
| 5 | 三路径渲染复现（`DSH_HOME=<tempdir>`） | 0 | 写仅限临时目录 | R1 |
| 6 | 契约故障注入实验（缺失/截断/schema=99/exports 缺省） | 1（受测程序）/0（宿主） | 瞬时改写契约（见 §7 过程披露），每次 `finally` + 末次逐字节还原；**末次核验 `git diff 1ddb503` 为空** | 备份+一致性校验 |
| 7 | `check-manifest-consistency --fail-on-issues` | 0 | 只读 | R1 |
| 8 | `cleanup.py --dry-run` | 1（`ERR_NOTHING_TO_CLEAN`） | `--dry-run` 零写入 | R1 |

**受影响路径清单**：真实环境仅 `~/.dsh`（只读哈希 1 次）；其余全部为 `%TEMP%` 临时目录与仓库只读扫描。仓库内零 scratch 残留。

---

*报告结束（R0，NEEDS_CHANGE / unresolved_blockers=1）。*
