# v0.101.0 运行设置

在工作单元上使用 `loop status --unit <id> --json` 查询当前目标、验收和回执。跨会话恢复、独立交付与后续机会均沿用同一工作单元及其记录。发布者可在独立消费目录以真实验收命令核对版本行为。

| 设置 | 生效范围 |
| --- | --- |
| `GOVERNANCE_ENFORCEMENT` | 既有的宿主操作守卫。具体操作的覆盖范围取决于接入的宿主。[宿主边界](../../adapters/dsh/README.md) |
| `GOVERNANCE_LEGACY_BEHAVIOR=1` | 恢复旧的性能配置，保留数据、独立复审和权限检查。 |
| `SPG_RELEASE_GATE_TIMEOUT` | 调整发行检查单个子命令的超时秒数。每次检查的最终状态及对应候选须记录在发行回执中。 |

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
