# v0.101.1 独立发行签核

DEC-407 授权发布本补丁。两份独立审查绑定组装提交 [859c959f049d](https://github.com/peterwangze/software-project-governance/commit/859c959f049d3887ce45d88e58ba8e71fa8b4c15) 及 Git 树 `642d218e09790f6345f2053409ac0d57cbc54cb8`。

| 审查人 | 结论 | 治理回执 | 审查报告 SHA-256 |
| --- | --- | --- | --- |
| Code Reviewer | APPROVED | REVIEW-FIX-548-R0 | `fbc96fb1c1aab07c1a2d56e95823dfe73905d48b222052dcfb22ca29760bd306` |
| Release Reviewer | APPROVED | REVIEW-REL-106-R4 | `ca772eadac32169428efa9ebb1c822acf6c27b4089283379e8d4cdf659dbc330` |

从该树打包后，在独立消费项目离线安装。主技能路径和插件包路径两种首次调用均指向安装中的技能；空项目识别为场景 A，含游戏项目文件时识别为场景 B。用同一源码树作为本地市场在隔离的 ZCode CLI 中安装，宿主列出了主技能和治理命令，调用后返回正确的消费项目根。

组装包 SHA-256 为 `df807339f105b3fe4020325e4e9a33813817c4824fd84d76ea479427050b3a1f`，成品验收回执 SHA-256 为 `646357c7f1301a4b740e876f678dc539db97feec6ec85158653974609ef0c381`。[组装提交 CI](https://github.com/peterwangze/software-project-governance/actions/runs/45323805267)

用户通过 DEC-408 为本次发行接受治理健康检查中的四项历史风险（RISK-044、059、047、062）及六个既有合并提交（#23、24、25、27、28、29）。首次候选的原始检查退出 1，共 10 项。候选的其他完整发布检查和真实 ZCode 市场首次使用须通过。最终候选的原始检查结果、证据摘要及转换关系写入[原生账本](../../skills/software-project-governance/core/releases/0.101.1.json)。
