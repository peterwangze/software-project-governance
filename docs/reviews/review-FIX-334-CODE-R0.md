APPROVED_WITH_NOTES
unresolved_blockers=0

# REVIEW-FIX-334-CODE-R0 — FIX-334 / FIX-335 代码审查（round 0）

| 项 | 值 |
|---|---|
| 审查结论 | **APPROVED_WITH_NOTES** |
| `unresolved_blockers` | **0**（独立结构字段；无未解决 BLOCKING finding） |
| round | R0（本报告为 FIX-334 / FIX-335 的首轮审查，无前轮） |
| 审查对象 | 未提交工作树（已 staged，工作树 == 索引），对照 HEAD `22cf185982f949839776811d096e70d48beb884f` |
| 代码面 | `skills/software-project-governance/infra/tests/test_dsh_doctor.py`（+65/−1）、`.../tests/test_archguard_ratchet.py`（+42/−2） |
| 文档面（次要，仅核事实性） | `README.md`（+4）、`project/CHANGELOG.md`（+2）、`docs/release/release-checklist-0.81.0.md`（+42/−6）、`docs/release/rollback-plan-0.81.0.md`（+24/−7） |
| 发现计数 | P0 = 0 · P1 = 0 · **P2 = 1** · P3 = 6 |
| Reviewer | Code Reviewer Agent（只读审查；唯一写入 = 本报告） |

**结论理由（一句话）**：两处「版本钉腐朽」修复均**真正消除腐朽且未弱化断言**（派生 + 反相敏感、原断言逐字保留、边界与 fail-closed 均成立），硬门槛五项全过；唯一的 P2 是**发布文档滞后于同批代码修复**（Gate 10 明细段仍把已由 FIX-335 修绿的两例登记为候选侧失败），按 code-review 分级为非阻塞项并转出 Release Reviewer。

---

## 0. 独立复现声明（我亲自做了什么）

| 我亲自执行/核对 | 结果 |
|---|---|
| 读全部 diff（`git diff HEAD`，两个测试文件 + README/CHANGELOG + 两份 release 文档） | 逐行读，见 §2~§6 |
| 实跑 `test_dsh_doctor`（`$tmpHome` 重定向 `DSH_HOME`，两次：dotted 模块名 + discover） | **Ran 86 tests, OK**（39.365s / 36.975s，两次同值，skip=0） |
| 实跑 `test_archguard_ratchet`（同隔离口径） | **Ran 38 tests, OK**（115.027s） |
| 实跑 `verify_workflow.py archguard-ratchet` | **PASS**：R1 24412 ≤ anchor 24412 / R2 47 ≤ 47 / R5 84-84 + 71-71 / R7 `deterministic=True; committed==fresh True` / `0 violations` |
| 实跑 `verify_workflow.py check-dsh-boundary` | **PASS 0 failing criterion**：K-2 契约外字面量 0（**11** declared consumers）/ K-8 26 claims·14 strong·**55** test files·71 segments·84 keys / K-7 NOT_RUN |
| 只读内存探针（`python -`，不落盘） | 渲染 16796 bytes / sha256 `6caf90fe…e55d`；`（v0.81.0）` 在渲染中出现 **1** 次；把该行回退为 `v0.80.0` 后 sha256 **逐字节 == `00e0d330…3723`**；派生断言在该变异下为 **False**；fuse 边界三例（0.81.0 / 0.9.9 / 1.0.9）派生值均 NOT expired、`expire==version` 均 expired=True；prerelease `0.81.0-rc1` → `_parse_semver=None` |
| `git rev-list --count` | `d87ead8..3074120` = **31** / `d87ead8..a89341e` = **33** / `d87ead8..22cf185` = **34**（与文档逐值一致） |
| 残留变异核查 | `git status --porcelain` 仅 7 条预期路径、零 untracked；`SKILL.md` 不在 diff 内；`test_dsh_doctor.py` 已无任何 ≥32 位 hex 字面量；`.governance/` 为 gitignored（`.gitignore:10`） |
| 我 **未** 能验证的 | ① 两位开发者声称的 `%TEMP%` 副本反相实验已删除、不可复检（见 §4.3，改以源码 + 内存探针 + 仓内零残留三条间接证据裁决）；② rollback-plan §4/§4.1 的两次 `git revert` 干跑（需建隔离 worktree + 写操作，超出本审查只读红线）→ 标「未验证」，转 Release Reviewer；③ 2026-09-13 的全量取数树（`38F/2E`）已不存在，无法对帐（见 §6.3） |

**红线合规**：全程未使用 Write/Edit 修改任何被审文件；未执行 `git add/commit/restore/reset/checkout/stash`、未使用 `git worktree`；隔离变量名一律 `$tmpHome`（**未出现 `$home`**）；`DSH_HOME` 每条命令均重定向到 `%TEMP%` 新建目录并在输出首行打印；未 stat/读写用户真实 `~/.dsh`。

---

## 1. 命令上报（逐条：命令 / 退出码 / 摘要）

