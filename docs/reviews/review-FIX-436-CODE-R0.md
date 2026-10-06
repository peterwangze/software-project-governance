# REVIEW-FIX-436-CODE-R0 — DEC-316/317 sweep 收尾批（F-2 / R1-1 / R1-2 / R1-3 / F-8 / F-B3 / F-C1）

**Round: R0（初审）** | Reviewer: Code Reviewer（只读实读审查；角色契约 Bash/Write/Edit 禁止——未运行任何命令、未修改任何文件，报告全文返回 Coordinator 机录）| 日期：2026-10-06

**审查对象**：FIX-436 六子项（F-2 / R1-1 / R1-2·R1-3 / F-8 / F-B3 / F-C1）。

**审查面声明**：工作树 staged 变更（未 commit，对照 HEAD `f1a47fd`）——Reviewer 无命令通道，以仓库当前文件态实读为审查面；与 HEAD 的逐行 diff 不可达，锚行/标记行「零触碰」以**功能面验证**替代（守卫正则对合 + 标记在场 + 引文同步 + 相邻行号考古），如实标注于「未验证项」①。裁定依据实读：`.governance/decision-log.md` DEC-316/317/318/319、`docs/reviews/review-FIX-432-CODE-R0.md`（F-2/F-8 原始 finding）、`review-FIX-432-CODE-R1.md`（R1-1/R1-2/R1-3 原始 finding）、`review-FEAT-088-CODE-R0.md`（F-B3/F-C1，§7 四点理由）。

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**（无 BLOCKING finding；六子项全部落地且与 DEC-316/317 裁定逐项对合）

findings 计数：**P0=0 · P1=0 · P2=0 · P3=2**（两条均为边角演进备注，不阻塞）。

## 一、六子项逐项实读核验

### 1. F-2：bp F-A5 注记措辞收紧 — 通过

实读 `references/behavior-protocol.md` L843-857 + L850 + L874：

- **声称落点逐项对合**：①「无发现」前置条件已改为「判定=『可跳过』，或判定=『受限』且无通道阻断事实与本地降级动作」（L857）✓；②新增「判定=『受限』且存在通道阻断事实时，结果记『被阻止』——专用于承载 EXP-03 通道阻断事实（样本 S2 形态：判定=受限、未发起外部调用、结果=被阻止），此时 MUST NOT 因『未发起动作』改记『无发现』（EXP-03 记录义务）」（L857）✓；③四态枚举未动——L850 schema 注释 `# 有发现 | 无发现 | 失败 | 被阻止（「未探测」形态映射见下）` 恰四态 + 下行指针，无第五枚举 ✓；④落款「FIX-436 F-2 措辞收紧」可追溯 ✓。
- **与 S2 样本自洽性（验收①核心）**：实读 `docs/research/feat-086-prospective-samples-2026-10-04.md` L62-68——S2 = 判定=受限 + 通道阻断事实在场（角色契约禁用 Agent 类通道）+ 本地降级动作（M10.3 规范源+runtime_capabilities 先例）+ 结果=被阻止。收紧后 S2 明确落入第二支（存在阻断事实→被阻止）；第一支双前置条件（无阻断**且**无降级）S2 均不满足——原 R0 F-2 指出的「括号短语严格读法与 S2 冲突」被精确消除。S3~S5（L80/L97/L114：判定=可跳过 + 结果=无发现 + `# 未发起探测` 注释）由第一支「判定=可跳过」直接覆盖 ✓。
- **与 DEC-316(2) 不矛盾**：DEC-316 核心裁定（不增「未探测」枚举 + 由「判定」轴消歧 + 不增态理由）在 L857 完整保留（「判定≠需要 ⇒ 无探测动作」「矛盾态组合（判定=需要+结果=未探测）」原样在文）；DEC-316 残余处置段明示 F-2「归下一张 behavior-protocol 票承载」= 修复预授权，本票为授权路径内执行 ✓。
- **锚行/标记行零触碰（quote_sync 守卫依赖）**：功能面验证通过——守卫锚正则（verify_workflow.py L12041-12044）与 bp L874「任务级触发入口位于 SKILL.md…表后一行：「…」」对合 ✓；`生成≠咨询` 标记在 L867（consult 行）/L870（adapter 段）两处在场 ✓；SKILL.md L364 触发行与引文 span 逐字同步（grep 全文件恰 1 命中）✓。行号相对 FIX-432 R0/R1 时点（L865/L868/L872 → L867/L870/L874）整体 +2，与 L855/L857 段扩展净增 2 行（bp 905→907）相容，无中间插入迹象。
- 残余边角 → **finding N-1（P3）**。

