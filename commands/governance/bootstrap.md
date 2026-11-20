# /governance 入口引导：平台注入 · vendor 兜底 · 超时/升级链 · 错误码

> FEAT-038 拆分自路由层的「入口引导（FIX-238）」节与「错误码」节（逐字搬移，零语义丢失）。
> 本文件不在默认注入面——**触发条件**：`<plugin_home>` 解析失败 / `resolved_root_ok == false` / resolve_entry 超时或缺依赖 / bootstrap 引导段陈旧 / 需要按错误码处置时 Read。
> 正常路径见路由层「第一动作」。本页处理旧命令和诊断。

## 定位与恢复

优先从宿主加载的位置找 `skills/software-project-governance`。Claude 使用 `CLAUDE_PLUGIN_ROOT` 下的技能，Codex 使用已加载 `SKILL.md` 所在目录。显式配置安装位置的宿主沿用 `SOFTWARE_PROJECT_GOVERNANCE_HOME` 或 `SPG_HOME`。

从用户项目根运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。要求成功退出、JSON 可解析且 `resolve.resolved_root_ok == true`。任一失败，MUST STOP 并显示实际根和诊断；必要时可使用同目录 `bootstrap.cmd` 或 `bootstrap.sh` 调查定位超时。未初始化进入 Scenario A；已初始化读取 `loops`，用 `loop status --unit <id>` 按目标、原件和阻塞恢复。

升级须经用户授权。数据损坏时保留原件；运行记录和独立回执保持可追溯。`health.state="deferred"` 按“待检查”显示。行为灰度开关只调整性能与首次交互时机，返工、授权和独立验收持续有效。

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| GOV-ERR-001 | `.governance/` 不存在但用户拒绝初始化 | 停止，告知用户需初始化 |
| GOV-ERR-002 | plan-tracker.md 损坏且无法修复 | 停止，建议手动检查或重建 |
| GOV-ERR-003 | git hooks 缺失且无法安装（非 git 项目） | 降级模式——session 级检查 |
| GOV-ERR-004 | 版本降级（安装版本 < 记录版本） | 警告，建议更新插件。注：resolve_entry.py 只检测升级（host_v < active_version → scenario C）；降级检测由 LLM-side 比对 active_version 与 plan-tracker 记录版本完成——resolver 不覆盖此路径 |
| GOV-ERR-005 | bootstrap 超时/缺失/不可执行（file-not-found / timeout / python-missing / store-stub） | 停止，展示分类诊断；调大 `SPG_RESOLVE_TIMEOUT` 或重装插件；不静默、不无限重试 |
| GOV-ERR-006 | 引导段陈旧但未检测到更高版本 SKILL.md | 停止，输出 `/plugin update` 指引；版本不可解析时不升级（fail-closed） |
