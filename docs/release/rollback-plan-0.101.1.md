# 0.101.1 回退步骤

若首次启动读到其他项目、不能恢复已有工作单元，或已下载包的摘要与公开附件不符，保留失败命令、安装版本、两条根路径和原始回执。涉及已有数据时先暂停对应写入。

1. 保存目标项目治理数据、工作产物及当前安装来源。用独立消费目录验证副本可读，升级后产生的记录单独保留。
2. 在隔离目录取得[上一版 v0.101.0](https://github.com/peterwangze/software-project-governance/releases/tag/v0.101.0)，核对标签剥离提交 `9ab770a762c7d0bf0509ecdbf687dcfe7a3591b2`。使用该树或已核验的上一版附件安装到隔离宿主。
3. 从消费项目副本运行上一版技能目录内的 `infra/verify_workflow.py governance-bootstrap --format json`。上一版的技能目录可从本次插件包的 `skills/software-project-governance` 取得。对照原记录核对 `resolve.host_project_root`，再用 `loop status --unit <原单元> --json` 核对目标、证据和最近裁决。
4. 副本验收通过并取得实际切换授权后，再将受影响宿主切回已核验的上一版。公开过的标签、附件和回执保留，后续修复使用新版本。

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
