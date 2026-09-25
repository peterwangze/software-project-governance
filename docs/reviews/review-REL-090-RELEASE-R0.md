# Review — REL-090 RELEASE R0（0.89.0 版本规划·发布半面）

> **审查对象**: `docs/planning/version-plan-0.89.0.md`（0.89.0 版本规划——M-0 规划面产出，草案 v1 2026-09-25）
> **轮次**: R0 · **半面**: RELEASE（M-0 双审之二——发布半面）
> **审查日期**: 2026-09-25 · **审查者**: Release Reviewer Agent（software-project-governance-release-reviewer）
> **审查依据**: `skills/release-review/SKILL.md` + 角色定义 `agents/release-reviewer.md`
> **审查性质**: **规划期审查（M-0），非发布就绪审查**——发布就绪证据（tag/ledger/四件套终稿/门禁实测）属 M-1R~M-8 产物，不得以「尚未存在」判 FAIL；审查重点是规划中是否为其留有明确席位且口径与事实源一致。
> **写入边界**: 本报告为唯一写入文件；审查对象与全部事实源只读；`.governance/` 治理记录零写入。

---

## 1. 事实源核验清单（本报告证据基线）

| # | 事实源 | 核验点 | 结果 |
|---|--------|--------|------|
| F1 | `docs/planning/version-plan-0.89.0.md` L1-128 | 审查对象全文（§1~§9） | 已通读 |
| F2 | `docs/planning/version-plan-0.88.0.md` L1-115 | 先例形态（§3/§3b/§5） | 已通读 |
| F3 | `docs/release/release-plan-0.88.0.md` | M 链全表先例（L86-101）、门禁摘要（L112-124） | 已核 |
| F4 | `docs/release/release-checklist-0.88.0.md` L1-70 | 回填位纪律先例（「M-2 数值不预填」） | 已核 |
| F5 | `docs/release/rollback-plan-0.88.0.md` | §7 B-12/B-13 回退显式化专节（F-11）、§8 两路径、§9 候选池 | 已核 |
| F6 | `docs/release/feature-flags-0.88.0.md` | §2 B-12 出厂全 WARN、§3 B-13 MD_ACTIVE、§7 未发布面 | 已核 |
| F7 | `.governance/decision-log.md` L136/180/181/183/184/185/186 | DEC-197/238/239/241/242/243/244 | 已核 |
| F8 | `.governance/plan-tracker.md` L82-88 | 热表七行（REL-090+六票） | 已核 |
| F9 | `.governance/plan-tracker.md` L306/307 | roadmap 0.88.0 行 / 0.89.0 行 | 已核（0.88.0 行发现 P2-2，见 §4） |
| F10 | `.governance/risk-log.md` L1-L6 | RISK-036/039/046/047/050/059 现值 | 已核（RISK-036 行全文受单行格式截断限制，经双源交叉印证——见 P3-1） |
| F11 | `.governance/session-snapshot.md` L7/14/17/21/29/33/44 | 0.88 收口态+披露面维持席 | 已核 |
| F12 | `.governance/change-triage/{FIX-390,391,392,393,394,FEAT-065,REL-090}.json` | 载荷票 triage 机录（priority/deps/files） | 七件全部存在，逐票比对一致 |
| F13 | `project/CHANGELOG.md` L5-48 | 0.88.0 段行为变更交付事实 | 已核 |
| F14 | `skills/software-project-governance/core/releases/0.88.0.json` | 0.88.0 manifest 存在性（发布链闭环旁证） | 存在 |

---

## 2. 五维度逐项结论（发布审查维度）

### D1. 发布检查清单映射 —— **PASS（规划期）**

