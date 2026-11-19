# Agent 调度模板

Coordinator 负责派发前的并发预检、取锁和收尾。派发使用宿主的子代理入口，只发送填好的下方工单。锁与隔离见[行为协议 M7.6、M7.6a](behavior-protocol.md)，审查结论由 Coordinator 按 M7.4 用 `review-record` 记入。

## 模板

````
## {task_id} — {task_summary}

你是 {agent_role} Agent。执行前依据角色定义 `{role_definition_path}` 和任务规范 `{task_skill_path}` 工作。宿主已注入全文的部分直接使用，其余从相应路径读取。

- 任务与原意：{task_description}
- 可修改范围：{file_list}
- 优先级：{priority}
- 验收标准：{acceptance_criteria}
- 执行约束：{hard_gates}
- 真实环境约束：{destructive_redlines}

按任务描述执行；如有待试用的资源，先在授权范围内用本事务样本验证。按约定入口验收，返回工件、观察和待解决项；采用或排除候选时交回理由与验收证据。

只修改授权范围内的文件。用户交互、最终决策、跨代理协调及治理状态写回由 Coordinator 负责。仅在工单已预授权时，可向指定 incidents 日志追加真实环境操作记录。
````

## Coordinator 填写

| 占位符 | 填入内容 |
| --- | --- |
| `{task_id}`、`{task_summary}`、`{priority}` | 沿用现有任务编号、摘要、优先级。 |
| `{agent_role}`、`{role_definition_path}`、`{task_skill_path}` | 角色名及本次实际使用的角色定义和任务 SKILL 路径。 |
| `{task_description}` | 用户原意、本次要解决的具体缺口。依[行为协议 M10](behavior-protocol.md) 判断，需探索时先用宿主已授权的渠道检索，交接候选来源、取舍和试用结果，或说明待试项。可跳过或受限时写明依据和可行路径。已有回执可直接引用。 |
| `{file_list}` | 获准修改的路径。只读任务注明只读。 |
| `{acceptance_criteria}` | 要交回的工件、正常验收入口、可观察的完成条件及结果记录位置。 |
| `{hard_gates}` | 此事务的硬门槛。执行包有建议步数预算时在此标明建议值。 |
| `{destructive_redlines}` | 按下节填写。 |

## 真实环境任务

目标含仓库外路径、验收或描述涉及用户真实环境，或 triage 给出 `analysis.side_effect.touches_real_env=true`，任一成立就将以下红线捆绑包逐字填入 `{destructive_redlines}`。其余工单填「不适用——本任务无用户真实环境操作」。

```
【破坏性红线】禁止对用户 HOME 下任何配置目录执行删除/清空/重建/移动；构造测试场景一律使用临时目录；对用户环境的全部写操作限制为安装目标自身的追加式写入。

【配套规则 R1——真实环境三选一】任何涉及用户真实环境（$HOME 下配置目录、$DSH_HOME、仓库外任意路径）的测试/验收/安装操作，执行前必须满足三选一并留痕：(a) 隔离环境——环境变量重定向至临时目录（如 DSH_HOME=<tempdir>）；(b) 事先完整备份 + 操作后一致性校验；(c) 用户经 ask_user_question 逐项授权。三者皆缺禁止执行，无豁免。

【配套规则 R4——真实环境命令逐条上报】你在用户真实环境执行的每条命令必须在结构化返回中逐条上报（命令、时间、退出码、影响路径），由 Coordinator 于收到当下机写 evidence 行留痕；无上报的真实环境操作按违规处理。仅当本派发 prompt 预授权 incidents 留痕文件（.governance/incidents/{task_id}-*.log）时，方可向该文件追加实时命令日志（仅限该路径、仅限追加）——这是「不修改 .governance/ 治理记录」禁令的例外之一（另一例外=Coordinator 自身的治理写回职责，不受本禁令约束）。
```

真实环境任务同时在 `{hard_gates}` 传入隔离变量纪律：PowerShell 使用非保留的 `$tmpHome` 保存临时目录并显式设置 `$env:DSH_HOME`，禁止给 `$HOME` 或任意大小写变体赋值。R4 逐条上报同样适用于隔离命令。红线原文的变更须经决策记录，R1、R4 以[行为协议 M7.7](behavior-protocol.md) 为准。
