# v0.102.0 组装签核

DEC-409 记录用户对本版 GitHub 发行的授权。本次签核对应组装提交 `8172d50d0842087cbf4af3a0714807076e5037f4`、Git 树 `621db0a0ef675aacd7d85e9fcbf53bb11bd0279b` 及从该树构建的包。[组装提交](https://github.com/peterwangze/software-project-governance/commit/8172d50d0842087cbf4af3a0714807076e5037f4) · [本次组装 CI](https://github.com/peterwangze/software-project-governance/actions/runs/45385746614)

前一次组装的 Ubuntu CI 报告两项入口回归。FIX-552 在主技能首段补明定向读取步骤，让模型先按单元和问题查摘要，再按需读取选定原件。会话恢复示例采用 `loop status --json --unit <id>`。独立审查者从本次 Git 树导出源码复跑原测试，2 项用例和 19 项子测试均通过。新旧参数顺序在同一个消费项目单元返回相同 JSON。[上轮 PR #32](https://github.com/peterwangze/software-project-governance/pull/32) · [上轮失败 CI](https://github.com/peterwangze/software-project-governance/actions/runs/45384046683)

| 独立审查 | 结论 | 治理回执 | 原报告 SHA-256 |
| --- | --- | --- | --- |
| Code Reviewer | APPROVED | REVIEW-FIX-552-R0 | `893b0c93439120eebe66140662ad3198116339dbdf2ef1fb54454bf57d254212` |
| Release Reviewer | APPROVED | REVIEW-REL-107-R4 | `54186367fa2e2be07395055f4106dae15e4a491f253b878e1456413f16b89aea` |

组装包共 3,117,612 字节，SHA-256 为 `6aec9ac5d489396684e22ef803f302808d0ebd9691134b34d2b70f746522dc86`。Release Reviewer 核对了包内 546 个成员，394 件与组装树原字节一致，另 152 件仅有换行差异。

Package QA 在隔离消费项目离线安装，启动返回 0.102.0、实际技能根和项目根。按问题词查回 `learn:footfall`，按引用定位中文路径的原件。回复省略原件正文，无关查询返回空结果。收口核对初始四项计数均为零，改变原件后报告 `changed=1`。包体验收回执 SHA-256 为 `d1e9a7eb6695b976dcabd77202ac7e03cee53ccb74c0c66eb9cf6d8287bf552a`。

回退演练用上一版公开附件切回 0.101.1，恢复原单元并读取原件。重新安装本次组装包后，查回 `learn:capture` 且收口核对通过。核对的六项消费项目文件前后逐字节一致。回退回执 SHA-256 为 `6c1126cd71e9721f3f64f2f892cccb9d666fa7f9a4ce484f45edcbd17bdb4053`。

冻结候选的完整发布门须记录实际提交、原始退出码和命中项。若治理健康检查仍命中历史告警，按本次发行的用户裁决处理。候选状态及后续转换见[原生发布账本](../../skills/software-project-governance/core/releases/0.102.0.json)。
