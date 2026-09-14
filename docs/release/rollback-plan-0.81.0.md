# Rollback Plan — 0.81.0（REL-077）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.81.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.81.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；真实环境面仍未验证（真机三项由用户手动执行回贴，未回贴前一律标「未验证」），非 Windows 平台未验证。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张；本版的隔离验收 = 「隔离环境安装冒烟（环境变量重定向至临时目录）通过」，不等于真实外部首会话验证通过。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；do not claim 1.0.0 production-ready。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **纯数据/声明（新增）** | `adapters/dsh/host-contract.json`（契约数据）、`adapters/dsh/fixtures/host-facts-*.json`、`core/releases/0.81.0.json` | **无副作用**——删除/回退文件即可，无运行时状态 |
| **新增代码（加性）** | `infra/dsh_contract.py`、`infra/checks/dsh_boundary.py`（Check 28w）、`infra/dsh_doctor.py`、`infra/tests/dsh_fixtures.py` | **加性**——0.80.0 不引用它们；回退后成为未使用文件（`cleanup.py` 会按 manifest diff 清理） |
| **消费方改造（行为保持）** | `lib/index.js`（契约绑定 + 惰性化 + JS `schema_version` fail-closed）、`infra/dsh_compat.py`（零校验不得 PASS + group 语义对齐 + 惰性绑定）、`adapters/dsh/launch.py`（渲染/解码守卫 + `DSH_HOME` 收敛 + 写入守卫对称化） | **需重装预设**——见 §2.2（渲染产物仅 persona 版本行随版本号变化（0.81.0 = `6caf90fe…e55d` / 0.80.0 = `00e0d330…3723`，其余字节不变），但代码路径变化） |
| **注册面（加性）** | `quickscan_registry.py` / `registry.py`（Check 28w 段 + `dsh-doctor` 命令）、`core/manifest.json` | 加性；回退后 0.80.0 的 82 命令 / 70 段计数恢复 |
| **行为变更（用户可感知，2 项）** | ① `launch.py --install` 对**缺失/不可读 `package.json`** 由 rc 0（写占位 `"0"` 标记）改为 **rc 1 拒绝**；② `--install`/`--sync`/`--uninstall` 在**真实 home 形态的 `DSH_HOME`** 下由可用改为 **exit 2 REFUSED**（`--dry-run` 仍放行） | **回滚即恢复旧行为**（含旧的"静默写占位版本"与"可写真实 home"风险）——回滚说明 MUST 明确告知这一取舍 |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> status --porcelain
# 2) 回退到本版之前的稳定点（二选一）
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.81.0 窗口 `d87ead8..e376ddf（0.81.0 发布 tip = transition 提交）`**：
#        起点 = `d87ead8`（0.80.0 线 tip；0.80.0 基线即实测于该提交，§4 验证 6）
#        终点 = **发布 tip**（M-5 transition 提交；其 hash 由 M-5 生成后回填，不预先编造）
git -C <plugin_root> revert --no-commit d87ead8..e376ddf（0.81.0 发布 tip = transition 提交）
#        区间**计数不写死**（FIX-334 / REVIEW-REL-077-RELEASE-R0 F-03：原稿"31 + 该冻结提交"少 1）：
#        M-5 现场以 `git rev-list --count d87ead8..e376ddf（0.81.0 发布 tip = transition 提交）` 取值记入 EVD。本文件写作时点实测
#        （tip = 门禁收口提交 `22cf185`）为 **34** = 31（Change Inventory 窗口 `d87ead8..3074120`）
#        + `5e6d8c7`（M-1 冻结推进）+ `a89341e`（候选打包）+ `22cf185`（门禁收口）；
#        候选打包点上的计数为 **33**（= 前述前 3 项之和）。
#        V8 `3074120` / V10 `61b571c` 仅为本区间末两个代表性交付，**不是**区间本身。
#        **终点为什么必须是发布 tip 而不是候选打包提交 `a89341e`**（F-04）：`a89341e..<tip>` 内的提交
#        修改了**区间内新增**的三件套 release 文档，故在 tip 上执行 `revert d87ead8..a89341e` 会冲突
#        （实测 3 处，见 §4「revert 干跑」行）；只有 `..e376ddf（0.81.0 发布 tip = transition 提交）` 才是"回到 0.80.0 行为"的完整区间。
#    (b) 直接切回稳定 tag
git -C <plugin_root> checkout v0.80.0
# 3) 重装适配层（隔离验证后再对真实环境执行）
$env:DSH_HOME = "<用户 DSH home>"; python adapters/dsh/launch.py --install
```

**注意**：0.81.0 的**行为变更②**在回滚后**消失**——即 `--install` 重新允许写真实 home。回滚后 MUST 提醒使用者：不要在不隔离的 shell 里执行 `--install`（这正是本版修掉的事故面）。

### 2.2 用户侧（受影响用户）

预设是**可再生产物**，回滚不需要用户手工编辑：

1. 回退插件版本（上节）；
2. 运行 `python adapters/dsh/launch.py --sync`（或重启 dsh 让 JS 侧 `ensurePreset()` 重建）；
3. 校验：回滚后 `agent.cordis.yml` 的 sha256 应等于 **0.80.0 基线** `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`（0.81.0 候选态实测为 `6caf90fec1f2773eaa0128f0fa5c7a7795b512c8a36d603f5cd6e939ff48e55d`（16796 bytes）——两者差异**恰为 persona 版本行 1 处**（`治理工作流（v0.81.0）` → `（v0.80.0）`），即版本行变更的必然结果；故回滚**会**把该行改回 `v0.80.0`，**除该行外**预设内容逐字节不变）。

## 3. 数据安全（回滚不损坏用户数据）

- 本版**不新增任何用户数据文件**；`~/.dsh/.agent-presets/governance/` 的 4 个文件全部是**可再生的渲染产物**（含 `.dsh-bundle-version` 幂等标记）。
- 本版**不改动** dsh 宿主既有配置行、不注册宿主平面服务、不写 `settings.yaml`（`check-dsh-preset-smoke` 实测 `real-home writes: 0`）。
- 因此回滚的**唯一数据动作**是"重新渲染预设"，最坏情形是"预设暂时未渲染"（下次启动重建），**无数据丢失路径**。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证 | 期望 |
|---|---|---|
| 1 | `check-version-consistency` | PASSED（版本声明回到 0.80.0） |
| 2 | `check-projection-sync --fail-on-issues` | PASSED |
| 3 | `check-manifest-consistency --fail-on-issues` | PASSED |
| 4 | `check-dsh-preset-smoke`（28u，`DSH_HOME=%TEMP%`） | exit 0 + `real-home writes: 0` |
| 5 | 三路径渲染 sha256（**回滚后**） | `00e0d330…3723`（**0.80.0 基线值**；0.81.0 候选态为 `6caf90fe…e55d`，两者差异仅 persona 版本行 1 处） |
| 6 | `test_dsh_compat` / `test_dsh_contract` / `test_dsh_adapter` | 回到 0.80.0 基线（**实测于 `d87ead8` = 0.80.0 tip**：`test_dsh_compat` **43** / `test_dsh_adapter` **46**；`test_dsh_contract` **本版新增**（0.80.0 时该文件不存在），回滚后应为"文件不存在"） |
| 7 | 预设页面与会话可用性 | 宿主可正常启动、治理会话技能完整（**真机项，需用户回贴**） |
| 8 | **revert 干跑（回滚演练）** | **已执行**（隔离 worktree，主工作树零试跑）：区间 `d87ead8..a89341e` 在 `a89341e` 上 **干净**（0 冲突，80 路径 = 39 删除 + 41 修改）；同一区间在当前 tip `22cf185` 上 **3 处冲突**（三件套 release 文档）⇒ 证明终点必须是**发布 tip**。详见下方演练记录。 |

### 4.1 revert 干跑记录（回滚演练 —— SKILL 硬门槛「至少一次」）

**执行方式**：全部在 `%TEMP%` 的**隔离 git worktree** 内进行（`git worktree add --detach <dir> <commit>`），主工作树**零 revert 试跑**、零 `git stash`；每次干跑后 `git revert --abort` 复原并 `git worktree remove --force` 删除隔离副本。

| 干跑 | 隔离 worktree 起点 | 命令 | 退出码 | 冲突 | 涉及文件数 |
|---|---|---|---|---|---|
| A（预设终点 = 候选打包提交） | `a89341e` | `git revert --no-commit --no-edit d87ead8..a89341e` | **0** | **0** | **80**（39 `D` + 41 `M`） |
| B（同一区间在当前 tip 上） | `22cf185`（= 写作时点发布 tip） | 同上 | **1** | **3**（`docs/release/feature-flags-0.81.0.md`、`docs/release/release-checklist-0.81.0.md`、`docs/release/rollback-plan-0.81.0.md`，均 `UU`） | 35（5 `D` + 27 `M` + 3 `UU`） |

**结论**：① 区间 `d87ead8..a89341e` 在候选打包点上可无冲突回退（80 路径）；② 但在**发布 tip** 上执行同一区间会因**区间外提交改动了区间内新增的三件套**而冲突（3 处）⇒ 回滚 MUST 以 `d87ead8..e376ddf（0.81.0 发布 tip = transition 提交）` 表达区间（区间整体覆盖 post-candidate 提交，包括三件套的修改），而不是 `..a89341e`；③ 干跑 B 的 `git revert --abort` 复原后 worktree 干净、主工作树 `git status --porcelain` 仍只有本次修复涉及的文件。

## 5. 不可回滚项（如实列出）

| 项 | 说明 |
|---|---|
| `v0.81.0` 的 annotated tag | 若已推送，则不删除（回滚通过新增 revert 提交表达，不改写已推送历史） |
| **补推的 `v0.79.0` / `v0.80.0` tag** | 属历史对齐，非本版功能，回滚不影响 |
| 已落库的治理记录（`.governance/**`、`EVD-*`、`REVIEW-*`） | 历史不可改；回滚以**新增**记录表达（治理记录不进 git） |

## 6. 回滚触发条件

1. 宿主在安装 0.81.0 后出现**启动失败 / 预设页异常 / 新会话不可用**（dsh 升级事故族）；
2. 契约读取失败导致护栏整体不可用**且** 28u/28v 无法给出可用裁决；
3. 真机三项验收（`docs/release/real-machine-acceptance-0.81.0.md`）出现**回归级**失败；
4. 用户明确要求回退。

**决策权**：1/2/3 由 Coordinator 升级用户裁决（M-4 范围）；4 由用户直接决定。

---

*M-1 冻结完成（2026-09-13）；FIX-334 于 2026-09-14 按 REVIEW-REL-077-RELEASE-R0 F-03/F-04 更正区间表述与计数并补演练记录。V8/V10 终态（`3074120` / `61b571c`）已按实测回填；**回滚区间 = 整个 0.81.0 窗口 `d87ead8..e376ddf（0.81.0 发布 tip = transition 提交）`**——写作时点 tip = 门禁收口提交 `22cf185`，`git rev-list --count d87ead8..22cf185` = **34**；候选打包提交 `a89341e` 上为 **33**（= 31 + `5e6d8c7` + `a89341e`）。原稿「31 commits + 本候选打包提交」= 32 **少 1**（REVIEW-REL-077-RELEASE-R0 **F-03**）；区间终点由「候选打包提交」改为**发布 tip**（同报告 **F-04**，依据 = §4.1 的两次 revert 干跑：候选点上 0 冲突 / 发布 tip 上 3 处冲突）；V8/V10 只是该区间末两个代表提交、不是区间本身（REVIEW-REL-077-CODE-R0 **F-01** 更正；候选打包提交 = `a89341e`（由 ledger 派生））。本文件作为 M-2 门禁「回滚方案」的交付物参与 `check-release`。*