| # | 命令（`<r>` = `D:/AI/agent/claude/coding/project_management_workflow`） | 退出码 | 摘要 |
|---|---|---|---|
| 1 | `git -C <r> diff --stat` | 0 | **空输出**——改动已 staged，故改用 `git diff HEAD`（如实记录，非失败） |
| 2 | `git -C <r> rev-parse HEAD` + `status --porcelain` | 0 | HEAD = `22cf185982f949839776811d096e70d48beb884f`；7 条已 staged 路径、**零** untracked |
| 3 | `git -C <r> diff HEAD --stat` | 0 | 7 files changed, 478 insertions(+), 16 deletions(-) |
| 4 | `git -C <r> diff HEAD -- skills/.../tests/test_dsh_doctor.py` | 0 | +65/−1；新增 docstring + `assertTrue(rendered)` + parity 子进程 + 派生断言 |
| 5 | `git -C <r> diff HEAD -- skills/.../tests/test_archguard_ratchet.py` | 0 | +42/−2；新增 `import extract_skill_version` + `ExemptionMechanismTests` docstring + `_not_yet_expired_version()` + 两处 fixture 改派生 |
| 6 | `git -C <r> diff HEAD -- README.md project/CHANGELOG.md` | 0 | README 两处 B-2 写入守卫限定；CHANGELOG 新增 `**Breaking changes：无**` + B-1/B-2 升级须知块 |
| 7 | `git -C <r> diff HEAD -- docs/release/release-checklist-0.81.0.md docs/release/rollback-plan-0.81.0.md` | 0 | Gate 6/7 复跑回填、Gate 10 归因更正 + 新增「Gate 10 明细」段、Gate 13/14 更正、rollback §4/§4.1 干跑记录 |
| 8 | `$env:DSH_HOME=<%TEMP% 新目录>; python -m unittest skills.software-project-governance.infra.tests.test_dsh_doctor` | 0 | **Ran 86 tests in 36.975s — OK**（任务书给定的原命令，实测可用） |
| 9 | `$env:DSH_HOME=<%TEMP% 新目录>; python -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_doctor.py -t .` | 0 | **Ran 86 tests in 39.365s — OK**（与 #8 一致；`dsh-doctor refused: --rehearse requires --against` 为该套件既有预期输出） |
| 10 | 同上 `-p test_archguard_ratchet.py` | 0 | **Ran 38 tests in 115.027s — OK** |
| 11 | `python -`（stdin 内存探针，见 §0；`DSH_HOME=%TEMP%`） | 0 | 渲染 16796B / `6caf90fe…e55d`；回退 persona 行 ⇒ sha256 == `00e0d330…3723`；派生断言在该变异下 False；fuse 边界三例正确 |
| 12 | `$env:DSH_HOME=<%TEMP%>; python .../verify_workflow.py check-dsh-boundary` | 0 | `Result: PASS — 0 failing criterion(a)`；K-2 `0 (11 declared consumer(s) scanned)`；K-8 `(55 test file(s), 71 segment(s), 84 command key(s))` |
| 13 | `$env:DSH_HOME=<%TEMP%>; python .../verify_workflow.py archguard-ratchet` | 0 | `Result: PASS (0 violations; ...)`；R1 24412≤24412 / R5 84-84+71-71 / R7 `deterministic=True; committed==fresh True` |
| 14 | `git -C <r> log --oneline -8` / `log -1 -- <template>` / `rev-list --count ×3` | 0 | 模板版本行由 `a89341e`（0.81.0 候选打包）投影；计数 31/33/34 与文档一致 |
| 15 | `git -C <r> check-ignore -v .governance/plan-tracker.md` + `ls-files .governance` | 0 | `.gitignore:10:.governance/`；tracked 计数 0 ⇒ `git worktree` 无活体治理数据，佐证 pristine 差异解释 |
| 16 | `git show 5e6d8c7:...SKILL.md` / 模板 / 测试文件 | 0 | 5e6d8c7：`version: 0.80.0`、persona 行 `（v0.80.0）`、测试仍含 `00e0d330…` 旧字面量 ⇒ 确为 «bump 前» 树 |
| 17 | `git log --grep=FIX-256/272/253` + `grep .governance`（FIX-334/335 登记） | 0 | FIX-253/FIX-256/FIX-272 先例确认；EVD-1036/1037、`fix335-packet.json`、incidents 记录存在 |
| 18 | `Select-String`（release 文档行号定位） | 0 | Gate 10 明细段：L100/101（双树取数）、L110/111（#4/#5）、L126/127（结论）；rollback §4 L78 / §4.1 L80 |

---

## 2. 维度 1 —— 正确性

### 2.1 `test_dsh_doctor.test_the_python_render_is_the_launchers_own_output`（L626-696）

