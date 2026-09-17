# Rollback Plan — 0.83.0（REL-079）

> **M-0 草案（REL-079 prep，2026-09-17）**——Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.82.0.md` 先例（含 0.81.0 回滚审查 R0 F-01/F-03/F-04 与 0.82.0 区间勘误注记的区间教训）。回滚演练（§4 #10）为 M-2/M-5 期义务，本草案不预填演练结果。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.83.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.83.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-0，2026-09-17）0.83.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记 —— MUST 先读）

**回滚区间 = 整个 0.83.0 窗口 `24cfb04..<发布 tip>`**：

- **起点 = `24cfb04`**（0.82.0 发布线末位提交——post-transition integrity 公式修正；`v0.82.0` tag peel = transition 提交 `b63584c`。RELEASE R0 F-2 机核勘误 2026-09-17：`git rev-parse v0.82.0^{}` = b63584c 实测；区间起点值 24cfb04 不变——revert 24cfb04..tip 恰恢复 0.82.0 released 态含 integrity 修正）；
- **终点 = `<发布 tip>`**（0.83.0 发布 tip = M-5 transition 提交；hash 由 M-5 生成后回填，**不预先编造**）；
- 写作时点计数不写死：M-5 现场以 `git rev-list --count 24cfb04..<发布 tip>` 取值记入 EVD。M-0 起草期已知构成 = 0.83.0 载荷 **3 commits**（`57c6fc4` / `bf7e25a` / `589e99f`——FIX-348/349/350）+ M-0 prep 批（本三件套/CHANGELOG 段）+ M-1 候选打包 + M-2/M-3 门禁与审查批 + M-5 transition——后四类在起草期未提交。

> **⚠️ 先例教训注记（区间锚定，照 0.81.0 R0 F-01 / 0.82.0 勘误注记教训）**：起点必须是 0.82.0 **发布线末位**（`24cfb04`；`v0.82.0` tag peel = `b63584c`，见 §区间锚定勘误），**不是**当前 HEAD（`589e99f`——其上已含本版全部载荷）。以 HEAD 为起点的区间不覆盖 0.83.0 载荷（`57c6fc4`~`589e99f` 共 3 commits），按该区间 revert 将留下全部引擎判定面改动、回不到 0.82.0 行为——与 0.81.0 回滚审查 R0 **F-01**（区间误写代表提交，revert 后回不到上一版本行为）**同形**。终点必须是发布 tip 而非候选打包提交——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**，实测 3 处 UU）。M-3 Release Reviewer 复核本节。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **检查器判定面（行为变更主体）** | Check 16 同 EVD fan-out 判定口径（FIX-349③）+ Check 10 M5 record-doc 白名单扩展（FIX-348/DEC-198） | **回滚即恢复 0.82.0 判定行为——含已知过报面回归，逐项如实列出**：① Check 16 「模板复用」假阳面回归（是否复现 19 条取决于热数据形态——FIX-349 数据面不随 git 窗口回退，如实按回滚后当场 health 输出披露，不预判数字）；② `docs/requirements/**` 设计文档处置记录行误报回归（`m5_option_list_no_auq` 修前面——live 实例 `dsh-compat-design-0.81.0.md:292` 形态） |
| **新增扫描面** | Check 14 子检查 6——Unicode 行/段分隔符扫描（8 字符族含 U+000C，FIX-349⑥） | **防护面回退**（非已知缺陷回归，如实区分）：Unicode 分隔符检测面消失，EVD-890 形态的「不可见分隔符致扫描假阴性」重新不可机检；数据面（治理热文件残留已清除）不受回滚影响 |
| **ArchGuard 判定面/配置面** | 豁免 gate 四面扩展 + dup 三精确路径豁免（[EXEMPT] 披露）+ schema `project/**`/`.governance/**` 豁免 + release_docs 阈值 30→80 + ratchet 重锚 R1 24453→24583 / R4 print 1299→1301（FIX-350/DEC-201） | **回滚即恢复 0.82.0 判定面——三红回归**：① fixture 投影镜像（`project/**`）误报回归（28n 面）；② 镜像 dup 假阳回归（28p 面，无 [EXEMPT] 披露通道形态）；③ release_docs 阈值回 30——74 版本现状重新超阈红（28q release_docs_versions 面）；棘轮锚随代码回退回 24453/1299——**与 0.82.0 态自洽**（回滚后门禁按回退后锚判定，非 fail-closed 误报）；`.governance/**`/`project/**` 重新进架构扫描 |
| **治理数据面（FIX-349 数据批）** | Check 5/17 数据清零行 + DEC-199/DEC-200 落账 + EVD-1065 日期勘误 + REL-079 入账（`.governance/`，gitignored） | **不进 git 窗口**——回滚零触碰；已清理的数据行与新日期基线在 0.82.0 引擎下同样合法（数据卫生是纯改善，无回滚冲突）；Check 30 V2 ×1（RISK-051）两侧同在，不受影响 |
| **发布文档** | 本三件套 + `project/CHANGELOG.md` [0.83.0] 段 | 区间内新增文档——0.81.0 先例 F-04 实证「在发布 tip 上 revert 不完整区间会因这些文档冲突」⇒ **回滚 MUST 以完整区间 `24cfb04..<发布 tip>` 表达** |
| **渲染/预设交付面** | **产品零变更预期**——窗口三 commits 范围面未含 `adapters/dsh/` 渲染面（`lib/index.js`/`launch.py`/`cordis.patch.yml`）与 `host-contract.json`；渲染语义与模板零触碰（M-2 Gate 7/11/12 机检载体复核） | 回滚对预设产物**零影响**：渲染产物字节在 0.83.0 窗口内**除 persona 版本行外**预期不变（仅该行随 M-1 bump 变化——§2.2 第 3 步与 §4 验证表 #5 承载双值对照）；无需"重装预设"级回滚动作 |
| **豁免账本/既有开关** | 本版零触碰——`core/loop-runtime-claim-exemptions.json` 与 4 条豁免维持，0.82.0 既有开关全部保留 | 回滚对豁免账本与既有开关**零影响**（账本本版无改动，两侧版本同一文件状态） |
| **测试面** | FIX-349/350 新增用例（test_architecture_health.py +102、test_archguard_ratchet.py +7 等——DEC-201 ⑤ 追认批） | 回退后测试基线回到 0.82.0 期清单（0.82.0 终态 = `test_verify_workflow` 850 OK exit 0；discover 口径 3200 期）——**计数下降是回滚的预期结果，不是回滚失败**（§4 验证表 #7 如实注记） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> status --porcelain
# 2) 回退到本版之前的稳定点（二选一）
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.83.0 窗口
#        `24cfb04..<发布 tip>`**（<发布 tip> = M-5 transition 提交，hash 由 M-5
#        生成后回填；本文件写作时点该提交不存在，不预填）：
git -C <plugin_root> revert --no-commit 24cfb04..<发布 tip>
#        区间计数不写死：M-5 现场以 `git rev-list --count 24cfb04..<发布 tip>` 取值
#        记入 EVD。起点必须是 24cfb04（0.82.0 发布 tip）而非 589e99f（载荷线 tip）——
#        见「区间锚定」先例教训注记（0.81.0 R0 F-01 同形教训）。
#    (b) 直接切回稳定 tag
git -C <plugin_root> checkout v0.82.0
# 3) 重装适配层（隔离验证后再考虑后续动作；0.81.0 B-2 写入守卫在回滚后仍有效——
#    该守卫属 0.81.0/0.82.0 交付，本窗口未触碰）：
$env:DSH_HOME = "<目标目录（隔离临时目录）>"; python adapters/dsh/launch.py --install
```

**注意**：回滚后**恢复的已知缺陷面**（§1 检查器判定面行 ①~② + ArchGuard 行 ①~③）MUST 在回滚说明中如实告知——特别是 release_docs 阈值红（74 > 30）与 fixture 镜像/dup 假阳回归（这三项在 0.82.0 期作为既有红基线披露，本版修复）。

### 2.2 用户侧（受影响用户）

预设是**可再生产物**，回滚不需要用户手工编辑：

1. 回退插件版本——`git checkout v0.82.0`（维护者）或经插件市场重装 0.82.0 版本（用户侧降级路径）；
2. 运行 `python adapters/dsh/launch.py --sync`（或重启 dsh 让 JS 侧 `ensurePreset()` 重建）；
3. 校验：回滚后 `agent.cordis.yml` 的 sha256 应等于 **0.82.0 基线值**（⟦M-2 回填——取 0.82.0 期实测终值，见 `docs/release/rollback-plan-0.82.0.md` §2.2 回填段/0.82.0 checklist Gate 11 当场值；本草案不预填不编造⟧，persona 版本行 = `治理工作流（v0.82.0）`）。0.83.0 候选态预期 = 同一 sha 语义、仅 persona 版本行变 `（v0.83.0）`（M-1 bump 后 M-2 实测回填，本草案不预填 0.83.0 渲染值）——因 0.83.0 对渲染语义零产品变更，两者差异**恰为 persona 版本行 1 处**（0.81.0/0.82.0 先例同构）。

### 2.3 发布前中止（M-0~M-4 窗口）

- **仅中止发布工程批**（M-0 prep 批 / M-1 候选打包提交，未推送）：`git reset --hard <保留基线>`（默认保留基线 = `589e99f` 载荷线 tip——保留 FIX-348/349/350 载荷、仅丢弃 release 工程提交；`core/releases/0.83.0.json` candidate 与本地 `v0.83.0` tag〔若已打：`git tag -d v0.83.0`〕一并清理）；
- **连窗口载荷一并放弃**（仅当用户明确要求）：`git reset --hard 24cfb04`——回 0.82.0 发布 tip；
- **已推送后不得 reset**——改走 §2.1 revert 路径（新增 revert 提交表达，不改写已推送历史）；
- 纪律：`reset --hard` 属破坏性 git——default-confirm 模式 MUST 用户确认；maximum-autonomy 模式下亦属发布关键决策停点（DEC-200 预授权不免除——预授权覆盖 transition/tag/push 推进面，不覆盖中止面的破坏性操作授权）。

## 3. 数据安全（回滚不损坏用户数据）

- 本版**不新增任何用户数据文件**；`~/.dsh/.agent-presets/governance/` 的文件全部是**可再生的渲染产物**（含 `.dsh-bundle-version` 幂等标记）。
- 本版**不改动** dsh 宿主既有配置行、不注册宿主平面服务、不写 `settings.yaml`（渲染/预设交付面产品零变更预期；0.82.0 期 `check-dsh-preset-smoke` 的 `real-home writes: 0` 判据在 0.83.0 M-2 复跑）。
- 豁免账本（`core/loop-runtime-claim-exemptions.json`）本版零触碰——回滚前后同一文件状态，**无用户数据丢失路径**。
- 治理记录（`.governance/**`）gitignored 不进窗口——回滚零触碰；FIX-349 的数据清理行（Check 5/17 清零、日期勘误）与 DEC-199/DEC-200 落账**不随回滚消失**（它们记录的是历史事实，非 0.83.0 引擎的运行时依赖）。
- 因此回滚的**唯一数据动作**是"重新渲染预设"，最坏情形是"预设暂时未渲染"（下次启动重建），**无数据丢失路径**。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证 | 期望 |
|---|---|---|
| 1 | `check-version-consistency` | PASSED（版本声明回到 0.82.0） |
| 2 | `check-projection-sync --fail-on-issues` | PASSED |
| 3 | `check-manifest-consistency --fail-on-issues` | PASSED |
| 4 | `check-dsh-preset-smoke`（28u，`DSH_HOME=%TEMP%` 隔离） | exit 0 + `real-home writes: 0` |
| 5 | 三路径渲染 sha256（**回滚后**） | = **0.82.0 基线值**（⟦M-2 回填⟧——persona 版本行回 `v0.82.0`；0.83.0 窗口渲染语义零产品变更 ⇒ 差异恰为版本行 1 处） |
| 6 | 契约 SHA（**回滚后**） | = 0.82.0 released 终值（本窗口未触碰 `adapters/dsh/host-contract.json`——回滚前后预期同值，M-2/回滚后实测为准） |
| 7 | `test_verify_workflow` / 全量基线 | 回到 0.82.0 基线形态（850 OK exit 0 族 / discover 口径 3200 期）；**如实注记**：FIX-349/350 新增用例（+102/+7 等）随回退消失——**计数下降是回滚的预期结果，不是回滚失败** |
| 8 | `check-governance`（health） | 0.82.0 判定行为下的当场基线——**已知过报面回归如实披露**（Check 16「模板复用」假阳 / `docs/requirements` 误报 / release_docs 阈值红 74>30 / fixture 镜像与 dup 假阳回归），逐条归因「回滚预期结果」，不预判具体数字 |
| 9 | `check-release`（released 态复跑）+ 版本一致性回读 | `check-release --version 0.82.0 --require-changelog --lineage-mode released --release-commit 24cfb04` 裁决可用；`check-version-consistency` 全投影 = 0.82.0 回读一致 |
| 10 | **revert 干跑（回滚演练）** | **M-2/M-5 期义务（≥1 次）**：在 `%TEMP%` 隔离 git worktree（`git worktree add --detach <dir> <commit>`）执行 `git revert --no-commit --no-edit 24cfb04..<当时 tip>`，记录退出码/冲突/涉及文件数，`git revert --abort` 复原后删除隔离副本；主工作树**零 revert 试跑、零 `git stash`**。预期形态（按 0.81.0 F-04 教训预判，以实测为准）：区间在候选打包提交上执行时，post-candidate 的 release 文档修改会造成冲突 ⇒ 终点必须是发布 tip。记录格式照 0.81.0 §4.1（干跑表：起点/命令/退出码/冲突/文件数 + 结论） |

## 5. 不可回滚项（如实列出）

| 项 | 说明 |
|---|---|
| `v0.83.0` 的 annotated tag | 若已推送，则不删除（回滚通过新增 revert 提交表达，不改写已推送历史） |
| 已落库的治理记录（`.governance/**`、`EVD-1064~1067`、`REVIEW-FIX-348/349/350-*`、DEC-198~201、RISK-051、FIX-349 数据清理行） | 历史不可改；回滚以**新增**记录表达（治理记录不进 git） |
| Check 30 V2 缺口承载记录（RISK-051/DEC-199 (a)） | 历史缺口的「如实保留」裁决不随回滚改变——0.82.0 引擎下该缺口同样不可补造 |

## 6. 回滚触发条件

1. 0.83.0 判定面变更出现**回归级事故**——过报消除面意外吞掉真实违规（如 Check 16 判定收窄后真实模板复用/证据质量问题不再被任何机检面发现），或 ArchGuard 豁免面放行真实架构漂移且无受审恢复路径；
2. Unicode 扫描面（Check 14 子检查 6）在合法治理数据上产生洪泛级误报，导致 /governance 健康信号不可用；
3. 发布门禁（check-release / release-ledger / projection）在 0.83.0 态出现**不可解释的失真**，且 28u/28v 无法给出可用裁决；
4. 用户明确要求回退。

**决策权**：1/2/3 由 Coordinator 升级用户裁决（M-4 范围；DEC-200 预授权不免除——预授权覆盖推进面，回滚触发属停点授权语义）；4 由用户直接决定。

---

*M-0 草案（2026-09-17，REL-079 prep——Release Agent 起草）。区间锚定（起点 `24cfb04` = 0.82.0 发布线末位；tag peel = b63584c——F-2 机核勘误 2026-09-17）为对照 0.81.0 R0 F-01/F-04 教训的先例延续，M-3 Release Reviewer 复核。`<发布 tip>` 占位由 M-5 生成后回填（不预先编造）；§4 #10 回滚演练记录由 M-2/M-5 期按 0.81.0 §4.1 格式回填；渲染 sha256 双值（0.82.0 基线 / 0.83.0 候选）由 M-2 实测回填。本文件作为 M-2 门禁「回滚方案」的交付物参与 `check-release`。*
