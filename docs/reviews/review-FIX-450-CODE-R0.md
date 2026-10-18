# FIX-450 入口预算与契约迁移 CODE R0

- 日期：2026-10-18（Asia/Shanghai）；独立回归执行于 2026-10-17，恢复审查后复用其已保存原始结果，预算及候选核对于 2026-10-18 完成。
- 结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- 审查基准 HEAD：`f0910607beaf5480b2f1d80718c8b639c4c34eda`
- 审批范围：FIX-450 的入口文字迁移、新执行细则和诊断文档；SKILL 提交对象必须是下述排除 FEAT-098 WIP 的候选。本结论不审查或批准 FEAT-098，不替代全项目 CI 或发布验收。

## 对象与提交候选绑定

| 对象 | 文件字节 SHA-256 |
| --- | --- |
| 当前 `skills/software-project-governance/SKILL.md`（含保全 WIP，仅作为比对上下文） | 820686802ac7a47344d54a691dd598bc2d7ac58f1fe0b3aee6e8647aa7a9f539 |
| `skills/software-project-governance/references/behavior-contract-details.md` | e2f9899ee060dd2126a917a34bd34965edc73e1450f6a112d8b5108a6cb879ac |
| `docs/diagnostics/fix-450-skill-budget.md` | 29ea6d5f9a7635ba85a29976b6bd7ea27f1359077051e4f624ef389a75255112 |
| `.governance/candidate-FIX450-SKILL.md`（将送 SKILL 路径的候选内容，仅读） | 6c0c5e54db1cd4839bb4d4a10544846fee326e019728ca2c42e49f5f8e88e6c3 |
| `.governance/preserved-FEAT098-SKILL-block.bin`（1336 bytes，仅读） | 315383712a7dcc55a9a5ae426555f4bc41549e82a3255be3fedba0d423e9b058 |

独立读取候选字节并执行无写入的 `git hash-object --path=skills/software-project-governance/SKILL.md --stdin`，按目标路径 Git 属性规范化后的 **index blob 为 `22d96c593777e7be66cbf0299d9135160ce539d7`**。不应用路径过滤的原始字节 blob 为 `38544b14189b785886a4b58f740ac8507c4acff4`；二者差异来自文本换行规范化，不能把 raw SHA-256 与 Git blob 混称。审批绑定上述候选内容与目标路径映射，不授权整体 stage 当前含 WIP 的工作树 SKILL。

独立断言全部通过：

1. 原 FEAT-098 块在 before 与当前 SKILL 中各出现一次，原始字节 SHA-256 完全一致；候选严格等于当前文件只移除此块，其他字节不变。
2. before 移除此块并规范化换行后与 HEAD 完全相同。因此没有把其他未识别 WIP 混入本票。
3. 排除健康摘要、关键契约/执法、自动化分级三处迁移区域后，候选剩余全文与 HEAD 完全相同。候选仅含 FIX-450，未改版本、其他规则或 FEAT-098 正文。

## 语义与可达性审查

**原文保全**：从 HEAD 独立提取 C1–C11 十一条正文及 bootstrap-health、enforcement、automation-levels 三块，与新细则作精确匹配，**14/14 全部逐字承接**（规范化文本换行）。C5/C6 frozen 文本还在入口逐字保留。独立比对记录及各单元 SHA-256 在 `.codex-sandbox/FIX-450/review-r0/semantic-and-candidate.json`。

**触发器**：入口仍逐条列出全部十一项，intro 明确写十一条；统一要求任一触发在动作前 MUST 读取对应完整细则，细则不可读即停止。C1 保留复审/熔断/唯一通过终态/delta，C2/C3 保留推荐与依据门，C4 保留真实环境三选一和逐命令留痕，C7–C9 保留派发、事件化健康与单源，未将强制步骤改成可选提示。未新增默认许可或降级豁免。

**FEAT-097**：每轮 `goal-bridge --action record`、四维危险区收口、warning 仅披露、DRAINING 仅在途、检查点用户裁决、BLOCKED 未授权拒收、恢复授权命令、跨会话幂等与规则变更披露、阈值/映射和 off 退路全部在 C10 原文；入口仍有对应触发和禁止静默续跑的安全边界。

**FEAT-095**：六边界及 exit 2/3/4、四类硬阻断、白名单仅限相关阻塞复审、task/channel scoped、全局新工作准入限流、WIP checkpoint、异常 fail-closed、off 零副作用、机器记录和 remedy 全部原文迁入。入口仍列六边界、退出码、关键边界和仅协议+CLI的能力限定；未宣称宿主拦截已接线。原文已有的 exit 4 提示/动作放行表述保留，没有在本票改变执行器判据。

**健康摘要与分级**：会话先快路径、deferred 显示待检查、四态/NOT_RUN、N=unknown、只读摘要、超时降级、推进前必须 full、安全不随 legacy 回退均有入口触发和原文细则。A/B/C 区分、C 未实现、write-guard 的 B 检查器+A协议触发、post-commit advisory 及其权威/回退时点均保留。

**可达性**：候选中四个细则文件链接均指向实际新文件；C1–C11 及三个命名锚各唯一出现，入口以文件链接+§标识指向，未继续使用已知校验器不识别的 URL fragment。新文件位于已有 references 产品目录规则覆盖范围；Producer 的 manifest/cross-reference 成功日志已阅读，未修改校验器消除报错。按需细则是强制规范承接，不是删除正文后依赖记忆。

## 独立预算测量

