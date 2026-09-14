# Review — REVIEW-REL-077-RELEASE-R0（0.81.0 发布候选 · M-3 发布半面独立审查）

## 结论：**NEEDS_CHANGE**

- **round**：R0（Release 面首轮，无前轮；产品代码半面 R1 = `APPROVED_WITH_NOTES / unresolved_blockers=0`，测试面 R0 各为 `APPROVED_WITH_NOTES / unresolved_blockers=0`）
- **blocking**：**F-01（P1）×1** ⇒ 硬门槛「发布检查清单全部 PASS / 逐项有可复核证据」不成立
- **必修项**：4 项（F-01、F-02、F-03、F-04）+ 2 项文档一致性（F-05、F-06）——见 §7 与 §10
- **审查边界（事实依据红线）**：全程**只读**，未执行任何 python/gate/测试命令（只读 git + 只读文件/哈希读取）⇒ 凡依赖执行的门禁数值（`check-release` 13/13、ledger PASS、全量测试计数、28u/28v/28w、渲染 sha256 字节值、归档计数）均为**文档级事实，未独立复现**，已逐条标注（§8）。
- 返回 Coordinator 的结论与本首行**同一**：`NEEDS_CHANGE`

---

## 0. 审查对象

| 产物 | 路径 | 我的复核方式 |
|---|---|---|
| 发布检查清单 | `docs/release/release-checklist-0.81.0.md` | 14 行逐条裁决 + 占位扫描 + 与 EVD-1034 交叉比对 |
| Feature Flags | `docs/release/feature-flags-0.81.0.md` | 逐节 + 与 `adapters/dsh/launch.py` 代码面比对 |
| 回滚方案 | `docs/release/rollback-plan-0.81.0.md` | 区间端点/计数实测 + 步骤可执行性 + 自洽性 |
| CHANGELOG | `project/CHANGELOG.md`（`:5-37`） | 覆盖度 + breaking 范式比对（0.78.0/0.78.1/0.80.0） |
| 版本规划 | `docs/release/version-plan-0.81.0.md` | §2 semver 论证 + §4 门禁清单 + §5 入出槽 + §7/§8 |
| release manifest | `skills/software-project-governance/core/releases/0.81.0.json` | 键面 + `candidate_commit` 派生实测 |
| 真机验收规程 | `docs/release/real-machine-acceptance-0.81.0.md` | 措辞纪律 + 全库「真机」声明扫描 |
| 授权链 / 风险 | DEC-189~194 引用、`RISK-050`、`RISK-036` | `.governance/risk-log.md:39/:44` |
| 候选/门禁提交 | `a89341e` / `22cf185` / `3074120` / `61b571c` | `git show --stat` / `rev-list --count` / `log --reverse` |

---

## 1. 维度一：发布检查清单（逐项裁决）

### 1.1 M-2 表 14 项逐条裁决

| # | 文档结论 | 我的独立复核 | 裁决 |
|---|---|---|---|
| 1 | `check-version-consistency` PASSED + 1 WARN | **复现成立**：全部 tracked 版本声明面 = 0.81.0（4×plugin.json / marketplace / package.json / SKILL.md 根+e2e 镜像 / core/manifest.json / architecture-baseline.json / governance-init 标记面 / AGENTS.md / AGENTS.md.template / 4 hooks）；唯一 `"version": "0.80.0"` = 历史 `core/releases/0.80.0.json`（其自身记录，非声明面）。WARN 源 `plan-tracker.md:11` = `0.80.0` ✓；未跟踪 `CLAUDE.md` `@bootstrap-version: 0.80.0` 经 `git ls-files -- CLAUDE.md`（空）+ `git check-ignore -v` = `.gitignore:3:CLAUDE.md` 确认为 gitignored ⇒ 披露**准确** | **PASS**（措辞与事实一致） |
| 2 | `check-projection-sync` PASSED（15 mirrors） | 未执行；声明面交叉核验无残留旧版本 ⇒ 无矛盾 | 未复现（文档级） |
| 3 | `check-injection-contract` PASSED（3 files / 23 anchors） | 未执行；`INJECTION_CONTRACT_ANCHORS`（`verify_workflow.py:6614`）实存，锚点含 0.81.0 标记面 | 未复现（文档级） |
| 4 | `check-manifest-consistency` PASS（689 / 770） | 未执行 | 未复现（文档级） |
| 5 | `cleanup.py --dry-run` 零删除；exit=1 为正常终止码 | **复现成立**：`infra/cleanup.py:26 ERR_NOTHING_TO_CLEAN = 1` ⇒ exit=1 的重新解释**不是** FAIL→PASS 包装 | **PASS**（判据重解释合规） |
| 6 | `archguard-ratchet` 预检 PASSED + **残留占位** | **不满足**：行内值来自「V8 在制品状态」（`R1 24405`），而 EVD-1034（`evidence-log.md:2087`）的 M-2 值 = `R1 24412`；候选提交 `a89341e` **修改了** `core/architecture-baseline.json`（`git show --stat a89341e`）⇒ 锚点确实变了 ⇒ 见 **F-06** | **NEEDS_CHANGE（证据未回填）** |
| 7 | Check 28w 预检 PASSED + **残留占位** | 同上：行内 `K-8 54 测试文件` vs EVD-1034 `K-8 55` ⇒ 见 **F-06** | **NEEDS_CHANGE（证据未回填）** |
| 8 | 28u PASSED + flake 如实登记 | 未执行；登记方式（连续两次复跑 + 归因 + 不作缺陷）符合诚实披露要求 | 未复现（文档级，登记合规） |
| 9 | 28v PASSED（23/18/5 + writes 0） | 未执行 | 未复现（文档级） |
| 10 | 零产品代码回归 + 既有失败基线 3 条 | **部分不成立**：归因①「真回归→FIX-328/330」与②「版本钉过期经证伪」机制自洽，但归因③把 `test_the_python_render_is_the_launchers_own_output` 判为「**pristine 侧**失败」与版本事实**正好相反** ⇒ **F-01（blocking）**；且 R0 F-04 要求的「重取全量原始失败清单并逐条贴出」被声明已履行却不存在 ⇒ **F-02** | **NEEDS_CHANGE** |
| 11 | 三路径渲染 parity `6caf90fe…e55d`（16796 bytes） | 结构性支撑复现成立（`agent-presets/` 仅 2 文件，唯一版本字面量 = `agent.cordis.yml.template:51`）；字节值与「仅 1 处差异」的字节级结论未复现（需执行渲染） | 未复现（结构支撑强） |
| 12 | 契约 SHA `96F92485…43FC6E` 未变 | **逐位复现成立**：`Get-FileHash host-contract.json` = `96F9248579FCE72592C000D410C0466CBB035D7C7E8D5885941FB6434643FC6E`，`74702` bytes | **PASS** |
| 13 | `check-release` 静态 13/13 PASS；执行面 3 项 FAIL 全为既有基线 | 未执行；`Result: FAILED — 6 issue(s)` 被如实写出（未包装成 PASS）；但执行面 3 项的「既有」定性中，`unit tests` 属**确定性预算口径**（见 F-07），且同批 Gate 10 存在反向归因（F-01）⇒ 定性「全为既有基线」力度不足 | 部分成立（含 F-07） |
| 14 | 回滚区间 = 整个 0.81.0 窗口 | 区间**端点正确、计数错误**，且终点非发布 tip、无演练记录 ⇒ **F-03 / F-04** | **NEEDS_CHANGE（计数+终点）** |

