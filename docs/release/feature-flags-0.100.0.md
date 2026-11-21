# v0.100.0 运行开关

FEAT-130 与 FEAT-131 通过现有 CLI 启用。为工作单元记录事实取舍时调用 `loop learn --kind decision`，交付后记录反馈用 `--kind opportunity`，选用某条建议时显式提供 `--from-learning`。现有宿主可继续使用 `loop status --json` 查询自己的项目。

| 设置 | 适用面 |
| --- | --- |
| `GOVERNANCE_ENFORCEMENT` | 现有动作级执法开关。默认关闭时保留 advisory 行为；开启后的守卫覆盖范围取决于宿主及操作。[DSH 宿主边界](../../adapters/dsh/README.md) |
| `GOVERNANCE_LEGACY_BEHAVIOR=1` | 沿用旧的性能行为；数据完整性和权限约束继续生效。 |
| `SPG_WEB_INSTALL_TIMEOUT` | 本地 Web 控制台安装依赖的超时秒数，默认 120。 |
| `DSH_DESKTOP_APP_DIR` | 指向待验证的桌面安装目录。兼容性报告会显示实际运行时、安装包身份及行级校验结果。 |
| `SPG_RELEASE_GATE_TIMEOUT` | 发布执行门的单命令超时秒数，由发行端根据机器和测试规模配置。 |

RISK-036 继续跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
