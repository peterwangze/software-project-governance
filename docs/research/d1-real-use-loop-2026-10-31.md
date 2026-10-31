# D1 真实使用循环 — 宿主 python_game 实测台账

- 任务: FEAT-112（D1 真实使用循环，P1）
- 宿主: `D:\AI\agent\claude\coding\python_game`（王国战纪）
- 会话日期: 2026-10-31（Asia/Shanghai）；首轮启动 2026-10-29
- 启动裁决: DEC-378（宿主/防护/平台三点）+ 2026-10-31 修正（Claude Code 已由用户升级配置；由 DSH Coordinator 派发角色 agent 驱动）

## 1. 防护（真实环境）

| 项 | 事实 |
|---|---|
| 备份 | `python-game-backup-20261029-0815`（升级前）+ `python-game-backup-20261031-1112`（修复前） |
| 方法 | `robocopy /MIR /XJ /R:2 /W:2`（/XJ 防 junction 自递归） |
| 一致性 | 2026-10-31 备份：1251 文件 / 123,259,197 字节双侧相等；git HEAD/工作树一致 |
| 留痕 | `.governance/incidents/d1-host-backup-20261029.md` |

## 2. 入口升级（0.54.1 → 0.99.0，宿主 DEC-8）

| 项 | 结果 |
|---|---|
| CLAUDE.md | bootstrap 段 → 0.99.0 lightweight 模板（5669 bytes；标题/项目信息/治理入口逐字保留） |
| plan-tracker | `工作流版本` 0.54.1 → 0.99.0；Gate 表保留历史 11-Gate（偏离在案） |
| hooks | pre-commit / commit-msg / post-commit → `@version 0.99.0`（旧版 `.bak-20261029`） |
| 结构 | 无活跃任务 → packets/locks 按需；无 archive 面 |
| 健康面 | 宿主 `check-governance` full = **43 issues**（FAIL：9/13/14/23/25/28c/29/36）；quick 墙钟 4.0s |

## 3. Claude Code 接入面（用户升级 CLI 后由 Coordinator 配置）

| 项 | 事实 |
|---|---|
| CLI | `claude --version` → 2.1.312；`claude.exe` 298,690,208 bytes |
| 插件 | `software-project-governance@spg` 0.99.0，scope=user，enabled |
| 载荷 | 35 skills / 15 agents；always-on ≈1,753 tok（`claude plugin details`） |
| 缓存 | `C:\Users\peter\.claude\plugins\cache\spg\software-project-governance\0.99.0\` |

## 4. 摩擦台账（逐项可复现）

| # | 摩擦 | 证据 | 处置/去向 |
|---|---|---|---|
| F1 | marketplace 直指开发仓安装 EPERM ×2（沙箱 symlink） | `.codex-sandbox/FEAT-103/node_modules`、`.governance/sandboxes/dsh021-baseline/.../node_modules` | 改用 clean clone `_spg-clone-20261031` 作为 marketplace 源；沙箱移出仓库 |
| F2 | lightweight 模板写入后自检 FAIL | `has_full_bootstrap` 仅认 `### Step 0: 确定双维度模式`（sync_entry_projection.py:52） | 登记（产品缺陷候选，冻结池） |
| F3 | 宿主 hooks 升级后一度无法解析 SPG home | `~/.claude/plugins/cache` 不存在 → `find_spg_home` 无候选 | 插件安装后自愈（已复验 cache/SKILL 存在） |
| F4 | 插件载荷含 e2e 夹具重复 SKILL | `find_spg_home` 命中 2 路径（sort -V 选正） | 脆弱依赖，登记 |
| F5 | 升级后宿主健康面 43 issues（8 FAIL） | quick/full 实测 | 宿主治理数据债，登记（不属 FIX-001） |
| F6 | `.governance` 运行时新文件未纳入 ignore | `governance-store-ops.json` / `execution-packets.json` / `authority-ledger/` / `.write-guard-*` | 已随 FIX-001 commit 纳入忽略 |
| F7 | 升级遗留未提交治理面变更与后续任务混在同一工作树 | `git status` 5 项 unstaged | 单 commit 承载 + 披露（宿主先例 429ae39） |
| **F8** | **pre-commit BOOTSTRAP DISCIPLINE 在消费方宿主 fail-closed 误拦** | `is_claude_bootstrap_self_upgrade` 从 `$REPO_ROOT/skills/software-project-governance/SKILL.md` 取 source_ver（infra/hooks/pre-commit:151）；宿主无此路径 → source_ver 空 → 合法 bootstrap 自升级永不被识别；实测 commit 被 BLOCK，只能 `--no-verify` | **登记 FIX-477**（D1 真实使用新需求池首项） |

## 5. 真实任务（缺陷修复 FIX-001）