### 1.2 占位扫描（`⟦…⟧`）

全仓 `docs/release/` 扫描：4 处命中——两处在 **Gate 表**（`:84` Gate 6、`:85` Gate 7，形如 `⟦M-2 需在全部切片落地后重跑⟧`），一处为真机回贴面（`:97` `⟦待用户回贴⟧`，**允许**），一处为冻结纪律引文（`:117`，**允许**）。
⇒ **残留占位超出「仅真机回贴面」允许范围**（F-06）。

### 1.3 Gate 10 失败分类自洽性

- ①（真回归 → FIX-328/FIX-330）与 ②（「版本钉过期」归因证伪）**机制描述自洽**，且 ② 的证伪方向与「二者从动态锚派生」一致；
- ③ **不自洽**：`docs/release/release-checklist-0.81.0.md:88` 把 `test_the_python_render_is_the_launchers_own_output` 的失败归到 **pristine 侧**，而该测试的硬钉是 **0.80.0 时代的哈希**（见 F-01 的 4 条实测证据链）⇒ 候选树上不可满足、pristine 树上可满足，**归因方向反了**。这是「把未披露的候选态失败说成基线噪声」的事实错误，不是措辞问题。

### 1.4 「FAIL 包装成 PASS」检查

- Gate 5（exit=1 → 零删除判据）**合规**（代码常量实证）。
- Gate 12（契约 SHA）**逐位相符**。
- Gate 13 写出了 `Result: FAILED — 6 issue(s)` 与 3 项执行面 FAIL，**未**包装为 PASS。
- 唯一实质问题 = Gate 10 的**反向归因**（F-01）与 Gate 6/7 的**未回填**（F-06）。

### 1.5 Change Inventory 校验（我做过的最强核查）

| 核查 | 结果 |
|---|---|
| `git rev-list --count d87ead8..3074120` | **31** ✓（与文档一致） |
| `git rev-list --count 71f73eb..3074120` | **32** ✓ |
| 表内 31 个 commit hash vs `git log --reverse --format=%h d87ead8..3074120` | **31/31 全等、0 处不一致**、编号 1..31 连续无重复 ✓ |
| 窗口首/末 | `4d93b24`（#1）/ `3074120`（#31）✓ |
| `d87ead8` 语义 | `v0.80.0^{commit}` = `71f73eb`；`merge-base --is-ancestor 71f73eb d87ead8` = 真，反向 = 假 ⇒ `d87ead8` = 0.80.0 线 tip（post-tag 记账提交）⇒ 区间起点选择**正确**（不误吃 0.80.0 内容） |
| `git rev-list --count d87ead8..a89341e` | **33**（= 31 + `5e6d8c7` + `a89341e`）⇒ Gate 14/回滚方案写的「31 + 该冻结提交」**少 1**（F-03） |
| `5e6d8c7`（M-1 冻结推进） | 在回滚区间内但未被 Change Inventory 计入（口径选择，需在 Gate 14 说明） |

---

## 2. 维度二：回滚方案可执行性

