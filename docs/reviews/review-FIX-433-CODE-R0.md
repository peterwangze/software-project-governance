# Code Review — FIX-433 R0（CODE）

- **任务**：FIX-433 — `launch.py --sync`「真实用户根刷新」死路指引 sweep（纯文档/字符串，零运行时行为变更）
- **审查者**：独立 Code Reviewer（R0）
- **日期**：2026-01-30（会话内审查）
- **审查对象**：工作区未 commit 改动（`git status --porcelain` 全量核对）
- **终裁**：**APPROVED_WITH_NOTES**（unresolved_blockers = 0；1×P2 + 2×P3）

---

## 1. 审查范围与方法

- **diff 事实源**：`git status --porcelain` + `git diff --stat` + `git diff`（逐文件全文核对）。改动面 = 恰好 10 个 modified 文件、35 insertions / 24 deletions、18 个 hunk；无 staged 变更、无 untracked 新文件、无删除文件；`.governance/**` 零出现；豁免面（docs/release、docs/requirements、docs/marketplace、project/CHANGELOG.md）零出现。
- **守卫事实独立核对**：直读 `adapters/dsh/launch.py` L826（`SMOKE_EXIT_REFUSED = 2`）、L855-915（`write_side_refusal`：`$DSH_HOME` 未显式设置/空白/profile 不可解析/解析至真实 DSH home 一律拒）、L917-922（`_refuse_write` 返回 exit 2 + `[REFUSED]` 输出）、L1803-1809（argparse：`--install`/`--sync` 同 dest="install" 别名）。
- **残留扫描**：grep 全仓库 `launch\.py.*--sync|--sync.*launch\.py`（65 匹配）+ `adapters/dsh/**` 与 `lib/index.js` 内全部 `--sync`（7+1 匹配），逐条分类。
- **独立复跑**：4 项 verify_workflow check + pytest 三文件（见 §3，全部 exit 0）。
- **模板行数**：`adapters/dsh/AGENTS.md.template` = 37 行（`Get-Content -Encoding UTF8` 计数，另经 check-entry-bootstrap-sync 输出 `3633B/37L` 交叉印证）。声称「仍 37 行」属实。

## 2. 逐维度结论

### 2.1 正确性 — PASS

- **exit 2 事实**：所有新表述（launch.py docstring「refuses the real home (exit 2)」、template「设计性拒绝 exit 2」、根 README「必拒 `exit 2`」、manifest「refused with exit 2」等）与 `SMOKE_EXIT_REFUSED = 2` 一致，无 exit 1 误写。
- **重启正道语义**：「git pull 后重启 dsh——bundle 宿主行 `ensurePreset()` 按包版本幂等重渲染」各面表述与 lib/index.js `ensurePreset` 的实际角色（宿主行渲染，contract-unreadable 时跳过并警告）一致；「版本未变不写」的幂等语义与 adapter-manifest 及测试套件（test_dsh_contract 通过）佐证一致。
- **无 HMR 失真**：adapters/dsh/README.md L44 保留「boot-time 应用，非 HMR，不重启不生效」——bundle 层语义准确，未把重启说成 HMR。
- **launch.py 注释**（L609-611）：「hooks 自升级 = `git pull` + 重启（或显式重定向隔离 DSH_HOME 下 `--sync`）」——skill-root.txt marker 由渲染器写入、重启后 ensurePreset 重写 marker，语义正确。
- **dsh_doctor.py 6 处 remediation** 逐条语义正确（S1 五种 FAIL 形态的修复动作从死路 `--sync` 改为重启；S6 给出隔离限定下仍可用 `--sync` 的正确复合指引）。`_remediation(action, command, expected)` 的 command 位放动作句式与既有未改动调用（L553 `python …/verify_workflow.py …` 带占位符、L384 `set DSH_HOME=<dir>`）惯例一致，无契约破坏。
- **lib/index.js warn 串**：「重定向 DSH_HOME 到临时目录后在那里跑 `--sync` 看确切错误——真实根写侧在渲染前被拒」——技术上成立（渲染管线同源、DSH_HOME 仅决定写入目标；旧串在真实根会先被 exit 2 拒绝、用户看不到渲染错误，确属死路），新指引给出可行复现路径。

### 2.2 完整性 — PASS

