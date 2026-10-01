# Rollback Plan — 0.82.0（REL-078）

> **M-0 草案（REL-078 prep，2026-09-18）**——Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.81.0.md` 先例（含其 R0 F-01/F-03/F-04 三条区间教训）。回滚演练（§4.1）为 M-2/M-5 期义务，本草案不预填演练结果。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.82.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.82.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-0，2026-09-18）0.82.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含 M-0 起草期勘误注记 —— MUST 先读）

**回滚区间 = 整个 0.82.0 窗口 `e376ddf..<发布 tip>`**：

- **起点 = `e376ddf`**（0.81.0 发布 tip = transition 提交 = `v0.81.0` tag peel；0.81.0 基线即锚定于该发布态）；
- **终点 = `<发布 tip>`**（0.82.0 发布 tip = M-5 transition 提交；hash 由 M-5 生成后回填，**不预先编造**）；
- 写作时点计数不写死：M-5 现场以 `git rev-list --count e376ddf..<发布 tip>` 取值记入 EVD。M-0 起草期已知构成 = 0.82.0 载荷 **11 commits**（`8bd6a8a` 至 `845c050` **含首提交**——git 记法 `8bd6a8a..845c050` 语义为不含首的 10，本计数按含首即 `git rev-list --count 8bd6a8a^..845c050` = 11，FIX-339~346 批）+ FIX-338 发布后修复 **3 commits**（`1db58f5`/`02ad554`/`dfafa95`）+ M-0 prep 批（本三件套/CHANGELOG/FIX-324/326 并入/日期炸弹修复）+ M-1 候选打包 + M-2/M-3 门禁与审查批 + M-5 transition——后四类在起草期未提交。

> **⚠️ 勘误注记（区间锚定，照 0.81.0 先例 R0 F-01 教训）**：REL-078 M-0 任务书原文将区间写作 `845c050..<发布 tip>`。`845c050` 为**当前 HEAD**（0.81.0 发布后修复线 tip，其上已含 FIX-338 三个发布后修复 commits），**不是** 0.81.0 发布 tip；以 `845c050` 为起点的区间**不覆盖已落库的 0.82.0 载荷**（`8bd6a8a` 至 `845c050` 含首共 11 commits——FIX-339/341/312/314/342+344/320+322/345/323+325+336/333/332+337/313+346），按该区间 revert 将留下全部 0.82.0 引擎改动、回不到 0.81.0 行为——与 0.81.0 回滚审查 R0 **F-01**（"原稿区间误写两个代表提交，按此 revert 将留下 29 个 0.81.0 提交、回不到 0.80.0 行为"）**同形**。故本文件按 0.81.0 先例语义以 **`e376ddf..<发布 tip>`** 为完整回滚区间，并如实登记该锚定差异；0.81.0 先例 **F-04**（区间终点必须是发布 tip 而非候选打包提交——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突）同理适用于终点。M-3 Release Reviewer 复核本节。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **引擎判定面（行为变更主体）** | `verify_workflow.py` 窗口净变更（FIX-339 版本锚参数化与面判据 / FIX-312+342 归档判据 / FIX-341 tpa 归档索引 / FIX-344 Check 30c 后缀感知 / FIX-345 authority 双锚） | **回滚即恢复 0.81.0 判定行为——含已知缺陷面回归，逐项如实列出**：① `hot fact source` 9 条 0.38.x 假阳回归（FIX-339 修前面）；② loop-claims `installed_host` 回 **BLOCKED**（FIX-320 豁免账本随数据资产行一并回退）；③ Check 30c 第二半面假 WARN 复现（FIX-344 修前面）；④ G-04 CWD 守卫回「无机器守卫」形态（FIX-325 修前）；⑤ 新决策引用已归档 task 被误迁的面回归（FIX-312 修前） |
| **数据资产（新增文件）** | `core/loop-runtime-claim-exemptions.json`（FIX-320 豁免账本） | **加性**——回退后 0.81.0 不引用它；loop-claims 回 BLOCKED（0.81.0 已知基线，非数据丢失）；账本文件删除/回退本身 fail-closed（三锚断锚 FAIL，无静默放行路径） |
| **测试面** | FIX-323/325/336 守卫与收集面 + FIX-313 parity 测试 + FIX-346 预算定标 + 日期炸弹修复（test_change_triage） | 回退后测试基线回到 0.81.0 期清单：`test_dsh_compat` 在 discover 口径**整模块不可收集**（FIX-336 修前）⇒ 全量计数口径回 2983 族；日期炸弹用例回**必红**（`'WARN' not found in ''`）；性能预算回 8.0s 不可达断言 |
| **契约/manifest 注释** | `adapters/dsh/host-contract.json` 三处 evidence.* 写入路径 note 更正（FIX-326③，as-built 对齐）+ `adapters/dsh/adapter-manifest.json` dsh-doctor 登记一句（FIX-326①） | **纯注释/声明面**——回退恢复 0.81.0 字节与契约 SHA `96F92485…43FC6E`（74702 bytes）；回滚后 Gate 12 按 0.81.0 值记录。`recording.writer` 字段未动（钉扎测试 `test_recorded_evidence_is_not_hand_filled` 两态均绿） |
| **发布文档** | 本三件套 + `project/CHANGELOG.md` [0.82.0] 段 | 区间内新增文档——0.81.0 先例 F-04 实证「在发布 tip 上 revert 不完整区间会因这些文档冲突（实测 3 处 UU）」⇒ **回滚 MUST 以完整区间 `e376ddf..<发布 tip>` 表达** |
| **渲染/预设交付面** | **产品零变更**——窗口 diff 实测：`adapters/dsh/` 零改动；`lib/index.js` 仅注释面（FIX-313 DEC-196 注释真实性 + F4 权衡登记）；渲染语义与模板零触碰 | 回滚对预设产物**零影响**：渲染产物字节在 0.82.0 窗口内**除 persona 版本行外**全程不变（仅该行随 M-1 bump 变化——§2.2 第 3 步与 §4 验证表 #5 承载双值对照）；无需"重装预设"级回滚动作 |
| **治理记录面** | FIX-343 数据回填 / DEC-187 更正 / DEC-194 补记等（`.governance/`，gitignored） | **不进 git 窗口**——回滚不影响；治理记录历史不可改（§5） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> status --porcelain
# 2) 回退到本版之前的稳定点（二选一）
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.82.0 窗口
#        `e376ddf..<发布 tip>`**（<发布 tip> = M-5 transition 提交，hash 由 M-5
#        生成后回填；本文件写作时点该提交不存在，不预填）：
git -C <plugin_root> revert --no-commit e376ddf..<发布 tip>
#        区间计数不写死：M-5 现场以 `git rev-list --count e376ddf..<发布 tip>` 取值
#        记入 EVD。起点必须是 e376ddf（0.81.0 发布 tip）而非 845c050（HEAD）——
#        见「区间锚定」勘误注记（0.81.0 R0 F-01 同形教训）。
#    (b) 直接切回稳定 tag
git -C <plugin_root> checkout v0.81.0
# 3) 重装适配层（隔离验证后再对真实环境执行；0.81.0 B-2 写入守卫在回滚后仍有效——
#    该守卫属 0.81.0 交付，本窗口未触碰）
$env:DSH_HOME = "<目标目录（隔离临时目录）>"; python adapters/dsh/launch.py --install
```

