# /governance 入口引导：平台注入 · vendor 兜底 · 超时/升级链 · 错误码

> FEAT-038 拆分自路由层的「入口引导（FIX-238）」节与「错误码」节（逐字搬移，零语义丢失）。
> 本文件不在默认注入面——**触发条件**：`<plugin_home>` 解析失败 / `resolved_root_ok == false` / resolve_entry 超时或缺依赖 / bootstrap 引导段陈旧 / 需要按错误码处置时 Read。
> 正常路径无需本文件：路由层的「第一动作」「第二动作」已覆盖常规解析。

## 入口引导（FIX-238：平台注入 + vendor 兜底 + 超时/升级链）

**第一动作的 `<plugin_home>` 解析（消除占位符歧义——FIX-238.1）**：

- **平台注入变量（首选）**：
  - Claude Code：`$CLAUDE_PLUGIN_ROOT`（插件安装根；`<plugin_home>` = `$CLAUDE_PLUGIN_ROOT/skills/software-project-governance`）
  - Codex：从 system context 中 `software-project-governance` skill 的 `file:` 绝对路径解析（`<plugin_install_root>/skills/software-project-governance/SKILL.md` → `<plugin_home>` = 该 `skills/software-project-governance` 目录）
  - 通用环境变量：`SOFTWARE_PROJECT_GOVERNANCE_HOME` / `SPG_HOME`（已安装宿主显式指定）
- **vendor 引导脚本兜底（宿主无 AGENTS.md/CLAUDE.md 时仍可定位）**：`<plugin_home>/infra/bootstrap.sh`（POSIX）与 `<plugin_home>/infra/bootstrap.cmd`（Windows）随插件发布分发，定位 resolve_entry.py → 运行 `--json` → 输出 envelope。
  - POSIX：`bash "<plugin_home>/infra/bootstrap.sh"`
  - PowerShell：`& "<plugin_home>\infra\bootstrap.cmd"`（等价地 `python "<plugin_home>/infra/resolve_entry.py" --json`）
  - 平台注入 + 脚本兜底都不可用时 → **STOP fail-closed**，展示分类诊断，不呈现治理状态（DEC-080 / RISK-038）。

**resolve_entry 超时兜底（FIX-238.3）**：所有调用侧（bootstrap.sh / bootstrap.cmd / `verify_workflow.py resolve-entry`）共享退出码契约：`0` 成功（stdout 为 envelope JSON）；`1` 其他失败；`2` python 缺失；`3` resolve_entry.py 缺失（FileNotFound）；`4` 超时；`5` store stub（resolve_entry.py 存在但不是 canonical 解析器——缺 FX-130 marker，重装插件）。超时值 `SPG_RESOLVE_TIMEOUT`（正整数秒，默认 15s；非法回退默认——FIX-234 先例）。超时/缺失输出分类诊断（`spg-bootstrap-error: <category>`）且 exit 非 0，**不静默、不无限重试**。

**旧宿主 bootstrap 升级链（FIX-238.2——@bootstrap-version 陈旧标记）**：

- 陈旧标记：平台原生入口文件（AGENTS.md/CLAUDE.md）引导段 `@bootstrap-version` 头 < SKILL.md frontmatter `active_version`（或缺失头——视为 pre-0.73.0 陈旧）。
- 标陈旧且更高版本 SKILL.md 已安装 → **先升级 bootstrap 段**（从当前模板写回该段，保留入口文件其余内容不变），再继续后续引导。
- 未检测到更高版本 → 输出确定性错误 + `/plugin update` 指引，**不无限 fallback**。
- 版本比较 fail-closed：无法确定新版本（版本串不可解析）→ **不升级**，输出指引。

**web-console `--install` 超时（FIX-238.4）**：`SPG_WEB_INSTALL_TIMEOUT`（正整数秒，默认 120s；非法回退默认）。超时后输出诊断（`npm install timed out after Ns (SPG_WEB_INSTALL_TIMEOUT)`）不挂起；`--fail-on-issues` 时 exit 124。`--governance-entry` 保持非阻塞（FIX-150，不改）。

---

## 行为灰度开关（FEAT-040——legacy 回退通道）

切片 A（AUDIT-154，0.84.0）一次性落地四个热路径行为变更：FEAT-034（首次交互前置）/ FEAT-035（升级确认门）/ FEAT-036（Snapshot 双契约）/ FEAT-038（Scenario 按需加载）。本开关是它们的**回退通道**——一个总开关，不是逐 FEAT 矩阵。

**两个臂（一个决策）**：