- **席位完整性**：§3b M-1R 行定义四件套交付件（release-plan-0.89.0 / release-checklist-0.89.0 回填位 / rollback-plan-0.89.0 / feature-flags-0.89.0）+ 出口判据「四件齐 + cross-refs PASS + 回退显式化」——与 REL-088 先例（F3/F4/F5/F6）同构；§9 验证方式明确「组合清单随 M-1R 四件套转入 release-checklist 重点席」——组合测试席的清单映射闭合。
- **回填位纪律**：M-2 出口判据「全条目实测留 EVD」+ M-5「checklist 全席回填」与 0.88 checklist「M-2 数值不预填」纪律（F4 L3/L16）同型；M-1R 草案期不预填实测值的义务通过 M-5 出口判据「TO_BE_DEFINED=0」承载。
- **门禁→checklist 映射**：§4 七条门禁逐条可判定（见 §3-3 核验），每条在 M-2 出口判据「§4 门禁全条目 + §9 组合测试集」中有唯一席位。

### D2. 回滚方案 —— **PASS（规划期）**

- **无数据级回退触发面判定成立**：§7「本版无行为变更激活（§8）→ 无数据级回退触发面」——前提 §8「=无激活」经 0.88 交付事实三方印证（F6 feature-flags §2 出厂态=全 WARN/姿态文件缺席、§3 出厂态=MD_ACTIVE/状态文件缺席；F5 rollback §7.1 双层表述第一层=本版实际交付态；F13 CHANGELOG L41「机制交付，真实翻转留 Coordinator」+L37「切换授权前置三条件入 RISK-059」）。判定成立。
- **发布级回退口径**：§7/§3b「tag + event integrity sha256 双锚（0.87 FIX-349 口径承袭）」——与 0.88 §3b 回滚锚定原则逐字同源；ledger candidate/released 两态（ADR-010）在 M-5/M-6 行落位。
- **B-12/B-13 回退预案引用如实**：§7 引用「0.88 rollback-plan §8 两路径（REL-088 F-11）——0.89 不触发；激活授权票决策时按该预案 + RISK-059 前置执行」——核对 F5：`rollback-plan-0.88.0.md` §7 专节（B-12 `--deactivate-block`/break-glass + B-13 rollback-begin/export/activate 三段）与 §8 两路径（部署 v0.87.0 tag vs revert 重建）真实存在；「不触发」表述与 §8「无激活」判定自洽；引用如实、无编造。
- **M-1R 席位**：rollback-plan-0.89.0 行「区间锚定 + B-12/B-13 回退预案引用不触发——§7」——回退显式化义务传递到位。

### D3. CHANGELOG 面 —— **PASS（附 P2-1 备注）**

- **落字依据明确**：§8「CHANGELOG 0.89.0 行为变更节如实写『无激活』（M-1 落字依据——本节为规划口径）」+ M-1 行「CHANGELOG 0.89.0 段（行为变更节如实写『无激活』——§8）」——落字义务、落字内容、落字时点（M-1）三要素齐备。
- **依据与 0.88 事实一致**：「无激活」判定与 F6/F13 印证的 0.88 交付态一致（见 D2）。
- **P2-1（非阻塞）**：M-1 行未落字 CHANGELOG canonical 归属（DEC-242① 既决口径 = `project/CHANGELOG.md` 权威、根面为投影）——0.88 期「双位过渡→M-3 裁决→M-5 落字」的返工回路不应在 0.89 重复。详见 §4。

### D4. Feature Flag 姿态（B-12/B-13）—— **PASS**

- **B-12**：§8「机制 0.88 已交付（FEAT-064）——出厂全 WARN；0.89 无 `--activate-block` 执行」——与 F6 §2（出厂态=全 WARN，本版交付态=文件缺席）+ F13 L41 一致；DEC-239②（机制交付/真实翻转分离——翻转经 `--activate-block` 由 Coordinator 发布窗裁决）口径承接准确。
- **B-13**：§8「协议层 0.88 已交付（FEAT-061）——权威标记缺省 MD_ACTIVE epoch0；0.89 无真实切换」——与 F6 §3（缺省 MD_ACTIVE epoch 0 零足迹）+ DEC-238② 一致；`.decision-store-state.json` 缺省缺席语义与 `.write-guard-posture.json` 缺省全 WARN 语义均与 rollback §3 数据安全节（F5 L104-105）一致。
- **激活授权不捆绑**：§1 不承载清单 + §5「只核验不激活」+ §7「独立授权票（不捆绑、不排期）」+ DEC-244 原文「激活授权票不捆绑」——四处一致，边界钉死。
- **M-1R feature-flags 席位**：「B-12 分族姿态全 WARN + B-13 MD_ACTIVE 未激活如实登记」——登记面与 0.88 先例同型（P3-2 措辞张力见 §4）。