### 2. R1-1：QuoteSyncGuardTests 新增 3 case — 通过

实读 `infra/tests/test_verify_workflow.py` L24888-24954：

- **`test_bp_anchor_line_prefix_reworded_is_flagged`（分支③）**：锚行前缀「表后一行」→「表后两行」变异 → `assertEqual(len(issues), 1)` 恰 1 条 ✓ + `assertIn("anchor line missing or reworded", issues[0])` 与守卫 L12047-12048 issue 文案逐字子串对合 ✓ + `assertNotIn("adapter-manifest.json", issues[0])` 验证 manifest 面不串扰 ✓ + 前置 `assertIn("表后一行", lines[hit[0]])`（L24908-24911）防上游措辞漂移导致夹具静默失效 ✓ + `len(hit)==1` 锚行唯一定位 ✓。分支真实性：守卫 `if not m: … elif …` 结构下正则失配只走分支③，引文 drift 分支（elif）不可达，manifest sweep 面未触碰（复制的 bp 副本标记在）——恰 1 条的逻辑推演成立。
- **`test_unreadable_bp_or_skill_fails_closed`（分支①②）**：unlink bp → 恰 1 条含「behavior-protocol.md」+「unreadable」+「fail-closed」（与守卫 L12034 `{bp_path.as_posix()} unreadable (fail-closed)` 对合）✓；恢复 bp 后 unlink SKILL.md → 恰 1 条含「SKILL.md」（L12038 对合）✓。unlink（FileNotFoundError ⊂ OSError）与守卫 `except OSError` 精确对合 ✓。
- **`test_single_manifest_bad_json_fails_closed`（分支⑥b）**：写 `"{ not json"` → `json.loads` 抛 JSONDecodeError → 恰 1 条含 rel +「unreadable or invalid JSON」（与守卫 L12070 逐字对合）✓；rel 取 `[-1]`（dsh），其余五 manifest 复制完好静默 ✓。
- **沙箱隔离形态**：`_governance_temp_dir`（L94-101，既有 FIX-403/404 家族 helper：tempfile.gettempdir+uuid+`rmtree(ignore_errors=True)` 降级清理）+ `patch.object(vw, "ROOT", Path(root))`——8 规范面 `shutil.copyfile` 只读复制入临时 ROOT，全部变异经 `_write(root, …)` 只写副本，**真实仓零写入**（逐行实读无一处写向 `vw.ROOT`）✓。

### 3. R1-2 / R1-3 — 通过

- **R1-2**：`_ANCHOR_RE` 注释（L24757-24761）明示「VERBATIM COPY of the guard's inline regex (verify_workflow.py `_check_quote_sync_issues` — the regex lives inline in the function body, so it cannot be imported). The two MUST be updated together in one change; drift fails visibly via `_real_citation`'s assertIsNotNone, never silently」——与 R1-2 修复建议逐字对应 ✓；`_real_citation` docstring（L24785-24790）同步改写（「verbatim copy … the two MUST be updated together, see _ANCHOR_RE」）✓。正则本体与守卫 L12042 **逐字符比对一致**（含 `SKILL\.md` 转义、空格、全角标点、非贪婪捕获）✓。
- **R1-3**：L24852 / L24946 两处 `rel = vw.QUOTE_SYNC_ADAPTER_MANIFESTS[-1]` 替代 dsh 字面量，注释（L24848-24851）说明「no dsh-specific fixture to rot if the platform roster moves」✓。`[-1]` 与守卫元组（L12012-12019）末位 `adapters/dsh/adapter-manifest.json` 精确等价 ✓。

