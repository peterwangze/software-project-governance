# Code Review: FEAT-020-R0 — 契约矩阵冻结与特征测试

- **Task**: FEAT-020（R0；AUDIT-150 REFACTOR-contract-matrix-freeze 零回归证明基线）
- **Reviewer**: Code Reviewer Agent（只读审查）
- **Round**: R0（首次审查）
- **审查对象**: 未提交工作树改动 —— `git diff HEAD` 为空（零已跟踪文件修改）+ 5 个新文件：
  - `skills/software-project-governance/infra/contract_matrix/__init__.py`（17 行）
  - `skills/software-project-governance/infra/contract_matrix/generator.py`（634 行）
  - `skills/software-project-governance/infra/contract_matrix/snapshots.json`（412 行）
  - `skills/software-project-governance/infra/contract_matrix/golden_samples.txt`（993 行）
  - `skills/software-project-governance/infra/tests/test_contract_matrix.py`（361 行）
- **审查方法**: 只读 git + 逐行读 5 个新文件全文 + 引擎源码交叉核对（`verify_workflow.py` dispatch 表 L24196-24280、横幅 69 处、产品门注册表 L14666-14751、`cmd_governance_write_guard` L22612-22670、post-commit hook Step 4b L195-300、5 个代表性 check 函数实现）+ manifest/.gitattributes/.gitignore/ci.yml 核对。测试运行结果采信 Developer 声明并以代码内容交叉印证（边界见 §6）。

---

## 一、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 1 项 P2、若干 P3）

**Face 1（CLI dispatch，AST 提取）——核实一致。**
- 引擎 `main()` 内 commands 字典唯一赋值在 `verify_workflow.py:24196`，L24197-24276 恰好 80 个条目，全字面量 str 键 + Name handler，无 `**spread`、无条件注册；全仓库 grep 无 `commands.update` / `commands[` 逐键赋值（其余 `commands` 匹配为无关局部变量：L4471/6010/6215/12739）。AST 提取器（generator.py:95-143）的覆盖面 = 引擎真实 dispatch 全集。
- 3 个双键别名组与源码逐一对上：`cmd_dynamic_lifecycle_migration`（L24244/24245）、`cmd_check_deterministic_scaffolds`（L24265/24266）、`cmd_check_interruption_policy`（L24267/24268）；80 - 3 = 77 handler ✓。快照 keys 列表与源码条目抽查（含 web-console/resolve-entry/gemini-auth-preflight/task-priority-analysis/change-triage/governance-write-guard 等）全部一致。
- 提取器对非字面量键/非 Name handler fail loudly（generator.py:124-130）——未来引擎漂移不会静默漏提。

**Face 2（Check 段清单，横幅 ∪ 注册表）——核实一致。**
- 引擎横幅实数 69 个（grep `┌─ Check` 全部 69 处 print，L14774-16411）。其中 4 个为无填充线形态（`┐` 前是空格而非 `─`）：Check 18e（L15329）、18g（L15373）、18h（L15395）、28l（L15836）——正则 `─*\s*┐`（generator.py:148-149）中 `─*` 匹配零次 + `\s*` 吃空格，两种形态均覆盖，实测 titles 含 18e/18g/18h/28l ✓。
- `Check 30b` 无横幅，仅存于两个产品门注册表（`_PLUGIN_PRODUCT_CHECK_IDS` frozenset L14691、`_PRODUCT_GATE_LABELS` dict L14747，标题 "Loop wiring call sites" 与快照一致）——69 横幅 + 1 注册表 = 70 段 ✓。注册表各 25 项，其余 24 项已有横幅（`titles.setdefault` 保留横幅标题优先，如 28d 保留横幅版 "Runtime Readiness Matrix (FIX-106)" 而非注册表 label）✓。
- 横幅全部位于 `verify_workflow.py` 主文件（infra 目录 grep 确认；tests 中的构造横幅不在提取对象内）；L16464 docstring 的 `Check N` 通用描述不满足 `[0-9]+[a-z]?`，不产生假阳性。