**注意**：回滚后**恢复的已知缺陷面**（§1 引擎判定面行 ①~⑤）MUST 在回滚说明中如实告知——特别是 `hot fact source` 假阳回归与 loop-claims `installed_host` 回 BLOCKED（这两项在 0.81.0 期作为既有基线披露，本版修复）。

### 2.2 用户侧（受影响用户）

预设是**可再生产物**，回滚不需要用户手工编辑：

1. 回退插件版本（上节）；
2. 运行 `python adapters/dsh/launch.py --sync`（或重启 dsh 让 JS 侧 `ensurePreset()` 重建）；
3. 校验：回滚后 `agent.cordis.yml` 的 sha256 应等于 **0.81.0 基线** `6caf90fec1f2773eaa0128f0fa5c7a7795b512c8a36d603f5cd6e939ff48e55d`（**16796 bytes**，persona 版本行 = `治理工作流（v0.81.0）`）。0.82.0 候选态预期 = 同一 sha 语义、仅 persona 版本行变 `（v0.82.0）`（M-1 bump 后 M-2 实测回填，本草案不预填 0.82.0 渲染值）——因 0.82.0 对渲染语义零产品变更，两者差异**恰为 persona 版本行 1 处**（0.81.0 先例同构）。

## 3. 数据安全（回滚不损坏用户数据）

