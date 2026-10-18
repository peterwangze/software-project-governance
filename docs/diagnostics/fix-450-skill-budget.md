# FIX-450 — SKILL 与关键行为契约预算收敛

日期：2026-10-17（Asia/Shanghai）。状态：Producer 交付，未提交，独立审查由 Coordinator 派发。本票只编辑入口 SKILL、新细则与本报告；没有修改测试、预算计价/阈值、执法代码、manifest、用户配置或治理记录，也未启动 DSH。

## 复现与改动

原入口全文18,574 tokens，超过既有16,000线；关键契约从「关键行为契约」至下一「产品代码 vs 治理记录边界」计9,648 UTF-8 bytes，超过既有4,096线。intro写十条，实际编号1–11。FEAT-097长细则、FEAT-095执法详表及全文健康摘要积累到入口，触发既有预算和计数守护。本票调整承接位置，保持安全语义和门槛。

入口仍保留十一条逐项触发器及安全边界；完整十一条、执法详表、bootstrap健康摘要和非resident自动化分级说明逐字迁入 `skills/software-project-governance/references/behavior-contract-details.md`。入口保留原标题；触发时 MUST 在执行前读对应 C1–C11 / §enforcement / §bootstrap-health / §automation-levels，细则不可读不得执行。条5/6 frozen文字未改。按需读取不能视为可选或缓存豁免。

交叉引用器把 Markdown URL的 `#fragment` 当作文件名，初次检查报三个悬空引用（validation-5，exit 1）；改为文件链接+明确节名，细则保留对应命名锚，未改校验器。复验validation-9/13均exit 0。

## 实测预算

| 面 | Before | After | 既有线 | 结果 |
|---|---:|---:|---:|---|
| SKILL 全文 calibrated tokens | 18,574 | 15,440 | 16,000 | PASS，余量 560 |
| 关键契约 UTF-8 bytes | 9,648 | 3,719 | 4,096 | PASS |
| resident lightweight tokens | 4,441 | 4,441 | 6,200 | PASS（未改 resident） |
| resident standard tokens | 5,925 | 5,925 | 6,200 | PASS（未改 resident） |
| resident strict tokens | 6,197 | 6,197 | 6,200 | PASS（未改 resident） |

采用既有 `checks.injection_budget.check_injection_budget()` / CLI计价，没有以host字符密度替代calibrated计量。三profile均issues=[]、verdict=PASS。strict resident原有余量仅3 tokens，本票未扩大或消耗此面。

## 原文保全与触发映射

以下14个承接单元由修改前快照逐段提取，与新细则作精确子串比较：14/14原文匹配，入口对应标题/编号保留。SHA为换行规范化UTF-8原文SHA-256。完整值与预算测量在 `.governance/sandboxes/fix450/measurement.json`。细则原文是实际规范，映射摘要不替代规则。

| 细则节 | 入口触发/安全边界 | 原文SHA前16位 | 原文匹配 |
|---|---|---|---|
| C1 | 审查结论/轮次→复审、升级、唯一通过终态、delta注入 | `d390aafd8d5ad4af` | YES |
| C2 | 完成→依赖分析/证据/三要素推荐卡/空原因，禁止自行续作 | `4c26a67473742a00` | YES |
| C3 | 下一步选项→逐项依赖理由 | `46211268849ae264` | YES |
| C4 | 真实环境→三选一防护、逐条上报和机录、限定验收措辞 | `51868daf67e06562` | YES |
| C5 | 推荐排序→需求源、同级用户点名优先 | `1857bde7727cda1f` | YES |
| C6 | 问题触发→当场闭环及成本 | `0d5776a4cc2c4a62` | YES |
| C7 | 独立任务/等待→批量派发、禁止轮询 | `8f67cbf912b9e3d1` | YES |
| C8 | 全量→首检/推进/异常三触发 | `d7de906e364b5386` | YES |
| C9 | 热数据→单源路径 | `e58b2add35731cf9` | YES |
| C10 | goal每轮→四维危险区/收口状态机/授权恢复/checkpoint/off | `20c7623b0bc1a398` | YES |
| C11 | 六边界→执法判定、禁止绕行 | `bb9655d5070cfe02` | YES |
| bootstrap-health | 会话→快路径/首次交互/四态披露/full深检/fail-safe/legacy | `830adf014d282405` | YES |
| enforcement | 六边界→硬阻断/限流/提示、WIP/scoped、机器记录/降级 | `172e77ebe71372d2` | YES |
| automation-levels | 对外自动看护→A/B/C准确宣示、write-guard时点边界 | `65ea37981604daa9` | YES |

FEAT-098四行（体验脊柱/成本基线两段及空行）与before快照按原始字节比较完全一致；SHA-256 `315383712a7dcc55a9a5ae426555f4bc41549e82a3255be3fedba0d423e9b058`。本票未移动、删除或改写；Coordinator提交时继续与FEAT-098分开处理。

新细则匹配既有manifest产品目录条目 `skills/software-project-governance/references/`（type=dir）与 `skills/software-project-governance/references/**/*.md` glob，实测 `Path.glob` 包含新文件；最终manifest检查exit 0。无需调整manifest或预算面。

## 验证

命令均在仓库运行，Python为 `C:/Python314/python.exe`，无用户HOME操作。日志仅在仓库隔离工件 `.governance/sandboxes/fix450/validation-N.log`。

| 命令（仓库根） | 结果 | 日志 |
|---|---|---|
| `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_injection_budget_gate.py -v` | 11/11 PASS，exit 0 | 首轮工具stdout |
| `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_adapter.py -k injection_contract -v` | 3/3 PASS，exit 0 | validation-1 |
| `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_review_machine_provenance.py -v` | 41/41 PASS，exit 0 | validation-2 |
| `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_behavior_profile.py -v` | 49/49 PASS，exit 0 | validation-7 |
| `python -X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_verify_workflow.py -k enforcement_skill_protocol -v` | 1/1 PASS，exit 0 | validation-8 |
| `python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-injection-budget --format json` | exit 0 | validation-10 |
| `python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-injection-contract` | exit 0 | validation-11 |
| `python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues` | exit 0 | validation-12 |
| `python -X utf8 skills/software-project-governance/infra/verify_workflow.py check-cross-references` | exit 0 | validation-13 |
| `python -X utf8 skills/software-project-governance/infra/verify_workflow.py` | exit 0 | validation-14 |

测试合计105个通过，覆盖条数/冻结文本/4KB预算、三profile hard resident与独立skill线、防降级、full深检义务与执法锚。最后额外迁移自动化分级说明后，仅复跑上表末五项必要CLI与三profile实测，未重复已通过完整模块。

## 硬门槛与范围

- 默认verify、交叉引用、manifest：PASS。
- 向后兼容：CLI/数据/执法行为未修改；原安全条文逐字保留，入口触发仍强制读取。
- 无虚假API/mock/硬编码结果：文档迁移，无新增API实现。
- 全项目单测、DSH运行时安装：未运行。本报告不声称整个版本或远程CI通过；集成镜像同步与独立审查由Coordinator处理。

Proposed evidence-log：FIX-450将全文18574→15440/16000、契约9648→3719/4096B，保持resident及既有安全语义；14单元原文迁移验证、FEAT-098四行字节保全、105相关测试与五项最终CLI通过。附件为本报告、新细则、隔离测量与日志。

Proposed decision/risk entry：无规则姿态或风险接受变更。未直接修改 `.governance/` 治理记录；仅sandbox运行工件，最终记账由Coordinator负责。未提交。