**Face 3（Result 形状，实调签名）——核实稳定。** 5 个代表性函数（evidence_domain.py:242 / risk_domain.py:147 / review_domain.py:2960 / triage_domain.py:242 / verify_workflow.py:22368）逐一读实现：返回 dict 的键面全部无条件构造——`check_evidence_completeness` 4 键（L262-267）、`check_risk_staleness` 3 键（L164-168）、`check_governance_write_shapes` 预初始化 4 面 + SKIP 兜底（L22406-22411）、`check_change_triage` 7 键 return（L347-355）且 wiring 子 dict 在 `check_triage_wiring` 两个分支均为恒定 4 键（triage_domain.py:124-127/143-154）、`check_loop_wiring_call_sites` 4 键。值依赖 `.governance` 数据但 `type_signature`（generator.py:213-235）只取键面+类型名、序列 collapse 为 `$seq`——**键面恒定 ⇒ 形状签名与本机治理状态无关**。CI 端 `.governance/` 被 gitignore（checkout 无此目录）时各函数均正常降级返回同键面（文件缺失分支逐一存在）。

**Face 4（guard 输出 pin）——核实到位（详见重点 4）。** guard 命令入口 `cmd_governance_write_guard`（L22612）即 `check_governance_write_shapes()` 的 thin entry + 打印；`--project-root` 经全局参数改写事实源（golden fixture A 空 host 全 SKIPPED、fixture B 畸形行 FAIL 的事实输出自证机制生效）。

**发现（正确性）**：
- **P2-1** `generator.py:42`：`_REPO_ROOT = _ENGINE_PATH.parents[2]` 实际指向 `<repo>/skills` 而非仓库根（parents[0]=infra、[1]=software-project-governance、[2]=skills）。当前无功能破坏——`git -C <repo>/skills` 会向上发现 `.git`（快照 git_head 为 40 位 sha 佐证）、guard/verify 子进程不依赖 cwd（golden verify PASSED 佐证）——但变量名实不符是潜伏缺陷：未来任何依赖 cwd=repo-root 的相对解析会静默错位。建议改为 `parents[3]` 或以 `_ENGINE_PATH.parents[2]` 重新命名。
- P3-4 `generator.py:180-199`：注册表提取器对非字面量构造（未来若改为 `frozenset(A | B)` 等 BinOp）静默得到空集而不 raise——30b 将丢失、count 69≠70 会被 drift 检出（fail 方向正确），但报错表现为"段数漂移"而非"解析失败"，定位成本高。可加非字面量即 raise 的守卫。

### 维度 2：安全性 — 通过

- 无硬编码密钥/token；无注入面（`subprocess.run` 全部列表参数，无 shell=True；正则均作用于自产文本）。
- fixture 清理 `shutil.rmtree(_GUARD_FIXTURE_BASE, ignore_errors=True)`（generator.py:291）只删除 tempdir 下自建固定前缀目录 `spg-contract-matrix-guard`，零真实环境接触（`.governance`、`$HOME` 配置目录均不触碰）——"真实环境防护"三选一之"隔离环境（临时目录）"满足 ✓。
- 并发边界：固定 tempdir 路径在两个进程并行跑（如并行 pytest）时会互删重建 fixture——当前 CI 串行执行无触发路径（P3 备注级）。
- **P2-3（隐私/整洁）**：`golden_samples.txt:9/22/990` 含开发者本机绝对路径与用户名（`C:\Users\peter\AppData\Local\Temp\...`）；且 `contract_matrix/` 位于 manifest `product.entries` 的 `skills/software-project-governance/infra/` dir 条目下（已核实 manifest 结构），将随插件分发给最终用户。建议 fixture 路径在样例头部做占位化（如 `<temp>\spg-contract-matrix-guard\pass-host`）。

### 维度 3：可维护性 — 通过

- 命名表达意图（extract_/derive_/diff_faces 等）；docstring 密度高且与实现一致（含设计锚点 §8.1/§10）；四 face 分节清晰；冻结申报（FREEZE_POINT/PYTHON_FAMILY_PINS/REPRESENTATIVE_RESULT_CALLS）与提取数据显式分离并注释"NOT extracted data"——杜绝手抄清单的审计面处理得当。
- 模块职责单一：generator 只做提取/harness，`__init__.py` 只做包说明；测试只做特征断言。
- `diff_faces`/`_dict_drift`（generator.py:465-493）递归 diff 报告路径化 drift（missing/added/changed 三类），可维护性好。
- 无超长函数（`derive_guard_output_pin` 71 行但线性分节；`write_golden_samples` 31 行）。