### D5. 版本号合规 —— **PASS**

- **semver 顺延**：0.88.0（已发布 2026-09-25，tag v0.88.0 = transition 33d19b0，integrity sha256:9069916b，ledger 本地+remote 双 PASS——F8 L11/L44、F11 L7、F14 manifest 在案）→ 0.89.0 顺延 +1，不跳号。
- **无占用**：roadmap 0.89.0 行唯一（F9 L307，状态=规划）；triage version_chain 终点 0.88.0、1.0.0 预留位未触碰（F12）；`docs/release/` 无 0.89 文件；无 0.89.x tag/预留冲突证据。
- **MINOR 理由充分**：载荷含 FEAT-065（锁腿真释放升级 + acquire TTL 判定面——新增自动化能力面，非纯 bug fix，PATCH 不适用）；六票均无接口删除、无用户可见 breaking（§8——B-x 新登记预期=无，M-1/M-3 按实际 diff 复核的护栏条款在场）；行为变更激活为零，1.0.0 预留不动。MINOR 判定成立。

---

## 3. 八项审查要点逐项核验

### 3-1. 版本号与范围 —— PASS

- **范围 = DEC-244 零扩缩**：DEC-244（F7 L186）授权面 = 必选六项（09-30 风险窗履行 + FIX-390/391/392 披露面消解 + FIX-393/394 深检新票）+ B-12/B-13 五前置核验（不激活）+ FEAT-045 P-a（FEAT-065）；挂起 0.90+ 七项。映射：六票载荷 §2、风险窗 §6、五前置 §5、挂起 §7——**逐项对位，零扩项零缩项**。§1「不承载」清单与 §7 挂起清单逐项比对 DEC-244 挂起清单（God Module 拆分/存储分离其余表/task_status BLOCK 机录化/FEAT-045 P-b/HotFactSource 版本字面量族/GOVERNANCE_SESSION_ID 复核/量测边缘+FIX-380 P2-1）——一致（FIX-380 P2-1 为 0.88 rollback §9 #7 候选池既有项，session-snapshot L33 同源）。
- **载荷票表与热表七行/triage 机录一致**：热表七行（F8 L82-88）与 §2 六票+发布链逐行比对——

| 票 | 规划（§2）优先级 | 热表优先级 | 规划依赖 | triage 机录 | 规划文件面 | triage files |
|----|------|------|------|------|------|------|
| FIX-393 | P1 | P1（L83） | `[]` | `depends_on:[]` ✓ | task_priority/verify_workflow/archive | 同三文件 ✓ |
| FIX-394 | P2 | P2（L84） | `[]` | `depends_on:[]` ✓ | task_row_update/closure_chain | 同两文件 ✓ |
| FIX-390 | P2 | P2（L86） | `[]` | `depends_on:[]` ✓ | verify_workflow/checks/evidence_domain | 同两文件 ✓ |
| FIX-391 | P2 | P2（L87） | `[]` | `depends_on:[]` ✓ | closure_chain | 同 ✓ |
| FIX-392 | P2 | P2（L88） | `[]` | `depends_on:[]` ✓ | verify_workflow | 同 ✓ |
| FEAT-065 | P2 | P2（L85） | `[FEAT-045]`（0.88 已交付） | `blocked_by:[FEAT-045]` ✓ | closure_chain/tests/test_closure_chain | 同两文件 ✓ |

  REL-090 triage（P1/0.89.0/deps=[]/files=version-plan-0.89.0.md）与热表 L82 行一致。**七行全对齐，零漂移**。
