# 附录：Gate 表 / classic 判定产物消费点普查（ADR-019 附录基线 · FEAT-068 产出）

> **ADR-019 §8.4 / §4 RB-1+RB-3 缓解**：凡消费 classic 判定产物或 plan-tracker Gate 表的读路径逐点清单化——分族授权票翻转族变更时同步审计本清单；退役条件「兼容消费点清零」（ADR-019 §2.8 要素②）以本清单为机器可查基线。
> **普查方法**：真实仓库只读 grep + 源码逐点核对（锚点 file:line 全部实读核验于 2026-09-27，verify_workflow.py 行号基准 = 26358 行锚点态）。
> **权威署名口径**（ADR-019 §2.4）：下列消费点当前产出的判定均为 `authority: classic-g1g11`；翻转后各点须迁移为 loop-engineering 权威署名或降级为只读解释器。

## 1. 判定权威面（auto_judge / gate-check 消费链）

| # | 消费点 | 锚点 | 消费内容 | 翻转族处置 | 退役条件挂钩 |
|---|---|---|---|---|---|
| A1 | `verify_workflow.py::auto_judge_gate`（定义） | verify_workflow.py:17669 | gate_execution_registry 驱动的 classic 四值判定（passed/blocked/passed-with-conditions/needs_human），产出署名 classic-g1g11 | 「判定权威」族首点：该函数按族切至 loop 权威署名 | 族全宿主翻转后进入删除候选清单 |
| A2 | gate-check CLI 调用点 | verify_workflow.py:17787 / 25183 / 26238（argparse 注册） | 经 CLI 暴露 auto_judge 判定 | 同 A1 族 | 同上 |
| A3 | `review_record.py` GATE_VERDICT_TO_RESULT | review_record.py:75-79 | gate 引擎 verdict→review 结论映射（Wiring B，FIX-236.2/ADR-017 §3.4）；`needs_human` 无渲染即不接线 | 审查链族：翻转时同步映射 loop gate 结果→结论 | verdict 词表切换后替换映射表 |
| A4 | loop 附加分支接线 | verify_workflow.py:17787 区（需显式 unit_id，best-effort 降级） | classic 判定渲染后附加 loop 触发——AUDIT-155 C-09 判定主体仍是 classic | 接线族：unit 锚定桥就绪后切判定主体 | 与 E-1 unit 锚定裁决联动 |

## 2. 热数据投影面（bootstrap/呈现消费链）

| # | 消费点 | 锚点 | 消费内容 | 处置 |
|---|---|---|---|---|
| B1 | `bootstrap_aggregate.py::parse_gate_summary` | bootstrap_aggregate.py:121（`_GATE_SECTION_PREFIX = "## Gate 状态跟踪"`）、:296-315（`next_gate` 推导） | plan-tracker Gate 表→bootstrap `gates`/`next_gate` 投影——「下一个 Gate」坐标的呈现源头（C-10 呈现性权威） | 「呈现投影」族：切 loop face 时同步改造（ADR §6 步骤 3 主层级重排） |
| B2 | bootstrap gates 面聚合 | bootstrap_aggregate.py:643-644 | `payload["gates"] = parse_gate_summary(plan_text)` + budget 位 | 同 B1 |
| B3 | `_parse_plan_workflow_model` | verify_workflow.py:4101-4143 | Gate 表存在性→`classic-phase-gate` 模型判定；被迁移 idempotency/回滚 prior-model 读取复用 | 模型探测族：loop 宿主判定需同步（flow-unit-runtime 存在性优先） |
| B4 | `check_gate_consistency`（C-10 空转原址） | verify_workflow.py:9918-9972 | Gate 表 vs 证据一致性——FEAT-068 前实际校验仅 completeness/orphan（Gate 坐标零校验=病理本体）；其内惰性 `pass` 死码已于 FEAT-068 移除一处（净增行零化改造） | 已部分修复：机器面校验由 Check 3b（`check_evidence_binding_drift`）接管；classic 面维持 legacy 行为 |

## 3. 检查策略与注册表面