### 维度 4：性能 — 通过（P3 提示）

- AST 解析 24k 行引擎每 extract 2 次（`_engine_tree` 无缓存）≈ 数百 ms 级，可接受。
- 主要成本在 guard 真实子进程：测试进程内约 12 次（见 P3-1），CI 无 timeout 配置（ci.yml 仅 4 步）——3.11 端时长负担但无失败风险。
- 无 N+1 / O(n²) 问题；fixture rmtree+重建以确定性优先，取舍合理。

### 维度 5：测试覆盖 — 通过

- 27 例清点：SnapshotFile 4 + FreezePoint 3 + CliDispatch 3 + CheckSegments 3 + ResultShapes 2 + GuardPin 4 + Determinism 2 + RedGreen 5（4 扰动 + 1 绿）+ GoldenSidecar 1 = 27 ✓，与声称一致。
- 核心路径（4 面 match 断言）、确定性（两次提取 + harness 零 drift）、红绿保护、冻结点计数（80/70）、3.11 fail-closed、CRLF 容错（setUp 与 golden 读取均 normalize，对应 `.gitattributes` 只锁 `*.py/*.json` 而 `*.txt` 无 eol 锁的已核实事实）全覆盖。
- 错误路径（提取器 raise 分支）无直接单测——在特征测试哲学下由 drift 断言间接承担（引擎漂移 → raise 或 drift → 红），可接受（P3 级）。

---

## 二、6 个审查重点逐项结论

### 重点 1：提取器正确性 — 通过
见维度 1。**70 段与 80 键的提取经源码逐项对照为真全覆盖**：dispatch 无任何动态注册路径（AST 字面量提取 + 全仓 grep 双重印证）；4 个无填充线横幅被 `─*\s*┐` 边界覆盖；30b 由注册表 AST 补入且标题一致。

### 重点 2：快照确定性 — 通过（含边界说明）
- **比对面排除时变字段已核实**：`check_against_snapshot`（generator.py:496-502）只对 `stored["faces"]` 做 `diff_faces`；`generated`（timestamp/git_head/python.*）、`freeze_point`、`python_family_pins` 均不参与比对。`save_snapshot` 用 `sort_keys=True, indent=2, ensure_ascii=False, newline="\n"`，测试 `test_snapshot_uses_stable_canonical_ordering` 反向钉住文件字节 == canonical dump。
- **Result 形状实调无本机状态依赖**：5 函数键面无条件构造（逐一核实，见维度 1）；换 cwd/换环境（CI 无 .governance）形状签名不变。
- **self-check 方法论边界（P3-3）**：`--self-check` 仅证同进程两次提取零差异，不覆盖跨进程/跨 cwd 维度；实际跨端护城河由特征测试（match 断言）+ CI 3.11 实跑构成。当前组合充分，建议在 docstring 中明示此分工以防误用 self-check 作为唯一确定性证据。

### 重点 3：测试质量 — 通过
4 例扰动真实拦截（同一 `diff_faces` 递归 diff 的函数级证明：加键/删段的 list repr drift、类型变异的路径 drift、行变异的字符串 drift，断言的 `any(... in d)` 均能命中）；CRLF 容错实现与 `.gitattributes` 事实一致；`test_running_interpreter_family_is_pinned`（test_contract_matrix.py:113-123）实现 3.11 族 fail-closed：非钉族解释器运行即红并给出处置指引——生成与比对同族约束落实。

### 重点 4：guard pin 面（FEAT-017 F-2 收编）— 通过
hook 消费点在 **post-commit** Step 4b（pre-commit grep 无 guard 消费）。4 个解析点逐一对照 pin：

