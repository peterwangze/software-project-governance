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

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| GOV-ERR-001 | `.governance/` 不存在但用户拒绝初始化 | 停止，告知用户需初始化 |
| GOV-ERR-002 | plan-tracker.md 损坏且无法修复 | 停止，建议手动检查或重建 |
| GOV-ERR-003 | git hooks 缺失且无法安装（非 git 项目） | 降级模式——session 级检查 |
| GOV-ERR-004 | 版本降级（安装版本 < 记录版本） | 警告，建议更新插件。注：resolve_entry.py 只检测升级（host_v < active_version → scenario C）；降级检测由 LLM-side 比对 active_version 与 plan-tracker 记录版本完成——resolver 不覆盖此路径 |
| GOV-ERR-005 | bootstrap 超时/缺失/不可执行（file-not-found / timeout / python-missing / store-stub） | 停止，展示分类诊断；调大 `SPG_RESOLVE_TIMEOUT` 或重装插件；不静默、不无限重试 |
| GOV-ERR-006 | 引导段陈旧但未检测到更高版本 SKILL.md | 停止，输出 `/plugin update` 指引；版本不可解析时不升级（fail-closed） |
