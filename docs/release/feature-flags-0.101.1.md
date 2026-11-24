# 0.101.1 运行设置

首次入口默认从当前宿主加载的主技能确定技能根，只有插件包位置时才使用包内的 `skills/software-project-governance`。升级后，正常启动沿用用户当前项目目录。

| 场景 | 设置或操作 |
| --- | --- |
| 宿主提供已加载的技能或包 | 由入口直接使用本次来源，无需设置环境变量。ZCode 的技能与包排错见[市场安装说明](../marketplace/zcode-marketplace-install.md)。 |
| 显式指定安装位置 | 既有 `SOFTWARE_PROJECT_GOVERNANCE_HOME` 或 `SPG_HOME` 可提供技能或包的绝对目录。沿[入口定位](../../commands/governance/bootstrap.md) 检查技能名、脚本及来源一致性。 |
| 使用旧性能配置 | `GOVERNANCE_LEGACY_BEHAVIOR=1` 保留现有行为开关语义；工作单元、独立验收和安装来源检查照常执行。 |

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
