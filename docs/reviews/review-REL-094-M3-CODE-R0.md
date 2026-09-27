# REL-094 M-3 CODE 半面审查报告（R0）— 0.91.0 发布候选

| 项 | 值 |
|---|---|
| 审查对象 | 0.91.0 发布候选 = HEAD `98104cb53c931f330b2ea1da44cda2356099d872`（REL-093 M-8 `8d25101` 之后 4 commit：FEAT-072 `196894a` → FIX-399 `9bafdf6` → REL-094 M-1 `bc3f052` → M-1R `98104cb`） |
| 审查类型 | 发布候选 CODE 半面（0.90 先例三要点扩展为五清单——任务书 REL-094 M-3） |
| Reviewer | Code Reviewer Agent（Coordinator REL-094 M-3 派发；只读审查，唯一产出=本报告） |
| Round | R0 ｜ 审查日期：2026-09-28 ｜ 工作树：clean（git status 空） |
| **Verdict** | **APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 · P1=0 · P2=0 · P3=3（均非阻塞备注）** |

---

## 0. 方法与亲跑命令清单

全部结论基于下列亲跑命令与文件实读，无推测成分：

| # | 命令/动作 | 用途 |
|---|---|---|
| 1 | `git log 8d25101..HEAD --stat` / `--name-only` / `rev-parse HEAD` / `status --short` | 四 commit 分工与范围文件清单（33 文件） |
| 2 | `git show 196894a -- <behavior-protocol/verify_workflow/SKILL/persona/interaction-boundary/test_dsh_adapter>` | FEAT-072 全部 hunk 实读 |
| 3 | `git show 9bafdf6 -- <verify_workflow/test_verify_workflow>` | FIX-399 全部 hunk 实读 |
| 4 | `git show bc3f052 -- <verify_workflow>` | M-1 六锚手钉 diff 实读 |
| 5 | `git show 98104cb -- <architecture-baseline/m0 manifest/test_archguard_ratchet>` | M-1R 基线面 diff 实读 |
| 6 | `git diff 8d25101..HEAD -- *verify_workflow.py`（全量行读） | 行为变更面核查 |
| 7 | `python skills/software-project-governance/infra/resolve_entry.py --json` | fail-closed 前置（resolved_root_ok=true） |
| 8 | **`python .../verify_workflow.py check-governance --summary-only`**（亲跑） | 门禁现状复核 |
| 9 | Grep `.governance/evidence-log.md` / `decision-log.md` / `plan-tracker.md` | 零幻觉核验 |
| 10 | Grep `docs/reviews/review-{FEAT-072-DESIGN,FIX-399-CODE,REL-094-M1,REL-094-M1R}-R0.md` | 审查链 verdict 抽验 |
| 11 | Grep `task_priority.py` / `RECO-` / `推荐卡|三要素`（infra 全域） | 推荐文案下游消费方核查 |

注：全量 pytest 4359P/0F/1S/527 subtests 为本会话 pwsh-170 已录输出（M-2 窗口实测），本审查按任务边界仅亲跑 check-governance（清单 4），未复跑全量 pytest——引用处已标注来源。

---

## 1. 清单一：载荷纯粹性与实读 ✓

### 1.1 四 commit 分工核对（`git log 8d25101..HEAD --stat`）

| commit | 票 | 职责面 | 文件数 | 纯粹性判定 |
|---|---|---|---|---|
| `196894a` | FEAT-072（载荷） | 行为契约文本 4 注入面 + 机检锚 + 测试 | 6（+102/−6） | ✓ 无版本字面量/基线面夹带 |
| `9bafdf6` | FIX-399（载荷） | 28c 正则 + 语义 + 测试 | 2（+95/−4） | ✓ 无任何夹带 |
| `bc3f052` | REL-094 M-1（版本面） | 版本 bump + 投影再生 + CHANGELOG + 收编三份 R0 报告 | 26（+446/−32） | ✓ verify_workflow.py 仅 12 行=REQUIRED_SNIPPETS 六处 0.90.0→0.91.0 字面量，零逻辑变更 |
| `98104cb` | REL-094 M-1R（基线面） | archguard 重锚 + M0 重钉 + 冻结字面量 + M1R 报告 | 4（+167/−17） | ✓ 无载荷/版本面夹带 |

