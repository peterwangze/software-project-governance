# 证据编号前缀约定（EV- / EVD- 跨仓映射）

本文档是跨仓证据编号前缀的约定事实源（FIX-289⑥ / FIX-281⑥ 缺陷面）：说明 `EVD-` 与 `EV-` 两套前缀的语义、各自所属的编号空间，以及跨仓引用时的映射规则。背景：FIX-281 跨仓申报时，本仓 evidence 行（`EVD-`）与宿主仓（router 仓）evidence 行（`EV-`）因前缀形似且无映射说明产生歧义。

## 两套编号空间

| 前缀 | 所属编号空间 | 语义 | 机器解析方（本仓） |
|------|------------|------|------------------|
| `EVD-{n}` | **插件开发仓（本仓）** 的 host 治理空间 | `.governance/evidence-log.md` 的 evidence 行 ID，`n` 为本仓内单调递增编号 | verify_workflow.py（Check 13 编号缺口检测、Check 34 快照锚 S1/S3、完成证据判定）、archive.py（`| EVD-` 行迁移扫描）、infra/checks/evidence_domain.py |
| `EV-{n}` | **宿主项目仓（如 router 仓）** 的治理空间 | 该仓自己 `.governance/evidence-log.md` 的 evidence 行 ID，编号独立于本仓 | 本仓扫描器不解析宿主仓行；仅以「仓限定引用」出现在本仓文档中 |

要点：

- 两套空间**相互独立**：没有全局注册表，没有数值映射关系。`EVD-898` 与 `EV-898` 无任何隐含关联——前缀相似纯属历史，编号值不可互换解读。
- 本仓 evidence-log 内还有同表的兄弟行族（同一编号约定体系、非 `EVD-` 前缀）：`REVIEW-{task}-R{n}`（review-record CLI 机器写入的审查结论行，见 `infra/review_record.py`）、`TRIAGE-{task}`（change-triage 入账行）、`RECO-{task}`（task-priority-analysis 推荐快照行）。session-snapshot 的「下次会话优先级」必须引用 `RECO-{task}` 或 `EVD-{n}` 锚（behavior-protocol.md M7.4 step 6 / REQ-108）。
- 行模板权威源：`core/templates/evidence-log.md`。

## EV- 的本仓实证（跨仓引用实例）

宿主仓 evidence 行以「router EV-」限定形式出现在本仓文档中（这些引用指向 router 仓的 evidence-log，不在本仓解析）：

- 0.78.1 版本规划文档引用 `router EV-066`（2026-08-23）与 `EV-071/073`（2026-08-27）作为 FIX-281 九项缺陷面的实证留痕；
- REL-073 设计审查记录引用 `router EV-066/071/073` 与 `EV-038` 先例；
- 审计报告（`docs/requirements/audit-148-v1-verify-alarm-validation.md`）记录 router 侧任务族：router 仓的任务 ID 另有 `EVO-{n}` 族（如 EVO-004）与自己的 `FIX-{n}` 编号——**各仓的任务编号空间同样相互独立**，本仓 `FIX-281` 与 router 仓 `FIX-006` 等同名前缀编号互不相关。

Loop 运行时侧的关联记号：flow-unit 的 `gate_state.evidence_refs` 是自由字符串列表（`core/loop-runtime-contract.json`；infra/checks/flow_unit_runtime_v2.py 仅校验 list 类型，infra/loop_gate_processor.py 以 append 语义写入）。其元素没有强制格式，但应按下方映射规则书写，保证跨仓可读。

## 跨仓引用映射规则（约定）

跨仓申报 / 跨仓文档引用证据时：

1. **仓限定强制**：引用宿主仓证据必须写成「{仓名} EV-{n}」（如 `router EV-066`）；禁止裸写 `EV-{n}` 或 `EVD-{n}` 充当跨仓引用——裸编号无法定位所属仓，正是 FIX-281⑥ 歧义的根因。
2. **本仓证据用本仓行族 ID**：指向本仓治理证据时使用 `EVD-{n}` / `REVIEW-{task}-R{n}` / `RECO-{task}` / `TRIAGE-{task}`，不使用 `EV-` 前缀。
3. **不写跨仓路径字面量**：另一仓的文件位置以「仓名 + 行 ID」表述，不写成路径形式——跨仓路径在本仓不可解析，会被 check-cross-references 判为悬空引用。
4. **loop `evidence_refs` 元素**：指向本仓证据时写本仓行族 ID（如 `EVD-898`）或本仓 review 文件名；指向宿主仓证据时写「{仓名} EV-{n}」形式的字符串。
5. **映射说明的唯一事实源**：跨仓申报中需要解释两套编号关系时，引用本文档，不要在各申报文档中自行发明映射表。

> 边界说明：规则 1~4 是文档与申报的书写约定（本仓扫描器对 `EV-` 引用不做机器强制）；违反它们不会触发 check FAIL，但会复现编号歧义。跨仓行 ID 的真实语义以对侧仓的 evidence-log 为准。