使用当前原版 `checks.injection_budget.check_injection_budget()`，只复制其声明的真实注入源到仓内临时预算夹具，再分别换入 before、当前、候选 SKILL。没有修改计价算法、阈值、surface 表或测试。结果见 `.codex-sandbox/FIX-450/review-r0/budget-measurement.json`。

| 面 | Before | 当前工作树 | FIX-450 提交候选 | 原线 |
| --- | ---: | ---: | ---: | ---: |
| SKILL calibrated tokens（含 FEAT-098 的前后可比口径） | 18574 | 15440 | — | 16000 |
| SKILL calibrated tokens（排除 FEAT-098，HEAD→候选） | 18160 | — | 15026 | 16000 |
| 关键契约 UTF-8 bytes（使用原测试同一截取法） | 9648 | 3719 | 3719 | 4096 |
| resident lightweight | 4441 | 4441 | 4441 | 6200 |
| resident standard | 5925 | 5925 | 5925 | 6200 |
| resident strict | 6197 | 6197 | 6197 | 6200 |

FIX-450 自身的同口径入口缩减为 **3134 calibrated tokens**；候选比含 WIP 的当前版本少 414 tokens 是排除 FEAT-098 的结果，不混记为 FIX-450 的额外收益。before 的 skill tier 为既有 report-only，故 API 顶层依然可能 PASS，但其 `skill_over_budget=true`；本审没有将该信号描述为原 API hard FAIL。当前与候选三 profile 均无 issues，skill_over_budget=false。

独立反向控制将 standard resident 预算由 6200 设为 5924：真实 5925 tokens 导致 **FAIL / resident hard-gate issue**。原硬门没有被文档迁移绕过。细则整份在实际加载时另约 **5038 calibrated tokens**，不在既有默认 surface 表；本票只降低入口预算，不能据此声称触发细则后的总执行成本或账单同幅下降。

## 测试、五维度与 AI 专项

已保存的独立回归在 2026-10-17 执行，**105 tests / 0F / 0E / OK / exit 0，6.651s**；恢复后源对象 hash 与文本未变，未重复整组。覆盖 budget gate 11、provenance 41、behavior profile 49、DSH injection-contract 3、FEAT-095 protocol 面 1。包括缺锚拒收、条5/6及计数、4KB、resident hard/防降级、full/legacy 边界与执法锚；FIX-450 没有修改这些测试。

| 维度 | 结论 |
| --- | --- |
| 正确性 | 通过：14 原文单元保全、十一条计数、强制读取和候选范围一致；独立预算及相关回归符合预期。 |
| 安全性 | 通过：授权、拒收、升级、真实环境防护、预算收口和执法边界保留；缺细则明确停止，无新许可面。 |
| 可维护性 | 通过：入口触发器与 C/§标识映射明确，按需细则有唯一命名锚；候选只涉及三处迁移，无冗余代码改动。 |
| 性能 | 预算面通过：原计价口径下入口下降，resident 未变；不把延迟加载负担或计费收益包装成实测性能提升。 |
| 测试覆盖 | 通过本范围：105 项独立回归与三 profile/candidate/负向预算核验；不替代远端 CI、实际 agent 行为或发布测试。 |

AI 五项均完成：无新 mock/硬编码成功返回/幻觉 API/未实现 TODO/无关扩展；本改动是规范文字迁移，命令及能力均沿用原实现，不新增执行或安装逻辑。

## 证据与范围备注

仓内证据根：`.codex-sandbox/FIX-450/review-r0/`。`regression.json` 与 `budget.json` 含真实 argv、cwd、UTC 起止、exit 和访问范围；TEMP/TMP/DSH_HOME 均重定向仓内 scratch，无 SDK 读取、DSH 启动或用户应用配置写入。预算运行 UTC 为 2026-10-18 11:57:12.756868→11:57:13.013003，exit 0。证据 SHA-256：

| 证据 | SHA-256 |
| --- | --- |
| regression.json | bc68bda576edd12a5b6f27fa869679dc7f6ddea6d00fa0ecf5678b32fec716b9 |
| regression.log | a6fe31c1ba0746d669b4741aeb4d388ffe9a1de8c9857998d88369c0de039030 |
| budget.json | f4056486450b8607e2fedb21b7e2441965229d8cc50d70f7f687d0b2660b8c65 |
| budget-measurement.json | a27493ea57f794cdac33520b173a19b73281c852570e1916f628cfcd807d19e4 |
| semantic-and-candidate.json | af89df72e0d6b11713209bbffa9d6b6dc5a78ab719afdbbd2e50eb6c64d4125f |

P0=0，P1=0，P2=0；P3 范围备注：

- **N1 / P3**：Coordinator 只可将已绑定的候选送 SKILL 目标 index，保留工作树 FEAT-098 原块单独处理。此批准不包含 FEAT-098 文字本身或其能力验收。
- **N2 / P3**：strict resident 仍只余 3 tokens，未通过本票扩大；按需细则仍有加载成本。需要未来容量/成本结论时应重新按对应注入与调用口径测量。
- **N3 / P3**：全套单测、GitHub Python 3.11、宿主实际按需读取行为和版本发布未在本轮验收；FIX-453 R1 既有审查不可被本报告替换或扩范围。

五维度、AI 五项、设计/安全一致性与分级硬门槛已完成，无本范围未解决阻塞。Reviewer 仅新增本报告和仓内 scratch 证据；未修改三份待审对象、候选、保全块、index 或治理记录，未提交或实际安装。
