# FIX-313 代码审查报告（Code Review R0 — V10）

- **任务**：FIX-313（0.81.0，P2；设计切片 **V10**）`lib/index.js` catch 清理退化（防误删非己目录）
- **Round**：R0（首次审查）
- **审查对象 = 恰 2 文件**：`lib/index.js`（`git diff --numstat` = 66/13；工作树 sha256 `D16DD62A…`、blob `1d92205`）、`skills/software-project-governance/infra/tests/test_dsh_adapter.py`（187/0）
- **修前基线**：`HEAD:lib/index.js`（blob `a70e169`，sha256 `7B58CB8E…`；经 `git hash-object` 逐字节核对 ≡ `2d66d0f:lib/index.js`）
- **Reviewer**：Code Reviewer Agent（只读；全部实验在 `%TEMP%\fix313-r0`；**真实 `~/.dsh` 零写入**）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0；P1×1 / P2×3 / P3×4）

> **基线更正（F6）**：派发时称 HEAD `9e80c6a`，审查时实测 HEAD = **`a5e762295085e81664793b0767c5a3f2d91bea52`**（晚 3 个 REL-077 文档提交）；`git diff 9e80c6a HEAD -- <2 files>` 为**空** ⇒ 受审 diff 逐字节同一，结论不受影响。
> **边界声明**：不评判并发写入者（V8/FEAT-031）的在制改动（`registry.py`/`quickscan_registry.py`/`verify_workflow.py`/`test_registry.py`/`core/manifest.json`/`checks/dsh_boundary.py`/`dsh_doctor.py`/`fixtures/*`/`architecture-baseline.json`/`archguard_ratchet.py`/`snapshots.json`）。因「`check-governance` FAIL 41→41」「manifest-consistency PASSED」两项的自述载体属并发文件，**本审查不以其为采纳依据**，改用可归属 V10 的等价证据。

## 1. 缺陷真实且可达 —— 两条均独立复现（RED）

| 场景 | 触发机制 | 修前（RED） | 修后（GREEN） |
|---|---|---|---|
| **S1** | `preset.yml` 换成同名目录 ⇒ `EISDIR`（抛出点在 staging 树写完后） | preset root 被清空 ⇒ 用户 `governance.staging-personal-scratch/NOTES.md` **连同真 staging 一起被删** | 用户目录存活，**且插件自己的 staging 仍被正常清理**（正相对照） |
| **S2** | `resolveDshHome()` 抛错 ⇒ `outcome.dir=''`、`presetId='governance'` ⇒ `dirname('.')` 扫**进程 CWD** | **CWD 中两个 `governance.staging-*` 目录全被删** | 全部存活 + fail-safe 告警「nothing was removed」 |
| **S3** | 模板换成目录 ⇒ **staging 创建之前**抛错 | 用户目录被删（缺陷(a) 第二触发路径） | 存活 + 同上 |
| **S4/S4b** | 钉住 `Date.now`/`Math.random` 制造**同名碰撞** | 用户同名目录及文件被 `rmSync` **前置删除** | 完好；8 次熔断零删 / 换名重试后**正常同步成功** |
| **S7** | `logger.info` 抛错（**rename 成功后**） | 用户目录仍被删（成功同步亦有爆炸半径） | 完好；preset 4 文件完好 |

**可达性澄清（重要）**：设计 §6.1 记「触发条件未复现」。实测 —— (a) **预设根路径确定性可达、无需注入**；(b) **CWD 一支在 Windows 上无法靠清空环境变量触发**（清空全部 home 变量后 `os.homedir()` 仍返回真实路径，且命名空间改写对 ESM 具名绑定无效）⇒ 审查方改用 **ESM `registerHooks` 故障注入**（受审件 blob 前后一致、未改动）端到端复现。**Developer 的「可达」论证成立，但 CWD 一支的触发条件在 POSIX / 注入侧** —— 这直接决定 F1 的 fixture 设计。

## 2. 修法正确性（独立复核）