- **批次排布依据**：§2 批次一/二/三的同文件串行判断与 triage conflicts 机录吻合（FIX-390×FIX-392 同 `verify_workflow.py`；FIX-391×FEAT-065×FIX-394 closure 腿同 `closure_chain.py`——F12 conflicts 节逐一在案）。

### 3-2. 发布链映射（§3b）—— PASS

- **对照 DEC-197 标准链语义**（F7 L136）：M-0 规划双审→M-1 版本 bump→M-1R 四件套→M-2 门禁实测→M-3 双半面→M-4 风险裁决+go→M-5 checklist+manifest→M-6 ledger→M-7 tag+push→M-8 归档收口——步骤完整、时序单调，与 0.88 实际执行链（F3 L86-101：M-0→载荷→M-1→M-1R→M-2→M-3→M-4→M-5→M-6→M-7→M-8）同构；「M-4 go/no-go 由 Coordinator 呈现」+「预授权不免除 M-2/M-3」（DEC-197 语义）经 M-4 出口判据「复评机录入 risk-log + go 裁决 DEC 入账」承载。
- **0.88 先例形态注入**：M-1 行「REL-087 先例形态」（SKILL frontmatter 权威锚+REQUIRED_SNIPPETS 锚+投影面再生+双根 entry sync+CHANGELOG 段+bump 票随链入账）与 REL-087 交付面（F8 L115）一致；M-1R 行「REL-088 先例」四件套构成与 F3-F6 一致。
- **回滚锚定双锚原则**：§3b「发布全程 tag + event integrity sha256 双锚（0.87 FIX-349 口径承袭——0.88 §3b）」——与 0.88 §3b 回滚锚定原则同源；M-7 出口判据「本地/remote tag peel 一致」+ taggerdate 权威（FIX-349 口径）在场。
- **M-3 终态口径**：「双半面 GO（终态口径同 0.88：APPROVED / AWN/0）」与 release-review SKILL 终态语义（APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES 为通过终态）一致。
- **M-0 出口判据可判定**：「双 GO（APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES）」——本轮报告即该判据的消费输入之一。

### 3-3. 门禁面（§4）—— PASS（七条全可执行可判定，口径与 0.88 M-2 实测基线一致）

| # | 门禁 | 规划口径 | 0.88 实测基线核验 | 判定 |
|---|------|---------|------------------|------|
| 1 | 全量 pytest | 基线 4119P/0F（历史首次全绿）+零回归目标+「全量只在 M-2 是预算非免检许可」护栏 | 4119P/0F 与 F8 L11/L44、F11 L14 一致；护栏条款与 0.88 §3 条 1（F2 L67）逐字同源 | ✓ |
| 2 | verify 全量+e2e+check-governance | 已知披露面基线 36 issues（REQ-092×6+EVD-1146×1+DEC-241 例外×4+Check 30 V3×5）；FIX-390/392 后 census 收窄至 7 | 36 census 与 DEC-243 实测口径（F7 L185）逐项一致；收窄算术 16→7 自洽（-4-5）；REQ-092 零豁免红线维持（DEC-227 路线 a） | ✓ |
| 3 | LRC 复算 | 预算 361,923；越线按 FIX-369 公式重定标（非豁免） | 361,923 = FIX-369 重定标值（F8 L11）；非豁免口径与 0.88 §7（F2 L110）同源 | ✓ |
| 4 | archguard 棘轮席 | 0.88 基线 regen 26193（sanctioned）——M-1R 门禁摘要显式列 | regen 26193 sanctioned 与 F11 L14、DEC-243② 一致 | ✓ |
| 5 | Check 28s 复测 | ERROR 现值 1690.6KB——0.88 窗口行进入归档范围后复测（M-8 联动） | 1690.6KB 与 F11 L21 一致；「下归档周期消解」先例（0.87/0.88 同型）在场 | ✓ |
| 6 | check-release 两态+ledger+projection+quality-tools | candidate 态/ released 态复跑；quality-tools 未安装记 NOT_RUN 不虚报 | 两态流程与 0.88 M-5/M-6 实际链（F3 L97-98、F11 L18-19）一致；NOT_RUN 如实原则符合 SKILL 事实依据红线 | ✓ |
| 7 | §9 组合测试集为 M-2 必查席 | 「禁全量」不得退化为「只测单票」（0.88 §3.2 口径） | 与 0.88 §3 条 2（F2 L68）同源；§9 四项组合锚定 triage conflicts 机录 | ✓ |