| 检查项 | 结论 |
|---|---|
| 区间是否 = **整个** 0.81.0 窗口 | **是**（`d87ead8..a89341e`，33 提交，覆盖全部产品代码改动）；`git revert A..B` 区间形式在 `git 2.52.0.windows.1` 下可用 ✓ |
| 计数事实自洽 | **否**——「31 commits + 该冻结提交」与实际 33 不符（F-03）；EVD-1034 gate 14 同错 |
| 步骤可执行 | **基本可执行**：`log/status` 取证 → `revert --no-commit <range>`（或 `checkout v0.80.0`）→ 重装预设；`$env:DSH_HOME=<真实 home>` + `--install` 在回滚后**语义自洽**（守卫随回滚消失，文档 `:46` 已声明并加提醒）✓ |
| 终点选择 | **需修正**（F-04）：终点是候选打包提交，而当前 HEAD 已是 `22cf185`（`git rev-list --count a89341e..HEAD` = 1，且该提交**修改了三件套 release 文档本身**：`git show --stat 22cf185` = 3 文件 +34/−16），M-5 还会追加 transition 提交 ⇒ 在发布 tip 上执行该区间 revert 会出现「区间外提交已改动了区间内新增的文件」的上下文不匹配，存在冲突/残留风险 |
| 是否已演练（SKILL 硬门槛：至少一次） | **无任何演练证据**（§4 的 7 项验证都是「回滚后 MUST 全绿」的待执行清单）⇒ 硬门槛「回滚方案存在且已验证 = 已验证」**未满足** |
| 渲染哈希说法自洽性 | **自洽**：`rollback-plan:19/54/70` + `release-checklist:89` + `real-machine-acceptance:84` + `version-plan:17` 一致（0.81.0 = `6caf90fe…e55d`、0.80.0 基线/回滚后 = `00e0d330…3723`、差异仅 persona 版本行 1 处），并显式禁止「保持 `00e0d330…3723` 不变」的措辞；结构支撑：`agent-presets/` 仅 2 文件 + `agent.cordis.yml.template:51` 为唯一版本字面量（我实测）。**字节值本身未复现**（需执行渲染） |
| 数据安全论证 | 与代码事实一致（预设 = 可再生产物、`real-home writes: 0`）；§5「不可回滚项」登记合理 ✓ |

---

## 3. 维度三：CHANGELOG 质量（用户视角）

| 检查项 | 结论 |
|---|---|
| 是否覆盖本次全部变更 | **覆盖良好**：AUDIT-153 / FEAT-028~031（V1~V8）/ FIX-311·313·315·316·317 / FIX-319·321 / RISK-050 挂载 / FIX-320 如实披露；仅缺测试卫生类（FIX-327/328/329/330）——属内部面，可接受（P3 观察） |
| breaking changes 是否显式标注 | **未达既有范式**（F-05）：`version-plan:44/48` 声明「对既有用户可见行为保持 / 本版无 breaking change」，在 `VERSIONING.md:11`（Breaking = 删改 MUST 规则 / Gate 语义 / governance 字段格式）口径下**成立**；但 0.78.0（`CHANGELOG:171`）、0.78.1（`:126`）、0.80.0（`:55`）都在条目内显式写 `**Breaking changes：…**`，0.81.0 条目全文**无该标记**；而 B-2 使 README 仍在文档化的手工路径（`README.md:33/81-82/106-107/402-407/425-427`）在真实 home 下 `exit 2 [REFUSED]`（代码实证：`launch.py:655-657`、`:851-911`、`:1803` 放行 `--dry-run`） |
| 分类是否成立 | **成立（L11 口径）**，但按 `VERSIONING.md:83`（1.0.0 前 Minor 可含有限 Breaking，**必须 CHANGELOG 显式标注**）+ `:107`（V-Gate：Breaking 需文档 + 迁移指南），把「不构成 breaking」写成**显式结论**比省略更合规；同类变更在 0.80.0 被写作 Breaking，口径不一致会被外部审查追问 |
| 验收① 诚实性措辞 | **合规** ✓：`CHANGELOG:23` 与 `release-checklist:133-143` 均为「由独立审查的故障注入复现成立，机器守卫待 FIX-325」，**未**声称有测试守卫（硬约束满足） |
| 真机项措辞 | **合规** ✓：`CHANGELOG:35` 明写「回贴前 MUST NOT 声明真机项通过」 |

---

## 4. 维度四：Feature Flag

| 检查项 | 结论 |
|---|---|
| 「新增 opt-in 开关 = 0」论证是否成立 | **成立**：feature-flags §1/§3 的新增面（Check 28w、`dsh-doctor`、契约文件）均为**默认启用**的检查/命令，非用户开关；代码面无新 opt-in |
| 写入守卫无开关（Kill Switch 缺口） | **如实登记**：§1 表 + §4 D-1 明写「刻意没有 opt-in，登记 FIX-324」；代码面复核一致（`launch.py:655/851-911` 无 opt-in 分支，唯一放行 = `--dry-run` 只读预览，`:1803`） |
| B-1/B-2「关闭/回退」路径 | **写清**：§2 表给出旧行为/新行为/理由/影响面；回退路径 = 版本回滚（`rollback-plan:21/46` 明写「回滚即恢复旧行为（含旧的可写真实 home 风险）」+ 提醒），且拒绝消息本身给出可行动指引（`launch.py:879-886` 提示把 `DSH_HOME` 指向临时目录）✓ |
| 与 0.80.0 开关对照 | 无删除、语义未变的声明与代码面无矛盾 ✓ |

**结论：Feature Flag 维度通过**（唯一欠账是 README 文档口径未同步 → 已并入 F-05；登记号 FIX-324 存在）。

---

## 5. 维度五：版本号合规 + 风险与 no-overclaim

