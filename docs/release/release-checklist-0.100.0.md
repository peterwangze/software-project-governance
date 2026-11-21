# v0.100.0 发布核对清单

此表规定要核实的对象。每次执行的对象、命令、实测结论和例外由独立签核记录保存。[独立签核](signoff-0.100.0.md)

| 步骤 | 验收条件 |
| --- | --- |
| 累计范围 | 从 `v0.99.0` 剥离后的提交核对本次载荷、上版顺延工作和本版未交付项。[版本计划](version-plan-0.100.0.md) |
| FEAT-131 合并 | PR #2 指向 master，最新 FEAT-131 提交所在的 GitHub Actions 运行完成，verify 作业成功后合并。[PR 及检查记录](https://github.com/peterwangze/software-project-governance/pull/2) |
| 版本和材料 | 运行 `check-version-consistency` 和 `check-manifest-consistency --fail-on-issues`，核对版本投影、变更日志、旗标与回滚方案。 |
| 独立签核及发行门 | CODE 和 RELEASE 审查关联审阅对象与实际证据。对已登记的发布单元运行 `check-release --version 0.100.0 --unit <发布单元> --require-changelog --lineage-mode candidate`；逐项记录实测结果、未测原因和经裁定的例外。 |
| Git 和 GitHub | 原生候选清单通过检查后，单独提交候选至已发布的清单转换，并给转换提交打 annotated tag。发布后用 `release-ledger --version 0.100.0 --remote origin`、远端 tag 对象及剥离值、GitHub Release 状态核对同一版本。 |

RISK-036 继续跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