### 3-4. 行为变更面（§8）—— PASS

「=无激活」判定与 0.88 交付事实一致（三方证据链：feature-flags-0.88.0 §2/§3 + rollback §7.1 第一层 + project/CHANGELOG.md L37/L41——详见 D2/D4）；`.write-guard-posture.json` 缺省缺席=全 WARN、decision-log 权威状态机现值=MD_ACTIVE epoch0 的缺省语义均经 0.88 交付文档与 DEC-238②/DEC-239② 互证。护栏条款在场：「若出现实质行为面（如 FIX-394 状态列文本格式变化被判定为可见面）如实入账并知会双审」+「B-x 新登记预期=无——M-1/M-3 按实际 diff 复核」——判定不是免检声明而是带复核义务的规划口径。**六票 triage files 面均不含 SKILL.md/commands 投影面**（F12 逐票核对属实——投影面再生随 M-1 常规执行的表述成立）。

### 3-5. 回退与挂起（§7）—— PASS

无数据级回退触发面口径成立（见 D2）；B-12/B-13 回退预案引用 `rollback-plan-0.88.0.md` §8（F-11 两路径）「不触发」——**如实**（预案真实存在、触发前提=激活/切换执行，而 0.89 明确零激活）；挂起清单与 DEC-244 一致；「独立授权票（不捆绑、不排期）」边界钉死；「候选未排期（如实登记）：review-record CLI --force 旗标——未入 0.89 载荷亦未入挂起清单」与 risk-log RISK-047 现值注记（F10 L4 DEC-243④ 注记）一致。

### 3-6. 五前置核验（§5）—— PASS

- **逐项 DEC 锚准确性**：①②③=DEC-238④ 三前置（F7 L180④ + RISK-059 三缺口 F10 L6 逐字对应：archive DEC 归档路由/freshness 接线/11 处 DEC-nnn① 勘误行处置）；④=DEC-239⑦-1 archguard R1 锚处置（0.88 M-2 regen 26193 sanctioned——F11 L14 佐证「已执行」现状）；⑤=DEC-239⑦-2 F-5①③ 组合测试（「归切换授权票」原文语义承接；FEAT-061 cutover 验收项④——F8 L106 佐证）。
- **核验动作+结论回填位+失败判据**：五行均有 M-0 核验动作（复核登记一致性）+「待 M-0 执行回填」结论位 + §5 末「核验结论判据」（登记一致性复核完成+逐项回填=通过；发现被绕开执行=核验失败→上报不视为可激活）——逐项可判定。
- **「只核验不激活」边界钉死**：§5 标题+引言（DEC-244 授权原文）+核验结论判据+§7 独立授权票——四层防线；激活条件显式指向「五前置闭环+证明包审查（feat061-rehearsal-result.json 口径）后另行授权」。
- **范围注记**：cutover 授权票验收项⑤（FEAT-062 F-7 dec_in_world 耦合——F8 L106）不在五前置内——该验收项属切换授权票自身验收面（REVIEW-FEAT-062-R1 补落），与 DEC-244「DEC-238④×3+DEC-239⑦×2」的授权框架不冲突，非遗漏。