- verify_workflow.py 在范围内被三个 commit 先后触及，但三段 hunk 各归其票（注入锚 dict／28c 正则区／版本字面量），符合 DEC-266(5)「verify_workflow.py 共址、FEAT-072→FIX-399 串行」的既定批序，**非交叉夹带**。
- 宿主根 `CLAUDE.md`/`.governance/` 不在 git 跟踪（AUDIT-082 `bea6f24` 起解除跟踪）——EVD-1208 files_changed 所列 CLAUDE.md 为盘上文件写入，与 git 历史**零矛盾**（本条为核查中澄清项，非发现）。

### 1.2 关键 hunk 抽查（每票 2 处，逐行实读）

**FEAT-072**：
1. **M7.4 6c 三要素条款**（behavior-protocol.md @@ -555/-585 两块）：step 6b/6c 重写落实 DEC-266 全部裁决点——三行卡固定标签「服务目标：/解决问题：/方案要点：」+ 第三行子标签「依赖理由：」；候选依赖状态核验（不得将受阻任务表述为可直接执行）；依赖理由可追溯且不得替代三要素；三态依据缺失降级（未载明/来源不可用/依据冲突）；短选项与卡一一对应含「自主执行推荐项/暂停」、MUST NOT 默认自主执行；「执行前需澄清」不被自主执行豁免；空推荐禁虚构选项；session-snapshot 轻量投影行 SHOULD + bootstrap next_actions 边界句；L558 注记关键词清单同步（三要素/推荐卡）。**与 commit message 及 EVD-1204 声明逐项一致。**
2. **锚 dict 新条目**（verify_workflow.py INJECTION_CONTRACT_ANCHORS @@ -6750/-6757）：双注入面（persona/SKILL.md）各增「三要素」「推荐卡」+ **新增 behavior-protocol.md canonical 锚块**（三完整标签，existence-only fail-closed）——注释明确语义与既有路径同构。**与「机检锚 canonical 三标签」声明一致。**

**FIX-399**：
1. **正则 L1920 区**（verify_workflow.py @@ -1917,7 +1917,11）：`FIX_105_SNAPSHOT_RELEASE_VERSION_RE` 日期捕获组 `(?:\d{4}-\d{2}-\d{2})[^*]*` 容忍装饰尾巴 + FIX-399 注释；`_latest_published_release_fact` 单元格内取**末日期**（发布日语义）+ 语义与局限注释（时序假设、labelled 提取需格式归一——即 REVIEW-FIX-399-R0 P2-1 延期项的如实披露）。**与声明一致。**
2. **重钉 manifest rebaseline 块**（98104cb · m0/manifest.json @@ -42）：behavior-protocol.md pin `[512,556]→[522,566]`、SKILL.md pin `[223,230]→[225,232]`，双源新 content/file SHA-256；**新增 `rebaseline.last` 溯源块**（at 2026-09-28、task=REL-094 M-1R、authorization=FEAT-072（DEC-266 + REVIEW-FEAT-072-R0）与 FIX-399（REVIEW-FIX-399-R0）授权修改、**prior 双源哈希逐字节存档**）。**与「重钉 + prior 存档」声明一致；授权链可追溯。**

**测试实读**：FEAT-072 `test_dsh_adapter.py` +74 行 = `test_injection_contract_three_element_card_anchors`（正向断言双注入面 + canonical 三标签 + `baseline["issues"]==[]` + 三路移除负例）；FIX-399 `test_verify_workflow.py` +76 行 = **恰 6 个 `test_fix399_*` 用例**（纯格式/装饰单日期/多日期取末/跳过非已发布行/跳过无日期已发布行/快照事实源集成）。**「6 测试用例」「负例测试」声明属实。**

---

## 2. 清单二：CHANGELOG 声明一致性 ✓（逐项核验表）

`project/CHANGELOG.md` L5-37（0.91.0 准备态段）：

