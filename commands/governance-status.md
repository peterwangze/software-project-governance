# governance-status — 恢复工作单元状态

在宿主根运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。确认 `resolve.resolved_root_ok`。项目和权限信息来自 `project`，本轮事实来自 `loops`。需要单件详情时运行 `loop status --unit <id> --json`；使用 `loop status --json` 查看所有并行工作。

说明用户目标、单元及所属父单元、层级和轮次，本轮产出与最近签核，尚缺的证据或下一项操作。例如“发票导出的一处中文截断复验未过，修改单元回到实现；交付单元仍待它重新验收”。只有记录中能查到的事实才可填入。空列表应提示从实际需求开始；无法读取时展示错误，保留运行原件。

需要排查健康异常时取 `check-governance --summary-only --scope quick`；未执行的健康检查标为待检查。发布或版本操作前运行 full。会话状态、审查记录与正式发布授权各有自己的证据。权限模式、风险、候选排序和证据位置按用户当前问题展开。