| 检查项 | 裁决 | 事实依据 |
|---|---|---|
| 不可满足性是否消除 | ✅ 消除 | 旧断言的不可满足性来自**两条树属性轴**：persona 版本行（`agent-presets/governance/agent.cordis.yml.template:51`，由 `a89341e` 投影为 `（v0.81.0）`）与渲染代入的**绝对包路径**（`launch.py:467-470` 把 `__GOVERNANCE_REPO_ROOT__` 替换为 `str(path.resolve())`）。新断言为 (a) 同树 parity 的 sha256 相等、(b) `assertIn(f"（v{version}）", rendered)` —— 两者皆不引用字面量、不引用检出路径，故对任意版本 / 任意路径可满足（我在当前树实测绿：86 OK）。 |
| `assertTrue(rendered)` 是否覆盖「拒渲染返回空串」 | ✅ 覆盖 | `launch.py:441-473`：模板缺失/不可解码 ⇒ `return ""`（L463/465），残留 `__…__` token ⇒ `return ""`（L471-472）。L664 的 `assertTrue(rendered, …)` 在任何比对**之前**执行 ⇒ 空渲染必失败；且空渲染下的 parity 会被 sha256 不等二次捕获。我的探针实测 `render_composition()` 非空（16796 B）。 |
| parity 是否真是「另一条交付路径」 | ✅ 是（真子进程），捕获面收窄见 P3-3 | L669-682：`subprocess.run([sys.executable, "-c", script, str(launcher)], …, cwd=_PACKAGE_ROOT, env={**os.environ, "DSH_HOME": str(self.clean_home())})` —— **新解释器**、`importlib.util.spec_from_file_location` **从磁盘重读同一 `launch.py`**、独立模块对象；不是「同进程同对象渲染两次」。我实测 `_python_render` 本身即按路径 import 该 launcher（`dsh_doctor.py:916-931`），故 parity 实际捕获的是「进程级不确定性」+「`_python_render` 若改走其他渲染器且字节不同」。 |
| 是否存在自证式断言（零捕获力） | ⚠️ 非零捕获力，但**不是**字面量级的字节钉 | 见 P3-3 的边界陈述：parity 两侧执行同一函数，故「字节等价的重新实现」不会被捕获；这是**有意的**捕获面收窄（字面量恰是腐朽之源），且用例名声称的 delegation 另有实现事实支撑（`dsh_doctor.py:916-931` 注释与代码：import by path → `module.render_composition()`）。 |
| 派生断言的捕获力（反相实证） | ✅ 敏感 | 我在内存中把渲染文本的**唯一 1 处** `（v0.81.0）` 回退为 `（v0.80.0）`：`（v0.81.0） in mut == False` ⇒ L694-696 必红。即"投影滞后于 SKILL.md"会被此断言捕获。 |
| 子进程调用参数正确性 / 真实性 | ✅ | `text=True + encoding + errors` 组合经实跑无异常；`assertEqual(proc.returncode, 0, proc.stderr)` 在子进程失败时给出 stderr（可诊断）；`timeout=120` 有界。 |

### 2.2 `test_archguard_ratchet.ExemptionMechanismTests`（L359-419）

| 检查项 | 裁决 | 事实依据 |
|---|---|---|
| 原断言是否**逐字**保留（语义未弱化） | ✅ 原样 | L407-408 `self.assertEqual(effective, [])` + `self.assertTrue(disclosures)`；L418-419 `self.assertEqual(len(effective), 1)` + `self.assertIn("OVER-ALLOWANCE", effective[0]["exemption"])`。diff 中这四行为**上下文字段**（未改动），我另读工作树原文确认，**没有**把 `assertEqual(effective, [])` 换成弱断言。 |
| `_not_yet_expired_version()` 在任何版本下是否严格大于当前版本 | ✅ 成立（含 `x.y.9` 边界） | L383-396：`extract_skill_version` → `assertRegex(r"^\d+\.\d+\.\d+$")` → `patch+1` → `assertGreater(tuple(derived), tuple(current))`。关键在**判据侧**：`_parse_semver` 返回 `Tuple[int,int,int]`（`archguard_ratchet.py:173-182`），`_entry_expired` 用 `version >= expire` 的**元组比较**（L665-678）——故 `0.9.10 > 0.9.9` 数值成立。我的探针实测：`0.81.0→0.81.1`、`0.9.9→0.9.10`、`1.0.9→1.0.10` 三例 `expired_at_derived` 全为 **False**；`expire == version` 为 **True**（这正是 FIX-335 修前 `EXPIRED:0.81.0` 的成因）。**若判据改用字符串比较，`x.y.9` 会翻车——此处不存在该缺陷。** |
| prerelease / 非规范版本形态 | ✅ fail-closed（已披露，见 P3-6） | prerelease 当前版本 ⇒ `extract_skill_version` 正则失配返回 `""` ⇒ `assertRegex` 报错（测试**红**，不静默）；`_parse_semver("0.81.0-rc1")` = `None` ⇒ 产品侧判「不可读、全豁免 ACTIVE + disclosed」。与 `VERSIONING.md:1-7`「不需要预发布标签」一致。 |
| `assertRegex` fail-closed 是否有效 | ✅ 有效 | 正则锚定 `^\d+\.\d+\.\d+$` 且 `extract_skill_version` 只在 `^version: X.Y.Z$` 时返回非空（`checks/version.py:20-22`）⇒ 解析失败必报错，无「空串静默通过」路径（空串会先被 `assertRegex` 拒绝）。 |
| bump 反相红是否成立（语义是否恒真） | ✅ 非恒真 | 「未来版本越过分派生 fuse」时：`version == expire` ⇒ `_entry_expired=True` ⇒ `apply_exemptions` 把违例打上 `EXPIRED:<fuse>` 并保留（`archguard_ratchet.py:708-717`）⇒ `assertEqual(effective, [])` 必红。我以探针在判据函数上实证了该形态（`expire==version ⇒ True`）。**未**复跑「副本 bump 0.82.0」的原始实验（写操作越界），但结论由源码判据 + 探针两点支撑。 |
| 同一文件是否还有同族残留 | ⚠️ 1 处（**当前惰性**，见 P3-1） | `test_archguard_ratchet.py:457` 仍钉 `expire_version: "0.81.0"`（`test_authored_zone_survives_regen`）。该路径**不判到期**：`build_baseline` 把 `exemptions` 原样携带（`archguard_ratchet.py:874`），该用例只断言 `len(rebuilt["exemptions"]) == 2`（L459）。另 L425 `"0.78.1"` 是**有意**的「已到期」fixture（版本单调递增 ⇒ 不会腐朽）。全测试目录 `expire_version` 字面量仅此 2 处。 |