| 检查项 | 结论 |
|---|---|
| 0.81.0 = MINOR 论证（`version-plan` §2） | **成立**：新增能力面（契约 + 访问器 + Check 28w + `dsh-doctor` + fixture）+ 无 `VERSIONING.md:11` 意义上的 breaking；非 MAJOR ✓；非 PATCH（含新增能力与门禁）✓；版本号未被预留（plan-tracker 路线图无 0.81.0 预留行——文档声明，未逐行复核即接受为规划事实） |
| 跳号/语义化违规 | **未发现**：0.80.0 → 0.81.0 单调 +1；`check-version-consistency` 声明面实测一致（我复现的声明面全为 0.81.0） |
| `check-version-consistency` PASS 是否覆盖全部版本声明面 | **覆盖面无遗漏**（我逐一核了 4 plugin.json / marketplace / package.json / SKILL.md×2 / manifest.json / architecture-baseline.json / hooks×4 / bootstrap 标记面 / AGENTS.md.template）；两类残留均为 **gitignored 本地文件**（`plan-tracker.md`、`CLAUDE.md`）⇒ 不属发布面，M-8 转版正确 |
| RISK-050 是否被误声明关闭 | **否** ✓：`.governance/risk-log.md:44` = **打开**、截止 `2026-10-31`、收口条件含真实环境验收；三件套 + CHANGELOG + version-plan §6/§8 一致写「不声明关闭」 |
| 三件套「保守边界声明」是否真实（非形式化免责） | **真实**：5 个 token 齐备 + 就地否定 `1.0.0 production-ready`，且逐条绑定本版事实（真机三项未回贴 ⇒ 未验证；隔离验收措辞限定；RISK-036 打开）✓。RISK-036 经 `risk-log.md:39` = 打开 ✓ |
| 真机三项是否被任何文档声明为通过 | **否** ✓：全库「真机」在 release 面向文档/CHANGELOG 的命中全部是禁止性/未验证表述（`real-machine-acceptance:101`、`checklist:55/97/106/116`、`version-plan:119/135`、`CHANGELOG:35`）；`⟦待用户回贴⟧` 为允许占位 |
| 文件存在性/结构性核对 | 三件套 + 规程 + manifest 均实存；manifest 键面 = candidate 态（`lifecycle_state/effective_state.lifecycle_state = candidate`、`events=[]`、`provenance=native`、`schema_version=1`）✓；`git log --diff-filter=A -- …/0.81.0.json` = **`a89341e`** ⇒ ledger 的 `candidate_commit`（`derivation=git_commit_adding_path`）与文档声明**一致** ✓ |

---

## 6. 硬门槛逐条裁决（`agents/release-reviewer.md`）

| 门槛项 | 阈值 | 我的裁决 |
|---|---|---|
| 发布检查清单全部 PASS | = 100% | **未满足**：14 项中 2 项（Gate 6/7）在冻结产物内仍是「V8 在制品预检」值 + 残留占位（F-06）；Gate 10 含反向归因（F-01）；Gate 14 计数错误（F-03） |
| 回滚方案存在且已验证 | = 已验证 | **未满足**：方案存在、步骤基本可执行，但**无演练记录**，且区间终点非发布 tip（F-04） |
| CHANGELOG 用户视角完整 | 关键段全部覆盖 | **满足**（新增/变更/修复/披露齐全；F-05 为范式/显式声明问题，非缺失） |
| breaking changes 已标注 | = 100% | **部分满足**：L11 口径下「无 breaking」成立，但缺显式结论行与升级须知高亮（F-05；同类变更在 0.80.0 写作 Breaking） |
| Feature Flag 关闭验证 | 全部通过 | **满足**（新增开关 0；B-1/B-2 回退路径 = 版本回滚且已写明；无开关面登记 FIX-324）|

---

## 7. Findings

### F-01 — **P1（blocking）** — 候选态存在**未披露且被反向归因**的测试失败：`test_dsh_doctor.py` 的渲染哈希硬钉仍是 0.80.0 值

- **位置**：`skills/software-project-governance/infra/tests/test_dsh_doctor.py:626-632`；`docs/release/release-checklist-0.81.0.md:88`（Gate 10 归因③）；对照面 `docs/release/release-checklist-0.81.0.md:89`（Gate 11）、`docs/release/real-machine-acceptance-0.81.0.md:84`
- **事实依据（4 条实测链）**：
  1. `git log -S"00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723" -- …/test_dsh_doctor.py` → 唯一引入提交 = **`3074120`**（V8，版本 bump **之前**）；`git show --stat a89341e` 的 35 个文件中**不含** `test_dsh_doctor.py` ⇒ 版本 bump（`0.80.0` → `0.81.0`）**未同步**该硬钉。
  2. `git show 5e6d8c7:agent-presets/governance/agent.cordis.yml.template` = `（v0.80.0）`；`a89341e` / `HEAD` = `（v0.81.0）`。
  3. 渲染输入取自**被测树自身**：`adapters/dsh/launch.py:81 ROOT = Path(__file__).resolve().parents[2]`、`:271 return ROOT / COMPOSITION_TEMPLATE`，`dsh_doctor.py:916-931 _python_render(root)` 直接 `exec` 该 `launch.py` 并调 `render_composition()`；`agent-presets/` 仅 2 文件，唯一版本字面量 = `agent.cordis.yml.template:51`（我实测 `git grep -E "0\.(7[0-9]|8[0-9])\.[0-9]" -- agent-presets/` 仅此 1 命中）。
  4. 同批文档自证：候选态渲染 = `6caf90fe…e55d`（Gate 11 + 规程 §2 行 5），与 `00e0d330…3723` 差异**恰为该版本行** ⇒ 候选树上 `test_the_python_render_is_the_launchers_own_output` 的断言**不可满足**；pristine（`5e6d8c7`）树上**可满足** —— 与 Gate 10 归因③「在 **pristine 侧**失败」**方向相反**。
- **影响**：① 发布候选树自带一个必然失败的测试，属「版本钉腐朽」第 3 例，而 Gate 10 ② 已宣告该归因被证伪；② Gate 10 的「零产品代码回归 / 既有失败基线 3 条 / 差集逐条归因」在证据上不完整并含反向陈述（产品代码本身未受损：该断言只在测试内，S4 运行面按运行时计算哈希）；③ 对一个以「零校验不得 PASS / 严格看护」为本版主题的发布，自证式硬钉失配会被外部审查第一时间看到。
- **建议（最小修复）**：把 `:632` 改为候选态值 `6caf90fe…e55d`（或改为从模板/`package.json` 派生，彻底消灭硬钉）→ 复跑 `test_dsh_doctor`（应 70 OK）→ 重取全量原始失败清单并逐条贴出（F-02）→ 更正 Gate 10 归因③与「既有失败基线」计数。

