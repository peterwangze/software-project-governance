# Rollback Plan — 0.81.0（REL-077）

- **状态**：**M-1 冻结**（2026-09-13）——行为清单已确定；`V8` 交付项与最终 commit 清单已按实测回填。**回滚区间 = 整个 0.81.0 窗口 `d87ead8..<0.81.0 候选打包提交>`**（实测 `d87ead8..3074120` = **31 commits**，加本候选打包提交本身）；`61b571c`（V10）/ `3074120`（V8）**仅为本区间末两个代表提交，不是区间本身**——原稿把区间写成这 2 个提交，按文执行会留下 29 个 0.81.0 提交、回不到 0.80.0 行为（REVIEW-REL-077-CODE-R0 **F-01** 已更正）。
- **对应版本**：0.81.0（dsh 宿主兼容性体系化）；前置稳定版本 = **0.80.0**（tag `v0.80.0`）。
- **回滚目标**：在不损坏用户数据的前提下，把插件恢复到 0.80.0 行为。

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
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.81.0 窗口**：
#        起点 = `d87ead8`（0.80.0 线 tip；0.80.0 基线即实测于该提交，§4 验证 6）
#        终点 = 本版候选打包提交（= `docs/release/release-checklist-0.81.0.md` 的冻结提交）
git -C <plugin_root> revert --no-commit d87ead8..<0.81.0 候选打包提交>
#        实测区间含 31 个提交（本文件配套的 Change Inventory 全表 `d87ead8..3074120`），加候选打包提交本身；
#        V8 `3074120` / V10 `61b571c` 仅为本区间末两个代表性交付，**不是**区间本身。
#        候选打包提交的 hash 此刻由 M-2 期 `release-ledger --version 0.81.0 --no-remote` 从 git 派生后回填——
#        它是本 checklist 的冻结提交，故本文件不预先编造该 hash。
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

*M-1 冻结完成（2026-09-13）。V8/V10 终态（`3074120` / `61b571c`）已按实测回填；**回滚区间 = 整个 0.81.0 窗口 `d87ead8..<0.81.0 候选打包提交>`（实测 31 commits + 本候选打包提交），V8/V10 只是该区间末两个代表提交、不是区间本身**（REVIEW-REL-077-CODE-R0 **F-01** 更正；候选打包提交的 hash 待 M-2 期 ledger 派生后回填，本文件不编造）。本文件作为 M-2 门禁「回滚方案」的交付物参与 `check-release`。*
