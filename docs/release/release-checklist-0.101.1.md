# 0.101.1 发布核对清单

REL-106 的发布者在每一步保留对应源码提交、原始命令、退出状态及产物摘要。独立签核和公开下载复核分别记录在本版发布回执中。

1. 对照[版本范围](version-plan-0.101.1.md)核实 `v0.101.0` 之后的累计变更。运行 `release-projection`、`check-version-consistency`、`check-projection-sync` 和 `check-manifest-consistency --fail-on-issues`，核对 Claude、Codex、ZCode 清单及包版本均为 0.101.1。
2. 在独立的宿主配置和消费项目中，从候选安装插件，用宿主列出的技能或命令文件定位首次入口，核对 `resolve.plugin_home`、`resolve.host_project_root`、`active_version` 与退出码。另测直接技能安装、带空格的位置和原路径失效；保留[回退演练](rollback-plan-0.101.1.md)结果。
3. 对最终候选运行完整验证器与发布门，核对 CODE、RELEASE 独立签核、发行账本及 CI 的实际结果。候选发生变化，按新提交重新核验相关门。
4. 核实公开标签剥离值、主干可达性和 GitHub Release 附件的下载摘要。再从公开 GitHub 仓库添加市场并在空白消费项目执行首次启动，核对宿主实际选中的版本及返回的两条根路径。

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