### F-02 — **P2** — R0 F-04 的「重取全量原始失败清单并逐条贴出」被声明为**已履行**，但清单不存在

- **位置**：`docs/release/release-checklist-0.81.0.md:88`（「**已履行**：见 FIX-328/FIX-330 的定向复跑与全量差集复核，证据行 EVD-1033/EVD-1034」）；`.governance/evidence-log.md:2080`（EVD-1033）、`:2087`（EVD-1034）
- **事实依据**：EVD-1033 只给 `Ran 2983 failures=38 errors=2` + 3 项归因；EVD-1034 gate 10 只给 3 桶归因（「1 真回归已修 / 2 经证伪为瞬时红 / 其余 pristine 侧噪声」）；两处与 checklist 正文均**无 38 条失败的逐条清单**。
- **影响**：正是该缺口使 F-01 漏检——逐条贴出时 `test_dsh_doctor` 的失败会立即显形；R0 F-04 的义务实质未达成却标注已履行。
- **建议**：重取时把原始失败清单（模块 + 用例名）贴入 Gate 10 或新增 EVD 行，逐条标注「既有 / 本版引入 / 环境敏感」。

### F-03 — **P2** — 回滚窗口计数错误（写 31+1，实测 33）且 Change Inventory 未覆盖 `5e6d8c7`

- **位置**：`docs/release/release-checklist-0.81.0.md:92`（Gate 14）；`docs/release/rollback-plan-0.81.0.md:36`（§2.1 注释）、`:93`（尾注）；`.governance/evidence-log.md:2087`（EVD-1034 gate 14 同错）
- **事实依据**：`git rev-list --count d87ead8..3074120` = **31**（✓ 与 Change Inventory 一致）；`git rev-list --count d87ead8..a89341e` = **33**（31 + `5e6d8c7` M-1 冻结推进 + `a89341e` 候选打包）⇒ 文中「共 31 commits + 该冻结提交」（=32）**少 1**；`5e6d8c7` 属 0.81.0 窗口但不在 Change Inventory 的 `d87ead8..3074120` 口径内（口径选择本身合理，但 Gate 14 的区间描述须与实测同源）。
- **影响**：低-中（区间端点与 revert 命令正确）；但发布文档的计数与实测不符，且会随发布准备提交继续漂移。
- **建议**：改为实测值（当前 33）或取消固定计数、只写端点 + 现场 `git rev-list --count` 查询。

### F-04 — **P2** — 回滚区间终点是「候选打包提交」而非发布 tip，且**无演练记录**

- **位置**：`docs/release/rollback-plan-0.81.0.md:34-39`（区间定义 + 命令）、`:62-72`（§4 验证清单）
- **事实依据**：`git rev-list --count a89341e..HEAD` = **1**（`22cf185`），且 `git show --stat 22cf185` = 3 文件 +34/−16（**三件套 release 文档本身**）；M-5 还会追加 transition 提交 ⇒ `git revert --no-commit d87ead8..a89341e` 在发布 tip 上执行时，区间内新增的三个 release 文档已被区间外提交修改，反相应用（删除性 hunk / 上下文）与当前树不匹配，存在冲突或残留风险；文档未声明该次序问题，也无任何 revert 干跑证据（SKILL 硬门槛要求「回滚方案已演练（至少一次）」）。
- **影响**：事故时回滚可能先卡冲突；残留的 post-candidate 提交会造成「已回到 0.80.0」的错觉。
- **建议**：① 终点改为发布 tip（`d87ead8..v0.81.0^{commit}`，或声明 `..HEAD` 语义）；② 在 M-5 打 tag **之前**以 `git revert --no-commit --no-edit d87ead8..<tip>` 干跑并记录冲突面（随后 `git revert --abort` 不留痕），把结果作为「已演练」证据；③ 显式声明 post-candidate 提交（`22cf185` / transition / released manifest）是否必须回滚。

### F-05 — **P2** — CHANGELOG 缺显式 breaking/行为变更声明块；README 手工安装口径未同步 B-2

- **位置**：`project/CHANGELOG.md:29`（行为变更段）、`:5-37`（0.81.0 条目全文无 `Breaking`）；`docs/release/version-plan-0.81.0.md:44,48`；`README.md:33/81-82/106-107/402-407/425-427`
- **事实依据**：0.78.0（`CHANGELOG:171`）/ 0.78.1（`:126`）/ 0.80.0（`:55`）均显式书写 `**Breaking changes：…**` 或「Breaking changes：无」，0.81.0 两者皆无；`VERSIONING.md:11` 的 Breaking 定义不含 B-1/B-2（故「无 breaking」成立），但 `:83` 要求 1.0.0 前 Minor 的有限 Breaking **必须在 CHANGELOG 显式标注**，`:107` 要求 Breaking 有文档 + 迁移指南；代码面实证 B-2 拒绝真实 home（`launch.py:655-657`/`:851-911`，`--dry-run` 由 `:1803` 放行），而 README 未加任何限定或指引。
- **影响**：用户与外部审查无法从 CHANGELOG 直接读到「本版声明无 breaking + 2 项行为变更 + 升级须知」，须跳链 feature-flags；README 的手工路径在真实 home 下会得到 `exit 2 [REFUSED]`（拒绝消息本身可行动，故非阻塞级）。
- **建议**：在 0.81.0 条目顶部加显式结论行：`Breaking changes：无（VERSIONING.md L11 定义）；用户可感知行为变更 B-1/B-2（升级须知）`；同步 README 手工安装段的限定语，或在该处加一行指向 `feature-flags-0.81.0.md` §2 的指针（FIX-324 承接亦可，但发布文档需自证一致）。