| hook 解析点（post-commit） | pin 字段 | 覆盖判定 |
|---|---|---|
| `grep -q '^Result: PASS'`（L268） | `result_pass_line`（整行字面）+ `result_fail_prefix` 族 | 覆盖且更严 |
| `grep -q '^Result: FAIL'`（L275） | `result_fail_prefix` + `result_fail_regex`（`^Result: FAIL — \d+ issue(s)。[\s\S]*$`） | 覆盖且更严 |
| `grep -c '^ *- '`（L276/283，0+ 空格宽松） | `issue_line_prefix="    - "` + `issue_line_regex`（恰好 4 空格 + 可选 `L\d+`） | pin 严于 hook——缩进漂移先被 pin 拦截 |
| rc ∈ {0,1}（case L266/274） | `exit_codes` {pass:0, fail:1, wellformed:0} | 覆盖 |

hook 不解析 header/face 行，pin 额外钉了 `header_line`/`face_line_regex`/`face_labels`——超集防护。**pin 完整覆盖 hook 消费面，F-2 收编到位。** 另：guard 入口 `sys.stdout.reconfigure(encoding="utf-8")`（verify_workflow.py:22631）保证子进程输出跨端字节稳定，pin 中中文字符串在 3.11 ubuntu 端重提取可复现——这是 pin 设计正确性的关键事实。

### 重点 5：AI 专项 5 项 + 文件面 + 纯粹性 — 通过
- **mock 残留**：无。测试零 mock import，全部真实提取 + 真实子进程。
- **硬编码返回值**：无欺骗性硬编码。`snapshots.json` 是设计规定的冻结基线（protection-net 语义）；generator 内字面量仅限任务规定的申报（S6 残余波次/S4 族钉）与设计选样（5 个代表性构造点），均注释标明"NOT extracted data"；测试的 `FROZEN_CLI_KEY_COUNT=80`/`FROZEN_CHECK_SEGMENT_COUNT=70` 为任务规定的冻结点计数申报。
- **幻觉 API**：无。所用标准库 API（ast/subprocess/json/tempfile/argparse/atexit/shutil）真实；对引擎属性经 `getattr` 可调用性校验（generator.py:238-244）；`vw` re-export 链存在（verify_workflow.py:1091/1111/1165/1231）。
- **未实现 TODO**：无 TODO/FIXME/placeholder。
- **过度实现**：无明显过度。四个模式（--regen/--check/--self-check/--golden）均为验收 ②③ 与差分 harness 要求；wellformed fixture 服务三态 fail-closed 校验（generator.py:358-367，缺失即 raise）。
- **文件面**：新文件全部位于 `infra/contract_matrix/` + `infra/tests/`——紧邻被冻结引擎，合理；`manifest.json` `product.entries` 含 `infra/` dir 条目且 cleanup.py `expand_canonical` 按 dir 展开收磁盘文件（cleanup.py:244-246），新文件自动入 canonical——**不会被 cleanup 判残留误删**；`__pycache__/*.pyc` 工作树残留已被 `.gitignore`（`__pycache__/`）排除，不会入库。triage 两路径记录在 `.governance/`（runtime data，不在本审查对象内）——由 Coordinator 侧闭环。
- **纯粹性**：`git diff HEAD --stat` 为空——**"零引擎行改动"声称属实**（全部改动为纯新增 5 文件）。

### 重点 6：存量失败归属采信 — 采信（边界标注）
Developer 方法论（stash 新文件 → 跑基线 → 对照全量）合理；代码交叉印证成立：改动为纯新增（`git diff HEAD` 空），新增文件不被既有 816 套件中的任何测试导入（除新测试自身），无因果路径使存量 31F/E 由本 diff 引入。**边界**：Reviewer 未复跑测试（只读审查约束），stash 对照的原始输出未附证据文件——按任务硬门槛"测试运行采信 Developer + 代码内容交叉印证"处理，27/27、self-check 7729B×2×3、健康 30 无新增均采信并标注此边界。

---

