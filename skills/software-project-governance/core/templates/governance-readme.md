# 治理材料入口

1. 在[任务表](plan-tracker.md)找到事项、任务 ID 和验收条件。
2. 用任务 ID 在[证据记录](evidence-log.md)找到结论和证据位置。需要了解取舍或待解决的问题时，再查[决策](decision-log.md)或[风险](risk-log.md)。
3. 需要复核时，按记录中的项目相对路径或链接打开原件。条目已归档，可从项目根的 `.governance/archive/index.md` 按编号查询。索引尚未生成或只记得事项名称时，在已有的 `.governance/archive/tasks/` 中按名称或 ID 找任务，再在 `.governance/archive/evidence/` 中按任务 ID 查证据位置。

需要确认当前轮次和门禁裁决时，从项目根运行 `python "<plugin_home>/infra/verify_workflow.py" loop status --unit <单元ID> --json`。`<plugin_home>` 为已安装的 `software-project-governance` 技能目录。

## 留存材料

简单事项在现有记录中写明结果和依据即可。需要留存独立材料时，已有原件直接引用；新材料默认放在 `.governance/materials/<任务或单元ID>/`，用到时再建目录。格式、文件名和内部组织由任务决定。材料较多时，可在该目录加一页导航，让读者按结论选择要看的原件。

试验默认在临时工作区运行，把复核结论所需的输入、结果或持久引用留给任务。需要重现完整现场时，可以保留整套工作区并注明用途。

收口时，从任务记录实际打开支撑结论的材料。多项任务共用同一原件时引用同一位置。已经签核或绑定摘要的文件保留原路径和内容，修订另存并在新记录中注明接替哪条结论。