### F-06 — **P2** — Gate 6/7 仍为「V8 在制品预检」值 + 残留 ⟦⟧ 占位，与 EVD-1034 的实际 M-2 值矛盾

- **位置**：`docs/release/release-checklist-0.81.0.md:84`（Gate 6）、`:85`（Gate 7）
- **事实依据**：行内值 `R1 24405` / `K-8 54 测试文件` 来自预检；EVD-1034（`evidence-log.md:2087`）的 M-2 值 = `R1 24412` / `K-8 55 测试文件`；候选提交 `a89341e` 修改了 `core/architecture-baseline.json`（`git show --stat a89341e`）⇒ 棘轮锚点在冻结提交上确实变化，正是「需重跑」的对象；两行各留 1 处 `⟦M-2 需在全部切片落地后重跑⟧`（全仓 `docs/release/` 共 4 处 ⟦⟧，另 2 处为真机面与纪律引文，属允许面）。
- **影响**：14 项中 2 项在冻结产物里没有「候选提交上」的证据，而表头声称「由 M-2 门禁实测逐项回填」；残留占位超出允许范围。
- **建议**：用 EVD-1034 的值回填 Gate 6/7（并注明 `24405→24412` 的成因 = 候选提交内 `test_triage_write_guard.py` 与 architecture-baseline 同步），删除两处占位。

### F-07 — **P3** — `unit tests` 超时的定性措辞不准确（非「时序噪声」）

- **位置**：`docs/release/release-checklist-0.81.0.md:91`（Gate 13 ③）
- **事实依据**：`verify_workflow.py:5946 _RELEASE_GATE_TIMEOUT_DEFAULT = 180`、`:5947 SPG_RELEASE_GATE_TIMEOUT`（FIX-234 可覆盖）、`:6024`「unit tests」面**只跑** `test_verify_workflow.py` 单模块；同批自述该模块在 discover 下 **258.1s** 完成 ⇒ 单模块预算 180s < 墙钟 ≈258s，属**确定性口径/预算不匹配**（可配置），不是随机 flake；本版对 `test_verify_workflow.py` 的新增内容 = 9 个 scope-bold 用例（`git diff d87ead8..a89341e -- …/test_verify_workflow.py` 的 `def test_` 行），属廉价用例，故「主因非本版引入」判断有支撑，但「既有」本身**未被实测证明**（无 pristine/0.80.0 侧的同一门禁运行记录）。
- **影响**：措辞会把可复现的口径问题说成抖动，掩盖「该门禁在当前默认配置下恒不绿」；也削弱「执行面 3 项 FAIL 全为既有基线」的力度。
- **建议**：改为「单模块 180s 预算 < 模块墙钟（≈258s）⇒ 确定性超时；缓解 = `SPG_RELEASE_GATE_TIMEOUT` 或 discover 模式；非本版引入（新增 9 个廉价用例）」，并补 pristine 侧门禁运行记录以支撑「既有」。

### F-08 — **P3** — 清单尾部 M-1 结语与已回填的 M-2 表自相矛盾

- **位置**：`docs/release/release-checklist-0.81.0.md:106`
- **事实依据**：结语仍写「「Candidate Gate Results」的 M-2 门禁实测与真机三项回贴仍为待办」，而 Gate 1~5、8~13 已标「实测」。
- **影响**：低；冻结产物内自相矛盾，后续审查会重复提出。
- **建议**：改为「M-2 门禁实测已回填（见上表）；真机三项回贴仍为待办」。

### F-09 — **P3** — Gate 13 的「既有基线」归因未在本轮独立复现（保留为文档级事实）

- **位置**：`docs/release/release-checklist-0.81.0.md:91`
- **事实依据**：`docs/reviews/review-FIX-300-CODE-R0.md` 实存（0.66.1 期）；`governance health` 88 issues 与 `loop runtime claim gate` 4 条的**当前**数值需执行命令确认，我在只读边界内未执行 ⇒ 标「未复现」。
- **影响**：低（不改变结论方向）。
- **建议**：如需强化，M-4 前把两条命令原始输出贴入 Gate 13。

---

## 8. 独立复现声明

**我亲自复核（可复现的实测）**：

