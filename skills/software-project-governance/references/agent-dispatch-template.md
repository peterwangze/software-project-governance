# Agent 调度模板

需要派发子代理时，Coordinator 按[行为协议 M7.6、M7.6a](behavior-protocol.md) 预检并发、取锁和收尾，通过宿主仅发送填好的工单。审查结论按 M7.4 用 `review-record` 记入。

## 模板

````
## {task_id} — {task_summary}

你是 {agent_role} Agent，按角色定义 `{role_definition_path}` 和任务规范 `{task_skill_path}` 执行，只补读宿主尚未注入的部分。

- 任务与原意：{task_description}
- 可修改范围：{file_list}
- 优先级：{priority}
- 验收标准：{acceptance_criteria}
- 执行约束：{hard_gates}
- 真实环境约束：{destructive_redlines}

有待试资源时，在授权与预算内用事务样本验证并交代取舍。候选未达标，用原验收条件复测可行备选。交回工件和验收结果，仍受阻时附失败样本和待决项。

只修改授权范围内的文件。用户交互、最终决策、跨代理协调及治理状态写回由 Coordinator 负责。仅在工单已预授权时，可向指定 incidents 日志追加真实环境操作记录。
````

## Coordinator 填写

| 占位符 | 填入内容 |
| --- | --- |
| `{task_id}`、`{task_summary}`、`{priority}` | 现有任务编号、摘要和优先级。 |
| `{agent_role}`、`{role_definition_path}`、`{task_skill_path}` | 角色名、角色定义和绑定的 SKILL 路径。 |
| `{task_description}` | 用户原意、单元 ID、父单元及本轮需要解决的缺口。宿主 `.governance/<intake.record>` 给出受理依据和候选资源 `prior_art`。当前来源沿用 `task-priority-analysis` 的裁决；有修订时从 `intake.demand_revisions` 取依据，旧包缺少定位可用 `execution-packet --task <ID>` 刷新预览。按[行为协议 M10](behavior-protocol.md) 从宿主授权渠道补缺，引用试用回执或标明待试项。跳过或受限时注明依据和可行路径。 |
| `{file_list}` | 获准路径。沿用已明确的 `allowed_change_scope`，只读任务标明只读。 |
| `{acceptance_criteria}` | 沿用已明确的 `acceptance_contract`，给出工件、正常验收入口、可观察的完成条件和结果位置。 |
| `{hard_gates}` | 本事务的硬门槛。有建议步数预算时注明建议值。 |
| `{destructive_redlines}` | 按下节填写。 |

## 真实环境任务

目标含仓库外路径、验收或描述涉及用户真实环境，或 triage 给出 `analysis.side_effect.touches_real_env=true`，任一成立就将以下红线捆绑包逐字填入 `{destructive_redlines}`。其余工单填「不适用——本任务无用户真实环境操作」。

```
【破坏性红线】禁止对用户 HOME 下任何配置目录执行删除/清空/重建/移动；构造测试场景一律使用临时目录；对用户环境的全部写操作限制为安装目标自身的追加式写入。

【配套规则 R1——真实环境三选一】任何涉及用户真实环境（$HOME 下配置目录、$DSH_HOME、仓库外任意路径）的测试/验收/安装操作，执行前必须满足三选一并留痕：(a) 隔离环境——环境变量重定向至临时目录（如 DSH_HOME=<tempdir>）；(b) 事先完整备份 + 操作后一致性校验；(c) 用户经 ask_user_question 逐项授权。三者皆缺禁止执行，无豁免。

【配套规则 R4——真实环境命令逐条上报】你在用户真实环境执行的每条命令必须在结构化返回中逐条上报（命令、时间、退出码、影响路径），由 Coordinator 于收到当下机写 evidence 行留痕；无上报的真实环境操作按违规处理。仅当本派发 prompt 预授权 incidents 留痕文件（.governance/incidents/{task_id}-*.log）时，方可向该文件追加实时命令日志（仅限该路径、仅限追加）——这是「不修改 .governance/ 治理记录」禁令的例外之一（另一例外=Coordinator 自身的治理写回职责，不受本禁令约束）。
```

真实环境任务同时在 `{hard_gates}` 传入隔离变量纪律：PowerShell 使用非保留的 `$tmpHome` 保存临时目录并显式设置 `$env:DSH_HOME`，禁止给 `$HOME` 或任意大小写变体赋值。兼容探测使用 `check-dsh-preset-compat --isolated-home <本次分配的绝对临时目录> --fail-on-issues`；目录由派发者独立给定。R4 逐条上报同样适用于隔离命令。红线原文的变更须经决策记录，R1、R4 以[行为协议 M7.7](behavior-protocol.md) 为准。