---

## 3. 维度 2 —— 安全性

| 检查项 | 裁决 | 依据 |
|---|---|---|
| 隔离（真实环境防护） | ✅ 合规 | 新 parity 子进程显式注入 `DSH_HOME = str(self.clean_home())`（`%TEMP%` 新建的 `.dsh`，`test_dsh_doctor.py:90-96, 681`），且 `launch.py` 的 `ROOT = Path(__file__).resolve().parents[2]`（L81）——渲染只依赖被测树，不依赖环境变量；`launch.py` 模块级仅有常量定义（L69-119），无 import 期读写（契约惰性读取，注释明示 L95-97）⇒ 子进程「只 import + render，不 install、不写」。 |
| 是否可能写到仓内/真实环境 | ✅ 无 | parity 子进程只 `sys.stdout.write(<hexdigest>)`；`rendered` 全程在内存；`clean_home()` 建在 `%TEMP%`。我实测后 `git status --porcelain` 仍只有 7 条预期路径、零 untracked（`__pycache__` 已被 `.gitignore:13` 忽略）。 |
| 注入 / 命令构造 | ✅ 无风险 | 子进程 argv 为固定脚本 + `str(launcher)`（`Path`，非 shell）；无 `shell=True`；`-c` 脚本不含外部插值。 |
| 敏感数据 | ✅ | 新增代码无密钥/token/凭据；渲染内容由契约 token 表决定。 |
| 权限/对外副作用 | ✅ | 两处修复均为测试面，无产品代码改动（`git diff` 中无 `dsh_doctor.py` / `archguard_ratchet.py` / `launch.py`）。 |

---

## 4. 维度 3 —— 可维护性 + 反相红绿证据可信性

### 4.1 命名 / 注释 / 重复代码

| 检查项 | 裁决 | 依据 |
|---|---|---|
| 命名可读 | ✅ | `_not_yet_expired_version` 直述语义；docstring 明示「fuse strictly ABOVE the shipped version」。 |
| 函数长度 | ✅ | 新增 helper 12 行（L383-396）；新测试体 69 行（含 30 行 docstring），无超长函数。 |
| 重复代码 | ✅ 受控 | 派生逻辑复用既有 `checks.version.extract_skill_version`（与 `test_dsh_adapter.py:732-738`、`test_change_triage.py:800-803`、`test_verify_workflow.py:14687-14692` 同形），未新增第二实现；两处 fixture 用同一 helper（无复制粘贴的第二种派生）。 |
| 注释与实现一致 | ✅ | `test_dsh_doctor.py:627-656` 的三条声明与实现逐条对应（parity L669-687 / derivation L689-696 / refused-render L663-664）；`test_archguard_ratchet.py:360-379` 的「第 4 例」叙述与 `plan-tracker:103`、`EVD-1037` 一致。 |

### 4.2 设计一致性（是否与先例同形；是否唯一事实源）

| 检查项 | 裁决 | 依据 |
|---|---|---|
| 与 FIX-253 / FIX-256 / FIX-272 同形 | ✅ | FIX-253：`test_dsh_adapter.py:725-738`「从 SKILL frontmatter 派生替代硬编码字面量 + truthiness guard」；FIX-256：同型（`git log --grep=FIX-256` 的提交说明「precedent-isomorphic with truthiness guard」）；FIX-272：preset persona 版本行的 `@version-line` 动态锚 + 权威版本 fail-closed。新代码是同一形态的第 3/4 例，且 `test_dsh_doctor.py:690` 显式标注 FIX-253 先例。 |
| `extract_skill_version` 是否唯一事实源 | ✅ 事实源唯一（解析器见 P3-2） | 事实源 = `SKILL.md` frontmatter（DEC-096，`checks/version.py:9-22` 标注为 "source of truth"）；本批**未**引入第二个事实源（未读 `package.json`/plugin.json 作为新断言基准）。被审测试与产品判据都只读该文件。 |
| 是否与 Check 40 / injection-contract 锚重复 | ✅ 互补，无冲突 | `check-injection-contract` 守护**模板文件**的版本锚（FIX-272），新断言守护**渲染产物**的版本行（`assertIn`），层级不同。 |
| 改动的纯粹性（D4） | ✅ | 两个测试文件均只做「钉 → 派生」一件事；无顺手重构、无格式噪声（diff 全文可读）。 |

### 4.3 反相红绿证据的可信性 + 副本实验是否污染仓内

