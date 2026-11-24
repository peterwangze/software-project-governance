# v0.101.1 独立发行签核

DEC-407 授权发布本补丁。两份独立审查绑定组装提交 [98bdbe25f86f](https://github.com/peterwangze/software-project-governance/commit/98bdbe25f86f717b25806bd7bd65041622fbe255) 及 Git 树 `0fab867138dd9b920f43950eb9116329320578d8`。

| 审查人 | 结论 | 治理回执 | 审查报告 SHA-256 |
| --- | --- | --- | --- |
| Code Reviewer | APPROVED | REVIEW-REL-106-R0 | `2d270e1db59719e32cda21f14d07e129c88ce406847e5a462106c57fc483149d` |
| Release Reviewer | APPROVED | REVIEW-REL-106-R0-RELEASE-REVIEWER | `470526cc2a14bc76a43358a00a869d19370347ae9a6ec2733fbe3d755eaca9df` |

从该树打包后，在独立消费项目离线安装。主技能路径和插件包路径两种首次调用均指向安装中的技能；空项目识别为场景 A，含游戏项目文件时识别为场景 B。用同一源码树作为本地市场在隔离的 ZCode CLI 中安装，宿主列出了主技能和治理命令，调用后返回正确的消费项目根。

组装包 SHA-256 为 `8302a3d5d07ef64531c37026a582029ffd45925e5a4a0976fe51f749a2482f78`，成品验收回执 SHA-256 为 `a2be6490c7af49fa6780a6074e906582ebaaedfd675fe0512373c88a37a02985`。[组装提交 CI](https://github.com/peterwangze/software-project-governance/actions/runs/45319810376)

组装、候选和正式标签对应不同的包内容。候选的 CI、发布门及其转换提交按[本版核对清单](release-checklist-0.101.1.md)验收，转换关系见[原生账本](../../skills/software-project-governance/core/releases/0.101.1.json)。
