# FIX-316 代码审查报告（Code Review R0 — V5+V6+V7）

- **任务**：FIX-316（0.81.0 切片 V5 渲染/解码守卫 + V6 `DSH_HOME` 收敛 + V7 版本证据看护与写入守卫对称化）
- **Round**：R0（首次审查；无前轮 findings）
- **审查对象**：工作树未提交改动 5 文件（+1063/−93），HEAD = `85fb309`：`launch.py`（+623/−?）· `lib/index.js`（+21）· `cordis.patch.yml`（+15）· `adapter-manifest.json`（+4）· `tests/test_dsh_compat.py`（+493 / +22 用例）
- **Reviewer**：Code Reviewer Agent（只读；全部构造/变异/红绿实证在 `%TEMP%\fix316-review\` 副本内完成并已清理；真实 home **零写**）
- **结论**：**NEEDS_CHANGE / `unresolved_blockers=2`**（P0 = 0；硬门槛 5/5 通过）
- **权威**：AUDIT-153 §5（G-05/G-07/G-10/G-11/G-12、D-50/54/56/66）；设计 §3.3、§4.4.4、§4.4.6、§4.4.7、§6.1 V5/V6/V7

## 1. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✅ |
| 5 维度全覆盖 | 100% | 逐项有结论 | ✅ |
| 每条发现标级别 | 100% | 15 条全带 P0~P3 | ✅ |
| 设计一致性检查 | 已完成 | §6.1 V5/V6/V7 逐条；**2 条未达标**（F-5、F-9） | ✅（含未达标项） |
| AI 专项 5 项 | 全部完成 | 逐项 | ✅ |

**为何不是 APPROVED_WITH_NOTES**：`APPROVED_WITH_NOTES` 要求 `unresolved_blockers=0`，而存在 2 项未闭合的**设计判据级**缺陷（F-2、F-5）。**为何不是 BLOCKED**：无架构级问题，全部可定点修复。

## 2. Findings

| # | 级别 | 位置 | 事实（已独立复现） | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-2** | **P1 阻塞** | `launch.py:366`（`package_version`）、`:960`（`_repo_root_for_preset`）、`:483`（`write_rendered_preset` 内 `_read_text(_preset_metadata())` 未处理）；测试面 | **设计 §4.4.6 G10-b「公共入口不得泄漏栈」被实测证伪**：非 UTF-8 `package.json` → `package_version()` **抛 `UnicodeDecodeError`**；`install_preset()`（= `main(["--install"])` 公共入口）**同样逃逸**；`verify_preset_loading()` + 非 UTF-8 `skill-root.txt` → **抛**；非 UTF-8 `preset.yml` → `CompositionUnreadable` 逃逸 `install_preset`。设计 ③ 明列三入口（`render_composition`/`verify_preset_loading`/**`main(["--install"])`**），交付只覆盖前两者 ⇒ **`main` 入口零覆盖** | 本片自述判据未闭环；同类解码口径不一致在改动文件内仍有 3 处 | 三处读点改走 `_read_text`（或边界捕获 `CompositionUnreadable` → 可行动诊断 + 稳定退出码）；补 `main(["--install"])` 用例（无栈 + 退出码稳定 + 消息含文件名与偏移） |
| **F-5** | **P1 阻塞** | `launch.py:749-780`（`_real_home_witness` 未改）；`test_dsh_adapter.py:1013-1017`；`dsh_fixtures.py:292` | 设计 §3.3 第 11 行把 **D-54 指派给 V5**；§6.1 V5 标题含 D-54、文件清单含 `launch.py`+`dsh_fixtures.py`、验收 ⑤ 要求「采样对象/时刻/比较式」按 §3.3 且 `FX-WITNESS-01` 可机检。实测：`top_level` 仍带 `size:mtime_ns`（未弱化）、无双采样、`FX-WITNESS-01` **无任何测试消费**（全仓 1 命中 = 登记处）；且既有 `test_dsh_adapter.py:1013-1017` 断言「改 `settings.yaml` → witness 变化」，**正是 D-54 要求删除的行为** | V5 验收 ⑤ 未交付；机器判据与设计目标互相矛盾 | 二选一：(a) 实现 D-54 + 消费 FX-WITNESS-01 + 改写 `:1013-1017`；(b) 登记为有意延期的 P2 遗留并加注偏差 —— **Coordinator 已裁决走 (a)，并放开 `test_dsh_adapter.py`/`dsh_fixtures.py` 授权** |
| **F-1** | P2 | `launch.py:679-712` + 文档面 | 守卫**实测有效**（24 形态 × 3 入口全拒；junction/大小写/相对路径均不可绕）。但 `--install`/`--sync`/`--uninstall` 的**真实 home 目标从此永久不可达**，而 `README.md:82/106-108/425-428/449`、`adapters/dsh/README.md:25/29/32`、`AGENTS.md.template:19`（引导 agent 让用户跑 `--install`）、`ADR-018:321`、`feature-flags-0.80.0.md:28` 仍以该命令为唯一手工/离线/升级路径；设计自身范式是「默认拒绝 + 显式 opt-in」（§5.1 `--allow-host-probe`），本守卫**无 opt-in**；`uninstall --dry-run` 也被拒（与 `install --dry-run` 不对称） | 文档化路径静默失效；用户面行为变更 | (a) 补显式 opt-in 或交互确认；或 (b) 登记「CLI 永不写真实 home」+ 同步文档 + 放行 `uninstall --dry-run`（只读预览）。**拒绝本身已被任务书列为预期形态**，故本条只判文档/登记缺口 |
| **F-8** | P2 | `test_dsh_compat.py`（`WriteSideHomeConvergenceTests`/`WriteEntryGuardTests`，读真实 `Path.home()`） | **事故同形 hazard**：把新测试跑在 **HEAD（无守卫）`launch.py`** 上时，`test_real_home_shapes_are_refused` 与 `test_unset_dsh_home_is_refused…` 会调用真实写入口 ⇒ 精确产生 `<home>/.agent-presets/` 与 `<home>/.dsh/.agent-presets/`（审查方在重定向 profile 下完整复现） | **红绿实证流程本身即真实 home 写入路径**——与本次三次事故同形 | 守卫形态矩阵改断言**纯谓词** `write_side_refusal()`；入口级断言用 seam（patch `launch.real_dsh_home`/`USERPROFILE`）隔离；**禁止在真实 profile 上调用写入口** |
| **F-3** | P2 | `launch.py:833-895`（`_shape_violations`，本片新增判据） | **变异实证**：对 item_indent / stage→allowed_forms / key_indent / entry_count / list_style **各做独立 neutralization，5 个全部存活**（13 tests 全绿）；唯一相关测试只做正相断言（`== []`） | 新增机器判据**无防护网**，可静默腐化（P4）；repo 先例 review-FEAT-030-R1 N-1 对同类缺口判 P1 | 至少 1 条反相用例（模板/item 缩进或条目数偏离声明 → `_shape_violations` 非空且两个入口判 FAIL） |
| **F-4** | P2 | `launch.py:482-483` + `:549-558`（清理分支） | 实测：非 UTF-8 `preset.yml` → 异常在 `destination.mkdir()` **之后**抛出 ⇒ `if not write_rendered_preset(staging)` 清理分支不可达 ⇒ `$DSH_HOME/.agent-presets/governance.staging-<pid>-…` **永久残留**（下次 install 用新名，旧残留永不回收） | 失败安装会在用户 DSH home 留下垃圾目录；旧代码用 `shutil.copyfile`（原始字节）**无此失败面**——本次新引入 | `write_rendered_preset` 内 try/except 或 `install_preset` try/finally 清 staging |
| **F-6** | P2 | `launch.py:879-886` vs `:896-952` | 实测 `- !!js new URL('skills', baseUrl)` 被 `_resolve_skill_entry` 判 `form='baseUrl'`/`issue=None`（合法），却被 `_shape_violations` 判 `form='relative'` → 「declared ['absolute-path']」violation ⇒ **同文件两判断互相矛盾** | 使用 loader 自身 self-location 形态的 composition 会假 FAIL | 二者择一对齐（把 `baseUrl` 加入 stage 允许集，或从 resolver 撤掉该形态并声明只支持 token/绝对路径） |
| **F-7** | P2 | `launch.py:127-129` + `:133-136` 注释 | `NEWLINE_POLICY` 与 `SKILL_FRONTMATTER` 在 `launch.py` 内**零读取点**（`_fact(...)` 从未调用），`lib/index.js` 也无 `newlinePolicy` 绑定；注释声称它们是 `test_dsh_contract.py` 的 traceability anchors，实测该测试**直接读契约字段**、不读本映射 | `own.render.newline_policy` 变异为 `crlf` **不改变任何消费者输出** ⇒ 声明不承重；注释断言失实（G-08 类）；与同片「删死代码」取向相左 | 要么消费（写入侧断言 `_fact("NEWLINE_POLICY")=="lf"`），要么删除两项并修正注释；`SKILL_FRONTMATTER` 与本片无关可直接移除 |
| **F-9** | P2 | `adapter-manifest.json:75`、`cordis.patch.yml:30-38`；对照 §4.4.7 ④ / §6.1 V7① | 授权 6 文件 **0 命中** ✅；**全仓残余 36 处 / 15 文件**（含 `README.md:417,454`、`adapters/dsh/README.md:53`、`project/CHANGELOG.md:15`、`test_readme_evidence_levels.py:66`、docs/release 与多份历史审查报告）。Developer 声明**与实测一致（诚实）** | 设计 V7① 「**全仓**无字面量」字面未达；README 两处是**仍在复述同一 `runtime-verified` 声明的第二事实源**（manifest 已去字面量，README 未同步）；docs/** 多为历史/缺陷描述，清除反而破坏证据 | 把「全仓」收窄为「授权声明面 + README 复述面」并登记 docs/** 豁免（或入 V9 一并处理）；README 两文件同步指向契约 |
| **F-10** | P3 | `adapter-manifest.json:75` | `verified_on` 由 ISO 日期改为散文指针；消费者只查非空；G12-a 的「与契约一致」由 K-7 承担（K-7 按 §2.8 属 V8） | 字段语义从机器可读日期退化为散文，V7② 实质延后到 V8 | 注明「V8 K-7 前该字段不参与机器比对」 |
| **F-11** | P3 | `launch.py:906-936` | 合法 YAML 改写实测：缩进平移 2/4、6/8、item 缩进 8 → FAIL；flow sequence → FAIL（报文「declares 0 entries, declared 2」）；条目行内注释 → FAIL | 有意严格，但报文对行内注释/flow 形态**误导** | 保持严格，改报文言辞；或解析时剥离行内注释 |
| **F-12** | P3 | `test_dsh_compat.py:2050-2075`（`_JS_PROBE`） | 依赖 `replace(/^export /gm,'')` + `import.meta.url` 赋值的**非标准源码重写** | 若 `lib/index.js` 出现行首 `export` 字面量或 `import.meta` 变只读即整体失效（可能以 skip 静默） | 改为临时包内追加 `export { resolveDshHome }`（审查方本轮即用此法，稳定） |
| **F-13** | P3 | `launch.py:764-763`、`:874-878` | `DSH_HOME="   "` 报「is not set」（实为 set-but-blank）；「declares 1 entries」单复数 | 文案精度 | 区分 unset/blank；单复数修正 |
| **F-14** | P3 | `launch.py:105`（`REPO_TOKEN`） | 重构后文件内**无读取点**，仅作 K-2 文本锚存活（`test_dsh_contract.py:1024`） | 定义处未声明其锚定用途，易被后续清理误删 | 定义处注明「仅作 K-2/契约比对锚」 |
| **F-15** | P3 | `test_dsh_compat.py` G-07 用例 | 实测 HEAD **已有** `render_composition` 的 `leftover_scan` 拒绝行为 ⇒ 新用例在 HEAD 上表现为 **AttributeError（`launch.leftovers` 不存在）** 而非行为性红 | 「改前红」对 FX-TOKEN-01/02 属**API 缺失型红**；V5① 的红绿实证对该 fixture **名不副实** | 注记差异；为 bootstrap 路径补一条真正的行为性红绿 |

## 3. 三项裁决的独立结论

- **(a) 单 commit —— 可接受**（D4 偏差成立且无害）：三切片在 `launch.py` 内确实交织（`write_side_refusal` 同时服务 V6/V7；`_read_text`/`_shape_violations` 服务 G-05/G-10/D-66）；无越界文件。**唯一要求**：分节 message MUST 逐条声明各切片**未交付项**（F-5 的 D-54、F-9 的全仓口径、G05-c/d），否则会把三片完成度差异掩盖成「全绿」印象。
- **(b) `--smoke` 模板侧 shape 断言 —— 不过严，保留正确，但不是空转**：shipped 模板与渲染面均 `[]`（无误判）；会 FAIL 的仅缩进平移/flow/行内注释/`!!js` 形态；**真正问题是它无防护网**（F-3）。须补 1 条反相用例。
- **(c) `dsh_compat.py` 零改动 —— 接受，覆盖度需收窄声明**：契约 `host.rows[]` 确无 `customSkillDirs`（逐字段实测）；G05-a（`<=`→`<`）已实现并红绿实证；G05-b 用既有契约字段在 `launch.py` 侧双向断言 ⇒ **主要缺陷（漏项）同等覆盖成立**；但 **G05-c（探针差分）/G05-d（NOT_RUN 级披露）未实现** ⇒ 须登记为 V5 未完项或移交 V8，**避免「G-05 已全绿」的过度声明**。

## 4. 事故专项审查

**① 恢复证据链**：**足以限定在 launcher 写面，不足以覆盖整个 `~/.dsh`**。审查方两次采样一致：`agent.cordis.yml` 16796 B / `00E0D330…3723`（= 金标 = JS 文件 = Python 文本 = install 文件，**四路 sha 全等**）、`preset.yml` 379 B、`skill-root.txt` 54 B、兄弟预设完好、误建目录 exists=False。论证边界：`install_preset` 写面**恰好**是那 4 文件 + 创建预设根 ⇒ 上述证据对本 launcher 写面充分；**不能**据此断言整个 `~/.dsh` 无写入。
**措辞收窄要求**：由「真实环境已恢复至事故前状态，无遗留损坏」→「**launcher 写面**已恢复（4 文件逐字节金标 + 误建目录已清除），`~/.dsh` 其余面不在本次证据范围」。
**一处不可分辨性**：真实预设 4 文件 mtime 全为 **09:29:17**（晚于 incident 文件 09:27:52 与误建目录再现 09:29:08）；「重建恢复」与「以真实 home 为目标的再次 `--install`」**内容上不可区分**（两者都用同一渲染器 + 同一 token 表）⇒ 内容级复核证明**终态无损坏**，但不能证明**最后一次写由谁发起**。

**② 守卫对称化是否真正堵住同类事故**：对 `launch.py` 三个写入口 **是**；对全系统 **否**（三点残余）：
- 已实证有效：24 形态矩阵 + 3 入口 × 6 形态 = 18/18 `rc=2 + [REFUSED]`；`install --dry-run` 仍放行；相对路径经 `resolve()` 落真实 home 亦被拒；符号链接/junction 因 `resolve()` 不可绕。`main()` 各分支静态审计确认守卫位置正确（早于任何 `mkdir`/`rmtree`）。
- **残余 1（本轮 MUST 修）**：**新测试自身构成真实 home 写入路径**（F-8）。
- **残余 2（设计边界，非本片缺陷）**：`lib/index.js::ensurePreset()` 无同类守卫且**不能**有（JS 侧「未设 ⇒ `~/.dsh`」是合法主路径）⇒ 「同类事故不可能再发生」只能声明为「**launch.py 的 CLI 写入口**不可能再发生」。
- **残余 3（弱）**：`write_rendered_preset(destination)` 直调可绕守卫（当前仅被两个已守卫路径调用）；建议加 docstring 声明「调用方 MUST 先过 `write_side_refusal`」。

**③「未解观测」独立判断**：**最可能是在守卫落地前**用真实 home 形态的 `DSH_HOME` 运行写入口（`<home>` → 09:29:08 误建目录；未设/`<home>\.dsh` → 09:29:17 真实预设 mtime；**相隔 9 秒与一次「形态矩阵试跑」完全吻合**，审查方在重定向 profile 下精确复现了这一对写入）。5 个在制文件 mtime 09:37:30 晚于该窗口 ⇒ 当时文件很可能尚无守卫。**当前代码未发现残留写入路径**；Developer 的「未复现」恰是守卫生效后的**预期结果**，故不构成「删除即结案」。**红绿流程本身是可复现 hazard（F-8），必须堵。**

## 5. 独立复现结论（11/11）

| # | 项 | 结果 |
|---|---|---|
| 1 | G-05 红→绿 | RED `[]` → GREEN 2 条（渲染后均为存在的绝对路径）✅ |
| 2 | G-10 红→绿 | RED 抛 `UnicodeDecodeError`（byte 0xff @72）→ GREEN `verdict=FAIL` + 偏移诊断 + render `""`，**不抛** ✅ |
| 3 | D-66 | 孤立 CR：RED 0 → GREEN 1（与 JS 一致）✅ |
| 4 | D-50/D-56 | `urllib|urljoin|urlparse` 仅剩文档提及；`cpSync` 0 ✅ |
| 5 | V6 收敛 + 探测侧 fail-closed | **20 例矩阵 0 分歧**；`_profile_planes` 未设/空白 → `[]`，**含阳性对照**（证明非空转）✅ |
| 6 | V7-grep | 授权 6 文件 0 命中；全仓残余 **36/15**（Developer 声明属实）✅ |
| 7 | `--smoke` 断言事实化 | `18/23 … verified; 5 NOT verified`（取 `coverage`，不重算）；终句显式声明未校验行不折进 PASS ✅ |
| 8 | 行为保持硬基线 | 三路径（+真实安装态）四路 sha256 全等 `00e0d330…3723`；28u exit 0 + `real-home writes: 0`；28v `1/23/18/5` + `writes: 0`；契约 sha 未变 ✅ |
| 9 | 测试 | 93 / 120 / 46 全 OK ✅ |
| 10 | 门禁 | `check-governance` BASE/WT **均 48 FAIL / 91 issues，`Compare-Object` 为空**；manifest-consistency PASSED；cleanup 零删除；projection-sync PASSED ✅ |
| 11 | 变异实证 | G-05/M3b/M3c/M4/M5b **被抓**（M5b 且被改写落在**重定向** fake home ⇒ 隔离有效）；**`_shape_violations` 的 5 个 neutralization 全部存活（=F-3）** ✅ |

## 6. 结论与下一步

**NEEDS_CHANGE / `unresolved_blockers=2`**。处置路径：退回同一 Developer 修 **F-2（P1）+ F-5（P1，Coordinator 已裁决实现 D-54 并放开 `test_dsh_adapter.py`/`dsh_fixtures.py` 授权）**，同批修 **F-4/F-8/F-3/F-6/F-7**（P2）与 **F-13/F-14**（P3 文案/注释）；**F-1/F-9 转文档/登记任务**；随后按 M7.4 step 4.6 以 **R1** 复审同一 Reviewer。

**审查方一句话**：实现质量高、红绿与 parity/门禁全部实测通过（P0=0），但本片自述判据 G10-b 被实测证伪（F-2）且设计指派给 V5 的 D-54 未交付（F-5）⇒ NEEDS_CHANGE/2；**F-1（守卫使文档化真实 home 路径不可达且无 opt-in）与 F-8（新测试自身即真实 home 写入路径，正是本次事故的同形 hazard）请优先裁决与登记。**

## 7. 真实环境命令上报表（R4）

13 条命令全部只读或落在 `%TEMP%` 隔离面：真实 home 仅 `Get-ChildItem/Get-FileHash/Test-Path` 只读采样（09:52 / 10:2x）；28u/28v/`--smoke`/三路径 parity 均 `DSH_HOME=%TEMP%` 重定向且 `writes: 0`；入口级调用**绝不走 `main()`**，在 `%TEMP%` 副本内经 `os.environ` 切换 + `USERPROFILE` 全局重定向；junction 实验仅在 `%TEMP%`（`rmdir` 只删重解析点）；`%TEMP%\fix316-review`（291.5 MB）已清理。**未触碰** Developer 的事故/恢复痕迹与 `~/.dsh` 任何内容；仓库 `git status` 仅 5 个在制文件、契约 sha 未变。

---

*报告结束（R0，NEEDS_CHANGE / unresolved_blockers=2）。*