| 问题 | 裁决 | 事实依据 |
|---|---|---|
| 双方自述的反相是否足以证明断言非恒真 | ✅ 充分（就本批两处而言） | ① **F-01 反相**（改模板版本行/契约 token ⇒ 红）：我**独立复现**了机制——把渲染文本的 persona 行回退一版，sha256 恰为旧钉值 `00e0d330…3723`，派生断言为 False ⇒ 版本行/契约 token 一变即红，且旧钉值只在 «0.80.0 版本 + 原检出路径» 可满足。② **FIX-335 反相**（fuse 到/过派生值 ⇒ 红）：判据源码 + 探针实证 `version >= expire` 行为，且「修前 `EXPIRED:0.81.0` 2 failures」与 plan-tracker/EVD-1037 一致。③ 两者都不是「恒真断言」：F-01 的派生断言在**版本行回退**下红；FIX-335 的两例在**版本越过 fuse** 时红。 |
| 副本实验是否改到了仓内文件 | ✅ 未发现污染 | `git diff HEAD` 只含 7 条预期路径；两文件工作树 == 索引（status 无 `MM`）；`SKILL.md` **不在** diff（⇒ 0.82.0 副本 bump 未污染权威源）；`test_dsh_doctor.py` 中已无任何 ≥32 位 hex 字面量（旧钉值仅以 `00e0d330…3723` 省略号形式出现在 L631 docstring，**非断言**）；`test_archguard_ratchet.py` 内 `0.81.0` 仅出现在 docstring（L371-372）与惰性 fixture（L457，见 P3-1）；模板 persona 行为正确的 `（v0.81.0）`。 |
| 副本实验证据的存续性 | ⚠️ 不可复检（已登记） | 声称的 `%TEMP%` 副本已删除，无法重跑比对其原始输出；且 FIX-335 的**首次**隔离命令存在 `$home` 变量名冲突导致 `DSH_HOME` 落到 `C:\Users\peter`（`.governance/incidents/incident-20260914-fix335-dshhome-redirect-failure.md`，已按 M7.7 违规窗口登记、FIX-337 待执行）。该次事故的后续命令已改用 `$tmpHome` 且逐条打印重定向。**结论**：该次事件的输出不宜作为真实环境证据，但本报告 §2.2 的裁决不依赖它（依赖源码判据 + 我的独立探针 + 我的模块级实跑）。 |

---

## 5. 维度 4 —— 性能

| 检查项 | 裁决 | 依据 |
|---|---|---|
| 算法复杂度 | ✅ | 新增逻辑为 O(1) 版本解析 + 一次哈希比较。 |
| 新增 I/O 开销 | ✅ 可接受 | parity 新增 1 次解释器启动 + 1 次模板读；`test_dsh_doctor` 整模块 **39.4s**（含 doctor 全量 S0–S7 与演练用例），增量与既有 `CliGateTests`（`test_archguard_ratchet.py:465-472`，同型子进程）量级一致。 |
| 不必要循环 / N+1 | ✅ 无 | 无循环内 I/O。 |
| 超时与资源释放 | ✅ | 子进程 `timeout=120`、`capture_output` 自动回收；`clean_home()` 注册 `addCleanup` 清理临时目录。 |

---

## 6. 维度 5 —— 测试覆盖

| 检查项 | 裁决 | 依据 |
|---|---|---|
| 核心路径有测试 | ✅ | `test_dsh_doctor` **86 OK**（我两次实跑）、`test_archguard_ratchet` **38 OK**；`archguard-ratchet` 门禁 **PASS**（我复跑）。 |
| 边界测试 | ✅ | 版本边界（`x.y.9` 型）经判据层探针覆盖；空渲染边界由 `assertTrue` + sha256 双重覆盖；fuse「未到期/已到期」两侧分别由 L398-408 / L421-429 覆盖。 |
| 错误路径测试 | ✅ | 模板缺失 ⇒ FAIL（`test_dsh_doctor.py:698-719`）；版本不可解析 ⇒ `assertRegex` fail-closed；`_entry_expired` 对不可解析 `expire_version` 永不到期（探针实测）。 |
| 覆盖率是否下降 | ✅ 未下降 | 断言**未**被削弱（§2.2 逐字核对）；唯一「减少」的是对**字面量字节**的钉死，属腐朽源，非有效覆盖。 |
| 术语诚实性（70 → 86） | ✅ 已核实 | 文档把「70 OK」更正为「86 OK」：我实跑两次均 **Ran 86 tests OK**（旧值 70 见 `git log 210b200` 的 M-2 回填，属 V8 期陈旧计数）⇒ 更正正确。 |

### 6.1 发布文档事实性抽查（次要面，仅核事实性）

