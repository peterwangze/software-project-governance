# v0.101.0 发布核对清单

REL-105 由 DEC-400 授权。组装由 REL-105 承接，发布单元 `REL-105-release` 的 G9 由独立 Release Reviewer 签核。版本范围和两条真实使用旅程见[版本计划](version-plan-0.101.0.md)。

| 环节 | 取得的证据 |
| --- | --- |
| 版本与来源 | 在同一候选运行 `release-projection`、`check-version-consistency`、`check-manifest-consistency --fail-on-issues` 和 `archguard-ratchet`。核对变更日志与自上版标签以后的累计差异。 |
| 用户结果 | 保存新旧版本在同预算下产出的各自工件、盲验回执、失败和成本。验证拒收已知负例、拦截局部验收代替整件交付，合格工件可通过。 |
| 安装与回退 | 从已审 Git 树打包，在独立消费目录用 `npm install --offline --ignore-scripts` 安装。通过实际安装的 JS 和 CLI 入口完成一次从登记到恢复的操作，并用上一标签的包与升级前数据在副本中演练恢复。[恢复步骤](rollback-plan-0.101.0.md) |
| 候选发布门 | 保存 CODE 与 RELEASE 的独立回执，然后登记原生候选清单。运行 `check-release --version 0.101.0 --unit REL-105-release --require-changelog --lineage-mode candidate --require-delivery-evidence`，核实实际执行门和交付证据。检查 PR 的 Ubuntu 和 Windows 作业。 |
| 正式附件 | 仅提交候选清单转换，对转换提交打附注标签。从标签的 Git 树打包，上传 GitHub 正式 Release，下载附件对比 SHA-256。运行 `release-ledger --version 0.101.0 --remote origin`，再以标签剥离值作为 `--release-commit`，运行 `check-release --version 0.101.0 --unit REL-105-release --require-changelog --lineage-mode released --require-delivery-evidence`。核对主干包含发布提交及两个 CI 作业的最终状态。 |

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
