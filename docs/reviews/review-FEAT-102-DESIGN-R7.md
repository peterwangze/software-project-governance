# FEAT-102 — DESIGN R7 增量复审（R6 设计面修订）

- 日期：2026-10-21（Asia/Shanghai）；独立 Design Reviewer（继续由同一非 Producer Reviewer 执行）。
- 规范：`design-reviewer`、`design-review`、`tech-review`；真实环境红线保持。
- **对象绑定**：被审设计 = `docs/architecture/dsh-adapter-version-decoupling.md` 当前工作树字节，SHA-256 `488140EC358B04F123E20C192D6F271A5742886BDC5E26D79609C5C50FC1CD70`（788 行 / 116,401 B）；delta base = `docs/reviews/review-FEAT-102-DESIGN-R6.md`，SHA-256 `CCA7DF96CFE1E9FA3384BAD489766A508DC869C2B26D8454AEE00281C884A69C`（286 行；其机器记录为 `REVIEW-FEAT-102-R7`，因 `REVIEW-FEAT-102-R6` 已被 CODE R0 使用；本报告是其 **DESIGN R7** 增量复审）。R6 审阅时的设计字节为 `23E3B02D...`（738 行 / 99,818 B）。
- **排除面**：代码/测试/契约/README/投影文件当前处于 CODE 链返工中（未提交、未审查，工作树在变）。本报告**只判设计文本与事实一致性**；不把在途实现当已修复，也不因其漂移改判设计结论。为核对 persona 投影与 §3.1 状态陈述，只读查看了 `version-projections.json` 工作树 diff 与 CODE R0 报告头，这属于“验证设计陈述是否与工作树事实相符”，不是对实现正确性的审查。
- **行为裁定依据**：`DEC-366`（`decision-log.md:233`）：① R3-B1 接受为已知边界并限定支持声明；② legacy 恢复 R0 默认 warn-only、不自动渲染；③ §4.1 raw/accepted+BASE_BROKEN 降级为 declaration-based + known boundary；基线锚点切 0.2.1-rc.2。另核对 `DEC-363`（`decision-log.md:230`，FEAT-103 授权）、`EVD-2120`（`evidence-log.md:3023`，返工第一轮 585/0/0）、`EVD-2119`（`evidence-log.md:3020`，CLI fallback=1 改判 NOT_RUN）。
- **方法**：先复算设计/R6 报告 hash；用 `git diff` 得到 R6→R7 的 92 插入/42 删除，再用归一化 section 比对确认 §14/§15 与 R3/G/S-A3 历史字节未变；读取 DEC-366/EVD-2120/EVD-2119/DEC-363、CODE R0 报告头、persona 投影工作树 diff；本轮**不运行宿主、不跑测试**（实现面返工中，测试面以 CODE R1 稳定字节为准）。命令见 §5.3。