| 文档项 | 文档值 | 我的实测/核对 | 裁决 |
|---|---|---|---|
| Gate 6（`release-checklist-0.81.0.md` 第 6 行） | R1 24412 ≤ anchor 24412；R5 84/84 + 71/71；R7 `deterministic=True; committed==fresh True` | 复跑逐值相同，`Result: PASS (0 violations; raw findings 0)` | ✅ 口径一致 |
| Gate 7（同文件第 7 行） | K-2「契约外字面量 0，扫 **11** 个声明消费方」；K-8「**55** 测试文件 / 71 段 / 84 命令键」；K-7 `NOT_RUN` | 复跑：`K-2: 0 (11 declared consumer(s) scanned)`；`K-8: 26 coverage claim(s) … (55 test file(s), 71 segment(s), 84 command key(s))`；K-7 NOT_RUN；`0 failing` | ✅ 口径一致（原「8 / 54」的更正方向正确） |
| Gate 11（同文件第 11 行） | `6caf90fe…e55d`（16796 bytes）；「唯一 1 处 `v0.81.0` 回退 ⇒ 逐字节等于 `00e0d330…3723`」 | 探针：16796 B / `6caf90fe…e55d`；回退后 sha256 **完全相等** | ✅ 独立复现 |
| Gate 10 双树数字（L100/L101） | 候选 `Ran 2983 / 36F 2E 1S`（808.063s）；pristine `@5e6d8c7` `Ran 2983 / 28F 9E 4S`（729.480s） | 与 Coordinator 已知事实一致；pristine 解释链核实：`.governance/` gitignored（`.gitignore:10`）⇒ worktree 无活体数据 ⇒ skipped 4 与候选侧活体用例缺席成立；5e6d8c7 实测为 «bump 前» 树（`version: 0.80.0`） | ✅ 口径一致（内部差额见 P3-4、标签见 P3-5） |
| Gate 13 | 明写 `Result: FAILED - 7 issue(s)`，逐项归因既有基线 | 未复跑（release 门禁属 Release Reviewer/发布期）；**未见把 FAIL 写成 PASS** | ✅ 未overclaim（未复跑部分标「未验证」） |
| Gate 14 / rollback §4 | 区间 `d87ead8..<发布 tip>`；计数 31 / 33 / 34；§4.1 两次干跑（候选点 0 冲突 80 路径 / tip 3 冲突） | `rev-list --count` 三值 **31 / 33 / 34 全部与文档一致**；干跑记录**未验证**（需建隔离 worktree + revert，越只读红线） | ✅ 计数一致；干跑标「未验证」转 Release Reviewer |
| CHANGELOG L37 | `**Breaking changes：无**` + B-1/B-2 升级须知 | 口径可追溯 `core/VERSIONING.md:11`（Breaking = MUST 规则删除/重命名、Gate 语义、governance 字段格式变更）；B-1 核实：`install_preset` 走严格 `package_version()`（`launch.py:687-691`）⇒ rc 1；B-2 核实：`write_side_refusal`（L851-874）+ `_refuse_write`（L913-918，`SMOKE_EXIT_REFUSED=2`）在 install（L655-657）/ uninstall（L779-781）接线，`--sync` 复用 install（L1751） | ✅ 两项行为变更已显式披露，无 breaking overclaim 也无 underclaim |
| README L85 / L419 | `--install/--sync/--uninstall` 在真实 home 形态下 `exit 2 + [REFUSED]`；未设/空串视为真实 home；`--dry-run` 放行 | 与 `write_side_refusal` docstring（L858-873：unset / blank / profile-unresolvable 三种形态 + 临时目录放行）逐条一致 | ✅ 事实一致 |

---

## 7. Findings（`文件:行号` + 级别 + 依据 + 影响 + 建议）

### P2-1（唯一 P2；非阻塞，转出）发布文档滞后于同批代码修复 —— Gate 10 明细段

- **位置**：`docs/release/release-checklist-0.81.0.md:110-111`（明细表 #4/#5「候选」列 = `1 块`）、`:126`（「**本版已修 1 项**」）、`:127`（「其修复需要改 `test_archguard_ratchet.py`（超出 FIX-334 允许改动面），建议登记独立 FIX」）
- **事实依据**：① 同批工作树**已**含 FIX-335（`test_archguard_ratchet.py` +42/−2，本报告 §2.2 审查通过）；② 我实跑 `test_archguard_ratchet` = **Ran 38 tests OK**，两例由 `EXPIRED:0.81.0` 转绿；③ 同批 `plan-tracker.md:103` 亦记 FIX-335「修复 = 从权威源派生」，即 :127 建议的「独立 FIX」已在本批交付。
- **影响**：该 checklist 与本批代码同批提交时，读者/M-2/M-4 复核者会认为「候选树仍存在 2 处候选侧失败且尚未修复」，与树矛盾；同时「本版已修 1 项」少算 1 项。属**低估/滞后**（非 FAIL→PASS 方向的 overclaim），不构成发布阻塞，但会污染门禁结论口径。
- **建议**：同批把 :110-111 的候选列改为「**已修（FIX-335，不再出现）**」、:126 改为「本版已修 2 项（F-01 + FIX-335 第 4 例）」、:127 改为「已由 FIX-335 处置」；或（若刻意保留 FIX-335 之前的取数快照）显式标注「该表为 FIX-335 落地前的取数，终值由 M-2 末次复跑回填」。**处置责任 = Release Reviewer / Coordinator**（发布文档面不在 Code Reviewer 修改权限内）。

### P3-1 同族惰性字面量残留：`test_archguard_ratchet.py:457`