1. `git rev-list --count`：`d87ead8..3074120` = **31**；`71f73eb..3074120` = **32**；`d87ead8..a89341e` = **33**；`a89341e..HEAD` = **1**。
2. **Change Inventory 全表 31 个 commit hash** 与 `git log --reverse --format=%h d87ead8..3074120` **逐行全等（31/31，0 mismatch）**；首/末 = `4d93b24` / `3074120`。
3. 基线语义：`v0.80.0^{commit}` = `71f73eb`；`merge-base --is-ancestor 71f73eb d87ead8` = 真 / 反向 = 假 ⇒ `d87ead8` = 0.80.0 线 tip（post-tag 记账）；`d87ead8` 提交信息 = REL-076 M-5 回填。
4. manifest 键面：`core/releases/0.81.0.json` 全文（candidate 态、`events=[]`、`derivation=git_commit_adding_path`）；`git log --diff-filter=A -- <manifest>` = **`a89341e`**（= 文档声明的 candidate commit，同批入库需成立）。
5. 版本声明面：`git grep -l 0.81.0`（60+ 命中）+ 定向 `git grep -E '"version" *: *"0\.80\.0"'` ⇒ 除历史 `0.80.0.json` 外无残留声明面；SKILL.md frontmatter `version: 0.81.0`；bootstrap 标记面（`AGENTS.md:5`、`AGENTS.md.template:3`、`commands/governance-init.md`）全为 0.81.0。
6. `CLAUDE.md` 未跟踪：`git ls-files -- CLAUDE.md` 空 + `git check-ignore -v` = `.gitignore:3:CLAUDE.md`；`.gitignore` 前 6 行实测。
7. 模板版本行三时点比对：`5e6d8c7` = `v0.80.0`、`a89341e` = `v0.81.0`、`HEAD` = `v0.81.0`；`agent-presets/` 仅 2 文件、唯一版本字面量 = `agent.cordis.yml.template:51`。
8. **F-01 的证据链**：`git log -S<旧哈希> -- test_dsh_doctor.py` = `3074120`；`git show --stat a89341e` 不含该文件；`launch.py:81/:271` + `dsh_doctor.py:916-931` + `test_dsh_doctor.py:35-43/626-632` 全文阅读（无 skip 装饰、无跳过分支）。
9. 契约字节：`Get-FileHash adapters/dsh/host-contract.json` = `96F92485…43FC6E`（74702 bytes）——与 Gate 12 逐位相符。
10. Gate 5 判据：`infra/cleanup.py:26 ERR_NOTHING_TO_CLEAN = 1`。
11. 门禁面代码：`verify_workflow.py:5946/5947/6016-6026`（180s 默认 + 环境覆盖 + 「unit tests」= 单模块）；`launch.py:617-661/795-830/851-911/1803`（B-2 守卫、`--dry-run` 放行、拒绝消息内容）。
12. 占位扫描：`docs/release/` 全量 `⟦…⟧` = 4 处（Gate 6/7 + 真机面 + 纪律引文）。
13. 措辞面：全库「真机」在 release 文档/CHANGELOG 的命中全部为禁止/未验证表述；`00e0d330` 全库 31 处命中逐条查看（0.81.0 文档面 5 处均已带 `6caf90fe` 对照 + 禁止措辞；仅 `docs/reviews/review-REL-077-CODE-R1.md:95` 为对旧状态的引用，属评审历史）。
14. 风险账本：`RISK-050`（`:44`）= 打开 / 截止 `2026-10-31` / 收口含真实环境验收；`RISK-036`（`:39`）= 打开。
15. 归档结构：`.governance/archive/index.md` 存在（1154 行，Task 索引表 + 版本列），`Hot 89 + Archived 91 = Total 180` 自洽 —— **精确计数未复现**（需 `check-archive-integrity`）。
16. `git --version` = `2.52.0.windows.1` ⇒ `git revert <range>` 形式可用。

**我未能独立复现（执行边界外，按 fail-closed 标为「文档级事实」）**：

- `check-release` 静态 13/13 与 `Result: FAILED — 6 issue(s)`、`release-ledger` 的 `state: PASS` / `trust_level: NATIVE_CANDIDATE`；
- 全量测试的 `2983 / 38 / 2`（候选）与 `2983 / 28 / 9`（pristine）及差集清单；
- 28u / 28v / 28w 的实际输出与 K-1~K-13 逐条结论；
- 渲染 sha256 字节值 `6caf90fe…e55d`（16796 bytes）与「还原 1 处即等于 `00e0d330…3723`」；
- `archguard-ratchet` 的 `R1 24412` / `R7 deterministic`、`governance health` 88 issues、`check-archive-integrity` PASS。

⇒ 这些数值**不构成**本轮 blocking 的依据；F-01 的 blocking 依据全部来自可复现的静态实测（§8 第 7/8 条）。

---

## 9. 命令上报（全部只读；无任何写操作）