### 4. F-8：三消费点 `.get` 注释改写 — 通过（纯注释变更确认）

三处实读：L7505-7508（release 面，`.get` 在 L7509）/ L16565-16567（Check 12 引擎面，`.get` 在 L16568）/ L22481-22483（CLI 面，`.get` 在 L22484）。新注释统一为「the current check_cross_references() always emits the key — .get only tolerates pre-FIX-432/partial dict shapes (that lack it)」——主事实（活调用恒发键）前置、`.get` 定位为防御性容忍，消除了 R0 F-8 指出的「理由不实」（L7507 版另附真实场景「e.g. fixtures」，比 R0 建议「defensive .get; the live call always provides the key」更具体）。**逻辑零变更确认**：三处 `.get("quote_sync", [])` 调用形态、默认值、计数路径（`xr_issues += len(xr_quote)` / `all_issues` / `fail = True`）全部原样 ✓。开发者报行号（L7505/L16504/L22414）有漂移，实体定位以实读为准——票面已预告漂移可能，非问题。

### 5. F-B3：check_exploration_sample_advisories — 通过（本票最高风险面，逐面核验）

实读 verify_workflow.py L12327-12370（定义）+ L16602-16606（Check 12 引擎面）+ L22513-22517（CLI 面）+ 测试 L24957-24999：

