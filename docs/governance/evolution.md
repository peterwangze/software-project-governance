# 工作流的职责与演进方向

用户的原始意图和交付物的完成条件，应能从第一次对话一直追溯到最终验收。维护者在新增规则、选择工具或退出旧能力时，先指出哪位用户在什么操作上受阻，以及改动会怎样改善交付。

## 循环与门禁各自承担什么

每笔工作从一个可验收的目标开始。立项确定范围，准备循环验证选型和环境。交付时，内层围绕一次修改反复执行、观察和复审，中层把多个修改交成一个用户可验收的工作单元，外层依据使用反馈决定下一轮目标。多个工作单元可以同时处于不同的层和轮次。

Gate 的结论要能指回当轮的工作单元、被检查的成品和验收依据。复审发现缺陷时，把失败样本交回处理它的那一层。修正后用原条件复验。发布决定另有其范围和授权。跨会话接续时，维护者需要知道还有哪笔交付受阻、上次看见什么、接下来由谁处理。

角色、技能和基础设施按实际调用保留。执行者在需要时取用调研、实现、测试或发布能力；审查者沿原件独立验收。一份回执应能同时供后续执行、状态显示和恢复使用。删减某项能力前，用实际事务找出它的调用者和独有保障，再验证保留的入口仍能让成功交付、让失败返回正确的位置。

例如，修正启动器标题时，工作单元只登记一次目标、启动命令和预期输出。命令仍打印旧标题时，内层保留这次输出并要求返工。修正后重跑原命令，下一位维护者可以从同一单元查到前后两次结果。需要独立签收的成品则沿事先约定的成品验收条件复验。[可重放的运行入口用例](../../skills/software-project-governance/infra/tests/test_loop_workflow.py)

## 一笔事务怎样推进

| 工作流负责什么 | 谁行动，留下什么 |
| --- | --- |
| 意图识别、事务分解 | 协调者与用户对齐成品、约束和验收入口，拆出能独立验证的事务。保留原话和未决取舍。 |
| 路径规划、落盘契约 | 依据缺口、依赖和预算选下一步。把范围、负责人、资源与验收方法放进现有工单。宿主提供权限、隔离和执行能力。DSH 已获授权的单项直修沿原生入口领取任务。 |
| 主动探索、兼容开放 | 新领域、资源选型、重复失败或准备自建通用能力时，执行者先探测当前平台和项目已有能力，再查社区代码、工具、素材或方法。核对上游与版本，用实际输入试用，把采用或淘汰的理由和复验入口交给下一人。受限时写明哪一步无法验证。 |
| 过程看护、循环演进 | 由能观察成品的人按契约验收。协调者依据回执收口、修正路径或请用户裁决。缺证据时保留未知，出现新事实时更新同一份契约。领域验收由项目和领域工具承接。 |