| CHANGELOG 声明 | 实况核验 | 判定 |
|---|---|---|
| FEAT-072（commit `196894a`，2026-09-27） | git：Sun Sep 27 23:43:05 2026 +0800 ✓ | 一致 |
| FIX-399（commit `9bafdf6`，2026-09-28；**HEAD 即此 commit，含两票**） | git：Mon Sep 28 00:50:28 2026 ✓；「HEAD 即此 commit」= M-0 载荷冻结时点语义——DEC-267(1) 明载冻结载荷=两 commit、冻结记录须含「合并态 HEAD 证明」，冻结时 HEAD=`9bafdf6` ✓（措辞备注见 N-2） | 一致 |
| 两票均 R0 APPROVED_WITH_NOTES/0 | 盘上报告 verdict 实读：review-FEAT-072-DESIGN-R0（AWN/0，P2×1 P3×2）、review-FIX-399-CODE-R0（AWN/0，P0=0 P1=0 P2=1 P3=3）+ REVIEW-×2 机录行同值 | 一致 |
| persona 净增 +76B、standard/strict 两档 PASS | EVD-1204（≤~150 目标内）；M-1 报告 L93-94 三档复测 | 一致 |
| 6 测试用例 | §1.2 实读恰 6 个 `test_fix399_*` | 一致 |
| 同数据 A/B 净效果 −1 误报零新增 | EVD-1205（stash 对照实测 HEAD 基线 34→33：28c 误报消解、新增问题 0） | 一致（引用证据行） |
| 已知限制① strict 5991/6000 余量 9 tok（M-1 后实测）+ 0.92 治理票已登记 | M-1 报告 L94 亲跑 `check-injection-budget --profile strict → 5991/6000 PASSED（余量 9）`；DEC-267(2) 处置(a) 逐字对应 | 一致 |
| 已知限制② evidence-log 1,737,424 bytes（≈1697KB，M-1 时点实测） | EVD-1208/DEC-265(5) 同值；今日亲跑 1,744,908 B（M-1R 后证据追加所致，CHANGELOG 已标注「M-1 时点」，不矛盾） | 一致 |
| 已知限制③ 28c 正则跨行加固延期（REVIEW-FIX-399-R0 P2-1→0.91+ 候选池） | 盘上 review-FIX-399-CODE-R0 P2=1 + plan-tracker 版本表「〔REVIEW-FIX-399-R0 P2-1 出槽〕」 | 一致 |
| 已知限制④ 版本面再生纪律（release-projection --write written=17→幂等 written=0） | EVD-1208「17→0→0→审查复跑 0，28b 消解」；bc3f052 文件面与投影面吻合 | 一致 |
| Changed：lightweight 4241/6000、strict 5991/6000 均 PASS | M-1 报告 L92/L94 亲跑三档（4241/5719/5991）+「Over budget — gated: none」 | 一致 |
| M-1 收编三份 R0 报告 + REVIEW-REL-094-R0 | bc3f052 收编 review-FEAT-072-DESIGN / review-FIX-399-CODE / review-REL-094-M1 三文件 + M-1R 收编第四份 | 一致 |
| 准备态注记（日期不预填、发布终账随 M-2+ 补记） | 发布日期字段「未发布（准备态）」✓，与 FIX-349 taggerdate 口径注记一致 | 一致 |

**与 git 历史零矛盾**（哈希、日期、commit 分工、HEAD 位置全部核对）。

---

## 3. 清单三：零幻觉核验 ✓（抽验 19 处，全部实存）

| 实体 | 实存位置 |
|---|---|
| DEC-265 | decision-log L207（0.91.0 推进与发布授权；28c 根因 verify_workflow.py:1920 入账；28s 维持 DEC-264 口径） |
| DEC-266 | decision-log L208（FEAT-072 契约设计裁决——三行卡标签/锚设计/预算目标/防编造三态/批序） |
| DEC-267 | decision-log L209（M-0 载荷冻结：196894a + 9bafdf6 + strict 9 tok 处置(a) + M-3 确认无下游推荐格式依赖义务） |
| EVD-1204 | evidence-log L2851（FEAT-072 交付闭环，6 文件清单与 diff 吻合） |
| EVD-1205 | evidence-log L2854（FIX-399 交付，stash 对照 −1 误报） |
| EVD-1207 | evidence-log L2856（FIX-399 用户影响字段行，取代 L2855 重复残留行 EVD-1206——残留已如实标注） |
| EVD-1208 | evidence-log L2863（M-1 版本面，含 strict 5991 实测与 written=17 幂等四度） |
| REVIEW-FEAT-072-R0 | evidence-log L2853 机录行 AWN/0 ↔ 盘上 DESIGN-R0 报告 |
| REVIEW-FIX-399-R0 | evidence-log L2858 机录行 AWN/0 ↔ 盘上 CODE-R0 报告 |
| REVIEW-REL-094-R0 | evidence-log L2862 机录行 AWN/0 ↔ 盘上 M1-R0 报告 |
| REVIEW-REL-094-R1 | evidence-log L2865 机录行 AWN/0 ↔ 盘上 M1R-R0 报告 |
| TRIAGE-FEAT-072 / TRIAGE-FIX-399 / TRIAGE-REL-094 | evidence-log L2849 / L2847 / L2860（change-triage CLI 机录 ×3） |
| commit `196894a` / `9bafdf6` / `bc3f052` / `98104cb` | git log 逐一确认 |