- **所有权证明链完整**：`stagingCreated` **仅 1 个写入点**（`:498`，紧跟**非递归** `mkdirSync` 正常返回），3 个读取点；`mkdirSync` 抛错路径保持 `false`（S3 走 else 分支、实测零删）。
- **成功后 `staging` 无重赋值**（循环条件 `attempt < 8 && !stagingCreated`）⇒ catch 中的 `staging` 恒为被创建路径，无「名字漂移」。
- **无无限循环**（上限 8，S4 实测熔断返回）；**碰撞后不误删**（EEXIST 只重试）。
- **`rmSync(staging)` 在 rename 后为 no-op**（S7 实测）。
- **fail-safe 全分支成立**：创建前失败 ⇒ 不删 + 告警；8 次熔断 ⇒ 不删 + 点名确切父路径；已创建后失败 ⇒ 只删精确路径；清理自身抛错 ⇒ 不抛出 + 给出确切残留路径。**「删了但没证明」的残余分支 = 0**（新代码无任何按名匹配/枚举式删除）。
- **`rmSync(userDir)` 保留正确**：`userDir` 由契约（`host.env.home_var`/`host.home.user_preset_dir`/`own.preset.id`）经 `resolveDshHome` 派生的**确定性绝对路径**，非对枚举结果做名字匹配；被 `write_policy: staging+rename` 语义必需，且有版本标记幂等短路。该行**未被 diff 触及** ⇒ 不属本片范围。**准确表述是「契约指定目标」，不是「已证明属己」**。

## 3. 行为保持（全部通过）

渲染 sha256 **`00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`**（16796 B，`leftovers=[]`）**JS ≡ Python ≡ 修前 ≡ 修后**；导出面 4 项与契约一致；顶层零 I/O 实测（包/cwd/DSH_HOME 指纹不变）；`node --check` exit 0；**无死代码**（`presetId` 已移除，13 个标识符全在用）；同一包路径下 userDir 4 文件 sha256 修前≡修后且二次运行幂等；三套件 **50 / 120 / 120 OK**（含一次 R1 隔离复跑）。

## 4. Findings

| ID | 级别 | 位置 | 问题（事实） | 独立证据 | 建议 |
|---|---|---|---|---|---|
| **F1** | **P1** | `test_dsh_adapter.py:1402-1517` + `lib/index.js:547-561` | **设计 §6.1 V10 验收①（G-04 CWD 退化反相）无任何机器守卫**：3 条新用例均未触发该路径（test1/2 的失败点是 EISDIR 且 `DSH_HOME` 已设 ⇒ `outcome.dir` 非空；test3 不执行产品代码） | **M5 部分回归变异**（仅在「无已证明 staging」分支复原旧前缀扫描）⇒ 整个 adapter 套件 `Ran 50 … OK`，而同一 M5 件在 S2 下**仍删除 CWD 中从未创建的目录** | ① 补反相 fixture（cwd 预置 staging 名 + 令 `resolveDshHome()` 抛错；**Windows 需 Node ≥22.15 的 ESM `registerHooks` 注入，仓声明 engines≥20 ⇒ 需 skip/NOT_RUN 政策**）；**或** ② 在 Gate/证据面显式记录「验收①由外部证据（本审查 S2/S3/S4）成立」并登记跟进任务。**⚠️ 发布/CHANGELOG 若声称「验收① 有测试守卫」即为不实陈述** |
| F2 | P2 | `test_dsh_adapter.py:1480-1517` | `test_cleanup_ownership_predicate_is_load_bearing` **不加载也不执行 `lib/index.js`**：重放被删实现三步形状 + `rmtree` 自己的 fixture，断言**自证式** ⇒ **零回归捕获力** | M1/M2/M3/M4 下该用例**一律 ok** | 删除，或改造成 F3 的真实碰撞 guard（推荐后者——一次改动同时关闭 F1/F2/F3） |
| F3 | P2 | `lib/index.js:494-511` | 新增的 **EEXIST 换名重试 + 8 次熔断 + 其告警路径无测试** | M4（复原 adopt-and-destroy）下 3 用例全 OK；S4/S4b 证明差异真实 | 加碰撞 fixture（钉住 `Date.now`+`Math.random`） |
| F4 | P2 | `lib/index.js:530-561` | 修后**失去唯一的孤儿 staging GC 路径**（旧前缀扫描虽不安全，却是崩溃遗留的唯一清理者）⇒ 孤儿在 `<dshHome>/.agent-presets/` 内永久累积。**属 P7 安全换整洁的有意权衡，但未被任何文档登记** | S1/S7：任何 `governance.staging-*` 修后一律存活 | 在设计/module 注释显式登记该权衡；**未验证项**：宿主是否把 `.agent-presets/` 下兄弟目录当作候选 preset 枚举（无证据，**不作断言**） |
| F5 | P3 | `lib/index.js:488-490,535` | 注释写 `created`，实际变量名 `stagingCreated` | 读码 | 改注释（纯文本） |
| F6 | P3 | 基线声明 | 见文首「基线更正」 | 实测 | 记录基线用 `a5e7622` + blob 哈希 |
| F7 | P3 | 设计 §6.1「改 `lib/index.js`（1-3 行）」vs 实测 +66/−13 | 规模超设计下限（重试循环 + 2 条告警 + 17 行注释块），**属必要扩展**：S4 证明 pre-mkdir `rmSync` 本身具破坏性 | S4/S4b | **发布注记按实际改动面描述（勿写「1-3 行」）** |
| F8 | P3 | `lib/index.js:526` `rmSync(userDir)` | 保留**正确**；残余观察：删目标前无「属己」判据，唯一信号是契约派生路径 + 版本标记短路 | 读码 + 契约 | 无需修改；**不得**在文档中称该路径「已证明属己」 |