### 3-7. 风险窗（§6）—— PASS

- **时序纪律闭合**：「窗内履行不迟于 2026-09-30。若 0.89 M-4 晚于 09-30，复评裁决须窗内独立先行入账（risk-log 机录），M-4 消费其结论——0.88 规划 F-13 口径」——复评义务与 M-4 的时序关系闭合（复评独立先行、M-4 消费结论，两不误）；Check 8 门禁联动现值标「待 M-1R 核对——**待验证**」（诚实标记，见 3-8）。
- **逐条承接与 risk-log 现值一致性**：
  - RISK-036：规划「维持打开——0.88 窗口无新交付；关闭标准未满足」= DEC-243① 裁决原文（F7 L185①）；热 risk-log 行在案（F10 L1，DEC-243 注记 grep 命中）。
  - RISK-039：规划「维持打开（正向注记：4119P/0F+archguard regen+拆分候选入池）」= DEC-243②；热行「打开/截止 2026-09-30」（F10 L2）一致。
  - RISK-046：规划「维持打开（实质接近关闭——FEAT-013 根因修复+F-2 竞态独立验证+acquire 锁腿候选入 0.89）」= DEC-243③；「确认候选池承载=FEAT-065 已立票入 0.89 载荷→维持观察至 0.89 落地关闭」与 DEC-243③「维持观察至 0.89 落地关闭」一致；FEAT-065 立票事实（F12/L85）成立。
  - RISK-047：规划「同窗观察：CLI --force 旗标候选未入 0.89 载荷（未排期）」= DEC-243④ + 热行注记（F10 L4）逐字吻合。
  - RISK-050：规划「打开（窗外——截止 2026-10-31）；不属 09-30 窗；本表仅登记在案」——热行「打开/2026-10-31」（F10 L5）一致；窗外定位正确。
  - RISK-059：规划「§5 五前置核验对象——激活授权票前置，非 09-30 窗义务」——热行「打开（2026-09-25 登记）」（F10 L6）一致。
- **M-4 承载与 RISK-050/059 的窗外/非窗定位**：RISK-050（10-31）与 RISK-059（授权票前置）不入 09-30 窗义务清单——定位正确，无义务错配。

### 3-8. 诚实性（两处「待验证」+§5 回填空位）—— PASS（规划期可接受）

- **待验证①（§5③）**：「11 处勘误行当前实测行数**待验证**」——登记时点口径与实测行数的差异明确标记，核验动作（复核现存勘误行计数）与失败判据（被手工提前改动=核验失败）在场——这是诚实的悬置而非含糊。
- **待验证②（§6 时序纪律）**：「Check 8 自 10-01 转 FAIL 的门禁联动；现值待 M-1R 核对——**待验证**」——0.88 F-13 口径的现值核验后置到 M-1R（版本面 bump 时点），责任人/时点明确。
- **§5 回填空位×5**：「待 M-0 执行回填」——M-0 内含核验义务的执行期占位，判据段定义了通过/失败两态——规划期占位合规（与 0.88 checklist「M-2 数值不预填」纪律同构）。
- **无编造**：全文未发现将未执行动作写成已执行、未实测数值写成实测值的表述；「未激活」「不触发」「如适用」等弱主张措辞与事实源一致。符合 release-review SKILL 事实依据红线。

---

## 4. Findings 分级枚举

### P0（阻塞）

无。

### P1（重要）

无。

### P2（建议）