- **依据**：`test_authored_zone_survives_regen` 的 fixture 仍钉 `"expire_version": "0.81.0"`（== 当前版本）；但该用例只调 `ar.build_baseline`（`archguard_ratchet.py:785-875`，其中 L874 `exemptions` 原样携带、**不判到期**），断言仅 `len(rebuilt["exemptions"]) == 2`（L459）⇒ 当前**不会**腐朽（我实跑 38 OK 佐证）。
- **影响**：若未来 `build_baseline` 引入「到期剪枝」（与 `run_check` L962/971 的到期过滤语义对齐），该 fixture 会立刻复活为「候选侧必然失败」的同类缺陷。
- **建议**：改用 `self._not_yet_expired_version()`，或就地加一行注释声明「此值不参与到期判定（carryover probe only）」。**不阻塞合并。**

### P3-2 派生 helper 与被测产品用了同一事实源的两个解析器

- **依据**：测试派生用 `checks.version.extract_skill_version`（`test_archguard_ratchet.py:36, 390`），而被测产品 `ar.apply_exemptions` 用 `ar.read_skill_version`（`archguard_ratchet.py:185-202, 689`）。两者读同一 `SKILL.md` frontmatter，但解析实现不同（正则 `^version: X.Y.Z$` vs frontmatter 作用域 `startswith("version:")`）。
- **影响**：极端写法下（如 `version: 0.81.0 # note`）解析结果可分歧；但**双向 fail-closed**——测试侧 `assertRegex` 直接报错，产品侧判 unreadable 并 `disclosed`（L691-698）后按 ACTIVE 处理，**不存在静默通过**。事实源仍唯一（P3-2 是解析器重复，非事实源重复）。
- **建议**：可选把派生改为 `ar.read_skill_version(_SKILL_ROOT)`（与被测判据同源），或在 helper docstring 注明「故意使用 checks.version 以与 FIX-253/FIX-256 先例同形」。**不阻塞。**

### P3-3 parity 断言的捕获力边界（登记，非缺陷）

- **依据**：`test_dsh_doctor.py:669-687` 的「另一条路径」= 新解释器 + 磁盘重读同一 `launch.py` + 独立模块对象（✅ 非同一对象自证），但两侧执行**同一文件同一函数**；子进程 `cwd` 与父进程同为 `_PACKAGE_ROOT`。
- **影响**：「字节等价的重新实现」（若 `_python_render` 改成自己实现渲染器且恰好逐字节相同）与「依赖 cwd 的渲染变化」不会被 parity 捕获；而版本跟踪轴由派生断言（L689-696）独立守住。整体仍为**非零捕获力**，且这是消除字面量腐朽的**有意代价**。
- **建议**：无动作；后续若需强化 delegation 机检，可在 `_python_render` 层加结构性断言（会引入结构耦合，需权衡）。

### P3-4 Gate 10 两次候选态取数未对帐（差额 2 vs 已列修复 1）

- **依据**：`release-checklist-0.81.0.md:88`（2026-09-13 候选态 `failures=38, errors=2`）vs `:100`（2026-09-14 候选态 `failures=36, errors=2`）——差 2；同文件 :113 说明候选侧重取的**新增/修复**仅有 #13 doctor 渲染 1 项（`已修（不再出现）`），#4/#5 在两次取数中均记为失败。
- **影响**：读者无法从文档复原 −2 的构成。活体耦合可解释其一（#2/#3 读活体 `.governance/` 文件，而 Gate 13 自述活体面在同一窗口推进了 88→96 issues；archive migrate 亦改了活体数据），但文档未写明。
- **建议**：补一句「两次取数非块对块可比（活体治理数据面在窗口内变动，逐项见 #2/#3）」或列出差额项。**转 Release Reviewer。**

### P3-5 pristine 基线标签精度：`5e6d8c7（= v0.80.0 线）`

- **依据**：`release-checklist-0.81.0.md:101` 把 `5e6d8c7` 标为「= v0.80.0 线」；我实测该提交 `SKILL.md: version: 0.80.0`、模板 persona 行 `（v0.80.0）`（确为 **bump 前**态），但其父提交 = V8 `3074120`，且同批 `rollback-plan-0.81.0.md:31` 明确「起点 `d87ead8` = 0.80.0 线 tip」⇒ 5e6d8c7 不是 0.80.0 线 tip，而是 0.81.0 线上的 prep 提交。
- **影响**：术语可能让复核者把「pristine」误读为「0.80.0 发布态」，进而误解差集含义（实为 «bump 前工作态 vs bump 后候选态»）。
- **建议**：改为「`@5e6d8c7`（bump 前的 0.80.0 版本态，含 V8；≠ 0.80.0 线 tip `d87ead8`）」。**低优先级。**

### P3-6 非规范版本下 helper 走 fail-closed 报错（已披露，登记）

- **依据**：`test_archguard_ratchet.py:391-392`；prerelease 版本 ⇒ `extract_skill_version` 返回 `""` ⇒ `assertRegex` 报错（模块变红而非静默）；产品侧同版本形态判「不可读 + ACTIVE + disclosed」。与 `core/VERSIONING.md:7`「不需要预发布标签」一致。
- **建议**：无动作；如未来引入 prerelease 版本策略，此处需同步（登记为口径依赖）。

### P3-7 新增「可启动第二解释器」硬依赖（无 skip 路径）

- **依据**：`test_dsh_doctor.py:677-682` 使用 `sys.executable`；无 `skipIf`/`skipUnless`。与既有先例同形（`test_archguard_ratchet.py:468-472` 的 `CliGateTests._run`、doctor 自身的 JS 渲染子进程）。
- **影响**：在禁止 spawn 子进程的受限环境该用例会红而非 skip；本机 86 用例 39.4s，成本可接受。
- **建议**：无动作（如未来 CI 出现受限 spawn 面，再按既有 skip 惯例处理）。