## 5. 测试有效性（变异矩阵）

| 变异 | 内容 | 结果 |
|---|---|---|
| M0 | 修后原样 | `Ran 3 OK` |
| **M1** | **修前件（还原前缀删除）** | **`FAILED (failures=2)`** —— 完全复现 Developer 自述 |
| **M2** | 清理改为「永不删除」 | **正相对照 FAIL** ⇒ 「一概不删」被拦下，**正相对照是承重的** |
| M3 | 去掉 `stagingCreated` 判据 | 3 项全 OK ⇒ 该判据未被钉住（但在当前循环结构下不可被利用，属防御性冗余） |
| M4 | 复原 `rmSync(staging)`+递归 `mkdirSync` | 3 项全 OK ⇒ **碰撞分支零覆盖**（F3） |
| **M5** | **部分回归**（仅复原「无证明」分支的旧扫描） | **全量套件 50 OK 而 CWD 误删仍在** ⇒ **验收①无守卫（F1）** |

⇒ test1/test2 是真守卫；**test3 自证式、零捕获力（F2）**，且**不能**替代验收①要求的反相 fixture。

## 6. 结论与处置

**APPROVED_WITH_NOTES / `unresolved_blockers=0`** —— 修复逻辑正确，两条缺陷经独立复现证明确实存在且被消除，正常路径逐字节不变，无 P0/无 BLOCKING。

**Coordinator 裁决（本报告出具后执行）**：**采 F1 路径 ②**（显式记录验收①由外部证据成立 + 登记跟进任务 **FIX-325** 承载 F1 fixture / F2 改写 / F3 碰撞 guard / F4 权衡登记），并在发布文档中**不得**声称验收①有测试守卫。

## 7. 真实环境命令上报表（R4）

7 类命令全部只读或落 `%TEMP%\fix313-r0`（1130 文件副本）：`git` 只读子命令；`robocopy` 到 `%TEMP%`；`node *.mjs`（S1–S7，`DSH_HOME`/`HOME`/`USERPROFILE` 全重定向）；`python` 变异/runner；三套件（含一次 R1 隔离复跑，套件内部自建 `%TEMP%` home）；`import launch` 纯函数只读调用；`node --check`。**真实环境写入审计**：真实 `~/.dsh/.agent-presets/governance` mtime = **09:29:17** 而审查窗口 **11:50–12:02** ⇒ 未被写入；全部日志对 `C:\Users\peter\.dsh` **0 命中**；`~/.agent-presets` 不存在。**仓内零写入**（受审 2 blob 审查前后哈希一致）。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
