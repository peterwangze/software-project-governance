# v0.100.0 累计发行签核

本版以公开标签 `v0.99.0`（提交 `fb564155d6ef0f9bfbc9ec6f56c9061435dd9f0d`）为累计起点。用户先确认了 FEAT-131 的合并与累计发布，再确认将 DSH 桌面兼容性修复纳入本版。[累计范围](version-plan-0.100.0.md)

| 复核环节 | 审阅对象与结论 |
| --- | --- |
| FEAT-131 合并 | 独立审查与成品验收覆盖旧工作单元接续和反馈复用。GitHub 对提交 `b3e88706438fad6e06516dfd71f69ddd283de164` 的检查成功后，PR #2 合入 master 的 `06133876f621e3a97921527adeffd6b6d1f1298c`，主干检查也已通过。[PR #2](https://github.com/peterwangze/software-project-governance/pull/2) · [提交 CI](https://github.com/peterwangze/software-project-governance/actions/runs/44852888293) · [主干 CI](https://github.com/peterwangze/software-project-governance/actions/runs/44853363141) |
| Code Reviewer | 版本组装提交 `6b7e6820f9012560fa40a3807f46779ab6f2476e`，Git 树 `0c2b6ffe71454a481755f3d0a3585064bd0109d1`。审阅累计差异、投影与可重放性，结论 **APPROVED**。[版本检查](https://github.com/peterwangze/software-project-governance/actions/runs/44857240363) |
| Release Reviewer | 从同一 Git 树生成源码归档，运行 `npm pack --ignore-scripts`，将 SHA-256 为 `5f0140929b1911c02add44fc8439aed19718f32149c1fded7c1ae2187faccea9` 的版本组装包离线安装到空消费目录。JS 入口、已安装 CLI、宿主对照和用户文件保护均已实测，结论 **APPROVED**。此 SHA-256 对应签核时的版本组装包。 |
| 发行动作 | 添加本签核记录与原生候选清单，随后只提交清单由候选转为已发布的变更。对应的 Git 树、附注标签剥离值与附件的最终校验值由发布账本与 GitHub Release 记录。[发布账本](../../skills/software-project-governance/core/releases/0.100.0.json) · [GitHub Release](https://github.com/peterwangze/software-project-governance/releases/tag/v0.100.0) |

### 实际交付

在空消费项目登记用户原话和订单验收条件，关闭进程后用包内 CLI 重开订单，核对订单号。随后依据已落盘的反馈登记新增承运人字段的机会，显式选中该机会，再从新进程确认原单元保存原话、后继单元保存新目标。检验同时覆盖首次 bootstrap 和包的公开 JS 导出。

干净源码的完整性、版本、清单、引用、27 项投影与 10 项旧快照检查均通过。ArchGuard 报告零违规。GitHub 在上述提交上完成 Linux 测试与引用检查。

从同一包在独立的 DSH_HOME 生成预设，分别运行公开命令 `dsh-doctor --stage S1 --stage S2 --json`。桌面版通过实际 Electron 与 app.asar 校验，npm CLI 通过安装侧的 Node 与宿主包校验。

| DSH 对照 | 成品目录与工具行 |
| --- | --- |
| 桌面 0.2.2-rc.5，新预设 | S1、S2 均通过，26 个启用行中 22 行通过宿主配置校验，另 4 行的模块未提供配置 schema。 |
| npm CLI 0.2.1-rc.2，新预设 | S1、S2 均通过，26 个启用行中 20 行通过宿主配置校验，另 6 行的模块未提供配置 schema。 |
| 桌面 0.2.2-rc.5，升级前的旧预设副本 | S1 报出残留、缺项和来源缺失。S2 指出 `./list-agents` 已无导出，命令退出 1。诊断前后，真实用户的 governance 预设目录内 4 个文件的哈希逐项一致。 |
| 含人工编辑的新预设 | 重跑安装后退出 2，手工写入的内容完整保留。 |

### 恢复与实测边界

在隔离检出的 `v0.99.0` 和空客户项目实测旧版 bootstrap，可解析正确安装根。使用匹配的 npm CLI 0.2.1-rc.2 在新 DSH_HOME 安装旧版预设，并重跑 S1、S2，均通过。旧预设与手工编辑应先完整备份，在副本中核实恢复结果后再切换。[回滚方案](rollback-plan-0.100.0.md)

本次实测覆盖命令、文件、实际宿主配置和回滚。完整真实模型会话、宿主设置页的展示、跨项目验收成功率和耗时仍需独立样本。[已验证范围](version-plan-0.100.0.md)