- 本版**不新增任何用户数据文件**；`~/.dsh/.agent-presets/governance/` 的文件全部是**可再生的渲染产物**（含 `.dsh-bundle-version` 幂等标记）。
- 本版**不改动** dsh 宿主既有配置行、不注册宿主平面服务、不写 `settings.yaml`（交付面产品零变更；0.81.0 期 `check-dsh-preset-smoke` 的 `real-home writes: 0` 判据在 0.82.0 M-2 复跑）。
- 豁免账本（`core/loop-runtime-claim-exemptions.json`）为仓库内受审数据资产，回退 = 恢复 0.81.0 判定行为（BLOCKED 既有基线），**无用户数据丢失路径**。
- 治理记录（`.governance/**`）gitignored 不进窗口——回滚零触碰；FIX-343 回填的归档行与 DEC-187 更正**不随回滚消失**（它们记录的是历史事实，非 0.82.0 引擎的运行时依赖）。
- 因此回滚的**唯一数据动作**是"重新渲染预设"，最坏情形是"预设暂时未渲染"（下次启动重建），**无数据丢失路径**。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证 | 期望 |
|---|---|---|
| 1 | `check-version-consistency` | PASSED（版本声明回到 0.81.0） |
| 2 | `check-projection-sync --fail-on-issues` | PASSED |
| 3 | `check-manifest-consistency --fail-on-issues` | PASSED |
| 4 | `check-dsh-preset-smoke`（28u，`DSH_HOME=%TEMP%`） | exit 0 + `real-home writes: 0` |
| 5 | 三路径渲染 sha256（**回滚后**） | `6caf90fe…e55d`（**0.81.0 基线值**，16796 bytes——persona 版本行回 `v0.81.0`） |
| 6 | 契约 SHA（**回滚后**） | `96F92485…43FC6E`（0.81.0 基线，74702 bytes——FIX-326③ note 更正回退） |
| 7 | `test_dsh_compat` / `test_dsh_adapter` / `test_dsh_contract` | 回到 0.81.0 基线形态；**如实注记**：discover 口径下 `test_dsh_compat` 回到「整模块不可收集」（FIX-336 修前面），全量计数口径回 2983 族——该"计数下降"是回滚的预期结果，不是回滚失败 |
| 8 | `check-loop-runtime-claims`（installed_host） | 回 BLOCKED（0.81.0 已知基线——豁免账本回退的预期结果，非回滚失败） |
| 9 | 预设页面与会话可用性 | 宿主可正常启动、治理会话技能完整（真机面——回滚后建议用户冒烟；非本版新增义务） |
| 10 | **revert 干跑（回滚演练）** | **M-2/M-5 期义务（≥1 次）**：在 `%TEMP%` 隔离 git worktree（`git worktree add --detach <dir> <commit>`）执行 `git revert --no-commit --no-edit e376ddf..<当时 tip>`，记录退出码/冲突/涉及文件数，`git revert --abort` 复原后删除隔离副本；主工作树**零 revert 试跑、零 `git stash`**。预期形态（按 0.81.0 先例 F-04 教训预判，以实测为准）：区间在候选打包提交上执行时，post-candidate 的 release 文档修改会造成冲突 ⇒ 终点必须是发布 tip。记录格式照 0.81.0 §4.1（干跑表：起点/命令/退出码/冲突/文件数 + 结论） |

## 5. 不可回滚项（如实列出）

| 项 | 说明 |
|---|---|
| `v0.82.0` 的 annotated tag | 若已推送，则不删除（回滚通过新增 revert 提交表达，不改写已推送历史） |
| 已落库的治理记录（`.governance/**`、`EVD-*`、`REVIEW-*`、FIX-343 回填行、DEC-187 更正） | 历史不可改；回滚以**新增**记录表达（治理记录不进 git） |
| 豁免账本的受审提交历史 | 账本文件可随区间回退，但其受审登记历史（FIX-320 审查链、EVD-1049）不可改写 |

## 6. 回滚触发条件

1. 0.82.0 引擎判定面出现**回归级事故**——如实数据被误 FAIL 洪泛（如版本锚派生误判活跃版本）或「未发布虚报已发布」防护在新数据形态下漏报；
2. 豁免账本完整性事故——三锚 fail-closed 误触发导致 `check-loop-runtime-claims` 在合法数据上整体不可用**且**无受审恢复路径；
3. 发布门禁（check-release / release-ledger / projection）在 0.82.0 态出现**不可解释的失真**，且 28u/28v 无法给出可用裁决；
4. 用户明确要求回退。

**决策权**：1/2/3 由 Coordinator 升级用户裁决（M-4 范围；DEC-197 标准链的停点逐项授权语义）；4 由用户直接决定。

---

*M-0 草案（2026-09-18，REL-078 prep——Release Agent 起草）。区间锚定勘误注记（`845c050` → `e376ddf`）为对照 0.81.0 回滚审查 R0 F-01/F-04 教训的更正，M-3 Release Reviewer 复核。`<发布 tip>` 占位由 M-5 生成后回填（不预先编造）；§4.1 回滚演练记录由 M-2/M-5 期按 0.81.0 §4.1 格式回填。本文件作为 M-2 门禁「回滚方案」的交付物参与 `check-release`。*
