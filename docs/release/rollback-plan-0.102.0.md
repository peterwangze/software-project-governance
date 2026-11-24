# 0.102.0 回退步骤

若启动或定向查询暴露其他任务的独有正文，查询丢失已登记的原件，或公开附件与已核验摘要不符，暂停扩大分发，保存版本、提交、安装路径、脱敏命令输出及涉事单元 ID。

1. 备份消费项目的治理记录和材料原件，保留项目相对路径。在独立副本复现问题。
2. 从上一版发布页取得 `v0.101.1`，核对标签剥离提交为 `1ed1ce7a0a7959eff52fc09c778c90ce7d18cf92`，将该版本装入隔离宿主。[上一版发布物](https://github.com/peterwangze/software-project-governance/releases/tag/v0.101.1)
3. 在项目副本中运行上一版 `infra/verify_workflow.py governance-bootstrap --format json`，核对消费项目根、版本和原单元。用 `loop status --unit <id> --json` 复核目标、判据、裁决和证据，再按已登记位置核对一份原件。0.101.1 提供的查询方式见[运行设置](feature-flags-0.102.0.md)。
4. 副本验收通过且切换授权覆盖受影响宿主后，将这些宿主切回已核验版本。保留 0.102.0 生成的单元记录、公开标签与附件，以便重放和修正。

RISK-036 跟踪外部验证。official approval、marketplace approval、universal/full runtime support 和 external first-session pilot success 仍需各自的独立证据。