| 臂 | 形态 | 适用 | 优先级 |
|----|------|------|--------|
| 会话级 | 环境变量 `GOVERNANCE_LEGACY_BEHAVIOR=1` | 用户**当下**踩到问题——不必动治理文件即可退回 | 高 |
| 项目级 | plan-tracker `## 项目配置` 的 `- **behavior_profile**: legacy` | 项目需要旧形态超过一个会话 | 中 |
| 默认 | `modern`（新协议） | 未配置 | 低 |

- 取值词表（封闭）：legacy = `1/true/yes/on/legacy`；modern = `0/false/no/off/modern`（大小写不敏感，自动 strip）。
- **非法值不猜（fail-closed）**：空值/未设置 → 落到下一臂；非空但不在词表内（如 `legacyy`）→ **不按 legacy 执行**（静默接受拼写错误会直接废掉回退意图），也**不静默按 modern 执行**——在 `governance-bootstrap` 的 `behavior.invalid` 显式报告后按下一臂决定。
- **生效形态的唯一事实源 = `governance-bootstrap --format json` 的 `behavior` 面**（`profile`/`source`/`reverted`/`invariants`/`invalid`）；协议文本只描述边界，不承担判定。legacy 生效时该命令把回退提示置于 `next_actions` **首位**（提醒不可被 5 条上限挤掉）。

**回退范围（只回退性能/编排行为）**：

| 面 | modern（默认） | legacy 回退 |
|----|---------------|------------|
| FEAT-034 bootstrap 热数据入口 | `governance-bootstrap` 单命令快路径（≤8KB 投影） | plan-tracker 六段热数据逐段读取 |
| FEAT-034 首次交互时序 | 热数据就绪后立即 `ask_user_question`；深检后置 | 深检（健康摘要 + 交叉验证）先行，再进入首次 ask |
| FEAT-036 snapshot 渲染契约 | 默认交互视图 ≤8 字段；完整契约按需取 | 直接渲染完整交付信任快照 |
| FEAT-038 Scenario 加载 | 路由层为默认载荷；命中场景按需 Read | 会话开始预加载全部 `commands/governance/*.md` |

**安全语义硬边界（legacy 模式一律不回退——无豁免）**：

1. **升级确认门（FEAT-035）**：版本升级写序列 MUST 先呈现摘要并经 `ask_user_question` 确认；**确认前零写操作**。
2. **异常不隐藏**：异常先于状态展示；`health.state="deferred"` 显示「待检查」而非通过。
3. **fail-closed**：`resolved_root_ok == false` → MUST STOP，不呈现治理状态（DEC-080 / RISK-038）。
4. **真实环境防护（M7.7）**：三选一（隔离/备份+校验/逐项授权），三者皆缺即禁止执行。
5. **复审必达（M7.4）**：`NEEDS_CHANGE` 且 round<3 → MUST 立即复审，不得跳过。

> **为什么回退边界如此划**：legacy 是**性能/编排**回退，不是安全回退。FEAT-035 的确认门代价是一次交互确认，收益是"展示状态不再隐含修改项目的授权"（DEC-209）——把它做成可回退等于把知情同意做成可选项。`behavior_profile.py` 的 `revert_contract_issues()` 是该边界的机检：任何试图把安全语义塞进 `LEGACY_REVERTS` 的改动会让守护测试翻红，而不是靠注释自律。

**验证命令**：

```bash
python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format json   # behavior 面
GOVERNANCE_LEGACY_BEHAVIOR=1 python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format text
python -m pytest <plugin_home>/infra/tests/test_behavior_profile.py -q              # 边界守护
```

**相关**：完整边界表与机检契约见 `skills/software-project-governance/SKILL.md`「行为灰度开关」段与 `infra/behavior_profile.py`。

---

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| GOV-ERR-001 | `.governance/` 不存在但用户拒绝初始化 | 停止，告知用户需初始化 |
| GOV-ERR-002 | plan-tracker.md 损坏且无法修复 | 停止，建议手动检查或重建 |
| GOV-ERR-003 | git hooks 缺失且无法安装（非 git 项目） | 降级模式——session 级检查 |
| GOV-ERR-004 | 版本降级（安装版本 < 记录版本） | 警告，建议更新插件。注：resolve_entry.py 只检测升级（host_v < active_version → scenario C）；降级检测由 LLM-side 比对 active_version 与 plan-tracker 记录版本完成——resolver 不覆盖此路径 |
| GOV-ERR-005 | bootstrap 超时/缺失/不可执行（file-not-found / timeout / python-missing / store-stub） | 停止，展示分类诊断；调大 `SPG_RESOLVE_TIMEOUT` 或重装插件；不静默、不无限重试 |
| GOV-ERR-006 | 引导段陈旧但未检测到更高版本 SKILL.md | 停止，输出 `/plugin update` 指引；版本不可解析时不升级（fail-closed） |