## 三、发现汇总

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-1 | **P2** | `contract_matrix/generator.py:42` | `_REPO_ROOT = parents[2]` 指向 `<repo>/skills` 而非仓库根（名实不符；当前被 git 子目录回退与子进程 cwd 无关性掩盖，无功能破坏） | 改 `parents[3]` 或重命名变量；遗留需记跟踪表 |
| F-2 | **P2** | `contract_matrix/golden_samples.txt:764-958, 975-987` | verify/stages 样例大范围 mojibake（README snippet 中文、stages 横幅 box 字符全部 `?` 化）——根因是这两条命令路径未 `reconfigure(stdout, utf-8)`（引擎既有行为），golden 以 `errors="replace"` 固化了损坏形态；人审材料不可读，且 3.11 ubuntu（UTF-8 locale）重跑 `--golden` 形态不同，头部 "rerun --golden to compare" 的跨端可比性声明不成立。不影响快照断言面（guard 路径有 reconfigure，pin 中文完好且跨端可复现） | 样例生成时对非 reconfigure 命令设 `PYTHONIOENCODING=utf-8`（或 `env` 注入）后重生成；或在头部声明 Windows 端形态限制 |
| F-3 | **P2** | `contract_matrix/golden_samples.txt:9/22/990` + `core/manifest.json` product.entries | golden 含开发者本机绝对路径与用户名，且 contract_matrix/ 随 product infra/ dir 分发给最终用户 | fixture 路径占位化后重生成 |
| F-4 | P3 | `tests/test_contract_matrix.py:210-217` | `@lru_cache` 装饰实例方法：unittest 每测试新实例 → 缓存永不跨测试命中且持有旧 self；guard 子进程在测试进程内重复执行约 12 次（CI 时长负担） | 提为模块级函数或 `setUpClass` 缓存 |
| F-5 | P3 | `generator.py:538` | `resolved[1:] if resolved[0].endswith('.py')` 死分支（`resolved[0]` 恒为 `--project-root`/`verify` 等参数，永不以 .py 结尾） | 删除分支 |
| F-6 | P3 | `generator.py:578-590` | `--self-check` 仅证同进程确定性，不覆盖跨进程/跨 cwd 维度 | docstring 明示护城河分工（特征测试 + CI 承担跨端） |
| F-7 | P3 | `generator.py:180-199` | 注册表非字面量构造时静默空集（不 raise），30b 丢失表现为 count 漂移而非解析失败 | 非字面量即 raise |
| F-8 | P3 | `golden_samples.txt:989-993` | check-governance 样例 stdout 为空、exit 1 且未记录 stderr——人审无法看到失败原因 | golden 段落追加 stderr 摘要 |

**P0 = 0，P1 = 0**。P2×3 + P3×5 均不阻塞：F-1 当前无破坏路径；F-2/F-3 仅影响非断言的人审 sidecar，不影响快照/测试/CI 任何断言面。

---

## 四、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅ 0 |
| 5 维度全覆盖 = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐项有结论 |
| 每条发现标注级别 = 100% | ✅ F-1~F-8 全部 P2/P3 |
| 设计一致性检查已完成 | ✅ 对照 FEAT-020 设计 §8.1（代表性选样 5 构造点）/§10（验收 ② 确定性 ③ 黄金样例）；FEAT-017 F-2 收编对照 post-commit Step 4b 逐解析点核验；AUDIT-150 零回归基线意图与四面冻结实现一致 |
| AI 专项 5 项全部完成 | ✅ mock 残留/硬编码/幻觉 API/未实现 TODO/过度实现逐项有结论（重点 5） |

---

## 五、审查结论

# APPROVED_WITH_NOTES

**unresolved_blockers = 0**

四契约面提取正确性经源码逐项交叉核实为真（80 键/77 handler/3 别名组、70 段 union 含 4 无填充横幅边界与 30b 注册表补入、5 构造点键面恒定、guard pin 覆盖 hook 消费面且更严）；快照确定性与跨端稳定性成立（faces-only 比对 + sort_keys/LF + reconfigure-utf-8 + 3.11 fail-closed + CI 实跑落实）；纯粹性属实（git diff HEAD 为空）；27 例特征测试含真拦截力的红绿保护。P2×3（_REPO_ROOT 名实不符 / golden mojibake / golden 本机路径随 product 分发）建议随下一切片处理并记遗留，不构成本轮阻塞。

*审查边界声明：测试运行数据（27/27、self-check ×3、stash 基线对照、健康 30、manifest/projection/cross-ref PASS）采信 Developer 声明，以代码内容交叉印证；CI 3.11 端实际执行结果以流水线为准（本审查未运行任何测试）。*
