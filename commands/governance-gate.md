# governance-gate — 判断当前工作单元的本轮门禁

独立调用时先按本次加载的主技能 `software-project-governance` §B1 或同一插件包的[入口定位](governance/bootstrap.md) 确认 `<plugin_home>`，以下命令均从用户项目根执行。使用者指定单元和待验证的行为，运行 `loop status --unit <id> --json`，核对层级、绑定任务、轮次、Gate 和验收约定。只给 Gate 名称时查看匹配的工作单元；结果有歧义时由用户指定对象。资料不足就如实报告缺口。

1. 在相同目标和输入下复验当前工件，对照 `core/stage-gates.md` 的适用条件。
2. 由适用的独立审查者把裁决写为该任务、轮次的 `REVIEW-TASK-Rn`。保留成品、验证方法和失败样本。
3. 使用 `python "<plugin_home>/infra/verify_workflow.py" loop gate --unit <id> --gate <Gx> --review <REVIEW-TASK-Rn>`。正常审查入口已消费同一回执时，先读取单元的最新结果。
4. 复读该单元。材料充分时向父单元交接工件；需要改动就带原失败样本返回执行者；权限、未解决阻断或熔断由协调者处理。发布决策仍需独立授权。
