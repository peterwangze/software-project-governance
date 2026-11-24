# 把项目目标交给循环

用项目已有的需求、工作树和用户给定的成品标准确定第一项可执行事务。已有代码可作为本轮输入，审查回执须来自当前单元和工件。

收集项目名、用户目标、验收操作、运行权限和适用 Profile。具备插件命令的宿主使用 `/governance` 读取初始化规程。仅安装本技能时，在目标项目的 `.governance/` 下从本目录的 `templates/` 补齐 `plan-tracker.md`、`evidence-log.md`、`decision-log.md`、`risk-log.md`。用真实项目、目标、权限、触发模式及安装版本填入配置。为宿主创建或补充一条项目指引，指向本技能和从项目根执行的 `governance-bootstrap --format json`。用本技能 `infra/verify_workflow.py` 按[循环入口](lifecycle.md)登记第一项工作，或在同一运行记录中恢复已经登记的工作。

验收接入时，从独立的新进程读取该单元，核对稳定 ID、目标、层级、关联任务和待验证条件。记录缺失或损坏就报告诊断并保留原件。

首次接入时，若 `.governance/README.md` 缺失，将[材料入口模板](templates/governance-readme.md)复制到该路径。向用户指出这个入口；项目已有入口时沿用原文。