**无引用不存在实体**；REVIEW ×4 均为 review-record CLI 机器写入行（非手写），docs 路径与盘上文件一一对应。

---

## 4. 清单四：门禁事实 ✓

**亲跑 `check-governance --summary-only`（本审查时点）输出**：

```
Governance: 20 issues
[FAIL] 28s: Governance Data Size (FIX-160): .governance/evidence-log.md 1744908 bytes (1704.0 KB)
[WARN] 2: Risk Staleness (>7 days): 3 stale risk(s):
[WARN] 14: Structural Validity: 451 structural issue(s) (0 blocking):
[WARN] 15: Commit Scope Verification: 2 scope discipline issue(s):
[WARN] 24: Version Consistency (FIX-052): plan-tracker workflow version=0.90.0, expected=0.91.0
共 20 issues，--level strict 查看全部
```

- **20 issues、唯一 FAIL=28s（既有 DEC-264 结构性约束披露族）——与会话声明完全一致** ✓
- 全量 pytest 4359P/0F/1S/527 subtests：引用本会话 pwsh-170 输出（M-2 实测；本审查未复跑，见 §0 注）。
- WARN 24 为发布链进行中预期态（0.90 先例于 M-5b transition 更新 plan-tracker 版本；M-5/M-8 后自然消解）——观察项，非缺陷。
- strict 注入预算硬门：M-1 报告亲跑三档全 PASS + `Over budget — gated: none`；本时点 check-governance 无预算 FAIL 佐证门仍绿。

---

## 5. 清单五：行为变更面核查（N-2）✓

### 5.1 接口 / CLI / 文件格式

- **CLI 面**：范围 diff 中 `add_argument` / `def cmd_` / `sys.argv` 变更行 = **0**——无旗标增删改。
- **接口删除**：verify_workflow.py 范围内仅三段增量（版本字面量/正则区/锚 dict）；`_latest_published_release_fact` 同函数同返回形状（`version/date/date_text`），无函数删除。
- **文件格式破坏**：28c 正则为**召回向放宽**（纯格式旧行行为不变——EVD-1205 两消费点归因）；锚 dict 为 existence-only 新增；M0 pin 变更携 rebaseline 溯源块与 prior 存档（授权变更重钉，非静默漂移——DEC-262② sanctioned regen 策略 + 0.90 先例）。
- **版本面**：M-1 六锚手钉 + release-projection 确定性再生（幂等四度）——确定性投影，非手工漂移。

### 5.2 FEAT-072 推荐呈现形态变化 = agent 行为契约升级（预期分类）

- **RECO 行机器写入格式未变**：范围 33 文件清单**不含 task_priority.py**（RECO-{task} 行写入器与 Check 34 族判据所在）；grep 确认 Check 34/快照引用校验（verify_workflow.py L22561-22721、test_completion_recommendation.py）均校验**行 ID/marker**（`RECO-{task}` + `task-priority-analysis 机器写入`）与「下次会话优先级」节的快照 ID 引用，**无任何 schema 断言依赖旧推荐文案**。
- 「三要素/推荐卡」在 infra 代码中仅出现于注入锚 dict 与其测试（existence-only）——**无机器消费方解析推荐卡正文**。
- session-snapshot 投影行格式（`{任务标识}｜目标：…｜依据：{RECO 引用}…`）为 SHOULD、非机检项。
- **DEC-267(3) 预期分类「无 breaking——M-3 确认无下游依赖原推荐格式接口」：本节即该确认义务的履行** ✓