- **advisory 确不阻断（验收④全查）**：①Check 12 引擎面（L16605-16606，位于 `cmd_check_governance` L16048 起的 check-governance 宿主健康面内）——`for advisory in …: print(f"│  [ADVISORY] {advisory}")`，不触碰 `xr_issues`/`all_issues` 任何计数变量，Check 12 PASS 行判据 `xr_issues == 0` 不含 advisory ✓；②CLI 面（L22516-22517，`cmd_check_cross_references`）——同样仅 print，`fail` 变量只被 dangling/deprecated/cycles/quote_sync/channel_issues 置位，advisory 循环位于 `if fail: sys.exit(1)`（L22520-22521）之前的纯输出路径 ✓；③无第三消费点（全局 grep `EXPLORATION_SAMPLE` 恰 5 处 = 定义 3 + 消费 2）✓。
- **registry 零 churn**：无新编号 check 声明属实——F-B3 以 print 级挂载骑 Check 12 与 check-cross-references CLI（FEAT-088 quote_sync 同款承载纪律），不进任何 check 编号清单/argparse 注册 ✓。
- **additive（CLI/JSON 接口零变更）**：`check_exploration_sample_advisories()` 独立函数，不经 `check_cross_references()` 返回 dict 挂载——该 dict 键集零变更；advisory 只进 stdout 渲染、不写任何结构化 dict/JSON 面 ✓。
- **确定性单事实**：`re.search(r"(?m)^exploration:", text)` 行首匹配——只判「committed 样本报告携带 ≥1 个 `exploration:` 区块」；不可读 → advisory（非 FAIL，advisory 面宽松方向正确）；不判 omission legality（docstring 与 issue 文案均明示「honest-vs-lazy omission stays human-judged」）——与 DEC-317 四点理由（判定面不同/机检效力边界/A10 薄度/更适载体）逐条对合，载体骑 check-governance 宿主健康面与裁定吻合 ✓。
- **双态测试真覆盖**：健康态 `test_healthy_repo_yields_no_advisories` 对真实 ROOT 断言 `== []`（实读两样本文件：feat-086 五块 L38/63/80/97/114、feat-087 三块 L30/63/131——当前态前提成立）；WARN 态隔离 root 剥离 `exploration:` 行 → 恰 1 advisory + 文案断言（「no \`exploration:\` block」/「FIX-436」与实现 L12365-12369 逐字对合）+ `_read_stripped` 前置 assert 防夹具上游漂移 ✓。剥离逻辑（startswith 行删除）与检测 regex（`(?m)^` 行首）一致 ✓。
- **载体薄度**：函数 26 行 + 元组 2 行 + 消费 2×3 行 + 注释块——最小面 ✓。

### 6. F-C1：探针边界措辞明示 — 通过

实读 L12262-12270 + L12304-12322：

- **9 行注释**（L12262-12270，恰 9 行）：明示「the corroboration below is a DOCUMENT-WIDE substring match — deliberately weaker than the §-level granularity the evidence prose may claim」「a heuristic §-neighborhood rule would fire definite FAILs on legal shapes (the false-alarm class this guard forbids)」「§-level positioning stays human-review territory」——落款「FIX-436 (F-C1, option b / DEC-317(2))」✓。
- **`feasible_probe` 字符串值**（L12308-12315）：明示「read-only, DOCUMENT-WIDE substring match, NOT section-scoped — a date present anywhere in the cited document corroborates, so the §-level granularity claimed by evidence prose is human-review territory」——FEAT-088 R0 F-C1 建议的「至少在 probe_layering.feasible_probe 措辞中明示 document-wide，非节定位」**逐字兑现** ✓。
- **仅字符串值编辑、键集合不变**：`probe_layering` 三键 `static_evidence_form`/`feasible_probe`/`not_probeable` 原样，仅 feasible_probe 值扩展 ✓；判定逻辑 L12276 `verified_on.strip() not in ref_text`（document-wide substring）**未动**——收紧后声明与实际行为精确一致（此前声明粒度强于行为，现在措辞如实）✓。
- **与守卫「FAIL 仅触发于确定性事实」原则自洽**：注释本身论证了为何不引入 §-邻域启发式（会对合法形态制造确定性 FAIL 误报）——该原则（L12110-12113「FAIL fires only on definite facts … never on heuristics」）未被违反，反而被注释显式援引 ✓。DEC-317(2)「强化定位或措辞明示边界二选一」→ 选措辞明示（option b），落地 ✓。

### 7. 回归证据链自洽性（验收⑥）

开发者声称：全量 verify exit 0 / check-cross-references PASS / check-manifest-consistency 1038 一致 / 双跑「Ran 1052 FAILED (failures=2) → Ran 1057 FAILED (failures=2)」/ 新 5 case 全绿（3 R1-1 + 2 F-B3）/ 同二预存失败（ContractTierBudgetTests / Feat039InjectionBudgetTests）。Reviewer 无命令通道未复跑（→未验证项②），可核的间接证据：**+5 case 与 1052→1057 精确吻合**（3+2=5）；5 case 断言与实现文案逐字对合（§2/§5 上述）——测试逻辑上可绿的推演自洽；预存失败族存在性有 DEC-319（FIX-438 披露「契约族 12 预存测试失败」）佐证，failures=2 前后不变的**零新增**声称与文件态相容（本票全部增量不含 ContractTierBudget/Feat039Injection 面）。数字链形式自洽，采信为「声称一致」，不作独立验证依据。

## 二、5 维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| **正确性** | **通过** | 六子项逻辑逐项核验（§一）：F-2 两支映射与 S2/S3~S5 实测形态自洽；R1-1 三 case 分支覆盖真实（if/elif 结构推演）；F-B3 判定单事实确定性；F-C1 措辞与行为精确一致；F-8 纯注释；边界（不可读文件→advisory/issue、坏 JSON→fail-closed continue）均有确定行为 |
| **安全性** | **通过** | 全部增量只读仓内文件 + 字符串拼接输出，无注入/求值面、无密钥、无外部输入面；F-B3 `errors="replace"` 宽松方向仅作用于 advisory 面（漏 advisory 无害，不制造误 FAIL）；测试对真实仓零写入（隔离 helper + patch.object 逐行核读） |
| **可维护性** | **通过（附 N-1/N-2）** | 注释全部携带出处（FIX-436 F-C1/DEC-317(2)、F-B3/DEC-317、R1-2 verbatim-copy 同步契约）；R1-3 去 dsh 硬编码；F-8 注释诚实化；命名表意（EXPLORATION_SAMPLE_REPORTS/check_exploration_sample_advisories）；残余：样本元组生命周期同步义务（N-2）、F-2 边角组合（N-1） |
| **性能** | **通过** | F-B3 两消费点各 2 次小文件 read_text（一次性、无循环放大），相对 Check 12 全仓扫描可忽略；R1-1 case 各复制 8 小文件 + 守卫单次调用；F-2/F-8/F-C1 零运行时成本（纯文本） |
| **测试覆盖** | **通过** | +5 case：守卫分支③①②⑥b（含「恰 1 条+文案逐字+manifest 排除」精确断言与夹具前置防漂移）+ F-B3 双态（真实仓健康态 + 隔离剥离 WARN 态）；守卫 6 分支现全覆盖（④⑤ 由 FIX-432 R1 case 承载）；无宽断言凑绿迹象 |

## 三、发现列表

| # | 级别 | 文件:行号 | 问题 | 依据 | 修复建议 |
|---|------|----------|------|------|---------|
| N-1 | **P3** | references/behavior-protocol.md L857 | F-2 两支字面对「判定=受限 且 无通道阻断事实 且 **有**本地降级动作」组合均未显式覆盖（第一支要求无降级、第二支要求有阻断）。语义上该组合近乎矛盾态（做本地降级 ⇒ 探测需求被不可用通道阻断 ⇒ 阻断事实在场，如 S2），故现实样本无歧义；且此措辞为 R0 F-2 修复建议原文的忠实执行。 | S2（feat-086 样本 L62-68）实测形态落入第二支；S3~S5 落入第一支；构造第三态需「做了降级却否认被阻断」的自相矛盾记录 | 知识分享级：后续 behavior-protocol 票可补一句「本地降级动作在场即视为通道阻断事实在场」显式闭合；或永久接受语义蕴含读法，无需本票动作 |
| N-2 | **P3** | infra/verify_workflow.py L12339-12342 | `EXPLORATION_SAMPLE_REPORTS` 硬编码双样本元组——未来新增 committed 样本报告（如 0.96.0+ 的 exploration 留痕样本）不会自动纳入 advisory 覆盖，需手工同步；与 R0 F-6（QUOTE_SYNC 六元组硬编码）同族演进备注。advisory 性质决定漏报后果轻（丢 advisory 覆盖面，无 FAIL/安全面），且健康态测试对真实仓 fail-visible（文件移除→测试红+advisory 双红信号）。 | 全局引用恰 5 处无发现机制；FEAT-086/087 样本为当前仅有的两个 committed exploration 样本 | 后续票在 M10.2 或 sweep 惯例处标注「新增 committed 样本报告 MUST 同步 EXPLORATION_SAMPLE_REPORTS」一句；或接受现状（观察级） |

## 四、AI 代码专项 5 项结论

1. **mock 残留 = 无**：`patch.object(vw, "ROOT", Path(root))` 为仓库既有标准隔离手法（R0 BM-4/R1 报告先例），断言全部基于守卫/函数真实返回值；F-B3 测试零 mock（真实 ROOT 健康态 + 物理复制副本变异态）。
2. **硬编码返回值 = 无**：advisory/issue 字符串全部由实测检查路径构造；测试变异文案（「表后两行」/`{ not json`）是注入输入而非返回值伪造；两处前置 `assertIn`（锚行子串、样本区块在场）防夹具静默失效。
3. **幻觉 API = 无**：仅 `re.search`/`Path.read_text`/`json.loads`/`shutil.copyfile`/`patch.object` 标准库调用；无新增 import（沿文件既有模块级 import）。
4. **未实现 TODO = 无**：全部新块（L12262-12270 / L12327-12370 / 测试 L24757-24999）实读，零 TODO/FIXME/XXX。
5. **过度实现 = 无**：六子项均为最小面——F-B3 函数 26 行+双消费 print；F-C1 注释+单字符串值；F-8 三处注释；R1-1 恰建议的 3 case；R1-3 一行替换；无投机配置面或预留参数。

## 五、蓝军挑战（3 条）

- **BM-1「F-B3 advisory 误阻断通道」**：逐一排查两消费点的全部计数/退出变量——Check 12 面 advisory 循环后紧跟 `if xr_issues == 0: [PASS]`（advisory 不入 xr_issues）；CLI 面 `fail` 置位清单（dangling/deprecated/cycles/quote_sync/channel_issues）均不含 advisory，`sys.exit(1)` 前纯 print。第三消费点全局 grep 排除。通道封死。
- **BM-2「F-2 修订是否越权改判 DEC-316」**：DEC-316(2) 字面「（或受限未发起动作）→无发现」与 S2 的矛盾正是 F-2 原始 finding；DEC-316 残余处置段明示 F-2 归下一张票承载（修复预授权），DEC-318 将 F-2 列入本票票面——授权链完整；DEC-316 核心裁定（四态不增枚举+判定消歧）逐项保留。非越权。
- **BM-3「新测试凑绿面」**：三重防凑绿——恰 N 计数（`assertEqual(len, 1)`）+ 目标文案逐字断言（与实现字符串逐子串对合，本审查逐条比对）+ 反向排除（manifest 不串扰）+ 夹具前置断言；`_ANCHOR_RE` 与守卫正则逐字符比对一致（verbatim 契约成立）。

## 六、硬门槛裁决表

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|------|------|------|
| P0 阻塞问题数 | = 0 | **✓ 通过** | findings 表实证 P0=0 |
| 5 维度全覆盖 | = 100% | **✓ 通过** | §二逐项有结论 |
| 每条发现标注级别 | = 100% | **✓ 通过** | N-1/N-2 均带 P3 |
| 设计一致性检查 | 已完成 | **✓ 通过** | DEC-316(2)（不增枚举/判定消歧/F-2 预授权）、DEC-317(1)（F-B3 advisory 载体+四点理由）、DEC-317(2)（F-C1 二选一→措辞明示）、DEC-318（票面范围）逐项对合；守卫既有契约（quote_sync 锚/标记/引文同步、FAIL 仅确定性事实）功能面验证通过 |
| AI 代码专项 5 项 | 全部完成 | **✓ 通过** | §四逐项结论 |
| 结论三选一（+AWN 扩展） | — | **APPROVED_WITH_NOTES** | 无 BLOCKING finding |

## 七、未验证项清单（不作通过依据，如实标注）

1. **与 HEAD `f1a47fd` 的逐行 diff**——Reviewer 无命令通道；以当前文件态实读替代。「锚行/标记行零触碰」为功能面验证（守卫正则对合 L874、标记在场 L867/L870、SKILL.md L364 引文逐字同步、行号漂移 +2 与段扩展相容），非字节级比对；「F-8 逻辑零变更」「F-C1 仅字符串值编辑」同理为实读形态判定（调用形态/判定逻辑原样）而非 diff 级证明。
2. **开发者硬门槛命令输出**（全量 verify exit 0 / check-cross-references PASS / check-manifest-consistency 1038 / 双跑 1052→1057 failures=2 / 新 5 case 全绿）——未复跑（角色契约 Bash 禁止）；间接依据=+5 与 1052→1057 精确吻合 + 5 case 断言-实现逐字对合推演自洽 + evidence-log 暂无 FIX-436 开发机录（顺序合理：hook 链要求 REVIEW 证据先行）。建议 Coordinator 收口时随 commit 证据一条命令闭合。
3. **同二预存失败归因**（ContractTierBudgetTests / Feat039InjectionBudgetTests）——不可复跑；DEC-319/FIX-438 披露链佐证该失败族预存，与本票增量面（quote_sync 测试/exploration advisory/bp 措辞）无交集，相容但非独立复核。
4. **测试实际执行绿**——未运行；以断言与实现文案逐字对合 + 隔离形态逐行核读的逻辑推演为据。

## 最终结论

**APPROVED_WITH_NOTES**

- **unresolved_blockers = 0**
- 六子项（F-2 / R1-1 / R1-2·R1-3 / F-8 / F-B3 / F-C1）全部落地且与 DEC-316/317/318 裁定及守卫既有契约逐项对合；F-B3 高风险面（不阻断/零 churn/additive/双态覆盖）四查全过。
- 2 条 P3（N-1 F-2 边角组合语义蕴含、N-2 样本元组生命周期备注）为观察级，不阻塞合并，可随后续 sweep/behavior-protocol 票顺手处置或接受现状。

---

**审查报告全文完**——交 Coordinator 经 review-record CLI 机录持久化（本 Reviewer 未写入任何文件，符合角色契约与派发禁令）。
