# FIX-316 代码审查报告（Code Review R1 — 复审）

- **任务**：FIX-316（0.81.0 切片 V5+V6+V7）
- **Round**：**R1（复审）**；**前轮引用**：`REVIEW-FIX-316-R0` = NEEDS_CHANGE / `unresolved_blockers=2`（`docs/reviews/review-FIX-316-CODE-R0.md`，已完整重读并作为逐条比对基线）
- **审查对象**：工作树 7 文件（HEAD 仍 `85fb309`；`+2141/−140`）：`launch.py`（1544→1746 行）·`lib/index.js`·`cordis.patch.yml`·`adapter-manifest.json`·`test_dsh_compat.py`（+1049）·**`test_dsh_adapter.py`（+76，新增授权）**·**`dsh_fixtures.py`（+163，新增授权）**
- **Reviewer**：Code Reviewer Agent（只读；构造/变异全在 `%TEMP%\fix316-r1\` 副本；`USERPROFILE`/`HOME` 重定向；`main(["--install"])` 仅在 `%TEMP%` 副本 + 一次性 `DSH_HOME` 下运行；**真实环境零写**）
- **结论**：**NEEDS_CHANGE / `unresolved_blockers=1`**（P0 = 0；硬门槛 5/5 通过）
- **为何不是 APPROVED_WITH_NOTES**：存在 **1 项本轮新引入的公共入口栈泄漏 + 相对 HEAD 的功能回归（N-1）**。**为何不是 BLOCKED**：N-1 是 4 行内的定点修复。
- **R0 两条 P1 阻塞项均已闭环**（F-2、F-5）；本轮阻塞来自**本轮新代码**。

## 1. 逐条比对（R0 15 条）

| R0 | 级别 | 本轮判定 | 独立证据 | 仍存问题 |
|---|---|---|---|---|
| **F-2** | P1 | **已修复** | 全部内容型读取走 `_read_text`（静态扫描无遗漏）；**新增 `PublicEntryDecodeBoundaryTests`（5 tests）真实调用 `main(["--install"])`**，覆盖设计 §4.4.6 ③ 第三入口。审查方**自建副本**复跑：非 UTF-8 `package.json` → **rc 1 / raised=None / `traceback=False`** + 含文件名与 `byte offset 13`；`preset.yml` → offset 15；`skill-root.txt` → 结构化 FAIL 不抛；健康对照 → rc 0 + 4 文件 | 无（`_repo_root_for_preset` 对不可解 marker 静默按缺失处理 → N-6b，P3） |
| **F-5** | P1 | **已修复** | D-54 与 §3.3 第 11 行**逐字核对**：`top_level` 只记名字（实测样本无 size/mtime）；`write_surface` 不容忍竞态；第 2 次采样仅在疑似时取。`FX-WITNESS-01` 从 `DEFERRED` → **可执行 oracle**（审查方独立 emit + 执行：rc 0、`verdict=PASS`、6 条 judgment 全 true），两处测试消费；`test_dsh_adapter.py:1013-1017` 按 C-23 改写并在 diff 内声明 | 无 |
| F-1 | P2 | **部分修复**（dry-run 半边已修；opt-in/文档未动，按裁决转出） | 顺序锚点实测 `739 dry_run → 759 守卫 → 766 rmtree`；`install` 同构；dry-run 在真实 home 形态 rc 0 且**不含** `[REFUSED]`；非 dry-run rc 2 + `[REFUSED]` | 转出项**无持久登记** → N-7 |
| **F-8** | P2 | **已修复** | `_isolated_profile()` seam 实测：`Path.home()`/`real_dsh_home()`/`preset_dir()` 三者全落 fake。**删守卫变异**（调用点 3→1）→ `WriteEntryGuardTests` **如实转红 9 条**，而真实 profile 的**适配器写面 oracle** 三次采样一致（含 6 s 无操作对照，噪声底 = 0）；两次独立运行结论一致 | 无 |
| F-3 | P2 | **其声明 5 项已修复；仍存 1 个存活变异** | 其 5 项（key_indent/item_indent/entry_count/entry_form/baseUrl_stage）**全部被抓**；审查方另构造 8 项，**6 项被抓**，**`list_style` 检查移除存活** | → N-3（P3） |
| **F-4** | P2 | **已修复** | 元数据读**前移到 `mkdir` 之前**；`write_rendered_preset` 内 try/except。**诱导「mkdir 之后的失败」**（`_fact("PRESET_MARKER")` 抛 `OSError(28)`）→ rc 1、`staging-*` 残留 **`[]`**；非 UTF-8 路径下 DSH home 树**完全为空** | 该保险丝**无测试覆盖** → N-2 |
| F-6 | P2 | **已修复** | `!!js` 归类为 `baseUrl`，rendered 允许集含 `baseUrl`；M5/M7 变异**均被抓** | 无 |
| F-7 | P2 | **已修复** | `SKILL_FRONTMATTER` 已删；`NEWLINE_POLICY` 现有读者 `require_lf_newline_policy()`。**独立注入** `"crlf"` → rc 1 + `ContractMalformed` + **未写任何文件** | 无 |
| F-9 | P2 | 未修复（转出） | 授权 7 文件 **0 命中**；全仓仍 **36/15** | **无持久登记** → N-7 |
| F-10 | P3 | 未修复（转出） | manifest 未再改动 | → N-7 |
| F-11 | P3 | 未修复（转出）；单复数已修 | 报文仍为 `form 'relative'`；`declares 1 entry` 已修 | → N-7 |
| **F-12** | P3 | **未修复，且未列入转出清单** | `_JS_PROBE` 的 `replace(/^export /gm,'')` + `import.meta.url =` 原样保留 | **登记遗漏** → N-7 |
| F-13 | P3 | **已修复** | unset 与 set-but-blank 两条消息实测 `!=` | 无 |
| F-14 | P3 | **已修复** | `launch.py:101-110` 注释块声明锚定用途 | 无 |
| **F-15** | P3 | **未修复，且未列入转出清单** | bootstrap token 路径仍无行为性红绿 | **登记遗漏** → N-7 |

**统计**：已修复 **9** + F-3 声明 5 项；部分修复 **1**（F-1）；转出未修 **5**；**未修未转出 2**（F-12/F-15）；**新引入回归 1**（N-1）。

## 2. 本轮新发现

| # | 级别 | 位置 | 事实（已独立实测） | 影响 | 建议 |
|---|---|---|---|---|---|
| **N-1** | **P1 阻塞** | `launch.py:835-860`（`write_side_refusal → real_dsh_home() → Path.home()`）；调用者 `install_preset:635`/`uninstall_preset:759`/`smoke_preset:1469` | **新引入公共入口栈泄漏 + 相对 HEAD 的功能回归**。环境：`DSH_HOME` 为有效可写目录、OS profile 全不可解析（`USERPROFILE`/`HOME`/`HOMEDRIVE`/`HOMEPATH` 均未设）。同一 env 仅换树对照：**HEAD `install_preset()` → rc 0 且正常写 4 文件**；**R1 → `RuntimeError: Could not determine home directory.`**，`uninstall_preset()` 同，**`main(["--install"])` 同（无任何 try ⇒ 真机 CLI traceback + 非零退出）**。根因：守卫在 `raw` 非空非空白时**必须先** `real_dsh_home()`，而 R0 及更早，`install`/`uninstall` 在 `DSH_HOME` 为普通路径时**不触碰 `Path.home()`**。本仓库 **JS 侧**已把该场景视为真实故障模式并加守卫（`lib/index.js:408-415` 明示 `uv_os_homedir ENOENT`）⇒「不可达」不成立 | 违反本片自述判据 G10-b 的**新实例**；对「显式指定 `DSH_HOME` 的合法安装」是**功能回归**（HEAD 可用、R1 崩） | 守卫内 try/except：`try: real_home = real_dsh_home() except (RuntimeError, OSError): return "<var> is set but the user profile cannot be resolved — refusing to <op>"`（fail-closed 拒绝、**绝不抛**）；补一条**擦除 profile** 的反相用例 |
| **N-2** | P2 | `launch.py:684-691` + `PublicEntryDecodeBoundaryTests` | F-4 的「belt & braces」清理分支**无测试覆盖**：删除该 `rmtree(staging, ignore_errors=True)`（变异 M13）后 5 个用例**仍全绿**（因解码失败现在早于 staging 创建） | 唯一覆盖「`mkdir` 之后失败」的保险丝可被静默移除 | 补 1 条反相：诱导写入期失败 → 断言 `<DSH_HOME>` 下无 `*.staging-*` |
| **N-3** | P3 | `launch.py:1153-1156` | `list_style` 检查移除（M6）在 23 个用例下**存活**；且该检查只审**声明值**、不审文档形态（flow sequence 实际落到 entry_count 报文） | shape 判据一维无防护网 | 并入「声明 vs 文档形态」双面判据，或标注为契约自检并删不可达分支 |
| **N-4** | P3 | `launch.py:979-983`（docstring 末句） | 原句「Without a resampler … **the write surface alone decides**」与实现**相反**：无 resampler 时 top_level 差集**直接 FAIL**（实测 `failures=["real DSH home top level changed: f:x"]`） | 文档断言失实（G-08 类） | 改为「without a resampler a top-level delta is a failure」 |
| **N-5** | P3 | `launch.py:996-1005` | `reproduced` 判据为「后第 2 次采样相对**基线**仍有**任何** top_level 差异」；构造「出现的是**另一个**变化」→ 仍 FAIL（fail-closed）。设计字面是「复现**同样**变化才 FAIL」 | 字面判据下非同源变化不应按原变化 FAIL | 保留 fail-closed 行为但在注释写明取舍；或改为集合差集相等判定 |
| **N-6** | P3 | (a) `dsh_fixtures.py:222-236`；(b) `launch.py:1200-1215` | (a) 注释自称「**ASCII-only**」但含 U+2014（em dash）：`src.encode('ascii')` 抛 `UnicodeEncodeError`（pos 17），另有**未使用**的 `textwrap` import（无害）。(b) 不可解码的 `skill-root.txt` 被**静默**按缺失处理，**不产生 issue/NOT_RUN 披露** | (a) 新代码注释-事实不符（同 F-7 类）；(b) 与「不得静默降级」取向相左 | (a) 改注释或换 `--`，删 `textwrap`；(b) 作为 issue/NOT_RUN 披露 |
| **N-7** | P3（登记） | `.governance/*` + `docs/release/release-checklist-0.80.0.md` | **两处登记遗漏**：(i) 5 项转出项（G05-c/G05-d、F-9、F-10、F-11、F-1）在治理文件中**全量检索无任何持久登记**（派发正文的裁定**不是**持久记录）；(ii) **F-12/F-15 既未修复也未列入转出清单 ⇒ 无归属** | 转出项会随会话结束失去去向；F-12/F-15 将静默丢失 | 在 evidence-log 追加转出项清单行并在 plan-tracker/release-checklist 登记；F-12/F-15 补登记或明确关闭 —— **Coordinator 侧动作** |
| **N-8** | P3 | `launch.py:583-584` vs `:668` | 严格 `require_package_version()` 只装在 `install_preset`；`write_rendered_preset` 写 marker 仍用宽松读（可写 `"0"`），`smoke_preset` 直调无该门 | 防御纵深：未来新增调用方可能绕过 | version 作参数传入，或写入点也用严格读 |

## 3. 七项定向复验结论

1. **F-2 三读点 + 三入口 → 成立**：静态扫描全部 `read_text|open(` 调用点，内容型读取无遗漏（仅剩 2 处 `errors="replace"` 为诊断型、不泄漏栈）；设计 ③ 三入口齐备，审查方**自建副本**复跑确认 rc 1 + `traceback=False` + 偏移。
2. **`require_package_version()` 拒绝语义 —— 论证成立**：独立读 JS 确认幂等判据（`if (existsSync(userDir) && current === version) return outcome`）；写占位 `"0"` ⇒ `current === version` 恒假 ⇒ **每次 boot 重建预设**。故 fail-closed 正确，且实测被拒时**零副作用**（连 `.agent-presets` 都不创建）。新增失败面仅 N-8（P3）。
3. **F-4 staging 零残留 → 成立（含 `mkdir` 之后的失败）**：三条路径实测（pre-flight 失败 → home 树空；诱导 `OSError` → `staging=[]`；健康 → rc 0 + 4 文件）；但保险丝无测试 → N-2。
4. **D-54「与基线比 vs 与首后样本比」—— 基线比较才是设计要求（Developer 自查修正正确）**：设计对两种结局给出确定语义标签（仅出现一次 = advisory；复现 = FAIL），**只有基线比较同时满足两者**；用首后样本比较会让两者**各自反转**。审查方以变异注入证实测试已钉住该语义；实测矩阵：race → `PASS + 1 advisory`；persistent add/remove → `FAIL`；write_surface 变化带豁免型 resample → **仍 FAIL**。
5. **F-8 隔离性 → 成立（含最强形式）**：seam 直证三处路径全落 fake；删守卫变异 3→1 → 用例转红 9 条；真实 profile 适配器写面 oracle 三次一致（噪声底 = 0）；两次独立运行可重复。**方法论纠错如实披露**：审查方首次用「整个 `~/.dsh` 递归 + 内容 sha」做 oracle 误得「已变更」，复检确认是**宿主会话持续写 `sessions/`/`storages/` 的噪声**；改用适配器写面 oracle 后一致 —— 这也**反向印证** witness 设计「排除宿主自带活动」的必要性。
6. **F-3 → 其 5 项全被抓；审查方另构造 8 项中 6 项被抓、2 项存活**（`list_style` → N-3；F-4 清理 → N-2）。
7. **(d) dry-run 可证伪性 → 判据成立且已被审查方升级**：初版「母目录递归指纹」**不足**（漏掉 `<home>/.agent-presets` 这一历史事故形态；无内容哈希时同 size 改内容会漏检）；升级为**全 profile 内容级 oracle**（目录 size+mtime_ns；文件 size+mtime_ns+sha256）后两种盲区消除。4 次 dry-run（install/uninstall × 两形态）→ rc 0 + `[DRY-RUN]` + 无 `[REFUSED]` + **`whole_profile_identical: true (diff = [])`**；同形态非 dry-run 4 次 → rc 2 `[REFUSED]` 且 oracle 一致、目标文件存活。

## 4. 事故专项复评（R1 增量）

- EVD-1024 已把「未解观测」登记为「最可能 = 早期探针版本（`DSH_HOME` 误设为 `<home>`）的残留再生成」并记录**事件 3 = `v7_guard_probe.py` 首版 RED 段在 `%TEMP%` 副本内执行原树未守卫的 `install_preset()`** —— 与审查方 R0 的独立复现机制**完全一致** ⇒ 该观测**不再需要保留为「指向未修复残留路径」的怀疑**。
- 本轮**最强形式验证**：**在无守卫代码上运行守卫回归测试也不会触碰真实 profile** ⇒ R0 指出的「红绿流程本身即写入 hazard」已被彻底堵住。
- 残余（设计边界，非缺陷）：`lib/index.js::ensurePreset()` 仍无同类守卫且**不能**有（JS 未设 `DSH_HOME` 是合法主路径）；`write_rendered_preset` 直调仍可绕（已加 docstring 声明调用方义务）。

## 5. 硬门槛复核

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 | = 0 | **0** | ✅ |
| 5 维度 | 100% | 逐项有结论（正确性缺陷 = N-1/N-2） | ✅ |
| 发现分级 | 100% | 8 条新发现全带级别；R0 15 条逐条判定 | ✅ |
| 设计一致性 | 已完成 | §6.1 V5/V6/V7 逐条；R0 两条未达标已闭环 1、转出 1 | ✅ |
| AI 专项 5 项 | 全部完成 | mock 残留无（`patch.dict` 为环境隔离）/硬编码无/幻觉 API 无/TODO 0/过度实现无 | ✅ |

**行为保持硬基线（R1 自跑）**：四路渲染 sha256 全等 `00e0d330…3723`；契约 sha256 未变；28u **exit 0 + `real-home writes: 0`**；28v `1/23/18/5` + exit 0；`--smoke` 两 surface `18/23 + 5 NOT verified (NO_SCHEMA=5)`；三套件 **113 / 120 / 47 OK**；`check-governance --summary-only --level strict`：BASE(HEAD) = **48 FAIL / 91 issues**，WT = **48 FAIL / 91 issues**，**`Compare-Object` 输出为空 ⇒ FAIL 行不增**（Developer 自述 40→40 为**同一结论、不同绝对数**；绝对数随治理记录演进，非本次 diff 的函数 —— 建议后续引用同一命令同一时点数字）；manifest-consistency / projection-sync / `check-agent-adapters` PASSED；cleanup 零删除。

## 6. 结论与下一步

**NEEDS_CHANGE / `unresolved_blockers=1`（N-1）**。处置：退回同一 Developer 修 **N-1（P1，约 4 行 + 1 反相用例）**，同批修 **N-2（P2 测试缺口）** 与 **N-3/N-4/N-5/N-6/N-8（P3）**；**N-7 的登记遗漏为 Coordinator 侧动作**（本报告出具后即执行）；随后按 M7.4 step 4.6 以 **R2** 复审（round=2 < 3）。

**审查方一句话**：R0 两条阻塞项（F-2 栈泄漏 / F-5 D-54）**已实证闭环**，F-1/F-3/F-4/F-6/F-7/F-8/F-13/F-14 亦已验证正确（守卫对称化更是「无守卫代码上也不再触碰真实 profile」）；但本轮新代码引入 **N-1** ⇒ NEEDS_CHANGE/1；请优先裁决 N-1 并补登记 N-2 与 **N-7 的两处登记遗漏（F-12/F-15 未归属 + 5 项转出项无持久行）**。

## 7. 真实环境命令上报表（R4）

11 类命令全部只读或落 `%TEMP%`：真实 profile 仅只读采样（前后各一次）；谓词矩阵为**纯函数**（只读环境变量与路径解析）；入口级拒写与 dry-run oracle 全部 `USERPROFILE`/`HOME`/`HOMEDRIVE`/`HOMEPATH` 重定向；`main(["--install"])` 覆盖仅在 `%TEMP%` 副本 + 一次性 `DSH_HOME`（边界豁免项）；13 项变异在 `%TEMP%\MUT` 副本（守卫变异**故意不加**外部重定向以检验测试自身隔离）；环境擦除对照在子进程 env 中全清 profile 且 `DSH_HOME` 指向一次性 `%TEMP%` 目录；junction 实验仅在 `%TEMP%`（`rmdir` 只删重解析点）；`%TEMP%\fix316-r1`（264.9 MB）已清理。**未触碰** Developer 的事故/恢复痕迹与 `~/.dsh` 任何内容；仓库 `git status` 仅 7 个在制文件 + 前轮报告未跟踪；`__pycache__` 时间戳早于套件运行 ⇒ `PYTHONDONTWRITEBYTECODE=1` 生效、零字节码写入。**真实 home 写操作 = 0 次。**

---

*报告结束（R1，NEEDS_CHANGE / unresolved_blockers=1）。*