| # | 消费点 | 锚点 | 消费内容 | 处置 |
|---|---|---|---|---|
| C1 | 检查注册表 Check 3 | registry.py:429 | `"3": verify_workflow.check_gate_consistency` 注册消费 | Check 3b 并行注册（FEAT-068 已接线） |
| C2 | lifecycle registry 模式常量 | verify_workflow.py:2466-2467（`classic-phase-gate`/`dynamic-flow-gate`） | active/default 模式判定基线 | 「active 模式翻转」=授权票事项（ADR §5 影响面已列） |
| C3 | gate_execution_registry 结构校验 | verify_workflow.py:3373-3384（`_check_gate_execution_registry`：`status=active-classic-compatibility`、`classic_registry_execution=true`、`execution_scope=classic-g1-g11-only`） | classic 注册表契约执法 | 翻转票必须同步改写这些断言（§2.4 署名切换 diff 核查项的执法面） |
| C4 | registry 静态快照消费 | review_record.py:80-85（`classic_registry_execution=True` 等） | 同上数据面的 review 侧复述 | 同 C3 |
| C5 | claims 扫描守卫（唯一已在产 loop 代码） | checks/loop_runtime_claims.py:211/314/1298-1331/2622（installed_host/product_release/AUTHORITY_SOURCE_OCCURRENCE） | 阻止未经验证宣称 loop 已激活——翻转后方向需反转（允许宣称+验证署名） | 「runtime 声明」族随首张翻转票重定向 |

## 4. 入口/文档注入面（FIX-011 投影链）

| # | 消费点 | 锚点 | 消费内容 | 处置 |
|---|---|---|---|---|
| D1 | SKILL.md Gate/按需读取面 | SKILL.md:108/113/142/190/419 | next_gate/Gate 词汇与 Gate 检查必读注册 | 「协议呈现」族随步骤 3/4 重写（ADR §5 文档层清单） |
| D2 | CLAUDE.md 模式确认句 | CLAUDE.md:22 | `Gate {gate}: {status}` 坐标句 | 同 D1 |
| D3 | AGENTS.md（CLAUDE.md 薄指针投影） | AGENTS.md 对应行 | 同源投影 | 同 D1（经 governance-init.md 模板投影） |
| D4 | governance-init.md 注入模板 | commands/governance-init.md:108/201/284/468/488 | Step 7 注入模板 Gate/next_gate 槽位——canonical source | **模板先行**：任何入口句改造必须先改此处（FIX-011 链） |

## 5. 数据/工具面

| # | 消费点 | 锚点 | 消费内容 | 处置 |
|---|---|---|---|---|
| E1 | `discover_governance_context` 族 | verify_workflow.py:8752 区 | Gate 表进上下文包（e2e 消费） | 上下文族：loop face 并轨后切换 |
| E2 | e2e 测试面 | tests/e2e/test_governance_init.py:92 | check_gate_consistency 消费 | 随 C1 |
| E3 | 迁移工具 prior-model 读取 | loop_migration.py（`_parse_workflow_model` 宽容面）+ plan 族 `parse_workflow_model` | plan-tracker 模型行→prior 记录 | 退役时改为迁移适配器（ADR §2.8 classic 降级形态） |
| E4 | check-governance Check 3（dispatch） | verify_workflow.py cmd_check_governance（`gate_issues = check_gate_consistency()` + Check 3b 接线） | 聚合消费 | 随 B4/C1 |
| E5 | FEAT-068 新增：Check 3b 武装判定 | verify_workflow.py Check 3 tail compound 接线 → checks/evidence_domain.py | 机器维护面（flow-unit-runtime.json）漂移校验——本附录产出的第一处 loop 时代校验消费点 | 随真实迁移授权票进入常驻执法 |

## 6. 普查结论（退役条件基线声明）

1. **消费点总量**：22 处（判定权威 4 / 投影呈现 4 / 检查注册 5 / 入口文档 4 / 数据工具 5）。
2. **翻转 diff 核查项**（供每张分族授权票引用）：票内 diff 必须同时触及「对应消费点行」+「`authority` 署名迁移」+「本清单对应行状态更新」三者，缺一即假切换（ADR-019 §2.4/§6 步骤 4 核查项）。
3. **清零口径**：退役条件②「兼容消费点清零」= 本清单 §1~§4 各点全部变为 loop 权威署名消费或已删除；§2.2/§2.8 的 classic 只读解释器（迁移适配器形态）不计入消费点。
4. **机器化路径**：本清单格式（表+锚点行）可被后续票脚本化对账（grep 锚点行存在性 + 权威署名扫描）；机制化接入授权票模板（ADR §6 步骤 4 D-6 事项）为后续票工作。