| # | 命令（摘要） | 退出码 | 结论摘要 |
|---|---|---|---|
| 1 | `git log --oneline -6` | 0 | HEAD = `22cf185`（门禁收口）→ `a89341e`（候选打包）→ `5e6d8c7` → `3074120` |
| 2 | `git rev-list --count d87ead8..3074120 / 71f73eb..3074120 / d87ead8..a89341e / 71f73eb..a89341e / a89341e..HEAD` | 0 | 31 / 32 / **33** / 34 / 1 |
| 3 | `git log --oneline -1 <d87ead8 / v0.80.0 / 71f73eb>` + `git tag --list v0.8*` | 0 | `v0.80.0` peel = `71f73eb`；`d87ead8` = REL-076 M-5 回填 |
| 4 | `git merge-base --is-ancestor 71f73eb d87ead8` | 0（真） | 71f73eb 是 d87ead8 祖先（反向 exit=1 假） |
| 5 | `git show --stat --oneline a89341e` / `22cf185` | 0 | 候选 35 文件 +1251/−110（含 manifest `1 +`）；收口 3 文件 +34/−16（三件套） |
| 6 | `git log --diff-filter=A -- <0.81.0.json>` | 0 | `a89341e`（= ledger 派生源） |
| 7 | `git show <c>:package.json` / `<c>:agent.cordis.yml.template`（c = d87ead8/5e6d8c7/a89341e/22cf185/HEAD） | 0 | 0.80.0 → 0.81.0；模板版本行 `v0.80.0` → `v0.81.0` |
| 8 | `git log -S<旧哈希> -- test_dsh_doctor.py`、`git log -3 -- …`、`git diff --stat d87ead8..a89341e -- …test_dsh_doctor.py …test_verify_workflow.py` | 0 | 硬钉引入 = `3074120`；窗口内仅新增（1128 / 140 行） |
| 9 | `git status --porcelain`（定向过滤） | 0 | 被审文件无本地未提交改动（工作树对 `docs/`/`tests/` 干净） |
| 10 | `git grep -n "0\.80\.0" -- skills/.../tests`、`git grep -n -E '"version" *: *"0\.80\.0"'`、`git grep -l 0.81.0` | 0 | 测试内无其他版本硬钉；无残留声明面 |
| 11 | `git grep -n -E "0\.(7[0-9]|8[0-9])\.[0-9]" -- agent-presets/`、`git ls-files agent-presets/` | 0 | 唯一版本字面量 = 模板 `:51`；目录仅 2 文件 |
| 12 | `git grep -n "真机" -- <release 文档/CHANGELOG>`（含 PASS/通过 过滤） | 0 | 全部为禁止/未验证表述 |
| 13 | `git grep -n "@bootstrap-version"`、`git show HEAD:skills/.../SKILL.md`（前 8 行） | 0 | 标记面 0.81.0；frontmatter `version: 0.81.0` |
| 14 | `git ls-files -- CLAUDE.md`、`git check-ignore -v CLAUDE.md`、`git show HEAD:.gitignore` | 0 | CLAUDE.md 未跟踪 / `.gitignore:3`；AGENTS.md 亦在 ignore 列表但为 tracked |
| 15 | `git diff a89341e^ a89341e -- README.md` | 0 | 候选仅改 2 行（tag 推送口径），未涉及 `--install` 拒绝 |
| 16 | `git log --reverse --oneline d87ead8..3074120` + 表内 hash 逐行比对脚本 | 0 | **31/31 全等、0 mismatch** |
| 17 | `git --version` | 0 | `2.52.0.windows.1` |
| 18 | `Get-FileHash adapters/dsh/host-contract.json -Algorithm SHA256` + `Get-Item .Length`（只读哈希） | 0 | `96F92485…43FC6E` / 74702 B |
| 19 | `Get-Content -Encoding UTF8`（只读，AGENTS.md 规定的 UTF-8 读法）读取 `.governance/risk-log.md:44`、`.governance/evidence-log.md:2080/2087`、`.governance/archive/index.md` 头部 | 0 | RISK-050 打开/2026-10-31；EVD-1033/1034 无原始失败清单；archive index 存在 |

未执行任何 `git add/commit/restore/reset/checkout/stash/revert`，未执行任何 python/gate/测试，未触碰 `$HOME/.dsh` 或仓库外路径。

---

## 10. 发布就绪裁决

**裁决：不具备进入 M-4/M-5（transition + annotated tag）的条件。**

理由：硬门槛「发布检查清单全部 PASS / 逐项有可复核证据」未满足——冻结产物内 2/14 门禁行仍是「V8 在制品预检」值且带残留占位（F-06），Gate 10 含**与版本事实相反**的失败归因（F-01），Gate 14/回滚方案的窗口计数与实测不符（F-03），回滚区间终点非发布 tip 且无演练证据（F-04）。产品代码、版本号、manifest、三件套结论**本身**未发现实质缺陷（契约字节、版本一致面、Change Inventory、RISK 状态、no-overclaim 与真机措辞均通过核验）⇒ 属「证据完整性 + 文档正确性」类阻塞，而非架构/功能类阻塞。

**最小阻塞项清单（修完即可重跑本审查 R1）**

| # | 动作 | 覆盖 finding | 判据（修复验收） |
|---|---|---|---|
| 1 | 修 `test_dsh_doctor.py:632` 的 0.80.0 硬钉（改为候选态值或改为派生），复跑 `test_dsh_doctor` | F-01 | 该套件在候选树全绿（70 OK）且不再依赖版本字面量 |
| 2 | 重取全量原始失败清单并**逐条贴出**；更正 Gate 10 归因③与「既有失败基线 3 条」计数 | F-01 / F-02 | checklist Gate 10 或 EVD 行含逐条清单 + 正确归因 |
| 3 | 回填 Gate 6/7 的 M-2 实测值（EVD-1034：`R1 24412` / `K-8 55`）并删除两处 `⟦M-2 需…⟧` 占位；说明锚点变更成因 | F-06 | `docs/release/` 仅真机面保留 `⟦⟧` |
| 4 | 更正窗口计数（33，或取消固定计数）+ 把回滚终点改为发布 tip + 在打 tag 前做一次 `git revert --no-commit` 干跑并留证（`--abort` 收尾） | F-03 / F-04 | rollback-plan 计数与 `rev-list --count` 同源；文档含演练记录 |
| 5 | CHANGELOG 0.81.0 条目加显式结论行（`Breaking changes：无（L11）；行为变更 B-1/B-2 → 升级须知`），并同步 README 手工安装段或加指针 | F-05 | 条目内可见声明；README 与代码行为一致 |
| 6 | （建议一并）修正措辞「时序噪声」、订正清单 `:106` 结语 | F-07 / F-08 | 措辞与确定性事实一致；结语不再自相矛盾 |

**M-4/M-5 之前的推荐次序**：1 → 2 → 3 → 4（干跑可与 4 合并）→ 5 → 6 → 复审（同一 Release Reviewer，R1，需在报告中标注 `round=R1` 并逐条比对本轮 findings 的修复状态）。真机三项仍由用户手动执行回贴，**回贴前任何文档不得声明通过**（本轮已核：现无此类声明）。

---

*审查方：Release Reviewer Agent（只读）｜审查对象版本：0.81.0（REL-077）｜候选打包提交 `a89341e`，门禁收口提交 `22cf185`｜结论：**NEEDS_CHANGE**｜机录建议：Coordinator 以 review-record 持久化（`round=R0`，`unresolved_blockers` 仅在本报告作为 APPROVED_WITH_NOTES 时才是通过终态字段；本轮为 NEEDS_CHANGE，须返工后发起 R1 复审）*