现有入口为[探索协议](../../skills/software-project-governance/references/behavior-protocol.md#m10-主动生态探索协议exp-0105)、[普通派发工单](../../skills/software-project-governance/references/agent-dispatch-template.md)和 [DSH 原生入口](../../adapters/dsh/README.md)。

## 哪些事实改变了取舍

- **让真实需求决定下一轮。** AUDIT-160 的 12 项候选全部来自内部信号。DEC-377 据此冻结尚无新需求的工作。DEC-388、389、393、395 将原始意图、验收缺口和宿主直修回执连起来。本次从活跃表移出 11 项冻结工作和 1 项候选，对同一份计划只移除这些行，正常入口仍返回相同的 6 个候选，顺序也相同。路线图保留逐项编号和解冻条件。[历史复盘](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/research/audit-160-evolution-thesis-2026-10-28.md)
- **比较在成品上可见的差异。** AUDIT-158 的 12 个回溯样本里，4 个值得探索，4 个都缺少可追溯引用。AUDIT-162 的候选字体虽覆盖 569 字中的 568 字，在游戏实际字号下仍发生字形碰撞。另一次 Codex 交接，QA 在 DSH 的同一份配置上验证 PyYAML 可保留第 7 行的自定义标签，另一候选在该行报错。两次试验都得到了可复验的取舍。[字体验收样本](../research/thin-open-transaction-routing-2026-11-18.md) · [DSH 配置试验记录](https://github.com/peterwangze/software-project-governance/blob/7f49227a973955502dea67b7880eb501810eb391/docs/governance/evolution.md)
- **让每项职责只在实际承担者处出现。** DEC-396 复盘普通派发时发现，工单让执行者重复处理协调者的锁和审查记录。移出这些段落后，独立 QA 用工单交接的 markdown-it-py 渲染并核对了全部 11 个字段。相同口径下，普通模板正文由 4,528 降至 886 个 UTF-8 字节。确认宿主、权限和交付物所需的独立验收仍有自己的入口。[派发协议](../../skills/software-project-governance/references/behavior-protocol.md) · [markdown-it-py 上游](https://markdown-it-py.readthedocs.io/en/latest/using.html)
- **让旧实验随证据退出。** 迁移工具曾从治理仓目录结构猜测其他项目的工作单元。在两个真实项目上，旧推断均未给出可用候选。现行入口从目标和验收条件直接建立单元。历史推断工具及试验记录可以在当时的版本回放。[历史迁移实验](https://github.com/peterwangze/software-project-governance/blob/36f0b633e3f446e721d3e35b7ba04bd30d936f54/docs/migration/dynamic-flow-gate-migration-0.55.0.md)
- **同一次验收应能一次写完，日后能打开当时的原件。** 在两条写命令之间中断，会留下证据而任务仍在原状态。一次事务写入通过了同样的中断试验。按编号找历史的五道题，现行归档指针已全部命中；同号记录与勘误需要各自的原文位置。先在真实事务比较填写和找回的成本，再决定是否引入新的存储。[治理记录写入与检索实验](../research/process-records-storage-retrieval-2026-11-19.md)

## 怎样判断一条角色指令值得留下

SkillsBench 在 87 个任务、18 组模型与宿主配置上，加入针对任务编写的技能后，平均通过率从 33.9% 升到 50.5%。SWE-Skills-Bench 把 98 个公开技能分别放入真实软件仓库做配对验证，其中 92 个没有显著效果。两项研究的任务和技能来源不同。维护本项目的提示词时，先选一个真实失败和一个本来正确的对照，在相同输入、权限下看交付结果。[SkillsBench v4](https://arxiv.org/abs/2602.12670v4) · [SWE-Skills-Bench v2](https://arxiv.org/abs/2603.15401v2) · [Agent Skills 的评测方法](https://agentskills.io/skill-creation/evaluating-skills)

| 事务 | 本项目采用的做法 |
| --- | --- |
| 代码评审 | 借鉴 Claude Code 审查插件对候选发现的二次核验。沿真实调用方比较改动前后的行为，用输入、位置、影响和能推翻初判的证据解释结论。评审者只读，复用原有审查和返工入口。[上游审查命令](https://github.com/anthropics/claude-plugins-official/blob/c905cd8fec340e465dd66990b82b95b6e45db212/plugins/code-review/commands/code-review.md) · [本项目审查技能](../../skills/code-review/SKILL.md) |
| QA 与测试审查 | 借鉴 Aider 复用项目测试命令、把失败回交给执行者的方式，以及 k6 按指标定义阈值的做法。测用户入口和最终状态，保留每项指标的单位、方向与适用范围。单项验收可以独立完成，正式 G7 仍核对完整材料。[Aider 测试反馈](https://aider.chat/docs/usage/lint-test.html) · [k6 阈值](https://grafana.com/docs/k6/latest/using-k6/thresholds/) · [本项目测试技能](../../skills/stage-testing/SKILL.md) |

FEAT-124 用 FIX-502 的修复及逆向变更、AUDIT-165 的两组归档数据做了四题匿名配对。新旧指令均满足预先冻结的 12 项判据。用 k6 回放既有观测，延迟上限、命中下限和阈值相等的四次判定都符合预期。另用上游 `skills-ref` 校验三份技能并生成全库 26 项发现清单，独立执行者仅凭名称和说明就为五个请求选对了入口，包括一次无需技能的请求。这些结果支持保留精简后的指令。整体成功率和交付耗时仍需用更多真实任务测量。[Agent Skills 参考实现](https://github.com/agentskills/agentskills/tree/83021e2be457a9b6679148719c1f6074f0ad975e/skills-ref)

## 从目标到验收的回放

用 FEAT-126 的同一项用户操作检查八项职责。用户需要在独立宿主中运行维护命令，安装目录含空格。仅查看治理仓内的测试结果会漏掉这个条件。

| 环节 | 可复验的判断 |
| --- | --- |
| 意图识别、事务分解 | 保留需求依据，将「在独立宿主按文档运行命令」单独验收。立项的需求依据可以是原话或决策引用，读者可回到原件辨别。 |
| 路径规划、落盘契约 | FEAT-127 复盘时，旧立项命令丢掉了验收原文，重复提供来源只留下最后一个，旧执行包还推荐用户项目里不存在的测试。现在执行包引用本次立项原件，并复用已给的文件范围和验收条件。宿主的实际验收命令由熟悉该项目的人填写。 |
| 主动探索、兼容开放 | 用开源 markdown-it-py 从原始文档抽出命令，再交给 PowerShell 在含空格的目录执行。后续工作可以沿原件找到全部候选及来源。采用哪一项，仍需附上本事务的试用结果。[解析器的源行映射](https://markdown-it-py.readthedocs.io/en/latest/using.html) |
| 循环演进、过程看护 | 三条旧命令实跑失败。修正路径引号后，沿用原样本和验收条件，三条命令均通过；移走索引文件时完整性检查仍拒绝通过。独立审查依据变更内容和运行回执签核，执行包里的验收原文只说明要证明什么。[修正及其差异](https://github.com/peterwangze/software-project-governance/commit/3595ccc6cc45e360f03f92e6b731e8ef8d9c5fdd) |

历史工单缺少验收原文时，只使用仍可查到的计划或已维护的执行契约。新的候选来源可重复传给 `change-triage --prior-art`，受理时按顺序保留。需要换路时，在同一授权范围内用原标准复测备选，并把失败样本交给复审者。[立项入口](../../commands/change-triage.md) · [派发模板](../../skills/software-project-governance/references/agent-dispatch-template.md)

## 保留与退出的依据

FEAT-125 把 DSH 安装说明收回适配器，让影响证据直接引用已审查的 Git 内容，让普通启动复用一次根定位。三次调整都保留了用户原来的操作入口。继续精简时，可以从一笔事务反向追踪事实由谁产生、谁要据此作决定，以及哪种失败需要停止。日常技能保留这些判断，恢复、升级、清理的操作细则在触发时读取。单独分发 `skills/` 的宿主也必须能完成承诺的操作。[宿主分发契约](../../skills/software-project-governance/core/protocol/plugin-contract.md) · [FEAT-125 变更](https://github.com/peterwangze/software-project-governance/compare/411a4b3...2a4e696)

技能前言曾多出一行，十一条关键契约正文未变，同一份内容却需要重新登记行号才能通过 CI。维护检查现在用 Markdown 章节定位，再对原始正文验摘要。无关段落可以移动。同名章节、已审条款的删改或把整段藏进代码示例都会触发复核。历史清单仍能按当时的行段还原。[原行号修正](https://github.com/peterwangze/software-project-governance/commit/a4b1aa421ee449f55c24fc2889acc832a0b21ba2) · [Markdown 解析器的源行映射](https://markdown-it-py.readthedocs.io/en/latest/using.html)

在 Codex 和 DSH 接到合适的真实事务时，分别观察新资源获用、试用后淘汰、探索受限和成熟直修。每组对照保持输入、权限、预算和验收标准相同。从派发开始计时，直到执行者第一次直接查询、复现或试用与验收缺口有关的资源。未到达这一步的任务也计入受理总数，记下暂停原因。比较两条路径时先看成品和通过率，再在同质量的结果间比较耗时与成本。普通 Codex 交接和 DSH 本地入口已有回执，DSH 同条件模型成品仍待补样。

同一缺口在多个项目重复出现，才考虑上移到治理核心。退出一项责任前，找出当前读取者、独有保障与承接点，分别验证正常入口、错误输入和旧版回放。当前承诺和独立签收证据继续按原索引查阅。历史材料按原路径执行 `git show 7f49227:<路径>`，更早一批可使用 `7b9fd37`。[本轮清理前的版本树](https://github.com/peterwangze/software-project-governance/tree/7f49227a973955502dea67b7880eb501810eb391)