## 1. 结构化结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
object=design_488140EC + R6_report_CCA7DF96
design_diff=+92/-42 (only sections 3/4/6/8/12/16 + new §17)
history_preserved=YES (§14/§15 text hashes identical to R6)
scope_creep=NONE_FOUND
forbidden_overclaims=NONE_FOUND (no "取消已解决"/"FEAT-102 完成"/"全链 PASS")
p0=0
p1=0
p2=2 (N-R7-1 test numbers, N-R7-2 §3.1 in-flight status)
p3=3 (N-R7-3 §4.1 residual, N-R7-4 §4.3 residual, N-R7-5 §16.4.1 residual)
host_run=NOT_RUN
tests=NOT_RUN (design-only; authoritative rework result EVD-2120 = 585/0/0)
user_readjudication_required=NONE (DEC-366 covers the three behavior boundaries)
```

**结论：`APPROVED_WITH_NOTES`，`unresolved_blockers=0`。** 设计方向与 DEC-366 一致，D-R6-1～7 的主体已真实落文本，历史失败轨迹与 §15 提案未被“修好”。剩余问题均为**文本/状态准确性与历史合同清理**，不是新的设计方向 blocker；其中 N-R7-1、N-R7-2 是发布/机录前**必须修正**的文本项（不影响 AWN 作为设计方向通过的终态）。

## 2. D-R6-1～7 逐条判定

| ID | R6 finding | R7 事实（设计文本） | 判定 |
|---|---|---|---|
| D-R6-1 | P1-1 carried R3-B1 | 文首状态行、§12 ADR、§16.2（L746）、§16.4.3 均明确“R3-B1 仍未闭合、native 不提供取消、不得写‘取消已解决’、FEAT-102 不标完成”；支持声明限定为「native 核心切片 + 已知 pending-record 窗口」；窗口接受引 DEC-366①，闭环交 FEAT-103（DEC-363） | **真实落文本**；与 DEC-366① 一致；无过度声明 |
| D-R6-2 | P1-2 legacy 自动写入 | §6 表/段（L207-215）、§16.1 第 1 条（L734-739）、§16.2 诊断面、§16.3 反例、§16.4.5 均改为 absent/disabled/unreadable/ambiguous 四态；无 registry 只 warn、不自动渲染、不写目录；写目录仅显式 `launch.py --install` | **真实落文本**；与 DEC-366② 一致；实现面待 CODE R1（排除） |
| D-R6-3 | P2-1 raw/accepted + BASE_BROKEN | §4.1 增加 2026-10-21 修订块（L85-91），明确 declaration-based、不读 `fiber.config`、不做 `registry.resolve` broken 审计，accepted/raw 与 base-broken 为已知边界；§16.2 新 bullet（L747）；§16.4.7 列 NOT_RUN | **真实落文本**；与 DEC-366③ 一致；残留历史合同清理见 N-R7-3 |
| D-R6-4 | P2-3 模块/接口合同 | §3.1（L49-64）更新为六个 `lib/dsh-native/*` 模块并给出 disposition；§4.3（L122-126）声明 `RuntimeOutcome` 为历史合同并列出实际 code 集合 | **落文本，但有两处准确性问题**：§3.1 状态列把在途四态/no-auto-legacy 标“已实现”（N-R7-2）；§4.3 旧“错误码至少”段未标注且实际 code 集合不完整（N-R7-4） |
| D-R6-5 | P2-2 persona 双副本/投影 | §8 S-B（L247-249）采用“两份副本 + 测试同步 + 版本投影必达”；明确工作树已有未提交、未审查的 `dsh-persona-body-version` → `persona.md.template` 条目，**不算已落地**、以 CODE R1 为准 | **真实落文本**；与实际工作树相符（该条目确在未提交 diff 中）；无“已落地”前瞻断言 |
| D-R6-6 | P2-4/P2-5 测试状态/版本锚点/状态行/ADR | 版本锚点已改 0.2.1-rc.2（文首/§6 首行）；状态行/§12 ADR 更新到 R6/R7；§16.3 改为“HEAD `98d99c2` 570 passed；返工工作树 585 → 580/5 非一致快照、CODE R1 为准” | **部分落文本**：锚点/状态/ADR 正确；§16.3 测试数字**不充分诚实**（N-R7-1：省略权威 585/0，保留 580/5 并称 5 项失败需关闭）；§16.4.1 开头仍留“1 行 CLI 回退”（N-R7-5） |
| D-R6-7 | P2-6 fallback 四态 | §16.1 第 1 条写清 absent/disabled/unreadable/ambiguous 四态及 code；后三态与 absent 一样 warn-only、不落 legacy | **真实落文本**；与 DEC-366② 一致；实现四态在途（CODE R1） |

**范围纪律核对**：R6→R7 section 比对（归一化）显示 §1/2/5/7/9/10/11/13/14/15/（§13、§14、§15 全文）**SAME**；§14 text SHA `16738FDC...`、§15 text SHA `25EC6BFE...` 两侧完全相同。R3/G/S-A3 失败轨迹、§15 U 提案原文未被“修好”；改动只落在 §3/§4/§6/§8/§12/§16，并新增 §17 修订记录。未发现超范围改写。

**越权声明核对**：全文检索/逐句检查未发现“取消已解决”“FEAT-102 完成”“全链 PASS”等断言；出现的是“不得写‘取消已解决’”“FEAT-102 不因此标完成”“不是全链通过”等限定语。支持声明与 DEC-366① 一致。

## 3. 新增/残留 findings

### N-R7-1（P2，必须修正）§16.3/§17 的测试数字省略权威 585/0，并把非一致快照 580/5 写成需关闭的失败

**事实**：`EVD-2120`（`evidence-log.md:3023`）的权威返工第一轮为 **585 passed / 0 failed / 0 skipped，119 subtests，670.36s，UTC 13:00:27.929Z→13:11:38.991Z，exit 0**。设计 §16.3（L755）写“同日含 CODE R0 返工的工作树收集 585 项 → **580 passed / 5 failed**（adapter ×2、boundary ×3）……5 项失败属返工面，须由 CODE R1 关闭；本设计不声称‘585 全绿’”；§17 D-R6-6 行（L783）重复同一 580/5。

**判定**：这**不是充分诚实**。虽然文本已限定“非一致性快照、以 CODE R1 为准”，但它：(a) 省略了权威 585/0/0；(b) 把 580/5 写成返工面结果并要求 CODE R1 关闭 5 项失败，而权威结果明确 0 failed；(c) “不声称 585 全绿”反而否定了已发生的 585/0/0 测试事实。5 项失败来自返工进行中 conftest 未收口的非一致快照，不应被保留为“需关闭项”。

**最小修改**（§16.3 L755 + §17 D-R6-6 L783 两处同步）：
> 返工第一轮权威实测（EVD-2120）：**585 passed / 0 failed / 0 skipped（119 subtests，670.36s，UTC 13:00:27.929Z→13:11:38.991Z，exit 0）**。另一次返工进行中的读取得到 580/5，是 conftest 未收口的**非一致快照，不作为结果**；最终以 CODE R1 在稳定字节上的复核为准。测试级 585/0 不等于 T01-T20 全链/运行时全矩阵 PASS。

删除“5 项失败属返工面，须由 CODE R1 关闭”和“本设计不声称 585 全绿”这两句，或按上式替换。该修改是**文本准确性**项，不改变设计方向；但应在发布/机录/对外声明前完成。

### N-R7-2（P2，必须修正）§3.1 状态表把在途 CODE R0 返工标成“已实现”，与 §16.4.5/6 自述冲突

**事实**：§3.1（L53、L55、L59）把 `lib/index.js` 的“不再自动写 legacy”、`source.js` 的四态、`bridge.js` 的四态编排标为“已实现”。但稳定 HEAD `98d99c2` 的代码没有四态/no-auto-legacy（R6 审查字节）；工作树中的四态与 legacy 移除是 **CODE R0 返工，未提交、未审查**；设计 §16.4.5（L764）自己说 legacy 自动写入移除“工作树已有未提交返工，未经审查，不算已落地；由 CODE R1 关闭”，§16.4.6 对 persona 投影同样声明。

**判定**：这是“把在途实现当已修复”的状态过报，且与同一文档的 §16.4.5/6 矛盾。它不改变设计行为（§16.1 的四态/无自动 legacy 合同本身正确），但会让读者/CODE R1 误以为 I-R6-1/I-R6-2 已关闭。

**最小修改**：把 §3.1 表中 `lib/index.js`、`source.js`、`bridge.js` 三行的状态从“已实现”改为“设计已定；实现待 CODE R1（legacy no-autowriter/四态返工）”；或在该表下加一行明确“状态仅指提交面；§16.1 四态与 DEC-366② 的实现在途，以 CODE R1 为准”。表题“按实际落地更新”建议改为“按设计合同与提交面状态”。

### N-R7-3（P3，建议修正）§4.1 历史合同仍保留“不能删去 BASE_BROKEN”的旧硬门句

§4.1 第 5 条（L103）开头标注“2026-10-21 已降级为 known boundary……BASE_BROKEN 拒收不再是 native 路径当前要求”，但同段末尾仍保留“无法证明则候选失败，不能删去 BASE_BROKEN 拒收要求”。两句直接矛盾，即使 section 头部有“历史合同”标签，也会误导读者。建议把第 2/3/5 条整体放进“历史原文（不适用）”引用块，或在该句后加“〔历史要求；DEC-366③ 已取代〕”并删除“不能删去”的当前语气。

### N-R7-4（P3，建议修正）§4.3 旧“错误码至少”段未标注，且“实际 code 集合”不完整

§4.3 的 disposition 声明本节为历史合同，但 L128-130 仍保留旧 `RuntimeOutcome` 形状与“错误码至少：HOST_PROTOCOL_UNKNOWN、……REGISTRATION_BROKEN、INIT_TIMEOUT、DISPOSED_DURING_START”的当前语气；这些码未实现。另一方面，L125 的“实际 code 集合”并未穷举当前工作树代码：至少缺 `BASE_DISABLED`/`BASE_DISABLED_UNEVALUABLE`（`source.js`）、`PERSONA_ROW_MISSING`/`PERSONA_ROW_DUPLICATE`/`SKILL_ROW_MISSING`/`SKILL_ROW_DUPLICATE`（`overlay.js`），以及 `lib/index.js` 的 `NATIVE_PATH_UNAVAILABLE`。建议把旧段标为“历史错误码表（不要求实现）”，并把 L125 改为“主要 code（非穷举；最终以 CODE R1 稳定字节为准）”或补齐。该条不影响 AWN，但属于残留的接口合同不一致。

### N-R7-5（P3，建议修正）§16.4.1 开头仍写“1 行经 CLI 回退”，与同段更正冲突

§16.4.1（L760）开头仍说“真实环境由 FAIL 转 PASS（19/23 行校验、**1 行经 CLI 回退**、4 行 NO_SCHEMA）”，同段后文已明确 `1 行经 CLI 回退` 在隔离 `dsh021-baseline` 实测为 0，仅合成平面可复现，CODE R0 已改判 **NOT_RUN**（EVD-2119）。建议把开头改为“19/23、4 行 NO_SCHEMA；CLI 回退 0（合成平面 1，NOT_RUN）”，保留后文澄清。该条为事实一致性 P3。

## 4. 独立事实与对象绑定核对

### 4.1 设计增量与历史保留

- 当前设计 `488140EC...`（788 行 / 116,401 B）；R6 报告 `CCA7DF96...`（286 行）；R6 设计输入 `23E3B02D...`（738 行 / 99,818 B）。
- R6→R7 `git diff --stat`：**+92/−42**，134 行变更；section 归一化比对：§1/2/5/7/9/10/11/13/14/15 SAME；§3/4/6/8/12/16 CHANGED；§17 新增。§14 text SHA `16738FDC...`、§15 text SHA `25EC6BFE...` 与 R6 完全相同 → R3/G/S-A3 失败轨迹、§15 U 提案原文保留。
- §17 是新增修订记录，逐条映射 D-R6-1～7；其“不修改历史事实/不把 NOT_RUN 写成 PASS/不删失败轨迹”的自我纪律与 section 比对一致。

### 4.2 DEC-366 与 EVD 事实

- `DEC-366`（`decision-log.md:233`）：用户三项裁定 ①②③ + 0.2.1-rc.2 锚点；明确“均来自用户显式选择，不由 Coordinator 代决”。设计文首/§6/§16.2/§16.4.3/§12 的引用与之一致。
- `EVD-2120`（`evidence-log.md:3023`）：返工第一轮 **585/0/0、119 subtests、670.36s、13:00:27.929Z→13:11:38.991Z、exit 0**。N-R7-1 据此判定 §16.3 不充分。
- `EVD-2119`（`evidence-log.md:3020`）：`fallback=1` 在 EVD-2112 隔离基线实测 0，仅合成平面可复现，改判 **NOT_RUN**；§16.4.1 的更正与之一致，但开头残留 N-R7-5。
- `DEC-363`（`decision-log.md:230`）：用户授权 FEAT-103 隔离补丁验证；设计“真正闭环交由 FEAT-103（DEC-363）”有据，不构成“取消已解决”的断言。

### 4.3 persona 投影

工作树 `git diff -- skills/software-project-governance/core/version-projections.json` 确实出现未提交条目：
```json
{ "id": "dsh-persona-body-version", "kind": "transformed_text",
  "target": "agent-presets/governance/persona.md.template",
  "pattern": "治理工作流（v[0-9]+\\.[0-9]+\\.[0-9]+）",
  "replacement": "治理工作流（v{version}）", "count": 1 }
```
设计 §8 S-B 所述“工作树已出现未提交、未审查、不算已落地、以 CODE R1 为准”与事实相符；没有把该条目写成已落地或已审。该条 **PASS**。注意：这只验证“设计陈述与工作树事实一致”，未验证投影条目的实现正确性（归 CODE R1）。

### 4.4 排除面 / 未运行

- 代码/测试/契约/README/投影均处于 CODE 链返工中；本报告未运行宿主、未跑测试，不能把 EVD-2120 的 585/0/0 当作 R7 自身复跑，也不能把工作树四态/legacy 移除当作已审实现。
- 设计文档本身也是工作树未提交修订；被审字节为写报告时的 `488140EC`。R7 报告写入前未再改设计；若设计在报告落盘后被继续修改，应重新绑定 hash，本报告只对 `488140EC` 负责。
- 未运行：`check-dsh-preset-compat`、任何 DSH boot、任何测试套件、CODE R1 实现面；均 **NOT_RUN**，不得读成 PASS。

## 5. 命令审计

完整机器可读审计：`.codex-sandbox/FEAT-102/design-r7/command-audit.json`，SHA-256 `935AFBCE3D92E44E7929D7721DA4B6FA7EA0D7A6FA97F037A4989E6BBB4B8EAD`。三条命令均为只读/scratch；无宿主运行、无 DSH_HOME 重定向需求、无真实 profile 读写。

| ID | 命令（摘要） | started UTC | ended UTC | exit | 影响路径 / 备注 |
|---|---|---|---|---|---|
| R7-STATIC | 设计/R6 报告/投影/契约 hash、`git status`、设计 diffstat | 2026-10-21T00:09:01.7448592Z | 2026-10-21T00:09:02.1333367Z | 0 | 只读；设计 `488140EC`、R6 `CCA7DF96`、diff `+92/−42`；日志 `r7-static-audit.log` / `DF4A55AD...` |
| R7-SECTIONS | 归一化 section 比对 R6 design (HEAD) vs R7 design | 2026-10-21T00:12:06.4606672Z | 2026-10-21T00:12:06.6455892Z | 0 | §14/§15 SAME；`r7-section-compare.log` / `63FF081D...` |
| R7-EVIDENCE | 读 DEC-366/EVD-2120/EVD-2119/DEC-363/CODE R0 头/投影 diff | 2026-10-21T00:12:09.9187051Z | 2026-10-21T00:12:10.3204471Z | 0 | 只读；`r7-evidence-read.log` / `3A53D252...` |

补充：`git diff -- docs/...` 的设计增量文件另存为 `.codex-sandbox/FEAT-102/design-r7/design-r6-to-r7.diff`，SHA-256 `6E1A7E1C...`；该命令为只读、未单独打印 UTC，section 比对日志可复现其结论。没有运行测试/宿主，因此不存在测试/宿主的 exit code 需要审计。

## 6. 结论、备注与路由

- **结论：`APPROVED_WITH_NOTES`，`unresolved_blockers=0`。** D-R6-1、D-R6-2、D-R6-5、D-R6-7 真实落文本且与 DEC-366 对应；D-R6-3 落文本（有历史合同残留 N-R7-3）；D-R6-4 落文本（有状态过报/残留 N-R7-2/N-R7-4）；D-R6-6 部分落文本（N-R7-1/N-R7-5）。
- **发布前必须修正（文本，不是方向 blocker）**：**N-R7-1**（§16.3/§17 测试数字，补 585/0/0、把 580/5 限定为非一致快照、删除“5 项失败需关闭”）；**N-R7-2**（§3.1 状态列，把在途四态/no-auto-legacy 标为“设计已定/CODE R1”，不要标“已实现”）。
- **建议同步修正（P3）**：N-R7-3（§4.1 旧“不能删去 BASE_BROKEN”）、N-R7-4（§4.3 旧错误码段与不完整实际 code 集）、N-R7-5（§16.4.1 开头“1 行 CLI 回退”）。
- **无需用户再裁定**：DEC-366①`②`③ 已覆盖行为边界；N-R7-1/N-R7-2 是设计文本准确性，不是新的行为/风险接受。R3-B1 仍为已知边界，支持声明仍限定为「native 核心切片 + 已知 pending-record 窗口」；FEAT-102 不标完成。
- **实现面**：CODE R1 按设计合同继续处理 I-R6-1～I-R6-7；不要把本报告 AWN 当作在途代码已审、测试已全绿或发布授权。

## 附录：输入/证据 hash

| 文件 | SHA-256 |
|---|---|
| 设计（R7 被审） | `488140EC358B04F123E20C192D6F271A5742886BDC5E26D79609C5C50FC1CD70` |
| R6 报告（delta base） | `CCA7DF96CFE1E9FA3384BAD489766A508DC869C2B26D8454AEE00281C884A69C` |
| 设计 R6→R7 diff（scratch） | `6E1A7E1C0C7294982F9623CBE7A71EFA9922CD90A36CAC086F6B2EE9B861126D` |
| command-audit.json | `935AFBCE3D92E44E7929D7721DA4B6FA7EA0D7A6FA97F037A4989E6BBB4B8EAD` |
| r7-static-audit.log | `DF4A55AD7F6DB8B2909591E6C4FC1FC1B73B515488C9BFB94F2C4578E337310C` |
| r7-section-compare.log | `63FF081DBA84BE92C57B44354728F01CF30772B8EAC2E7F92EE07149BD4A7751` |
| r7-evidence-read.log | `3A53D25263ACD501782EC55428B6DD6DBD50483073F8D31C166F7B8426F3FFAF` |
