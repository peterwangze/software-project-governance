# 0.102.0 运行设置

本版的材料查询随主技能安装，使用时直接调用该技能的 `infra/verify_workflow.py`。材料保留原格式，已有项目可沿用原记录及路径。

| 需要回答的问题 | 命令或设置 |
| --- | --- |
| 当前工作依据是否足够？ | `governance-bootstrap --format json` 提供当前单元和判据。事实足够就继续执行。 |
| 哪份材料可补足当前判据？ | `loop materials --unit <id> --query <问题词>` 返回限定范围的摘要。用返回的标识执行 `loop materials --unit <id> --ref <标识>`，按需读取原件的相应片段。 |
| 收口时材料是否仍可定位？ | 显式运行 `loop materials --unit <id> --check`。依据返回的计数及示例处理异常，并对该单元复查。 |
| 使用 0.101.1 核验原记录时从何处进入？ | 运行 `loop status --unit <id> --json` 检查该单元，根据其中的绑定和该任务的证据条目复核原件。 |

`GOVERNANCE_LEGACY_BEHAVIOR=1` 沿用既有性能配置。RISK-036 跟踪外部验证。official approval、marketplace approval、universal/full runtime support 和 external first-session pilot success 仍需各自的独立证据。