- **P2-1 · M-1 CHANGELOG 落字未显式继承 canonical 归属**：§3b M-1 行与 §8 只写「CHANGELOG 0.89.0 段」，未落字 DEC-242① 既决口径（canonical=`project/CHANGELOG.md`，根 `changelog.md` 为投影）。0.88 期经历了「M-1 双位过渡→M-3 裁决 canonical→M-5 落字+入 manifest」的返工回路（F3 L65、F7 L184①、F11 L15/18）；0.89 无激活态下 CHANGELOG 面薄，重新双位只会复刻裁决成本并引入 projection/static-pin 交叉风险。**建议**：M-1 执行时按 DEC-242① 单 canonical 落位（0.89.0 段写入 `project/CHANGELOG.md`，根面随投影再生），在 M-1 交付描述中显式注明。〔证据锚：version-plan-0.89.0.md L47/L113；DEC-242①；release-plan-0.88.0.md L65〕
- **P2-2 · roadmap 0.88.0 行 M 链备注未随 M-8 回填至终态（先例基线残留）**：`plan-tracker.md` roadmap 0.88.0 行状态列已回填「已发布 2026-09-25」，但其 M 链描述列仍为 M-0 期中途文本（「M-0 双半面审查中（…Release R0 NEEDS_CHANGE/3 修复中）→ M-1~M-8 标准链…」），未承载 M 链终态事实（M-0 双 GO→4119P/0F→双半面 GO→DEC-243 go→transition 33d19b0→tag→M-8 收口）；对照 0.87.0 行先例（M-8 收口回填+tag/integrity 事实+「本行随 M-8 收口回填（FIX-367 复发预防义务）」注记）为未竟义务。该残留在 plan-tracker 数据面（FIX-394「13 行一次性数据对齐」范围为任务行 B~E 批+REL-087/088/089，不含 roadmap 行），0.89 §3b M-8 仅含「roadmap 0.89.0 行状态回填」。**非审查对象缺陷，不阻塞 M-0 GO**（M 链终态权威记录在 plan-tracker 项目配置/项目总览/REL-086 行+session-snapshot，均一致）。**建议**：0.89 M-8 收口批增补「0.88.0 roadmap 行 M 链终态补回填」席位（一行数据勘正，M1.2 通道即可），或并入 FIX-394 一次性数据对齐现场裁量。〔证据锚：plan-tracker.md L306 vs L305（0.87.0 行先例）；session-snapshot.md L9-21〕

### P3（注记）

- **P3-1 · RISK-036 行全文未逐字重读（显示截断下的部分核实）**：热 risk-log 前段为单行超长格式，RISK-036 行位于第 1 行内，本审查工具对该行显示截断，未能逐字复读全行；已核实：①RISK-036 行存在于热 risk-log（grep 命中 L1）；②该行含 DEC-243 注记（「DEC-243」grep 命中 L1）；③规划 §6 RISK-036 行内容与 DEC-243① 裁决原文逐项一致；④session-snapshot L17/L44（「RISK-036/039/046 维持打开」「打开（DEC-243 裁决注记）」）交叉印证。四源一致，风险为低；如实登记为「经交叉印证的部分核实」而非逐字核实。〔证据锚：risk-log.md L1；DEC-243①；session-snapshot.md L17/L44；version-plan-0.89.0.md L87〕
- **P3-2 · M-1R feature-flags「如适用」措辞与「四件齐」出口判据的措辞张力**：§3b M-1R 行件面写「feature-flags-0.89.0 如适用」，同行出口判据为「四件齐」——0.88 先例为四件全交；0.89 无激活态下 feature-flags 仍有实质登记面（B-12/B-13 姿态+灰度开关边界+未发布面），建议 M-1R 起草按四件全交执行，消除「可缺件」歧义解读。出口判据本身无弱化。〔证据锚：version-plan-0.89.0.md L48；feature-flags-0.88.0.md 全文形态〕
- **P3-3 · 编辑面**：§9④ 与 §4 条 5 的交叉引用写作「§4.5」（节-条混排）；建议统一为「§4 条 5」。不影响判定。〔证据锚：version-plan-0.89.0.md L65/L126〕

---

## 5. 硬门槛裁决（规划期映射）