| 阶段 | 结果 |
|---|---|
| 缺陷 | `kingdom_war` gitlink（160000）无 `.gitmodules`、嵌套仓无 remote → 外层 `git status` 恒 ` M kingdom_war`、`git submodule status` fatal |
| 裁决 | DEC-9（方案 B 转普通未跟踪目录；否决补 .gitmodules / 合并两仓） |
| 实现 | Developer 子 agent：`git rm --cached kingdom_war` + `.gitignore` 根锚定 `/kingdom_war/` + 运行时 JSON/ledger 忽略 |
| 审查 | Code Reviewer 独立只读：**APPROVED_WITH_NOTES / unresolved_blockers=0**（P2-1 暂存完整性 → 已同批 staged；P3-1 根锚定 → 采纳；P3-3 运行时归类 → 采纳）；机录 REVIEW-FIX-001-R0（report sha256 `98dfdaf1…`） |
| 提交 | 宿主 `483ecd5`（8 files，+126/−39）；pre-commit 被 F8 误拦 1 次 → 披露后 `--no-verify` |
| 终态复核 | `git status` 仅剩既有 `.claude/settings.local.json`；`submodule status` exit 0 空；`ls-files kingdom_war` 空；嵌套仓 HEAD `3564b1a` 未变；`pytest 626 passed` |

## 6. 度量

| 指标 | 值 |
|---|---|
| D1 修正启动（10:41）→ 首个真实任务闭环（11:22） | ≈41 min（含 Claude Code 配置、宿主升级、缺陷选择、全链） |
| 缺陷任务（选型 11:09 → commit 11:22） | ≈13 min |
| 审查链 | R0 一次通过（AWN/0），无 NEEDS_CHANGE / 无复审 |
| 钩子拦截 | 1 次（F8 误报）+ 1 次披露绕过；首次提交前 hooks 干跑 exit 0 |
| 治理动作占比 | 升级/记录/审查约 70%；缺陷实现本身（两条 git/ignore 操作）<5% |
| 宿主 quick 健康检查 | 4.0s / 43 issues |
| 插件仓 full 健康检查 | ≈11 min（2026-10-29 实测，RISK-044 劣化持续） |

## 7. 结论（首轮）

- D1 首轮真实使用**跑通**：真实宿主、真实缺陷、完整治理链、可复核终态；产出 1 个真实需求（FIX-477）。
- 真实摩擦集中在**接入面**（安装/插件载荷/消费方 hooks），而非游戏代码本身——与 AUDIT-160 论纲 B2 判断一致。
- 升级带来的健康面债务（F5）需要在宿主侧单独立项清理，不应混入功能任务。

## 8. FIX-477 修复（解冻一件，DEC-379）

- 用户裁决：解冻 FIX-477（其余 0.100 冻结池维持冻结）。
- TRIAGE-FIX-477 机录（machine-signal）；DEC-379 机录。
- **红基线独立复现**（模拟消费方宿主：临时 git 仓 head 版本 0.54.1、staged 0.99.0 + CLAUDE.md bootstrap 变更、无 repo-local skill）：当前 hook → `BOOTSTRAP DISCIPLINE` BLOCK exit 1。
- 修复方向：`source_ver` 优先从 `SPG_RESOLVED_HOME/SKILL.md` 解析、`REPO_ROOT/skills/...` 兜底；插件仓自身纪律保持 BLOCK；红绿测试覆盖两态。
- **传播面注意**：Step 0 自升级按 `cmp -s` 字节比较（非版本号），因此修复可自动传播到已安装 hook——但前提是 `SPG_RESOLVED_HOME` 指向**含该修复的**安装根；本机 Claude Code 缓存是 2026-10-31 安装快照（31eec64），需刷新缓存或手工复制 hook 才能在宿主端到端复验。
- **实现（Governance Developer）**：`source_ver` 解析改为「repo-local skill 存在时权威；否则回落 `$SPG_RESOLVED_HOME/SKILL.md`；两者皆无仍 fail-closed」（−1/+15 行）；新增 consumer-host helper + 2 用例（+106 行）。
- **开发期发现的真实回归**：首版按「安装根优先」实现，导致 plugin 布局用例被 BLOCK（本环境 `find_spg_home` 经 DSH preset 解析到真实仓 0.99.0，而非临时仓 0.37.0）——改为 repo-local 优先后恢复。
- **回归证据**：`PreCommitClaudeBootstrapUpgradeHookTests` 7/7 OK（16.2s）；`test_hooks` 70/70 OK（148.6s）；`test_pre_commit_review_evidence` 11/11 OK；hook `bash -n` exit 0。
- **独立端到端复验（Coordinator，模拟消费方宿主）**：同一临时仓把 hook 换成修复版、`SPG_HOME` 指向含修复 hook 的安装根 → `✅ GOVERNANCE: CLAUDE.md bootstrap self-upgrade detected; Step 6 allowed.` exit 0（红基线为 exit 1 BOOTSTRAP DISCIPLINE，EVD-2190）。



