# v0.102.0 组装签核

DEC-409 记录用户对本版 GitHub 发行的授权。代码审查和发布审查均核对了组装提交 `3556d735ce89c87c4769b20f83a2fedbdc28f2c4` 的树 `109aaf5170896b813899c0249fa5f5f41a86a14a`。[组装提交](https://github.com/peterwangze/software-project-governance/commit/3556d735ce89c87c4769b20f83a2fedbdc28f2c4) · [组装提交 CI](https://github.com/peterwangze/software-project-governance/actions/runs/45384046683)

| 独立审查 | 结论 | 治理回执 | 原报告 SHA-256 |
| --- | --- | --- | --- |
| Code Reviewer | APPROVED | REVIEW-REL-107-R0 | `ce6159d3092ed5a53d354d65d0831572df2ad820b78cca078e96ec5ca87b7f5e` |
| Release Reviewer | APPROVED | REVIEW-REL-107-R1 | `1e21cfa22a32f9f178d0e772315d614d96f3492bd611ef869ebb9a22fbc64328` |

组装包共 3,117,569 字节，SHA-256 为 `2c5e4325a145f271398568ccd1b3b30bb1a7850a8caea519490605e5b04b3568`。Release Reviewer 将包内 546 个文件与组装树逐件比较，394 件原字节相同，另 152 件仅有换行差异。

Package QA 在隔离消费项目离线安装，启动返回 0.102.0 及正确的技能根与项目根。按问题词查询得到 `learn:footfall`，按引用定位到带中文和空格的原件路径。查询回复省略原件正文，无关词返回空结果。收口核对的四项计数初始均为零，改变原件后报告 `changed=1`。包体验收回执 SHA-256 为 `1fa772deae96838eb45591bd5f82febe2a489e54b4c750e2a3d38b8b9be6d071`。

回退演练使用上一版公开附件离线切换至 0.101.1，成功恢复原单元并读取原件。切回 0.102.0 后查回 `learn:capture`，收口核对通过。抽验的六项消费项目文件前后逐字节一致。回退回执 SHA-256 为 `b6f8d64db9c8e93898b20d7805185874ead53f461d14a4004b0b7e541af497b2`。

本次签核覆盖上述组装树和包。冻结候选的完整发布门须记录实际提交、原始退出码及命中项。若治理健康检查仍命中历史告警，须按本次发行的用户裁决处理。候选状态和后续转换见[原生发布账本](../../skills/software-project-governance/core/releases/0.102.0.json)。