| 硬门槛项 | 规划期判定 | 依据 |
|----------|-----------|------|
| 发布检查清单席位 100% 映射 | **PASS**——M-1R 四件套+回填位+组合清单转入席位齐备 | §3b M-1R/M-5 出口判据；0.88 checklist 先例（F4） |
| 回滚方案存在且显式 | **PASS（规划期）**——双锚原则+无数据级触发面判定成立+0.88 §7/§8 预案引用如实、M-1R 回退显式化席位在 | §7/§3b；rollback-plan-0.88.0 §7/§8（F5） |
| CHANGELOG 用户视角完整（席位） | **PASS（附 P2-1）**——落字依据（§8「无激活」）+落字时点（M-1）明确；canonical 归属建议 M-1 显式继承 | §8；DEC-242①；project/CHANGELOG.md 0.88.0 段形态（F13） |
| Feature Flag 关闭/姿态验证（席位） | **PASS**——B-12 全 WARN/B-13 MD_ACTIVE 与 0.88 交付事实一致；kill-switch 通道为 0.88 已验证交付件（EVD-1155/1156），0.89 仅引用不触发 | §8；feature-flags-0.88.0 §2/§3/§7（F6）；DEC-238②/239② |
| 版本号合规 | **PASS**——0.88.0→0.89.0 顺延+1，无占用，MINOR 理由充分，1.0.0 预留不动 | §1；F8 L307；F12 version_chain；F14 |
| 无未解决 BLOCKING finding | **PASS**——P0=0，P1=0 | §4 |

---

## 6. 最终结论

## **APPROVED_WITH_NOTES**

**unresolved_blockers=0**

- **通过理由**：规划期发布半面八项审查要点全部 PASS——范围与 DEC-244 零扩缩且与热表/triage 机录逐票一致；M-0~M-8 链对照 DEC-197 语义与 0.88 先例完整、双锚回滚原则在场；七条门禁可执行可判定且口径与 0.88 M-2 实测基线逐项吻合；「=无激活」判定与 0.88 交付事实三方互证；五前置核验逐项 DEC 锚+回填位+失败判据齐备、只核验不激活边界钉死；风险窗时序纪律闭合、六风险承接与 risk-log 现值一致；两处「待验证」+五处回填空位均为带判据的诚实悬置，无编造、无越权主张。P0=P1=0。
- **保留备注（非阻塞，跟踪面）**：P2-1（M-1 CHANGELOG canonical 归属显式继承 DEC-242①）、P2-2（0.88 roadmap 行 M 链终态补回填——建议纳入 0.89 M-8 或 FIX-394 对齐面）、P3-1/2/3（注记级）。
- **边界重申**：本结论为 M-0 规划面 GO，不构成发布就绪判定——M-1R 四件套、M-2 门禁实测、M-3 双半面、M-4 go/no-go、M-6 ledger、M-7 tag 的发布就绪证据在后续链位独立审查；本半面 GO 不豁免其中任何一环。
- **复审链语义**：本报告为 REL-090 发布半面 R0 终态报告（APPROVED_WITH_NOTES，unresolved_blockers=0——release-review SKILL 通过终态口径）；Design 半面结论由 Design Reviewer 独立出具，M-0 出口判据「双 GO」以两半面终态合并为准。

---

*审查报告冻结（2026-09-25，Release Reviewer Agent，REL-090 RELEASE R0）。事实基线：审查对象 version-plan-0.89.0.md（128 行全文）；先例面 version-plan-0.88.0.md + docs/release 0.88 四件套（plan/checklist/rollback/feature-flags）；治理面 decision-log DEC-197/238/239/241/242/243/244、plan-tracker 热表 L82-88+roadmap L306/307、risk-log 六风险行、session-snapshot 全文；机录面 .governance/change-triage 七件 JSON 逐票比对；CHANGELOG 面 project/CHANGELOG.md 0.88.0 段；manifest 存在性 core/releases/0.88.0.json。RISK-036 行全文因热文件单行格式显示截断未逐字复读，以四源交叉印证替代（P3-1 如实登记）。本报告为唯一写入文件；审查对象与治理记录零写入。*