---

## 6. 五维度审查结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✓ 通过 | 四 commit hunk 逐行实读与声明一致；28c 末日期语义附时序假设披露；锚 fail-closed 语义同构既有路径；测试真实（6+1 用例，负例到位） |
| 安全性 | ✓ 通过 | 无硬编码密钥/注入面；版本字面量与数据面变更；fail-closed 门（预算硬门/锚存在性）全部保持；M0 重钉携授权链防未授权漂移 |
| 可维护性 | ✓ 通过 | 关键变更均带出处注释（FIX-399 语义+局限、锚块归属、rebaseline 溯源、archguard 增量归因）；冻结字面量与注释同步更新 |
| 性能 | ✓ 通过 | 正则 findall 于 plan 内容，量级可忽略；无新增热循环；R4 census 1318 不变 |
| 测试覆盖 | ✓ 通过 | FEAT-072 正向+三路移除负例；FIX-399 六用例覆盖纯格式/装饰/多日期/跳过/集成；archguard 冻结字面量测试同步（模块 38 tests，EVD-1209）；全量 4359P/0F/1S（pwsh-170 引用） |

## 7. AI 代码专项 5 项检查

| 项 | 结论 |
|---|---|
| mock 残留 | 无——测试走临时目录/fixture 真实读写 |
| 硬编码返回值 | 无 |
| 幻觉 API 调用 | 无——引用的 `re/_parse_iso_date/REGEN 流程`均实存且被调用 |
| 未实现 TODO | 无——注释均为「局限披露」（P2-1 延期项），非未完成 TODO |
| 过度实现 | 无——FEAT-072 严格落在 DEC-266 裁决范围；FIX-399 仅正则+语义+测试；版本/基线面为确定性再生 |

## 8. 发现列表

| 编号 | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| N-1 | P3（承继 REVIEW-REL-094-R0） | project/CHANGELOG.md L18 | DEC-267(2) 措辞修正第二从句「计量或生成内容变化也可能越界」未逐字落入 strict 预算披露行（现保留「当前口径下」限定语，语义主干完整） | M-3+/发布态改写该段时补入该从句 |
| N-2 | P3（本审新提，措辞） | project/CHANGELOG.md L14 | 「HEAD 即此 commit，含两票」为 M-0 冻结时点语义（与 DEC-267 及 git 零矛盾），但发布后读者可能误读为发布时 HEAD | 发布终账（M-2+ 补记 Commit 区间时）改写为明确时点表述，如「M-0 冻结时 HEAD=9bafdf6」 |
| N-3 | P3（观察，非缺陷） | check-governance WARN 24 | plan-tracker 工作流版本 0.90.0 vs expected 0.91.0 为发布链进行中预期态（0.90 先例于 M-5b transition 更新） | 无需动作；M-5/M-8 后自然消解 |

**P0=0 · P1=0 · P2=0**。无未解决 BLOCKING finding。

## 9. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 = 0 | ✓ |
| 5 维度全覆盖 = 100% | ✓（§6 逐维有结论） |
| 每条发现标注级别 = 100% | ✓（§8 全部 P0~P3 标注） |
| 设计一致性（DEC-265/266/267 比对） | ✓（§1.2/§2 逐裁决点核对） |
| AI 代码专项 5 项 | ✓（§7 逐项有结论） |

## 10. 结论

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0**

0.91.0 发布候选 `98104cb` 的 CODE 半面核验通过：载荷两票 diff 与其 REVIEW 声明及 EVD/DEC 记录逐项吻合；版本面/基线面为确定性再生与授权重钉且溯源完备；CHANGELOG 0.91.0 段逐声明与实况一致、与 git 历史零矛盾；零幻觉抽验 19 处全部实存；check-governance 亲跑 20 issues 现状一致（唯一 FAIL=28s 既有）；行为变更面无接口删除/CLI 变更/格式破坏，推荐卡升级确认无下游机器消费方依赖旧文案格式。三条 P3 备注均非阻塞，其中 N-1/N-2 建议在发布终账改写时一并处理。

（本报告为 CODE 半面；RELEASE 半面由对应 Reviewer 另行出具。）
