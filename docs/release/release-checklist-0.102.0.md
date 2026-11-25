# 0.102.0 发布核对清单

REL-107 的每份回执须能定位源码提交、运行命令、退出状态及验证对象。候选签核和公开下载复核分别入账。

1. 核对主技能、宿主清单、包版本和模板投影均为 0.102.0。执行 `release-projection`、`check-version-consistency`、`check-projection-sync` 和 `check-manifest-consistency --fail-on-issues`。
2. 从候选安装到临时消费项目，建立带判据的单元、可用问题词命中的原件及无关材料。确认启动包保留单元判据且省略无关正文，`loop materials --unit <id> --query <问题词>` 返回对应摘要，`--ref` 定位原件。换用无匹配词，应返回空结果。
3. 对该临时单元运行 `--check`，记录正常结果。另在其托管目录放入未登记文件，再运行应报告该项，原件仍可读取。在消费项目副本演练[回退步骤](rollback-plan-0.102.0.md)。
4. 对冻结候选核对完整验证器、发布门、CI、CODE 与 RELEASE 独立签核和发行账本。公开后核对标签剥离提交、主干可达性及附件下载摘要，并从公开分发物复跑第 2 步。

RISK-036 跟踪外部验证。official approval、marketplace approval、universal/full runtime support 和 external first-session pilot success 仍需各自的独立证据。