---

## 8. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ **无** | 本批新增代码零 `unittest.mock`；`test_archguard_ratchet.py:285` 的 `from unittest.mock import patch` 属既有 R7 用例，非本批改动（diff 未触及）。 |
| 2 | 硬编码返回值 | ✅ **无** | 新断言不含期望字面量：`assertTrue(rendered)` / sha256 相等 / `assertIn(f"（v{version}）")` / `patch+1` 派生。历史字面量仅出现在 docstring（`test_dsh_doctor.py:631` 带省略号）；`test_dsh_doctor.py` 全文已无 ≥32 位 hex 字面量（grep 零命中）。 |
| 3 | 幻觉 API | ✅ **无** | `assertRegex/assertGreater/assertIn/assertTrue` 签名正确；`subprocess.run(capture_output, text, encoding, errors, timeout, cwd, env)`、`importlib.util.spec_from_file_location/module_from_spec/exec_module` 均为真实 API 并经**实跑**验证；`checks.version.extract_skill_version` 确实存在（`checks/version.py:20`）且 `checks` 为真包（`__init__.py` 存在）。 |
| 4 | 未实现 TODO | ✅ **无** | 本批 diff 无 `TODO`/`FIXME`/`NotImplementedError`/占位 `pass`；两处修复均为完整实现 + 断言。 |
| 5 | 过度实现 | ✅ **判定为必要扩展**（非过度） | 69 行实现中 ~30 行为 docstring（本仓测试惯例：每例携带行为理由与缺陷溯源），功能内核 ~25 行 = 三条性质（非空渲染 / parity / 版本派生）逐条对应用例名所声称的 claim；无新增生产代码、无新增第三方依赖、无新增 skip、无顺手改动（D4 纯粹性成立）。相对 7 行旧实现，增长来自「一个断言拆成三条不可腐朽的断言」+ 证据说明，而非范围外功能。 |

---

## 9. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✅ 通过 |
| 5 维度全覆盖 | = 100% | 正确性 / 安全性 / 可维护性 / 性能 / 测试覆盖 五节均有逐项结论（§2~§6） | ✅ 通过 |
| 每条发现标注级别 | = 100% | P2×1 + P3×6，逐条带文件:行号 | ✅ 通过 |
| 设计一致性检查 | 已完成 | §4.2：与 FIX-253/FIX-256/FIX-272 同形、事实源唯一、无 ADR/契约偏离 | ✅ 通过 |
| AI 代码专项 5 项 | 全部完成 | §8 逐项结论 | ✅ 通过 |

**结论：`APPROVED_WITH_NOTES`，`unresolved_blockers=0`。** 代码面（FIX-334 F-01 + FIX-335 第 4 例）可合并：P0 = 0、P1 = 0，断言未弱化、腐朽已消除、反相可红、门禁复跑绿。唯一 P2 属发布文档滞后（§7 P2-1），按 code-review 分级为非阻塞项转出 Release Reviewer；P3 均为登记/可选优化。

---

## 10. 需 Coordinator 处置的转出项

| # | 转出项 | 建议处置 | 责任 |
|---|---|---|---|
| T-1 | §7 P2-1：`release-checklist-0.81.0.md:110-111 / :126 / :127` 仍把已由 FIX-335 修绿的两例登记为候选侧失败并建议「独立 FIX」 | 同批更新该表/结语为「FIX-335 已修」，或显式声明为 FIX-335 前的取数快照 | Release Reviewer / Coordinator |
| T-2 | §6.1：rollback-plan §4.1 的两次 `revert` 干跑（0 冲突 / 3 冲突）**未验证**（本审查只读红线内不可复跑） | 由 Release Reviewer 或 M-2/M-5 期在隔离 worktree 复跑留证 | Release Reviewer |
| T-3 | §7 P3-4：Gate 10 两次候选态取数差额（38→36 vs 已列 1 项修复）未对帐 | 补差额说明或标注「非块对块可比」 | Release Reviewer |
| T-4 | §7 P3-1：`test_archguard_ratchet.py:457` 同族惰性字面量 | 登记后续 FIX（或同批改派生 + 注释） | Coordinator（可并入 FIX-336/337 批次） |
| T-5 | 本次审查覆盖 **FIX-334 + FIX-335 两个 task**，报告只有 `REVIEW-FIX-334-CODE-R0` 一个 ID | 机器记录时：`REVIEW-FIX-334-CODE-R0 = APPROVED_WITH_NOTES / unresolved_blockers=0`；FIX-335 的 review 证据可引用本报告（若需独立 REVIEW 记录，请勿以本轮之外的轮次号回填） | Coordinator（review-record 机录） |
| T-6 | `.governance/incidents/incident-20260914-fix335-dshhome-redirect-failure.md` 记录的 M7.7 违规窗口（`$home` 保留变量致隔离静默失效） | 已由 FIX-337 登记；建议在 FIX-337 落地前，所有派发 prompt 的隔离命令统一使用 `$tmpHome` 并在执行当下逐条上报 | Coordinator |