- Developer 声称的 10 文件全部位置均在 diff 中核实：adapters/dsh/README.md（L29+L44）、AGENTS.md.template（L37）、adapter-manifest.json（L63）、launch.py（docstring L26-33 + 注释 L609-611，改动后行号）、根 README.md（L109+L430）、SKILL.md L478、e2e 投影 SKILL.md L478（与主 SKILL.md 同 blob hash `37ac32a..10e174`，逐字一致）、dsh_doctor.py（6 处）、lib/index.js（L474-478）、agent-entry-differences.md（L69）。任务方计数 16 锚点、按 hunk 实数 18（投影镜像对/launch.py 双处可能合并计数），覆盖无缺口。
- **修改文件内 `--sync` 残留**（grep 逐条核对）：launch.py L26（docstring 隔离语义）/L611（隔离限定注释）/L1805（argparse 旗标定义）；README×2、template、manifest、SKILL×2、references、lib、doctor 各 1 处——全部为隔离限定或旗标定义/守卫文档语义，**零死路残留**。
- **全仓库非修改文件残留**：project/CHANGELOG.md（5）、docs/release/**（feature-flags/release-checklist/rollback-plan/version-plan/real-machine-acceptance 等）、docs/requirements/**（3）、docs/marketplace/（1）——全部在显式豁免面内且 `git status` 证实零触碰。docs/architecture/ADR-020（2 处）与 docs/reviews/review-FEAT-073-R0.md（1 处）为装配构造事实描述/不可变历史记录，不构成升级死路指引（见 F-3）。

### 2.3 无回归 — PASS

- **launch.py**：diff 仅 docstring 1 hunk（-2/+5）+ 注释 1 hunk（-1/+2）；`write_side_refusal`、`_refuse_write`、argparse、渲染与 smoke 逻辑**零改动**（diff 逐行验证 + 直读守卫源码交叉印证）。
- **dsh_doctor.py**：6 hunk 全部为 `_remediation(...)` 字符串参数改写，无逻辑/签名/控制流改动。
- **lib/index.js**：仅 `ensurePreset` 内 warn 调用的参数拼接串（-1/+3），`return outcome` 及渲染逻辑未动。
- 复跑测试全绿（§3）佐证：301 passed + 102 subtests，含 dsh 契约/兼容/适配器三面。

### 2.4 一致性 — PASS

十个面统一呈现同一语义三角：**真实用户根刷新正道 = `git pull` + 重启 dsh（`ensurePreset()` 按包版本幂等重渲染）**；**`--sync` 仅限显式重定向 `DSH_HOME` 的隔离环境**；**对真实根设计性拒绝 exit 2**。中英文表述（docstring/manifest/lib 为英文，中文文档为中文）语义等价无漂移。

### 2.5 纯粹性 — PASS

35+/24- 全部落在声称锚点内；无顺手重构、无格式化噪音（行尾警告为既有 CRLF/LF 状态，非本改动引入的内容问题）；无范围外文件；`.governance/**` 与全部豁免路径零接触。

### 2.6 R5 措辞 — PASS

修改面内无「真实环境安装/真机安装」类违禁表述。隔离验证措辞采用规范形态：根 README L109「isolated-env only, DSH_HOME redirected to a temporary directory」；dsh_doctor.py S6「DSH_HOME redirected to a temporary directory」；中文面「显式重定向 `DSH_HOME` 的隔离环境」。

## 3. 独立复跑事实（审查者本人执行）

| 命令 | 结果 | exit |
|---|---|---|
| `verify_workflow.py check-agent-adapters` | 6 adapter runtime-verified，contracts synchronized | **0** |
| `verify_workflow.py check-cross-references` | 77 files / 733 refs，全部 PASS | **0** |
| `verify_workflow.py check-projection-sync` | source 0.95.0，28 mirrors，PASSED | **0** |
| `verify_workflow.py check-entry-bootstrap-sync` | repo-root + e2e-fixture + dsh-dialect(3633B/37L) PASSED | **0** |
| `pytest test_dsh_adapter + test_dsh_compat + test_dsh_contract -q` | **301 passed, 102 subtests passed** in 51.22s | **0** |

Developer 声称的验证数字（77/733、28 镜像、301+102）与审查者独立复跑**逐项吻合**。

## 4. 发现清单

| # | 级别 | 位置 | 发现 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | `adapters/dsh/README.md` L29 | shell 代码块的命令位置放自然语言：`git -C <仓库> pull; 重启 dsh`。逐字复制（替换占位符后）git pull 会执行、随后「重启」不是命令会报 not found。块内 `<仓库>` 占位符已表明非逐字复制块，注释亦已解释语义，故仅为形式瑕疵；对照根 README.md L109 的处理（整行改 `#` 纯注释行）更妥 | 将「重启 dsh」移入注释或仿根 README 用纯注释行呈现 |
| F-2 | P3 | 根 `README.md` L107/L110、`adapters/dsh/README.md` L26 | 紧邻的 `--install`/`--uninstall` 行仍以「user preset root」语境呈现，而 `write_side_refusal` 对三者一视同仁拒绝真实根。FIX-433 范围仅限 `--sync`，这些行未被要求改、也确未改（超范围反而违规）；但 L109 新注释只点名 `--sync` 被拒，读者可能推断 `--install` 可对真实根执行（如降级行 `git checkout v<旧tag> + --install` 同为死路） | 未来候选：写侧旗标（`--install`/`--uninstall`）指引面同等 sweep 或补一句「写侧旗标一律隔离限定」 |
| F-3 | P3 | `docs/architecture/ADR-020` L42/L289、`docs/reviews/review-FEAT-073-R0.md` L47 | 含 `launch.py --install/--sync 单次装配` 表述。内容是渲染管线构造事实/历史审查记录，**不构成升级死路指引**（不教「git pull 后 `--sync` 刷真实根」），故不判遗漏；但 docs/architecture 与 docs/reviews 不在任务列举的显式豁免清单（docs/release·requirements·marketplace、project/CHANGELOG.md）内 | 未来任务明确豁免清单时将 ADR/reviews 目录显式入账，避免逐案边界判断 |

无 P0、无 P1。

## 5. 终裁

**APPROVED_WITH_NOTES**（unresolved_blockers = 0）。

理由：16 锚点 sweep 全覆盖、守卫逻辑零触碰、live 面零死路残留、四项 check 与三文件 pytest 独立复跑全绿、R5 措辞合规；唯一 P2 为代码块形式瑕疵（不破坏语义、不误导为危险操作），P3×2 为范围外观察。改动可合并；F-1 可随下次文档触达顺手修复，F-2/F-3 登记为未来候选。

---

*审查依据：git status/diff 工作区事实、launch.py L826/L855-922/L1803-1809 直读、全仓库 grep 残留分类、审查者独立复跑输出（§3）。本报告为审查者唯一写入文件。*
